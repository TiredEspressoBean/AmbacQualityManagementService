# Data Management

**Admin** > **Data Management** (`/Edit`)

One index of every shared-configuration table in the system, in the style of the
Django admin index. If you are setting a plant up, or changing something the shop
relies on rather than something the shop is *doing*, this is where it lives.

## Why things moved here

The dividing line is **how often you touch it**:

| | Lives in |
|---|---|
| Run the business daily or weekly | The **sidebar** |
| Shared config touched monthly or yearly | **Data Management** only |

So several pages left the sidebar and are reached from here instead: **Step
Timings**, **Machine Eligibility**, **Changeovers**, **Repair Codes**, **Rebuild
Levels**, **Measurements** and **Work Centers**. **Processes** and **Receiving
Inspection Plans** stayed, because they are worked on continuously.

!!! tip "More people can reach this than before"
    The Data Management link now shows to anyone who can view **at least one** of
    its tables, and the page lists only the tables you can view. It used to be
    limited to user administrators — so a Production Manager who maintains work
    centres or step timings now gets there without one.

## What a row tells you

Each table shows a **row count** and the actions you hold permission for —
**Add**, **Import**, **Export**.

| Marker | Means |
|--------|-------|
| **rev** tag | Editing this table creates a **revision** rather than overwriting |
| Indented under a parent | The rows belong to that parent and are edited on its form |

An indented table says where its rows are edited — *on the part type*, *on the
step*, *on the machine*. It has no form of its own.

## The tables

### Products & routing

| Table | |
|-------|---|
| **Part Types** `rev` | with **BOMs & BOM lines** `rev`, **Life limits** and **Teardown** `rev`, all edited on the part type |
| **Processes** `rev` | with **Steps** `rev` (on the process), **Step Timings** (on the step), **Machine Eligibility** (on the step or machine), **Measurement Definitions** `rev` (on the step), **Substeps** (on the step) |
| **Error Types** `rev` | The defect catalogue |
| **Life Limit Definitions** `rev` | What a part can wear out by |

### Equipment & scheduling

**Equipment** `rev` (with **Changeovers**, edited on the machine), **Equipment
Types** `rev`, **Tooling**, **Work Centers** `rev`, **Shifts** `rev`.

### Quality

**Sampling Rule Sets** `rev` (with **Sampling Rules**, edited on the rule set),
**Receiving Inspection Plans** `rev`, **Document Types** `rev`, **Approval
Templates** `rev`.

### Supply & reman

**Purchased Materials**, **Companies** `rev`, **Repair Codes** `rev`, **Rebuild
Levels** `rev`, **Storage Locations**.

### People & access

**Users**, **User Groups**, **Job Roles**, **Training Types** `rev`, **External
Contacts**.

### Orders & records

**Orders**, **Work Orders**, **Parts**, **Cores**, **Order Milestones** `rev`,
**Quality Reports**.

### Documents & audit

**Documents** `rev`, **3D Models** `rev`, **Audit Log**.

## Setting up a plant: the load order

The **Load order** panel is a checklist of which tables to import first, because
later ones point at earlier ones. Each entry ticks once that table has data, with
a running count.

1. Companies
2. Part Types
3. Purchased Materials
4. Equipment Types
5. Equipment
6. Work Centers
7. Shifts
8. Processes & steps
9. Step timings
10. Machine eligibility
11. Measurement definitions
12. Sampling rules
13. Job Roles
14. Training Types

!!! tip "Follow it even if you are only loading part of a plant"
    This is a dependency order, not a style preference — later tables name
    earlier ones.

    Import out of order and you don't lose the file: each row naming something
    that doesn't exist yet (a step or machine by name, a part type) comes back as
    a **not-found error on that row**, and the rest of the file imports normally.
    Fix the order and re-import just those rows.

    So the cost of getting it wrong is rework, not damage — but the rework grows
    with the size of the file.

**Recent changes** alongside it draws from the audit log, so you can see what has
been touched lately without leaving the page.

