# Recording Measurements

Capture inspection and measurement data for parts as they move through production. Measurements provide traceability and feed into SPC analysis.

## Measurement Definitions

Measurements are defined at the step level by administrators. Each definition specifies:

| Property | Description | Example |
|----------|-------------|---------|
| **Name** | What's being measured | "Outer Diameter" |
| **Nominal** | Target value | 25.000 |
| **Upper Tolerance** | Maximum acceptable | +0.010 |
| **Lower Tolerance** | Minimum acceptable | -0.010 |
| **Unit** | Unit of measure | mm |
| **Required** | Must be recorded to proceed | Yes/No |

## Recording Measurements

Measurements are captured as part of the work at a step. There is no standalone
"Record Measurements" button on a part.

### In the step player (most common)

See [Running Work Instructions](../dwi/running.md).

When a step defines measurement captures, they appear as substeps:

1. Open the step's substeps for your part (**Start Work** from the work order)
2. Work through to the measurement substep
3. Enter the measured value
4. Tap **Confirm & next**

The value is evaluated against the specification as you enter it.

### On a Quality Report

A quality report captures measurement results against each measurement
definition — used for inspections and when documenting a non-conformance. See
[Quality Reports](../quality/quality-reports.md).

### During Incoming Inspection

Inspecting a received material lot has its own **Record Measurements** action on
the lot, under **Supply** > **Incoming Inspection**.

!!! note "No bulk measurement entry"
    There is no quick-entry or multi-part measurement screen. Values are
    recorded per part, through one of the paths above.

## Pass/Fail Determination

The system automatically calculates pass/fail:

```
Pass: Lower Limit ≤ Measured Value ≤ Upper Limit
Fail: Measured Value < Lower Limit OR Measured Value > Upper Limit
```

### Visual Indicators

| Result | Indicator |
|--------|-----------|
| **Pass** | Green checkmark |
| **Fail** | Red X |

!!! note "There is no warning zone"
    Evaluation is binary. A measurement definition carries a nominal, an upper
    tolerance and a lower tolerance and nothing else, so a value is either in
    spec or out of it — a reading sitting just inside a limit is not flagged.
    Use [SPC Charts](../../analysis/spc.md) to spot drift before it goes out.

## Measurement Types

There are two, and only two. A definition set to anything else evaluates as
permanently out of spec, so stick to these.

### Numeric Measurements
Standard measured values with tolerances:

- Dimensions (length, diameter, thickness)
- Weight
- Temperature
- Pressure

### Attribute Measurements
Pass/fail only, no numeric value:

- Visual inspection (acceptable/defect)
- Go/No-Go gauge
- Functional test

## Equipment Calibration

Measurements may require calibrated equipment:

1. Select the measurement instrument
2. System verifies calibration is current
3. Measurement is linked to equipment record

!!! warning "Expired Calibration"
    If equipment calibration has expired, you may be blocked from recording measurements or warned to use different equipment.

## Where recorded measurements appear

There is no **Measurements** tab on a part. A measurement recorded at an
inspection-point substep is written as a measurement result against the
**Quality Report** that substep produced, and that report is where the numeric
evidence is listed — name, value, specification, pass/fail, who recorded it and
when.

Numeric results also flow into SPC, so they appear in control charts and
capability analysis without anything further being done to them. See [SPC
Charts](../../analysis/spc.md).

## Correcting a measurement

**A recorded measurement cannot be edited.** There is no edit action, for any
role — a measurement result is evidence, and evidence that can be quietly
rewritten is not evidence. How you fix a wrong value depends entirely on
whether you have confirmed it yet.

### Before you confirm — the review screen

The review screen at the end of the step player lists everything you recorded.
This is the last easy place to fix a mistyped value: tap the entry, correct it,
carry on. Nothing has been sealed as a completion yet.

### After you confirm — QA voids the completion

Once confirmed, the substep completion holding that measurement can only be
**voided**, by QA Inspector, QA Manager, or Tenant Admin, with a reason. The
work is then redone and a fresh measurement recorded.

!!! warning "Voiding is not a quiet correction"
    A voided completion no longer satisfies its substep, so the part stops
    where it is — and because unsplit parts advance as a cohort, its whole lot
    stops with it. The original value stays visible, struck through, with the
    reason and who voided it.

    This is the intended cost. Correcting a sealed quality record is a
    deliberate, visible act, not a typo fix. See [Voiding a
    completion](../dwi/running.md#voiding-a-completion).

## Evidence alongside a measurement

Photos, files and scans are not attached to a measurement. They are **captures
in their own right** — a photo substep, a file substep — recorded next to the
measurement in the same step and sealed the same way.

Authoring the step is what decides whether evidence is required. If an
inspection needs a photo of the setup, the step needs a photo substep; there is
no ad-hoc attach.

## Failed Measurements

When a measurement fails:

### Automatic Quarantine
If configured, parts with failed measurements automatically enter quarantine.

### Manual Review
The operator decides between:

1. **Re-measure**, if the reading itself is suspect — and before the step is
   completed, a corrected value simply replaces the draft
2. **Create a quality report**, which is the route that raises the issue
   formally

!!! note "There is no Flag button on a part"
    Raising an issue means creating a quality report. There is no separate
    flag-for-review action.

### Rework
Rework is a **disposition decision**, not a move the operator makes. Record the
failed measurement, raise a quality report, and let the disposition decide
between Rework, Repair, Use As Is, Scrap or Return to Supplier.

!!! note "There is no 'move to rework step' button"
    Parts do not get pushed to a step by hand. A *Rework* disposition sets the
    part to `REWORK_NEEDED`; the routing follows from that. See
    [Dispositions](../quality/dispositions.md).

## SPC Integration

Measurements feed into Statistical Process Control:

- View control charts for any measurement
- Calculate Cp/Cpk capability indices
- Identify trends and shifts
- Set control limits

See [SPC Charts](../../analysis/spc.md) for details.

## Permissions

| Permission | Allows |
|------------|--------|
| `view_measurementresult` | View measurement history |
| `add_measurementresult` | Record new measurements |
| `delete_measurementresult` | Remove a measurement result entirely. Held by Tenant Admin, QA Manager, Production Manager and Document Controller. |

## Next Steps

- [SPC Charts](../../analysis/spc.md) - Analyze measurement trends
- [Flagging Issues](flagging-issues.md) - Handle failed measurements
- [Moving Parts Forward](moving-parts.md) - Continue production
