"""Rough-cut capacity planning (RCCP) + capable-to-promise (CTP).

Aggregate capacity-vs-load arithmetic — the coarse long-range planning layer above
the CP-SAT scheduler. These tests pin the behaviours that make the answer
trustworthy: capacity reflects the shift calendar and lights-out machines, load
counts only REMAINING work (no terminal-state dwell, no rework branch, no vendor
time), and CTP is CUMULATIVE — an order may consume every free hour between now and
its due date, not just its due month's.
"""
from datetime import date, timedelta
from datetime import time as dtime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from Tracker.models import (
    Companies, Equipments, OptimizationConfig, Parts, PartTypes, Processes, ProcessStatus,
    ProcessStep,
    Shift, StepEdge, Steps, StepTiming, Tenant, WorkCenter, WorkOrder, WorkOrderStatus,
)
from Tracker.services.planning import rccp
from Tracker.tests.base import TenantContextMixin


class _RccpFixture(TenantContextMixin):
    """The shop under test: one operator on a Mon-Fri 8h shift, one attended machine
    in Cell A, one 60 min/piece step. So one unit = one labor hour and one Cell A
    hour, which is what lets the tests below state expectations as plain numbers.

    A fixture mixin rather than a base test class: subclassing a TestCase to reuse
    its setUp re-runs every one of its tests in the subclass too, which is pure
    duplicated work on a suite that is already slow.
    """

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="RCCP", slug="rccp", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.user = get_user_model().objects.create_user(
            username="rccp-op", email="rccp@c.test", password="x", tenant=self.tenant)
        # A Mon-Fri 8h day shift, one operator rostered → the labor capacity basis.
        self.shift = Shift.objects.create(
            tenant=self.tenant, code="DAY", name="Day", start_time=dtime(8, 0),
            end_time=dtime(16, 0), days_of_week="0,1,2,3,4", is_active=True)
        self.user.default_shift = self.shift
        self.user.save(update_fields=["default_shift"])

        self.wc = WorkCenter.objects.create(tenant=self.tenant, name="Cell A", code="A")
        self.machine = Equipments.objects.create(
            tenant=self.tenant, name="M-1", is_schedulable=True, runs_unattended=False)
        self.wc.equipment.add(self.machine)

        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Widget")
        # APPROVED: CTP quotes only against a releasable (approved, current) routing.
        self.process = Processes.objects.create(
            tenant=self.tenant, name="W", part_type=self.pt, status=ProcessStatus.APPROVED)
        # 60 min/piece on one step in Cell A → 1 hour of work per unit.
        self.step = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Cut", step_type="TASK",
            work_center=self.wc)
        StepTiming.objects.create(tenant=self.tenant, step=self.step, cycle_time_minutes=60)
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)

    def _wo(self, qty, due, start=None, erp="WO-1"):
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id=erp, workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=qty, process=self.process, expected_completion=due,
            expected_start=start)
        for i in range(qty):
            Parts.objects.create(
                tenant=self.tenant, ERP_id=f"{erp}-P{i}", part_type=self.pt,
                work_order=wo, step=self.step)
        return wo


