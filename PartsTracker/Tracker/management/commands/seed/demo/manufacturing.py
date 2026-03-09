"""
Demo manufacturing seeder with preset part types, processes, and equipment.

Creates deterministic manufacturing setup matching DEMO_DATA_SYSTEM.md:
- Part types: Common Rail Injector (primary)
- Process: Injector Reman with 12 steps including rework loop
- Equipment: Flow test stands, torque wrenches, with calibration status
"""

from datetime import timedelta
from django.utils import timezone

from django.contrib.auth.models import Group

from Tracker.models import (
    PartTypes, Processes, Steps, ProcessStep, StepEdge,
    Equipments, EquipmentType, MeasurementDefinition,
    CalibrationRecord, EquipmentStatus,
)
from Tracker.models.mes_lite import ProcessStatus, EdgeType

from ..base import BaseSeeder


# Demo part types
# Note: PartTypes model fields are: name, ID_prefix, ERP_id (no description field)
DEMO_PART_TYPES = [
    {
        'name': 'Common Rail Injector',
        'ERP_id': 'CRI-001',
        'ID_prefix': 'INJ',
    },
]

# Demo process with steps
# Processes model fields: name, is_remanufactured, part_type (FK), is_batch_process,
# status, category, change_description, approved_at/by
# NOTE: There is NO 'description' field on Processes - removed invalid field
# Steps within use: name, order, requires_qa_signoff, description (Steps model has description)
#
# ALL Steps model fields must be explicitly set:
# - Basic: name, description, pass_threshold, expected_duration
# - QA/Sampling: block_on_quarantine, requires_qa_signoff, sampling_required, min_sampling_rate
# - FPI: requires_first_piece_inspection, fpi_scope
# - Workflow: block_on_measurement_failure, block_on_spc_violation, override_expiry_hours
# - Undo: undo_window_minutes, rollback_requires_approval
# - Batch: requires_batch_completion
# - Type: step_type, is_decision_point, decision_type
# - Terminal: is_terminal, terminal_status
# - Cycle: max_visits, revisit_assignment, revisit_role (Group FK - use group name, resolved at runtime)
DEMO_PROCESS = {
    'name': 'Injector Reman',
    'is_remanufactured': True,
    'category': 'MANUFACTURING',
    'steps': [
        {
            'name': 'Core Receiving', 'order': 1, 'description': 'Receive and grade incoming cores',
            'pass_threshold': 1.0, 'expected_duration': None,
            'block_on_quarantine': True, 'requires_qa_signoff': True,
            'sampling_required': False, 'min_sampling_rate': 0.0,
            'requires_first_piece_inspection': False, 'fpi_scope': 'PER_WORKORDER',
            'block_on_measurement_failure': False, 'block_on_spc_violation': False,
            'override_expiry_hours': 24, 'undo_window_minutes': 15, 'rollback_requires_approval': True,
            'requires_batch_completion': False,
            'max_visits': None, 'revisit_assignment': 'ANY', 'revisit_role_name': None,
        },
        {
            'name': 'Disassembly', 'order': 2, 'description': 'Disassemble injector into components',
            'pass_threshold': 1.0, 'expected_duration': None,
            'block_on_quarantine': False, 'requires_qa_signoff': False,
            'sampling_required': False, 'min_sampling_rate': 0.0,
            'requires_first_piece_inspection': False, 'fpi_scope': 'PER_WORKORDER',
            'block_on_measurement_failure': False, 'block_on_spc_violation': False,
            'override_expiry_hours': 24, 'undo_window_minutes': 30, 'rollback_requires_approval': False,
            'requires_batch_completion': False,
            'max_visits': None, 'revisit_assignment': 'ANY', 'revisit_role_name': None,
        },
        {
            'name': 'Component Grading', 'order': 3, 'description': 'Grade and sort components by condition',
            'pass_threshold': 1.0, 'expected_duration': None,
            'block_on_quarantine': True, 'requires_qa_signoff': True,
            'sampling_required': False, 'min_sampling_rate': 0.0,
            'requires_first_piece_inspection': False, 'fpi_scope': 'PER_WORKORDER',
            'block_on_measurement_failure': False, 'block_on_spc_violation': False,
            'override_expiry_hours': 24, 'undo_window_minutes': 15, 'rollback_requires_approval': True,
            'requires_batch_completion': False,
            'max_visits': None, 'revisit_assignment': 'ANY', 'revisit_role_name': None,
        },
        {
            'name': 'Cleaning', 'order': 4, 'description': 'Ultrasonic clean all components',
            'pass_threshold': 1.0, 'expected_duration': None,
            'block_on_quarantine': False, 'requires_qa_signoff': False,
            'sampling_required': False, 'min_sampling_rate': 0.0,
            'requires_first_piece_inspection': False, 'fpi_scope': 'PER_WORKORDER',
            'block_on_measurement_failure': False, 'block_on_spc_violation': False,
            'override_expiry_hours': 24, 'undo_window_minutes': 60, 'rollback_requires_approval': False,
            'requires_batch_completion': True,  # All parts cleaned together
            'max_visits': None, 'revisit_assignment': 'ANY', 'revisit_role_name': None,
        },
        {
            'name': 'Nozzle Inspection', 'order': 5, 'description': 'Inspect nozzle spray pattern and wear',
            'pass_threshold': 1.0, 'expected_duration': None,
            'block_on_quarantine': True, 'requires_qa_signoff': True,
            'sampling_required': True, 'min_sampling_rate': 0.25,  # 25% sampling
            'requires_first_piece_inspection': True, 'fpi_scope': 'PER_WORKORDER',  # FPI enabled
            'block_on_measurement_failure': True, 'block_on_spc_violation': True,  # SPC-enabled step
            'override_expiry_hours': 8, 'undo_window_minutes': 15, 'rollback_requires_approval': True,
            'requires_batch_completion': False,
            'max_visits': 2, 'revisit_assignment': 'ROLE', 'revisit_role_name': 'QA Manager',
        },
        {
            'name': 'Flow Testing', 'order': 6, 'description': 'Test fuel flow rate and pressure',
            'pass_threshold': 1.0, 'expected_duration': None,
            'block_on_quarantine': True, 'requires_qa_signoff': True,
            'sampling_required': True, 'min_sampling_rate': 0.20,  # 20% sampling
            'requires_first_piece_inspection': True, 'fpi_scope': 'PER_WORKORDER',  # FPI enabled
            'block_on_measurement_failure': True, 'block_on_spc_violation': True,  # SPC-enabled step
            'override_expiry_hours': 8, 'undo_window_minutes': 15, 'rollback_requires_approval': True,
            'requires_batch_completion': False,
            'max_visits': 2, 'revisit_assignment': 'ROLE', 'revisit_role_name': 'QA Manager',
        },
        {
            'name': 'Assembly', 'order': 7, 'description': 'Reassemble injector with new seals',
            'pass_threshold': 1.0, 'expected_duration': None,
            'block_on_quarantine': False, 'requires_qa_signoff': False,
            'sampling_required': False, 'min_sampling_rate': 0.0,
            'requires_first_piece_inspection': False, 'fpi_scope': 'PER_WORKORDER',
            'block_on_measurement_failure': True, 'block_on_spc_violation': False,  # Torque measurement
            'override_expiry_hours': 24, 'undo_window_minutes': 30, 'rollback_requires_approval': False,
            'requires_batch_completion': False,
            'max_visits': None, 'revisit_assignment': 'ANY', 'revisit_role_name': None,
        },
        {
            'name': 'Final Test', 'order': 8, 'description': 'Final functional test under pressure',
            'pass_threshold': 1.0, 'expected_duration': None,
            'block_on_quarantine': True, 'requires_qa_signoff': True,
            'sampling_required': True, 'min_sampling_rate': 0.10,  # 10% sampling
            'requires_first_piece_inspection': True, 'fpi_scope': 'PER_WORKORDER',  # FPI enabled
            'block_on_measurement_failure': True, 'block_on_spc_violation': True,  # SPC-enabled step
            'override_expiry_hours': 4, 'undo_window_minutes': 15, 'rollback_requires_approval': True,
            'requires_batch_completion': False,
            'max_visits': 2, 'revisit_assignment': 'ROLE', 'revisit_role_name': 'QA Manager',
        },
        {
            'name': 'Packaging', 'order': 9, 'description': 'Package for shipping',
            'pass_threshold': 1.0, 'expected_duration': None,
            'block_on_quarantine': False, 'requires_qa_signoff': False,
            'sampling_required': False, 'min_sampling_rate': 0.0,
            'requires_first_piece_inspection': False, 'fpi_scope': 'PER_WORKORDER',
            'block_on_measurement_failure': False, 'block_on_spc_violation': False,
            'override_expiry_hours': 24, 'undo_window_minutes': 60, 'rollback_requires_approval': False,
            'requires_batch_completion': False,
            'max_visits': None, 'revisit_assignment': 'ANY', 'revisit_role_name': None,
        },
        {
            'name': 'Complete', 'order': 10, 'description': 'Order complete and ready to ship',
            'pass_threshold': 1.0, 'expected_duration': None,
            'block_on_quarantine': False, 'requires_qa_signoff': False,
            'sampling_required': False, 'min_sampling_rate': 0.0,
            'requires_first_piece_inspection': False, 'fpi_scope': 'PER_WORKORDER',
            'block_on_measurement_failure': False, 'block_on_spc_violation': False,
            'override_expiry_hours': 24, 'undo_window_minutes': 0, 'rollback_requires_approval': True,
            'requires_batch_completion': False,
            'max_visits': None, 'revisit_assignment': 'ANY', 'revisit_role_name': None,
        },
        {
            'name': 'Rework', 'order': 11, 'description': 'Rework station for failed parts',
            'pass_threshold': 1.0, 'expected_duration': None,
            'block_on_quarantine': False, 'requires_qa_signoff': False,
            'sampling_required': False, 'min_sampling_rate': 0.0,
            'requires_first_piece_inspection': False, 'fpi_scope': 'PER_WORKORDER',
            'block_on_measurement_failure': False, 'block_on_spc_violation': False,
            'override_expiry_hours': 24, 'undo_window_minutes': 30, 'rollback_requires_approval': True,
            'requires_batch_completion': False,
            'max_visits': 3, 'revisit_assignment': 'DIFFERENT', 'revisit_role_name': None,  # Different operator for rework
        },
    ],
}

