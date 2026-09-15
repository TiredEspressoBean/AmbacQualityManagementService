# Part Types

Define product templates that determine how parts are tracked.

## What are Part Types?

Part Types define:

- **Product identity** - Part number, description
- **Default process** - Manufacturing workflow
- **Attributes** - Fields for this type of part
- **3D model** - Visual representation

## Creating a Part Type

1. Navigate to **Admin** > **Data Management** > **Part Types**
2. Click **New Part Types**
3. Fill in details:

| Field | Description | Required |
|-------|-------------|----------|
| **Name** | Part type name | Yes |
| **ERP ID Prefix** | Prefix used when generating part identifiers | No |
| **ERP ID** | External identifier for this type | No |
| **Made in-house** | This type can be manufactured | No |
| **Purchased** | This type can be bought | No |
| **ITAR Controlled** | Subject to ITAR | No |
| **ECCN** | Export Control Classification Number | No |
| **USML Category** | US Munitions List category | No |

4. Click **Create Part Type**

!!! tip "Make, buy, or both"
    **Made in-house** and **Purchased** are independent. A type that is both
    can be manufactured or sourced, which is what lets it appear in production
    and in [sourcing requirements](../../workflows/scheduling/overview.md#requirements).

## Part Type Fields

### Identification

| Field | Description |
|-------|-------------|
| **Name** | Display name |
| **ERP ID Prefix** | Prefix for generated part identifiers |
| **ERP ID** | External identifier |

### Sourcing

| Field | Description |
|-------|-------------|
| **Made in-house** | Can be manufactured |
| **Purchased** | Can be bought |
| **Preferred supplier** | Default supplier for purchased types |
| **Purchase lead time (days)** | Lead time used by sourcing requirements |
| **Requires supplier qualification** | Only qualified suppliers may supply it |
| **Requires part approval** | Lots are held from suppliers without a [part approval](../../workflows/supply/part-approvals.md) |

### Export Control

| Field | Description |
|-------|-------------|
| **ITAR Controlled** | Subject to ITAR |
| **ECCN** | Export Control Classification Number |
| **USML Category** | US Munitions List category |

See [Export Controls](../../compliance/export-controls.md).

!!! note "Not part-type fields"
    Cycle time is set per **step** in the process, not on the part type — see
    [Step Configuration](../processes/steps.md). There is no customer part
    number, revision, unit of measure, inspection level, or critical-dimension
    field on a part type.

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

- By product line (Common Rail, HEUI, Unit Injector)
- By customer (OEM vs Aftermarket)
- By facility
- By application (Automotive, Heavy Duty, Marine)

Use categories for filtering and reporting.

!!! example "Injector Product Lines"
    - **Common Rail Injector** - Bosch, Denso, Delphi common rail systems
    - **HEUI Injector** - Caterpillar/Navistar hydraulic electronic injectors
    - **Unit Injector** - Detroit Diesel, Cummins mechanical unit injectors

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
CRI-100,Common Rail Injector,Diesel common rail fuel injector,Common Rail Injector Remanufacturing
HEUI-200,HEUI Injector,Hydraulic electronic unit injector,HEUI Remanufacturing
UI-300,Unit Injector,Mechanical unit fuel injector,Unit Injector Remanufacturing
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
| `view_parttypes` | View part types |
| `add_parttypes` | Create part types |
| `change_parttypes` | Edit part types |
| `delete_parttypes` | Deactivate part types |

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
