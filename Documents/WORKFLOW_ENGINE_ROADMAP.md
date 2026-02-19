# Workflow Engine - Phased Implementation Roadmap

**Last Updated:** January 16, 2026
**Status:** Phase 1-2 Complete, Phase 3 ~95% Complete
**Priority:** High (Customer Need)

---

## Overview

Build a general-purpose workflow engine, starting with remanufacturing branching support and evolving toward a full visual process designer. Each phase delivers standalone value while laying groundwork for the next.

**Customer Driver:** Remanufacturing workflows with inspection-based routing (pass/fail/grade decisions)

### Example: Remanufacturing with Rework Loop

```
Receive → Disassemble → Clean → Inspect ──[PASS]──→ Reassemble → Final QA → Ship
                                  │                                │
                                  │                            [FAIL]
                               [FAIL]                              │
                                  │                                ▼
                                  ▼                         Rework (max 2)
                             Rework (max 3) ◄───────────────────┘
                                  │
                             [max exceeded]
                                  │
                                  ▼
                           Scrap Decision ──→ Scrap Terminal
                                  │
                                  └──────────→ Return to Supplier Terminal
```

**Cycle control:** Each rework step has `max_visits`. After 3 inspection failures, part routes to scrap decision instead of endless loops.

---

## Current State Analysis

### Part Progression (mes_lite.py)
- Graph-based routing via `StepEdge` model
- Supports decision points (QA result, measurement, manual)
- Cycle limits with escalation paths
- Batched advancement for work orders
- `StepExecution` tracks part visits through steps

### Existing Workflow Patterns (qms.py, core.py)
- **State machine:** `transition_to()` with allowed_transitions map
- **Blockers:** `get_blocking_items()` for pre-conditions
- **Templates:** ApprovalTemplate → ApprovalRequest snapshot pattern
- **Signals:** Auto-trigger workflows on model events

### Key Insight
The approval system already has workflow concepts (states, transitions, blockers). The goal is to generalize this into a reusable engine.

---

## Phase 1: Process Definition Schema

**Goal:** Define the data model for branching workflows with decision points and cycle control.

### 1.1 Step Model Fields

**File:** `PartsTracker/Tracker/models/mes_lite.py`

The `Steps` model defines individual workflow nodes:

```python
class Steps(SecureModel):
    # ... existing fields (name, description, part_type) ...

    # Visual node type for flow editor
    STEP_TYPE_CHOICES = [
        ('start', 'Start'),
        ('task', 'Task'),
        ('decision', 'Decision'),
        ('rework', 'Rework'),
        ('timer', 'Timer/Wait'),
        ('terminal', 'Terminal'),
    ]
    step_type = models.CharField(max_length=20, choices=STEP_TYPE_CHOICES, default='task')

    # Decision point configuration
    is_decision_point = models.BooleanField(default=False)
    decision_type = models.CharField(max_length=20, choices=[
        ('qa_result', 'Based on QA Pass/Fail'),
        ('measurement', 'Based on Measurement Threshold'),
        ('manual', 'Manual Operator Selection'),
    ], blank=True)

    # Terminal step marker
    is_terminal = models.BooleanField(default=False)
    terminal_status = models.CharField(max_length=20, choices=[
        ('completed', 'Completed Successfully'),
        ('scrapped', 'Scrapped'),
        ('returned', 'Returned to Supplier'),
        ('rma', 'RMA'),
        ('hold', 'On Hold'),
    ], blank=True)

    # Cycle control (for rework loops)
    max_visits = models.PositiveIntegerField(null=True, blank=True)

    # Operator assignment on revisit
    revisit_assignment = models.CharField(max_length=20, choices=[
        ('any', 'Any Qualified Operator'),
        ('same', 'Same as Previous'),
        ('different', 'Different Operator'),
        ('role', 'Specific Role'),
    ], default='any')
    revisit_role = models.ForeignKey('auth.Group', null=True, blank=True, on_delete=models.SET_NULL)
```

### 1.2 StepEdge Model (Graph-Based Routing)

**Key Design Decision:** Instead of `next_step_default`/`next_step_alternate` FK fields on Steps, we use a separate `StepEdge` table. This enables:

- Steps can be reused across multiple process versions
- Each process version has its own edge configuration
- Clean separation of step behavior from process structure
- Better support for complex routing (multiple conditions per edge)

