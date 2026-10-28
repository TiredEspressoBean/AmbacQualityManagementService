# Dashboard Overview

uqmes has several dashboards. Two of them are easy to confuse, because the
**Analytics** page's own heading reads *Quality Dashboard* while a different page
is the Quality dashboard.

## Available Dashboards

| Dashboard | Route | Focus |
|-----------|-------|-------|
| **Analytics** | `/analysis` | Quality KPIs, FPY trend, what needs attention, top defects, downtime. Headed *Quality Dashboard* |
| **Quality dashboard** | `/quality` | **CAPAs** — counts, quick actions, approvals, your tasks |
| **NCR Analysis** | `/quality/ncrs` | NCR trend, aging, disposition breakdown |
| **Defect Analysis** | `/quality/defects` | Defects by type, process, part — with filters and CSV export. See [Defect Analysis](defects.md) |
| **SPC Charts** | `/spc` | Control charts, capability indices. See [SPC](spc.md) |
| **Tracker** | `/tracker` | Order progress |

## Analytics (`/analysis`)

Navigate to **Analytics** in the sidebar.

A status banner at the top sums things up — *Quality on track*, *Some issues
need attention* or *Immediate attention required* — with **View Issues** jumping
to the attention list.

### KPI cards

| KPI | Description | Opens |
|-----|-------------|-------|
| **First Pass Yield** | Percentage passing first time over the last 7 days, against a **95%** target. Planned repairs are left out, and their share is shown as *needed repair* | SPC |
| **Scrap Rate** | Percentage of parts scrapped | NCR Analysis |
| **Rework Rate** | Percentage of parts reworked | NCR Analysis |
| **Open Issues** | Open NCRs plus parts in quarantine | Dispositions |
| **Active CAPAs** | CAPAs not yet closed | CAPAs |
| **Overdue** | CAPAs past their due date | CAPAs |

### Below the cards

- **FPY Trend** — first pass yield over the period, with its average and the
  target line, and a link to SPC
- **Needs Attention** — up to five urgent items, each linking to where it is
  dealt with; *All Clear — No urgent issues* when there are none
- **Top Defects** — the five most frequent error types, with **Full Analysis**
  linking to Defect Analysis
- **Downtime** — hours lost over the period, **By cause** and **By machine**
- **Explore** links to **NCR Analysis**, **Defect Patterns**, **CAPA
  Management** and **All Reports**

### Period

The page has one control: a period toggle of **30**, **60** or **90 days**, on
the FPY Trend card. It sets the FPY trend, scrap and rework rates, Top Defects
and Downtime; the other cards are current counts.

!!! note "No dimension filters, chart drill-down, export or refresh"
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

Headed *NCR & Disposition Analysis*, with the same **30 / 60 / 90 day** toggle.
Cards for **Total NCRs**, **Open NCRs**, **Avg Age** and **Closure Rate**; then
the **NCR Trend** (created against closed), the **Disposition Breakdown** —
rework, repair, scrap, use as is, return to supplier, not a nonconformance — the
**NCR Aging** buckets and **Summary Statistics**.

**Awaiting a CAPA decision** lists failed reports nobody has yet decided a CAPA
on, and **Open Dispositions** the non-conforming parts still being dispositioned.

**Repeat defects** lists every defect recorded **three or more times on failed
reports** in the selected period — the classic CAPA candidate. Each row names
the defect, the part types and steps it turned up on, and the count. See
[Repeat Defects](defects.md#repeat-defects).

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
