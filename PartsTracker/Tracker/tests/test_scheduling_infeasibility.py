"""An INFEASIBLE solve has to explain itself.

Every lot-op's start and end are bounded by the horizon, so all admitted work must
finish inside the window. Ask for more hours than the window holds and CP-SAT returns
INFEASIBLE — no plan, and no reason. The planner then sees an empty board with nothing
to act on, which is worse than a bad plan.

Until deferral lets the solver spill work out of the window, the guard at least names
the resource that overflowed. These tests pin that it fires on a genuinely overloaded
window, stays quiet on a healthy one, and never itself breaks a solve.
"""
from datetime import time as dtime, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from Tracker.models import (
    Equipments, OptimizationConfig, Parts, PartTypes, Processes, ProcessStep, Shift,
    StepEquipmentAffinity, Steps, StepTiming, Tenant, WorkCenter, WorkOrder,
    WorkOrderStatus,
)
from Tracker.services.scheduling.solver import solve_schedule
from Tracker.tests.base import TenantContextMixin


class InfeasibilityGuardTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="IF", slug="infeasible", tier="PRO")
        self.set_tenant_context(self.tenant)
        get_user_model().objects.create_user(
            username="if-op", email="if@c.test", password="x", tenant=self.tenant,
            default_shift=Shift.objects.create(
                tenant=self.tenant, code="DAY", name="Day", start_time=dtime(8, 0),
                end_time=dtime(16, 0), days_of_week="0,1,2,3,4", is_active=True))
        # A 3-day window on one attended machine over one 8h shift: ~24h of capacity.
        self.config = OptimizationConfig.objects.create(tenant=self.tenant, horizon_days=3)
        self.wc = WorkCenter.objects.create(tenant=self.tenant, name="Cell A", code="A")
        self.machine = Equipments.objects.create(
            tenant=self.tenant, name="M-1", is_schedulable=True, runs_unattended=False)
        self.wc.equipment.add(self.machine)
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Widget")
        self.process = Processes.objects.create(
            tenant=self.tenant, name="W", part_type=self.pt)
        self.step = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Cut", step_type="TASK",
            work_center=self.wc)
        # 2h per unit. Deliberately NOT a full shift's worth: attended time is padded
        # by the 15% PFD allowance, so an 8h op can never fit an 8h shift window and
        # every solve would be infeasible for a reason that has nothing to do with
        # aggregate capacity — which would make the healthy-case test meaningless.
        self.timing = StepTiming.objects.create(
            tenant=self.tenant, step=self.step, cycle_time_minutes=120)
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=self.step, equipment=self.machine,
            affinity=StepEquipmentAffinity.Affinity.PREFERRED)
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)

    def _orders(self, n):
        """`n` separate single-unit work orders — separate so they can't batch into
        one lot and must each occupy the machine in turn."""
        for i in range(n):
            wo = WorkOrder.objects.create(
                tenant=self.tenant, ERP_id=f"OL-{i}",
                workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=1,
                process=self.process,
                expected_completion=timezone.localdate() + timedelta(days=2))
            Parts.objects.create(tenant=self.tenant, ERP_id=f"OL-{i}-P",
                                 part_type=self.pt, work_order=wo, step=self.step)

    def test_an_overloaded_window_explains_itself(self):
        """30 × 2h onto one machine in a ~24h window. The result is still INFEASIBLE —
        the guard doesn't fix that — but it must say why, and name the resource."""
        self._orders(30)
        result = solve_schedule(self.tenant, time_limit_seconds=15)

        self.assertEqual(result.solver_status, "INFEASIBLE")
        self.assertEqual(result.tasks.count(), 0)
        self.assertTrue(result.infeasible_reason,
                        "an empty board with no explanation is the failure mode this "
                        "guard exists to prevent")
        self.assertIn("window", result.infeasible_reason.lower())
        # Names a specific short resource, not just "something went wrong".
        self.assertTrue(
            "Cell A" in result.infeasible_reason
            or "Labor" in result.infeasible_reason,
            result.infeasible_reason)

    def test_a_feasible_solve_records_no_reason(self):
        """The field is a failure explanation — a healthy plan must leave it blank, or
        the board would show a scary message over a perfectly good schedule."""
        self._orders(1)
        result = solve_schedule(self.tenant, time_limit_seconds=15)
        self.assertIn(result.solver_status, ("OPTIMAL", "FEASIBLE"))
        self.assertEqual(result.infeasible_reason, "")

    def test_the_diagnosis_reports_the_capacity_figures(self):
        from Tracker.services.scheduling.data import get_schedule_horizon
        from Tracker.services.scheduling.infeasibility import diagnose_infeasible

        self._orders(30)
        d = diagnose_infeasible(self.tenant, get_schedule_horizon(self.tenant))
        self.assertEqual(d['cause'], 'overload')
        worst = d['resources'][0]
        self.assertGreater(worst['required_hours'], worst['available_hours'])
        self.assertGreater(worst['overload_hours'], 0)

    def test_an_unexplained_infeasibility_says_so_rather_than_guessing(self):
        """No resource over capacity ⇒ don't blame capacity. A planner would act on a
        wrong reason, so 'unknown' with a list of things to check beats a confident
        fiction."""
        from Tracker.services.scheduling.data import get_schedule_horizon
        from Tracker.services.scheduling.infeasibility import diagnose_infeasible

        self._orders(1)  # trivially fits
        d = diagnose_infeasible(self.tenant, get_schedule_horizon(self.tenant))
        self.assertEqual(d['cause'], 'unknown')
        self.assertIn("no resource is obviously over capacity", d['summary'])

    def test_a_broken_diagnosis_never_breaks_the_solve(self):
        """The guard is advisory. If it raises, the schedule must still be written —
        losing a plan to a failed explanation would be a self-inflicted outage."""
        from unittest.mock import patch

        self._orders(30)
        with patch("Tracker.services.scheduling.infeasibility.diagnose_infeasible",
                   side_effect=RuntimeError("boom")):
            result = solve_schedule(self.tenant, time_limit_seconds=15)
        self.assertEqual(result.solver_status, "INFEASIBLE")
        self.assertEqual(result.infeasible_reason, "")
