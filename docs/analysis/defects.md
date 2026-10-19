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

| Control | Purpose |
|---------|---------|
| **Period** | 30, 60, or 90 days |
| **Part type** | All part types, or one |
| **Defect type** | Click a bar in **By Defect Type** |
| **Process** | Click a bar in **By Process** |

Active filters show as chips above the charts; click one to remove it, or
**Clear** to remove them all.

Across the top, four cards: **Total Defects**, **Defect Rate**, **Top Type** and
**Trend**, with a **Defect Trend** chart beneath. Then the two breakdowns, **By
Defect Type** and **By Process**, each with a count. Below that, **Defect
Records** lists the individual defects:

| Column | Shows |
|--------|-------|
| **Part** | The affected part |
| **Part Type** | Its type |
| **Process** | The process it was running |
| **Defect** | The error type recorded |
| **Date** | When it was found |
| **Status** | Where the defect stands |

**Export** downloads CSV. With rows ticked, it exports just those; otherwise it
exports every record in the current view, respecting all the filters above.

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

## Reading the page

### Trend

**Defect Trend** plots defects across the period you chose. Look for:

- **Increasing trend** — a problem getting worse
- **Decreasing trend** — an improvement working
- **Spikes** — a specific event
- **Cycles** — something periodic: shifts, maintenance

Use **Defect Rate** rather than **Total Defects** when volume varies — a busier
month will show more defects without anything getting worse.

### By Process

Where defects are **detected**. A defect found at final test may well have
been made at machining; the page records where it was found, not where it
originated, so the origin is a root-cause question for the CAPA.

!!! note "Part type is a filter, not a breakdown"
    There is no *by part type* chart. Pick a part type in the selector to see
    one type's defects, then compare by switching.

## By Supplier/Lot

Supplier quality is **not** analysed on this page. Use **Supply** >
**Supplier Quality**, which scores each supplier on lots received, accepted and
rejected, reject rate, certificate-of-conformance (CoC) compliance, on-time
delivery, and open supplier corrective action requests (SCARs). See
[Supply](../workflows/supply/overview.md#supplier-quality).

!!! example "Demo: Supplier Quality Issue"
    Analysis of nozzle defects in order ORD-2024-0038 traced the issue to a specific Delphi batch. This data supported CAPA-2024-003's root cause finding.


## Repeat Defects

The **Repeat defects** card on **NCR Analysis** (`/quality/ncrs`) lists every
defect recorded **three or more times on failed reports** in the page's period,
most frequent first, up to ten. Each row shows:

- the defect
- **Part types** and **Steps** it turned up on
- how many times — *12×*

A defect that keeps repeating across part types points at a shared cause — a
step, a machine, a supplier — rather than one product. It is the usual reason to
raise a CAPA. When nothing has reached three, the card reads *No defect has
repeated in this period*.

## Defect Cost Analysis

!!! note "Cost of quality is not tracked"
    Nothing records the cost of scrap, rework, inspection or returns, and no
    cost figures appear here. Scrap is reported on
    [Analytics](dashboard.md#analytics-analysis) as a **rate**, not a value.

## Clicking a chart filters, it does not drill down

Clicking a bar in **By Defect Type** or **By Process** adds that filter; it does
not open a list. The records behind the numbers are the **Defect Records** table
on the same page, already narrowed to match. Its rows are not links — to open a
part, look it up by its ID.

!!! note "No comparison, custom or scheduled reports"
    There is no period-over-period comparison, no benchmark line, no report
    builder and no scheduled report. Export the records and compare outside.

## Other exports

The quality reports list (**Quality** > **Quality Reports**) exports **CSV** or
**Excel**, the latter with reference sheets and validation. See [Exporting
Data](exporting.md).

## Permissions

| Permission | Allows |
|------------|--------|
| `view_documents` *or* `view_chatsession` | Makes the Analytics link appear in the sidebar |
| `view_qualityreports` | See underlying data |
| `export_data` | Generate PDF reports. This page's CSV export is built in the browser and needs only the view permissions above |

## Next Steps

- [Dashboard Overview](dashboard.md) - KPI summaries
- [SPC Charts](spc.md) - Process monitoring
- [Heat Maps](heatmaps.md) - Visual defect locations
- [CAPA Overview](../workflows/capa/overview.md) - Corrective actions
