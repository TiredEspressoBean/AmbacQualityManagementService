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

**Reach along the chain (2026-10-21).** After a revision implemented with KEEP_ALL,
running work stays on the older version for days or weeks; a deviation raised then must
still reach it. So a temporary change lists in-flight work orders on every approved
version of its chain, and is put in force on each work order's OWN version: the version
it was drafted on gets the drafted change, and each older version gets a fork of itself
carrying the same edit (`reach_rows`, `put_in_force`). Every such version links back to
the PCR through `Processes.temporary_change`. A version where the edit doesn't apply
cleanly (a step it touches differs there) is listed but refused.
"""
from __future__ import annotations

from django.core.exceptions import ValidationError

from Tracker.services.core.clock import tenant_today


def temporary_pcr_for(process):
    """The PCR whose temporary change produced `process` (a temporary version), or None."""
    from Tracker.models import ProcessChangeRequest
    if process is None or not getattr(process, 'is_temporary', False):
        return None
    if process.temporary_change_id:
        return process.temporary_change
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
    """The process version an implemented temporary PCR was drafted as, or None. See
    `temporary_versions_of` for every version it is in force on."""
    order = getattr(pcr, 'order', None)
    if order is None or order.status != order.Status.IMPLEMENTED:
        return None
    version = order.draft_process_version
    return version if version is not None and version.is_temporary else None


def temporary_versions_of(pcr) -> list:
    """Every version an implemented temporary PCR is in force on: the drafted one, and
    the fork of each older chain version it reached. Empty when not in force."""
    from Tracker.models import Processes
    main = temporary_version_of(pcr)
    if main is None:
        return []
    others = (Processes.objects  # tenant-safe: .objects auto-scopes; keyed to the PCR
              .filter(temporary_change=pcr, is_temporary=True, archived=False)
              .exclude(pk=main.pk).order_by('version'))
    return [main, *others]


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
    """Where a work order on a temporary version goes back to: the version it branched
    from, which is the work order's own version and may be older than current (the
    deviation followed it there). A retired version is archived on approval of its
    successor but still runs its work orders, so it still counts. Only if that version
    is no longer approved does it fall to the line's current approved version."""
    from Tracker.models import ProcessStatus
    from Tracker.services.change_control.rebase import find_current_approved
    baseline = temporary_version.previous_version
    if baseline is None:
        return None
    if baseline.status == ProcessStatus.APPROVED:
        return baseline
    return find_current_approved(baseline)


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


# ---------------------------------------------------------------------------
# Reach along the version chain
# ---------------------------------------------------------------------------

def chain_versions(process) -> list:
    """The approved versions of `process`'s version chain (older, current and later)
    that a temporary change drafted on it can reach. Retired versions are in it —
    approving a successor archives its predecessor, but work orders still run it.
    Drafts, deprecated and temporary versions are not."""
    from Tracker.models import ProcessStatus
    return [v for v in process.get_version_history()
            if v.status == ProcessStatus.APPROVED and not v.is_temporary]


def _identity_edges(process) -> set:
    """Edges by step identity: stable across versions, unlike step row ids, which change
    whenever a step is versioned."""
    return {(e.from_step.identity_id, e.to_step.identity_id, e.edge_type, bool(e.pre_approved))
            for e in process.step_edges.select_related('from_step', 'to_step')}


def _changed_identities(a, b) -> set:
    """Step identities that differ between two versions: added, removed, modified (incl.
    their substeps), or whose connections changed."""
    from Tracker.services.change_control.diff import compute_process_diff
    diff = compute_process_diff(a, b)
    steps = diff.get('steps', {})
    out = {e['identity_id'] for k in ('added', 'removed', 'modified') for e in steps.get(k, [])}
    out |= set(diff.get('substeps', {}).keys())
    for edge in _identity_edges(a) ^ _identity_edges(b):
        out |= {edge[0], edge[1]}
    return {str(i) for i in out}


def _step_names(*processes) -> dict:
    names = {}
    for p in processes:
        for ps in p.process_steps.select_related('step'):
            names.setdefault(str(ps.step.identity_id), ps.step.name)
    return names


def applicability(draft, version) -> str | None:
    """Why the temporary change drafted as `draft` can't be put on `version` cleanly, or
    None when it can. Clean means every step the change touches (edits, removes, or
    reconnects) is the same on `version` as on the version it was drafted on."""
    from Tracker.services.change_control.diff import compute_process_diff
    base = draft.previous_version
    if base is None or version.pk == base.pk:
        return None
    intent = compute_process_diff(base, draft)
    added = {str(e['identity_id']) for e in intent.get('steps', {}).get('added', [])}
    touched = _changed_identities(base, draft) - added
    differs = touched & _changed_identities(version, base)
    settings = set(intent.get('process') or {}) & set(compute_process_diff(version, base).get('process') or {})
    if settings:
        return f"Doesn't apply cleanly to v{version.version}: process settings differ"
    if not differs:
        return None
    names = _step_names(base, version)
    listed = ", ".join(sorted(names.get(i, "a step") for i in differs))
    return f"Doesn't apply cleanly to v{version.version}: {listed} differs"


def reach_rows(pcr, draft) -> list:
    """The picker rows for a temporary change: in-flight work orders on every version of
    its chain, each with its version and whether the change applies to it cleanly."""
    from Tracker.services.change_control.impact_analysis import affected_workorders_with_impact
    base = draft.previous_version or pcr.target_process
    rows = []
    for version in chain_versions(base):
        reason = applicability(draft, version)
        for row in affected_workorders_with_impact(
                target_process=version, proposed_change_diff=pcr.proposed_change_diff or {},
                new_process=draft if version.pk == base.pk else None):
            row.update(version=version.version, version_id=str(version.id),
                       applies_cleanly=reason is None, not_clean_reason=reason)
            rows.append(row)
    return rows


