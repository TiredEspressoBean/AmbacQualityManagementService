# Step Completion System Design

## Overview

This document defines the completion semantics for manufacturing process steps in the Ambac Tracker MES/QMS system. It addresses how parts transition between steps, integrating with existing scheduling and labor tracking infrastructure.

**Target Markets:** General manufacturing, Automotive, Aerospace (AS9100)

---

## Current State

### Existing Infrastructure

| Component | Status | Purpose |
|-----------|--------|---------|
| **ScheduleSlot** | ✅ Partial | Production scheduling with status tracking |
| **StepExecution** | ✅ Partial | Part-step tracking with `claim()` action |
| **TimeEntry** | ✅ Complete | Labor tracking with all context fields |
| **WorkCenter** | ✅ Complete | Workstation grouping |
| **Equipment** | ✅ Complete | Individual machines with calibration |
| **Shift** | ✅ Complete | Work shift definitions |
| **PartsStatus** | ✅ Complete | Enum with PENDING, IN_PROGRESS, AWAITING_QA, READY_FOR_NEXT_STEP, etc. |
| **Parts** | ✅ Complete | Part tracking with `part_status`, `step`, `increment_step()` |

### Existing StepExecution Fields (mes_lite.py)

```python
# Already implemented - DO NOT re-add
part = ForeignKey('Parts')
step = ForeignKey(Steps)
visit_number = PositiveIntegerField(default=1)
entered_at = DateTimeField(auto_now_add=True)   # When part entered step
exited_at = DateTimeField(null=True)            # When part left step
assigned_to = ForeignKey(User, null=True)
completed_by = ForeignKey(User, null=True)
next_step = ForeignKey(Steps, null=True)
decision_result = CharField(max_length=50)
status = CharField(choices=['pending', 'in_progress', 'completed', 'skipped'])
```

### Existing Steps Fields (mes_lite.py)

```python
# Already implemented - relevant fields
step_type = CharField()  # 'task', 'start', 'decision', 'rework', 'timer', 'terminal'
is_decision_point = BooleanField()
decision_type = CharField()
is_terminal = BooleanField()
terminal_status = CharField()
max_visits = PositiveIntegerField(null=True)
requires_qa_signoff = BooleanField()
sampling_required = BooleanField()
min_sampling_rate = IntegerField()  # REMOVE - orphaned, see Sampling Integration section
```

### Current Gaps

| Gap | Impact |
|-----|--------|
| `claim()` always sets `in_progress` | Can't track "assigned but not started" |
| No `started_at` timestamp | Can't distinguish entered vs work started |
| No `complete()` action | Completion is implicit in `increment_step()` |
| No completion settings on Steps | Can't configure batch vs individual flow |
| No batch completion logic | Parts can't wait for batch synchronization |
| No `release()` action | Operators can't release work back to pool |
| Missing status choices | No 'claimed' or 'cancelled' status |
| ScheduleSlot missing operator assignment | Can't track who's assigned to slots |
| No sampling/QA check in `increment_step()` | Parts advance without QualityReport verification |
| Batch logic ignores `requires_batch_completion` | Uses `is_decision_point` instead of settings |
| `qa_result` defaults to FAIL | Missing QualityReport routes to fail path, not blocked |
| Incomplete terminal status mapping | Only 3 of 8 statuses mapped to PartsStatus |
| `can_advance_step` placeholder | Referenced but not implemented |
| `min_sampling_rate` orphaned | Field exists, validation never enforced |
| FPI auto-flag missing | First part not auto-designated for FPI |
| FPI check not wired | `get_fpi_status()` exists but not enforced in `increment_step()` |
| No `FPIRecord` model | FPI scope tracking not implemented |
| No FPI override/waive endpoints | Can't change FPI part or skip FPI |
| `is_mandatory` not enforced | Mandatory measurements don't block completion |
| No `StepExecutionMeasurement` model | Measurements tied to QualityReports (sampled only) |
| No measurement progress tracking | Can't see 3 of 5 measurements complete |
| No `StepOverride` model | No escape hatch when blocks occur |
| No override workflow | Can't request, approve, or track overrides |
| No hard block detection | Quarantine/regulatory holds not enforced |
| No `StepRollback` model | Can't move parts backward through process |
| No `VoidableModel` mixin | Records can't be voided, only deleted |
| No edit audit trail | Record edits not tracked |
| No quick undo | Can't reverse just-completed step |
| **Cascade Gaps** | |
| No WorkOrder auto-complete | All parts finish terminal step, WO stays IN_PROGRESS |
| No Order auto-complete | All WOs complete, Order stays IN_PROGRESS |
| No step completion notifications | No alerts on completion, escalation, batch ready |
| No outbound HubSpot sync | CRM unaware of production progress |
| No ScheduleSlot completion link | Scheduling system out of sync with production |

---

## Design Goals

1. **Explicit Lifecycle**: Claim → Start → Complete as separate actions
2. **Batch Flexibility**: Support synchronized batch and individual part flow
3. **Separate Labor Tracking**: TimeEntry remains independent, not auto-created
4. **Station Awareness**: Capture workstation when available, optional otherwise
5. **Backward Compatible**: Existing processes continue to work
6. **Regulatory Ready**: Audit trail suitable for AS9100

---

## Data Model Changes

### 1. StepExecution Model Additions

Fields to ADD (existing fields like `assigned_to`, `completed_by`, `decision_result` already exist):

```python
class StepExecution(SecureModel):
    # ... existing fields (part, step, visit_number, entered_at, exited_at,
    #     assigned_to, completed_by, next_step, decision_result, status) ...

    # STATUS - Update choices to add 'claimed' and 'cancelled'
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),         # Existing
            ('claimed', 'Claimed'),         # NEW - Assigned, not started
            ('in_progress', 'In Progress'), # Existing
            ('completed', 'Completed'),     # Existing
            ('skipped', 'Skipped'),         # Existing
            ('cancelled', 'Cancelled'),     # NEW - Work order cancelled
        ],
        default='pending'
    )

    # TIMING - Add explicit work timestamps (distinct from entered_at/exited_at)
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When operator began working (distinct from entered_at)"
    )
    """
    entered_at = when part arrived at step (auto)
    started_at = when operator began work (explicit)
    """

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When operator finished working (distinct from exited_at)"
    )
    """
    completed_at = when operator finished work (explicit)
    exited_at = when part left step (may differ if batch waiting)
    """

    # STATION - Optional workstation tracking (NEW)
    work_center = models.ForeignKey(
        'WorkCenter',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Workstation where work was performed"
    )

    equipment = models.ForeignKey(
        'Equipments',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Specific equipment used"
    )

    # ATTENTION FLAGS (NEW)
    needs_reassignment = models.BooleanField(
        default=False,
        help_text="Flagged for supervisor to reassign (e.g., operator unavailable)"
    )
```

**Note:** `assigned_to`, `completed_by`, and `decision_result` already exist in the model.

### 2. Steps Model Additions

```python
class Steps(SecureModel):
    # ... existing fields ...

    # === COMPLETION SETTINGS ===

    requires_operator_completion = models.BooleanField(
        default=True,
        help_text="Operator must explicitly complete (vs auto-advance)"
    )
    """
    When True: Operator clicks "Complete" to advance part(s)
    When False: Parts auto-advance (pass-through steps)

    Ignored when requires_qa_signoff=True (QA logic governs)
    """

    requires_batch_completion = models.BooleanField(
        default=True,
        help_text="All parts at step must be ready before any advance"
    )
    """
    When True: Parts marked 'ready' wait; batch advances when all ready
    When False: Each part advances immediately upon completion

    Only applicable when requires_operator_completion=True

    Use cases:
    - True: Assembly lines, synchronized operations, batch processing
    - False: Reman repair (variable times), individual flow
    """

    requires_explicit_start = models.BooleanField(
        default=False,
        help_text="Claim and Start are separate actions"
    )
    """
    When True: Operator must claim, then separately start
    When False: Claiming auto-starts the work

    Use cases:
    - True: Setup time needed, queue management, shift handoffs
    - False: Instant work (visual inspection, simple tasks)
    """

    def save(self, *args, **kwargs):
        # Auto-populate completion settings from step_type defaults on creation
        if self._state.adding:
            defaults = STEP_TYPE_DEFAULTS.get(self.step_type, {})
            for field, value in defaults.items():
                # Only apply default if field hasn't been explicitly set
                current = getattr(self, field)
                model_default = self._meta.get_field(field).default
                if current == model_default:
                    setattr(self, field, value)
        super().save(*args, **kwargs)


# Step type default values for completion settings
STEP_TYPE_DEFAULTS = {
    'task': {
        'requires_operator_completion': True,
        'requires_batch_completion': True,
        'requires_explicit_start': False,
    },
    'start': {
        'requires_operator_completion': False,
        'requires_batch_completion': False,
        'requires_explicit_start': False,
    },
    'decision': {
        'requires_operator_completion': False,
        'requires_batch_completion': False,
        'requires_explicit_start': False,
    },
    'rework': {
        'requires_operator_completion': True,
        'requires_batch_completion': False,  # Variable repair times
        'requires_explicit_start': False,
    },
    'timer': {
        'requires_operator_completion': True,
        'requires_batch_completion': True,
        'requires_explicit_start': False,
    },
    'terminal': {
        'requires_operator_completion': False,
        'requires_batch_completion': False,
        'requires_explicit_start': False,
    },
}
```

### 3. Step Type Defaults

Defaults are auto-populated on step creation based on `step_type`. Users can override in the process flow editor.

| Step Type | requires_operator_completion | requires_batch_completion | requires_explicit_start |
|-----------|------------------------------|---------------------------|------------------------|
| `task` | `True` | `True` | `False` |
| `start` | `False` | `False` | `False` |
| `decision` | `False` | `False` | `False` |
| `rework` | `True` | `False` | `False` |
| `timer` | `True` | `True` | `False` |
| `terminal` | `False` | `False` | `False` |

---

## StepExecution Lifecycle

### State Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│    Part enters step (StepExecution created)                             │
│                         │                                               │
│                         ▼                                               │
│                   ┌──────────┐ ◄───────────────────────────────────┐    │
│                   │ PENDING  │  No operator assigned               │    │
│                   └────┬─────┘                                     │    │
│                        │                                           │    │
│          ┌─────────────┴─────────────┐                             │    │
│          │                           │                             │    │
│          ▼                           ▼                             │    │
│   requires_explicit_start?     requires_explicit_start?            │    │
│        = True                       = False                        │    │
│          │                           │                             │    │
│          ▼                           │                             │    │
│   ┌──────────┐                       │                             │    │
│   │ CLAIMED  │ ◄─── claim() ─────────┤                             │    │
│   │          │  assigned_to = user   │                             │    │
│   └────┬─────┘                       │                             │    │
│        │    │                        │                             │    │
│        │    └── release() ───────────┼─────────────────────────────┘    │
│        │                             │                             │    │
│        │ start()                     │ claim() (auto-starts)       │    │
│        │ started_at = now()          │ assigned_to = user          │    │
│        │                             │ started_at = now()          │    │
│        ▼                             ▼                             │    │
│   ┌─────────────────────────────────────┐                          │    │
│   │          IN_PROGRESS                │  Work actively happening │    │
│   │                                     │                          │    │
│   └──────────────────┬──────────────────┘                          │    │
│                      │         │                                   │    │
│                      │         └── release() ──────────────────────┘    │
│                      │                                                  │
│                      │ complete()                                       │
│                      │ completed_at = now()                             │
│                      │ completed_by = user                              │
│                      ▼                                                  │
│   ┌─────────────────────────────────────┐                               │
│   │           COMPLETED                 │                               │
│   └──────────────────┬──────────────────┘                               │
│                      │                                                  │
│                      ▼                                                  │
│            Check advancement rules                                      │
│                      │                                                  │
│        ┌─────────────┴─────────────┐                                    │
│        │                           │                                    │
│        ▼                           ▼                                    │
│   requires_qa_signoff?      requires_batch_completion?                  │
│        = True                      = True                               │
│        │                           │                                    │
│        ▼                           ▼                                    │
│   AWAITING_QA              READY_FOR_NEXT_STEP                          │
│   (wait for reports)       (wait for batch)                             │
│        │                           │                                    │
│        │                           │ All parts ready?                   │
│        │                           ▼                                    │
│        │                     ┌───────────┐                              │
│        │                     │ YES → Batch advances to next step        │
│        │                     │ NO  → Wait for remaining parts           │
│        │                     └───────────┘                              │
│        │                           │                                    │
│        └───────────┬───────────────┘                                    │
│                    ▼                                                    │
│              NEXT STEP                                                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## API Endpoints

### StepExecution Actions

#### Claim Step Execution

```
POST /api/StepExecutions/{id}/claim/
```

**Behavior:**
- If `step.requires_explicit_start = True`: Sets status to `claimed`
- If `step.requires_explicit_start = False`: Sets status to `in_progress` and `started_at`

**Request:**
```json
{
    "work_center": 3,    // Optional: workstation ID
    "equipment": 12      // Optional: equipment ID
}
```

**Response:**
```json
{
    "id": 456,
    "status": "claimed",  // or "in_progress"
    "assigned_to": 42,
    "started_at": null,   // or timestamp if auto-started
    "part": { "id": 101, "serial": "SN-001" },
    "step": { "id": 5, "name": "Machining" }
}
```

#### Start Step Execution

```
POST /api/StepExecutions/{id}/start/
```

**Preconditions:**
- Status must be `claimed`
- Current user must be `assigned_to` (or have override permission)

**Request:**
```json
{
    "work_center": 3,    // Optional: can update station
    "equipment": 12,     // Optional: can update equipment
    "notes": "Starting with fresh tooling"
}
```

**Response:**
```json
{
    "id": 456,
    "status": "in_progress",
    "started_at": "2024-01-15T14:32:00Z",
    "assigned_to": 42
}
```

#### Release Step Execution

```
POST /api/StepExecutions/{id}/release/
```

Operator releases their own claimed or in-progress work back to the pool.

**Preconditions:**
- Status must be `claimed` or `in_progress`
- Current user must be `assigned_to`

**Request:**
```json
{
    "reason": "Shift ending, handing off"  // Optional
}
```

**Response:**
```json
{
    "id": 456,
    "status": "pending",
    "assigned_to": null,
    "released_by": 42,
    "released_at": "2024-01-15T16:00:00Z"
}
```

**Note:** Unlike `reassign()` which transfers to another operator, `release()` returns work to the unassigned pool. Any `started_at` timestamp is cleared.

---

#### Complete Step Execution

```
POST /api/StepExecutions/{id}/complete/
```

**Preconditions:**
- Status must be `claimed` or `in_progress` (if `claimed`, auto-backfills `started_at`)
- Current user must be `assigned_to` (or have `complete_stepexecution_any` permission)

**Request:**
```json
{
    "notes": "Completed within tolerance",
    "decision_result": "pass"  // Optional: for decision steps
}
```

**Response (batch mode, not all ready):**
```json
{
    "status": "marked_ready",
    "batch_progress": {
        "ready": 8,
        "pending": 2,
        "total": 10,
        "percent": 80
    }
}
```

**Response (batch complete or individual mode):**
```json
{
    "status": "advanced",
    "new_step": {
        "id": 6,
        "name": "Assembly"
    }
}
```

### Batch Operations

#### Complete All Parts at Step

```
POST /api/WorkOrders/{id}/complete-step/
```

Completes all active parts at a step and triggers batch advancement. Parts in `pending`, `claimed`, or `in_progress` status are marked complete.

**Request:**
```json
{
    "step_id": 5,
    "force": false  // If true, advances even if not all parts ready
}
```

#### Get Step Completion Status

```
GET /api/WorkOrders/{id}/step-status/{step_id}/
```

**Response:**
```json
{
    "step": {
        "id": 5,
        "name": "Machining",
        "requires_operator_completion": true,
        "requires_batch_completion": true,
        "requires_explicit_start": false
    },
    "completion": {
        "total": 10,
        "pending": 0,
        "claimed": 0,
        "in_progress": 2,
        "completed": 8,
        "is_batch_ready": false,
        "progress_percent": 80
    },
    "parts": [
        {"id": 101, "serial": "SN-001", "status": "completed"},
        {"id": 102, "serial": "SN-002", "status": "in_progress"},
        // ...
    ]
}
```

---

## Labor Tracking (Separate)

Labor tracking via TimeEntry is **independent** of step execution lifecycle. Operators explicitly clock in/out.

**Note:** The TimeEntry model already exists with all required fields (`entry_type`, `start_time`, `end_time`, `user`, `part`, `work_order`, `step`, `equipment`, `work_center`). Only the `clock_in()` and `clock_out()` actions need to be added.

### Clock In

```
POST /api/TimeEntries/clock_in/
```

**Request:**
```json
{
    "entry_type": "production",  // production/setup/rework/downtime/indirect
    "part": 101,                 // Optional
    "work_order": 42,            // Required
    "step": 5,                   // Optional
    "work_center": 3,            // Optional (from terminal or manual)
    "equipment": 12,             // Optional
    "notes": "Starting machining operation"
}
```

**Response:**
```json
{
    "id": 789,
    "entry_type": "production",
    "start_time": "2024-01-15T14:32:00Z",
    "end_time": null,
    "user": 42,
    "work_order": 42,
    "is_active": true
}
```

### Clock Out

```
POST /api/TimeEntries/{id}/clock_out/
```

**Request:**
```json
{
    "notes": "Completed run, switching to next job"
}
```

**Response:**
```json
{
    "id": 789,
    "start_time": "2024-01-15T14:32:00Z",
    "end_time": "2024-01-15T15:45:00Z",
    "duration_seconds": 4380,
    "duration_hours": 1.22,
    "is_active": false
}
```

