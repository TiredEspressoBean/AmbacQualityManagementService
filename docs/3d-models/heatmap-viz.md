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

### By work order

Use the **Work order** filter to narrow the map to one work order's parts.

## Heat Map Options

Two sliders shape how the heat map renders:

| Option | Effect |
|--------|--------|
| **Radius** | How far each defect's heat spreads from its point |
| **Intensity** | How strongly each defect contributes to the colour |

!!! note "No opacity, interpolation or contour controls"
    Older instructions listed Point Size, Opacity, Interpolation and Contours,
    and a choice between Defect Count, Defect Rate and per-severity maps. The
    two sliders above are the whole of it.

## Filtering

The viewer filters on five things, all of them dropdowns:

| Filter | Default |
|--------|---------|
| **Step** | All Steps |
| **Defect type** | All Defect Types |
| **Severity** | All Severities |
| **Time** | All Time |
| **Work order** | All Work Orders |

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

!!! note "Planned Feature"
    Heat map image export (PNG) is planned. There is no export or screenshot
    control in the heat map viewer yet — use your operating system's screen
    capture.

!!! warning "There is no Generate Report or Export Data button"
    Older instructions on this page described both, plus scheduled heat map
    reports. None of them exist. Annotation data is reachable through the REST
    API if you need it outside the viewer.

## Permissions

| Permission | Allows |
|------------|--------|
| `view_heatmapannotations` | View heat maps and their annotation details |
| `export_data` | Export heat map data |

## Next Steps

- [Creating Annotations](annotations.md) - Add defect data
- [Defect Analysis](../analysis/defects.md) - Statistical analysis
- [CAPA Overview](../workflows/capa/overview.md) - Address findings
