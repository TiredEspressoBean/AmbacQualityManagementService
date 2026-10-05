# Shipping

**The other end of the building.** Getting finished work to the customer with the
right paperwork, and knowing afterwards whether it went on time.

!!! info "There is no Shipping group"
    As with [Receiving](receiving.md), this is a **job** rather than a group. The
    work sits with whoever your shop gives it to — commonly **Operator**, **Shift
    Lead** or **Production Manager**.

## What is ready to go

**Supply** > **Shipping** gathers, grouped by order:

- **units that have finished their route's Ship step** — the work is done and the
  unit is waiting to leave
- **finished stock on an order**
- **a customer's own material**, under that customer

You can add **your own stock lots** to a shipment too — surplus bar, a kit —
whole or in part.

!!! note "Cores go back through Remanufacturing"
    A reman core returning to its owner is not shipped from here. See
    [Remanufacturing Overview](../workflows/reman/overview.md).

## Shipping it

Tick what is going, press **Ship…**, and give the carrier, tracking, your ERP
shipper or packing-slip number, expected delivery and any notes. The shipment is
numbered **SHP-YYYY-######**.

**Partial shipments are allowed** — ship what is ready rather than holding a
complete order for one line.

### The paperwork

The **packing list** prints with every shipment. A **CoC** prints too for any
customer whose company record has **CoC with every shipment** — the page badges
those customers, so you know before you pack.

!!! tip "Tracking can come later"
    The field is optional at shipping and editable afterwards. A number that
    arrives in the afternoon goes onto the existing shipment rather than needing
    a second one.

## After it has gone

- **Shipped** lists past shipments, with a data export
- A shipment's page (`/production/shipments/$shipmentId`) keeps its paperwork
  editable
- **Void…** reverses one, with a reason, and puts the units and lots back

!!! warning "Void a mistake; don't ship a correction"
    Voiding restores the record. Shipping again to patch an error leaves two
    shipments and a delivery-performance figure that describes neither.

## Whether you are on time

**Shipping** shows **on-time %** over the last 90 days, and each order's
**Shipping card** shows shipped against ordered per line, the shipments
themselves, and flags late lines.

## Next Steps

- [Shipping workflow](../workflows/supply/shipping.md) — the full reference
- [Receiving](receiving.md) — the other direction
- [Locations & Cycle Counts](../workflows/supply/locations.md)
