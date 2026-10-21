"""
QuarantineDisposition aggregate services.

Holds the disposition aggregate's business logic: applying a disposition's
decision to its part's status (`apply_disposition_to_part`) and the top-level
close flow (`complete_disposition_resolution`). `QuarantineDisposition.save()`
delegates the part cascade here rather than carrying it inline.
"""
from __future__ import annotations

import logging

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from Tracker.services.core.clock import tenant_today

from Tracker.models import QuarantineDisposition

logger = logging.getLogger(__name__)


def _auto_disposition_description(report) -> str:
    """What failed, in words. A report captured at a step usually has no description
    of its own, which left every auto-opened disposition reading "No description"."""
    if (report.description or "").strip():
        return f"Failed quality report: {report.description.strip()}"
    where = report.step.name if report.step_id else "inspection"
    findings = []
    if report.pk:
        findings += [d for d in report.defects.select_related("error_type")
                     .values_list("error_type__error_name", flat=True)[:3] if d]
        # The readings that failed, with their limits, so QA can decide from the
        # disposition without opening the report.
        for m in report.measurements.select_related("definition").filter(is_within_spec=False)[:3]:
            findings.append(_reading_text(m))
    return f"Failed {where}" + (f": {', '.join(findings)}" if findings else "")


def _findings(report) -> list[str]:
    """A failed report's findings in words: its own description, else its defects and
    out-of-spec readings."""
    if (report.description or "").strip():
        return [report.description.strip()]
    out = [d for d in report.defects.select_related("error_type")
           .values_list("error_type__error_name", flat=True)[:3] if d]
    out += [_reading_text(m) for m in
            report.measurements.select_related("definition").filter(is_within_spec=False)[:3]]
    return out


def refresh_disposition_description(disposition) -> None:
    """Rewrite an auto-written description from every report the disposition now holds.

    A step's captures land after its report is first saved FAIL (defects, a second
    report joining), so the description written at that moment named only the step.
    Only an auto-written one ("Failed …") is rewritten — never what a person typed."""
    if not (disposition.description or "").startswith("Failed"):
        return
    findings = []
    for r in disposition.quality_reports.order_by("created_at"):
        for f in _findings(r):
            if f not in findings:
                findings.append(f)
    where = disposition.step.name if disposition.step_id else "inspection"
    text = f"Failed {where}" + (f": {', '.join(findings)}" if findings else "")
    if text != disposition.description:
        disposition.description = text
        disposition.save(update_fields=["description"])


def _reading_text(m) -> str:
    """'Bore Diameter 4.007 mm (limits 3.995–4.005)' — or the pass/fail verdict."""
    d = m.definition
    if m.value_numeric is None:
        return f"{d.label} {m.value_pass_fail or 'FAIL'}"
    unit = f" {d.unit}" if d.unit else ""
    value = f"{m.value_numeric:g}"
    limits = ""
    if d.nominal is not None and (d.upper_tol is not None or d.lower_tol is not None):
        lo = f"{float(d.nominal - (d.lower_tol or 0)):g}"
        hi = f"{float(d.nominal + (d.upper_tol or 0)):g}"
        limits = f" (limits {lo}–{hi})"
    return f"{d.label} {value}{unit}{limits}"


def open_disposition_for_failed_report(report) -> QuarantineDisposition:
    """The disposition a failed in-process report belongs to: the one already open for
    this part at this step on this visit, or a new one.

    One nonconformance is one decision. A step can file several reports for a single
    finding — a visual with a defect and a measurement that's out — and each opened
    its own disposition, so QA owed two decisions and had to close both before the
    part could move (walk 2026-10-20). A later visit, or another step, is a new
    finding and opens its own. Auto-opened dispositions are unassigned: the QA queue
    takes them (user decision 2026-10-20).
    """
    from Tracker.models import StepExecution

    part, step = report.part, report.step
    if part is not None and step is not None:
        visit = (StepExecution.objects  # tenant-safe: scoped by the part FK
                 .filter(archived=False, part=part, step=step)
                 .order_by('-entered_at').first())
        if visit is not None:
            same_finding = (QuarantineDisposition.objects  # tenant-safe: scoped by the part FK
                            .filter(archived=False, part=part, step=step,
                                    current_state__in=['OPEN', 'IN_PROGRESS'],
                                    created_at__gte=visit.entered_at)
                            .order_by('created_at').first())
            if same_finding is not None:
                same_finding.quality_reports.add(report)
                refresh_disposition_description(same_finding)
                return same_finding

    existing_rework_count = 0
    if part is not None and step is not None:
        existing_rework_count = QuarantineDisposition.objects.filter(  # tenant-safe: part FK
            part=part, step=step, disposition_type='REWORK').count()
    disposition = QuarantineDisposition.objects.create(
        assigned_to=None,
        part=part,
        step=step,
        rework_attempt_at_step=existing_rework_count + 1,
        description=_auto_disposition_description(report),
    )
    disposition.quality_reports.add(report)
    return disposition


