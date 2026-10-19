# Dashboard Overview

uqmes has several dashboards. Two of them are easy to confuse, because the
**Analytics** page's own heading reads *Quality Dashboard* while a different page
is the Quality dashboard.

## Available Dashboards

| Dashboard | Route | Focus |
|-----------|-------|-------|
| **Analytics** | `/analysis` | Quality KPIs, FPY trend, what needs attention, top defects. Headed *Quality Dashboard* |
| **Quality dashboard** | `/quality` | **CAPAs** — counts, quick actions, approvals, your tasks |
| **NCR Analysis** | `/quality/ncrs` | NCR trend, aging, disposition breakdown |
| **Defect Analysis** | `/quality/defects` | Defects by type, process, part — with filters and CSV export. See [Defect Analysis](defects.md) |
| **SPC Charts** | `/spc` | Control charts, capability indices. See [SPC](spc.md) |
| **Tracker** | `/tracker` | Order progress |

## Analytics (`/analysis`)

Navigate to **Analytics** in the sidebar.

### KPI cards

| KPI | Description |
|-----|-------------|
| **First Pass Yield** | Percentage passing without rework, against a **95%** target |
| **Scrap Rate** | Percentage of parts scrapped |
| **Rework Rate** | Percentage of parts reworked |
| **Open Issues** | Open quality issues |
| **Active CAPAs** | CAPAs in progress |
| **Overdue** | CAPAs past their due date |

### Below the cards

- **FPY Trend** — first pass yield over the period, with the target line, and a
  link to SPC
- **Needs attention** — the urgent items; *All Clear — No urgent issues* when
  there are none
- **Top Defects** — the most frequent error types, linking to Defect Analysis
- Links to **NCRs**, **CAPAs** and the quality reports list

### Period

The page has one control: a period toggle of **30**, **60** or **90 days**.

!!! note "No dimension filters, drill-down, export or refresh"
    There is no part type, process, customer or error type filter here, no
    custom date range, nothing to click through from a chart, and no export.
    To see the records behind a number, open the page that owns them: [Defect
    Analysis](defects.md), [Quality Reports](../workflows/quality/quality-reports.md),
    or [SPC](spc.md). For files, see [Exporting Data](exporting.md).

## Quality dashboard (`/quality`)

Navigate to **Quality** > **Dashboard**. This is the **CAPA** dashboard:

| Tile | Counts |
|------|--------|
| **Open CAPAs** | Requiring attention |
| **Overdue** | Past due date |
| **Pending Verification** | Awaiting review |
| **Closed** | Successfully resolved |

Below: **Quick Actions** (*View All CAPAs*, *Create New CAPA*), the items
**requiring your approval**, and **My Tasks** — CAPA tasks assigned to you.

!!! note "No FPY, quarantine count or charts here"
    Yield, scrap and defect charts are on **Analytics**. The *In quarantine*
    count is on **Home**.

## NCR Analysis (`/quality/ncrs`)

NCRs over time, how long they stay open, and how their dispositions break down —
scrap, rework, use as is, return to supplier.

**Repeat defects** lists every defect recorded **three or more times on failed
reports** in the selected period — the classic CAPA candidate. Each row names
the defect, the part types and steps it turned up on, and the count. See
[Repeat Defects](defects.md#repeat-defects).

## Big Screen Mode

For shop floor displays:

1. Go to **`/big-screen`** directly — it is a real page but has **no sidebar
   entry**, so you have to type the URL
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