### Get Active Time Entries

```
GET /api/TimeEntries/active/
```

Returns all open time entries for current user (clocked in, not clocked out).

### Labor Tracking Design Rationale

**Why separate from step execution:**

| Scenario | Step Execution | Time Entry |
|----------|---------------|------------|
| Multiple operators on one part | One `completed_by` | Multiple entries, one per operator |
| Setup then production | One execution | Two entries (setup, production) |
| Shift handoff mid-part | One execution continues | First operator clocks out, second clocks in |
| Break during work | Status stays `in_progress` | Clock out for break, clock in after |
| Rework | New visit_number | New entry with `entry_type=rework` |

---

## Station Capture

### Terminal-Aware (Preferred)

Terminals at fixed workstations auto-populate station info:

```javascript
// Terminal configuration (stored in browser/app)
const TERMINAL_CONFIG = {
    work_center_id: 3,
    equipment_id: 12,
    station_name: "CNC Mill #2"
};

// API calls include terminal context
POST /api/StepExecutions/{id}/start/
{
    "work_center": TERMINAL_CONFIG.work_center_id,
    "equipment": TERMINAL_CONFIG.equipment_id
}
```

### Optional (Mobile/Tablet)

Mobile operators can:
- Select station from dropdown
- Skip station selection (null values)
- Scan equipment barcode

```json
POST /api/StepExecutions/{id}/start/
{
    // work_center and equipment are optional
    "notes": "Working at auxiliary bench"
}
```

---

## Batch Completion Logic

### Core Algorithm

```python
def complete_step_execution(execution, operator, decision_result=None):
    """Complete a step execution and check advancement."""
    step = execution.step
    part = execution.part

    # Mark execution complete
    execution.status = 'completed'
    execution.completed_at = timezone.now()
    execution.completed_by = operator
    execution.decision_result = decision_result
    execution.save()

    # Check if QA governs
    if step.requires_qa_signoff:
        part.part_status = PartsStatus.AWAITING_QA
        part.save()
        return {"status": "awaiting_qa"}

    # Check if operator completion required
    if not step.requires_operator_completion:
        # Auto-advance step
        return advance_part(part, operator)

    # Check batch requirements
    if step.requires_batch_completion:
        part.part_status = PartsStatus.READY_FOR_NEXT_STEP
        part.save()
        return check_and_advance_batch(part.work_order, step, operator)
    else:
        # Individual advancement
        return advance_part(part, operator)


def check_and_advance_batch(work_order, step, operator):
    """Check if batch is ready and advance if so."""

    # Use select_for_update to prevent race conditions
    with transaction.atomic():
        parts_at_step = Parts.objects.select_for_update().filter(
            work_order=work_order,
            step=step
        ).exclude(
            part_status__in=[
                PartsStatus.SCRAPPED,
                PartsStatus.CANCELLED,
                PartsStatus.QUARANTINED
            ]
        )

        total = parts_at_step.count()
        ready = parts_at_step.filter(
            part_status=PartsStatus.READY_FOR_NEXT_STEP
        ).count()
        pending = total - ready

        if pending == 0 and total > 0:
            # All parts ready - advance batch
            for part in parts_at_step:
                advance_part(part, operator)

            return {
                "status": "batch_advanced",
                "parts_advanced": total
            }
        else:
            return {
                "status": "marked_ready",
                "batch_progress": {
                    "ready": ready,
                    "pending": pending,
                    "total": total,
                    "percent": (ready / total * 100) if total > 0 else 0
                }
            }
```

### Race Condition Prevention

The `select_for_update()` ensures that when two operators complete the last two parts simultaneously:

1. First transaction locks all parts at step
2. First transaction sees 1 pending, marks part ready, releases lock
3. Second transaction locks all parts at step
4. Second transaction sees 0 pending, advances entire batch

---

## UI Design

### Process Flow Editor - Step Settings

Add "Completion Settings" section to step editor panel:

```
┌─────────────────────────────────────────┐
│ Step Details                    [task]  │
├─────────────────────────────────────────┤
│ Name: [Machining              ]         │
│ Description: [                 ]        │
├─────────────────────────────────────────┤
│ ▼ Completion Settings                   │
│                                         │
│   Requires Operator Completion    [✓]   │
│   Operator must explicitly complete     │
│                                         │
│   ┌─────────────────────────────────┐   │
│   │ Batch Completion Required   [✓] │   │
│   │ All parts ready before advance  │   │
│   └─────────────────────────────────┘   │
│                                         │
│   ┌─────────────────────────────────┐   │
│   │ Explicit Start Required     [ ] │   │
│   │ Claim and Start are separate    │   │
│   └─────────────────────────────────┘   │
│                                         │
│   Note: Ignored when QA Signoff         │
│   is required.                          │
├─────────────────────────────────────────┤
│ ▼ QA Settings                           │
│   Requires QA Signoff             [ ]   │
│   Sampling Required               [ ]   │
│   ...                                   │
└─────────────────────────────────────────┘
```

### Work Order Execution - Batch Progress

```
┌─────────────────────────────────────────────────────────────────┐
│ Work Order: WO-2024-0142                                        │
│ Process: Fuel Injector Reman                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Current Step: Machining                     [Complete All ▼]   │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │  ████████████████████░░░░  8/10 Ready                       │ │
│ │                            80%                               │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ Part        │ Status        │ Operator    │ Action       │   │
│ ├──────────────────────────────────────────────────────────┤   │
│ │ SN-001      │ ✓ Ready       │ J. Smith    │              │   │
│ │ SN-002      │ ✓ Ready       │ J. Smith    │              │   │
│ │ SN-003      │ ⚙ In Progress │ M. Jones    │ [Complete]   │   │
│ │ SN-004      │ ○ Claimed     │ M. Jones    │ [Start]      │   │
│ │ SN-005      │ ○ Pending     │ —           │ [Claim]      │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Operator Workload View

```
┌─────────────────────────────────────────────────────────────────┐
│ My Work Queue                                    M. Jones       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ⚙ IN PROGRESS (2)                                              │
│ ├─ SN-003 @ Machining     WO-2024-0142    [Complete]           │
│ └─ SN-107 @ Assembly      WO-2024-0138    [Complete]           │
│                                                                 │
│ ○ CLAIMED (1)                                                   │
│ └─ SN-004 @ Machining     WO-2024-0142    [Start]              │
│                                                                 │
│ Available to Claim (5)                          [View Queue →] │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Audit Trail

### Step Execution Events

All state transitions are logged via Django's `auditlog`:

```json
{
    "model": "StepExecution",
    "object_id": 456,
    "action": "update",
    "changes": {
        "status": ["claimed", "in_progress"],
        "started_at": [null, "2024-01-15T14:32:00Z"]
    },
    "actor": {"id": 42, "username": "mjones"},
    "timestamp": "2024-01-15T14:32:00Z"
}
```

### StepTransitionLog (Existing)

Step transitions continue to be logged:

```python
StepTransitionLog.objects.create(
    part=part,
    step=new_step,
    operator=operator,
    timestamp=timezone.now()
)
```

### Batch Advancement Events

```json
{
    "event": "batch_advancement",
    "timestamp": "2024-01-15T15:45:00Z",
    "actor": {"id": 42, "username": "mjones"},
    "work_order": {"id": 15, "ERP_id": "WO-2024-0142"},
    "from_step": {"id": 5, "name": "Machining"},
    "to_step": {"id": 6, "name": "Assembly"},
    "parts_advanced": 10,
    "trigger": "batch_complete"
}
```

---

## Identity Verification

For aerospace (AS9100) compliance, sensitive actions can require identity confirmation:

### Lightweight E-Sign Pattern

```python
@action(detail=True, methods=['post'])
def complete(self, request, pk=None):
    execution = self.get_object()
    step = execution.step

    # Check if step requires identity verification
    if step.requires_identity_verification:
        password = request.data.get('password')
        if not request.user.check_password(password):
            return Response(
                {"detail": "Identity verification failed"},
                status=status.HTTP_401_UNAUTHORIZED
            )

    # Proceed with completion...
```

**Request with verification:**
```json
POST /api/StepExecutions/{id}/complete/
{
    "password": "******",
    "notes": "Final inspection complete"
}
```

### Future Enhancement

Add `requires_identity_verification` field to Steps model when needed.

---

## Migration Strategy

### Phase 1: Add Fields (Non-Breaking)

```python
# Migration
class Migration(migrations.Migration):
    operations = [
        # StepExecution fields
        migrations.AddField(
            model_name='stepexecution',
            name='started_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='stepexecution',
            name='completed_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='stepexecution',
            name='work_center',
            field=models.ForeignKey(null=True, blank=True, ...),
        ),
        migrations.AddField(
            model_name='stepexecution',
            name='equipment',
            field=models.ForeignKey(null=True, blank=True, ...),
        ),
        migrations.AddField(
            model_name='stepexecution',
            name='needs_reassignment',
            field=models.BooleanField(default=False),
        ),

        # Steps fields
        migrations.AddField(
            model_name='steps',
            name='requires_operator_completion',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='steps',
            name='requires_batch_completion',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='steps',
            name='requires_explicit_start',
            field=models.BooleanField(default=False),
        ),

        # Update status choices
        migrations.AlterField(
            model_name='stepexecution',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('claimed', 'Claimed'),
                    ('in_progress', 'In Progress'),
                    ('completed', 'Completed'),
                    ('skipped', 'Skipped'),
                    ('cancelled', 'Cancelled'),
                ],
                default='pending',
                max_length=20
            ),
        ),
    ]
```

### Phase 2: Update claim() Action

Modify existing `claim()` to respect `requires_explicit_start` and prevent race conditions:

```python
@action(detail=True, methods=['post'])
def claim(self, request, pk=None):
    # Use select_for_update to prevent concurrent claim race condition
    with transaction.atomic():
        execution = StepExecution.objects.select_for_update().get(pk=pk)
        step = execution.step

        # Validation
        if execution.status == 'completed':
            return Response({"detail": "Cannot claim completed execution"}, status=400)

        if execution.assigned_to and execution.assigned_to != request.user:
            return Response({"detail": "Already assigned to another operator"}, status=409)

        # Assign to user
        execution.assigned_to = request.user

        # Station capture (optional)
        if 'work_center' in request.data:
            execution.work_center_id = request.data['work_center']
        if 'equipment' in request.data:
            execution.equipment_id = request.data['equipment']

        # Check if auto-start
        if step.requires_explicit_start:
            execution.status = 'claimed'
        else:
            execution.status = 'in_progress'
            execution.started_at = timezone.now()

        execution.save()
        return Response(StepExecutionSerializer(execution).data)
```

### Phase 3: Add New Actions

Add `start()`, `complete()`, and `release()` actions to StepExecutionViewSet.

```python
@action(detail=True, methods=['post'])
def start(self, request, pk=None):
    """Explicitly start a claimed execution."""
    with transaction.atomic():
        execution = StepExecution.objects.select_for_update().get(pk=pk)

        if execution.status != 'claimed':
            return Response(
                {"detail": f"Cannot start execution in '{execution.status}' status"},
                status=400
            )

        if execution.assigned_to != request.user:
            # Check for override permission
            if not request.user.has_perm('tracker.start_stepexecution_any'):
                return Response(
                    {"detail": "Not assigned to this execution"},
                    status=403
                )

        # Update station if provided
        if 'work_center' in request.data:
            execution.work_center_id = request.data['work_center']
        if 'equipment' in request.data:
            execution.equipment_id = request.data['equipment']

        execution.status = 'in_progress'
        execution.started_at = timezone.now()
        execution.save()

        return Response(StepExecutionSerializer(execution).data)


@action(detail=True, methods=['post'])
def release(self, request, pk=None):
    """Release claimed or in-progress work back to the pool."""
    with transaction.atomic():
        execution = StepExecution.objects.select_for_update().get(pk=pk)

        if execution.status not in ('claimed', 'in_progress'):
            return Response(
                {"detail": f"Cannot release execution in '{execution.status}' status"},
                status=400
            )

        if execution.assigned_to != request.user:
            # Only the assigned operator can release their own work
            # Supervisors should use reassign() instead
            return Response(
                {"detail": "Can only release your own work"},
                status=403
            )

        # Reset to pending
        previous_status = execution.status
        execution.status = 'pending'
        execution.assigned_to = None
        execution.started_at = None  # Clear any start time

        # Log the release reason if provided
        reason = request.data.get('reason', '')

        execution.save()

        return Response({
            "id": execution.id,
            "status": "pending",
            "previous_status": previous_status,
            "released_by": request.user.id,
            "released_at": timezone.now().isoformat(),
            "reason": reason
        })


@action(detail=True, methods=['post'])
def complete(self, request, pk=None):
    """Complete a step execution and handle batch advancement."""
    with transaction.atomic():
        execution = StepExecution.objects.select_for_update().get(pk=pk)
        step = execution.step
        part = execution.part

        # Validation
        if execution.status == 'completed':
            return Response(
                {"detail": "Already completed"},
                status=400
            )

        if execution.status == 'pending':
            return Response(
                {"detail": "Must claim before completing"},
                status=400
            )

        # Permission check
        if execution.assigned_to != request.user:
            if not request.user.has_perm('tracker.complete_stepexecution_any'):
                return Response(
                    {"detail": "Not assigned to this execution"},
                    status=403
                )

        # Handle "complete without start" - auto-backfill start time
        if execution.status == 'claimed':
            execution.started_at = timezone.now()

        # Check max visits (block if this would exceed the limit)
        # max_visits=3 allows visits 1, 2, 3; blocks on visit 4+
        if step.max_visits and execution.visit_number > step.max_visits:
            if not request.user.has_perm('tracker.override_max_visits'):
                return Response({
                    "detail": "Maximum rework attempts exceeded",
                    "visit_number": execution.visit_number,
                    "max_visits": step.max_visits,
                    "requires": "tracker.override_max_visits permission"
                }, status=403)

        # Mark execution complete
        execution.status = 'completed'
        execution.completed_at = timezone.now()
        execution.completed_by = request.user
        execution.decision_result = request.data.get('decision_result')
        execution.save()

        # Determine advancement behavior
        if step.requires_qa_signoff:
            part.part_status = PartsStatus.AWAITING_QA
            part.save()
            return Response({"status": "awaiting_qa", "execution_id": execution.id})

        if not step.requires_operator_completion:
            # Auto-advance (pass-through step)
            result = advance_part(part, request.user)
            return Response({"status": "advanced", **result})

        if step.requires_batch_completion:
            # Mark ready, check batch
            part.part_status = PartsStatus.READY_FOR_NEXT_STEP
            part.save()
            result = check_and_advance_batch(part.work_order, step, request.user)
            return Response(result)
        else:
            # Individual advancement
            result = advance_part(part, request.user)
            return Response({"status": "advanced", **result})
```

### Phase 4: Add TimeEntry Actions

Add `clock_in()` and `clock_out()` actions to TimeEntryViewSet.

### Phase 5: Update UI

- Add completion settings to step editor panel
- Add batch progress indicators to work order views
- Add claim/start/complete buttons to operator interface

---

## Edge Cases

### 1. All Parts Quarantined / Dead Work Order

If all active parts at a step get quarantined/scrapped, trigger supervisor notification:

```python
def check_dead_work_order(work_order, step):
    """Check if work order has no active parts at step."""
    active_parts = Parts.objects.filter(
        work_order=work_order,
        step=step
    ).exclude(
        part_status__in=[QUARANTINED, SCRAPPED, CANCELLED]
    ).count()

    if active_parts == 0:
        # Notify supervisors
        notify_supervisors(
            event='dead_work_order',
            work_order=work_order,
            step=step,
            message=f"Work order {work_order.ERP_id} has no active parts at {step.name}"
        )
```

### 2. Part Added Mid-Process

New part added to work order starts at first step, independent of batch position. Does not join any existing batch waiting at later steps.

### 3. Supervisor Force Advance

```
POST /api/WorkOrders/{id}/complete-step/
{
    "step_id": 5,
    "force": true
}
```

Advances ready parts, leaves pending parts behind. Left-behind parts remain at step, available for:
- Individual completion (if `requires_batch_completion` changed to False)
- Next batch formation (if more parts arrive)
- Manual disposition

Requires `force_advance_batch` permission.

### 4. Rework Re-Entry

Part returning from rework creates new StepExecution with `visit_number += 1`. Batch context is current parts at step, not original batch. Rework steps default to `requires_batch_completion=False` for individual flow.

### 5. Config Change Mid-Process

Work orders are associated with a process version. Changing step settings on a process creates a new version; existing work orders continue with original settings.

### 6. Complete Without Start

If `complete()` is called on a `claimed` execution (operator never called `start()`):

```python
# In complete() action
if execution.status == 'claimed':
    # Auto-backfill start time
    execution.started_at = timezone.now()
    execution.status = 'in_progress'
    # Then proceed with completion logic
```

Rationale: Pragmatic. If they're completing, they did the work. Audit trail shows `started_at ≈ completed_at`.

### 7. Max Visits Exceeded

When a part exceeds `max_visits` on a step:

```python
def check_max_visits(execution, step):
    # max_visits=3 allows visits 1, 2, 3; blocks on visit 4+
    if step.max_visits and execution.visit_number > step.max_visits:
        raise MaxVisitsExceeded(
            f"Part has exceeded maximum rework attempts ({step.max_visits})",
            execution=execution,
            requires_permission='tracker.override_max_visits'
        )
```

Behavior: Block completion/advancement. Supervisor must either:
- Override with `tracker.override_max_visits` permission
- Disposition the part (scrap, quarantine, deviation)

