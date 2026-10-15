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

1. Navigate to **Production** > **Processes**
2. Click **New Process**
3. Fill in basic information:

| Field | Description | Required |
|-------|-------------|----------|
| **Name** | Descriptive name | Yes |
| **Description** | Purpose and scope | Yes |
| **Version** | Initial version (e.g., 1.0) | Yes |
| **Part Type** | Default part type (optional) | No |

4. Click **Save**

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
| **Name** | What's measured |
| **Nominal** | Target value |
| **Upper Tolerance** | Max acceptable |
| **Lower Tolerance** | Min acceptable |
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

To activate a process:

1. Complete all steps and configuration
2. Click **Submit for Approval**
3. Select approval template
4. Approvers review
5. On approval, status becomes **Current**

!!! warning "Approval cannot be skipped"
    There is no *Activate* or *Make Current* shortcut for when approval "isn't
    enforced". Submitting for approval is the only route to Current, and it
    refuses outright if the tenant has no **PROCESS_APPROVAL** template:

    > *PROCESS_APPROVAL approval template not found. Please configure approval
    > templates.*

    Two other prerequisites refuse in the same way: the process must still be a
    **draft**, and it must have **at least one step**.

## Duplicating a process

Use **Duplicate as Template** in the Process Flow editor. It copies the whole
process as a new draft, which you then modify and submit for approval.

!!! note "There is no template flag, and no step-level copy"
    A process is not *marked* as a template — duplicating one is the whole
    mechanism. And there is no way to copy a single step's configuration into
    another process.

## Linking to Part Types

Associate process with part types:

1. Open process
2. In **Part Types** section
3. Select part types that use this process
4. Save

Or from Part Type:
1. Open Part Type
2. Select default process
3. Save

## Testing Process

Before activation:

1. Create test order
2. Create test work order with draft process
3. Move parts through steps
4. Verify flow works correctly
5. Check measurements capture
6. Confirm requirements enforce

## Versioning

### Creating New Version

1. Open current process
2. Click **Create New Version**
3. Draft copy created
4. Make changes
5. Submit for approval
6. On approval:
   - New version becomes Current
   - Old version becomes Obsolete
   - In-flight work continues on old version

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
