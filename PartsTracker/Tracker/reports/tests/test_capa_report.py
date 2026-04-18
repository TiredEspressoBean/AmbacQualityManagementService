"""
Tests for CapaReportAdapter.

Covers:
- 4 standard tests via ReportAdapterTestMixin (fixture validation,
  template compile, determinism, cross-tenant stub)
- Targeted fixture shape checks
- Cross-tenant security test using a DB-backed TestCase

Cross-tenant security test uses a DB-backed TestCase since it needs
real CAPA rows across two tenants.
"""
from django.test import SimpleTestCase, TestCase

from Tracker.reports.adapters.capa_report import CapaReportAdapter
from Tracker.reports.services.pdf_generator import (
    PdfGenerator,
    ReportParamError,
)
from Tracker.reports.tests.base import ReportAdapterTestMixin


class TestCapaReportAdapter(ReportAdapterTestMixin, SimpleTestCase):
    """Template + Pydantic + determinism tests against the fixture."""
    adapter_class = CapaReportAdapter
    fixture_name = "capa_report_sample"

    def test_cross_tenant_id_is_rejected(self):
        # Stub — real cross-tenant probe lives in
        # CapaReportAdapterCrossTenantTests (below), which needs a real
        # database and is a TestCase, not SimpleTestCase.
        self.skipTest(
            "Cross-tenant probe is in "
            "CapaReportAdapterCrossTenantTests (requires DB)."
        )


class CapaReportFixtureShapeTests(SimpleTestCase):
    """Targeted checks on the fixture beyond Pydantic validation."""

    def _fixture(self):
        mixin = TestCapaReportAdapter()
        return mixin._load_fixture()

    def test_fixture_has_capa_number(self):
        """Fixture must have a non-empty capa_number for the title block."""
        fixture = self._fixture()
        self.assertTrue(
            fixture.get("capa_number", ""),
            "fixture must have a non-empty capa_number",
        )

    def test_fixture_has_five_tasks(self):
        """Fixture must include the 5 tasks described in the spec."""
        fixture = self._fixture()
        tasks = fixture.get("tasks", [])
        self.assertEqual(len(tasks), 5, "fixture must have exactly 5 tasks")

    def test_fixture_tasks_cover_all_three_types(self):
        """Fixture tasks must include CONTAINMENT, CORRECTIVE, and PREVENTIVE types."""
        fixture = self._fixture()
        types = {t["task_type"] for t in fixture.get("tasks", [])}
        for expected in ("CONTAINMENT", "CORRECTIVE", "PREVENTIVE"):
            self.assertIn(
                expected, types,
                f"fixture tasks must include a {expected} task",
            )

    def test_fixture_has_five_whys_rca(self):
        """Fixture RCA must use FIVE_WHYS method with at least 3 why pairs."""
        fixture = self._fixture()
        rca = fixture.get("rca", {}) or {}
        self.assertEqual(rca.get("method"), "FIVE_WHYS")
        whys = (rca.get("five_whys") or {}).get("whys", [])
        self.assertGreaterEqual(
            len(whys), 3,
            "fixture must have at least 3 why pairs",
        )

    def test_fixture_has_verification(self):
        """Fixture must include a verification section."""
        fixture = self._fixture()
        self.assertIsNotNone(
            fixture.get("verification"),
            "fixture must include a verification section",
        )

    def test_fixture_verification_is_confirmed(self):
        """Fixture verification result must be CONFIRMED."""
        fixture = self._fixture()
        result = (fixture.get("verification") or {}).get("effectiveness_result")
        self.assertEqual(
            result,
            "CONFIRMED",
            "fixture verification must have effectiveness_result=CONFIRMED",
        )


# ---------------------------------------------------------------------------
# DB-backed tests — exercise the full adapter with real ORM queries
# ---------------------------------------------------------------------------


class CapaReportAdapterCrossTenantTests(TestCase):
    """
    Verifies the param serializer rejects CAPA IDs from other tenants.
    This is the security-critical test — if this fails, a user in
    Tenant A could generate a CAPA Report PDF for a CAPA owned by
    Tenant B.
    """

    @classmethod
    def setUpTestData(cls):
        from Tracker.models import Tenant, User
        from Tracker.models.qms import CAPA

        cls.tenant_a = Tenant.objects.create(
            slug="capa-test-a", name="CAPA Tenant A"
        )
        cls.tenant_b = Tenant.objects.create(
            slug="capa-test-b", name="CAPA Tenant B"
        )

        cls.user_a = User.objects.create_user(
            username="capa-user-a",
            email="capa-a@example.com",
            password="x",
            tenant=cls.tenant_a,
        )
        cls.user_b = User.objects.create_user(
            username="capa-user-b",
            email="capa-b@example.com",
            password="x",
            tenant=cls.tenant_b,
        )

        import datetime
        cls.capa_in_b = CAPA.objects.create(
            tenant=cls.tenant_b,
            capa_number="CAPA-CA-2026-TEST-001",
            capa_type="CORRECTIVE",
            severity="MINOR",
            status="OPEN",
            problem_statement="Cross-tenant test CAPA — do not close.",
            initiated_date=datetime.date.today(),
        )

    def test_user_a_cannot_generate_report_for_tenant_b(self):
        """User in Tenant A submits a CAPA ID from Tenant B → rejected."""
        with self.assertRaises(ReportParamError) as ctx:
            PdfGenerator().generate(
                "capa_report",
                {"id": self.capa_in_b.id},
                user=self.user_a,
            )
        self.assertIn("id", ctx.exception.errors)

    def test_user_b_can_generate_own_report(self):
        """Sanity: the owning tenant's user can generate their CAPA report."""
        pdf = PdfGenerator().generate(
            "capa_report",
            {"id": self.capa_in_b.id},
            user=self.user_b,
        )
        self.assertTrue(pdf.startswith(b"%PDF"))
