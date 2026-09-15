# Step Configuration

Configure individual steps within manufacturing processes.

## Step Basics

A step represents a single operation in a process:

| Property | Description |
|----------|-------------|
| **Name** | Display name (e.g., "CNC Machining") |
| **Description** | Detailed description |
| **Sequence** | Order in process |
| **Step Type** | Category of operation |

## Step Types

| Type | Use For |
|------|---------|
| **Production** | Manufacturing operations |
| **Inspection** | Quality checks |
| **Rework** | Repair or correction |
| **Assembly** | Component assembly |
| **Packaging** | Final packaging |
| **Shipping** | Ship preparation |
| **Hold** | Waiting point |

## Where Steps Are Edited

Steps are edited on the **Process Flow** viewer, in the context of the process
graph — not from a standalone step form.

1. Go to **Production** > **Processes** and open the process, or open
   **Process Flow** directly
2. Turn on **Edit Mode**
3. Click a step to open its properties panel
4. Click **Advanced** for the full settings

**Add Step** creates a new step in the flow; **Delete Step** removes the
selected one. Connections between steps are drawn on the graph itself, which is
why this is the right surface — a step's routing and its properties are edited
together.

!!! note "The legacy step form"
    `/StepForm/edit/{id}` still exists and exposes a reduced set of fields.
    It is a legacy route being phased out; use the Process Flow editor.

## Step Properties

The properties panel covers:

| Field | Purpose |
|-------|---------|
| **Name** | Step name |
| **Operation number** | Op number within the routing |
| **Description** | What the step is |
| **Work center** | Where the step runs |

### Timing

| Field | Purpose |
|-------|---------|
| **Needs an operator** | Whether the step is attended |
| **Setup (min)** | Setup time |
| **Cycle, per piece (min)** | Run time per piece |
| **Operator attention** | e.g. tied to the machine for the whole run |

!!! warning "Cycle time feeds capacity planning"
    A step with no cycle time contributes **no load**, so capacity planning
    shows more free capacity than exists and release dates come out too late.
    See [Capacity Planning](../../workflows/scheduling/capacity.md).

### Advanced

| Setting | Purpose |
|---------|---------|
| **Decision point** | The step branches on an outcome |
| **Terminal step** | The routing ends here |
| **Expected duration** | Planned duration |
| **Max visits (rework limit)** | How many times a part may revisit the step |
| **Requires QA signoff** | QA must sign the step off |
| **Sampling required** | Sampling applies at this step |
| **Requires first-piece inspection** | FPI gates the step |
| **Move lot as a unit** | Parts advance as a cohort rather than individually |

## Step Requirements

### Measurement Requirements

Link measurements to collect at this step:

1. In step detail, go to **Measurements**
2. Click **Add Measurement**
3. Select existing measurement definition or create new
4. Set as required or optional
5. Save

Parts cannot advance if required measurements are missing.

### Training Requirements

A training requirement names a **training type** and a **minimum competency
level** (1–4), and is scoped to exactly one of:

| Scope | Meaning |
|-------|---------|
| **Step** | Required to work this step |
| **Process** | Required across the whole process |
| **Equipment type** | Required to operate that equipment |
| **Job role** | Part of a role's competence profile |

!!! note "Not editable on the step form"
    The step edit form has no training section — it covers the step's name,
    operation number, description, part type, first-piece inspection, sampling,
    measurements, fallback, and documents. Training requirements are managed
    from the training surfaces under **Quality** > **Training**, and through
    the API.

!!! tip "This is what gates operator dispatch"
    Scheduling only assigns an operator to a step they are qualified for, at
    the required minimum level. A step whose requirement nobody meets shows up
    as unassignable work — see [Training
    Matrix](../../workflows/tracking/training-matrix.md).

Operators without required training may be blocked.

### Equipment Requirements

Equipment relates to a step in two distinct ways:

| Mechanism | Purpose |
|-----------|---------|
| **Step equipment affinity** | Which equipment this step prefers or requires — used by scheduling |
| **Equipment + roles capture** | What equipment was *actually* used, recorded by the operator on a substep |

!!! note "Not editable on the step form"
    The step edit form has no equipment section. Affinities are configured
    through the work-center and scheduling surfaces; the capture is configured
    when [authoring work instructions](../../workflows/dwi/authoring.md).

Used for:
- Equipment utilization tracking
- Calibration verification
- Routing decisions

### Document Requirements

Link work instructions and references:

1. Open the step in the editor
2. Use **Attach Documents**
3. Select the document(s)
4. Save