### 8. Work Order Cancellation

When a work order is cancelled:

```python
def cancel_work_order(work_order, reason=''):
    with transaction.atomic():
        # Cancel all parts
        Parts.objects.filter(work_order=work_order).exclude(
            part_status__in=[SCRAPPED, SHIPPED, COMPLETED]
        ).update(part_status='cancelled')

        # Cancel active step executions
        StepExecution.objects.filter(
            part__work_order=work_order,
            status__in=['pending', 'claimed', 'in_progress']
        ).update(status='cancelled')

        # Close open time entries
        TimeEntry.objects.filter(
            work_order=work_order,
            end_time__isnull=True
        ).update(
            end_time=timezone.now(),
            notes=Concat('notes', Value(f'\n[Auto-closed: Work order cancelled - {reason}]'))
        )

        work_order.status = 'cancelled'
        work_order.save()
```

### 9. Operator Deactivated/Deleted

When a user account is deactivated or deleted:

```python
# StepExecution.assigned_to uses SET_NULL
assigned_to = models.ForeignKey(
    User,
    null=True,
    blank=True,
    on_delete=models.SET_NULL,
    related_name='step_executions'
)
```

Behavior:
- `assigned_to` becomes `None`
- Status remains unchanged (`claimed` or `in_progress`)
- Work appears in "unassigned work needing attention" queries
- Supervisor must reassign

### 10. Parallel Path Split (Decision Point)

When a decision step splits parts onto different paths:

```
         ┌─→ [Path A] ─→┐
[Split]──┤              ├──→ [Merge]
         └─→ [Path B] ─→┘
```

Each path becomes an independent batch:
- 10 parts split: 6 → A, 4 → B
- Path A batch = 6 parts
- Path B batch = 4 parts
- Each path's batch completion is independent

### 11. Parallel Path Merge

**Limitation:** Merge steps with `requires_batch_completion=True` wait for parts *currently at the step*, not for all paths to complete.

```
Path B (fast): 4 parts arrive at merge first
  → If batch completion enabled: 4/4 ready, advance immediately
  → Path A parts (arriving later) form a new batch

Path A (slow): 6 parts arrive at merge later
  → 6/6 ready, advance as second batch
```

**If you need "wait for entire work order to reassemble":**
- Set merge step to `requires_batch_completion=False` (individual flow at merge)
- Set the *next* step after merge to `requires_batch_completion=True`
- Parts accumulate at next step until all have passed through merge

### 12. Mark Unavailable with In-Progress Work

When marking an operator unavailable who has `in_progress` work:

```python
# In set_availability() - extend existing logic
if new_status == 'unavailable':
    # Release claimed (safe)
    released = StepExecution.objects.filter(
        assigned_to=user, status='claimed'
    ).update(status='pending', assigned_to=None)

    # Flag in_progress for attention (not safe to auto-release)
    flagged = StepExecution.objects.filter(
        assigned_to=user, status='in_progress'
    ).update(needs_reassignment=True)

    result['in_progress_flagged'] = flagged
```

In-progress work may have partial state (measurements, notes). Supervisor decides whether to:
- Reassign to another operator (work continues)
- Release to pool (another operator restarts)

---

## Operator Availability & Scheduling Integration

When an operator is unavailable (sick, emergency, vacation), their assigned work and scheduled slots need to be handled. This integrates with the scheduling system.

### 1. OperatorAvailability Model

```python
class OperatorAvailability(SecureModel):
    """Tracks operator availability status."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='availability'
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ('available', 'Available'),
            ('unavailable', 'Unavailable'),
            ('on_break', 'On Break'),
        ],
        default='available'
    )

    unavailable_reason = models.CharField(
        max_length=50,
        blank=True,
        help_text="sick, vacation, personal, training, etc."
    )

    unavailable_since = models.DateTimeField(null=True, blank=True)
    expected_return = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Operator Availabilities"
```

### 2. ScheduleSlot Model Additions

```python
class ScheduleSlot(SecureModel):
    # ... existing fields ...

    assigned_operator = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='schedule_slots',
        help_text="Primary operator assigned to this slot"
    )

    needs_reassignment = models.BooleanField(
        default=False,
        help_text="Flagged for supervisor to reassign"
    )
```

### 3. Set Availability Endpoint

Unified endpoint for managing operator availability with full scheduling integration:

```
POST /api/Users/{id}/set_availability/
```

**Request:**
```json
{
    "status": "unavailable",
    "reason": "sick",
    "expected_return": "2024-01-16T08:00:00Z",
    "release_claims": true,
    "handle_schedule_slots": "flag_for_reassignment"
}
```

**Options for `handle_schedule_slots`:**
- `"leave"` - Don't change schedule slots
- `"flag_for_reassignment"` - Mark slots as needing reassignment
- `"cancel"` - Cancel future scheduled slots

**Backend:**
```python
@action(detail=True, methods=['post'])
def set_availability(self, request, pk=None):
    user = self.get_object()
    new_status = request.data.get('status', 'unavailable')

    # Update or create availability record
    availability, _ = OperatorAvailability.objects.get_or_create(user=user)
    availability.status = new_status
    availability.unavailable_reason = request.data.get('reason', '')

    if new_status == 'unavailable':
        availability.unavailable_since = timezone.now()
        availability.expected_return = request.data.get('expected_return')
    else:
        availability.unavailable_since = None
        availability.expected_return = None

    availability.save()

    result = {
        "user_id": user.id,
        "status": new_status,
        "reason": availability.unavailable_reason,
    }

    # Handle work and scheduling only when marking unavailable
    if new_status == 'unavailable':

        # 1. Release claimed (not started) StepExecutions
        if request.data.get('release_claims', True):
            released = StepExecution.objects.filter(
                assigned_to=user,
                status='claimed'
            ).update(status='pending', assigned_to=None)
            result['claims_released'] = released

        # 2. Handle ScheduleSlots
        slot_action = request.data.get('handle_schedule_slots', 'flag_for_reassignment')
        future_slots = ScheduleSlot.objects.filter(
            assigned_operator=user,
            scheduled_date__gte=timezone.now().date(),
            status='scheduled'
        )

        if slot_action == 'cancel':
            cancelled = future_slots.update(status='cancelled')
            result['slots_cancelled'] = cancelled
        elif slot_action == 'flag_for_reassignment':
            flagged = future_slots.update(needs_reassignment=True)
            result['slots_flagged_for_reassignment'] = flagged
        # 'leave' = do nothing

        # 3. Close open TimeEntries
        from django.db.models.functions import Concat
        from django.db.models import Value

        closed = TimeEntry.objects.filter(
            user=user,
            end_time__isnull=True
        ).update(
            end_time=timezone.now(),
            notes=Concat('notes', Value(f'\n[Auto-closed: {new_status} - {availability.unavailable_reason}]'))
        )
        result['time_entries_closed'] = closed

    return Response(result)
```

**Response:**
```json
{
    "user_id": 42,
    "status": "unavailable",
    "reason": "sick",
    "claims_released": 3,
    "slots_flagged_for_reassignment": 2,
    "time_entries_closed": 1
}
```

### 4. Reassign Step Execution

Supervisor reassigns individual work items:

```
POST /api/StepExecutions/{id}/reassign/
```

**Request:**
```json
{
    "assigned_to": 45,
    "reason": "Original operator unavailable"
}
```

**Backend:**
```python
@action(detail=True, methods=['post'])
def reassign(self, request, pk=None):
    execution = self.get_object()
    new_operator_id = request.data.get('assigned_to')

    # Validate new operator is available
    try:
        new_operator = User.objects.get(id=new_operator_id)
        if hasattr(new_operator, 'availability') and new_operator.availability.status != 'available':
            return Response(
                {"detail": "Cannot reassign to unavailable operator"},
                status=status.HTTP_400_BAD_REQUEST
            )
    except User.DoesNotExist:
        return Response({"detail": "Operator not found"}, status=404)

    # If work was in_progress, reset to claimed
    if execution.status == 'in_progress':
        execution.status = 'claimed'
        execution.started_at = None

    execution.assigned_to = new_operator
    execution.save()

    return Response(StepExecutionSerializer(execution).data)
```

### 5. Release My Claims (Operator Self-Service)

Operators can release their own unclaimed work (e.g., end of shift):

```
POST /api/StepExecutions/release_my_claims/
```

**Backend:**
```python
@action(detail=False, methods=['post'])
def release_my_claims(self, request):
    """Release all claimed (not started) work back to pool."""
    released = StepExecution.objects.filter(
        assigned_to=request.user,
        status='claimed'
    ).update(status='pending', assigned_to=None)

    return Response({"released": released})
```

### 6. Scheduling Queries

```python
# Slots needing reassignment (supervisor dashboard)
ScheduleSlot.objects.filter(
    needs_reassignment=True,
    scheduled_date__gte=timezone.now().date()
).select_related('work_order', 'work_center', 'assigned_operator')

# Available operators for a shift
User.objects.filter(
    availability__status='available'
).exclude(
    schedule_slots__scheduled_date=target_date,
    schedule_slots__shift=target_shift,
    schedule_slots__status='scheduled'
)

# Operators currently unavailable
User.objects.filter(
    availability__status='unavailable'
).select_related('availability')
```

### 7. Supervisor Dashboard UI

```
┌─────────────────────────────────────────────────────────────────┐
│ Workforce Status                                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Operator Status                                                 │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ 🟢 John Smith      Available                               │  │
│ │ 🔴 Mary Jones      Unavailable (sick)                      │  │
│ │    └─ Expected return: Tomorrow 8:00 AM                    │  │
│ │    └─ 2 schedule slots need reassignment                   │  │
│ │ 🟢 Bob Wilson      Available                               │  │
│ │ 🟡 Jane Doe        On Break                                │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                 │
│ Slots Needing Reassignment                      [Reassign All]  │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ Tomorrow 8:00 AM │ CNC Mill    │ was: Mary │ [Assign ▼]   │  │
│ │ Tomorrow 2:00 PM │ Assembly    │ was: Mary │ [Assign ▼]   │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                 │
│ [+ Mark Operator Unavailable]                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

Mark Operator Unavailable Dialog:
┌─────────────────────────────────────────────────────────────────┐
│ Mark Operator Unavailable                              [×]      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Operator:        [Mary Jones           ▼]                       │
│ Reason:          [Sick                 ▼]                       │
│ Expected Return: [📅 Tomorrow 8:00 AM    ]                      │
│                                                                 │
│ Work Handling:                                                  │
│ [✓] Release claimed work (3 items) back to pool                 │
│                                                                 │
│ In-progress work (1 item):                                      │
│   ○ Leave assigned (supervisor will reassign manually)          │
│   ● Reassign to: [Bob Wilson ▼]                                 │
│                                                                 │
│ Future schedule slots (2 slots):                                │
│   ○ Leave as-is                                                 │
│   ● Flag for reassignment                                       │
│   ○ Cancel slots                                                │
│                                                                 │
│                              [Cancel]  [Mark Unavailable]       │
└─────────────────────────────────────────────────────────────────┘
```

### 8. Summary

| Action | Endpoint | Who | What |
|--------|----------|-----|------|
| Set availability | `POST /Users/{id}/set_availability/` | Supervisor | Mark available/unavailable with full integration |
| Release execution | `POST /StepExecutions/{id}/release/` | Operator | Release single claimed/in-progress work to pool |
| Release my claims | `POST /StepExecutions/release_my_claims/` | Operator | Bulk release all claimed work (end of shift) |
| Reassign execution | `POST /StepExecutions/{id}/reassign/` | Supervisor | Transfer specific work to another operator |

---

## Permissions

| Action | Permission |
|--------|------------|
| Claim step execution | `tracker.claim_stepexecution` |
| Start step execution | `tracker.start_stepexecution` |
| Start any (not assigned to self) | `tracker.start_stepexecution_any` |
| Complete step execution | `tracker.complete_stepexecution` |
| Complete any (not assigned to self) | `tracker.complete_stepexecution_any` |
| Release own execution | `tracker.release_stepexecution` |
| Reassign step execution | `tracker.reassign_stepexecution` |
| Release all own claims (bulk) | `tracker.release_own_claims` |
| Force advance batch | `tracker.force_advance_batch` |
| Override max visits limit | `tracker.override_max_visits` |
| Set operator availability | `tracker.set_user_availability` |
| Cancel work order | `tracker.cancel_workorder` |
| Clock in/out | `tracker.add_timeentry` |
| Configure step completion | `tracker.change_steps` |

---

## Future Consideration: Batch-Primary Interface

### Current vs Future Model

The current design tracks individual StepExecutions with claim/start/complete actions. This provides maximum flexibility but may be more granular than typical operator workflows require.

**Observed pattern:**
- Normal flow: Operators work at batch level ("complete all parts at this step")
- Exceptions: Individual part handling (rework, QA samples, quarantine)

| Interaction | Frequency | Current Design | Future Enhancement |
|-------------|-----------|----------------|-------------------|
| Batch completion | ~95% | `POST /WorkOrders/{id}/complete-step/` | Primary interface |
| Individual completion | ~5% | `POST /StepExecutions/{id}/complete/` | Exception interface |
| QA inspection | Per sampling | Individual StepExecution | Unchanged |
| Rework | Exception | Individual StepExecution | Unchanged |

### Future: StepBatchAssignment Model

When batch-level tracking becomes primary, add:

```python
class StepBatchAssignment(SecureModel):
    """Batch-level work assignment. Primary operator interface."""
    work_order = models.ForeignKey(WorkOrders, on_delete=models.CASCADE)
    step = models.ForeignKey(Steps, on_delete=models.CASCADE)

    # Assignment
    assigned_to = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    status = models.CharField(choices=[
        ('pending', 'Pending'),
        ('claimed', 'Claimed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ], default='pending')

    # Timing
    claimed_at = models.DateTimeField(null=True)
    started_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)

    # Station
    work_center = models.ForeignKey(WorkCenter, null=True, blank=True)
    equipment = models.ForeignKey(Equipments, null=True, blank=True)

    # Flags
    needs_reassignment = models.BooleanField(default=False)

    class Meta:
        unique_together = ['work_order', 'step']
```

### Future: Batch-Level Endpoints

```
PRIMARY (Normal Flow):
POST /api/WorkOrders/{id}/steps/{step_id}/claim/
POST /api/WorkOrders/{id}/steps/{step_id}/start/
POST /api/WorkOrders/{id}/steps/{step_id}/complete/

SECONDARY (Exceptions - unchanged):
POST /api/StepExecutions/{id}/claim/
POST /api/StepExecutions/{id}/complete/
```

### Future: TimeEntry Linking

Clarify TimeEntry links to Work Order + Step for normal flow:

```python
class TimeEntry(SecureModel):
    work_order = models.ForeignKey(WorkOrders)  # Required
    step = models.ForeignKey(Steps, null=True)  # Typical
    part = models.ForeignKey(Parts, null=True)  # Only for rework/exceptions
```

### Why Defer

1. Current StepExecution model works for MVP
2. Batch endpoints can wrap existing logic
3. StepBatchAssignment adds value when operator UX is built
4. Individual StepExecution records still needed for QA, traceability

### Migration Path

1. **Phase 1 (Current):** Individual StepExecutions, batch operations via `complete-step` endpoint
2. **Phase 2:** Add StepBatchAssignment model, batch endpoints
3. **Phase 3:** UI uses batch endpoints primarily, individual for exceptions

---

## Summary

This design extends the existing ScheduleSlot and StepExecution infrastructure with:

1. **Explicit lifecycle**: `pending` → `claimed` → `in_progress` → `completed` (with `release()` back to pending)
2. **Timing fields**: `started_at`, `completed_at` on StepExecution
3. **Completion settings**: Three flags on Steps with auto-populated step_type defaults
4. **Batch logic**: Parts can wait for batch or flow individually
5. **Separate labor**: TimeEntry independent with clock_in/clock_out
6. **Station awareness**: Optional work_center/equipment capture
7. **Operator availability**: Integrated with scheduling, handles work release and slot reassignment
8. **Race condition safety**: `select_for_update()` on claim, release, and batch completion
9. **Edge case coverage**: Max visits, work order cancellation, parallel paths, dead work order detection

The implementation is backward-compatible and builds on existing patterns.

---

## Sampling Integration

This section defines how sampling rules integrate with step completion and part advancement.

### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Remove `min_sampling_rate`** | ✅ Remove | Orphan field - validation never enforced. Sampling rules guarantee coverage. |
| **Remove validation methods** | ✅ Remove | `validate_sampling_coverage()` and `get_sampling_coverage_report()` never called |
| **Require SamplingRuleSet** | ✅ Enforce | If `sampling_required=True`, a SamplingRuleSet MUST exist for the step/part-type |
| **QA signoff mechanism** | QaApproval | Explicit QA inspector action, separate from QualityReports (inspection data) |

### Sampling Rule Types

The sampling engine supports these deterministic selection methods:

| Rule Type | Description | Coverage Guarantee |
|-----------|-------------|-------------------|
| `every_nth_part` | Every Nth part (e.g., every 5th) | ✅ Exactly 1/N of parts |
| `percentage` | First X% of parts by created_at | ✅ Exactly X% |
| `first_n_parts` | First N parts | ✅ Exactly N parts |
| `last_n_parts` | Last N parts | ✅ Exactly N parts |
| `exact_count` | Exactly N parts (no variance) | ✅ Exactly N parts |
| `random` | Deterministic pseudo-random (seeded) | ⚠️ ~X% with variance |

