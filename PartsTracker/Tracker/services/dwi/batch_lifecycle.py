"""
BatchExecution lifecycle service — the only write path for sealing and completing a
load.

Every batch step has three phases (user decision 2026-11-03):

  1. **Load** (attended): the load is started and the batch substeps up to the
     step's seal point are done.
  2. **Seal**: the load closes — membership locked — and the machine runs; the
     operator may walk away. The seal point is the batch substep flagged
     `seals_load` (confirming it seals the load); with none, it sits after the last
     batch substep and the operator presses Seal.
  3. **Complete**: the operator comes back, does the batch substeps after the seal
     point (none, when unflagged: a bare Complete), and completes the load. That
     stamps `completed_at` and fires advancement. **Parts advance at Complete, never
     at Seal.**

Started -> sealed is the attended load time; sealed -> completed the cycle
(services/scheduling/measured). A FAIL on a completion-phase inspection contains the
load as any batch FAIL does (qms.batch_disposition.contain_failed_batch).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

if TYPE_CHECKING:
    from Tracker.models import BatchExecution, User


logger = logging.getLogger(__name__)

# Cohorts at or below this size advance synchronously in the seal request so
# the operator sees the move immediately; larger cohorts defer advancement to
# Celery (3d) to keep the seal request bounded.
ASYNC_ADVANCE_THRESHOLD = 50


def _queue_lot_advance(**kwargs):
    """Queue a cohort's advancement. A seam of our own for tests to patch: patching
    `.delay` on the Celery task object corrupts eager-result state for the rest of a
    test run."""
    from Tracker.tasks import advance_lot_task
    advance_lot_task.delay(**kwargs)


def batch_phases(step) -> tuple[list, list]:
    """(load-phase, completion-phase) batch substeps of `step`, each in order. The
    substep flagged `seals_load` ends the load phase; with none, every batch substep
    is in the load phase and the completion phase is empty."""
    from Tracker.models import Substep, SubstepScope
    subs = list(Substep.objects.filter(step=step, scope=SubstepScope.BATCH, archived=False)  # tenant-safe: FK to a scoped step
                .order_by('order', 'created_at'))
    seal = next((i for i, s in enumerate(subs) if s.seals_load), None)
    if seal is None:
        return subs, []
    return subs[:seal + 1], subs[seal + 1:]


def phase_of(substep) -> str:
    """'load' or 'completion': which phase of its step's batch substeps this is."""
    load, _ = batch_phases(substep.step)
    return 'load' if any(s.id == substep.id for s in load) else 'completion'


def keep_one_seal_point(substep) -> None:
    """One seal point per step: flagging a substep `seals_load` moves the seal point
    there, clearing it from the step's other substeps."""
    from Tracker.models import Substep
    if not getattr(substep, 'seals_load', False):
        return
    (Substep.objects.filter(step_id=substep.step_id, seals_load=True)  # tenant-safe: FK to a scoped step
     .exclude(pk=substep.pk).update(seals_load=False))


def _missing(batch, substeps) -> list[str]:
    """Required substeps among `substeps` with no live completion on the batch."""
    from Tracker.models import SubstepCompletion
    required = [s for s in substeps if not s.is_optional]
    done = set(SubstepCompletion.objects.filter(  # tenant-safe: keyed to a scoped batch
        batch_execution_id=batch.id, substep_id__in=[s.id for s in required], is_voided=False,
    ).values_list('substep_id', flat=True))
    return [f"Batch substep '{s.title}' has no completion on this batch."
            for s in required if s.id not in done]


@dataclass(frozen=True)
class CompleteResult:
    batch_id: str
    completed_at: str
    # What happened to the load's own parts (walk 2026-11-04: "its parts move on" was
    # said when the lot held them back). Not known when advancement went to Celery.
    moved: int = 0
    waiting: int = 0
    waiting_reasons: tuple = ()  # the advancement's own words, e.g. the lot-wait text
    queued: bool = False


@dataclass(frozen=True)
class SealResult:
    batch_id: str
    sealed_at: str
    problems: list[str]


