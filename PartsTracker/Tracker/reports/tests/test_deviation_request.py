"""
Tests for DeviationRequestAdapter.

Covers:
- 4 standard tests via ReportAdapterTestMixin (fixture validation,
  template compile, determinism, cross-tenant stub)
- Cross-tenant DB test: a user in Tenant A cannot generate a deviation
  request PDF for a disposition owned by Tenant B.
- Disposition-type rejection: submitting a REWORK or SCRAP disposition
  ID is rejected at the param-serializer level.
"""
from django.test import SimpleTestCase, TestCase

from Tracker.reports.adapters.deviation_request import DeviationRequestAdapter
from Tracker.reports.services.pdf_generator import (
    PdfGenerator,
    ReportParamError,
)
from Tracker.reports.tests.base import ReportAdapterTestMixin


class TestDeviationRequestAdapter(ReportAdapterTestMixin, SimpleTestCase):
    """Template + Pydantic + determinism tests against the fixture."""
    adapter_class = DeviationRequestAdapter
    fixture_name = "deviation_request_sample"

    def test_cross_tenant_id_is_rejected(self):
        # Stub — real cross-tenant probe lives in
        # DeviationRequestAdapterCrossTenantTests (below), which needs
        # a real database and is a TestCase, not SimpleTestCase.
        self.skipTest(
            "Cross-tenant probe is in "
            "DeviationRequestAdapterCrossTenantTests (requires DB)."
        )


class DeviationRequestFixtureShapeTests(SimpleTestCase):
    """Targeted checks on the fixture beyond Pydantic validation."""

    def test_fixture_disposition_type_is_use_as_is_or_repair(self):
        """Fixture must exercise a USE_AS_IS or REPAIR disposition, not REWORK/SCRAP."""
        mixin = TestDeviationRequestAdapter()
        fixture = mixin._load_fixture()
        self.assertIn(
            fixture.get("disposition_type"),
            {"USE_AS_IS", "REPAIR"},
            "fixture disposition_type must be USE_AS_IS or REPAIR",
        )

    def test_fixture_has_resolution_notes(self):
        """Fixture must have a non-empty engineering justification."""
        mixin = TestDeviationRequestAdapter()
        fixture = mixin._load_fixture()
        self.assertTrue(
            fixture.get("resolution_notes", ""),
            "fixture must have a non-empty resolution_notes (engineering justification)",
        )

    def test_fixture_requires_customer_approval(self):
        """Fixture exercises the customer approval section (requires_customer_approval=True)."""
        mixin = TestDeviationRequestAdapter()
        fixture = mixin._load_fixture()
        self.assertTrue(
            fixture.get("requires_customer_approval"),
            "fixture must set requires_customer_approval=True to exercise the "
            "customer approval section and 3-column signature block",
        )


# ---------------------------------------------------------------------------
# DB-backed tests — exercise the full adapter with real ORM queries
# ---------------------------------------------------------------------------


class DeviationRequestAdapterCrossTenantTests(TestCase):
    """
    Verifies the param serializer rejects QuarantineDisposition IDs from
    other tenants.  This is the security-critical test — if this fails,
    a user in Tenant A could generate a Deviation Request PDF for a
    disposition owned by Tenant B.

    Also verifies that REWORK/SCRAP disposition IDs are rejected even
    when they belong to the correct tenant.
    """

    @classmethod
    def setUpTestData(cls):
        import datetime
        from Tracker.models import Tenant, User, QuarantineDisposition

        cls.tenant_a = Tenant.objects.create(
            slug="dev-req-test-a", name="DevReq Tenant A"
        )
        cls.tenant_b = Tenant.objects.create(
            slug="dev-req-test-b", name="DevReq Tenant B"
        )

        cls.user_a = User.objects.create_user(
            username="dev-req-user-a",
            email="dev-req-a@example.com",
            password="x",
            tenant=cls.tenant_a,
        )
        cls.user_b = User.objects.create_user(
            username="dev-req-user-b",
            email="dev-req-b@example.com",
            password="x",
            tenant=cls.tenant_b,
        )

        # USE_AS_IS disposition owned by Tenant B
        cls.use_as_is_in_b = QuarantineDisposition.objects.create(
            tenant=cls.tenant_b,
            disposition_number="DISP-TEST-B-001",
            disposition_type="USE_AS_IS",
            severity="MINOR",
            current_state="OPEN",
            description="Test cosmetic scratch — cross-tenant probe fixture",
            resolution_notes="No effect on form, fit, or function.",
            requires_customer_approval=False,
        )

        # REWORK disposition owned by Tenant A (wrong type, right tenant)
        cls.rework_in_a = QuarantineDisposition.objects.create(
            tenant=cls.tenant_a,
            disposition_number="DISP-TEST-A-REWORK",
            disposition_type="REWORK",
            severity="MAJOR",
            current_state="OPEN",
            description="Test rework disposition — type rejection probe",
            resolution_notes="",
            requires_customer_approval=False,
        )

    def test_user_a_cannot_generate_deviation_request_for_tenant_b(self):
        """User in Tenant A submits a QuarantineDisposition ID from Tenant B → rejected."""
        with self.assertRaises(ReportParamError) as ctx:
            PdfGenerator().generate(
                "deviation_request",
                {"id": self.use_as_is_in_b.id},
                user=self.user_a,
            )
        self.assertIn("id", ctx.exception.errors)

    def test_rework_disposition_is_rejected_for_deviation_request(self):
        """REWORK disposition type is not valid for a deviation request → rejected."""
        with self.assertRaises(ReportParamError) as ctx:
            PdfGenerator().generate(
                "deviation_request",
                {"id": self.rework_in_a.id},
                user=self.user_a,
            )
        self.assertIn("id", ctx.exception.errors)

    def test_user_b_can_generate_own_deviation_request(self):
        """Sanity: the owning tenant's user can generate their deviation request."""
        pdf = PdfGenerator().generate(
            "deviation_request",
            {"id": self.use_as_is_in_b.id},
            user=self.user_b,
        )
        self.assertTrue(pdf.startswith(b"%PDF"))
