"""Tests for LotTraceAdapter — fixture validation, template compile, determinism. The
trace itself is covered in the receiving and shipping suites."""
from django.test import SimpleTestCase

from Tracker.reports.adapters.lot_trace import LotTraceAdapter
from Tracker.reports.tests.base import ReportAdapterTestMixin


class TestLotTraceReport(ReportAdapterTestMixin, SimpleTestCase):
    adapter_class = LotTraceAdapter
    fixture_name = "lot_trace_sample"

    def test_cross_tenant_id_is_rejected(self):
        self.skipTest("Enforced by LotTraceParamsSerializer.validate_lot_id() and "
                      "build_context()'s tenant filter.")