def assert_no_open_batch_overlap(*, step, parts) -> None:
    """3c — disjoint-membership invariant for open batches.

    A part may be a member of at most one OPEN (not yet completed) batch at a
    given step — loading, or sealed and running. Multiple concurrent open batches
    per (WO, step) are allowed — a fixed-capacity op (furnace/wash/autoclave)
    legitimately splits one lot into several loads — but their membership must be
    disjoint, else it's ambiguous which load's cycle data covers the part.

    Completed loads don't count: a part may later join a new batch (rare, but
    valid — a redo).

    Raises ValidationError naming the overlapping part count.
    """
    from Tracker.models import BatchExecution

    part_ids = [getattr(p, 'id', p) for p in parts]
    if not part_ids:
        return
    in_open_batch = set(
        BatchExecution.objects.filter(archived=False,
            step=step, completed_at__isnull=True, parts__id__in=part_ids,
        ).values_list('parts__id', flat=True)
    )
    overlapping = in_open_batch & set(part_ids)
    if overlapping:
        raise ValidationError(
            f"{len(overlapping)} selected part(s) are already in an open batch "
            "at this step. Complete that load before starting another with them."
        )


def seal_batch(*, batch: "BatchExecution", user: "User") -> SealResult:
    """Seal a load: it's loaded, its load-phase substeps are done, and the machine
    runs. Locks membership; does NOT advance the parts (complete_batch does). Raises
    ValidationError if it isn't ready to seal (missing load-phase completions,
    foreign parts, empty)."""
    from Tracker.models import BatchExecution
    from Tracker.services.mes.parts import TERMINAL_PART_STATUSES

    # One transaction holds a row lock on the batch across check -> validate -> seal,
    # so two concurrent seals can't both pass the already-sealed check. The second
    # blocks on the lock, then sees sealed_at set and returns the idempotent result.
    with transaction.atomic():
        batch = BatchExecution.objects.select_for_update().get(pk=batch.id)

        if batch.sealed_at is not None:
            return SealResult(
                batch_id=str(batch.id),
                sealed_at=batch.sealed_at.isoformat(),
                problems=[],
            )

        problems: list[str] = []
        members = list(batch.parts.all())

        # 3c — membership reconciliation: a member that went terminal
        # (scrapped/cancelled) after batch start is no longer a live cohort
        # member. Drop it from the batch so seal doesn't validate against — or
        # later try to advance — a dead part. Split parts stay (Case-19: the
        # batch substep still covers a split-out part's operation).
        dropped = [p for p in members if p.part_status in TERMINAL_PART_STATUSES]
        if dropped:
            batch.parts.remove(*dropped)
            logger.info(
                "Seal reconcile: dropped %d terminal part(s) from batch %s: %s",
                len(dropped), batch.id, [str(p.id) for p in dropped],
            )
        parts = [p for p in members if p.part_status not in TERMINAL_PART_STATUSES]

        if not parts:
            problems.append("Batch has no live parts (all members are scrapped/cancelled).")

        foreign = [p for p in parts if p.work_order_id != batch.work_order_id]
        if foreign:
            problems.append(
                f"Batch contains parts from other WOs: {[str(p.id) for p in foreign]}. "
                "One BatchExecution per WO is invariant."
            )

        load_phase, _ = batch_phases(batch.step)
        problems += _missing(batch, load_phase)

        if problems:
            raise ValidationError(problems)

        batch.sealed_at = timezone.now()
        batch.save(update_fields=['sealed_at'])
        logger.info("BatchExecution %s sealed by user %s", batch.id, user.id)

    return SealResult(
        batch_id=str(batch.id),
        sealed_at=batch.sealed_at.isoformat(),
        problems=[],
    )


