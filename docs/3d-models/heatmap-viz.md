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
  Medium once, Low half; an annotation with no severity counts as Medium
- **The defaults scale themselves** — with **Auto-adjust** on (the default),
  Radius starts at 5% of the model's largest dimension, and Intensity starts
  lower the more annotations are in view (1.5 ÷ √count), so a busy map does not
  turn solid red

!!! tip "Red means saturated, not 'the most'"
    Once an area reaches red, more defects there change nothing, so two areas
    can read the same red with very different counts behind them. Turn
    **Intensity** down to tell dense areas apart again.

    And because severity weights the heat, a few Critical defects can glow as
    hot as many Low ones. Filter by **Severity** when you need a count.

## Viewing Heat Maps

### By Part Type

1. Navigate to **Quality** > **Heat Map**
2. On the **By Part Type** tab, select a part type — only part types with a 3D
   model are listed
3. Heat map shows the defects annotated on that part type's model, across all
   its parts

This view identifies:
- Systemic location issues
- Design or process problems
- Areas needing improvement

### By Specific Part

1. On the Heat Map page's **By Specific Part** tab, choose the **Part Type**
   and the **Part**, then **View Heatmap** — or open
   `/heatMapViewer/part/{partId}`
2. Heat map shows defects on that specific part
3. Useful for part-specific investigation

### By work order

Use the **Work order** filter to narrow the map to one work order's parts.

!!! warning "The map draws the 200 most recent matching defects"
    The viewer loads the **200 newest** annotations that match the filters and
    draws only those. When more match, a banner at the top of the model reads
    *Showing the newest &lt;N&gt; of &lt;M&gt; annotations — narrow the date range
    or filters to see the rest.*, the header reads *Showing &lt;N&gt; of &lt;M&gt;
    defects*, and the Severity and Defect Type counts still cover all
    &lt;M&gt;. Narrow the filters (a date range, a work order, a defect type)
    until the banner goes away before reading the map as the whole picture.

## Heat Map Options

Under **Heatmap Settings**:

| Option | Effect |
|--------|--------|
| **Enable Heatmap** | Turns the heat on or off; the annotation markers stay |
| **Auto-adjust** | On: Radius and Intensity are multipliers on the self-scaling defaults, with the resulting value shown beneath each. Off: they are set directly |
| **Radius** | How far each defect's heat spreads from its point |
| **Intensity** | How strongly each defect contributes to the colour |

Radius and Intensity each have a slider and a box to type a value.

!!! note "No opacity, interpolation or contour controls"
    The settings above are the whole of it — there is no point size,
    opacity, interpolation or contour setting, and no choice between count,
    rate and per-severity maps. To see one severity, filter by it.

## Filtering

| Filter | Options |
|--------|---------|
| **Manufacturing Step** | Shown when the part type has more than one model: chooses which model. **All Steps** shows the part type's general model (the one with no step); the other options are the steps that have a model, by step name |
| **Defect Type** | All defect types, or one of those present, with its count |
| **Severity** | All severities, or one of those present, with its count |
| **Date Range** | All time, last 7, 30 or 90 days, or a custom start and end — by the date the annotation was made |
| **Work Order** | All work orders, or one |

**Clear All Filters** resets Defect Type, Severity, Date Range and Work Order.

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
