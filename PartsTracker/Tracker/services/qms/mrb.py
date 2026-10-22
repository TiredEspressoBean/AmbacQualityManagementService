"""MRB Review — where a part goes when a step's visit cap runs out.

A step with `max_visits` (Rework 3, an inspection 2) escalates along its ESCALATION
edge once the part has used its visits. Arriving there holds the part (QUARANTINED)
and opens an unassigned disposition naming the step whose cap it hit; the existing
disposition flow decides, and this module routes the part out on that decision
(user decision 2026-10-22):

- REWORK / REPAIR → the process's rework step, and the capped step allows one more
  visit (`extra_visits`). Fail again and the part comes straight back here.
- USE_AS_IS (on a concession) → on as if the last check had passed: the pass edge of
  the capped step, or — when the capped step IS the rework step — of the check the
  part was leaving when it escalated.
- SCRAP → the existing scrap cascade; nothing to route.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone


def extra_visits(part, step) -> int:
    """Visits an MRB rework decision has granted `step` for this part: one each."""
    from Tracker.models import QuarantineDisposition
    return QuarantineDisposition.objects.filter(  # tenant-safe: scoped by the part FK
        part=part, escalated_from_step=step, archived=False,
        disposition_type__in=('REWORK', 'REPAIR')).count()


def is_hold_step(process, step) -> bool:
    """An MRB-style holding step: not terminal, no edges out, and reached only by
    escalation (visit cap) or fail (ALTERNATE) edges. The engine holds a part there
    and routes it out on the disposition. Mirrors the flow editor's rule
    (ambac-tracker-ui/src/lib/process-validation.ts)."""
    from Tracker.models import EdgeType, StepEdge
    if process is None or step is None or step.is_terminal:
        return False
    edges = StepEdge.objects.filter(process=process)  # tenant-safe: scoped by process
    if edges.filter(from_step=step).exists():
        return False
    incoming = set(edges.filter(to_step=step).values_list('edge_type', flat=True))
    return bool(incoming) and incoming <= {EdgeType.ESCALATION, EdgeType.ALTERNATE}


def open_for_escalation(part, *, capped_step, visits: int):
    """Hold the part at the escalation step and open the decision. Called by the
    advance once the part has moved there. Unassigned: the QA queue takes it."""
    return _hold(part, capped_step,
                 f"Visit cap reached at {capped_step.name} ({visits} visit(s)). "
                 f"Decide: scrap, use as is on a concession, or one more rework.",
                 supersede_rework=True)


def open_for_failure(part, *, failed_step):
    """A part sent to the holding step by a failed check (a fail edge into MRB).
    `escalated_from_step` is the check, so use-as-is continues on its pass edge.
    The FAIL report usually opened a disposition already: one finding, one decision —
    that one is adopted rather than a second opened."""
    from Tracker.models import PartsStatus, QuarantineDisposition
    open_ncr = (QuarantineDisposition.objects  # tenant-safe: scoped by the part FK
                .filter(part=part, archived=False, current_state__in=['OPEN', 'IN_PROGRESS'],
                        escalated_from_step__isnull=True)
                .order_by('created_at').first())
    if open_ncr is not None:
        open_ncr.escalated_from_step = failed_step
        open_ncr.save(update_fields=['escalated_from_step', 'updated_at'])
        if part.part_status != PartsStatus.QUARANTINED:
            part.part_status = PartsStatus.QUARANTINED
            part.save(update_fields=['part_status'])
        return open_ncr
    return _hold(part, failed_step,
                 f"Failed {failed_step.name}. "
                 f"Decide: scrap, use as is on a concession, or rework.")


def _hold(part, from_step, description, *, supersede_rework=False):
    import logging
    from Tracker.models import PartsStatus, QualityReports, QuarantineDisposition

    part.part_status = PartsStatus.QUARANTINED
    part.save(update_fields=['part_status'])
    disposition = QuarantineDisposition.objects.create(
        tenant=part.tenant, part=part, step=part.step, assigned_to=None,
        escalated_from_step=from_step, description=description)
    # The evidence: the last failed report on the part, which is what sent it round
    # the loop that ran out. A disposition is about a finding, and the edit form
    # rightly refuses one with none (MRB walk 2026-10-22).
    last_fail = (QualityReports.objects  # tenant-safe: scoped by the part FK
                 .filter(part=part, status='FAIL').order_by('-created_at').first())
    if last_fail is not None:
        disposition.quality_reports.add(last_fail)
    # The rework decision this escalation ends: its part never returns to the check
    # that would close it, so close it here, pointing at the decision that replaces it.
    reworks = (QuarantineDisposition.objects.none() if not supersede_rework else
               QuarantineDisposition.objects  # tenant-safe: scoped by the part FK
               .filter(part=part, archived=False, current_state='IN_PROGRESS',
                       disposition_type__in=('REWORK', 'REPAIR'))
               .exclude(pk=disposition.pk))
    for open_rework in reworks:
        note = (f"Superseded: the part reached the visit cap at {from_step.name} and "
                f"went to MRB under {disposition.disposition_number}.")
        open_rework.resolution_notes = (f"{open_rework.resolution_notes}\n{note}".strip()
                                        if open_rework.resolution_notes else note)
        open_rework.current_state = 'CLOSED'
        try:
            open_rework.save(update_fields=['resolution_notes', 'current_state', 'updated_at'])
        except ValueError:  # pending annotations: leave it for a person
            logging.getLogger(__name__).info(
                "Rework disposition %s left open on escalation", open_rework.pk)
    return disposition


def route_after_decision(disposition, user) -> None:
    """Move an escalated part out of MRB per the decision. No-op for a disposition
    that isn't an escalation, or a part no longer at the MRB step."""
    from Tracker.models import EdgeType, ProcessStep, StepEdge, StepExecution

    if not disposition.escalated_from_step_id or disposition.part_id is None:
        return
    kind = disposition.disposition_type
    if kind not in ('REWORK', 'REPAIR', 'USE_AS_IS'):
        return
    part = disposition.part
    part.refresh_from_db()
    process = part.work_order.process if part.work_order_id else None
    if process is None or not is_hold_step(process, part.step):
        return  # not at MRB (already routed, or never got there): nothing to move
    capped = disposition.escalated_from_step

    if kind in ('REWORK', 'REPAIR'):
        rework = [ps.step for ps in ProcessStep.objects.filter(  # tenant-safe: scoped by process
            process=process, step__step_type='REWORK').select_related('step')]
        if len(rework) != 1:
            return  # zero or ambiguous: routed by hand from the control page
        target = rework[0]
    else:
        check = capped
        if capped.step_type == 'REWORK':
            # Capped going INTO rework: the check it failed is where it came from.
            before = (StepExecution.objects  # tenant-safe: scoped by the part FK
                      .filter(part=part).exclude(step=part.step)
                      .order_by('-entered_at').first())
            check = before.step if before else capped
        edge = StepEdge.objects.filter(  # tenant-safe: scoped by process
            process=process, from_step=check, edge_type=EdgeType.DEFAULT).first()
        if edge is None:
            return
        target = edge.to_step

    _move(part, target, user)


def _move(part, step, user) -> None:
    from Tracker.models import PartsStatus, StepExecution, StepTransitionLog

    with transaction.atomic():
        StepExecution.objects.filter(  # tenant-safe: scoped by the part FK
            part=part, step=part.step, exited_at__isnull=True).update(
                status='COMPLETED', exited_at=timezone.now())
        part.step = step
        if part.part_status == PartsStatus.QUARANTINED:
            part.part_status = PartsStatus.IN_PROGRESS
        part.save(update_fields=['step', 'part_status'])
        visit = StepExecution.get_visit_count_for_update(part, step) + 1
        execution = StepExecution.objects.create(
            part=part, step=step, visit_number=visit, status='PENDING')
        from Tracker.services.dwi.sampling_decisions import evaluate_substep_sampling
        evaluate_substep_sampling(execution)
        StepTransitionLog.objects.create(part=part, step=step, operator=user)
