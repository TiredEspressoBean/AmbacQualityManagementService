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
    Inspecting an injector body, an inspector marks a burr where a fuel passage
    breaks into the bore. The marker belongs to that inspection's quality report,
    and every marker like it adds to the heat map, where a repeat location shows up
    as a pattern.

## Creating an Annotation

### Method 1: From the work order page

1. Open the work order, select the part, and open the **3D** tab of the **QA
   panel** on the right — see [which model it uses](uploading.md#linking-to-part-types)
2. Under **Quality Report**, choose the report the defect belongs to. The list
   offers the work order's **Fail** reports that carry an error type marked
   **Requires 3D Annotation**
3. Click the location on the model where the defect is — a marker appears
4. Click the marker to open *Edit Defect Annotation*, and fill in **Error
   Type**, **Severity Level** and **Notes**
5. Click **Save New (N)**

This panel shows only the markers you are placing now, not the part's earlier
annotations — those are on the [heat map](heatmap-viz.md) and in the Annotator.

### Method 2: The Annotator (`/annotator`)

The standalone page starts from **Select Quality Reports**, which lists the
reports carrying an error type marked **Requires 3D Annotation**. Tick the report
or reports and click **Start Annotating**: it opens their part on its model —
see [which model it uses](uploading.md#linking-to-part-types) — with the
annotations already on that part and model. Clicking the model opens
*Edit Defect Annotation* straight away, and the annotation is saved when you
close it. A disposition that is waiting on annotations links here — **Go to
Annotator** — with its reports already selected.

!!! note "There is no 'Add Annotation' button"
    Annotations are created by clicking the model itself while in annotate
    mode, and only once a quality report is selected — the annotation has to
    belong to something.

### Method 3: As a substep capture

A step can include a **Part annotation** capture, so the operator marks the
model as part of the work instructions. There the report is already the
substep's own. See [Authoring Work Instructions](../workflows/dwi/authoring.md).

!!! important "Some defects must be annotated before a disposition can close"
    An error type can be marked **Requires 3D Annotation**. A disposition linked
    to a quality report carrying such an error **cannot be completed** until
    that report has at least one annotation — the disposition form says *"N
    quality report(s) require 3D annotations before this disposition can be
    closed"* and links to the Annotator. See [Error Types](../admin/setup/error-types.md).

## Annotation Form

| Field | Description |
|-------|-------------|
| **Location** | Captured from your click on the model (X, Y, Z) — you do not type it |
| **Error Type** | Category of defect — the error types marked **Requires 3D Annotation** (from the work order page, those on the chosen report). Starts at the first one |
| **Severity Level** | Low, Medium, High or Critical. Starts at Low |
| **Notes** | Free text |

!!! note "The quality report is not an optional field"
    An annotation belongs to a report — in standalone QA review you select the
    report *before* the model accepts a click, and in a substep capture the
    report is the substep's own. There is no "Linked NCR" picker on the form.

## Where the annotation lands

The point is captured from where you click on the model. Rotate and zoom to get
the angle you want before clicking — the viewer's orbit, pan and zoom all work
in annotate mode.

## Correcting an annotation

| Change | Where |
|--------|-------|
| **Error type, severity, notes** | **Edit Annotation** on the heat map viewer, or *Edit Defect Annotation* in the annotator |
| **Delete it** | Select it in the annotator — *Edit Defect Annotation* — and delete. Once its quality report is finished, only the quality team can |
| **Move it** | Not possible. Delete it and place a new one |

!!! important "Deleting is open while inspecting, closed once the report is finished"
    While every quality report an annotation belongs to is still **Pending**,
    anyone on staff can delete it, so an inspector can remove a misplaced
    marker as they work.

    Once **any** of its reports is no longer Pending — **Pass**, **Fail** or
    **Needs repair** — the annotation is inspection evidence. Deleting it then needs
    `delete_submitted_heatmapannotations`, by default held by **QA Inspector,
    QA Manager and Tenant Admin**; anyone else does not see **Delete**, and the
    server refuses — *"This annotation is on a finished quality report, so it is
    inspection evidence. Only the quality team can delete it."*

    A delete archives the annotation rather than destroying it, and is in the
    audit log. Editing its type, severity and notes stays open to staff.

## Attaching Photos

Photos are attached through the quality report the annotation belongs to, not
through the annotation itself.

## Viewing Existing Annotations

Annotations show as markers on the model, and in the **Annotations** list that
the list button in the viewer's bottom-right corner opens. Select one, on the
model or in the list, to open it:

- In the **annotator**, it opens *Edit Defect Annotation* — error type,
  severity, notes, and delete
- On the **heat map viewer**, it shows its details — including **Date Found**
  and **Reported By** — with **Edit Annotation**

To see many at once across parts, use the [heat map](heatmap-viz.md), with its
filters.

## Annotation Permissions

| Permission | Allows |
|------------|--------|
| `add_heatmapannotations` | Create annotations |
| `change_heatmapannotations` | Edit an annotation's type, severity and notes |
| `delete_heatmapannotations` | Remove an annotation whose reports are all still Pending, or that has none |
| `delete_submitted_heatmapannotations` | Remove an annotation on a finished (Pass, Fail or Needs repair) report |
| `view_heatmapannotations` | View annotations |

## Troubleshooting

### Can't Click on Model
- Ensure model is fully loaded
- Check the annotator is set to **Annotate Defects**, not **Navigate View**
- Try different view angle

### Annotation Appears Wrong Location
- Rotate the model and check from another angle — a point that looks off from
  one view is often correct
- If it really is wrong, delete it and place it again; an annotation cannot be
  moved

### Photo Won't Upload
Photos attach to the **quality report**, not to the annotation. Upload it
there.

## Next Steps

- [Heat Map Visualization](heatmap-viz.md) - See aggregated data
- [Viewing Models](viewing.md) - Navigation guide
- [Quality Reports](../workflows/quality/quality-reports.md) - NCR management
