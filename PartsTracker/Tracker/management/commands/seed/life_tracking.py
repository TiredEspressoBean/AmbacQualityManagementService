"""
Life Tracking seed data: Life limit definitions and tracking records.

Seeds life-limited component tracking for remanufacturing operations.
"""

import random
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone

from Tracker.models import (
    LifeLimitDefinition, PartTypeLifeLimit, LifeTracking,
    PartTypes, Core, HarvestedComponent, Parts,
)
from django.contrib.contenttypes.models import ContentType
from .base import BaseSeeder


class LifeTrackingSeeder(BaseSeeder):
    """
    Seeds life tracking data for remanufacturing.

    Creates:
    - LifeLimitDefinitions (cycles, hours, shelf life)
    - PartTypeLifeLimit associations for component types
    - LifeTracking records on cores (incoming life data)
    - LifeTracking on harvested components/parts (transferred from cores)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Standard life limit definitions for diesel injector components
        self.life_limit_definitions = [
            # (name, unit, unit_label, is_calendar_based, soft_limit, hard_limit)
            ('Operating Hours', 'hours', 'Hours', False, Decimal('8000'), Decimal('10000')),
            ('Flight Cycles', 'cycles', 'Cycles', False, Decimal('15000'), Decimal('20000')),
            ('Start Cycles', 'cycles', 'Start Cycles', False, Decimal('18000'), Decimal('25000')),
            ('Injection Cycles', 'cycles', 'Injection Cycles', False, Decimal('500000000'), Decimal('750000000')),
            ('Shelf Life', 'days', 'Days', True, Decimal('270'), Decimal('365')),
        ]

    def seed(self, part_types, cores=None, harvested_components=None):
        """Run the life tracking seeding process."""
        # Create life limit definitions
        definitions = self._create_life_limit_definitions()

        # Link definitions to component part types
        self._create_part_type_life_limits(definitions, part_types)

        # Create life tracking on cores
        if cores:
            self._create_core_life_tracking(cores, definitions)

        # Create life tracking on parts from harvested components
        if harvested_components:
            self._create_component_life_tracking(harvested_components, definitions)

        return definitions

    def _create_life_limit_definitions(self):
        """Create standard life limit definitions."""
        definitions = {}
        created_count = 0

        for name, unit, unit_label, is_calendar, soft_limit, hard_limit in self.life_limit_definitions:
            definition, created = LifeLimitDefinition.objects.get_or_create(
                tenant=self.tenant,
                name=name,
                defaults={
                    'unit': unit,
                    'unit_label': unit_label,
                    'is_calendar_based': is_calendar,
                    'soft_limit': soft_limit,
                    'hard_limit': hard_limit,
                }
            )
            definitions[name] = definition
            if created:
                created_count += 1

        if created_count > 0:
            self.log(f"Created {created_count} life limit definitions")
        else:
            self.log(f"Life limit definitions already exist ({len(definitions)} total)")

        return definitions

    def _create_part_type_life_limits(self, definitions, part_types):
        """Link life limit definitions to component part types."""
        # Component types that should have life tracking
        component_names = ['Injector Body', 'Plunger Assembly', 'Nozzle', 'Spring Set',
                          'Solenoid Valve', 'Control Valve']

        # Default life limits for reman components
        default_limits = ['Operating Hours', 'Start Cycles']

        # Also apply to main injector type
        main_types = ['Common Rail Injector']

        created_count = 0

        for pt in part_types:
            if pt.name in component_names or pt.name in main_types:
                for limit_name in default_limits:
                    definition = definitions.get(limit_name)
                    if not definition:
                        continue

                    _, created = PartTypeLifeLimit.objects.get_or_create(
                        part_type=pt,
                        definition=definition,
                        defaults={
                            'tenant': self.tenant,
                            'is_required': pt.name in main_types,  # Required for main type
                        }
                    )
                    if created:
                        created_count += 1

        if created_count > 0:
            self.log(f"Created {created_count} part type life limit associations")

    def _create_core_life_tracking(self, cores, definitions):
        """Create life tracking records on incoming cores."""
        created_count = 0

        # Relevant definitions for cores
        ops_hours_def = definitions.get('Operating Hours')
        start_cycles_def = definitions.get('Start Cycles')

        if not ops_hours_def or not start_cycles_def:
            self.log("  Warning: Missing life limit definitions for cores", warning=True)
            return

        core_ct = ContentType.objects.get_for_model(Core)

        # Source distribution for life data
        source_weights = [
            (LifeTracking.Source.OEM, 0.15),
            (LifeTracking.Source.CUSTOMER, 0.40),
            (LifeTracking.Source.LOGBOOK, 0.25),
            (LifeTracking.Source.ESTIMATED, 0.20),
        ]

        for core in cores:
            # Skip scrapped cores - they don't need life tracking
            if core.status == 'SCRAPPED':
                continue

            # Check if tracking already exists
            existing = LifeTracking.objects.filter(
                content_type=core_ct,
                object_id=core.pk,
            ).exists()

            if existing:
                continue

            # Generate realistic accumulated values based on condition grade
            # A-grade: lower usage, B-grade: medium, C-grade: high usage
            grade_multipliers = {
                'A': (0.1, 0.3),   # 10-30% of soft limit
                'B': (0.3, 0.6),   # 30-60% of soft limit
                'C': (0.6, 0.85),  # 60-85% of soft limit
            }
            mult_range = grade_multipliers.get(core.condition_grade, (0.3, 0.6))
            multiplier = random.uniform(*mult_range)

            source = self.weighted_choice(source_weights)

            # Create Operating Hours tracking
            ops_hours_value = float(ops_hours_def.soft_limit) * multiplier
            ops_hours_value = Decimal(str(round(ops_hours_value, 1)))

            LifeTracking.objects.create(
                tenant=self.tenant,
                content_type=core_ct,
                object_id=core.pk,
                definition=ops_hours_def,
                accumulated=ops_hours_value,
                source=source,
                reference_date=core.received_date - timedelta(days=random.randint(365, 3650)),
            )

            # Create Start Cycles tracking (proportional to hours)
            # Typical ratio: ~2-3 starts per hour of operation
            starts_per_hour = random.uniform(2.0, 3.5)
            start_cycles_value = float(ops_hours_value) * starts_per_hour
            start_cycles_value = Decimal(str(int(start_cycles_value)))

            LifeTracking.objects.create(
                tenant=self.tenant,
                content_type=core_ct,
                object_id=core.pk,
                definition=start_cycles_def,
                accumulated=start_cycles_value,
                source=source,
                reference_date=core.received_date - timedelta(days=random.randint(365, 3650)),
            )

            created_count += 2

        self.log(f"Created {created_count} life tracking records on cores")

    def _create_component_life_tracking(self, harvested_components, definitions):
        """
        Create life tracking on parts that were created from harvested components.

        This simulates the life transfer that happens via accept_to_inventory(transfer_life=True).
        For demo purposes, we create tracking records for components whose parts
        might not have had life transferred during seeding.
        """
        created_count = 0

        ops_hours_def = definitions.get('Operating Hours')
        start_cycles_def = definitions.get('Start Cycles')

        if not ops_hours_def or not start_cycles_def:
            return

        parts_ct = ContentType.objects.get_for_model(Parts)
        core_ct = ContentType.objects.get_for_model(Core)

        for hc in harvested_components:
            # Only process components that have been accepted to inventory
            if not hc.component_part:
                continue

            part = hc.component_part

            # Check if tracking already exists on the part
            existing = LifeTracking.objects.filter(
                content_type=parts_ct,
                object_id=part.pk,
            ).exists()

            if existing:
                continue

            # Get life tracking from the source core
            core_tracking = LifeTracking.objects.filter(
                content_type=core_ct,
                object_id=hc.core.pk,
            )

            for core_lt in core_tracking:
                # Transfer life data from core to part
                LifeTracking.objects.create(
                    tenant=self.tenant,
                    content_type=parts_ct,
                    object_id=part.pk,
                    definition=core_lt.definition,
                    accumulated=core_lt.accumulated,
                    source=LifeTracking.Source.TRANSFERRED,
                    reference_date=core_lt.reference_date,
                )
                created_count += 1

        if created_count > 0:
            self.log(f"Created {created_count} life tracking records transferred to parts")
