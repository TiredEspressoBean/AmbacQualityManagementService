"""
Tests for NcrAdapter.

Covers:
- 4 standard tests via ReportAdapterTestMixin (fixture validation,
  template compile, determinism, cross-tenant stub)
- Dispatch-level tests exercising the full PdfGenerator path

Cross-tenant security test uses a DB-backed TestCase since it needs
real QuarantineDisposition rows across two tenants.
"""
from django.test import SimpleTestCase, TestCase

from Tracker.reports.adapters.ncr import NcrAdapter
from Tracker.reports.services.pdf_generator import (
    PdfGenerator,
    ReportParamError,
)
from Tracker.reports.tests.base import ReportAdapterTestMixin


class TestNcrAdapter(ReportAdapterTestMixin, SimpleTestCase):
    """Template + Pydantic + determinism tests against the fixture."""
    adapter_class = NcrAdapter
    fixture_name = "ncr_report_sample"

    def test_cross_tenant_id_is_rejected(self):
        # Stub — real cross-tenant probe lives in NcrAdapterCrossTenantTests
        # (below), which needs a real database and is a TestCase, not
        # SimpleTestCase.
        self.skipTest(
            "Cross-tenant probe is in NcrAdapterCrossTenantTests "
            "(requires DB)."
        )


class NcrAdapterFixtureShapeTests(SimpleTestCase):
    """Targeted checks on the fixture beyond Pydantic validation."""

    def test_fixture_exercises_defects_list(self):
        """Ensure the fixture has at least one defect row — if someone
        accidentally empties the defects list, the template won't render
        the defect table and the test silently loses coverage."""
        mixin = TestNcrAdapter()
        fixture = mixin._load_fixture()
        reports = fixture["quality_reports"]
        self.assertTrue(reports, "fixture must have at least one quality report")
        self.assertTrue(
            any(qr["defects"] for qr in reports),
            "fixture must exercise the defects table",
        )


# ---------------------------------------------------------------------------
# DB-backed tests — exercise the full adapter with real ORM queries
# ---------------------------------------------------------------------------


class NcrAdapterCrossTenantTests(TestCase):
    """
    Verifies the param serializer rejects NCR IDs from other tenants.
    This is the security-critical test — if this fails, a user in
    Tenant A could generate a PDF of an NCR from Tenant B.
    """

    @classmethod
    def setUpTestData(cls):
        from Tracker.models import Tenant, User, QuarantineDisposition

        cls.tenant_a = Tenant.objects.create(
            slug="ncr-test-a", name="Tenant A"
        )
        cls.tenant_b = Tenant.objects.create(
            slug="ncr-test-b", name="Tenant B"
        )

        cls.user_a = User.objects.create_user(
            username="ncr-user-a",
            email="ncr-a@example.com",
            password="x",
            tenant=cls.tenant_a,
        )
        cls.user_b = User.objects.create_user(
            username="ncr-user-b",
            email="ncr-b@example.com",
            password="x",
            tenant=cls.tenant_b,
        )

        # tenant-safe: tests deliberately create cross-tenant rows
        cls.qd_in_b = QuarantineDisposition.objects.create(
            tenant=cls.tenant_b,
            disposition_number="DISP-TEST-B-0001",
            current_state="OPEN",
            severity="MAJOR",
            description="NCR owned by Tenant B",
        )

    def test_user_a_cannot_generate_ncr_for_tenant_b(self):
        """User in Tenant A submits an NCR ID from Tenant B → rejected."""
        with self.assertRaises(ReportParamError) as ctx:
            PdfGenerator().generate(
                "ncr_report",
                {"id": self.qd_in_b.id},
                user=self.user_a,
            )
        # Should fail validation on the id field
        self.assertIn("id", ctx.exception.errors)

    def test_user_b_can_generate_own_ncr(self):
        """Sanity: the owning tenant's user can generate their NCR."""
        pdf = PdfGenerator().generate(
            "ncr_report",
            {"id": self.qd_in_b.id},
            user=self.user_b,
        )
        self.assertTrue(pdf.startswith(b"%PDF"))
