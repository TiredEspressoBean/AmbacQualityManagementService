"""
Serializer routing tests for the four MES Standard leaf models that are
versioned through `create_new_version`.

Each test class mirrors the pattern in `DocumentTypeSerializerRoutingTestCase`
(test_versioning.py) and verifies that content edits produce a new version
while non-versioning field updates (archived, status, is_active) go through
a plain save.
"""
from rest_framework.test import APIRequestFactory

from Tracker.models import EquipmentType, Equipments, WorkCenter, Shift
from Tracker.serializers.mes_lite import EquipmentTypeSerializer, EquipmentsSerializer
from Tracker.serializers.mes_standard import WorkCenterSerializer, ShiftSerializer
from Tracker.tests.base import TenantTestCase


# =============================================================================
# EquipmentType
# =============================================================================

class EquipmentTypeSerializerRoutingTestCase(TenantTestCase):
    """`EquipmentTypeSerializer.update` routes content edits through
    versioning; archive toggles through plain save."""

    def setUp(self):
        super().setUp()
        self.obj = EquipmentType.objects.create(
            name='CMM Machine',
            description='Coordinate measuring machine',
            requires_calibration=True,
            default_calibration_interval_days=90,
            is_portable=False,
            track_downtime=True,
        )
        self.factory = APIRequestFactory()

    def _serializer(self, instance, data, partial=True):
        request = self.factory.patch('/')
        request.user = self.user_a
        return EquipmentTypeSerializer(
            instance, data=data, partial=partial,
            context={'request': request},
        )

    def test_content_edit_creates_new_version(self):
        s = self._serializer(self.obj, {'description': 'Updated description'})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.description, 'Updated description')
        self.obj.refresh_from_db()
        self.assertFalse(self.obj.is_current_version)

    def test_requires_calibration_toggle_creates_new_version(self):
        """Toggling calibration requirement is a content change."""
        s = self._serializer(self.obj, {'requires_calibration': False})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertFalse(result.requires_calibration)

    def test_archive_only_update_does_not_version(self):
        s = self._serializer(self.obj, {'archived': True})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 1)
        self.assertTrue(result.archived)
        self.assertEqual(result.id, self.obj.id)

    def test_mixed_archive_and_content_creates_new_version(self):
        s = self._serializer(self.obj, {'archived': True, 'description': 'Rev B'})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.description, 'Rev B')

    def test_empty_update_is_noop(self):
        s = self._serializer(self.obj, {})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.pk, self.obj.pk)
        self.assertEqual(result.version, 1)


# =============================================================================
# Equipments
# =============================================================================

class EquipmentsSerializerRoutingTestCase(TenantTestCase):
    """`EquipmentsSerializer.update` routes content edits through
    versioning; archive and status changes through plain save."""

    def setUp(self):
        super().setUp()
        self.eq_type = EquipmentType.objects.create(
            name='Caliper',
            requires_calibration=True,
        )
        self.obj = Equipments.objects.create(
            name='Digital Caliper #1',
            serial_number='CAL-001',
            equipment_type=self.eq_type,
            location='QA Lab',
            notes='',
        )
        self.factory = APIRequestFactory()

    def _serializer(self, instance, data, partial=True):
        request = self.factory.patch('/')
        request.user = self.user_a
        return EquipmentsSerializer(
            instance, data=data, partial=partial,
            context={'request': request},
        )

    def test_content_edit_creates_new_version(self):
        s = self._serializer(self.obj, {'location': 'Machine Shop'})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.location, 'Machine Shop')
        self.obj.refresh_from_db()
        self.assertFalse(self.obj.is_current_version)

    def test_serial_number_change_creates_new_version(self):
        """Serial number is identity data — a content change."""
        s = self._serializer(self.obj, {'serial_number': 'CAL-001-REPLACED'})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.serial_number, 'CAL-001-REPLACED')

    def test_archive_only_update_does_not_version(self):
        s = self._serializer(self.obj, {'archived': True})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 1)
        self.assertTrue(result.archived)
        self.assertEqual(result.id, self.obj.id)

    def test_mixed_archive_and_content_creates_new_version(self):
        s = self._serializer(self.obj, {'archived': True, 'location': 'Tool Crib'})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.location, 'Tool Crib')

    def test_empty_update_is_noop(self):
        s = self._serializer(self.obj, {})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.pk, self.obj.pk)
        self.assertEqual(result.version, 1)