```python
class EdgeType(models.TextChoices):
    DEFAULT = 'default', 'Default/Pass'      # Normal flow or pass condition
    ALTERNATE = 'alternate', 'Alternate/Fail' # Fail condition or alternate path
    ESCALATION = 'escalation', 'Escalation'  # Max visits exceeded


class StepEdge(models.Model):
    """
    Directed edge between steps, scoped to a specific process version.

    This is the core of the DAG structure for workflow routing.
    """
    process = models.ForeignKey(Processes, on_delete=models.CASCADE, related_name='step_edges')
    from_step = models.ForeignKey(Steps, on_delete=models.CASCADE, related_name='outgoing_edges')
    to_step = models.ForeignKey(Steps, on_delete=models.CASCADE, related_name='incoming_edges')
    edge_type = models.CharField(max_length=20, choices=EdgeType.choices, default=EdgeType.DEFAULT)

    # Optional: measurement-based conditions on the edge itself
    condition_measurement = models.ForeignKey(MeasurementDefinition, null=True, blank=True, on_delete=models.SET_NULL)
    condition_operator = models.CharField(max_length=10, choices=[('gte', '>='), ('lte', '<='), ('eq', '=')], blank=True)
    condition_value = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    class Meta:
        unique_together = [('process', 'from_step', 'to_step', 'edge_type')]
```

### 1.3 StepExecution Model (Visit Tracking)

Tracks each part's visit to a step for cycle counting and analytics:

```python
class StepExecution(SecureModel):
    """Tracks a part's visit to a step - from entry to exit."""
    part = models.ForeignKey(Parts, on_delete=models.CASCADE, related_name='step_executions')
    step = models.ForeignKey(Steps, on_delete=models.PROTECT)
    visit_number = models.PositiveIntegerField()  # 1st, 2nd, 3rd time at this step

    # Entry (set when part enters step)
    entered_at = models.DateTimeField(auto_now_add=True)
    assigned_to = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    # Exit (set when part leaves step)
    exited_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    decision_result = models.CharField(max_length=20, blank=True)  # 'pass', 'fail', etc.

    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ], default='pending')

    @classmethod
    def get_visit_count(cls, part, step):
        """Get how many times a part has visited a step."""
        return cls.objects.filter(part=part, step=step).count()

    @classmethod
    def get_current_execution(cls, part):
        """Get the active execution for a part (not yet exited)."""
        return cls.objects.filter(part=part, exited_at__isnull=True).first()
```

### 1.4 Part Routing Logic

The `Parts` model includes methods for routing through the workflow:

```python
class Parts(SecureModel):
    # ... existing fields ...

    def _get_edge(self, from_step, edge_type):
        """Get a StepEdge for the current process context."""
        process = self.work_order.process if self.work_order else None
        if not process:
            return None
        edge = StepEdge.objects.filter(
            process=process, from_step=from_step, edge_type=edge_type
        ).first()
        return edge.to_step if edge else None

    def _check_cycle_limit(self, target_step):
        """Check if part has exceeded max visits. Returns escalation step if exceeded."""
        if target_step is None or target_step.max_visits is None:
            return target_step

        current_visits = StepExecution.get_visit_count(self, target_step)
        if current_visits >= target_step.max_visits:
            # Route to escalation edge instead
            return self._get_edge(target_step, EdgeType.ESCALATION)
        return target_step

    def get_next_step(self, decision_result=None):
        """
        Determine next step based on current step configuration.

        For decision points:
        - qa_result: Uses latest QualityReport pass/fail
        - measurement: Evaluates against edge conditions
        - manual: Requires explicit decision_result parameter

        Returns Steps instance or None if terminal.
        """
        current = self.step
        if not current or current.is_terminal:
            return None

        if current.is_decision_point:
            # Decision routing via StepEdge
            if decision_result in ('pass', 'default') or str(decision_result).upper() == 'PASS':
                return self._check_cycle_limit(self._get_edge(current, EdgeType.DEFAULT))
            else:
                return self._check_cycle_limit(self._get_edge(current, EdgeType.ALTERNATE))

        # Non-decision: follow default edge
        return self._check_cycle_limit(self._get_edge(current, EdgeType.DEFAULT))

    def increment_step(self, operator=None, decision_result=None):
        """
        Advance part to next step, creating StepExecution records.

        - Completes current StepExecution
        - Determines next step via get_next_step()
        - Creates new StepExecution for entering step
        - Handles terminal steps (sets part_status)
        """
        # ... implementation details ...
```

