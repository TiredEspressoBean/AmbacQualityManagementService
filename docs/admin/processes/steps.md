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

| Type | What it marks |
|------|---------------|
| **Task** | Ordinary work. The default. |
| **Start** | Where the flow begins |
| **Decision** | A branch point — see *Decision Points* |
| **Rework** | Repair or correction |
| **Timer / Wait** | A wait, e.g. a cure or a soak |
| **Terminal** | An end of the flow |
| **Receiving Inspection** | Incoming acceptance |
| **Repair** | A reman repair node, reached only when its repair code is raised |

!!! note "Step type is a flow marker, not a work category"
    It sets how the step reads in the flow editor and, for Decision, Terminal
    and Repair, how it behaves. There is no *Production*, *Assembly*,
    *Packaging*, *Shipping*, *Hold* or *Complete* type — older lists on this
    and other pages named categories that do not exist.

!!! important "A step belongs to a part type — or, if it is Receiving Inspection, to a material"
    This is enforced in the database, not just in the form, and it is the one
    place the two diverge:

    - Every ordinary step belongs to **a part type**.
    - A **Receiving Inspection** step may instead belong to **a material** —
      which is how incoming acceptance is authored for bulk stock that is never
      a unit.

    It is strictly one or the other. A step cannot carry both, and a
    material-owned step that is not Receiving Inspection is rejected outright.

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

!!! note "The standalone step form"
    `/editor/steps/{id}/edit` exposes a reduced set of fields, and is read-only
    for step content when the step belongs to a process — use the Process Flow
    editor for that. **Timing** and **Machines** stay editable there, because
    they are scheduling data every version shares.

    The old `/StepForm/edit/{id}` redirects to it for now.

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
| **QA sign-off** | Whether a lot needs QA to release it off this step, and how firmly that release is signed — *Not required*, *Check off* (recorded under their login), or *Signature + password* (they re-enter their own password). Whoever did the step's own work is always refused, at every level. |
| **Sampling required** | Sampling applies at this step |
| **Requires first-piece inspection** | FPI gates the step |
| **Move lot as a unit** | Parts advance as a cohort rather than individually |
| **Block on quarantine** | A quarantined part cannot advance off this step. **Off by default** |

!!! warning "Block on quarantine is off unless you set it"
    This is the setting people assume is global behaviour. A quarantined part
    can **never ship** — that is unconditional. But it keeps moving from step to
    step unless the step it is at has this flag.

    So if your procedure is "a held part stops at the next operation", arm it on
    the operations where that matters, and be ready to say which ones have it.
    Arming every step is also legitimate; the default simply is not that.

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

!!! note "The gate refuses, it does not warn"
    An operator whose record does not meet a step's training requirement is
    **stopped**, and told what is missing — *"Level 1, needs Level 2"*. It is
    not a warning they can click past.

    A supervisor can authorise the start anyway, with a reason, and the
    authorisation is written onto the step execution: who was authorised, who
    authorised it, what was missing, and when. That is a recorded business
    decision, not a way to make the requirement disappear.

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

The **FPI scope** select decides what one passed or waived first piece releases.
Each option is a real gate; the editor shows its hint under the select.

| Scope | Hint | Effect |
|-------|------|--------|
| **Per Work Order** | *One first piece releases this step for the whole work order.* | One buy-off releases the step for every part on the work order |
| **Per Shift** | *Each shift day needs its own first piece on the work order.* | Keyed by the shop-floor date: a pass on another day does not release today's run |
| **Per Equipment** | *Each machine needs its own first piece on the work order. A part with no machine recorded is held.* | Keyed by the production machine on the part's visit to the step — from the machine authored on the step or the live schedule, or set by the operator. A pass on another machine does not release this one |

See [First Piece Inspection](../../workflows/work-orders/fpi.md).

### QA Sign-off Required

Require QA approval to advance:

1. Set **QA sign-off** to *Check off* or *Signature + password* (it is a three-way choice, not a toggle)
2. QA inspector must approve via QaApproval
3. Parts wait for approval before advancing

### Moving a lot as a unit

Tick **Move lot as a unit** in the step's Advanced settings. Parts then advance
as a cohort rather than individually: the lot moves once enough of it is ready,
which is what **Pass threshold** sets — the fraction of the cohort that must be
READY before the batch goes.

!!! note "The field is named differently underneath"
    The stored field is `requires_batch_completion`. If you meet that name in
    the API or an export, it is this setting.

### Outside processing

A step done by a vendor — plating, heat treat, specialist machining — is marked
**Outside process (subcontract)** in the step's properties. That reveals:

| Field | What it does |
|-------|--------------|
| **Default vendor** | Who the parts usually go to. Can be changed per shipment |
| **Special process** | The special process this step performs, e.g. *Heat treat*. Blank by default |
| **Turnaround (calendar days)** | How long the scheduler reserves for the vendor. Blank uses the vendor's own default, then the organisation's |

!!! important "Special process is a gate at send-out"
    With **Special process** set, parts can only be sent to a vendor holding an
    **active** (approved or conditional, in-date) supplier qualification for a
    special process with the **same name** — matched ignoring case. Otherwise
    send-out is refused: *"<Vendor> has no active qualification for <process>.
    Qualify them for it, or send the parts to a vendor who is."*

    It refuses rather than holds, because once parts have gone the work is
    already being done to them. Leave the field blank and nothing is checked.

    Spell the process the same way here and on the qualification — *Nitriding*
    on the step will not match *Nitride* on the vendor.

See [Outside Processing](../../workflows/supply/outside-processing.md) for
sending parts out and receiving them back.

### Settings that are enforced but have no control

These are real properties of a step, and the advancement gate honours them — but
**the step editor has no control for them**, so you cannot see or change them
from the product. They are set through the Django admin.

| Setting | Effect | Default |
|---------|--------|---------|
| **Block on measurement failure** | Parts cannot advance if any measurement is out of spec | Off |
| **Block on SPC violation** | Parts cannot advance if an SPC-enabled measurement is out of control | Off |
| **Override expiry hours** | How long an override stays good before it must be re-approved | 24 |
| **Undo window minutes** | How long after completing a step it can still be undone | 15 |
| **Rollback requires approval** | Whether rolling a part back needs supervisor approval | On |

!!! warning "You can be held by a setting you cannot see"
    If parts are blocked at a step and nothing in the editor explains why, one
    of these may be on. The undo window and rollback rule in particular are
    enforced at runtime and produce refusals — *"Undo window expired (15
    minutes)"* — that read as bugs when you don't know the setting exists.

**Auto-advance** is different again: it lives on the step's place *in a
particular process*, not on the step, and defaults to **on**. It is settable
through the API but has no control in the editor either.

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
