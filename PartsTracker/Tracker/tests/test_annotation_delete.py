"""Who can delete a 3D defect annotation.

Mid-inspection the annotator saves each marker at once, linked to the inspection's
still-PENDING quality report, so an inspector must be able to remove a mis-placed one.
Once a linked report is finished (PASS / FAIL) the annotation is evidence the
"Requires 3D Annotation" disposition gate reads, and deleting it is the quality
team's call (`delete_submitted_heatmapannotations`).
"""
from Tracker.models import HeatMapAnnotations, Parts, PartTypes, QualityReports, ThreeDModel
from Tracker.tests.base import TenantTestCase

LINE_ROLE = ['view_heatmapannotations', 'delete_heatmapannotations', 'full_tenant_access']


class AnnotationDeleteTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        part_type = PartTypes.objects.create(tenant=self.tenant_a, name="Body")
        # No file: the post-save conversion task only queues for an uploaded file.
        model = ThreeDModel.objects.create(
            tenant=self.tenant_a, name="Body", file="", part_type=part_type,
            processing_status="COMPLETED")
        self.part = Parts.objects.create(tenant=self.tenant_a, ERP_id="ANN-1", part_type=part_type)
        self.report = QualityReports.objects.create(
            tenant=self.tenant_a, part=self.part, status="PENDING", detected_by=self.user_a)
        self.annotation = HeatMapAnnotations.objects.create(
            tenant=self.tenant_a, model=model, part=self.part,
            position_x=0, position_y=0, position_z=0, defect_type="Scoring")
        self.annotation.quality_reports.add(self.report)

    def _finish_report(self):
        self.report.status = "FAIL"
        self.report.save(update_fields=["status"])

    def _delete_as(self, perms):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, perms)
        self.authenticate_as(self.user_a)
        return self.client.delete(f"/api/HeatMapAnnotation/{self.annotation.id}/")

    def _gone(self):
        return not HeatMapAnnotations.objects.filter(pk=self.annotation.pk, archived=False).exists()

    def test_mid_inspection_a_line_role_can_delete(self):
        resp = self._delete_as(LINE_ROLE)
        self.assertEqual(resp.status_code, 204, resp.content)
        self.assertTrue(self._gone())

    def test_on_a_finished_report_a_line_role_is_refused(self):
        self._finish_report()
        resp = self._delete_as(LINE_ROLE)
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertIn("quality team", resp.json()["detail"])
        self.assertFalse(self._gone())

    def test_on_a_finished_report_the_quality_team_can_delete(self):
        self._finish_report()
        resp = self._delete_as(LINE_ROLE + ['delete_submitted_heatmapannotations'])
        self.assertEqual(resp.status_code, 204, resp.content)
        self.assertTrue(self._gone())

    def test_an_annotation_on_no_report_is_a_draft(self):
        self.annotation.quality_reports.clear()
        resp = self._delete_as(LINE_ROLE)
        self.assertEqual(resp.status_code, 204, resp.content)

    def test_the_api_says_which_are_submitted(self):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, LINE_ROLE)
        self.authenticate_as(self.user_a)
        url = f"/api/HeatMapAnnotation/{self.annotation.id}/"
        self.assertFalse(self.client.get(url).json()["is_submitted"])
        self._finish_report()
        self.assertTrue(self.client.get(url).json()["is_submitted"])
