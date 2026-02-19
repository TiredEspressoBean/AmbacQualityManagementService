# First Piece Inspection (FPI)

First Piece Inspection ensures production setup is correct before running full batches. This guide covers FPI workflow in Ambac Tracker.

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

1. Navigate to **Admin** > **Processes**
2. Edit the process
3. On the relevant step, enable **Requires First Piece Inspection**
4. Save

When enabled, the first part at that step triggers FPI workflow.

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

## FPI Status Indicators

| Status | Meaning | Icon |
|--------|---------|------|
| **Not Required** | FPI not enabled for this step | — |
| **Pending** | First piece not yet inspected | Yellow |
| **Passed** | FPI approved, batch released | Green |
| **Failed** | FPI rejected, setup adjustment needed | Red |

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

Multiple failures may trigger:

- Supervisor notification
- Quality hold
- Root cause investigation

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
| `submit_fpi` | Submit first piece for review |
| `approve_fpi` | Approve/reject FPI |
| `view_fpi` | View FPI status and records |

## Best Practices

1. **Complete measurements** - Record all required data
2. **Include photos** - Visual evidence of setup
3. **Don't skip** - FPI catches setup errors early
4. **Review promptly** - Don't delay batch release
5. **Document failures** - Track and improve

## Next Steps

- [Recording Measurements](../tracking/measurements.md) - Measurement capture
- [Quality Reports](../quality/quality-reports.md) - Handling failures
- [Process Configuration](../../admin/processes/overview.md) - Configure FPI
