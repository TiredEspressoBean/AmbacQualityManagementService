"""What a first piece is FOR: the context an FPI record covers, by the step's scope.

User decision 2026-10-28 (B1): the scope is a real gate.

- **Per Work Order** — one buy-off releases the step for the whole work order.
- **Per Shift** — each run of a shift (Day on the 12th, Night on the 12th) needs its
  own passed or waived first piece at the step on that work order. Which shift it is
  comes from the shift calendar (`scheduling.calendars.shift_at`: the shift that started
  most recently); a night shift past midnight keeps its start date. A shift edited into
  a new version is the same shift. With no shifts configured, the plant date stands in.
- **Per Equipment** — each machine the work runs on needs its own. The machine is the
  PRODUCTION equipment on the part's visit to the step (stamped from the step's
  authored machine or the live schedule, or set by the operator). A part whose machine
  isn't recorded is held: there is nothing to say which first piece covers it.

Per Operator was removed (it never keyed a record).

Which records decide (B2): a superseded waiver and a voided pass release nothing; any
other PASSED or WAIVED record in the context does. Starting a new first piece after a
waiver supersedes the waiver, so the newest record decides.
"""
from __future__ import annotations

from dataclasses import dataclass

PER_WORKORDER = 'PER_WORKORDER'
PER_SHIFT = 'PER_SHIFT'
PER_EQUIPMENT = 'PER_EQUIPMENT'


@dataclass(frozen=True)
class FpiContext:
    """The slice of FPI records that covers one part (or the step, for Per Work Order).

    `known` is False for a Per Equipment step when the machine isn't recorded.
    `shift_ids` is every version of the shift, so an edit to the shift mid-run doesn't
    lose its first piece; empty when no shift calendar applies (keyed by date alone)."""
    scope: str
    shift_date: object = None
    shift_id: object = None
    shift_ids: tuple = ()
    shift_name: str = ''
    equipment_id: object = None
    equipment_name: str = ''
    known: bool = True

    def filters(self) -> dict:
        if self.scope == PER_SHIFT:
            if self.shift_ids:
                return {'shift_date': self.shift_date, 'shift_id__in': self.shift_ids}
            return {'shift_date': self.shift_date, 'shift__isnull': True}
        if self.scope == PER_EQUIPMENT:
            return {'equipment_id': self.equipment_id}
        return {}

    @property
    def label(self) -> str:
        """Who the first piece is for, as the banner and cards say it ("" for a WO)."""
        if self.scope == PER_SHIFT and self.shift_date:
            if self.shift_name:
                return f"{self.shift_name} on {self.shift_date:%d %b}"
            return f"the {self.shift_date:%d %b} shift"
        if self.scope == PER_EQUIPMENT:
            return self.equipment_name or ("an unrecorded machine" if not self.known else "")
        return ""


def machine_of(part, step):
    """The PRODUCTION machine on `part`'s current visit to `step`, or None."""
    if part is None:
        return None
    from Tracker.models import StepExecution
    from Tracker.models.qms import EquipmentRole, StepExecutionEquipment
    se = StepExecution.get_current_execution(part)
    if se is None or str(se.step_id) != str(step.id):
        return None
    link = (StepExecutionEquipment.objects
            .filter(step_execution=se, role=EquipmentRole.PRODUCTION)
            .select_related('equipment').first())
    return link.equipment if link else None


def _shift_context(shift, shift_date) -> FpiContext:
    if shift is None:
        return FpiContext(scope=PER_SHIFT, shift_date=shift_date)
    return FpiContext(scope=PER_SHIFT, shift_date=shift_date, shift_id=shift.id,
                      shift_ids=tuple(v.id for v in shift.get_version_history()),
                      shift_name=shift.name)