class RccpTests(_RccpFixture, TestCase):

    # --- capacity ----------------------------------------------------------

    def test_labor_capacity_tracks_crew_and_shift_calendar(self):
        """Capacity = rostered crew × the shift calendar's working hours — not
        wall-clock, so weekends/nights never inflate the promise."""
        out = rccp.build_capacity_load(self.tenant, months=2)
        first = out["labor"]["series"][0]
        self.assertEqual(out["labor"]["crew_size"], 1)
        # An 8h Mon-Fri shift can never reach a month's calendar hours.
        self.assertGreater(first["capacity_hours"], 0)
        self.assertLess(first["capacity_hours"], 31 * 24)

    def test_the_current_month_offers_only_what_is_left_of_it(self):
        """Pinned dates, not today's: the bug this guards against only showed late in a
        month. On 21 Oct 2026 (a Wednesday) the October bucket is the rest of October —
        about 7½ shift days of an 8h Mon-Fri shift — not all 22 working days, which read
        a busy crew as two-thirds idle. On the 1st it is the whole month."""
        from datetime import datetime
        from unittest import mock
        from Tracker.services.core.clock import plant_tz
        tz = plant_tz(self.tenant)
        with mock.patch.object(rccp.timezone, 'now',
                               return_value=datetime(2026, 10, 21, 12, 0, tzinfo=tz)):
            late = rccp.build_capacity_load(self.tenant, months=2)["labor"]["series"]
        with mock.patch.object(rccp.timezone, 'now',
                               return_value=datetime(2026, 10, 1, 0, 0, tzinfo=tz)):
            whole = rccp.build_capacity_load(self.tenant, months=2)["labor"]["series"]
        self.assertEqual((late[0]["bucket"], whole[0]["bucket"]), ("2026-10", "2026-10"))
        self.assertAlmostEqual(whole[0]["capacity_hours"], 22 * 8, delta=8)    # 22 weekdays
        self.assertAlmostEqual(late[0]["capacity_hours"], 7.5 * 8, delta=8)    # 21st noon → 30th
        # Later months are whole either way.
        self.assertEqual(late[1]["capacity_hours"], whole[1]["capacity_hours"])

    def test_a_yearly_closure_in_the_middle_year_of_a_long_view_comes_off_labor(self):
        """A 24-month view from November 2026 spans 2026–2028; 2027's yearly closures
        were skipped (only the first and last years were looked at), overstating every
        2027 month's labor capacity."""
        from datetime import datetime
        from unittest import mock
        from Tracker.models import PlantCalendarException
        from Tracker.services.core.clock import plant_tz
        tz = plant_tz(self.tenant)
        now = datetime(2026, 11, 2, 12, 0, tzinfo=tz)
        with mock.patch.object(rccp.timezone, 'now', return_value=now):
            before = rccp.build_capacity_load(self.tenant, months=24)["labor"]["series"]
        # Wed 14 July in 2027, stored years earlier as a yearly holiday.
        PlantCalendarException.objects.create(
            tenant=self.tenant, name="Summer holiday", kind="HOLIDAY", recurrence="YEARLY",
            start_time=datetime(2020, 7, 14, 0, 0, tzinfo=tz),
            end_time=datetime(2020, 7, 15, 0, 0, tzinfo=tz))
        with mock.patch.object(rccp.timezone, 'now', return_value=now):
            after = rccp.build_capacity_load(self.tenant, months=24)["labor"]["series"]
        july = next(i for i, b in enumerate(before) if b["bucket"] == "2027-07")
        self.assertAlmostEqual(before[july]["capacity_hours"] - after[july]["capacity_hours"], 8, delta=0.5)

    def test_planned_absence_comes_off_the_crews_capacity(self):
        """A booked week of PTO is a week the crew can't work — capacity is each
        person's own shift windows less their labor-calendar blocks, not headcount ×
        the plant's hours."""
        from datetime import datetime
        from unittest import mock
        from Tracker.models import LaborCalendarBlock
        from Tracker.services.core.clock import plant_tz
        tz = plant_tz(self.tenant)
        now = datetime(2026, 10, 21, 12, 0, tzinfo=tz)
        with mock.patch.object(rccp.timezone, 'now', return_value=now):
            before = rccp.build_capacity_load(self.tenant, months=2)["labor"]["series"][1]
        LaborCalendarBlock.objects.create(
            tenant=self.tenant, user=self.user, kind='PTO', recurrence='ONCE', is_active=True,
            start_time=datetime(2026, 11, 2, 0, 0, tzinfo=tz),
            end_time=datetime(2026, 11, 7, 0, 0, tzinfo=tz))       # Mon 2nd – Fri 6th
        with mock.patch.object(rccp.timezone, 'now', return_value=now):
            after = rccp.build_capacity_load(self.tenant, months=2)["labor"]["series"][1]
        self.assertEqual(before["bucket"], "2026-11")
        self.assertAlmostEqual(before["capacity_hours"] - after["capacity_hours"], 5 * 8, delta=0.5)

    def test_lights_out_machine_gets_calendar_hours(self):
        """A lights-out machine's capacity is wall-clock, an attended one's is shift
        hours — the runs_unattended resolution the scheduler uses."""
        before = next(w for w in rccp.build_capacity_load(self.tenant, months=1)["work_centers"]
                      if w["name"] == "Cell A")["series"][0]["capacity_hours"]
        Equipments.objects.filter(pk=self.machine.pk).update(runs_unattended=True)
        after = next(w for w in rccp.build_capacity_load(self.tenant, months=1)["work_centers"]
                     if w["name"] == "Cell A")["series"][0]["capacity_hours"]
        self.assertGreater(after, before)

    def _lights_out_cell(self, now, months):
        from unittest import mock
        with mock.patch.object(rccp.timezone, 'now', return_value=now):
            return next(w for w in rccp.build_capacity_load(self.tenant, months=months)["work_centers"]
                        if w["name"] == "Cell A")["series"]

    def test_a_plant_closure_stops_lights_out_machines_too(self):
        """A closure stops every machine, as in the solver: a 2-day shutdown takes 48 h
        off each lights-out machine's month."""
        from datetime import datetime
        from Tracker.models import PlantCalendarException
        from Tracker.services.core.clock import plant_tz
        tz = plant_tz(self.tenant)
        now = datetime(2026, 11, 2, 12, 0, tzinfo=tz)
        Equipments.objects.filter(pk=self.machine.pk).update(runs_unattended=True)
        before = self._lights_out_cell(now, 3)
        PlantCalendarException.objects.create(
            tenant=self.tenant, name="Shutdown", kind="SHUTDOWN",
            start_time=datetime(2026, 12, 21, 0, 0, tzinfo=tz),
            end_time=datetime(2026, 12, 23, 0, 0, tzinfo=tz))
        after = self._lights_out_cell(now, 3)
        dec = next(i for i, b in enumerate(before) if b["bucket"] == "2026-12")
        self.assertAlmostEqual(before[dec]["capacity_hours"] - after[dec]["capacity_hours"], 48, delta=0.5)

    def test_a_yearly_closure_in_a_middle_year_stops_lights_out_machines(self):
        from datetime import datetime
        from Tracker.models import PlantCalendarException
        from Tracker.services.core.clock import plant_tz
        tz = plant_tz(self.tenant)
        now = datetime(2026, 11, 2, 12, 0, tzinfo=tz)
        Equipments.objects.filter(pk=self.machine.pk).update(runs_unattended=True)
        before = self._lights_out_cell(now, 24)
        PlantCalendarException.objects.create(
            tenant=self.tenant, name="Summer holiday", kind="HOLIDAY", recurrence="YEARLY",
            start_time=datetime(2020, 7, 14, 0, 0, tzinfo=tz),
            end_time=datetime(2020, 7, 15, 0, 0, tzinfo=tz))
        after = self._lights_out_cell(now, 24)
        july = next(i for i, b in enumerate(before) if b["bucket"] == "2027-07")
        self.assertAlmostEqual(before[july]["capacity_hours"] - after[july]["capacity_hours"], 24, delta=0.5)

    # --- load --------------------------------------------------------------

    def test_load_counts_remaining_work_of_active_orders(self):
        """10 units × 60 min = 10 h of load in the due bucket's window."""
        today = timezone.now().date()
        self._wo(10, due=today + timedelta(days=5), start=today)
        out = rccp.build_capacity_load(self.tenant, months=2)
        total = sum(r["load_hours"] for r in out["labor"]["series"])
        self.assertAlmostEqual(total, 10.0, places=1)

    def test_completed_and_held_orders_carry_no_load(self):
        """Only schedulable work counts — a finished or held order isn't demand."""
        today = timezone.now().date()
        wo = self._wo(10, due=today + timedelta(days=5), erp="WO-DONE")
        WorkOrder.objects.filter(pk=wo.pk).update(
            workorder_status=WorkOrderStatus.COMPLETED)
        out = rccp.build_capacity_load(self.tenant, months=2)
        self.assertEqual(sum(r["load_hours"] for r in out["labor"]["series"]), 0.0)

    # --- capable-to-promise ------------------------------------------------

    def test_ctp_accepts_an_order_that_fits(self):
        today = timezone.now().date()
        r = rccp.capable_to_promise(self.tenant, self.pt.id, 5, today + timedelta(days=20), months=6)
        self.assertTrue(r["feasible"], r)
        self.assertEqual(r["binding_resources"], [])
        self.assertAlmostEqual(r["work_content_hours"]["labor"], 5.0, places=1)

    def test_ctp_rejects_an_oversized_order_and_names_the_binding_resource(self):
        """5000 h of work can't fit a one-operator shop in a month; the answer must
        say WHICH resource ran out, not just 'no'."""
        today = timezone.now().date()
        r = rccp.capable_to_promise(self.tenant, self.pt.id, 5000, today + timedelta(days=20), months=6)
        self.assertFalse(r["feasible"])
        self.assertTrue(r["binding_resources"])
        self.assertIn("free_through_target", r["binding_resources"][0])

    def test_ctp_is_cumulative_so_a_later_date_can_fit_what_an_early_one_cannot(self):
        """The core rule: an order may use every free hour between now and its due
        date. Same order, later date → feasible, and the earliest-fit bucket is
        reported so a planner can counter-offer."""
        today = timezone.now().date()
        qty = 300  # 300 h — more than one month of a single 8h-day operator
        soon = rccp.capable_to_promise(self.tenant, self.pt.id, qty, today + timedelta(days=20), months=24)
        later = rccp.capable_to_promise(self.tenant, self.pt.id, qty, today + timedelta(days=550), months=24)
        self.assertFalse(soon["feasible"])
        self.assertTrue(later["feasible"], later)
        self.assertIsNotNone(soon["earliest_feasible_bucket"])

    def test_ctp_answers_name_the_date_asked_about_not_just_its_month(self):
        """A refusal is measured to the DUE DATE; the earliest-fit scan starts at the
        same bucket but measures to its END. Reporting both as the bucket label made
        them collide: a due date early in a month read as
        "Not by 2026-11 ... Earliest it fits: 2026-11" — a counter-offer restating the
        date just refused, which a planner could act on and promise a customer a date
        the shop had already rejected.

        Walked in the browser 2026-10-12 (300 injectors due 2026-11-01).
        """
        from datetime import date
        today = timezone.now().date()
        # First of a month, far enough out to be in a later bucket than today's.
        y, m = (today.year, today.month + 2) if today.month <= 10 else (today.year + 1, today.month - 10)
        first_of_month = date(y, m, 1)
        qty = 300  # more than the hours available by the 1st, but not by month end

        r = rccp.capable_to_promise(self.tenant, self.pt.id, qty, first_of_month, months=24)

        # The date asked about is reported, so the refusal can be stated precisely.
        self.assertEqual(r["target_date"], first_of_month.isoformat())
        self.assertNotEqual(r["target_date"], r["target_bucket"])

        if not r["feasible"] and r["earliest_feasible_bucket"] == r["target_bucket"]:
            # The exact collision: fits by month end, not by the date. The caller must
            # be able to say "end of <bucket>" rather than repeat the refusal back.
            self.assertTrue(
                r["earliest_is_target_bucket"],
                "earliest fit is the due date's own bucket but the flag doesn't say so, "
                "so the UI cannot distinguish the counter-offer from the refusal")

    def test_ctp_counts_only_the_hours_between_now_and_the_due_date(self):
        """The sliding window, pinned on a date-independent case.

        The cumulative test above only catches the whole-month overcount when
        `today + 20d` happens to cross a month boundary — it passes in the first
        third of a month and fails in the rest, which is why this went unnoticed.
        Due TOMORROW fails on any date: one working day cannot absorb 100 h, but
        whole-month arithmetic credits the entire month (176 h here) and says yes.

        Both halves of the window are wrong the same way and this catches both:
        hours already elapsed this month are not capacity for a promise made
        today, and hours after the due date cannot serve that due date.
        """
        today = timezone.now().date()
        r = rccp.capable_to_promise(self.tenant, self.pt.id, 100, today + timedelta(days=1), months=6)
        self.assertFalse(
            r["feasible"],
            f"100 h cannot be made by tomorrow on an 8 h/day shop; got {r}",
        )
        self.assertTrue(r["binding_resources"])
        # The reported headroom must be a day or so of work, not a month of it.
        self.assertLess(r["binding_resources"][0]["free_through_target"], 100)

    def test_ctp_reports_unroutable_part_type_instead_of_guessing(self):
        bare = PartTypes.objects.create(tenant=self.tenant, name="NoRoute")
        r = rccp.capable_to_promise(self.tenant, bare.id, 1, timezone.now().date(), months=3)
        self.assertFalse(r["feasible"])
        self.assertIn("reason", r)