def apply_disposition_to_part(disposition: QuarantineDisposition, *, user=None) -> None:
    """Apply a disposition's decision to its part's status.

    Maps `disposition_type` to a part status and, for REWORK/REPAIR, bumps the
    rework counter. Idempotent: if the part is already at the mapped status it is
    a no-op, so it never double-applies or double-increments.

    Intended to fire when the `disposition_type` is *set or changed* (the
    OPEN->IN_PROGRESS decision), NOT on close — `QuarantineDisposition.save()`
    only calls this on a type change, so a later close can't re-apply/re-increment.

    `user` is accepted for symmetry with non-request callers; in the request path
    auditlog attributes the `part.save()` to `request.user` via middleware.
    """
    from Tracker.models import PartsStatus, Parts

    if disposition.part_id is None or not disposition.disposition_type:
        return

    # Only act once the decision is being implemented (or closed).
    if disposition.current_state not in ('IN_PROGRESS', 'CLOSED'):
        return

    # Keys MUST match the uppercase DISPOSITION_TYPES values.
    status_mapping = {
        'REWORK': PartsStatus.REWORK_NEEDED,
        'REPAIR': PartsStatus.REWORK_NEEDED,  # AS9100: may not fully conform
        'SCRAP': PartsStatus.SCRAPPED,
        # Accepted as it is: back at work on its step. Not READY_FOR_NEXT_STEP —
        # that is the batch-staging status (advance_part_step sets it while a unit
        # waits for its batch), so a use-as-is part read as batch-staged on every
        # queue and dispatch list until someone completed the step. The disposition
        # is a decision, not routing; the operator completes the step as usual.
        'USE_AS_IS': PartsStatus.IN_PROGRESS,
        'RETURN_TO_SUPPLIER': PartsStatus.CANCELLED,
    }

    # QMS design intent: a disposition is a *documented decision*, not a
    # routing action. Loop-back decisions (REWORK / REPAIR) only translate
    # into a part-status change while the part is still held awaiting a
    # decision — QUARANTINED, or the initial PENDING before it entered
    # production. Once the part has moved past that point (IN_PROGRESS at
    # a step, AWAITING_QA at visit N, REWORK_IN_PROGRESS, terminal, etc.)
    # the disposition is a paper record of what was authorized; the
    # operator has already routed the part, and cascading REWORK_NEEDED
    # would drag it backwards.
    #
    # Terminal decisions (SCRAP / USE_AS_IS / RETURN_TO_SUPPLIER) keep the
    # cascade at any state — closing an NCR with SCRAP IS the terminal
    # decision, and the terminal-precedence guard below still protects
    # against downgrades.
    LOOPBACK_TYPES = ('REWORK', 'REPAIR')
    ROUTABLE_STATUSES = (PartsStatus.QUARANTINED, PartsStatus.PENDING)
    new_status = status_mapping.get(disposition.disposition_type)
    if not new_status:
        return  # unknown type

    # Terminal-dominant precedence (2a): a less-severe disposition must not pull a
    # part out of — or downgrade — a terminal status. SCRAP dominates everything;
    # a REWORK/REPAIR/USE_AS_IS decision can't reactivate a SCRAPPED/CANCELLED part.
    # (Reversing a terminal status is the deliberate, permission-gated bulk path
    # from 0d, never an incidental side-effect of another disposition.)
    terminal_rank = {
        PartsStatus.SCRAPPED: 3,
        PartsStatus.CANCELLED: 2,
        PartsStatus.COMPLETED: 1,
        PartsStatus.SHIPPED: 1,
        PartsStatus.IN_STOCK: 1,
        PartsStatus.AWAITING_PICKUP: 1,
        PartsStatus.CORE_BANKED: 1,
        PartsStatus.RMA_CLOSED: 1,
        PartsStatus.DISMANTLED: 1,
    }

    # Lock the part so the read-check-write below is atomic. Dispositions are
    # per-QR (several can target one part), and the advancement engine writes
    # part_status too; without the lock two concurrent appliers each read a
    # stale status and the precedence guard can be defeated — e.g. a REWORK
    # decision reviving a part another disposition just SCRAPPED, or the rework
    # counter double-incrementing. The second applier blocks here, then re-reads
    # the committed status and the guard holds.
    with transaction.atomic():
        part = Parts.objects.select_for_update().get(pk=disposition.part_id)
        if part.part_status == new_status:
            return  # idempotent no-op
        if part.part_status == PartsStatus.SHIPPED:
            # Gone to the customer: nothing here can scrap or cancel it, and a
            # disposition on it is a record (decide_disposition refuses the decision;
            # this is the backstop for the model-save cascade).
            return
        if terminal_rank.get(part.part_status, 0) > terminal_rank.get(new_status, 0):
            return  # current terminal status outranks this decision — don't regress it
        # A decision that puts the part back to work (use as is, rework) releases it
        # only when nothing else on it is still undecided: another open nonconformance
        # keeps it held (walk 2026-10-20 — a use-as-is on one disposition put the part
        # back in production while its twin was OPEN). The last decision releases it.
        # Terminal decisions (scrap, return) don't wait.
        if disposition.disposition_type in ('USE_AS_IS', 'REWORK', 'REPAIR'):
            undecided_elsewhere = (QuarantineDisposition.objects  # tenant-safe: part FK
                                   .filter(part_id=part.pk, archived=False,
                                           current_state__in=['OPEN', 'IN_PROGRESS'])
                                   .filter(Q(disposition_type__isnull=True) | Q(disposition_type=''))
                                   .exclude(pk=disposition.pk).exists())
            if undecided_elsewhere:
                return
        # Loop-back-only guard: REWORK/REPAIR only routes parts that are still
        # held awaiting a decision. If the part has already moved on
        # (AWAITING_QA, IN_PROGRESS, REWORK_IN_PROGRESS, READY, etc.), the
        # disposition is a paper record — someone has already routed the part.
        if (disposition.disposition_type in LOOPBACK_TYPES
                and part.part_status not in ROUTABLE_STATUSES):
            return

        # A core's part takes its status from the core's reman stage
        # (Documents/CORE_AS_PART_DESIGN.md), so scrapping one is a stage change:
        # written straight to the part, the core would still read as in teardown or
        # rebuild and the next stage write would revive the part.
        if new_status == PartsStatus.SCRAPPED:
            from Tracker.services.reman.core_part import scrap_if_core

            if scrap_if_core(part, reason=f"disposition {disposition.disposition_number}"):
                return

        part.part_status = new_status
        if disposition.disposition_type in ('REWORK', 'REPAIR'):
            part.total_rework_count += 1
        part.save(update_fields=['part_status', 'total_rework_count'])


