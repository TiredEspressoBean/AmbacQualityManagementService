"""
Demo 3D models seeder with preset data.

Creates:
- 1-2 ThreeDModel records linked to part types
- 5-10 HeatMapAnnotations with realistic defect positions
- All data deterministic for consistent demo experience
"""

import os
import shutil
from django.conf import settings
from django.core.files.base import ContentFile

from Tracker.models import (
    ThreeDModel, HeatMapAnnotations, PartTypes, Parts, User,
    QualityReports, ModelProcessingStatus,
)

from ..base import BaseSeeder


# Demo 3D models to create
DEMO_3D_MODELS = [
    {
        'name': '3D Model - Common Rail Injector',
        'part_type': 'Common Rail Injector',
        'file_type': 'glb',
        'version': 1,
        'is_current_version': True,
    },
]

# Realistic annotation coordinates on a benchy model (from real data)
# These are positions in scaled space (model scaled to ~3 units)
DEMO_HEATMAP_ANNOTATIONS = [
    # Hull area - coating defects
    {
        'part_serial': 'INJ-0038-003',
        'position_x': 0.4710,
        'position_y': -0.3082,
        'position_z': 0.5955,
        'defect_type': 'Coating defects present',
        'severity': 'LOW',
        'notes': 'Minor coating irregularity observed on hull surface',
    },
    {
        'part_serial': 'INJ-0038-007',
        'position_x': 0.2821,
        'position_y': -0.3059,
        'position_z': 0.5298,
        'defect_type': 'Coating defects present',
        'severity': 'MEDIUM',
        'notes': 'Coating defect with visible discoloration',
    },
    {
        'part_serial': 'INJ-0038-008',
        'position_x': 0.2999,
        'position_y': -0.1841,
        'position_z': 0.6156,
        'defect_type': 'Coating defects present',
        'severity': 'LOW',
        'notes': 'Small area of coating irregularity',
    },
    # Cabin/deck area - layer separation
    {
        'part_serial': 'INJ-0038-010',
        'position_x': 0.6779,
        'position_y': 0.5497,
        'position_z': -0.6679,
        'defect_type': 'Layer separation',
        'severity': 'LOW',
        'notes': 'Minor layer separation detected',
    },
    {
        'part_serial': 'INJ-0038-011',
        'position_x': 0.6787,
        'position_y': 0.5377,
        'position_z': -0.6980,
        'defect_type': 'Layer separation',
        'severity': 'LOW',
        'notes': 'Layer separation near deck area',
    },
    {
        'part_serial': 'INJ-0042-017',
        'position_x': 1.2149,
        'position_y': 0.1190,
        'position_z': -0.6669,
        'defect_type': 'Layer separation',
        'severity': 'MEDIUM',
        'notes': 'Moderate layer separation requiring monitoring',
    },
    {
        'part_serial': 'INJ-0042-019',
        'position_x': 0.9073,
        'position_y': 0.5218,
        'position_z': -0.3667,
        'defect_type': 'Layer separation',
        'severity': 'HIGH',
        'notes': 'Significant layer separation - disposition required',
    },
    # Chimney area - dimensional issues
    {
        'part_serial': 'INJ-0038-003',
        'position_x': -0.2860,
        'position_y': -0.1342,
        'position_z': 1.0418,
        'defect_type': 'Dimensional out of tolerance',
        'severity': 'HIGH',
        'notes': 'Critical dimensional deviation at chimney',
    },
    {
        'part_serial': 'INJ-0038-007',
        'position_x': -0.1081,
        'position_y': 0.0956,
        'position_z': 1.0661,
        'defect_type': 'Dimensional out of tolerance',
        'severity': 'MEDIUM',
        'notes': 'Dimensional tolerance exceeded',
    },
    {
        'part_serial': 'INJ-0042-017',
        'position_x': -0.2720,
        'position_y': 0.1473,
        'position_z': 1.1223,
        'defect_type': 'Dimensional out of tolerance',
        'severity': 'LOW',
        'notes': 'Minor dimensional variation noted',
    },
]


