# Dashboard Overview

uqmes provides several dashboards for monitoring operations, quality, and production metrics.

## Available Dashboards

| Dashboard | Route | Focus |
|-----------|-------|-------|
| **Analysis Dashboard** | `/analysis` | KPI trends, FPY, defect pareto, needs attention |
| **Quality Dashboard** | `/quality` | Open CAPAs, NCRs, disposition status |
| **SPC Charts** | `/spc` | Control charts, capability indices |
| **Defect Analysis** | `/quality/defects` | Defect trends by type, supplier, part |
| **Tracker** | `/tracker` | Order progress, production status |

### Analysis Dashboard (`/analysis`)

Navigate to **Analytics** in the sidebar or go directly to `/analysis`

Focus: Comprehensive KPI analysis
- First Pass Yield trend with date range toggle
- Needs attention items (overdue CAPAs, pending approvals)
- Defect Pareto charts
- Links to SPC, Defects, and CAPAs

### Quality Dashboard (`/quality`)

Navigate to **Quality** > **Dashboard** or `/quality`

Focus: Quality metrics and performance
- Open CAPAs and NCRs
- Defect trends
- First Pass Yield
- Disposition breakdown

### Production Views

| Page | Route | Focus |
|------|-------|-------|
| Tracker | `/tracker` | Order cards with progress bars (customer-facing) |
| Work Orders | `/production/work-orders` | Production queue and inspection |
| Dispositions | `/production/dispositions` | Quarantine and disposition management. Listed under **Quality** in the sidebar despite the URL. |

## Quality Dashboard

### KPI Cards

Four metrics across the top:

| KPI | Description |
|-----|-------------|
| **First Pass Yield** | Percentage passing without rework, against a 95% target |
| **Scrap Rate** | Percentage of parts scrapped |
| **Active CAPAs** | CAPAs in progress |
| **Overdue** | CAPAs past their due date |

Below them, a **needs-attention** row surfaces NCRs open more than 7 days,
CAPAs past due, parts in quarantine, and CAPAs pending verification — the same
counts the Home page shows.

**View Issues**, **NCR Analysis**, **Full Analysis** and **SPC** open the
detailed views.

### Charts

**Defect Trend**
- Line chart showing NCRs over time
- By day, week, or month
- Identify increasing/decreasing trends

**Defect Pareto**
- Bar chart of defects by error type
- 80/20 analysis
- Focus improvement efforts

**Disposition Breakdown**
- Pie chart of disposition decisions
- Scrap, Rework, Use As Is, RTV
- Track disposition patterns

### Recent Activity

- Latest quality reports
- Recent CAPA updates
- Documents pending approval

## Analytics Dashboard

### Period

The dashboard has one control: a period selector offering **30 days**,
**60 days**, and **90 days**.

!!! note "No dimension filters here"
    There is no part type, process, customer, or error type filter on the
    dashboard. To slice defects that way, use
    [Defect Analysis](defects.md), which has its own filters and CSV export.

### KPI Trends

**FPY Trend**
- First Pass Yield over time
- Target line overlay
- By part type or process

**Defect Rate**
- Defects per unit or per thousand
- Trend analysis
- Compare periods

**NCR Aging**
- Time to close NCRs
- Identify bottlenecks
- Track improvement

### Defect Analysis

**Pareto by Error Type**
- Which defects occur most
- Cumulative percentage line
- Focus areas for improvement

**Defect by Process Step**
- Where defects are found
- Detection effectiveness
- Process problem areas

**Defect by Part Type**
- Which parts have most issues
- Compare performance
- Prioritize attention

### Repeat Defects

Track recurring issues:

- Same error on same part type
- Indicator of systemic problems
- CAPA candidates

## Dashboard Widgets

### Widget Types

| Type | Purpose |
|------|---------|
| **KPI Card** | Single metric with trend |
| **Line Chart** | Trends over time |
| **Bar Chart** | Comparisons |
| **Pie Chart** | Distributions |
| **Table** | Lists of records |

!!! note "Planned Feature"
    Dashboard widget customization (add/remove, resize, rearrange) is planned for a future release.

!!! warning "There are no preset ranges, custom ranges, drill-down or refresh"
    Older instructions on this page described seven preset ranges, a custom
    date picker, clicking a chart to open the records behind it, and a Refresh
    icon. None of them exist.

    The period selector described above — 30 / 60 / 90 days — is the whole of
    the dashboard's interactivity. To see the records behind a number, open the
    page that owns them: [Defect Analysis](defects.md), [Quality
    Reports](../workflows/quality/quality-reports.md), or
    [SPC](spc.md).

## Exporting Dashboard Data

!!! note "Planned Feature"
    Dashboard export functionality is planned for a future release.

When available:

- Export individual charts as PNG or CSV
- Export entire dashboard as PDF

For current data exports, see [Exporting Data](exporting.md).

## Big Screen Mode

For shop floor displays:

1. Navigate to **Big Screen** (`/big-screen`)
2. Full-screen optimized display (press F11)
3. Large, readable fonts
4. Shows KPIs, FPY trend, defects by type, and recent activity

!!! note "Planned Feature"
    Big screen configuration options (metrics selection, rotation interval, display theme) are planned for a future release.

## Permissions

| Permission | Allows |
|------------|--------|
| `view_documents` *or* `view_chatsession` | Makes the Analytics link appear in the sidebar |
| `view_qualityreports` | See NCR data |
| `view_capa` | See CAPA data |

!!! note
    There is no dedicated `view_analytics` permission. The Analytics link is
    shown to anyone holding `view_documents` or `view_chatsession`; the data
    each chart shows is then limited by the permissions on the underlying
    records.

## Next Steps

- [SPC Charts](spc.md) - Process control analysis
- [Defect Analysis](defects.md) - Deep dive on defects
- [Exporting Data](exporting.md) - Reports and exports
