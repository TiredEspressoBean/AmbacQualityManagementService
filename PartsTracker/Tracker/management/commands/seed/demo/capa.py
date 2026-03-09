"""
Demo CAPA seeder with preset CAPAs matching DEMO_DATA_SYSTEM.md.

Creates:
- CAPA-2024-001: Closed with verification (torque wrench calibration)
- CAPA-2024-002: In verification - tasks complete, awaiting verification (training scenario)
- CAPA-2024-003: In progress (nozzle defects, main demo)
- CAPA-2024-004: Open (pending RCA - contamination issue)
- CAPA-2024-005: Open, just initiated (customer complaint)
"""

from datetime import timedelta
from django.utils import timezone

from Tracker.models import (
    CAPA, CapaTasks, CapaTaskAssignee, RcaRecord, FiveWhys, Fishbone, CapaVerification,
    QualityReports, Steps, WorkOrder, User,
    CapaTaskType, CapaTaskStatus, CapaTaskCompletionMode, RcaReviewStatus, RootCauseVerificationStatus,
    CapaStatus, CapaSeverity, CapaType, EffectivenessResult,
)

from ..base import BaseSeeder


# Demo CAPAs matching DEMO_DATA_SYSTEM.md
# All enum values use proper enum members (UPPERCASE) for consistency
DEMO_CAPAS = [
    {
        'capa_number': 'CAPA-2024-001',
        'problem_statement': 'Torque wrench calibration drift causing loose fittings',
        'status': CapaStatus.CLOSED,
        'capa_type': CapaType.CORRECTIVE,
        'severity': CapaSeverity.MINOR,
        'initiated_by': 'sarah.qa@demo.ambac.com',
        'assigned_to': 'mike.ops@demo.ambac.com',
        'initiated_days_ago': 45,
        'completed_days_ago': 20,
        'approval_required': False,
        'approval_status': 'NOT_REQUIRED',
        'immediate_action': 'Quarantine affected torque wrenches for recalibration',
        'rca': {
            'method': 'FIVE_WHYS',
            'problem_description': 'Multiple loose fitting failures detected in final test',
            'root_cause_summary': 'Calibration interval too long for usage rate',
            'conducted_by': 'sarah.qa@demo.ambac.com',
            'conducted_days_ago': 40,
            'review_status': RcaReviewStatus.COMPLETED,
            'verification_status': RootCauseVerificationStatus.VERIFIED,
            'five_whys': {
                'why_1_question': 'Why are fittings coming loose?',
                'why_1_answer': 'Torque applied was below specification',
                'why_2_question': 'Why was torque below spec?',
                'why_2_answer': 'Torque wrench was under-reading by 15%',
                'why_3_question': 'Why was the wrench under-reading?',
                'why_3_answer': 'Calibration had drifted beyond tolerance',
                'why_4_question': 'Why had calibration drifted?',
                'why_4_answer': 'Wrench exceeded recommended usage cycles',
                'why_5_question': 'Why exceeded usage cycles?',
                'why_5_answer': 'Calibration interval based on time, not usage',
                'identified_root_cause': 'Calibration interval based on time, not usage',
            },
        },
        'verification': {
            'verified_by': 'jennifer.mgr@demo.ambac.com',
            'verified_days_ago': 21,
            'effectiveness_result': EffectivenessResult.CONFIRMED,
            'verification_method': 'Production monitoring and quality metric review',
            'verification_criteria': 'Zero torque-related defects over 30-day monitoring period',
            'verification_notes': '30-day monitoring shows zero torque-related defects',
        },
        'tasks': [
            {'description': 'Recalibrate all torque wrenches', 'assignee': 'mike.ops@demo.ambac.com', 'status': CapaTaskStatus.COMPLETED, 'task_type': CapaTaskType.CONTAINMENT},
            {'description': 'Implement usage-based calibration tracking', 'assignee': 'jennifer.mgr@demo.ambac.com', 'status': CapaTaskStatus.COMPLETED, 'task_type': CapaTaskType.CORRECTIVE},
            {'description': 'Update calibration procedure', 'assignee': 'sarah.qa@demo.ambac.com', 'status': CapaTaskStatus.COMPLETED, 'task_type': CapaTaskType.PREVENTIVE},
        ],
    },
    {
        # IN_VERIFICATION scenario - all tasks complete, awaiting verification
        'capa_number': 'CAPA-2024-002',
        'problem_statement': 'Supplier documentation inconsistency causing receiving delays',
        'status': CapaStatus.PENDING_VERIFICATION,
        'capa_type': CapaType.PREVENTIVE,
        'severity': CapaSeverity.MINOR,
        'initiated_by': 'mike.ops@demo.ambac.com',
        'assigned_to': 'sarah.qa@demo.ambac.com',
        'initiated_days_ago': 30,
        'due_days': 7,  # Past due for verification
        'approval_required': False,
        'approval_status': 'NOT_REQUIRED',
        'immediate_action': 'Manual verification of incoming documentation',
        'rca': {
            'method': 'FIVE_WHYS',
            'problem_description': 'Receiving inspection frequently delayed due to missing supplier docs',
            'root_cause_summary': 'No standardized documentation checklist for suppliers',
            'conducted_by': 'mike.ops@demo.ambac.com',
            'conducted_days_ago': 25,
            'review_status': RcaReviewStatus.COMPLETED,
            'verification_status': RootCauseVerificationStatus.VERIFIED,
            'five_whys': {
                'why_1_question': 'Why are receiving inspections delayed?',
                'why_1_answer': 'Required documentation often missing',
                'why_2_question': 'Why is documentation missing?',
                'why_2_answer': 'Suppliers unsure of requirements',
                'why_3_question': 'Why are suppliers unsure?',
                'why_3_answer': 'No standardized checklist provided',
                'why_4_question': 'Why no standardized checklist?',
                'why_4_answer': 'Documentation requirements varied by part type',
                'why_5_question': 'Why varied requirements?',
                'why_5_answer': 'Historical accumulation without consolidation',
                'identified_root_cause': 'No standardized documentation checklist for suppliers',
            },
        },
        # No verification yet - training scenario for pending verification
        'tasks': [
            {'description': 'Create supplier documentation checklist', 'assignee': 'mike.ops@demo.ambac.com', 'status': CapaTaskStatus.COMPLETED, 'task_type': CapaTaskType.CORRECTIVE},
            {'description': 'Distribute checklist to all suppliers', 'assignee': 'sarah.qa@demo.ambac.com', 'status': CapaTaskStatus.COMPLETED, 'task_type': CapaTaskType.CORRECTIVE},
            {'description': 'Train receiving staff on new requirements', 'assignee': 'mike.ops@demo.ambac.com', 'status': CapaTaskStatus.COMPLETED, 'task_type': CapaTaskType.PREVENTIVE},
        ],
    },
    {
        'capa_number': 'CAPA-2024-003',
        'problem_statement': 'Elevated Nozzle Rejection Rate - March 2024',
        'status': CapaStatus.IN_PROGRESS,
        'capa_type': CapaType.CORRECTIVE,
        'severity': CapaSeverity.MAJOR,
        'initiated_by': 'jennifer.mgr@demo.ambac.com',
        'assigned_to': 'jennifer.mgr@demo.ambac.com',
        'initiated_days_ago': 7,
        'due_days': 14,
        'approval_required': True,
        'approval_status': 'PENDING',
        'immediate_action': 'Quarantine remaining nozzle inventory from batch NZ-2024-0315',
        'step': 'Nozzle Inspection',
        'work_order': 'WO-2024-0038-A',
        'link_quality_reports': True,  # Link QRs from Great Lakes order
        'rca': {
            'method': 'FISHBONE',
            'problem_description': '5 nozzle failures in 12-unit order vs. expected 1-2',
            'root_cause_summary': 'Supplier process change not communicated; audit schedule lapsed',
            'conducted_by': 'jennifer.mgr@demo.ambac.com',
            'conducted_days_ago': 5,
            'review_status': RcaReviewStatus.COMPLETED,
            'verification_status': RootCauseVerificationStatus.UNVERIFIED,
            'fishbone': {
                'problem_statement': 'Elevated nozzle rejection rate - 5 failures in 12-unit Great Lakes order',
                'man_causes': [
                    'Supplier audit overdue by 6 months',
                    'No incoming inspection for process changes',
                    'Training gap on nozzle inspection',
                ],
                'machine_causes': [
                    'Spray test equipment unable to detect micro-cracks',
                    'Magnification insufficient for crack detection',
                    'Flow meter sensitivity limits',
                ],
                'material_causes': [
                    'Supplier batch NZ-2024-0315 heat treatment variance',
                    'Delphi process change to heat treatment',
                    'Micro-cracks in nozzle bore from thermal stress',
                ],
                'method_causes': [
                    'Incoming inspection procedure outdated',
                    'No supplier process change notification system',
                    'Spray pattern test sampling rate too low',
                ],
                'measurement_causes': [
                    'Visual inspection cannot detect micro-cracks',
                    '3D heatmap analysis not part of incoming inspection',
                    'Spray angle tolerance too wide',
                ],
                'environment_causes': [
                    'No environmental factor identified',
                    'Storage conditions acceptable',
                    'No contamination detected',
                ],
                'identified_root_cause': 'Supplier process change (heat treatment) not communicated; supplier audit overdue by 6 months allowed change to go undetected',
            },
        },
        'tasks': [
            {'description': 'Contact Delphi re: batch NZ-2024-0315', 'assignee': 'jennifer.mgr@demo.ambac.com', 'status': CapaTaskStatus.COMPLETED, 'task_type': CapaTaskType.CONTAINMENT},
            {'description': 'Quarantine remaining batch inventory', 'assignee': 'mike.ops@demo.ambac.com', 'status': CapaTaskStatus.COMPLETED, 'task_type': CapaTaskType.CONTAINMENT},
            {'description': 'Schedule supplier audit', 'assignee': 'jennifer.mgr@demo.ambac.com', 'status': CapaTaskStatus.IN_PROGRESS, 'due_days': 7, 'task_type': CapaTaskType.CORRECTIVE},
            {
                'description': 'Update incoming inspection procedure',
                'assignee': 'sarah.qa@demo.ambac.com',
                'status': CapaTaskStatus.NOT_STARTED,
                'due_days': 10,
                'task_type': CapaTaskType.CORRECTIVE,
                # Multi-person task: QA Manager and QA Inspector both must approve
                'completion_mode': CapaTaskCompletionMode.ALL_ASSIGNEES,
                'assignees': [
                    {'user': 'sarah.qa@demo.ambac.com', 'status': CapaTaskStatus.NOT_STARTED},
                    {'user': 'maria.qa@demo.ambac.com', 'status': CapaTaskStatus.NOT_STARTED},
                ],
            },
            {
                'description': 'Implement tightened sampling for nozzles',
                'assignee': 'sarah.qa@demo.ambac.com',
                'status': CapaTaskStatus.NOT_STARTED,
                'due_days': 5,
                'task_type': CapaTaskType.PREVENTIVE,
                # Multi-person task: Any one of QA or Production can complete
                'completion_mode': CapaTaskCompletionMode.ANY_ASSIGNEE,
                'assignees': [
                    {'user': 'sarah.qa@demo.ambac.com', 'status': CapaTaskStatus.NOT_STARTED},
                    {'user': 'jennifer.mgr@demo.ambac.com', 'status': CapaTaskStatus.NOT_STARTED},
                ],
            },
        ],
    },
    {
        'capa_number': 'CAPA-2024-004',
        'problem_statement': 'Recurring contamination in cleaning process affecting seal integrity',
        'status': CapaStatus.OPEN,
        'capa_type': CapaType.CORRECTIVE,
        'severity': CapaSeverity.MAJOR,
        'initiated_by': 'jennifer.mgr@demo.ambac.com',
        'assigned_to': 'jennifer.mgr@demo.ambac.com',
        'initiated_days_ago': 3,
        'due_days': 21,
        'approval_required': True,
        'approval_status': 'PENDING',
        'immediate_action': 'Increased cleaning solution filtration and monitoring',
        # No RCA yet - investigation pending
        'tasks': [
            {'description': 'Review cleaning process parameters', 'assignee': 'mike.ops@demo.ambac.com', 'status': CapaTaskStatus.IN_PROGRESS, 'due_days': 5, 'task_type': CapaTaskType.CONTAINMENT},
            {'description': 'Conduct contamination analysis', 'assignee': 'sarah.qa@demo.ambac.com', 'status': CapaTaskStatus.NOT_STARTED, 'due_days': 7, 'task_type': CapaTaskType.CORRECTIVE},
        ],
    },
    {
        'capa_number': 'CAPA-2024-005',
        'problem_statement': 'Customer complaint - unit returned after 30 days with leak',
        'status': CapaStatus.OPEN,
        'capa_type': CapaType.CORRECTIVE,
        'severity': CapaSeverity.MAJOR,
        'initiated_by': 'jennifer.mgr@demo.ambac.com',
        'assigned_to': 'sarah.qa@demo.ambac.com',
        'initiated_days_ago': 0,  # Today
        'due_days': 14,
        'approval_required': True,
        'approval_status': 'PENDING',
        'immediate_action': 'Quarantine returned unit for failure analysis',
        # No RCA yet - just initiated
        'tasks': [
            {'description': 'Receive and document returned unit', 'assignee': 'mike.ops@demo.ambac.com', 'status': CapaTaskStatus.NOT_STARTED, 'due_days': 2, 'task_type': CapaTaskType.CONTAINMENT},
            {'description': 'Perform failure analysis', 'assignee': 'sarah.qa@demo.ambac.com', 'status': CapaTaskStatus.NOT_STARTED, 'due_days': 5, 'task_type': CapaTaskType.CORRECTIVE},
        ],
    },
]


