"""
Demo life tracking seeder with preset, deterministic data.

Creates the exact life tracking configuration for demo scenarios:
- LifeLimitDefinitions (Operating Hours, Injection Cycles, Shelf Life)
- PartTypeLifeLimit associations for injector components
- LifeTracking records on parts/cores with known values

All data is deterministic to support consistent demos and training.
"""

from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from Tracker.models import (
    LifeLimitDefinition, PartTypeLifeLimit, LifeTracking,
    PartTypes, Core, Parts,
)

from ..base import BaseSeeder


# Preset demo life limit definitions
# Note: All fields explicitly set - do not rely on model defaults
DEMO_LIFE_LIMIT_DEFINITIONS = [
    {
        'name': 'Operating Hours',
        'unit': 'hours',
        'unit_label': 'Hours',
        'is_calendar_based': False,
        'soft_limit': Decimal('8000'),
        'hard_limit': Decimal('10000'),
    },
    {
        'name': 'Injection Cycles',
        'unit': 'cycles',
        'unit_label': 'Injection Cycles',
        'is_calendar_based': False,
        'soft_limit': Decimal('500000000'),
        'hard_limit': Decimal('750000000'),
    },
    {
        'name': 'Start Cycles',
        'unit': 'cycles',
        'unit_label': 'Start Cycles',
        'is_calendar_based': False,
        'soft_limit': Decimal('18000'),
        'hard_limit': Decimal('25000'),
    },
    {
        'name': 'Shelf Life',
        'unit': 'days',
        'unit_label': 'Days',
        'is_calendar_based': True,
        'soft_limit': Decimal('270'),
        'hard_limit': Decimal('365'),
    },
]


# Demo part type life limit associations
# Maps part type names to life limit names they should have
DEMO_PART_TYPE_LIFE_LIMITS = {
    'Common Rail Injector': ['Operating Hours', 'Start Cycles'],
    'Injector Body': ['Operating Hours', 'Start Cycles'],
    'Plunger Assembly': ['Operating Hours', 'Injection Cycles'],
    'Nozzle': ['Operating Hours', 'Injection Cycles'],
    'Spring Set': ['Operating Hours'],
    'Solenoid Valve': ['Operating Hours', 'Start Cycles'],
    'Control Valve': ['Operating Hours', 'Start Cycles'],
}


# Demo life tracking data for specific cores/parts
# Format: (identifier, life_limit_name, accumulated_value, source, reference_days_ago)
# Note: All fields explicitly set - do not rely on model defaults
# Enum values use UPPERCASE members: LifeTracking.Source.CUSTOMER, .OEM, .LOGBOOK, etc.
DEMO_CORE_LIFE_TRACKING = [
    # Core with moderate usage (B grade)
    {
        'core_identifier': 'CORE-001',
        'tracking': [
            {
                'definition_name': 'Operating Hours',
                'accumulated': Decimal('4250.5'),
                'source': LifeTracking.Source.CUSTOMER,  # UPPERCASE enum
                'cached_status': 'OK',
                'reset_history': [],
                'reference_days_ago': 1825,  # ~5 years
            },
            {
                'definition_name': 'Start Cycles',
                'accumulated': Decimal('11200'),
                'source': LifeTracking.Source.CUSTOMER,  # UPPERCASE enum
                'cached_status': 'OK',
                'reset_history': [],
                'reference_days_ago': 1825,
            },
        ],
    },
    # Core with low usage (A grade)
    {
        'core_identifier': 'CORE-002',
        'tracking': [
            {
                'definition_name': 'Operating Hours',
                'accumulated': Decimal('1850.0'),
                'source': LifeTracking.Source.OEM,  # UPPERCASE enum
                'cached_status': 'OK',
                'reset_history': [],
                'reference_days_ago': 730,  # 2 years
            },
            {
                'definition_name': 'Start Cycles',
                'accumulated': Decimal('4920'),
                'source': LifeTracking.Source.OEM,  # UPPERCASE enum
                'cached_status': 'OK',
                'reset_history': [],
                'reference_days_ago': 730,
            },
        ],
    },
    # Core with high usage (C grade) - near soft limit
    {
        'core_identifier': 'CORE-003',
        'tracking': [
            {
                'definition_name': 'Operating Hours',
                'accumulated': Decimal('7425.0'),
                'source': LifeTracking.Source.LOGBOOK,  # UPPERCASE enum
                'cached_status': 'WARNING',  # Near soft limit
                'reset_history': [],
                'reference_days_ago': 2920,  # ~8 years
            },
            {
                'definition_name': 'Start Cycles',
                'accumulated': Decimal('21380'),
                'source': LifeTracking.Source.LOGBOOK,  # UPPERCASE enum
                'cached_status': 'WARNING',  # Near soft limit
                'reset_history': [],
                'reference_days_ago': 2920,
            },
        ],
    },
    # Core with estimated life data
    {
        'core_identifier': 'CORE-004',
        'tracking': [
            {
                'definition_name': 'Operating Hours',
                'accumulated': Decimal('3100.0'),
                'source': LifeTracking.Source.ESTIMATED,  # UPPERCASE enum
                'cached_status': 'OK',
                'reset_history': [],
                'reference_days_ago': 1460,  # 4 years
            },
            {
                'definition_name': 'Start Cycles',
                'accumulated': Decimal('8540'),
                'source': LifeTracking.Source.ESTIMATED,  # UPPERCASE enum
                'cached_status': 'OK',
                'reset_history': [],
                'reference_days_ago': 1460,
            },
        ],
    },
]


