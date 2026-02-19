# Generic Workflow Engine Design

## Overview

This document defines the architecture for a **generic workflow engine** that can model any business process—manufacturing, quality, NPI, document control, HR, and beyond—using a unified process/step/execution pattern.

**Goal:** Transform the system from a "parts tracker" into a **configurable operations platform** where any business process can be defined, executed, and tracked with the same rigor.

**Target Markets:** Automotive (IATF 16949), Aerospace (AS9100), Medical Devices (ISO 13485), General Manufacturing

---

## Design Principles

1. **Process Agnostic**: Same engine runs manufacturing, CAPA, NPI, document approval
2. **Configuration over Code**: New workflows created via UI, not development
3. **Unified Audit Trail**: All workflows share the same tracking infrastructure
4. **Composable**: Workflows can trigger other workflows
5. **Backward Compatible**: Existing manufacturing processes continue to work
6. **Domain-Aware**: Support domain-specific features (measurements, sampling) without polluting generic model

---

## Current State

### What Exists (Manufacturing-Specific)

| Component | Location | Coupling |
|-----------|----------|----------|
| `Process` | mes_lite.py | Generic ✓ |
| `Steps` | mes_lite.py | Mostly generic |
| `ProcessStep` | mes_lite.py | Generic ✓ |
| `StepEdge` | mes_lite.py | Generic ✓ |
| `StepExecution` | mes_lite.py | **Hardcoded to Parts** |
| `Parts.increment_step()` | mes_lite.py | **Logic embedded in model** |
| `MeasurementDefinition` | mes_lite.py | Manufacturing-specific |
| `SamplingRule` | mes_standard.py | Manufacturing-specific |

### Current StepExecution Model

```python
class StepExecution(SecureModel):
    part = ForeignKey('Parts')  # ❌ Hardcoded subject
    step = ForeignKey(Steps)
    visit_number = PositiveIntegerField(default=1)
    entered_at = DateTimeField(auto_now_add=True)
    exited_at = DateTimeField(null=True)
    assigned_to = ForeignKey(User, null=True)
    completed_by = ForeignKey(User, null=True)
    status = CharField()  # pending, in_progress, completed
    decision_result = CharField()
    next_step = ForeignKey(Steps, null=True)
```

### Current Advancement Logic

```python
# Lives on Parts model - tightly coupled
class Parts(SecureModel):
    def increment_step(self, operator=None, decision_result=None):
        # 200+ lines of advancement logic
        # Hardcoded to Parts, WorkOrder, sampling, etc.
```

---

## Target Architecture

### Core Concepts

```
┌─────────────────────────────────────────────────────────────────┐
│                      WORKFLOW ENGINE                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ProcessTemplate          "APQP", "CAPA", "Manufacturing"       │
│       │                                                          │
│       ▼                                                          │
│  Process                  Instance for a tenant                  │
│       │                                                          │
│       ▼                                                          │
│  Steps                    Phases/operations in the process       │
│       │                                                          │
│       ├── StepRequirements    What must be done at this step    │
│       │                                                          │
│       └── StepEdges           Routing to next step(s)           │
│                                                                  │
│  ────────────────────────────────────────────────────────────── │
│                                                                  │
│  WorkflowInstance         A specific execution of a process     │
│       │                   (replaces WorkOrder concept)          │
│       │                                                          │
│       ▼                                                          │
│  WorkflowSubject          The thing moving through the process  │
│       │                   (Part, PartType, CAPA, Document...)   │
│       │                                                          │
│       ▼                                                          │
│  StepExecution            Subject at a specific step            │
│                                                                  │
│  ────────────────────────────────────────────────────────────── │
│                                                                  │
│  WorkflowEngine           Service that advances subjects        │
│                           Checks requirements, routes, triggers │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Model

### Process Classification

```python
class ProcessCategory(models.TextChoices):
    """High-level categorization of process types."""
    MANUFACTURING = 'manufacturing', 'Manufacturing'
    QUALITY = 'quality', 'Quality'
    NPI = 'npi', 'New Product Introduction'
    DOCUMENT = 'document', 'Document Control'
    EQUIPMENT = 'equipment', 'Equipment & Maintenance'
    SUPPLIER = 'supplier', 'Supplier Management'
    HR = 'hr', 'Human Resources'
    CUSTOMER = 'customer', 'Customer Management'


