"""Mark a tenant's active committed schedule stale from outside a solve.

`ScheduleResult.is_stale` is an advisory UI flag ("schedule out of date —
re-solve"). It is set when a fresh solve supersedes the active plan, by the
reactive signals in `Tracker/signals.py`, and by service paths that change the
schedulable set without going through a `post_save` the signals watch — notably
bulk `.update()` / `bulk_update` quarantines in `services/qms/` (quality_gate,
batch_disposition), which the `Parts` disruption signal never sees.

Keeping the mechanism in one place means every path trips the flag identically.
"""
from __future__ import annotations


def mark_active_schedule_stale(tenant_id) -> None:
    """Flip the tenant's active, committed schedule to stale.

    Bulk `.update()` (intentionally) bypasses auditlog and save signals —
    `is_stale` is an advisory UI flag, not an audited business fact, and this
    avoids re-entrancy. Drafts are what-if scenarios that never went live, so
    they are left alone.
    """
    if not tenant_id:
        return
    from Tracker.models import ScheduleResult
    # all_tenants + explicit tenant_id: callers run in varied contexts (requests,
    # signals, beat tasks); don't depend on the tenant ContextVar being set.
    ScheduleResult.all_tenants.filter(
        tenant_id=tenant_id, is_active=True, is_draft=False, is_stale=False,
    ).update(is_stale=True)
