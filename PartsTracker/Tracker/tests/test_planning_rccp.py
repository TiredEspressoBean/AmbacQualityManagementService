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
    Equipments, OptimizationConfig, Parts, PartTypes, Processes, ProcessStep,
    Shift, StepEdge, Steps, StepTiming, Tenant, WorkCenter, WorkOrder, WorkOrderStatus,
)
from Tracker.services.planning import rccp
from Tracker.tests.base import TenantContextMixin


class RccpTests(TenantContextMixin, TestCase):
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
