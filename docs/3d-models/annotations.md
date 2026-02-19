# Creating Annotations

Annotations mark defect locations on 3D models, enabling visual tracking and heat map analysis.

## What are Annotations?

Annotations are:

- **Location markers** on 3D models
- **Linked to quality data** (NCRs, parts)
- **Aggregated for heat maps** to show patterns
- **Visual documentation** of defects

## When to Create Annotations

Create annotations when:

- Recording a defect location
- Documenting inspection findings
- Flagging an issue on a part
- Building quality history

## Creating an Annotation

### Method 1: From Part Annotator

1. Navigate to **Part Annotator** (`/annotator`)
2. Select the part
3. Model loads with existing annotations
4. Click location on model where defect is
5. Fill in annotation form
6. Save

### Method 2: During Quality Report Creation

1. Create or open a quality report
2. Click **Add Annotation** or **Mark on Model**
3. 3D viewer opens
4. Click defect location
5. Annotation links to NCR automatically

### Method 3: From Heat Map Viewer

1. Open Heat Map for part type
2. Click **Add Annotation** button
3. Select part to annotate
4. Click location on model
5. Complete annotation form

## Annotation Form

### Required Fields

| Field | Description |
|-------|-------------|
| **Location** | Auto-captured from click (X, Y, Z) |
| **Error Type** | Category of defect |
| **Severity** | Minor, Major, Critical |

### Optional Fields

| Field | Description |
|-------|-------------|
| **Description** | Detailed notes |
| **Linked NCR** | Quality report reference |
| **Photo** | Image attachment |

## Precise Placement

### Clicking on Model

1. Rotate model to see defect location
2. Click directly on surface
3. Marker appears at click point
4. Adjust if needed by dragging

### Coordinates Display

As you move cursor:
- X, Y, Z coordinates display
- Helps with precise placement
- Matches real part dimensions

### Adjustment

After placing:
1. Click annotation to select
2. Drag to adjust position
3. Or enter coordinates manually
4. Save changes

## Annotation Types

### Single Point
Standard annotation at one location:
- Click to place
- Best for discrete defects

### Area (if supported)
Mark a region:
- Click multiple points to define boundary
- For larger defect areas
- Shows as highlighted region

## Attaching Photos

Add visual evidence:

1. In annotation form, find **Photo** section
2. Click **Upload** or drag image
3. Image attaches to annotation
4. Viewable from annotation details

Photo tips:
- Clear, focused images
- Include reference for scale
- Consistent lighting
- Capture before any repair

## Linking to Quality Reports

### During NCR Creation

1. Annotation created from NCR automatically links
2. Appear in NCR's annotation section
3. NCR shows annotation location

### Manual Linking

1. Open existing annotation
2. Click **Link to NCR**
3. Search and select NCR
4. Save

### Viewing Links

From annotation:
- See linked NCR
- Click to open NCR

From NCR:
- See all linked annotations
- Click to view on model

## Editing Annotations

### Modifying

1. Click annotation on model
2. Click **Edit**
3. Change fields as needed
4. Save

Changes are logged in audit trail.

### Repositioning

1. Select annotation
2. Click **Move**
3. Click new location
4. Save

### Deleting

1. Select annotation
2. Click **Delete**
3. Confirm

!!! note "Audit Trail"
    Deleted annotations are logged. Consider whether annotation should remain for historical accuracy.

## Viewing Existing Annotations

### On Model

Annotations appear as colored points:
- Click to see details
- Hover for quick info
- Color indicates severity

### In List

Below the viewer, annotation list shows:
- Error type
- Severity
- Date created
- Creator

Click list item to highlight on model.

## Bulk Annotations

For multiple defects of same type:

1. Click **Multi-Add** mode
2. Configure error type and severity
3. Click multiple locations
4. All share same settings
5. Exit multi-add mode
6. Save

## Annotation Permissions

| Permission | Allows |
|------------|--------|
| `add_heatmapannotation` | Create annotations |
| `change_heatmapannotation` | Edit annotations |
| `delete_heatmapannotation` | Remove annotations |
| `view_heatmapannotation` | View annotations |

## Best Practices

1. **Accurate placement** - Precise location matters for analysis
2. **Consistent classification** - Use correct error types
3. **Add context** - Descriptions help investigation
4. **Include photos** - Visual evidence is valuable
5. **Link to NCRs** - Connects data for traceability

## Troubleshooting

### Can't Click on Model
- Ensure model is fully loaded
- Check annotation mode is enabled
- Try different view angle

### Annotation Appears Wrong Location
- Verify model scale is correct
- Check surface normals
- Try different click position

### Photo Won't Upload
- Check file size (< 10 MB)
- Use supported format (PNG, JPG)
- Verify upload permission

## Next Steps

- [Heat Map Visualization](heatmap-viz.md) - See aggregated data
- [Viewing Models](viewing.md) - Navigation guide
- [Quality Reports](../workflows/quality/quality-reports.md) - NCR management
