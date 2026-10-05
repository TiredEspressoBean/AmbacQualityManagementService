# Data Import & Export

Import and export data in bulk using CSV or Excel files.

## Overview

The import/export system provides:

- **Export**: Download filtered data as CSV or Excel
- **Import**: Upload data files to create or update records
- **Templates**: Download pre-formatted templates for data entry
- **Excel Features**: Reference sheets, dropdowns, and auto-calculated fields

## What supports it, and where the buttons are

**The buttons appear only where the model actually supports them.** If a list's
toolbar has no **Import**, that model cannot be imported — it is not a
permissions problem and not a bug to report.

1. Navigate to a data editor (e.g., **Admin** > **Data Management** > **Parts**)
2. The toolbar shows **Import** and **Export** where they apply
3. Any active search/filter is applied to exports

### What can be imported and exported

| Area | Models |
|------|--------|
| **Production** | Parts, Orders, Work Orders, Part Types |
| **Materials & tooling** | Material, Fixture |
| **Calendars** | Plant calendar exceptions (holidays/closures), labour calendar blocks (a person's leave), overtime windows |
| **Capacity** | Work centres, Shifts |
| **Training** | Job roles, Training types, Training requirements, **Training records** (added, never rewritten) |
| **Calibration** | Calibration records (**create only** — no update) |
| **Equipment** | Equipment, Equipment types, Companies |
| **Quality reference** | Error types (the defect catalogue), Measurement definitions, Part-type life limits, External contacts, Repair codes |
| **Scheduling setup** | Step timings, Step equipment affinities, Work-centre changeovers |
| **Structure** | Bills of material — see [Bills of material](#bills-of-material) |
| **Inventory** | Storage locations |

### Where to find the buttons

**Start at [Data Management](data-management.md) (`/Edit`).** It lists every
shared-config table with its **Import** and **Export** links, so it is the
shortest route to any of them and shows only the tables you can see.

The table below says where each one's buttons live on its own page. A few are in
a **section header** rather than a page toolbar — those export only the scope you
are in:

| Model | Where |
|-------|-------|
| **Job roles** | `/quality/training/roles` |
| **Training types** | `/quality/training/types` |
| **Calibration records** | `/quality/calibrations/records` |
| **Training requirements** | The **Required competencies** section, on a job role, an equipment type, a process, or the process-flow step panel. Exports just that role/step/process/equipment type; import rows name their own scope. Hidden when the section is read-only. |
| **Measurement definitions** | `/quality/measurement-definitions` for the whole list, or the per-step **Measurements** header (process-flow step panel, receiving plan step, step or process edit form) to export just that step. Editing and versioning stay in the step editor. |
| **Plant closures** | `/production/calendar`, *Plant closures* card |
| **Recurring labour blocks** | `/production/calendar`, *Recurring blocks* card |
| **Overtime windows** | `/production/calendar`, *Overtime / extra shifts* card |
| **Work centres** | `/admin/work-centers`, page header |
| **Shifts** | `/editor/shifts` |
| **Life limit definitions** | `/editor/life-limit-definitions` |
| **External contacts** | `/settings/notifications/external-contacts` |
| **Bills of material** | The **Bill of Materials** card on a part type |

!!! note "One-off absences have no buttons of their own"
    They share a file with recurring blocks, but only the *Recurring blocks*
    card carries the toolbar — import both through that one.

    Which **life limits apply to a part type** is set on the part type's own
    form; `/editor/life-limit-definitions` is the catalogue of limits available
    to pick from.

On the calendar cards, **Import** appears only for users who can plan; on work
centres it needs `add_workcenter`.

## Exporting Data

### Export Formats

| Format | Best For | Features |
|--------|----------|----------|
| **Excel (.xlsx)** | Data review & editing | Reference sheets, dropdowns, formulas |
| **CSV** | Simple data transfer | Universal compatibility, smaller files |

### How to Export

1. Navigate to the data editor
2. Apply any filters or search (optional)
3. Click the **Export** dropdown
4. Select **Export as Excel** or **Export as CSV**
5. File downloads automatically

### Excel Export Features

Excel exports include advanced features for easier data management:

#### Multiple Worksheets

| Sheet | Purpose |
|-------|---------|
| **Instructions** | Field documentation, types, and requirements |
| **Data** | Your exported records |
| **[Reference Sheets]** | Lookup tables for foreign key relationships |

#### Reference Sheets

For fields that link to other records (e.g., Part Type, Order), the export includes reference sheets with valid values:

```
Sheet: PartTypes
| ID                                   | Name                  |
|--------------------------------------|-----------------------|
| 019cc953-b91b-7f31-8ed3-d04d30485eb1 | Common Rail Injector  |
| 019cc953-bded-7750-8cbd-775594e5918e | Injector Body         |
```

#### Dropdown Validation

Columns with constrained values have dropdown lists:

- **Foreign Key fields**: Select from reference sheet values
- **Status fields**: Select from valid statuses (e.g., PENDING, IN_PROGRESS, COMPLETE)
- **Boolean fields**: Select True or False

#### Auto-Calculated ID Fields

When you select a name from a dropdown, the corresponding ID column automatically updates using an Excel formula. These columns are marked with `(auto)` in the header and highlighted in light green.

Example:
- Select "Common Rail Injector" from the **Part Type Name** dropdown
- The **Part Type (auto)** column automatically fills with the UUID

#### Required Fields

Required fields are marked with an asterisk (`*`) in the column header. Empty required fields are highlighted in yellow.

### Filtered Exports

Exports respect your current filters:

1. Use the search box to filter records
2. Apply dropdown filters (status, type, etc.)
3. Export - only matching records are included

This allows you to export subsets like:
- All parts with status "IN_PROGRESS"
- All orders for a specific customer
- Records created in a date range

## Importing Data

### Import Modes

| Mode | Creates New | Updates Existing | Deletes Missing |
|------|-------------|-----------------|-----------------|
| **Create** | Yes | No (error if exists) | No |
| **Update** | No (error if not found) | Yes | No |
| **Upsert** (default) | Yes | Yes | No |

!!! warning "Import Does Not Delete"
    Records that exist in the database but are NOT in your import file are left untouched. Import only creates and/or updates - it never deletes records.

### How to Import

1. Navigate to the data editor
2. Click the **Import** button
3. Download a template (optional but recommended)
4. Drag & drop your file or click to browse
5. Review the column mapping preview
6. Adjust mappings if needed
7. Select import mode
8. Click **Import**

### Import Process

#### Step 1: File Upload

Supported formats:
- CSV (.csv)
- Excel (.xlsx, .xls)

Maximum file size: **10 MB**, and **10,000 rows** per import. Exports cap at
**50,000 rows**. Split a bigger job into several files.

#### Step 2: Column Mapping

The system automatically maps columns based on:
- Exact name matches (high confidence)
- Similar names (medium confidence)
- Custom mappings you configure

For each column, you can:
- Accept the suggested mapping
- Select a different target field
- Skip the column (won't be imported)

#### Step 3: Preview & Import

Review:
- Total rows to process
- Mapped columns
- Sample data

Then click **Import** to process.

### Import Results

After import, you'll see:

| Metric | Description |
|--------|-------------|
| **Total** | Rows processed |
| **Created** | New records created |
| **Updated** | Existing records updated |
| **No change** | Rows that matched what was already there |
| **Errors** | Rows that failed |

!!! tip "No change is how you tell a clean round trip"
    Re-import an export you didn't edit and every row should report **No change**,
    not Updated. If rows come back as Updated, something is being rewritten —
    usually a date or time being reinterpreted on the way in.

Error details show:
- Row number
- Error message
- Which field caused the issue

### Large Imports

For files with 100+ rows:
- Import runs in the background
- You'll receive a task ID
- Check progress via the status indicator
- You can close the dialog and continue working

## Templates

### Downloading Templates

Templates are in the **Import** dialog, not the Export menu: *Download template:
**Excel (.xlsx)** | **CSV***.

A template carries all importable columns, reference sheets and dropdown
validation (Excel only). Columns that genuinely need an answer are marked `*` —
yes/no columns and ones with a default are not, since leaving them blank is a
valid choice rather than an omission.

!!! note "Templates have no example rows"
    They used to, and the examples imported as real data if you left them in.
    Now the guidance lives where it can't be mistaken for content: as **comments
    on the header cells** and on the **Instructions** sheet.

    So an empty-looking template is the correct one. Hover a header for the hint.

### Best Practices for Templates

1. **Start with a template** - Ensures correct column names and format
2. **Keep the header row** - Column names must match exactly
3. **Use dropdowns** - Prevents invalid values
4. **Fill required fields** - Marked with asterisk

## Loading a whole plant: the Master workbook

**Admin** > **Master workbook** (`/admin/master-workbook`), also linked from a
**Master workbook** panel on [Data Management](data-management.md).

*"Load a plant from one spreadsheet: a sheet per table, in load order. Every
upload is checked first, and nothing is kept until every row loads."*

Where per-table import loads one thing, this loads a **plant**: **34 sheets in
load order**, running Users → Companies → External Contacts → Storage Locations
→ Part Types → Materials → BOMs → equipment and tooling → work centres, shifts
and plant closures → changeovers, step timings, machine eligibility →
measurements and sampling → error types, repair codes, life limits → order
milestones → training (job roles, types, requirements, records) → calibration
records → Orders → Work Orders → Parts → Cores → **Stock on Hand** → **On
Order**.

!!! tip "The Cores sheet loads reman cores already in the building"
    They arrive at **Received**. A row needs a **core type** and a **condition
    grade**. The customer has to exist as a **customer** — or as a **supplier**,
    for a PURCHASED core — and **fulfilment** follows that customer's standing
    arrangement when you leave it blank.

    See [Receiving Cores](../../workflows/reman/receiving.md) for what those
    fields mean.

### Two ways to start

| Button | Gives you |
|--------|-----------|
| **Blank** | An empty workbook to fill in |
| **Filled in** | *"Filled in with what's in UQMES now — edit it and upload it back"* |

**Filled in** is the one to reach for on a system that already has data: it makes
the workbook a round-trip editing tool rather than only a migration one. It
contains each sheet **you may view**, and uploading it back unchanged adds
nothing.

!!! note "A filled-in download is recorded"
    It is an export of your operating data, so it goes in the access log like any
    other.

### Check it, then load it

1. Download **Blank** or **Filled in**
2. Fill it in or edit it
3. **Upload**, then **Check it** — a **dry run that keeps nothing**, reporting per
   sheet: new / updated / no change / errors, with **spreadsheet row numbers**
4. **Load it** — enabled only after a check with **no errors**

!!! important "Loading is all or nothing"
    A clean check is the gate, and the load then applies every sheet or none. You
    cannot half-load a plant and be left guessing which half.

    Re-uploading **updates** rather than duplicating, and **nothing is ever
    deleted** — so the workbook is safe to iterate on until it is right.

!!! note "Processes and steps are not on it"
    Build those in the process editor first — the page says so. Everything that
    hangs off a step (timings, measurements, sampling) then has something to
    attach to.

    Sheets you don't need can be left empty.

The sheet list shows a **lock** on sheets you lack permission for.

!!! note "Loading users does not invite them"
    The **Users** sheet creates people without sending anything. At go-live, use
    **Invite N not yet invited** on **User Management** — it appears only when
    someone has never been invited, never signed in and has no password, which is
    exactly who the workbook loads. It lists the addresses and confirms before
    sending, and never includes suspended users.

    That separation is deliberate: loading a plant is not the same event as
    opening it to its staff, and a migration you run three times should not mail
    everyone three times.

## Writing a spreadsheet

The conventions below apply to every import, and getting them wrong is the usual
cause of a rejected row.

### Naming another record

| You are pointing at | Write |
|---------------------|-------|
| Most records (supplier, part type, machine) | Its **name**, or its **ERP id / serial number / code** |
| A person | Their **email address** |
| A process step | **`Process > Step`** — e.g. `Pump Build > Assembly` |

A bare step name works only when exactly one step in the tenant has it. "Assembly"
exists in most processes, so qualify it.

### Several values in one column

Separate them with a **semicolon and a space**: `Mill 1; Mill 2`.

### Dates and times

Write dates as **`YYYY-MM-DD`**. It is the only unambiguous form.

!!! warning "03/04/2026 is read month-first"
    A slash-separated date where both numbers are 12 or under could be read
    either way round. The import reads it **month first** — 4 March, not 3 April
    — and flags the row with a warning. Check those warnings, or avoid the
    format.

Times are in the tenant's shop-floor clock (the organisation's default
timezone), on the way in and the way out. A time you export is the time you
import.

### Moving a part to a step

A Parts import can set `step`, within the process of the part's **own work
order** — give the `work_order` too if the part hasn't got one. The step must
belong to that process.

!!! note "A reman core is refused"
    > This part is a reman core; its step follows its stage. Move it with the
    > core's teardown and rebuild actions instead.

    A core's position is derived from its stage, so setting it directly would put
    the two out of step. Re-importing a core at the step it is already on changes
    nothing and is not refused.

## Bills of material

BOMs import and export from the **Bill of Materials** card on a part type
(`/editor/part-types/$id/edit`). They work differently enough from the rest to be
worth their own rules.

### One sheet, many BOMs

Every row names its own BOM — **part_type**, **revision**, **bom_type** — so one
file can carry several. The remaining columns are the line:

`line_number`, `component_type` (a part) **or** `material` (a raw material),
`quantity`, `unit_of_measure`, `source` (MAKE/BUY), `consumed_at_step`
(`Process > Step`), `find_number`, `reference_designator`, `is_optional`,
`allow_harvested`, `notes`.

!!! warning "The file replaces the BOM, it does not merge into it"
    The rows for a given BOM are its **complete line list**. A line you leave out
    is a line you removed. Export first and edit that, rather than writing a
    partial file.

### An import never releases a BOM

| What you import onto | What happens |
|----------------------|--------------|
| A **released** BOM | A new **draft** revision is created |
| A **draft** BOM | Edited in place |
| A part with **no** BOM | A new draft |

Release stays a person's approval — there is no file you can write that puts a
BOM into production. An unchanged file changes nothing at all.

### One bad line fails its own BOM

A line that doesn't validate fails **that whole BOM**, and every row belonging to
it reports why. Other BOMs in the same file still import.

That is the right granularity: a BOM half-applied is worse than one not applied,
but there is no reason for a bad line on one part to block twenty others.

Lines are validated exactly as the edit form validates them — a raw material
cannot be `MAKE`, for instance.

!!! note "The export is the template"
    Exporting writes the same sheet (current BOMs only) and imports straight
    back. For a structure this shaped, round-tripping the export beats filling a
    blank template.

## Round trip

Export a list, edit it in Excel, import it back as **update**. Rows you didn't
touch change nothing.

Columns the system manages — created and updated timestamps, read-only fields —
are ignored, with a warning rather than an error, so an unedited export imports
cleanly.

An **update** row needs only the columns it changes, plus something that
identifies the record: its id, or its natural key (code, name, serial number).

## Versioned records

Part types, equipment, companies, the defect catalogue, measurement definitions
and others are versioned. **An import edits them exactly as the edit form does:**

- a change to **content** creates a **new version**
- a change to **status or a flag** saves in place
- on a part type, a change to **sourcing** — preferred supplier, lead time,
  safety stock — saves in place too, since it describes how you buy the thing
  rather than what it is

Shifts version on a **content** edit; turning one active or inactive saves in
place without making a version, since availability is not a change to what the
shift *is*.

So a bulk import of part types is not a shortcut around versioning — it produces
the same version history as editing each one by hand, which is the point.

### What survives a new version

Editing a machine, supplier, part type, work centre or shift **keeps everything
attached to it** — calibrations, downtime history, approvals, qualifications,
processes, BOMs, machine eligibility. A new version is the same thing, updated,
not a replacement that starts empty.

Revising a **step** inside a process revision copies that step's machine
eligibility, changeovers and fixtures onto the new step, and the step currently
in force keeps its own until the revision is approved.

!!! tip "This is why an edit is safe"
    The reason to say so plainly: people avoid editing versioned master data for
    fear of orphaning its history. You don't have to. Edit the record.
5. **Use reference sheets** - Look up valid IDs or use names

## Field Types

### Foreign Key Fields

Fields that reference other records (e.g., `part_type`, `order`):

**Option 1: Use the Name column with dropdown**
- Select from the dropdown
- ID auto-populates (Excel only)

**Option 2: Provide the UUID directly**
- Paste the exact UUID
- Must match an existing record

### Choice/Enum Fields

Fields with predefined values (e.g., `part_status`):

- Use the dropdown to see valid values
- Must match exactly (case-sensitive)
- Common values: `PENDING`, `IN_PROGRESS`, `COMPLETE`, `QUARANTINED`

### Boolean Fields

True/false fields (e.g., `requires_sampling`, `itar_controlled`):

- Use dropdown: `True` or `False`
- Also accepts: `true`, `false`, `1`, `0`, `yes`, `no`

### Date Fields

Dates should be formatted as:
- `YYYY-MM-DD` (recommended)
- `MM/DD/YYYY`
- Excel date values (numeric)

### Text Fields

- Plain text, no special formatting needed
- Watch for leading/trailing spaces
- Special characters are allowed

## Troubleshooting

### Common Import Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Required field missing" | Required column empty | Fill in the required value |
| "Invalid choice" | Value not in allowed list | Use dropdown or check valid values |
| "Related object not found" | FK reference doesn't exist | Check reference sheet for valid IDs |
| "Duplicate key" | Record already exists (create mode) | Use upsert mode or update existing |
| "Record not found" | ID doesn't exist (update mode) | Use upsert mode or check ID |

### Export Issues

| Issue | Solution |
|-------|----------|
| Export is empty | Check your filters - may be too restrictive |
| Missing columns | Not all fields are exported by default |
| Formulas show errors | Reference data may be empty |

## Permissions

| Permission | Allows |
|------------|--------|
| `view_[model]` | Export data |
| `add_[model]` | Import with create mode |
| `change_[model]` | Import with update/upsert mode |

## API Access

For programmatic import/export, see the [API Documentation](../../integrations/api.md).

### Export Endpoint
```
GET /api/{Model}/export/csv/
GET /api/{Model}/export/xlsx/
```

Query parameters:
- `fields`: Comma-separated field names
- `filename`: Custom filename
- `search`: Search filter
- Any filter parameters

### Import Endpoint
```
POST /api/{Model}/import/
```

Form data:
- `file`: CSV or Excel file
- `mode`: `create`, `update`, or `upsert`
- `column_mapping`: JSON mapping of columns

### Template Endpoint
```
GET /api/{Model}/import-template/csv/
GET /api/{Model}/import-template/xlsx/
```

## Next Steps

- [API Documentation](../../integrations/api.md) - Programmatic access
- [Audit Trail](../../analysis/audit-trail.md) - Track import/export activity
- [User Permissions](../users/permissions.md) - Configure access
