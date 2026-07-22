"""Tests for ScarReportAdapter — 4 standard tests via ReportAdapterTestMixin."""
from django.test import SimpleTestCase

from Tracker.reports.adapters.scar import ScarReportAdapter
from Tracker.reports.tests.base import ReportAdapterTestMixin


class TestScarReportAdapter(ReportAdapterTestMixin, SimpleTestCase):
    """Fixture validation + template compile + determinism against the fixture."""
    adapter_class = ScarReportAdapter
    fixture_name = "scar_sample"

    def test_cross_tenant_id_is_rejected(self):
        self.skipTest(
            "Cross-tenant isolation is enforced by the tenant filter in "
            "ScarParamsSerializer.validate_id() (the CAPA lookup) and the ORM "
            "query in build_context(). Full probe requires DB state - see "
            "integration tests."
        )