# USE_AS_IS and REPAIR accept known-nonconforming product, so the standard treats
# them as the highest-authority decisions — requiring recorded customer / design
# approval (a concession or deviation) before the disposition is authorized.
_APPROVAL_REQUIRED_TYPES = {'USE_AS_IS', 'REPAIR'}

# Decisions that act on a unit we hold — refused once it has shipped.
_OFF_SITE_REFUSED_TYPES = {'SCRAP', 'RETURN_TO_SUPPLIER'}


def decide_disposition(
    disposition: QuarantineDisposition,
    *,
    disposition_type: str,
    authorized_by,
    notes: str = '',
    customer_approval: dict | None = None,
) -> QuarantineDisposition:
    """Authorize and record a disposition decision (its ``disposition_type``).

    Choosing rework / repair / scrap / use-as-is / return-to-supplier is the
    authorized act under AS9100 & ISO 9001 8.7 and 21 CFR 820.90: the record must
    carry who authorized it, captured here as ``decision_authorized_by`` /
    ``_at``. Setting the type drives the existing cascade in
    ``QuarantineDisposition.save()`` — OPEN -> IN_PROGRESS and the part-status
    update via ``apply_disposition_to_part``.

    ``authorized_by`` is whoever the viewset resolved as the authority: the
    caller when they hold ``approve_disposition``, or an inline co-signer.

    Raises:
        ValueError: unknown type; a decision on a closed record; or a
            USE_AS_IS / REPAIR decision without a customer/design-approval
            reference (these accept nonconforming product and need a concession).
    """
    valid = dict(QuarantineDisposition.DISPOSITION_TYPES)
    if disposition_type not in valid:
        raise ValueError(f"Unknown disposition type: {disposition_type!r}.")

    if disposition.current_state == 'CLOSED':
        raise ValueError("This disposition is closed; its decision can no longer be changed.")

    # Rework and repair act on a part, which a bought lot isn't: the decision was
    # recorded and the lot sat REJECTED with nothing to do. Its outcomes are back to the
    # supplier, scrap, or use as-is on a concession.
    if disposition.material_lot_id and disposition_type in ('REWORK', 'REPAIR'):
        raise ValueError(
            "A material lot can't be reworked or repaired here — return it to the supplier "
            "(who can sort or rework it), scrap it, or use it as-is on a concession.")

    # A shipped unit is at the customer: we can't scrap it or send it back to a
    # supplier, and writing either would make the record say it never left.
    if disposition_type in _OFF_SITE_REFUSED_TYPES and disposition.part_id:
        from Tracker.models import Parts
        # Read fresh: the cached `disposition.part` can predate the shipment.
        part = Parts.objects.select_related('customer_shipment__customer').get(  # tenant-safe: by the disposition's FK
            pk=disposition.part_id)
        if part.part_status == 'SHIPPED':
            shipment = part.customer_shipment
            where = f" on {shipment.shipment_number} to {shipment.customer.name}" if shipment else ""
            raise ValueError(
                f"{part.ERP_id} has already shipped{where}. It isn't here to "
                f"{'scrap' if disposition_type == 'SCRAP' else 'return to a supplier'} "
                "— handle it as a customer return.")

    if disposition_type in _APPROVAL_REQUIRED_TYPES:
        reference = str((customer_approval or {}).get('reference') or '').strip()
        if not reference:
            raise ValueError(
                f"A '{valid[disposition_type]}' decision accepts nonconforming product and "
                "requires recorded customer/design approval — provide an approval reference."
            )
        disposition.requires_customer_approval = True
        disposition.customer_approval_received = True
        disposition.customer_approval_reference = reference
        disposition.customer_approval_date = (
            (customer_approval or {}).get('date') or tenant_today(disposition.tenant)
        )

    disposition.disposition_type = disposition_type
    disposition.decision_authorized_by = authorized_by
    disposition.decision_authorized_at = timezone.now()
    if notes:
        existing = disposition.resolution_notes or ''
        disposition.resolution_notes = f"{existing}\n{notes}".strip() if existing else notes

    disposition.save()
    disposition.refresh_from_db()
    # A material lot's disposition moves the lot (accepted on concession / scrapped);
    # a part's is applied by the model's own cascade.
    if disposition.material_lot_id:
        from Tracker.services.qms.lot_reject import apply_disposition_to_lot
        apply_disposition_to_lot(disposition)
    return disposition