class RccpSeesBeyondDetailedHorizonTests(_RccpFixture, TestCase):
    """RCCP and CTP must see work releasing past the SOLVER's horizon.

    `get_active_workorders` filters out work whose `expected_start` is beyond the
    detailed window — a guard for the solver's arithmetic (`_release_minutes` clamps
    into [0, H], so a far-dated order made the whole board INFEASIBLE). That filter
    has no business in a monthly bucket sum, and applying it here blinded the one
    layer built to look past the horizon. Worse for CTP, which would then promise
    capacity without counting the load already committed against it.
    """

    def _far_start(self):
        """A start date safely past any plausible detailed horizon."""
        from Tracker.services.scheduling.data import get_schedule_horizon
        return get_schedule_horizon(self.tenant).end.date() + timedelta(days=120)

    def test_capacity_load_counts_work_starting_beyond_the_solver_horizon(self):
        far = self._far_start()
        self._wo(10, due=far + timedelta(days=5), start=far, erp="WO-FAR")
        out = rccp.build_capacity_load(self.tenant, months=36)
        total = sum(r["load_hours"] for r in out["labor"]["series"])
        self.assertAlmostEqual(total, 10.0, places=1,
                               msg="far-dated work vanished from the rough-cut view")

    def test_solver_still_excludes_it(self):
        """The guard must stay where it was needed — this is a scoped read, not a
        removal."""
        from Tracker.services.scheduling import data
        far = self._far_start()
        self._wo(10, due=far + timedelta(days=5), start=far, erp="WO-FAR")
        self.assertEqual([w.erp_id for w in data.get_active_workorders(self.tenant)], [])
        self.assertEqual(
            [w.erp_id for w in data.get_active_workorders(self.tenant, within_horizon=False)],
            ["WO-FAR"])

    def test_ctp_counts_far_dated_load_against_free_capacity(self):
        """A promise made blind to committed far-dated work is worse than no promise.

        Measured on `free_through_target` rather than on `feasible`, because feasible
        cannot show this: `_fits` clamps each bucket's free capacity at zero, so one
        overloaded bucket never drags the cumulative total negative and a small order
        still fits around it. Free capacity, though, drops by exactly the load counted
        — which is the thing under test.
        """
        far = self._far_start()
        target = far + timedelta(days=10)
        # Large enough that Labor is binding in BOTH runs, so both answers carry a
        # free_through_target to compare. No Parts are created for a candidate, so
        # the size is free.
        candidate = 100_000

        def labor_free(result):
            return next(b["free_through_target"] for b in result["binding_resources"]
                        if b["resource"] == "Labor")

        clear = rccp.capable_to_promise(self.tenant, self.pt.id, candidate, target,
                                        months=36)
        # 100 units = 100 labor hours, committed to a bucket at/behind the target.
        self._wo(100, due=target, start=far, erp="WO-FAR")
        loaded = rccp.capable_to_promise(self.tenant, self.pt.id, candidate, target,
                                         months=36)

        self.assertLess(
            labor_free(loaded), labor_free(clear),
            msg="free capacity through the target was unchanged by 100 h of committed "
                "far-dated work — CTP is not counting it")


