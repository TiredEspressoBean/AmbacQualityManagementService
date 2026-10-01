"""Tests for ReceivingInspectionRecordAdapter — fixture validation, template compile,
determinism (ReportAdapterTestMixin). The context built from real records is covered
in test_receiving_phase3."""
from django.test import SimpleTestCase

from Tracker.reports.adapters.receiving_inspection_record import ReceivingInspectionRecordAdapter
from Tracker.reports.tests.base import ReportAdapterTestMixin


class TestReceivingInspectionRecordAdapter(ReportAdapterTestMixin, SimpleTestCase):
    adapter_class = ReceivingInspectionRecordAdapter
    fixture_name = "receiving_inspection_record_sample"

    def test_cross_tenant_id_is_rejected(self):
        self.skipTest(
            "Enforced by the tenant filter in ReceivingInspectionRecordParamsSerializer."
            "validate_lot_id() and build_context(); covered against the database in "
            "test_receiving_phase3.")
