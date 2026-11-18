"""Is a part held by a nonconformance? One question, one answer (user ruling
2026-11-17: "simplify these aspects because exception trees are probably the problem").

The disposition is the single source of truth. A part is held while it has an
UNDECIDED nonconformance; a decided disposition — use as is, not a nonconformance,
rework / repair (routed), scrap, return — resolves everything that raised it: the
quarantine, the out-of-spec reading, the failed sample. The release gates (quarantine
hold, readings in spec, sampling) each ask this, rather than re-deriving it from the
readings or the report.

A failure nothing has dispositioned yet (a reading or sample that failed `since` a
moment with no disposition raised after it) holds the part too — the safety net, not a
bypass: a FAIL report raises its disposition (disposition.open_disposition_for_failed_
report), and until one exists the part waits for it.
"""
from __future__ import annotations


def undecided_disposition(part):
    """The part's open nonconformance — a disposition not closed and not yet decided —
    or None."""
    from django.db.models import Q
    from Tracker.models import QuarantineDisposition
    # held=False: a decision for the record (a part already past the step or shipped
    # when the NCR was raised) holds nothing.
    return (QuarantineDisposition.objects  # tenant-safe: FK-correlated to a scoped part
            .filter(part=part, archived=False, held=True)
            .exclude(current_state='CLOSED')
            .filter(Q(disposition_type__isnull=True) | Q(disposition_type=''))
            .order_by('-created_at').first())


def nonconformance_hold(part, since=None, *, then: str = "it moves on once that's decided.") -> str | None:
    """Why `part` is held by a nonconformance, or None when nothing holds it.

    `since`: a failure at that moment (an out-of-spec reading at the visit, a failed
    sample) holds the part until a disposition is raised for it and decided — one
    raised before `since` doesn't cover it."""
    from Tracker.models import PartsStatus, QuarantineDisposition
    if part is None:
        return None
    open_one = undecided_disposition(part)
    if open_one is not None:
        return (f"{part.ERP_id} is quarantined — {open_one.disposition_number} decides what "
                f"happens to it; {then}")
    # A decision takes the part off QUARANTINED, so quarantined with nothing undecided
    # is a quarantine no disposition has been raised for yet.
    if part.part_status == PartsStatus.QUARANTINED:
        return f"{part.ERP_id} is quarantined — it needs a disposition before it moves on."
    if since is not None and not QuarantineDisposition.objects.filter(  # tenant-safe: FK-correlated to a scoped part
            part=part, archived=False, created_at__gte=since).exists():
        return f"{part.ERP_id} failed here — it needs a disposition before it moves on."
    return None


# --- Where a decided nonconformance sends the part ---------------------------------
# The disposition decides WHETHER the part moves (above); this decides WHERE (user
# ruling 2026-11-17, "follow the step's Fail branch"). One function for every caller:
# the decision-time rework routing, MRB, and a QA-result decision step.

PASS_DECISIONS = ('USE_AS_IS', 'NOT_NONCONFORMANCE')
FAIL_DECISIONS = ('REWORK', 'REPAIR')


def decided_outcome(part, step, since=None) -> str | None:
    """'PASS' or 'FAIL' from the part's latest decided disposition at `step` (raised at
    or after `since`, when given) — use as is / not a nonconformance pass, rework /
    repair fail — or None when nothing decided covers it."""
    from Tracker.models import QuarantineDisposition
    decided = (QuarantineDisposition.objects  # tenant-safe: FK-correlated to a scoped part
               .filter(part=part, archived=False,
                       disposition_type__in=PASS_DECISIONS + FAIL_DECISIONS)
               .order_by('-created_at'))
    if since is not None:
        decided = decided.filter(created_at__gte=since)
    if step is not None:
        decided = decided.filter(models_q_step(step))
    d = decided.first()
    if d is None:
        return None
    return 'PASS' if d.disposition_type in PASS_DECISIONS else 'FAIL'


def models_q_step(step):
    """Dispositions at `step` — or with no step recorded (older ones), which count."""
    from django.db.models import Q
    return Q(step=step) | Q(step__isnull=True)


def fail_destination(part, process):
    """Where a rework / repair decision sends the part: its current step's Fail branch
    when the step has exactly one, else the process's one Rework step, else None (routed
    by hand from the control page).

    A Fail branch into a holding step (MRB Review) isn't a rework destination: that is
    where an UNDECIDED part waits, and a decided one there would never move on. The
    decision goes to the Rework step instead."""
    from Tracker.models import EdgeType, ProcessStep, StepEdge
    from Tracker.services.qms.mrb import is_hold_step
    if process is None:
        return None
    fail_edges = list(StepEdge.objects.filter(  # tenant-safe: scoped by process
        process=process, from_step_id=part.step_id, edge_type=EdgeType.ALTERNATE)
        .select_related('to_step')[:2])
    if len(fail_edges) == 1 and not is_hold_step(process, fail_edges[0].to_step):
        return fail_edges[0].to_step
    rework = [ps.step for ps in ProcessStep.objects.filter(  # tenant-safe: scoped by process
        process=process, step__step_type='REWORK').select_related('step')]
    return rework[0] if len(rework) == 1 else None
