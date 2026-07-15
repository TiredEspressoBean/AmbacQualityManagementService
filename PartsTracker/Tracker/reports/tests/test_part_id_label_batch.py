"""Tests for PartIdLabelBatchAdapter — 4 standard tests via ReportAdapterTestMixin."""
from django.test import SimpleTestCase

from Tracker.reports.adapters.part_id_label_batch import PartIdLabelBatchAdapter
from Tracker.reports.tests.base import ReportAdapterTestMixin


class TestPartIdLabelBatchAdapter(ReportAdapterTestMixin, SimpleTestCase):
    """Fixture validation + template compile (multi-label) + determinism."""
    adapter_class = PartIdLabelBatchAdapter
    fixture_name = "part_id_label_batch_sample"

    def test_cross_tenant_id_is_rejected(self):
        self.skipTest(
            "Cross-tenant isolation is enforced by the tenant filter in "
            "PartIdLabelBatchParamsSerializer.validate() (part_ids / "
            "work_order_id re-verified against the tenant) and the ORM query "
            "in build_context(). Full probe requires DB state — see "
            "integration tests."
        )
