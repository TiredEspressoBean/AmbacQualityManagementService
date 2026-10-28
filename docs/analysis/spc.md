# SPC Charts

Statistical Process Control (SPC) uses charts to monitor process stability and capability.

## What is SPC?

SPC applies statistical methods to:

- **Monitor** process variation
- **Detect** shifts and trends
- **Prevent** defects before they occur
- **Improve** process capability

## Accessing SPC

| Page | Route | Purpose |
|------|-------|---------|
| SPC Charts | `/spc` | Main control chart view with measurement selection |
| SPC Report | Button on the SPC page | Generates a PDF SPC report, downloaded — or emailed to you, where this deployment sends mail |
| Analysis Dashboard | `/analysis` | Overview with links to SPC |

Navigate to **Analytics**, then select **SPC** (on the FPY Trend card) or the
**First Pass Yield** card, or go directly to `/spc`. The page is headed
*Statistical Process Control*.

## Control Charts

The system supports three chart types. The **Chart Type** toggle chooses
between a subgroup chart and **I-MR**; which subgroup chart you get — X̄-R or
X̄-S — follows the subgroup size:

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
| **Chart Type** | Subgroup (X̄-R or X̄-S), I-MR | The subgroup chart is X̄-S when the subgroup size is over 8, X̄-R otherwise |
| **Date Range** | Last 30, 60, 90 or 180 days | How far back to pull data. Starts at 90 |
| **Subgroup Size (n)** | 2–10, 15, 20, 25 | Number of consecutive measurements per point. Subgroup charts only; starts at 5 |

Standard practice is subgroup size of 5. Larger subgroups detect smaller shifts but require more data.

## Chart Display

The SPC view shows:

- The measurement's **Nominal**, **Tolerance**, **USL** and **LSL**
- A plain-language summary — *Action Needed*, *Monitor Closely*, *Process
  Healthy* or *Capability not judged yet* — with a suggested next step
- Control chart with data points, under **Control Charts**; **Histogram** and
  **Data Table** are the other two tabs
- Control limits (calculated, or frozen)
- Specification limits (from measurement definition)
- Out-of-control points highlighted, and listed under **Out of Control Points
  Detected** with the rule each broke

Click a point to open its subgroup — its mean, range and individual values —
with **Investigate (Create CAPA)**.

## Out-of-Control Rules

uqmes applies the **Western Electric** rules. The numbering matters: the
practitioner guide escalates by rule number, so Rule 2 has to mean the same
thing in both places.

| Rule | Description | Pattern it suggests |
|------|-------------|---------------------|
| **Rule 1** | One point beyond 3σ | A shock — something changed outright |
| **Rule 2** | 2 of 3 consecutive points beyond 2σ, same side | A shift beginning |
| **Rule 3** | 4 of 5 consecutive points beyond 1σ, same side | A smaller sustained shift |
| **Rule 4** | 8 consecutive points on one side of centre | The process has moved |
| **Rule 5** | 6 consecutive points steadily rising or falling | A trend — tool wear, drift |
| **Rule 6** | 14 consecutive points alternating up and down | Cycling, often two alternating sources |
| **Rule 7** | 15 consecutive points within 1σ | Stratification — limits too wide, or over-smoothed data |
| **Rule 8** | 8 consecutive points beyond 1σ, either side | A mixture of two populations |

!!! warning "Do not renumber these against another reference"
    Nelson's rules describe the same signals in a **different order** — its Rule
    2 is an 8-point run, not 2 of 3 beyond 2σ. Escalation in the
    [practitioner guide](spc-practitioner-guide.md) is keyed to the numbers
    above, so mixing the two schemes sends the wrong response to the wrong
    signal.

!!! important "Which rules you actually get depends on the chart"
    Not all eight are evaluated on every chart type:

    | Chart | Rules evaluated |
    |-------|-----------------|
    | **X̄-R** and **X̄-S** — the averages chart | **1–8** |
    | **X̄-R** and **X̄-S** — the range / std-dev chart | **1–4** |
    | **I-MR** — individuals and moving range | **1–5** |

    So the subtler patterns — alternating (6), stratification (7) and mixture
    (8) — are flagged **only on the averages chart of a subgroup plot**. If you
    are running I-MR because of low volume or destructive testing, those three
    will never fire, and you are reading the chart for them yourself.

    That is not unusual practice — the later rules are weakest on individuals —
    but do not take an absence of Rule 7 flags on an I-MR chart as evidence
    there is no stratification.

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

