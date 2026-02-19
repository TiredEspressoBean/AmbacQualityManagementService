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

### From Part Detail

1. Open the part
2. Navigate to **Measurements** tab
3. Click **Record Measurements**
4. Enter values for each measurement
5. Click **Save**

### During Step Transition

If measurements are required before moving forward:

1. Attempt to move the part forward
2. A measurement form appears
3. Enter the required values
4. Submit to record and advance

### Quick Entry Mode

For high-volume measurement entry:

1. Select multiple parts at the same step
2. Click **Record Measurements**
3. Enter values - use Tab to move between fields
4. Values apply to selected parts or enter individually
5. Save all measurements

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
| **Warning** | Yellow (near limits) |

### Warning Zones

Some measurements define warning zones (e.g., within 20% of limits). Values in warning zones pass but flag potential drift.

## Measurement Types

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

### Text Observations
Free-text notes:

- Surface condition description
- Serial number verification
- Lot number confirmation

## Equipment Calibration

Measurements may require calibrated equipment:

1. Select the measurement instrument
2. System verifies calibration is current
3. Measurement is linked to equipment record

!!! warning "Expired Calibration"
    If equipment calibration has expired, you may be blocked from recording measurements or warned to use different equipment.

## Measurement History

View all measurements for a part:

1. Open the part detail
2. Go to **Measurements** tab
3. See chronological list of all measurements
4. Each entry shows:
   - Measurement name
   - Recorded value
   - Pass/fail status
   - Date/time
   - Operator
   - Equipment used

## Editing Measurements

To correct a measurement error:

1. Find the measurement in history
2. Click **Edit** (if permitted)
3. Enter the corrected value
4. Provide a reason for the change
5. Save

!!! info "Audit Trail"
    Both original and corrected values are retained in the audit trail.

## Measurement Attachments

Attach evidence to measurements:

- Photos of measurement setup
- Inspection reports
- CMM output files
- Calibration certificates

1. Record the measurement
2. Click **Attach File**
3. Upload supporting documentation

## Failed Measurements

When a measurement fails:

### Automatic Quarantine
If configured, parts with failed measurements automatically enter quarantine.

### Manual Review
The operator must decide:

1. Re-measure (possible measurement error)
2. Flag for quality review
3. Create a quality report

### Rework Loop
If the part can be reworked:

1. Record the failed measurement
2. Move part to rework step
3. Perform corrective action
4. Re-measure

## Bulk Measurement Import

For CMM or automated inspection systems:

1. Navigate to **Import Measurements**
2. Upload CSV or equipment export file
3. Map columns to measurement definitions
4. Review and confirm import
5. Measurements are recorded with import timestamp

### CSV Format
```csv
part_serial,measurement_name,value,equipment_id,timestamp
WA-001,Outer Diameter,25.003,CMM-001,2026-03-15T10:30:00
WA-001,Length,100.002,CMM-001,2026-03-15T10:30:05
WA-002,Outer Diameter,24.998,CMM-001,2026-03-15T10:31:00
```

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
| `view_measurements` | View measurement history |
| `add_measurements` | Record new measurements |
| `change_measurements` | Edit measurements |
| `delete_measurements` | Remove measurements |

## Next Steps

- [SPC Charts](../../analysis/spc.md) - Analyze measurement trends
- [Flagging Issues](flagging-issues.md) - Handle failed measurements
- [Moving Parts Forward](moving-parts.md) - Continue production