class DemoCapaSeeder(BaseSeeder):
    """
    Creates preset CAPAs with RCA records and tasks.

    All data is deterministic - same result every time.
    """

    def __init__(self, stdout, style, tenant, scale='small'):
        super().__init__(stdout, style, scale=scale)
        self.tenant = tenant
        self.today = timezone.now()

    def seed(self, users):
        """
        Create all demo CAPAs.

        Args:
            users: dict with user lists including by_email lookup

        Returns:
            dict with created CAPAs, tasks, RCA records
        """
        self.log("Creating demo CAPAs...")

        result = {
            'capas': [],
            'tasks': [],
            'rca_records': [],
            'verifications': [],
        }

        # Get user lookup
        user_map = users.get('by_email', {})

        # Get step and work order lookups
        steps = Steps.objects.filter(tenant=self.tenant)
        step_map = {s.name: s for s in steps}

        work_orders = WorkOrder.objects.filter(tenant=self.tenant)
        wo_map = {wo.ERP_id: wo for wo in work_orders}

        for capa_data in DEMO_CAPAS:
            capa = self._create_capa(capa_data, user_map, step_map, wo_map)
            result['capas'].append(capa)

            # Create RCA if specified
            rca_data = capa_data.get('rca')
            if rca_data:
                rca = self._create_rca(rca_data, capa, user_map)
                result['rca_records'].append(rca)

                # Create Five Whys (OneToOne with RcaRecord)
                five_whys_data = rca_data.get('five_whys')
                if five_whys_data and rca_data.get('method') == 'FIVE_WHYS':
                    self._create_five_whys(five_whys_data, rca)

                # Create Fishbone (OneToOne with RcaRecord)
                fishbone_data = rca_data.get('fishbone')
                if fishbone_data and rca_data.get('method') == 'FISHBONE':
                    self._create_fishbone(fishbone_data, rca)

            # Create verification if specified
            ver_data = capa_data.get('verification')
            if ver_data:
                ver = self._create_verification(ver_data, capa, user_map)
                result['verifications'].append(ver)

            # Create tasks
            for task_data in capa_data.get('tasks', []):
                task = self._create_task(task_data, capa, user_map)
                result['tasks'].append(task)

            # Link quality reports if specified
            if capa_data.get('link_quality_reports'):
                self._link_quality_reports(capa)

        self.log(f"  Created {len(result['capas'])} CAPAs")
        self.log(f"  Created {len(result['rca_records'])} RCA records")
        self.log(f"  Created {len(result['tasks'])} CAPA tasks")

        return result

    def _create_capa(self, capa_data, user_map, step_map, wo_map):
        """Create a CAPA.

        Note: CAPA.initiated_date has auto_now_add=True, so we can only
        set it when creating (not updating). For demo purposes, we accept
        the current date for initiated_date.

        All fields are explicitly set - we do not rely on model defaults.
        """
        initiated_by = user_map.get(capa_data['initiated_by'])
        assigned_to = user_map.get(capa_data['assigned_to'])

        # Calculate verification timestamp for CLOSED status
        verified_by = None
        approved_by = None
        approved_at = None
        if capa_data.get('verification'):
            verified_by = user_map.get(capa_data['verification']['verified_by'])
        if capa_data['approval_status'] == 'APPROVED':
            # Use initiator as approver for demo
            approved_by = initiated_by
            approved_at = self.today - timedelta(days=capa_data.get('completed_days_ago', 0) + 1)

        # Build defaults with all fields explicitly set
        defaults = {
            'problem_statement': capa_data['problem_statement'],
            'status': capa_data['status'],  # Already a CapaStatus enum member
            'capa_type': capa_data['capa_type'],  # Already a CapaType enum member
            'severity': capa_data['severity'],  # Already a CapaSeverity enum member
            'initiated_by': initiated_by,
            'assigned_to': assigned_to,
            'immediate_action': capa_data.get('immediate_action', ''),
            # Approval workflow
            'approval_required': capa_data['approval_required'],  # Explicitly required
            'approval_status': capa_data['approval_status'],  # Explicitly required (NOT_REQUIRED, PENDING, etc.)
            'approved_by': approved_by,
            'approved_at': approved_at,
            'allow_self_verification': False,  # Explicit - no self-verification allowed
            # Set due_date - either from data or None
            'due_date': (self.today + timedelta(days=capa_data['due_days'])).date() if capa_data.get('due_days') else None,
            # Set completed_date - either from data or None
            'completed_date': (self.today - timedelta(days=capa_data['completed_days_ago'])).date() if capa_data.get('completed_days_ago') else None,
            # Verification (set after closure)
            'verified_by': verified_by,
            # Context links - set step, work_order, and part
            'step': step_map.get(capa_data['step']) if capa_data.get('step') else None,
            'work_order': wo_map.get(capa_data['work_order']) if capa_data.get('work_order') else None,
            'part': None,  # Explicit - linked via quality_reports M2M
        }

        capa, _ = CAPA.objects.update_or_create(
            tenant=self.tenant,
            capa_number=capa_data['capa_number'],
            defaults=defaults
        )

        return capa

    def _create_rca(self, rca_data, capa, user_map):
        """Create an RCA record for a CAPA.

        All fields are explicitly set - we do not rely on model defaults.
        """
        conducted_by = user_map.get(rca_data['conducted_by'])
        conducted_date = (self.today - timedelta(days=rca_data['conducted_days_ago'])).date()

        # Calculate verification timestamp if verified
        verification_status = rca_data['verification_status']  # Already an enum member
        is_verified = (verification_status == RootCauseVerificationStatus.VERIFIED)
        root_cause_verified_at = conducted_date + timedelta(days=2) if is_verified else None
        root_cause_verified_by = conducted_by if is_verified else None  # Use conductor as verifier for demo

        # review_status and verification_status are already enum members in rca_data
        rca, _ = RcaRecord.objects.update_or_create(
            capa=capa,
            defaults={
                'tenant': capa.tenant,
                'rca_method': rca_data['method'],
                'problem_description': rca_data['problem_description'],
                'root_cause_summary': rca_data['root_cause_summary'],
                'conducted_by': conducted_by,
                'conducted_date': conducted_date,
                'rca_review_status': rca_data['review_status'],  # Already an enum member
                'root_cause_verification_status': verification_status,
                # Verification tracking
                'root_cause_verified_at': root_cause_verified_at,
                'root_cause_verified_by': root_cause_verified_by,
                'self_verified': is_verified,  # In demo, conductor self-verifies
            }
        )

        return rca

    def _create_five_whys(self, five_whys_data, rca):
        """Create a Five Whys record (OneToOne with RcaRecord)."""
        FiveWhys.objects.update_or_create(
            rca_record=rca,
            defaults={
                'tenant': rca.tenant,
                'why_1_question': five_whys_data.get('why_1_question', ''),
                'why_1_answer': five_whys_data.get('why_1_answer', ''),
                'why_2_question': five_whys_data.get('why_2_question', ''),
                'why_2_answer': five_whys_data.get('why_2_answer', ''),
                'why_3_question': five_whys_data.get('why_3_question', ''),
                'why_3_answer': five_whys_data.get('why_3_answer', ''),
                'why_4_question': five_whys_data.get('why_4_question', ''),
                'why_4_answer': five_whys_data.get('why_4_answer', ''),
                'why_5_question': five_whys_data.get('why_5_question', ''),
                'why_5_answer': five_whys_data.get('why_5_answer', ''),
                'identified_root_cause': five_whys_data.get('identified_root_cause', ''),
            }
        )

    def _create_fishbone(self, fishbone_data, rca):
        """Create a Fishbone diagram (OneToOne with RcaRecord).

        Fishbone model fields:
        - rca_record: OneToOneField to RcaRecord
        - problem_statement: TextField
        - man_causes: JSONField (list of strings)
        - machine_causes: JSONField (list of strings)
        - material_causes: JSONField (list of strings)
        - method_causes: JSONField (list of strings)
        - measurement_causes: JSONField (list of strings)
        - environment_causes: JSONField (list of strings)
        - identified_root_cause: TextField (nullable)
        """
        Fishbone.objects.update_or_create(
            rca_record=rca,
            defaults={
                'tenant': rca.tenant,
                'problem_statement': fishbone_data.get('problem_statement', ''),
                'man_causes': fishbone_data.get('man_causes', []),
                'machine_causes': fishbone_data.get('machine_causes', []),
                'material_causes': fishbone_data.get('material_causes', []),
                'method_causes': fishbone_data.get('method_causes', []),
                'measurement_causes': fishbone_data.get('measurement_causes', []),
                'environment_causes': fishbone_data.get('environment_causes', []),
                'identified_root_cause': fishbone_data.get('identified_root_cause', ''),
            }
        )

    def _create_verification(self, ver_data, capa, user_map):
        """Create a CAPA verification record.

        All fields are explicitly set - we do not rely on model defaults.

        CapaVerification model fields:
        - verification_method: TextField (how effectiveness was verified)
        - verification_criteria: TextField (what defines success)
        - verification_date: DateField
        - verified_by: ForeignKey to User
        - effectiveness_result: CharField using EffectivenessResult enum
        - verification_notes: TextField
        """
        verified_by = user_map.get(ver_data['verified_by'])
        verified_date = (self.today - timedelta(days=ver_data['verified_days_ago'])).date()

        ver, _ = CapaVerification.objects.update_or_create(
            capa=capa,
            defaults={
                'tenant': capa.tenant,
                'verified_by': verified_by,
                'verification_date': verified_date,
                'verification_method': ver_data['verification_method'],  # Explicitly required
                'verification_criteria': ver_data['verification_criteria'],  # Explicitly required
                'effectiveness_result': ver_data['effectiveness_result'],  # Already an enum member
                'verification_notes': ver_data.get('verification_notes', ''),
            }
        )

        return ver

    def _create_task(self, task_data, capa, user_map):
        """Create a CAPA task with optional multi-person assignments.

        All fields are explicitly set - we do not rely on model defaults.
        """
        assignee = user_map.get(task_data['assignee'])

        # Get enum values directly from task_data (they are already enum members)
        status = task_data['status']  # Already a CapaTaskStatus enum member
        task_type = task_data['task_type']  # Already a CapaTaskType enum member
        completion_mode = task_data.get('completion_mode', CapaTaskCompletionMode.SINGLE_OWNER)  # Default to SINGLE_OWNER

        defaults = {
            'tenant': capa.tenant,
            'assigned_to': assignee,
            'status': status,
            'task_type': task_type,
            'completion_mode': completion_mode,
            # Set due_date - either from data or None
            'due_date': (self.today + timedelta(days=task_data['due_days'])).date() if task_data.get('due_days') else None,
        }

        # Set completed_date and completed_by for COMPLETED tasks
        if status == CapaTaskStatus.COMPLETED:
            defaults['completed_date'] = self.today.date() if hasattr(self.today, 'date') else self.today
            defaults['completed_by'] = assignee
        else:
            # Explicitly set to None for non-completed tasks
            defaults['completed_date'] = None
            defaults['completed_by'] = None

        task, _ = CapaTasks.objects.update_or_create(
            capa=capa,
            description=task_data['description'],
            defaults=defaults
        )

        # Create CapaTaskAssignee records for multi-person tasks
        if task_data.get('assignees'):
            self._create_task_assignees(task, task_data['assignees'], user_map)

        return task

    def _create_task_assignees(self, task, assignees_data, user_map):
        """Create CapaTaskAssignee records for multi-person task assignment.

        All fields are explicitly set - we do not rely on model defaults.
        """
        for assignee_data in assignees_data:
            user = user_map.get(assignee_data['user'])
            if not user:
                continue

            # Status is already a CapaTaskStatus enum member in assignees_data
            status = assignee_data['status']

            assignee, _ = CapaTaskAssignee.objects.update_or_create(
                tenant=self.tenant,
                task=task,
                user=user,
                defaults={
                    'status': status,
                    'completed_at': timezone.now() if status == CapaTaskStatus.COMPLETED else None,
                    'completion_notes': assignee_data.get('notes', '') if status == CapaTaskStatus.COMPLETED else '',
                }
            )

    def _link_quality_reports(self, capa):
        """Link quality reports from Great Lakes order to CAPA.

        QualityReports model fields:
        - status: CharField with choices PASS, FAIL, PENDING (not current_state)
        - part: ForeignKey to Parts (Parts.ERP_id is the field name)
        """
        # Get quality reports from INJ-0038-* parts that are failures
        qrs = QualityReports.objects.filter(
            tenant=self.tenant,
            part__ERP_id__startswith='INJ-0038',
            status='FAIL'
        )

        if qrs.exists():
            capa.quality_reports.add(*qrs)
