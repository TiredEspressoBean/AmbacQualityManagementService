"""Tests for RtvSheetAdapter — fixture validation, template compile, determinism. The
context built from real records is covered in test_receiving_phase4."""
from django.test import SimpleTestCase

from Tracker.reports.adapters.rtv_sheet import RtvSheetAdapter
from Tracker.reports.tests.base import ReportAdapterTestMixin


class TestRtvSheetAdapter(ReportAdapterTestMixin, SimpleTestCase):
    adapter_class = RtvSheetAdapter
    fixture_name = "rtv_sheet_sample"

    def test_cross_tenant_id_is_rejected(self):
        self.skipTest("Enforced by RtvSheetParamsSerializer.validate_lot_id() and "
                      "build_context()'s tenant filter.")
