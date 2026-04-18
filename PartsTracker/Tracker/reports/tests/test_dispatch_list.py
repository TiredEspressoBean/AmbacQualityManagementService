"""
Tests for DispatchListAdapter.

Covers:
- 4 standard tests via ReportAdapterTestMixin (fixture validation,
  template compile, determinism, cross-tenant stub)
- Targeted fixture shape tests verifying summary counts and sort order
  are consistent with the group/item data

Cross-tenant test is not applicable: this report has no single-record ID.
The param serializer only checks that the user has a tenant context, so
there is nothing to reject across tenants — each user is scoped to their
own tenant by the validate() method.
"""
from django.test import SimpleTestCase

from Tracker.reports.adapters.dispatch_list import (
    DispatchListAdapter,
    DispatchListContext,
)
from Tracker.reports.tests.base import ReportAdapterTestMixin


class TestDispatchListAdapter(ReportAdapterTestMixin, SimpleTestCase):
    """Template + Pydantic + determinism tests against the fixture."""
    adapter_class = DispatchListAdapter
    fixture_name = "dispatch_list_sample"

    def test_cross_tenant_id_is_rejected(self):
        # Not applicable — DispatchListAdapter accepts no record ID.
        # The param serializer only validates that the user has a tenant
        # context, which is inherently scoped to a single tenant.
        self.skipTest(
            "DispatchListAdapter has no record ID; cross-tenant isolation "
            "is enforced by the ORM query filtering on tenant= in build_context()."
        )


class DispatchListFixtureShapeTests(SimpleTestCase):
    """Targeted checks on the fixture beyond Pydantic validation."""

    def setUp(self):
        self._mixin = TestDispatchListAdapter()
        self._fixture = self._mixin._load_fixture()

    def test_total_open_wos_matches_sum_of_group_counts(self):
        """total_open_wos must equal the sum of wo_count across all groups."""
        total = sum(g["wo_count"] for g in self._fixture["groups"])
        self.assertEqual(
            self._fixture["total_open_wos"],
            total,
            "fixture total_open_wos does not match sum of group wo_counts",
        )

    def test_wo_count_matches_items_length(self):
        """Each group's wo_count must equal len(items) in that group."""
        for group in self._fixture["groups"]:
            self.assertEqual(
                group["wo_count"],
                len(group["items"]),
                f"Group {group['step_name']!r}: wo_count does not match len(items)",
            )

    def test_overdue_count_matches_negative_days(self):
        """overdue_count must equal the number of items with days_until_due < 0."""
        overdue = sum(
            1
            for g in self._fixture["groups"]
            for item in g["items"]
            if item.get("days_until_due") is not None and item["days_until_due"] < 0
        )
        self.assertEqual(
            self._fixture["overdue_count"],
            overdue,
            "fixture overdue_count does not match count of items with days_until_due < 0",
        )

    def test_items_sorted_by_due_date_within_each_group(self):
        """Within each group, items must be sorted by due date ascending (None last)."""
        for group in self._fixture["groups"]:
            dates = [
                item["due_date"] if item["due_date"] is not None else "9999-99-99"
                for item in group["items"]
            ]
            self.assertEqual(
                dates,
                sorted(dates),
                f"Group {group['step_name']!r} items are not sorted by due_date ascending",
            )

    def test_fixture_has_overdue_and_future_items(self):
        """Fixture must contain at least one overdue and one future item."""
        all_items = [item for g in self._fixture["groups"] for item in g["items"]]
        has_overdue = any(
            item.get("days_until_due") is not None and item["days_until_due"] < 0
            for item in all_items
        )
        has_future = any(
            item.get("days_until_due") is not None and item["days_until_due"] > 0
            for item in all_items
        )
        self.assertTrue(has_overdue, "fixture has no overdue items (days_until_due < 0)")
        self.assertTrue(has_future, "fixture has no future items (days_until_due > 0)")

    def test_fixture_has_item_with_no_due_date(self):
        """Fixture must include at least one item where due_date is null (null branch coverage)."""
        all_items = [item for g in self._fixture["groups"] for item in g["items"]]
        has_null = any(item["due_date"] is None for item in all_items)
        self.assertTrue(
            has_null,
            "fixture has no item with null due_date — null branch in template not exercised",
        )

    def test_fixture_has_multiple_groups(self):
        """Fixture must have at least 2 work-center groups."""
        self.assertGreaterEqual(
            len(self._fixture["groups"]),
            2,
            "fixture must have at least 2 work-center groups for section rendering coverage",
        )

    def test_context_model_validates_cleanly(self):
        """DispatchListContext must accept the fixture without raising."""
        try:
            ctx = DispatchListContext(**self._fixture)
        except Exception as exc:
            self.fail(f"DispatchListContext validation failed: {exc}")
        self.assertEqual(ctx.total_open_wos, sum(g.wo_count for g in ctx.groups))