# Demo equipment types
# EquipmentType model fields: name, description, requires_calibration, default_calibration_interval_days,
# is_portable, track_downtime
# Note: requires_calibration drives whether calibration tracking is enabled for equipment of this type
DEMO_EQUIPMENT_TYPES = [
    {
        'name': 'Flow Bench',
        'description': 'Precision flow testing equipment',
        'requires_calibration': True,
        'default_calibration_interval_days': 90,
        'is_portable': False,
        'track_downtime': True,
    },
    {
        'name': 'Torque Tool',
        'description': 'Calibrated torque wrenches',
        'requires_calibration': True,
        'default_calibration_interval_days': 60,
        'is_portable': True,
        'track_downtime': False,
    },
    {
        'name': 'Cleaning Station',
        'description': 'Ultrasonic cleaning equipment',
        'requires_calibration': False,  # Cleaning stations don't need calibration
        'default_calibration_interval_days': None,
        'is_portable': False,
        'track_downtime': True,
    },
    {
        'name': 'Test Bench',
        'description': 'Functional test benches',
        'requires_calibration': True,
        'default_calibration_interval_days': 90,
        'is_portable': False,
        'track_downtime': True,
    },
]

# Demo equipment
# Equipments model fields: name, serial_number, equipment_type (FK), status, location,
# calibration_interval_days, manufacturer, model_number, notes
# Note: calibration_days is used to calculate CalibrationRecord.due_date (negative = overdue)
# Calibration tracking happens via CalibrationRecord model, NOT on Equipments directly
DEMO_EQUIPMENT = [
    {'name': 'Flow Test Stand #1', 'type': 'Flow Bench', 'serial': 'FTS-001', 'calibration_days': 30, 'location': 'QA Lab'},
    {'name': 'Flow Test Stand #2', 'type': 'Flow Bench', 'serial': 'FTS-002', 'calibration_days': 60, 'location': 'QA Lab'},
    {'name': 'Torque Wrench TW-25', 'type': 'Torque Tool', 'serial': 'TW-025', 'calibration_days': -15, 'location': 'Tool Crib'},  # OVERDUE
    {'name': 'Torque Wrench TW-26', 'type': 'Torque Tool', 'serial': 'TW-026', 'calibration_days': 45, 'location': 'Tool Crib'},
    {'name': 'Ultrasonic Cleaner UC-1', 'type': 'Cleaning Station', 'serial': 'UC-001', 'calibration_days': None, 'location': 'Machine Shop'},  # No calibration needed
    {'name': 'Final Test Bench FTB-1', 'type': 'Test Bench', 'serial': 'FTB-001', 'calibration_days': 25, 'location': 'QA Lab'},
]

