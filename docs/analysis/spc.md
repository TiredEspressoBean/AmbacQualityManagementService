# SPC Charts

Statistical Process Control (SPC) uses charts to monitor process stability and capability.

## What is SPC?

SPC applies statistical methods to:

- **Monitor** process variation
- **Detect** shifts and trends
- **Prevent** defects before they occur
- **Improve** process capability

## Accessing SPC

Navigate to **Analytics** > **SPC** or `/spc`

## Control Charts

The system supports three chart types, selected via the **Chart Type** toggle:

### X̄-R (X-bar and Range)
For subgroups of 2-8 samples. Uses Range to estimate variation.

- **X̄ Chart**: Tracks subgroup averages, detects shifts in process centering
- **R Chart**: Tracks range within subgroups, detects changes in variation

### X̄-S (X-bar and Std Dev)
For subgroups of 9+ samples. Uses Std Dev for better accuracy.

- **X̄ Chart**: Same as above
- **S Chart**: Uses standard deviation instead of range
- Auto-selected when subgroup size > 8

### I-MR (Individual and Moving Range)
For individual measurements (n=1).

- **Individual X**: Each point is one measurement
- **Moving Range**: Variation between consecutive points
- Use for: low-volume, destructive testing, or continuous processes

## Reading Control Charts

```
UCL ─────────────────────────────────────
         *    *
    *        *   *  *    *
CL  ─────*────────────────*────*──────────
           *     *    *      *
LCL ─────────────────────────────────────
```

| Element | Meaning |
|---------|---------|
| **UCL** | Upper Control Limit |
| **CL** | Center Line (average) |
| **LCL** | Lower Control Limit |
| **Points** | Individual measurements or subgroup averages |

## Control Limits vs Specification Limits

| Type | Source | Purpose |
|------|--------|---------|
| **Control Limits** | Process data (3σ) | Monitor stability |
| **Specification Limits** | Engineering/customer | Define acceptance |

A process can be in control but not capable (or vice versa).

## Selecting Data

### Measurement Selection

Use the dropdowns at the top to select:

1. **Process** - The manufacturing process
2. **Step** - The specific step within the process
3. **Measurement** - The measurement definition to analyze

### Chart Settings

| Setting | Options | Description |
|---------|---------|-------------|
| **Chart Type** | X̄-R, X̄-S, I-MR | Auto-selects X̄-S for subgroups > 8 |
| **Date Range** | 30, 60, 90, 180 days | How far back to pull data |
| **Subgroup Size (n)** | 2-25 | Number of consecutive measurements per point |

Standard practice is subgroup size of 5. Larger subgroups detect smaller shifts but require more data.

## Chart Display

The SPC view shows:

- Control chart with data points
- Control limits (calculated)
- Specification limits (from measurement definition)
- Out-of-control points highlighted
- Trend indicators

## Out-of-Control Rules

Points are flagged for:

| Rule | Description |
|------|-------------|
| **Rule 1** | Point beyond 3σ (outside control limits) |
| **Rule 2** | 9 points in a row on same side of center |
| **Rule 3** | 6 points trending in same direction |
| **Rule 4** | 14 points alternating up and down |
| **Rule 5** | 2 of 3 points beyond 2σ |
| **Rule 6** | 4 of 5 points beyond 1σ |

## Capability Indices

### Cp (Process Capability)
Measures potential capability:

```
Cp = (USL - LSL) / (6σ)
```

| Cp Value | Interpretation |
|----------|----------------|
| < 1.0 | Not capable |
| 1.0 - 1.33 | Marginally capable |
| 1.33 - 1.67 | Capable |
| > 1.67 | Highly capable |

### Cpk (Process Capability Index)
Accounts for centering:

```
Cpk = min[(USL - μ) / 3σ, (μ - LSL) / 3σ]
```

Low Cpk with higher Cp indicates centering issue.

### Pp and Ppk (Performance)
Based on overall variation (not just within-subgroup):

- Pp/Ppk use overall standard deviation
- Compare to Cp/Cpk for stability assessment

## Capability Summary

The SPC page shows:

| Metric | Value | Status |
|--------|-------|--------|
| Cp | 1.45 | Capable |
| Cpk | 1.32 | Capable |
| Mean | 25.002 | Centered |
| Std Dev | 0.003 | - |
| USL | 25.010 | - |
| LSL | 24.990 | - |

## Baseline Management

### Freezing Limits

Once your process is stable, lock the control limits:

1. Verify process is stable (no red flags, random scatter)
2. Click **Freeze Limits**
3. Control limits are locked for ongoing monitoring
4. Future data is compared against frozen baseline

### Updating Baseline

When process improves significantly:

1. Review new stable data period
2. Click **Update Baseline**
3. New limits replace old
4. Document reason for change (required)

## Histogram

View distribution of measurements:

- Normal curve overlay
- Specification limits shown
- Visual capability assessment

## SPC Reports

Generate reports:

### Single Measurement Report
- Control chart
- Capability summary
- Data table
- Out-of-control events

### Comparison Report
- Multiple measurements
- Side-by-side capability
- Trend comparison

### Export Options
- PDF for distribution
- CSV for analysis
- Image for presentations

## Printing SPC

Navigate to `/spc/print` for print-optimized view:

- Full-page charts
- Summary tables
- Formatted for paper

## Permissions

| Permission | Allows |
|------------|--------|
| `view_analytics` | View SPC charts |
| `view_measurements` | Access measurement data |
| `change_spc_baseline` | Modify baselines |

## Best Practices

1. **Monitor regularly** - Check charts daily/weekly
2. **React to signals** - Investigate out-of-control points
3. **Don't over-adjust** - Only adjust for assignable causes
4. **Update baselines** - After confirmed improvements
5. **Document changes** - Note process adjustments

## Next Steps

- [Dashboard Overview](dashboard.md) - Overall metrics
- [Defect Analysis](defects.md) - Quality analysis
- [Recording Measurements](../workflows/tracking/measurements.md) - Data collection