class Process(SecureModel):
    """
    A defined workflow that subjects move through.

    Can represent manufacturing processes, CAPA workflows, NPI phases, etc.
    """
    name = CharField(max_length=200)
    description = TextField(blank=True)

    # Classification
    category = CharField(
        max_length=50,
        choices=ProcessCategory.choices,
        default=ProcessCategory.MANUFACTURING
    )

    # What type of subject goes through this process?
    subject_type = ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        help_text="The model type that moves through this process (Parts, CAPA, Document, etc.)"
    )

    # Versioning & Status
    version = CharField(max_length=20, default='1.0')
    status = CharField(choices=ProcessStatus.choices, default=ProcessStatus.DRAFT)

    # Template reference (for cloning standard processes)
    template_source = CharField(
        max_length=50,
        blank=True,
        help_text="Template this was created from (e.g., 'APQP', 'CAPA_8D', 'ISO_DOC_CONTROL')"
    )

    class Meta:
        indexes = [
            models.Index(fields=['category', 'status']),
            models.Index(fields=['subject_type']),
        ]
```

### Steps (Mostly Unchanged)

```python
class Steps(SecureModel):
    """
    A single stage within a process.

    Steps are generic—domain-specific behavior comes from:
    - StepRequirements (what must be completed)
    - Domain-specific extensions (MeasurementDefinition for manufacturing)
    """
    name = CharField(max_length=200)
    description = TextField(blank=True)

    # Step behavior
    step_type = CharField(
        max_length=20,
        choices=StepType.choices,
        default=StepType.TASK
    )

    # Decision configuration
    is_decision_point = BooleanField(default=False)
    decision_type = CharField(max_length=50, blank=True)

    # Terminal configuration
    is_terminal = BooleanField(default=False)
    terminal_status = CharField(max_length=50, blank=True)

    # Execution settings (from Step Completion Design)
    requires_explicit_start = BooleanField(default=False)
    requires_operator_completion = BooleanField(default=True)
    requires_batch_completion = BooleanField(default=False)
    requires_qa_signoff = BooleanField(default=False)

    # Cycle limits
    max_visits = PositiveIntegerField(null=True, blank=True)

    # Time limits
    expected_duration = DurationField(null=True, blank=True)
    max_duration = DurationField(null=True, blank=True)
    escalate_on_overdue = BooleanField(default=False)
```

### Step Requirements (New)

```python
class RequirementType(models.TextChoices):
    """Types of requirements that can gate step completion."""
    DOCUMENT = 'document', 'Document Required'
    APPROVAL = 'approval', 'Approval Required'
    CHECKLIST = 'checklist', 'Checklist Completion'
    FORM = 'form', 'Form Submission'
    MEASUREMENT = 'measurement', 'Measurement Recording'
    SIGNATURE = 'signature', 'Electronic Signature'
    CHILD_WORKFLOW = 'child_workflow', 'Child Workflow Completion'
    CUSTOM = 'custom', 'Custom Validation'


class StepRequirement(SecureModel):
    """
    A requirement that must be satisfied to complete a step.

    Generic requirements work across all process types.
    Domain-specific requirements (measurements) link to domain models.
    """
    step = ForeignKey(Steps, on_delete=models.CASCADE, related_name='requirements')

    # Requirement definition
    requirement_type = CharField(max_length=50, choices=RequirementType.choices)
    name = CharField(max_length=200)
    description = TextField(blank=True)

    # Behavior
    is_mandatory = BooleanField(default=True)
    order = PositiveIntegerField(default=0)

    # Type-specific configuration (stored as JSON for flexibility)
    config = JSONField(default=dict)
    # Examples:
    # - document: {"document_type_id": 5, "min_count": 1}
    # - approval: {"template_id": 3}
    # - checklist: {"items": ["Item 1", "Item 2", "Item 3"]}
    # - form: {"schema": {...}, "ui_schema": {...}}
    # - measurement: {"measurement_definition_id": 12}
    # - child_workflow: {"process_id": 8, "count": 1}

    class Meta:
        ordering = ['step', 'order']
        indexes = [
            models.Index(fields=['step', 'requirement_type']),
        ]

    def is_satisfied(self, execution) -> bool:
        """
        Check if this requirement is satisfied for a given execution.

        Delegates to type-specific validators.
        """
        from .services.requirement_validators import get_validator
        validator = get_validator(self.requirement_type)
        return validator.is_satisfied(self, execution)


