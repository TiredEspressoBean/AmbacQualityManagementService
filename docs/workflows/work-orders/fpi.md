# First Piece Inspection (FPI)

First Piece Inspection ensures production setup is correct before running full batches. This guide covers FPI workflow in uqmes.

!!! example "Demo: FPI Failure Scenario"
    In demo mode, work order WO-2024-0042-A demonstrates FPI workflow:

    - **INJ-0042-025** failed FPI at Assembly step (torque spec exceeded)
    - Operator Mike Rodriguez sees batch is held pending FPI resolution
    - Inspector Sarah Chen can approve or reject the FPI submission
    - Remaining 23 parts are blocked until FPI passes
    - After adjustment, a new first piece must pass before batch releases

## What is First Piece Inspection?

FPI (also called First Article Inspection at setup level) is a quality check on the **first part** produced after:

- New job setup
- Tool change
- Machine adjustment
- Shift change
- Material lot change

The first piece must pass inspection before remaining parts can proceed.

## Enabling FPI

FPI is configured per process step:

1. Open the process in the **Process Flow** editor and turn on **Edit Mode**
2. Click the step, then open **Advanced**
3. Enable **Requires first-piece inspection**
4. Set the **FPI scope** — when the requirement resets

See [Step Configuration](../../admin/processes/steps.md).

When enabled, the first part at that step triggers FPI workflow.

### Scope is per work order

**One buy-off releases the step for the whole work order.** Once a first piece is
signed off at a step, every part at that step may proceed — regardless of shift
change, machine change or who is running it.

!!! warning "The per-shift and per-equipment settings do not hold work"
    A step carries an FPI *scope* setting offering Per Shift and Per Equipment, and
    it does change which inspection **records** get created — a new shift or a
    different machine mints its own. But the gate that actually holds parts ignores
    it: one PASSED or WAIVED inspection satisfies the step for the entire work
    order either way.

    So the extra records read as per-shift control that is not enforced. **Do not
    rely on it.** If a shift or machine change genuinely needs re-verification,
    make it a separate step or a check in the work instruction, where it will
    actually hold.

## FPI Workflow

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Setup   │────▶│ First    │────▶│   FPI    │────▶│ Release  │
│          │     │  Part    │     │  Review  │     │  Batch   │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                      │                 │
                      │                 ▼
                      │          ┌──────────┐
                      │          │   Fail   │
                      │          │  Adjust  │
                      │          └──────────┘
                      │                │
                      └────────────────┘
```

### Step 1: First Part Produced

1. Operator completes setup
2. Produces first part
3. Records measurements on first part
4. Submits for FPI review

### Step 2: FPI Review

1. Inspector reviews first part
2. Checks all required measurements
3. Compares to specifications
4. Approves or rejects

### Step 3: Approval

If approved:

1. First part moves to next step
2. Remaining parts are released for production
3. FPI status shows "Passed"

### Step 4: Rejection

If rejected:

1. First part is flagged
2. Remaining parts are held
3. Operator adjusts setup
4. New first piece is produced
5. FPI repeats

### Conditional Pass

!!! note "Planned Feature"
    Conditional Pass exists as a recordable result, but nothing writes it yet:
    the pass and fail actions each set their own result outright, and the only
    outcomes you can record today are pass, fail, waive and acknowledge. There is
    no path to a conditional pass in the product.

An inspection can also be recorded as a **Conditional Pass** — accepted with a
qualification rather than a clean pass or an outright fail. The record keeps
the outcome separately from the status, so a conditionally-passed FPI reads as
**Passed** on the step while the result itself shows the condition.

Use it when the setup is acceptable to run but something was noted that the
next inspection should re-check.

## FPI Status Indicators

| Status | Meaning | Icon |
|--------|---------|------|
| **Not Required** | FPI not enabled for this step | — |
| **Pending** | First piece not yet inspected | Yellow |
| **Passed** | FPI approved, batch released | Green |
| **Failed** | FPI rejected, setup adjustment needed | Red |
| **Waived** | FPI requirement bypassed (with approval) | Gray |

### Waiving FPI

In some cases, FPI can be waived:

1. Click the **Waive** button on the FPI banner
2. Enter a reason (minimum 10 characters)
3. Confirm the waiver

Parts are released without first piece verification.

Waivers are logged with:
- Who waived
- When waived
- Reason for waiver

Use sparingly - FPI catches setup errors early.

## Viewing FPI Status

### On Work Order
The work order shows FPI status for each step:

```
Step: Machining
FPI: Passed ✓
Parts released: 10/10
```

### On Tracker
Orders with pending FPI show a badge or indicator.

## Performing FPI Inspection

1. First part completes the step
2. System prompts for FPI measurements
3. Enter all required measurements
4. Submit the FPI record
5. Inspector reviews (if separate approval needed)
6. Approve or reject

### FPI Checklist

Some processes use an FPI checklist:

- Visual inspection points
- Dimensional checks
- Functional tests
- Setup verification

Check off each item before approval.

## FPI Documentation

FPI records include:

| Data | Description |
|------|-------------|
| Part | First piece serial number |
| Measurements | All recorded values |
| Inspector | Who performed/approved |
| Timestamp | When approved |
| Equipment | Machine/setup used |
| Attachments | Photos, CMM reports |

## Batch Hold During FPI

While FPI is pending:

- Other parts at that step are held
- Cannot proceed to next step
- Clear visual indicator on Tracker
- "Waiting for FPI" status

After FPI passes:

- All held parts are released
- Can proceed normally
- Batch production continues

## Failed FPI Handling

When FPI fails:

1. **First piece** enters quality workflow (possibly quarantine)
2. **Operator** notified to adjust
3. **Remaining parts** stay held
4. **New first piece** produced after adjustment
5. **Repeat FPI** on new first piece

!!! note "Nothing counts the failures for you"
    Each failure is recorded and emits an `fpi.decided` event, but no escalation
    is built in — nothing notifies on the second failure or places a hold on the
    third. Repeated failures are a judgement someone makes from the record.

    If you want to be told, that is a [notification
    rule](../../admin/setup/notification-rules.md) on `fpi.decided`. The hold, if one
    is warranted, is still placed by hand.

## FPI Metrics

Track FPI performance:

- **First-time pass rate**: FPIs passed on first attempt
- **FPI duration**: Time from submission to approval
- **Repeat FPI rate**: How often FPI must be repeated

## FPI vs FAI

| Concept | Scope | Timing |
|---------|-------|--------|
| **FPI** | Setup verification | Each production run |
| **FAI** | Full design validation | New part number, first production |

FPI is routine; FAI is comprehensive qualification.

## Permissions

| Permission | Allows |
|------------|--------|
| `view_fpirecord` / `add_fpirecord` | See and start a first-piece inspection |
| `sign_off_fpi` | Approve/reject FPI |
| `view_fpirecord` | View FPI status and records |

## Next Steps

- [Recording Measurements](../tracking/measurements.md) - Measurement capture
- [Quality Reports](../quality/quality-reports.md) - Handling failures
- [Process Configuration](../../admin/processes/overview.md) - Configure FPI
