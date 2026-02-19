# Dashboard Overview

Ambac Tracker provides several dashboards for monitoring operations, quality, and production metrics.

## Available Dashboards

### Quality Dashboard
Navigate to **Quality** > **Dashboard**

Focus: Quality metrics and performance
- Open CAPAs and NCRs
- Defect trends
- First Pass Yield
- Disposition breakdown

### Analytics Dashboard
Navigate to **Analytics** (in Tools section)

Focus: Comprehensive analysis
- KPI trends over time
- Defect Pareto charts
- FPY analysis
- Custom date ranges

### Production Dashboard
Via Work Orders or Tracker views

Focus: Production status
- Order progress
- Work order status
- Throughput metrics
- On-time delivery

## Quality Dashboard

### KPI Cards

Top-level metrics at a glance:

| KPI | Description |
|-----|-------------|
| **Open CAPAs** | Active corrective actions |
| **Open NCRs** | Quality reports awaiting disposition |
| **Pending Approvals** | Items awaiting your approval |
| **FPY (This Month)** | First Pass Yield percentage |

Click any card to drill down to details.

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

### Filters

Customize your view:

| Filter | Options |
|--------|---------|
| **Date Range** | Preset or custom |
| **Part Type** | All or specific |
| **Process** | All or specific |
| **Customer** | All or specific |
| **Error Type** | All or specific |

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

### Customizing Widgets

Some dashboards allow widget customization:

1. Click **Customize** or gear icon
2. Add/remove widgets
3. Resize widgets
4. Arrange layout
5. Save configuration

### Widget Types

| Type | Purpose |
|------|---------|
| **KPI Card** | Single metric with trend |
| **Line Chart** | Trends over time |
| **Bar Chart** | Comparisons |
| **Pie Chart** | Distributions |
| **Table** | Lists of records |
| **Gauge** | Progress toward goal |

## Date Range Selection

### Preset Ranges

- Today
- This Week
- This Month
- This Quarter
- Last 30 Days
- Last 90 Days
- Year to Date

### Custom Range

1. Click **Custom**
2. Select start date
3. Select end date
4. Apply

### Comparing Periods

Some charts support comparison:

1. Enable **Compare to Previous**
2. Current period vs same length prior
3. Identify improvements or declines

## Drilling Down

Click on chart elements to drill down:

1. Click a bar in Pareto chart
2. Opens list of related NCRs
3. Click NCR to view details

Or:

1. Click data point on trend
2. Shows records for that period
3. Navigate to details

## Refreshing Data

Dashboards update automatically, but you can force refresh:

1. Click **Refresh** icon
2. Data reloads from server
3. Charts update

## Exporting Dashboard Data

Export for reporting:

1. Click **Export** on chart
2. Select format (PNG, CSV)
3. Download

Or export entire dashboard:

1. Click **Export Dashboard**
2. PDF or presentation format
3. Include all visible charts

## Big Screen Mode

For shop floor displays:

1. Navigate to **Big Screen** (`/big-screen`)
2. Full-screen optimized display
3. Auto-rotating metrics
4. Large, readable fonts

Configure:
- Metrics to display
- Rotation interval
- Display theme

## Permissions

| Permission | Allows |
|------------|--------|
| `view_analytics` | Access dashboards |
| `view_qualityreport` | See NCR data |
| `view_capa` | See CAPA data |

## Best Practices

1. **Check daily** - Stay on top of trends
2. **Use filters** - Focus on relevant data
3. **Act on insights** - Dashboard is for action
4. **Share regularly** - Keep team informed
5. **Set targets** - Visible goals drive improvement

## Next Steps

- [SPC Charts](spc.md) - Process control analysis
- [Defect Analysis](defects.md) - Deep dive on defects
- [Exporting Data](exporting.md) - Reports and exports
