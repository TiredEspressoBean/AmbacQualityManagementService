# Shipping

Shipping's slice of [the shop day](../shop-day.md): sending finished work with its
paperwork, fixing a shipment recorded by mistake, returning a customer's own
material, and sending work out to a subcontract vendor. Every exercise is on the
training shop, and every record it names is one the training seed creates.

**About 1½ hours**, in one sitting. **Before you start:** nothing.

!!! warning "On a training instance only"
    Every exercise writes real records: a shipment you record tells the customer's
    order it has gone. See the [training program](../index.md).

## How a session runs

1. **Watch.** Your trainer works the modules on the training instance, saying what
   they look at and why.
2. **Regenerate.** Your trainer puts every exhibit back as it was (below).
3. **Do it with help.** You work the same modules on the same exhibits, with your
   trainer beside you.
4. **Try to break it.** Where a module has a refusal, something the system won't let
   you do, do it on purpose and read what it says. The refusal is part of the
   lesson, not an error.
5. **Alone.** After another regenerate, the [final task](#final-task-observed),
   with your trainer watching and not helping.

**Regenerating** (for the trainer): **Settings** > **Organization** > **Regenerate
demo data**, then type `REGENERATE` to confirm. It needs a Tenant Admin login, appears only
on the training tenant, and replaces **everyone's** work on the instance. It runs in
the background and takes a few minutes; the card stops waiting after five, so if it
hasn't finished by then, reload the page later rather than pressing it again.

## Who you are

| You log in as | When |
|---------------|------|
| **Rosa Kim**, Shipping, `rosa.ship@demo.ambac.com` | Every module |

Every password is `demo123`.

---

## 1. Your desk

**You will:** find what's ready to go.

Log in as Rosa. **Shipping dock** links **Shipments**, **Outside processing**,
**Locations** and **Material lots**; **Look up** counts what's out at vendors and
what's ready to ship.

**Supply** > **Shipping**: *What can go to customers now, and what has gone.
Invoicing stays in your ERP.* **Ready to ship** groups everything by order and
customer: units waiting at their route's **Ship step**, and a customer's own
material under **Customer property**. **On time, last 90 days** is how you're doing.

A unit appears here only once it has reached its Ship step, so everything before it,
inspection included, is done. Being in Shipping doesn't let you send something that
hasn't passed.

---

## 2. Ship part of an order

**You will:** ship four of the six units waiting on an order.

1. Under `ORD-2024-0042` (Midwest Fleet Services), tick `INJ-0042-011` to `-014`.
2. **Ship 4…**: *Each part at a Ship step completes it, so its sign-off checks must
   be done.* Enter the carrier (`UPS Freight`) and your ERP shipper or packing-slip
   number (`PS-88213`). Leave tracking blank: you don't have it yet.
3. **Ship**. The packing list downloads, and the shipment opens: `SHP-…`, *Shipped ·
   4 units to Midwest Fleet Services*, with **Packing list**, **CoC**, **Edit
   paperwork** and **Void…**.

The other two keep waiting. Ship what's ready rather than holding the order for one
line.

---

## 3. Paperwork after the truck leaves

**You will:** add the tracking number to the shipment you just made.

**Edit paperwork**: *Tracking numbers and the ERP's shipper number often come after
the truck leaves.* Enter `1Z-DEMO-0042B` and **Save**: *Paperwork saved.*

The number goes on the shipment you have; it never needs a second one.

---

## 4. A shipment recorded by mistake

**You will:** void a shipment and put its units back.

1. On the same shipment, **Void…**: *For a shipment recorded by mistake — the parts
   didn't go. They return to their Ship step (sign-off runs again) or to stock.
   Goods that went and came back are a return, not a void.*
2. Give the reason (*Recorded against the wrong pallet*) and **Void shipment**.

The shipment stays on record as *Voided*, with your reason, and the four units are
back under **Ready to ship**.

Void a mistake; don't ship a correction on top of it. Two shipments for one set of
goods leave the order and the on-time figure describing neither.

---

## 5. Customer property

**You will:** return part of a customer's own material.

`RCV-CUST-0001` is 120 Common Rail Injectors belonging to Midwest Fleet Services,
listed under **Customer property**: theirs, not yours.

1. Tick **Ship lot RCV-CUST-0001** and **Ship 1…**. *Blank quantity ships the whole
   lot; less splits that much off and the rest stays.*
2. Enter **20** and a carrier (*Customer pickup*), then **Ship**.

The shipment carries `RCV-CUST-0001-01`, 20 EA. The other 100 stay here, still
theirs.

---

## 6. Send work out, and book it back

**You will:** send parts to a subcontract vendor and receive them back.

1. **Supply** > **Outside Processing**. **Ready to ship** groups what has reached an
   outside step, by step and vendor: *Nitride Coating · Apex Plating Co*.
2. **Send out**. Enter the vendor's reference and how many, then **Send … out**. They
   move to **At vendor**.
3. When they come back, **Receive back** on the shipment: *received — return
   inspection opened*.

The return inspection is QA's, in **Incoming Inspection**. The units stay on their
route the whole time: outside processing is not a shipment to a customer.

---

## R. A customer's own unit goes back (reman shops)

!!! info "Skip this section if your shop doesn't reman"

**You will:** return a repair unit the customer declined to have repaired.

A unit sent in for repair and return is the customer's: the right serial has to go
back to the right customer, even though an exchange unit with the same part number
would fit. It can go back once it's rebuilt, or once the customer has declined the
work.

1. On **Ready to ship**, `ORD-2024-0044` (Midwest Fleet Services) lists
   `CORE-240215-0011`: *Scope declined — to be returned unrepaired*. Its nozzle was
   found cracked and the customer said no to replacing it.
2. Tick it, **Ship 1…**, give the carrier, **Ship**.

The core's record now reads *returned unrepaired*, with the shipment number as its
return reference. The shipment offers **Returned as received** in place of a CoC: it
says the unit goes back without repair at the customer's request, who declined and
how, and the findings behind the work they declined. Nothing is certified.

The usual case is a unit that's been rebuilt. `ORD-2024-0047` (Northern Trucking)
lists `CORE-240217-0013`: *Rebuilt — ready to return*. Ship it the same way. The
shipment offers the **Packing list** and a **CoC**, and the core reads *returned*. The
CoC names the customer's own serial, says the unit was *repaired*, and leaves the
authorised-by line for QA to sign.
Either way the customer gets their own property back, by the same dispatch.

---

## What isn't yours

| Not yours | Whose |
|-----------|-------|
| Pass or fail a unit, or its return inspection | QA |
| The price, the invoice | Your ERP |
| Decide that a customer's unit goes back unrepaired | Production manager, with the customer |

---

## Final task — observed

Your trainer regenerates the data, logs you in as Rosa, and says only: *"Midwest
want whatever's ready on 0042 today; tracking comes this afternoon. Oh, and send back
thirty of their own injectors."* Then they watch without helping:

- ship the units waiting on `ORD-2024-0042`, without tracking
- add the tracking number to that shipment
- return 30 of `RCV-CUST-0001`, leaving the rest

Your trainer is watching for:

- [ ] You shipped what was ready without waiting for the rest.
- [ ] Tracking went onto the existing shipment, not a second one.
- [ ] The customer's material went back as part of their lot, not your stock.

## Recording your qualification

Passing the final task is the assessment. The record is a **training record**, which
your QA manager writes. See [Training Records](../../workflows/quality/training-records.md).
