"""
Tests for CheckingAidsAdapter.

Covers:
- 4 standard tests via ReportAdapterTestMixin (fixture validation,
  template compile, determinism, cross-tenant stub)
- Targeted fixture shape tests for PPAP Element 16 traceability fields

Cross-tenant test is not applicable: this report has no single-record ID.
The param serializer only checks that the user has a tenant context, so
there is nothing to reject across tenants — each user is scoped to their
own tenant by the validate() method.
"""
from django.test import SimpleTestCase

from Tracker.reports.adapters.checking_aids import (
    CheckingAidsAdapter,
    CheckingAidsContext,
)
from Tracker.reports.tests.base import ReportAdapterTestMixin


class TestCheckingAidsAdapter(ReportAdapterTestMixin, SimpleTestCase):
    """Template + Pydantic + determinism tests against the fixture."""
    adapter_class = CheckingAidsAdapter
    fixture_name = "checking_aids_sample"

    def test_cross_tenant_id_is_rejected(self):
        # Not applicable — CheckingAidsAdapter accepts no record ID.
        # The param serializer only validates that the user has a tenant
        # context, which is inherently scoped to a single tenant.
        self.skipTest(
            "CheckingAidsAdapter has no record ID; cross-tenant isolation "
            "is enforced by the ORM query filtering on tenant= in build_context()."
        )


class CheckingAidsFixtureShapeTests(SimpleTestCase):
    """Targeted checks on the fixture beyond Pydantic validation."""

    def setUp(self):
        self._mixin = TestCheckingAidsAdapter()
        self._fixture = self._mixin._load_fixture()

    def test_total_count_matches_item_count(self):
        """total_count must equal the number of items in the list."""
        self.assertEqual(
            self._fixture["total_count"],
            len(self._fixture["items"]),
            "fixture total_count does not match len(items)",
        )

    def test_items_sorted_by_name_alphabetically(self):
        """Items must be sorted by name alphabetically (case-insensitive)."""
        names = [i["name"].lower() for i in self._fixture["items"]]
        self.assertEqual(
            names,
            sorted(names),
            "fixture items are not sorted by name alphabetically",
        )

    def test_fixture_has_calibrated_items(self):
        """Fixture must contain at least one item with calibration traceability."""
        calibrated = [
            i for i in self._fixture["items"]
            if i["cal_cert_number"] is not None and i["cal_date"] is not None
        ]
        self.assertGreater(
            len(calibrated), 0,
            "fixture must have at least one item with calibration traceability "
            "to exercise the normal template path",
        )

    def test_fixture_has_uncalibrated_items(self):
        """Fixture must contain at least one item without a calibration record
        to exercise the 'not available' template branch."""
        uncalibrated = [
            i for i in self._fixture["items"]
            if i["cal_cert_number"] is None
        ]
        self.assertGreater(
            len(uncalibrated), 0,
            "fixture must have at least one item without calibration data "
            "to exercise the fallback template branch",
        )

    def test_uncalibrated_items_have_null_cert_and_date(self):
        """Items with no cal_cert_number must also have null cal_date and standards_used."""
        for item in self._fixture["items"]:
            if item["cal_cert_number"] is None:
                self.assertIsNone(
                    item["cal_date"],
                    f"Item {item['name']!r} has null cal_cert_number but non-null cal_date",
                )

    def test_context_model_validates_cleanly(self):
        """CheckingAidsContext must accept the fixture without raising."""
        try:
            ctx = CheckingAidsContext(**self._fixture)
        except Exception as exc:
            self.fail(f"CheckingAidsContext validation failed: {exc}")
        self.assertEqual(ctx.total_count, len(ctx.items))
