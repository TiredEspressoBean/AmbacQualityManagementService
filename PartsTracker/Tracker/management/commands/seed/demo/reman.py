"""
Demo remanufacturing seeder with preset, deterministic reman data.

Creates:
- DisassemblyBOMLines for Common Rail Injector disassembly
- Cores with different statuses (RECEIVED, IN_DISASSEMBLY, DISASSEMBLED)
- HarvestedComponents from cores with grades (A, B, C, SCRAP)

All data is deterministic - same result every time for demo consistency.
"""

from datetime import timedelta
from decimal import Decimal
from django.utils import timezone

from Tracker.models import (
    Core, HarvestedComponent, DisassemblyBOMLine,
    PartTypes, Companies, User,
)

from ..base import BaseSeeder


# Component definitions for injector disassembly (reverse BOM)
DEMO_DISASSEMBLY_BOM = [
    {
        'component_name': 'Injector Body',
        'component_prefix': 'BODY',
        'expected_qty': 1,
        'expected_fallout_rate': Decimal('0.05'),  # 5%
        'line_number': 1,
        'notes': 'Main housing - check for cracks and corrosion',
    },
    {
        'component_name': 'Nozzle',
        'component_prefix': 'NOZL',
        'expected_qty': 1,
        'expected_fallout_rate': Decimal('0.15'),  # 15%
        'line_number': 2,
        'notes': 'Critical wear item - verify spray pattern capability',
    },
    {
        'component_name': 'Solenoid Valve',
        'component_prefix': 'SOLV',
        'expected_qty': 1,
        'expected_fallout_rate': Decimal('0.08'),  # 8%
        'line_number': 3,
        'notes': 'Electronic component - test resistance and response time',
    },
]


