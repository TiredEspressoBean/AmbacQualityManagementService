"""The FAIL-QR auto-disposition signal creates at most one disposition per
report, and does not resurrect a fresh one after the first is CLOSED.

`auto_create_disposition` (Tracker/signals.py) opens a disposition when a
part QR is saved FAIL. Its dedup guard used to check only
`current_state IN (OPEN, IN_PROGRESS)`, so re-saving a still-FAIL QR whose
disposition had since been CLOSED re-fired the signal and minted a second,
orphan bare NCR — a source of the double-disposition seen on some exhibits.
The guard now checks whether the report already produced *any* disposition
(there is no CANCELLED state to justify re-opening).
"""
from django.contrib.auth import get_user_model

from Tracker.models import (
    PartTypes, Parts, ProcessStep, Processes, QualityReports,
    QuarantineDisposition, Steps, Tenant, WorkOrder, WorkOrderStatus,
)
from Tracker.tests.base import TenantContextMixin, VectorTestCase


class AutoDispositionNoDuplicateTests(TenantContextMixin, VectorTestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(
            name="Auto Disp", slug="auto-disp", tier="PRO")
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        self.qa = User.objects.create_user(
            username="ad-qa", email="qa@ad.test", password="x", tenant=self.tenant)
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="W")
        self.process = Processes.objects.create(
            tenant=self.tenant, name="P", part_type=self.pt)
        self.step = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Flow", step_type="TASK")
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-AD-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=1, process=self.process)
        self.part = Parts.objects.create(
            tenant=self.tenant, ERP_id="P-AD-1", part_type=self.pt,
            work_order=self.wo, step=self.step)

    def _fail_qr(self):
        # detected_by gives the signal an assignee fallback (no QA groups here).
        return QualityReports.objects.create(
            tenant=self.tenant, part=self.part, step=self.step,
            status='FAIL', description='out of spec', detected_by=self.qa)

    def _disp_count(self, qr):
        return QuarantineDisposition.objects.filter(quality_reports=qr).count()

    def test_one_auto_disposition_per_fail_qr(self):
        qr = self._fail_qr()
        self.assertEqual(self._disp_count(qr), 1,
                         'a FAIL QR auto-creates exactly one disposition')

    def test_resaving_closed_fail_qr_does_not_duplicate(self):
        """The bug this guards: closing the auto-disposition and re-saving the
        still-FAIL QR must NOT resurrect a second one."""
        qr = self._fail_qr()
        disp = QuarantineDisposition.objects.get(quality_reports=qr)
        disp.current_state = 'CLOSED'
        disp.save()
        # Any later edit of the still-FAIL report re-fires post_save.
        qr.description = 'out of spec (annotated)'
        qr.save()
        self.assertEqual(self._disp_count(qr), 1,
                         'a re-saved FAIL QR with a CLOSED disposition must not '
                         'resurrect a second auto-disposition')

    def test_resaving_open_fail_qr_does_not_duplicate(self):
        """Sanity: the original OPEN-state dedup still holds too."""
        qr = self._fail_qr()
        qr.description = 'edited while open'
        qr.save()
        self.assertEqual(self._disp_count(qr), 1)
