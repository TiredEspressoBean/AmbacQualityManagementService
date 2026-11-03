"""In-flight work — the step visits and loads someone has open, to pick one up again.

What the "Resume" picker on Operator Home and "Continue work" on a work order list:

  - **part visits**: a StepExecution someone holds (`assigned_to`) that hasn't left the
    step — waiting (PENDING / CLAIMED) or started (IN_PROGRESS). An unassigned waiting
    part is the queue, not anyone's work in flight, so it isn't listed.
  - **loads**: a BatchExecution not yet completed, held by whoever started it —
    loading (OPEN) or sealed and running (RUNNING): a running load still has its
    completion-phase substeps and its Complete to come.

Progress counts a substep as done when it is confirmed (a live completion) or has a
draft — "where the work has got to", not a quality figure. A part visit counts its
per-part substeps; a load its batch substeps.

`everyone=False` is the operator's own work. Seeing everyone's is the supervisor view;
the caller decides who may ask for it.

**Holder off the clock.** Work whose holder has no open attendance entry (SHIFT, or a
BREAK / LUNCH pause) is marked `holder_off_clock`: they clocked out, or never clocked
in, and left it open. It stays theirs, drafts and all; the mark is for a supervisor
deciding whether to take it over. It is read live from the clock rather than stamped
at clock-out, so a break never trips it and clocking back in clears it.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone
from uuid import UUID

from django.db.models import Q

OPEN_STATUSES = ('PENDING', 'CLAIMED', 'IN_PROGRESS')


@dataclass(frozen=True)
class InFlightItem:
    kind: str  # 'part' | 'load'
    id: UUID  # the StepExecution, or the BatchExecution
    step_id: UUID
    step_name: str
    part_id: UUID | None
    part_erp_id: str | None
    part_count: int  # 1 for a part visit; the load's size for a load
    work_order_id: UUID | None
    work_order_erp_id: str | None
    status: str  # an execution status; a load's is 'OPEN' (loading) or 'RUNNING' (sealed)
    sealed_at: datetime | None  # a load's seal; None for a part visit
    holder_id: int | None
    holder_name: str
    started_at: datetime | None
    entered_at: datetime | None
    substeps_total: int
    substeps_done: int
    holder_off_clock: bool
    # Where "continue" opens the runtime: a load is worked from one of its parts.
    resume_execution_id: UUID | None
    resume_part_id: UUID | None


def _name(user) -> str:
    return (user.get_full_name() or user.get_username()) if user else ''


def in_flight(tenant, *, user, everyone=False, work_order_id=None,
              off_clock=False) -> list[InFlightItem]:
    """Open part visits and loads, newest activity first."""
    from Tracker.models import BatchExecution, StepExecution, Substep, SubstepCompletion

    execs = (StepExecution.objects
             .filter(tenant=tenant, archived=False, status__in=OPEN_STATUSES,
                     exited_at__isnull=True, assigned_to__isnull=False)
             .select_related('step', 'part', 'part__work_order', 'assigned_to'))
    loads = (BatchExecution.objects
             .filter(tenant=tenant, archived=False, completed_at__isnull=True)
             .select_related('step', 'work_order', 'started_by'))
    if not everyone:
        execs = execs.filter(assigned_to=user)
        loads = loads.filter(started_by=user)
    if work_order_id:
        execs = execs.filter(part__work_order_id=work_order_id)
        loads = loads.filter(work_order_id=work_order_id)
    execs, loads = list(execs), list(loads)

    from Tracker.models import TimeEntry
    from Tracker.services.mes.labor_report import ATTENDANCE_TYPES
    holders = {e.assigned_to_id for e in execs} | {b.started_by_id for b in loads}
    on_clock = set(TimeEntry.objects
                   .filter(tenant=tenant, archived=False, user_id__in=holders,
                           end_time__isnull=True, entry_type__in=ATTENDANCE_TYPES)
                   .values_list('user_id', flat=True))
    if off_clock:
        execs = [e for e in execs if e.assigned_to_id not in on_clock]
        loads = [b for b in loads if b.started_by_id not in on_clock]

    step_ids = {e.step_id for e in execs} | {b.step_id for b in loads}
    per_part, per_load = defaultdict(set), defaultdict(set)
    for sid, scope, sub_id in (Substep.objects
                               .filter(tenant=tenant, archived=False, step_id__in=step_ids)
                               .values_list('step_id', 'scope', 'id')):
        (per_load if scope == 'batch' else per_part)[sid].add(sub_id)

    done_by_exec, done_by_load = defaultdict(set), defaultdict(set)
    for ex_id, b_id, sub_id in (SubstepCompletion.objects
                                .filter(tenant=tenant, is_voided=False)
                                .filter(Q(step_execution_id__in=[e.id for e in execs])
                                        | Q(batch_execution_id__in=[b.id for b in loads]))
                                .values_list('step_execution_id', 'batch_execution_id', 'substep_id')):
        if ex_id:
            done_by_exec[ex_id].add(sub_id)
        if b_id:
            done_by_load[b_id].add(sub_id)

    def progress(subs, done, draft):
        drafted = {UUID(k) for k in (draft or {}) if _is_uuid(k)}
        return len(subs), len(subs & (done | drafted))

    out: list[InFlightItem] = []
    for e in execs:
        total, done = progress(per_part[e.step_id], done_by_exec[e.id], e.capture_draft)
        wo = e.part.work_order if e.part_id else None
        out.append(InFlightItem(
            kind='part', id=e.id, step_id=e.step_id, step_name=e.step.name,
            part_id=e.part_id, part_erp_id=e.part.ERP_id if e.part_id else None, part_count=1,
            work_order_id=wo.id if wo else None, work_order_erp_id=wo.ERP_id if wo else None,
            status=e.status, sealed_at=None,
            holder_id=e.assigned_to_id, holder_name=_name(e.assigned_to),
            started_at=e.started_at, entered_at=e.entered_at,
            substeps_total=total, substeps_done=done,
            holder_off_clock=e.assigned_to_id not in on_clock,
            resume_execution_id=e.id, resume_part_id=e.part_id,
        ))

    # A load opens on one of its parts' visits at the step, where the batch panel is.
    members = defaultdict(list)
    for b_id, part_id in (BatchExecution.parts.through.objects  # tenant-safe: keyed to scoped loads
                          .filter(batchexecution_id__in=[b.id for b in loads])
                          .values_list('batchexecution_id', 'parts_id')):
        members[b_id].append(part_id)
    open_visit = {
        (part_id, step_id): ex_id
        for ex_id, part_id, step_id in (StepExecution.objects
                                        .filter(tenant=tenant, archived=False,
                                                exited_at__isnull=True,
                                                part_id__in={p for ps in members.values() for p in ps})
                                        .values_list('id', 'part_id', 'step_id'))
    }
    for b in loads:
        total, done = progress(per_load[b.step_id], done_by_load[b.id], b.capture_draft)
        resume = next(((p, open_visit[(p, b.step_id)]) for p in members[b.id]
                       if (p, b.step_id) in open_visit), (None, None))
        out.append(InFlightItem(
            kind='load', id=b.id, step_id=b.step_id, step_name=b.step.name,
            part_id=None, part_erp_id=None, part_count=len(members[b.id]),
            work_order_id=b.work_order_id, work_order_erp_id=b.work_order.ERP_id,
            status='RUNNING' if b.sealed_at else 'OPEN', sealed_at=b.sealed_at,
            holder_id=b.started_by_id, holder_name=_name(b.started_by),
            started_at=b.started_at, entered_at=b.started_at,
            substeps_total=total, substeps_done=done,
            holder_off_clock=b.started_by_id not in on_clock,
            resume_execution_id=resume[1], resume_part_id=resume[0],
        ))

    # Most recently started (or, never started, arrived) first.
    out.sort(key=lambda i: (i.started_at or i.entered_at or _EPOCH), reverse=True)
    return out


_EPOCH = datetime(1970, 1, 1, tzinfo=dt_timezone.utc)


def _is_uuid(s) -> bool:
    try:
        UUID(str(s))
        return True
    except ValueError:
        return False


@dataclass(frozen=True)
class HandOffCandidate:
    user_id: int
    name: str
    trained: bool  # qualified for the step, as the training gate reads it
    at_station: bool  # rostered at the step's work center


def hand_off_candidates(execution) -> list[HandOffCandidate]:
    """Who a supervisor can hand a step to: the tenant's own active staff who record
    substeps (not customer-portal accounts, not read-only roles), minus its holder.
    Trained for the step first, then rostered at its station, then the rest — a
    hand-off to someone untrained needs the training override (lifecycle.reassign)."""
    from Tracker.models import User, UserWorkCenterMembership
    from Tracker.services.training import check_training_authorization

    tenant = execution.tenant
    step = execution.step
    process = getattr(execution.subject_work_order, 'process', None)
    station = set()
    if getattr(step, 'work_center_id', None):
        station = set(UserWorkCenterMembership.objects
                      .filter(tenant=tenant, work_center_id=step.work_center_id, archived=False)
                      .values_list('user_id', flat=True))
    out = []
    for u in (User.objects.filter(tenant=tenant, is_active=True, user_type=User.UserType.INTERNAL)
              .exclude(pk=execution.assigned_to_id).order_by('first_name', 'last_name', 'username')):
        if not u.has_tenant_perm('add_substepcompletion', tenant) or u.is_customer(tenant):
            continue
        out.append(HandOffCandidate(
            user_id=u.id, name=_name(u),
            trained=check_training_authorization(u, step, process=process).authorized,
            at_station=u.id in station,
        ))
    out.sort(key=lambda c: (not c.trained, not c.at_station))
    return out