class StepRequirementCompletion(SecureModel):
    """
    Tracks completion of a requirement for a specific execution.
    """
    execution = ForeignKey('StepExecution', on_delete=models.CASCADE, related_name='requirement_completions')
    requirement = ForeignKey(StepRequirement, on_delete=models.CASCADE)

    # Completion state
    is_complete = BooleanField(default=False)
    completed_at = DateTimeField(null=True)
    completed_by = ForeignKey(User, null=True, on_delete=models.SET_NULL)

    # Evidence (type-specific)
    evidence = JSONField(default=dict)
    # Examples:
    # - document: {"document_ids": [45, 46]}
    # - approval: {"approval_request_id": 123}
    # - checklist: {"checked_items": [0, 1, 2]}
    # - form: {"submitted_data": {...}}
    # - measurement: {"measurement_ids": [789]}

    class Meta:
        unique_together = ['execution', 'requirement']
```

### Workflow Instance (Generalized WorkOrder)

```python
class WorkflowInstance(SecureModel):
    """
    A specific execution of a process.

    For manufacturing: equivalent to WorkOrder (batch of parts through process)
    For CAPA: a single CAPA going through the CAPA workflow
    For NPI: a part type going through APQP phases
    """
    process = ForeignKey(Process, on_delete=models.PROTECT, related_name='instances')

    # Human-readable identifier
    identifier = CharField(max_length=100)  # Auto-generated: WO-2024-001, CAPA-2024-031, etc.
    name = CharField(max_length=200, blank=True)

    # Status
    status = CharField(max_length=50, choices=WorkflowStatus.choices, default='pending')

    # Timing
    started_at = DateTimeField(null=True)
    completed_at = DateTimeField(null=True)
    due_date = DateField(null=True, blank=True)

    # Context - what triggered this workflow?
    triggered_by = ForeignKey(
        'StepExecution',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="If this workflow was triggered by another workflow's step"
    )

    # Parent workflow (for nested workflows)
    parent_instance = ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='child_instances'
    )

    # Ownership
    owner = ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='owned_workflows')

    # Additional context (flexible)
    context = JSONField(default=dict)
    # Examples:
    # - Manufacturing: {"erp_id": "WO-123", "quantity": 50}
    # - CAPA: {"source": "customer_complaint", "complaint_id": 456}
    # - NPI: {"customer_id": 78, "target_ppap_date": "2024-06-01"}

    class Meta:
        indexes = [
            models.Index(fields=['process', 'status']),
            models.Index(fields=['identifier']),
            models.Index(fields=['status', 'due_date']),
        ]


class WorkflowStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    IN_PROGRESS = 'in_progress', 'In Progress'
    ON_HOLD = 'on_hold', 'On Hold'
    COMPLETED = 'completed', 'Completed'
    CANCELLED = 'cancelled', 'Cancelled'
```

### Polymorphic Step Execution

```python
class StepExecution(SecureModel):
    """
    Tracks a subject's progress at a specific step.

    The subject is polymorphic—can be a Part, CAPA, Document, PartType, etc.
    """
    # The workflow this execution belongs to
    workflow_instance = ForeignKey(
        WorkflowInstance,
        on_delete=models.CASCADE,
        related_name='executions'
    )

    # The step being executed
    step = ForeignKey(Steps, on_delete=models.PROTECT)

    # Polymorphic subject - what is moving through the process
    subject_type = ForeignKey(ContentType, on_delete=models.PROTECT)
    subject_id = PositiveIntegerField()
    subject = GenericForeignKey('subject_type', 'subject_id')

    # Visit tracking (for loops/rework)
    visit_number = PositiveIntegerField(default=1)

    # Lifecycle timestamps
    entered_at = DateTimeField(auto_now_add=True)
    started_at = DateTimeField(null=True)  # When work actually began
    exited_at = DateTimeField(null=True)

    # Status
    status = CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('claimed', 'Claimed'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('skipped', 'Skipped'),
            ('cancelled', 'Cancelled'),
        ],
        default='pending'
    )

    # Assignment
    assigned_to = ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='assigned_executions')
    completed_by = ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='completed_executions')

    # Decision result (for decision points)
    decision_result = CharField(max_length=100, blank=True)

    # Routing
    next_step = ForeignKey(Steps, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    # Notes
    notes = TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['workflow_instance', 'step', 'status']),
            models.Index(fields=['subject_type', 'subject_id']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['status', 'entered_at']),
        ]

    @classmethod
    def get_current_execution(cls, subject, workflow_instance):
        """Get the active execution for a subject in a workflow."""
        content_type = ContentType.objects.get_for_model(subject)
        return cls.objects.filter(
            workflow_instance=workflow_instance,
            subject_type=content_type,
            subject_id=subject.pk,
            status__in=['pending', 'claimed', 'in_progress']
        ).order_by('-entered_at').first()
