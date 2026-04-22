"""
Serializer-routing tests for Companies and DisassemblyBOMLine versioning.

Both are plain SecureModel leaves. All editable fields are "content"
except `archived`. Content edits route through `create_new_version`;
archive-only updates go through a plain save.

Follows the pattern established in test_versioning.py::DocumentTypeSerializerRoutingTestCase.
"""
from rest_framework.test import APIRequestFactory

from Tracker.models import Companies, PartTypes
from Tracker.models.reman import DisassemblyBOMLine
from Tracker.serializers.core import CompanySerializer
from Tracker.serializers.reman import DisassemblyBOMLineSerializer
from Tracker.tests.base import TenantTestCase


class CompanySerializerRoutingTestCase(TenantTestCase):
    """`CompanySerializer.update` routes content edits through versioning;
    archive toggles through plain save."""

    def setUp(self):
        super().setUp()
        self.company = Companies.objects.create(
            name='Acme Corp',
            description='Initial supplier record',
        )
        self.factory = APIRequestFactory()

    def _serializer(self, instance, data, partial=True):
        request = self.factory.patch('/')
        request.user = self.user_a
        return CompanySerializer(
            instance, data=data, partial=partial,
            context={'request': request},
        )

    def test_content_edit_creates_new_version(self):
        s = self._serializer(self.company, {'description': 'Updated supplier info'})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.description, 'Updated supplier info')
        self.company.refresh_from_db()
        self.assertFalse(self.company.is_current_version)

    def test_name_edit_creates_new_version(self):
        s = self._serializer(self.company, {'name': 'Acme Corp Ltd'})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.name, 'Acme Corp Ltd')

    def test_archive_only_update_does_not_version(self):
        s = self._serializer(self.company, {'archived': True})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 1)
        self.assertTrue(result.archived)
        # Same row — id must not change.
        self.assertEqual(result.id, self.company.id)

    def test_mixed_archive_and_content_creates_new_version(self):
        # Any content field in the payload routes through versioning
        # even when archived is also present.
        s = self._serializer(self.company, {'archived': True, 'description': 'Rev B'})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.description, 'Rev B')

    def test_empty_update_is_noop(self):
        s = self._serializer(self.company, {})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.pk, self.company.pk)
        self.assertEqual(result.version, 1)


class DisassemblyBOMLineSerializerRoutingTestCase(TenantTestCase):
    """`DisassemblyBOMLineSerializer.update` routes content edits through
    versioning; archive toggles through plain save."""

    def setUp(self):
        super().setUp()
        self.core_pt = PartTypes.objects.create(name='Alternator Core')
        self.component_pt = PartTypes.objects.create(name='Rotor Assembly')
        self.bom_line = DisassemblyBOMLine.objects.create(
            core_type=self.core_pt,
            component_type=self.component_pt,
            expected_qty=1,
            expected_fallout_rate='0.05',
            notes='Initial spec',
            line_number=10,
        )
        self.factory = APIRequestFactory()

    def _serializer(self, instance, data, partial=True):
        request = self.factory.patch('/')
        request.user = self.user_a
        return DisassemblyBOMLineSerializer(
            instance, data=data, partial=partial,
            context={'request': request},
        )

    def test_content_edit_creates_new_version(self):
        s = self._serializer(self.bom_line, {'notes': 'Updated handling notes'})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.notes, 'Updated handling notes')
        self.bom_line.refresh_from_db()
        self.assertFalse(self.bom_line.is_current_version)

    def test_quantity_edit_creates_new_version(self):
        s = self._serializer(self.bom_line, {'expected_qty': 2, 'expected_fallout_rate': '0.10'})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.expected_qty, 2)

    def test_archive_only_update_does_not_version(self):
        s = self._serializer(self.bom_line, {'archived': True})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 1)
        self.assertTrue(result.archived)
        # Same row — id must not change.
        self.assertEqual(result.id, self.bom_line.id)

    def test_mixed_archive_and_content_creates_new_version(self):
        # Any content field in the payload routes through versioning
        # even when archived is also present.
        s = self._serializer(self.bom_line, {'archived': True, 'notes': 'Rev B'})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.notes, 'Rev B')

    def test_empty_update_is_noop(self):
        s = self._serializer(self.bom_line, {})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.pk, self.bom_line.pk)
        self.assertEqual(result.version, 1)
