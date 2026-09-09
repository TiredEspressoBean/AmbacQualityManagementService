"""On-order supply (expected receipts) and safety stock.

Two small additions that exist for the planner, not the stockroom:

- **ON_ORDER lots** make stock that is bought-but-not-delivered visible to netting.
  Without them the sourcing report sees only what has physically landed, so it tells
  you to order something that is already on a truck.
- **Safety stock** is held back from planning so coverage warns while there is still
  material to react with, rather than at the last unit.

The load-bearing property in both cases is *which* queries see the new state: planning
counts ON_ORDER as incoming, and consumption must never be able to pick it.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from Tracker.models import (
    BOM, BOMLine, Material, MaterialLot, PartTypes, Processes, Tenant,
    WorkOrder, WorkOrderStatus,
)
from Tracker.services.mes.consumption import available_quantity
from Tracker.services.mes.material_lot import (
    receive_expected_lot, record_expected_receipt,
)
from Tracker.services.mes.requirements import sourcing_requirements
from Tracker.tests.base import TenantContextMixin


class _MaterialFixture(TenantContextMixin, TestCase):
    """One assembly, one BUY line, one work order — the smallest shape that produces
    demand for a purchased material."""

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="OnOrder", slug="on-order", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.user = get_user_model().objects.create_user(
            username="s", email="s@c.test", password="x", tenant=self.tenant)
        self.asm = PartTypes.objects.create(tenant=self.tenant, name="Injector")
        self.proc = Processes.objects.create(
            tenant=self.tenant, name="P", part_type=self.asm,
            status="APPROVED", is_current_version=True)
        self.bom = BOM.objects.create(
            tenant=self.tenant, part_type=self.asm, revision="A",
            bom_type="ASSEMBLY", status="RELEASED", is_current_version=True)
        self.oring = Material.objects.create(
            tenant=self.tenant, name="O-Ring", purchase_lead_time_days=14)
        BOMLine.objects.create(
            tenant=self.tenant, bom=self.bom, material=self.oring,
            quantity=Decimal(2), source="BUY", line_number=1)

    def _work_order(self, qty=5, start=None):
        return WorkOrder.objects.create(
            tenant=self.tenant, ERP_id=f"WO-{qty}",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=qty,
            process=self.proc, expected_start=start or (date.today() + timedelta(days=30)))

    def _on_hand(self, qty, lot_number="L1"):
        return MaterialLot.objects.create(
            tenant=self.tenant, lot_number=lot_number, material=self.oring,
            received_date=date.today(), received_by=self.user,
            quantity=Decimal(qty), quantity_remaining=Decimal(qty),
            unit_of_measure="EA", status="ACCEPTED")


class ExpectedReceiptTests(_MaterialFixture):
    def test_creates_on_order_lot_with_placeholder_number(self):
        lot = record_expected_receipt(
            tenant=self.tenant, material=self.oring, quantity=Decimal(50),
            promised_date=date.today() + timedelta(days=10), erp_po_number="PO-77")

        self.assertEqual(lot.status, "ON_ORDER")
        self.assertEqual(lot.quantity_remaining, Decimal(50))
        self.assertEqual(lot.lot_number, "ONORDER-PO-77")
        # Nothing has been received, so there is no receipt date and no receiver.
        self.assertIsNone(lot.received_date)
        self.assertIsNone(lot.received_by)
        # Unit of measure falls back to the material's.
        self.assertEqual(lot.unit_of_measure, self.oring.unit_of_measure)

    def test_placeholder_numbers_do_not_collide(self):
        """Two lines on one PO, or two POs with no reference at all — the tenant-unique
        constraint on lot_number must still hold."""
        kw = dict(tenant=self.tenant, material=self.oring, quantity=Decimal(5),
                  promised_date=date.today() + timedelta(days=3), erp_po_number="PO-9")
        a = record_expected_receipt(**kw)
        b = record_expected_receipt(**kw)
        c = record_expected_receipt(**kw)
        self.assertEqual(len({a.lot_number, b.lot_number, c.lot_number}), 3)

    def test_promised_date_is_required(self):
        """An undated receipt cannot be placed in a bucket, so it would count as cover
        without ever landing — worse than not recording it."""
        with self.assertRaises(ValueError):
            record_expected_receipt(
                tenant=self.tenant, material=self.oring, quantity=Decimal(5),
                promised_date=None)

    def test_quantity_must_be_positive(self):
        with self.assertRaises(ValueError):
            record_expected_receipt(
                tenant=self.tenant, material=self.oring, quantity=Decimal(0),
                promised_date=date.today())

    def test_defaults_supplier_from_material(self):
        from Tracker.models import Companies
        supplier = Companies.objects.create(tenant=self.tenant, name="Acme Seals")
        self.oring.preferred_supplier = supplier
        self.oring.save(update_fields=["preferred_supplier"])

        lot = record_expected_receipt(
            tenant=self.tenant, material=self.oring, quantity=Decimal(5),
            promised_date=date.today() + timedelta(days=5))
        self.assertEqual(lot.supplier_id, supplier.id)

    def test_explicit_supplier_overrides_the_preferred_one(self):
        """Second-sourcing is normal — the preferred supplier is a default, not a rule."""
        from Tracker.models import Companies
        preferred = Companies.objects.create(tenant=self.tenant, name="Acme Seals")
        alternate = Companies.objects.create(tenant=self.tenant, name="Second Source Ltd")
        self.oring.preferred_supplier = preferred
        self.oring.save(update_fields=["preferred_supplier"])

        lot = record_expected_receipt(
            tenant=self.tenant, material=self.oring, quantity=Decimal(5),
            promised_date=date.today() + timedelta(days=5), supplier=alternate)
        self.assertEqual(lot.supplier_id, alternate.id)

    def test_supplier_and_promised_date_feed_on_time_delivery(self):
        """The point of carrying a supplier: OTD is scored as received_date <=
        promised_date across a supplier's dated lots, so an expectation that gets booked
        in becomes a real scorecard data point."""
        from Tracker.models import Companies
        from Tracker.services.qms.supplier_scorecard import compute_supplier_scorecard
        supplier = Companies.objects.create(tenant=self.tenant, name="Acme Seals")
        promised = date.today() + timedelta(days=7)

        lot = record_expected_receipt(
            tenant=self.tenant, material=self.oring, quantity=Decimal(10),
            promised_date=promised, supplier=supplier)
        receive_expected_lot(
            lot, lot_number="ACME-1", received_by=self.user,
            received_date=promised - timedelta(days=1))    # a day early

        card = compute_supplier_scorecard(supplier)
        self.assertEqual(card.promised_lots, 1)
        self.assertEqual(card.on_time_rate, 1.0)


class OnOrderCountsAsSupplyTests(_MaterialFixture):
    def test_on_order_covers_the_shortfall(self):
        """The whole point: stock on a truck stops the report demanding a second order."""
        self._work_order(qty=5)          # demand 10, nothing on hand
        short_before = [r for r in sourcing_requirements(self.tenant)['source']
                        if r['material'] == "O-Ring"]
        self.assertEqual(short_before[0]['qty_short'], 10)

        record_expected_receipt(
            tenant=self.tenant, material=self.oring, quantity=Decimal(10),
            promised_date=date.today() + timedelta(days=7), erp_po_number="PO-1")

        after = [r for r in sourcing_requirements(self.tenant)['source']
                 if r['material'] == "O-Ring"]
        self.assertEqual(after, [], "on-order stock should cover the shortfall")

    def test_partial_cover_leaves_the_remainder_short(self):
        self._work_order(qty=5)          # demand 10
        record_expected_receipt(
            tenant=self.tenant, material=self.oring, quantity=Decimal(4),
            promised_date=date.today() + timedelta(days=7))

        rows = [r for r in sourcing_requirements(self.tenant)['source']
                if r['material'] == "O-Ring"]
        self.assertEqual(rows[0]['qty_short'], 6)

    def test_on_order_stock_is_not_available_to_consume(self):
        """It must count as *incoming*, never as usable. Consumption and staging filter
        on an allowlist of ACCEPTED/IN_USE, which is what makes this safe."""
        record_expected_receipt(
            tenant=self.tenant, material=self.oring, quantity=Decimal(100),
            promised_date=date.today() + timedelta(days=7))
        self.assertEqual(available_quantity(self.oring.id, self.tenant), Decimal("0"))

    def test_on_hand_and_incoming_stay_disjoint(self):
        """Accepted stock must not be counted twice — once as held, once as promised."""
        self._work_order(qty=5)          # demand 10
        self._on_hand(6)
        record_expected_receipt(
            tenant=self.tenant, material=self.oring, quantity=Decimal(2),
            promised_date=date.today() + timedelta(days=7))

        rows = [r for r in sourcing_requirements(self.tenant)['source']
                if r['material'] == "O-Ring"]
        self.assertEqual(rows[0]['qty_short'], 2)   # 10 − 6 on hand − 2 on order


class ReceiveExpectedLotTests(_MaterialFixture):
    def _expect(self, qty=20):
        return record_expected_receipt(
            tenant=self.tenant, material=self.oring, quantity=Decimal(qty),
            promised_date=date.today() + timedelta(days=7), erp_po_number="PO-5")

    def test_receipt_stamps_real_lot_number_and_receiver(self):
        lot = receive_expected_lot(
            self._expect(), lot_number="SUP-A-4471", received_by=self.user)

        self.assertEqual(lot.status, "RECEIVED")
        self.assertEqual(lot.lot_number, "SUP-A-4471")
        self.assertEqual(lot.received_by_id, self.user.id)
        self.assertEqual(lot.received_date, date.today())

    def test_short_shipment_books_what_actually_arrived(self):
        lot = receive_expected_lot(
            self._expect(qty=20), lot_number="SUP-B", received_by=self.user,
            quantity=Decimal(17))
        self.assertEqual(lot.quantity, Decimal(17))
        self.assertEqual(lot.quantity_remaining, Decimal(17))

    def test_lands_at_received_not_accepted(self):
        """Incoming inspection still owns whether the stock is usable — receiving an
        expected lot must not smuggle it into consumable status."""
        lot = receive_expected_lot(
            self._expect(), lot_number="SUP-C", received_by=self.user)
        self.assertEqual(lot.status, "RECEIVED")
        self.assertEqual(available_quantity(self.oring.id, self.tenant), Decimal("0"))

    def test_refuses_a_lot_that_is_not_on_order(self):
        already_here = self._on_hand(5, lot_number="WALKIN-1")
        with self.assertRaises(ValueError):
            receive_expected_lot(
                already_here, lot_number="X", received_by=self.user)

    def test_requires_a_lot_number(self):
        with self.assertRaises(ValueError):
            receive_expected_lot(self._expect(), lot_number="", received_by=self.user)


class SafetyStockTests(_MaterialFixture):
    def test_buffer_is_held_back_from_coverage(self):
        """Stock that exactly covers demand is *not* covered once a buffer is reserved —
        that early warning is the entire purpose of the field."""
        self._work_order(qty=5)          # demand 10
        self._on_hand(10)
        self.assertEqual(
            [r for r in sourcing_requirements(self.tenant)['source']
             if r['material'] == "O-Ring"],
            [], "10 on hand covers demand of 10 with no buffer set")

        self.oring.safety_stock = Decimal(4)
        self.oring.save(update_fields=["safety_stock"])

        rows = [r for r in sourcing_requirements(self.tenant)['source']
                if r['material'] == "O-Ring"]
        self.assertEqual(rows[0]['qty_short'], 4)
        self.assertEqual(rows[0]['safety_stock'], 4.0)

    def test_unset_buffer_changes_nothing(self):
        self._work_order(qty=5)          # demand 10
        self._on_hand(10)
        self.assertIsNone(self.oring.safety_stock)
        self.assertEqual(
            [r for r in sourcing_requirements(self.tenant)['source']
             if r['material'] == "O-Ring"], [])

    def test_per_work_order_readout_reports_physical_on_hand(self):
        """The buffer changes what's *committable*, not what's on the shelf. A report
        that quietly shrank on_hand would have the picker and the planner arguing about
        the same bin."""
        from Tracker.services.mes.requirements import work_order_material_requirements
        self._on_hand(10)
        self.oring.safety_stock = Decimal(4)
        self.oring.save(update_fields=["safety_stock"])
        wo = self._work_order(qty=5)     # demand 10

        row = next(r for r in work_order_material_requirements(wo)['rows']
                   if r['component'] == "O-Ring")
        self.assertEqual(row['on_hand'], 10.0)       # physical count, unchanged
        self.assertEqual(row['safety_stock'], 4.0)
        self.assertEqual(row['short_qty'], 4.0)      # 10 − (10 − 4)
        self.assertEqual(row['status'], 'short')
