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

Print **location labels** as a thermal label or a Letter sheet. A label's QR code
opens the location; its barcode reads **LOC:&lt;code&gt;** when the location has a
label code, otherwise **LOC:&lt;name&gt;** — and older labels still scan.

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

Put something in the wrong place? **Move…** it again. There is no undo, and
nothing needs one: the history keeps both moves, which is what actually happened.

## Cycle counts

**Cycle Counts** in the sidebar, after **Materials** (`/production/cycle-counts`),
is where counting is worked. Its badge is the number of items due. **Materials** has
a **Cycle counts** button with the same *N due*.

A count is of one thing:

- **An item** — a part type or material, in every location it's kept. This is the
  default.
- **A location** — everything kept there.

**Start a count** asks which, with **An item** chosen; pick it (*Pick a part type or
material*, part types listed first) or the location, and switch on **Blind — hide the
expected quantities while counting** if you want to. A location's own page still has
**Count this location**. One item or location can have only one count open at a time.

!!! important "A location count covers exactly that location"
    Counting a rack does **not** count the bins inside it — unlike the location
    page, which includes them by default. Each location is counted on its own, so
    count the level where the stock actually sits.

    This is the one place in Locations where "inside" is excluded, which is
    exactly why it is worth knowing before you count a rack and find it nearly
    empty.

The page's tabs:

| Tab | Holds |
|-----|-------|
| **Due** | What to count next — see below |
| **Waiting for a lead** | Submitted counts, to apply or send back |
| **In progress** | Counts still being counted |
| **Missing units** | Units a count didn't find, until they're accounted for |
| **To key into Glovia** | Applied counts whose differences haven't been keyed into your ERP |
| **All counts** | Every count; one of an item reads *&lt;name&gt; item, every location* |

Each tab shows how many it holds. A lead with submitted counts waiting opens on
**Waiting for a lead**; everyone else, on **Due**.

### What's due, and how often

How often something is counted depends on the **item**, not the location. Every
material and part type has a **Cycle-count class**:

| Class | Meaning | Counted every (default) | Tolerance (default) |
|-------|---------|-------------------------|---------------------|
| **A** | Counted most often | 30 days | ±1 % |
| **B** | Counted regularly | 90 days | ±3 % |
| **C** | Counted least often | 365 days | ±5 % |

Everything starts as **C**. Set the class on the material's form, or on the part
type's form (with **Purchased** ticked) or its **Sourcing** dialog. It can also be
imported. UQMES doesn't
rank items by value for you — that takes cost, which your ERP holds — so promote
the items that matter by hand.

Changing a part type's class doesn't create a new version of it: how often its stock
is counted isn't part of what the part is.

Editing a material or part type shows, under its class, when it was last counted and
when it's next due: *Last counted &lt;date&gt; · next due &lt;date&gt; · every N days
as class C*. *never* means never counted; a due date of *now*, or *&lt;date&gt;
(overdue)*, is in amber with a **Cycle counts** link. Kept in more than one location,
it names the first one due (hover for all of them). With no stock in a location it
reads *No stock in a location, so nothing to count.* It goes by the saved class, so
save a change before reading it.

