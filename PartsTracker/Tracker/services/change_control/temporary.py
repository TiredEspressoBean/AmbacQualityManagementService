"""Temporary process changes (deviations), done through change control.

A temporary change is an ordinary PCR → PCO → PCN with three differences:

- **Scope.** It applies to the work orders named when it is implemented (migrated with
  MIGRATE_SELECTED, never KEEP_ALL / MIGRATE_ALL). Its process version is approved but
  never current: the baseline stays current and unarchived, and every new work order
  keeps using it. The named work orders' parts bound the quantity.
- **Ending.** It ends when its work orders finish, with `temporary_until` as the
  backstop. After that date its work can't start or advance until a PCR extends it, or
  the work order is moved back to the baseline.
- **Extension is a change.** A PCR whose `extends_request` names the temporary change,
  carrying the new date and no process edit, approved and implemented like any other.

Customer agreement reuses `customer_notification_required`, with the answer recorded
in `customer_agreement` (or attached) — not a separate approval gate.
"""
from __future__ import annotations

from django.core.exceptions import ValidationError

from Tracker.services.core.clock import tenant_today


def temporary_pcr_for(process):
    """The PCR whose temporary change produced `process` (a temporary version), or None."""
    from Tracker.models import ProcessChangeRequest
    if process is None or not getattr(process, 'is_temporary', False):
        return None
    return (ProcessChangeRequest.objects  # tenant-safe: .objects auto-scopes to the current tenant
            .filter(draft_process_version=process, is_temporary=True, extends_request__isnull=True)
            .order_by('-created_at').first())


def validate_temporary_request(pcr) -> None:
    """At submission: a temporary change needs a future end date; an extension needs a
    temporary change that is in force, and a later date than it has now."""
    if not pcr.is_temporary and pcr.extends_request_id is None:
        return
    today = tenant_today(pcr.tenant_id)
    if pcr.temporary_until is None:
        raise ValueError("A temporary change needs the date it ends.")
    if pcr.temporary_until <= today:
        raise ValueError("A temporary change must end after today.")
    if pcr.extends_request_id is not None:
        version = temporary_version_of(pcr.extends_request)
        if version is None:
            raise ValueError(
                f"{pcr.extends_request.artifact_number} isn't a temporary change in force, "
                f"so there is nothing to extend.")
        if version.temporary_until and pcr.temporary_until <= version.temporary_until:
            raise ValueError(
                f"An extension must end after {version.temporary_until:%Y-%m-%d}, the date "
                f"{pcr.extends_request.artifact_number} ends now.")


def temporary_version_of(pcr):
    """The process version an implemented temporary PCR put in force, or None."""
    order = getattr(pcr, 'order', None)
    if order is None or order.status != order.Status.IMPLEMENTED:
        return None
    version = order.draft_process_version
    return version if version is not None and version.is_temporary else None


def refusal(work_order) -> str | None:
    """Why `work_order` can't be worked because its temporary change has ended, or None."""
    process = getattr(work_order, 'process', None)
    if process is None or not process.is_temporary or process.temporary_until is None:
        return None
    if process.temporary_until >= tenant_today(work_order.tenant_id):
        return None
    pcr = temporary_pcr_for(process)
    number = pcr.artifact_number if pcr else f"{process.name} v{process.version}"
    return (f"{number} is a temporary change that ended on {process.temporary_until:%Y-%m-%d}. "
            f"Extend it through change control, or move {work_order.ERP_id} back to the "
            f"baseline, before more work is done.")


def assert_in_date(work_order) -> None:
    """Refuse work on an expired temporary change. Not a start-gate refusal: those can
    be overridden with a supervisor's credentials, and extending a deviation is change
    control's decision, not the floor's."""
    reason = refusal(work_order)
    if reason:
        raise ValidationError(reason)


def baseline_for(temporary_version):
    """Where a work order on a temporary version goes back to: the current approved
    version of the line it branched from — the baseline, or its successor if a
    permanent change has superseded it since."""
    from Tracker.services.change_control.rebase import find_current_approved
    baseline = temporary_version.previous_version
    return find_current_approved(baseline) if baseline is not None else None


def return_to_baseline(work_order, *, resolutions=None):
    """Move a work order off a temporary change onto the baseline, re-pointing its
    parts by step identity exactly as a migration does. Raises
    `StrandedPartsNeedResolution` when parts sit at a step the baseline lacks."""
    from django.db import transaction
    from Tracker.services.change_control.part_remap import (
        StrandedPartsNeedResolution, remap_workorder_parts)

    temporary = work_order.process
    if temporary is None or not temporary.is_temporary:
        raise ValueError(f"{work_order.ERP_id} isn't on a temporary change.")
    baseline = baseline_for(temporary)
    if baseline is None:
        raise ValueError("The temporary change has no baseline to return to.")
    with transaction.atomic():
        work_order.process = baseline
        work_order.save(update_fields=['process', 'updated_at'])
        unresolved = remap_workorder_parts(work_order, baseline, resolutions)
        if unresolved:
            raise StrandedPartsNeedResolution(unresolved)
    return work_order


def notice_lines(pcr, pco) -> str:
    """What a PCN adds for a temporary change or an extension."""
    if pcr.extends_request_id is not None:
        return (f"\n\nExtension of temporary change {pcr.extends_request.artifact_number}: "
                f"now in force until {pcr.temporary_until:%Y-%m-%d}.")
    if not pcr.is_temporary:
        return ""
    from Tracker.models import WorkOrder
    ids = [str(i) for i in (pco.migrated_workorder_ids or [])]
    names = list(WorkOrder.objects.filter(id__in=ids).order_by('ERP_id')  # tenant-safe: .objects auto-scopes
                 .values_list('ERP_id', flat=True))
    return (f"\n\nTEMPORARY change, in force until {pcr.temporary_until:%Y-%m-%d}, for "
            f"these work orders only: {', '.join(names) or 'none'}. The baseline remains "
            f"current for all other work.")
