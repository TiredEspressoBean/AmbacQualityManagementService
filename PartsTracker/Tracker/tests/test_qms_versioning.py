"""
Tests for `create_new_version` routing on QualityErrorsList and TrainingType.

Both are plain SecureModel leaves. Content edits route through
`create_new_version`; archive-only edits go through plain save.

Covers per model:
  - content edit → new version
  - archive-only → no version
  - mixed archive + content → new version
  - empty payload → noop
  - model-specific content field toggle
"""
from rest_framework.test import APIRequestFactory

from Tracker.models import QualityErrorsList, TrainingType
from Tracker.serializers.qms import QualityErrorsListSerializer
from Tracker.serializers.training import TrainingTypeSerializer
from Tracker.tests.base import TenantTestCase


# ---------------------------------------------------------------------------
# QualityErrorsList
# ---------------------------------------------------------------------------

class QualityErrorsListSerializerVersioningTestCase(TenantTestCase):
    """`QualityErrorsListSerializer.update` routes content edits through
    versioning; archive toggles go through plain save."""

    def setUp(self):
        super().setUp()
        self.qe = QualityErrorsList.objects.create(
            error_name='Surface Crack',
            error_example='Visible linear crack on the outer surface.',
            requires_3d_annotation=True,
        )
        self.factory = APIRequestFactory()

    def _serializer(self, instance, data, partial=True):
        request = self.factory.patch('/')
        request.user = self.user_a
        return QualityErrorsListSerializer(
            instance, data=data, partial=partial,
            context={'request': request},
        )

    def test_content_edit_creates_new_version(self):
        s = self._serializer(self.qe, {'error_name': 'Surface Crack Rev B'})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.error_name, 'Surface Crack Rev B')
        self.qe.refresh_from_db()
        self.assertFalse(self.qe.is_current_version)

    def test_archive_only_update_does_not_version(self):
        s = self._serializer(self.qe, {'archived': True})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 1)
        self.assertTrue(result.archived)
        # Same row — id must be unchanged.
        self.assertEqual(result.id, self.qe.id)

    def test_mixed_archive_and_content_creates_new_version(self):
        s = self._serializer(self.qe, {'archived': True, 'error_name': 'Surface Crack Rev C'})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.error_name, 'Surface Crack Rev C')

    def test_empty_update_is_noop(self):
        s = self._serializer(self.qe, {})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.pk, self.qe.pk)
        self.assertEqual(result.version, 1)

    def test_requires_3d_annotation_toggle_creates_new_version(self):
        """Toggling the annotation-required flag is a content change."""
        s = self._serializer(self.qe, {'requires_3d_annotation': False})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertFalse(result.requires_3d_annotation)
        # Unchanged fields carried forward.
        self.assertEqual(result.error_name, self.qe.error_name)
        self.assertEqual(result.error_example, self.qe.error_example)


# ---------------------------------------------------------------------------
# TrainingType
# ---------------------------------------------------------------------------

class TrainingTypeSerializerVersioningTestCase(TenantTestCase):
    """`TrainingTypeSerializer.update` routes content edits through
    versioning; archive toggles go through plain save."""

    def setUp(self):
        super().setUp()
        self.tt = TrainingType.objects.create(
            name='Blueprint Reading',
            description='Ability to read and interpret engineering blueprints.',
            validity_period_days=365,
        )
        self.factory = APIRequestFactory()

    def _serializer(self, instance, data, partial=True):
        request = self.factory.patch('/')
        request.user = self.user_a
        return TrainingTypeSerializer(
            instance, data=data, partial=partial,
            context={'request': request},
        )

    def test_content_edit_creates_new_version(self):
        s = self._serializer(self.tt, {'description': 'Updated blueprint reading curriculum.'})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.description, 'Updated blueprint reading curriculum.')
        self.tt.refresh_from_db()
        self.assertFalse(self.tt.is_current_version)

    def test_archive_only_update_does_not_version(self):
        s = self._serializer(self.tt, {'archived': True})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 1)
        self.assertTrue(result.archived)
        self.assertEqual(result.id, self.tt.id)

    def test_mixed_archive_and_content_creates_new_version(self):
        s = self._serializer(self.tt, {'archived': True, 'name': 'Blueprint Reading v2'})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.name, 'Blueprint Reading v2')

    def test_empty_update_is_noop(self):
        s = self._serializer(self.tt, {})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.pk, self.tt.pk)
        self.assertEqual(result.version, 1)

    def test_validity_period_change_creates_new_version(self):
        """Changing validity_period_days is a content change that re-clocks
        all downstream training-record expiry calculations."""
        s = self._serializer(self.tt, {'validity_period_days': 180})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.validity_period_days, 180)
        # Unchanged fields carried forward.
        self.assertEqual(result.name, self.tt.name)
        self.assertEqual(result.description, self.tt.description)
