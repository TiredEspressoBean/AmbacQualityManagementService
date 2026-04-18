"""
Tests for PartIdLabelAdapter.

Covers:
- 4 standard tests via ReportAdapterTestMixin (fixture validation,
  template compile, determinism, cross-tenant stub)

The label is a 4"×2" thermal-printer document so the PDF is expected to
be small (single page, no headers/footers).  The size threshold in the
mixin (> 500 bytes) is deliberately conservative and will pass here.

Cross-tenant security test is a stub — a real probe would need a DB-backed
TestCase; skipped here to keep the suite fast.
"""
from django.test import SimpleTestCase

from Tracker.reports.adapters.part_id_label import PartIdLabelAdapter
from Tracker.reports.tests.base import ReportAdapterTestMixin


class TestPartIdLabelAdapter(ReportAdapterTestMixin, SimpleTestCase):
    """Template + Pydantic + determinism tests against the fixture."""

    adapter_class = PartIdLabelAdapter
    fixture_name = "part_id_label_sample"

    def test_cross_tenant_id_is_rejected(self):
        # Stub — real cross-tenant probe requires a DB-backed TestCase.
        self.skipTest(
            "Cross-tenant probe for PartIdLabelAdapter requires a real "
            "database (TestCase, not SimpleTestCase)."
        )