```

---

## Workflow Engine Service

### Core Engine

```python
# services/workflow_engine.py

class WorkflowEngine:
    """
    Central service for workflow execution.

    Handles:
    - Starting workflows
    - Advancing subjects through steps
    - Checking requirements
    - Triggering child workflows
    - Cascading completions
    """

    def start_workflow(
        self,
        process: Process,
        subjects: list,
        context: dict = None,
        owner: User = None,
        parent_execution: StepExecution = None
    ) -> WorkflowInstance:
        """
        Start a new workflow instance with the given subjects.

        Args:
            process: The process to execute
            subjects: List of model instances to move through the process
            context: Additional context (ERP ID, customer, etc.)
            owner: User who owns this workflow
            parent_execution: If triggered by another workflow

        Returns:
            The created WorkflowInstance
        """
        # Validate subjects match process.subject_type
        expected_type = process.subject_type
        for subject in subjects:
            actual_type = ContentType.objects.get_for_model(subject)
            if actual_type != expected_type:
                raise ValueError(
                    f"Process '{process.name}' expects {expected_type.model}, "
                    f"got {actual_type.model}"
                )

        # Create workflow instance
        instance = WorkflowInstance.objects.create(
            process=process,
            identifier=self._generate_identifier(process),
            status=WorkflowStatus.IN_PROGRESS,
            started_at=timezone.now(),
            owner=owner,
            triggered_by=parent_execution,
            context=context or {}
        )

        # Get first step
        first_step = self._get_first_step(process)

        # Create initial executions for all subjects
        for subject in subjects:
            self._create_execution(instance, subject, first_step)

        return instance

    def advance(
        self,
        execution: StepExecution,
        user: User,
        decision_result: str = None,
        force: bool = False
    ) -> str:
        """
        Advance a subject from current step to next step.

        Args:
            execution: The current step execution
            user: User performing the advancement
            decision_result: Result for decision points
            force: Skip requirement checks (supervisor override)

        Returns:
            'completed' | 'advanced' | 'waiting' | 'blocked'
        """
        step = execution.step

        # Check requirements unless forced
        if not force:
            unmet = self._get_unmet_requirements(execution)
            if unmet:
                return 'blocked', unmet

        # Determine next step
        next_step = self._get_next_step(execution, decision_result)

        # Complete current execution
        execution.status = 'completed'
        execution.exited_at = timezone.now()
        execution.completed_by = user
        execution.decision_result = decision_result or ''
        execution.next_step = next_step
        execution.save()

        # Handle terminal step
        if next_step is None:
            self._handle_terminal(execution)
            return 'completed'

        # Check batch waiting
        if step.requires_batch_completion:
            if not self._is_batch_ready(execution):
                return 'waiting'
            # Batch ready - advance all
            self._advance_batch(execution, next_step, user)
            return 'advanced'

        # Individual advancement
        self._create_execution(
            execution.workflow_instance,
            execution.subject,
            next_step
        )

        return 'advanced'

    def claim(self, execution: StepExecution, user: User) -> StepExecution:
        """Claim a pending execution."""
        if execution.status != 'pending':
            raise ValueError(f"Cannot claim execution in status '{execution.status}'")

        execution.status = 'claimed'
        execution.assigned_to = user
        execution.save()
        return execution

    def start(self, execution: StepExecution, user: User) -> StepExecution:
        """Start working on a claimed execution."""
        if execution.status not in ('pending', 'claimed'):
            raise ValueError(f"Cannot start execution in status '{execution.status}'")

        execution.status = 'in_progress'
        execution.started_at = timezone.now()
        if not execution.assigned_to:
            execution.assigned_to = user
        execution.save()
        return execution

    def release(self, execution: StepExecution, user: User, reason: str = '') -> StepExecution:
        """Release a claimed or in-progress execution back to the pool."""
        if execution.status not in ('claimed', 'in_progress'):
            raise ValueError(f"Cannot release execution in status '{execution.status}'")

        execution.status = 'pending'
        execution.assigned_to = None
        execution.started_at = None
        execution.notes = f"{execution.notes}\n[Released by {user}: {reason}]".strip()
        execution.save()
        return execution

    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================

    def _get_first_step(self, process: Process) -> Steps:
        """Get the first step in a process."""
        process_step = ProcessStep.objects.filter(
            process=process
        ).order_by('order').first()

        if not process_step:
            raise ValueError(f"Process '{process.name}' has no steps")

        return process_step.step

    def _get_next_step(self, execution: StepExecution, decision_result: str = None) -> Steps:
        """Determine the next step based on edges and decision result."""
        step = execution.step
        process = execution.workflow_instance.process

        # Check for explicit edges
        edges = StepEdge.objects.filter(
            process=process,
            from_step=step
        )

        if step.is_decision_point:
            # Route based on decision
            if decision_result in ('pass', 'approved', 'yes'):
                edge = edges.filter(edge_type=EdgeType.DEFAULT).first()
            elif decision_result in ('fail', 'rejected', 'no'):
                edge = edges.filter(edge_type=EdgeType.ALTERNATE).first()
            else:
                # Try to match custom decision result
                edge = edges.filter(condition=decision_result).first()
                if not edge:
                    edge = edges.filter(edge_type=EdgeType.DEFAULT).first()

            return edge.to_step if edge else None

        # Non-decision: follow default edge or process order
        default_edge = edges.filter(edge_type=EdgeType.DEFAULT).first()
        if default_edge:
            return default_edge.to_step

        # Fallback to ProcessStep ordering
        current_order = ProcessStep.objects.get(process=process, step=step).order
        next_process_step = ProcessStep.objects.filter(
            process=process,
            order__gt=current_order
        ).order_by('order').first()

        return next_process_step.step if next_process_step else None

    def _get_unmet_requirements(self, execution: StepExecution) -> list:
        """Get list of unmet requirements for an execution."""
        unmet = []
        for req in execution.step.requirements.filter(is_mandatory=True):
            if not req.is_satisfied(execution):
                unmet.append(req)
        return unmet

    def _create_execution(
        self,
        workflow_instance: WorkflowInstance,
        subject,
        step: Steps
    ) -> StepExecution:
        """Create a new execution for a subject at a step."""
        content_type = ContentType.objects.get_for_model(subject)

        # Calculate visit number
        visit_count = StepExecution.objects.filter(
            workflow_instance=workflow_instance,
            subject_type=content_type,
            subject_id=subject.pk,
            step=step
        ).count()

        return StepExecution.objects.create(
            workflow_instance=workflow_instance,
            step=step,
            subject_type=content_type,
            subject_id=subject.pk,
            visit_number=visit_count + 1,
            status='pending'
        )

    def _handle_terminal(self, execution: StepExecution):
        """Handle completion of a terminal step."""
        workflow_instance = execution.workflow_instance

        # Check if all subjects in this workflow are at terminal
        active_executions = StepExecution.objects.filter(
            workflow_instance=workflow_instance,
            status__in=['pending', 'claimed', 'in_progress']
        ).exists()

        if not active_executions:
            # All subjects complete - close workflow
            workflow_instance.status = WorkflowStatus.COMPLETED
            workflow_instance.completed_at = timezone.now()
            workflow_instance.save()

            # Trigger parent workflow if this was a child
            if workflow_instance.triggered_by:
                self._notify_parent_workflow(workflow_instance)

    def _is_batch_ready(self, execution: StepExecution) -> bool:
        """Check if all subjects at this step are ready to advance."""
        pending = StepExecution.objects.filter(
            workflow_instance=execution.workflow_instance,
            step=execution.step,
            status__in=['pending', 'claimed', 'in_progress']
        ).exclude(pk=execution.pk).exists()

        return not pending

    def _advance_batch(self, execution: StepExecution, next_step: Steps, user: User):
        """Advance all subjects at a step together."""
        completed_executions = StepExecution.objects.filter(
            workflow_instance=execution.workflow_instance,
            step=execution.step,
            status='completed'
        )

        for exec in completed_executions:
            self._create_execution(
                execution.workflow_instance,
                exec.subject,
                next_step
            )

    def _generate_identifier(self, process: Process) -> str:
        """Generate a unique identifier for a workflow instance."""
        prefix_map = {
            ProcessCategory.MANUFACTURING: 'WO',
            ProcessCategory.QUALITY: 'QA',
            ProcessCategory.NPI: 'NPI',
            ProcessCategory.DOCUMENT: 'DOC',
            ProcessCategory.EQUIPMENT: 'EQ',
            ProcessCategory.SUPPLIER: 'SUP',
            ProcessCategory.HR: 'HR',
            ProcessCategory.CUSTOMER: 'CUS',
        }
        prefix = prefix_map.get(process.category, 'WF')
        year = timezone.now().year

        # Get next sequence number
        last = WorkflowInstance.objects.filter(
            identifier__startswith=f"{prefix}-{year}-"
        ).order_by('-identifier').first()

        if last:
            last_num = int(last.identifier.split('-')[-1])
            next_num = last_num + 1
        else:
            next_num = 1

        return f"{prefix}-{year}-{next_num:04d}"

    def _notify_parent_workflow(self, child_instance: WorkflowInstance):
        """Notify parent workflow that child completed."""
        parent_execution = child_instance.triggered_by
        if not parent_execution:
            return

        # Check if parent step's child workflow requirement is now satisfied
        # This will be picked up by the requirement validator
        pass
