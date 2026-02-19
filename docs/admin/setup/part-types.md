# Part Types

Define product templates that determine how parts are tracked.

## What are Part Types?

Part Types define:

- **Product identity** - Part number, description
- **Default process** - Manufacturing workflow
- **Attributes** - Fields for this type of part
- **3D model** - Visual representation

## Creating a Part Type

1. Navigate to **Data Management** > **Part Types**
2. Click **+ New Part Type**
3. Fill in details:

| Field | Description | Required |
|-------|-------------|----------|
| **Name** | Part type name | Yes |
| **Part Number** | Product identifier | Yes |
| **Description** | Product description | No |
| **Default Process** | Manufacturing workflow | Recommended |
| **Active** | Available for use | Yes |

4. Save

## Part Type Fields

### Identification

| Field | Description |
|-------|-------------|
| **Name** | Display name |
| **Part Number** | Your numbering scheme |
| **Customer Part Number** | Customer's identifier |
| **Revision** | Drawing revision |
| **UOM** | Unit of measure (each, ft, kg) |

### Manufacturing

| Field | Description |
|-------|-------------|
| **Default Process** | Primary manufacturing process |
| **Alternate Processes** | Other valid processes |
| **Estimated Cycle Time** | Per-part production time |
| **Material** | Primary material |

### Quality

| Field | Description |
|-------|-------------|
| **Inspection Level** | Default inspection requirements |
| **Critical Dimensions** | Key measurements |
| **3D Model** | Linked visual model |
| **Drawing** | Linked drawing document |

### Export Control

| Field | Description |
|-------|-------------|
| **ITAR Controlled** | Defense article flag |
| **ECCN** | Export classification |
| **Country of Origin** | Manufacturing location |

## Linking to Process

Connect part type to manufacturing process:

1. In **Default Process** field
2. Select process
3. All parts of this type use this process by default
4. Can override per work order

## 3D Model

Link visual model for annotations:

1. In **3D Model** field
2. Select uploaded model
3. Model used for heat maps
4. Enable defect annotation

See [Uploading Models](../../3d-models/uploading.md).

## Drawing Links

Attach engineering drawings:

1. In **Drawing** field
2. Select or upload drawing
3. Available during production
4. Revision tracked

## Custom Attributes

If custom fields are configured:

- Additional part type-specific fields
- Captured when creating parts
- Displayed in part detail

## Part Type Categories

Organize part types:

- By product line
- By customer
- By facility
- By material type

Use categories for filtering and reporting.

## Part Type Versioning

Track changes to part type configuration:

- Version history maintained
- Changes logged
- Can revert if needed

Important for audit compliance.

## Creating Parts from Type

When parts are created:

1. Select part type
2. Type defaults apply
3. Process assigned
4. Attributes pre-filled

Parts inherit from type configuration.

## Bulk Operations

### Import Part Types

```csv
part_number,name,description,default_process
PN-001,Widget Assembly,Standard widget,Widget Production
PN-002,Bracket,Steel bracket,Bracket Process
```

### Export Part Types

1. Click **Export**
2. Download CSV with all part types
3. Use for reference or import to other system

## Active vs Inactive

- **Active**: Available for new parts
- **Inactive**: Hidden from selection, existing parts remain

Don't delete—inactivate to preserve history.

## Permissions

| Permission | Allows |
|------------|--------|
| `view_parttype` | View part types |
| `add_parttype` | Create part types |
| `change_parttype` | Edit part types |
| `delete_parttype` | Deactivate part types |

## Best Practices

1. **Consistent numbering** - Standard part number format
2. **Complete configuration** - Fill in all relevant fields
3. **Link processes** - Connect to manufacturing
4. **Attach drawings** - Documents readily available
5. **Regular review** - Keep current

## Next Steps

- [Process Configuration](../processes/overview.md) - Manufacturing workflows
- [Equipment](equipment.md) - Production equipment
- [Error Types](error-types.md) - Defect categories
