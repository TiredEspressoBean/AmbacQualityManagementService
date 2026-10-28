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
    ProcessStep, CAPA, CapaStatus,
    CapaType, CapaSeverity, CapaTasks, CapaTaskType, CapaTaskStatus,
    RcaRecord, RcaReviewStatus, RootCauseVerificationStatus,
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
        'name': 'ASSESS-PM-001',
        'description': 'Production manager assessment - order management',
        'status': OrdersStatus.PENDING,
        'parts_count': 8,
        'parts_prefix': 'ASSESS-PM-001',
        'customer_key': 'Midwest Fleet Services',
        'distribute_parts': False,
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
            # The base track is new manufacture: training work runs on Injector Build.
            # (processes.first() picked whichever came first, which was Injector Reman,
            # so new injectors appeared at Core Receiving.)
            from .routes import BUILD, process_named
            self._default_process = (process_named(self.tenant, BUILD)
                                     or self._default_part_type.processes.first())
            if self._default_process:
                self._process_steps = list(
                    ProcessStep.objects.filter(process=self._default_process)
                    .select_related('step')
                    .order_by('order')
                )

        # Create training data in order of dependencies
        self._create_training_orders()
        self._create_training_parts()
        self._create_training_capas()

        # Create assessment data (for practical assessment sections)
        self._create_assessment_orders()
        self._create_assessment_parts()
        self._create_assessment_capas()

        train_orders = len([k for k in self._orders if k.startswith('TRAIN')])
        assess_orders = len([k for k in self._orders if k.startswith('ASSESS')])
        self.log(f"  Created {train_orders} training orders, {assess_orders} assessment orders")
        self.log(f"  Created {len(self._parts)} parts")
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
            customer_company, customer = self._order_customer(
                order_config, customers, default_customer)

            order, created = Orders.objects.update_or_create(
                tenant=self.tenant,
                order_number=order_config['name'],  # Use TRAIN-* as order_number
                defaults={
                    'name': order_config['name'],
                    'customer': customer,
                    'company': customer_company,
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

        # Working steps only: up to the terminal one, not it and not the Rework step
        # ordered after it. A part placed at Ship has nothing left to schedule, and one
        # at Rework got there through no disposition.
        steps = []
        for ps in self._process_steps:
            if ps.step.is_terminal:
                break
            steps.append(ps.step)
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
                    'quantity': config['parts_count'],
                    'expected_completion': order.estimated_completion,
                }
            )

            # Create parts
            requires_sampling_count = config.get('requires_sampling_count', 0)

            for i in range(config['parts_count']):
                part_serial = f"{config['parts_prefix']}-{i + 1:03d}"

                # Determine which step this part should be at
                step = self._determine_part_step(steps, i, config)
                # PartsStatus: IN_PROGRESS, COMPLETED, QUARANTINED, etc.
                status = PartsStatus.IN_PROGRESS

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

            if config['status'] == OrdersStatus.ON_HOLD:
                self._hold(work_order, config)

    def _hold(self, work_order, config):
        """Hold the work order the way a manager does, through the hold service. Its
        parts keep their places; quarantining them would need a quality report and a
        disposition behind each, which a held order doesn't have."""
        from Tracker.models import User, WorkOrderHold
        from Tracker.services.mes.work_order import place_on_hold
        if WorkOrderHold.objects.filter(work_order=work_order, cleared_at__isnull=True,
                                        is_voided=False).exists():
            return
        manager = User.objects.filter(email='jennifer.mgr@demo.ambac.com').first()
        place_on_hold(work_order, 'QUALITY', manager, notes=config['description'])

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

            self._ensure_rca_for_verification_ready(capa, capa_config, assigned_user)
            self._capas[capa_config['number']] = capa

    # =========================================================================
    # Assessment Data Creation (mirrors training data but for assessments)
    # =========================================================================

    def _order_customer(self, order_config, customers, default_customer):
        """The order's company, and a contact there if it has one. Taking the company
        from a contact, with the default customer as fallback, put every order on
        Midwest Fleet whenever the named company had no contact user."""
        company = self._companies.get(order_config['customer_key'])
        if company is None:
            return (default_customer.parent_company if default_customer else None,
                    default_customer)
        return company, next((c for c in customers if c.parent_company == company), None)

    def _create_assessment_orders(self):
        """Create assessment orders for practical assessment exercises."""
        customers = self._users.get('customers', [])
        default_customer = customers[0] if customers else None

        for order_config in ASSESSMENT_ORDERS:
            customer_company, customer = self._order_customer(
                order_config, customers, default_customer)

            order, created = Orders.objects.update_or_create(
                tenant=self.tenant,
                order_number=order_config['name'],  # Use ASSESS-* as order_number
                defaults={
                    'name': order_config['name'],
                    'customer': customer,
                    'company': customer_company,
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

        # Working steps only: up to the terminal one, not it and not the Rework step
        # ordered after it. A part placed at Ship has nothing left to schedule, and one
        # at Rework got there through no disposition.
        steps = []
        for ps in self._process_steps:
            if ps.step.is_terminal:
                break
            steps.append(ps.step)
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
                    'quantity': config['parts_count'],
                    'expected_completion': order.estimated_completion,
                }
            )

            requires_sampling_count = config.get('requires_sampling_count', 0)

            for i in range(config['parts_count']):
                part_serial = f"{config['parts_prefix']}-{i + 1:03d}"
                step = self._determine_part_step(steps, i, config)
                status = PartsStatus.IN_PROGRESS

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

    def _ensure_rca_for_verification_ready(self, capa, capa_config, user):
        """Give a verification-ready preset the RCA record its status implies.

        `CAPASerializer` returns `CAPA.computed_status`, not the stored
        `status` field, and PENDING_VERIFICATION requires
        `all_tasks_completed() AND rca_complete()`. `rca_complete()` wants an
        `RcaRecord` whose `root_cause_summary` is non-null.

        Both of these presets declare PENDING_VERIFICATION and mark every task
        complete, but never created an RCA — so they computed as In Progress
        and the Verification tab had nothing to act on. Two exhibits whose
        stated purpose is "practise the verification and closure workflow"
        couldn't be used for it.

        Same class of bug as the containment tag-along in
        seed/demo/capa.py: the seed asserted a status without arranging the
        facts that produce it.
        """
        if capa_config['status'] != CapaStatus.PENDING_VERIFICATION:
            return
        RcaRecord.objects.update_or_create(
            capa=capa,
            defaults={
                'tenant': self.tenant,
                'rca_method': 'FIVE_WHYS',
                'problem_description': capa_config['problem_statement'][:200],
                'root_cause_summary': capa_config.get(
                    'root_cause_summary',
                    'Root cause identified and addressed; retained for '
                    'verification practice.',
                ),
                'conducted_by': user,
                'conducted_date': self.today.date() if hasattr(self.today, 'date') else self.today,
                'rca_review_status': RcaReviewStatus.COMPLETED,
                'root_cause_verification_status': RootCauseVerificationStatus.VERIFIED,
            },
        )

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

            self._give_go_ahead(capa)
            self._ensure_rca_for_verification_ready(capa, capa_config, assigned_user)
            self._capas[capa_config['number']] = capa

    def _give_go_ahead(self, capa):
        """Its corrective work is done, so its plan was approved first, through the
        approval service. Only a QA Manager approves a Major/Critical CAPA's plan (B3,
        2026-10-28), and Maria is the shop's only one: having raised it, she approves it
        herself — allowed for a CAPA when nobody else is eligible, with the comment as
        her justification, and flagged self-approved on the record."""
        from datetime import timedelta
        from Tracker.models import ApprovalRequest, ApprovalDecision, ApprovalResponse, User
        from Tracker.services.core.approval import submit_approval_response
        request = ApprovalRequest.objects.filter(object_id=str(capa.id), status='PENDING').first()
        approver = User.objects.filter(email='maria.qa@demo.ambac.com').first()
        if request is None or approver is None or not request.can_approve(approver):
            self.log(f"  Warning: no go-ahead given for {capa.capa_number}", warning=True)
            return
        response = submit_approval_response(
            request, approver, ApprovalDecision.APPROVED,
            comments='Tooling plan and containment are adequate; proceed.',
            signature_meaning='Approved')
        from django.utils import timezone
        when = timezone.now() - timedelta(days=10)
        ApprovalResponse.objects.filter(pk=response.pk).update(decision_date=when, created_at=when)
        ApprovalRequest.objects.filter(pk=request.pk).update(completed_at=when)
        CAPA.objects.filter(pk=capa.pk).update(approved_at=when)