```

---

## Requirement Validators

```python
# services/requirement_validators.py

class BaseRequirementValidator:
    """Base class for requirement validators."""

    def is_satisfied(self, requirement: StepRequirement, execution: StepExecution) -> bool:
        raise NotImplementedError


class DocumentRequirementValidator(BaseRequirementValidator):
    """Validates that required documents are attached."""

    def is_satisfied(self, requirement: StepRequirement, execution: StepExecution) -> bool:
        config = requirement.config
        required_type_id = config.get('document_type_id')
        min_count = config.get('min_count', 1)

        # Get documents attached to the subject
        subject = execution.subject
        if not hasattr(subject, 'documents'):
            return False

        if required_type_id:
            count = subject.documents.filter(
                document_type_id=required_type_id,
                archived=False
            ).count()
        else:
            count = subject.documents.filter(archived=False).count()

        return count >= min_count


class ApprovalRequirementValidator(BaseRequirementValidator):
    """Validates that required approvals are obtained."""

    def is_satisfied(self, requirement: StepRequirement, execution: StepExecution) -> bool:
        from Tracker.models import ApprovalRequest

        config = requirement.config
        template_id = config.get('template_id')

        # Check for approved ApprovalRequest linked to this execution
        approval = ApprovalRequest.objects.filter(
            content_type=execution.subject_type,
            object_id=execution.subject_id,
            status='APPROVED'
        )

        if template_id:
            approval = approval.filter(template_id=template_id)

        return approval.exists()


