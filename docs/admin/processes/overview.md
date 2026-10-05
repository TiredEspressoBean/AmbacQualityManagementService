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

## Process Types

### Production Process
Standard manufacturing workflow:
- Sequential steps
- Quality gates
- Measurement collection

### Rework Process
For correcting defects:
- Subset of production steps
- Additional inspection
- Links back to main process

### Incoming Inspection
For receiving material:
- Inspection steps only
- Sampling rules
- Supplier quality tracking

## Process Versioning

Processes support version control:

| Version | Status | Description |
|---------|--------|-------------|
| v1.0 | Obsolete | Original process |
| v2.0 | Obsolete | Added inspection step |
| v3.0 | Current | Updated measurements |
| v3.1 | Draft | Adding new equipment |

### Version Rules
- Only one **Current** version active
- **Draft** versions for development
- **Obsolete** versions archived
- Parts track which version they used

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
| **Step form** (standalone) | **Timing** and **Machines** only — scheduling data shared by every version |
| **Steps list** | Nothing directly. Its row action is *Edit in process*, which opens the flow editor with the step selected |

The standalone step form is **read-only for step content** when the step belongs
to a process, with a banner offering *Edit in [process] vN*. The API refuses the
same edits, so it holds however you reach it:

> This step is part of an approved process version. Open it from a draft of the
> process to change it; the draft gets its own copy.

!!! tip "Why timing and machines are the exception"
    They are not statements about *how the work is done* — they are statements
    about how long it takes and what it runs on, which every version shares.
    Editing them from anywhere is safe, and is why those two sections stay live
    on a form that is otherwise read-only.

## Process Approval

Changes to processes may require approval:

1. Create or edit process (Draft)
2. Submit for approval
3. Reviewers approve changes
4. Process becomes Current
5. Previous version becomes Obsolete

## Linking Processes

### To Part Types
Each part type links to a default process:
- New parts of that type use the process
- Can override per work order

### To Work Orders
Work orders specify which process to follow:
- Usually default from part type
- Can select different process

## Process Configuration Elements

### Steps
Individual operations in sequence.

See [Step Configuration](steps.md).

### Measurements
Data collection requirements per step.

See [Measurement Definitions](measurements.md).

### Requirements
What's needed to complete a step:
- Training requirements
- Equipment requirements
- Document requirements
- Approval requirements

### Branching
Conditional paths through a process, built on the
[Process Flow](#process-flow) graph:

- **Decision points** — a step marked *Decision point* branches on its outcome
  (for example Pass / Fail)
- **Alternative routes** — rework and scrap paths off a failed decision
- **Terminal steps** — where a route ends, with its terminal status

## Viewing Processes

### Process List

Navigate to **Production** > **Processes**

See all processes with:
- Name and description
- Version and status
- Part types using it
- Step count

### Process Detail

Click a process to see:
- Full step sequence
- Each step's requirements
- Linked part types
- Version history

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

Track process performance:

| Metric | Description |
|--------|-------------|
| **Cycle Time** | Average time through process |
| **Step Duration** | Time at each step |
| **Bottleneck** | Longest step |
| **FPY** | First pass yield |
| **Rework Rate** | % requiring rework |

## Permissions

| Permission | Allows |
|------------|--------|
| `view_processes` | View processes |
| `add_processes` | Create processes |
| `change_processes` | Edit processes |
| `respond_to_approval` | Respond to a process approval request (eligibility also set by the approval template) |
| `delete_processes` | Remove processes |

## Next Steps

- [Creating Processes](creating.md) - Build new processes
- [Step Configuration](steps.md) - Configure steps
- [Measurement Definitions](measurements.md) - Define measurements