class RccpOutsideProcessSpanTests(_RccpFixture, TestCase):
    """Vendor turnaround has to widen the back-scheduled run-up.

    An outside-process step costs no capacity (`_step_hours` returns `(0, 0)`) but
    consumes calendar time, so it appears in no resource's hours. `_load_span` adds
    `ref.osp_days` for the routing's steps on top of the work-content span — otherwise a
    routing that ships out for plating is planned to start as though the trip is free.

    `ref.osp_days` comes from `sched_data.get_outside_process_step_days`, the same
    four-tier chain the solver uses: step → supplier → tenant config → 7 days.
    """

    def _add_osp_step(self, *, lead_days=None, supplier=None):
        """Append a subcontract operation to the fixture's routing."""
        step = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Plating", step_type="TASK",
            work_center=self.wc, is_outside_process=True,
            outside_process_lead_days=lead_days, outside_supplier=supplier)
        ProcessStep.objects.create(process=self.process, step=step, order=2)
        return step

    def _planned_start(self, erp="WO-OSP"):
        """The back-scheduled release date RCCP computes for a single dated order."""
        out = rccp.build_capacity_load(self.tenant, months=12)
        row = next(r for r in out["planned_releases"] if r["erp_id"] == erp)
        return row["planned_start"]

    def test_osp_turnaround_widens_the_span(self):
        """A 60-day trip to the platers has to be run up to, not absorbed. Without it
        the order is planned to release two months too late and is late on arrival."""
        today = timezone.now().date()
        due = today + timedelta(days=300)   # far enough that neither answer clamps

        self._wo(5, due=due, erp="WO-OSP")
        without = self._planned_start()

        self._add_osp_step(lead_days=60)
        with_osp = self._planned_start()

        self.assertLess(with_osp, without)
        self.assertAlmostEqual((without - with_osp).days, 60, delta=2)

    def test_osp_step_contributes_no_hours(self):
        """The trip is elapsed VENDOR time. Counting it as our hours reported thousands
        of hours of load on a work centre nobody was standing at."""
        today = timezone.now().date()
        self._wo(5, due=today + timedelta(days=300), start=today, erp="WO-OSP")

        before = rccp.build_capacity_load(self.tenant, months=12)
        labor_before = sum(r["load_hours"] for r in before["labor"]["series"])
        cell_before = sum(r["load_hours"] for w in before["work_centers"]
                          if w["name"] == "Cell A" for r in w["series"])

        self._add_osp_step(lead_days=60)

        after = rccp.build_capacity_load(self.tenant, months=12)
        labor_after = sum(r["load_hours"] for r in after["labor"]["series"])
        cell_after = sum(r["load_hours"] for w in after["work_centers"]
                         if w["name"] == "Cell A" for r in w["series"])

        self.assertAlmostEqual(labor_after, labor_before, places=1)
        self.assertAlmostEqual(cell_after, cell_before, places=1)

    def test_supplier_default_applies_when_the_step_has_no_lead_days(self):
        """Tier 2 of the chain: the vendor's own quoted turnaround."""
        today = timezone.now().date()
        due = today + timedelta(days=300)
        supplier = Companies.objects.create(
            tenant=self.tenant, name="Apex Plating",
            default_outside_process_turnaround_days=45)

        self._wo(5, due=due, erp="WO-OSP")
        without = self._planned_start()

        self._add_osp_step(lead_days=None, supplier=supplier)
        with_osp = self._planned_start()

        self.assertAlmostEqual((without - with_osp).days, 45, delta=2)

    def test_tenant_config_default_applies_when_neither_is_set(self):
        """Tier 3: an OSP step with no lead days and no supplier still costs calendar
        time — falling through to zero would be the one wrong answer."""
        today = timezone.now().date()
        due = today + timedelta(days=300)
        cfg, _ = OptimizationConfig.objects.get_or_create(tenant=self.tenant)
        OptimizationConfig.objects.filter(pk=cfg.pk).update(
            default_outside_process_turnaround_days=30)

        self._wo(5, due=due, erp="WO-OSP")
        without = self._planned_start()

        self._add_osp_step(lead_days=None, supplier=None)
        with_osp = self._planned_start()

        self.assertAlmostEqual((without - with_osp).days, 30, delta=2)