def complete_disposition_resolution(
    disposition: QuarantineDisposition,
    user,
) -> QuarantineDisposition:
    """Mark resolution as completed and close the disposition if in progress.

    The blocker check + state mutation + save run inside a transaction
    with SELECT FOR UPDATE so a concurrent writer can't add a new blocker
    (e.g., a fresh quality report) between the check and the save.
    Without this, the disposition could close while a blocker is in flight,
    leaving the parts cascade in `QuarantineDisposition.save()` to act on
    a stale state.

    Raises:
        ValueError: blockers exist (pending annotations, etc.).
    """
    with transaction.atomic():
        # Lock the row so the blocker check below sees a consistent view.
        # Tenant-scoped (`.objects`): every caller runs under request or
        # tenant_context (serializer decision path, advance-off-rework close,
        # the async advance task), so this stays within the active tenant
        # rather than reaching across tenants via `.unscoped`.
        locked = (
            QuarantineDisposition.objects
            .select_for_update()
            .get(pk=disposition.pk)
        )

        blockers = locked.get_completion_blockers()
        if blockers:
            raise ValueError(
                f"Cannot complete disposition: {'; '.join(blockers)}"
            )

        # Completing a return-to-supplier on a lot means it went back: ship it, which
        # closes this record too. Closed here instead, the lot stayed REJECTED and
        # shipping it was then refused for want of an open disposition.
        if (locked.material_lot_id and locked.disposition_type == 'RETURN_TO_SUPPLIER'
                and locked.material_lot.status == 'REJECTED'):
            from Tracker.services.qms.lot_reject import ship_back
            ship_back(locked.material_lot, user)
            disposition.refresh_from_db()
            return disposition

        locked.resolution_completed = True
        locked.resolution_completed_by = user
        locked.resolution_completed_at = timezone.now()

        if locked.current_state == 'IN_PROGRESS':
            locked.current_state = 'CLOSED'

        locked.save()

    disposition.refresh_from_db()
    return disposition