def _fork_with_change(version, draft, pcr, *, user):
    """A DRAFT fork of `version` carrying the edit `draft` made to its own base. Steps are
    shared rows across versions, so the fork points at the draft's own step rows for
    every step the change edits or adds; it never copies them."""
    from Tracker.models import ProcessStep, StepEdge
    from Tracker.services.change_control.diff import compute_process_diff
    from Tracker.services.mes.processes import fork_version_for_deviation

    base = draft.previous_version
    intent = compute_process_diff(base, draft)
    # The process-only fork: `version` is usually retired (archived), which the generic
    # versioning won't fork.
    fork = fork_version_for_deviation(
        version, user=user,
        change_description=(f"{pcr.artifact_number}: temporary change carried onto "
                            f"v{version.version} for its in-flight work orders"))
    for field in intent.get('process') or {}:
        setattr(fork, field, getattr(draft, field))
    if intent.get('process'):
        fork.save()

    draft_ps = {str(ps.step.identity_id): ps for ps in draft.process_steps.select_related('step')}
    steps = intent.get('steps', {})
    # tenant-safe: every query below is scoped to the new fork (process=fork).
    for entry in steps.get('removed', []):
        ident = entry['identity_id']
        ProcessStep.objects.filter(process=fork, step__identity_id=ident).delete()
        StepEdge.objects.filter(process=fork, from_step__identity_id=ident).delete()
        StepEdge.objects.filter(process=fork, to_step__identity_id=ident).delete()
    swapped = {str(e['identity_id']) for e in steps.get('modified', [])} | {
        str(i) for i in (intent.get('substeps') or {})}
    for ident in swapped:
        new_row = draft_ps[ident].step
        old = ProcessStep.objects.filter(process=fork, step__identity_id=ident).first()
        if old is None or old.step_id == new_row.id:
            continue
        old_step = old.step_id
        ProcessStep.objects.filter(process=fork, step_id=old_step).update(step=new_row)
        StepEdge.objects.filter(process=fork, from_step_id=old_step).update(from_step=new_row)
        StepEdge.objects.filter(process=fork, to_step_id=old_step).update(to_step=new_row)
    for entry in steps.get('added', []):
        ps = draft_ps[str(entry['identity_id'])]
        ProcessStep.objects.create(process=fork, step=ps.step, order=ps.order,
                                   is_entry_point=ps.is_entry_point)

    # Connections, by identity: drop what the change removed, add what it added.
    rows = {ps.step.identity_id: ps.step for ps in fork.process_steps.select_related('step')}
    before, after = _identity_edges(base), _identity_edges(draft)
    for f, t, kind, pre in before - after:
        StepEdge.objects.filter(process=fork, from_step__identity_id=f, to_step__identity_id=t,
                                edge_type=kind, pre_approved=pre).delete()
    for f, t, kind, pre in after - before:
        if f in rows and t in rows:
            StepEdge.objects.create(process=fork, from_step=rows[f], to_step=rows[t],
                                    edge_type=kind, pre_approved=pre)
    return fork


def put_in_force(pcr, draft, new_version, selected_workorder_ids, *, user, resolutions=None) -> list:
    """Move the selected work orders onto the temporary change, each on its own version.

    `new_version` is the drafted change, already approved as temporary; work orders on
    the version it was drafted on go there. Every other chain version with a selected
    work order gets a fork carrying the same edit, approved as temporary with the same
    end date and linked to the PCR. Refuses, before moving anything, any work order the
    change doesn't apply to cleanly or that isn't on the chain."""
    from Tracker.models import WorkOrder
    from Tracker.services.change_control.impact_analysis import IN_FLIGHT_WORKORDER_STATUSES
    from Tracker.services.change_control.part_remap import (
        StrandedPartsNeedResolution, remap_workorder_parts)
    from Tracker.services.mes.processes import approve_process

    base = draft.previous_version or pcr.target_process
    chain = {v.pk: v for v in chain_versions(base)}
    wanted = {str(i) for i in selected_workorder_ids}
    work_orders = list(WorkOrder.objects.filter(  # tenant-safe: .objects auto-scopes
        pk__in=wanted, archived=False, workorder_status__in=IN_FLIGHT_WORKORDER_STATUSES))
    refused = []
    if len(work_orders) != len(wanted):
        refused.append("some selected work orders aren't in flight")
    for wo in work_orders:
        version = chain.get(wo.process_id)
        if version is None:
            refused.append(f"{wo.ERP_id} isn't on a version of {base.name}")
        else:
            why = applicability(draft, version)
            if why is not None:
                refused.append(f"{wo.ERP_id}: {why}")
    if refused:
        raise ValueError("Can't put the temporary change on: " + "; ".join(refused) + ".")

    new_version.temporary_change = pcr
    new_version.save(update_fields=['temporary_change', 'updated_at'])
    targets = {base.pk: new_version}
    migrated, unresolved = [], []
    for wo in work_orders:
        target = targets.get(wo.process_id)
        if target is None:
            fork = _fork_with_change(chain[wo.process_id], draft, pcr, user=user)
            target = approve_process(fork, user=user, temporary_until=pcr.temporary_until)
            target.temporary_change = pcr
            target.save(update_fields=['temporary_change', 'updated_at'])
            targets[wo.process_id] = target
        wo.process = target
        wo.save(update_fields=['process', 'updated_at'])
        unresolved.extend(remap_workorder_parts(wo, target, resolutions))
        migrated.append(wo.id)
    if unresolved:
        raise StrandedPartsNeedResolution(unresolved)
    return migrated
