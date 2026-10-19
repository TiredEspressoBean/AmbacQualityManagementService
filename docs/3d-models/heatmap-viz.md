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
```

Heat **adds up**: each defect contributes heat around its point — how much is
set by **Intensity**, how far it spreads by **Radius** — and overlapping
contributions sum until they reach red, where they stop.

Two things shape a defect's contribution before you touch anything:

- **Severity weights it** — Critical counts double, High one and a half times,
  Medium once, Low half
- **The defaults scale themselves** — Radius starts at 5% of the model's largest
  dimension, and Intensity starts lower the more annotations are in view
  (1.5 ÷ √count), so a busy map does not turn solid red

!!! tip "Red means saturated, not 'the most'"
    Once an area reaches red, more defects there change nothing, so two areas
    can read the same red with very different counts behind them. Turn
    **Intensity** down to tell dense areas apart again.

    And because severity weights the heat, a few Critical defects can glow as
    hot as many Low ones. Filter by **Severity** when you need a count.

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
    The two sliders above are the whole of it — there is no point size,
    opacity, interpolation or contour setting, and no choice between count,
    rate and per-severity maps. To see one severity, filter by it.

## Filtering

| Filter | Options |
|--------|---------|
| **Manufacturing Step** | All steps, or one |
| **Defect Type** | All defect types, or one |
| **Severity** | All, Low, Medium, High or Critical |
| **Date Range** | All time, last 7, 30 or 90 days, or a custom start and end |
| **Work Order** | All work orders, or one |

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

1. Set the date range to the earlier period
2. Take a screen capture — the viewer has no export
3. Set the date range to the later period
4. Compare the two

Look for:
- New hot spots
- Reduced intensity (improvement)
- Shifted patterns

## Taking Action

### Investigating Hot Spots

1. Narrow the filters until the hot spot is what you are looking at
2. Select the annotation points inside it — each shows its defect type,
   severity, notes, date found and who reported it
3. Open the linked quality reports for the parts involved
4. Look for what they share: step, machine, material lot, shift

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

!!! note "No export of any kind"
    There is no image export, no report and no data export from the heat map
    viewer, and no scheduled heat map report. Use your operating system's screen
    capture for an image; annotation data is reachable through the REST API.

## Permissions

| Permission | Allows |
|------------|--------|
| `view_heatmapannotations` | View heat maps and their annotation details |
| `change_heatmapannotations` | **Edit Annotation** from the viewer |

## Next Steps

- [Creating Annotations](annotations.md) - Add defect data
- [Defect Analysis](../analysis/defects.md) - Statistical analysis
- [CAPA Overview](../workflows/capa/overview.md) - Address findings
