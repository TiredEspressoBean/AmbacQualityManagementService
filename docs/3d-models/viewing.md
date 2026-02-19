# Viewing 3D Models

The 3D model viewer allows you to inspect parts visually and interact with defect annotations.

## Accessing the Viewer

### From Heat Map Page

1. Navigate to **Quality** > **Heat Map**
2. Select a Part Type with a 3D model
3. Viewer loads automatically

### From Part Detail

1. Open a part record
2. If the part type has a 3D model, click **View 3D Model**
3. Viewer opens with part-specific annotations

### Direct Access

Navigate to `/heatMapViewer/partType/{id}` or `/heatMapViewer/part/{id}`

## Viewer Interface

```
┌─────────────────────────────────────────────────────────┐
│  [Controls]                              [Settings]     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│                                                         │
│                    3D Model View                        │
│                                                         │
│                                                         │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  [Annotations List]                                     │
└─────────────────────────────────────────────────────────┘
```

## Navigation Controls

### Mouse Controls

| Action | Effect |
|--------|--------|
| **Left Drag** | Rotate model |
| **Right Drag** | Pan view |
| **Scroll** | Zoom in/out |
| **Double Click** | Center on clicked point |

### Touch Controls (Mobile/Tablet)

| Action | Effect |
|--------|--------|
| **One Finger Drag** | Rotate |
| **Two Finger Drag** | Pan |
| **Pinch** | Zoom |
| **Double Tap** | Reset view |

### Keyboard Shortcuts

| Key | Effect |
|-----|--------|
| `R` | Reset view |
| `+` / `-` | Zoom in/out |
| `Arrow Keys` | Rotate |
| `Esc` | Deselect annotation |

## Toolbar Controls

### View Controls

| Button | Function |
|--------|----------|
| **Reset** | Return to default view |
| **Zoom to Fit** | Fit model in view |
| **Front/Back/Side** | Preset angles |
| **Perspective/Ortho** | Toggle projection |

### Display Options

| Option | Function |
|--------|----------|
| **Wireframe** | Show mesh edges |
| **Solid** | Normal rendering |
| **X-Ray** | Semi-transparent |
| **Points** | Show annotation points |

### Annotation Controls

| Option | Function |
|--------|----------|
| **Show All** | Display all annotations |
| **Filter** | Filter by type/severity |
| **Hide** | Hide annotations |
| **Add** | Create new annotation |

## Annotation Points

Annotations appear as colored markers on the model:

### Color Coding

| Color | Meaning |
|-------|---------|
| **Red** | Critical severity |
| **Orange** | Major severity |
| **Yellow** | Minor severity |
| **Blue** | Information/note |

### Heat Map Mode

In heat map mode, points are colored by frequency:

| Color | Frequency |
|-------|-----------|
| **Blue** | Low (1-2 occurrences) |
| **Green** | Medium-low |
| **Yellow** | Medium |
| **Orange** | Medium-high |
| **Red** | High (many occurrences) |

## Interacting with Annotations

### Selecting Annotations

1. Click on an annotation point
2. Point highlights
3. Details panel shows information

### Annotation Details

When selected, view:
- Error type
- Severity
- Description
- Date created
- Who created it
- Linked quality report

### Navigation from Annotation

From annotation details:
- **View NCR**: Open linked quality report
- **View Part**: Go to part record
- **View Similar**: Find similar annotations

## Filtering Annotations

Filter which annotations display:

### By Error Type
- Select specific types
- Show only dimensional, visual, etc.

### By Severity
- Critical only
- Major and above
- All

### By Date Range
- Recent only
- Specific period
- All time

### By Part
- Specific part's annotations
- All parts of type

## Exporting Views

### Screenshot

1. Position model as desired
2. Click **Screenshot** or camera icon
3. PNG downloads with current view

### Print View

1. Click **Print**
2. Print-optimized layout generates
3. Print or save as PDF

## Performance Tips

### Slow Loading

- Check internet connection
- Wait for full model load
- Try reducing annotation count (filter)

### Choppy Rotation

- Close other browser tabs
- Use modern browser (Chrome, Firefox, Edge)
- Reduce display quality in settings

### Mobile Performance

- Use WiFi connection
- Limit annotation display
- Accept simplified rendering

## Permissions

| Permission | Allows |
|------------|--------|
| `view_threedmodel` | View models |
| `view_heatmap` | View heat map overlays |
| `add_annotation` | Create new annotations |

## Next Steps

- [Creating Annotations](annotations.md) - Add defect markers
- [Heat Map Visualization](heatmap-viz.md) - Defect frequency display
- [Uploading Models](uploading.md) - Add new models
