"""Labor calendar blocks — operator non-working time (PTO / sick / meeting / break),
one-off or weekly, company-wide or per person. Covers the solver tie-in
(get_operator_shift_windows subtracts blocks) and serializer validation.
"""
from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from Tracker.models import (
    LaborCalendarBlock, OvertimeWindow, PlantCalendarException, Shift, Tenant,
)
from Tracker.serializers.scheduling import (
    LaborCalendarBlockSerializer, OvertimeWindowSerializer,
)
from Tracker.services.scheduling import data as sched_data
from Tracker.tests.base import TenantContextMixin


class LaborCalendarEngineTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Cal", slug="labor-cal", tier="PRO")
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        self.shift = Shift.objects.create(
            tenant=self.tenant, name="Day", code="DAY",
            start_time=time(6, 0), end_time=time(18, 0),
            days_of_week="0,1,2,3,4,5,6", is_active=True)
        self.op = User.objects.create_user(
            username="op1", email="op1@c.test", password="x",
            tenant=self.tenant, user_type="INTERNAL", default_shift=self.shift)
        self.horizon = sched_data.get_schedule_horizon(self.tenant)

    @staticmethod
    def _minutes(windows):
        return sum((e - s).total_seconds() for s, e in windows) / 60

    def _tomorrow_at(self, hour):
        return (self.horizon.start + timedelta(days=1)).replace(
            hour=hour, minute=0, second=0, microsecond=0)

    def test_baseline_operator_has_windows(self):
        w = sched_data.get_operator_shift_windows(self.tenant, self.horizon)
        self.assertIn(self.op.id, w)
        self.assertGreater(self._minutes(w[self.op.id]), 0)

    def test_company_once_block_reduces_all_operators(self):
        base = self._minutes(
            sched_data.get_operator_shift_windows(self.tenant, self.horizon)[self.op.id])
        start = self._tomorrow_at(9)  # a company all-hands 09:00–10:00 tomorrow
        LaborCalendarBlock.objects.create(
            tenant=self.tenant, user=None, kind="MEETING", recurrence="ONCE",
            start_time=start, end_time=start + timedelta(hours=1))
        after = self._minutes(
            sched_data.get_operator_shift_windows(self.tenant, self.horizon)[self.op.id])
        self.assertAlmostEqual(base - after, 60, delta=1)

    def test_user_block_only_affects_that_user(self):
        User = get_user_model()
        op2 = User.objects.create_user(
            username="op2", email="op2@c.test", password="x",
            tenant=self.tenant, user_type="INTERNAL", default_shift=self.shift)
        start = self._tomorrow_at(9)  # op1 out 09:00–11:00; op2 unaffected
        LaborCalendarBlock.objects.create(
            tenant=self.tenant, user=self.op, kind="PTO", recurrence="ONCE",
            start_time=start, end_time=start + timedelta(hours=2))
        w = sched_data.get_operator_shift_windows(self.tenant, self.horizon)
        self.assertAlmostEqual(
            self._minutes(w[op2.id]) - self._minutes(w[self.op.id]), 120, delta=1)

    def test_weekly_block_expands_over_horizon(self):
        company, _ = sched_data.get_labor_calendar_blocks(self.tenant, self.horizon)
        self.assertEqual(company, [])
        LaborCalendarBlock.objects.create(
            tenant=self.tenant, user=None, kind="MEETING", recurrence="WEEKLY",
            days_of_week="0", window_start=time(9, 0), window_end=time(9, 30))
        company2, _ = sched_data.get_labor_calendar_blocks(self.tenant, self.horizon)
        self.assertGreaterEqual(len(company2), 4)  # ≥4 Mondays in a 30-day window

    def test_inactive_block_ignored(self):
        start = self._tomorrow_at(9)
        LaborCalendarBlock.objects.create(
            tenant=self.tenant, user=None, kind="MEETING", recurrence="ONCE",
            start_time=start, end_time=start + timedelta(hours=1), is_active=False)
        company, _ = sched_data.get_labor_calendar_blocks(self.tenant, self.horizon)
        self.assertEqual(company, [])


class YearlyClosureTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Clo", slug="closures", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.horizon = sched_data.get_schedule_horizon(self.tenant)

    def test_yearly_closure_recurs_into_horizon(self):
        # A holiday whose month/day is ~5 days out, but stored in a PRIOR year:
        # the YEARLY rule must still block it in the current horizon.
        occ = self.horizon.start + timedelta(days=5)
        stored_start = occ.replace(year=occ.year - 1, hour=0, minute=0, second=0, microsecond=0)
        PlantCalendarException.objects.create(
            tenant=self.tenant, name="Founders Day", kind="HOLIDAY", recurrence="YEARLY",
            start_time=stored_start, end_time=stored_start + timedelta(days=1))
        closures = sched_data.get_calendar_closures(self.tenant, self.horizon)
        self.assertTrue(closures, "yearly closure should recur into the horizon")

    def test_yearly_closure_outside_horizon_excluded(self):
        occ = self.horizon.start + timedelta(days=90)  # ~3 months out, past the 30-day horizon
        stored_start = occ.replace(year=occ.year - 1, hour=0, minute=0, second=0, microsecond=0)
        PlantCalendarException.objects.create(
            tenant=self.tenant, name="Far Holiday", kind="HOLIDAY", recurrence="YEARLY",
            start_time=stored_start, end_time=stored_start + timedelta(days=1))
        self.assertEqual(sched_data.get_calendar_closures(self.tenant, self.horizon), [])

    def test_once_closure_in_horizon_blocks(self):
        start = (self.horizon.start + timedelta(days=3)).replace(hour=0, minute=0, second=0, microsecond=0)
        PlantCalendarException.objects.create(
            tenant=self.tenant, name="Shutdown", kind="SHUTDOWN", recurrence="ONCE",
            start_time=start, end_time=start + timedelta(days=2))
        self.assertTrue(sched_data.get_calendar_closures(self.tenant, self.horizon))


class OvertimeEngineTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="OT", slug="overtime", tier="PRO")
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        # Weekdays only — so a Saturday overtime window is genuinely *added* time.
        self.shift = Shift.objects.create(
            tenant=self.tenant, name="Day", code="DAY",
            start_time=time(6, 0), end_time=time(18, 0),
            days_of_week="0,1,2,3,4", is_active=True)
        self.op = User.objects.create_user(
            username="otop", email="otop@c.test", password="x",
            tenant=self.tenant, user_type="INTERNAL", default_shift=self.shift)
        self.horizon = sched_data.get_schedule_horizon(self.tenant)

    @staticmethod
    def _minutes(windows):
        return sum((e - s).total_seconds() for s, e in windows) / 60

    def _next_saturday(self):
        for i in range(1, 14):
            cand = self.horizon.start + timedelta(days=i)
            if cand.weekday() == 5:  # Saturday
                return cand.replace(hour=0, minute=0, second=0, microsecond=0)
        raise AssertionError("no Saturday in range")

    def _op_minutes(self):
        w = sched_data.get_operator_shift_windows(self.tenant, self.horizon)
        return self._minutes(w.get(self.op.id, []))

    def test_overtime_adds_weekend_shift(self):
        base = self._op_minutes()
        sat = self._next_saturday()
        # Run the Day shift (06:00–18:00 = 12h) on Saturday.
        OvertimeWindow.objects.create(
            tenant=self.tenant, shift=self.shift, recurrence="ONCE",
            start_date=sat.date(), end_date=sat.date())
        self.assertAlmostEqual(self._op_minutes() - base, 12 * 60, delta=2)

    def test_closure_beats_overtime(self):
        base = self._op_minutes()
        sat = self._next_saturday()
        OvertimeWindow.objects.create(
            tenant=self.tenant, shift=self.shift, recurrence="ONCE",
            start_date=sat.date(), end_date=sat.date())
        PlantCalendarException.objects.create(
            tenant=self.tenant, name="Holiday", kind="HOLIDAY", recurrence="ONCE",
            start_time=sat, end_time=sat + timedelta(days=1))
        # Closure wins → the overtime adds nothing.
        self.assertAlmostEqual(self._op_minutes(), base, delta=2)

    def test_overtime_scoped_to_shift_crew(self):
        User = get_user_model()
        night = Shift.objects.create(
            tenant=self.tenant, name="Night", code="NGT",
            start_time=time(18, 0), end_time=time(6, 0),
            days_of_week="0,1,2,3,4", is_active=True)
        op_night = User.objects.create_user(
            username="night", email="n@c.test", password="x",
            tenant=self.tenant, user_type="INTERNAL", default_shift=night)
        sat = self._next_saturday()
        # Overtime runs the DAY shift Saturday → only day-shift crew get it.
        OvertimeWindow.objects.create(
            tenant=self.tenant, shift=self.shift, recurrence="ONCE",
            start_date=sat.date(), end_date=sat.date())
        w = sched_data.get_operator_shift_windows(self.tenant, self.horizon)
        self.assertGreater(self._minutes(w[self.op.id]), self._minutes(w[op_night.id]))


class OvertimeWindowSerializerTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="OTS", slug="overtime-s", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.shift = Shift.objects.create(
            tenant=self.tenant, name="Day", code="DAY",
            start_time=time(6, 0), end_time=time(18, 0),
            days_of_week="0,1,2,3,4", is_active=True)

    def test_once_requires_dates(self):
        s = OvertimeWindowSerializer(data={"shift": self.shift.id, "recurrence": "ONCE"})
        self.assertFalse(s.is_valid())

    def test_valid_weekly(self):
        s = OvertimeWindowSerializer(data={
            "shift": self.shift.id, "recurrence": "WEEKLY", "days_of_week": "5,6"})
        self.assertTrue(s.is_valid(), s.errors)


class LaborCalendarBlockSerializerTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="CalS", slug="labor-cal-s", tier="PRO")
        self.set_tenant_context(self.tenant)

    def test_once_requires_dates(self):
        s = LaborCalendarBlockSerializer(data={"recurrence": "ONCE", "kind": "PTO"})
        self.assertFalse(s.is_valid())

    def test_weekly_requires_window(self):
        s = LaborCalendarBlockSerializer(
            data={"recurrence": "WEEKLY", "kind": "MEETING", "days_of_week": "0"})
        self.assertFalse(s.is_valid())

    def test_valid_once_company_block(self):
        now = timezone.now()
        s = LaborCalendarBlockSerializer(data={
            "recurrence": "ONCE", "kind": "MEETING", "user": None,
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat()})
        self.assertTrue(s.is_valid(), s.errors)

    def test_valid_weekly_block(self):
        s = LaborCalendarBlockSerializer(data={
            "recurrence": "WEEKLY", "kind": "MEETING", "user": None,
            "days_of_week": "0,2", "window_start": "09:00", "window_end": "09:30"})
        self.assertTrue(s.is_valid(), s.errors)
