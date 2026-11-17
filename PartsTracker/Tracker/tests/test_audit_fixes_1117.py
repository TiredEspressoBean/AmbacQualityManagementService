"""Doc-audit fixes, user's go 2026-11-17 — one rule each, not more branches.

1. ncr.opened carries the NCR's real severity (the worst defect), not PASS/FAIL.
2. Reassigning a CAPA task notifies the new assignee (it only ever did on creation).
3. A document can't be classified above what the person classifying it can view.
4. A reserved harvested part can be released — the refusal pointed at a release that
   had no endpoint.
6. ITAR access is the user's us_person flag; a dead `itar_authorized` check is gone.
"""
from datetime import date
from unittest import mock

from django.contrib.auth import get_user_model
from rest_framework.exceptions import PermissionDenied

from Tracker.tests.base import TenantTestCase


class NcrSeverityTests(TenantTestCase):
    def test_severity_is_the_worst_defect_not_the_status(self):
        from Tracker.models import QualityErrorsList, QualityReportDefect, QualityReports
        from Tracker.services.qms.quality_report import report_severity
        report = QualityReports.objects.create(tenant=self.tenant_a, status="PASS",
                                               detected_by=self.user_a)
        self.assertEqual(report_severity(report), "MAJOR")   # none recorded
        err = QualityErrorsList.objects.create(tenant=self.tenant_a, error_name="Burr")
        for sev in ("MINOR", "CRITICAL", "MAJOR"):
            QualityReportDefect.objects.create(report=report, error_type=err, severity=sev)
        self.assertEqual(report_severity(report), "CRITICAL")


class CapaTaskReassignmentTests(TenantTestCase):
    def test_reassigning_a_task_notifies_the_new_assignee_once(self):
        from Tracker.models import CAPA, CapaTasks
        other = get_user_model().objects.create_user(
            username="capa-b", email="capab@t.test", password="x", tenant=self.tenant_a)
        capa = CAPA.objects.create(tenant=self.tenant_a, capa_type="CORRECTIVE", severity="MINOR",
                                   problem_statement="Burr on bore", initiated_by=self.user_a)
        with mock.patch("Tracker.tasks.send_capa_task_assignment_notification.delay") as send:
            with self.captureOnCommitCallbacks(execute=True):
                task = CapaTasks.objects.create(tenant=self.tenant_a, capa=capa, task_type="CORRECTIVE",
                                                description="Deburr", assigned_to=self.user_a)
            self.assertEqual(send.call_count, 1)            # created
            with self.captureOnCommitCallbacks(execute=True):
                task.assigned_to = other
                task.save()
            self.assertEqual(send.call_count, 2)            # reassigned
            with self.captureOnCommitCallbacks(execute=True):
                task.description = "Deburr and re-measure"
                task.save()
            self.assertEqual(send.call_count, 2)            # same assignee: no notice


class ClassifyAboveViewTests(TenantTestCase):
    def test_a_classification_you_couldnt_view_is_refused(self):
        from Tracker.services.export_control import ExportControlService
        self.grant_tenant_permissions(self.user_a, self.tenant_a, ["view_documents"])
        with self.assertRaisesMessage(PermissionDenied,
                                      "You can't classify a document above what you can view."):
            ExportControlService.assert_can_classify(self.user_a, "SECRET")
        ExportControlService.assert_can_classify(self.user_a, "PUBLIC")   # fine

    def test_upload_applies_it(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            "view_documents", "add_documents", "full_tenant_access"])
        self.authenticate_as(self.user_a, self.tenant_a)
        r = self.client.post("/api/Documents/", {
            "file": SimpleUploadedFile("spec.pdf", b"%PDF-1.4 test"), "file_name": "spec.pdf",
            "classification": "SECRET"}, format="multipart")
        self.assertEqual(r.status_code, 403, r.content)
        self.assertIn("above what you can view", str(r.content))


class ReleaseReservationTests(TenantTestCase):
    def test_a_reserved_part_is_released_by_whoever_may_reserve(self):
        from Tracker.models import Parts, PartTypes
        from Tracker.services.reman.core_part import create_core
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Injector")
        owner = create_core(tenant=self.tenant_a, core_number="OWNER-R1", core_type=pt,
                            fulfilment_mode="REPAIR_RETURN", status="DISASSEMBLED",
                            received_date=date.today(), received_by=self.user_a)
        part = Parts.objects.create(tenant=self.tenant_a, ERP_id="NOZ-R1", part_type=pt,
                                    reserved_for_core=owner)
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            "view_parts", "change_parts", "full_tenant_access"])
        self.authenticate_as(self.user_a, self.tenant_a)
        r = self.client.post(f"/api/Parts/{part.id}/release_reservation/", {}, format="json")
        self.assertEqual(r.status_code, 403, r.content)     # can't reserve, can't release
        reserver = get_user_model().objects.create_user(
            username="res-b", email="resb@t.test", password="x", tenant=self.tenant_a)
        self.grant_tenant_permissions(reserver, self.tenant_a, [
            "view_parts", "change_parts", "accept_component", "full_tenant_access"])
        self.authenticate_as(reserver, self.tenant_a)
        r = self.client.post(f"/api/Parts/{part.id}/release_reservation/", {}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        part.refresh_from_db()
        self.assertIsNone(part.reserved_for_core_id)


class ItarIsUsPersonTests(TenantTestCase):
    def test_only_the_us_person_flag_grants_itar(self):
        from Tracker.services.export_control import ExportControlService
        self.user_a.us_person = False
        self.user_a.itar_authorized = True   # not a field; must not grant anything
        self.assertFalse(ExportControlService.can_access_itar_data(self.user_a)[0])
        self.user_a.us_person = True
        self.assertTrue(ExportControlService.can_access_itar_data(self.user_a)[0])
