"""Reactive re-plan: disruptive domain events flip the active
`ScheduleResult.is_stale` (Tracker/signals.py). The flag is an advisory
"schedule out of date" hint for the planner — not an auto-solve.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from Tracker.models import (
    BatchExecution,
    DowntimeEvent,
    Equipments,
    Fixture,
    MaterialLot,
    Parts,
    PartsStatus,
    PartTypes,
    PlantCalendarException,
    Processes,
    QualityReports,
    ScheduleResult,
    Shift,
    StepEquipmentAffinity,
    StepTiming,
    Steps,
    Tenant,
    WorkCenterChangeover,
    WorkOrder,
    WorkOrderStatus,
)
from Tracker.tests.base import TenantContextMixin


class ScheduleStaleSignalTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Sch", slug="sched-stale", tier="PRO")
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        self.user = User.objects.create_user(
            username="planner", email="p@c.test", password="x", tenant=self.tenant)
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Nz")
        self.process = Processes.objects.create(tenant=self.tenant, name="P", part_type=self.pt)
        self.step = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name="Op1")

    def _active_schedule(self):
        now = timezone.now()
        return ScheduleResult.objects.create(
            tenant=self.tenant, horizon_start=now, horizon_end=now + timedelta(days=1),
            is_active=True, is_stale=False,
        )

    def _wo(self, erp="WO-1", status=WorkOrderStatus.IN_PROGRESS):
        return WorkOrder.objects.create(
            tenant=self.tenant, ERP_id=erp, workorder_status=status,
            quantity=1, process=self.process)

    def _is_stale(self, sched):
        sched.refresh_from_db()
        return sched.is_stale

    def test_new_workorder_marks_stale(self):
        sched = self._active_schedule()
        self._wo("WO-NEW")
        self.assertTrue(self._is_stale(sched))

    def test_workorder_priority_change_marks_stale(self):
        wo = self._wo("WO-PRI")
        sched = self._active_schedule()  # created after WO so it starts fresh
        wo.priority = 1
        wo.save(update_fields=['priority'])
        self.assertTrue(self._is_stale(sched))

    def test_part_scrap_marks_stale(self):
        wo = self._wo("WO-SCR")
        part = Parts.objects.create(
            tenant=self.tenant, ERP_id="P-1", part_type=self.pt,
            work_order=wo, step=self.step)
        sched = self._active_schedule()
        part.part_status = PartsStatus.SCRAPPED
        part.save(update_fields=['part_status'])
        self.assertTrue(self._is_stale(sched))

    def test_part_split_marks_stale(self):
        wo = self._wo("WO-SPL")
        part = Parts.objects.create(
            tenant=self.tenant, ERP_id="P-2", part_type=self.pt,
            work_order=wo, step=self.step)
        sched = self._active_schedule()
        part.split_from_lot = True
        part.save(update_fields=['split_from_lot'])
        self.assertTrue(self._is_stale(sched))

    def test_routine_advance_status_does_not_mark_stale(self):
        wo = self._wo("WO-ADV")
        part = Parts.objects.create(
            tenant=self.tenant, ERP_id="P-3", part_type=self.pt,
            work_order=wo, step=self.step)
        sched = self._active_schedule()
        part.part_status = PartsStatus.IN_PROGRESS
        part.save(update_fields=['part_status'])
        self.assertFalse(self._is_stale(sched))

    def test_downtime_event_marks_stale(self):
        sched = self._active_schedule()
        eq = Equipments.objects.create(tenant=self.tenant, name="CNC-1")
        DowntimeEvent.objects.create(
            tenant=self.tenant, equipment=eq, category='UNPLANNED',
            reason='Spindle fault', start_time=timezone.now(),
            reported_by=self.user)
        self.assertTrue(self._is_stale(sched))

    def test_draft_schedule_not_marked_stale(self):
        now = timezone.now()
        draft = ScheduleResult.objects.create(
            tenant=self.tenant, horizon_start=now, horizon_end=now + timedelta(days=1),
            is_active=False, is_draft=True, is_stale=False)
        self._wo("WO-DRAFT")
        draft.refresh_from_db()
        self.assertFalse(draft.is_stale)

    # -- QMS bulk-quarantine paths --------------------------------------------
    # Quality holds quarantine parts via bulk `.update()` / `bulk_update`, which
    # bypass the Parts post_save above. The service paths flag the schedule
    # explicitly (Tracker/services/qms/{quality_gate,batch_disposition}); these
    # guard that they do, and document why it's needed.

    def test_bulk_quarantine_update_alone_bypasses_signal(self):
        """A raw bulk `.update()` to QUARANTINED does NOT fire the Parts
        post_save, so the schedule is not flagged — the gap the service paths
        close. (Regression guard: if this ever starts passing on its own, the
        explicit flagging in the QMS services is redundant.)"""
        wo = self._wo("WO-BULK")
        Parts.objects.create(
            tenant=self.tenant, ERP_id="P-BULK", part_type=self.pt,
            work_order=wo, step=self.step, part_status=PartsStatus.IN_PROGRESS)
        sched = self._active_schedule()
        Parts.objects.filter(work_order=wo).update(part_status=PartsStatus.QUARANTINED)
        self.assertFalse(self._is_stale(sched))

    def test_quality_gate_hold_marks_stale(self):
        """`quality_gate._hold` quarantines in-process parts via bulk `.update()`
        and must flag the active schedule so they leave the board."""
        from types import SimpleNamespace
        from Tracker.services.qms.quality_gate import _hold
        wo = self._wo("WO-HOLD")
        Parts.objects.create(
            tenant=self.tenant, ERP_id="P-HOLD", part_type=self.pt,
            work_order=wo, step=self.step, part_status=PartsStatus.IN_PROGRESS)
        sched = self._active_schedule()
        _hold(SimpleNamespace(step=self.step), work_order=wo, material_lot=None)
        self.assertTrue(self._is_stale(sched))

    def test_batch_containment_marks_stale(self):
        """A failed batch cycle contains its members via `bulk_update`
        (`batch_disposition.contain_failed_batch`, fired by the FAIL-QR signal)
        and must flag the active schedule."""
        wo = self._wo("WO-BATCH")
        parts = [
            Parts.objects.create(
                tenant=self.tenant, ERP_id=f"P-BAT-{i}", part_type=self.pt,
                work_order=wo, step=self.step, part_status=PartsStatus.IN_PROGRESS)
            for i in range(2)
        ]
        batch = BatchExecution.objects.create(
            tenant=self.tenant, work_order=wo, step=self.step, started_by=self.user)
        batch.parts.set(parts)
        sched = self._active_schedule()
        QualityReports.objects.create(
            tenant=self.tenant, batch_execution=batch, step=self.step,
            status='FAIL', description='cycle fail', detected_by=self.user)
        self.assertTrue(self._is_stale(sched))

    # -- Capacity / timing master-data triggers -------------------------------
    # Edits to the solver's inputs (calendars, timings, eligibility, changeover,
    # tooling, material receipts) invalidate the live plan.

    def _material_lot(self, lot_number="LOT-1"):
        from decimal import Decimal
        return MaterialLot.objects.create(
            tenant=self.tenant, lot_number=lot_number,
            received_date=timezone.now().date(), received_by=self.user,
            quantity=Decimal("10"), quantity_remaining=Decimal("10"),
            unit_of_measure="EA")

    def test_plant_calendar_exception_marks_stale(self):
        sched = self._active_schedule()
        now = timezone.now()
        PlantCalendarException.objects.create(
            tenant=self.tenant, name="Christmas",
            start_time=now, end_time=now + timedelta(days=1))
        self.assertTrue(self._is_stale(sched))

    def test_step_timing_marks_stale(self):
        sched = self._active_schedule()
        StepTiming.objects.create(
            tenant=self.tenant, step=self.step, cycle_time_minutes=5)
        self.assertTrue(self._is_stale(sched))

    def test_fixture_marks_stale(self):
        sched = self._active_schedule()
        Fixture.objects.create(tenant=self.tenant, name="Vise", quantity=2)
        self.assertTrue(self._is_stale(sched))

    def test_affinity_marks_stale(self):
        eq = Equipments.objects.create(tenant=self.tenant, name="CNC-A")
        sched = self._active_schedule()
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=self.step, equipment=eq)
        self.assertTrue(self._is_stale(sched))

    def test_changeover_marks_stale(self):
        eq = Equipments.objects.create(tenant=self.tenant, name="CNC-B")
        step2 = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Op2")
        sched = self._active_schedule()
        WorkCenterChangeover.objects.create(
            tenant=self.tenant, equipment=eq, from_step=self.step, to_step=step2,
            changeover_minutes=15)
        self.assertTrue(self._is_stale(sched))

    def test_shift_marks_stale(self):
        from datetime import time
        sched = self._active_schedule()
        Shift.objects.create(
            tenant=self.tenant, name="Day", code="DAY",
            start_time=time(6, 0), end_time=time(14, 0))
        self.assertTrue(self._is_stale(sched))

    def test_equipment_operating_shifts_change_marks_stale(self):
        from datetime import time
        eq = Equipments.objects.create(tenant=self.tenant, name="CNC-C")
        shift = Shift.objects.create(
            tenant=self.tenant, name="Night", code="NGT",
            start_time=time(22, 0), end_time=time(6, 0))
        sched = self._active_schedule()
        eq.operating_shifts.add(shift)
        self.assertTrue(self._is_stale(sched))

    def test_equipment_capacity_change_marks_stale(self):
        eq = Equipments.objects.create(tenant=self.tenant, name="CNC-D")
        sched = self._active_schedule()
        eq.is_schedulable = True
        eq.save(update_fields=['is_schedulable'])
        self.assertTrue(self._is_stale(sched))

    def test_material_lot_receipt_marks_stale(self):
        sched = self._active_schedule()
        self._material_lot()
        self.assertTrue(self._is_stale(sched))

    def test_material_lot_status_change_marks_stale(self):
        lot = self._material_lot()
        sched = self._active_schedule()
        lot.status = 'ACCEPTED'
        lot.save(update_fields=['status'])
        self.assertTrue(self._is_stale(sched))

    def test_material_lot_consumption_does_not_mark_stale(self):
        """A partial consumption (quantity_remaining only) must NOT flag — else
        the flag churns on routine execution."""
        from decimal import Decimal
        lot = self._material_lot()
        sched = self._active_schedule()
        lot.quantity_remaining = lot.quantity_remaining - Decimal("1")
        lot.save(update_fields=['quantity_remaining'])
        self.assertFalse(self._is_stale(sched))
