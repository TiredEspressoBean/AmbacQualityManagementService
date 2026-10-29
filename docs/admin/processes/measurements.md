# Measurement Definitions

Configure what data to collect during manufacturing and inspection.

## What are Measurement Definitions?

Measurement definitions specify:

- **What** to measure (feature name)
- **Target value** (nominal)
- **Acceptable range** (tolerances)
- **Units** of measure
- **When** to collect (which step)

## Creating Measurements

### From the step

1. Open the step where the measurement is collected
2. In the **Measurement Definitions** section, click **Add Measurement**
3. Fill in the definition
4. Save

!!! note "Which surface"
    In the **Process Flow** editor, select the step and use **Configure
    measurements**.

!!! note "There is a list, but no standalone editor"
    **Data Management** > **Measurement Definitions**
    (`/quality/measurement-definitions`) lists every definition in one place, and carries **Import** and **Export**.
    It is for finding and bulk-loading them.

    **Editing stays on the step**, using the procedure above — a definition
    belongs to the step that collects it, and versions with it.

## Measurement Fields

### Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| **Name** | What's being measured | "Outer Diameter" |
| **Nominal** | Target value | 25.000 |
| **Upper Tolerance** | How far **above** nominal is acceptable | 0.010 |
| **Lower Tolerance** | How far **below** nominal is acceptable | 0.010 |
| **Unit** | Unit of measure | mm |

!!! danger "Enter both tolerances as positive numbers"
    Both are **distances from nominal**, not signed offsets. The limits are worked
    out as `nominal + upper` and `nominal − lower`, so the minus is already applied
    for you.

    Typing `-0.010` into Lower Tolerance gives `25.000 − (−0.010) = 25.010` — the
    lower limit lands **above** nominal, on top of the upper limit, and the
    acceptable range collapses to a single value. Every real part then fails, and
    the spec looks reasonable on screen.

    A tolerance of zero on one side is written as `0`, not as a sign.

### Optional Fields

| Field | Description |
|-------|-------------|
| **Description** | Additional context |
| **Measurement Type** | **Numeric** or **Pass/Fail** — those are the only two. A Pass/Fail definition takes no nominal or tolerances. |
| **Equipment Required** | Specific instrument |
| **Procedure Reference** | Document link |
| **Drawing Reference** | Where on drawing |

## Tolerance Specification

### Bilateral Tolerance
Equal deviation both directions:
- Nominal: 25.000
- Upper: 0.010
- Lower: 0.010
- Range: 24.990 to 25.010

### Unilateral Tolerance
Deviation in one direction:
- Nominal: 25.000
- Upper: 0.000
- Lower: 0.010
- Range: 24.990 to 25.000

### Asymmetric Tolerance
Different each direction:
- Nominal: 25.000
- Upper: 0.015
- Lower: 0.005
- Range: 24.995 to 25.015

## Measurement Types

There are **two**, and no others:

| Type | What it captures |
|------|------------------|
| **Numeric** | A measured value, checked against nominal and tolerances |
| **Pass/Fail** | A go/no-go result. Takes no nominal and no tolerances. |

!!! warning "There is no Attribute or Text type"
    There are two types, numeric and pass/fail. Free-form observations are captured with a **text input** in the work
    instruction, not as a measurement — only measurements are evaluated against
    a specification and feed SPC.

## Units

Common units supported:

| Category | Units |
|----------|-------|
| **Length** | mm, in, m, ft |
| **Weight** | g, kg, oz, lb |
| **Temperature** | °C, °F, K |
| **Pressure** | psi, bar, Pa |
| **Angle** | degrees, radians |
| **Force** | N, lbf |
| **Torque** | Nm, ft-lb |

Custom units can be added.

## Required vs Optional

The definition's **Required** checkbox (*Must be measured to complete step*) is
recorded, but nothing reads it: it does not stop a part moving on.

- **Whether a reading must be taken** is set where it is captured — the step's
  [work instructions](../../workflows/dwi/authoring.md). A substep can't be
  completed with a required capture left blank.
- **Whether an out-of-spec reading holds the part** is the step's **Block on
  out-of-spec measurement** setting, in the flow editor's **Advanced** settings.
  Off, an out-of-spec reading is recorded, but it doesn't hold the part.

## Control plan and drawing reference

**Characteristic number** is the balloon number on the drawing — the AS9102 and
control-plan reference. It is the field that ties a measurement here to the
characteristic on the print.

!!! note "Control method, reaction plan and sample frequency are not fields"
    A measurement definition carries the characteristic number and nothing else
    of the control plan. How the characteristic is controlled and what to do
    when it goes out of spec live in your control plan document; how often it is
    measured is a [sampling rule](../setup/sampling-rules.md).

## SPC

Tick **SPC enabled** on the definition to feed its results into the control
charts. See [SPC Charts](../../analysis/spc.md).

!!! note "No subgroup size on the definition"
    Subgrouping is a property of the chart, not of the measurement.

## Gauges

Two optional fields name the instrument:

| Field | Description |
|-------|-------------|
| **Default equipment** | The preferred gauge — what the operator gets by default |
| **Backup equipment** | The fallback when the default is unavailable |

Which gauge was *actually* used is recorded by the operator at capture time, so
these are defaults rather than a restriction.

## Bulk Import

Import measurements from spreadsheet:

```csv
name,nominal,upper_tol,lower_tol,unit,required
Outer Diameter,25.000,0.010,0.010,mm,true
Length,100.000,0.050,0.050,mm,true
Surface Finish,32,,, Ra µin,false
```

!!! danger "Both tolerance columns are positive — check before you upload"
    `lower_tol` is a **distance below nominal**, exactly as in the form. A negative
    value in that column inverts the limit, and an import applies it to every row
    at once. The result looks like a complete, tidy spec list in which nothing can
    pass.

    If you are adapting a spreadsheet from a drawing that writes tolerances as
    ± or as signed offsets, **strip the signs from the lower column first**. See
    the warning under [Tolerance Specification](#tolerance-specification).

1. Prepare CSV with measurement data
2. Click **Import**
3. Upload file
4. Review and confirm
5. Measurements created

## Measurement History

Track changes to definitions:
- Who changed what
- When changed
- Previous values
- Reason for change

Important for compliance (changes affect specifications).

## Drawing References

Link measurements to drawing callouts:

1. Add **Drawing Reference** field
2. Enter balloon/callout number
3. Link to drawing document
4. Operators can reference drawing

## Permissions

| Permission | Allows |
|------------|--------|
| `add_measurementdefinition` | Create definitions |
| `change_measurementdefinition` | Edit definitions |
| `delete_measurementdefinition` | Remove definitions |
| `view_measurementdefinition` | View definitions |

## Troubleshooting

### Measurement Not Appearing
- Check step assignment
- Verify measurement is active
- Confirm process version

### Wrong Pass/Fail
- Verify tolerances are correct
- Check upper/lower signs
- Confirm unit matches

### Can't Record Value
- Check user has permission
- Verify measurement is enabled
- Check required equipment calibration

## Next Steps

- [Step Configuration](steps.md) - Configure steps
- [Recording Measurements](../../workflows/tracking/measurements.md) - User guide
- [SPC Charts](../../analysis/spc.md) - Analysis
