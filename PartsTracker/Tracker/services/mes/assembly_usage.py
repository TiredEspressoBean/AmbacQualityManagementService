"""
AssemblyUsage aggregate services.

Tiny for now — one mutator. Expand here if the removal flow grows
side effects (inventory returns, audit logs, etc.).
"""
from __future__ import annotations

from django.utils import timezone

from Tracker.models import AssemblyUsage


def remove_assembly_usage(
    usage: AssemblyUsage,
    user,
    reason: str = '',
) -> AssemblyUsage:
    """Mark a component as removed from the assembly.

    A reman unit finished and ready to go back goes back to In Rebuild — it's missing
    a component now, so it isn't ready to ship until the slot is filled again (user
    decision 2026-10-26). A unit that has already left can't have components removed.
    """
    from django.core.exceptions import ValidationError
    from django.db import transaction
    from Tracker.services.reman.core_steps import core_of

    core = core_of(usage.assembly) if usage.assembly_id else None
    if core is not None and core.status in ('RETURNED', 'RETURNED_UNREPAIRED', 'SHIPPED'):
        raise ValidationError(
            f"{core.core_number} has already gone ({core.get_status_display()}) — its as-built "
            "record stands.")
    with transaction.atomic():
        usage.removed_at = timezone.now()
        usage.removed_by = user
        usage.removal_reason = reason
        usage.save()
        if core is not None and core.status in ('REBUILT', 'REBUILT_TO_STOCK'):
            from Tracker.services.reman.core_part import sync_part_status
            who = (user.get_full_name() or user.get_username()) if user else 'system'
            why = (reason or '').strip().rstrip('.')
            line = (f"{timezone.now():%Y-%m-%d} {who}: back to rebuild — {usage.component or usage.component_harvested} "
                    f"removed{f': {why}' if why else ''}.")
            core.status = 'IN_REBUILD'
            core.condition_notes = f"{core.condition_notes}\n{line}".strip()
            core.save(update_fields=['status', 'condition_notes', 'updated_at'])
            sync_part_status(core)
    return usage
