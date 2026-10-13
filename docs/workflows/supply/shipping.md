# Shipping

**Supply** > **Shipping** (`/production/shipments`)

Sending finished work and material out to customers, and keeping the record of
what went when.

## What is ready to ship

The page gathers two kinds of thing, grouped by order:

- **Units waiting at their route's Ship step** — a terminal step whose status is
  *Shipped*, so the unit has finished its work and is waiting to leave
- **Finished stock on an order**

A customer's own material appears under that customer — see [Customer
property](overview.md#customer-property).

!!! note "Cores are never here"
    A reman core goes back to its owner through Remanufacturing, not through
    Shipping. See [Remanufacturing Overview](../reman/overview.md).

## Shipping something

Tick what is going and press **Ship…**. The dialog takes:

| Field | |
|-------|---|
| **Carrier** | *"UPS Ground, customer pickup…"* |
| **Tracking number** | Can be added later |
| **ERP shipper / packing-slip number** | Your reference in the system that owns the paperwork |
| **Expected delivery** | |
| **Notes** | |

Shipping **prints the packing list**. If the customer has **CoC with every
shipment** set on their company record, the certificate prints with it — the
page shows a badge on those customers so you know before you ship.

### Shipping your own stock

**Ship stock…** sends material rather than finished units — surplus bar stock, a
kit. Scan or type the lot number; shipping **part** of it splits the remainder
off and ships only what is going.

A shipped lot takes the status **Shipped**.

## After it has gone

The shipment page keeps the paperwork **editable after shipping** — a tracking
number that arrives later goes on the existing record rather than needing a new
one.

**Void…** reverses a shipment, with a **required reason**, and puts the units and
lots back where they were.

!!! tip "Void rather than ship a correction"
    Voiding restores the record to what it was. Shipping a second time to fix a
    mistake leaves two shipments and an on-time figure that reflects neither.

## Returning a customer's own material

The board has a second half, grouped under the customer it belongs to:
**Customer property** — their material sitting in your stores, which can go back
to them. It is filtered on the lot having an **owner**, independently of any
Ship step, so it appears whether or not anything is on a route.

The ship dialog is lot-aware: *"Blank quantity ships the whole lot; less splits
that much off and the rest stays"* — so a partial return works.

!!! note "Customer property is identified and protected throughout (ISO 9001 §8.5.3)"
    Consumption draws it only for that customer's work, requirements never cover
    anyone else's demand with it, dock metrics leave it out of the rejected-PPM
    figure, and the lot label prints the owner *"so nobody draws it into someone else's job"*.

## Seeing whether you are on time

- **Shipping** shows **on-time %** over the last 90 days
- An order's **Shipping card** shows shipped against ordered per line, the
  shipments themselves, and flags lines that are late

!!! warning "If on-time reads \"—\", the orders have no dated lines"
    The figure attributes each shipment to its work order's **order line** and
    compares against that line's **due date**. An order with no line, or a line
    with no due date, cannot be scored — so the board shows *"On time, last 90
    days: —"* even beside units that plainly shipped, and the **Line · due**
    column is empty for the same reason.

    That is a data gap rather than a delivery problem. Check the order has lines
    with due dates before reading anything into the figure.

!!! note "This is OTD to the CUSTOMER"
    Supplier on-time delivery is a different measure, on the receiving side —
    see [Receiving Metrics](overview.md#receiving-metrics).

## Next Steps

- [Supply Overview](overview.md) — receiving, the other direction
- [Locations & Cycle Counts](locations.md) — where stock sits in between
