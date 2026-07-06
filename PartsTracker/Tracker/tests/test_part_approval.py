"""Part-approval (PPAP/FAI) lifecycle + receiving approval-gate tests."""
import datetime
from decimal import Decimal

from Tracker.tests.base import TenantTestCase
from Tracker.models import Companies, PartTypes, MaterialLot, PartApproval
from Tracker.services.qms import part_approval as svc
from Tracker.services.qms import receiving_inspection


class PartApprovalServiceTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.supplier = Companies.objects.create(tenant=self.tenant_a, name="Great Lakes Diesel", description="")
        self.part_type = PartTypes.objects.create(tenant=self.tenant_a, name="Gear")

    def _open(self, **kw):
        return svc.open_approval(
            part_type=self.part_type, supplier=self.supplier, user=self.user_a, **kw)

    def _approved(self):
        return svc.is_part_approved(part_type=self.part_type, supplier=self.supplier)

    def test_open_creates_pending_with_number(self):
        a = self._open()
        self.assertEqual(a.status, "PENDING")
        self.assertTrue(a.approval_number.startswith("PA-"))
        self.assertFalse(self._approved())  # PENDING is not active

    def test_grant_approves(self):
        svc.grant(self._open(), user=self.user_a, expiry_date=datetime.date(2099, 1, 1))
        self.assertTrue(self._approved())

    def test_conditional_is_active(self):
        svc.grant(self._open(), user=self.user_a, conditional=True)
        a = svc.approving_record_for(part_type=self.part_type, supplier=self.supplier)
        self.assertEqual(a.status, "CONDITIONAL")

    def test_expired_excluded(self):
        svc.grant(self._open(), user=self.user_a,
                  effective_date=datetime.date(2020, 1, 1), expiry_date=datetime.date(2020, 2, 1))
        self.assertFalse(self._approved())

    def test_suspend_and_disqualify(self):
        a = self._open()
        svc.grant(a, user=self.user_a)
        svc.suspend(a, user=self.user_a, reason="drawing revision pending")
        self.assertEqual(a.status, "SUSPENDED")
        self.assertFalse(self._approved())
        svc.disqualify(a, user=self.user_a)
        self.assertEqual(a.status, "DISQUALIFIED")
        with self.assertRaises(ValueError):
            svc.grant(a, user=self.user_a)

    def test_scope_mismatch_does_not_cover(self):
        other = PartTypes.objects.create(tenant=self.tenant_a, name="Bracket")
        svc.grant(svc.open_approval(part_type=other, supplier=self.supplier, user=self.user_a),
                  user=self.user_a)
        self.assertFalse(self._approved())  # approved for Bracket, not Gear

    def test_supplier_mismatch_does_not_cover(self):
        other_supplier = Companies.objects.create(tenant=self.tenant_a, name="Acme", description="")
        svc.grant(svc.open_approval(part_type=self.part_type, supplier=other_supplier, user=self.user_a),
                  user=self.user_a)
        self.assertFalse(self._approved())  # approved for Acme, not Great Lakes

    def test_resolve_status_dto(self):
        svc.grant(self._open(approval_type=PartApproval.APPROVAL_FAI),
                  user=self.user_a, expiry_date=datetime.date(2099, 1, 1))
        st = svc.resolve_status(part_type=self.part_type, supplier=self.supplier)
        self.assertTrue(st.approved)
        self.assertEqual(st.status, "APPROVED")
        self.assertEqual(st.approval_type, "FAI")
        self.assertGreater(st.days_to_expiry, 0)

    def test_expire_task_logic(self):
        a = self._open()
        svc.grant(a, user=self.user_a, expiry_date=datetime.date(2020, 1, 1))
        # past-expiry record is still APPROVED until expire() runs, but not "active"
        self.assertFalse(self._approved())
        svc.expire(a)
        self.assertEqual(a.status, "EXPIRED")


class ReceivingApprovalGateTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.supplier = Companies.objects.create(tenant=self.tenant_a, name="Acme", description="")
        self.part_type = PartTypes.objects.create(
            tenant=self.tenant_a, name="Gear", requires_part_approval=True)

    def _lot(self):
        return MaterialLot.objects.create(
            tenant=self.tenant_a, lot_number="LOT-PA", received_date=datetime.date(2026, 1, 1),
            received_by=self.user_a, quantity=Decimal("100"), quantity_remaining=Decimal("100"),
            unit_of_measure="EA", status="RECEIVED", material_type=self.part_type, supplier=self.supplier)

    def test_unapproved_part_is_held(self):
        lot = self._lot()
        receiving_inspection.route_received_lot(lot, self.user_a)
        lot.refresh_from_db()
        self.assertEqual(lot.status, "QUARANTINE")
        self.assertEqual(lot.hold_reason, "PART_UNAPPROVED")

    def test_approved_part_passes(self):
        svc.grant(svc.open_approval(part_type=self.part_type, supplier=self.supplier, user=self.user_a),
                  user=self.user_a)
        lot = self._lot()
        receiving_inspection.route_received_lot(lot, self.user_a)
        lot.refresh_from_db()
        # No RECEIVING step configured -> dock-to-stock, not held.
        self.assertEqual(lot.status, "ACCEPTED")

    def test_flag_off_not_held(self):
        self.part_type.requires_part_approval = False
        self.part_type.save()
        lot = self._lot()
        receiving_inspection.route_received_lot(lot, self.user_a)
        lot.refresh_from_db()
        self.assertEqual(lot.status, "ACCEPTED")
