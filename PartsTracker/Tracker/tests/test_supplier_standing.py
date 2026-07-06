"""Supplier standing — scorecard → recommend-only qualification review.

Key invariant under test: `evaluate_supplier_standing` / `review_and_notify` recommend
but NEVER transition a qualification (recommend-only mode).
"""
import datetime
from decimal import Decimal

from Tracker.tests.base import TenantTestCase
from Tracker.models import Companies, PartTypes, MaterialLot, SupplierQualification
from Tracker.services.qms import supplier_qualification as qual_svc
from Tracker.services.qms import supplier_standing as svc


class SupplierStandingTests(TenantTestCase):
    _counter = 0

    def setUp(self):
        super().setUp()
        self.supplier = Companies.objects.create(tenant=self.tenant_a, name="Acme", description="")
        self.part_type = PartTypes.objects.create(tenant=self.tenant_a, name="Gear")

    def _lots(self, *, accepted=0, rejected=0, coc=True, promised=None, received=None):
        received = received or datetime.date(2026, 1, 1)
        for status, k in (("ACCEPTED", accepted), ("REJECTED", rejected)):
            for _ in range(k):
                SupplierStandingTests._counter += 1
                MaterialLot.objects.create(
                    tenant=self.tenant_a, lot_number=f"LOT-{SupplierStandingTests._counter}",
                    received_date=received, received_by=self.user_a,
                    quantity=Decimal("10"), quantity_remaining=Decimal("10"), unit_of_measure="EA",
                    status=status, material_type=self.part_type, supplier=self.supplier,
                    certificate_of_conformance=("CoC-1" if coc else ""),
                    promised_date=promised,
                )

    def _grant(self, *, conditional=False):
        q = qual_svc.open_qualification(supplier=self.supplier, part_type=self.part_type, user=self.user_a)
        qual_svc.grant(q, user=self.user_a, conditional=conditional, expiry_date=datetime.date(2099, 1, 1))
        return q

    # --- recommendations -----------------------------------------------------

    def test_within_thresholds_no_recommendation(self):
        self._grant()
        self._lots(accepted=10)  # 0 rejects, CoC on all, no promise → scorecard A, all approved
        rec = svc.evaluate_supplier_standing(self.supplier)
        self.assertEqual(rec.rating, "A")
        self.assertEqual(rec.recommended_action, svc.ACTION_NONE)

    def test_high_reject_recommends_suspend(self):
        q = self._grant()
        self._lots(accepted=8, rejected=2)  # reject_rate 0.20 ≥ 0.10 → C
        rec = svc.evaluate_supplier_standing(self.supplier)
        self.assertEqual(rec.rating, "C")
        self.assertEqual(rec.recommended_action, svc.ACTION_REVIEW_SUSPEND)
        # RECOMMEND-ONLY invariant: the qualification is untouched.
        q.refresh_from_db()
        self.assertEqual(q.status, "APPROVED")

    def test_late_delivery_recommends_conditional(self):
        self._grant()
        # All accepted (reject 0), but every lot late → on-time 0% < 85% → C without reject/SCAR.
        self._lots(accepted=5, promised=datetime.date(2026, 1, 1), received=datetime.date(2026, 2, 1))
        rec = svc.evaluate_supplier_standing(self.supplier)
        self.assertEqual(rec.rating, "C")
        self.assertEqual(rec.recommended_action, svc.ACTION_REVIEW_CONDITIONAL)

    def test_recovery_recommends_restore(self):
        q = self._grant(conditional=True)  # currently CONDITIONAL
        self._lots(accepted=10)            # metrics now clean → scorecard A
        rec = svc.evaluate_supplier_standing(self.supplier)
        self.assertEqual(rec.rating, "A")
        self.assertEqual(rec.recommended_action, svc.ACTION_REVIEW_RESTORE)
        q.refresh_from_db()
        self.assertEqual(q.status, "CONDITIONAL")  # unchanged — recommend only

    def test_no_history_no_recommendation(self):
        self._grant()
        rec = svc.evaluate_supplier_standing(self.supplier)  # no lots → rating None
        self.assertIsNone(rec.rating)
        self.assertEqual(rec.recommended_action, svc.ACTION_NONE)

    # --- review_and_notify ---------------------------------------------------

    def test_review_and_notify_flagged_does_not_transition(self):
        q = self._grant()
        self._lots(accepted=8, rejected=2)
        rec = svc.review_and_notify(self.supplier)  # emits supplier.standing_review
        self.assertEqual(rec.recommended_action, svc.ACTION_REVIEW_SUSPEND)
        q.refresh_from_db()
        self.assertEqual(q.status, "APPROVED")  # still not transitioned

    def test_review_and_notify_clean_is_noop(self):
        self._grant()
        self._lots(accepted=10)
        rec = svc.review_and_notify(self.supplier)
        self.assertEqual(rec.recommended_action, svc.ACTION_NONE)
