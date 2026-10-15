# Shipping

**The other end of the building.** Getting finished work to the customer with the
right paperwork, and knowing afterwards whether it went on time.

!!! info "Shipping is a group"
    There is a **Shipping** group you can be put in, as there is for
    [Receiving](receiving.md). It needs nothing beyond the ordinary staff
    permissions — shipping, voiding a shipment, outside processing and the export
    behind a CoC are all already there — so **Operator**, **Shift Lead** and
    **Production Manager** can do this work too.

    It exists as a named role so a person can hold it, be trained for it, and be
    found in the system as the one who ships.

!!! warning "Shipping is not release authority"
    Releasing product is a quality act (ISO 9001 §8.6), and the Ship step's own
    sign-off substeps enforce it. Being in the Shipping group does not let you
    release something that hasn't passed.

## What is ready to go

**Supply** > **Shipping** gathers, grouped by order:

- **units that have finished their route's Ship step** — the work is done and the
  unit is waiting to leave
- **finished stock on an order**
- **a customer's own material**, under that customer

You can add **your own stock lots** to a shipment too — surplus bar, a kit —
whole or in part.

!!! warning "A returned core gets no shipment, and so no paperwork"
    A reman core going back to its owner is not shipped from here — **Return**
    in Remanufacturing sends it, and that does not create a shipment record.

    The consequence is worth knowing before a customer asks: because the packing
    list and the certificate of conformance are both built from a shipment, a
    returned repair can have **neither**. The as-built record of what was
    replaced does exist on the unit, but nothing joins it to a certificate.

    If a customer needs a document describing what was done to their unit,
    produce it outside the system for now. See
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

!!! warning "The percentage describes only part of what you shipped"
    On-time is measured against each **order line's due date**. A work order
    raised directly, with no order line, has no date to measure — and it is
    **silently left out of the calculation** rather than counted late.

    So the figure is a percentage of the shipments that happen to carry order
    lines, not of everything that went out. A shop whose work orders mostly
    bypass order lines can read a confident **100%** off a handful of
    deliveries while most of its shipping is invisible to the measure.

    Before quoting the number to anyone, check how many of your shipped work
    orders actually carry an order line.

## Next Steps

- [Shipping workflow](../workflows/supply/shipping.md) — the full reference
- [Receiving](receiving.md) — the other direction
- [Locations & Cycle Counts](../workflows/supply/locations.md)
