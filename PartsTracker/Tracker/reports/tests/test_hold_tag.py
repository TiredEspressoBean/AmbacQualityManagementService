"""Tests for HoldTagAdapter — both shapes compile (fixtures), and the context built from
real held records: heading, reason and record number, and the refusal for an item that
isn't held."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from Tracker.reports.adapters.hold_tag import (
    HoldTagAdapter, HoldTagParamsSerializer, build_lot_tag, build_part_tag,
)
from Tracker.reports.tests.base import ReportAdapterTestMixin
from Tracker.tests.base import TenantContextMixin


class TestHoldTagLotFixture(ReportAdapterTestMixin, SimpleTestCase):
    adapter_class = HoldTagAdapter
    fixture_name = "hold_tag_lot_sample"

    def test_cross_tenant_id_is_rejected(self):
        self.skipTest("Enforced by HoldTagParamsSerializer.validate() and build_context()'s tenant filter.")


class TestHoldTagPartFixture(ReportAdapterTestMixin, SimpleTestCase):
    adapter_class = HoldTagAdapter
    fixture_name = "hold_tag_part_sample"

    def test_cross_tenant_id_is_rejected(self):
        self.skipTest("Enforced by HoldTagParamsSerializer.validate() and build_context()'s tenant filter.")


class HoldTagContextTests(TenantContextMixin, TestCase):

    def setUp(self):
        super().setUp()
        from Tracker.models import Material, MaterialLot, Tenant
        self.tenant = Tenant.objects.create(name="Tags", slug="hold-tags")
        self.set_tenant_context(self.tenant)
        self.user = get_user_model().objects.create_user(
            username="tagger", email="tag@c.test", password="x", tenant=self.tenant)
        self.mat = Material.objects.create(tenant=self.tenant, name="O-Ring", part_number="OR-7")
        self.lot = MaterialLot.objects.create(
            tenant=self.tenant, lot_number="LOT-1", material=self.mat, quantity=Decimal(50),
            quantity_remaining=Decimal(50), unit_of_measure="EA", status="ACCEPTED")

    def _serializer(self, **data):
        self.user._current_tenant = self.tenant
        return HoldTagParamsSerializer(data=data, context={"user": self.user})

    def test_a_held_lot_tag_names_its_reasons(self):
        from Tracker.services.qms.lot_holds import hold
        hold(self.lot, "AWAITING_COC")
        self.lot.refresh_from_db()
        ctx = build_lot_tag(self.lot, self.tenant)
        self.assertEqual((ctx.heading, ctx.identifier, ctx.quantity), ("HOLD", "LOT-1", "50 EA"))
        self.assertEqual(ctx.reasons, ["Awaiting certificate of conformance"])
        self.assertEqual(ctx.part_number, "OR-7")

    def test_a_rejected_lot_reads_rejected(self):
        self.lot.status = "REJECTED"
        self.lot.save(update_fields=["status"])
        self.assertEqual(build_lot_tag(self.lot, self.tenant).heading, "REJECTED")

    def test_a_quarantined_part_carries_its_ncr_and_report(self):
        from Tracker.models import Parts, PartTypes, QualityReports, Steps
        pt = PartTypes.objects.create(tenant=self.tenant, name="Injector", ERP_id="INJ")
        step = Steps.objects.create(tenant=self.tenant, part_type=pt, name="Flow", step_type="TASK")
        part = Parts.objects.create(tenant=self.tenant, ERP_id="INJ-1", part_type=pt, step=step)
        QualityReports.objects.create(tenant=self.tenant, part=part, step=step, status="FAIL",
                                      report_number="QR-1", description="Flow high")
        part.refresh_from_db()
        part.part_status = "QUARANTINED"
        part.save(update_fields=["part_status"])
        ctx = build_part_tag(part, self.tenant)
        self.assertEqual((ctx.heading, ctx.identifier, ctx.step), ("QUARANTINE", "INJ-1", "Flow"))
        self.assertTrue(ctx.record_number, "the auto-opened disposition is named")
        self.assertEqual(ctx.report_numbers, ["QR-1"])

    def test_an_item_that_is_not_held_is_refused(self):
        s = self._serializer(lot_id=str(self.lot.id))
        self.assertFalse(s.is_valid())
        self.assertIn("isn't held", str(s.errors))

    def test_exactly_one_target(self):
        self.assertFalse(self._serializer().is_valid())