class RccpMachineVsLaborTests(_RccpFixture, TestCase):
    """Machine hours and labor hours are different numbers.

    The fixture's step is FULL attention (operator tied to the machine), so the two
    coincide there and the bug was invisible. On a load/unload step the operator only
    touches each piece — charging the full machine run to the crew overstates the
    resource RCCP treats as usually binding.
    """

    def _series_totals(self, months=3):
        out = rccp.build_capacity_load(self.tenant, months=months)
        labor = sum(b["load_hours"] for b in out["labor"]["series"])
        cell = next(w for w in out["work_centers"] if w["name"] == "Cell A")
        machine = sum(b["load_hours"] for b in cell["series"])
        return labor, machine

    def test_full_attention_charges_the_whole_run_to_labor(self):
        today = timezone.now().date()
        self._wo(10, due=today + timedelta(days=5), start=today)
        labor, machine = self._series_totals()
        self.assertAlmostEqual(labor, 10.0, delta=0.5)
        self.assertAlmostEqual(machine, 10.0, delta=0.5)

    def test_load_unload_charges_only_the_touch_time_to_labor(self):
        """60 min cycle, 6 min touch: the machine is busy 10 h for 10 pieces, the
        operator 1 h. Before the split both read 10 h."""
        from Tracker.models import StepTiming
        StepTiming.objects.filter(step=self.step).update(
            attention_type="load_unload", load_unload_per_piece=6)
        today = timezone.now().date()
        self._wo(10, due=today + timedelta(days=5), start=today)
        labor, machine = self._series_totals()
        self.assertAlmostEqual(machine, 10.0, delta=0.5,
                               msg="the machine is still occupied for the full run")
        self.assertAlmostEqual(labor, 1.0, delta=0.5,
                               msg="only the per-piece touch occupies the operator")

    def test_unattended_charges_setup_only(self):
        """A robot feeds it: the machine runs 10 h, the operator does the 30 min setup
        and walks away."""
        from Tracker.models import StepTiming
        StepTiming.objects.filter(step=self.step).update(
            attention_type="unattended", setup_minutes=30, load_unload_per_piece=6)
        today = timezone.now().date()
        self._wo(10, due=today + timedelta(days=5), start=today)
        labor, machine = self._series_totals()
        self.assertAlmostEqual(machine, 10.5, delta=0.5)
        self.assertAlmostEqual(labor, 0.5, delta=0.5,
                               msg="setup only — the stale touch time must not count")


class RccpLoadPlacementTests(_RccpFixture, TestCase):
    """WHERE an order's hours land, not just how many there are.

    One unit is one labor hour here and one rostered operator is worth roughly 176 h a
    month, so an order's required span is computable by hand and the assertions below
    are about placement rather than magnitude.
    """

    def _labor_series(self, months=24):
        out = rccp.build_capacity_load(self.tenant, months=months)
        return [b["load_hours"] for b in out["labor"]["series"]]

    def test_undated_order_lands_near_its_due_date_not_today(self):
        """The core of the rule. A small order due in ~10 months needs far less than a
        month of capacity, so it belongs in its due bucket — not smeared from today."""
        today = timezone.now().date()
        self._wo(20, due=today + timedelta(days=300), erp="WO-FAR")
        series = self._labor_series()
        self.assertAlmostEqual(sum(series), 20.0, places=1)
        self.assertEqual(series[0], 0.0,
                         "work due in ten months must not load this month")
        self.assertGreater(sum(series[7:]), 0.0, "load vanished instead of moving")

    def test_a_big_order_backs_up_over_the_months_it_needs(self):
        """500 h against ~176 h/month can't fit one bucket, so it occupies the run-up —
        the reason point-loading the due month was wrong in the other direction."""
        today = timezone.now().date()
        self._wo(500, due=today + timedelta(days=300), erp="WO-BIG")
        series = self._labor_series()
        loaded = [i for i, h in enumerate(series) if h > 0]
        # Each bucket is rounded to 0.1 in the response, so a spread order's total can
        # drift by up to 0.05 per bucket — tolerance, not an equality.
        self.assertAlmostEqual(sum(series), 500.0, delta=0.5)
        self.assertGreaterEqual(len(loaded), 3, "500 h should span several buckets")
        self.assertEqual(series[0], 0.0, "it still should not start today")

    def test_explicit_start_date_still_wins(self):
        """Back-scheduling is the fallback. A planner who sets a release date owns it."""
        today = timezone.now().date()
        self._wo(20, due=today + timedelta(days=300), start=today, erp="WO-DATED")
        series = self._labor_series()
        self.assertGreater(series[0], 0.0,
                           "an explicit start date must place load from that date")

    def test_work_already_started_loads_from_now(self):
        """An OPEN StepExecution means hours are being burned today, whatever the due
        date says — back-scheduling that would be wrong in the opposite direction."""
        from Tracker.models import StepExecution
        today = timezone.now().date()
        wo = self._wo(20, due=today + timedelta(days=300), erp="WO-RUNNING")
        StepExecution.objects.create(
            tenant=self.tenant, part=wo.parts.first(), step=self.step,
            entered_at=timezone.now())
        series = self._labor_series()
        self.assertGreater(series[0], 0.0,
                           "in-progress work must load the current bucket")