class DemoThreeDModelSeeder(BaseSeeder):
    """
    Creates preset 3D models and annotations for the demo scenario.

    All data is deterministic - same result every time.
    """

    def __init__(self, stdout, style, tenant, scale='small'):
        super().__init__(stdout, style, scale=scale)
        self.tenant = tenant

    def seed(self, users):
        """
        Create all demo 3D models and annotations.

        Args:
            users: dict with user lists including by_email lookup

        Returns:
            dict with created models and annotations
        """
        self.log("Creating demo 3D models and annotations...")

        result = {
            '3d_models': [],
            'annotations': [],
        }

        # Source benchy file from seed_assets (baked into Docker image for airgap deployments)
        source_benchy = os.path.join(settings.BASE_DIR, 'seed_assets', 'models', '3DBenchy.glb')

        # Fallback to media if seed_assets doesn't exist (for backwards compatibility)
        if not os.path.exists(source_benchy):
            source_benchy = os.path.join(settings.MEDIA_ROOT, 'models', '3DBenchyStepFile_dPId9CK.glb')

        if not os.path.exists(source_benchy):
            self.log(
                "  Benchy source file not found. Skipping 3D model creation.",
                warning=True
            )
            # Create dummy file for demo purposes
            source_benchy = None

        # Get part type lookup
        part_types = PartTypes.objects.filter(tenant=self.tenant)
        part_type_map = {pt.name: pt for pt in part_types}

        # Create 3D models
        for model_data in DEMO_3D_MODELS:
            part_type = part_type_map.get(model_data['part_type'])
            if not part_type:
                self.log(f"  Warning: Part type '{model_data['part_type']}' not found", warning=True)
                continue

            model = self._create_3d_model(model_data, part_type, source_benchy)
            if model:
                result['3d_models'].append(model)

                # Create annotations for this model
                annotations = self._create_annotations_for_model(model, users)
                result['annotations'].extend(annotations)

        self.log(f"  Created {len(result['3d_models'])} 3D models")
        self.log(f"  Created {len(result['annotations'])} heatmap annotations")

        return result

    def _create_3d_model(self, model_data, part_type, source_benchy):
        """Create or update a 3D model.

        ThreeDModel fields:
        - name: CharField(max_length=255)
        - file: FileField (required)
        - part_type: ForeignKey to PartTypes
        - step: ForeignKey to Steps (optional)
        - file_type: CharField (e.g., 'glb')
        - is_current_version: BooleanField
        - version: IntegerField
        - processing_status: CharField (uses ModelProcessingStatus enum)
        """
        # Prepare the file path first
        safe_name = part_type.name.replace(' ', '_').replace('/', '_')
        dest_filename = f"3DBenchy_{safe_name}.glb"
        file_path = f"models/{dest_filename}"

        # Handle file copying
        if source_benchy and os.path.exists(source_benchy):
            dest_path = os.path.join(settings.MEDIA_ROOT, 'models', dest_filename)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            try:
                shutil.copy2(source_benchy, dest_path)
            except Exception as e:
                self.log(f"  Could not copy benchy file: {e}", warning=True)

        # Explicitly set all fields - do NOT rely on model defaults
        defaults = {
            'file_type': model_data['file_type'],
            'is_current_version': model_data['is_current_version'],
            'version': model_data['version'],
            'processing_status': ModelProcessingStatus.COMPLETED,
            'file': file_path,
        }

        model, created = ThreeDModel.objects.update_or_create(
            tenant=self.tenant,
            part_type=part_type,
            name=model_data['name'],
            defaults=defaults,
        )

        # Handle file for new models without source benchy
        if created and (not source_benchy or not os.path.exists(source_benchy)):
            model.file.save(
                dest_filename,
                ContentFile(b'Demo 3D model placeholder - benchy file not found'),
                save=True
            )

        action = "Created" if created else "Updated"
        self.log(f"  {action} 3D model: {model.name}")
        return model

    def _create_annotations_for_model(self, three_d_model, users):
        """Create heatmap annotations for a 3D model.

        HeatMapAnnotations fields:
        - model: ForeignKey to ThreeDModel
        - part: ForeignKey to Parts
        - quality_reports: ManyToManyField to QualityReports (optional)
        - position_x, position_y, position_z: FloatField
        - measurement_value: FloatField (optional)
        - defect_type: CharField (optional)
        - severity: CharField choices (LOW, MEDIUM, HIGH, CRITICAL)
        - notes: TextField (optional)
        - created_by: ForeignKey to User
        """
        # Get parts of this type
        parts = Parts.objects.filter(
            tenant=self.tenant,
            part_type=three_d_model.part_type
        )
        part_map = {p.ERP_id: p for p in parts}

        # Get a default user for annotations
        qa_users = users.get('qa_staff', [])
        if not qa_users:
            qa_users = users.get('employees', [])

        if not qa_users:
            self.log("  Warning: No users found for annotation creator", warning=True)
            return []

        default_user = qa_users[0]

        annotations = []

        for ann_data in DEMO_HEATMAP_ANNOTATIONS:
            # Find the part by serial number
            part = part_map.get(ann_data['part_serial'])
            if not part:
                # Part doesn't exist yet, skip this annotation
                continue

            # Explicitly set all fields - do NOT rely on model defaults
            # Severity must be UPPERCASE: LOW, MEDIUM, HIGH, CRITICAL
            defaults = {
                'defect_type': ann_data['defect_type'],
                'severity': ann_data['severity'],  # Must be UPPERCASE
                'notes': ann_data['notes'],
                'measurement_value': ann_data.get('measurement_value', None),
                'created_by': default_user,
            }

            annotation, created = HeatMapAnnotations.objects.update_or_create(
                tenant=self.tenant,
                model=three_d_model,
                part=part,
                position_x=ann_data['position_x'],
                position_y=ann_data['position_y'],
                position_z=ann_data['position_z'],
                defaults=defaults,
            )
            annotations.append(annotation)

            # Link to quality reports if any exist for this part
            quality_reports = QualityReports.objects.filter(
                tenant=self.tenant,
                part=part
            )[:2]
            if quality_reports.exists():
                annotation.quality_reports.set(quality_reports)

        return annotations
