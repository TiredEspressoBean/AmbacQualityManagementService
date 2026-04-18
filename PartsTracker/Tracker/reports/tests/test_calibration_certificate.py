"""
Tests for CalibrationCertificateAdapter.

Covers:
- 4 standard tests via ReportAdapterTestMixin (fixture validation,
  template compile, determinism, cross-tenant stub)
- Dispatch-level tests exercising the full PdfGenerator path

Cross-tenant security test uses a DB-backed TestCase since it needs
real CalibrationRecord rows across two tenants.
"""
from django.test import SimpleTestCase, TestCase

from Tracker.reports.adapters.calibration_certificate import (
    CalibrationCertificateAdapter,
)
from Tracker.reports.services.pdf_generator import (
    PdfGenerator,
    ReportParamError,
)
from Tracker.reports.tests.base import ReportAdapterTestMixin


class TestCalibrationCertificateAdapter(ReportAdapterTestMixin, SimpleTestCase):
    """Template + Pydantic + determinism tests against the fixture."""
    adapter_class = CalibrationCertificateAdapter
    fixture_name = "calibration_certificate_sample"

    def test_cross_tenant_id_is_rejected(self):
        # Stub — real cross-tenant probe lives in
        # CalibrationCertificateAdapterCrossTenantTests (below), which needs
        # a real database and is a TestCase, not SimpleTestCase.
        self.skipTest(
            "Cross-tenant probe is in "
            "CalibrationCertificateAdapterCrossTenantTests (requires DB)."
        )


class CalibrationCertificateFixtureShapeTests(SimpleTestCase):
    """Targeted checks on the fixture beyond Pydantic validation."""

    def test_fixture_has_certificate_number(self):
        """Ensure the fixture has a non-empty certificate_number so the
        title block renders meaningfully."""
        mixin = TestCalibrationCertificateAdapter()
        fixture = mixin._load_fixture()
        self.assertTrue(
            fixture.get("certificate_number", ""),
            "fixture must have a non-empty certificate_number",
        )

    def test_fixture_has_standards_used(self):
        """Ensure the fixture exercises the standards traceability section —
        a blank string would silently skip the NIST statement."""
        mixin = TestCalibrationCertificateAdapter()
        fixture = mixin._load_fixture()
        self.assertTrue(
            fixture.get("standards_used", ""),
            "fixture must have a non-empty standards_used to exercise "
            "the NIST traceability section",
        )


# ---------------------------------------------------------------------------
# DB-backed tests — exercise the full adapter with real ORM queries
# ---------------------------------------------------------------------------


class CalibrationCertificateAdapterCrossTenantTests(TestCase):
    """
    Verifies the param serializer rejects CalibrationRecord IDs from
    other tenants.  This is the security-critical test — if this fails,
    a user in Tenant A could generate a Calibration Certificate PDF for
    equipment owned by Tenant B.
    """

    @classmethod
    def setUpTestData(cls):
        import datetime
        from Tracker.models import Tenant, User, CalibrationRecord
        from Tracker.models.mes_standard import Equipments

        cls.tenant_a = Tenant.objects.create(
            slug="cal-test-a", name="Cal Tenant A"
        )
        cls.tenant_b = Tenant.objects.create(
            slug="cal-test-b", name="Cal Tenant B"
        )

        cls.user_a = User.objects.create_user(
            username="cal-user-a",
            email="cal-a@example.com",
            password="x",
            tenant=cls.tenant_a,
        )
        cls.user_b = User.objects.create_user(
            username="cal-user-b",
            email="cal-b@example.com",
            password="x",
            tenant=cls.tenant_b,
        )

        # Create a minimal equipment record owned by Tenant B
        cls.equipment_b = Equipments.objects.create(
            tenant=cls.tenant_b,
            name="Test Gauge — Tenant B",
            serial_number="SN-TEST-B-001",
        )

        today = datetime.date.today()
        cls.record_in_b = CalibrationRecord.objects.create(
            tenant=cls.tenant_b,
            equipment=cls.equipment_b,
            calibration_date=today,
            due_date=today.replace(year=today.year + 1),
            result="PASS",
            calibration_type="SCHEDULED",
            certificate_number="CAL-TEST-B-0001",
        )

    def test_user_a_cannot_generate_certificate_for_tenant_b(self):
        """User in Tenant A submits a CalibrationRecord ID from Tenant B → rejected."""
        with self.assertRaises(ReportParamError) as ctx:
            PdfGenerator().generate(
                "calibration_certificate",
                {"id": self.record_in_b.id},
                user=self.user_a,
            )
        # Should fail validation on the id field
        self.assertIn("id", ctx.exception.errors)

    def test_user_b_can_generate_own_certificate(self):
        """Sanity: the owning tenant's user can generate their certificate."""
        pdf = PdfGenerator().generate(
            "calibration_certificate",
            {"id": self.record_in_b.id},
            user=self.user_b,
        )
        self.assertTrue(pdf.startswith(b"%PDF"))