# =============================================================================
# WorkCenter
# =============================================================================

class WorkCenterSerializerRoutingTestCase(TenantTestCase):
    """`WorkCenterSerializer.update` routes content edits through
    versioning; archive toggles through plain save."""

    def setUp(self):
        super().setUp()
        self.obj = WorkCenter.objects.create(
            name='Assembly Bay',
            code='ASM',
            description='Main assembly area',
            capacity_units='hours',
            default_efficiency=95,
            cost_center='CC-100',
        )
        self.factory = APIRequestFactory()

    def _serializer(self, instance, data, partial=True):
        request = self.factory.patch('/')
        request.user = self.user_a
        return WorkCenterSerializer(
            instance, data=data, partial=partial,
            context={'request': request},
        )

    def test_content_edit_creates_new_version(self):
        s = self._serializer(self.obj, {'description': 'Revised assembly area'})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.description, 'Revised assembly area')
        self.obj.refresh_from_db()
        self.assertFalse(self.obj.is_current_version)

    def test_cost_center_change_creates_new_version(self):
        """Cost center is accounting config — a content change."""
        s = self._serializer(self.obj, {'cost_center': 'CC-200'})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.cost_center, 'CC-200')

    def test_archive_only_update_does_not_version(self):
        s = self._serializer(self.obj, {'archived': True})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 1)
        self.assertTrue(result.archived)
        self.assertEqual(result.id, self.obj.id)

    def test_mixed_archive_and_content_creates_new_version(self):
        s = self._serializer(self.obj, {'archived': True, 'description': 'Closed bay'})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.description, 'Closed bay')

    def test_empty_update_is_noop(self):
        s = self._serializer(self.obj, {})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.pk, self.obj.pk)
        self.assertEqual(result.version, 1)


# =============================================================================
# Shift
# =============================================================================

class ShiftSerializerRoutingTestCase(TenantTestCase):
    """`ShiftSerializer.update` routes content edits through versioning;
    archive and is_active toggles through plain save."""

    def setUp(self):
        super().setUp()
        self.obj = Shift.objects.create(
            name='Day Shift',
            code='DAY',
            start_time='06:00:00',
            end_time='14:00:00',
            days_of_week='0,1,2,3,4',
            is_active=True,
        )
        self.factory = APIRequestFactory()

    def _serializer(self, instance, data, partial=True):
        request = self.factory.patch('/')
        request.user = self.user_a
        return ShiftSerializer(
            instance, data=data, partial=partial,
            context={'request': request},
        )

    def test_content_edit_creates_new_version(self):
        s = self._serializer(self.obj, {'start_time': '07:00:00'})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(str(result.start_time), '07:00:00')
        self.obj.refresh_from_db()
        self.assertFalse(self.obj.is_current_version)

    def test_days_of_week_change_creates_new_version(self):
        """Changing which days a shift applies is a structural content change."""
        s = self._serializer(self.obj, {'days_of_week': '0,1,2,3,4,5'})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.days_of_week, '0,1,2,3,4,5')

    def test_archive_only_update_does_not_version(self):
        s = self._serializer(self.obj, {'archived': True})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 1)
        self.assertTrue(result.archived)
        self.assertEqual(result.id, self.obj.id)

    def test_mixed_archive_and_content_creates_new_version(self):
        s = self._serializer(self.obj, {'archived': True, 'start_time': '07:00:00'})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)

    def test_empty_update_is_noop(self):
        s = self._serializer(self.obj, {})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.pk, self.obj.pk)
        self.assertEqual(result.version, 1)