### Sampling → Step Completion Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   Part enters step                                                          │
│         │                                                                   │
│         ▼                                                                   │
│   ┌─────────────────────┐                                                   │
│   │ Evaluate sampling   │  SamplingFallbackApplier.evaluate()               │
│   │ rules for this      │                                                   │
│   │ step + part_type    │                                                   │
│   └──────────┬──────────┘                                                   │
│              │                                                              │
│       ┌──────┴──────┐                                                       │
│       │             │                                                       │
│       ▼             ▼                                                       │
│   requires_     requires_                                                   │
│   sampling      sampling                                                    │
│   = True        = False                                                     │
│       │             │                                                       │
│       │             │                                                       │
│       ▼             ▼                                                       │
│   Operator      Operator                                                    │
│   completes     completes                                                   │
│   work          work                                                        │
│       │             │                                                       │
│       ▼             │                                                       │
│   ┌─────────────┐   │                                                       │
│   │ QA creates  │   │                                                       │
│   │ Quality     │   │                                                       │
│   │ Report      │   │                                                       │
│   └──────┬──────┘   │                                                       │
│          │          │                                                       │
│          ▼          │                                                       │
│   ┌─────────────┐   │                                                       │
│   │ Report      │   │                                                       │
│   │ status?     │   │                                                       │
│   └──────┬──────┘   │                                                       │
│      ┌───┴───┐      │                                                       │
│      │       │      │                                                       │
│    PASS    FAIL     │                                                       │
│      │       │      │                                                       │
│      │       ▼      │                                                       │
│      │   QUARANTINE │                                                       │
│      │   (separate  │                                                       │
│      │    flow)     │                                                       │
│      │              │                                                       │
│      ▼              ▼                                                       │
│   ┌───────────────────────────────────────┐                                 │
│   │         can_advance_from_step()       │                                 │
│   └───────────────────┬───────────────────┘                                 │
│                       │                                                     │
│                       ▼                                                     │
│             Check step advancement rules                                    │
│             (batch completion, QA signoff, etc.)                            │
│                       │                                                     │
│                       ▼                                                     │
│                  NEXT STEP                                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Part Advancement Logic

```python
def can_advance_from_step(part, step):
    """
    Check if part can advance from step.
    Called before advancement in complete() action.
    """
    # 1. If part was flagged for sampling, must have QualityReport
    if part.requires_sampling:
        has_report = QualityReports.objects.filter(
            part=part,
            step=step
        ).exists()
        if not has_report:
            return False, "Sampling inspection required"

        # Check report passed (failed parts go to quarantine flow)
        report = QualityReports.objects.filter(part=part, step=step).latest('created_at')
        if report.status == 'FAIL':
            return False, "Part failed QA - requires disposition"

    # 2. If step requires QA signoff, check for QaApproval
    if step.requires_qa_signoff:
        has_approval = QaApproval.objects.filter(
            part=part,
            step=step,
            approved=True
        ).exists()
        if not has_approval:
            return False, "QA signoff required"

    return True, None
```

### QA Signoff vs Sampling

These are **separate** concepts:

| Concept | Model | Purpose | Who |
|---------|-------|---------|-----|
| **Sampling** | `QualityReports` | Inspection data for sampled parts | QA Inspector |
| **QA Signoff** | `QaApproval` | Explicit approval gate | QA Inspector |

- **Sampling**: Determined by rules, flags specific parts, creates QualityReports
- **QA Signoff**: Step-level gate, all parts at step require inspector approval before advancing

Both can be enabled on a step. When both enabled:
1. Sampled parts need QualityReports AND QaApproval
2. Non-sampled parts only need QaApproval

### Configuration Validation

When saving a Step with `sampling_required=True`:

```python
def clean(self):
    if self.sampling_required:
        # Check if any SamplingRuleSet exists for this step
        from Tracker.models import SamplingRuleSet
        has_rules = SamplingRuleSet.objects.filter(
            step=self,
            active=True,
            is_fallback=False
        ).exists()

        if not has_rules:
            raise ValidationError({
                'sampling_required':
                    'Sampling requires at least one active SamplingRuleSet for this step. '
                    'Configure rules in the step editor before enabling sampling.'
            })
```

**Note:** This validation is advisory at step creation (rules might be added later). The enforcement happens at runtime - if no rules match, part is not flagged for sampling and proceeds without inspection.

### Fields to Remove

Remove from `Steps` model (migration):

```python
# Remove - orphaned field
min_sampling_rate = models.FloatField(...)

# Remove - never called
def validate_sampling_coverage(self, work_order): ...
def get_sampling_coverage_report(self, work_order): ...
```

Remove from UI:
- `step-editor-panel.tsx`: Remove "Min Sampling Rate (%)" input
- Related serializers: Remove `min_sampling_rate` field

### Fallback Sampling

The sampling engine supports fallback rulesets triggered by consecutive failures:

```
Primary Rules: 10% sampling
    │
    │ 3 consecutive FAILs
    ▼
Fallback Rules: 50% sampling (triggered via SamplingTriggerState)
    │
    │ 5 consecutive PASSes
    ▼
Primary Rules: Back to 10%
```

This is already implemented in `SamplingFallbackApplier.evaluate()` and `QualityReports.save()._trigger_sampling_fallback()`.

### Integration Gaps to Address

| Gap | Status | Action |
|-----|--------|--------|
| `can_advance_from_step()` | ❌ Missing | Add to `complete()` action |
| QaApproval creation endpoint | ❌ Missing | Add `POST /api/QaApprovals/` |
| SamplingRuleSet validation | ⚠️ Partial | Add warning in step editor |
| `min_sampling_rate` removal | ❌ Pending | Migration to remove field |

---

## Decision Point & Routing Analysis

This section documents the current state of the decision/routing system and identifies gaps.

### Current Implementation

**Location:** `Parts.get_next_step()` and `Parts.increment_step()` in `mes_lite.py:2114-2420`

#### StepEdge Model (mes_lite.py:974-1041)

```python
class EdgeType(models.TextChoices):
    DEFAULT = 'default', 'Default/Pass'      # Normal flow or pass condition
    ALTERNATE = 'alternate', 'Alternate/Fail' # Fail condition or alternate path
    ESCALATION = 'escalation', 'Escalation'   # Max visits exceeded

class StepEdge(models.Model):
    process = ForeignKey(Processes)      # Scoped to process version
    from_step = ForeignKey(Steps)
    to_step = ForeignKey(Steps)
    edge_type = CharField(choices=EdgeType.choices)

    # Measurement-based routing (optional)
    condition_measurement = ForeignKey(MeasurementDefinition, null=True)
    condition_operator = CharField()  # 'gte', 'lte', 'eq'
    condition_value = DecimalField(null=True)
```

#### Decision Type Routing

| decision_type | How It Routes | Source |
|---------------|---------------|--------|
| `qa_result` | PASS → DEFAULT edge, FAIL → ALTERNATE edge | Latest `QualityReports.status` |
| `measurement` | Evaluates edge conditions vs measurement values | `MeasurementResult.actual_value` |
| `manual` | Requires explicit `decision_result` parameter | Operator input |

#### Cycle Limit Handling

`_check_cycle_limit()` (mes_lite.py:2072-2100):
- Counts visits via `StepExecution.get_visit_count(part, step)`
- If `visit_count >= max_visits` → routes to ESCALATION edge
- If no ESCALATION edge defined → returns None (triggers completion/error)

### Routing Gaps

#### 1. No Sampling/QA Check Before Advancement

**Problem:** `increment_step()` advances parts without checking if sampled parts have QualityReports or if QA signoff is complete.

**Current:** (mes_lite.py:2274-2275)
```python
# Determine next step using workflow logic
next_step = self.get_next_step(decision_result)
# ... immediately proceeds to advance
```

**Fix:** Add `can_advance_from_step()` check before calling `get_next_step()`:
```python
# Check advancement prerequisites
can_advance, reason = can_advance_from_step(self, self.step)
if not can_advance:
    raise AdvancementBlocked(reason)

next_step = self.get_next_step(decision_result)
```

#### 2. Batch Logic Ignores Completion Settings

**Problem:** Batch waiting uses `not is_decision_point` instead of `requires_batch_completion` flag.

**Current:** (mes_lite.py:2327)
```python
if self.work_order and not self.step.is_decision_point:
    # Mark this part ready and wait for others
```

**Fix:**
```python
if self.work_order and self.step.requires_batch_completion:
    # Mark this part ready and wait for others
```

#### 3. No `requires_operator_completion` Check

**Problem:** `increment_step()` doesn't check if step requires operator completion before auto-advancing.

**Fix:** Add check at start of `increment_step()`:
```python
if self.step.requires_operator_completion:
    # Should only be called from explicit complete() action
    # Not from auto-advance scenarios
    pass
```

Or restructure so `increment_step()` is only called from `complete()` action, and auto-advance steps call a separate `auto_advance()` method.

#### 4. qa_result Defaults to FAIL When No Report Exists

**Problem:** If no QualityReport exists, routing defaults to FAIL path instead of blocking.

**Current:** (mes_lite.py:2144)
```python
decision_result = latest_qr.status if latest_qr else 'FAIL'
```

**Fix:** Block advancement if qa_result decision requires a report:
```python
if latest_qr is None:
    raise DecisionDataMissing(
        f"QA result decision requires a QualityReport at step {current.name}"
    )
decision_result = latest_qr.status
```

#### 5. Incomplete Terminal Status Mapping

**Problem:** Only 3 of 8 terminal statuses are mapped to PartsStatus.

**Current:** (mes_lite.py:2281-2288)
```python
status_map = {
    'completed': PartsStatus.COMPLETED,
    'scrapped': PartsStatus.SCRAPPED,
    'returned': PartsStatus.CANCELLED,
}
```

**Fix:** Complete the mapping:
```python
TERMINAL_STATUS_MAP = {
    'completed': PartsStatus.COMPLETED,
    'shipped': PartsStatus.SHIPPED,
    'stock': PartsStatus.IN_STOCK,
    'scrapped': PartsStatus.SCRAPPED,
    'returned': PartsStatus.CANCELLED,
    'awaiting_pickup': PartsStatus.AWAITING_PICKUP,
    'core_banked': PartsStatus.CORE_BANKED,
    'rma_closed': PartsStatus.COMPLETED,  # or dedicated status
}
```

**Note:** May need to add missing PartsStatus enum values.

#### 6. `can_advance_step` Placeholder Not Implemented

**Problem:** Code references a method that doesn't exist.

**Current:** (mes_lite.py:2343-2346)
```python
if hasattr(self.step, 'can_advance_step') and not self.step.can_advance_step(
    work_order=self.work_order, step=self.step
):
    return "marked_ready"
```

**Fix:** Implement on Steps model or remove placeholder. This is where sampling/QA signoff batch-level checks would go:
```python
def can_advance_step(self, work_order):
    """Check if all parts at this step in work order can advance."""
    parts_at_step = Parts.objects.filter(work_order=work_order, step=self)

    for part in parts_at_step:
        can_advance, reason = can_advance_from_step(part, self)
        if not can_advance:
            return False, reason

    return True, None
```

#### 7. Decision Points Always Use Individual Advancement

**Problem:** Decision points skip batch waiting entirely, going straight to individual advancement.

**Current:** (mes_lite.py:2327, 2393)
```python
if self.work_order and not self.step.is_decision_point:
    # batch logic...
# ...
# Individual part advancement (decision points or no work order)
```

**Analysis:** This may be intentional - after a decision split, parts route to different paths so batch waiting doesn't make sense. However, the *next* step after the decision might want batch behavior.

**Recommendation:** Keep current behavior for decision points, but ensure the target steps handle batching correctly.

### Routing Gaps Summary

| Gap | Severity | Fix Location |
|-----|----------|--------------|
| No sampling/QA check | 🔴 High | `increment_step()` or new `complete()` action |
| Batch ignores settings | 🔴 High | Line 2327 |
| No operator completion check | 🟡 Medium | `increment_step()` |
| qa_result defaults to FAIL | 🟡 Medium | Line 2144 |
| Incomplete terminal map | 🟡 Medium | Lines 2281-2288 |
| `can_advance_step` placeholder | 🟡 Medium | Steps model |
| Decision skips batch | 🟢 Low | Likely intentional |

---

## First Piece Inspection (FPI)

First Piece Inspection verifies machine/process setup before full production. The first part is inspected thoroughly; if it passes, remaining parts can proceed.

### Design: Hybrid Auto-Flag with Override

**Approach:** Automatically flag the first part reaching a step, but allow operator to designate a different part if needed.

### Data Model

#### Existing Fields (already implemented)

```python
# Steps model
requires_first_piece_inspection = BooleanField(default=False)

# QualityReports model
is_first_piece = BooleanField(default=False)
```

#### New Fields

```python
# Parts model - track FPI designation
class Parts(SecureModel):
    # ... existing fields ...

    is_fpi_candidate = models.BooleanField(
        default=False,
        help_text="Auto-flagged as first piece inspection candidate"
    )
    """
    Set automatically when part is first to reach an FPI-required step.
    Operator can override by designating a different part.
    """

    fpi_override_reason = models.CharField(
        max_length=200,
        blank=True,
        help_text="Reason for overriding auto-flagged FPI part"
    )


# StepExecution model - track FPI status per execution
class StepExecution(SecureModel):
    # ... existing fields ...

    is_fpi = models.BooleanField(
        default=False,
        help_text="This execution is for First Piece Inspection"
    )

    fpi_status = models.CharField(
        max_length=20,
        choices=[
            ('not_applicable', 'Not Applicable'),
            ('pending', 'Pending Inspection'),
            ('passed', 'Passed'),
            ('failed', 'Failed'),
            ('waived', 'Waived'),
        ],
        default='not_applicable'
    )
```

#### FPI Scope Tracking

```python
class FPIRecord(SecureModel):
    """
    Tracks FPI status for a (work_order, step, scope) combination.
    Scope allows re-FPI requirements on shift/equipment changes.
    """
    work_order = models.ForeignKey(WorkOrders, on_delete=models.CASCADE)
    step = models.ForeignKey(Steps, on_delete=models.CASCADE)

    # Scope - what triggers a new FPI requirement
    part_type = models.ForeignKey(PartTypes, null=True, on_delete=models.CASCADE)
    equipment = models.ForeignKey(Equipments, null=True, on_delete=models.SET_NULL)
    shift = models.ForeignKey(Shift, null=True, on_delete=models.SET_NULL)

    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('in_progress', 'In Progress'),
            ('passed', 'Passed'),
            ('failed', 'Failed'),
            ('waived', 'Waived'),
        ],
        default='pending'
    )

    # The part used for FPI
    fpi_part = models.ForeignKey(Parts, null=True, on_delete=models.SET_NULL, related_name='fpi_records')
    quality_report = models.ForeignKey(QualityReports, null=True, on_delete=models.SET_NULL)

    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True)
    completed_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    # Override tracking
    was_auto_assigned = models.BooleanField(default=True)
    override_reason = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ['work_order', 'step', 'part_type', 'equipment', 'shift']
```

### FPI Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   Part enters FPI-required step                                             │
│         │                                                                   │
│         ▼                                                                   │
│   ┌─────────────────────────────────┐                                       │
│   │ Check: FPIRecord exists for     │                                       │
│   │ (work_order, step, scope)?      │                                       │
│   └──────────────┬──────────────────┘                                       │
│           ┌──────┴──────┐                                                   │
│           │             │                                                   │
│           ▼             ▼                                                   │
│        EXISTS       NOT EXISTS                                              │
│           │             │                                                   │
│           │             ▼                                                   │
│           │      ┌──────────────────────┐                                   │
│           │      │ Create FPIRecord     │                                   │
│           │      │ status='pending'     │                                   │
│           │      │ fpi_part=this_part   │  ◄── Auto-assign first part       │
│           │      │ was_auto_assigned=T  │                                   │
│           │      └──────────┬───────────┘                                   │
│           │                 │                                               │
│           ▼                 ▼                                               │
│   ┌─────────────────────────────────┐                                       │
│   │ FPIRecord.status?               │                                       │
│   └──────────────┬──────────────────┘                                       │
│       ┌──────────┼──────────┬──────────┐                                    │
│       │          │          │          │                                    │
│       ▼          ▼          ▼          ▼                                    │
│    PASSED     PENDING    FAILED     WAIVED                                  │
│       │          │          │          │                                    │
│       │          │          │          │                                    │
│       ▼          ▼          ▼          ▼                                    │
│   All parts   Is this    Block all   All parts                              │
│   can work    the FPI    parts.      can work                               │
│   normally    part?      Operator    normally                               │
│       │          │       must fix    (skip FPI)                             │
│       │      ┌───┴───┐   setup &        │                                   │
│       │      │       │   retry          │                                   │
│       │     YES     NO      │           │                                   │
│       │      │       │      │           │                                   │
│       │      ▼       ▼      │           │                                   │
│       │   Must do  BLOCKED  │           │                                   │
│       │   FPI      (wait    │           │                                   │
│       │   first    for FPI) │           │                                   │
│       │      │       │      │           │                                   │
│       └──────┴───────┴──────┴───────────┘                                   │
│                      │                                                      │
│                      ▼                                                      │
│              Continue step execution                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### API Endpoints

#### Get FPI Status

```
GET /api/WorkOrders/{id}/fpi-status/{step_id}/
```

**Response:**
```json
{
    "step_id": "uuid",
    "step_name": "CNC Machining",
    "requires_fpi": true,
    "fpi_records": [
        {
            "id": "uuid",
            "part_type": "Fuel Injector Body",
            "equipment": "CNC Mill #2",
            "shift": null,
            "status": "pending",
            "fpi_part": {
                "id": "uuid",
                "serial": "SN-001"
            },
            "was_auto_assigned": true,
            "blocked_parts_count": 9
        }
    ]
}
```

