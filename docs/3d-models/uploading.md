# Uploading 3D Models

3D models enable visual defect tracking and heat map analysis. This guide covers uploading and configuring models.

## Supported File Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| **glTF** | .gltf, .glb | Recommended format, web-optimized |
| **OBJ** | .obj | Common 3D format |
| **STL** | .stl | CAD/3D printing format |
| **STEP** | .step, .stp | CAD exchange format — converted for you |
| **PLY** | .ply | Mesh format |

Everything is converted to **GLB** after upload, whatever you send.

!!! warning "FBX and IGES are not supported"
    Earlier versions of this page listed them. Convert to STEP, STL, OBJ or
    glTF first.

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
| **Part Type** | Associated part type |
| **Description** | Optional notes |
| **Version** | Model version |

5. Click **Upload**

### File Size Guidelines

| Size | Recommendation |
|------|----------------|
| < 10 MB | Optimal, fast loading |
| 10-50 MB | Acceptable, may load slowly |
| > 50 MB | Consider simplifying |

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

### From STEP

**You do not need to convert a STEP file.** Upload it as-is — the server
converts it to GLB for you. Converting it yourself in CAD first is wasted work
and usually loses fidelity.

Convert by hand only for a format not in the table above, such as FBX or
IGES.

### From STL

STL files usually work directly, but consider:
- Adding smooth normals
- Reducing if very high-poly
- Converting to glTF for smaller size

## Model Positioning

!!! warning "There are no orientation, scale or units controls"
    The upload form has four fields — Name, Part Type, Description, Version —
    and nothing to rotate, centre, set an "up" direction, choose units or apply
    a scale factor.

    The model is used as it was exported, so **get the orientation and scale
    right in your CAD package before uploading**. A model that imports sideways
    is re-exported and uploaded again.

## Linking to Part Types

Each model is linked to a Part Type:

1. Edit the model
2. Select **Part Type**
3. Save

When creating defect annotations on parts of that type, this model is used.

!!! note "One model per part type"
    A model is linked to a part type and that is the model used for annotation
    on parts of that type. There is no concept of alternative views — assembly,
    exploded, cross-section — attached to one part type.

## Model Versioning

When parts change, update models:

!!! note "Planned Feature"
    There is no in-place **Upload New Version** action on a 3D model. Upload the
    updated file as a model record and retire the old one.

Previous versions are retained for historical parts.

## Thumbnail Generation

Thumbnails are generated automatically and used in lists and previews. There
is no way to regenerate or re-frame one — the viewer has no camera control to
set a view from.

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