def complete_batch(*, batch: "BatchExecution", user: "User") -> CompleteResult:
    """Complete a sealed load: the run is finished and the completion-phase substeps
    are done. Stamps completed_at / completed_by and releases the parts to advance;
    this, not the seal, is the cohort's "Complete step". Idempotent once completed.

    Raises:
        ValidationError: the load isn't sealed yet, or a required completion-phase
            substep has no completion on it.
    """
    from Tracker.models import BatchExecution
    from Tracker.services.mes.parts import TERMINAL_PART_STATUSES

    with transaction.atomic():
        batch = BatchExecution.objects.select_for_update().get(pk=batch.id)
        if batch.completed_at is not None:
            return CompleteResult(batch_id=str(batch.id), completed_at=batch.completed_at.isoformat())
        if batch.sealed_at is None:
            raise ValidationError("Seal the load before completing it.")
        _, completion_phase = batch_phases(batch.step)
        problems = _missing(batch, completion_phase)
        if problems:
            raise ValidationError(problems)

        batch.completed_at = timezone.now()
        batch.completed_by = user
        batch.save(update_fields=['completed_at', 'completed_by'])
        logger.info("BatchExecution %s completed by user %s", batch.id, user.id)

        live = [p for p in batch.parts.all() if p.part_status not in TERMINAL_PART_STATUSES]
        # Small cohorts advance synchronously so the operator sees the move
        # immediately. Large cohorts (3d) would make the request gate + advance
        # hundreds of parts inline and risk a timeout, so dispatch the advancement
        # to Celery after commit; the load is completed regardless.
        if len(live) > ASYNC_ADVANCE_THRESHOLD:
            wo_id = str(batch.work_order_id)
            step_id = str(batch.step_id)
            tenant_id = str(batch.tenant_id)
            operator_id = getattr(user, 'id', None)
            transaction.on_commit(
                lambda: _queue_lot_advance(
                    work_order_id=wo_id,
                    step_id=step_id,
                    tenant_id=tenant_id,
                    operator_id=operator_id,
                )
            )
            logger.info("Batch %s complete: %d-part cohort - advancement dispatched async.",
                        batch.id, len(live))
            return CompleteResult(batch_id=str(batch.id),
                                  completed_at=batch.completed_at.isoformat(), queued=True)
        from Tracker.models import Parts
        from Tracker.services.mes.advancement import try_advance_lot
        result = try_advance_lot(
            work_order_id=str(batch.work_order_id),
            step_id=str(batch.step_id),
            tenant_id=str(batch.tenant_id),
            operator=user,
        )
        # Which of the load's parts actually left the step, and why the rest didn't.
        still = set(Parts.objects.filter(  # tenant-safe: .objects auto-scopes; pks from the load
            pk__in=[p.pk for p in live], step_id=batch.step_id).values_list('pk', flat=True))
        reasons = []
        for p in live:
            if p.pk in still:
                for r in (result.blockers_by_part.get(str(p.id))
                          or result.split_parts_blocked.get(str(p.id)) or []):
                    if r not in reasons:
                        reasons.append(r)

    return CompleteResult(batch_id=str(batch.id), completed_at=batch.completed_at.isoformat(),
                          moved=len(live) - len(still), waiting=len(still),
                          waiting_reasons=tuple(reasons))


# What a membership change records when no reason is given: while a part's step is still
# being worked the load is too, and the record that matters is the one confirmed when
# the step completes (user decision 2026-11-03).
OPEN_LOAD_CORRECTION = "Corrected while the load was open"


def _record_membership(batch, user, *, added=None, removed=None, reason=""):
    from django.contrib.contenttypes.models import ContentType
    from Tracker.models import BatchExecution, RecordEdit
    RecordEdit.objects.create(
        tenant=batch.tenant, content_type=ContentType.objects.get_for_model(BatchExecution),
        object_id=batch.id, field_name="parts",
        old_value=removed.ERP_id if removed else "", new_value=added.ERP_id if added else "",
        reason=(reason or "").strip() or OPEN_LOAD_CORRECTION, edited_by=user)


