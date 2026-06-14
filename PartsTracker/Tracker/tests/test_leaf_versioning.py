"""
Serializer routing tests for three leaf SecureModels routed through
`create_new_version`: PartTypes, MeasurementDefinition, ThreeDModel.

Each test class mirrors the pattern in `DocumentTypeSerializerRoutingTestCase`
(test_versioning.py) and verifies that content edits produce a new version
while non-versioning field updates (archived, operational state) go through
a plain save.
"""
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIRequestFactory

from django.contrib.contenttypes.models import ContentType

from Tracker.models import Documents, MeasurementDefinition, PartTypes, Steps, ThreeDModel
from Tracker.serializers.dms import ThreeDModelSerializer
from Tracker.serializers.mes_lite import PartTypesSerializer
from Tracker.serializers.qms import MeasurementDefinitionSerializer
from Tracker.tests.base import TenantTestCase


# =============================================================================
# PartTypes
# =============================================================================

class PartTypesSerializerRoutingTestCase(TenantTestCase):
    """`PartTypesSerializer.update` routes content edits through
    versioning; archive toggles through plain save."""

    def setUp(self):
        super().setUp()
        self.obj = PartTypes.objects.create(
            name='Fuel Injector',
            ID_prefix='FJ-',
            ERP_id='ERP-001',
            itar_controlled=False,
            eccn='EAR99',
            usml_category='',
        )
        self.factory = APIRequestFactory()

    def _serializer(self, instance, data, partial=True):
        request = self.factory.patch('/')
        request.user = self.user_a
        return PartTypesSerializer(
            instance, data=data, partial=partial,
            context={'request': request},
        )

    def test_content_edit_creates_new_version(self):
        s = self._serializer(self.obj, {'name': 'Fuel Injector Mk2'})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.name, 'Fuel Injector Mk2')
        self.obj.refresh_from_db()
        self.assertFalse(self.obj.is_current_version)

    def test_archive_only_update_does_not_version(self):
        s = self._serializer(self.obj, {'archived': True})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 1)
        self.assertTrue(result.archived)
        self.assertEqual(result.id, self.obj.id)

    def test_mixed_archive_and_content_creates_new_version(self):
        s = self._serializer(self.obj, {'archived': True, 'name': 'Archived Injector'})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.name, 'Archived Injector')

    def test_empty_update_is_noop(self):
        s = self._serializer(self.obj, {})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.pk, self.obj.pk)
        self.assertEqual(result.version, 1)

    def test_rename_creates_new_version(self):
        """Renaming a part type is a content change that increments version."""
        s = self._serializer(self.obj, {'name': 'High-Pressure Injector', 'ID_prefix': 'HPI-'})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.name, 'High-Pressure Injector')
        self.assertEqual(result.ID_prefix, 'HPI-')
        # Unchanged fields carried forward.
        self.assertEqual(result.ERP_id, 'ERP-001')


# =============================================================================
# Leaf-model Document carry-forward (base SecureModel.create_new_version)
# =============================================================================

class LeafDocumentCarryForwardTestCase(TenantTestCase):
    """Leaf versioned models (no create_new_version override) that declare a
    `documents` GenericRelation must carry their attachments onto the new
    version via the base SecureModel.create_new_version. PartTypes stands in
    for the six such models (Companies, PartTypes, Equipments,
    QualityErrorsList, ThreeDModel, TrainingType)."""

    def setUp(self):
        super().setUp()
        self.part_type = PartTypes.objects.create(name='Carrier PT', ID_prefix='CP-')
        self.doc = Documents.objects.create(
            content_type=ContentType.objects.get_for_model(PartTypes),
            object_id=self.part_type.pk,
            file_name='pt-drawing-rev-A.pdf',
            is_image=False,
            classification='INTERNAL',
            status='APPROVED',
            approved_by=self.user_a,
        )

    def test_document_carried_to_new_version(self):
        v2 = self.part_type.create_new_version(
            user=self.user_a, name='Carrier PT Mk2',
        )
        pt_ct = ContentType.objects.get_for_model(PartTypes)
        v2_docs = Documents.objects.filter(content_type=pt_ct, object_id=v2.pk)
        self.assertEqual(v2_docs.count(), 1)
        v2_doc = v2_docs.first()
        # Fresh row, same content, approval carried forward unchanged.
        self.assertNotEqual(v2_doc.pk, self.doc.pk)
        self.assertEqual(v2_doc.file_name, 'pt-drawing-rev-A.pdf')
        self.assertEqual(v2_doc.status, 'APPROVED')
        self.assertEqual(v2_doc.approved_by, self.user_a)

    def test_v1_document_unchanged(self):
        self.part_type.create_new_version(user=self.user_a, name='Carrier PT Mk2')
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.status, 'APPROVED')
        self.assertEqual(self.doc.object_id, str(self.part_type.pk))


# =============================================================================
# MeasurementDefinition
# =============================================================================

