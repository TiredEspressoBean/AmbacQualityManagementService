# Material Lot Tracking

Material lots are managed from **Supply** > **Materials**
(`/production/material-lots`), a hub segmented by lifecycle status — **On
order**, **Awaiting inspection**, **On hand**, and **Held** — with **Expect**,
**Receive**, and **Inspect** actions, plus import and export.

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
| **Status** | RECEIVED, IN_USE, CONSUMED, SCRAPPED, QUARANTINE |
| **Quantity** | Amount in lot (with unit) |
| **Parent Lot** | If this lot was split from another |

### Lot Statuses

| Status | Meaning |
|--------|---------|
| **On Order** | Expected, not yet arrived |
| **Received** | Arrived, not yet inspected or released |
| **Awaiting Inspection** | Held for incoming inspection |
| **Accepted** | Passed inspection |
| **Rejected** | Failed inspection |
| **In Use** | Released and available for production |
| **Consumed** | Fully used |
| **Scrapped** | Disposed of |
| **Quarantine** | Under investigation |

### Material Usage

**Material usage** records track consumption:

- Which lot was used
- How much was consumed
- Which part/work order used it
- When and by whom

## Lot Lifecycle

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   RECEIVED   │────▶│    IN_USE    │────▶│   CONSUMED   │
│              │     │              │     │              │
│ Incoming     │     │ Available    │     │ Fully used   │
│ inspection   │     │ for use      │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
       │                    │
       │                    │ If issue found
       ▼                    ▼
┌──────────────┐     ┌──────────────┐
│   SCRAPPED   │     │  QUARANTINE  │
│              │     │              │
│ Disposed     │     │ Under        │
│              │     │ investigation│
└──────────────┘     └──────────────┘
```

### Later statuses

Beyond the lifecycle above, a lot can reach:

| Status | Means |
|--------|-------|
| **Cancelled** | An expected receipt you are no longer waiting for |
| **Returned** | Rejected and shipped back to the supplier |
| **Shipped** | Sent out to a customer — see [Shipping](../supply/overview.md) |

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

The lots land in **Awaiting inspection**. They become **On hand** once
[incoming inspection](../supply/overview.md#incoming-inspection) passes, or go
to **Held** if it doesn't.

!!! tip "Expecting material"
    **Expect** records a lot you know is coming before it arrives, so it shows
    under **On order**.

### Using Material

During production:

1. Select material lot to use
2. Record quantity consumed
3. Link to part/work order
4. Remaining quantity updates automatically

### Splitting Lots

To divide a lot:

1. Select lot to split
2. Specify quantity for new lot
3. System creates child lot with parent reference
4. Both lots maintain traceability

### Quarantining Lots

When issues are suspected:

1. Change lot status to QUARANTINE
2. Document reason
3. Investigate affected parts
4. Either release (back to IN_USE) or scrap

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
| **The lot** | On hand of total, how it was counted, received date, location, use-by, CoC |
| **Came from** | Supplier, their lot, heat, bought from, ERP PO/line, and **split from / split into** as links |
| **Reached** | The customers this lot reached |
| **Where it went** | Quantity used, at which step, on which part, **built into** the assembly chain up to the top, work order · order, customer |
| **History** | The record's own change history |

Its header carries the lot's primary action (**Inspect** or **Resolve**),
**Label**, **Documents** and **Inspection record** — plus **RTV sheet** once the
lot is rejected — and a hold panel when the lot is held.

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
