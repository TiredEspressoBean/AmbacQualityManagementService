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

### From Process Step

1. Open the process
2. Open the step where measurement is collected
3. Click **Add Measurement** in Measurements section
4. Fill in definition
5. Save

### From Measurement Editor

1. Navigate to **Data Management** > **Measurements** (if available)
2. Click **+ New Measurement**
3. Fill in details
4. Link to step(s)
5. Save

## Measurement Fields

### Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| **Name** | What's being measured | "Outer Diameter" |
| **Nominal** | Target value | 25.000 |
| **Upper Tolerance** | Max acceptable deviation | +0.010 |
| **Lower Tolerance** | Min acceptable deviation | -0.010 |
| **Unit** | Unit of measure | mm |

### Optional Fields

| Field | Description |
|-------|-------------|
| **Description** | Additional context |
| **Measurement Type** | Numeric, Attribute, Text |
| **Equipment Required** | Specific instrument |
| **Procedure Reference** | Document link |
| **Drawing Reference** | Where on drawing |

## Tolerance Specification

### Bilateral Tolerance
Equal deviation both directions:
- Nominal: 25.000
- Upper: +0.010
- Lower: -0.010
- Range: 24.990 to 25.010

### Unilateral Tolerance
Deviation in one direction:
- Nominal: 25.000
- Upper: +0.000
- Lower: -0.010
- Range: 24.990 to 25.000

### Asymmetric Tolerance
Different each direction:
- Nominal: 25.000
- Upper: +0.015
- Lower: -0.005
- Range: 24.995 to 25.015

## Measurement Types

### Numeric
Standard measured values:
- Dimensions (length, diameter)
- Weight
- Temperature
- Force

Includes tolerances, calculates pass/fail.

### Attribute
Go/No-Go checks:
- Visual acceptable/reject
- Functional pass/fail
- Thread gauge go/no-go

Boolean result only.

### Text
Free-form observations:
- Surface condition notes
- Serial number verification
- General observations

No pass/fail calculation.

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

### Required Measurements
- Must be recorded to advance
- Blocks step transition if missing
- Use for critical dimensions

### Optional Measurements
- Can record or skip
- Doesn't block advancement
- Use for reference data

## Measurement Groups

Organize related measurements:

```
Measurement Group: Bore Dimensions
├── Bore Diameter
├── Bore Depth
├── Bore Roundness
└── Bore Surface Finish
```

Groups help organize complex parts.

## Control Plan Integration

Link measurements to control plan:

| Field | Description |
|-------|-------------|
| **Characteristic Number** | Control plan reference |
| **Control Method** | How controlled |
| **Reaction Plan** | What to do if out of spec |
| **Sample Frequency** | How often to measure |

## SPC Configuration

Enable SPC tracking:

1. Toggle **Track for SPC**
2. Set **Subgroup Size** (if applicable)
3. Measurements feed SPC charts

See [SPC Charts](../../analysis/spc.md).

## Equipment Association

Link to measurement equipment:

1. In **Equipment** field
2. Select equipment type or specific instrument
3. System checks calibration status
4. Records which equipment used

## Copying Measurements

Copy between steps or processes:

1. Open source measurement
2. Click **Copy**
3. Select destination step
4. Adjust as needed
5. Save

## Bulk Import

Import measurements from spreadsheet:

```csv
name,nominal,upper_tol,lower_tol,unit,required
Outer Diameter,25.000,0.010,-0.010,mm,true
Length,100.000,0.050,-0.050,mm,true
Surface Finish,32,,, Ra µin,false
```

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

## Best Practices

1. **Match drawing** - Exact specifications
2. **Clear names** - Descriptive, unambiguous
3. **Appropriate precision** - Match capability
4. **Group logically** - Related measurements together
5. **Document changes** - Track spec changes

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