#### Override FPI Part

```
POST /api/FPIRecords/{id}/override/
```

Designate a different part for FPI (e.g., first part was damaged).

**Request:**
```json
{
    "new_fpi_part": "part-uuid",
    "reason": "Original part damaged during handling"
}
```

**Preconditions:**
- FPI status must be `pending` or `failed`
- New part must be at the same step
- User must have `override_fpi_part` permission

#### Submit FPI Result

```
POST /api/FPIRecords/{id}/submit/
```

Submit FPI inspection result (creates QualityReport with `is_first_piece=True`).

**Request:**
```json
{
    "status": "passed",
    "quality_report_id": "uuid",  // Or inline report data
    "notes": "All dimensions within tolerance"
}
```

#### Waive FPI

```
POST /api/FPIRecords/{id}/waive/
```

Skip FPI requirement (requires elevated permission).

**Request:**
```json
{
    "reason": "Repeat order, same setup as WO-2024-100",
    "reference_work_order": "uuid"  // Optional: reference to previous passing FPI
}
```

**Preconditions:**
- User must have `waive_fpi` permission
- Audit logged

### FPI Scope Options

Configure when a new FPI is required:

| Scope | When New FPI Required | Use Case |
|-------|----------------------|----------|
| **Work Order only** | Once per work order per step | Default, simplest |
| **+ Part Type** | Different part types need separate FPI | Mixed work orders |
| **+ Equipment** | Equipment change triggers re-FPI | Setup-sensitive |
| **+ Shift** | Shift change triggers re-FPI | Aerospace, strict |

```python
# Steps model - scope configuration
class Steps(SecureModel):
    # ... existing fields ...

    fpi_scope = models.CharField(
        max_length=20,
        choices=[
            ('work_order', 'Per Work Order'),
            ('part_type', 'Per Part Type'),
            ('equipment', 'Per Equipment'),
            ('shift', 'Per Shift'),
        ],
        default='work_order',
        help_text="What triggers a new FPI requirement"
    )
```

### Integration with Step Completion

Update `can_advance_from_step()` to check FPI:

```python
def can_advance_from_step(part, step):
    """Check if part can advance from step."""

    # ... existing checks (sampling, QA signoff) ...

    # FPI check
    if step.requires_first_piece_inspection:
        fpi_record = FPIRecord.objects.filter(
            work_order=part.work_order,
            step=step,
            # Apply scope filters based on step.fpi_scope
        ).first()

        if not fpi_record:
            return False, "FPI not initiated"

        if fpi_record.status == 'pending':
            if fpi_record.fpi_part_id == part.id:
                return False, "This part must complete FPI inspection first"
            else:
                return False, f"Waiting for FPI on part {fpi_record.fpi_part.serial}"

        if fpi_record.status == 'failed':
            return False, "FPI failed - setup adjustment required"

        # status is 'passed' or 'waived' - allow advancement

    return True, None
```

### Auto-Flag Logic

When part enters FPI-required step:

```python
def on_part_enters_step(part, step):
    """Called when part transitions to a new step."""

    if not step.requires_first_piece_inspection:
        return

    # Build scope filter
    scope_filter = {
        'work_order': part.work_order,
        'step': step,
    }
    if step.fpi_scope in ('part_type', 'equipment', 'shift'):
        scope_filter['part_type'] = part.part_type
    if step.fpi_scope in ('equipment', 'shift'):
        # Get from current StepExecution or terminal context
        scope_filter['equipment'] = get_current_equipment(part)
    if step.fpi_scope == 'shift':
        scope_filter['shift'] = get_current_shift()

    # Check if FPI record exists
    fpi_record, created = FPIRecord.objects.get_or_create(
        **scope_filter,
        defaults={
            'status': 'pending',
            'fpi_part': part,
            'was_auto_assigned': True,
        }
    )

    if created:
        # This part is auto-assigned as FPI candidate
        part.is_fpi_candidate = True
        part.save(update_fields=['is_fpi_candidate'])

        # Notify operator
        notify_operator(
            event='fpi_required',
            part=part,
            step=step,
            message=f"Part {part.serial} auto-designated for First Piece Inspection"
        )
```

### FPI Failure Handling

When FPI fails:

```python
def on_fpi_failed(fpi_record, quality_report):
    """Handle FPI failure."""

    fpi_record.status = 'failed'
    fpi_record.quality_report = quality_report
    fpi_record.save()

    # Options for the FPI part:
    # 1. Quarantine it (setup was wrong, part may be defective)
    # 2. Allow rework (if adjustable)
    # 3. Scrap (if unrecoverable)

    # For now, mark as needing attention
    fpi_record.fpi_part.part_status = PartsStatus.AWAITING_DISPOSITION
    fpi_record.fpi_part.save()

    # Notify supervisor
    notify_supervisors(
        event='fpi_failed',
        work_order=fpi_record.work_order,
        step=fpi_record.step,
        message=f"FPI failed at {fpi_record.step.name}. Setup adjustment required."
    )


def retry_fpi(fpi_record, new_part=None):
    """Retry FPI after setup adjustment."""

    if new_part:
        # Use different part for retry
        fpi_record.fpi_part = new_part
        fpi_record.was_auto_assigned = False

    fpi_record.status = 'pending'
    fpi_record.quality_report = None
    fpi_record.save()
```

### UI Indicators

#### Work Order / Step View

```
┌─────────────────────────────────────────────────────────────────┐
│ Step: CNC Machining                                             │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ ⚠️ FIRST PIECE INSPECTION REQUIRED                          │ │
│ │                                                             │ │
│ │ FPI Part: SN-001 (auto-assigned)      Status: PENDING       │ │
│ │                                                             │ │
│ │ [Override Part]  [Submit FPI Result]  [Waive FPI]           │ │
│ │                                                             │ │
│ │ 9 parts blocked, waiting for FPI to pass                    │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ Parts at Step:                                                  │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ SN-001  │ ★ FPI Part  │ [Do FPI Inspection]                │ │
│ │ SN-002  │ 🔒 Blocked  │ Waiting for FPI                     │ │
│ │ SN-003  │ 🔒 Blocked  │ Waiting for FPI                     │ │
│ │ ...     │             │                                     │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Permissions

| Permission | Description |
|------------|-------------|
| `do_fpi` | Submit FPI inspection results |
| `override_fpi_part` | Designate different part for FPI |
| `waive_fpi` | Skip FPI requirement (elevated) |
| `retry_fpi` | Retry FPI after failure |

### Edge Cases

| Scenario | Behavior |
|----------|----------|
| First part damaged before FPI | Operator uses override to designate different part |
| FPI fails, same part retried | Reset FPI status to pending, part stays at step |
| FPI fails, different part used | Override to new part, original part dispositioned |
| Equipment change mid-batch | If `fpi_scope=equipment`, new FPI required |
| Shift change mid-batch | If `fpi_scope=shift`, new FPI required |
| FPI waived | Audit logged, all parts proceed |
| Part type without FPI record | Auto-creates FPI record with first part |

### Gaps to Address

| Gap | Status | Action |
|-----|--------|--------|
| `FPIRecord` model | ❌ Missing | Add model |
| Auto-flag on step entry | ❌ Missing | Add signal/hook in `increment_step()` |
| FPI check in advancement | ⚠️ Exists in `can_advance_step()` | Wire up `can_advance_step()` |
| Override endpoint | ❌ Missing | Add API endpoint |
| Waive endpoint | ❌ Missing | Add API endpoint |
| UI indicators | ❌ Missing | Add to work order view |
| `fpi_scope` field | ❌ Missing | Add to Steps model |

---

## Measurement Completion

Mandatory measurements are data collection requirements that must be fulfilled before step completion. This is separate from sampling/QualityReports (quality verification).

### Design Principle

| Concept | Purpose | Model |
|---------|---------|-------|
| **Measurements** | Data collection (SPC, traceability) | `StepExecutionMeasurement` |
| **QualityReports** | Quality verification for sampled parts | `QualityReports` + `MeasurementResult` |

Both can coexist - a sampled part may have both mandatory step measurements AND a QualityReport with inspection measurements.

### Data Model

#### Existing Models (keep as-is)

```python
# MeasurementDefinition - defines what to measure
# StepMeasurementRequirement - links definitions to steps with is_mandatory flag
# MeasurementResult - values collected during QualityReports (sampling)
```

#### New Model: StepExecutionMeasurement

```python
class StepExecutionMeasurement(SecureModel):
    """
    Records a measurement taken during step execution.

    Separate from MeasurementResult (which is tied to QualityReports/sampling).
    This enables mandatory measurements on ALL parts, not just sampled ones.
    """
    execution = models.ForeignKey(
        StepExecution,
        on_delete=models.CASCADE,
        related_name='measurements'
    )
    definition = models.ForeignKey(
        MeasurementDefinition,
        on_delete=models.PROTECT
    )

    # Value (one of these based on definition.type)
    value_numeric = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        null=True,
        blank=True
    )
    value_pass_fail = models.CharField(
        max_length=4,
        choices=[('PASS', 'Pass'), ('FAIL', 'Fail')],
        null=True,
        blank=True
    )

    # Auto-calculated
    is_within_spec = models.BooleanField(default=False)

    # Tracking
    recorded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    recorded_at = models.DateTimeField(auto_now_add=True)

    # Equipment used for measurement (traceability)
    measurement_equipment = models.ForeignKey(
        'Equipments',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Measuring device used (caliper, CMM, etc.)"
    )

    # Notes
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['execution', 'definition']
        ordering = ['definition__stepmeasurementrequirement__sequence']

    def save(self, *args, **kwargs):
        self.is_within_spec = self._evaluate_spec()
        super().save(*args, **kwargs)

    def _evaluate_spec(self):
        """Check if value is within tolerance."""
        defn = self.definition

        # Get tolerance (use step override if exists)
        req = StepMeasurementRequirement.objects.filter(
            step=self.execution.step,
            measurement=defn
        ).first()

        upper = req.tolerance_upper_override if req and req.tolerance_upper_override else defn.upper_tol
        lower = req.tolerance_lower_override if req and req.tolerance_lower_override else defn.lower_tol

        if defn.type == 'NUMERIC':
            if self.value_numeric is None:
                return False
            nominal = float(defn.nominal or 0)
            value = float(self.value_numeric)
            return (nominal - float(lower or 0)) <= value <= (nominal + float(upper or 0))

        elif defn.type == 'PASS_FAIL':
            return self.value_pass_fail == 'PASS'

        return False
```

### Measurement Progress Tracking

Add to StepExecution:

```python
class StepExecution(SecureModel):
    # ... existing fields ...

    @property
    def measurement_progress(self):
        """Get measurement completion status."""
        step = self.step

        # Get mandatory measurements for this step
        mandatory = StepMeasurementRequirement.objects.filter(
            step=step,
            is_mandatory=True
        ).values_list('measurement_id', flat=True)

        if not mandatory:
            return {
                'required': 0,
                'completed': 0,
                'remaining': 0,
                'is_complete': True,
                'details': []
            }

        # Get completed measurements
        completed_ids = self.measurements.values_list('definition_id', flat=True)

        # Build details
        details = []
        for req in StepMeasurementRequirement.objects.filter(
            step=step
        ).select_related('measurement').order_by('sequence'):
            measurement = self.measurements.filter(definition=req.measurement).first()
            details.append({
                'definition_id': str(req.measurement_id),
                'label': req.measurement.label,
                'is_mandatory': req.is_mandatory,
                'sequence': req.sequence,
                'is_complete': measurement is not None,
                'is_within_spec': measurement.is_within_spec if measurement else None,
                'value': measurement.value_numeric or measurement.value_pass_fail if measurement else None,
            })

        required_count = len(mandatory)
        completed_count = len(set(mandatory) & set(completed_ids))

        return {
            'required': required_count,
            'completed': completed_count,
            'remaining': required_count - completed_count,
            'is_complete': completed_count >= required_count,
            'details': details
        }

    def get_missing_measurements(self):
        """Get list of mandatory measurements not yet recorded."""
        mandatory_ids = StepMeasurementRequirement.objects.filter(
            step=self.step,
            is_mandatory=True
        ).values_list('measurement_id', flat=True)

        completed_ids = self.measurements.values_list('definition_id', flat=True)
        missing_ids = set(mandatory_ids) - set(completed_ids)

        return MeasurementDefinition.objects.filter(id__in=missing_ids)
```

### Integration with Step Completion

Update `can_advance_from_step()`:

```python
def can_advance_from_step(part, step):
    """Check if part can advance from step."""

    # Get current execution
    execution = StepExecution.get_current_execution(part)
    if not execution:
        return False, "No active step execution"

    # ... existing checks (sampling, QA signoff, FPI) ...

    # Mandatory measurements check
    progress = execution.measurement_progress
    if not progress['is_complete']:
        missing = execution.get_missing_measurements()
        missing_names = ', '.join(m.label for m in missing[:3])
        if len(missing) > 3:
            missing_names += f' (+{len(missing) - 3} more)'
        return False, f"Missing mandatory measurements: {missing_names}"

    # Check all measurements within spec (optional - configurable)
    if step.block_on_measurement_failure:
        out_of_spec = execution.measurements.filter(is_within_spec=False)
        if out_of_spec.exists():
            return False, f"Measurement(s) out of spec: {out_of_spec.first().definition.label}"

    return True, None
```

### Step Configuration

Add to Steps model:

```python
class Steps(SecureModel):
    # ... existing fields ...

    block_on_measurement_failure = models.BooleanField(
        default=False,
        help_text="If True, part cannot advance if any measurement is out of spec"
    )
    """
    When enabled:
    - All measurements must be within spec to advance
    - Out-of-spec triggers disposition workflow (similar to QA fail)

    When disabled:
    - Measurements are recorded but don't block advancement
    - Out-of-spec is just data (for SPC trending)
    """
```

### API Endpoints

#### Get Step Measurements Required

```
GET /api/StepExecutions/{id}/measurements/
```

**Response:**
```json
{
    "execution_id": "uuid",
    "step_name": "Final Inspection",
    "progress": {
        "required": 5,
        "completed": 3,
        "remaining": 2,
        "is_complete": false
    },
    "measurements": [
        {
            "definition_id": "uuid",
            "label": "Outer Diameter",
            "type": "NUMERIC",
            "unit": "mm",
            "nominal": 25.4,
            "upper_tol": 0.05,
            "lower_tol": 0.05,
            "is_mandatory": true,
            "sequence": 1,
            "value": 25.42,
            "is_within_spec": true,
            "recorded_at": "2024-01-15T10:30:00Z",
            "recorded_by": "John Smith"
        },
        {
            "definition_id": "uuid",
            "label": "Surface Finish",
            "type": "NUMERIC",
            "unit": "Ra",
            "nominal": 1.6,
            "upper_tol": 0.4,
            "lower_tol": 0.4,
            "is_mandatory": true,
            "sequence": 2,
            "value": null,
            "is_within_spec": null,
            "recorded_at": null,
            "recorded_by": null
        }
    ]
}
```

#### Record Measurement

```
POST /api/StepExecutions/{id}/measurements/
```

**Request:**
```json
{
    "definition_id": "uuid",
    "value_numeric": 25.42,
    "measurement_equipment": "uuid",  // Optional
    "notes": "Measured at 3 points, averaged"  // Optional
}
```

**Validation:**
- Execution must be `in_progress` status
- Definition must be linked to execution's step
- User must have `record_measurement` permission

#### Record Multiple Measurements (Batch)

```
POST /api/StepExecutions/{id}/measurements/batch/
```

**Request:**
```json
{
    "measurements": [
        {"definition_id": "uuid1", "value_numeric": 25.42},
        {"definition_id": "uuid2", "value_pass_fail": "PASS"},
        {"definition_id": "uuid3", "value_numeric": 1.58}
    ],
    "measurement_equipment": "uuid"  // Applied to all
}
```

### Relationship with QualityReports

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   Part at Step                                                              │
│       │                                                                     │
│       ├──────────────────────────────────────────┐                          │
│       │                                          │                          │
│       ▼                                          ▼                          │
│   ┌─────────────────────────┐    ┌─────────────────────────────────────┐    │
│   │ MANDATORY MEASUREMENTS  │    │ SAMPLING / QA                       │    │
│   │ (All parts)             │    │ (Sampled parts only)                │    │
│   ├─────────────────────────┤    ├─────────────────────────────────────┤    │
│   │ StepExecutionMeasurement│    │ QualityReports + MeasurementResult  │    │
│   │                         │    │                                     │    │
│   │ • Production data       │    │ • Inspection data                   │    │
│   │ • SPC trending          │    │ • Pass/Fail determination           │    │
│   │ • Traceability          │    │ • Defect documentation              │    │
│   │                         │    │                                     │    │
│   │ Blocks: completion      │    │ Blocks: advancement (if required)   │    │
│   └─────────────────────────┘    └─────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Example scenario:**

A step has:
- 5 mandatory measurements (all parts must record)
- Sampling rule: 10% of parts

For a **non-sampled part**:
1. Record 5 mandatory measurements via `StepExecutionMeasurement`
2. Complete step

For a **sampled part**:
1. Record 5 mandatory measurements via `StepExecutionMeasurement`
2. QA inspector creates `QualityReport` with additional inspection measurements
3. If QA passes, complete step

### UI: Measurement Collection Form

```
┌─────────────────────────────────────────────────────────────────┐
│ Step: Final Machining                    Part: SN-0042         │
├─────────────────────────────────────────────────────────────────┤
│ Measurements (3 of 5 complete)           ████████░░░░ 60%      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 1. Outer Diameter *                      ✓ 25.42 mm            │
│    Spec: 25.40 ± 0.05 mm                 [Within spec]         │
│                                                                 │
│ 2. Length *                              ✓ 100.02 mm           │
│    Spec: 100.00 ± 0.10 mm                [Within spec]         │
│                                                                 │
│ 3. Surface Finish *                      ✓ 1.58 Ra             │
│    Spec: 1.60 ± 0.40 Ra                  [Within spec]         │
│                                                                 │
│ 4. Thread Depth *                        [ Enter value ]       │
│    Spec: 12.00 ± 0.05 mm                 [Required]            │
│                                                                 │
│ 5. Hardness *                            [ Enter value ]       │
│    Spec: 58-62 HRC                       [Required]            │
│                                                                 │
│ 6. Visual Inspection                     ○ Pass  ○ Fail        │
│    (Optional)                                                   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ Measuring Equipment: [Select caliper/CMM...           ▼]       │
├─────────────────────────────────────────────────────────────────┤
│              [Save Progress]        [Complete Step]            │
│                                     (disabled - 2 required)    │
└─────────────────────────────────────────────────────────────────┘

