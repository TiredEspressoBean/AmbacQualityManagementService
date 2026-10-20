"""Batch 1 of the seed-arc findings (2026-10-20): quality records that were corrupted or hidden.

1. A report edited to FAIL opened a disposition (post_save signal) but never
   quarantined the part — the FAIL consequences ran only on create.
2. Quarantines written in bulk (quality-gate hold, failed batch cycle) left no audit
   entry on the parts.
3. A PATCH changing disposition_type answered 200 with the type unchanged.
"""
from types import SimpleNamespace

from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType

from Tracker.models import (
    Parts, PartTypes, QualityReports, QuarantineDisposition, Steps, WorkOrder,
)
from Tracker.services.qms.quality_report import on_report_failed
from Tracker.tests.base import TenantTestCase


class _Fixture(TenantTestCase):
    def setUp(self):
        super().setUp()
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Injector")
        self.step = Steps.objects.create(tenant=self.tenant_a, name="Flow test", part_type=pt)
        self.wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id="WO-QR-1", quantity=2,
                                           workorder_status="IN_PROGRESS")
        self.part = Parts.objects.create(tenant=self.tenant_a, ERP_id="QR-1", part_type=pt,
                                         work_order=self.wo, step=self.step, part_status="IN_PROGRESS")


class EditedToFailTests(_Fixture):

    def test_a_report_edited_to_fail_quarantines_and_opens_one_disposition(self):
        qr = QualityReports.objects.create(tenant=self.tenant_a, part=self.part, step=self.step,
                                           status="PENDING", detected_by=self.user_a)
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_qualityreports', 'change_qualityreports', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        resp = self.client.patch(f"/api/QualityReports/{qr.id}/", {"status": "FAIL"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.part.refresh_from_db()
        self.assertEqual(self.part.part_status, "QUARANTINED")
        self.assertEqual(QuarantineDisposition.objects.filter(quality_reports=qr).count(), 1)

    def test_only_the_transition_into_fail_reacts(self):
        qr = QualityReports.objects.create(tenant=self.tenant_a, part=self.part, step=self.step,
                                           status="FAIL", detected_by=self.user_a)
        self.assertFalse(on_report_failed(qr, "FAIL"))
        qr.status = "PASS"
        self.assertFalse(on_report_failed(qr, "PENDING"))


class QuarantineIsAuditedTests(_Fixture):

    def test_a_quality_gate_hold_writes_each_parts_history(self):
        from Tracker.services.qms.quality_gate import _hold
        _hold(SimpleNamespace(step=self.step), work_order=self.wo, material_lot=None)
        self.part.refresh_from_db()
        self.assertEqual(self.part.part_status, "QUARANTINED")
        entries = LogEntry.objects.filter(content_type=ContentType.objects.get_for_model(Parts),
                                          object_pk=str(self.part.pk))
        self.assertTrue(any("part_status" in (e.changes or {}) for e in entries))


class DispositionTypeOnEditTests(_Fixture):

    def setUp(self):
        super().setUp()
        self.disp = QuarantineDisposition.objects.create(
            tenant=self.tenant_a, part=self.part, step=self.step, assigned_to=self.user_a)
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_quarantinedisposition', 'change_quarantinedisposition', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)

    def test_changing_the_type_by_edit_is_refused_not_ignored(self):
        resp = self.client.patch(f"/api/QuarantineDispositions/{self.disp.id}/",
                                 {"disposition_type": "SCRAP"}, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("Decide", str(resp.json()))
        self.disp.refresh_from_db()
        self.assertFalse(self.disp.disposition_type)

    def test_resending_the_current_type_with_an_edit_passes(self):
        resp = self.client.patch(f"/api/QuarantineDispositions/{self.disp.id}/",
                                 {"disposition_type": self.disp.disposition_type or "",
                                  "description": "Bore oversize"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
