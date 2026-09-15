# Operator Guide

This guide is for production floor operators who move parts through manufacturing steps and record production data in uqmes.

!!! tip "Demo Account"
    In demo mode, log in as **Mike Rodriguez** (mike.ops@demo.ambac.com) to experience the operator workflow with real work queue items like parts INJ-0042-020 (at Assembly) and INJ-0042-022 (at Cleaning).

## Your Role

As an Operator, you:

- Move parts through production steps
- Record measurements and data
- Flag issues when problems occur
- Track work order progress
- Use equipment for operations

## Getting Started

### First-Time Setup

1. Log in with credentials from your admin
2. Review the [Navigation Tour](../getting-started/navigation.md)
3. Familiarize yourself with the Tracker

### Your Main Pages

| Page | Location | Purpose |
|------|----------|---------|
| **Work Orders** | Production > Work Orders | Your main work queue |
| **Inbox** | Personal > Inbox | CAPA tasks and notifications (if assigned) |
| **Tracker** | Tracker | Customer-facing order view |

## Daily Workflow

### 1. Get Your Assignment

Your supervisor assigns you to specific work orders:

1. Check with your supervisor for today's work assignment
2. Note the work order number and operation you're assigned to
3. Review any special instructions

### 2. Find Your Work Order

1. Navigate to **Production** > **Work Orders**
2. Search or filter to find your assigned work order
3. Click to open the work order detail
4. Review parts at your step

### 3. Work on Parts

For each operation:

1. Open the step's work instructions for your part
2. Work through the substeps, recording what each one asks for
3. Complete the step — the parts advance on their own once the step's
   requirements are met
4. Continue to next part or batch

## Moving Parts Forward

**There is no "Pass" button.** Parts advance automatically once the work at a
step is recorded. Your job is to complete the step; the system handles the
transition.

### Working a Step

Full detail: [Running Work Instructions](../workflows/dwi/running.md).

The step player shows **one substep at a time**:

1. Open the step's substeps for your part
2. Record what the substep asks for — a measurement, a check, a signature
3. Tap **Confirm & next** to seal that substep and move to the next one
4. If a substep genuinely does not apply, tap **Mark N/A** and pick a reason
5. At the end you get a **review screen** showing everything you recorded —
   jump back to fix anything that looks wrong
6. Tap **Complete step**

Once the step is complete and its requirements are satisfied, the parts move
forward on their own.

!!! tip "Parts move as a lot"
    Parts that have not been split advance together: all parts at the same work
    order and step move on, or none of them do. If parts seem stuck, it is
    usually because one part in the lot still has outstanding work.

!!! note "First Piece Inspection can hold the step"
    If the step has a pending First Piece Inspection, advancing is blocked for
    every part at that step until the FPI is signed off. **Complete step** then
    becomes the buy-off action for whoever is authorised to sign it.

### Quick Tips

- Complete steps promptly — a lot cannot advance until every part is done
- Use **Mark N/A** rather than guessing a value when something doesn't apply
- Check the review screen before completing; it is the last easy place to fix
  a mistyped measurement

## Recording Measurements

When your step requires measurements:

### Recording Values

Measurements are captured as substeps inside the step player, not from a
separate "Record Measurements" button:

1. Work through the step's substeps until you reach a measurement capture
2. Enter the measured value
3. The system evaluates it against the specification automatically
4. Tap **Confirm & next**

### Reading Pass/Fail

| Indicator | Meaning |
|-----------|---------|
| Green ✓ | Measurement passed |
| Red ✗ | Measurement failed |
| Yellow ! | Warning (near limit) |

### If Measurement Fails

1. Verify your measurement is correct
2. Re-measure if uncertain
3. If confirmed fail, flag the part
4. Follow your supervisor's guidance

## Flagging Issues

There is **no Flag button on a part**. Where a problem goes depends on where
you find it:

- **Working the step** — record the result on the inspection-point substep in
  the step player. That writes the quality record for you.
- **Part already past the step** — tick it in the work order's parts list and
  click **Quarantine**.
- **Bigger than one part** — open the work order and click **Report…**.

See [Flagging Issues](../workflows/tracking/flagging-issues.md) for the full
procedure and when to use each.

### When to Flag

- Part doesn't meet visual standards
- Measurement out of tolerance
- Damage discovered
- Process deviation occurred
- Anything that seems wrong

!!! tip "When in Doubt, Flag It"
    It's better to flag a potential issue than let a bad part continue.

## Using Equipment

If equipment tracking is enabled:

### Selecting Equipment

1. When moving parts, you may be prompted
2. Select the equipment you used
3. System records utilization

### Checking Calibration

Before using measurement equipment:
- Look for calibration status indicator
- Green = current calibration
- Red = overdue, don't use

## Work Orders

### Viewing Work Order Details

1. Navigate to **Production** > **Work Orders**
2. Find your assigned work order
3. See parts by step
4. View work instructions

### Accessing Work Instructions

1. Open the work order
2. Go to **Documents** tab
3. Click linked work instruction
4. Follow procedures

## First Piece Inspection (FPI)

If FPI is required at your step:

### The Process

1. Complete first part
2. Record all measurements
3. Submit for FPI review
4. Wait for approval
5. Once passed, continue with batch

### While Waiting

- Other parts are held automatically
- Continue setup verification
- Don't proceed until FPI passes

## End of Shift

### Handoff

1. Update part status for in-progress work
2. Note any issues in work order
3. Inform next shift of status

### Don't Leave Hanging

- Complete any step you finished, so the lot isn't held up
- Record all measurements
- Flag any open issues

## Common Tasks Quick Reference

| Task | Steps |
|------|-------|
| Move part forward | Complete the step — advancement is automatic |
| Record measurement | Step player → measurement substep → enter value → **Confirm & next** |
| Substep doesn't apply | Step player → **Mark N/A** → pick a reason |
| Finish a step | Step player → review screen → **Complete step** |
| Flag issue | In the player: record it on the inspection substep · Otherwise: tick the part → **Quarantine** |
| View instructions | Open work order → Documents → Click instruction |

## What You CAN'T Do

As an operator, you typically cannot:

- Create or edit orders
- Approve dispositions
- Close CAPAs
- Upload documents
- Manage users

Contact your supervisor for these actions.

## Troubleshooting

### "Cannot move forward"

Check for:
- Required measurements not recorded
- Pending approval
- FPI required but not passed
- Part in quarantine

### "Permission denied"

- You may not have access to this action
- Contact supervisor or admin

### Part not showing

- Check filters on Work Orders page
- Verify correct work order
- Part may be at different step

## Getting Help

- **Your Supervisor**: Process questions, permissions
- **Quality**: Measurement issues, defects
- **IT/Admin**: Login issues, system problems

## Related Documentation

- [Tracker Overview](../workflows/tracking/tracker-overview.md)
- [Moving Parts](../workflows/tracking/moving-parts.md)
- [Recording Measurements](../workflows/tracking/measurements.md)
- [Flagging Issues](../workflows/tracking/flagging-issues.md)
- [First Piece Inspection](../workflows/work-orders/fpi.md)
