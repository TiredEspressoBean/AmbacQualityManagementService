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
| **Preferred supplier** | Default supplier for purchased types. Offers **suppliers only** |
| **Preferred supplier's lead time (days)** | Lead time used by sourcing requirements |
| **Safety stock** | A quantity held back from planning, so the sourcing report warns while there is still stock to react with |
| **Requires supplier qualification** | Only qualified suppliers may supply it |
| **Requires part approval** | Lots are held from suppliers without a [part approval](../../workflows/supply/part-approvals.md) |

!!! note "Safety stock doesn't stop you issuing"
    It is held back from the **planning** view, not from the shelf — the same as
    on a Material. The point is that the sourcing report goes red while you still
    have stock to react with, rather than when you are already out. See [How the
    numbers are made](../../workflows/scheduling/how-the-numbers-are-made.md).

### Who can change sourcing, and who can change the part

These are deliberately different people.

**Can change a part type's sourcing** covers just three fields — preferred
supplier, lead time, safety stock. **Purchasing** holds it, as does anyone who
can author part types.

On the part types list a holder sees a **truck** icon, **Sourcing**, which opens
a three-field dialog. The **pencil** and **delete** icons appear only with
`change_parttypes` / `delete_parttypes`.

!!! tip "A buyer can maintain sourcing without being able to edit the part"
    That is the whole point of the split. Lead times and preferred suppliers
    change often and belong to whoever buys; the part's definition does not and
    belongs to engineering.

!!! important "Sourcing changes do not create a new version"
    Supplier, lead time and safety stock are edited **in place**. They describe
    how you buy the thing, not what the thing is — so versioning them would fill
    the history with commercial churn and make a real engineering change harder
    to find.

    The change is still recorded in the audit log, and the **History** card shows
    it as an in-place change.

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
    number, revision, inspection level, or critical-dimension field on a part
    type, and no country of origin.

    There *is* a **purchase unit**, but it describes how the part is bought and
    counted at receiving rather than acting as a general unit of measure — see
    [Receiving and recovery](#receiving-and-recovery) below.

### Receiving and recovery

| Field | Description |
|-------|-------------|
| **Can be recovered** | A used one of these can be recovered from a torn-down core and put back into service. This is the MRO classification — rotable and repairable items can, expendables cannot. Leave it off and the type will not appear as something a teardown can yield. |
| **Default disassembly process** | Preselected in the operator's bulk-teardown dialog. Optional; without it the picker simply starts with nothing chosen. |
| **Purchase unit** | How the part is **bought and counted at receiving** — stock unit, box, or pound. |
| **Units per purchase unit** | Stock units in one purchase unit, so pieces per box or pieces per pound. Not used when the purchase unit is already the stock unit. |
| **Requires CoC** | Hold each received lot until its certificate of conformance is uploaded. |
| **Requires heat number** | Hold each received lot until its heat / melt number is entered. |

!!! note "The four 'requires' flags are holds, not warnings"
    Requires CoC, requires heat number, requires supplier qualification and
    requires part approval each **hold a received lot** until the condition is met.
    If someone asks why received stock cannot be used yet, these are the first
    things to check — the lot is not lost, it is held.

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

## Creating parts from a type

When parts are created against a type, the type's defaults apply — its process,
its ERP ID prefix, and the rest of its configuration.

## Bulk import and export

Part types can be imported and exported. **Export first and fill in the file you
get back** rather than building one from a column list: the identity fields are
**Name**, **ERP ID** and **ERP ID Prefix**, and an older version of this page
showed a `part_number` column that is not a field.

Start at [Data Management](../data/data-management.md) for the Import and Export
links, and see [Import & Export](../data/import-export.md) for how references to
other records are written.

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

## Next Steps

- [Process Configuration](../processes/overview.md) - Manufacturing workflows
- [Equipment](equipment.md) - Production equipment
- [Error Types](error-types.md) - Defect categories
