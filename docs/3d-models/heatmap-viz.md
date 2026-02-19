# Heat Map Visualization

Heat maps overlay defect frequency data on 3D models, revealing patterns in where defects occur.

## Understanding Heat Maps

A heat map shows defect concentration:

- **Color intensity** indicates frequency
- **Hot spots** show problem areas
- **Cool areas** have few or no defects

### Color Scale

```
Low ─────────────────────────────── High
Blue    Cyan    Green   Yellow   Red
  1      2-3     4-6     7-10    11+
```

The scale adjusts based on your data range.

## Viewing Heat Maps

### By Part Type

1. Navigate to **Quality** > **Heat Map**
2. Select a Part Type
3. Heat map shows all defects across parts of that type

This view identifies:
- Systemic location issues
- Design or process problems
- Areas needing improvement

### By Specific Part

1. Navigate to `/heatMapViewer/part/{partId}`
2. Heat map shows defects on that specific part
3. Useful for part-specific investigation

### By Order

Filter heat map to show only parts from a specific order:
1. Open Heat Map viewer
2. Apply **Order** filter
3. View defects for that order's parts

## Heat Map Options

### Data Options

| Option | Effect |
|--------|--------|
| **Defect Count** | Color by number of defects |
| **Defect Rate** | Color by defects per production volume |
| **By Severity** | Separate heat maps per severity level |

### Display Options

| Option | Effect |
|--------|--------|
| **Point Size** | Larger/smaller annotation markers |
| **Opacity** | Heat map transparency |
| **Interpolation** | Smooth color transitions |
| **Contours** | Show frequency lines |

## Filtering Heat Map Data

### By Date Range

1. Select date range filter
2. Show only defects from that period
3. Compare different time periods

### By Error Type

1. Select specific error types
2. Heat map shows only those defects
3. Analyze specific defect categories

### By Severity

- Show all severities
- Critical only
- Major and above
- Minor only

### By Source

- All defects
- Production defects only
- Customer-reported only
- Incoming inspection only

## Interpreting Heat Maps

### Patterns to Look For

| Pattern | Possible Meaning |
|---------|------------------|
| **Single hot spot** | Specific process issue, tooling problem |
| **Edge concentration** | Handling damage, machining entry |
| **Symmetric spots** | Fixture or tooling related |
| **Random scatter** | Multiple causes, general variability |
| **Linear pattern** | Toolpath issue, grain direction |
| **Surface areas** | Material or coating problems |

### Comparing Heat Maps

Compare to identify changes:

1. Set date range A
2. Screenshot or save
3. Set date range B
4. Compare visually

Look for:
- New hot spots
- Reduced intensity (improvement)
- Shifted patterns

## Taking Action

### Investigating Hot Spots

1. Click on a hot spot
2. View list of annotations at that location
3. Click annotations to see details
4. Review linked NCRs
5. Identify common factors

### Root Cause Questions

For identified hot spots:
- What step in process affects this location?
- What equipment contacts here?
- What's the material flow at this point?
- Is there a handling touch point?

### Improvement Actions

Based on findings:
- Create CAPA for systemic issues
- Modify process to address root cause
- Add inspection focus at problem areas
- Update work instructions

## Tracking Improvement

Monitor heat map changes over time:

1. Baseline heat map before action
2. Implement corrective action
3. Heat map after implementation period
4. Compare for reduction in hot spots

Document improvement in CAPA verification.

## Exporting Heat Maps

### Image Export

1. Position model to desired view
2. Click **Export** or screenshot icon
3. PNG downloads with heat map overlay

### Report Export

1. Click **Generate Report**
2. PDF includes:
   - Heat map image
   - Top defect locations table
   - Statistics summary

### Data Export

1. Click **Export Data**
2. CSV of annotation locations and frequencies
3. For external analysis

## Heat Map Reports

### Standard Reports

- **Hot Spot Analysis**: Top defect locations
- **Trend Comparison**: Before/after periods
- **Part Type Comparison**: Compare across types

### Scheduled Reports

Set up recurring heat map reports:
1. Configure report parameters
2. Set schedule (weekly, monthly)
3. Select recipients
4. Reports email automatically

## Permissions

| Permission | Allows |
|------------|--------|
| `view_heatmap` | View heat maps |
| `view_heatmapannotation` | See annotation details |
| `export_data` | Export heat map data |

## Best Practices

1. **Regular review** - Check heat maps weekly
2. **Filter strategically** - Focus analysis
3. **Look for changes** - Compare time periods
4. **Act on findings** - Heat maps drive improvement
5. **Share with team** - Visualizations communicate issues

## Next Steps

- [Creating Annotations](annotations.md) - Add defect data
- [Defect Analysis](../analysis/defects.md) - Statistical analysis
- [CAPA Overview](../workflows/capa/overview.md) - Address findings