def add_parts_to_batch(*, batch: "BatchExecution", parts, user: "User", reason: str = "") -> list:
    """Put forgotten pieces into a load that isn't completed yet — loading or running
    (user decision 2026-11-03: until Complete load the operator corrects membership
    freely; no reason needed). The same checks as starting a load: at the load's step,
    on its work order, not held, not in another open load. An added part rides the load:
    its captures cover it (the advancement gate reads them through membership), its
    visit at the step follows the load's holder, and if the load's FAIL containment has
    already fired it is quarantined with the load.

    Returns the parts added. Raises ValidationError naming why not.
    """
    from Tracker.models import BatchExecution, PartsStatus, QuarantineDisposition, StepExecution
    from Tracker.services.mes.parts import TERMINAL_PART_STATUSES

    with transaction.atomic():
        batch = BatchExecution.objects.select_for_update().get(pk=batch.id)
        if batch.completed_at is not None:
            raise ValidationError("This load is complete; its parts are final.")
        current = set(batch.parts.values_list('id', flat=True))
        new = [p for p in parts if p.id not in current]
        if not new:
            raise ValidationError("Those parts are already in this load.")
        problems = []
        for p in new:
            if p.step_id != batch.step_id:
                problems.append(f"{p.ERP_id} isn't at {batch.step.name}.")
            elif p.work_order_id != batch.work_order_id:
                problems.append(f"{p.ERP_id} is on another work order.")
            elif p.part_status in ("QUARANTINED", "ON_HOLD") or p.part_status in TERMINAL_PART_STATUSES:
                problems.append(f"{p.ERP_id} is held or finished and can't go into a load.")
        if problems:
            raise ValidationError(problems)
        if BatchExecution.objects.filter(archived=False, step=batch.step, completed_at__isnull=True,
                                         parts__in=new).exclude(pk=batch.pk).exists():
            raise ValidationError("A selected part is already in another open load at this step.")

        batch.parts.add(*new)
        for p in new:
            _record_membership(batch, user, added=p, reason=reason)

        # Its visit follows the load's holder: the one holding most of the others.
        held = list(StepExecution.objects  # tenant-safe: FK-correlated to a scoped load's parts
                    .filter(step_id=batch.step_id, part_id__in=current, exited_at__isnull=True,
                            archived=False, assigned_to__isnull=False))
        if held:
            from collections import Counter
            top = Counter(v.assigned_to_id for v in held).most_common(1)[0][0]
            model_visit = next(v for v in held if v.assigned_to_id == top)
            for v in (StepExecution.objects  # tenant-safe: FK-correlated to the added scoped parts
                      .filter(step_id=batch.step_id, part__in=new, exited_at__isnull=True,
                              archived=False).exclude(assigned_to_id=top)):
                snap = {k: val for k, val in (model_visit.training_authorization or {}).items()
                        if k != 'previous'}
                snap['carried_with'] = str(model_visit.id)
                if v.training_authorization:
                    snap['previous'] = v.training_authorization
                v.assigned_to_id = top
                v.training_authorization = snap or None
                v.save(update_fields=['assigned_to', 'training_authorization', 'updated_at'])

        # A load already contained by its failed cycle holds the newcomer too.
        if QuarantineDisposition.objects.filter(archived=False, batch_execution=batch,
                                                current_state__in=["OPEN", "IN_PROGRESS"]).exists():
            from Tracker.services.qms.batch_disposition import _QUARANTINABLE
            for p in new:
                if p.part_status in _QUARANTINABLE:
                    p.part_status = PartsStatus.QUARANTINED
                    p.save(update_fields=["part_status"])
    return new


def remove_part_from_batch(*, batch: "BatchExecution", part, user: "User", reason: str = "") -> str:
    """Take a piece out of a load. While the part's own visit at the step is still open
    — its step not yet completed, whatever the load's phase — it simply comes out (no
    reason needed — user decision 2026-11-03); it then has no load at the step and
    waits there until it's in one. Once that visit is completed (the load completed and
    the part moved on), it goes through remove_part_from_sealed_batch: a reason, and
    the part rolled back to the step.

    Returns REMOVED or ROLLBACK_PENDING. Raises ValidationError naming why not.
    """
    from Tracker.models import BatchExecution, StepExecution
    visit_open = StepExecution.objects.filter(  # tenant-safe: FK-correlated to a scoped part
        part=part, step_id=batch.step_id, exited_at__isnull=True, archived=False).exists()
    if not visit_open:
        return remove_part_from_sealed_batch(batch=batch, part=part, user=user, reason=reason)
    with transaction.atomic():
        batch = BatchExecution.objects.select_for_update().get(pk=batch.id)
        if not batch.parts.filter(pk=part.pk).exists():
            raise ValidationError(f"{part.ERP_id} isn't in this load.")
        if batch.parts.count() == 1:
            raise ValidationError("It's the load's only part — a load needs at least one.")
        batch.parts.remove(part)
        _record_membership(batch, user, removed=part, reason=reason)
    return REMOVED


