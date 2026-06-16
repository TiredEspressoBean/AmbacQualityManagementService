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
        # IN_PROGRESS in save(), which is what fires _update_part_status.
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