def context_for(step, work_order, *, part=None, equipment=None, shift=None,
                shift_date=None) -> FpiContext:
    """The context `part` (or the given machine / shift) needs a first piece for. With
    no shift given, a Per Shift step takes the shift running now."""
    scope = step.fpi_scope or PER_WORKORDER
    if scope == PER_SHIFT:
        if shift is None and shift_date is None:
            from Tracker.services.scheduling.calendars import shift_at
            running = shift_at(work_order.tenant)
            if running is not None:
                shift, shift_date = running
            else:
                from Tracker.services.core.clock import tenant_today
                shift_date = tenant_today(work_order.tenant)
        elif shift_date is None:
            from Tracker.services.core.clock import tenant_today
            shift_date = tenant_today(work_order.tenant)
        return _shift_context(shift, shift_date)
    if scope == PER_EQUIPMENT:
        machine = equipment if equipment is not None else machine_of(part, step)
        if machine is None:
            return FpiContext(scope=scope, known=False)
        return FpiContext(scope=scope, equipment_id=machine.id, equipment_name=machine.name)
    return FpiContext(scope=PER_WORKORDER)


def context_of_record(fpi) -> FpiContext:
    """The context an existing record covers."""
    scope = fpi.step.fpi_scope or PER_WORKORDER
    if scope == PER_SHIFT:
        return _shift_context(fpi.shift, fpi.shift_date)
    if scope == PER_EQUIPMENT:
        return FpiContext(scope=scope, equipment_id=fpi.equipment_id,
                          equipment_name=fpi.equipment.name if fpi.equipment else '',
                          known=fpi.equipment_id is not None)
    return FpiContext(scope=PER_WORKORDER)


def records_for(step, work_order, ctx: FpiContext):
    """The FPI records in `ctx`, newest first. Empty for an unknown machine."""
    from Tracker.models import FPIRecord
    qs = FPIRecord.objects.filter(work_order=work_order, step=step, archived=False)
    if not ctx.known:
        return qs.none()
    return qs.filter(**ctx.filters()).order_by('-created_at')


def qa_released(step, work_order, part=None) -> bool:
    """Whether `part` has the step's QA release on `work_order`. A direct step sign-off
    releases the work order; a first-piece pass releases its own context only, so on a
    Per Shift / Per Equipment step one context's void doesn't take another's release
    (round-1 #7). With no part, any live release counts."""
    from Tracker.models import QaApproval
    qs = QaApproval.objects.filter(step=step, work_order=work_order, archived=False)  # tenant-safe: scoped FKs
    if part is None or not step.requires_first_piece_inspection:
        return qs.exists()
    if qs.filter(fpi_record__isnull=True).exists():
        return True
    ctx = context_for(step, work_order, part=part)
    return qs.filter(fpi_record__in=records_for(step, work_order, ctx)).exists()


def status_in(step, work_order, ctx: FpiContext) -> dict:
    """The FPI state of one context, in the shape `Steps.get_fpi_status` returns."""
    from Tracker.models import FPIStatus, Parts
    base = {'context_label': ctx.label}
    records = records_for(step, work_order, ctx)
    released = records.filter(status__in=[FPIStatus.PASSED, FPIStatus.WAIVED]).first()
    if released is not None:
        return {**base, 'status': released.status, 'fpi_record_id': str(released.id),
                'designated_part_id': str(released.designated_part_id) if released.designated_part_id else None,
                'blocked_parts_count': 0}
    blocked = Parts.objects.filter(work_order=work_order, step=step).count()
    latest = records.filter(status__in=[FPIStatus.PENDING, FPIStatus.FAILED]).first()
    status = latest.status if latest is not None else FPIStatus.PENDING
    return {**base, 'status': status, 'fpi_record_id': str(latest.id) if latest else None,
            'designated_part_id': str(latest.designated_part_id) if latest and latest.designated_part_id else None,
            'blocked_parts_count': blocked}


def step_status(step, work_order, part=None) -> dict:
    """The FPI gate for `part` at `step` — or, with no part, for the work order's parts
    at the step taken together (held if any one of them is)."""
    if part is not None or (step.fpi_scope or PER_WORKORDER) != PER_EQUIPMENT:
        return status_in(step, work_order, context_for(step, work_order, part=part))
    from Tracker.models import Parts
    first = None
    for p in Parts.objects.filter(work_order=work_order, step=step, archived=False):
        s = status_in(step, work_order, context_for(step, work_order, part=p))
        if s['status'] not in ('PASSED', 'WAIVED'):
            return s
        first = first or s
    return first or status_in(step, work_order, context_for(step, work_order))