class RccpOrderLineDemandTests(_RccpFixture, TestCase):
    """Open order lines no work order carries yet are placed like an undated work
    order — back from the line's due date on the approved routing — and join the load.
    A line that can't be placed is flagged, never dumped into the current month."""

    def _line(self, qty, due, part_type=None, n=1):
        from Tracker.models import OrderLine, Orders
        order = Orders.objects.create(tenant=self.tenant, name=f"Demand {n}")
        return OrderLine.objects.create(tenant=self.tenant, order=order, line_number=1,
                                        part_type=part_type or self.pt, quantity=qty,
                                        due_date=due)

    def test_a_line_due_next_year_loads_next_year_not_today(self):
        self._line(20, timezone.now().date() + timedelta(days=300))
        out = rccp.build_capacity_load(self.tenant, months=24)
        labor = out["labor"]["series"]
        self.assertAlmostEqual(sum(b["load_hours"] for b in labor), 20.0, delta=0.5)
        self.assertEqual(labor[0]["load_hours"], 0.0, "a line due in ten months must not load today")
        # The share from order lines is reported alongside, so the page can say so.
        self.assertAlmostEqual(sum(b["order_line_hours"] for b in labor), 20.0, delta=0.5)
        cell = next(w for w in out["work_centers"] if w["name"] == "Cell A")
        self.assertAlmostEqual(sum(b["order_line_hours"] for b in cell["series"]), 20.0, delta=0.5)
        demand = out["unplanned_demand"]
        self.assertEqual((demand["lines"], demand["placed_lines"], demand["units"]), (1, 1, 20))
        self.assertEqual(demand["unplaceable"], [])

    def test_work_order_hours_are_not_counted_as_order_line_hours(self):
        self._wo(10, due=timezone.now().date() + timedelta(days=60))
        labor = rccp.build_capacity_load(self.tenant, months=6)["labor"]["series"]
        self.assertAlmostEqual(sum(b["load_hours"] for b in labor), 10.0, delta=0.5)
        self.assertEqual(sum(b["order_line_hours"] for b in labor), 0.0)

    def test_a_line_with_no_due_date_is_flagged_not_loaded(self):
        self._line(5, None)
        out = rccp.build_capacity_load(self.tenant, months=6)
        self.assertEqual(sum(b["load_hours"] for b in out["labor"]["series"]), 0.0)
        flagged = out["unplanned_demand"]["unplaceable"]
        self.assertEqual([(u["quantity"], u["reason"]) for u in flagged], [(5, "No due date")])
        self.assertEqual(out["unplanned_demand"]["placed_lines"], 0)

    def test_a_line_with_no_approved_routing_is_flagged_not_loaded(self):
        bare = PartTypes.objects.create(tenant=self.tenant, name="No Route")
        self._line(5, timezone.now().date() + timedelta(days=60), part_type=bare)
        out = rccp.build_capacity_load(self.tenant, months=6)
        self.assertEqual(sum(b["load_hours"] for b in out["labor"]["series"]), 0.0)
        flagged = out["unplanned_demand"]["unplaceable"]
        self.assertEqual(len(flagged), 1)
        self.assertEqual(flagged[0]["part_type"], "No Route")
        self.assertTrue(flagged[0]["reason"])

    def test_an_overdue_line_loads_now(self):
        self._line(5, timezone.now().date() - timedelta(days=40))
        labor = rccp.build_capacity_load(self.tenant, months=6)["labor"]["series"]
        self.assertAlmostEqual(labor[0]["load_hours"], 5.0, delta=0.1)

    def test_a_fully_planned_line_carries_no_extra_load(self):
        line = self._line(10, timezone.now().date() + timedelta(days=60))
        wo = self._wo(10, due=timezone.now().date() + timedelta(days=60), erp="WO-PEG")
        wo.order_line = line
        wo.save(update_fields=["order_line"])
        labor = rccp.build_capacity_load(self.tenant, months=6)["labor"]["series"]
        self.assertAlmostEqual(sum(b["load_hours"] for b in labor), 10.0, delta=0.5,
                               msg="the line's units are the work order's — not counted twice")
        self.assertEqual(sum(b["order_line_hours"] for b in labor), 0.0)


class RccpOrderLineMaterialTests(_RccpFixture, TestCase):
    """An order line has no work orders yet, so nothing carries its components: the BOM
    is exploded through MAKE lines down to what is bought, grossed up by each routing's
    expected yield, and the demand lands at the line's planned start."""

    def setUp(self):
        super().setUp()
        from decimal import Decimal
        from Tracker.models import BOM, BOMLine, Material
        self.oring = Material.objects.create(tenant=self.tenant, name="O-Ring")
        self.rod = Material.objects.create(tenant=self.tenant, name="Rod")
        # A made sub-assembly whose one step scraps half of what it starts.
        self.sub = PartTypes.objects.create(tenant=self.tenant, name="Sub")
        sub_proc = Processes.objects.create(tenant=self.tenant, name="S", part_type=self.sub,
                                            status=ProcessStatus.APPROVED)
        sub_step = Steps.objects.create(tenant=self.tenant, part_type=self.sub, name="Turn",
                                        step_type="TASK", work_center=self.wc, scrap_rate=Decimal("0.5"))
        ProcessStep.objects.create(process=sub_proc, step=sub_step, order=1)

        def bom(pt):
            return BOM.objects.create(tenant=self.tenant, part_type=pt, revision="A",
                                      bom_type="ASSEMBLY", status="RELEASED", is_current_version=True)
        top = bom(self.pt)
        BOMLine.objects.create(tenant=self.tenant, bom=top, material=self.oring,
                               quantity=Decimal(2), source="BUY", line_number=1)
        BOMLine.objects.create(tenant=self.tenant, bom=top, component_type=self.sub,
                               quantity=Decimal(1), source="MAKE", line_number=2)
        BOMLine.objects.create(tenant=self.tenant, bom=bom(self.sub), material=self.rod,
                               quantity=Decimal(3), source="BUY", line_number=1)

    def _materials(self, qty, due):
        from Tracker.models import OrderLine, Orders
        order = Orders.objects.create(tenant=self.tenant, name="Demand")
        OrderLine.objects.create(tenant=self.tenant, order=order, line_number=1,
                                 part_type=self.pt, quantity=qty, due_date=due)
        out = rccp.build_capacity_load(self.tenant, months=24)
        return {m["name"]: m["series"] for m in out["materials"]}

    def test_bom_explodes_through_make_lines_with_yield(self):
        mats = self._materials(4, timezone.now().date() + timedelta(days=60))
        self.assertAlmostEqual(sum(b["demand"] for b in mats["O-Ring"]), 8.0)   # 4 × 2
        # 4 Sub needed at 50 % yield → start 8 → 8 × 3 rods.
        self.assertAlmostEqual(sum(b["demand"] for b in mats["Rod"]), 24.0)

    def test_line_demand_is_firm_and_lands_at_the_planned_start(self):
        mats = self._materials(4, timezone.now().date() + timedelta(days=300))
        series = mats["O-Ring"]
        self.assertEqual(series[0]["demand"], 0.0, "a line due next year needs no parts today")
        loaded = [b for b in series if b["demand"]]
        self.assertEqual(len(loaded), 1, "material lands in the start bucket, not spread")
        self.assertEqual(loaded[0]["demand_by_band"], {"firm": 8.0})


