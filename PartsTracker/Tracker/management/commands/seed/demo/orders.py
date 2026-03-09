"""
Demo orders seeder with preset orders matching DEMO_DATA_SYSTEM.md.

Creates:
- ORD-2024-0042: Midwest Fleet (in progress, 24 parts)
- ORD-2024-0038: Great Lakes Diesel (completed, 12 parts, triggered CAPA)
- ORD-2024-0048: Northern Trucking (pending, 8 parts)
"""

from datetime import timedelta
from django.utils import timezone

from Tracker.models import (
    Orders, Parts, WorkOrder, Steps,
    OrdersStatus, WorkOrderStatus, WorkOrderPriority, PartsStatus,
    StepExecution, StepTransitionLog, EquipmentUsage,
    Equipments, ProcessStep,
    FPIRecord, FPIStatus, FPIResult, PartTypes,
)

from ..base import BaseSeeder


# Demo orders config matching DEMO_DATA_SYSTEM.md
# Note: Orders model uses order_number, name, company (FK), customer (FK to User),
# order_status, estimated_completion. It does NOT have: po_number, received_date,
# due_date, quantity, completed_date.
DEMO_ORDERS = [
    {
        'order_number': 'ORD-2024-0042',
        'name': 'Midwest Fleet Order - 24 Injectors',
        'company_name': 'Midwest Fleet Services',
        'days_ago': 10,
        'estimated_completion_days': 5,
        'status': OrdersStatus.IN_PROGRESS,
        'work_order': {
            'ERP_id': 'WO-2024-0042-A',
            'priority': WorkOrderPriority.HIGH,
            'workorder_status': WorkOrderStatus.IN_PROGRESS,
            'created_days_ago': 9,
            'expected_completion_days': 4,
            'quantity': 24,
        },
        'parts': [
            # 16 complete
            {'serial': 'INJ-0042-001', 'step': 'Complete', 'part_status': PartsStatus.COMPLETED},
            {'serial': 'INJ-0042-002', 'step': 'Complete', 'part_status': PartsStatus.COMPLETED},
            {'serial': 'INJ-0042-003', 'step': 'Complete', 'part_status': PartsStatus.COMPLETED},
            {'serial': 'INJ-0042-004', 'step': 'Complete', 'part_status': PartsStatus.COMPLETED},
            {'serial': 'INJ-0042-005', 'step': 'Complete', 'part_status': PartsStatus.COMPLETED},
            {'serial': 'INJ-0042-006', 'step': 'Complete', 'part_status': PartsStatus.COMPLETED},
            {'serial': 'INJ-0042-007', 'step': 'Complete', 'part_status': PartsStatus.COMPLETED},
            {'serial': 'INJ-0042-008', 'step': 'Complete', 'part_status': PartsStatus.COMPLETED},
            {'serial': 'INJ-0042-009', 'step': 'Complete', 'part_status': PartsStatus.COMPLETED},
            {'serial': 'INJ-0042-010', 'step': 'Complete', 'part_status': PartsStatus.COMPLETED},
            {'serial': 'INJ-0042-011', 'step': 'Complete', 'part_status': PartsStatus.COMPLETED},
            {'serial': 'INJ-0042-012', 'step': 'Complete', 'part_status': PartsStatus.COMPLETED},
            {'serial': 'INJ-0042-013', 'step': 'Complete', 'part_status': PartsStatus.COMPLETED},
            {'serial': 'INJ-0042-014', 'step': 'Complete', 'part_status': PartsStatus.COMPLETED},
            {'serial': 'INJ-0042-015', 'step': 'Complete', 'part_status': PartsStatus.COMPLETED},
            {'serial': 'INJ-0042-016', 'step': 'Complete', 'part_status': PartsStatus.COMPLETED},
            # 2 quarantined
            {'serial': 'INJ-0042-017', 'step': 'Flow Testing', 'part_status': PartsStatus.QUARANTINED},
            # 1 in rework
            {'serial': 'INJ-0042-019', 'step': 'Rework', 'part_status': PartsStatus.REWORK_IN_PROGRESS},
            # In progress at various steps
            {'serial': 'INJ-0042-018', 'step': 'Final Test', 'part_status': PartsStatus.IN_PROGRESS},
            {'serial': 'INJ-0042-020', 'step': 'Assembly', 'part_status': PartsStatus.IN_PROGRESS},
            {'serial': 'INJ-0042-021', 'step': 'Flow Testing', 'part_status': PartsStatus.IN_PROGRESS},
            {'serial': 'INJ-0042-022', 'step': 'Cleaning', 'part_status': PartsStatus.IN_PROGRESS},
            # 1 scrapped
            {'serial': 'INJ-0042-023', 'step': None, 'part_status': PartsStatus.SCRAPPED},
            # 1 early stage
            {'serial': 'INJ-0042-024', 'step': 'Component Grading', 'part_status': PartsStatus.IN_PROGRESS},
        ],
    },
    {
        'order_number': 'ORD-2024-0038',
        'name': 'Great Lakes Diesel Order - 12 Injectors',
        'company_name': 'Great Lakes Diesel Supply',
        'days_ago': 25,
        'estimated_completion_days': -5,  # already past due (shipped)
        'status': OrdersStatus.COMPLETED,
        'work_order': {
            'ERP_id': 'WO-2024-0038-A',
            'priority': WorkOrderPriority.NORMAL,
            'workorder_status': WorkOrderStatus.COMPLETED,
            'created_days_ago': 24,
            'expected_completion_days': -6,
            'quantity': 12,
        },
        'parts': [
            # All shipped - some required rework (these triggered CAPA)
            {'serial': 'INJ-0038-001', 'step': 'Complete', 'part_status': PartsStatus.COMPLETED, 'reworked': False},
            {'serial': 'INJ-0038-002', 'step': 'Complete', 'part_status': PartsStatus.COMPLETED, 'reworked': False},
            {'serial': 'INJ-0038-003', 'step': 'Complete', 'part_status': PartsStatus.COMPLETED, 'reworked': True},
            {'serial': 'INJ-0038-004', 'step': 'Complete', 'part_status': PartsStatus.COMPLETED, 'reworked': False},
            {'serial': 'INJ-0038-005', 'step': 'Complete', 'part_status': PartsStatus.COMPLETED, 'reworked': False},
            {'serial': 'INJ-0038-006', 'step': 'Complete', 'part_status': PartsStatus.COMPLETED, 'reworked': False},
            {'serial': 'INJ-0038-007', 'step': 'Complete', 'part_status': PartsStatus.COMPLETED, 'reworked': True},
            {'serial': 'INJ-0038-008', 'step': 'Complete', 'part_status': PartsStatus.COMPLETED, 'reworked': True},
            {'serial': 'INJ-0038-009', 'step': 'Complete', 'part_status': PartsStatus.COMPLETED, 'reworked': False},
            {'serial': 'INJ-0038-010', 'step': 'Complete', 'part_status': PartsStatus.COMPLETED, 'reworked': True},
            {'serial': 'INJ-0038-011', 'step': 'Complete', 'part_status': PartsStatus.COMPLETED, 'reworked': True},
            {'serial': 'INJ-0038-012', 'step': 'Complete', 'part_status': PartsStatus.COMPLETED, 'reworked': False},
        ],
    },
    {
        'order_number': 'ORD-2024-0048',
        'name': 'Northern Trucking Order - 8 Injectors',
        'company_name': 'Northern Trucking Co',
        'days_ago': 1,
        'estimated_completion_days': 10,
        'status': OrdersStatus.PENDING,
        'work_order': {
            'ERP_id': 'WO-2024-0048-A',
            'priority': WorkOrderPriority.NORMAL,
            'workorder_status': WorkOrderStatus.PENDING,
            'created_days_ago': 1,
            'expected_completion_days': 10,
            'quantity': 8,
        },
        # Parts not yet created for pending order
        'parts': [],
    },
]


