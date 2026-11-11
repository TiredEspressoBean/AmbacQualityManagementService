"""Per Shift keys on the shift calendar, not the date (2026-11-11).

Which shift a moment belongs to: the shift (or overtime run of one) that started most
recently. A handover belongs to the incoming shift; time outside every shift belongs to
the one that just ended; a night shift past midnight keeps its start date. A shift
edited into a new version is the same shift. With no shifts configured, Per Shift keys
on the plant date as before (test_fpi_scope_1028 covers that).
"""
from datetime import date, datetime, time
from unittest.mock import patch

from Tracker.models import (
    FPIRecord, FPIStatus, OvertimeWindow, PartTypes, Parts, Shift, StepExecution, Steps,
    WorkOrder,
)
from Tracker.services.core.clock import plant_tz
from Tracker.services.qms.fpi import start_fpi
from Tracker.services.scheduling.calendars import shift_at
from Tracker.tests.base import TenantTestCase

WED = date(2026, 11, 11)
EVERY_DAY = "0,1,2,3,4,5,6"


class ShiftAtTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        self.tz = plant_tz(self.tenant_a)

    def _shift(self, code, start, end, days=EVERY_DAY):
        return Shift.objects.create(tenant=self.tenant_a, name=code.title(), code=code,
                                    start_time=start, end_time=end, days_of_week=days)

    def _at(self, day, hh, mm=0):
        return datetime.combine(day, time(hh, mm)).replace(tzinfo=self.tz)

    def test_three_shifts_handover_and_overnight(self):
        day = self._shift("DAY", time(6), time(14, 30))
        swing = self._shift("SWING", time(14), time(22, 30))
        night = self._shift("NIGHT", time(22), time(6, 30))
        self.assertEqual(shift_at(self.tenant_a, self._at(WED, 10)), (day, WED))
        # 14:15 both run; Swing started most recently, so it's Swing's.
        self.assertEqual(shift_at(self.tenant_a, self._at(WED, 14, 15)), (swing, WED))
        # 02:00 Thursday is still Wednesday's night shift.
        self.assertEqual(shift_at(self.tenant_a, self._at(date(2026, 11, 12), 2)), (night, WED))

    def test_out_of_shift_belongs_to_the_shift_that_ended(self):
        day = self._shift("DAY", time(6), time(14, 30))
        self.assertEqual(shift_at(self.tenant_a, self._at(WED, 17)), (day, WED))
        self.assertEqual(shift_at(self.tenant_a, self._at(WED, 5)), (day, date(2026, 11, 10)))

    def test_overtime_run_counts_as_its_shift(self):
        day = self._shift("DAY", time(6), time(14, 30), days="0,1,2,3,4")
        sat = date(2026, 11, 14)
        self.assertEqual(shift_at(self.tenant_a, self._at(sat, 10)), (day, date(2026, 11, 13)))
        OvertimeWindow.objects.create(tenant=self.tenant_a, shift=day, recurrence='ONCE',
                                      start_date=sat, end_date=sat)
        self.assertEqual(shift_at(self.tenant_a, self._at(sat, 10)), (day, sat))

    def test_no_shifts_configured(self):
        self.assertIsNone(shift_at(self.tenant_a, self._at(WED, 10)))


class PerShiftGateTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        t = self.tenant_a
        self.pt = PartTypes.objects.create(tenant=t, name="Body", ID_prefix="B")
        self.step = Steps.objects.create(tenant=t, part_type=self.pt, name="Turn", step_type="TASK")
        from Tracker.services.mes.step_gates import set_gates_from_flags
        set_gates_from_flags(self.step, requires_first_piece_inspection=True, fpi_scope='PER_SHIFT')
        self.wo = WorkOrder.objects.create(tenant=t, ERP_id="WO-SHIFT", quantity=2)
        self.part = Parts.objects.create(tenant=t, ERP_id="B-1", part_type=self.pt,
                                         work_order=self.wo, step=self.step)
        StepExecution.objects.create(tenant=t, part=self.part, step=self.step,
                                     visit_number=1, status="IN_PROGRESS")
        self.day = Shift.objects.create(tenant=t, name="Day", code="DAY",
                                        start_time=time(6), end_time=time(14, 30))
        self.night = Shift.objects.create(tenant=t, name="Night", code="NIGHT",
                                          start_time=time(22), end_time=time(6, 30))
        self.grant_tenant_permissions(self.user_a, t, ['sign_off_fpi', 'view_fpirecord',
                                                        'add_fpirecord', 'full_tenant_access'])

    def _on(self, shift):
        return patch('Tracker.services.scheduling.calendars.shift_at', return_value=(shift, WED))

    def _record(self, status, shift, shift_date=WED):
        return FPIRecord.objects.create(tenant=self.tenant_a, work_order=self.wo, step=self.step,
                                        part_type=self.pt, designated_part=self.part,
                                        status=status, shift=shift, shift_date=shift_date)

    def _gate(self):
        return self.step.get_fpi_status(self.wo, part=self.part)

    def test_day_pass_does_not_release_the_night_shift_on_the_same_date(self):
        self._record(FPIStatus.PASSED, self.day)
        with self._on(self.day):
            self.assertEqual(self._gate()['status'], FPIStatus.PASSED)
        with self._on(self.night):
            gate = self._gate()
            self.assertEqual(gate['status'], FPIStatus.PENDING)
            self.assertEqual(gate['context_label'], "Night on 11 Nov")

    def test_a_date_only_record_does_not_release_a_shift(self):
        self._record(FPIStatus.PASSED, None)
        with self._on(self.day):
            self.assertEqual(self._gate()['status'], FPIStatus.PENDING)

    def test_an_edited_shift_keeps_its_first_piece(self):
        self._record(FPIStatus.PASSED, self.day)
        new_day = self.day.create_new_version(user=self.user_a, end_time=time(15))
        with self._on(new_day):
            self.assertEqual(self._gate()['status'], FPIStatus.PASSED)

    def test_start_stamps_the_running_shift_and_endpoint_reports_it(self):
        with self._on(self.night):
            fpi, created = start_fpi(self.wo, self.step, self.user_a, part=self.part)
        self.assertTrue(created)
        self.assertEqual((fpi.shift_id, fpi.shift_date), (self.night.id, WED))
        self.authenticate_as(self.user_a, self.tenant_a)
        r = self.client.get(f"/api/FPIRecords/{fpi.id}/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["shift_info"]["name"], "Night")
        # Starting again for the record's shift (as the waiver card does) finds it.
        r = self.client.post("/api/FPIRecords/get-or-create/", {
            "work_order": str(self.wo.id), "step": str(self.step.id),
            "shift": str(self.night.id), "shift_date": str(WED),
        }, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["fpi"]["id"], str(fpi.id))
