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
    Convert to one of the formats above first. A file outside that list is
    rejected with *"Unsupported format: `.fbx`"* and the list of what is
    accepted.

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
    rather than assumed missing.

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
| **Name** | Display name |
| **File** | The model file |
| **Part Type** | The part type it shows — required |
| **Step** | Optional: the step whose intermediate state it shows, when it is not the finished part |

A model is versioned for you; there is no version field to fill in.

5. Click **Upload**

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
    The upload form has four fields — Name, File, Part Type and Step — and
    nothing to rotate, centre, set an "up" direction, choose units or apply
    a scale factor.

    The model is used as it was exported, so **get the orientation and scale
    right in your CAD package before uploading**. A model that imports sideways
    is re-exported and uploaded again.

## Linking to Part Types

Every model belongs to a **part type**, chosen on the form. A part type can have
**several** models — the finished part, and others tied to a **step** to show an
intermediate state.

!!! warning "The work order page annotates on the first model by name"
    When you annotate a part from the work order page's QA panel, it uses the
    part type's model that comes **first alphabetically** — whatever its step,
    and whether or not it has finished converting. With more than one model on a
    type, name the one you want annotated so it sorts first, and archive models
    you no longer use.

    Annotating from a work-instruction substep uses the model that substep's
    **Part annotation** capture was authored with.

## Model Versioning

There is no **Upload New Version** action on a 3D model. Upload the updated file
as a new model record and archive the old one. Annotations belong to the model
they were placed on, so the old model's annotations stay with it.

## Thumbnails

There are none. Models are listed by name; open one to see it.

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