!!! tip "For a whole plant, use the Master workbook instead"
    The **Master workbook** panel links to `/admin/master-workbook`, which carries
    33 sheets in load order in one file, with a dry-run check before anything is
    written. The load order above is the per-table route; the workbook is the
    same sequence as one document. See [Master
    workbook](import-export.md#loading-a-whole-plant-the-master-workbook).

## How the list pages work

### Show archived, and Restore

Deleting a row **archives** it rather than destroying it. The **Show archived**
switch reveals archived rows, greyed, with an **Archived** badge and a **Restore**
button.

That is why deleting is safe here, and why a "missing" record is usually archived
rather than gone.

Each config edit form also has an **Archive this …** section at the bottom: it
confirms, then returns you to the list, where **Show archived** brings it back.

!!! note "Not every table has it"
    **Processes**, **Users**, **User Groups**, **Cores** and **Documents** have no
    *Show archived*, because each has a lifecycle of its own — a process has
    versions and statuses, a core has stages, a user's **access** is removed
    rather than the user archived. Use the lifecycle that belongs to the record.

    The Users list shows **Access removed** for someone whose membership has been
    suspended. See [Deactivating
    Users](../users/deactivating.md#why-deactivate-not-delete).

!!! important "Four things really are irreversible"
    Almost every delete confirmation in uqmes now says the record is archived,
    with history kept and restorable from here — because that is what happens.

    Four are genuinely permanent, and say so: **cancelling a work order**,
    **scrapping cores**, **discarding unsaved substep edits**, and **resetting
    demo data**. Read those four prompts properly.

    A **Step** that belongs to a process has no *Archive this* section either;
    steps are removed in the process editor.

### Archiving several at once

Row checkboxes give you *"N selected · Archive selected · Clear"*.

### Filtering

On a wide screen, a **Filter** panel sits to the right of the table: *By <field>*
groups of choices, the current one in bold, with a **Clear** link. Narrower
screens keep the same filters as dropdowns in the toolbar.

### Getting back

A **Data Management** link at the top of every list page returns you to the index.

## History

Most edit forms carry a **History** card at the bottom. It lists each revision —
**rev N** — with what changed from the one before, as *field: old → new*, who made
it and when. In-place changes and deletes are listed too.

It reaches beyond the config tables: **3D Models**, **Users**, **Orders**, **Work
Orders**, **Parts**, **Quality Reports**, **Receiving Inspection Plans**, **User
Groups** and the **core detail** page have one as well. **Work Centers**,
**Shifts** and **Order Milestones** carry History on the row rather than the
form.

Records revised before the audit trail existed say so rather than showing an
empty diff.

!!! note "Author names on the audit log"
    The audit log page previously showed every author as *System*. That was a
    schema fault, now fixed — real names appear, on both the History card and the
    audit log itself.

## Pickers

Dropdown pickers on these forms are **searchable combo boxes**. The visible
difference from the old ones: the value you already chose stays on screen while
you type to search for another.

Multi-selects show their choices as **chips** — dispositions' and CAPAs' quality
reports, CAPA dispositions, and the quality form's operators and error types.

**Error types** keep their **Add new error type** action, pre-filled with whatever
you had typed as a search.

## Storage locations

**Data Management** > **Storage Locations** (`/editor/storage-locations`), under
Supply & reman.

A location is a **record**, not a piece of text — and locations **nest**: a bin
sits in a rack, a rack in an area. This page shows the same tree as
[Locations](../../workflows/supply/locations.md), plus the ability to **remove**
one.

Each location carries:

| | |
|---|---|
| **Parent** | What it sits inside |
| **Kind** | Warehouse, area, rack, shelf, bin, cage, yard, dock, work cell, line-side, other |
| **Label code** | Optional; used on its printed label |
| **Held stock only** | Only quarantined or rejected stock may go there |
| **Receiving dock** | Deliveries land here unless the receiver picks elsewhere |
| **In use** | Turn it off and the location accepts nothing new |

!!! tip "You don't have to set this up in advance"
    Anyone who can receive or move stock can create one from any picker — **Add
    location "X"** — so locations accumulate as the shop names them. A stock
    import also creates any location its sheet names.

    What this page adds is the ability to *organise* them afterwards: nest them,
    give them kinds and codes, and retire the ones you stopped using.

!!! warning "Remove only works on an empty location"
    A location holding anything cannot be removed. Turn **In use** off instead —
    it stops accepting new stock while keeping the record of what was there.

**Renaming a location renames it everywhere.** It is one record, so there is no
re-tagging to do.

You will meet location pickers on the Equipment form (**Location**), on batch lot
receiving (`/production/material-lots/receive`), in the core lots receive dialog,
and in **Receive expected lot**, which has a **Put away at** field.

!!! note "Equipment import is stricter than stock import"
    A **stock** import creates locations it names. An **equipment** import must
    name a location that **already exists**. In batch receive, a pasted location
    that doesn't match shows as a row error rather than being created silently.

## Next Steps

- [Import & Export](import-export.md) — loading these tables in bulk
- [Scheduling Setup](../../workflows/scheduling/setup.md) — the three scheduling tables in detail
