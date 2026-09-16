# Defect Analysis

Analyze defect data to identify patterns, prioritize improvements, and track quality performance.

## Accessing Defect Analysis

Navigate to **Analytics**, then click **Defects**, or go directly to `/quality/defects`

## Pareto Analysis

The Pareto chart shows defect distribution:

```
Error Types (Defect Count)
├── Dimensional    ████████████████ (45%)
├── Visual         ████████ (22%)
├── Material       ████ (12%)
├── Functional     ███ (9%)
├── Documentation  ██ (6%)
└── Other          ██ (6%)
```

### 80/20 Rule

Typically 80% of defects come from 20% of causes.

Focus improvement efforts on the "vital few":
1. Identify top error types
2. Root cause analysis
3. Corrective action
4. Monitor improvement

### Filtering

The page offers:

| Control | Purpose |
|---------|---------|
| **Period** | 30, 60, or 90 days |
| **Part type** | All part types, or one |

Defects are broken down by **type** and by the **step** where they were found,
each with a count. Below that, **Defect Records** lists the individual defects:

| Column | Shows |
|--------|-------|
| **Part** | The affected part |
| **Part Type** | Its type |
| **Process** | The process it was running |
| **Defect** | The error type recorded |
| **Date** | When it was found |
| **Status** | Where the defect stands |

**Export** downloads the current view as CSV, respecting the period and part
type you have selected.

!!! note "No severity filter"
    Defects cannot be filtered by severity here. Severity lives on the CAPA
    and the disposition, not on the defect record shown in this view.

### How the filters apply

Everything on the page follows your filters — the KPI cards included. Two rules
are worth knowing, because both look like bugs until you know them.

**The breakdowns each ignore their own axis.** *By Defect Type* respects every
filter except defect type; *By Process* respects every filter except process.
Filtering by process narrows *By Defect Type* to that process's defects, while
*By Process* keeps listing every process.

That is deliberate: each breakdown is also the control you click to *set* that
filter. If *By Defect Type* filtered itself, clicking **Porosity** would leave
one bar at 100% with nothing left to click.

**Choosing a defect type changes the numerator only.** Defect rate is failures
over inspections, and an inspection is not tagged with a defect type — it
either happened or it didn't. So filtering by defect type narrows the failure
count but leaves the inspected total alone.

!!! warning "Expect the rate to move less than you think"
    Narrowing the denominator the same way would leave only inspections that
    already found that defect, and **every rate would read 100%**.

    Process and part type are different: those describe the inspection itself,
    so they narrow both sides and the rate moves as you would expect.

    If a rate looks stubbornly high after picking a defect type, this is why —
    you are seeing that defect against *all* inspections in scope, which is the
    useful number.

## Trend Analysis

### Defect Trend Over Time

Line chart showing defects by period:

- Daily, weekly, or monthly
- Total count or rate
- Compare to targets

### Identifying Patterns

Look for:
- **Increasing trend**: Problem getting worse
- **Decreasing trend**: Improvement working
- **Spikes**: Specific event caused issues
- **Cycles**: Periodic patterns (shifts, maintenance)

### Rate vs Count

| Metric | Formula | Use When |
|--------|---------|----------|
| **Count** | Total defects | Volume is constant |
| **Rate** | Defects / Parts produced | Volume varies |

## By Process Step

Where are defects detected?

| Step | Defects | % |
|------|---------|---|
| Component Grading | 12 | 25% |
| Nozzle Inspection | 18 | 38% |
| Flow Testing | 10 | 21% |
| Final Test | 8 | 16% |

### Detection vs Origin

Defects detected at a step may have originated earlier:

- Early detection = good (less rework)
- Late detection = costly (scrap or rework done)

Track both:
- Where detected
- Where originated (root cause)

## By Part Type

Which products have quality issues?

| Part Type | Defects | Rate |
|-----------|---------|------|
| Common Rail Injector | 45 | 2.3% |
| HEUI Injector | 12 | 0.8% |
| Unit Injector | 28 | 3.1% |

Compare:
- Absolute counts
- Rates (normalized by production)
- Trends over time

## By Supplier/Lot

Supplier quality is **not** analysed on this page. Use **Supply** >
**Supplier Quality**, which scores each supplier on lots received, accepted and
rejected, reject rate, CoC compliance, on-time delivery, and open SCARs. See
[Supply](../workflows/supply/overview.md#supplier-quality).

!!! example "Demo: Supplier Quality Issue"
    Analysis of nozzle defects in order ORD-2024-0038 traced the issue to a specific Delphi batch. This data supported CAPA-2024-003's root cause finding.

Use for:
- Supplier quality ratings
- Incoming inspection decisions
- Sourcing decisions

## Repeat Defects

Identify recurring issues:

### Definition
Same error type + same part type occurring multiple times.

### Analysis
- How often does it repeat?
- Time between occurrences
- Root cause addressed?

### Actions
- Create CAPA for systemtic issues
- Review existing CAPAs effectiveness
- Escalate if not improving

## Defect Cost Analysis

!!! note "Planned Feature"
    Cost of quality is not tracked. Nothing records the cost of scrap, rework,
    inspection, or returns, and no cost figures appear in defect analysis.

    The scrap **rate** is reported on the [Quality
    Dashboard](dashboard.md) as a percentage of parts, not a monetary value.

Use for:
- Prioritizing improvements
- ROI of quality projects
- Management reporting

## Drill-Down Capability

From any chart, drill down:

1. Click data point or bar
2. View list of related NCRs
3. Click NCR for details
4. Navigate to parts, CAPAs

## Comparative Analysis

### Period Comparison
- This month vs last month
- This quarter vs same quarter last year
- Before/after improvement

### Benchmark Comparison
- Against target
- Against industry standards
- Against best-in-class

## Custom Reports

!!! note "Planned Feature"
    Custom report builder functionality is planned for a future release. Currently, use filters on the defect analysis page and export data for external analysis.

### Scheduled Reports

!!! note "Planned Feature"
    Scheduled defect reports are planned for a future release. Currently, export reports manually.

## Export Options

Export defect data from the Quality Reports table (**Quality > Quality Reports**):

| Format | Use Case |
|--------|----------|
| **CSV** | Data analysis in Excel |
| **Excel** | Includes reference sheets and validation |

!!! note "Planned Feature"
    PDF and image export from analytics charts are planned for a future release.

## Permissions

| Permission | Allows |
|------------|--------|
| `view_documents` *or* `view_chatsession` | Makes the Analytics link appear in the sidebar |
| `view_qualityreports` | See underlying data |
| `export_data` | Export reports |

## Next Steps

- [Dashboard Overview](dashboard.md) - KPI summaries
- [SPC Charts](spc.md) - Process monitoring
- [Heat Maps](heatmaps.md) - Visual defect locations
- [CAPA Overview](../workflows/capa/overview.md) - Corrective actions
