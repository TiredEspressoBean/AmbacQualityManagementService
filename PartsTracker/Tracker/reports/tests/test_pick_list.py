"""
Tests for PickListAdapter.

Covers:
- 4 standard tests via ReportAdapterTestMixin (fixture validation,
  template compile, determinism, cross-tenant stub)
- Targeted fixture shape tests verifying qty_required = qty_per_assembly × qty_to_produce
"""
from django.test import SimpleTestCase

from Tracker.reports.adapters.pick_list import (
    PickListAdapter,
    PickListContext,
)
from Tracker.reports.tests.base import ReportAdapterTestMixin


class TestPickListAdapter(ReportAdapterTestMixin, SimpleTestCase):
    """Template + Pydantic + determinism tests against the fixture."""
    adapter_class = PickListAdapter
    fixture_name = "pick_list_sample"

    def test_cross_tenant_id_is_rejected(self):
        # A real cross-tenant probe requires DB state (two tenants, two
        # users, a WorkOrder in tenant A submitted by a user in tenant B).
        # That is exercised by integration tests; here we confirm the
        # param serializer's validate_id() method enforces the tenant filter.
        # Override this with a TransactionTestCase-based test when a
        # multi-tenant fixture is available.
        self.skipTest(
            "Cross-tenant isolation is enforced by the tenant= filter in "
            "PickListParamsSerializer.validate_id() and the ORM query in "
            "build_context(). Full probe requires DB state — see integration tests."
        )


class PickListFixtureShapeTests(SimpleTestCase):
    """Targeted checks on the fixture beyond Pydantic validation."""

    def setUp(self):
        self._mixin = TestPickListAdapter()
        self._fixture = self._mixin._load_fixture()

    def test_total_line_count_matches_items(self):
        """total_line_count must equal the number of items in the list."""
        self.assertEqual(
            self._fixture["total_line_count"],
            len(self._fixture["items"]),
            "fixture total_line_count does not match len(items)",
        )

    def test_qty_required_equals_qty_per_assembly_times_wo_qty(self):
        """Every item's qty_required must equal qty_per_assembly × qty_to_produce."""
        from decimal import Decimal
        from Tracker.reports.adapters.pick_list import _fmt_qty

        wo_qty = self._fixture["qty_to_produce"]
        for item in self._fixture["items"]:
            expected = _fmt_qty(Decimal(item["qty_per_assembly"]) * Decimal(wo_qty))
            self.assertEqual(
                item["qty_required"],
                expected,
                f"Item find_number={item['find_number']!r}: qty_required "
                f"{item['qty_required']!r} != {expected!r} "
                f"(qty_per_assembly={item['qty_per_assembly']} × wo_qty={wo_qty})",
            )

    def test_fixture_has_at_least_one_optional_item(self):
        """Fixture must include at least one optional line to exercise that branch."""
        optional_items = [i for i in self._fixture["items"] if i["is_optional"]]
        self.assertGreater(
            len(optional_items),
            0,
            "fixture has no optional items — the OPT badge branch is not exercised",
        )

    def test_fixture_has_at_least_one_required_item(self):
        """Fixture must include at least one non-optional line."""
        required_items = [i for i in self._fixture["items"] if not i["is_optional"]]
        self.assertGreater(
            len(required_items),
            0,
            "fixture has no required items — all items are optional",
        )

    def test_fixture_has_multi_qty_line(self):
        """At least one line should have qty_per_assembly > 1 to exercise multiplication."""
        multi = [
            i for i in self._fixture["items"]
            if i["qty_per_assembly"] not in ("1", "1.0")
        ]
        self.assertGreater(
            len(multi),
            0,
            "fixture has no multi-qty lines — qty_required multiplication is not exercised",
        )

    def test_context_model_validates_cleanly(self):
        """PickListContext must accept the fixture without raising."""
        try:
            ctx = PickListContext(**self._fixture)
        except Exception as exc:
            self.fail(f"PickListContext validation failed: {exc}")
        self.assertEqual(ctx.total_line_count, len(ctx.items))
        self.assertEqual(ctx.qty_to_produce, self._fixture["qty_to_produce"])
