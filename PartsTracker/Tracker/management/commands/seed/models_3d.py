"""
3D Models seed data: ThreeDModel and HeatMapAnnotations.
"""

import os
import random
import shutil
from django.conf import settings

from Tracker.models import (
    ThreeDModel, HeatMapAnnotations, Parts, QualityReports,
)
from .base import BaseSeeder


# Realistic annotation coordinates on a benchy model (from real data)
# These are positions in scaled space (model scaled to ~3 units)
BENCHY_ANNOTATIONS = [
    # Hull area - coating defects
    {'x': 0.4710, 'y': -0.3082, 'z': 0.5955, 'defect_type': 'Coating defects present', 'severity': 'low'},
    {'x': 0.2821, 'y': -0.3059, 'z': 0.5298, 'defect_type': 'Coating defects present', 'severity': 'medium'},
    {'x': 0.2999, 'y': -0.1841, 'z': 0.6156, 'defect_type': 'Coating defects present', 'severity': 'low'},
    {'x': 0.4050, 'y': -0.0024, 'z': -0.1466, 'defect_type': 'Coating defects present', 'severity': 'low'},
    {'x': 0.5941, 'y': -0.2539, 'z': 0.5218, 'defect_type': 'Coating defects present', 'severity': 'low'},
    {'x': 0.3851, 'y': 0.0180, 'z': -0.0699, 'defect_type': 'Coating defects present', 'severity': 'high'},
    {'x': -0.0131, 'y': -0.1376, 'z': 0.5827, 'defect_type': 'Coating defects present', 'severity': 'medium'},
    # Cabin/deck area - layer separation
    {'x': 0.6779, 'y': 0.5497, 'z': -0.6679, 'defect_type': 'Layer separation', 'severity': 'low'},
    {'x': 0.6787, 'y': 0.5377, 'z': -0.6980, 'defect_type': 'Layer separation', 'severity': 'low'},
    {'x': 1.2149, 'y': 0.1190, 'z': -0.6669, 'defect_type': 'Layer separation', 'severity': 'medium'},
    {'x': 0.9073, 'y': 0.5218, 'z': -0.3667, 'defect_type': 'Layer separation', 'severity': 'high'},
    {'x': -0.6264, 'y': 0.5147, 'z': -0.9464, 'defect_type': 'Layer separation', 'severity': 'medium'},
    # Chimney area - dimensional issues
    {'x': -0.2860, 'y': -0.1342, 'z': 1.0418, 'defect_type': 'Dimensional out of tolerance', 'severity': 'high'},
    {'x': -0.1081, 'y': 0.0956, 'z': 1.0661, 'defect_type': 'Dimensional out of tolerance', 'severity': 'medium'},
    {'x': -0.2720, 'y': 0.1473, 'z': 1.1223, 'defect_type': 'Dimensional out of tolerance', 'severity': 'low'},
]


class ThreeDModelSeeder(BaseSeeder):
    """
    Seeds 3D model-related data.

    Creates:
    - ThreeDModel records linked to part types
    - HeatMapAnnotations with realistic defect positions
    - Links annotations to quality reports
    """

    def seed(self, part_types, employees):
        """Create 3D benchy models and realistic annotations for each part type."""
        self.log("Creating 3D models and annotations...")

        # Source benchy file from seed_assets (baked into Docker image for airgap deployments)
        source_benchy = os.path.join(settings.BASE_DIR, 'seed_assets', 'models', '3DBenchy.glb')

        # Fallback to media if seed_assets doesn't exist (for backwards compatibility)
        if not os.path.exists(source_benchy):
            source_benchy = os.path.join(settings.MEDIA_ROOT, 'models', '3DBenchyStepFile_dPId9CK.glb')

        if not os.path.exists(source_benchy):
            self.log(
                "  Benchy source file not found. Ensure seed_assets/models/3DBenchy.glb exists.",
                warning=True
            )
            return

        models_created = 0
        annotations_created = 0

        for part_type in part_types:
            result = self._create_model_for_part_type(part_type, employees, source_benchy)
            if result:
                models_created += result['models']
                annotations_created += result['annotations']

        self.log(f"Created {models_created} 3D models and {annotations_created} annotations", success=True)

    def _create_model_for_part_type(self, part_type, employees, source_benchy):
        """Create 3D model and annotations for a single part type."""
        # Check if model already exists for this part type
        existing_model = ThreeDModel.objects.filter(
            part_type=part_type,
            is_current_version=True
        ).first()

        if existing_model:
            self.log(f"  Model already exists for {part_type.name}, skipping...")
            return None

        # Create a unique filename for this part type
        safe_name = part_type.name.replace(' ', '_').replace('/', '_')
        dest_filename = f"3DBenchy_{safe_name}.glb"
        dest_path = os.path.join(settings.MEDIA_ROOT, 'models', dest_filename)

        # Ensure models directory exists
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

        # Copy benchy file
        try:
            shutil.copy2(source_benchy, dest_path)
        except Exception as e:
            self.log(f"  Could not copy benchy file for {part_type.name}: {e}", warning=True)
            return None

        if not os.path.exists(dest_path):
            self.log(f"  Could not create model file for {part_type.name}", warning=True)
            return None

        # Create the ThreeDModel record
        three_d_model = ThreeDModel.objects.create(
            tenant=self.tenant,
            name=f"3D Benchy - {part_type.name}",
            file=f"models/{dest_filename}",
            part_type=part_type,
            file_type="glb",
            is_current_version=True,
            version=1,
        )

        self.log(f"  Created 3D model for {part_type.name}")

        # Create annotations
        annotations_created = self._create_annotations_for_model(
            three_d_model, part_type, employees
        )

        return {'models': 1, 'annotations': annotations_created}

    def _create_annotations_for_model(self, three_d_model, part_type, employees):
        """Create heatmap annotations for a 3D model."""
        # Get parts of this type to link annotations to
        parts_of_type = list(Parts.objects.filter(part_type=part_type)[:10])

        if not parts_of_type:
            self.log(f"  No parts found for {part_type.name}, skipping annotations", warning=True)
            return 0

        # Select a random subset (3-6) of annotations for variety
        num_annotations = random.randint(3, 6)
        selected_annotations = random.sample(
            BENCHY_ANNOTATIONS,
            min(num_annotations, len(BENCHY_ANNOTATIONS))
        )

        operator = random.choice(employees)
        annotations_created = 0

        for ann_data in selected_annotations:
            # Pick a random part of this type
            part = random.choice(parts_of_type)

            annotation = HeatMapAnnotations.objects.create(
                tenant=self.tenant,
                model=three_d_model,
                part=part,
                position_x=ann_data['x'],
                position_y=ann_data['y'],
                position_z=ann_data['z'],
                defect_type=ann_data['defect_type'],
                severity=ann_data['severity'],
                notes=f"Demo annotation - {ann_data['defect_type']} detected during inspection",
                created_by=operator,
            )

            # Link to any quality reports for this part
            quality_reports = QualityReports.objects.filter(part=part)[:2]
            if quality_reports.exists():
                annotation.quality_reports.set(quality_reports)

            annotations_created += 1

        return annotations_created
