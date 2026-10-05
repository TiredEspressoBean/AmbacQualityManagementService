"""Tests for the cycle count sheet and differences adapters — fixture validation,
template compile, determinism. Building them from real counts is covered in
test_cycle_count."""
from django.test import SimpleTestCase

from Tracker.reports.adapters.cycle_count import CycleCountReportAdapter, CycleCountSheetAdapter
from Tracker.reports.tests.base import ReportAdapterTestMixin

_SKIP = ("Enforced by CycleCountParamsSerializer.validate_count_id() and "
         "build_context()'s tenant filter.")


class TestCycleCountSheet(ReportAdapterTestMixin, SimpleTestCase):
    adapter_class = CycleCountSheetAdapter
    fixture_name = "cycle_count_sheet_sample"

    def test_cross_tenant_id_is_rejected(self):
        self.skipTest(_SKIP)


class TestCycleCountReport(ReportAdapterTestMixin, SimpleTestCase):
    adapter_class = CycleCountReportAdapter
    fixture_name = "cycle_count_report_sample"

    def test_cross_tenant_id_is_rejected(self):
        self.skipTest(_SKIP)
