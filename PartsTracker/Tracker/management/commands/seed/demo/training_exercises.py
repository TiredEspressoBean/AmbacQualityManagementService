"""
Training exercises data seeder.

Creates deterministic TRAIN-* objects referenced in training guide exercises.
These are separate from the main demo narrative data (ORD-2024-*, etc.)
and are specifically designed for hands-on training exercises.

See docs/training/training-data-setup.md for the complete exercise data matrix.
"""

from datetime import timedelta
from django.utils import timezone

from Tracker.models import (
    Orders, OrdersStatus, WorkOrder, WorkOrderStatus, Parts, PartsStatus,
    ProcessStep, QualityReports, QuarantineDisposition, CAPA, CapaStatus,
    CapaType, CapaSeverity, CapaTasks, CapaTaskType, CapaTaskStatus,
)

from ..base import BaseSeeder


# Training orders configuration
TRAINING_ORDERS = [
    {
        'name': 'TRAIN-001',
        'description': 'Basic operator training order',
        'status': OrdersStatus.IN_PROGRESS,
        'parts_count': 10,
        'parts_prefix': 'TRAIN-001',
        'customer_key': 'Midwest Fleet Services',
        'distribute_parts': True,  # Distribute across steps
    },
    {
        'name': 'TRAIN-PM-001',
        'description': 'Production manager exercise order',
        'status': OrdersStatus.PENDING,
        'parts_count': 5,
        'parts_prefix': 'TRAIN-PM-001',
        'customer_key': 'Northern Trucking Co',
        'distribute_parts': False,  # All at start step
    },
    {
        'name': 'TRAIN-BOTTLE',
        'description': 'Bottleneck scenario - parts stuck at inspection step',
        'status': OrdersStatus.IN_PROGRESS,
        'parts_count': 8,
        'parts_prefix': 'TRAIN-BOTTLE',
        'customer_key': 'Midwest Fleet Services',
        'distribute_parts': 'bottleneck',  # Most parts at middle step
    },
    {
        'name': 'TRAIN-HOLD',
        'description': 'Quality hold scenario order',
        'status': OrdersStatus.ON_HOLD,
        'parts_count': 6,
        'parts_prefix': 'TRAIN-HOLD',
        'customer_key': 'Great Lakes Diesel',
        'distribute_parts': False,
    },
    {
        'name': 'TRAIN-FPI-001',
        'description': 'FPI training exercise - first piece inspection',
        'status': OrdersStatus.IN_PROGRESS,
        'parts_count': 15,
        'parts_prefix': 'TRAIN-FPI-001',
        'customer_key': 'Midwest Fleet Services',
        'distribute_parts': False,
        'step_name': 'Final Test',  # Parts at inspection step for FPI training
        'work_order_id': 'TRAIN-FPI-001',
        'requires_sampling_count': 1,  # First part requires QA (FPI scenario)
    },
]

# Training quality reports
TRAINING_QUALITY_REPORTS = [
    {
        'number': 'QR-TRAIN-001',
        'description': 'Surface scratch on housing - training exercise. Surface defect found during visual inspection.',
        'status': 'FAIL',
        'part_key': 'TRAIN-101-003',
        'sampling_method': 'manual',
        'is_first_piece': False,
    },
    {
        'number': 'QR-TRAIN-002',
        'description': 'Flow test out of spec - training exercise. Flow measurement 15% below specification.',
        'status': 'FAIL',
        'part_key': 'TRAIN-101-005',
        'sampling_method': 'manual',
        'is_first_piece': False,
    },
]

# Training dispositions
TRAINING_DISPOSITIONS = [
    {
        'number': 'DISP-TRAIN-001',
        'current_state': 'IN_PROGRESS',  # Pending manager approval
        'disposition_type': 'REWORK',
        'severity': 'MINOR',
        'qa_report_key': 'QR-TRAIN-001',
        'description': 'Recommend rework - polish surface to remove scratch.',
        'resolution_notes': '',
        'containment_action': '',
        'requires_customer_approval': False,
        'customer_approval_received': False,
        'customer_approval_reference': '',
        'scrap_verified': False,
        'scrap_verification_method': '',
        'resolution_completed': False,
        'rework_attempt_at_step': 1,
    },
    {
        'number': 'DISP-TRAIN-002',
        'current_state': 'OPEN',  # Incomplete, for rejection exercise
        'disposition_type': '',  # Not yet decided
        'severity': 'MAJOR',
        'qa_report_key': 'QR-TRAIN-002',
        'description': '',  # Missing info for rejection exercise
        'resolution_notes': '',
        'containment_action': '',
        'requires_customer_approval': False,
        'customer_approval_received': False,
        'customer_approval_reference': '',
        'scrap_verified': False,
        'scrap_verification_method': '',
        'resolution_completed': False,
        'rework_attempt_at_step': 1,
    },
]