# Demo measurement definitions
# Note: Fields use model names (label, type, nominal, upper_tol, lower_tol)
# Tolerances are relative to nominal (not absolute spec limits)
# Numeric fields have precision 9, scale 6 - values must be < 1000
DEMO_MEASUREMENTS = [
    {
        'label': 'Flow Rate',
        'step': 'Flow Testing',
        'unit': 'mL/min',
        'nominal': 120.0,
        'lower_tol': 20.0,  # LSL = 120 - 20 = 100
        'upper_tol': 20.0,  # USL = 120 + 20 = 140
        'type': 'NUMERIC',
        'spc_enabled': True,
    },
    {
        'label': 'Spray Angle',
        'step': 'Nozzle Inspection',
        'unit': 'degrees',
        'nominal': 15.0,
        'lower_tol': 3.0,   # LSL = 15 - 3 = 12
        'upper_tol': 3.0,   # USL = 15 + 3 = 18
        'type': 'NUMERIC',
        'spc_enabled': True,
    },
    {
        'label': 'Spray Pattern',
        'step': 'Nozzle Inspection',
        'unit': '',
        'nominal': None,
        'lower_tol': None,
        'upper_tol': None,
        'type': 'PASS_FAIL',
        'spc_enabled': False,
    },
    {
        'label': 'Leak Test Pressure',
        'step': 'Final Test',
        'unit': 'bar',
        'nominal': 200.0,   # Scaled down from 2000 to fit decimal precision
        'lower_tol': 5.0,   # LSL = 200 - 5 = 195
        'upper_tol': 5.0,   # USL = 200 + 5 = 205
        'type': 'NUMERIC',
        'spc_enabled': True,
    },
    {
        'label': 'Assembly Torque',
        'step': 'Assembly',
        'unit': 'Nm',
        'nominal': 25.0,
        'lower_tol': 2.0,   # LSL = 25 - 2 = 23
        'upper_tol': 2.0,   # USL = 25 + 2 = 27
        'type': 'NUMERIC',
        'spc_enabled': False,
    },
]