class ChecklistRequirementValidator(BaseRequirementValidator):
    """Validates that all checklist items are completed."""

    def is_satisfied(self, requirement: StepRequirement, execution: StepExecution) -> bool:
        config = requirement.config
        required_items = config.get('items', [])

        # Get completion record
        completion = execution.requirement_completions.filter(
            requirement=requirement
        ).first()

        if not completion:
            return False

        checked_items = completion.evidence.get('checked_items', [])
        return len(checked_items) == len(required_items)


class MeasurementRequirementValidator(BaseRequirementValidator):
    """Validates that required measurements are recorded."""

    def is_satisfied(self, requirement: StepRequirement, execution: StepExecution) -> bool:
        config = requirement.config
        definition_id = config.get('measurement_definition_id')

        if not definition_id:
            return True

        # Check for measurement linked to this execution
        from Tracker.models import StepExecutionMeasurement
        return StepExecutionMeasurement.objects.filter(
            execution=execution,
            definition_id=definition_id,
            value__isnull=False
        ).exists()


class ChildWorkflowRequirementValidator(BaseRequirementValidator):
    """Validates that required child workflows are completed."""

    def is_satisfied(self, requirement: StepRequirement, execution: StepExecution) -> bool:
        config = requirement.config
        required_process_id = config.get('process_id')
        required_count = config.get('count', 1)

        completed_children = WorkflowInstance.objects.filter(
            triggered_by=execution,
            process_id=required_process_id,
            status=WorkflowStatus.COMPLETED
        ).count()

        return completed_children >= required_count


# Registry
VALIDATORS = {
    RequirementType.DOCUMENT: DocumentRequirementValidator(),
    RequirementType.APPROVAL: ApprovalRequirementValidator(),
    RequirementType.CHECKLIST: ChecklistRequirementValidator(),
    RequirementType.MEASUREMENT: MeasurementRequirementValidator(),
    RequirementType.CHILD_WORKFLOW: ChildWorkflowRequirementValidator(),
}

def get_validator(requirement_type: str) -> BaseRequirementValidator:
    return VALIDATORS.get(requirement_type, BaseRequirementValidator())
