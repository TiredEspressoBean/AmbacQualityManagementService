# Step Configuration

Configure individual steps within manufacturing processes.

## Step Basics

A step represents a single operation in a process:

| Property | Description |
|----------|-------------|
| **Name** | Display name (e.g., "CNC Machining") |
| **Description** | Detailed description |
| **Step Type** | Category of operation |

There is no sequence number: the connections drawn between steps in the flow
editor are the routing. See [How steps are
ordered](creating.md#how-steps-are-ordered).

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

The type is picked from the **Step Type** menu under **Add Step** when the step
is added.

!!! note "Step type is a flow marker, not a work category"
    It sets how the step reads in the flow editor and, for Decision, Terminal
    and Repair, how it behaves. There is no *Production*, *Assembly*,
    *Packaging*, *Shipping*, *Hold* or *Complete* type.

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

1. Go to **Production** > **Processes** and use the process's **Edit Process**
   row action, or open **Process Flow** directly
2. Turn on **Edit Mode**
3. Click a step to open its properties panel
4. Click **Advanced** for the full settings
5. Click **Save** to store the changes — steps are saved with the process,
   never one at a time

**Add Step** creates a new step in the flow; **Delete Step**, at the foot of the
properties panel, takes the selected one out of it. Connections between steps
are drawn on the graph itself, which is why this is the right surface — a step's
routing and its properties are edited together.

!!! note "The standalone step form"
    `/editor/steps/{id}/edit` exposes a reduced set of fields, and is read-only
    for step content when the step belongs to a process — use the Process Flow
    editor for that. **Timing** and **Machines** stay editable there, because
    they are scheduling data on the step row rather than its controlled
    content; a change there reaches every process version still sharing the
    row. The API refuses the same content edit — see [Where step content is
    edited](overview.md#where-step-content-is-edited).

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
| **QA signoff** | Whether a lot needs QA to release it off this step, and how firmly that release is signed — *Not required*, *Check off* (recorded under their login), or *Signature + password* (they re-enter their own password). At every level, the sign-off is refused to anyone who signed one of the step's substeps on that work order, or who is assigned to or completed a part's open visit to the step on it — *"Segregation of duties: you completed work on this step — a different qualified inspector has to sign it off."* |
| **Sampling required** | Sampling applies at this step |
| **Min sampling rate (%)** | Shown once sampling is required: the minimum percentage of parts sampled at this step |
| **Requires first-piece inspection** | FPI gates the step |
| **FPI scope** | Shown once FPI is required: what one first piece releases — see [FPI Scope](#fpi-scope) |
| **Block on quarantine** | *A quarantined part can't move on from this step until its quarantine is decided.* **Off by default** |
| **Block on out-of-spec measurement** | *A part with an out-of-spec reading at this step can't move on until it's dealt with.* The part is held with *"One or more measurements are out of specification"*. **Off by default** |
| **Sequencing** | The order the step's substeps are worked in — *Sequential* or *Free order*. See [Sequencing](../../workflows/dwi/authoring.md#sequencing) |
| **Move lot as a unit** | Parts advance as a cohort rather than individually |
| **Batch ready threshold (% of lot ready to advance)** | Shown once **Move lot as a unit** is on — see [Moving a lot as a unit](#moving-a-lot-as-a-unit) |

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
4. Save

Whether a reading must be taken is set in the step's [work
instructions](../../workflows/dwi/authoring.md), not here. A reading outside its
limits holds the part only when the step's **Block on out-of-spec measurement**
is on.

### Training Requirements

A training requirement names a **training type** and a **minimum competency
level** (1–4), and is scoped to exactly one of:

| Scope | Meaning |
|-------|---------|
| **Step** | Required to work this step |
| **Process** | Required across the whole process |
| **Equipment type** | Required to operate that equipment |
| **Job role** | Part of a role's competence profile |

!!! note "Where a step's training is set"
    In the flow editor, the step panel's **Configuration** > **Required
    Training** opens *Required Training — "&lt;step&gt;"*, the competencies an
    operator must hold for the operation. Like the step's other dialogs, it is
    editable on a draft with **Edit Mode** on. The standalone step form has no
    training section.

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
| **Machines** | The machines that can run this step, and how well — used by scheduling, which only places the step on machines listed here |
| **Equipment + roles capture** | What equipment was *actually* used, recorded by the operator on a substep |

!!! note "Where each is set"
    **Machines** is in the flow editor's step panel (**Configuration** >
    **Machines**), and is also the **Machines** card on the standalone step
    form. The capture is configured when [authoring work
    instructions](../../workflows/dwi/authoring.md).

Used for:
- Equipment utilization tracking
- Calibration verification
- Routing decisions

### Document Requirements

Attach work instructions, SOPs, drawings and specs to a step from the step
panel's **Configuration** > **Documents**, or under **Attach Documents** on the
standalone step form.

Attached documents are reference for the people working the step. They do not
gate it: nothing checks that a document was opened before a part moves on.

## Step Controls

### First Piece Inspection

Enable FPI for this step:

1. Switch on **Requires first-piece inspection** in the step's **Advanced**
   settings
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

1. Set **QA signoff** to *Check off* or *Signature + password* (it is a three-way choice, not a toggle)
2. QA inspector must approve via QaApproval
3. Parts wait for approval before advancing

### Moving a lot as a unit

Tick **Move lot as a unit** in the step's Advanced settings. Parts then advance
as a cohort rather than individually: the lot moves once enough of it is ready,
which is what **Batch ready threshold (% of lot ready to advance)** sets — the
share of the lot that must be READY before the batch goes. It is not a pass/fail
threshold. It defaults to 100%, the whole lot.

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
    send-out is refused: *"&lt;Vendor&gt; has no active qualification for &lt;process&gt;.
    Qualify them for it, or send the parts to a vendor who is."*

    It refuses rather than holds, because once parts have gone the work is
    already being done to them. Leave the field blank and nothing is checked.

    Spell the process the same way here and on the qualification — *Nitriding*
    on the step will not match *Nitride* on the vendor.

See [Outside Processing](../../workflows/supply/outside-processing.md) for
sending parts out and receiving them back.

### Settings that are enforced but have no control

These are real properties of a step, and the advancement gate honours them — but
**nothing in the product sets them**: the step editor has no control for them,
the API does not expose them, and there is no admin screen for steps. Every step
runs on the defaults below unless they are changed directly in the database.

| Setting | Effect | Default |
|---------|--------|---------|
| **Block on measurement failure** | Parts cannot advance if any measurement is out of spec | Off |
| **Block on SPC violation** | Parts cannot advance if an SPC-enabled measurement is out of control | Off |
| **Override expiry hours** | How long an override stays good before it must be re-approved | 24 |
| **Undo window minutes** | How long after completing a step it can be undone without approval | 15 |
| **Rollback requires approval** | Whether rolling a part back needs supervisor approval | On |

!!! warning "You can be held by a setting you cannot see"
    If parts are blocked at a step and nothing in the editor explains why, one
    of these may be on. The undo window and rollback rule in particular are
    enforced at runtime. A rollback inside the window still needs approval while
    **Rollback requires approval** is on (*"Rollback requires approval"*); past
    the window it is sent for approval rather than refused — *"Past the 15-minute
    undo window — the rollback needs approval"*.

**Auto-advance** is different again: it lives on the step's place *in a
particular process*, not on the step, and defaults to **on**. It is settable
through the API but has no control in the editor either.

## Sampling Configuration

Apply sampling rules at inspection steps from the step panel's
**Configuration** > **Sampling Rules**. Authoring them takes the sampling
permissions, not only the step ones.

See [Sampling Rules](../setup/sampling-rules.md).

## Step Transitions

Parts follow the connections drawn between steps on the graph. There is no
separate sequence to maintain.

### Decision points

A **Decision** step, or any step with **Decision point** on, branches on an
outcome. Its **Decision type** says how the outcome is decided:

- *Based on QA Pass/Fail*
- *Based on Measurement Threshold*
- *Manual Operator Selection*
- *Based on Quality Gate (aggregate signal)*

Where rejected items go is a connection: draw it on the graph, or pick a step
under **Route rejected items to…** and click **Add**.

### Rework limit

A **Rework** step's **Max visits before escalation** — **Max visits (rework
limit)** under **Advanced** on other steps — caps how many times a part may come
back to the step. Blank is unlimited.

## Copying Steps

There is no step-level copy, and no step templates. A whole process can be
duplicated from the process flow editor with **Duplicate as Template**; copying
the configuration of a single step between processes is not available.

## Removing a Step

In **Edit Mode**, select the step and click **Delete Step** at the foot of its
properties panel, then **Save**. The step is taken out of this process only; the
step row itself is kept, because other versions of the process may share it.

A step that parts have already been worked at can't be removed. The save is
refused — *"Cannot remove steps with execution history: &lt;steps&gt;."* — and
the editor shows *Failed to save process*.

## Step History

A step's changes — when, who and what — are on the **History** card of the
standalone step form.

## Permissions

| Permission | Allows |
|------------|--------|
| `view_steps` | View step configuration |
| `change_steps` | Editing steps in Process Flow. **Edit Mode** needs `change_processes` as well, because the steps are saved with the process |
| `delete_steps` | Archive a step that belongs to no process, from the standalone step form. Taking a step out of a process is **Delete Step** in Process Flow, which needs only the editing permissions |

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
