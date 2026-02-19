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

Navigate to **Quality** > **Heat Map** or `/heatmap`

## Heat Map Views

### By Part Type

View aggregate defects across all parts of a type:

1. Select a Part Type
2. Heat map shows defect frequency across all parts
3. Identifies systemic location issues

### By Specific Part

View defects on a single part:

1. Select or search for part
2. See all defects on that part
3. Useful for part-specific analysis

### By Order

View defects across parts in an order:

1. Select order
2. Combined heat map of all parts
3. Identify order-specific patterns

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

Each point represents:

| Data | Description |
|------|-------------|
| **Location** | X, Y, Z coordinates |
| **Frequency** | Number of defects at location |
| **Error Types** | Types of defects found |
| **Severity** | Distribution of severities |

### Filtering

Filter heat map data:

- **Date Range**: Time period
- **Error Type**: Specific defect types
- **Severity**: Minor/Major/Critical
- **Detected By**: Who found the defects

## Creating Annotations

### During Inspection

1. Flag a part with defect
2. Select **Annotate on Model**
3. Click location on 3D model
4. Enter defect details
5. Save annotation

### From Part Annotator

Navigate to **Part Annotator** (`/annotator`):

1. Select part and model
2. Click location of defect
3. Fill in annotation form
4. Attach photo if available
5. Save

### Annotation Details

| Field | Description |
|-------|-------------|
| **Location** | 3D coordinates (auto from click) |
| **Error Type** | Category of defect |
| **Severity** | Minor/Major/Critical |
| **Description** | Detailed notes |
| **Photo** | Optional image |

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

### Correlation

Correlate heat map with:

- Equipment used
- Operator
- Material lot
- Time of production

## Heat Map Reports

### Export Options

- **Image**: PNG for presentations
- **PDF**: With statistics summary
- **Data**: CSV of annotation locations

### Report Contents

- 3D view capture
- Location frequency table
- Error type breakdown
- Trend comparison

## Time-Based Analysis

Compare heat maps over time:

- Before and after process changes
- Different production periods
- Improvement validation

## Permissions

| Permission | Allows |
|------------|--------|
| `view_heatmap` | View heat maps |
| `add_annotation` | Create annotations |
| `view_threedmodel` | Access 3D models |

## Best Practices

1. **Annotate accurately** - Precise location matters
2. **Use consistently** - Train all inspectors
3. **Review patterns** - Regular analysis
4. **Act on insights** - Improve processes
5. **Track over time** - Measure improvement

## Next Steps

- [3D Models](../3d-models/uploading.md) - Model management
- [Creating Annotations](../3d-models/annotations.md) - Annotation guide
- [Defect Analysis](defects.md) - Statistical analysis
