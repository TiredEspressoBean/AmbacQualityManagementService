"""Tests for RequirementsAdapter — fixture validation + Typst template compile."""
from django.test import SimpleTestCase

from Tracker.reports.adapters.requirements import RequirementsAdapter
from Tracker.reports.tests.base import ReportAdapterTestMixin


class TestRequirementsAdapter(ReportAdapterTestMixin, SimpleTestCase):
    adapter_class = RequirementsAdapter
    fixture_name = "requirements_sample"

    def test_lanes_present(self):
        ctx = self._build_context_from_fixture()
        self.assertTrue(ctx.source and ctx.produce and ctx.tooling)
