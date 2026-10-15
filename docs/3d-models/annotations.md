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

!!! example "Diesel Injector Annotation"
    When inspecting a Common Rail Injector, an inspector clicks on the nozzle tip area of the 3D model to mark erosion damage. This annotation links to quality report QR-2024-0187, contributing to the heat map that later revealed a systemic nozzle tip issue.

## Creating an Annotation

### Method 1: From Work Order

1. Navigate to **Production > Work Orders**
2. Open the work order containing the part you want to annotate
3. Find the part and click **Annotate** or open the annotation tool
4. Model loads with existing annotations
5. Click location on model where defect is
6. Fill in annotation form — **Error Type**, **Severity Level**, and **Notes**
7. Save

### Method 2: From a Quality Report

1. Open the **Part Annotator** for the part
2. Select the quality report the defect belongs to
3. Click the defect location directly on the model
4. Complete the annotation form
5. The annotation links to that report

!!! note "There is no 'Add Annotation' button"
    Annotations are created by clicking the model itself while in annotate
    mode. In standalone QA review you must select a quality report before
    the model accepts a click — the annotation has to belong to something.

### Method 3: As a substep capture

A step can include a **Part annotation** capture, so the operator marks the
model as part of the work instructions. See
[Authoring Work Instructions](../workflows/dwi/authoring.md).

## Annotation Form

| Field | Description |
|-------|-------------|
| **Location** | Captured from your click on the model (X, Y, Z) — you do not type it |
| **Error Type** | Category of defect |
| **Severity Level** | Minor, Major, Critical |
| **Notes** | Free text |

!!! note "The quality report is not an optional field"
    An annotation belongs to a report — in standalone QA review you select the
    report *before* the model accepts a click, and from Method 1 the report is
    the one you are working in. There is no "Linked NCR" picker on the form.

## Where the annotation lands

The point is captured from where you click on the model. Rotate and zoom to get
the angle you want before clicking — the viewer's orbit, pan and zoom all work
in annotate mode.

!!! warning "There is no way to edit, move or delete an annotation"
    No Edit, Move, Delete, Multi-Add or Area control exists, and no way to type
    coordinates by hand. A misplaced annotation is corrected the way any other
    quality record is: it stands, and you add a correct one.

    The API will accept a change to an annotation's position, so an integration
    could move one. Nothing in the product offers it.

    Older instructions on this page described all of those controls. None of
    them exist.

## Attaching Photos

Photos are attached through the quality report the annotation belongs to, not
through the annotation itself.

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

## Annotation Permissions

| Permission | Allows |
|------------|--------|
| `add_heatmapannotations` | Create annotations |
| `change_heatmapannotations` | Edit annotations |
| `delete_heatmapannotations` | Remove annotations |
| `view_heatmapannotations` | View annotations |

## Troubleshooting

### Can't Click on Model
- Ensure model is fully loaded
- Check annotation mode is enabled
- Try different view angle

### Annotation Appears Wrong Location
- Rotate the model and check from another angle — a point that looks off from
  one view is often correct
- Try a different click position on the next one; an existing annotation
  cannot be moved

### Photo Won't Upload
Photos attach to the **quality report**, not to the annotation. Upload it
there.

## Next Steps

- [Heat Map Visualization](heatmap-viz.md) - See aggregated data
- [Viewing Models](viewing.md) - Navigation guide
- [Quality Reports](../workflows/quality/quality-reports.md) - NCR management
