# Uploading 3D Models

3D models enable visual defect tracking and heat map analysis. This guide covers uploading and configuring models.

## Supported File Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| **glTF** | .gltf, .glb | Recommended format, web-optimized |
| **OBJ** | .obj | Common 3D format |
| **STL** | .stl | CAD/3D printing format |
| **FBX** | .fbx | Autodesk format |
| **STEP** | .step, .stp | CAD exchange format |

### Recommended: glTF

glTF (GL Transmission Format) is preferred because:
- Web-optimized for fast loading
- Supports materials and textures
- Binary version (.glb) is compact
- Wide tool support

## Uploading a Model

### From 3D Models Editor

1. Navigate to **Data Management** > **3D Models**
2. Click **+ Upload Model**
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

### From STEP/IGES

Use CAD software to convert:
1. Open in CAD (Fusion 360, FreeCAD, etc.)
2. Export as glTF or OBJ
3. Verify visual quality
4. Upload converted file

### From STL

STL files usually work directly, but consider:
- Adding smooth normals
- Reducing if very high-poly
- Converting to glTF for smaller size

## Model Positioning

After upload, position the model:

### Default Orientation
Model imports at original orientation. Adjust if needed:
- Rotate to standard viewing angle
- Set "up" direction
- Center the model

### Scale
Verify scale matches real part:
- Set units (mm, inches)
- Verify dimensions
- Adjust scale factor if needed

## Linking to Part Types

Each model is linked to a Part Type:

1. Edit the model
2. Select **Part Type**
3. Save

When creating defect annotations on parts of that type, this model is used.

## Multiple Views

Upload multiple models for different views:

- **Full Assembly**: Complete view
- **Exploded View**: Component relationships
- **Cross Section**: Internal features
- **Simplified**: Lower detail for overview

## Model Versioning

When parts change, update models:

1. Open existing model
2. Click **Upload New Version**
3. Select updated file
4. Enter version notes
5. Upload

Previous versions are retained for historical parts.

## Thumbnail Generation

Thumbnails are auto-generated:

- Used in lists and previews
- Captured from default view
- Regenerate by adjusting view and saving

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

## Best Practices

1. **Use glTF** - Best performance
2. **Optimize first** - Reduce before upload
3. **Set scale correctly** - Annotations depend on it
4. **Version control** - Track model changes
5. **Link to part types** - Enable annotations

## Next Steps

- [Viewing Models](viewing.md) - Navigation and interaction
- [Creating Annotations](annotations.md) - Adding defect markers
- [Heat Map Visualization](heatmap-viz.md) - Defect overlays
