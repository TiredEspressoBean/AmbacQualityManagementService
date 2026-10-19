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

## Quality data on individual parts

Quality data is captured **in the step player**, not from a button on the part.
A substep marked as an inspection point writes a Quality Report alongside its
completion record, so recording the result at the step is what creates the
quality record.

To raise something on a part you are not currently running — or on the lot, the
machine, or the process — see [Flagging
Issues](flagging-issues.md).

## Step Requirements

Some steps have requirements that must be met before passing:

### Measurement Requirements

If a step requires measurements, you record them as you run the step:

1. Open the step in the step player
2. Work through the substeps, entering each measurement where it is asked for
3. Complete the step — the values are saved with the completion record

You do not fill in a Quality Report to enter measurements. The quality report
is produced *by* an inspection-point substep when you record its result.

### Decision Points

Some steps have branching based on results:

- **Pass** → Part continues to normal next step
- **Fail** → Part may route to rework or quarantine
- **Measurement-based** → Routing determined by value

!!! warning "A MANUAL decision point waits for a person"
    Not every decision point branches on its own. A decision point set to
    **manual** holds the part until someone chooses the branch — a Shift Lead,
    QA Inspector, QA Manager, Production Manager or Tenant Admin.

    This is the usual reason a part appears stuck at a step with nothing
    obviously wrong with it: nothing failed, the step is simply waiting on a
    decision nobody has made yet.

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

1. Create a Quality Report against the part with its result set to **FAIL** —
   it has to be FAIL *at creation*. Failing it afterwards opens a disposition
   but does **not** quarantine the part, which leaves somebody deciding a part
   that is still moving
2. Add each defect to the report, with its own error type, count, location and
   severity. Error type is **not** a field on the report itself
3. The part enters quarantine

!!! warning "Quarantine always stops a part shipping — it does not always stop it advancing"
    A quarantined part can never leave the building. Whether it stops at the
    **next step** depends on that step's **Block on quarantine** setting, which
    is **off by default**. On a routing where nobody armed it, a quarantined
    part keeps moving down the line until it reaches shipping.

    If your procedure expects a hold to stop work immediately, check the flag on
    the steps that matter. See [Quarantine](../quality/quarantine.md).

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

## Troubleshooting

### A part won't advance

Work down these, commonest first:

- **Another part in its lot isn't done.** Unsplit parts move as a cohort, so a
  finished part waits on its slowest sibling. This is the usual answer.
- **Required captures are missing** — a substep not completed, or a signature
  block unsigned.
- **The step is waiting on a First Piece Inspection** that nobody has bought off.
- **A manual decision point** is waiting for someone to choose the branch.
- **A completion was voided**, so it no longer satisfies its substep — and that
  holds the whole lot. Check the traveler.
- **The part is quarantined** *and* the step blocks on quarantine.
- **The operator isn't qualified** for the step, and nobody has authorised the
  override.

### "No parts at step"

- All parts may have already been passed
- Refresh the page to see current state

### "Insufficient permissions"

Contact your administrator to request appropriate access.

## Next Steps

- [Recording Measurements](measurements.md) - Capture inspection data
- [Part History](part-history.md) - View transition log
- [Flagging Issues](flagging-issues.md) - Report problems
