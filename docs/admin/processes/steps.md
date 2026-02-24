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

## Creating a Step

1. Open the process
2. Click **Add Step** or go to Steps tab
3. Fill in step details
4. Configure requirements
5. Save

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

Require operator training:

1. Go to **Training** section
2. Click **Add Training Requirement**
3. Select training type
4. Set as required or recommended
5. Save

Operators without required training may be blocked.

### Equipment Requirements

Specify equipment to use:

1. Go to **Equipment** section
2. Click **Add Equipment**
3. Select equipment type or specific equipment
4. Save

Used for:
- Equipment utilization tracking
- Calibration verification
- Routing decisions

### Document Requirements

Link work instructions and references:

1. Go to **Documents** section
2. Click **Link Document**
3. Select document(s)
4. Set as required or reference
5. Save

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

Copy configuration between steps:

1. Open source step
2. Click **Copy Step**
3. Select destination process
4. Adjust as needed
5. Save

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
| `change_step` | Create/edit steps |
| `delete_step` | Remove steps |
| `view_step` | View step configuration |

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