class MaterialOutlookExportTests(_RccpFixture, TestCase):
    """The buyer's spread: one row per item, keyed as the ERP keys it, demand per month
    in stock units with the purchase unit and its conversion beside it — no rounding to
    packs, since buying (and lot sizing) is the ERP's."""

    def setUp(self):
        super().setUp()
        from decimal import Decimal
        from Tracker.models import BOM, BOMLine, Material, OrderLine, Orders
        self.oring = Material.objects.create(
            tenant=self.tenant, name="O-Ring", part_number="OR-7", unit_of_measure="EA",
            purchase_unit="BOX", units_per_purchase_unit=Decimal("250"), safety_stock=Decimal("5"))
        bom = BOM.objects.create(tenant=self.tenant, part_type=self.pt, revision="A",
                                 bom_type="ASSEMBLY", status="RELEASED", is_current_version=True)
        BOMLine.objects.create(tenant=self.tenant, bom=bom, material=self.oring,
                               quantity=Decimal(3), source="BUY", line_number=1)
        order = Orders.objects.create(tenant=self.tenant, name="Demand")
        OrderLine.objects.create(tenant=self.tenant, order=order, line_number=1, part_type=self.pt,
                                 quantity=7, due_date=timezone.now().date() + timedelta(days=90))

    def _client(self, *perms):
        from django.contrib.auth.models import Permission
        from rest_framework.test import APIClient
        from Tracker.models import TenantGroup, UserRole
        g = TenantGroup.objects.create(tenant=self.tenant, name="g-export", is_custom=True)
        g.permissions.add(*Permission.objects.filter(codename__in=[*perms, "full_tenant_access"]))
        UserRole.objects.create(user=self.user, group=g)
        c = APIClient()
        c.force_authenticate(user=self.user)
        c.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        return c

    def test_material_rows_carry_the_erp_key_and_buying_units(self):
        m = rccp.build_capacity_load(self.tenant, months=6)["materials"][0]
        self.assertEqual((m["part_number"], m["unit_of_measure"], m["purchase_unit"],
                          m["units_per_purchase_unit"]), ("OR-7", "EA", "BOX", 250.0))
        self.assertEqual((m["on_hand"], m["incoming"]), (0.0, 0.0))

    def test_export_is_a_monthly_spread_in_stock_units(self):
        import csv
        import io
        r = self._client("view_scheduleresult", "export_data").get(
            "/api/Schedules/material-outlook/export/csv/?months=24")
        self.assertEqual(r.status_code, 200, r.content[:300])
        rows = list(csv.DictReader(io.StringIO(r.content.decode("utf-8-sig"))))
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual((row["Item"], row["Stock unit"], row["Purchase unit"],
                          row["Stock units per purchase unit"]), ("OR-7", "EA", "Box", "250.0"))
        month_cols = [k for k in row if len(k) == 7 and k[4] == "-"]
        self.assertEqual(len(month_cols), 24)
        # 7 units × 3, unrounded to boxes; the balance nets safety stock.
        self.assertEqual(sum(float(row[k] or 0) for k in month_cols), 21.0)
        self.assertEqual(float(row["Total demand"]), 21.0)
        self.assertEqual(float(row["Balance at end"]), -26.0)

    # --- when to act: first short month and order-by -------------------------

    def _row(self):
        return rccp.build_capacity_load(self.tenant, months=12)["materials"][0]

    def _stock(self, qty):
        from datetime import date
        from decimal import Decimal
        from Tracker.models import MaterialLot
        MaterialLot.objects.create(
            tenant=self.tenant, lot_number=f"LOT-{qty}", material=self.oring,
            received_date=date.today(), received_by=self.user, quantity=Decimal(qty),
            quantity_remaining=Decimal(qty), unit_of_measure="EA", status="ACCEPTED")

    def _first_of(self, label):
        from datetime import date
        y, m = map(int, label.split("-"))
        return date(y, m, 1)

    def test_order_by_is_the_first_short_month_less_the_lead_time(self):
        # 5 + 21 needed against 10: the balance goes short when the line's parts land.
        self._stock(10)
        self.oring.purchase_lead_time_days = 20
        self.oring.save(update_fields=["purchase_lead_time_days"])
        row = self._row()
        short = next(b["bucket"] for b in row["series"] if b["short"])
        self.assertEqual(row["first_short_month"], short)
        self.assertEqual(row["lead_time_days"], 20)
        self.assertEqual(row["order_by"], self._first_of(short) - timedelta(days=20))
        self.assertEqual(row["order_by_late"], row["order_by"] < timezone.localdate())

    def test_never_short_leaves_order_by_blank(self):
        self._stock(1000)
        row = self._row()
        self.assertIsNone(row["first_short_month"])
        self.assertIsNone(row["order_by"])
        self.assertFalse(row["order_by_late"])

    def test_no_lead_time_orders_by_the_first_short_month(self):
        self._stock(10)
        row = self._row()
        self.assertIsNone(row["lead_time_days"])
        self.assertEqual(row["order_by"], self._first_of(row["first_short_month"]))

    def test_export_carries_when_to_act_before_the_months(self):
        import csv
        import io
        self.oring.purchase_lead_time_days = 400   # certainly already late
        self.oring.save(update_fields=["purchase_lead_time_days"])
        r = self._client("view_scheduleresult", "export_data").get(
            "/api/Schedules/material-outlook/export/csv/?months=12")
        reader = csv.DictReader(io.StringIO(r.content.decode("utf-8-sig")))
        cols = reader.fieldnames
        self.assertEqual(cols[cols.index("Incoming") + 1:cols.index("Incoming") + 5],
                         ["Lead time (days)", "First short month", "Order by", "Late"])
        row = next(reader)
        self.assertEqual((row["Lead time (days)"], row["Late"]), ("400", "Late"))
        self.assertTrue(row["Order by"])

    def test_export_sits_behind_export_data(self):
        r = self._client("view_scheduleresult").get(
            "/api/Schedules/material-outlook/export/csv/")
        self.assertEqual(r.status_code, 403)