# Demo parts with life tracking (after harvesting/acceptance)
# Note: All fields explicitly set - do not rely on model defaults
# Enum values use UPPERCASE members: LifeTracking.Source.TRANSFERRED, .RESET, etc.
DEMO_PART_LIFE_TRACKING = [
    # Demo order parts with life tracking - connects to main orders seeder
    {
        'part_number': 'INJ-0042-001',  # Completed part from Midwest Fleet order
        'tracking': [
            {
                'definition_name': 'Operating Hours',
                'accumulated': Decimal('3200.0'),
                'source': LifeTracking.Source.CUSTOMER,  # From customer records
                'reference_days_ago': 5,
                'reset_history': [],
            },
        ],
    },
    {
        'part_number': 'INJ-0038-003',  # Reworked part from Great Lakes order
        'tracking': [
            {
                'definition_name': 'Operating Hours',
                'accumulated': Decimal('5800.5'),
                'source': LifeTracking.Source.LOGBOOK,
                'reference_days_ago': 20,
                'reset_history': [],
            },
        ],
    },
    # Part with transferred life from core (harvested component)
    {
        'part_number': 'INJ-BODY-001',
        'tracking': [
            {
                'definition_name': 'Operating Hours',
                'accumulated': Decimal('4250.5'),
                'source': LifeTracking.Source.TRANSFERRED,  # UPPERCASE enum
                'cached_status': 'OK',
                'reset_history': [],
                'reference_days_ago': 1825,
            },
            {
                'definition_name': 'Start Cycles',
                'accumulated': Decimal('11200'),
                'source': LifeTracking.Source.TRANSFERRED,  # UPPERCASE enum
                'cached_status': 'OK',
                'reset_history': [],
                'reference_days_ago': 1825,
            },
        ],
    },
    # Part with reset life after rebuild
    {
        'part_number': 'PLG-001',
        'tracking': [
            {
                'definition_name': 'Operating Hours',
                'accumulated': Decimal('0'),
                'source': LifeTracking.Source.RESET,  # UPPERCASE enum
                'cached_status': 'OK',
                'reset_history': [{'at': '2026-02-03T00:00:00', 'from_value': 4250.5, 'reason': 'Complete rebuild', 'user_id': None}],
                'reference_days_ago': 30,
            },
            {
                'definition_name': 'Injection Cycles',
                'accumulated': Decimal('0'),
                'source': LifeTracking.Source.RESET,  # UPPERCASE enum
                'cached_status': 'OK',
                'reset_history': [{'at': '2026-02-03T00:00:00', 'from_value': 350000000, 'reason': 'Complete rebuild', 'user_id': None}],
                'reference_days_ago': 30,
            },
        ],
    },
]