### Phase 1 Deliverables
- [x] Steps model with `step_type`, `is_decision_point`, `decision_type`, `is_terminal`
- [x] Steps model with cycle control (`max_visits`, `revisit_assignment`)
- [x] StepEdge model for graph-based routing (replaces inline FK approach)
- [x] StepExecution model for visit tracking
- [x] `get_next_step()` with routing logic using StepEdge
- [x] `increment_step()` creating StepExecution records
- [x] API accepts decision parameter
- [x] Migration with backwards-compatible defaults

---

## Phase 2: Process Approval & Duplication

**Goal:** Add approval workflow and copy functionality to Processes.

### Design Decision

Originally planned separate `ProcessTemplate` and `StepTemplate` models. After review, this is unnecessary because:

1. **SecureModel already provides versioning** - every change creates an immutable version
2. **Work Orders already link to Processes** - no need for separate "instance" concept
3. **Orders rarely deviate from standard** - when they do, just create a new Process

**Simplified approach:** Add a `status` field to control which processes can be used, plus a `duplicate()` method for copying.

### 2.1 Model Changes

```python
class ProcessStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'           # Editable, not available for production
    APPROVED = 'approved', 'Approved'  # Locked, available for work orders
    DEPRECATED = 'deprecated', 'Deprecated'  # Still works, but hidden from new orders


class Processes(SecureModel):
    # ... existing fields ...

    status = models.CharField(max_length=20, choices=ProcessStatus.choices, default=ProcessStatus.DRAFT)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    copied_from = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)

    @property
    def is_editable(self):
        return self.status == ProcessStatus.DRAFT

    def approve(self, user=None):
        """Lock process for production use."""
        # Validation, status change, timestamp

    def deprecate(self):
        """Mark as deprecated - still usable but hidden from new orders."""

    def duplicate(self, user=None, name_suffix=" (Copy)"):
        """Create a copy of this process with all steps and edges."""
```

### 2.2 Workflow

```
┌─────────┐    approve()    ┌──────────┐    deprecate()    ┌────────────┐
│  DRAFT  │ ──────────────► │ APPROVED │ ────────────────► │ DEPRECATED │
└─────────┘                 └──────────┘                   └────────────┘
     │                            │
     │ (editable)                 │ (used by work orders)
     │                            │
     │                            │ duplicate()
     │                            ▼
     │                      ┌─────────┐
     └──────────────────────│  DRAFT  │ (new copy)
                            └─────────┘
```

### Phase 2 Deliverables
- [x] Status field on Processes (DRAFT/APPROVED/DEPRECATED)
- [x] `approve()`, `deprecate()`, `duplicate()` methods
- [x] `copied_from` lineage tracking
- [x] API endpoints for status transitions
- [x] Migration to add status field
- [x] UI: Approve/Deprecate/Duplicate buttons
- [x] UI: Status badge on process list pages
- [x] UI: Filter by status in process selector

---

## Phase 3: Visual Process Designer

**Goal:** Full ReactFlow-based visual editor for creating and editing processes.

### 3.1 ReactFlow Editor Features

- [x] Drag-and-drop node palette (task, decision, rework, timer, terminal)
- [x] Click-to-connect nodes
- [x] Node property panel (name, type, config)
- [x] Decision node configuration (QA result, measurement, manual)
- [x] ELK auto-layout with layer constraints
- [x] Keyboard shortcuts (Delete, Escape)
- [x] Fit view button
- [x] Save/load to real API (fetches real processes, saves edge connections)
- [x] Validation (all paths lead to terminal, no orphans)
- [x] Edit mode lock (only DRAFT processes editable)

### 3.2 Custom Node Components

```typescript
const nodeTypes = {
  start: StartNode,        // Green, play icon
  task: TaskNode,          // Blue, rectangle
  decision: DecisionNode,  // Yellow, diamond shape
  rework: ReworkNode,      // Orange, with max visits indicator
  timer: TimerNode,        // Purple, with duration display
  terminal: TerminalNode,  // Red/Green based on status
};
```

### 3.3 Process Validation (Frontend)

