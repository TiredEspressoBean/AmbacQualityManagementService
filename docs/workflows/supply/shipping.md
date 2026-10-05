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

## Seeing whether you are on time

- **Shipping** shows **on-time %** over the last 90 days
- An order's **Shipping card** shows shipped against ordered per line, the
  shipments themselves, and flags lines that are late

## Next Steps

- [Supply Overview](overview.md) — receiving, the other direction
- [Locations & Cycle Counts](locations.md) — where stock sits in between
