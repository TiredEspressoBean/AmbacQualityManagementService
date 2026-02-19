# Moving Parts Forward

Moving parts through production steps is a core operation in Ambac Tracker. This guide covers the methods for passing parts to the next step.

## Understanding Steps

Parts follow a defined process with sequential steps:

```
[Raw Material] → [Machining] → [Inspection] → [Assembly] → [Final QC] → [Complete]
```

Each step represents a manufacturing operation. Parts must complete each step before moving to the next.

## Passing Parts (Primary Method)

The primary way to move parts forward is using the **Pass** button at the order level.

### Steps

1. Navigate to **QA Work Orders**
2. Find the order in the table
3. Click the **Pass** button on the order row
4. The **"Pass Part by Step"** dialog opens
5. Select the step you want to pass (shows step name and part count)
6. Click **Submit**

### What Happens

- All parts at the selected step move to the next step
- Operator and timestamp are recorded
- Progress bar updates automatically
- Toast confirms: "Part passed to next step."

!!! tip "Batch Operation"
    The Pass function moves ALL parts at the selected step. This is efficient for batch processing.

## Quality Reports (Individual Parts)

For detailed quality documentation on individual parts:

### Steps

1. Navigate to **QA Work Orders** and expand an order, or use **QA Parts** table
2. Find the specific part
3. Click **Quality Report**
4. Fill in the form:
   - Operator
   - Machine/equipment used
   - Measurements
   - Status (pass/fail)
5. Submit

### When to Use

- Recording detailed measurements
- Documenting quality checks
- Parts requiring individual attention

## Step Requirements

Some steps have requirements that must be met before passing:

### Measurement Requirements

If a step requires measurements:

1. Use the **Quality Report** form
2. Enter required measurement values
3. Submit the quality report
4. Parts can then be passed

### Decision Points

Some steps have branching based on results:

- **Pass** → Part continues to normal next step
- **Fail** → Part may route to rework or quarantine
- **Measurement-based** → Routing determined by value

## Step Transition Details

Each transition records:

| Data | Description |
|------|-------------|
| **From Step** | Previous step |
| **To Step** | New step |
| **Operator** | Who performed the action |
| **Timestamp** | When it occurred |
| **Decision** | Pass/fail/measurement value |
| **Duration** | Time at previous step |

## Quarantine

If an issue is found:

1. Click **Flag Issue** or create a Quality Report with fail status
2. Select the error type
3. Enter description
4. Part enters quarantine status

Quarantined parts cannot progress until disposition is determined. See [Quarantine](../quality/quarantine.md).

## Handling Quarantined Parts

For parts already in quarantine:

1. Find the part in the quarantine view
2. Click **Edit Disposition** or **Disposition**
3. Process the disposition
4. Once resolved, part can continue or be scrapped

## Cycle Limits and Escalation

If a part visits the same step too many times (rework cycles):

- System tracks visit count
- If max visits exceeded, part escalates
- Escalated parts route to escalation handler
- Prevents infinite rework loops

## Batch Processing

When a step is configured for batch processing:

1. Parts are marked as "Ready for Next Step"
2. System waits for other parts in the batch
3. When batch conditions are met, all parts advance together

## Transition Permissions

| Permission | Allows |
|------------|--------|
| `change_parts` | Basic part movement |
| `can_quarantine_parts` | Flag issues and quarantine |

## Troubleshooting

### "Cannot pass parts"

Check for:

- Parts in quarantine (need disposition first)
- Missing quality reports
- Required measurements not recorded

### "No parts at step"

- All parts may have already been passed
- Refresh the page to see current state

### "Insufficient permissions"

Contact your administrator to request appropriate access.

## Next Steps

- [Recording Measurements](measurements.md) - Capture inspection data
- [Part History](part-history.md) - View transition log
- [Flagging Issues](flagging-issues.md) - Report problems
