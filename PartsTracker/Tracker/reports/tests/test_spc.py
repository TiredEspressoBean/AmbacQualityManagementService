"""Tests for SpcAdapter — 4 standard tests via ReportAdapterTestMixin."""
from django.test import SimpleTestCase

from Tracker.reports.adapters.spc import SpcAdapter
from Tracker.reports.tests.base import ReportAdapterTestMixin


class TestSpcAdapter(ReportAdapterTestMixin, SimpleTestCase):
    """Fixture validation + template compile + determinism against the fixture."""
    adapter_class = SpcAdapter
    fixture_name = "spc_sample"

    def test_cross_tenant_id_is_rejected(self):
        self.skipTest(
            "Cross-tenant isolation is enforced by the tenant filter in "
            "SpcReportParamsSerializer.validate_measurement_id() and the ORM "
            "queries in build_context(). Full probe requires DB state — see "
            "integration tests."
        )