Required documents must be attached/accessed to proceed.

## Step Controls

### First Piece Inspection

Enable FPI for this step:

1. Toggle **Requires First Piece Inspection**
2. First part must pass FPI
3. Remaining parts held until FPI passes

#### FPI Scope

Configure when FPI resets:

| Scope | FPI Required |
|-------|--------------|
| **Per Work Order** | Once per work order |
| **Per Shift** | Each shift change |
| **Per Equipment** | Each machine/equipment change |
| **Per Operator** | Each operator change |

See [First Piece Inspection](../../workflows/work-orders/fpi.md).

### QA Sign-off Required

Require QA approval to advance:

1. Toggle **Requires QA Sign-off**
2. QA inspector must approve via QaApproval
3. Parts wait for approval before advancing

### Batch Completion

Synchronize parts in batch:

1. Toggle **Requires Batch Completion**
2. All parts in work order must reach "Ready" status
3. Parts advance together when batch is complete

### Hold Point

Create a mandatory stop:

1. Mark step as **Hold Point**
2. Parts cannot auto-advance
3. Explicit release required

### Auto-Advance

Enable automatic advancement:

1. Toggle **Auto-Advance**
2. Parts move forward when requirements met
3. No manual action needed

### Measurement Failure Blocking

Block parts when measurements fail:

1. Toggle **Block on Measurement Failure**
2. Parts cannot advance if any measurement is out of spec
3. Requires override approval to proceed

### Override Settings

Configure override behavior:

| Setting | Description |
|---------|-------------|
| **Override Expiry Hours** | Hours until override expires (default: 24) |
| **Undo Window Minutes** | Minutes during which completion can be undone (default: 15) |
| **Rollback Requires Approval** | Whether rolling back requires supervisor approval |

## Sampling Configuration

Apply sampling rules at inspection steps:

1. Go to **Sampling** section
2. Select sampling rule or rule set
3. Sampling applies to parts at this step

See [Sampling Rules](../setup/sampling-rules.md).

## Step Transitions

### Normal Flow

Default: parts advance to next step in sequence.

### Conditional Transitions

If branching enabled:
- Define conditions for different paths
- Route based on measurement results
- Route based on part attributes

### Rework Routing

Configure rework destination:
1. When part fails, where does it go?
2. Set rework step in configuration
3. Parts automatically route

## Time Tracking

Configure time tracking:

| Option | Description |
|--------|-------------|
| **Track Duration** | Log time at step |
| **Expected Duration** | Target time for planning |
| **Alert Threshold** | Notify if exceeds time |

## Step Attributes

### Visual Indicators

Configure display:
- **Color** - For Tracker display
- **Icon** - Visual identifier
- **Priority Display** - How urgency shows

### Capacity

For planning:
- **Capacity** - How many parts at once
- **Equipment slots** - Available machines
- **Operator requirements** - Staffing

## Copying Steps

!!! note "Planned Feature"
    There is no step-level copy. A whole process can be duplicated from the
    process flow editor with **Duplicate as Template**; copying the
    configuration of a single step between processes is not available.

## Step Templates

Create reusable step templates:

1. Configure a standard step
2. Save as template
3. When adding steps, start from template
4. Customize as needed

## Ordering Steps

### Reorder Steps

1. Open process
2. Go to Steps list
3. Drag and drop to reorder
4. Or edit sequence numbers
5. Save

### Insert Step

1. Add new step
2. Set sequence between existing steps
3. Other steps maintain relative order

### Remove Step

1. Select step
2. Click **Remove**
3. Confirm
4. Parts at that step need handling

## Step History

View step changes:
- When created/modified
- Who made changes
- What changed

Part of process version history.

## Permissions

| Permission | Allows |
|------------|--------|
| `change_steps` | Create/edit steps |
| `delete_steps` | Remove steps |
| `view_steps` | View step configuration |

## Best Practices

1. **Clear names** - Unambiguous operation names
2. **Appropriate detail** - Not too granular
3. **Document requirements** - Training, equipment, docs
4. **Test flow** - Before production
5. **Review regularly** - Keep current

## Troubleshooting

### Parts Stuck at Step
- Check requirements are met
- Verify user has permission
- Check if approval pending
- Check hold point status

### Requirements Not Enforcing
- Verify requirement is marked "required"
- Check process version is active
- Confirm work order uses this process

## Next Steps

- [Measurement Definitions](measurements.md) - Configure data collection
- [Creating Processes](creating.md) - Build processes
- [Process Overview](overview.md) - Concepts
