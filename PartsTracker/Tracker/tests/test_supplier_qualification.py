"""Supplier qualification (ASL) lifecycle + receiving qualification-gate tests."""
import datetime
from decimal import Decimal

from Tracker.tests.base import TenantTestCase
from Tracker.models import Companies, PartTypes, MaterialLot, SupplierQualification
from Tracker.services.qms import supplier_qualification as svc
from Tracker.services.qms import receiving_inspection


class SupplierQualificationServiceTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.supplier = Companies.objects.create(tenant=self.tenant_a, name="Great Lakes Diesel", description="")
        self.part_type = PartTypes.objects.create(tenant=self.tenant_a, name="Gear")

    def _open(self, **kw):
        return svc.open_qualification(
            supplier=self.supplier, part_type=self.part_type, basis="AUDIT", user=self.user_a, **kw)

    def _qualified(self):
        return svc.is_supplier_qualified(supplier=self.supplier, part_type=self.part_type)

    def test_open_creates_pending_with_number(self):
        q = self._open()
        self.assertEqual(q.status, "PENDING")
        self.assertTrue(q.qualification_number.startswith("SQUAL-"))
        self.assertFalse(self._qualified())  # PENDING is not active

    def test_grant_qualifies(self):
        svc.grant(self._open(), user=self.user_a, expiry_date=datetime.date(2099, 1, 1))
        self.assertTrue(self._qualified())

    def test_conditional_is_active(self):
        svc.grant(self._open(), user=self.user_a, conditional=True)
        q = svc.qualifying_record_for(supplier=self.supplier, part_type=self.part_type)
        self.assertEqual(q.status, "CONDITIONAL")

    def test_expired_excluded(self):
        svc.grant(self._open(), user=self.user_a,
                  effective_date=datetime.date(2020, 1, 1), expiry_date=datetime.date(2020, 2, 1))
        self.assertFalse(self._qualified())

    def test_suspend_and_disqualify(self):
        q = self._open()
        svc.grant(q, user=self.user_a)
        svc.suspend(q, user=self.user_a, reason="late deliveries")
        self.assertEqual(q.status, "SUSPENDED")
        self.assertFalse(self._qualified())
        svc.disqualify(q, user=self.user_a)
        self.assertEqual(q.status, "DISQUALIFIED")
        with self.assertRaises(ValueError):
            svc.grant(q, user=self.user_a)

    def test_scope_mismatch_does_not_cover(self):
        other = PartTypes.objects.create(tenant=self.tenant_a, name="Bracket")
        svc.grant(svc.open_qualification(supplier=self.supplier, part_type=other, user=self.user_a),
                  user=self.user_a)
        self.assertFalse(self._qualified())  # qualified for Bracket, not Gear

    def test_resolve_status_dto(self):
        svc.grant(self._open(), user=self.user_a, expiry_date=datetime.date(2099, 1, 1))
        st = svc.resolve_status(supplier=self.supplier, part_type=self.part_type)
        self.assertTrue(st.qualified)
        self.assertEqual(st.status, "APPROVED")
        self.assertGreater(st.days_to_expiry, 0)

    def test_expire_task_logic(self):
        q = self._open()
        svc.grant(q, user=self.user_a, expiry_date=datetime.date(2020, 1, 1))
        # past-expiry record is still APPROVED until expire() runs, but not "active"
        self.assertFalse(self._qualified())
        svc.expire(q)
        self.assertEqual(q.status, "EXPIRED")

    def test_expire_emits_notification(self):
        from Tracker.services.core.notifications.emit import notification_event
        seen = []
        receiver = lambda sender, **kw: seen.append(kw.get("event_code"))
        notification_event.connect(receiver, weak=False)
        try:
            q = self._open()
            svc.grant(q, user=self.user_a, expiry_date=datetime.date(2020, 1, 1))
            svc.expire(q)
        finally:
            notification_event.disconnect(receiver)
        self.assertIn("supplier.qualification_expired", seen)


class ReceivingQualificationGateTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.supplier = Companies.objects.create(tenant=self.tenant_a, name="Acme", description="")
        self.part_type = PartTypes.objects.create(
            tenant=self.tenant_a, name="Gear", requires_supplier_qualification=True)

    def _lot(self):
        return MaterialLot.objects.create(
            tenant=self.tenant_a, lot_number="LOT-Q", received_date=datetime.date(2026, 1, 1),
            received_by=self.user_a, quantity=Decimal("100"), quantity_remaining=Decimal("100"),
            unit_of_measure="EA", status="RECEIVED", material_type=self.part_type, supplier=self.supplier)

    def test_unqualified_supplier_is_held(self):
        lot = self._lot()
        receiving_inspection.route_received_lot(lot, self.user_a)
        lot.refresh_from_db()
        self.assertEqual(lot.status, "QUARANTINE")

    def test_qualified_supplier_passes(self):
        svc.grant(svc.open_qualification(supplier=self.supplier, part_type=self.part_type, user=self.user_a),
                  user=self.user_a)
        lot = self._lot()
        receiving_inspection.route_received_lot(lot, self.user_a)
        lot.refresh_from_db()
        # No RECEIVING step configured -> dock-to-stock, not held.
        self.assertEqual(lot.status, "ACCEPTED")

    def test_flag_off_not_held(self):
        self.part_type.requires_supplier_qualification = False
        self.part_type.save()
        lot = self._lot()
        receiving_inspection.route_received_lot(lot, self.user_a)
        lot.refresh_from_db()
        self.assertEqual(lot.status, "ACCEPTED")
