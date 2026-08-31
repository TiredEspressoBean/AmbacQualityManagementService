"""Periodic auto-resolve: re-solve tenants whose live schedule has drifted stale.

The staleness signals (`Tracker/signals.py`) mark the active `ScheduleResult`
out-of-date when the world changes under it (a quality hold, new demand, lost
capacity, a material receipt, …). This module is the half that *acts* on that
flag — the `tick_auto_resolve` beat (celery_app.py) calls it.

Opt-in per tenant via `OptimizationConfig.auto_resolve` (default OFF — nothing on
the floor changes without a human). `auto_resolve_min_interval_minutes` is an
anti-churn floor so a burst of changes batches into one re-solve.
"""
from __future__ import annotations

from datetime import timedelta


def due_auto_resolve_tenant_ids():
    """Tenant ids whose live schedule is stale, that opted into LIVE auto-resolve,
    and whose last solve is older than their anti-churn interval.

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
        is_due = ScheduleResult.all_tenants.filter(
            tenant_id=cfg.tenant_id, is_active=True, is_draft=False,
            is_stale=True, created_at__lte=cutoff,
        ).exists()
        if is_due:
            due.append(cfg.tenant_id)
    return due


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