# Preset demo cores with specific narratives
DEMO_CORES = [
    # Recently received cores
    {
        'core_number': 'CORE-240225-0001',
        'serial_number': 'SN-CRI-A47F92E1',
        'received_days_ago': 2,
        'status': 'RECEIVED',
        'condition_grade': 'B',
        'condition_notes': 'Good condition with normal wear patterns. Light corrosion on external surfaces.',
        'source_type': 'CUSTOMER_RETURN',
        'source_reference': 'RMA-45821',
        'customer_name': 'Midwest Fleet Services',
        'core_credit_value': Decimal('125.00'),
        'core_credit_issued': False,
    },
    {
        'core_number': 'CORE-240225-0002',
        'serial_number': 'SN-CRI-B23D14C8',
        'received_days_ago': 2,
        'status': 'RECEIVED',
        'condition_grade': 'C',
        'condition_notes': 'Fair condition. Heavy wear on nozzle tip. Carbon deposits present.',
        'source_type': 'CUSTOMER_RETURN',
        'source_reference': 'RMA-45821',
        'customer_name': 'Midwest Fleet Services',
        'core_credit_value': Decimal('75.00'),
        'core_credit_issued': False,
    },
    # Cores in disassembly
    {
        'core_number': 'CORE-240220-0003',
        'serial_number': 'SN-CRI-C89A55F3',
        'received_days_ago': 7,
        'status': 'IN_DISASSEMBLY',
        'disassembly_started_days_ago': 6,
        'condition_grade': 'A',
        'condition_notes': 'Excellent condition. Minimal wear. All components present.',
        'source_type': 'PURCHASED',
        'source_reference': 'PO-78432',
        'customer_name': 'Great Lakes Diesel',
        'core_credit_value': Decimal('175.00'),
        'core_credit_issued': False,
    },
    {
        'core_number': 'CORE-240220-0004',
        'serial_number': 'SN-CRI-D12B77A9',
        'received_days_ago': 7,
        'status': 'IN_DISASSEMBLY',
        'disassembly_started_days_ago': 5,
        'condition_grade': 'B',
        'condition_notes': 'Good condition. Some carbon buildup. Standard cleaning required.',
        'source_type': 'PURCHASED',
        'source_reference': 'PO-78432',
        'customer_name': 'Great Lakes Diesel',
        'core_credit_value': Decimal('135.00'),
        'core_credit_issued': False,
    },
    # Fully disassembled cores (components harvested)
    {
        'core_number': 'CORE-240215-0005',
        'serial_number': 'SN-CRI-E56F88D2',
        'received_days_ago': 12,
        'status': 'DISASSEMBLED',
        'disassembly_started_days_ago': 11,
        'disassembly_completed_days_ago': 10,
        'condition_grade': 'B',
        'condition_notes': 'Good condition with normal wear patterns.',
        'source_type': 'CUSTOMER_RETURN',
        'source_reference': 'RMA-45103',
        'customer_name': 'Northern Trucking Co',
        'core_credit_value': Decimal('110.00'),
        'core_credit_issued': True,
        'components': [
            {
                'component_name': 'Injector Body',
                'condition_grade': 'A',
                'disposition': 'REUSE',
                'condition_notes': 'Excellent. Ready for reuse without rework.',
                'position': '',
                'original_part_number': '',
                'is_scrapped': False,
                'scrap_reason': '',
            },
            {
                'component_name': 'Nozzle',
                'condition_grade': 'B',
                'disposition': 'REFURBISH',
                'condition_notes': 'Good condition. Minor surface wear acceptable.',
                'position': '',
                'original_part_number': '',
                'is_scrapped': False,
                'scrap_reason': '',
            },
            {
                'component_name': 'Solenoid Valve',
                'condition_grade': 'A',
                'disposition': 'REUSE',
                'condition_notes': 'Pristine condition. Passes all dimensional checks.',
                'position': '',
                'original_part_number': '',
                'is_scrapped': False,
                'scrap_reason': '',
            },
        ],
    },
    {
        'core_number': 'CORE-240215-0006',
        'serial_number': 'SN-CRI-F91C22B5',
        'received_days_ago': 12,
        'status': 'DISASSEMBLED',
        'disassembly_started_days_ago': 11,
        'disassembly_completed_days_ago': 9,
        'condition_grade': 'C',
        'condition_notes': 'Fair condition. Significant corrosion. May have high fallout.',
        'source_type': 'CUSTOMER_RETURN',
        'source_reference': 'RMA-45103',
        'customer_name': 'Northern Trucking Co',
        'core_credit_value': Decimal('60.00'),
        'core_credit_issued': True,
        'components': [
            {
                'component_name': 'Injector Body',
                'condition_grade': 'B',
                'disposition': 'REFURBISH',
                'condition_notes': 'Standard wear patterns. Suitable for rework.',
                'position': '',
                'original_part_number': '',
                'is_scrapped': False,
                'scrap_reason': '',
            },
            {
                'component_name': 'Nozzle',
                'condition_grade': 'SCRAP',
                'disposition': 'SCRAP',
                'condition_notes': 'Exceeded maximum wear limits.',
                'position': '',
                'original_part_number': '',
                'is_scrapped': True,
                'scrap_reason': 'Nozzle tip wear beyond tolerance',
            },
            {
                'component_name': 'Solenoid Valve',
                'condition_grade': 'C',
                'disposition': 'PENDING',
                'condition_notes': 'Fair condition. Near tolerance limits.',
                'position': '',
                'original_part_number': '',
                'is_scrapped': False,
                'scrap_reason': '',
            },
        ],
    },
    {
        'core_number': 'CORE-240210-0007',
        'serial_number': 'SN-CRI-G33E44F8',
        'received_days_ago': 17,
        'status': 'DISASSEMBLED',
        'disassembly_started_days_ago': 16,
        'disassembly_completed_days_ago': 15,
        'condition_grade': 'A',
        'condition_notes': 'Excellent condition. Very clean. No visible damage.',
        'source_type': 'CUSTOMER_RETURN',
        'source_reference': 'WTY-63271',
        'customer_name': 'Midwest Fleet Services',
        'core_credit_value': Decimal('185.00'),
        'core_credit_issued': True,
        'components': [
            {
                'component_name': 'Injector Body',
                'condition_grade': 'A',
                'disposition': 'REUSE',
                'condition_notes': 'Excellent. Ready for reuse without rework.',
                'position': '',
                'original_part_number': '',
                'is_scrapped': False,
                'scrap_reason': '',
            },
            {
                'component_name': 'Nozzle',
                'condition_grade': 'A',
                'disposition': 'REUSE',
                'condition_notes': 'Minimal wear. Within all tolerances.',
                'position': '',
                'original_part_number': '',
                'is_scrapped': False,
                'scrap_reason': '',
            },
            {
                'component_name': 'Solenoid Valve',
                'condition_grade': 'A',
                'disposition': 'REUSE',
                'condition_notes': 'Pristine condition. Passes all dimensional checks.',
                'position': '',
                'original_part_number': '',
                'is_scrapped': False,
                'scrap_reason': '',
            },
        ],
    },
    # Scrapped core
    {
        'core_number': 'CORE-240218-0008',
        'serial_number': 'SN-CRI-H77A99D1',
        'received_days_ago': 9,
        'status': 'SCRAPPED',
        'condition_grade': 'SCRAP',
        'condition_notes': 'Severe damage. Cracked body - not salvageable. Heavy corrosion damage throughout.',
        'source_type': 'CUSTOMER_RETURN',
        'source_reference': 'RMA-45673',
        'customer_name': 'Great Lakes Diesel',
        'core_credit_value': None,
        'core_credit_issued': False,
    },
]


