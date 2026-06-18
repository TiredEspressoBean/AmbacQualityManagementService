"""4c — live per-step part distribution endpoint for the flow-map overlay.

`GET /api/WorkOrders/{id}/step_metrics/` groups live parts by step and reports
total + attention buckets (in_rework / quarantined / awaiting_qa), excluding
terminal parts.
"""
from Tracker.models import (
    PartTypes,
    Parts,
    PartsStatus,
    Processes,
    ProcessStep,
    Steps,
    WorkOrder,
    WorkOrderStatus,
)
from Tracker.tests.base import TenantTestCase


class StepMetricsTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        t = self.tenant_a
        self.part_type = PartTypes.objects.create(tenant=t, name="Widget")
        self.process = Processes.objects.create(tenant=t, name="P", part_type=self.part_type)
        self.step1 = Steps.objects.create(tenant=t, part_type=self.part_type, name="Machining", step_type="TASK")
        self.step2 = Steps.objects.create(tenant=t, part_type=self.part_type, name="Inspect", step_type="TASK")
        ProcessStep.objects.create(process=self.process, step=self.step1, order=1)
        ProcessStep.objects.create(process=self.process, step=self.step2, order=2)
        self.wo = WorkOrder.objects.create(
            tenant=t, ERP_id="WO-SM-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=6, process=self.process,
        )

        def mk(erp, step, status):
            return Parts.objects.create(
                tenant=t, ERP_id=erp, part_type=self.part_type,
                work_order=self.wo, step=step, part_status=status,
            )

        # step1: 2 in progress, 1 quarantined, 1 in rework, 1 scrapped (excluded)
        mk("P1", self.step1, PartsStatus.IN_PROGRESS)
        mk("P2", self.step1, PartsStatus.IN_PROGRESS)
        mk("P3", self.step1, PartsStatus.QUARANTINED)
        mk("P4", self.step1, PartsStatus.REWORK_IN_PROGRESS)
        mk("P5", self.step1, PartsStatus.SCRAPPED)  # terminal → excluded
        # step2: 1 awaiting QA
        mk("P6", self.step2, PartsStatus.AWAITING_QA)

    def test_step_metrics_groups_and_buckets(self):
        self.authenticate_superuser(tenant=self.tenant_a)
        resp = self.client.get(f"/api/WorkOrders/{self.wo.id}/step_metrics/")
        self.assertEqual(resp.status_code, 200)
        by_id = {s["step_id"]: s for s in resp.json()["steps"]}

        s1 = by_id[str(self.step1.id)]
        self.assertEqual(s1["total"], 4)  # 2 IP + 1 quarantined + 1 rework; scrapped excluded
        self.assertEqual(s1["quarantined"], 1)
        self.assertEqual(s1["in_rework"], 1)
        self.assertEqual(s1["awaiting_qa"], 0)

        s2 = by_id[str(self.step2.id)]
        self.assertEqual(s2["total"], 1)
        self.assertEqual(s2["awaiting_qa"], 1)

    def test_terminal_only_step_absent(self):
        # A step whose only parts are terminal shouldn't appear at all.
        self.authenticate_superuser(tenant=self.tenant_a)
        resp = self.client.get(f"/api/WorkOrders/{self.wo.id}/step_metrics/")
        ids = {s["step_id"] for s in resp.json()["steps"]}
        # Both live steps present; no phantom entries.
        self.assertEqual(ids, {str(self.step1.id), str(self.step2.id)})