def membership_changes(batch) -> list[dict]:
    """The load's membership changes, oldest first: who added or removed which part,
    when, and why — for the load row and the traveller."""
    from django.contrib.contenttypes.models import ContentType
    from Tracker.models import BatchExecution, RecordEdit
    rows = (RecordEdit.objects  # tenant-safe: keyed to a scoped batch's id
            .filter(content_type=ContentType.objects.get_for_model(BatchExecution),
                    object_id=batch.id, field_name="parts")
            .select_related("edited_by").order_by("edited_at"))
    return [{
        "serial": r.new_value or r.old_value,
        "change": "added" if r.new_value else "removed",
        "by": (r.edited_by.get_full_name() or r.edited_by.get_username()) if r.edited_by else "",
        "at": r.edited_at,
        "reason": "" if r.reason == OPEN_LOAD_CORRECTION else r.reason,
    } for r in rows]


LOAD_DISCARDED = "Load discarded while loading"
RELEASED_WITH_LOAD = "Released with the discarded load"


def discard_batch(*, batch: "BatchExecution", user: "User", reason: str = "",
                  release: bool = False) -> int:
    """Abandon a load started by mistake, while it's still loading (user decision
    2026-11-03 — a one-part load had no way out: its only part has no ×, and with no
    other candidates there's nothing to add). Its parts go back to the step unloaded,
    free for a new load. Its loading captures are voided (any report they made is
    superseded) and its draft dropped; the load itself is archived, not deleted, and
    the discard is recorded with its parts.

    `release` is "I shouldn't have started this at all": the parts' visits at THIS step
    also go back to the queue — unassigned and unstarted, as before Start Work — each
    recorded as an edit of its holder (who, when, "Released with the discarded load").
    Their visits elsewhere are untouched. Returns how many visits were released.

    Raises:
        ValidationError: the load is sealed (the cycle has run: correct it instead), or
            a failed check has already contained it (its disposition decides).
    """
    from Tracker.models import BatchExecution, QuarantineDisposition, SubstepCompletion
    from Tracker.services.qms.report_supersede import void_completion

    with transaction.atomic():
        batch = BatchExecution.objects.select_for_update().get(pk=batch.id)
        if batch.archived:
            return
        if batch.sealed_at is not None:
            raise ValidationError("This load is sealed; the cycle has run. Correct its parts instead.")
        if QuarantineDisposition.objects.filter(archived=False, batch_execution=batch,  # tenant-safe: keyed to a scoped batch
                                                current_state__in=["OPEN", "IN_PROGRESS"]).exists():
            raise ValidationError("A failed check has contained this load; its disposition decides "
                                  "what happens to it.")
        why = (reason or "").strip() or LOAD_DISCARDED
        for c in SubstepCompletion.objects.filter(batch_execution=batch, is_voided=False):  # tenant-safe: keyed to a scoped batch
            void_completion(c, user, why)
        from django.contrib.contenttypes.models import ContentType
        from Tracker.models import RecordEdit
        RecordEdit.objects.create(
            tenant=batch.tenant, content_type=ContentType.objects.get_for_model(BatchExecution),
            object_id=batch.id, field_name="parts",
            old_value=", ".join(batch.parts.order_by('ERP_id').values_list('ERP_id', flat=True)),
            new_value="", reason=why, edited_by=user)
        batch.capture_draft = {}
        batch.save(update_fields=['capture_draft'])
        released = _release_visits(batch, user) if release else 0
        batch.delete()  # SecureModel: archives
    return released


