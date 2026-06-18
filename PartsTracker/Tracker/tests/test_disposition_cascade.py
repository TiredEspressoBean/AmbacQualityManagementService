"""Regression tests for the QuarantineDisposition -> Parts status cascade.

`QuarantineDisposition._update_part_status()` was dead code: a case mismatch
(lowercase state/type keys vs. the uppercase STATE_CHOICES / DISPOSITION_TYPES
values) made the guard always early-return, so choosing a disposition type
never moved the part. These tests lock in the fixed uppercase behavior so the
cascade can't silently regress.
"""
from Tracker.models import (
    Companies,
    Orders,
    OrdersStatus,
    Parts,
    PartsStatus,
    QuarantineDisposition,
    Tenant,
)
from Tracker.tests.base import TenantContextMixin, VectorTestCase


class DispositionPartStatusCascadeTests(TenantContextMixin, VectorTestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(
            name="Disp Cascade", slug="disp-cascade", tier="PRO"
        )
        self.set_tenant_context(self.tenant)
        self.company = Companies.objects.create(tenant=self.tenant, name="Acme")
        self.order = Orders.objects.create(
            tenant=self.tenant,
            name="ORD-DISP",
            company=self.company,
            order_status=OrdersStatus.IN_PROGRESS,
        )

    def _make_part(self, erp):
        return Parts.objects.create(
            tenant=self.tenant, ERP_id=erp, work_order=None, order=self.order,
        )

    def _disposition(self, part, disposition_type):
        # Creating with a disposition_type set auto-transitions OPEN ->
        # IN_PROGRESS in save(), which is what applies the decision to the part.
        return QuarantineDisposition.objects.create(
            tenant=self.tenant,
            part=part,
            disposition_type=disposition_type,
            description="regression fixture",
        )

    def test_rework_moves_part_to_rework_needed_and_increments_counter(self):
        part = self._make_part("P-RW")
        self.assertEqual(part.part_status, PartsStatus.PENDING)
        self.assertEqual(part.total_rework_count, 0)

        self._disposition(part, "REWORK")

        part.refresh_from_db()
        self.assertEqual(part.part_status, PartsStatus.REWORK_NEEDED)
        self.assertEqual(part.total_rework_count, 1)

    def test_repair_moves_part_to_rework_needed_and_increments_counter(self):
        part = self._make_part("P-RP")
        self._disposition(part, "REPAIR")

        part.refresh_from_db()
        self.assertEqual(part.part_status, PartsStatus.REWORK_NEEDED)
        self.assertEqual(part.total_rework_count, 1)

    def test_scrap_moves_part_to_scrapped_without_incrementing_rework(self):
        part = self._make_part("P-SC")
        self._disposition(part, "SCRAP")

        part.refresh_from_db()
        self.assertEqual(part.part_status, PartsStatus.SCRAPPED)
        self.assertEqual(part.total_rework_count, 0)

    def test_use_as_is_moves_part_to_ready(self):
        part = self._make_part("P-UAI")
        self._disposition(part, "USE_AS_IS")

        part.refresh_from_db()
        self.assertEqual(part.part_status, PartsStatus.READY_FOR_NEXT_STEP)

    def test_return_to_supplier_cancels_part(self):
        part = self._make_part("P-RTS")
        self._disposition(part, "RETURN_TO_SUPPLIER")

        part.refresh_from_db()
        self.assertEqual(part.part_status, PartsStatus.CANCELLED)

    def test_open_disposition_without_type_does_not_change_part(self):
        """Guard: an OPEN disposition with no type set must not touch the part."""
        part = self._make_part("P-OPEN")
        QuarantineDisposition.objects.create(
            tenant=self.tenant,
            part=part,
            description="open, no disposition type yet",
        )

        part.refresh_from_db()
        self.assertEqual(part.part_status, PartsStatus.PENDING)
        self.assertEqual(part.total_rework_count, 0)

    def test_close_after_rework_does_not_re_increment_or_regress(self):
        """Closing a REWORK disposition must NOT re-fire the cascade: no double
        rework count, and a part that moved on independently is not regressed.
        The decision applies on type-set, not on close."""
        part = self._make_part("P-CLOSE")
        disp = self._disposition(part, "REWORK")
        part.refresh_from_db()
        self.assertEqual(part.part_status, PartsStatus.REWORK_NEEDED)
        self.assertEqual(part.total_rework_count, 1)

        # The part moves on independently (e.g. operator picks up the rework).
        part.part_status = PartsStatus.IN_PROGRESS
        part.save(update_fields=["part_status"])

        # Closing the disposition (state change only, type unchanged) must not
        # touch the part again.
        disp.current_state = "CLOSED"
        disp.save()

        part.refresh_from_db()
        self.assertEqual(part.part_status, PartsStatus.IN_PROGRESS)  # not regressed
        self.assertEqual(part.total_rework_count, 1)  # not re-incremented

    def test_type_correction_applies_the_new_decision(self):
        """Changing the disposition_type (e.g. REWORK -> SCRAP) re-applies to the part."""
        part = self._make_part("P-CORRECT")
        disp = self._disposition(part, "REWORK")
        part.refresh_from_db()
        self.assertEqual(part.part_status, PartsStatus.REWORK_NEEDED)

        disp.disposition_type = "SCRAP"
        disp.save()

        part.refresh_from_db()
        self.assertEqual(part.part_status, PartsStatus.SCRAPPED)

    def test_close_service_completes_in_progress_disposition(self):
        """0c: complete_disposition_resolution closes an IN_PROGRESS disposition
        instead of raising on the (previously lowercase-buggy) blocker check."""
        from django.contrib.auth import get_user_model
        from Tracker.services.qms.disposition import complete_disposition_resolution

        part = self._make_part("P-COMPLETE")
        # MINOR severity → no containment requirement, so this stays focused on
        # the close service (containment gating is covered separately, 2f).
        disp = QuarantineDisposition.objects.create(
            tenant=self.tenant, part=part, disposition_type="USE_AS_IS",
            severity="MINOR", description="close-service test",
        )
        self.assertEqual(disp.current_state, "IN_PROGRESS")

        User = get_user_model()
        user = User.objects.create_user(
            username="qa-close", email="qa@close.test", password="x", tenant=self.tenant,
        )
        complete_disposition_resolution(disp, user)

        disp.refresh_from_db()
        self.assertEqual(disp.current_state, "CLOSED")
        self.assertTrue(disp.resolution_completed)

    # ----- 2a: terminal-dominant precedence -----

    def test_scrap_dominates_later_rework_cannot_un_scrap(self):
        """2a: once SCRAP sets the part terminal, a later (less-severe) REWORK
        disposition must NOT pull it back to REWORK_NEEDED."""
        part = self._make_part("P-PRECEDENCE")
        self._disposition(part, "SCRAP")
        part.refresh_from_db()
        self.assertEqual(part.part_status, PartsStatus.SCRAPPED)

        # A second disposition (a distinct defect) decides REWORK — must not regress.
        self._disposition(part, "REWORK")
        part.refresh_from_db()
        self.assertEqual(part.part_status, PartsStatus.SCRAPPED)
        self.assertEqual(part.total_rework_count, 0)  # never entered rework

    def test_scrap_dominates_a_use_as_is_part(self):
        """2a: SCRAP (terminal) applies over a part a USE_AS_IS disposition set READY."""
        part = self._make_part("P-SCRAP-WINS")
        self._disposition(part, "USE_AS_IS")
        part.refresh_from_db()
        self.assertEqual(part.part_status, PartsStatus.READY_FOR_NEXT_STEP)

        self._disposition(part, "SCRAP")
        part.refresh_from_db()
        self.assertEqual(part.part_status, PartsStatus.SCRAPPED)

    # ----- 2f: containment gate (Level 1) -----

    def test_major_disposition_needs_containment_to_close(self):
        """2f: a CRITICAL/MAJOR disposition can't complete until a containment
        action is recorded; once it is, it closes."""
        from django.contrib.auth import get_user_model
        from Tracker.services.qms.disposition import complete_disposition_resolution

        part = self._make_part("P-CONTAIN")
        disp = QuarantineDisposition.objects.create(
            tenant=self.tenant, part=part, disposition_type="USE_AS_IS",
            severity="MAJOR", description="major, no containment yet",
        )
        User = get_user_model()
        user = User.objects.create_user(
            username="qa-contain", email="qa@contain.test", password="x", tenant=self.tenant,
        )

        with self.assertRaises(ValueError):
            complete_disposition_resolution(disp, user)
        disp.refresh_from_db()
        self.assertEqual(disp.current_state, "IN_PROGRESS")  # blocked, not closed

        disp.containment_action = "Quarantined sibling lot LOT-42 and re-inspected the run."
        disp.save(update_fields=["containment_action"])
        complete_disposition_resolution(disp, user)

        disp.refresh_from_db()
        self.assertEqual(disp.current_state, "CLOSED")
