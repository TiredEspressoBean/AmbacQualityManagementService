# Uploading 3D Models

3D models enable visual defect tracking and heat map analysis. This guide covers uploading and configuring models.

## Supported File Formats

| Format | Extension | How it is handled |
|--------|-----------|-------------------|
| **STEP** | .step, .stp | CAD — meshed for you |
| **IGES** | .iges, .igs | CAD — meshed for you |
| **STL** | .stl | Mesh |
| **OBJ** | .obj | Mesh |
| **PLY** | .ply | Mesh |
| **glTF** | .gltf, .glb | Target format, optimised if needed |

Up to **50 MB**. Everything is converted to **GLB**, whatever you send.

!!! warning "FBX is not supported"
    Convert to one of the formats above first. The upload form's file picker
    takes only the extensions in the table, so it will not accept an FBX file.

### Things worth knowing per format

- **IGES** often carries open surfaces rather than closed solids. Those mesh,
  but can show **gaps** a STEP export of the same part would not. If an IGES
  model looks holed, re-export it as STEP.
- **glTF must be self-contained.** Use **GLB** if your export has separate
  `.bin` or texture files — the loose files are not uploaded with it.
- **An OBJ's materials are not kept.** Geometry survives; colours and textures
  do not.
- **Large meshes are decimated** toward a face target, so the model the viewer
  shows can be lighter than the file you sent.

!!! important "Conversion is not instant"
    The upload returns before the model is ready. It is saved as **Pending**,
    a background job converts it, and it finishes **Completed** or **Failed** —
    a failure records the reason on the model.

    So a model is **not viewable the moment you upload it**, and a model that
    never appears in the viewer is worth checking for a failed conversion
    rather than assumed missing. The status and the failure reason are not
    shown on screen; in the **3D Models** list, a new model's **File Type**
    reads **glb** once conversion has completed and **N/A** until then — or
    for good, if it failed.

### Recommended: glTF

glTF (GL Transmission Format) is preferred because:
- Web-optimized for fast loading
- Supports materials and textures
- Binary version (.glb) is compact
- Wide tool support

## Uploading a Model

### From 3D Models Editor

1. Navigate to **Data Management** > **3D Models**
2. Click **New 3D Models**
3. Select or drag-drop your file
4. Fill in model details:

| Field | Description |
|-------|-------------|
| **Model Name** | Display name |
| **3D Model File** | The model file |
| **Part Type** | The part type it shows — required |
| **Step** | Optional: the step whose intermediate state it shows, when it is not the finished part |

A model is versioned for you; there is no version field to fill in.

5. Click **Upload Model**

### File Size Guidelines

| Size | Recommendation |
|------|----------------|
| < 10 MB | Optimal, fast loading |
| 10-50 MB | Acceptable, may load slowly |
| > 50 MB | **Refused** — the form will not take it |

## Model Optimization

For best performance, optimize models before uploading:

### Reduce Polygon Count
- Simplify mesh in CAD software
- Remove internal geometry
- Use decimation tools

### Optimize Textures
- Compress texture images
- Reduce texture resolution
- Use efficient formats (PNG, JPEG)

### Clean Up
- Remove unused materials
- Delete hidden objects
- Merge duplicate vertices

## Converting Models

### From CAD

**You do not need to convert a STEP or IGES file.** Upload it as-is — the
server meshes it for you. Converting it yourself in CAD first is wasted work
and usually loses fidelity.

Convert by hand only for a format outside the table above, such as FBX.

### From STL

STL files usually work directly, but consider:
- Adding smooth normals
- Reducing if very high-poly
- Converting to glTF for smaller size

## Model Positioning

!!! warning "There are no orientation, scale or units controls"
    The upload form has four fields — Model Name, 3D Model File, Part Type and
    Step — and
    nothing to rotate, centre, set an "up" direction, choose units or apply
    a scale factor.

    The model is used as it was exported, so **get the orientation and scale
    right in your CAD package before uploading**. A model that imports sideways
    is re-exported and uploaded again.

## Linking to Part Types

Every model belongs to a **part type**, chosen on the form. A part type can have
**several** models — the finished part, and others tied to a **step** to show an
intermediate state.

!!! warning "Which model gets annotated"
    Each place that annotates picks one of the part type's models for you:

    - **The work order page's QA panel** (**3D** tab) uses a model that has
      finished converting, preferring one with no step; among several, the one
      that comes first alphabetically.
    - **The Annotator** (`/annotator`) uses the part type's model that comes
      **first alphabetically** — whatever its step, and whether or not it has
      finished converting.
    - **A work-instruction substep** uses the model its **Part annotation**
      capture was authored with.

    With more than one model on a type, name the one you want annotated so it
    sorts first, and archive models you no longer use.

## Model Versioning

To replace a model's file, open it from the **3D Models** list (**Edit 3D
Model**), choose the new file under **3D Model File** and **Save Changes**. That
creates a new version of the model, which is converted again like a fresh
upload. Annotations belong to the version they were placed on, so the earlier
version's annotations stay with it.

## Thumbnails

There are none. Models are listed by name; to see one, open its part type on the
**Heat Map** page.

## Permissions

| Permission | Allows |
|------------|--------|
| `view_threedmodel` | View models |
| `add_threedmodel` | Upload new models |
| `change_threedmodel` | Edit and update |
| `delete_threedmodel` | Remove models |

## Troubleshooting

### Model Won't Load
- Check file format is supported
- Verify file isn't corrupted
- Try converting to glTF
- Check file size

### Model Looks Wrong
- Verify scale/units
- Check orientation
- Review normals (may be inverted)
- Check material settings

### Slow Loading
- Reduce polygon count
- Compress textures
- Use glTF binary (.glb)
- Simplify geometry

## Next Steps

- [Viewing Models](viewing.md) - Navigation and interaction
- [Creating Annotations](annotations.md) - Adding defect markers
- [Heat Map Visualization](heatmap-viz.md) - Defect overlays