def _release_visits(batch, user) -> int:
    """The load's parts' open visits at its step, back to the queue: unassigned,
    unstarted. The hand-back is a RecordEdit on each visit — not the training snapshot,
    which the advancement gate trusts when set; an unstarted visit has none."""
    from django.contrib.contenttypes.models import ContentType
    from Tracker.models import RecordEdit, StepExecution
    ct = ContentType.objects.get_for_model(StepExecution)
    released = 0
    for v in (StepExecution.objects  # tenant-safe: FK-correlated to a scoped load's parts
              .filter(step_id=batch.step_id, part__in=batch.parts.all(), exited_at__isnull=True,
                      archived=False, status__in=('PENDING', 'CLAIMED', 'IN_PROGRESS'))
              .select_related('assigned_to')):
        holder = v.assigned_to
        v.assigned_to = None
        v.status = 'PENDING'
        v.started_at = None
        v.training_authorization = None
        v.save(update_fields=['assigned_to', 'status', 'started_at', 'training_authorization',
                              'updated_at'])
        RecordEdit.objects.create(
            tenant=batch.tenant, content_type=ct, object_id=v.id, field_name="assigned_to",
            old_value=(holder.get_full_name() or holder.get_username()) if holder else "",
            new_value="", reason=RELEASED_WITH_LOAD, edited_by=user)
        released += 1
    return released


REMOVED = "REMOVED"
ROLLBACK_PENDING = "ROLLBACK_PENDING"


def remove_part_from_sealed_batch(*, batch: "BatchExecution", part, user: "User", reason: str) -> str:
    """The wrong part went into a sealed batch: take it out, with a reason (user decision
    2026-10-22, Corrections #6 — no unseal). Out of the batch, the batch's completions no
    longer count for it, so it holds at the batch's step until its own work there is
    done. A part the batch already advanced one step is rolled back to the step first,
    under the rollback's own rules — which may send it for approval (ROLLBACK_PENDING:
    take it out again once approved); one further on is refused — roll it back first.

    The removal and its reason are kept as an edit of the batch's `parts`. Returns
    REMOVED or ROLLBACK_PENDING.

    Raises:
        ValidationError: naming why it can't.
    """
    from django.contrib.contenttypes.models import ContentType
    from Tracker.models import BatchExecution, RecordEdit, StepExecution

    reason = (reason or "").strip()
    if not reason:
        raise ValidationError("Say why the part is being taken out of the batch.")
    if batch.sealed_at is None:
        raise ValidationError("The batch isn't sealed — change its parts before sealing it.")
    if not batch.parts.filter(pk=part.pk).exists():
        raise ValidationError(f"{part.ERP_id} isn't in this batch.")
    with transaction.atomic():
        part.refresh_from_db()
        if part.step_id != batch.step_id:
            # Moved on with the cohort: back one step to the batch's step, if that's where
            # it came from.
            came_from = (StepExecution.objects  # tenant-safe: FK-correlated to a scoped part
                         .filter(part=part, next_step_id=part.step_id, status="COMPLETED", archived=False)
                         .order_by("-exited_at").values_list("step_id", flat=True).first())
            if came_from != batch.step_id:
                raise ValidationError(
                    f"{part.ERP_id} has moved on past {batch.step.name} — roll it back to that step "
                    "first, then take it out of the batch.")
            from Tracker.services.mes.parts import rollback_part_step
            try:
                result = rollback_part_step(part, user, reason=reason)
            except ValueError as e:
                # Say what it means here, not only the rollback's own words.
                raise ValidationError(
                    f"{part.ERP_id} has already moved on from {batch.step.name} and can't be stepped "
                    f"back to it ({str(e).removeprefix('Cannot rollback: ')}). Ask a lead how to put it right."
                ) from e
            if not result.get("success"):
                # Sent for approval (past the undo window, or the step asks for one): the
                # request stands, and the part comes out once it's approved and rolled back.
                # Returned, not raised — raising would undo the request it just made.
                return ROLLBACK_PENDING
        batch.parts.remove(part)
        RecordEdit.objects.create(
            tenant=batch.tenant, content_type=ContentType.objects.get_for_model(BatchExecution),
            object_id=batch.id, field_name="parts", old_value=part.ERP_id, new_value="",
            reason=reason, edited_by=user)
    return REMOVED
