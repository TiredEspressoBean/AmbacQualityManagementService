# Moving Parts Forward

Moving parts through production steps is a core operation in uqmes. This guide
covers how parts advance and what to do when they don't.

## Understanding Steps

Parts follow a defined process with sequential steps:

```
[Raw Material] → [Machining] → [Inspection] → [Assembly] → [Final QC] → [Complete]
```

Each step represents a manufacturing operation. Parts must complete each step before moving to the next.

## How Parts Advance

**Parts advance by themselves.** There is no "move to next step" button in the
normal flow. Advancement is *event-driven*: it fires whenever a state-changing
event is recorded — a substep completed, a batch sealed, a part split, an
override approved. When the step's requirements are satisfied, the parts move.

So the way to move a part forward is to **do and record the work at its current
step**.

### Working a step

1. Navigate to **Production** > **Work Orders**
2. Open your work order
3. Click **Start Work** and check the parts you'll work on
   (see [Running Work Instructions](../dwi/running.md))
4. In the step player, record each substep and tap **Confirm & next**
5. On the review screen, tap **Complete step**

### What Happens

- Your entries are recorded against the part with your name and a timestamp
- The part advances if the step's requirements are met
- Progress updates automatically

!!! tip "Lot cohesion"
    Parts that have not been split advance **as a cohort** — all parts at the
    same work order and step move together, or none do. A split part advances
    on its own as soon as its own requirements clear. This is the usual reason a
    finished part appears stuck: another part in its lot still has work
    outstanding.

!!! warning "Force advance is for emergencies"
    The work order control page has a force-advance control, labelled
    *"Force advance step (emergency; default flow is event-driven)"*. It bypasses
    the requirements that normally gate a step. Use it to recover from a stuck
    state, not as part of routine operation.

## Quality Reports (Individual Parts)

For detailed quality documentation on individual parts:

### Steps

1. From your work order, find the specific part in the parts list
2. Click **Quality Report**
3. Fill in the form:
   - Operator
   - Machine/equipment used
   - Measurements
   - Status (pass/fail)
4. Submit

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

1. Create a Quality Report against the part with a fail status
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
