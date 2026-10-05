# Receiving Cores

This guide covers how to receive and log incoming cores for remanufacturing.

## Two ways cores arrive

**Individually identified** — one unit, with its own identity from the moment it
lands. Received straight in as a core. This is the path below.

**In bulk** — a pallet of forty injector bodies, counted, no serials. Received as
a **core lot**, with each unit given an identity later. See [Bulk core
lots](#bulk-core-lots).

Either way, receive a core when a customer returns a used unit, purchasing takes
cores from a supplier or broker, a warranty return arrives, or a trade-in is
collected.

## Receiving Workflow

### Step 1: Open the receiving form

Neither receive form has a sidebar entry. Both are on the **Remanufacturing**
dashboard (`/reman`), as buttons in its header:

| Button | Goes to | For |
|--------|---------|-----|
| **Receive Core** | `/reman/cores/receive` | One unit, one form. This page. |
| **Receive Cores** | `/reman/cores/receive-batch` | Several at once, as a grid |
| **Core Lots** | `/reman/core-lots` | Counted, unidentified units — see [Bulk core lots](#bulk-core-lots) |

!!! warning "The two receive buttons differ by one letter"
    **Receive Core** is the single form; **Receive Cores** is the batch grid.
    Nothing else distinguishes them, so check which one you opened before
    typing.

The batch page is titled *Receive Cores* — *"Paste from a spreadsheet or enter
rows manually. All rows are saved together"* — and submits every row at once
with **Submit N cores**.

!!! tip "New Cores also takes you here"
    From **Remanufacturing > Cores**, the **New Cores** button goes straight to
    the single receive form rather than opening a blank create dialog.

### Step 2: Enter Core Information

**Required Fields:**

| Field | Description |
|-------|-------------|
| **Core Number** | Identifier for this core. **Optional** — leave it blank and it reads *Assigned*, and one is generated |
| **Core Type** | Type of unit (select from part types) |
| **Source Type** | How the core was obtained, e.g. Customer Return |
| **Received Date** | Date the core was received |
| **Condition Grade** | Overall condition, e.g. Grade B - Good |

**Optional Fields:**

| Field | Description |
|-------|-------------|
| **Serial Number** | Original equipment serial number |
| **Reference Number** | RMA, PO, or other reference |
| **Customer** | Customer who returned the core |
| **Credit Value ($)** | Core credit owed for the return — informational only |
| **Condition Notes** | Detailed observations |

!!! warning "Fulfilment is the consequential field"
    **Fulfilment** is required, and it decides the unit's whole downstream life.
    The options read as *"This unit goes back to them"* (repair and return) and
    *"They get a unit from stock"* (exchange).

    It determines whether the unit can **ever** be harvested, and whether the
    components recovered from it are reserved to it. It is pre-filled from the
    customer's standing arrangement and annotated with where that came from —
    if no arrangement is on record it says so and defaults to stock.

    It can be corrected on the core afterwards, but **only while the core is
    still Received**. Once teardown starts the edit is refused, because harvest,
    reservations and authorisation already follow from it. Check it now rather
    than relying on that window.


### Step 3: Assess Condition

**Condition Grade** is required. It is your judgement of the unit in front of
you, recorded at receipt:

| Grade | Condition |
|-------|-----------|
| **A** | Excellent — minimal wear |
| **B** | Good — normal wear |
| **C** | Fair — significant wear |
| **Scrap** | Not usable |

!!! note "The grade informs people, not the system"
    Nothing downstream branches on a core's condition grade — it does not pick a
    teardown route, gate a release or set a scope. What drives the rebuild is the
    grade each *component* is given at teardown.

    So treat it as the receiving inspector's summary for whoever handles the unit
    next, and put the substance in **Condition Notes**: visible damage, missing
    components, corrosion. Those are read during disassembly.

### Step 4: Set Core Credit (if applicable)

For customer returns with a credit agreement, enter the **Credit Value**. It can
be marked issued later, from the core's page.

!!! info "The credit is a note, not a transaction"
    uqmes does not price, invoice or pay anything. Recording a credit as issued
    stamps *when* and *by whom* on this record so the shop has its own trace —
    the money moves in whatever system owns it.

!!! warning "Issue Credit acts immediately, with no confirmation"
    Unlike **Scrap** and **Accept to Inventory**, which open a dialog, the
    **Issue Credit** button on the core's page records the credit the moment it
    is clicked. The button then disappears and Credit Status reads *Issued*.

    There is no undo in the interface.

### Step 5: Submit

Click **Receive Core**. The core is created at stage **Received**.

## Source Types

| Source | Use When |
|--------|----------|
| **Customer Return** | Customer returns core as part of reman exchange |
| **Purchased** | Core purchased from supplier or broker |
| **Warranty** | Core returned under warranty claim |
| **Trade-In** | Core accepted as trade-in on new purchase |

## Bulk core lots

**Remanufacturing** > **Core Lots** (`/reman/core-lots`)

**Receive in bulk** takes a lot in: a count of units of a core type, none of
them yet identified. The dialog is *Receive cores in bulk*; its submit is
**Receive lot**. They sit in the core bank as a quantity until the shop
chooses to identify them — at receiving inspection, when one is pulled for
teardown, or any time in between.

### Identifying a unit

On the lot's row, click **Identify a unit**. The dialog asks for **Condition**
(required), and optionally **Source**, **Serial number** and **Condition
notes** — you do not type a core number, it is generated. From that moment the
unit is an ordinary core, and its part records which lot it came out of, so the
trace back to the receipt survives.

Inside the dialog, **Identify** does one unit and closes; **Identify and next**
keeps it open for the following unit, which is the usual way to work through a
pallet at inspection.

!!! note "Identifying the last unit closes the lot"
    When the final unassigned unit is given an identity, the lot flips to
    **Consumed** on its own — so it stops counting toward the core bank. Nothing
    is lost; the units are simply cores now.

!!! warning "Condition grade is required"
    A unit cannot be identified without one. It is the first real assessment of
    that unit, and everything downstream — whether it is worth rebuilding, what
    its components are likely to grade — reads from it.

### Only exchange cores can arrive in bulk

A lot can only be received for **exchange**, and every identity assigned from one
is an exchange core. Repair-and-return means *this* unit goes back to its owner,
which needs an identity from the moment it is received.

!!! note "This is definitional, not shop policy"
    It is enforced when the lot is received rather than offered as a setting —
    a repair-and-return customer is refused. There is no configuration that
    makes an anonymous unit returnable to a particular owner.

### Why a lot has to be flagged as cores

A lot of cores is marked as holding cores when it is received, and nowhere else.

The part type cannot tell the difference: a reman shop's core type is usually the
very part number it sells, so **a bought lot of that part and a pallet of
returned cores share a type**. Without the flag, purchased stock would be counted
into the core bank.

The lot must still be *of* a core type — one that cores have been received as
before, or that has a disassembly BOM authored — so the bank knows what it
yields.

!!! tip "Don't reuse a purchased lot"
    If you are setting up demo or test data, receive a core lot through the core
    lot path rather than relabelling a purchased material lot. The flag is
    exactly what tells the two apart.

### Which lots count in the bank

Unassigned units count toward the core bank while the lot is **Received**,
**Awaiting inspection**, **Accepted** or **In use** — the states where the units
are in the building and could be identified.

They do not count when the lot is On Order (not arrived), in Quarantine or
Rejected (held, or going back), or Consumed or Scrapped (nothing left).

## After receiving

Once received, a core can be:

1. **Torn down** — see [Teardown](disassembly.md)
2. **Scrapped** — if inspection shows it is not usable
3. **Held** — awaiting a decision or more information

## Troubleshooting

### Core Number Already Exists

Core numbers must be unique. If the number is already used:

- Check if this is a duplicate receipt
- Use a different numbering scheme
- Append a suffix to distinguish

!!! tip "Or let the system number it"
    Leaving **Core Number** blank avoids the problem — the field reads *Assigned*
    and a unique number is generated at receipt. Type one only when the unit
    already carries a number you need to keep.

### Customer Not Found

If the returning customer isn't in the system:

- Add the company first via **Data Management > Companies**
- Or leave customer blank and add later

## Next Steps

- [Start Disassembly](disassembly.md) - Take apart the core
- [View Core Details](overview.md) - Review core information
