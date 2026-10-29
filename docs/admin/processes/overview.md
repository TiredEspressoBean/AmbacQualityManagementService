# Process Overview

Processes define manufacturing workflows in uqmes. This guide explains process concepts and structure.

## What is a Process?

A **Process** is a defined sequence of steps for manufacturing a part type:

```
Raw Material → Machining → Inspection → Assembly → Final QA → Complete
```

Processes determine:
- What steps parts go through
- What's required at each step
- Quality control points
- Measurement requirements

## Process Structure

```
Process
  └── Step 1: Raw Material
        └── Requirements (none)
  └── Step 2: Machining
        └── Equipment: CNC Mill
        └── Work Instructions: WI-001
  └── Step 3: Inspection
        └── Measurements: Diameter, Length
        └── Sampling: AQL 2.5
  └── Step 4: Assembly
        └── Requirements: Training X
  └── Step 5: Final QA
        └── Measurements: All dimensions
        └── Approval: QA sign-off
  └── Step 6: Complete
```

## What kind of process it is

There is no "process type" field. What a process is for comes from three
separate things:

| Setting | What it decides |
|---------|-----------------|
| **Category** | Manufacturing, Quality, Maintenance, New Product Introduction, or Document Control. Routing and reporting |
| **Remanufactured** | This process rebuilds an existing unit rather than making a new one |
| **Disassembly** | This process is a teardown, and may be picked when a core is torn down |

A part type can have several processes — a manufacturing routing and one or more
teardowns — and the work order picks which runs.

**Remanufactured** is the **Remanufacturing** switch, on the New Process dialog
and in the flow editor's **Process Settings**. **Category** and **Disassembly**
have no control in the product; they are set through the API
(`/api/Processes/`).

### Expected scrap

A process carries a **default scrap rate**, a fraction from 0 to 1, which its
steps inherit unless they set their own. A step's own rate is its **Expected
scrap (%)** in the flow editor; the process default has no control in the
product and is set through the API (`/api/Processes/`).

!!! tip "This is what makes a work order release 11 to ship 10"
    The rate grosses up the started quantity so the job still finishes the number
    asked for. Leaving it at zero is a claim that nothing is ever lost, and the
    cost of that claim is a short shipment discovered at the end.

## Process Versioning

A process has a **status**, and new versions are created rather than edited in
place:

| Status | Means |
|--------|-------|
| **Draft** | Editable, and not available to work orders |
| **Pending approval** | Submitted, waiting on its approvers |
| **Approved** | Locked, and what new work orders use |
| **Deprecated** | Still works for the jobs already running it, hidden from new ones |

When a revision is approved, the version it replaces keeps its **Approved**
status but is no longer the current version, so new work orders stop picking it.
**Deprecated** is a separate, deliberate action (**Process Actions** >
**Deprecate**) on an approved process.

!!! important "Deprecated is not deleted, and that is the point"
    A job that started on last year's routing finishes on last year's routing.
    Deprecating stops new work picking it up without disturbing work in flight —
    which is also why the version a part ran is readable long after.

### Versions share their steps

A process, its later versions and its copies **share the same step rows**. That is
deliberate: it is what lets any version's routing be read back as it stood on a
given date, rather than as it looks today.

The consequence is the thing to understand: editing a step could change what an
approved version says happened. So it doesn't.

### A draft takes its own copy

When a **draft** edits a step that something else depends on, the draft first gets
a **copy of its own**, and edits that. The other versions keep the original. You
will see:

> This draft now has its own copy of the step…

What triggers it is any edit to the step or to anything hanging off it — saving
step fields, opening one of the step panel's dialogs, editing its substeps, or
changing its timing.

The copy is taken **once**. Later edits on that draft land on the copy in place,
so you do not get a new step version per keystroke.

!!! note "A step used by nothing else is edited in place"
    The copy is only taken when the row is genuinely depended on elsewhere:
    another process links it, work has already been run at it, or parts are
    sitting at it right now. A step that belongs to this process alone is simply
    edited — no copy, no toast.

    So on a young process you may never see this happen, and on a mature one you
    will see it constantly. Both are correct.

The copy carries the step's **measurements, sampling rules, training, machines,
timing, substeps and documents**, so the draft is a faithful starting point
rather than a stripped one.

!!! warning "BOM allocation does not follow the copy"
    Which BOM line is *consumed at this step* is not carried over — a line points
    at one step, and BOMs version on their own lifecycle. Check it after a copy is
    taken on a step that consumes material.

### Where step content is edited

| Where | What you can change |
|-------|--------------------|
| **Process flow editor**, on a draft | Everything: name, description, inspection, measurements, sampling, training, substeps |
| **Step form** (standalone) | **Timing** and **Machines** only — scheduling data on the step row, so a change there reaches every version that uses that row |
| **Steps list** | Nothing directly. Its row action is *Edit in process*, which opens the flow editor with the step selected |

The standalone step form is **read-only for step content** when the step belongs
to a process, with a banner offering *Edit in &lt;process&gt; · v&lt;n&gt;*.
The API holds the same line. An edit of the step's own content
(`PATCH`/`PUT /api/Steps/<id>/`) that does not name the draft it is for
(`?process=<draft>`) is refused while the step belongs to any process that is
not archived — draft or approved:

