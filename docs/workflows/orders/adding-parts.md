# Adding Parts to Orders

Parts are the individual items tracked through production. This guide covers adding parts to orders.

## Adding Parts Manually

!!! warning "Not from the order page"
    The order detail page is read-only — it is the customer-facing view of an
    order and has no **Add Parts** control. Parts are added against the *work
    order* that carries the production.

### From the Work Orders Control Center

1. Go to **Production** > **WO Control Center**
2. Tick exactly one work order — the bulk bar appears at the bottom
3. Click **Add Parts** (it stays disabled until exactly one is selected)
4. Fill in the dialog:

| Field | Description |
|-------|-------------|
| **Part Type** | Shown, not chosen — it comes from the work order's process |
| **Start Step** | Which step of the process the new parts begin at |
| **Quantity** | Number of parts to create |
| **ERP ID Start** | The number the ERP IDs count up from |

5. Click to confirm, and the parts are created attached to that work order

!!! note "Not Production > Work Orders"
    That page is a read-only list with no bulk bar. The Control Center is the
    one with the actions.

!!! note "The work order needs a process"
    If the work order has no process assigned, the dialog refuses with "This
    work order has no process — assign a process first." There are no steps to
    start the parts at until one is.

## ERP ID Generation

Each part's ERP ID is built from the **work order's** ERP ID, the part type's
prefix, and a counter:

```
ERP ID = <work order ERP ID>-<part type's ID prefix><counter padded to 4 digits>
```

The counter starts at the **ERP ID Start** you entered and increments by one per
part. On work order `WO-1234`, a part type with prefix `WA` and an ERP ID
Start of 1 gives `WO-1234-WA0001`, `WO-1234-WA0002`, and so on. A
part type with no prefix configured falls back to `P`.

You do not type the prefix — set it on the part type.

!!! tip "Adding the same range twice does not duplicate"
    An ID that already exists on the work order is skipped. So if you are unsure
    whether an earlier add went through, adding the same range again is safe —
    you get the parts that were missing and nothing extra. To add *more* parts,
    start the counter past the last one.

## Lots

A part does not carry a lot number of its own. What groups parts is the **work
order** they were made on, and their trail back to material is the **material
lots** drawn into them at each step — see [Material Lot
Tracking](../tracking/lot-tracking.md).

## Part Attributes

A part carries its export-control fields — **ITAR controlled**, **ECCN**,
**export licence required**, **country of origin** — alongside its type, step,
status, work order and order.

There is no revision, material specification or customer part number field on a
part, and none on its part type either.

## Part Status

New parts start at the **Start Step** you chose, at **Pending**. See [Order
Status](order-status.md#part-status) for all eighteen statuses.

## Viewing Part Details

A part's own page carries its activity history, its traveller and what was
recorded against it. See [Part History](../tracking/part-history.md).

## Creating or Editing a Single Part

**Data Management** > **Parts** lists every part. **New Parts** opens the part
form (`/editor/parts/new`), and a row's edit action opens the same form for that
part (`/editor/parts/<id>/edit`). Adding parts through a work order, above, is
the normal route; the form is for one-off corrections.

| Field | Required | Notes |
|-------|----------|-------|
| **ERP Id** | Yes | *The part's ID in your ERP* |
| **Status** | No | The part's status — see the refusals below |
| **Order** | No | The customer order it counts toward |
| **Part Type** | Yes | |
| **Process (for filtering steps)** | No | Narrows the **Step** list only. It is not saved: *the process is determined automatically from the selected step* |
| **Step** | Yes | Where the part is |
| **Work Order** | No | |
| **Archived** | No | Takes the part out of lists, with its history kept |

Click **Submit**. A refused save shows the server's reason.

!!! important "What the form won't do"
    Some changes have their own actions, which record why, so the form refuses
    them:

    - **A part with an open disposition**: its status changes through that
      disposition — *"&lt;part&gt; has an open disposition (&lt;number&gt;); its
      status changes through that disposition."*
    - **Moving a part onto a rework step**: *"Send it to rework instead — that
      records why and opens the disposition QA reviews."*
    - **A reman core**: it is put on a work order by planning its teardown, and
      scrapped from the core so its stage records it — the form refuses both.

## Removing Parts

On the order page, the **Parts on this order** card lists each part with its
type, step and status. Tick the parts — or all of them — and press **Remove from
order (N)**:

> *Only the link to this customer order is removed. The parts stay on their work
> orders, at their current step and status, and no longer count toward this
> order.*

Removing needs `change_orders`. Each removal is recorded in the audit trail
against the part.

## Next Steps

- [Tracker Overview](../tracking/tracker-overview.md) - Track parts through production
- [Order Status](order-status.md) - Monitor overall progress
- [Order Documents](order-documents.md) - Attach related files
