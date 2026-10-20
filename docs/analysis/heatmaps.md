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

Pick a **Part Type** to see defects across every part of that type — the view
for systemic, location-driven problems — or a single **Part** to see just its
own.

!!! note "There is no by-order view"
    To look at one job, narrow by **Work Order** in the filters below.

## 3D Model Heat Map

When 3D models are configured:

### Interactive Viewer
- Rotate, zoom, pan the model
- Defect locations shown as colored points
- Click points for defect details

### Color Scale
```
Low ─────────────────────────────── High
Blue    Green    Yellow    Orange    Red
```

### Navigation
- **Scroll**: Zoom in/out
- **Drag**: Rotate model
- **Shift+Drag**: Pan
- **Click point**: View defect detail

## Heat Map Data

Each point is an **annotation**: a location on the model, the defect type
recorded, its severity, notes, who reported it and when.

### Filtering

| Filter | Options |
|--------|---------|
| **Manufacturing Step** | All steps, or one |
| **Defect Type** | All defect types, or one |
| **Severity** | All, **Low**, **Medium**, **High** or **Critical** |
| **Date Range** | All time, last 7, 30 or 90 days, or a custom range |
| **Work Order** | All work orders, or one |

**Heatmap Settings** adjusts how the points are drawn.

## Creating Annotations

An annotation has to belong to a **quality report**: the annotator asks you to
*select a report to annotate* before you can place a point.

### Where

- **In the step player**, where a substep carries a **Part annotation** capture
- **On the work order page**, from the QA panel on the right when a part is
  selected

### Placing one

1. Choose the quality report
2. Click the defect location on the 3D model
3. Fill in **Error Type**, **Severity Level** and **Notes**
4. Save

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