# Training CAPA
TRAINING_CAPAS = [
    {
        'number': 'CAPA-TRAIN-COMPLETE',
        'problem_statement': 'Training Exercise CAPA - Verification Practice. This CAPA has completed all corrective actions and is ready for verification closure. Use this to practice the CAPA verification and closure workflow.',
        'status': CapaStatus.PENDING_VERIFICATION,
        'capa_type': CapaType.CORRECTIVE,
        'severity': CapaSeverity.MINOR,
        'tasks': [
            {'description': 'Root cause analysis', 'completed': True},
            {'description': 'Implement corrective action', 'completed': True},
            {'description': 'Update work instruction', 'completed': True},
            {'description': 'Train affected personnel', 'completed': True},
        ],
    },
]

# =============================================================================
# ASSESSMENT DATA - For practical assessment sections in training guides
# =============================================================================

# Assessment orders (for final knowledge verification exercises)
ASSESSMENT_ORDERS = [
    {
        'name': 'ASSESS-001',
        'description': 'Operator assessment - find and track this order',
        'status': OrdersStatus.IN_PROGRESS,
        'parts_count': 6,
        'parts_prefix': 'ASSESS-001',
        'customer_key': 'Midwest Fleet Services',
        'distribute_parts': True,
    },
    {
        'name': 'ASSESS-003',
        'description': 'Operator assessment - specific part lookup',
        'status': OrdersStatus.IN_PROGRESS,
        'parts_count': 5,
        'parts_prefix': 'ASSESS-003',
        'customer_key': 'Northern Trucking Co',
        'distribute_parts': True,
    },
    {
        'name': 'ASSESS-004',
        'description': 'Operator assessment - search exercise',
        'status': OrdersStatus.PENDING,
        'parts_count': 4,
        'parts_prefix': 'ASSESS-004',
        'customer_key': 'Great Lakes Diesel',
        'distribute_parts': False,
    },
    {
        'name': 'ASSESS-QA-001',
        'description': 'QA Inspector assessment - FPI completion exercise',
        'status': OrdersStatus.IN_PROGRESS,
        'parts_count': 10,
        'parts_prefix': 'ASSESS-QA-001',
        'customer_key': 'Midwest Fleet Services',
        'distribute_parts': False,
        'step_name': 'Final Test',  # Parts at inspection step for FPI training
        'work_order_id': 'ASSESS-QA-001',
        'requires_sampling_count': 1,  # First part requires QA (FPI scenario)
    },
    {
        'name': 'ASSESS-QA-002',
        'description': 'QA Inspector assessment - sampling inspection exercise',
        'status': OrdersStatus.IN_PROGRESS,
        'parts_count': 12,
        'parts_prefix': 'ASSESS-QA-002',
        'customer_key': 'Northern Trucking Co',
        'distribute_parts': True,  # Parts distributed across steps
        'work_order_id': 'ASSESS-QA-002',
        'requires_sampling_count': 4,  # Some parts require QA (sampling scenario)
    },
    {
        'name': 'ASSESS-PM-001',
        'description': 'Production manager assessment - order management',
        'status': OrdersStatus.PENDING,
        'parts_count': 8,
        'parts_prefix': 'ASSESS-PM-001',
        'customer_key': 'Midwest Fleet Services',
        'distribute_parts': False,
    },
]

