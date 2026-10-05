# Locations & Cycle Counts

**Supply** > **Locations** (`/production/locations`)

Where everything physically is, and how you check the record still matches the
shelf.

## Locations

Locations **nest**: a bin inside a rack, a rack inside an area. The page shows
that tree, and **counts roll up** — a rack reports what its bins hold.

**Scan a location label**, or type a name or code, to open one.

### Arranging the tree

- **Drag** a location onto another to nest it inside
- **Drag** it onto the dashed strip to make it top-level
- The **pencil** edits it; **add-inside** creates a child
- **Tick rows** to print their labels

### A location's page

`/production/locations/$locationId` shows:

- the **lots and units** currently there, with a **Where** column
- **Inside:** chips for its sub-locations, and an **Include them** toggle
- the **moves in and out** over the last 7 days
- a **Machines** card — equipment is placed in locations too
- a **Put here** scan box: scan a lot or a unit and it moves here
- **Edit**

!!! note "Include them is on by default"
    A rack's page lists what is in its **bins** as well as on the rack itself,
    with the **Where** column naming the bin — so the page agrees with the tree's
    roll-up count.

    Turn the switch **off** to narrow it to what is on the rack itself.

Print **location labels** as a thermal label or a Letter sheet. A label carries
**LOC:<code>** when the location has a label code, otherwise **LOC:<name>** —
and older labels still scan.

### What a location can refuse

| Setting | Effect |
|---------|--------|
| **Held stock only** | Only quarantined or rejected stock may be **moved** there |
| **In use**, off | The location accepts nothing new |
| **Receiving dock** | Deliveries land here when the receiver doesn't pick somewhere |

!!! note "With two receiving docks, the first by name wins"
    The default is the first **active** dock in **alphabetical order** — so with
    *Dock A* and *Dock B*, deliveries land in Dock A.

    It only applies when nobody chooses. A location the receiver picks always
    wins.

!!! note "A receiving dock can't also be held-only"
    The two settings are refused together — *"A receiving dock can't also be for
    held stock only — deliveries arrive there before they're inspected."* Each
    switch greys out while the other is on, and the default-dock lookup skips a
    held-only location in any case.

    Deliveries arrive before anyone has judged them, so a dock cannot be a place
    only judged-bad stock may go.

### Moving something

**Move…** is in the Materials **⋯** menu and on the lot page. Moving **part** of
a lot splits the remainder off, so the record follows the material rather than
the paperwork.

Serialised units have a location too, not just material lots.

!!! tip "A location you need can be made on the spot"
    Any picker offers **Add location "X"** to anyone who can receive or move
    stock. You do not have to stop and go to an admin screen to put something
    away.

    Organising them — nesting, kinds, codes, retiring the unused — happens in
    [Data Management](../../admin/data/data-management.md#storage-locations).

**Renaming a location renames it everywhere.** It is one record, so nothing is
stranded and nothing needs re-tagging.

**Every move is recorded.** That is what makes the 7-day history on a location
page, and what lets a cycle count compare the record against the shelf.

## Cycle counts

Start one from a location page: **Count this location**, with an optional
**Blind** switch.

!!! important "A count covers exactly one location"
    Counting a rack does **not** count the bins inside it — unlike the location
    page, which includes them by default. Each location is counted on its own, so
    count the level where the stock actually sits.

    This is the one place in Locations where "inside" is excluded, which is
    exactly why it is worth knowing before you count a rack and find it nearly
    empty. `/production/cycle-counts` lists them, linked from Locations.

### Counting

On the count screen (`/production/cycle-counts/$countId`):

- enter a **quantity per lot**
- **tick each unit** that is present
- **scan anything you find** that isn't on the list

**Save** as you go, then **Submit**. Anything left uncounted is recorded as **not
there** — an omission is an answer, not a gap.

!!! tip "Blind counting is the honest version"
    A blind count hides the expected quantities, including on the count sheet
    PDF. Counters who can see what they are supposed to find tend to find it.

### What happens to the differences

After submitting, the differences appear as **Short**, **Over**, **Not found**
and **Found here**.

Nothing moves yet. Someone with **`apply_cyclecount`** — Tenant Admin, QA
Manager, Production Manager or Shift Lead — presses **Apply to UQMES**:

| Difference | Applying does |
|------------|---------------|
| Lot quantity differs | **Corrects the lot** by the difference — a recorded adjustment, reason *Cycle count CC-…* |
| Lot counted at zero | Adjusts it to **0**, which closes it as **Consumed** |
| Item found in this location | Moves it here |
| Unit missing | **Reports it only** |

!!! important "Lots are corrected; units are never written off"
    The two halves behave differently, and the difference matters before you
    press Apply.

    **A lot's quantity changes.** Counting one at zero adjusts it to zero and
    closes it as Consumed. That is a real change to the stock record. The
    adjustment is logged with its reason, so it stays traceable — but applying a
    count is not a dry run.

    **A serialised unit is only reported.** Losing one is a decision with
    consequences — for traceability, for a customer's order — and it belongs to a
    person, not to a stock count.


### Paperwork

| Output | For |
|--------|-----|
| **Count sheet (PDF)** | Counting on paper; blind counts hide expected quantities |
| **Differences (PDF)** | The result, for review or filing |
| **For the ERP** (spreadsheet) | Keying the adjustment into the system that owns stock value |

!!! note "uqmes does not adjust your ERP"
    Applying a count corrects **uqmes**. The spreadsheet exists so the same
    correction can be made where stock is valued — see [the receipts
    export](overview.md#handing-receipts-to-the-erp), which works the same way.

## Scanning

Every scan box — Home, Locations, staging, and the move and ship dialogs —
accepts the same things:

- lot numbers
- serial numbers
- work orders
- location labels (the barcode reads `LOC:<name>`)
- the QR code on a printed label

Staging's **I took a different lot** takes a scan and records the lot actually
used.

!!! tip "Setting up a scanner"
    Use a **keyboard-wedge** scanner — one that types what it reads — paired to
    the tablet as a **Bluetooth keyboard**. Configure it with:

    - an **Enter suffix**, so a scan submits the box it lands in
    - **Code 128** and **QR** enabled

    No driver or app is needed: if the scanner can type into a text box, it
    works everywhere scanning is accepted.

## Next Steps

- [Supply Overview](overview.md) — receiving and inspection
- [Shipping](shipping.md) — sending it out
- [Material Lot Tracking](../tracking/lot-tracking.md) — the lot's own record
