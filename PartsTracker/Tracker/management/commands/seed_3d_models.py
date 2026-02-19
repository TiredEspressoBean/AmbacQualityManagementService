"""
Seed 3D models from seed_assets directory.

This command:
1. Copies the benchy GLB from seed_assets/ to media/models/
2. Creates ThreeDModel database records for each part type
3. Optionally creates demo annotations

Works in airgap deployments since everything is baked into the Docker image.

Usage:
    python manage.py seed_3d_models
    python manage.py seed_3d_models --with-annotations
    python manage.py seed_3d_models --force  # Recreate even if exists
"""

import os
import shutil
import random
from django.conf import settings
from django.core.management.base import BaseCommand

from Tracker.models import (
    ThreeDModel, HeatMapAnnotations, PartTypes, Parts, QualityReports, User
)


# Realistic annotation coordinates on a benchy model (from real production data)
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


class Command(BaseCommand):
    help = "Seed 3D models from seed_assets directory for all part types"

    def add_arguments(self, parser):
        parser.add_argument(
            '--with-annotations',
            action='store_true',
            help='Also create demo annotations for each model',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Recreate models even if they already exist',
        )

    def handle(self, *args, **options):
        with_annotations = options['with_annotations']
        force = options['force']

        # Paths
        seed_assets_dir = os.path.join(settings.BASE_DIR, 'seed_assets', 'models')
        media_models_dir = os.path.join(settings.MEDIA_ROOT, 'models')
        source_benchy = os.path.join(seed_assets_dir, '3DBenchy.glb')

        # Verify source file exists
        if not os.path.exists(source_benchy):
            self.stdout.write(self.style.ERROR(
                f"Source benchy file not found at {source_benchy}\n"
                f"Please ensure seed_assets/models/3DBenchy.glb exists."
            ))
            return

        # Ensure media/models directory exists
        os.makedirs(media_models_dir, exist_ok=True)

        # Get all part types
        part_types = PartTypes.objects.all()
        if not part_types.exists():
            self.stdout.write(self.style.WARNING(
                "No part types found. Run setup_defaults or populate_test_data first."
            ))
            return

        models_created = 0
        models_skipped = 0
        annotations_created = 0

        for part_type in part_types:
            # Check if model already exists
            existing = ThreeDModel.objects.filter(
                part_type=part_type,
                is_current_version=True
            ).first()

            if existing and not force:
                self.stdout.write(f"  Model already exists for {part_type.name}, skipping...")
                models_skipped += 1
                continue

            # Delete existing if force
            if existing and force:
                self.stdout.write(f"  Removing existing model for {part_type.name}...")
                # Delete annotations first
                HeatMapAnnotations.objects.filter(model=existing).delete()
                existing.delete()

            # Create unique filename for this part type
            safe_name = part_type.name.replace(' ', '_').replace('/', '_')
            dest_filename = f"3DBenchy_{safe_name}.glb"
            dest_path = os.path.join(media_models_dir, dest_filename)

            # Copy benchy file
            shutil.copy2(source_benchy, dest_path)

            # Create ThreeDModel record
            three_d_model = ThreeDModel.objects.create(
                name=f"3D Benchy - {part_type.name}",
                file=f"models/{dest_filename}",
                part_type=part_type,
                file_type="glb",
                is_current_version=True,
                version=1,
            )
            models_created += 1
            self.stdout.write(self.style.SUCCESS(f"  Created 3D model for {part_type.name}"))

            # Create annotations if requested
            if with_annotations:
                annotations_created += self._create_annotations(three_d_model, part_type)

        self.stdout.write(self.style.SUCCESS(
            f"\nDone! Created {models_created} models, skipped {models_skipped}"
        ))
        if with_annotations:
            self.stdout.write(self.style.SUCCESS(f"Created {annotations_created} annotations"))

    def _create_annotations(self, model, part_type):
        """Create demo annotations for a model."""
        # Get parts of this type
        parts = list(Parts.objects.filter(part_type=part_type)[:10])
        if not parts:
            self.stdout.write(self.style.WARNING(
                f"    No parts found for {part_type.name}, skipping annotations"
            ))
            return 0

        # Get an operator for created_by
        operator = User.objects.filter(is_staff=True).first()
        if not operator:
            operator = User.objects.first()

        # Select random subset of annotations (3-6)
        num_annotations = random.randint(3, 6)
        selected = random.sample(BENCHY_ANNOTATIONS, min(num_annotations, len(BENCHY_ANNOTATIONS)))

        count = 0
        for ann_data in selected:
            part = random.choice(parts)

            annotation = HeatMapAnnotations.objects.create(
                model=model,
                part=part,
                position_x=ann_data['x'],
                position_y=ann_data['y'],
                position_z=ann_data['z'],
                defect_type=ann_data['defect_type'],
                severity=ann_data['severity'],
                notes=f"Demo annotation - {ann_data['defect_type']} detected during inspection",
                created_by=operator,
            )
            count += 1

            # Link to quality reports for this part
            quality_reports = QualityReports.objects.filter(part=part)[:2]
            if quality_reports.exists():
                annotation.quality_reports.set(quality_reports)

        self.stdout.write(f"    Created {count} annotations for {part_type.name}")
        return count
