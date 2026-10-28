"""Defect Records exports every row matching its filters (user decision 2026-10-28):
the page loaded 100 rows and Export wrote only those."""
import csv
import io

from Tracker.models import QualityErrorsList, QualityReports
from Tracker.tests.base import TenantTestCase


class DefectRecordsExportTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        burr = QualityErrorsList.objects.create(tenant=self.tenant_a, error_name="Burr", error_example="x")
        for i in range(120):
            qr = QualityReports.objects.create(tenant=self.tenant_a, status="FAIL", description=f"r{i}")
            if i < 30:
                qr.errors.add(burr)

    def _get(self, perms, **params):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, perms + ['full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        return self.client.get("/api/dashboard/defect-records-export/", params)

    @staticmethod
    def _rows(response):
        return list(csv.reader(io.StringIO(response.content.decode('utf-8-sig'))))[1:]

    def test_every_matching_row_is_exported(self):
        r = self._get(['view_qualityreports', 'export_data'])
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(len(self._rows(r)), 120)  # beyond the table's 100

    def test_filters_apply(self):
        r = self._get(['view_qualityreports', 'export_data'], defect_type="Burr")
        self.assertEqual(len(self._rows(r)), 30)

    def test_the_table_still_pages_the_same_rows(self):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, ['view_qualityreports', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        r = self.client.get("/api/dashboard/defect-records/", {"limit": 100, "defect_type": "Burr"})
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual((r.json()["total"], len(r.json()["data"])), (30, 30))

    def test_export_data_is_required(self):
        r = self._get(['view_qualityreports'])
        self.assertEqual(r.status_code, 403, r.content)