class MeasurementDefinitionSerializerRoutingTestCase(TenantTestCase):
    """`MeasurementDefinitionSerializer.update` routes content edits through
    versioning; archive toggles through plain save."""

    def setUp(self):
        super().setUp()
        self.part_type = PartTypes.objects.create(name='Widget', ID_prefix='WGT-')
        self.step = Steps.objects.create(
            name='Final Inspection',
            part_type=self.part_type,
            pass_threshold=1.0,
        )
        self.obj = MeasurementDefinition.objects.create(
            step=self.step,
            label='Outer Diameter',
            type='NUMERIC',
            unit='mm',
            nominal='25.000000',
            upper_tol='0.050000',
            lower_tol='-0.050000',
            required=True,
            spc_enabled=False,
        )
        self.factory = APIRequestFactory()

    def _serializer(self, instance, data, partial=True):
        request = self.factory.patch('/')
        request.user = self.user_a
        return MeasurementDefinitionSerializer(
            instance, data=data, partial=partial,
            context={'request': request},
        )

    def test_content_edit_creates_new_version(self):
        s = self._serializer(self.obj, {'label': 'Inner Diameter'})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.label, 'Inner Diameter')
        self.obj.refresh_from_db()
        self.assertFalse(self.obj.is_current_version)

    def test_archive_only_update_does_not_version(self):
        s = self._serializer(self.obj, {'archived': True})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 1)
        self.assertTrue(result.archived)
        self.assertEqual(result.id, self.obj.id)

    def test_mixed_archive_and_content_creates_new_version(self):
        s = self._serializer(self.obj, {'archived': True, 'label': 'Wall Thickness'})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.label, 'Wall Thickness')

    def test_empty_update_is_noop(self):
        s = self._serializer(self.obj, {})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.pk, self.obj.pk)
        self.assertEqual(result.version, 1)

    def test_tolerance_change_creates_new_version(self):
        """Tightening tolerances is a spec change that increments version."""
        s = self._serializer(
            self.obj,
            {'upper_tol': '0.025000', 'lower_tol': '-0.025000'},
        )
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertAlmostEqual(float(result.upper_tol), 0.025, places=3)
        self.assertAlmostEqual(float(result.lower_tol), -0.025, places=3)
        # Unchanged fields carried forward.
        self.assertEqual(result.label, 'Outer Diameter')
        self.assertEqual(result.unit, 'mm')


# =============================================================================
# ThreeDModel
# =============================================================================

class ThreeDModelSerializerRoutingTestCase(TenantTestCase):
    """`ThreeDModelSerializer.update` routes content edits through
    versioning; archive and operational-state updates through plain save."""

    def setUp(self):
        super().setUp()
        self.part_type = PartTypes.objects.create(
            name='Turbine Blade',
        )
        self.obj = ThreeDModel.objects.create(
            name='Blade v1',
            file=SimpleUploadedFile('blade.glb', b'GLB_STUB', content_type='model/gltf-binary'),
            part_type=self.part_type,
            original_filename='blade.glb',
            original_format='glb',
        )
        self.factory = APIRequestFactory()

    def _serializer(self, instance, data, partial=True):
        request = self.factory.patch('/')
        request.user = self.user_a
        return ThreeDModelSerializer(
            instance, data=data, partial=partial,
            context={'request': request},
        )

    def test_content_edit_creates_new_version(self):
        s = self._serializer(self.obj, {'name': 'Blade v1 Revised'})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.name, 'Blade v1 Revised')
        self.obj.refresh_from_db()
        self.assertFalse(self.obj.is_current_version)

    def test_archive_only_update_does_not_version(self):
        s = self._serializer(self.obj, {'archived': True})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 1)
        self.assertTrue(result.archived)
        self.assertEqual(result.id, self.obj.id)

    def test_mixed_archive_and_content_creates_new_version(self):
        s = self._serializer(self.obj, {'archived': True, 'name': 'Blade Archived'})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 2)
        self.assertEqual(result.name, 'Blade Archived')

    def test_empty_update_is_noop(self):
        s = self._serializer(self.obj, {})
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.pk, self.obj.pk)
        self.assertEqual(result.version, 1)

    def test_operational_status_update_does_not_version(self):
        """Processing-state updates from Celery workers must not trigger
        versioning — they are in-place operational toggles."""
        # Simulate what the Celery conversion task does after success.
        self.obj.processing_status = 'COMPLETED'
        self.obj.save(update_fields=['processing_status'])

        # A serializer patch with only operational fields also stays in-place.
        s = self._serializer(self.obj, {'processing_status': 'FAILED'})
        # processing_status is read_only on the serializer — validated_data
        # will be empty, which confirms no versioning path is taken.
        s.is_valid(raise_exception=True)
        result = s.save()

        self.assertEqual(result.version, 1)
        self.assertEqual(result.id, self.obj.id)
