"""
Manufacturing seed data: Part types, processes, steps, equipment.
"""

import random
from django.utils import timezone

from Tracker.models import (
    PartTypes, Processes, Steps, ProcessStep, StepEdge, EdgeType,
    EquipmentType, Equipments, MeasurementDefinition, ProcessStatus,
)
from .base import BaseSeeder


class ManufacturingSeeder(BaseSeeder):
    """
    Seeds manufacturing infrastructure.

    Creates:
    - Equipment types and equipment instances
    - Part types (injector types)
    - Processes with steps (including branching workflows)
    - Measurement definitions for steps
    - Failure clustering for realistic defect patterns
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.problematic_equipment = set()
        self.equipment_by_type = {}

    def seed(self, employees=None):
        """Run the full manufacturing seeding process."""
        equipment = self.create_equipment()
        self.setup_failure_clustering(equipment)
        part_types = self.create_part_types_and_processes(employees or [])

        # Collect all created processes and equipment types
        processes = list(Processes.objects.filter(tenant=self.tenant))
        equipment_types = list(EquipmentType.objects.filter(tenant=self.tenant))

        return {
            'equipment': equipment,
            'equipment_types': equipment_types,
            'part_types': part_types,
            'processes': processes,
        }

    # =========================================================================
    # Equipment
    # =========================================================================

    def create_equipment(self):
        """Create realistic diesel injector manufacturing equipment."""
        equipment_data = [
            # Testing Equipment
            ("Test Bench", ["TB-001", "TB-002", "TB-003", "TB-004"]),
            ("Flow Test Station", ["FT-001", "FT-002"]),
            ("Pressure Test Rig", ["PT-001", "PT-002"]),

            # Assembly Equipment
            ("Assembly Station", ["AS-001", "AS-002", "AS-003", "AS-004"]),
            ("Disassembly Station", ["DS-001", "DS-002", "DS-003"]),

            # Cleaning Equipment
            ("Ultrasonic Cleaner", ["UC-001", "UC-002"]),
            ("Parts Washer", ["PW-001", "PW-002", "PW-003"]),

            # Measuring Equipment
            ("CMM Machine", ["CMM-001"]),
            ("Surface Roughness Tester", ["SRT-001", "SRT-002"]),
        ]

        equipment = []
        for eq_type_name, equipment_names in equipment_data:
            eq_type, _ = EquipmentType.objects.get_or_create(
                name=eq_type_name,
                defaults={'tenant': self.tenant}
            )
            if not eq_type.tenant:
                eq_type.tenant = self.tenant
                eq_type.save()

            for eq_name in equipment_names:
                eq = Equipments.objects.create(
                    tenant=self.tenant,
                    name=eq_name,
                    equipment_type=eq_type
                )
                equipment.append(eq)

        self.log(f"Created {len(equipment)} pieces of manufacturing equipment")
        return equipment

    def setup_failure_clustering(self, equipment):
        """
        Designate some equipment as 'problematic' with higher failure rates.
        Creates realistic clustering where certain machines cause more issues.
        """
        self.problematic_equipment = set(random.sample(equipment, min(3, len(equipment))))

        # Group equipment by type for step-appropriate selection
        self.equipment_by_type = {}
        for eq in equipment:
            eq_type = eq.equipment_type.name if eq.equipment_type else 'General'
            if eq_type not in self.equipment_by_type:
                self.equipment_by_type[eq_type] = []
            self.equipment_by_type[eq_type].append(eq)

        problematic_names = [eq.name for eq in self.problematic_equipment]
        self.log(f"  Failure clustering: problematic equipment = {', '.join(problematic_names)}")

    def select_equipment_for_step(self, step, all_equipment):
        """Select appropriate equipment based on step type."""
        step_name_lower = step.name.lower()

        # Map step keywords to equipment types
        if any(kw in step_name_lower for kw in ['flow', 'testing', 'performance']):
            candidates = (self.equipment_by_type.get('Test Bench', []) +
                         self.equipment_by_type.get('Flow Test Station', []))
        elif any(kw in step_name_lower for kw in ['pressure', 'hydraulic']):
            candidates = (self.equipment_by_type.get('Pressure Test Rig', []) +
                         self.equipment_by_type.get('Test Bench', []))
        elif any(kw in step_name_lower for kw in ['inspection', 'qc', 'measurement', 'dimensional']):
            candidates = (self.equipment_by_type.get('CMM Machine', []) +
                         self.equipment_by_type.get('Surface Roughness Tester', []))
        elif any(kw in step_name_lower for kw in ['assembly', 'reassembly']):
            candidates = self.equipment_by_type.get('Assembly Station', [])
        elif any(kw in step_name_lower for kw in ['disassembly', 'teardown']):
            candidates = self.equipment_by_type.get('Disassembly Station', [])
        elif any(kw in step_name_lower for kw in ['cleaning', 'clean']):
            candidates = (self.equipment_by_type.get('Ultrasonic Cleaner', []) +
                         self.equipment_by_type.get('Parts Washer', []))
        else:
            candidates = all_equipment

        return random.choice(candidates) if candidates else random.choice(all_equipment)

    def get_failure_rate(self, equipment_piece, step):
        """Get failure rate based on equipment (problematic = higher rate) and step type."""
        if equipment_piece in self.problematic_equipment:
            base_rate = 0.35  # 35% failure rate for problematic equipment
        else:
            base_rate = 0.12  # 12% baseline

        # Detection steps are better at finding issues
        step_name_lower = step.name.lower()
        if any(kw in step_name_lower for kw in ['inspection', 'qc', 'testing', 'validation', 'verification']):
            base_rate *= 1.3  # 30% more likely to catch issues

        return min(0.50, base_rate)  # Cap at 50%

    # =========================================================================
    # Part Types and Processes
    # =========================================================================

    def create_part_types_and_processes(self, employees):
        """Create realistic diesel injector part types with manufacturing processes."""
        part_types = []

        # Common Rail Injector with full branching workflow
        cri_part_type = PartTypes.objects.create(
            tenant=self.tenant,
            name='Common Rail Injector',
            ID_prefix='CRI'
        )
        part_types.append(cri_part_type)
        self._create_cri_processes(cri_part_type, employees)

        # Unit Injector
        ui_part_type = PartTypes.objects.create(
            tenant=self.tenant,
            name='Unit Injector',
            ID_prefix='UI'
        )
        part_types.append(ui_part_type)
        self._create_ui_processes(ui_part_type, employees)

        # HEUI Injector
        heui_part_type = PartTypes.objects.create(
            tenant=self.tenant,
            name='HEUI Injector',
            ID_prefix='HEUI'
        )
        part_types.append(heui_part_type)
        self._create_heui_processes(heui_part_type, employees)

        self.log(f"Created {len(part_types)} part types with workflow-enabled processes")
        return part_types

    def _create_cri_processes(self, part_type, employees):
        """Create Common Rail Injector processes with full branching workflow."""
        # Flagship remanufacturing process with branching
        reman_process = Processes.objects.create(
            tenant=self.tenant,
            name=f'{part_type.name} - Remanufacturing',
            is_remanufactured=True,
            part_type=part_type,
            is_batch_process=False,
            status=ProcessStatus.APPROVED,
            approved_at=timezone.now(),
            approved_by=random.choice(employees) if employees else None,
        )

        # Steps with branching support
        steps_data = [
            # (name, step_type, is_decision, decision_type, is_terminal, terminal_status, max_visits, requires_qa, sampling_req, sampling_rate, expected_duration)
            ('Receive Core', 'start', False, '', False, '', None, False, False, 0, None),
            ('Disassemble', 'task', False, '', False, '', None, False, False, 0, None),
            ('Clean', 'timer', False, '', False, '', None, False, False, 0, '2h'),
            ('Inspect', 'decision', True, 'qa_result', False, '', None, True, True, 100, None),
            ('Reassemble', 'task', False, '', False, '', None, False, False, 0, None),
            ('Final Test', 'decision', True, 'measurement', False, '', None, True, True, 25, None),
            ('Rework', 'rework', False, '', False, '', 3, False, False, 0, None),
            ('Scrap Decision', 'decision', True, 'manual', False, '', None, False, False, 0, None),
            ('Scrap', 'terminal', False, '', True, 'scrapped', None, False, False, 0, None),
            ('Ship', 'terminal', False, '', True, 'shipped', None, False, False, 0, None),
            ('Return to Supplier', 'terminal', False, '', True, 'returned', None, False, False, 0, None),
        ]

        created_steps = {}
        for order, (name, step_type, is_decision, decision_type, is_terminal, terminal_status,
                    max_visits, requires_qa, sampling_req, sampling_rate, expected_duration) in enumerate(steps_data, 1):
            step = Steps.objects.create(
                tenant=self.tenant,
                name=name,
                part_type=part_type,
                description=f"{name} for Common Rail Injector remanufacturing",
                step_type=step_type,
                is_decision_point=is_decision,
                decision_type=decision_type if is_decision else '',
                is_terminal=is_terminal,
                terminal_status=terminal_status if is_terminal else '',
                max_visits=max_visits,
                requires_qa_signoff=requires_qa,
                sampling_required=sampling_req,
                min_sampling_rate=sampling_rate,
                expected_duration=expected_duration,
            )
            created_steps[name] = step
            ProcessStep.objects.create(
                process=reman_process,
                step=step,
                order=order,
                is_entry_point=(order == 1)
            )
            self._create_measurement_definitions(step)

        # Wire up branching connections
        self._create_cri_branching(reman_process, created_steps)

        # Draft process for approval workflow testing
        draft_process = Processes.objects.create(
            tenant=self.tenant,
            name=f'{part_type.name} - New Reman (Draft)',
            is_remanufactured=True,
            part_type=part_type,
            is_batch_process=False,
            status=ProcessStatus.DRAFT,
        )
        draft_steps = ['Intake', 'Teardown', 'Clean & Inspect', 'Rebuild', 'Test', 'Package']
        self._create_linear_steps(draft_process, draft_steps, part_type, "{} - DRAFT process step")

        # New manufacturing process (linear)
        new_mfg_process = Processes.objects.create(
            tenant=self.tenant,
            name=f'{part_type.name} - New Manufacturing',
            is_remanufactured=False,
            part_type=part_type,
            is_batch_process=True,
            status=ProcessStatus.APPROVED,
            approved_at=timezone.now(),
            approved_by=random.choice(employees) if employees else None,
        )
        new_mfg_steps = ['Material Receiving', 'Component Fabrication', 'Precision Machining', 'Assembly',
                        'Initial Testing', 'Calibration', 'Flow Testing', 'Final QC']
        self._create_linear_steps(new_mfg_process, new_mfg_steps, part_type,
                                  "{} for Common Rail Injector new manufacturing")

    def _create_cri_branching(self, process, steps):
        """Create branching edges for CRI remanufacturing process."""
        # Linear flow
        StepEdge.objects.create(process=process, from_step=steps['Receive Core'],
                                to_step=steps['Disassemble'], edge_type=EdgeType.DEFAULT)
        StepEdge.objects.create(process=process, from_step=steps['Disassemble'],
                                to_step=steps['Clean'], edge_type=EdgeType.DEFAULT)
        StepEdge.objects.create(process=process, from_step=steps['Clean'],
                                to_step=steps['Inspect'], edge_type=EdgeType.DEFAULT)

        # Inspect: Pass → Reassemble, Fail → Rework
        StepEdge.objects.create(process=process, from_step=steps['Inspect'],
                                to_step=steps['Reassemble'], edge_type=EdgeType.DEFAULT)
        StepEdge.objects.create(process=process, from_step=steps['Inspect'],
                                to_step=steps['Rework'], edge_type=EdgeType.ALTERNATE)

        # Reassemble → Final Test
        StepEdge.objects.create(process=process, from_step=steps['Reassemble'],
                                to_step=steps['Final Test'], edge_type=EdgeType.DEFAULT)

        # Final Test: Pass → Ship, Fail → Rework
        StepEdge.objects.create(process=process, from_step=steps['Final Test'],
                                to_step=steps['Ship'], edge_type=EdgeType.DEFAULT)
        StepEdge.objects.create(process=process, from_step=steps['Final Test'],
                                to_step=steps['Rework'], edge_type=EdgeType.ALTERNATE)

        # Rework → back to Inspect, escalates to Scrap Decision
        StepEdge.objects.create(process=process, from_step=steps['Rework'],
                                to_step=steps['Inspect'], edge_type=EdgeType.DEFAULT)
        StepEdge.objects.create(process=process, from_step=steps['Rework'],
                                to_step=steps['Scrap Decision'], edge_type=EdgeType.ESCALATION)

        # Scrap Decision: Default → Scrap, Alternate → Return to Supplier
        StepEdge.objects.create(process=process, from_step=steps['Scrap Decision'],
                                to_step=steps['Scrap'], edge_type=EdgeType.DEFAULT)
        StepEdge.objects.create(process=process, from_step=steps['Scrap Decision'],
                                to_step=steps['Return to Supplier'], edge_type=EdgeType.ALTERNATE)

    def _create_ui_processes(self, part_type, employees):
        """Create Unit Injector processes."""
        for proc_suffix, is_reman, steps_list in [
            ('Remanufacturing', True,
             ['Intake Inspection', 'Disassembly', 'Ultrasonic Cleaning', 'Pressure Testing',
              'Nozzle Replacement', 'Reassembly', 'Electronic Testing', 'Final Validation']),
            ('New Manufacturing', False,
             ['Raw Material Prep', 'Component Manufacturing', 'Quality Inspection', 'Assembly',
              'Electronic Testing', 'Performance Testing', 'Final QC']),
        ]:
            process = Processes.objects.create(
                tenant=self.tenant,
                name=f'{part_type.name} - {proc_suffix}',
                is_remanufactured=is_reman,
                part_type=part_type,
                is_batch_process=random.random() < 0.3,
                status=ProcessStatus.APPROVED,
                approved_at=timezone.now(),
                approved_by=random.choice(employees) if employees else None,
            )
            self._create_linear_steps(process, steps_list, part_type, "{} for " + part_type.name)

    def _create_heui_processes(self, part_type, employees):
        """Create HEUI Injector processes."""
        for proc_suffix, is_reman, steps_list in [
            ('Remanufacturing', True,
             ['Visual Inspection', 'Teardown', 'Component Cleaning', 'Hydraulic Testing',
              'Electrical Testing', 'Rebuild', 'Performance Testing', 'Quality Verification']),
            ('New Manufacturing', False,
             ['Material Sourcing', 'Component Fabrication', 'Hydraulic Assembly', 'Electrical Assembly',
              'System Testing', 'Final QC']),
        ]:
            process = Processes.objects.create(
                tenant=self.tenant,
                name=f'{part_type.name} - {proc_suffix}',
                is_remanufactured=is_reman,
                part_type=part_type,
                is_batch_process=random.random() < 0.3,
                status=ProcessStatus.APPROVED,
                approved_at=timezone.now(),
                approved_by=random.choice(employees) if employees else None,
            )
            self._create_linear_steps(process, steps_list, part_type, "{} for " + part_type.name)

    def _create_linear_steps(self, process, step_names, part_type, description_template="{}"):
        """Create a linear process with ProcessStep and StepEdge records."""
        steps = []
        prev_step = None
        for order, step_name in enumerate(step_names, 1):
            is_last = order == len(step_names)
            step = Steps.objects.create(
                tenant=self.tenant,
                name=step_name,
                part_type=part_type,
                description=description_template.format(step_name),
                step_type='terminal' if is_last else ('start' if order == 1 else 'task'),
                is_terminal=is_last,
                terminal_status='completed' if is_last else '',
                min_sampling_rate=0,
            )
            ProcessStep.objects.create(
                process=process,
                step=step,
                order=order,
                is_entry_point=(order == 1)
            )
            if prev_step:
                StepEdge.objects.create(
                    process=process,
                    from_step=prev_step,
                    to_step=step,
                    edge_type=EdgeType.DEFAULT
                )
            steps.append(step)
            prev_step = step
            self._create_measurement_definitions(step)
        return steps

    def _create_measurement_definitions(self, step):
        """Create realistic measurement definitions for a step."""
        measurements = []

        if 'Flow' in step.name:
            measurements.extend([
                ('Flow Rate', 'NUMERIC', 'mL/min', 850.0, 25.0, 25.0),
                ('Injection Pattern', 'PASS_FAIL', '', None, None, None),
            ])
        elif 'Pressure' in step.name:
            measurements.extend([
                ('Opening Pressure', 'NUMERIC', 'bar', 280.0, 10.0, 10.0),
                ('Closing Pressure', 'NUMERIC', 'bar', 250.0, 15.0, 15.0),
            ])
        elif any(word in step.name for word in ['Inspection', 'QC', 'Testing', 'Validation']):
            measurements.extend([
                ('Overall Length', 'NUMERIC', 'mm', 156.5, 0.1, 0.1),
                ('Surface Finish', 'NUMERIC', 'Ra µm', 0.8, 0.2, 0.2),
            ])
        elif any(word in step.name for word in ['Assembly', 'Disassembly', 'Reassembly']):
            measurements.extend([
                ('Assembly Complete', 'PASS_FAIL', '', None, None, None),
                ('Torque Spec', 'NUMERIC', 'Nm', 45.0, 5.0, 5.0),
            ])
        elif any(word in step.name for word in ['Cleaning', 'Clean']):
            measurements.extend([
                ('Cleanliness Check', 'PASS_FAIL', '', None, None, None),
                ('Contamination Level', 'NUMERIC', 'mg/L', 5.0, 2.0, 2.0),
            ])
        elif any(word in step.name for word in ['Machining', 'Fabrication']):
            measurements.extend([
                ('Dimensional Check', 'NUMERIC', 'mm', 12.5, 0.05, 0.05),
                ('Surface Quality', 'PASS_FAIL', '', None, None, None),
            ])
        elif any(word in step.name for word in ['Calibration', 'Adjustment']):
            measurements.extend([
                ('Calibration Status', 'PASS_FAIL', '', None, None, None),
                ('Tolerance Check', 'NUMERIC', '%', 0.0, 1.0, 1.0),
            ])
        else:
            measurements.extend([
                ('Process Complete', 'PASS_FAIL', '', None, None, None),
                ('Cycle Time', 'NUMERIC', 'sec', 120.0, 15.0, 15.0),
            ])

        for label, type_val, unit, nominal, upper_tol, lower_tol in measurements:
            MeasurementDefinition.objects.create(
                tenant=self.tenant,
                step=step,
                label=label,
                type=type_val,
                unit=unit,
                nominal=nominal,
                upper_tol=upper_tol,
                lower_tol=lower_tol
            )
