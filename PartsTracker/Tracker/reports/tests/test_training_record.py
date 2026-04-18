"""
Tests for TrainingRecordAdapter.

Covers:
- 4 standard tests via ReportAdapterTestMixin (fixture validation,
  template compile, determinism, cross-tenant stub)
- Targeted fixture-shape tests ensuring the report satisfies
  ISO 9001 §7.2 evidence requirements
"""
from django.test import SimpleTestCase

from Tracker.reports.adapters.training_record import (
    TrainingRecordAdapter,
)
from Tracker.reports.tests.base import ReportAdapterTestMixin


class TestTrainingRecordAdapter(ReportAdapterTestMixin, SimpleTestCase):
    """Template + Pydantic + determinism tests against the fixture."""
    adapter_class = TrainingRecordAdapter
    fixture_name = "training_record_sample"

    def test_cross_tenant_id_is_rejected(self):
        # Stub — a full cross-tenant probe requires DB state.
        # The param serializer filters by tenant on user_id; a real
        # probe would create a User in Tenant B and attempt generation
        # as a user in Tenant A.
        self.skipTest(
            "Cross-tenant probe requires DB state. "
            "Override in a TestCase subclass with real User rows."
        )


class TrainingRecordFixtureShapeTests(SimpleTestCase):
    """Targeted checks on the fixture beyond Pydantic validation."""

    def _fixture(self):
        mixin = TestTrainingRecordAdapter()
        return mixin._load_fixture()

    def test_fixture_has_employee_name(self):
        """Employee name must be non-empty so the title block renders."""
        fixture = self._fixture()
        self.assertTrue(
            fixture.get("employee_name", ""),
            "fixture must have a non-empty employee_name",
        )

    def test_fixture_has_records(self):
        """Must have at least one training record — an empty table is not
        a valid competence record under ISO 9001 §7.2."""
        fixture = self._fixture()
        self.assertTrue(
            len(fixture.get("records", [])) > 0,
            "fixture must contain at least one training record",
        )

    def test_fixture_has_mix_of_statuses(self):
        """Fixture should exercise both CURRENT and EXPIRED status paths
        so the status badge rendering is exercised in the test compile."""
        fixture = self._fixture()
        statuses = {r["status"] for r in fixture.get("records", [])}
        self.assertIn(
            "CURRENT", statuses,
            "fixture must contain at least one CURRENT record",
        )
        self.assertIn(
            "EXPIRED", statuses,
            "fixture must contain at least one EXPIRED record",
        )

    def test_fixture_summary_counts_match_records(self):
        """total_count must equal len(records) to catch copy-paste drift."""
        fixture = self._fixture()
        records = fixture.get("records", [])
        self.assertEqual(
            fixture.get("total_count"), len(records),
            "total_count in fixture must equal len(records)",
        )

    def test_fixture_has_no_expiry_records(self):
        """At least one record should have expires_date=null so the
        'no expiry' column rendering path is exercised."""
        fixture = self._fixture()
        no_expiry = [r for r in fixture.get("records", []) if r.get("expires_date") is None]
        self.assertTrue(
            len(no_expiry) > 0,
            "fixture must contain at least one record with expires_date=null",
        )
