"""Tests for LaborHoursAdapter — fixture validation + Typst template compile."""
from django.test import SimpleTestCase

from Tracker.reports.adapters.labor_hours import LaborHoursAdapter
from Tracker.reports.tests.base import ReportAdapterTestMixin


class TestLaborHoursAdapter(ReportAdapterTestMixin, SimpleTestCase):
    adapter_class = LaborHoursAdapter
    fixture_name = "labor_hours_sample"

    def test_totals_match_row_sums(self):
        ctx = self._build_context_from_fixture()
        self.assertAlmostEqual(ctx.total_on_shift, sum(r.on_shift_hours for r in ctx.rows), places=2)
        self.assertAlmostEqual(ctx.total_direct, sum(r.direct_hours for r in ctx.rows), places=2)