```typescript
// src/lib/process-validation.ts
export type ValidationIssue = {
  type: 'error' | 'warning';
  message: string;
  nodeId?: string;
};

export function validateProcessFlow(nodes: Node[], edges: Edge[]): ValidationIssue[];
```

Validation rules:
- Must have exactly one start node
- Must have at least one terminal node
- Decision nodes must have both pass and fail connections
- All nodes must be reachable from start (warning)
- All paths should reach a terminal (warning)
- Rework nodes should have max_visits configured (warning)

### Phase 3 Deliverables
- [x] ReactFlow visual editor component
- [x] Custom node types with proper styling
- [x] Node property panel
- [x] ELK auto-layout
- [x] Wire to real Steps/StepEdge API
- [x] Save derives connections from edges, sends to API
- [x] Create new steps via visual editor
- [x] Process validation before approval
- [x] Edit mode lock for non-DRAFT processes
- [x] "Duplicate & Edit" flow for modifying approved processes
- [ ] Overlay modes (work order, part journey, bottleneck) wired to real StepExecution data

---

## Phase 4: Generalized Workflow Engine

**Goal:** Generalized execution engine that can power manufacturing, approvals, CAPA, and custom workflows.

**Context:** Phase 1-3 implemented workflow execution for manufacturing parts (`StepExecution` tracks parts moving through `Steps`). Phase 4 generalizes this so ANY object can move through a workflow.

### 4.1 Unified Execution Models

```python
class WorkflowInstance(SecureModel):
    """A running instance of any workflow."""
    process = models.ForeignKey(Processes, on_delete=models.PROTECT)

    # Generic foreign key - what this workflow is for
    content_type = models.ForeignKey(ContentType, null=True, on_delete=models.SET_NULL)
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey()

    status = models.CharField(max_length=20, choices=[
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ])

    context = models.JSONField(default=dict)  # Workflow variables
    started_by = models.ForeignKey(User, on_delete=models.PROTECT)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True)


class NodeExecution(SecureModel):
    """Execution state of a single node in a workflow instance."""
    instance = models.ForeignKey(WorkflowInstance, related_name='executions', on_delete=models.CASCADE)
    step = models.ForeignKey(Steps, on_delete=models.PROTECT)

    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('skipped', 'Skipped'),
        ('failed', 'Failed'),
    ])

    assigned_to = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    result = models.JSONField(default=dict)
    entered_at = models.DateTimeField(null=True)
    exited_at = models.DateTimeField(null=True)
```

### 4.2 Workflow Engine Service

```python
class WorkflowEngine:
    def start(self, process, content_object, user, context=None):
        """Start a new workflow instance for any object."""
        instance = WorkflowInstance.objects.create(
            process=process,
            content_object=content_object,
            context=context or {},
            started_by=user,
            status='running',
        )
        # Find and activate start node
        start_step = process.steps.filter(step_type='start').first()
        self._activate(instance, start_step)
        return instance

    def complete_task(self, execution, result, user):
        """Complete a task node and advance the workflow."""
        execution.status = 'completed'
        execution.result = result
        execution.exited_at = timezone.now()
        execution.save()

        # Update instance context
        instance = execution.instance
        instance.context[f'node_{execution.step.name}'] = result
        instance.save()

        # Advance to next node
        self._advance(instance, execution.step, result)

    def _advance(self, instance, from_step, result=None):
        """Move workflow forward based on step type and edges."""
        next_step = self._get_next_step(instance.process, from_step, result)
        if next_step:
            self._activate(instance, next_step)

    def _activate(self, instance, step):
        """Activate a step for execution."""
        execution = NodeExecution.objects.create(
            instance=instance,
            step=step,
            status='active',
            entered_at=timezone.now(),
        )

        if step.step_type == 'terminal':
            instance.status = 'completed'
            instance.completed_at = timezone.now()
            instance.save()
```

### 4.3 Use Cases

| Use Case | Content Object | Workflow |
|----------|----------------|----------|
| Manufacturing | Parts | Production process |
| CAPA | CAPA | Investigation → Action → Verification |
| Document Approval | Documents | Draft → Review → Approve |
| NCR | QualityReports | Identify → Investigate → Disposition |
| Engineering Change | (new model) | Propose → Review → Implement |

### 4.4 Migration Path

