# Material Lot Tracking

Material lots are managed from **Supply** > **Materials**
(`/production/material-lots`), a hub of tabs — **On order**, **Late**,
**Awaiting inspection**, **On hand**, **Held**, **Rejected** and **All** — with
**Add expected delivery** and **Receive** actions, a per-row **Inspect**, plus
**Import expected deliveries** and **Receipts for ERP**.

Material lot tracking provides full traceability for raw materials, components, and consumables used in production.

## Overview

Lot tracking enables:

- **Material Traceability** - Track which lots were used in which parts
- **Supplier Tracking** - Link lots to suppliers and supplier lot numbers
- **Quarantine Management** - Isolate suspect material lots
- **Usage Tracking** - Record material consumption during production

## Key Concepts

### Material Lots

A **material lot** represents a batch of material received or produced:

| Field | Description |
|-------|-------------|
| **Lot Number** | Unique identifier for this lot |
| **Material Type** | Type of material (part type) |
| **Supplier** | Company that supplied this lot |
| **Supplier Lot Number** | Vendor's lot identification |
| **Status** | Where the lot is in its life — see [Lot Statuses](#lot-statuses) |
| **Quantity** | Amount in lot (with unit) |
| **Parent Lot** | If this lot was split from another |

### Lot Statuses

There are twelve. The column that matters most is the last one — whether
planning counts the lot as **stock**, as **incoming supply**, or as neither.

| Status | Meaning | Counts as |
|--------|---------|-----------|
| **On Order** | Expected, not yet arrived | Incoming supply |
| **Received** | Arrived, not yet inspected or released | Incoming supply, if it was expected (has a promised date); otherwise neither |
| **Awaiting Inspection** | Held for incoming inspection | Incoming supply, if it was expected (has a promised date); otherwise neither |
| **Accepted** | Passed inspection | **Stock** |
| **In Use** | Released and being drawn against | **Stock** |
| **Quarantine** | Held — under investigation, or a receiving hold | Neither |
| **Rejected** | Failed inspection, awaiting return or scrap | Neither |
| **Returned to supplier** | Shipped back on a return-to-supplier disposition | Neither |
| **Consumed** | Fully used | Neither |
| **Scrapped** | Destroyed | Neither |
| **Cancelled** | An expected receipt that will never come | Neither |
| **Shipped to customer** | Went out on a shipment — their property returned, or your material sold or kitted | Neither |

!!! important "Only Accepted and In Use can be drawn against"
    Consumption and staging work from an allowlist of **Accepted** and **In
    Use**. Everything else — including **On Order** — can never be picked or
    issued, so an expected receipt cannot be consumed by accident.

!!! note "Returned is not Scrapped, and Cancelled never was stock"
    **Returned** means the goods exist, at the vendor: not destroyed, and the
    record stays live for the credit conversation. **Scrapped** means gone.
    **Cancelled** is an expected receipt the ERP withdrew — it was never
    physical stock, and it stops counting as supply.

### Material Usage

**Material usage** records track consumption:

- Which lot was used
- How much was consumed
- Which part/work order used it
- When and by whom

## Lot Lifecycle

```
ON ORDER → RECEIVED / AWAITING INSPECTION → ACCEPTED → IN USE → CONSUMED

Inspection failed → REJECTED → RETURNED or SCRAPPED
A hold at any point → QUARANTINE (Held)
```

### Returned

A lot rejected and shipped back to its supplier becomes **Returned**. It holds no
stock and counts as neither stock nor incoming supply.

!!! important "Returned is not Scrapped"
    **Scrapped** means the material is gone. **Returned** means it exists, at the
    vendor. Keeping them apart matters because a returned lot is still a live
    record — the credit conversation, the SCAR and the supplier's quality history
    all hang off it.

See [Sending it back](../supply/overview.md#sending-it-back).

### Split lots

Rejecting **part** of a delivery splits the bad pieces into their own lot,
numbered `-01`, `-02` … and carrying the heat number, source, PO and CoC from the
parent. The remainder carries on.

A lot can be split while it is **awaiting inspection** and from **accepted
stock** — so a problem found later doesn't force a decision about the whole
quantity.

A split inherits the parent's situation rather than resetting it:

| Parent | The split pieces |
|--------|------------------|
| **Accepted stock** | Come out accepted |
| **Held** | Stay held |
| **Customer property** | Stay that customer's |

!!! note "Usage of a split lot still shows on the parent"
    The parent's **Where it went** includes what its split-off lots were used
    for, marked *from <lot>*. Splitting material does not break the trail back to
    the delivery it arrived in.

!!! note "A split lot can see its delivery's paperwork"
    **Documents** on a split lot lists the original delivery's documents,
    read-only, under **From lot <number>** — and the same appears in the
    receiving inspection documents dialog.

    The certificate arrived with the delivery, not with the pieces you split out
    of it, so the pieces have to be able to point at it.

## Common Operations

### Receiving Lots

When material arrives, use the receiving form rather than creating a lot
record by hand:

1. Go to **Supply** > **Materials** and click **Receive**
2. Add a row per lot — the form takes several at once, so a delivery of
   multiple lots is one submission
3. Enter the lot number, supplier, and quantity for each
4. Submit with **Receive N Lot(s)**

Where the lots land depends on the material's process. If it has a RECEIVING
step, they go to **Awaiting inspection**, and become **On hand** once
[incoming inspection](../supply/overview.md#incoming-inspection) passes, or
**Held** if it doesn't. With no RECEIVING step they are dock-to-stocked — on
hand straight away, with no inspection to wait for.

!!! tip "Expecting material"
    **Add expected delivery** records a lot you know is coming before it arrives, so it shows
    under **On order**.

### Using Material

**An operator does not choose a lot.** Consumption happens automatically when a
unit leaves a step that the released BOM says consumes something. The quantity
comes from the BOM line, and the usage is linked to the part, work order and
step without anyone entering it.

The lot is chosen in this order:

1. **What the picker actually staged** for that step — if someone recorded a
   lot at staging (including via **Took another**), that is what gets drawn.
   The sheet named what the plan *would* take; the picker took what was really
   on the shelf, and the record has to say what happened.
2. Otherwise **the customer's own property**, if this is their work — a
   free-issue kit is meant for their job, so it goes first.
3. Otherwise **own stock, oldest-expiry first (FEFO)**, then oldest receipt.
   Lots with no expiry sort last: dated stock is the stock that can spoil.

!!! note "Lots that can't be used are skipped, not consumed"
    A shelf-life-expired lot is passed over rather than drawn. Another
    customer's property is never drawn into your job at all.

!!! tip "This is what makes the traveller's \"lots drawn\" line real"
    Because the draw is automatic and recorded against the step, a unit's
    traveller can say which lots went into it without anyone having kept notes.
    See [Part History](part-history.md).

**Remaining quantity updates automatically** as lots are drawn.

### A draw recorded against the wrong lot

When the record says a unit drew from one lot but it really came from another,
open the lot it was **recorded** against. Under what it reached, each draw from
this lot has **Wrong lot?**. Choose the **lot actually used**, which must be the
same item with enough in stock, and give a reason. **Move the draw** gives the
quantity back to this lot, draws it from the right one, and keeps both lots'
records and the reason. The unit's trace then names the right lot.

It needs the stock-correction permission held by leads (`apply_cyclecount`). This
fixes the genealogy. **Adjust quantity** only fixes a count, and leaves the unit
traced to the wrong lot.

### Splitting Lots

To divide a lot:

1. Select lot to split
2. Specify quantity for new lot
3. System creates child lot with parent reference
4. Both lots maintain traceability

### Quarantining Lots

A lot is held automatically — paperwork missing at receipt, an unqualified
supplier or unapproved part, expired shelf life, a quality-gate rule, or an
inspector's whole-lot reject request. It shows under **Held**. **Review hold**
opens it; release each hold with a reason, or reject the lot.

!!! warning "Releasing a hold is a quality decision"
    Releasing takes the `approve_disposition` permission, not edit rights on the
    lot — accepting stock that was held is a disposition. The released lot does
    not simply go back to in use: it routes on through receiving as if it had
    just arrived, so it lands in inspection, or on hand if the material has no
    RECEIVING step.

## Traceability

Lot tracking enables forward and backward traceability:

**Forward Traceability**: Given a lot, find all parts that used it
- Useful for recalls and quality investigations
- Shows impact scope of material issues

**Backward Traceability**: Given a part, find which lots were used
- Supports root cause analysis
- Shows material history for any part

### The lot page

`/production/material-lots/$lotId` — reached by clicking any lot number — answers
both directions for one lot in one place:

In the order they appear:

| Section | Answers |
|---------|---------|
| **The lot** | On hand of total, how it was counted, received date, location, use-by, CoC. A lot still on order reads *"On hand 0 <unit> · <qty> expected"* |
| **Came from** | Supplier, their lot, heat, bought from, ERP PO/line, and **split from / split into** as links |
| **Reached** | The customers this lot reached |
| **Where it went** | Quantity used, at which step, on which part, **built into** the assembly chain up to the top, work order · order, customer |
| **History** | The record's own change history |

Its header carries the lot's primary action (**Inspect**, or **Review hold**
when held; **Inspection** once decided), **Label**, **Move**, **Documents**,
**Trace (PDF)** and **Inspection record** — plus **RTV sheet** while the lot is
waiting to go back to its supplier or once returned — and a hold panel when the
lot is held.

!!! warning "Reached shows what was recorded, not what is possible"
    A lot appears against a customer only where a **step recorded drawing from
    it**. Material consumed without that record won't appear, so treat a short
    list as a question about capture coverage rather than proof of limited
    exposure.

    This is the distinction that matters in a recall: *what we can show* is not
    automatically *what happened*.

## Integration Points

### SPC Analysis

When SPC charts show out-of-control signals:

- Check if affected parts share a material lot
- Material variation is a common root cause
- Lot-level analysis helps identify supplier issues

### Quality Reports

When creating quality reports:

- Link to material lot if material-related
- Supports supplier quality tracking
- Enables lot-based containment actions

### CAPA

Material-related CAPAs can:

- Reference specific material lots
- Track supplier-related corrective actions
- Drive incoming inspection improvements

## Permissions

| Permission | Allows |
|------------|--------|
| `view_materiallot` | View material lots |
| `add_materiallot` | Create new lots |
| `change_materiallot` | Update lot information |
| `delete_materiallot` | Delete lots |

## API Access

Material lots are available via the REST API:

- `GET /api/MaterialLots/` - List lots
- `POST /api/MaterialLots/` - Create lot
- `POST /api/MaterialLots/{id}/split/` - Split a lot
- Export to Excel supported

## Related Topics

- [Quality Reports](../quality/quality-reports.md) - Linking lots to NCRs
- [Quarantine](../quality/quarantine.md) - Managing quarantined lots
- [SPC Analysis](../../analysis/spc.md) - Material-related variations
