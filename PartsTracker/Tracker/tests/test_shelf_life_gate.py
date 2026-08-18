"""Material shelf-life unified under LifeTracking + the expired-material gate.

Covers UQMES task #9:
  * ``attach_shelf_life`` seeds a calendar LifeTracking record from the CoC date
    (absolute) or a material-type shelf-life definition (derived), and no-ops for
    materials with no shelf life.
  * The consumption backstop (``MaterialUsage.save`` → ``assert_lot_usable``) and
    the acceptance path (route soft-hold + ``accept``) block expired material.
  * ``extend_shelf_life`` is the governed release (reason + approver) and keeps the
    ``expiration_date`` mirror in sync.

The gate reads the LIVE ``is_blocked`` property (mirrors the part life-limit gate),
so calendar expiries are caught regardless of ``cached_status``.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from Tracker.models import (
    Companies,
    MaterialLot,
    MaterialUsage,
    Parts,
    PartTypes,
    Processes,
    ProcessStep,
    QualityReports,
    Steps,
    Tenant,
    WorkOrder,
    WorkOrderStatus,
)
from Tracker.models.life_tracking import (
    LifeLimitDefinition,
    LifeTracking,
    PartTypeLifeLimit,
)
from Tracker.services.life_tracking import shelf_life
from Tracker.services.qms import receiving_inspection
from Tracker.tests.base import TenantContextMixin


class ShelfLifeGateTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Shelf", slug="shelf-life", tier="PRO")
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        self.user = User.objects.create_user(
            username="op-shelf", email="shelf@c.test", password="x", tenant=self.tenant,
        )
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Adhesive")
        self.today = timezone.now().date()

    # ---- helpers -----------------------------------------------------------

    def _make_lot(self, *, material_type=None, manufacture_date=None,
                  expiration_date=None, lot_number="LOT-SL", qty="100"):
        return MaterialLot.objects.create(
            tenant=self.tenant, lot_number=lot_number, material_type=material_type,
            received_date=self.today, received_by=self.user,
            quantity=Decimal(qty), quantity_remaining=Decimal(qty), unit_of_measure="EA",
            manufacture_date=manufacture_date, expiration_date=expiration_date,
        )

    def _make_part(self):
        process = Processes.objects.create(tenant=self.tenant, name="P", part_type=self.pt)
        step = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name="Op1", step_type="TASK")
        ProcessStep.objects.create(process=process, step=step, order=1)
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-SL-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=1, process=process,
        )
        return Parts.objects.create(
            tenant=self.tenant, ERP_id="P-SL-1", part_type=self.pt, work_order=wo, step=step,
        )

    # ---- attach ------------------------------------------------------------

    def test_attach_from_absolute_expiration_date_expired(self):
        lot = self._make_lot(
            manufacture_date=self.today - timedelta(days=400),
            expiration_date=self.today - timedelta(days=35),
        )
        tracking = shelf_life.attach_shelf_life(lot)
        self.assertIsNotNone(tracking)
        self.assertTrue(tracking.definition.is_calendar_based)
        # override = (expiration - reference).days; current = days since reference.
        self.assertEqual(tracking.hard_limit_override, Decimal("365"))
        self.assertTrue(tracking.is_blocked)
        self.assertEqual(shelf_life.shelf_life_status(lot), "EXPIRED")

    def test_attach_from_absolute_expiration_date_fresh(self):
        lot = self._make_lot(
            manufacture_date=self.today, expiration_date=self.today + timedelta(days=365),
        )
        tracking = shelf_life.attach_shelf_life(lot)
        self.assertFalse(tracking.is_blocked)
        self.assertEqual(shelf_life.shelf_life_status(lot), "OK")

    def test_attach_derives_expiration_from_material_type_definition(self):
        shelf_def = LifeLimitDefinition.objects.create(
            tenant=self.tenant, name="Shelf Life", unit="days", unit_label="Days",
            is_calendar_based=True, hard_limit=Decimal("30"),
        )
        PartTypeLifeLimit.objects.create(part_type=self.pt, definition=shelf_def)
        lot = self._make_lot(material_type=self.pt, manufacture_date=self.today)
        tracking = shelf_life.attach_shelf_life(lot)
        self.assertIsNotNone(tracking)
        lot.refresh_from_db()
        # Derived from the type's 30-day shelf life.
        self.assertEqual(lot.expiration_date, self.today + timedelta(days=30))
        self.assertFalse(tracking.is_blocked)

    def test_attach_noop_when_no_shelf_life(self):
        lot = self._make_lot(material_type=self.pt)  # no date, no calendar def on type
        self.assertIsNone(shelf_life.attach_shelf_life(lot))
        self.assertIsNone(shelf_life.shelf_life_status(lot))

    def test_attach_is_idempotent(self):
        lot = self._make_lot(
            manufacture_date=self.today, expiration_date=self.today + timedelta(days=100),
        )
        shelf_life.attach_shelf_life(lot)
        shelf_life.attach_shelf_life(lot)
        self.assertEqual(LifeTracking.objects.for_object(lot).count(), 1)

    # ---- consumption backstop ---------------------------------------------

    def test_consume_fresh_lot_succeeds_and_decrements(self):
        lot = self._make_lot(
            manufacture_date=self.today, expiration_date=self.today + timedelta(days=365),
        )
        shelf_life.attach_shelf_life(lot)
        part = self._make_part()
        MaterialUsage.objects.create(
            tenant=self.tenant, lot=lot, part=part,
            qty_consumed=Decimal("10"), consumed_by=self.user,
        )
        lot.refresh_from_db()
        self.assertEqual(lot.quantity_remaining, Decimal("90.0000"))

    def test_consume_expired_lot_is_blocked(self):
        lot = self._make_lot(
            manufacture_date=self.today - timedelta(days=400),
            expiration_date=self.today - timedelta(days=35),
        )
        shelf_life.attach_shelf_life(lot)
        part = self._make_part()
        with self.assertRaises(ValueError):
            MaterialUsage.objects.create(
                tenant=self.tenant, lot=lot, part=part,
                qty_consumed=Decimal("10"), consumed_by=self.user,
            )
        lot.refresh_from_db()
        self.assertEqual(lot.quantity_remaining, Decimal("100.0000"), "balance untouched")

    # ---- acceptance path ---------------------------------------------------

    def test_route_soft_holds_expired_on_arrival(self):
        lot = self._make_lot(
            manufacture_date=self.today - timedelta(days=400),
            expiration_date=self.today - timedelta(days=35),
        )
        receiving_inspection.route_received_lot(lot, self.user)
        lot.refresh_from_db()
        self.assertEqual(lot.status, "QUARANTINE")
        self.assertEqual(lot.hold_reason, receiving_inspection.HOLD_SHELF_LIFE_EXPIRED)

    def test_accept_expired_lot_quarantines_and_raises(self):
        lot = self._make_lot(
            manufacture_date=self.today - timedelta(days=400),
            expiration_date=self.today - timedelta(days=35),
        )
        shelf_life.attach_shelf_life(lot)
        lot.status = "AWAITING_INSPECTION"
        lot.save(update_fields=["status"])
        report = QualityReports.objects.create(
            tenant=self.tenant, material_lot=lot, status="PASS",
        )
        with self.assertRaises(ValueError):
            receiving_inspection.accept(report, self.user)
        lot.refresh_from_db()
        self.assertEqual(lot.status, "QUARANTINE")
        self.assertEqual(lot.hold_reason, receiving_inspection.HOLD_SHELF_LIFE_EXPIRED)

    # ---- governed extension ------------------------------------------------

    def test_extend_shelf_life_unblocks_and_syncs_date(self):
        lot = self._make_lot(
            manufacture_date=self.today - timedelta(days=400),
            expiration_date=self.today - timedelta(days=35),
        )
        shelf_life.attach_shelf_life(lot)
        self.assertTrue(shelf_life.is_lot_shelf_life_expired(lot))
        new_date = self.today + timedelta(days=30)
        tracking = shelf_life.extend_shelf_life(
            lot, new_expiration_date=new_date, reason="Re-tested viscosity OK", approved_by=self.user,
        )
        lot.refresh_from_db()
        self.assertEqual(lot.expiration_date, new_date)
        self.assertFalse(tracking.is_blocked)
        self.assertFalse(shelf_life.is_lot_shelf_life_expired(lot))
        self.assertEqual(tracking.override_reason, "Re-tested viscosity OK")
        self.assertEqual(tracking.override_approved_by_id, self.user.id)

    def test_extend_requalifies_a_shelf_life_quarantined_lot(self):
        lot = self._make_lot(
            manufacture_date=self.today - timedelta(days=400),
            expiration_date=self.today - timedelta(days=35),
        )
        receiving_inspection.route_received_lot(lot, self.user)
        lot.refresh_from_db()
        self.assertEqual(lot.status, "QUARANTINE")
        shelf_life.extend_shelf_life(
            lot, new_expiration_date=self.today + timedelta(days=30),
            reason="Re-tested", approved_by=self.user,
        )
        lot.refresh_from_db()
        # Un-expired + re-qualified back into the receiving flow.
        self.assertEqual(lot.status, "RECEIVED")
        self.assertEqual(lot.hold_reason, "")

    def test_extend_requires_reason(self):
        lot = self._make_lot(
            manufacture_date=self.today, expiration_date=self.today + timedelta(days=10),
        )
        shelf_life.attach_shelf_life(lot)
        with self.assertRaises(ValueError):
            shelf_life.extend_shelf_life(
                lot, new_expiration_date=self.today + timedelta(days=100), reason="",
            )

    def test_extend_without_tracking_raises(self):
        lot = self._make_lot()  # no shelf life attached
        with self.assertRaises(ValueError):
            shelf_life.extend_shelf_life(
                lot, new_expiration_date=self.today + timedelta(days=100), reason="x",
            )