* = Mandatory
```

### Permissions

| Permission | Description |
|------------|-------------|
| `record_measurement` | Record measurements during step execution |
| `edit_measurement` | Edit previously recorded measurements |
| `override_measurement_block` | Advance despite out-of-spec measurements |

### Edge Cases

| Scenario | Behavior |
|----------|----------|
| Measurement out of spec | Recorded, flagged; blocks if `block_on_measurement_failure` |
| Measurement equipment not calibrated | Warning, but allows recording (equipment status tracked separately) |
| Edit after recording | Allowed if execution still `in_progress`; audit logged |
| Measurement on completed execution | Blocked - execution is immutable |
| Definition removed from step mid-work | Existing values kept; no longer required for completion |
| Batch complete with missing measurements | Blocked - each part must have its mandatory measurements |

### Gaps to Address

| Gap | Status | Action |
|-----|--------|--------|
| `StepExecutionMeasurement` model | ❌ Missing | Add model |
| `measurement_progress` property | ❌ Missing | Add to StepExecution |
| `block_on_measurement_failure` field | ❌ Missing | Add to Steps |
| Measurement enforcement in `can_advance_from_step()` | ❌ Missing | Add check |
| Measurement collection endpoints | ❌ Missing | Add API |
| Measurement UI in step execution | ❌ Missing | Add form component |

---

## Supervisor Override System

When blocking conditions prevent step completion, authorized users can override with proper justification. This is the "escape hatch" for edge cases and production emergencies.

### Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Configurable scope** | Supervisor chooses per-part or per-step (batch) |
| **Flexible specificity** | Can override specific block or all blocks |
| **Hard blocks exist** | Some conditions cannot be overridden |
| **Full audit trail** | Every override logged with reason, approver, timestamp |
| **Escalation option** | Critical overrides may require dual approval |

### Block Types

#### Soft Blocks (Overridable)

| Block | Default Overridable | Rationale |
|-------|---------------------|-----------|
| `sampling_incomplete` | ✅ Yes | Inspector unavailable, part known good |
| `qa_signoff_missing` | ✅ Yes | QA inspector unavailable, urgent order |
| `fpi_pending` | ✅ Yes | Setup verified manually |
| `fpi_failed` | ✅ Yes | Failure addressed, re-FPI not practical |
| `measurements_missing` | ✅ Yes | Equipment broken, known acceptable |
| `measurement_out_of_spec` | ✅ Yes | Known acceptable deviation (with NCR) |
| `max_visits_exceeded` | ✅ Yes | Supervisor approves additional rework |
| `batch_waiting` | ✅ Yes | Force advance subset |

#### Hard Blocks (Never Overridable)

| Block | Rationale |
|-------|-----------|
| `quarantine_active_ncr` | Part under active investigation - must resolve NCR |
| `regulatory_hold` | External agency hold (FDA, FAA) - legal requirement |
| `safety_critical_unsigned` | Safety step requires signature - cannot skip |
| `customer_witness_required` | Customer contractually required to witness |
| `recall_affected` | Part affected by active recall - must quarantine |

### Data Model

```python
class BlockType(models.TextChoices):
    """Types of blocks that can prevent step completion."""
    # Soft blocks (overridable)
    SAMPLING_INCOMPLETE = 'sampling_incomplete', 'Sampling Incomplete'
    QA_SIGNOFF_MISSING = 'qa_signoff_missing', 'QA Signoff Missing'
    FPI_PENDING = 'fpi_pending', 'FPI Pending'
    FPI_FAILED = 'fpi_failed', 'FPI Failed'
    MEASUREMENTS_MISSING = 'measurements_missing', 'Measurements Missing'
    MEASUREMENT_OUT_OF_SPEC = 'measurement_out_of_spec', 'Measurement Out of Spec'
    MAX_VISITS_EXCEEDED = 'max_visits_exceeded', 'Max Visits Exceeded'
    BATCH_WAITING = 'batch_waiting', 'Batch Waiting'

    # Hard blocks (not overridable)
    QUARANTINE_ACTIVE_NCR = 'quarantine_active_ncr', 'Quarantine - Active NCR'
    REGULATORY_HOLD = 'regulatory_hold', 'Regulatory Hold'
    SAFETY_CRITICAL = 'safety_critical', 'Safety Critical Unsigned'
    CUSTOMER_WITNESS = 'customer_witness', 'Customer Witness Required'
    RECALL_AFFECTED = 'recall_affected', 'Recall Affected'


class OverrideScope(models.TextChoices):
    """Scope of an override."""
    SINGLE_PART = 'single_part', 'Single Part'
    ALL_PARTS_AT_STEP = 'all_parts_at_step', 'All Parts at Step'
    WORK_ORDER = 'work_order', 'Entire Work Order'


class StepOverride(SecureModel):
    """
    Records a supervisor override of a blocking condition.

    Overrides can be targeted (specific block) or blanket (all blocks).
    Hard blocks cannot be overridden and will raise an error.
    """
    # What is being overridden
    work_order = models.ForeignKey(
        WorkOrders,
        on_delete=models.CASCADE,
        related_name='step_overrides'
    )
    step = models.ForeignKey(
        Steps,
        on_delete=models.CASCADE,
        related_name='overrides'
    )

    # Scope
    scope = models.CharField(
        max_length=20,
        choices=OverrideScope.choices,
        default=OverrideScope.SINGLE_PART
    )
    part = models.ForeignKey(
        Parts,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="Specific part (if scope is single_part)"
    )

    # What blocks are being overridden
    block_types = models.JSONField(
        default=list,
        help_text="List of BlockType values being overridden, or ['all'] for blanket"
    )
    """
    Examples:
    - ['sampling_incomplete'] - override just sampling
    - ['measurements_missing', 'measurement_out_of_spec'] - override measurement issues
    - ['all'] - blanket override of all soft blocks
    """

    # Justification (required)
    reason = models.TextField(
        help_text="Required justification for the override"
    )
    reason_category = models.CharField(
        max_length=50,
        choices=[
            ('equipment_unavailable', 'Equipment Unavailable'),
            ('personnel_unavailable', 'Personnel Unavailable'),
            ('customer_request', 'Customer Request'),
            ('engineering_disposition', 'Engineering Disposition'),
            ('production_emergency', 'Production Emergency'),
            ('known_acceptable', 'Known Acceptable Condition'),
            ('other', 'Other'),
        ]
    )

    # Supporting documentation
    ncr_reference = models.ForeignKey(
        'CAPA',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Related NCR/CAPA if applicable"
    )
    attachment = models.FileField(
        upload_to='overrides/',
        null=True,
        blank=True,
        help_text="Supporting documentation"
    )

    # Approval
    requested_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='override_requests'
    )
    requested_at = models.DateTimeField(auto_now_add=True)

    approved_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='override_approvals'
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    # For critical overrides requiring dual approval
    secondary_approver = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='override_secondary_approvals'
    )
    secondary_approved_at = models.DateTimeField(null=True, blank=True)

    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending Approval'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('expired', 'Expired'),
            ('used', 'Used'),
        ],
        default='pending'
    )

    # Expiration (override is time-limited)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Override expires if not used by this time"
    )

    # Tracking when override was actually used
    used_at = models.DateTimeField(null=True, blank=True)
    used_for_parts = models.JSONField(
        default=list,
        help_text="List of part IDs that were advanced using this override"
    )

    class Meta:
        ordering = ['-requested_at']

    def clean(self):
        """Validate override request."""
        from django.core.exceptions import ValidationError

        # Check for hard blocks
        hard_blocks = [
            'quarantine_active_ncr',
            'regulatory_hold',
            'safety_critical',
            'customer_witness',
            'recall_affected',
        ]

        if 'all' not in self.block_types:
            for block in self.block_types:
                if block in hard_blocks:
                    raise ValidationError({
                        'block_types': f"Cannot override hard block: {block}"
                    })

    def is_valid(self):
        """Check if override is currently valid for use."""
        from django.utils import timezone

        if self.status != 'approved':
            return False

        if self.expires_at and timezone.now() > self.expires_at:
            self.status = 'expired'
            self.save(update_fields=['status'])
            return False

        return True
```

### Step Configuration

```python
class Steps(SecureModel):
    # ... existing fields ...

    # Override settings
    requires_dual_approval_override = models.BooleanField(
        default=False,
        help_text="Critical step: overrides require two approvers"
    )

    override_expiry_hours = models.PositiveIntegerField(
        default=24,
        help_text="Hours until an approved override expires"
    )

    # Hard block flags (set by compliance/engineering)
    is_safety_critical = models.BooleanField(
        default=False,
        help_text="Safety-critical step: certain blocks cannot be overridden"
    )

    requires_customer_witness = models.BooleanField(
        default=False,
        help_text="Customer witness required: cannot override witness requirement"
    )
```

### Override Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   Operator attempts complete()                                              │
│         │                                                                   │
│         ▼                                                                   │
│   ┌─────────────────────────────────┐                                       │
│   │ can_advance_from_step()         │                                       │
│   └──────────────┬──────────────────┘                                       │
│           ┌──────┴──────┐                                                   │
│           │             │                                                   │
│           ▼             ▼                                                   │
│        BLOCKED       ALLOWED                                                │
│           │             │                                                   │
│           ▼             └──────────────────────────────────────────┐        │
│   Return blocks list                                               │        │
│   (with is_hard flag)                                              │        │
│           │                                                        │        │
│           ▼                                                        │        │
│   ┌─────────────────────────────────┐                              │        │
│   │ UI shows blocks to operator     │                              │        │
│   │ [Request Override] button       │                              │        │
│   └──────────────┬──────────────────┘                              │        │
│                  │                                                 │        │
│                  ▼                                                 │        │
│   ┌─────────────────────────────────┐                              │        │
│   │ Supervisor reviews request      │                              │        │
│   │ • Sees all blocks               │                              │        │
│   │ • Selects scope (part/batch)    │                              │        │
│   │ • Selects blocks to override    │                              │        │
│   │ • Enters reason                 │                              │        │
│   │ • Attaches NCR/documentation    │                              │        │
│   └──────────────┬──────────────────┘                              │        │
│                  │                                                 │        │
│           ┌──────┴──────┐                                          │        │
│           │             │                                          │        │
│           ▼             ▼                                          │        │
│     DUAL APPROVAL   SINGLE APPROVAL                                │        │
│     REQUIRED        SUFFICIENT                                     │        │
│           │             │                                          │        │
│           ▼             │                                          │        │
│   Second approver       │                                          │        │
│   reviews & approves    │                                          │        │
│           │             │                                          │        │
│           └──────┬──────┘                                          │        │
│                  │                                                 │        │
│                  ▼                                                 │        │
│   ┌─────────────────────────────────┐                              │        │
│   │ Override APPROVED               │                              │        │
│   │ Starts expiry countdown         │                              │        │
│   └──────────────┬──────────────────┘                              │        │
│                  │                                                 │        │
│                  ▼                                                 │        │
│   ┌─────────────────────────────────┐                              │        │
│   │ Operator completes step         │                              │        │
│   │ (override applied)              │                              │        │
│   └──────────────┬──────────────────┘                              │        │
│                  │                                                 │        │
│                  ▼                                                 │        │
│   Override marked USED                                             │        │
│   Parts recorded in used_for_parts                                 │        │
│                  │                                                 │        │
│                  └─────────────────────────────────────────────────┘        │
│                                                                             │
│                                      Part advances to next step             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Integration with can_advance_from_step()

```python
def can_advance_from_step(part, step, override=None):
    """
    Check if part can advance from step.

    Args:
        part: The part to check
        step: Current step
        override: Optional StepOverride to apply

    Returns:
        (can_advance: bool, blocks: list[dict])
        Each block dict contains:
        - type: BlockType value
        - message: Human-readable description
        - is_hard: Whether this is a hard block (cannot be overridden)
    """
    blocks = []

    # Get current execution
    execution = StepExecution.get_current_execution(part)
    if not execution:
        blocks.append({
            'type': 'no_execution',
            'message': 'No active step execution',
            'is_hard': True  # Can't override - invalid state
        })
        return False, blocks

    # Check sampling
    if part.requires_sampling:
        has_report = QualityReports.objects.filter(part=part, step=step).exists()
        if not has_report:
            blocks.append({
                'type': 'sampling_incomplete',
                'message': 'Part flagged for sampling but no QualityReport exists',
                'is_hard': False
            })

    # Check QA signoff
    if step.requires_qa_signoff:
        has_approval = QaApproval.objects.filter(part=part, step=step, approved=True).exists()
        if not has_approval:
            blocks.append({
                'type': 'qa_signoff_missing',
                'message': 'Step requires QA signoff',
                'is_hard': False
            })

    # Check FPI
    if step.requires_first_piece_inspection:
        fpi_record = FPIRecord.objects.filter(work_order=part.work_order, step=step).first()
        if not fpi_record or fpi_record.status == 'pending':
            blocks.append({
                'type': 'fpi_pending',
                'message': 'First Piece Inspection not completed',
                'is_hard': False
            })
        elif fpi_record.status == 'failed':
            blocks.append({
                'type': 'fpi_failed',
                'message': 'First Piece Inspection failed',
                'is_hard': False
            })

    # Check mandatory measurements
    progress = execution.measurement_progress
    if not progress['is_complete']:
        blocks.append({
            'type': 'measurements_missing',
            'message': f"Missing {progress['remaining']} mandatory measurement(s)",
            'is_hard': False
        })

    # Check measurement specs
    if step.block_on_measurement_failure:
        out_of_spec = execution.measurements.filter(is_within_spec=False)
        if out_of_spec.exists():
            blocks.append({
                'type': 'measurement_out_of_spec',
                'message': f"Measurement out of spec: {out_of_spec.first().definition.label}",
                'is_hard': False
            })

    # Check quarantine with active NCR (HARD BLOCK)
    if part.part_status == PartsStatus.QUARANTINED:
        active_ncr = CAPA.objects.filter(
            affected_parts=part,
            status__in=['open', 'in_progress']
        ).exists()
        if active_ncr:
            blocks.append({
                'type': 'quarantine_active_ncr',
                'message': 'Part quarantined with active NCR - must resolve NCR first',
                'is_hard': True
            })

    # Check regulatory hold (HARD BLOCK)
    if hasattr(part, 'regulatory_hold') and part.regulatory_hold:
        blocks.append({
            'type': 'regulatory_hold',
            'message': 'Part under regulatory hold',
            'is_hard': True
        })

    # Check customer witness (HARD BLOCK)
    if step.requires_customer_witness:
        has_witness = CustomerWitness.objects.filter(
            part=part,
            step=step,
            witnessed=True
        ).exists()
        if not has_witness:
            blocks.append({
                'type': 'customer_witness',
                'message': 'Customer witness required but not recorded',
                'is_hard': True
            })

    # Check safety critical (HARD BLOCK if unsigned)
    if step.is_safety_critical:
        has_safety_signoff = SafetySignoff.objects.filter(
            execution=execution,
            signed=True
        ).exists()
        if not has_safety_signoff:
            blocks.append({
                'type': 'safety_critical',
                'message': 'Safety-critical step requires signoff',
                'is_hard': True
            })

    # Apply override if provided
    if override and override.is_valid():
        blocks = _apply_override(blocks, override)

    # Check if any blocks remain
    has_blocks = len(blocks) > 0

    return not has_blocks, blocks


def _apply_override(blocks, override):
    """Remove overridden blocks from the list."""
    if 'all' in override.block_types:
        # Blanket override - remove all soft blocks
        return [b for b in blocks if b['is_hard']]
    else:
        # Targeted override - remove specific blocks
        return [b for b in blocks if b['type'] not in override.block_types or b['is_hard']]
