"""E7 — late-cause attribution. For a task finishing after its WO due date, tag the binding
constraint: material → uncovered operator → machine contention → late release → tight lead
time. On-time tasks get no cause."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from Tracker.models import (
    Equipments,
    Parts,
    PartTypes,
    Processes,
    ScheduledTask,
    ScheduleResult,
    Steps,
    Tenant,
    WorkOrder,
    WorkOrderStatus,
)
from Tracker.services.scheduling.late_cause import attribute_late_causes
from Tracker.tests.base import TenantContextMixin


class LateCauseTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="LC", slug="latecause", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="PT")
        self.proc = Processes.objects.create(tenant=self.tenant, name="P", part_type=self.pt)
        self.step = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name="Op")
        self.machine = Equipments.objects.create(tenant=self.tenant, name="CNC-1")
        self.now = timezone.now().replace(microsecond=0)
        self.due_past = (self.now - timedelta(days=1)).date()  # yesterday → tasks are late
        self.sched = ScheduleResult.objects.create(
            tenant=self.tenant, horizon_start=self.now, horizon_end=self.now + timedelta(days=5),
            is_active=True, is_stale=False)

    def _wo(self, erp, expected_completion=None, expected_start=None):
        return WorkOrder.objects.create(
            tenant=self.tenant, ERP_id=erp, workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=1, process=self.proc, expected_completion=expected_completion,
            expected_start=expected_start)

    def _part(self, wo, erp):
        return Parts.objects.create(tenant=self.tenant, ERP_id=erp, part_type=self.pt,
                                    work_order=wo, step=self.step)

    def _task(self, part, start, end, machine=None, requires_operator=False,
              assigned_operator=None, material_shortage=False):
        return ScheduledTask.objects.create(
            tenant=self.tenant, schedule=self.sched, part=part, step=self.step,
            machine=machine, start_time=start, end_time=end,
            requires_operator=requires_operator, assigned_operator=assigned_operator,
            material_shortage=material_shortage)

    def test_material_cause(self):
        p = self._part(self._wo("WO-M", self.due_past), "M-1")
        self._task(p, self.now, self.now + timedelta(hours=1), material_shortage=True)
        attribute_late_causes(self.sched)
        self.assertIn("Material short", ScheduledTask.objects.get(part=p).late_cause)

    def test_uncovered_cause(self):
        p = self._part(self._wo("WO-U", self.due_past), "U-1")
        self._task(p, self.now, self.now + timedelta(hours=1), requires_operator=True)
        attribute_late_causes(self.sched)
        self.assertIn("Uncovered", ScheduledTask.objects.get(part=p).late_cause)

    def test_machine_contention_cause(self):
        wo = self._wo("WO-C", self.due_past)
        pa, pb = self._part(wo, "C-1"), self._part(wo, "C-2")
        self._task(pa, self.now, self.now + timedelta(hours=1), machine=self.machine)
        # B starts 30 min after A finishes on the same machine → within the contention gap
        self._task(pb, self.now + timedelta(minutes=90), self.now + timedelta(hours=3),
                   machine=self.machine)
        attribute_late_causes(self.sched)
        self.assertIn("Machine contention", ScheduledTask.objects.get(part=pb).late_cause)

    def test_late_release_cause(self):
        future = (self.now + timedelta(days=2)).date()
        p = self._part(self._wo("WO-R", self.due_past, expected_start=future), "R-1")
        self._task(p, self.now, self.now + timedelta(hours=1))
        attribute_late_causes(self.sched)
        self.assertIn("Late release", ScheduledTask.objects.get(part=p).late_cause)

    def test_tight_lead_time_default(self):
        p = self._part(self._wo("WO-T", self.due_past), "T-1")
        self._task(p, self.now, self.now + timedelta(hours=1))  # no material/operator/machine
        attribute_late_causes(self.sched)
        self.assertIn("Tight lead time", ScheduledTask.objects.get(part=p).late_cause)

    def test_on_time_has_no_cause(self):
        due_future = (self.now + timedelta(days=3)).date()
        p = self._part(self._wo("WO-OK", due_future), "OK-1")
        self._task(p, self.now, self.now + timedelta(hours=1))
        attribute_late_causes(self.sched)
        self.assertEqual(ScheduledTask.objects.get(part=p).late_cause, "")