def route_part_to_rework_if_needed(disposition: QuarantineDisposition, user) -> None:
    """Route a REWORK/REPAIR disposition's part to the process's in-process rework
    step at *decision* time (when the type is set) — split off the lot and moved
    there, while the disposition stays IN_PROGRESS until the rework is re-inspected
    (2e closes it then). Per AS9100, a rework/repair isn't resolved until
    re-inspection passes, so the NCR-decision record stays open until verified.

    No-op unless: the type is REWORK/REPAIR, the part exists and isn't already
    split, and the process has exactly ONE rework step (zero or ambiguous → leave
    it REWORK_NEEDED for manual routing via the control page, 2c). Idempotent."""
    if disposition.disposition_type not in ('REWORK', 'REPAIR'):
        return
    part = disposition.part
    if part is None or part.split_from_lot:
        return
    process = part.work_order.process if part.work_order_id else None
    if process is None:
        return

    from Tracker.models import ProcessStep, PartSplitReason

    rework_steps = {
        ps.step_id: ps.step
        for ps in ProcessStep.objects.filter(
            process=process, step__step_type='REWORK',
        ).select_related('step')
    }
    if len(rework_steps) != 1:
        return  # zero or ambiguous — manual routing (2c)

    from Tracker.services.mes.splits import split_part_from_lot
    target = next(iter(rework_steps.values()))
    split_part_from_lot(
        part=part,
        reason=PartSplitReason.REWORK,
        user=user,
        rework_target_step=target,
        notes=f"Routed from disposition {disposition.disposition_number}",
    )
    logger.info(
        "Routed part %s to rework step %s from disposition %s",
        part.id, target.id, disposition.pk,
    )


def record_containment_complete(disposition, user) -> None:
    """Containment is done: stamp who recorded it and when (the logged-in user, now).
    Who physically did it, if someone else, is `containment_performed_by` — the
    caller's to set. Idempotent: an already-recorded containment keeps its stamp."""
    if disposition.containment_completed_at:
        return
    if not (disposition.containment_action or "").strip():
        raise ValueError("Describe the containment action before marking it complete.")
    disposition.containment_completed_by = user if getattr(user, "is_authenticated", False) else None
    disposition.containment_completed_at = timezone.now()
    disposition.save(update_fields=["containment_completed_by", "containment_completed_at", "updated_at"])


def record_scrap_verification(disposition, user, *, verified: bool) -> None:
    """Scrap verified (or un-verified): the verifier is whoever records it — this is
    their own attestation that the product was rendered unusable, so there is no
    separate "performed by"."""
    if verified and not disposition.scrap_verified_at:
        disposition.scrap_verified = True
        disposition.scrap_verified_by = user if getattr(user, "is_authenticated", False) else None
        disposition.scrap_verified_at = timezone.now()
    elif not verified:
        disposition.scrap_verified = False
        disposition.scrap_verified_by = None
        disposition.scrap_verified_at = None
    else:
        return
    disposition.save(update_fields=["scrap_verified", "scrap_verified_by", "scrap_verified_at", "updated_at"])