```

---

## Domain-Specific Extensions

The workflow engine is generic, but domains can extend it:

### Manufacturing Extension

```python
# Manufacturing-specific subject behavior
class Parts(SecureModel):
    """Manufacturing parts - subject of manufacturing workflows."""

    # Link to current workflow position (convenience)
    current_execution = ForeignKey(
        StepExecution,
        null=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    # Manufacturing-specific fields
    part_status = CharField(choices=PartsStatus.choices)
    requires_sampling = BooleanField(default=False)
    # ... etc

    def advance_step(self, user, decision_result=None):
        """Convenience method - delegates to workflow engine."""
        from .services.workflow_engine import WorkflowEngine

        engine = WorkflowEngine()
        execution = self.current_execution

        if not execution:
            raise ValueError("Part is not in an active workflow")

        result = engine.advance(execution, user, decision_result)

        # Update convenience pointer
        new_execution = StepExecution.get_current_execution(
            self, execution.workflow_instance
        )
        self.current_execution = new_execution
        self.save(update_fields=['current_execution'])

        return result
```

### Quality Extension (CAPA)

```python
class CAPA(SecureModel):
    """Corrective and Preventive Action - subject of quality workflows."""

    capa_number = CharField(max_length=50)
    severity = CharField(choices=CapaSeverity.choices)

    # Link to workflow
    workflow_instance = ForeignKey(
        WorkflowInstance,
        null=True,
        on_delete=models.SET_NULL
    )

    def start_capa_workflow(self, user):
        """Start the CAPA workflow for this CAPA."""
        from .services.workflow_engine import WorkflowEngine

        process = Process.objects.get(
            template_source='CAPA_8D',
            tenant=self.tenant,
            status=ProcessStatus.APPROVED
        )

        engine = WorkflowEngine()
        instance = engine.start_workflow(
            process=process,
            subjects=[self],
            owner=user,
            context={'severity': self.severity}
        )

        self.workflow_instance = instance
        self.save(update_fields=['workflow_instance'])
        return instance
```

---

## Process Templates

Pre-built templates for common workflows:

```python
PROCESS_TEMPLATES = {
    'APQP': {
        'category': ProcessCategory.NPI,
        'subject_type': 'PartType',
        'steps': [
            {'name': 'Planning', 'requirements': [
                {'type': 'document', 'name': 'Project Charter'},
                {'type': 'document', 'name': 'Timing Plan'},
                {'type': 'approval', 'name': 'Phase Gate 1'},
            ]},
            {'name': 'Product Design', 'requirements': [
                {'type': 'document', 'name': 'DFMEA'},
                {'type': 'document', 'name': 'Design Review Minutes'},
                {'type': 'checklist', 'name': 'Design Verification', 'items': [...]},
                {'type': 'approval', 'name': 'Phase Gate 2'},
            ]},
            {'name': 'Process Design', 'requirements': [
                {'type': 'document', 'name': 'PFMEA'},
                {'type': 'document', 'name': 'Control Plan'},
                {'type': 'document', 'name': 'Process Flow Diagram'},
                {'type': 'approval', 'name': 'Phase Gate 3'},
            ]},
            {'name': 'Validation', 'requirements': [
                {'type': 'child_workflow', 'name': 'Pilot Run', 'process': 'Manufacturing'},
                {'type': 'document', 'name': 'MSA Report'},
                {'type': 'document', 'name': 'Capability Study'},
                {'type': 'document', 'name': 'PPAP Package'},
                {'type': 'approval', 'name': 'Customer PPAP Approval'},
            ]},
            {'name': 'Production', 'is_terminal': True},
        ]
    },

    'CAPA_8D': {
        'category': ProcessCategory.QUALITY,
        'subject_type': 'CAPA',
        'steps': [
            {'name': 'D1: Team Formation', 'requirements': [
                {'type': 'form', 'name': 'Team Members'},
            ]},
            {'name': 'D2: Problem Description', 'requirements': [
                {'type': 'form', 'name': 'Problem Statement'},
            ]},
            {'name': 'D3: Containment', 'requirements': [
                {'type': 'form', 'name': 'Containment Actions'},
                {'type': 'approval', 'name': 'Containment Approval'},
            ]},
            {'name': 'D4: Root Cause Analysis', 'requirements': [
                {'type': 'document', 'name': '5-Why Analysis'},
                {'type': 'document', 'name': 'Fishbone Diagram'},
            ]},
            {'name': 'D5: Corrective Actions', 'requirements': [
                {'type': 'form', 'name': 'Corrective Action Plan'},
                {'type': 'approval', 'name': 'CA Approval'},
            ]},
            {'name': 'D6: Implementation', 'requirements': [
                {'type': 'checklist', 'name': 'Implementation Tasks'},
                {'type': 'document', 'name': 'Evidence of Implementation'},
            ]},
            {'name': 'D7: Preventive Actions', 'requirements': [
                {'type': 'form', 'name': 'Preventive Measures'},
            ]},
            {'name': 'D8: Verification', 'is_decision_point': True, 'requirements': [
                {'type': 'document', 'name': 'Effectiveness Evidence'},
            ]},
            # Decision: Effective? Yes -> Close, No -> Back to D4
            {'name': 'Closure', 'is_terminal': True, 'requirements': [
                {'type': 'approval', 'name': 'Final Approval'},
            ]},
        ]
    },

    'DOCUMENT_APPROVAL': {
        'category': ProcessCategory.DOCUMENT,
        'subject_type': 'Document',
        'steps': [
            {'name': 'Draft', 'requirements': [
                {'type': 'document', 'name': 'Document Content'},
            ]},
            {'name': 'Review', 'requirements': [
                {'type': 'approval', 'name': 'Technical Review'},
            ]},
            {'name': 'Approve', 'requirements': [
                {'type': 'approval', 'name': 'Management Approval'},
                {'type': 'signature', 'name': 'Electronic Signature'},
            ]},
            {'name': 'Released', 'is_terminal': True},
        ]
    },
}
```

---

## Migration Strategy

### Phase 1: Add Generic Infrastructure (Non-Breaking)

1. Add `ProcessCategory` to Process
2. Add `StepRequirement` and `StepRequirementCompletion` models
3. Add `WorkflowInstance` model
4. Create `WorkflowEngine` service
5. Keep existing manufacturing code working

### Phase 2: Parallel Operation

1. Manufacturing continues using existing `Parts.increment_step()`
2. New workflow types (CAPA, NPI) use `WorkflowEngine`
3. Validate engine behavior with non-critical workflows

### Phase 3: Migrate Manufacturing

1. Create `WorkflowInstance` for each `WorkOrder`
2. Migrate `StepExecution` to use polymorphic subject
3. Update `Parts.increment_step()` to delegate to `WorkflowEngine`
4. Deprecate manufacturing-specific code paths

### Phase 4: Unified UI

1. Single "My Tasks" view across all workflow types
2. Unified process designer
3. Cross-workflow reporting

---

## API Endpoints

### Workflow Management

```
POST   /api/workflows/                    # Start a workflow
GET    /api/workflows/                    # List workflow instances
GET    /api/workflows/{id}/               # Get workflow details
GET    /api/workflows/{id}/executions/    # Get all executions in workflow
PATCH  /api/workflows/{id}/               # Update workflow (status, context)
```

### Execution Actions

```
POST   /api/executions/{id}/claim/        # Claim an execution
POST   /api/executions/{id}/start/        # Start working
POST   /api/executions/{id}/complete/     # Complete and advance
POST   /api/executions/{id}/release/      # Release back to pool

GET    /api/executions/{id}/requirements/ # Get requirement status
POST   /api/executions/{id}/requirements/{req_id}/complete/  # Mark requirement done
```

### My Tasks

```
GET    /api/my-tasks/                     # All assigned/pending tasks across workflows
GET    /api/my-tasks/?category=quality    # Filter by process category
GET    /api/my-tasks/?overdue=true        # Filter overdue items
```

---

## Summary

### What This Enables

| Capability | Description |
|------------|-------------|
| **Any Process** | Manufacturing, Quality, NPI, Documents, HR, Suppliers |
| **Unified Tracking** | One inbox, one audit trail, one reporting system |
| **Configuration** | New workflows via UI, not code |
| **Composition** | Workflows trigger child workflows |
| **Compliance** | Same rigor applied everywhere |
| **Integration** | One API pattern for all processes |

### Implementation Priority

| Phase | Focus |
|-------|-------|
| 1 | Core engine + StepRequirement model |
| 2 | CAPA workflow (prove the pattern) |
| 3 | NPI/APQP workflow |
| 4 | Migrate manufacturing to engine |
| 5 | Document workflows |
| 6 | Full UI integration |

### Key Files to Create

```
PartsTracker/Tracker/
├── models/
│   ├── workflow.py          # WorkflowInstance, StepRequirement, etc.
│   └── ... existing ...
├── services/
│   ├── workflow_engine.py   # Core WorkflowEngine class
│   └── requirement_validators.py
├── viewsets/
│   └── workflow.py          # API endpoints
└── templates/
    └── process_templates.py  # APQP, CAPA, etc. templates
```