> This step is part of a process. Its content is edited there, so every other
> version of the process keeps the step as it was. Timing and machines can
> still be changed here.

Archiving, the operation number, the work center and timing still save
through that call.

A change to a step's measurement definitions, training requirements or
sampling rules is refused while any process using the step is out of draft:

> This step is part of an approved process version. Open it from a draft of the
> process to change it; the draft gets its own copy.

!!! tip "Why timing and machines are the exception"
    They are not statements about *how the work is done* — they are statements
    about how long it takes and what it runs on. Changed on the step form, they
    apply to the step row itself, and so to every version still sharing it; a
    draft that has taken its own copy has its own timing and machines, edited
    from the flow editor like the rest of its content.

## Process Approval

A new routing is created as a **Draft**. What happens next depends on the
tenant's change-control mode:

- **Simplified:** **Approve** it from the editor's **Process Actions**; it becomes
  **Approved** at once, and work orders can use it.
- **Regulated:** **Submit for approval**, which moves it to **Pending approval**.
  Its approvers respond; on approval it becomes **Approved**, on rejection it
  returns to **Draft**. Its author can't sign it unless the template allows
  self-approval.

Who may respond comes from the approval template, not from `change_processes`.
See [Approvals](../../workflows/approvals/overview.md). A revision of an approved
routing goes through a process change request instead. See [Creating
Processes](creating.md#process-approval).

## Linking Processes

### To Part Types

The link runs from the **process** to the part type, not the other way: a
process names the part type it is for, and a part type has no default-process
field.

So a part type's processes are whichever processes point at it. Create the
process against the type.

### To Work Orders

A work order names the process it follows, chosen from the approved processes
for its part type.

## Process Configuration Elements

### Steps
Individual operations in sequence.

See [Step Configuration](steps.md).

### Measurements
Data collection requirements per step.

See [Measurement Definitions](measurements.md).

### Requirements
What a step asks of the people and machines working it:
- Required training
- Machines that can run it
- Documents, for reference
- QA signoff

### Branching
Conditional paths through a process, built on the
[Process Flow](#process-flow) graph:

- **Decision points** — a step marked *Decision point* branches on its outcome
  (for example Pass / Fail)
- **Alternative routes** — rework and scrap paths off a failed decision
- **Terminal steps** — where a route ends, with its terminal status

## Viewing Processes

### Process List

The processes list is at `/editor/processes`, reached from the sidebar
(**Production** > **Processes**) or through **Data Management**. Its columns are
**Name**, **Status**, **Updated At**, **Number of Steps** and **Reman Process**.
Each row has:

- **View** — the process's record view
- **Edit Process** — opens it in **Process Flow**, below
- **Delete Process** — see [Deleting a process](#deleting-a-process)

**New Process** opens a dialog for the name and part type, then opens the new
process in Process Flow. See [Creating Processes](creating.md#creating-a-new-process).

!!! tip "The list is not where you build a routing"
    The steps, the order they run in, and the process's own settings are all
    edited in **Process Flow**.

### Deleting a process

**Delete Process** works only on a **draft**. Once a process is out of draft it
is refused:

> &lt;process&gt; is out of draft, so it can't be edited or deleted.

Deleting archives the process
rather than erasing it: its history is kept. The processes list has no **Show
archived**, so a deleted draft can't be brought back from there — see [Show
archived, and Restore](../data/data-management.md#show-archived-and-restore). An approved process leaves new work through **Deprecate** or a
newer version instead.

### Process Flow

**Process Flow** (`/process-flow`) is the editor for a process's steps and
routing — not an optional extra view:

- The routing as a flowchart, including branches and decision points
- **Edit Mode** to add, connect, and delete steps
- A properties panel per step (name, operation number, work center, timing)
  with an **Advanced** section for its gates
- A **Substeps** control opening that step's work instructions

See [Step Configuration](steps.md).

## Process Metrics

!!! note "There is no per-process performance view"
    Nothing reports cycle time, yield or rework rate *for a process*. The
    numbers that exist live elsewhere and are grouped differently:

    | What you want | Where it actually is |
    |---------------|----------------------|
    | Cycle and setup times | **Step timings** — a planning *input* you author, not a measurement of what happened |
    | Constraint / bottleneck | [Capacity planning](../../workflows/scheduling/capacity.md), by resource |
    | First pass yield, defect Pareto | Per **part type**, on its record view (**View** on the part types list) |
    | Rework rate | The quality dashboard, tenant-wide |

    Be careful with the first row in particular: a step's cycle time is what you
    told the scheduler to expect. It is not evidence of how long the work takes.

## Permissions

| Permission | Allows |
|------------|--------|
| `view_processes` | View processes |
| `add_processes` | Create processes |
| `change_processes` | Edit processes. **Edit Mode** in Process Flow needs `change_steps` as well |
| `respond_to_approval` | Respond to a process approval request (eligibility also set by the approval template) |
| `delete_processes` | Delete (archive) a draft process |

## Next Steps

- [Creating Processes](creating.md) - Build new processes
- [Step Configuration](steps.md) - Configure steps
- [Measurement Definitions](measurements.md) - Define measurements