```

### API Endpoints

#### Check Blocks

```
GET /api/Parts/{id}/completion-blocks/
```

**Response:**
```json
{
    "part_id": "uuid",
    "step": "Final Inspection",
    "can_advance": false,
    "blocks": [
        {
            "type": "sampling_incomplete",
            "message": "Part flagged for sampling but no QualityReport exists",
            "is_hard": false
        },
        {
            "type": "measurements_missing",
            "message": "Missing 2 mandatory measurement(s)",
            "is_hard": false
        }
    ],
    "has_hard_blocks": false,
    "pending_override": null
}
```

#### Request Override

```
POST /api/StepOverrides/
```

**Request:**
```json
{
    "work_order": "uuid",
    "step": "uuid",
    "scope": "single_part",
    "part": "uuid",
    "block_types": ["sampling_incomplete", "measurements_missing"],
    "reason": "Measurement equipment down for calibration, part visually inspected and confirmed good by engineering",
    "reason_category": "equipment_unavailable",
    "ncr_reference": "uuid"
}
```

#### Approve Override

```
POST /api/StepOverrides/{id}/approve/
```

**Request:**
```json
{
    "approved": true,
    "notes": "Approved per engineering disposition ED-2024-042"
}
```

#### Complete with Override

```
POST /api/StepExecutions/{id}/complete/
```

**Request:**
```json
{
    "override_id": "uuid"
}
```

### Permissions

| Permission | Description |
|------------|-------------|
| `request_override` | Request an override (operators) |
| `approve_override` | Approve override requests (supervisors) |
| `approve_override_secondary` | Secondary approval for critical steps |
| `view_override_audit` | View override history and reports |

### Audit & Reporting

All overrides are logged with:
- Requesting user and timestamp
- Approving user(s) and timestamp
- All blocks that were overridden
- Reason and category
- Parts affected
- When override was used

**Override Report:**
```
GET /api/StepOverrides/report/?date_from=2024-01-01&date_to=2024-01-31
```

Returns summary by:
- Override reason category
- Step
- Approver
- Most frequently overridden blocks

### Edge Cases

| Scenario | Behavior |
|----------|----------|
| Override expires before use | Status → 'expired', must request new |
| Override approved, part already advanced | Override unused, no effect |
| Blanket override but hard block exists | Hard blocks remain, soft blocks cleared |
| Override for batch, some parts have hard blocks | Soft-blocked parts advance, hard-blocked stay |
| Dual approval required, one rejects | Override rejected |
| Same block overridden twice | Most recent valid override applies |

### Gaps to Address

| Gap | Status | Action |
|-----|--------|--------|
| `StepOverride` model | ❌ Missing | Add model |
| `BlockType` enum | ❌ Missing | Add choices |
| Override check in `can_advance_from_step()` | ❌ Missing | Add parameter |
| Override request endpoint | ❌ Missing | Add API |
| Override approval endpoint | ❌ Missing | Add API |
| Override UI | ❌ Missing | Add components |
| Step override settings | ❌ Missing | Add fields to Steps |
| Hard block detection | ❌ Missing | Add checks for quarantine, regulatory, etc. |

---

## Undo & Rollback System

Allows correction of human error and moving parts backward through the process when needed.

### Scope

| In Scope | Out of Scope |
|----------|--------------|
| Edit data (measurements, notes) | Shipped parts (RMA/recall process) |
| Void and replace records | Completed work orders |
| Move part backward (any steps) | Scrapped parts |
| Re-trigger FPI/sampling | Cross-tenant operations |

### Rollback Types

| Type | Use Case | Complexity | Permission |
|------|----------|------------|------------|
| **Edit** | Fix typo, wrong value | Low | `edit_step_data` |
| **Void Record** | Invalidate QA report, create new | Low | `void_records` |
| **Undo Current** | Reverse just-completed step | Medium | `undo_step` |
| **Rollback to Step** | Move part back multiple steps | High | `rollback_part` |

### Data Model

```python
class RollbackReason(models.TextChoices):
    """Standard reasons for rollback."""
    OPERATOR_ERROR = 'operator_error', 'Operator Error'
    DATA_ENTRY_ERROR = 'data_entry_error', 'Data Entry Error'
    WRONG_DECISION = 'wrong_decision', 'Wrong Decision Path'
    DEFECT_FOUND = 'defect_found', 'Defect Found Later'
    REWORK_REQUIRED = 'rework_required', 'Rework Required'
    EQUIPMENT_ISSUE = 'equipment_issue', 'Equipment Issue Discovered'
    PROCESS_DEVIATION = 'process_deviation', 'Process Deviation'
    ENGINEERING_REQUEST = 'engineering_request', 'Engineering Request'
    CUSTOMER_REJECTION = 'customer_rejection', 'Customer Rejection'
    OTHER = 'other', 'Other'


class StepRollback(SecureModel):
    """
    Records a rollback operation on a part.

    Tracks what was rolled back, why, and what happened to affected records.
    """
    # What was rolled back
    part = models.ForeignKey(
        Parts,
        on_delete=models.CASCADE,
        related_name='rollbacks'
    )
    from_step = models.ForeignKey(
        Steps,
        on_delete=models.PROTECT,
        related_name='rollbacks_from',
        help_text="Step the part was at before rollback"
    )
    to_step = models.ForeignKey(
        Steps,
        on_delete=models.PROTECT,
        related_name='rollbacks_to',
        help_text="Step the part was rolled back to"
    )

    # Why
    reason = models.CharField(
        max_length=30,
        choices=RollbackReason.choices
    )
    reason_detail = models.TextField(
        help_text="Detailed explanation for the rollback"
    )

    # Related records (for traceability)
    ncr_reference = models.ForeignKey(
        'CAPA',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Related NCR if applicable"
    )

    # What happened to intermediate data
    voided_executions = models.JSONField(
        default=list,
        help_text="StepExecution IDs that were voided"
    )
    voided_quality_reports = models.JSONField(
        default=list,
        help_text="QualityReport IDs that were voided"
    )
    voided_measurements = models.JSONField(
        default=list,
        help_text="StepExecutionMeasurement IDs that were voided"
    )

    # Options
    preserve_measurements = models.BooleanField(
        default=False,
        help_text="If True, measurements at target step are preserved (edit scenario)"
    )
    require_re_inspection = models.BooleanField(
        default=True,
        help_text="If True, part is re-flagged for sampling at target step"
    )
    require_re_fpi = models.BooleanField(
        default=False,
        help_text="If True, FPI must be redone (equipment/process issue)"
    )

    # Approval
    requested_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='rollback_requests'
    )
    requested_at = models.DateTimeField(auto_now_add=True)

    approved_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='rollback_approvals'
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending Approval'),
            ('approved', 'Approved'),
            ('executed', 'Executed'),
            ('rejected', 'Rejected'),
        ],
        default='pending'
    )

    # Execution tracking
    executed_at = models.DateTimeField(null=True, blank=True)
    executed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='rollback_executions'
    )

    class Meta:
        ordering = ['-requested_at']
```

### Record Editing

For quick corrections (human error caught quickly):

```python
class RecordEdit(SecureModel):
    """
    Tracks edits to records (measurements, notes, etc.).

    Provides audit trail without requiring void-and-replace.
    """
    # What was edited
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_object = GenericForeignKey('content_type', 'object_id')

    # Field-level tracking
    field_name = models.CharField(max_length=100)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)

    # Why
    reason = models.TextField()

    # Who/when
    edited_by = models.ForeignKey(User, on_delete=models.PROTECT)
    edited_at = models.DateTimeField(auto_now_add=True)
```

**Editable Fields:**

| Model | Editable Fields | Non-Editable |
|-------|-----------------|--------------|
| `StepExecutionMeasurement` | `value_numeric`, `value_pass_fail`, `notes` | `definition`, `recorded_by`, `recorded_at` |
| `QualityReports` | `description`, `status` (with approval) | `part`, `step`, `report_number` |
| `StepExecution` | `notes`, `decision_result` (with approval) | `part`, `step`, `entered_at` |

### Void Records

For cases where edit isn't enough:

```python
class VoidableModel(models.Model):
    """Mixin for models that can be voided."""
    is_voided = models.BooleanField(default=False)
    voided_at = models.DateTimeField(null=True, blank=True)
    voided_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )
    void_reason = models.TextField(blank=True)
    replaced_by = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='replaces'
    )

    class Meta:
        abstract = True

    def void(self, user, reason, replacement=None):
        """Void this record."""
        self.is_voided = True
        self.voided_at = timezone.now()
        self.voided_by = user
        self.void_reason = reason
        self.replaced_by = replacement
        self.save()
```

**Apply to:**
- `QualityReports`
- `StepExecution`
- `StepExecutionMeasurement`
- `QaApproval`
- `FPIRecord`

### Rollback Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   Operator/Supervisor identifies need for rollback                          │
│         │                                                                   │
│         ▼                                                                   │
│   ┌─────────────────────────────────┐                                       │
│   │ Request Rollback                │                                       │
│   │ • Select part(s)                │                                       │
│   │ • Select target step            │                                       │
│   │ • Select reason                 │                                       │
│   │ • Enter detail                  │                                       │
│   │ • Options:                      │                                       │
│   │   ☐ Preserve measurements       │                                       │
│   │   ☑ Require re-inspection       │                                       │
│   │   ☐ Require re-FPI              │                                       │
│   └──────────────┬──────────────────┘                                       │
│                  │                                                          │
│           ┌──────┴──────┐                                                   │
│           │             │                                                   │
│           ▼             ▼                                                   │
│      SAME STEP      DIFFERENT STEP                                          │
│      (undo current)  (rollback)                                             │
│           │             │                                                   │
│           │             ▼                                                   │
│           │      ┌─────────────────────────────────┐                        │
│           │      │ Approval Required               │                        │
│           │      │ (rollback_part permission)      │                        │
│           │      └──────────────┬──────────────────┘                        │
│           │                     │                                           │
│           └──────────┬──────────┘                                           │
│                      │                                                      │
│                      ▼                                                      │
│   ┌─────────────────────────────────┐                                       │
│   │ Execute Rollback                │                                       │
│   │                                 │                                       │
│   │ 1. Void intermediate records:   │                                       │
│   │    • StepExecutions             │                                       │
│   │    • QualityReports             │                                       │
│   │    • Measurements               │                                       │
│   │    • QaApprovals                │                                       │
│   │                                 │                                       │
│   │ 2. Update part:                 │                                       │
│   │    • part.step = target_step    │                                       │
│   │    • part.part_status = PENDING │                                       │
│   │                                 │                                       │
│   │ 3. Create new StepExecution:    │                                       │
│   │    • At target step             │                                       │
│   │    • New visit_number           │                                       │
│   │    • status = 'pending'         │                                       │
│   │                                 │                                       │
│   │ 4. Re-evaluate sampling:        │                                       │
│   │    • If require_re_inspection   │                                       │
│   │                                 │                                       │
│   │ 5. Re-evaluate FPI:             │                                       │
│   │    • If require_re_fpi          │                                       │
│   │    • Reset FPIRecord status     │                                       │
│   └──────────────┬──────────────────┘                                       │
│                  │                                                          │
│                  ▼                                                          │
│   Part is now at target step, ready for work                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Rollback Execution Logic

```python
def execute_rollback(rollback: StepRollback, executor: User):
    """
    Execute an approved rollback.

    Voids intermediate records and moves part to target step.
    """
    from django.utils import timezone

    part = rollback.part
    from_step = rollback.from_step
    to_step = rollback.to_step

    # Get the path of steps to void (from current back to target)
    steps_to_void = get_steps_between(
        process=part.work_order.process,
        from_step=to_step,
        to_step=from_step,
        inclusive_end=True  # Include from_step
    )

    voided_executions = []
    voided_quality_reports = []
    voided_measurements = []

    # Void all StepExecutions in the path
    for step in steps_to_void:
        executions = StepExecution.objects.filter(
            part=part,
            step=step,
            is_voided=False
        )
        for exe in executions:
            exe.void(
                user=executor,
                reason=f"Rollback: {rollback.reason_detail}"
            )
            voided_executions.append(str(exe.id))

            # Void measurements on this execution
            if not rollback.preserve_measurements or step != to_step:
                for measurement in exe.measurements.filter(is_voided=False):
                    measurement.void(
                        user=executor,
                        reason=f"Rollback: {rollback.reason_detail}"
                    )
                    voided_measurements.append(str(measurement.id))

    # Void QualityReports in the path
    for step in steps_to_void:
        reports = QualityReports.objects.filter(
            part=part,
            step=step,
            is_voided=False
        )
        for report in reports:
            report.void(
                user=executor,
                reason=f"Rollback: {rollback.reason_detail}"
            )
            voided_quality_reports.append(str(report.id))

    # Void QaApprovals in the path
    QaApproval.objects.filter(
        part=part,
        step__in=steps_to_void,
        is_voided=False
    ).update(
        is_voided=True,
        voided_at=timezone.now(),
        voided_by=executor,
        void_reason=f"Rollback: {rollback.reason_detail}"
    )

    # Update part
    part.step = to_step
    part.part_status = PartsStatus.PENDING

    # Re-evaluate sampling if requested
    if rollback.require_re_inspection:
        evaluator = SamplingFallbackApplier(part=part)
        result = evaluator.evaluate()
        part.requires_sampling = result.get("requires_sampling", False)
        part.sampling_rule = result.get("rule")
        part.sampling_ruleset = result.get("ruleset")

    part.save()

    # Create new StepExecution at target step
    visit_number = StepExecution.get_visit_count(part, to_step) + 1
    StepExecution.objects.create(
        part=part,
        step=to_step,
        visit_number=visit_number,
        status='pending',
        notes=f"Rollback from {from_step.name}: {rollback.reason_detail}"
    )

    # Handle FPI if needed
    if rollback.require_re_fpi and to_step.requires_first_piece_inspection:
        fpi_record = FPIRecord.objects.filter(
            work_order=part.work_order,
            step=to_step
        ).first()
        if fpi_record:
            fpi_record.status = 'pending'
            fpi_record.quality_report = None
            fpi_record.save()

    # Update rollback record
    rollback.status = 'executed'
    rollback.executed_at = timezone.now()
    rollback.executed_by = executor
    rollback.voided_executions = voided_executions
    rollback.voided_quality_reports = voided_quality_reports
    rollback.voided_measurements = voided_measurements
    rollback.save()

    # Log transition
    StepTransitionLog.objects.create(
        part=part,
        step=to_step,
        operator=executor,
        transition_type='rollback',
        notes=f"Rolled back from {from_step.name}"
    )

    return rollback
```

### Quick Undo (Same Step)

For "I just clicked complete by mistake":

```python
def undo_current_step(part, user, reason):
    """
    Quick undo of just-completed step.

    Only works if:
    - Part just completed this step (within time window)
    - Part hasn't been claimed at next step
    - No downstream dependencies
    """
    current_step = part.step
    current_execution = StepExecution.objects.filter(
        part=part,
        step=current_step,
        status='completed',
        is_voided=False
    ).order_by('-exited_at').first()

    if not current_execution:
        raise ValueError("No completed execution to undo")

    # Check time window (configurable, e.g., 30 minutes)
    time_limit = timezone.now() - timedelta(minutes=30)
    if current_execution.exited_at < time_limit:
        raise ValueError("Undo window expired - use full rollback")

    # Check no downstream work
    next_execution = StepExecution.objects.filter(
        part=part,
        entered_at__gt=current_execution.exited_at,
        is_voided=False
    ).exists()

    if next_execution:
        raise ValueError("Part has moved to next step - use full rollback")

    # Reopen the execution
    current_execution.status = 'in_progress'
    current_execution.exited_at = None
    current_execution.completed_by = None
    current_execution.save()

    # Update part status
    part.part_status = PartsStatus.IN_PROGRESS
    part.save()

    # Log the undo
    RecordEdit.objects.create(
        content_type=ContentType.objects.get_for_model(StepExecution),
        object_id=current_execution.id,
        field_name='status',
        old_value='completed',
        new_value='in_progress',
        reason=reason,
        edited_by=user
    )

    return current_execution
```

### API Endpoints

#### Edit Record

```
PATCH /api/StepExecutionMeasurements/{id}/
```

**Request:**
```json
{
    "value_numeric": 25.42,
    "edit_reason": "Corrected decimal point error"
}
```

#### Void Record

```
POST /api/QualityReports/{id}/void/
```

**Request:**
```json
{
    "reason": "Wrong part scanned, report is for different part",
    "create_replacement": false
}
```

#### Quick Undo

```
POST /api/Parts/{id}/undo-current/
```

**Request:**
```json
{
    "reason": "Clicked complete prematurely"
}
```

#### Request Rollback

```
POST /api/StepRollbacks/
```

**Request:**
```json
{
    "part": "uuid",
    "to_step": "uuid",
    "reason": "defect_found",
    "reason_detail": "Crack found at downstream visual inspection",
    "ncr_reference": "uuid",
    "preserve_measurements": false,
    "require_re_inspection": true,
    "require_re_fpi": false
}
```

#### Approve Rollback

```
POST /api/StepRollbacks/{id}/approve/
```

#### Execute Rollback

```
POST /api/StepRollbacks/{id}/execute/
```

### Batch Rollback

For systemic issues (equipment out of cal, bad lot):

```python
class BatchRollback(SecureModel):
    """
    Rollback multiple parts at once.

    Used for systemic issues affecting many parts.
    """
    work_order = models.ForeignKey(WorkOrders, on_delete=models.CASCADE)
    to_step = models.ForeignKey(Steps, on_delete=models.PROTECT)

    # Which parts
    affected_parts = models.ManyToManyField(Parts)
    selection_criteria = models.JSONField(
        help_text="How parts were selected (for audit)"
    )
    """
    Example:
    {
        "type": "equipment",
        "equipment_id": "uuid",
        "date_range": ["2024-01-15", "2024-01-16"],
        "steps": ["uuid1", "uuid2"]
    }
    """

    # Same fields as StepRollback for reason, approval, etc.
    reason = models.CharField(max_length=30, choices=RollbackReason.choices)
    reason_detail = models.TextField()
    # ... approval fields ...

    # Tracking
    individual_rollbacks = models.ManyToManyField(
        StepRollback,
        related_name='batch_rollback'
    )
