# Creating Processes

Build manufacturing workflows for your products.

## Planning Your Process

Before creating in uqmes:

1. **Map current workflow** - Document actual steps
2. **Identify quality gates** - Where inspection occurs
3. **Define measurements** - What data to collect
4. **Note requirements** - Training, equipment, documents
5. **Consider exceptions** - Rework paths, alternatives

## Creating a New Process

### From Process Editor

1. Go to **Data Management** > **Processes** (`/editor/processes`)
2. Click **New Process**
3. Fill in basic information:

| Field | Description | Required |
|-------|-------------|----------|
| **Name** | Descriptive name | Yes |
| **Part Type** | What this process makes, rebuilds or tears down | **Yes** |
| **Category** | Manufacturing, Quality, Maintenance, NPI, or Document Control | No — defaults to Manufacturing |
| **Remanufactured** / **Disassembly** | What kind of work this is. See [Process Overview](overview.md#what-kind-of-process-it-is) | No |
| **Default scrap rate** | Expected loss, 0–1, inherited by steps that set none | No |

4. Click **Save**

!!! note "You do not choose a version number"
    Versioning is handled for you — a new version is created when the process
    changes, and the number follows. There is nothing to type.

Process is created in **Draft** status.

### Building the flow

Once the process exists, its steps and routing are built on the **Process
Flow** editor (`/process-flow`):

1. Open the process and turn on **Edit Mode**
2. **Add Step** for each operation
3. Draw the connections between steps on the graph
4. Click a step to set its properties, and **Advanced** for its gates

This is the surface to use — a step's routing and its properties are edited
together, which is not possible from the legacy step form.

## Adding Steps

### Sequential Steps

1. Open the process in the **Process Flow** editor and turn on **Edit Mode**
2. Click **Add Step**
3. Click the new step to open its properties and enter its details:

| Field | Description |
|-------|-------------|
| **Name** | Step name (e.g., "Machining") |
| **Description** | What happens at this step |
| **Step Type** | See [Step Types](steps.md#step-types) |

4. Save step
5. Repeat for each step

### How steps are ordered

Steps are not ordered by a sequence number you type. The process is a **graph**:
you draw edges between steps in the Process Flow editor, and the edges are the
routing. That is what lets a flow branch at a decision point and rejoin, which a
sequence number cannot express.

See [Step Types](steps.md#step-types) for what the type field offers.

## Configuring Steps

For each step, configure:

### Requirements

- **Measurements** - Data to collect
- **Training** - Required operator training
- **Equipment** - Machines to use
- **Documents** - Work instructions, drawings

### Controls

- **First Piece Inspection** - Require FPI
- **Approval Required** - Need sign-off
- **Sampling Rule** - Inspection sampling

See [Step Configuration](steps.md) for details.

## Measurement Definitions

Add measurements to inspection steps:

1. Open the step
2. Click **Add Measurement**
3. Define measurement:

| Field | Description |
|-------|-------------|
| **Label** | What's measured |
| **Nominal** | Target value |
| **Upper Tolerance** | How far above nominal is acceptable, as a positive amount |
| **Lower Tolerance** | How far below nominal is acceptable, as a positive amount |
| **Unit** | Unit of measure |
| **Required** | Must record to proceed |

See [Measurement Definitions](measurements.md) for details.

## Process Flow

### Linear Process

Simple sequential flow:
```
Step 1 → Step 2 → Step 3 → Complete
```

### With Inspection Points

```
Step 1 → Inspection 1 → Step 2 → Inspection 2 → Complete
```

### With Rework Loop

```
        ┌─────────────────────┐
        │                     │
        ↓                     │
Step 1 → Inspection → Pass → Step 2
              │
              └──→ Fail → Rework → (back to Inspection)
```

## Process Approval

How a new routing is approved depends on the tenant's change-control mode. In
either mode, **Process Actions** offers it only once the **Validation Issues**
panel has no errors and there are no unsaved changes.

- **Simplified:** **Process Actions** > **Approve — Lock for production use**.
  It is approved at once, and the author may approve their own routing.
- **Regulated:** **Process Actions** > **Submit for approval**. The routing moves
  to **Pending approval**, locked, and goes to the approvers on the tenant's
  **Process Approval** template. Its author can't sign it unless that template
  allows self-approval. When they sign, it becomes **Approved**; if they reject
  it, it returns to **Draft**.

!!! warning "Regulated mode has no direct approve"
    In Regulated mode the direct approve is refused, from the editor or the API,
    so a routing's first version is signed by someone else just as every revision
    of it is. Submitting refuses outright if the tenant has no **PROCESS_APPROVAL**
    template:

    > *PROCESS_APPROVAL approval template not found. Please configure approval
    > templates.*

    The process must also still be a **draft**, with **at least one step**.

A draft forked by **Propose Change** belongs to its process change request and is
approved through that request, in either mode. See [Change
Control](../../workflows/change-control/overview.md).

## Duplicating a process

Use **Duplicate as Template** in the Process Flow editor. It copies the whole
process as a new draft, which you then modify and approve as above.

!!! note "There is no template flag, and no step-level copy"
    A process is not *marked* as a template — duplicating one is the whole
    mechanism. And there is no way to copy a single step's configuration into
    another process.

## Linking to Part Types

A process is for **one** part type, named on the process itself when you create
it. There is no multi-select, and there is no field on the part type pointing
back.

To run the same routing on a second part type, duplicate the process and change
the part type on the copy.

## Checking a process before you approve it

!!! warning "You cannot trial a draft on a work order"
    A draft is deliberately unavailable to work orders — that is what *draft*
    means here. So there is no dry run: you cannot push a test part through it
    and watch.

What you can check before submitting:

1. Read the routing in **Process Flow** — every step reachable, every branch
   terminating somewhere
2. Open each step's properties and confirm its measurements, training, sampling
   and documents
3. Confirm the steps that should block a quarantined part have **Block on
   quarantine** set — it is off by default
4. Check **BOM allocation** on any step that consumes material, especially after
   a step copy, which does not carry it

Then approve it, and run the first job with someone watching. The first real
work order *is* the trial; plan for that rather than expecting a sandbox.

## Versioning

### Creating New Version

1. Open current process
2. Click **Create New Version**
3. Draft copy created
4. Make changes
5. Submit for approval
6. On approval:
   - The new version becomes **Approved**
   - The old one becomes **Deprecated**
   - Work already running continues on the old version

### Version Tracking

Parts record which process version they used:
- Historical accuracy
- Audit compliance
- Traceability

## Permissions

| Permission | Allows |
|------------|--------|
| `add_processes` | Create new processes |
| `change_processes` | Edit process configuration |
| `respond_to_approval` | Respond to a process approval request (eligibility also set by the approval template) |
| `delete_processes` | Remove processes |

## Next Steps

- [Step Configuration](steps.md) - Detailed step setup
- [Measurement Definitions](measurements.md) - Configure measurements
- [Process Overview](overview.md) - Concepts reference
