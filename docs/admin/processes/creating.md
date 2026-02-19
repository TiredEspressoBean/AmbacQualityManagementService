# Creating Processes

Build manufacturing workflows for your products.

## Planning Your Process

Before creating in Ambac Tracker:

1. **Map current workflow** - Document actual steps
2. **Identify quality gates** - Where inspection occurs
3. **Define measurements** - What data to collect
4. **Note requirements** - Training, equipment, documents
5. **Consider exceptions** - Rework paths, alternatives

## Creating a New Process

### From Process Editor

1. Navigate to **Data Management** > **Processes**
2. Click **+ New Process**
3. Fill in basic information:

| Field | Description | Required |
|-------|-------------|----------|
| **Name** | Descriptive name | Yes |
| **Description** | Purpose and scope | Yes |
| **Version** | Initial version (e.g., 1.0) | Yes |
| **Part Type** | Default part type (optional) | No |

4. Click **Save**

Process is created in **Draft** status.

### From Visual Editor

1. Navigate to **Process Flow**
2. Click **New Process**
3. Use drag-and-drop to build flow
4. Add steps and connections
5. Save

## Adding Steps

### Sequential Steps

1. Open the process
2. Click **Add Step**
3. Enter step details:

| Field | Description |
|-------|-------------|
| **Name** | Step name (e.g., "Machining") |
| **Description** | What happens at this step |
| **Sequence** | Order in process |
| **Step Type** | Production, Inspection, Rework |

4. Save step
5. Repeat for each step

### Step Sequence

Steps are ordered by sequence number:
- Step 1: sequence = 10
- Step 2: sequence = 20
- Step 3: sequence = 30

Using 10s allows inserting steps later.

## Step Types

| Type | Purpose |
|------|---------|
| **Production** | Manufacturing operations |
| **Inspection** | Quality checks |
| **Rework** | Repair/correction |
| **Hold** | Waiting point |
| **Complete** | Final step |

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

### Approval Without Workflow

If process approval isn't enforced:
1. Click **Activate** or **Make Current**
2. Process becomes active
3. Previous version becomes Obsolete

## Duplicating Processes

Create a new process from existing:

1. Open existing process
2. Click **Duplicate**
3. New process created as Draft
4. Modify as needed
5. Activate when ready

Use for:
- New versions
- Similar products
- Template starting points

## Process Templates

Create reusable templates:

1. Build a generic process
2. Mark as template
3. When creating new process, start from template
4. Customize for specific product

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
| `add_process` | Create new processes |
| `change_process` | Edit process configuration |
| `approve_process` | Approve for activation |
| `delete_process` | Remove processes |

## Best Practices

1. **Start simple** - Add complexity as needed
2. **Review with operations** - Validate with users
3. **Test thoroughly** - Before production use
4. **Document changes** - Version notes
5. **Train users** - On new processes

## Next Steps

- [Step Configuration](steps.md) - Detailed step setup
- [Measurement Definitions](measurements.md) - Configure measurements
- [Process Overview](overview.md) - Concepts reference