Four cards sit above the charts:

| Card | Shows |
|------|-------|
| **Cpk** | Against a target of ≥ 1.33 |
| **Cp** | Process potential |
| **Out of Control** | Points flagged |
| **Process σ** | Estimated within-subgroup spread, in the measurement's unit |

Below the charts, **Process Capability Summary** gives **Cp**, **Cpk**, **Pp**
and **Ppk** together. Until there are enough subgroups — or while the readings
show no spread at all — capability is shown as not yet judged, and **Freeze
Limits** stays unavailable.

## Baseline Management

### Freezing Limits

Once your process is stable, lock the control limits:

1. Verify process is stable (no red flags, random scatter)
2. Click **Freeze Limits**. *Freeze control limits* asks why; **Freeze limits**
   stays unavailable until you give a reason
3. Control limits are locked for ongoing monitoring
4. Future data is compared against frozen baseline

The Monitoring Mode badge's tooltip then reads *Frozen by &lt;name&gt; on
&lt;date&gt; — &lt;reason&gt;*.

### Updating Baseline

When process improves significantly:

1. Review new stable data period
2. Click **Unfreeze**. *Unfreeze control limits* asks why; the reason is kept
   on the baseline, which is marked **superseded**. The chart returns to
   baseline mode with recalculated limits
3. Once the new limits look right, click **Freeze Limits** to lock them, with
   its own reason

!!! note "There is no single 'update baseline' action"
    Re-baselining is unfreeze-then-freeze. The chart recalculates limits from
    current data while unfrozen, so check them before you freeze again.

!!! note "Reasons are recorded, not approved"
    Both reasons are stored on the baseline with who did it and when, and the
    change is in the audit log. Freezing or unfreezing takes no approval and
    sends no alert; any sign-off is your procedure's.

## Histogram

The **Histogram** tab (*Process Distribution*) shows the distribution of the
measurements as bars, with the **LSL** and **USL** marked — a visual capability
check. There is no normal-curve overlay.

## SPC Reports

Click **SPC Report** on the SPC page to generate a PDF:

- Full-page control charts
- Capability summary tables
- Delivered as a download, or emailed to you where this deployment sends mail

Select a measurement and date range first — the report is generated for the
current selection.

## Permissions

| Permission | Allows | Held by |
|------------|--------|---------|
| `view_documents` *or* `view_chatsession` | Makes the Analytics link appear in the sidebar | Every staff role |
| `view_measurementresult` | Read the measurement data behind a chart | Every staff role |
| `add_spcbaseline` / `change_spcbaseline` | **Freeze and re-freeze control limits** | QA Manager, QA Inspector, Production Manager, Shift Lead, Engineering, Document Controller, Tenant Admin |

*Held by* is the groups that hold it when an organisation is created. Group permissions can be changed, so check your own in [Roles & Groups](../admin/users/roles.md).

!!! note "Reading a chart is open; freezing limits is not"
    Anyone on staff can look at an SPC chart. **Freezing** the limits is quality
    planning — it decides what counts as out of control from then on — so it
    sits with the same tier that authors the rest of the quality model.

    **Operators, Planners and the docks cannot freeze a baseline.** If limits
    look wrong to you and you cannot change them, that is the boundary working,
    not a missing permission.

## Next Steps

- [SPC Practitioner Guide](spc-practitioner-guide.md) - Investigation workflows, CAPA criteria, baseline management
- [SPC Fundamentals Training](../training/tracks/spc-fundamentals.md) - Role-based training module
- [Dashboard Overview](dashboard.md) - Overall metrics
- [Defect Analysis](defects.md) - Quality analysis
- [Recording Measurements](../workflows/tracking/measurements.md) - Data collection
