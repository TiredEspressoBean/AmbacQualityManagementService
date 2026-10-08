# Shipping Training Guide

**Duration:** 2-3 hours
**Prerequisites:** None
**Goal:** Learn to ship finished work with the right paperwork, handle customer
property and subcontract send-out, and know whether you went out on time

!!! note "Role Name"
    This training is for the **Shipping** role in the system.

!!! info "Demo Environment Login"
    **Email:** admin@demo.ambac.com
    **Password:** `demo123`

    The demo has no account whose only group is Shipping. Alex Demo is
    **Tenant Admin**, which holds every shipping permission plus more.

!!! warning "Shipping has no Home landing yet"
    If your live account holds only Shipping, Home will be empty. Reach your work
    through the **Supply** section of the sidebar.

!!! danger "Shipping is not release authority"
    Releasing product is a quality act (ISO 9001 §8.6), and the Ship step's own
    sign-off substeps enforce it. Being in the Shipping group does **not** let
    you send something that hasn't passed.

---

## Module 1: What Is Ready to Go

### Learning Objectives

1. Find everything waiting to ship
2. Tell the four kinds of thing apart

### 1.1 The page

**Supply → Shipping** gathers, grouped by order:

- **Units that have finished their route's Ship step** — work done, waiting to leave
- **Finished stock on an order**
- **A customer's own material**, under that customer
- **Your own stock lots** — surplus bar, a kit — whole or in part

### 1.2 One thing that does not ship from here

!!! note "Cores go back through Remanufacturing"
    A reman core returning to its owner is not shipped from this page. See
    [Remanufacturing Overview](../workflows/reman/overview.md).

### Knowledge Check: Module 1

1. A customer's own material is sitting in your stores. Where does it appear?
2. A core needs to go back to its owner. Do you ship it from here?

---

## Module 2: Shipping It

### Learning Objectives

1. Create a shipment
2. Decide whether to ship partially

### 2.1 The dialog

Tick what is going, press **Ship…**, and give:

- Carrier and tracking
- Your ERP shipper or packing-slip number
- Expected delivery
- Any notes

The shipment is numbered **SHP-YYYY-######**.

### 2.2 Partial shipments

**Partial shipments are allowed** — ship what is ready rather than holding a
complete order for one line.

!!! tip "Tracking can come later"
    The field is optional at shipping and editable afterwards. A number that
    arrives in the afternoon goes onto the existing shipment rather than needing a
    second one.

### Knowledge Check: Module 2

1. Nine of ten units are done and the customer needs them. What do you do?
2. The carrier gives you the tracking number two hours after collection. Do you
   create a second shipment?

---

## Module 3: The Paperwork

### Learning Objectives

1. Know what prints automatically
2. Recognise a CoC customer before you pack

### 3.1 What prints

The **packing list** prints with every shipment.

A **CoC** prints too for any customer whose company record has **CoC with every
shipment**.

!!! tip "The page badges those customers"
    You know before you pack, not after the lorry has gone.

### 3.2 Why this matters

A CoC is the customer's evidence that what they received conforms. Shipping
without one where it is required means the goods arrive and cannot be used.

### Knowledge Check: Module 3

1. How do you know a customer needs a CoC?
2. What prints with every shipment regardless?

---

## Module 4: After It Has Gone

### Learning Objectives

1. Find and amend a past shipment
2. Void correctly rather than shipping a correction

### 4.1 Where it lives

- **Shipped** lists past shipments, with a data export
- A shipment's page (`/production/shipments/$shipmentId`) keeps its paperwork
  editable

### 4.2 Voiding

**Void…** reverses a shipment, with a reason, and puts the units and lots back.

!!! warning "Void a mistake; don't ship a correction"
    Voiding restores the record. Shipping again to patch an error leaves **two
    shipments** and a delivery-performance figure that describes neither.

### Knowledge Check: Module 4

1. You shipped the wrong serial. What is the correct fix?
2. What does voiding do to the units?

---

## Module 5: Customer Property

### Learning Objectives

1. Recognise material that isn't yours
2. Handle it correctly on the way out

Material belonging to a customer is tracked as theirs, labelled as theirs, and
appears under that customer on the shipping page. ISO 9001 §8.5.3 requires you to
identify, protect and safeguard it.

See [Customer property](../workflows/supply/overview.md#customer-property).

### Knowledge Check: Module 5

1. How do you tell a customer's own material from your stock?

---

## Module 6: Subcontract Send-Out

### Learning Objectives

1. Send work out to a vendor and book it back in

Outside processing sends work to a subcontract vendor and books it back. The unit
stays on its route — it has not left the shop in the sense that matters to the
traveller.

See [Outside Processing](../workflows/supply/outside-processing.md).

### Knowledge Check: Module 6

1. Is outside processing a shipment to a customer?

---

## Module 7: Whether You Are On Time

### Learning Objectives

1. Read the on-time figure and know what distorts it

**Shipping** shows **on-time %** over the last 90 days. Each order's **Shipping
card** shows shipped against ordered per line, the shipments themselves, and
flags late lines.

!!! warning "Shipping a correction instead of voiding one distorts this"
    Two shipments for one set of goods makes the figure describe neither. This is
    the practical reason the voiding rule matters.

### Knowledge Check: Module 7

1. Your on-time % looks wrong and you shipped a correction last week. Connected?

---

## Practical Assessment

### Task 1: Ship a partial order
Ship what is ready from a multi-line order and explain why you did not wait.

### Task 2: Identify a CoC customer
Find a customer flagged for CoC-with-every-shipment and say how you knew.

### Task 3: Add tracking after the fact
Create a shipment without tracking, then add it afterwards.

### Task 4: Void and re-ship
Void a shipment with a reason, confirm the units came back, then ship correctly.

### Task 5: Check your performance
Report on-time % for the last 90 days and identify one late line.

### Task 6: Find the boundary
A unit has not passed its Ship-step sign-off but the customer is chasing.
Explain what you can and cannot do.

---

## Training Completion

### Sign-Off Requirements

- [ ] Completed all modules
- [ ] Passed knowledge checks
- [ ] Completed practical assessment
- [ ] Supervisor verification

### Trainee Acknowledgment

By completing this training, I confirm that I:

- Will not ship product that has not passed its sign-off
- Will void a mistaken shipment rather than shipping a correction
- Will check the CoC badge before packing
- Will treat customer property as the customer's

### Recording the qualification

Create a **Training Record** under **Quality** > **Training**, as in [Operator
training](operator.md#recording-the-qualification).

---

## Quick Reference Card

### Shipping
- Tick → **Ship…** → carrier, tracking, shipper number, expected delivery
- Numbered **SHP-YYYY-######**
- Partials allowed; tracking can come later

### Paperwork
- **Packing list** — every shipment
- **CoC** — customers badged on the page

### Mistakes
- **Void…** with a reason → units and lots come back
- Never ship a second time to patch the first

### Not from here
- Reman cores going back to owners → Remanufacturing
- Releasing product that hasn't passed → nobody; the sign-off governs

---

## Next Steps

- [Shipping role guide](../roles/shipping.md)
- [Shipping workflow](../workflows/supply/shipping.md) — the full reference
- [Outside Processing](../workflows/supply/outside-processing.md)
- [Receiving Training](receiving.md) — the other direction
