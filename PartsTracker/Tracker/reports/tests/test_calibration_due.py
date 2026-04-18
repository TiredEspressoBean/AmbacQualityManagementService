"""
Tests for CalibrationDueAdapter.

Covers:
- 4 standard tests via ReportAdapterTestMixin (fixture validation,
  template compile, determinism, cross-tenant stub)
- Targeted fixture shape tests verifying summary counts are consistent
  with item data

Cross-tenant test is not applicable: this report has no single-record ID.
The param serializer only checks that the user has a tenant context, so
there is nothing to reject across tenants — each user is scoped to their
own tenant by the validate() method.
"""
from django.test import SimpleTestCase

from Tracker.reports.adapters.calibration_due import (
    CalibrationDueAdapter,
    CalibrationDueContext,
)
from Tracker.reports.tests.base import ReportAdapterTestMixin


class TestCalibrationDueAdapter(ReportAdapterTestMixin, SimpleTestCase):
    """Template + Pydantic + determinism tests against the fixture."""
    adapter_class = CalibrationDueAdapter
    fixture_name = "calibration_due_sample"

    def test_cross_tenant_id_is_rejected(self):
        # Not applicable — CalibrationDueAdapter accepts no record ID.
        # The param serializer only validates that the user has a tenant
        # context, which is inherently scoped to a single tenant.
        self.skipTest(
            "CalibrationDueAdapter has no record ID; cross-tenant isolation "
            "is enforced by the ORM query filtering on tenant= in build_context()."
        )


class CalibrationDueFixtureShapeTests(SimpleTestCase):
    """Targeted checks on the fixture beyond Pydantic validation."""

    def setUp(self):
        self._mixin = TestCalibrationDueAdapter()
        self._fixture = self._mixin._load_fixture()

    def test_summary_counts_match_items(self):
        """overdue_count and due_soon_count must match the actual item statuses."""
        items = self._fixture["items"]
        overdue = sum(1 for i in items if i["status"] == "OVERDUE")
        due_soon = sum(1 for i in items if i["status"] == "DUE_SOON")
        self.assertEqual(
            self._fixture["overdue_count"],
            overdue,
            "fixture overdue_count does not match count of OVERDUE items",
        )
        self.assertEqual(
            self._fixture["due_soon_count"],
            due_soon,
            "fixture due_soon_count does not match count of DUE_SOON items",
        )

    def test_total_equipment_matches_item_count(self):
        """total_equipment must equal the number of items in the list."""
        self.assertEqual(
            self._fixture["total_equipment"],
            len(self._fixture["items"]),
            "fixture total_equipment does not match len(items)",
        )

    def test_items_sorted_by_due_date_ascending(self):
        """Items must be sorted by due_date ascending so overdue items come first."""
        due_dates = [i["due_date"] for i in self._fixture["items"]]
        self.assertEqual(
            due_dates,
            sorted(due_dates),
            "fixture items are not sorted by due_date ascending",
        )

    def test_overdue_items_have_negative_days_until_due(self):
        """Every OVERDUE item must have days_until_due < 0."""
        for item in self._fixture["items"]:
            if item["status"] == "OVERDUE":
                self.assertLess(
                    item["days_until_due"],
                    0,
                    f"OVERDUE item {item['equipment_name']!r} has "
                    f"non-negative days_until_due={item['days_until_due']}",
                )

    def test_due_soon_items_have_days_in_range(self):
        """Every DUE_SOON item must have 0 <= days_until_due <= 30."""
        for item in self._fixture["items"]:
            if item["status"] == "DUE_SOON":
                self.assertGreaterEqual(item["days_until_due"], 0)
                self.assertLessEqual(
                    item["days_until_due"],
                    30,
                    f"DUE_SOON item {item['equipment_name']!r} has "
                    f"days_until_due={item['days_until_due']} > 30",
                )

    def test_fixture_has_both_overdue_and_current_items(self):
        """Fixture must exercise all three status values for full template coverage."""
        statuses = {i["status"] for i in self._fixture["items"]}
        for expected in ("OVERDUE", "DUE_SOON", "CURRENT"):
            self.assertIn(
                expected,
                statuses,
                f"fixture is missing a {expected!r} item — "
                "all three status branches must be exercised",
            )

    def test_context_model_validates_cleanly(self):
        """CalibrationDueContext must accept the fixture without raising."""
        try:
            ctx = CalibrationDueContext(**self._fixture)
        except Exception as exc:
            self.fail(f"CalibrationDueContext validation failed: {exc}")
        self.assertEqual(ctx.total_equipment, len(ctx.items))