# Assessment quality reports
ASSESSMENT_QUALITY_REPORTS = [
    {
        'number': 'QR-ASSESS-001',
        'description': 'Assessment exercise - dimensional out of tolerance. Bore diameter measures 0.003" oversize.',
        'status': 'FAIL',
        'part_key': 'ASSESS-QA-PART-001',
        'sampling_method': 'manual',
        'is_first_piece': False,
    },
    {
        'number': 'QR-ASSESS-002',
        'description': 'Assessment exercise - visual defect found during inspection.',
        'status': 'FAIL',
        'part_key': 'ASSESS-QA-PART-002',
        'sampling_method': 'manual',
        'is_first_piece': False,
    },
]

# Assessment dispositions
ASSESSMENT_DISPOSITIONS = [
    {
        'number': 'DISP-ASSESS-001',
        'current_state': 'IN_PROGRESS',  # Ready for QA Manager approval
        'disposition_type': 'REWORK',
        'severity': 'MAJOR',
        'qa_report_key': 'QR-ASSESS-001',
        'description': 'Recommend rework - re-hone bore to specification.',
        'resolution_notes': '',
        'containment_action': '',
        'requires_customer_approval': False,
        'customer_approval_received': False,
        'customer_approval_reference': '',
        'scrap_verified': False,
        'scrap_verification_method': '',
        'resolution_completed': False,
        'rework_attempt_at_step': 1,
    },
]

# Assessment CAPA
ASSESSMENT_CAPAS = [
    {
        'number': 'CAPA-ASSESS-READY',
        'problem_statement': 'Assessment CAPA - Ready for closure verification. Repeated dimensional failures on bore operations traced to worn tooling. All corrective actions complete.',
        'status': CapaStatus.PENDING_VERIFICATION,
        'capa_type': CapaType.CORRECTIVE,
        'severity': CapaSeverity.MAJOR,
        'tasks': [
            {'description': 'Perform 5-Why analysis on bore failures', 'completed': True},
            {'description': 'Replace worn boring tool', 'completed': True},
            {'description': 'Update tool change frequency in work instruction', 'completed': True},
            {'description': 'Train operators on tool wear indicators', 'completed': True},
        ],
    },
]