class DemoManufacturingSeeder(BaseSeeder):
    """
    Creates preset manufacturing setup for demo tenant.

    All data is deterministic - same result every time.
    """

    def __init__(self, stdout, style, tenant, scale='small'):
        super().__init__(stdout, style, scale=scale)
        self.tenant = tenant
        self.today = timezone.now().date()

    def seed(self, users=None):
        """
        Create all demo manufacturing data.

        Returns:
            dict with created data organized by type
        """
        self.log("Creating demo manufacturing setup...")

        result = {
            'part_types': [],
            'processes': [],
            'steps': [],
            'equipment': [],
            'equipment_types': [],
            'measurement_definitions': [],
        }

        # Create equipment types first
        result['equipment_types'] = self._create_equipment_types()

        # Create equipment
        result['equipment'] = self._create_equipment(result['equipment_types'])

        # Create part types first (required for process)
        result['part_types'] = self._create_part_types()

        # Create process and steps (needs part_type)
        primary_part_type = result['part_types'][0] if result['part_types'] else None
        process, steps = self._create_process_and_steps(primary_part_type)
        result['processes'] = [process]
        result['steps'] = steps

        # Link part types back to process (circular dependency)
        self._link_part_types_to_process(result['part_types'], process)

        # Create measurement definitions
        result['measurement_definitions'] = self._create_measurement_definitions(steps)

        self.log(f"  Created {len(result['part_types'])} part types")
        self.log(f"  Created {len(result['steps'])} steps in {len(result['processes'])} process")
        self.log(f"  Created {len(result['equipment'])} equipment items")
        self.log(f"  Created {len(result['measurement_definitions'])} measurement definitions")

        return result

    def _create_equipment_types(self):
        """Create equipment types with calibration and tracking settings."""
        equipment_types = []
        for et_data in DEMO_EQUIPMENT_TYPES:
            et, _ = EquipmentType.objects.update_or_create(
                tenant=self.tenant,
                name=et_data['name'],
                defaults={
                    'description': et_data.get('description', ''),
                    'requires_calibration': et_data.get('requires_calibration', False),
                    'default_calibration_interval_days': et_data.get('default_calibration_interval_days'),
                    'is_portable': et_data.get('is_portable', False),
                    'track_downtime': et_data.get('track_downtime', True),
                }
            )
            equipment_types.append(et)
        return equipment_types

    def _create_equipment(self, equipment_types):
        """Create equipment with calibration records where required.

        Equipments model fields: name, serial_number, equipment_type, status, location,
        calibration_interval_days, _requires_calibration_override, manufacturer, model_number, notes
        CalibrationRecord is created separately for equipment types that require calibration.
        """
        equipment_list = []
        type_map = {et.name: et for et in equipment_types}

        for eq_data in DEMO_EQUIPMENT:
            eq_type = type_map.get(eq_data['type'])

            eq, created = Equipments.objects.update_or_create(
                tenant=self.tenant,
                name=eq_data['name'],
                defaults={
                    'serial_number': eq_data['serial'],
                    'equipment_type': eq_type,
                    'status': EquipmentStatus.IN_SERVICE,  # Enum member from EquipmentStatus
                    'location': eq_data.get('location', ''),
                    'calibration_interval_days': None,  # Inherit from equipment_type
                    '_requires_calibration_override': None,  # Inherit from equipment_type
                    'manufacturer': '',
                    'model_number': '',
                    'notes': '',
                }
            )

            # Only create calibration record if equipment type requires calibration
            # and calibration_days is specified in the config
            calibration_days = eq_data.get('calibration_days')
            if eq_type and eq_type.requires_calibration and calibration_days is not None:
                calibration_due = self.today + timedelta(days=calibration_days)
                calibration_date = self.today - timedelta(days=30)  # Last calibrated 30 days ago
                CalibrationRecord.objects.update_or_create(
                    tenant=self.tenant,
                    equipment=eq,
                    calibration_date=calibration_date,  # Include in lookup to avoid duplicates
                    defaults={
                        'due_date': calibration_due,
                        'result': CalibrationRecord.CalibrationResult.PASS,  # UPPERCASE enum: PASS, FAIL, LIMITED
                        'calibration_type': CalibrationRecord.CalibrationType.SCHEDULED,  # UPPERCASE enum
                        'performed_by': 'External Lab',
                        'external_lab': 'Demo Calibration Services',
                        'certificate_number': f'CAL-{eq_data["serial"]}-2024',
                        'standards_used': 'NIST-traceable reference standards',
                        'as_found_in_tolerance': True,
                        'adjustments_made': False,
                        'notes': '',
                    }
                )
            equipment_list.append(eq)

        return equipment_list

    def _create_process_and_steps(self, part_type):
        """Create process with steps and edges.

        ALL fields on Steps model are explicitly set from config - no reliance on model defaults.
        """
        # Create process (requires part_type FK)
        # Uses DEMO_PROCESS config fields: is_remanufactured, category
        # All enum fields must be UPPERCASE
        process, _ = Processes.objects.update_or_create(
            tenant=self.tenant,
            name=DEMO_PROCESS['name'],
            part_type=part_type,
            defaults={
                'is_remanufactured': DEMO_PROCESS.get('is_remanufactured', False),
                'is_batch_process': False,
                'category': 'MANUFACTURING',  # UPPERCASE enum value
                'status': ProcessStatus.APPROVED,  # Use enum member for status
                'change_description': 'Initial demo process setup',
                'approved_at': timezone.now(),
                'approved_by': None,
            }
        )

        # Build Group lookup for revisit_role (Group FK)
        group_map = {}
        for step_data in DEMO_PROCESS['steps']:
            role_name = step_data.get('revisit_role_name')
            if role_name and role_name not in group_map:
                group, _ = Group.objects.get_or_create(name=role_name)
                group_map[role_name] = group

        # Create steps with ALL fields explicitly set from config
        steps = []
        step_map = {}
        for step_data in DEMO_PROCESS['steps']:
            step_name = step_data['name']
            is_terminal = step_name == 'Complete'
            is_entry = step_data['order'] == 1
            is_rework = step_name == 'Rework'

            # Set step_type based on step purpose
            if is_entry:
                step_type = 'START'
            elif is_terminal:
                step_type = 'TERMINAL'
            elif is_rework:
                step_type = 'REWORK'
            elif step_data.get('requires_qa_signoff', False):
                step_type = 'DECISION'
            else:
                step_type = 'TASK'

            # Resolve revisit_role Group FK from name
            revisit_role_name = step_data.get('revisit_role_name')
            revisit_role = group_map.get(revisit_role_name) if revisit_role_name else None

            # Create step with ALL model fields explicitly set from config
            step, _ = Steps.objects.update_or_create(
                tenant=self.tenant,
                name=step_name,
                part_type=part_type,
                defaults={
                    # Basic fields
                    'description': step_data['description'],
                    'pass_threshold': step_data.get('pass_threshold', 1.0),
                    'expected_duration': step_data.get('expected_duration'),
                    # QA & Sampling
                    'block_on_quarantine': step_data.get('block_on_quarantine', False),
                    'requires_qa_signoff': step_data.get('requires_qa_signoff', False),
                    'sampling_required': step_data.get('sampling_required', False),
                    'min_sampling_rate': step_data.get('min_sampling_rate', 0.0),
                    # First Piece Inspection
                    'requires_first_piece_inspection': step_data.get('requires_first_piece_inspection', False),
                    'fpi_scope': step_data.get('fpi_scope', 'PER_WORKORDER'),
                    # Workflow Control
                    'block_on_measurement_failure': step_data.get('block_on_measurement_failure', False),
                    'block_on_spc_violation': step_data.get('block_on_spc_violation', False),
                    'override_expiry_hours': step_data.get('override_expiry_hours', 24),
                    'undo_window_minutes': step_data.get('undo_window_minutes', 15),
                    'rollback_requires_approval': step_data.get('rollback_requires_approval', True),
                    'requires_batch_completion': step_data.get('requires_batch_completion', False),
                    # Step Type (visual)
                    'step_type': step_type,
                    # Decision behavior
                    'is_decision_point': step_data.get('requires_qa_signoff', False),
                    'decision_type': 'QA_RESULT' if step_data.get('requires_qa_signoff', False) else '',
                    # Terminal step
                    'is_terminal': is_terminal,
                    'terminal_status': 'COMPLETED' if is_terminal else '',
                    # Cycle control
                    'max_visits': step_data.get('max_visits'),
                    'revisit_assignment': step_data.get('revisit_assignment', 'ANY'),
                    'revisit_role': revisit_role,
                }
            )
            steps.append(step)
            step_map[step_name] = step

            # Create ProcessStep link with ALL fields
            ProcessStep.objects.update_or_create(
                process=process,
                step=step,
                defaults={
                    'order': step_data['order'],
                    'is_entry_point': is_entry,
                    'is_exit_point': is_terminal,
                }
            )

        # Create step edges (linear flow with rework loops)
        self._create_step_edges(process, step_map)

        return process, steps

    def _create_step_edges(self, process, step_map):
        """Create edges between steps including rework loops.

        Uses EdgeType enum for edge_type field (DEFAULT, ALTERNATE, ESCALATION).
        """
        # Main linear flow - DEFAULT edges (pass path)
        linear_edges = [
            ('Core Receiving', 'Disassembly', EdgeType.DEFAULT),
            ('Disassembly', 'Component Grading', EdgeType.DEFAULT),
            ('Component Grading', 'Cleaning', EdgeType.DEFAULT),
            ('Cleaning', 'Nozzle Inspection', EdgeType.DEFAULT),
            ('Nozzle Inspection', 'Flow Testing', EdgeType.DEFAULT),
            ('Flow Testing', 'Assembly', EdgeType.DEFAULT),
            ('Assembly', 'Final Test', EdgeType.DEFAULT),
            ('Final Test', 'Packaging', EdgeType.DEFAULT),
            ('Packaging', 'Complete', EdgeType.DEFAULT),
        ]

        # Rework routing - ALTERNATE edges (fail path)
        rework_edges = [
            ('Nozzle Inspection', 'Rework', EdgeType.ALTERNATE),
            ('Flow Testing', 'Rework', EdgeType.ALTERNATE),
            ('Final Test', 'Rework', EdgeType.ALTERNATE),
            ('Rework', 'Nozzle Inspection', EdgeType.DEFAULT),  # Re-enter inspection after rework
        ]

        all_edges = linear_edges + rework_edges

        for from_step_name, to_step_name, edge_type in all_edges:
            from_step = step_map[from_step_name]
            to_step = step_map[to_step_name]

            StepEdge.objects.update_or_create(
                process=process,
                from_step=from_step,
                to_step=to_step,
                edge_type=edge_type,  # Include in lookup to allow multiple edge types between same steps
                defaults={
                    'condition_measurement': None,
                    'condition_operator': '',
                    'condition_value': None,
                }
            )

    def _create_part_types(self):
        """Create part types from DEMO_PART_TYPES config.

        Explicitly sets all fields including ITAR/export control defaults.
        """
        part_types = []
        for pt_data in DEMO_PART_TYPES:
            pt, _ = PartTypes.objects.update_or_create(
                tenant=self.tenant,
                name=pt_data['name'],
                defaults={
                    'ID_prefix': pt_data.get('ID_prefix', ''),
                    'ERP_id': pt_data.get('ERP_id', ''),
                    'itar_controlled': False,
                    'eccn': '',
                    'usml_category': '',
                }
            )
            part_types.append(pt)
        return part_types

    def _link_part_types_to_process(self, part_types, process):
        """
        No-op: PartTypes model does not have a default_process field.
        The relationship is defined on Processes.part_type instead.
        """
        pass

    def _create_measurement_definitions(self, steps):
        """Create measurement definitions linked to steps.

        All type values must be UPPERCASE ('NUMERIC', 'PASS_FAIL').
        """
        step_map = {s.name: s for s in steps}
        definitions = []

        for md_data in DEMO_MEASUREMENTS:
            step = step_map.get(md_data['step'])
            if not step:
                continue

            # Ensure type is UPPERCASE
            measurement_type = md_data.get('type', 'NUMERIC').upper()

            md, _ = MeasurementDefinition.objects.update_or_create(
                tenant=self.tenant,
                label=md_data['label'],
                step=step,
                defaults={
                    'unit': md_data.get('unit', ''),
                    'nominal': md_data.get('nominal'),
                    'lower_tol': md_data.get('lower_tol'),
                    'upper_tol': md_data.get('upper_tol'),
                    'type': measurement_type,  # UPPERCASE: 'NUMERIC' or 'PASS_FAIL'
                    'required': True,
                    'spc_enabled': md_data.get('spc_enabled', False),
                }
            )
            definitions.append(md)

        return definitions
