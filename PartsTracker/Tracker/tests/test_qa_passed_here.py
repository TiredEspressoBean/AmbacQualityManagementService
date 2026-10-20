"""A sampled part needs QA until it passes *at its current step* (seed walk, 2026-10-20).

Every reader asked "has this part ever had a PASS report?", so a part walked through the
line with a pass at Machining never needed QA at Nozzle Inspection and never reached the
inspector's queue (services/qms/qa_status.py).
"""
import datetime

from django.utils import timezone

from Tracker.models import Parts, PartTypes, QualityReports, StepExecution, Steps, WorkOrder
from Tracker.services.qms.inspection_inbox import build_inbox_rows
from Tracker.tests.base import TenantTestCase


class QaPassedHereTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Injector")
        self.machining = Steps.objects.create(tenant=self.tenant_a, name="Machining", part_type=pt)
        self.nozzle = Steps.objects.create(tenant=self.tenant_a, name="Nozzle Inspection", part_type=pt)
        wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id="WO-QAH-1", quantity=1)
        self.part = Parts.objects.create(tenant=self.tenant_a, ERP_id="QAH-1", part_type=pt,
                                         work_order=wo, step=self.nozzle, part_status="IN_PROGRESS")
        Parts.objects.filter(pk=self.part.pk).update(requires_sampling=True)
        self.part.refresh_from_db()
        QualityReports.objects.create(tenant=self.tenant_a, part=self.part, step=self.machining,
                                      status="PASS", detected_by=self.user_a)
        StepExecution.objects.create(tenant=self.tenant_a, part=self.part, step=self.nozzle,
                                     visit_number=1, status="IN_PROGRESS")

    def _inbox_ops(self):
        return [r for r in build_inbox_rows() if r["type"] == "in_process"]

    def test_a_pass_at_an_earlier_step_does_not_clear_this_one(self):
        self.assertTrue(self.part.needs_qa)
        self.assertEqual(len(self._inbox_ops()), 1)

    def test_a_pass_here_this_visit_clears_it(self):
        QualityReports.objects.create(tenant=self.tenant_a, part=self.part, step=self.nozzle,
                                      status="PASS", detected_by=self.user_a)
        self.assertFalse(self.part.needs_qa)
        self.assertTrue(self.part.qa_completed)
        self.assertEqual(self._inbox_ops(), [])

    def test_a_pass_from_an_earlier_visit_here_does_not_count(self):
        old = QualityReports.objects.create(tenant=self.tenant_a, part=self.part, step=self.nozzle,
                                            status="PASS", detected_by=self.user_a)
        QualityReports.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - datetime.timedelta(days=2))
        self.assertTrue(self.part.needs_qa)

    def test_the_parts_filter_agrees(self):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, ['view_parts', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        ids = [r["id"] for r in self.client.get("/api/Parts/", {"needs_qa": "true"}).json()["results"]]
        self.assertIn(str(self.part.id), ids)
