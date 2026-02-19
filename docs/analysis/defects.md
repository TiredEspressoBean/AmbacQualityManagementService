# Defect Analysis

Analyze defect data to identify patterns, prioritize improvements, and track quality performance.

## Accessing Defect Analysis

Navigate to **Analytics** or **Quality** > **Defects**

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

### Filtering Pareto

Filter the Pareto chart:

| Filter | Purpose |
|--------|---------|
| **Date Range** | Period to analyze |
| **Part Type** | Specific product |
| **Process** | Specific workflow |
| **Step** | Where detected |
| **Severity** | Minor/Major/Critical |

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
| Incoming Inspection | 12 | 30% |
| Machining | 8 | 20% |
| Assembly | 15 | 38% |
| Final QA | 5 | 12% |

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
| Widget A | 45 | 2.3% |
| Widget B | 12 | 0.8% |
| Assembly X | 28 | 3.1% |

Compare:
- Absolute counts
- Rates (normalized by production)
- Trends over time

## By Supplier/Lot

Track quality by material source:

| Supplier | Lots | Defect Rate |
|----------|------|-------------|
| Supplier A | 24 | 1.2% |
| Supplier B | 18 | 4.5% |
| Supplier C | 12 | 0.5% |

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

Track cost of quality:

| Category | Cost |
|----------|------|
| **Scrap** | Material + labor lost |
| **Rework** | Additional labor |
| **Inspection** | Sorting/reinspection |
| **Returns** | Customer returns |

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

Build custom defect reports:

1. Select metrics
2. Apply filters
3. Choose visualization
4. Add calculations
5. Save report

### Scheduled Reports
- Daily summary email
- Weekly trend report
- Monthly management report

## Export Options

| Format | Use Case |
|--------|----------|
| **CSV** | Data analysis in Excel |
| **PDF** | Sharing, archives |
| **Image** | Presentations |

## Permissions

| Permission | Allows |
|------------|--------|
| `view_analytics` | Access defect analysis |
| `view_qualityreport` | See underlying data |
| `export_data` | Export reports |

## Best Practices

1. **Review regularly** - Weekly minimum
2. **Focus on trends** - Not just snapshots
3. **Use Pareto** - Prioritize the vital few
4. **Drill down** - Understand root causes
5. **Track improvements** - Verify actions worked

## Next Steps

- [Dashboard Overview](dashboard.md) - KPI summaries
- [SPC Charts](spc.md) - Process monitoring
- [Heat Maps](heatmaps.md) - Visual defect locations
- [CAPA Overview](../workflows/capa/overview.md) - Corrective actions