class TrainingExercisesSeeder(BaseSeeder):
    """
    Creates TRAIN-* objects for training guide exercises.

    These are deterministic, specific records referenced by name in
    the training documentation exercises.
    """

    def __init__(self, stdout, style, tenant, scale='small'):
        super().__init__(stdout, style, scale=scale)
        self.tenant = tenant
        self.today = timezone.now().date()

        # Cache for created objects
        self._orders = {}
        self._parts = {}
        self._quality_reports = {}
        self._dispositions = {}
        self._capas = {}

    def seed(self, companies, users, part_types=None):
        """
        Create all training exercise data.

        Args:
            companies: Dict with 'by_name' key mapping company names to objects
            users: Dict with user categories
            part_types: List of available part types

        Returns:
            dict with all created training data
        """
        self.log("Creating training exercise data (TRAIN-* objects)...")

        self._companies = companies.get('by_name', {})
        self._users = users
        self._part_types = part_types or []

        # Get a default part type and process
        self._default_part_type = self._part_types[0] if self._part_types else None
        self._default_process = None
        self._process_steps = []

        if self._default_part_type:
            # PartTypes has a reverse relation 'processes' from Processes.part_type FK
            self._default_process = self._default_part_type.processes.first()
            if self._default_process:
                self._process_steps = list(
                    ProcessStep.objects.filter(process=self._default_process)
                    .select_related('step')
                    .order_by('order')
                )

        # Create training data in order of dependencies
        self._create_training_orders()
        self._create_training_parts()
        self._create_training_quality_reports()
        self._create_training_dispositions()
        self._create_training_capas()

        # Create assessment data (for practical assessment sections)
        self._create_assessment_orders()
        self._create_assessment_parts()
        self._create_assessment_quality_reports()
        self._create_assessment_dispositions()
        self._create_assessment_capas()

        train_orders = len([k for k in self._orders if k.startswith('TRAIN')])
        assess_orders = len([k for k in self._orders if k.startswith('ASSESS')])
        self.log(f"  Created {train_orders} training orders, {assess_orders} assessment orders")
        self.log(f"  Created {len(self._parts)} parts")
        self.log(f"  Created {len(self._quality_reports)} quality reports")
        self.log(f"  Created {len(self._dispositions)} dispositions")
        self.log(f"  Created {len(self._capas)} CAPAs")

        return {
            'orders': self._orders,
            'parts': self._parts,
            'quality_reports': self._quality_reports,
            'dispositions': self._dispositions,
            'capas': self._capas,
        }

    def _create_training_orders(self):
        """Create training orders."""
        customers = self._users.get('customers', [])
        default_customer = customers[0] if customers else None

        for order_config in TRAINING_ORDERS:
            customer = default_customer

            # Try to find specific customer company
            customer_company = self._companies.get(order_config['customer_key'])
            if customer_company:
                # Find a customer user for this company
                for c in customers:
                    if c.parent_company == customer_company:
                        customer = c
                        break

            order, created = Orders.objects.update_or_create(
                tenant=self.tenant,
                order_number=order_config['name'],  # Use TRAIN-* as order_number
                defaults={
                    'name': order_config['name'],
                    'customer': customer,
                    'company': customer.parent_company if customer else None,
                    'order_status': order_config['status'],
                    'estimated_completion': self.today + timedelta(days=14),
                    'customer_note': order_config['description'],
                }
            )

            self._orders[order_config['name']] = {
                'order': order,
                'config': order_config,
            }

    def _create_training_parts(self):
        """Create training parts for each training order."""
        if not self._default_part_type or not self._default_process:
            self.log("  Warning: No part type/process available, skipping training parts")
            return

        steps = [ps.step for ps in self._process_steps]
        if not steps:
            return

        for order_name, order_data in self._orders.items():
            order = order_data['order']
            config = order_data['config']

            # Create work order for this training order
            # WorkOrder model: ERP_id, related_order (FK Orders), process (FK Processes),
            # workorder_status, priority, quantity. Does NOT have 'part_type' or 'order'.
            # Use custom work_order_id if specified, otherwise default to "WO-{order_name}"
            work_order_id = config.get('work_order_id', f"WO-{config['name']}")
            work_order, _ = WorkOrder.objects.update_or_create(
                tenant=self.tenant,
                ERP_id=work_order_id,
                defaults={
                    'related_order': order,
                    'process': self._default_process,
                    'workorder_status': WorkOrderStatus.IN_PROGRESS if config['status'] == OrdersStatus.IN_PROGRESS else WorkOrderStatus.PENDING,
                }
            )

            # Create parts
            requires_sampling_count = config.get('requires_sampling_count', 0)

            for i in range(config['parts_count']):
                part_serial = f"{config['parts_prefix']}-{i + 1:03d}"

                # Determine which step this part should be at
                step = self._determine_part_step(steps, i, config)
                # PartsStatus: IN_PROGRESS, COMPLETED, QUARANTINED, etc.
                status = PartsStatus.IN_PROGRESS if step != steps[-1] else PartsStatus.COMPLETED

                if config['status'] == OrdersStatus.ON_HOLD:
                    # Orders can be ON_HOLD but Parts uses QUARANTINED for held items
                    status = PartsStatus.QUARANTINED

                # First N parts require sampling (for QA training scenarios)
                requires_sampling = i < requires_sampling_count

                # Parts requiring sampling should be AWAITING_QA
                if requires_sampling and status == PartsStatus.IN_PROGRESS:
                    status = PartsStatus.AWAITING_QA

                # First part is FPI candidate for QA training scenarios
                is_fpi_candidate = (i == 0 and requires_sampling_count > 0)

                part, _ = Parts.objects.update_or_create(
                    tenant=self.tenant,
                    ERP_id=part_serial,
                    defaults={
                        'order': order,
                        'work_order': work_order,
                        'part_type': self._default_part_type,
                        'step': step,
                        'part_status': status,
                        'requires_sampling': requires_sampling,
                        'is_fpi_candidate': is_fpi_candidate,
                    }
                )

                self._parts[part_serial] = part

        # Create special parts for quality report exercises (not tied to orders above)
        for qr_config in TRAINING_QUALITY_REPORTS:
            part_key = qr_config.get('part_key')
            if part_key and part_key not in self._parts:
                # Create a standalone part for the quality report
                step = steps[len(steps) // 2] if steps else None  # Middle step

                part, _ = Parts.objects.update_or_create(
                    tenant=self.tenant,
                    ERP_id=part_key,
                    defaults={
                        'part_type': self._default_part_type,
                        'step': step,
                        'part_status': PartsStatus.QUARANTINED,
                    }
                )
                self._parts[part_key] = part

    def _determine_part_step(self, steps, part_index, config):
        """Determine which step a part should be at based on distribution config."""
        if not steps:
            return None

        # Check for explicit step_name first
        step_name = config.get('step_name')
        if step_name:
            for step in steps:
                if step.name == step_name:
                    return step
            # Fallback to first step if named step not found
            return steps[0]

        distribute = config.get('distribute_parts', False)

        if distribute is False:
            # All at first step
            return steps[0]
        elif distribute == 'bottleneck':
            # Most parts at middle step (bottleneck)
            middle_idx = len(steps) // 2
            if part_index < 2:
                # First two parts past the bottleneck
                return steps[min(middle_idx + 1, len(steps) - 1)]
            else:
                # Rest stuck at bottleneck
                return steps[middle_idx]
        else:
            # Distribute evenly across steps
            step_idx = (part_index * len(steps)) // config['parts_count']
            return steps[min(step_idx, len(steps) - 1)]

    def _create_training_quality_reports(self):
        """Create training quality reports."""
        qa_users = self._users.get('employees', [])
        detected_by = None
        for u in qa_users:
            if hasattr(u, 'email') and 'qa' in u.email.lower():
                detected_by = u
                break
        if not detected_by and qa_users:
            detected_by = qa_users[0]

        for qr_config in TRAINING_QUALITY_REPORTS:
            part = self._parts.get(qr_config['part_key'])

            qr, _ = QualityReports.objects.update_or_create(
                tenant=self.tenant,
                report_number=qr_config['number'],
                defaults={
                    'description': qr_config['description'],
                    'status': qr_config['status'],
                    'part': part,
                    'detected_by': detected_by,
                    'sampling_method': qr_config['sampling_method'],
                    'is_first_piece': qr_config['is_first_piece'],
                }
            )

            self._quality_reports[qr_config['number']] = qr

    def _create_training_dispositions(self):
        """Create training dispositions."""
        qa_managers = [u for u in self._users.get('employees', [])
                       if hasattr(u, 'email') and 'qa' in u.email.lower()]
        assigned_to = qa_managers[0] if qa_managers else None

        steps = [ps.step for ps in self._process_steps]
        middle_step = steps[len(steps) // 2] if steps else None

        for disp_config in TRAINING_DISPOSITIONS:
            qr = self._quality_reports.get(disp_config['qa_report_key'])

            defaults = {
                'current_state': disp_config['current_state'],
                'disposition_type': disp_config['disposition_type'],
                'severity': disp_config['severity'],
                'description': disp_config['description'],
                'resolution_notes': disp_config['resolution_notes'],
                'containment_action': disp_config['containment_action'],
                'requires_customer_approval': disp_config['requires_customer_approval'],
                'customer_approval_received': disp_config['customer_approval_received'],
                'customer_approval_reference': disp_config['customer_approval_reference'],
                'scrap_verified': disp_config['scrap_verified'],
                'scrap_verification_method': disp_config['scrap_verification_method'],
                'resolution_completed': disp_config['resolution_completed'],
                'rework_attempt_at_step': disp_config['rework_attempt_at_step'],
                'assigned_to': assigned_to,
                'step': middle_step,
            }

            # Update or create the disposition
            disp, created = QuarantineDisposition.objects.update_or_create(
                tenant=self.tenant,
                disposition_number=disp_config['number'],
                defaults=defaults,
            )

            # Link to quality report via M2M
            if qr and created:
                disp.quality_reports.add(qr)

            self._dispositions[disp_config['number']] = disp

    def _create_training_capas(self):
        """Create training CAPAs with tasks."""
        qa_managers = [u for u in self._users.get('employees', [])
                       if hasattr(u, 'email') and 'qa' in u.email.lower()]
        assigned_user = qa_managers[0] if qa_managers else None

        for capa_config in TRAINING_CAPAS:
            capa, created = CAPA.objects.update_or_create(
                tenant=self.tenant,
                capa_number=capa_config['number'],
                defaults={
                    'problem_statement': capa_config['problem_statement'],
                    'status': capa_config['status'],
                    'capa_type': capa_config['capa_type'],
                    'severity': capa_config['severity'],
                    'assigned_to': assigned_user,
                    'initiated_by': assigned_user,
                }
            )

            # Create tasks if CAPA was just created
            if created:
                for i, task_config in enumerate(capa_config.get('tasks', [])):
                    task_status = CapaTaskStatus.COMPLETED if task_config['completed'] else CapaTaskStatus.NOT_STARTED
                    CapaTasks.objects.create(
                        tenant=self.tenant,
                        capa=capa,
                        task_type=CapaTaskType.CORRECTIVE,
                        description=task_config['description'],
                        status=task_status,
                        assigned_to=assigned_user,
                        completed_date=self.today if task_config['completed'] else None,
                        completed_by=assigned_user if task_config['completed'] else None,
                    )

            self._capas[capa_config['number']] = capa

    # =========================================================================
    # Assessment Data Creation (mirrors training data but for assessments)
    # =========================================================================

    def _create_assessment_orders(self):
        """Create assessment orders for practical assessment exercises."""
        customers = self._users.get('customers', [])
        default_customer = customers[0] if customers else None

        for order_config in ASSESSMENT_ORDERS:
            customer = default_customer

            customer_company = self._companies.get(order_config['customer_key'])
            if customer_company:
                for c in customers:
                    if c.parent_company == customer_company:
                        customer = c
                        break

            order, created = Orders.objects.update_or_create(
                tenant=self.tenant,
                order_number=order_config['name'],  # Use ASSESS-* as order_number
                defaults={
                    'name': order_config['name'],
                    'customer': customer,
                    'company': customer.parent_company if customer else None,
                    'order_status': order_config['status'],
                    'estimated_completion': self.today + timedelta(days=21),
                    'customer_note': order_config['description'],
                }
            )

            self._orders[order_config['name']] = {
                'order': order,
                'config': order_config,
            }

    def _create_assessment_parts(self):
        """Create assessment parts for practical assessment exercises."""
        if not self._default_part_type or not self._default_process:
            return

        steps = [ps.step for ps in self._process_steps]
        if not steps:
            return

        # Create parts for assessment orders
        for order_name, order_data in self._orders.items():
            if not order_name.startswith('ASSESS'):
                continue

            order = order_data['order']
            config = order_data['config']

            # Use custom work_order_id if specified, otherwise default to "WO-{order_name}"
            work_order_id = config.get('work_order_id', f"WO-{config['name']}")
            work_order, _ = WorkOrder.objects.update_or_create(
                tenant=self.tenant,
                ERP_id=work_order_id,
                defaults={
                    'related_order': order,
                    'process': self._default_process,
                    'workorder_status': WorkOrderStatus.IN_PROGRESS if config['status'] == OrdersStatus.IN_PROGRESS else WorkOrderStatus.PENDING,
                }
            )

            requires_sampling_count = config.get('requires_sampling_count', 0)

            for i in range(config['parts_count']):
                part_serial = f"{config['parts_prefix']}-{i + 1:03d}"
                step = self._determine_part_step(steps, i, config)
                status = PartsStatus.IN_PROGRESS if step != steps[-1] else PartsStatus.COMPLETED

                if config['status'] == OrdersStatus.ON_HOLD:
                    status = PartsStatus.QUARANTINED

                # First N parts require sampling (for QA training scenarios)
                requires_sampling = i < requires_sampling_count

                # Parts requiring sampling should be AWAITING_QA
                if requires_sampling and status == PartsStatus.IN_PROGRESS:
                    status = PartsStatus.AWAITING_QA

                # First part is FPI candidate for QA training scenarios
                is_fpi_candidate = (i == 0 and requires_sampling_count > 0)

                part, _ = Parts.objects.update_or_create(
                    tenant=self.tenant,
                    ERP_id=part_serial,
                    defaults={
                        'order': order,
                        'work_order': work_order,
                        'part_type': self._default_part_type,
                        'step': step,
                        'part_status': status,
                        'requires_sampling': requires_sampling,
                        'is_fpi_candidate': is_fpi_candidate,
                    }
                )
                self._parts[part_serial] = part

        # Create special parts for assessment quality reports
        for qr_config in ASSESSMENT_QUALITY_REPORTS:
            part_key = qr_config.get('part_key')
            if part_key and part_key not in self._parts:
                step = steps[len(steps) // 2] if steps else None

                part, _ = Parts.objects.update_or_create(
                    tenant=self.tenant,
                    ERP_id=part_key,
                    defaults={
                        'part_type': self._default_part_type,
                        'step': step,
                        'part_status': PartsStatus.QUARANTINED,
                    }
                )
                self._parts[part_key] = part

    def _create_assessment_quality_reports(self):
        """Create assessment quality reports."""
        qa_users = self._users.get('employees', [])
        detected_by = None
        for u in qa_users:
            if hasattr(u, 'email') and 'qa' in u.email.lower():
                detected_by = u
                break
        if not detected_by and qa_users:
            detected_by = qa_users[0]

        for qr_config in ASSESSMENT_QUALITY_REPORTS:
            part = self._parts.get(qr_config['part_key'])

            qr, _ = QualityReports.objects.update_or_create(
                tenant=self.tenant,
                report_number=qr_config['number'],
                defaults={
                    'description': qr_config['description'],
                    'status': qr_config['status'],
                    'part': part,
                    'detected_by': detected_by,
                    'sampling_method': qr_config['sampling_method'],
                    'is_first_piece': qr_config['is_first_piece'],
                }
            )
            self._quality_reports[qr_config['number']] = qr

    def _create_assessment_dispositions(self):
        """Create assessment dispositions."""
        qa_managers = [u for u in self._users.get('employees', [])
                       if hasattr(u, 'email') and 'qa' in u.email.lower()]
        assigned_to = qa_managers[0] if qa_managers else None

        steps = [ps.step for ps in self._process_steps]
        middle_step = steps[len(steps) // 2] if steps else None

        for disp_config in ASSESSMENT_DISPOSITIONS:
            qr = self._quality_reports.get(disp_config['qa_report_key'])

            defaults = {
                'current_state': disp_config['current_state'],
                'disposition_type': disp_config['disposition_type'],
                'severity': disp_config['severity'],
                'description': disp_config['description'],
                'resolution_notes': disp_config['resolution_notes'],
                'containment_action': disp_config['containment_action'],
                'requires_customer_approval': disp_config['requires_customer_approval'],
                'customer_approval_received': disp_config['customer_approval_received'],
                'customer_approval_reference': disp_config['customer_approval_reference'],
                'scrap_verified': disp_config['scrap_verified'],
                'scrap_verification_method': disp_config['scrap_verification_method'],
                'resolution_completed': disp_config['resolution_completed'],
                'rework_attempt_at_step': disp_config['rework_attempt_at_step'],
                'assigned_to': assigned_to,
                'step': middle_step,
            }

            disp, created = QuarantineDisposition.objects.update_or_create(
                tenant=self.tenant,
                disposition_number=disp_config['number'],
                defaults=defaults,
            )

            if qr and created:
                disp.quality_reports.add(qr)

            self._dispositions[disp_config['number']] = disp

    def _create_assessment_capas(self):
        """Create assessment CAPAs with tasks."""
        qa_managers = [u for u in self._users.get('employees', [])
                       if hasattr(u, 'email') and 'qa' in u.email.lower()]
        assigned_user = qa_managers[0] if qa_managers else None

        for capa_config in ASSESSMENT_CAPAS:
            capa, created = CAPA.objects.update_or_create(
                tenant=self.tenant,
                capa_number=capa_config['number'],
                defaults={
                    'problem_statement': capa_config['problem_statement'],
                    'status': capa_config['status'],
                    'capa_type': capa_config['capa_type'],
                    'severity': capa_config['severity'],
                    'assigned_to': assigned_user,
                    'initiated_by': assigned_user,
                }
            )

            if created:
                for i, task_config in enumerate(capa_config.get('tasks', [])):
                    task_status = CapaTaskStatus.COMPLETED if task_config['completed'] else CapaTaskStatus.NOT_STARTED
                    CapaTasks.objects.create(
                        tenant=self.tenant,
                        capa=capa,
                        task_type=CapaTaskType.CORRECTIVE,
                        description=task_config['description'],
                        status=task_status,
                        assigned_to=assigned_user,
                        completed_date=self.today if task_config['completed'] else None,
                        completed_by=assigned_user if task_config['completed'] else None,
                    )

            self._capas[capa_config['number']] = capa
