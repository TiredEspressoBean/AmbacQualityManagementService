# Part Types

Define product templates that determine how parts are tracked.

## What are Part Types?

A part type is the definition of a thing you make, buy or recover. It carries:

- **Identity** — name, ERP id and the prefix used when generating part identifiers
- **Sourcing** — make, buy, preferred supplier, lead time, safety stock
- **Export control** — ITAR, ECCN, USML category
- **Receiving rules** — purchase unit, and the holds that keep a received lot
  from being used until its paperwork is in

!!! note "Processes and 3D models are attached *to* a part type, not chosen on it"
    A part type has no "default process" field and no "3D model" field. A
    [process](../processes/overview.md) names the part type it is for, and a
    [3D model](../../3d-models/uploading.md) does the same — so you create them
    against the type rather than picking them from the type's form.

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
    **Made in-house** and **Purchased** are independent, and a type can be both
    — a part you normally make but are short of this week.

    **Purchased** is the one that does work: it is what lets the type be a
    **BUY** line on a BOM, and what lets an expected receipt be imported
    against it. See [sourcing
    requirements](../../workflows/scheduling/overview.md#requirements).

!!! note "Made in-house is recorded but nothing reads it"
    Nothing refuses to manufacture a type with the flag off, and nothing
    filters by it. Set it accurately — it is the honest description of the
    part — but do not expect it to gate anything.

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

    There *is* a purchase unit — **Bought and counted by** — but it describes how the part is bought and
    counted at receiving rather than acting as a general unit of measure — see
    [Receiving and recovery](#receiving-and-recovery) below.

### Receiving and recovery

| Field | Description |
|-------|-------------|
| **Can be recovered** | A used one of these can be recovered from a torn-down core and put back into service. This is the MRO classification — rotable and repairable items can, expendables cannot. Leave it off and the type will not appear as something a teardown can yield. |
| **Default disassembly process** | Preselected in the operator's bulk-teardown dialog. Optional; without it the picker simply starts with nothing chosen. |
| **Bought and counted by** | How the part is **bought and counted at receiving** — the stock unit, **Box**, or **Pound (weighed)**. |
| **&lt;stock unit&gt; per box** / **per pound** | Stock units in one box or one pound. Shown only when the part is bought by the box or by the pound. |
| **Requires a certificate of conformance** | Hold each received lot until its certificate of conformance is uploaded. |
| **Requires a heat number** | Hold each received lot until its heat / melt number is entered. |

!!! note "The four 'requires' flags are holds, not warnings"
    Requires a certificate of conformance, requires a heat number, requires supplier qualification and
    requires part approval each **hold a received lot** until the condition is met.
    If someone asks why received stock cannot be used yet, these are the first
    things to check — the lot is not lost, it is held.

## Giving a part type a process

Processes are authored against a part type from the process side — see
[Process Configuration](../processes/overview.md). A type can have several: a
manufacturing routing, and, where the type **can be recovered**, one or more
teardown processes. The work order picks which one it runs.

Only the **default disassembly process** is held on the part type, and only as a
preselection for the teardown dialog.

## 3D Model

A 3D model is uploaded against a part type, and optionally against a particular
step where it shows an intermediate state. Models are what defect annotations
and heat maps are drawn on.

See [Uploading Models](../../3d-models/uploading.md).

## Bulk import and export

Part types can be imported and exported. **Export first and fill in the file you
get back** rather than building one from a column list. The identity fields are
**Name**, **ERP ID** and **ERP ID Prefix** — there is no part number field.

Start at [Data Management](../data/data-management.md) for the Import and Export
links, and see [Import & Export](../data/import-export.md) for how references to
other records are written.

## Quality for a part type

In the part types list, click **View** on a row. The detail page carries a
**Quality Overview** panel, which rolls up every part of that type:

- **First Pass Yield** across all inspections, with passed, failed and pending counts
- **Parts** — how many parts of this type exist
- **Open dispositions** and **Open CAPAs**
- **FPY Trend (30 days)** — daily first-pass yield over the last month
- **Top Defects** — the defect Pareto
- **SPC / Measurement Capability** — for each numeric measurement, the share in spec and, where it can be computed, Ppk
- **Recent Failures** — the five latest failed inspections

The panel shows only the records you are allowed to see, so two people can see
different numbers for the same part type.

## Retiring a part type

!!! warning "Delete archives the part type"
    The **delete** icon on the part types list asks *"Archive this part type?"*
    and, on **Archive**, takes the type out of the active lists. Nothing is
    removed: its history is kept, and it can be restored from
    [Data Management](../data/data-management.md).

    Archiving is not refused because processes, parts or BOM lines still refer
    to the type — those records keep pointing at it. There is no separate
    active / inactive flag and no retirement status.

    To stop a type being bought while keeping it in use, turn **Purchased** off
    — that removes it from BOM buy lines and expected receipts.

## Permissions

| Permission | Allows |
|------------|--------|
| `view_parttypes` | View part types |
| `add_parttypes` | Create part types |
| `change_parttypes` | Edit part types |
| `change_parttype_sourcing` | Edit **only** preferred supplier, lead time and safety stock |
| `delete_parttypes` | Archive a part type |

## Next Steps

- [Process Configuration](../processes/overview.md) - Manufacturing workflows
- [Equipment](equipment.md) - Production equipment
- [Error Types](error-types.md) - Defect categories
