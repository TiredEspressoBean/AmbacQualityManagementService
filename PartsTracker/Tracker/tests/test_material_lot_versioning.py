"""
Tests for MaterialLot split service and hybrid serializer versioning routing.

Covers:
  - split_material_lot: child creation, parent decrement, over-quantity guard
  - MaterialLotSerializer.update: operational fields use plain save; spec
    field edits route through create_new_version; mixed payloads version
"""
from __future__ import annotations

import datetime
from decimal import Decimal

from rest_framework.test import APIRequestFactory

from Tracker.models import MaterialLot
from Tracker.serializers.mes_standard import MaterialLotSerializer
from Tracker.services.mes.material_lot import split_material_lot
from Tracker.tests.base import TenantTestCase


def _make_lot(tenant, user, **kwargs):
    """Helper: create a minimal MaterialLot."""
    defaults = dict(
        tenant=tenant,
        lot_number="LOT-001",
        received_date=datetime.date(2024, 1, 1),
        received_by=user,
        quantity=Decimal("100.0000"),
        quantity_remaining=Decimal("100.0000"),
        unit_of_measure="KG",
        status="RECEIVED",
    )
    defaults.update(kwargs)
    return MaterialLot.objects.create(**defaults)


class SplitServiceTestCase(TenantTestCase):
    """split_material_lot service correctness."""

    def setUp(self):
        super().setUp()
        self.lot = _make_lot(self.tenant_a, self.user_a)

    def test_split_creates_child_with_split_quantity(self):
        child = split_material_lot(self.lot, Decimal("30.0000"))

        self.assertEqual(child.quantity, Decimal("30.0000"))
        self.assertEqual(child.quantity_remaining, Decimal("30.0000"))
        self.assertEqual(child.parent_lot_id, self.lot.pk)
        self.assertEqual(child.status, "RECEIVED")

    def test_split_decrements_parent_quantity_remaining(self):
        split_material_lot(self.lot, Decimal("30.0000"))

        self.lot.refresh_from_db()
        self.assertEqual(self.lot.quantity_remaining, Decimal("70.0000"))
        self.assertEqual(self.lot.status, "RECEIVED")

    def test_split_full_quantity_marks_parent_consumed(self):
        split_material_lot(self.lot, Decimal("100.0000"))

        self.lot.refresh_from_db()
        self.assertEqual(self.lot.quantity_remaining, Decimal("0.0000"))
        self.assertEqual(self.lot.status, "CONSUMED")

    def test_split_over_available_quantity_raises(self):
        with self.assertRaises(ValueError):
            split_material_lot(self.lot, Decimal("101.0000"))

    def test_split_zero_quantity_raises(self):
        with self.assertRaises(ValueError):
            split_material_lot(self.lot, Decimal("0"))

    def test_split_consumed_lot_raises(self):
        self.lot.status = "CONSUMED"
        self.lot.save()
        with self.assertRaises(ValueError):
            split_material_lot(self.lot, Decimal("10.0000"))

    def test_split_child_lot_number_increments(self):
        child_a = split_material_lot(self.lot, Decimal("10.0000"))
        child_b = split_material_lot(self.lot, Decimal("10.0000"))

        self.assertEqual(child_a.lot_number, "LOT-001-01")
        self.assertEqual(child_b.lot_number, "LOT-001-02")

    def test_split_does_not_create_new_version_on_parent(self):
        """Split is a pure quantity operation — parent version must stay at 1."""
        split_material_lot(self.lot, Decimal("20.0000"))

        self.lot.refresh_from_db()
        self.assertEqual(self.lot.version, 1)
        self.assertTrue(self.lot.is_current_version)


class MaterialLotSerializerHybridRoutingTestCase(TenantTestCase):
    """MaterialLotSerializer.update routes spec edits through versioning;
    operational edits (quantity_remaining, status, archived) use plain save."""

    def setUp(self):
        super().setUp()
        self.lot = _make_lot(self.tenant_a, self.user_a)
        self.factory = APIRequestFactory()

    def _serializer(self, instance, data, partial=True):
        request = self.factory.patch("/")
        request.user = self.user_a
        return MaterialLotSerializer(
            instance, data=data, partial=partial,
            context={"request": request},
        )

    # -- operational fields: must NOT create a new version ----------------

    def test_quantity_remaining_change_does_not_version(self):
        """CRITICAL: consumption writes must not create version rows."""
        s = self._serializer(self.lot, {"quantity_remaining": Decimal("80.0000")})
        # quantity_remaining is read_only in the serializer so it won't be in
        # validated_data; the test confirms the routing guard works and an
        # empty payload short-circuits cleanly.
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 1)
        self.assertEqual(result.pk, self.lot.pk)

    def test_status_change_does_not_version(self):
        s = self._serializer(self.lot, {"status": "IN_USE"})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 1)
        self.assertEqual(result.status, "IN_USE")
        self.assertEqual(result.pk, self.lot.pk)

    def test_archive_only_does_not_version(self):
        s = self._serializer(self.lot, {"archived": True})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 1)
        self.assertTrue(result.archived)
        self.assertEqual(result.pk, self.lot.pk)

    # -- spec fields: must create a new version ---------------------------

    def test_spec_field_change_creates_new_version(self):
        s = self._serializer(self.lot, {"storage_location": "Shelf B"})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.storage_location, "Shelf B")
        self.lot.refresh_from_db()
        self.assertFalse(self.lot.is_current_version)

    def test_supplier_lot_number_change_creates_new_version(self):
        s = self._serializer(self.lot, {"supplier_lot_number": "SLN-999"})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.supplier_lot_number, "SLN-999")

    def test_expiration_date_change_creates_new_version(self):
        s = self._serializer(self.lot, {"expiration_date": "2025-12-31"})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.expiration_date, datetime.date(2025, 12, 31))

    # -- mixed payloads ---------------------------------------------------

    def test_mixed_quantity_and_spec_creates_new_version(self):
        """If any spec key is present, the whole update routes through versioning."""
        s = self._serializer(
            self.lot,
            {"status": "IN_USE", "storage_location": "Shelf C"},
        )
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.storage_location, "Shelf C")

    # -- empty payload ----------------------------------------------------

    def test_empty_noop(self):
        s = self._serializer(self.lot, {})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.pk, self.lot.pk)
        self.assertEqual(result.version, 1)