class RccpCriticalResourceTests(_RccpFixture, TestCase):
    """`critical_only` is a lens, not a different calculation.

    RCCP is textbook-defined over critical resources only, and a forty-centre plant
    buries the six that matter among the rest. The risk in a filter like this is that
    it quietly becomes a second answer — hide a centre and the shop looks feasible.
    These tests pin the opposite: the same row carries the same numbers either way,
    and the lanes a filter has no business touching don't move.
    """

    def setUp(self):
        super().setUp()
        # A second centre carrying no work: the kind of row the filter exists to hide.
        self.quiet = WorkCenter.objects.create(
            tenant=self.tenant, name="Cell B", code="B")

    def _names(self, **kw):
        return [w["name"] for w in
                rccp.build_capacity_load(self.tenant, months=2, **kw)["work_centers"]]

    def test_unfiltered_view_shows_every_centre(self):
        self.assertEqual(sorted(self._names()), ["Cell A", "Cell B"])

    def test_critical_only_keeps_just_the_flagged_centres(self):
        WorkCenter.objects.filter(pk=self.wc.pk).update(is_critical=True)
        self.assertEqual(self._names(critical_only=True), ["Cell A"])

    def test_filter_does_not_change_the_numbers_on_a_kept_row(self):
        """The whole point. A filtered heatmap that reported different load would be a
        second, quieter answer to the same question."""
        today = timezone.now().date()
        self._wo(10, due=today + timedelta(days=5), start=today)
        WorkCenter.objects.filter(pk=self.wc.pk).update(is_critical=True)

        full = next(w for w in rccp.build_capacity_load(self.tenant, months=2)
                    ["work_centers"] if w["name"] == "Cell A")
        filtered = rccp.build_capacity_load(
            self.tenant, months=2, critical_only=True)["work_centers"][0]
        self.assertEqual(filtered["series"], full["series"])

    def test_labor_and_totals_are_untouched_by_the_filter(self):
        """Labor is not a work centre and never hides; `work_center_total` has to keep
        counting the centres the filter dropped, or a narrowed view is
        indistinguishable from a two-centre shop."""
        today = timezone.now().date()
        self._wo(10, due=today + timedelta(days=5), start=today)
        WorkCenter.objects.filter(pk=self.wc.pk).update(is_critical=True)

        full = rccp.build_capacity_load(self.tenant, months=2)
        filtered = rccp.build_capacity_load(self.tenant, months=2, critical_only=True)
        self.assertEqual(filtered["labor"]["series"], full["labor"]["series"])
        self.assertEqual(filtered["work_center_total"], 2)
        self.assertTrue(filtered["critical_only"])

    def test_no_flagged_centre_yields_an_empty_lane_rather_than_everything(self):
        """Empty is the honest answer to "show me what I said matters" when nothing is
        flagged. Falling back to every centre would make the toggle look broken."""
        self.assertEqual(self._names(critical_only=True), [])

    def test_flag_is_reported_on_every_row_so_the_unfiltered_view_can_mark_them(self):
        WorkCenter.objects.filter(pk=self.wc.pk).update(is_critical=True)
        rows = {w["name"]: w["is_critical"]
                for w in rccp.build_capacity_load(self.tenant, months=2)["work_centers"]}
        self.assertEqual(rows, {"Cell A": True, "Cell B": False})

    def test_the_flag_is_reachable_over_the_api(self):
        """A flag that ships on the model and nowhere else is a setting that does
        nothing — the exact failure the bottleneck flag had before it was serialized."""
        from Tracker.serializers.mes_standard import WorkCenterSerializer

        self.assertIn('is_critical', WorkCenterSerializer.Meta.fields)
        ser = WorkCenterSerializer(self.wc, data={'is_critical': True}, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        self.assertEqual(
            rccp.build_capacity_load(self.tenant, months=2,
                                     critical_only=True)["work_centers"][0]["name"],
            "Cell A")

    def test_watching_a_centre_does_not_fork_a_work_centre_version(self):
        """Narrowing a view is not a configuration change. Versioning the work centre
        every time a planner adjusts what they look at would bury real engineering
        history under screen preferences."""
        from Tracker.serializers.mes_standard import WorkCenterSerializer

        before = self.wc.version
        ser = WorkCenterSerializer(self.wc, data={'is_critical': True}, partial=True)
        ser.is_valid(raise_exception=True)
        saved = ser.save()
        self.assertEqual(saved.version, before)
        self.assertTrue(saved.is_critical)
