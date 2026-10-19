# Viewing 3D Models

The 3D model viewer allows you to inspect parts visually and interact with defect annotations.

## Accessing the Viewer

### From Heat Map Page

1. Navigate to **Quality** > **Heat Map**
2. Select a Part Type with a 3D model
3. Viewer loads automatically

### From the work order page

Select a part, and the **QA panel** on the right shows its part type's model —
see [which model it uses](uploading.md#linking-to-part-types).

### Direct Access

Navigate to `/heatMapViewer/partType/{id}` or `/heatMapViewer/part/{id}`

## Viewer Interface

The model fills the page, with the filters and heat map settings beside it and a
short controls reminder in the bottom-left corner. Selecting an annotation opens
its panel alongside the model.

## Navigation Controls

### Mouse Controls

| Action | Effect |
|--------|--------|
| **Left Drag** | Rotate model |
| **Right Drag** | Pan view |
| **Scroll** | Zoom in/out |

### Touch Controls (Mobile/Tablet)

| Action | Effect |
|--------|--------|
| **One Finger Drag** | Rotate |
| **Two Finger Drag** | Pan |
| **Pinch** | Zoom |

### Keyboard Shortcuts

| Key | Effect |
|-----|--------|
| `W` / `S` | Move forward / back |
| `A` / `D` | Strafe left / right |
| `Space` / `Ctrl` | Move up / down |
| `Q` / `E` | Yaw left / right |
| `R` / `F` | Pitch up / down |
| `Z` / `C` | Roll |
| `G` | Fullscreen |
| `Shift` | Hold for faster movement |

The viewer flies a camera rather than spinning a turntable, so movement is
WASD as in a game. The mouse still orbits, pans and zooms.

## Toolbar Controls

### Lighting

The one settings panel adjusts lighting: **Ambient**, **Main Light** and
**Fill Light**.

!!! warning "The rest of the toolbar does not exist"
    There is no Reset, Zoom to Fit, Front/Back/Side preset, Perspective/Ortho
    toggle, Wireframe, X-Ray, Points, Show All, Filter or Hide, and no
    double-click or double-tap action.

    To get back to a view you lost, reload the page.

!!! tip "Authors can save a starting view"
    In a work instruction's **Part annotation** capture, the author can use
    **Save view** to set the framing the operator's model opens at. That is
    the only place a view is saved.

!!! note "There is no Add button"
    Annotations are created by clicking the model itself while in annotate
    mode, and the annotation has to belong to a quality report. See
    [Annotations](annotations.md).

## How annotations appear

Annotations are drawn as **heat** on the model's surface, not as separate
markers: each one warms the area around its point, weighted by severity. See
[Heat Map Visualization](heatmap-viz.md) for how the colour is built.

## Selecting an annotation

Click on or near an annotated spot to select that annotation. Its panel shows
the **error type**, **severity**, **notes**, **who reported it**, the **date
found** and the **part**, with **Edit Annotation** for the first three.

!!! note "No links out from the panel"
    The panel has no *View NCR*, *View Part* or *View Similar* action. Open the
    quality report or the part from their own lists.

## Filtering

On the heat map viewer: **Manufacturing Step**, **Defect Type**, **Severity**
(Low, Medium, High, Critical), **Date Range** (all time, last 7, 30 or 90 days,
or custom) and **Work Order**. To see one part rather than a whole part type,
open `/heatMapViewer/part/{id}`.

## Exporting Views

There is no screenshot, print or export control in the viewer. Use your
operating system's screen capture.

## Performance Tips

### Slow Loading

- Check internet connection
- Wait for full model load
- Try reducing annotation count (filter)

### Choppy Rotation

- Close other browser tabs
- Use a current browser (Chrome, Firefox, Edge)

### Mobile Performance

- Use WiFi connection
- Limit annotation display
- Accept simplified rendering

## Permissions

| Permission | Allows |
|------------|--------|
| `view_threedmodel` | View models |
| `view_heatmapannotations` | View heat maps and their annotations |
| `add_heatmapannotations` | Create new annotations |

## Next Steps

- [Creating Annotations](annotations.md) - Add defect markers
- [Heat Map Visualization](heatmap-viz.md) - Defect frequency display
- [Uploading Models](uploading.md) - Add new models
