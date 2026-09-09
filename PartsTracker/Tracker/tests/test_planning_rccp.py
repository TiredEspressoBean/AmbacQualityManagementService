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
    Companies, Equipments, OptimizationConfig, Parts, PartTypes, Processes, ProcessStep,
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
        self.process = Processes.objects.create(
            tenant=self.tenant, name="W", part_type=self.pt)
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

    def test_lights_out_machine_gets_calendar_hours(self):
        """A lights-out machine's capacity is wall-clock, an attended one's is shift
        hours — the runs_unattended resolution the scheduler uses."""
        before = next(w for w in rccp.build_capacity_load(self.tenant, months=1)["work_centers"]
                      if w["name"] == "Cell A")["series"][0]["capacity_hours"]
        Equipments.objects.filter(pk=self.machine.pk).update(runs_unattended=True)
        after = next(w for w in rccp.build_capacity_load(self.tenant, months=1)["work_centers"]
                     if w["name"] == "Cell A")["series"][0]["capacity_hours"]
        self.assertGreater(after, before)

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