The intervals and tolerances are a Tenant Admin's, under **Settings** >
**Organization**, **Cycle counting (ABC)**: **Count every (days)** and **Tolerance
(%)** for each class, and **At least (units)**, a difference small enough to always
pass (so a bin of three isn't failed for being one out; **0** means percentage only).

The **Due** tab lists each item whose stock somewhere hasn't been counted within its
class's interval:

| Column | Shows |
|--------|-------|
| **Item** | The material or part type, and which it is |
| **Class** | A, B or C |
| **Due** | *Never counted*, *N days overdue* or *Due today*, and *every N days* under it |
| **Count** | **Count this item** starts a count of it everywhere it's kept; *or a whole location:* and a button for each of its due locations starts a count of that location |

An item's stock at a location counts as counted when a count covering it was
**applied** there — a count of the item, or of the whole location. A count started or
submitted doesn't clear it. With nothing due the tab reads *Nothing due — every item's
stock has been counted within its class's interval.*

Above the tabs, **Count accuracy, last 90 days** gives each class the share of
counted lines that were within tolerance; hover one for *N of M counted lines within
tolerance*. A class with nothing counted shows **—**. Under it, *Off because:* names
the three commonest reasons records were off, with how many of each.

**12-month trend** opens a chart of that accuracy month by month, a line per class;
a month with nothing counted is a gap. Hover a month for *Class A: N% (H of M lines)*.
Each count is judged as it was when applied, so promoting an item to a stricter class
later doesn't rewrite its past. With nothing applied in a year it reads *No counts
applied in the last 12 months.* **Hide trend** closes it.

### Counting

On the count screen (`/production/cycle-counts/$countId`):

- enter a **quantity per lot**
- answer **Here** or **Not here** for each unit
- **scan anything you find** that isn't on the list

An item count lists where each line is kept (**Kept at**), and has a **Found at
(location)** box beside the scan field: say where you found something before you scan
it, or it's refused (*Say where you found it first (the location box).*). Once added,
it reads *&lt;lot&gt; found at &lt;location&gt; — added to the count.* An item count
takes only that item; a location count, anything found there.

**Save** as you go, then **Submit count**.

!!! important "A blank line is not a zero"
    A line you leave blank stays **not counted**. It is left out of the
    differences, and applying the count doesn't touch its stock. The count says
    how many lines were not counted, before and after you submit. A shelf you
    found **empty** is an answer: enter **0**, or **Not here** for a unit.

    A skipped shelf is not missing stock, and the count should not write it off
    as missing.

!!! tip "Blind counting is the honest version"
    A blind count hides the expected quantities, including on the count sheet
    PDF. Counters who can see what they are supposed to find tend to find it.

### What happens to the differences

After submitting, the differences appear as **Short**, **Over**, **Not found**
and **Found here**.

Each difference also says whether it's within its item's **tolerance**, in the
item's own unit: *Class C · within ±8.10 EA* for a lot recorded at 162 (5 % of it),
or, in amber, *Class A · outside ±…*. A lot's tolerance is the larger of the class
percentage of its recorded quantity and the **At least (units)** setting. A unit (serial number) is within tolerance only when it was found where
the record says; one missing reads *outside*. Anything found here that the record
puts elsewhere is always outside.

!!! important "Outside tolerance: recount, or say why"
    With lines outside tolerance, the count shows *N lines are outside tolerance for
    their class*. Usually the answer is to **Send back for recount**. If you've
    checked and the difference is real, write why in the box under it — **Apply to
    UQMES** stays disabled until you do. The note is kept on the count, which then
    reads *Applied with lines outside tolerance: "…"*.

Nothing moves yet. Someone with **`apply_cyclecount`** — Tenant Admin, QA
Manager, Production Manager or Shift Lead — gives **every difference a reason** under
**Why**, then presses **Apply to UQMES**. It stays disabled until each has one (*Give
each difference a reason first*). The reasons:

- Used or moved without being booked
- Damaged or scrapped, not booked
- Kept in the wrong place
- Received wrong
- An earlier count was wrong
- Not known

The reasons stay on the count, and feed the *Off because:* line. Applying does:

| Difference | Applying does |
|------------|---------------|
| Lot quantity differs | **Corrects the lot** by the difference — a recorded adjustment, reason *Cycle count CC-… of &lt;what was counted&gt;* |
| Lot counted at zero | Adjusts it to **0**, which closes it as **Consumed** |
| Something found | Moves it to where it was found: this location, or in an item count, the **Found at** location |
| Unit missing | **Reports it only**, and lists it under **Missing units** |

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

### A count that looks wrong

Before it is applied, a submitted count can go back. The same people who can
apply it can choose **Send back for recount**, with a **required reason**. The
count reopens **with what was entered**, so the counter corrects the lines in
question rather than starting again, and the reason is kept on the count.

Once applied, a count is final. A difference found later is a new count, or an
**Adjust quantity** on the lot with its reason.

### Missing units

A unit a count didn't find goes on **Missing units**: its serial and item, where it
was expected, and the count (with its date and reason) that didn't find it. It comes
off the list on its own when it turns up — moved or placed since, or found in a later
count — or when it leaves for good (scrapped, shipped). Otherwise a lead says what
became of it, in **What became of it**, and **Resolve**s it; the note stays on the
count. Anyone else sees *Still missing*.

### Keying the differences into your ERP

**To key into Glovia** lists applied counts whose differences haven't been keyed yet,
with *N differences from M counts to key into Glovia*. **Download the sheet** gives
them all in one spreadsheet — Count, Location, Lot / serial, Item, Unit, Expected,
Counted, Difference, What, Reason, UQMES had it at, Note. Once they're in the ERP, a
lead marks them **Mark all keyed** and they leave the tab.

### Paperwork

| Output | For |
|--------|-----|
| **Count sheet (PDF)** | Counting on paper; blind counts hide expected quantities. An item count's sheet shows *Item, every location*, says where each line is, and has a box for anything found somewhere not on it |
| **Differences (PDF)** | The result, for review or filing |
| **For the ERP** (spreadsheet) | One count's differences, for keying into the system that owns stock value |

!!! note "uqmes does not adjust your ERP"
    Applying a count corrects **uqmes**. The spreadsheets exist so the same
    correction can be made where stock is valued — see [the receipts
    export](overview.md#handing-receipts-to-the-erp), which works the same way.

## Scanning

Scan the **QR code**. Every printed label and sheet carries one as its main code —
material lot labels, part labels, location labels, the traveler and the material
requisition — and it is the address of that record's page, so a phone camera opens
it too. Each also keeps a smaller **barcode** of its number, for a scanner that
can't read QR.

Every scan box — Home, Locations, staging, cycle counts, and the move and ship
dialogs — accepts the same things:

- the QR code on any printed label or sheet
- lot numbers
- serial numbers
- work orders
- location labels' barcodes (`LOC:<code>`, or `LOC:<name>` where the location has no
  label code)

Staging's **Took another** takes a scan and records the lot actually used.

!!! tip "Setting up a scanner"
    Use a **2D imaging** scanner, which reads QR codes (an older laser scanner
    reads only the barcodes), set up as a **keyboard-wedge** — it types what it
    reads — paired to the tablet as a **Bluetooth keyboard**. Configure it with:

    - an **Enter suffix**, so a scan submits the box it lands in
    - **QR** and **Code 128** enabled

    No driver or app is needed: if the scanner can type into a text box, it
    works everywhere scanning is accepted.

## Next Steps

- [Supply Overview](overview.md) — receiving and inspection
- [Shipping](shipping.md) — sending it out
- [Material Lot Tracking](../tracking/lot-tracking.md) — the lot's own record
