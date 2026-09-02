"""Periodic auto-resolve: re-solve tenants whose live schedule needs it.

Two things make a schedule need re-solving, and only one of them is an event:

**Drift.** The staleness signals (`Tracker/signals.py`) mark the active
`ScheduleResult` out-of-date when the world changes under it (a quality hold, new
demand, lost capacity, a material receipt, …).

**The roll.** Nothing has to happen at all. The detailed window is anchored at the
moment of the solve, so a plan solved with a 30-day horizon covers only 20 days of
future a week and a half later, and work that was beyond the window has since come
into it. Waiting for a staleness event would leave a tenant with a silently
shrinking plan and newly-eligible orders nobody scheduled — the plan doesn't go
wrong, it just runs out.

This module is the half that *acts*; the `tick_auto_resolve` beat (celery_app.py)
calls it. Opt-in per tenant via `OptimizationConfig.auto_resolve` (default OFF —
nothing on the floor changes without a human). `auto_resolve_min_interval_minutes`
is an anti-churn floor covering both triggers, so a burst of changes — or a roll
landing right after a stale flag — still batches into one re-solve.
"""
from __future__ import annotations

from datetime import timedelta

# Re-plan once the live schedule's remaining coverage falls to this fraction of the
# configured window. At 2/3, a 30-day horizon rolls after ~10 days: often enough that
# the far end is never guesswork nobody revisited, rarely enough that a shop with
# LIVE auto-resolve isn't re-solving every night for no reason.
_ROLL_COVERAGE_FRACTION = 2 / 3


def due_auto_resolve_tenant_ids():
    """Tenant ids that opted into LIVE auto-resolve and are due a re-solve — because
    their live schedule went stale, or because its window has rolled — and whose last
    solve is older than their anti-churn interval.

    Runs outside request context (beat task), so reads are cross-tenant via
    `all_tenants` with explicit `tenant_id` filtering — there is no tenant
    ContextVar set. `OptimizationConfig` is one row per tenant.
    """
    from django.utils import timezone
    from Tracker.models.scheduling import (
        AutoResolveMode, OptimizationConfig, ScheduleResult,
    )

    now = timezone.now()
    due = []
    for cfg in OptimizationConfig.all_tenants.filter(auto_resolve=AutoResolveMode.LIVE):
        # created_at is the schedule's last solve time; wait the interval past it so
        # a stale flag that flipped seconds after the solve doesn't re-solve at once.
        cutoff = now - timedelta(minutes=cfg.auto_resolve_min_interval_minutes)
        schedule = (
            ScheduleResult.all_tenants.filter(
                tenant_id=cfg.tenant_id, is_active=True, is_draft=False,
                created_at__lte=cutoff,
            ).order_by('-created_at').first()
        )
        if schedule is None:
            continue
        if schedule.is_stale or _window_has_rolled(schedule, cfg, now):
            due.append(cfg.tenant_id)
    return due


def _window_has_rolled(schedule, cfg, now) -> bool:
    """Has the live plan's remaining coverage shrunk past the roll threshold?

    Measured against the CONFIGURED window, not the schedule's own span: widening
    `horizon_days` should itself trigger a roll, because the plan no longer reaches
    as far as the tenant now asks it to.
    """
    configured = timedelta(days=max(1, cfg.horizon_days))
    remaining = schedule.horizon_end - now
    return remaining <= configured * _ROLL_COVERAGE_FRACTION


def run_due_auto_resolves(queue=None):
    """Queue a live re-solve for every due tenant. Returns the tenant ids queued.

    Uses the existing `run_solve_task` (takes a tenant id, re-fetches — the async
    convention). `draft=False`, so the solve supersedes the live schedule; the
    frozen zone + planner pins keep committed near-term work in place.

    `queue` is an injectable seam for tests (default: `run_solve_task.delay`) — a
    one-arg callable taking the tenant id string. It exists so tests need not
    patch the Celery task object, which corrupts eager-result state for the run.
    """
    if queue is None:
        from Tracker.tasks import run_solve_task
        queue = run_solve_task.delay
    ids = due_auto_resolve_tenant_ids()
    for tenant_id in ids:
        queue(str(tenant_id))
    return ids