class DemoRemanSeeder(BaseSeeder):
    """
    Creates preset remanufacturing data for the demo scenario.

    All data is deterministic and tied to specific demo narratives:
    - Fresh cores from Midwest Fleet (recently received)
    - Cores in active disassembly
    - Completed disassembly with harvested components
    - One scrapped core example
    """

    def __init__(self, stdout, style, tenant, scale='small'):
        super().__init__(stdout, style, scale=scale)
        self.tenant = tenant
        self.today = timezone.now()

    def seed(self, companies, users, part_types):
        """
        Create all demo reman data.

        Args:
            companies: dict with company lists (from DemoCompanySeeder)
            users: dict with user lists (from DemoUsersSeeder)
            part_types: list of PartTypes

        Returns:
            dict with created cores, components, and BOM lines
        """
        self.log("Creating demo remanufacturing data...")

        result = {
            'bom_lines': [],
            'cores': [],
            'components': [],
        }

        # Get component part types (create if needed)
        component_types = self._ensure_component_part_types()

        # Create DisassemblyBOMLines
        result['bom_lines'] = self._create_disassembly_bom_lines(part_types, component_types)

        # Create cores
        result['cores'] = self._create_cores(companies, users)

        # Create harvested components from disassembled cores
        result['components'] = self._create_harvested_components(result['cores'], users)

        self.log(f"  Created {len(result['bom_lines'])} disassembly BOM lines")
        self.log(f"  Created {len(result['cores'])} cores")
        self.log(f"  Created {len(result['components'])} harvested components")

        return result

    def _ensure_component_part_types(self):
        """Ensure component part types exist for harvesting."""
        component_types = {}

        for comp_data in DEMO_DISASSEMBLY_BOM:
            comp_name = comp_data['component_name']
            comp_prefix = comp_data['component_prefix']

            # Use update_or_create for deterministic creation
            comp_type, _ = PartTypes.objects.update_or_create(
                tenant=self.tenant,
                name=comp_name,
                defaults={
                    'ID_prefix': comp_prefix,
                }
            )
            component_types[comp_name] = comp_type

        return component_types

    def _create_disassembly_bom_lines(self, part_types, component_types):
        """Create DisassemblyBOMLines defining expected yields."""
        bom_lines = []

        # Find the Common Rail Injector part type (core type)
        cri_type = None
        for pt in part_types:
            if 'Common Rail' in pt.name:
                cri_type = pt
                break

        if not cri_type:
            self.log("  Warning: Common Rail Injector part type not found, skipping BOM lines")
            return bom_lines

        for bom_data in DEMO_DISASSEMBLY_BOM:
            comp_type = component_types.get(bom_data['component_name'])
            if not comp_type:
                continue

            bom_line, _ = DisassemblyBOMLine.objects.update_or_create(
                tenant=self.tenant,
                core_type=cri_type,
                component_type=comp_type,
                defaults={
                    'expected_qty': bom_data['expected_qty'],
                    'expected_fallout_rate': bom_data['expected_fallout_rate'],
                    'line_number': bom_data['line_number'],
                    'notes': bom_data['notes'],
                }
            )
            bom_lines.append(bom_line)

        return bom_lines

    def _create_cores(self, companies, users):
        """Create preset demo cores."""
        cores = []

        # Get company lookup
        if isinstance(companies, dict):
            company_map = companies.get('by_name', {})
        else:
            company_map = {c.name: c for c in companies} if companies else {}

        # Get employees for received_by, disassembled_by
        employees = users.get('employees', []) if isinstance(users, dict) else []
        if not employees:
            self.log("  Warning: No employees available for core creation")
            return cores

        # Get Common Rail Injector part type
        core_type = PartTypes.objects.filter(
            tenant=self.tenant,
            name__icontains='Common Rail'
        ).first()

        if not core_type:
            self.log("  Warning: Common Rail Injector part type not found")
            return cores

        for core_data in DEMO_CORES:
            core = self._create_single_core(core_data, core_type, company_map, employees)
            if core:
                cores.append(core)

        return cores

    def _create_single_core(self, core_data, core_type, company_map, employees):
        """Create a single core from configuration."""
        # Get customer company
        customer = company_map.get(core_data.get('customer_name'))

        # Calculate dates
        received_date = (self.today - timedelta(days=core_data['received_days_ago'])).date()
        received_datetime = timezone.make_aware(
            timezone.datetime.combine(received_date, timezone.datetime.min.time())
        ) + timedelta(hours=9)  # 9 AM receipt

        # Get a receiving employee
        received_by = employees[0] if employees else None

        # Calculate disassembly timestamps if applicable
        disassembly_started_at = None
        disassembly_completed_at = None
        disassembled_by = None

        if 'disassembly_started_days_ago' in core_data:
            disassembly_started_at = received_datetime + timedelta(
                days=core_data['received_days_ago'] - core_data['disassembly_started_days_ago']
            )

        if 'disassembly_completed_days_ago' in core_data:
            disassembly_completed_at = received_datetime + timedelta(
                days=core_data['received_days_ago'] - core_data['disassembly_completed_days_ago']
            )
            disassembled_by = employees[1] if len(employees) > 1 else employees[0]

        # Calculate core credit issued timestamp if applicable
        core_credit_issued_at = None
        if core_data.get('core_credit_issued') and disassembly_completed_at:
            core_credit_issued_at = disassembly_completed_at + timedelta(days=1)

        # Create the core with ALL fields explicitly set
        core, _ = Core.objects.update_or_create(
            tenant=self.tenant,
            core_number=core_data['core_number'],
            defaults={
                'serial_number': core_data['serial_number'],
                'core_type': core_type,
                'received_date': received_date,
                'received_by': received_by,
                'customer': customer,
                'source_type': core_data['source_type'],
                'source_reference': core_data['source_reference'],
                'condition_grade': core_data['condition_grade'],
                'condition_notes': core_data['condition_notes'],
                'status': core_data['status'],
                'disassembly_started_at': disassembly_started_at,
                'disassembly_completed_at': disassembly_completed_at,
                'disassembled_by': disassembled_by,
                'core_credit_value': core_data.get('core_credit_value'),
                'core_credit_issued': core_data.get('core_credit_issued', False),
                'core_credit_issued_at': core_credit_issued_at,
                'work_order': None,
            }
        )

        # Backdate the created_at timestamp
        Core.objects.filter(pk=core.pk).update(created_at=received_datetime)

        core.refresh_from_db()
        return core

    def _create_harvested_components(self, cores, users):
        """Create harvested components from disassembled cores."""
        components = []

        # Get employees for disassembled_by
        employees = users.get('employees', []) if isinstance(users, dict) else []
        if not employees:
            return components

        # Only process cores that have component definitions
        for core in cores:
            core_data = next((c for c in DEMO_CORES if c['core_number'] == core.core_number), None)
            if not core_data or 'components' not in core_data:
                continue

            # Get component type lookup
            component_types = {
                ct.name: ct for ct in PartTypes.objects.filter(tenant=self.tenant)
            }

            for comp_data in core_data['components']:
                comp_type = component_types.get(comp_data['component_name'])
                if not comp_type:
                    continue

                component = self._create_single_component(
                    core, comp_type, comp_data, employees
                )
                if component:
                    components.append(component)

        return components

    def _create_single_component(self, core, comp_type, comp_data, employees):
        """Create a single harvested component."""
        # Use disassembly completion time or approximate
        if core.disassembly_completed_at:
            disassembled_at = core.disassembly_completed_at
        elif core.disassembly_started_at:
            disassembled_at = core.disassembly_started_at + timedelta(hours=2)
        else:
            disassembled_at = timezone.now()

        # Get disassembly operator
        disassembled_by = employees[1] if len(employees) > 1 else employees[0]

        # Determine scrap timestamps if scrapped
        scrapped_at = None
        scrapped_by = None
        if comp_data['is_scrapped']:
            scrapped_at = disassembled_at + timedelta(minutes=30)
            scrapped_by = employees[2] if len(employees) > 2 else employees[0]

        # Create the component with ALL fields explicitly set
        component, _ = HarvestedComponent.objects.update_or_create(
            tenant=self.tenant,
            core=core,
            component_type=comp_type,
            position=comp_data.get('position', ''),
            defaults={
                'component_part': None,
                'disassembled_by': disassembled_by,
                'condition_grade': comp_data['condition_grade'],
                'condition_notes': comp_data['condition_notes'],
                'is_scrapped': comp_data['is_scrapped'],
                'scrap_reason': comp_data['scrap_reason'],
                'scrapped_at': scrapped_at,
                'scrapped_by': scrapped_by,
                'original_part_number': comp_data.get('original_part_number', ''),
            }
        )

        # Backdate timestamps
        HarvestedComponent.objects.filter(pk=component.pk).update(
            disassembled_at=disassembled_at,
            created_at=disassembled_at,
        )

        component.refresh_from_db()
        return component