class DemoOrdersSeeder(BaseSeeder):
    """
    Creates preset orders with parts at various workflow stages.

    All data is deterministic - same result every time.
    """

    def __init__(self, stdout, style, tenant, scale='small'):
        super().__init__(stdout, style, scale=scale)
        self.tenant = tenant
        self.today = timezone.now()

    def seed(self, companies, users, part_types, process, equipment=None):
        """
        Create all demo orders.

        Args:
            companies: list of Companies objects
            users: dict with user lists
            part_types: list of PartTypes
            process: the Processes object to use
            equipment: list of Equipments objects (optional)

        Returns:
            dict with created orders, work_orders, parts
        """
        self.log("Creating demo orders...")

        result = {
            'orders': [],
            'work_orders': [],
            'parts': [],
        }

        # Get company lookup by name
        company_map = {c.name: c for c in companies} if companies else {}

        # Get part type (default to first one)
        part_type = part_types[0] if part_types else None

        # Get step lookup
        steps = Steps.objects.filter(tenant=self.tenant)
        step_map = {s.name: s for s in steps}

        for order_data in DEMO_ORDERS:
            # Get company by name
            company = company_map.get(order_data['company_name'])

            # Create order
            order = self._create_order(order_data, company)
            result['orders'].append(order)

            # Create work order
            wo_data = order_data.get('work_order')
            if wo_data:
                work_order = self._create_work_order(wo_data, order, process)
                result['work_orders'].append(work_order)

                # Create parts
                parts_list = order_data.get('parts', [])
                for part_index, part_data in enumerate(parts_list):
                    part = self._create_part(part_data, order, work_order, part_type, step_map, part_index)
                    if part:
                        result['parts'].append(part)

        self.log(f"  Created {len(result['orders'])} orders")
        self.log(f"  Created {len(result['work_orders'])} work orders")
        self.log(f"  Created {len(result['parts'])} parts")

        return result

    def _create_order(self, order_data, company):
        """Create a single order.

        Orders model fields:
        - order_number: CharField (auto-generated if blank)
        - name: CharField
        - customer: FK to User (optional)
        - company: FK to Companies (optional)
        - order_status: CharField with OrdersStatus choices
        - estimated_completion: DateField (optional)
        - customer_note: TextField (optional)
        """
        estimated_completion = (self.today + timedelta(days=order_data['estimated_completion_days'])).date()

        defaults = {
            'name': order_data['name'],
            'company': company,
            'customer': None,  # Explicit: no customer user assigned
            'customer_note': None,  # Explicit: no notes
            'order_status': order_data['status'],
            'estimated_completion': estimated_completion,
            'original_completion_date': None,  # Explicit: not tracking original date
            # HubSpot fields - explicit nulls
            'current_hubspot_gate': None,
            'hubspot_deal_id': None,
            'last_synced_hubspot_stage': None,
            'hubspot_last_synced_at': None,
        }

        order, _ = Orders.objects.update_or_create(
            tenant=self.tenant,
            order_number=order_data['order_number'],
            defaults=defaults
        )

        return order

    def _create_work_order(self, wo_data, order, process):
        """Create a work order.

        WorkOrder model fields:
        - ERP_id: CharField (unique identifier)
        - related_order: FK to Orders
        - process: FK to Processes
        - workorder_status: CharField with WorkOrderStatus choices
        - priority: IntegerField with WorkOrderPriority choices
        - expected_completion: DateField (optional)
        - quantity: IntegerField
        - notes: TextField (optional)
        """
        expected_date = (self.today + timedelta(days=wo_data['expected_completion_days'])).date()

        defaults = {
            'related_order': order,
            'process': process,
            'workorder_status': wo_data['workorder_status'],
            'priority': wo_data['priority'],
            'expected_completion': expected_date,
            'quantity': wo_data.get('quantity', 1),
            'notes': '',  # Explicit: no notes
            'expected_duration': None,  # Explicit: no estimated duration
            'true_completion': None,  # Explicit: not yet completed
            'true_duration': None,  # Explicit: no actual duration
        }

        work_order, _ = WorkOrder.objects.update_or_create(
            tenant=self.tenant,
            ERP_id=wo_data['ERP_id'],
            defaults=defaults
        )

        return work_order

    def _create_part(self, part_data, order, work_order, part_type, step_map, part_index=0):
        """Create a part at specified step.

        Parts model fields:
        - ERP_id: CharField (serial number)
        - part_type: FK to PartTypes
        - order: FK to Orders
        - work_order: FK to WorkOrder
        - step: FK to Steps (current step)
        - part_status: CharField with PartsStatus choices
        """
        current_step = step_map.get(part_data.get('step')) if part_data.get('step') else None
        part_status = part_data['part_status']

        # Determine sampling requirement (every 5th part at QA steps)
        qa_steps = {'Flow Testing', 'Nozzle Inspection', 'Final Test'}
        step_name = part_data.get('step')
        requires_sampling = (
            step_name in qa_steps and
            part_index % 5 == 0 and
            part_status in [PartsStatus.IN_PROGRESS, PartsStatus.AWAITING_QA]
        )

        # Parts requiring sampling at QA steps should be AWAITING_QA
        if requires_sampling and part_status == PartsStatus.IN_PROGRESS:
            part_status = PartsStatus.AWAITING_QA

        # First part is FPI candidate
        is_fpi_candidate = (part_index == 0)

        # Track rework count from config
        rework_count = 1 if part_data.get('reworked') else 0

        part, _ = Parts.objects.update_or_create(
            tenant=self.tenant,
            ERP_id=part_data['serial'],
            defaults={
                'part_type': part_type,
                'order': order,
                'work_order': work_order,
                'step': current_step,
                'part_status': part_status,
                # Sampling fields
                'requires_sampling': requires_sampling,
                'sampling_rule': None,
                'sampling_ruleset': None,
                'sampling_context': {'trigger_reason': 'PERIODIC_SAMPLING'} if requires_sampling else {},
                # Rework tracking
                'total_rework_count': rework_count,
                # Export control fields
                'itar_controlled': False,
                'eccn': '',
                'export_license_required': False,
                'country_of_origin': '',
                # FPI fields
                'is_fpi_candidate': is_fpi_candidate,
                'fpi_override_reason': '',
            }
        )

        return part

    def seed_workflow_execution(self, process, users, equipment=None):
        """
        Create workflow execution data for existing parts.

        Creates:
        - StepExecution records showing part progression through workflow
        - StepTransitionLog entries showing part transitions
        - EquipmentUsage records linking equipment to step executions

        Args:
            process: the Processes object
            users: dict with user lists (employees, managers, etc)
            equipment: list of Equipments objects (optional)

        Returns:
            dict with counts of created records
        """
        self.log("Creating workflow execution data...")

        result = {
            'step_executions': 0,
            'step_transitions': 0,
            'equipment_usage': 0,
        }

        # Get all parts from demo orders
        parts = Parts.objects.filter(
            tenant=self.tenant,
            ERP_id__startswith='INJ-'
        )

        # Get process steps in order
        process_steps = ProcessStep.objects.filter(
            process=process
        ).select_related('step').order_by('order')

        ordered_steps = [ps.step for ps in process_steps]
        if not ordered_steps:
            self.log("  No process steps found", warning=True)
            return result

        # Get equipment by name for specific steps
        equipment_map = {}
        if equipment:
            equipment_map = {eq.name: eq for eq in equipment}

        # Map steps to equipment
        step_equipment_map = {
            'Flow Testing': ['Flow Test Stand #1', 'Flow Test Stand #2'],
            'Assembly': ['Torque Wrench TW-25', 'Torque Wrench TW-26'],
            'Cleaning': ['Ultrasonic Cleaner UC-1'],
            'Final Test': ['Final Test Bench FTB-1'],
        }

        # Get operators
        operators = users.get('employees', [])
        if not operators:
            operators = [None]

        for part in parts:
            # Determine which steps the part has completed
            current_step = part.step

            # Skip scrapped/cancelled parts with no step
            if not current_step and part.part_status in [PartsStatus.SCRAPPED, PartsStatus.CANCELLED]:
                continue

            # Find current step position
            current_step_idx = None
            for idx, step in enumerate(ordered_steps):
                if step == current_step:
                    current_step_idx = idx
                    break

            # If part is complete, it went through all steps
            if part.part_status == PartsStatus.COMPLETED:
                # Set to last step (Complete)
                current_step_idx = len(ordered_steps) - 1

            if current_step_idx is None:
                continue

            # Create execution history for all completed steps
            part_created_at = part.created_at or (self.today - timedelta(days=20))
            current_time = part_created_at

            # Check if part was reworked (from DEMO_ORDERS data)
            part_reworked = False
            for order_data in DEMO_ORDERS:
                for part_data in order_data.get('parts', []):
                    if part_data['serial'] == part.ERP_id and part_data.get('reworked'):
                        part_reworked = True
                        break

            # Create executions for completed steps
            for idx in range(current_step_idx + 1):
                step = ordered_steps[idx]

                # Determine if this is a rework visit
                visit_number = 1
                if part_reworked and step.name == 'Rework':
                    visit_number = 1
                elif part_reworked and step.name in ['Flow Testing', 'Assembly']:
                    # These steps were visited twice due to rework
                    # Create first visit
                    self._create_step_execution_record(
                        part, step, 1, current_time, operators, step_equipment_map,
                        equipment_map, completed=(idx < current_step_idx), result=result
                    )
                    # Advance time and create second visit
                    current_time = current_time + timedelta(hours=2, minutes=30)
                    visit_number = 2

                # Create the execution record
                current_time = self._create_step_execution_record(
                    part, step, visit_number, current_time, operators, step_equipment_map,
                    equipment_map, completed=(idx < current_step_idx), result=result
                )

                # Add some time between steps (1-3 hours)
                current_time = current_time + timedelta(hours=1, minutes=30)

        self.log(f"  Created {result['step_executions']} step executions")
        self.log(f"  Created {result['step_transitions']} step transitions")
        self.log(f"  Created {result['equipment_usage']} equipment usage records")

        return result

    def _create_step_execution_record(self, part, step, visit_number, entry_time,
                                     operators, step_equipment_map, equipment_map,
                                     completed=True, result=None):
        """
        Create StepExecution, StepTransitionLog, and EquipmentUsage records.

        Args:
            part: Parts object
            step: Steps object
            visit_number: int (1 for first visit, 2+ for rework)
            entry_time: datetime when part entered step
            operators: list of User objects
            step_equipment_map: dict mapping step name to equipment names
            equipment_map: dict mapping equipment name to Equipments objects
            completed: bool (True if step is completed, False if in progress)
            result: dict to track counts

        Returns:
            datetime for next step entry
        """
        if result is None:
            result = {'step_executions': 0, 'step_transitions': 0, 'equipment_usage': 0}

        # Pick an operator (deterministic based on part serial and step)
        operator_idx = (hash(f"{part.ERP_id}-{step.name}-{visit_number}") % len(operators))
        operator = operators[operator_idx]

        # Calculate timing
        step_duration = timedelta(hours=0.5, minutes=45)  # ~45 min per step
        started_at = entry_time + timedelta(minutes=5)
        exited_at = started_at + step_duration if completed else None

        # Determine next step for completed executions
        next_step = None
        if completed and step.name != 'Complete':
            # Look up next step in process (simplified - assumes linear flow)
            process_steps = ProcessStep.objects.filter(
                process=part.work_order.process
            ).select_related('step').order_by('order')

            steps_list = [ps.step for ps in process_steps]
            try:
                current_idx = steps_list.index(step)
                if current_idx + 1 < len(steps_list):
                    next_step = steps_list[current_idx + 1]
            except (ValueError, IndexError):
                pass

        # Create or update StepExecution
        # Note: StepExecution doesn't have unique_together, so we check for existing first
        execution = StepExecution.objects.filter(
            tenant=self.tenant,
            part=part,
            step=step,
            visit_number=visit_number
        ).first()

        if execution:
            # Update existing
            StepExecution.objects.filter(pk=execution.pk).update(
                entered_at=entry_time,
                started_at=started_at,
                exited_at=exited_at,
                assigned_to=operator,
                completed_by=operator if completed else None,
                next_step=next_step,
                status='COMPLETED' if completed else 'IN_PROGRESS',
                created_at=entry_time,
                updated_at=exited_at or entry_time
            )
            created = False
        else:
            # Create new
            execution = StepExecution.objects.create(
                tenant=self.tenant,
                part=part,
                step=step,
                visit_number=visit_number,
                entered_at=entry_time,
                started_at=started_at,
                exited_at=exited_at,
                assigned_to=operator,
                completed_by=operator if completed else None,
                next_step=next_step,
                status='COMPLETED' if completed else 'IN_PROGRESS',
            )
            result['step_executions'] += 1
            created = True

            # Backdate the execution
            StepExecution.objects.filter(pk=execution.pk).update(
                created_at=entry_time,
                updated_at=exited_at or entry_time
            )

        # Create StepTransitionLog for when part entered this step
        # Check if transition already exists (StepTransitionLog doesn't enforce uniqueness)
        transition_exists = StepTransitionLog.objects.filter(
            tenant=self.tenant,
            part=part,
            step=step,
            timestamp=entry_time
        ).exists()

        if not transition_exists:
            StepTransitionLog.objects.create(
                tenant=self.tenant,
                part=part,
                step=step,
                timestamp=entry_time,
                operator=operator,
            )
            result['step_transitions'] += 1

        # Create EquipmentUsage if this step uses equipment
        equipment_names = step_equipment_map.get(step.name, [])
        for eq_name in equipment_names:
            equipment_obj = equipment_map.get(eq_name)
            if equipment_obj:
                # Pick equipment deterministically
                if len(equipment_names) > 1:
                    # Choose based on part serial
                    eq_idx = hash(f"{part.ERP_id}-{step.name}") % len(equipment_names)
                    eq_name = equipment_names[eq_idx]
                    equipment_obj = equipment_map.get(eq_name)

                if equipment_obj:
                    # Check if usage already exists
                    usage_exists = EquipmentUsage.objects.filter(
                        tenant=self.tenant,
                        equipment=equipment_obj,
                        step=step,
                        part=part,
                        used_at=started_at
                    ).exists()

                    if not usage_exists:
                        EquipmentUsage.objects.create(
                            tenant=self.tenant,
                            equipment=equipment_obj,
                            step=step,
                            part=part,
                            operator=operator,
                            used_at=started_at,
                            notes=f"Used for {step.name} operation",
                        )
                        result['equipment_usage'] += 1

                # Only use one equipment per step
                break

        # Return next entry time
        return exited_at if exited_at else started_at

    def seed_fpi_records(self, work_orders, part_types, users, equipment):
        """
        Create First Piece Inspection records for demo work orders.

        FPI verifies setup correctness before full production begins.
        Creates deterministic FPI records for key inspection steps.
        """
        self.log("Creating demo FPI records...")

        fpi_count = 0
        qa_staff = users.get('qa_staff', users.get('employees', []))

        # Demo FPI configurations - deterministic data
        demo_fpi_configs = {
            'WO-2024-0042-A': [
                {'step': 'Nozzle Inspection', 'status': FPIStatus.PASSED, 'result': FPIResult.PASS},
                {'step': 'Flow Testing', 'status': FPIStatus.PASSED, 'result': FPIResult.PASS},
                {'step': 'Final Test', 'status': FPIStatus.PASSED, 'result': FPIResult.PASS},
            ],
            'WO-2024-0038-A': [
                {'step': 'Nozzle Inspection', 'status': FPIStatus.PASSED, 'result': FPIResult.PASS},
                {'step': 'Flow Testing', 'status': FPIStatus.FAILED, 'result': FPIResult.FAIL},  # Failed - led to CAPA
                {'step': 'Final Test', 'status': FPIStatus.PASSED, 'result': FPIResult.PASS},
            ],
            'WO-2024-0048-A': [
                {'step': 'Nozzle Inspection', 'status': FPIStatus.PENDING, 'result': ''},  # Pending - new order
            ],
        }

        equipment_map = {e.name: e for e in equipment} if equipment else {}
        steps = {s.name: s for s in Steps.objects.filter(tenant=self.tenant)}

        # Get part type for FPI records
        part_type = part_types[0] if part_types else None

        for work_order in work_orders:
            fpi_config = demo_fpi_configs.get(work_order.ERP_id, [])
            if not fpi_config:
                continue

            # Get first part as designated FPI part
            first_part = work_order.parts.order_by('ERP_id').first()

            for fpi_data in fpi_config:
                step = steps.get(fpi_data['step'])
                if not step:
                    continue

                # Determine inspector based on status
                inspector = None
                inspected_at = None
                if fpi_data['status'] in [FPIStatus.PASSED, FPIStatus.FAILED]:
                    inspector = qa_staff[0] if qa_staff else None
                    inspected_at = self.today - timedelta(days=1)

                # Select equipment based on step
                step_equipment = None
                if 'Flow' in fpi_data['step']:
                    step_equipment = equipment_map.get('Flow Test Stand #1')
                elif 'Test' in fpi_data['step']:
                    step_equipment = equipment_map.get('Test Bench #1')

                fpi, created = FPIRecord.objects.update_or_create(
                    tenant=self.tenant,
                    work_order=work_order,
                    step=step,
                    part_type=part_type,
                    defaults={
                        'designated_part': first_part,
                        'equipment': step_equipment,
                        'shift_date': (self.today - timedelta(days=2)).date(),
                        'status': fpi_data['status'],
                        'result': fpi_data['result'],
                        'inspected_by': inspector,
                        'inspected_at': inspected_at,
                    }
                )

                if created:
                    fpi_count += 1

        self.log(f"  Created {fpi_count} FPI records")
