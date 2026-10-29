# Heat Maps

Heat maps provide visual representation of defect distribution on parts, showing where issues occur most frequently.

## What is a Heat Map?

A heat map overlays defect frequency data onto a part representation:

- **Cool colors** (blue/green): Low defect frequency
- **Hot colors** (yellow/red): High defect frequency

This visual approach helps identify:
- Problem areas on parts
- Patterns in defect locations
- Focus areas for process improvement

## Accessing Heat Maps

Navigate to **Quality** > **Heat Map** (`/heatmap`), titled *Defect Heat Map*.

The per-part and per-type links — `/heatMapViewer/part/{id}` and
`/heatMapViewer/partType/{id}` — open **the same viewer** with that part or part
type already chosen. See [Heat Map
Visualization](../3d-models/heatmap-viz.md).

## Choosing what to show

On the **By Part Type** tab, pick a part type to see defects across every part
of that type — the view for systemic, location-driven problems. On the **By
Specific Part** tab, pick a part type and a part, then **View Heatmap**, to see
just that part's own.

!!! warning "Up to 200 defects at a time"
    The viewer draws the 200 most recent annotations that match the filters.
    When more match, a banner at the top of the model reads *Showing the newest
    &lt;N&gt; of &lt;M&gt; annotations — narrow the date range or filters to see
    the rest.* Narrow the filters until it goes away. See [Heat Map
    Visualization](../3d-models/heatmap-viz.md#by-work-order).

!!! note "There is no by-order view"
    To look at one job, narrow by **Work Order** in the filters below.

## 3D Model Heat Map

When 3D models are configured:

### Interactive Viewer
- Rotate, zoom, pan the model
- Defect locations shown as points coloured by severity, with heat around them
- Click points for defect details

### Color Scale
```
Low ─────────────────────────────── High
Blue    Cyan    Green    Yellow    Red
```

### Navigation
- **Scroll**: Zoom in/out
- **Drag**: Rotate model
- **Right-drag** or **Shift+Drag**: Pan
- **Click point**: View defect detail

See [Viewing Models](../3d-models/viewing.md) for the keyboard controls.

## Heat Map Data

Each point is an **annotation**: a location on the model, the defect type
recorded, its severity, notes, who reported it and when.

### Filtering

| Filter | Options |
|--------|---------|
| **Manufacturing Step** | Shown when the part type has more than one model: **All Steps** for the part type's general model, or a step that has its own model |
| **Defect Type** | All defect types, or one of those present, with its count |
| **Severity** | All severities, or one of those present, with its count |
| **Date Range** | All time, last 7, 30 or 90 days, or a custom range |
| **Work Order** | All work orders, or one |

**Heatmap Settings** turns the heat on or off and adjusts how it spreads
(**Radius**) and how strongly each defect counts (**Intensity**). Severity
weights each defect's heat: Critical double, High one and a half times, Medium
once, Low half.

## Creating Annotations

An annotation has to belong to a **quality report**: the annotator asks you to
*select a report to annotate* before you can place a point.

### Where

- **In the step player**, where a substep carries a **Defect annotation (3D)** capture
- **On the work order page**, from the **3D** tab of the QA panel on the right
  when a part is selected
- **In the Annotator** (`/annotator`), which a disposition waiting on
  annotations links to

### Placing one

From the work order page:

1. Choose the quality report
2. Click the defect location on the 3D model
3. Click the marker and fill in **Error Type**, **Severity Level** and **Notes**
4. **Save New**

See [Annotations](../3d-models/annotations.md) for the full procedure.

| Field | Description |
|-------|-------------|
| **Location** | 3D coordinates, from where you clicked |
| **Error Type** | Category of defect |
| **Severity Level** | Low, Medium, High or Critical |
| **Notes** | Detailed notes |

!!! note "No photo on an annotation"
    An annotation carries no image. Photograph the defect with a **Photo**
    capture on the inspection substep, or attach it to the quality report.

## Analyzing Heat Maps

### Pattern Recognition

Look for:

- **Clusters**: Multiple defects in one area
- **Linear patterns**: Along edges or features
- **Symmetry**: Mirror issues suggest tooling
- **Random scatter**: Different root causes

### Root Cause Insights

| Pattern | Possible Cause |
|---------|----------------|
| Edge concentration | Handling damage, tooling entry |
| Corner clusters | Machining access issues |
| Center area | Material defects |
| Consistent location | Fixture or tooling issue |
| Random distribution | Multiple causes |

!!! example "A cluster that points upstream"
    Defects clustering at the same spot on the model across many parts, invisible
    in a table of reports, usually share a cause upstream: a fixture, a tool, or a
    supplier batch. That is the pattern to raise a CAPA on.

### Correlation

Correlate heat map with:

- Equipment used
- Operator
- Material lot
- Time of production

## Heat Map Reports

!!! note "No export"
    The heat map cannot be exported as an image, PDF or CSV. Annotation data is
    available through the REST API.

## Time-Based Analysis

Use the **Date Range** filter to compare defect patterns over time — before and
after a process change, across production periods, or to confirm an improvement
held.

## Permissions

| Permission | Allows |
|------------|--------|
| `view_heatmapannotations` | View heat maps and their annotations |
| `add_heatmapannotations` | Create annotations |
| `delete_heatmapannotations` | Delete an annotation while its report is still Pending |
| `delete_submitted_heatmapannotations` | Delete one on a finished report — by default the quality team only |
| `view_threedmodel` | Access 3D models |

## Next Steps

- [3D Models](../3d-models/uploading.md) - Model management
- [Creating Annotations](../3d-models/annotations.md) - Annotation guide
- [Defect Analysis](defects.md) - Statistical analysis
