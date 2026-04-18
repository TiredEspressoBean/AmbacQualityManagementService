"""
Tests for BOMReportAdapter.

Covers:
- 4 standard tests via ReportAdapterTestMixin (fixture validation,
  template compile, determinism, cross-tenant stub)
- Targeted fixture shape checks ensuring key fields render meaningfully
"""
from django.test import SimpleTestCase

from Tracker.reports.adapters.bom_report import BOMReportAdapter
from Tracker.reports.tests.base import ReportAdapterTestMixin


class TestBOMReportAdapter(ReportAdapterTestMixin, SimpleTestCase):
    """Template + Pydantic + determinism tests against the fixture."""
    adapter_class = BOMReportAdapter
    fixture_name = "bom_report_sample"

    def test_cross_tenant_id_is_rejected(self):
        # Stub — a full cross-tenant DB probe would require creating BOM
        # records across two tenants (needs a TestCase with DB access).
        self.skipTest(
            "Cross-tenant probe requires DB state; "
            "implement as a separate TestCase subclass when needed."
        )


class BOMReportFixtureShapeTests(SimpleTestCase):
    """Targeted checks on the fixture beyond Pydantic validation."""

    def _fixture(self):
        mixin = TestBOMReportAdapter()
        return mixin._load_fixture()

    def test_fixture_has_parent_part_number(self):
        """Ensure the title block renders a meaningful part number."""
        fixture = self._fixture()
        self.assertTrue(
            fixture.get("parent_part_number", ""),
            "fixture must have a non-empty parent_part_number",
        )

    def test_fixture_has_lines(self):
        """Ensure the component table renders at least one row."""
        fixture = self._fixture()
        self.assertGreater(
            len(fixture.get("lines", [])),
            0,
            "fixture must contain at least one BOM line",
        )

    def test_fixture_line_count_matches_lines(self):
        """total_line_count must equal the length of the lines list."""
        fixture = self._fixture()
        self.assertEqual(
            fixture["total_line_count"],
            len(fixture["lines"]),
            "total_line_count must match the number of lines in the fixture",
        )

    def test_fixture_has_mix_of_optional_and_required(self):
        """Fixture should exercise both optional and required components."""
        fixture = self._fixture()
        optional_flags = [line["is_optional"] for line in fixture["lines"]]
        self.assertIn(True, optional_flags, "fixture must have at least one optional line")
        self.assertIn(False, optional_flags, "fixture must have at least one required line")

    def test_fixture_status_is_valid(self):
        """Status must be one of the BOM_STATUS_CHOICES."""
        fixture = self._fixture()
        valid_statuses = {"DRAFT", "RELEASED", "OBSOLETE"}
        self.assertIn(
            fixture.get("status"),
            valid_statuses,
            f"fixture status must be one of {valid_statuses}",
        )