class DemoLifeTrackingSeeder(BaseSeeder):
    """
    Creates preset demo life tracking data.

    All data is deterministic and supports specific training scenarios:
    - Core intake with life data from different sources
    - Part tracking with transferred life
    - Reset life after rebuild
    - Parts approaching soft/hard limits
    """

    def __init__(self, stdout, style, tenant, scale='small'):
        super().__init__(stdout, style, scale=scale)
        self.tenant = tenant

    def seed(self, part_types=None, cores=None, parts=None):
        """
        Create all demo life tracking data.

        Args:
            part_types: Optional queryset/list of PartTypes to link
            cores: Optional queryset/list of Cores to add tracking to
            parts: Optional queryset/list of Parts to add tracking to

        Returns:
            dict with created data organized by type
        """
        self.log("Creating demo life tracking data...")

        result = {
            'definitions': {},
            'part_type_limits': [],
            'core_tracking': [],
            'part_tracking': [],
        }

        # Phase 1: Life Limit Definitions
        result['definitions'] = self._create_life_limit_definitions()

        # Phase 2: Part Type Life Limit associations
        if part_types:
            result['part_type_limits'] = self._create_part_type_life_limits(
                result['definitions'],
                part_types
            )

        # Phase 3: Core life tracking
        if cores:
            result['core_tracking'] = self._create_core_life_tracking(
                result['definitions'],
                cores
            )

        # Phase 4: Part life tracking
        if parts:
            result['part_tracking'] = self._create_part_life_tracking(
                result['definitions'],
                parts
            )

        self.log(f"  Created {len(result['definitions'])} life limit definitions")
        self.log(f"  Created {len(result['part_type_limits'])} part type associations")
        self.log(f"  Created {len(result['core_tracking'])} core tracking records")
        self.log(f"  Created {len(result['part_tracking'])} part tracking records")

        return result

    def _create_life_limit_definitions(self):
        """Create preset life limit definitions."""
        definitions = {}

        for def_data in DEMO_LIFE_LIMIT_DEFINITIONS:
            definition, created = LifeLimitDefinition.objects.update_or_create(
                tenant=self.tenant,
                name=def_data['name'],
                defaults={
                    'unit': def_data['unit'],
                    'unit_label': def_data['unit_label'],
                    'is_calendar_based': def_data['is_calendar_based'],
                    'soft_limit': def_data['soft_limit'],
                    'hard_limit': def_data['hard_limit'],
                }
            )
            definitions[definition.name] = definition

            action = "Created" if created else "Updated"
            if self.verbose:
                self.log(f"    {action}: {definition.name} (soft: {definition.soft_limit}, hard: {definition.hard_limit})")

        return definitions

    def _create_part_type_life_limits(self, definitions, part_types):
        """Create part type life limit associations."""
        associations = []

        # Convert part_types to dict by name if it's a queryset
        if hasattr(part_types, 'filter'):
            part_type_dict = {pt.name: pt for pt in part_types}
        else:
            part_type_dict = {pt.name: pt for pt in part_types}

        for part_type_name, limit_names in DEMO_PART_TYPE_LIFE_LIMITS.items():
            part_type = part_type_dict.get(part_type_name)
            if not part_type:
                if self.verbose:
                    self.log(f"    Warning: Part type '{part_type_name}' not found", warning=True)
                continue

            for limit_name in limit_names:
                definition = definitions.get(limit_name)
                if not definition:
                    if self.verbose:
                        self.log(f"    Warning: Definition '{limit_name}' not found", warning=True)
                    continue

                # Main injector type has required tracking, components optional
                is_required = (part_type_name == 'Common Rail Injector')

                association, created = PartTypeLifeLimit.objects.update_or_create(
                    part_type=part_type,
                    definition=definition,
                    defaults={
                        'tenant': self.tenant,
                        'is_required': is_required,
                    }
                )
                associations.append(association)

                action = "Created" if created else "Updated"
                req_text = "required" if is_required else "optional"
                if self.verbose:
                    self.log(f"    {action}: {part_type_name} - {limit_name} ({req_text})")

        return associations

    def _create_core_life_tracking(self, definitions, cores):
        """Create life tracking on demo cores."""
        tracking_records = []

        # Convert cores to dict by identifier if needed
        # Assuming cores have a 'serial_number' or similar field
        core_dict = {}
        for core in cores:
            # Try common identifier fields
            identifier = None
            if hasattr(core, 'serial_number'):
                identifier = core.serial_number
            elif hasattr(core, 'core_number'):
                identifier = core.core_number
            elif hasattr(core, 'id'):
                # Fallback to creating identifier from ID
                identifier = f"CORE-{str(core.id)[:3].upper()}"

            if identifier:
                core_dict[identifier] = core

        core_ct = ContentType.objects.get_for_model(Core)

        for core_data in DEMO_CORE_LIFE_TRACKING:
            core = core_dict.get(core_data['core_identifier'])
            if not core:
                # Try to find first available core if exact match not found
                if cores and len(tracking_records) < len(cores):
                    # Use cores in order
                    try:
                        core = list(cores)[len(tracking_records) // 2]  # Spread across available cores
                    except (IndexError, TypeError):
                        continue
                else:
                    if self.verbose:
                        self.log(f"    Warning: Core '{core_data['core_identifier']}' not found", warning=True)
                    continue

            for tracking_data in core_data['tracking']:
                definition = definitions.get(tracking_data['definition_name'])
                if not definition:
                    continue

                # Calculate reference date
                reference_date = timezone.now().date() - timedelta(days=tracking_data['reference_days_ago'])

                tracking, created = LifeTracking.objects.update_or_create(
                    tenant=self.tenant,
                    content_type=core_ct,
                    object_id=core.pk,
                    definition=definition,
                    defaults={
                        'accumulated': tracking_data['accumulated'],
                        'source': tracking_data['source'],  # UPPERCASE enum value
                        'reference_date': reference_date,
                        'cached_status': tracking_data.get('cached_status', 'OK'),
                        'reset_history': tracking_data.get('reset_history', []),
                        # Override fields explicitly set to None
                        'hard_limit_override': None,
                        'soft_limit_override': None,
                        'override_reason': '',
                        'override_approved_by': None,
                    }
                )
                tracking_records.append(tracking)

                action = "Created" if created else "Updated"
                if self.verbose:
                    core_id = getattr(core, 'serial_number', getattr(core, 'core_number', str(core.pk)))
                    self.log(f"    {action}: Core {core_id} - {definition.name}: {tracking.accumulated} {definition.unit_label}")

        return tracking_records

    def _create_part_life_tracking(self, definitions, parts):
        """Create life tracking on demo parts."""
        tracking_records = []

        # Convert parts to dict by part_number or ERP_id
        part_dict = {}
        for part in parts:
            # Try part_number first (for harvested components)
            if hasattr(part, 'part_number') and part.part_number:
                part_dict[part.part_number] = part
            # Also map by ERP_id (serial number for regular parts like INJ-0042-001)
            if hasattr(part, 'ERP_id') and part.ERP_id:
                part_dict[part.ERP_id] = part

        parts_ct = ContentType.objects.get_for_model(Parts)

        for part_data in DEMO_PART_LIFE_TRACKING:
            part = part_dict.get(part_data['part_number'])
            if not part:
                # Try to find first available part if exact match not found
                if parts and len(tracking_records) < len(parts):
                    try:
                        part = list(parts)[len(tracking_records)]
                    except (IndexError, TypeError):
                        continue
                else:
                    if self.verbose:
                        self.log(f"    Warning: Part '{part_data['part_number']}' not found", warning=True)
                    continue

            for tracking_data in part_data['tracking']:
                definition = definitions.get(tracking_data['definition_name'])
                if not definition:
                    continue

                # Calculate reference date
                reference_date = timezone.now().date() - timedelta(days=tracking_data['reference_days_ago'])

                tracking, created = LifeTracking.objects.update_or_create(
                    tenant=self.tenant,
                    content_type=parts_ct,
                    object_id=part.pk,
                    definition=definition,
                    defaults={
                        'accumulated': tracking_data['accumulated'],
                        'source': tracking_data['source'],  # UPPERCASE enum value
                        'reference_date': reference_date,
                        'cached_status': tracking_data.get('cached_status', 'OK'),
                        'reset_history': tracking_data.get('reset_history', []),
                        # Override fields explicitly set to None
                        'hard_limit_override': None,
                        'soft_limit_override': None,
                        'override_reason': '',
                        'override_approved_by': None,
                    }
                )
                tracking_records.append(tracking)

                action = "Created" if created else "Updated"
                if self.verbose:
                    part_num = getattr(part, 'part_number', str(part.pk))
                    self.log(f"    {action}: Part {part_num} - {definition.name}: {tracking.accumulated} {definition.unit_label}")

        return tracking_records

    @property
    def verbose(self):
        """Check if verbose output is enabled."""
        return getattr(self, '_verbose', False)

    @verbose.setter
    def verbose(self, value):
        self._verbose = value