1. **Parts workflow** - Already working via `StepExecution`, optionally migrate to `WorkflowInstance`
2. **CAPA workflow** - Currently state machine in model, migrate to process definition
3. **Approval workflow** - Currently ApprovalTemplate/Request, migrate or integrate

### Phase 4 Deliverables
- [ ] WorkflowInstance and NodeExecution models
- [ ] WorkflowEngine service with start/complete/advance
- [ ] Automated action handlers (email, status update, webhook)
- [ ] Task inbox UI ("My Tasks" across all workflows)
- [ ] Workflow history/audit trail view
- [ ] CAPA workflow running on engine
- [ ] Document approval workflow running on engine
- [ ] Migration utilities for existing workflows

---

## Files to Modify/Create

### Phase 1 ✅ Complete
| File | Action | Status |
|------|--------|--------|
| `models/mes_lite.py` | Steps model with step_type, decision fields | ✅ Done |
| `models/mes_lite.py` | StepEdge model for graph routing | ✅ Done |
| `models/mes_lite.py` | StepExecution model | ✅ Done |
| `models/mes_lite.py` | `get_next_step()`, `increment_step()` | ✅ Done |
| `viewsets/mes_lite.py` | increment endpoint with decision param | ✅ Done |
| `serializers/mes_lite.py` | StepEdgeSerializer, StepExecutionSerializer | ✅ Done |

### Phase 2 ✅ Complete
| File | Action | Status |
|------|--------|--------|
| `models/mes_lite.py` | Status field, approve/deprecate/duplicate | ✅ Done |
| `viewsets/mes_lite.py` | API endpoints for status transitions | ✅ Done |
| UI | Status badges and filters | ✅ Done |

### Phase 3 ⏳ ~95% Complete
| File | Action | Status |
|------|--------|--------|
| `components/flow/*.tsx` | Custom node components | ✅ Done |
| `pages/ProcessFlowPage.tsx` | Visual editor with real API | ✅ Done |
| `lib/process-validation.ts` | Frontend validation | ✅ Done |
| `components/flow/validation-panel.tsx` | Validation UI | ✅ Done |
| Overlay modes | Real StepExecution data | ⏳ Remaining |

### Phase 4 🔲 Not Started
| File | Action |
|------|--------|
| `models/workflow.py` | WorkflowInstance, NodeExecution |
| `services/workflow_engine.py` | Execution engine |
| `viewsets/workflow.py` | Execution endpoints |
| `pages/MyTasksPage.tsx` | Unified task inbox |

---

## Implementation Order

1. **Phase 1** ✅ Complete - Process definition schema
2. **Phase 2** ✅ Complete - Process approval workflow
3. **Phase 3** ⏳ ~95% Complete - Visual editor
4. **Phase 4** 🔲 Not Started - Generalized workflow engine

**Current focus:** Phase 3 remaining item (overlay modes with real StepExecution data)

**Stop points:** Each phase is independently valuable. Can pause after any phase.

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing linear processes | Migration sets default edges from order, backwards compatible |
| Complex visual editor | Start with read-only view, add editing incrementally |
| Over-engineering | Phase 1-3 specific to manufacturing, Phase 4 only when needed |
| Performance with complex graphs | Limit nodes per process, use select_related |

---

## Success Criteria

### Phase 1 ✅ Complete
- [x] Steps model with branching fields (step_type, is_decision_point, is_terminal)
- [x] StepEdge model for graph-based routing
- [x] StepExecution model for visit tracking
- [x] Part routing logic (get_next_step, increment_step)

### Phase 2 ✅ Complete
- [x] Process status workflow (DRAFT → APPROVED → DEPRECATED)
- [x] Can duplicate a process for customization
- [x] Only APPROVED processes available for new work orders
- [x] Status badges/filters in list UI

### Phase 3 ⏳ ~95% Complete
- [x] Visual editor displays and edits real processes
- [x] Save persists edge connections to API
- [x] Visual editor creates NEW steps
- [x] Process validation before approval
- [x] Edit mode lock for non-DRAFT processes
- [ ] Overlay modes (work order, part journey) with real data

### Phase 4 🔲 Not Started
- [ ] WorkflowInstance/NodeExecution models
- [ ] WorkflowEngine service
- [ ] CAPA/Approval workflows running on engine
- [ ] Unified task inbox shows all pending tasks