```

### Permissions

| Permission | Description |
|------------|-------------|
| `edit_step_data` | Edit measurements, notes (quick fixes) |
| `void_records` | Void QualityReports, executions |
| `undo_step` | Quick undo of just-completed step |
| `rollback_part` | Full rollback to previous step |
| `batch_rollback` | Rollback multiple parts (systemic issues) |
| `view_rollback_history` | View rollback audit trail |

### Configuration

```python
class Steps(SecureModel):
    # ... existing fields ...

    # Rollback settings
    undo_window_minutes = models.PositiveIntegerField(
        default=30,
        help_text="Time window for quick undo (0 = disabled)"
    )

    rollback_requires_approval = models.BooleanField(
        default=True,
        help_text="If True, rollbacks require supervisor approval"
    )
```

### Edge Cases

| Scenario | Behavior |
|----------|----------|
| Undo after time window | Must use full rollback with approval |
| Rollback past FPI step | Option to require re-FPI |
| Part in batch, rollback one | Just that part rolls back, others stay |
| Rollback to step with batch waiting | Part joins batch at that step |
| Rollback voided part | Not allowed - void is permanent |
| Rollback scrapped part | Not allowed - scrapped is terminal |
| Edit voided record | Not allowed - void is permanent |
| Rollback past decision split | Returns to decision step, must re-decide |

### Gaps to Address

| Gap | Status | Action |
|-----|--------|--------|
| `StepRollback` model | ❌ Missing | Add model |
| `RecordEdit` model | ❌ Missing | Add model |
| `VoidableModel` mixin | ❌ Missing | Add mixin |
| `is_voided` fields | ❌ Missing | Add to QualityReports, StepExecution, etc. |
| Rollback execution logic | ❌ Missing | Add function |
| Quick undo endpoint | ❌ Missing | Add API |
| Batch rollback | ❌ Missing | Add model and logic |
| Rollback UI | ❌ Missing | Add components |

---

## Completion Cascade Effects (Spill-Out)

Step completion should trigger downstream state changes. These are not "future enhancements" but **core functionality** that needs to be wired.

### Current Spill-Out (Already Implemented)

When `increment_step()` runs:

| Target | Action | Location |
|--------|--------|----------|
| `StepExecution` | Marks completed, creates new for next step | mes_lite.py:2266-2403 |
| `Parts` | Updates step, part_status, sampling fields | mes_lite.py:2360-2415 |
| `StepTransitionLog` | Creates audit entry | mes_lite.py:2300, 2370, 2418 |

### Missing Cascade Effects

These should fire on step completion but currently don't:

#### 1. WorkOrder Status Cascade

**Gap:** All parts reach terminal step → WorkOrder stays IN_PROGRESS

```python
# Should happen in increment_step() when terminal reached
def _cascade_work_order_status(part):
    """Update WorkOrder status when all parts complete terminal step."""
    wo = part.work_order
    if not wo:
        return

    # Check if all parts at terminal
    non_terminal_parts = wo.parts.exclude(
        part_status__in=[PartsStatus.COMPLETED, PartsStatus.SCRAPPED, PartsStatus.CANCELLED]
    )

    if not non_terminal_parts.exists():
        # All parts at terminal status
        all_completed = wo.parts.filter(part_status=PartsStatus.COMPLETED).count()
        all_scrapped = wo.parts.filter(part_status=PartsStatus.SCRAPPED).count()

        if all_scrapped == wo.parts.count():
            wo.workorder_status = WorkOrderStatus.CANCELLED  # All scrapped
        else:
            wo.workorder_status = WorkOrderStatus.COMPLETED

        wo.true_completion = timezone.now().date()
        wo.save(update_fields=['workorder_status', 'true_completion'])
```

#### 2. Order Status Cascade

**Gap:** All WorkOrders complete → Order stays IN_PROGRESS

```python
# Should fire when WorkOrder status changes to COMPLETED
def _cascade_order_status(work_order):
    """Update Order status when all WorkOrders complete."""
    order = work_order.related_order
    if not order:
        return

    incomplete_wos = order.related_orders.exclude(
        workorder_status__in=[WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED]
    )

    if not incomplete_wos.exists():
        order.order_status = OrdersStatus.COMPLETED
        order.save(update_fields=['order_status'])
```

#### 3. Step Completion Notifications

**Gap:** No alerts on step completion, batch ready, escalation routing

**Notification Events to Add:**

| Event | Recipients | Trigger |
|-------|------------|---------|
| `batch_ready_for_advance` | Supervisors, next station | All parts at step marked ready |
| `step_escalated` | Supervisors, QA | Part routed to escalation edge |
| `terminal_reached` | Supervisors, order owner | Part completes final step |
| `work_order_completed` | Supervisors, customer (optional) | WO status → COMPLETED |
| `decision_split` | Supervisors | Decision routes to alternate path |
| `fpi_required` | QA, supervisors | First part auto-flagged for FPI |

```python
# Conceptual notification dispatch
class StepCompletionNotifier:
    """Dispatch notifications on step completion events."""

    def on_part_advanced(self, part, from_step, to_step, was_escalated=False):
        if was_escalated:
            self._notify('step_escalated', part=part, step=from_step)

        if to_step.is_terminal:
            self._notify('terminal_reached', part=part)

    def on_batch_ready(self, work_order, step, ready_count, total_count):
        if ready_count == total_count:
            self._notify('batch_ready_for_advance',
                         work_order=work_order, step=step)

    def on_work_order_completed(self, work_order):
        self._notify('work_order_completed', work_order=work_order)
```

#### 4. ScheduleSlot Completion

**Gap:** ScheduleSlot status not updated when step work completes

```python
# When step execution completes, check for associated schedule slot
def _cascade_schedule_slot(step_execution):
    """Mark ScheduleSlot complete when associated work finishes."""
    if not step_execution.work_center:
        return

    slot = ScheduleSlot.objects.filter(
        work_order=step_execution.part.work_order,
        step=step_execution.step,
        work_center=step_execution.work_center,
        status='IN_PROGRESS'
    ).first()

    if slot:
        # Check if all parts at this step are done
        remaining = step_execution.part.work_order.parts.filter(
            step=step_execution.step
        ).exclude(part_status=PartsStatus.READY_FOR_NEXT_STEP)

        if not remaining.exists():
            slot.status = 'COMPLETED'
            slot.actual_end_time = timezone.now()
            slot.save(update_fields=['status', 'actual_end_time'])
```

#### 5. HubSpot Progress Sync (Outbound)

**Gap:** CRM only syncs inbound; production progress not pushed to deals

**Design Decision Needed:** Do we want to:
- Push part-level progress? (chatty, real-time)
- Push order milestone events? (key stages only)
- Push on work order completion? (summary events)

```python
# Conceptual outbound sync - milestone-based
def _sync_hubspot_progress(order, event_type):
    """Push progress events to HubSpot deal."""
    if not order.hubspot_deal_id:
        return

    from Tracker.integrations.hubspot_service import HubSpotService

    service = HubSpotService()

    # Calculate progress
    total_parts = order.parts.count()
    completed_parts = order.parts.filter(part_status=PartsStatus.COMPLETED).count()
    progress_pct = (completed_parts / total_parts * 100) if total_parts else 0

    service.update_deal_properties(
        deal_id=order.hubspot_deal_id,
        properties={
            'production_progress': progress_pct,
            'production_status': order.order_status,
            'last_production_event': event_type,
            'last_production_update': timezone.now().isoformat(),
        }
    )
```

### Cascade Trigger Points

Where these cascades should fire in `increment_step()`:

```python
def increment_step(self, operator=None, decision_result=None):
    # ... existing logic ...

    # === TERMINAL STEP ===
    if next_step is None:
        # ... existing terminal handling ...

        # NEW: Cascade WorkOrder status
        _cascade_work_order_status(self)

        # NEW: Notify terminal reached
        StepCompletionNotifier().on_part_advanced(
            self, from_step=self.step, to_step=None
        )

        return "completed"

    # === BATCH ADVANCEMENT ===
    if self.work_order and not self.step.is_decision_point:
        # ... existing batch logic ...

        if not other_parts_pending.exists():
            # All parts ready

            # NEW: Notify batch ready
            StepCompletionNotifier().on_batch_ready(
                self.work_order, self.step,
                ready_count=ready_parts.count(),
                total_count=ready_parts.count()
            )

            # ... bulk advance ...

            # NEW: Update schedule slots
            _cascade_schedule_slot(current_execution)

    # === POST-ADVANCEMENT ===
    # NEW: Notify if escalated
    if was_escalated:
        StepCompletionNotifier().on_part_advanced(
            self, from_step=self.step, to_step=next_step, was_escalated=True
        )

    return "escalated" if was_escalated else "advanced"
```

### Cascade Gaps Summary

| Gap | Priority | Action |
|-----|----------|--------|
| WorkOrder auto-complete | High | Add `_cascade_work_order_status()` to `increment_step()` |
| Order auto-complete | High | Add signal on WorkOrder save when status→COMPLETED |
| Step completion notifications | Medium | Create `StepCompletionNotifier` dispatcher |
| ScheduleSlot completion | Medium | Add `_cascade_schedule_slot()` |
| HubSpot progress sync | Low | Decide scope; add outbound sync on milestones |
| Time entry auto-close | Deferred | Keep independent; document as optional future |

### Edge Cases

| Scenario | Behavior |
|----------|----------|
| All parts scrapped → WO status? | CANCELLED (not COMPLETED) |
| Some parts completed, some scrapped | COMPLETED (partial success) |
| WO completed but Order has other WOs | Order stays IN_PROGRESS |
| Schedule slot spans multiple shifts | Only close when last shift's work done |
| HubSpot sync fails | Log error, don't block step completion |
| Notification delivery fails | Log error, don't block step completion |

---

## Appendix: Edge Case Quick Reference

| Scenario | Behavior |
|----------|----------|
| Complete without start | Auto-backfill `started_at`, proceed |
| Part added mid-batch | Starts at step 1, independent |
| Max visits exceeded | Block completion, require supervisor override |
| All parts scrapped | Notify supervisors, work order needs attention |
| Force advance partial | Ready parts advance, others stay at step |
| Rework re-entry | New `visit_number`, joins current batch at step |
| Decision splits batch | Each path becomes independent batch |
| Merge step waiting | Waits for parts at step, not all paths |
| Work order cancelled | Parts/executions cancelled, time entries closed |
| Operator deleted | `assigned_to` nulled, work needs attention |
| Unavailable with in-progress | Flag `needs_reassignment`, don't auto-release |
| Sampled part missing report | Block advancement until QualityReport created |
| Sampling fails (FAIL status) | Part goes to quarantine flow, no advancement |
| No SamplingRuleSet but sampling_required | Part proceeds without sampling (no rules matched) |
| Fallback triggered | Higher sampling rate until consecutive passes |
| QA signoff required | All parts blocked until QaApproval created |
| qa_result decision, no report | **Gap**: Currently defaults to FAIL path; should block |
| Measurement decision, no data | Uses 0 as default; evaluates against edge conditions |
| Manual decision, no input | Raises ValueError requiring 'pass'/'fail' |
| No DEFAULT edge defined | Falls back to ProcessStep order+1 |
| No ESCALATION edge at max_visits | Returns None (triggers completion/error) |
| Terminal step with unmapped status | Falls back to PartsStatus.COMPLETED |
| FPI required, first part arrives | Auto-assign as FPI candidate, block others |
| FPI part damaged before inspection | Operator overrides to different part |
| FPI fails | Block all parts, notify supervisor, await setup fix |
| FPI retry same part | Reset to pending after setup adjustment |
| FPI retry different part | Override + disposition original part |
| Equipment change with fpi_scope=equipment | New FPI required for new equipment |
| Shift change with fpi_scope=shift | New FPI required for new shift |
| FPI waived | Audit logged, all parts unblocked |
| Multiple part types at FPI step | Separate FPI per part type if scoped |
| Mandatory measurements missing | Block step completion until all recorded |
| Measurement out of spec | Record value; block if `block_on_measurement_failure` |
| Edit measurement after recording | Allowed while execution `in_progress`; audit logged |
| Measurement on completed execution | Blocked - execution immutable |
| Sampled part with mandatory measurements | Both required: step measurements + QualityReport |
| Override requested, not yet approved | Part stays blocked until approval |
| Override approved, not yet used | Part can advance within expiry window |
| Override expired | Must request new override |
| Override for soft block with hard block present | Soft block cleared, hard block remains |
| Blanket override requested | All soft blocks cleared, hard blocks remain |
| Dual approval required, one rejects | Override rejected, must re-request |
| Override used for batch | All applicable parts recorded in `used_for_parts` |
| Hard block (quarantine/regulatory) | Cannot override, must resolve underlying issue |
| Quick undo within time window | Reopen execution, part back to in_progress |
| Quick undo after time window | Rejected - must use full rollback |
| Quick undo after part moved | Rejected - must use full rollback |
| Rollback single part in batch | Just that part rolls back, others stay |
| Rollback past FPI step | Option to require re-FPI |
| Rollback past decision point | Returns to decision, must re-decide |
| Rollback with preserved measurements | Measurements at target step kept |
| Batch rollback (equipment issue) | All affected parts rolled back together |
| Edit voided record | Not allowed - void is permanent |
| Rollback scrapped part | Not allowed - scrapped is terminal |

---

## Appendix: Future Integration Points

The following models interact with step completion but are outside the current design scope. They represent potential enhancement areas for pre-condition checks or post-completion triggers.

### Adjacent Model Summary

| Model | Location | Integration Type | Description |
|-------|----------|-----------------|-------------|
| **TimeEntry** | mes_standard.py | Post-completion | Labor tracking clock in/out. Currently independent of step lifecycle. Future: auto-close open entries on step completion? |
| **MaterialUsage** | mes_standard.py | Pre-condition | Material consumption traceability. Future: block step completion if required materials not logged? |
| **TrainingRecord** | qms.py | Pre-condition | Operator qualification tracking. Future: soft/hard block if operator training expired for step? |
| **TrainingRequirement** | qms.py | Pre-condition | What training is required for what. Future: tie requirements to Steps? |
| **CalibrationRecord** | qms.py | Pre-condition | Equipment calibration status. Future: block step if equipment out of calibration? |
| **WorkOrder** | mes_lite.py | Post-completion | Work order lifecycle. Future: auto-transition WO status when all parts complete final step? |
| **Documents** | mes_standard.py | Pre-condition | Work instructions and SOPs. Future: require work instruction acknowledgment before step start? |
| **ScheduleSlot** | mes_standard.py | Monitoring | Production scheduling. Future: track schedule adherence during step execution? |

### Potential Pre-Condition Checks

These could be added as blocking conditions similar to the soft/hard block system already designed:

```python
# Conceptual - not implemented
class StepPreCondition(models.Model):
    step = ForeignKey(Steps)
    condition_type = CharField(choices=[
        'training_current',      # Operator training not expired
        'equipment_calibrated',  # Equipment calibration current
        'materials_logged',      # Required materials consumed/logged
        'work_instruction_ack',  # Work instruction acknowledged
        'tool_checkout',         # Required tooling checked out
    ])
    is_blocking = BooleanField(default=True)  # Hard vs soft block
    error_message = CharField()
```

### Potential Post-Completion Triggers

These could fire after successful step completion:

```python
# Conceptual - not implemented
class StepPostTrigger(models.Model):
    step = ForeignKey(Steps)
    trigger_type = CharField(choices=[
        'close_time_entries',    # Auto-close open time entries
        'notify_next_station',   # Alert downstream workstation
        'update_schedule',       # Mark schedule slot complete
        'sync_erp',              # Push completion to ERP
        'generate_document',     # Auto-generate traveler/label
    ])
    is_enabled = BooleanField(default=True)
```

### Current Position

The core step completion system (claim → start → complete, sampling, FPI, measurements, overrides, rollback) is designed and documented. These integration points are noted for future consideration and would extend the completion logic with:

- Additional blocking conditions (training, calibration, materials)
- Automatic side-effects (time entry closure, schedule updates)
- External system sync (ERP, document generation)

These are **not required** for the current implementation but provide a clear extension path.

---

## Summary: Implementation Priority

### Phase 1 - Core Step Completion
1. Add `claimed` status to StepExecution
2. Add `started_at` field
3. Implement `claim()`, `start()`, `complete()`, `release()` actions
4. Add Step completion settings fields

### Phase 2 - Sampling & QA Integration
1. Integrate sampling check in `increment_step()`
2. Remove orphaned `min_sampling_rate` field
3. Add `can_advance_step()` with proper blocking
4. Fix `qa_result` decision routing to block on missing report

### Phase 2.5 - Completion Cascades (Spill-Out)
1. Add `_cascade_work_order_status()` - auto-complete WO when all parts terminal
2. Add WorkOrder→Order status cascade via signal
3. Add `StepCompletionNotifier` for batch_ready, escalation, terminal events
4. Wire ScheduleSlot completion on step finish

### Phase 3 - First Piece Inspection
1. Add `FPIRecord` model
2. Implement FPI auto-flag logic
3. Add FPI override/waive endpoints
4. Wire FPI check into completion blocking

### Phase 4 - Measurements
1. Add `StepExecutionMeasurement` model
2. Implement `is_mandatory` enforcement
3. Add measurement progress tracking
4. Separate from QualityReports sampling flow

### Phase 5 - Overrides
1. Add `StepOverride` model
2. Implement override request/approve workflow
3. Add soft/hard block detection
4. Wire override check into completion logic

### Phase 6 - Undo & Rollback
1. Add `VoidableModel` mixin
2. Add `RecordEdit` audit model
3. Add `StepRollback` model
4. Implement quick undo and full rollback logic
5. Add batch rollback capability

### Future Phases
- Training/qualification integration
- Equipment calibration checks
- Material consumption tracking
- Work instruction acknowledgment
- Time entry auto-close
- ERP sync triggers
