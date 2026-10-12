# Purchasing Training Guide

**Duration:** 3-4 hours
**Prerequisites:** None
**Goal:** Learn to manage supplier relationships, expected deliveries and
sourcing data — and to understand where uqmes stops and your ERP begins

!!! note "Role Name"
    This training is for the **Purchasing** role in the system.

!!! info "Demo Environment Login"
    **Email:** admin@demo.ambac.com
    **Password:** `demo123`

    The demo has no account whose only group is Purchasing. Alex Demo is
    **Tenant Admin**, which holds every purchasing permission plus more.

!!! danger "Read this before anything else"
    **uqmes does not hold purchase orders, prices, quotes, or approvals to
    spend.** It is not a purchasing system and will not become one.

    What it holds is **what you are expecting, from whom, when** — and what is
    waiting on it. Your PO lives in your ERP. If you find yourself looking for a
    place to type a price, you are looking in the wrong system.

---

## Module 1: The Boundary

### Learning Objectives

1. State what uqmes holds and what the ERP holds
2. Explain how a decision that needs a price gets made

### 1.1 Where the line is

| uqmes holds | Your ERP holds |
|-------------|----------------|
| What you are expecting, from whom, when | The purchase order |
| Which work orders are waiting on it | The price, the terms |
| Supplier qualification and approval status | The spend approval |
| Sourcing facts: lead time, preferred supplier, safety stock | The invoice |

### 1.2 How a priced decision actually happens

Where a flow appears to need a price — a buy decision on a kit, over-and-above
work on a repair — uqmes produces the **scope**: what work, what parts, and the
finding behind each. It exports that, and records the answer that comes back.

**Pricing happens in the system that owns it.**

!!! note "This is a design decision, not a gap"
    A scope with a price field invites a rate table, then a margin, then an
    approval workflow — and then you have a second, worse ERP that disagrees with
    the first one.

### Knowledge Check: Module 1

1. A supplier quotes you two prices for the same part. Where does that
   comparison happen?
2. What does uqmes give you to take to that decision?

---

## Module 2: Expected Deliveries

### Learning Objectives

1. Load what is on order
2. Work a late delivery
3. Handle a short delivery and a cancellation

### 2.1 Loading what is on order

Expected deliveries are how uqmes knows something is coming. Until an item is
expected, nothing downstream can tell you it is late or that work is waiting on
it.

See [Loading what is on order](../workflows/supply/overview.md#loading-what-is-on-order).

### 2.2 Chasing a late delivery

The **Late deliveries** card on Home names the item, quantity, supplier and
PO/line, with a lateness badge — and, more usefully, **which work orders it is
holding up**. Each row carries the supplier's deliveries contact and their email.

!!! note "\"Holding up\" is read from the production BOM"
    It means *this work needs that item*, not *this lot was earmarked for it*.
    Read it as "who is waiting on this", not as an allocation.

!!! tip "An absent card is good news"
    The card does not render when nothing is late. Empty space here is not a
    missing feature.

### 2.3 A short delivery is a decision

A short delivery is not an assumption the system makes for you — you decide
whether the balance is still coming or the line is closed. See [A short delivery
is a decision, not an
assumption](../workflows/supply/overview.md#a-short-delivery-is-a-decision-not-an-assumption).

### 2.4 Cancelling

See [Cancelling something you are no longer
expecting](../workflows/supply/overview.md#cancelling-something-you-are-no-longer-expecting).

### Knowledge Check: Module 2

1. A delivery is 5 days late and three work orders are waiting. Where do you see
   all of that at once?
2. 80 of 100 arrive. What does uqmes need you to decide?

---

## Module 3: Sourcing Facts Are Planning Inputs

### Learning Objectives

1. Maintain lead time, preferred supplier and safety stock
2. Explain what a wrong lead time does downstream

### 3.1 These are not filing

Lead time, preferred supplier and safety stock are what the **requirements
report nets against**.

!!! danger "A wrong lead time fails quietly"
    It produces a buy recommendation at the wrong moment, every time, and nothing
    flags it. The shortage shows up later as a work order that can't start, and
    the cause looks like a planning problem rather than a data one.

### 3.2 Sourcing is not definition

!!! note "You own where a part comes from, not what it is"
    You can change a bought part's supplier, lead time and safety stock. The
    part's **definition** — what it is, its drawing, its specs — stays with
    [Engineering](../roles/engineering.md).

    Two different questions about the same record.

Editing sourcing on a part does **not** create a new version of it.

### Knowledge Check: Module 3

1. Lead time on a bought casting is set to 2 days; it really takes 6 weeks. What
   happens, and when do you find out?
2. You need to change a purchased part's drawing. Can you?

---

## Module 4: Supplier Quality

### Learning Objectives

1. Raise a supplier qualification
2. Raise a SCAR against a supplier
3. Know what you cannot approve

### 4.1 Qualification

You raise supplier qualifications and maintain the approved supplier list. There
are two routes — qualifying for bulk stock, and qualifying on a certificate.

See [Supplier Quality](../workflows/supply/overview.md#supplier-quality) and
[Approved Suppliers](../workflows/supply/overview.md#approved-suppliers).

!!! warning "You raise it; QA approves it"
    `approve_supplierqualification` is **QA Manager's**, not yours. That is
    separation of duties, and it is deliberate — the person who owns the
    commercial relationship does not also certify the supplier's quality.

### 4.2 A SCAR is a CAPA against a supplier

When a supplier sends you something wrong, raise a **SCAR** from the rejected
lot. That creates a record the supplier is answerable to, rather than a phone
call nobody can find later.

See [Rejecting](../workflows/supply/overview.md#rejecting) and [Sending it
back](../workflows/supply/overview.md#sending-it-back).

### 4.3 What you cannot settle

| Not yours | Whose |
|-----------|-------|
| Approve a supplier qualification | QA Manager |
| Reject a whole lot (VDMR) | QA |
| Approve a disposition on rejected goods | QA Manager |

**You can see all of it and start all of it.** You cannot close it.

### 4.4 The supplier scorecard

**Supply → Supplier Quality** is where a supplier's behaviour becomes a number
rather than an impression — *"Receiving-inspection scorecards: acceptance, reject
rate, CoC compliance, on-time delivery, and open SCARs."*

Each supplier card carries its **qualification standing** — *Qualified*,
*Conditional*, *Not qualified* — and, where there is history:

| Measure | What it tells you |
|---------|-------------------|
| **Lots received** / **Accepted** / **Rejected** | The volume behind everything else |
| **Reject rate** | Quality, as a rate rather than an anecdote |
| **CoC compliance** | Whether the paperwork arrives with the goods |
| **On-time delivery** | Their promise-keeping, scored against the **first** promise |
| **Open SCARs** | What they already owe you an answer on |

Walked 2026-10-12 — Great Lakes Diesel showed **Rating C**, **9 lots received**,
**1 open SCAR**, and the card itself recommended an action: **"Review: suspend"**.

!!! tip "The recommendation is the useful part"
    The scorecard does not just report; it tells you when a supplier's standing
    should change. That is the moment to act — not three months later when
    somebody notices the reject rate.

!!! note "Honest empty states"
    A supplier with no receipts says *"No material lots received from this
    supplier yet."* rather than showing zeros that look like bad performance.
    A new supplier is not a failing one.

Changing the standing itself is a qualification decision, and **approving it is
QA Manager's** — you raise it.

### 4.5 Qualifications expiring

Home gives you **Supplier qualifications expiring** — the thing that bites
quietly, because an expired qualification blocks receipt rather than announcing
itself in advance.

### Knowledge Check: Module 4

1. A lot arrives out of spec. What two things can you do, and what must you wait
   for?
2. Why can't the buyer approve the supplier's own qualification?

---

## Module 5: Purchasing or Receiving?

### Learning Objectives

1. Tell the two roles apart
2. Know when one person holds both

### 5.1 Different jobs

| | Purchasing | [Receiving](receiving.md) |
|---|-----------|---------------------------|
| **Owns** | The supplier relationship and the order | The physical delivery |
| **Does** | Places it, chases it, qualifies the supplier | Takes it in, inspects it, puts it away |

At a small plant one person holds both — the roles compose. Separating them is
what lets a larger facility staff them separately.

### Knowledge Check: Module 5

1. Who decides a bin location for incoming stock?
2. Who chases the supplier when it hasn't arrived?

---

## Practical Assessment

### Task 1: Work the late list
Open Late deliveries. Pick a row and report the supplier, the contact you would
email, and every work order it is holding up.

### Task 2: Resolve a short delivery
Receive a partial quantity and record the decision about the balance.

### Task 3: Fix a sourcing fact
Find a material with a questionable lead time. Correct it and explain what the
requirements report will now do differently.

### Task 4: Raise a supplier qualification
Raise one, then identify who must approve it and why it isn't you.

### Task 5: Raise a SCAR
From a rejected lot, raise a SCAR. Explain what it becomes.

### Task 6: Read a scorecard
Open Supplier Quality. Pick the worst-performing supplier, quote its reject rate,
CoC compliance and open SCARs, and say what the card recommends you do.

### Task 7: State the boundary
A colleague asks you to "put the PO price in so we can compare". Explain, in your
own words, why that isn't in this system.

---

## Training Completion

### Sign-Off Requirements

- [ ] Completed all modules
- [ ] Passed knowledge checks
- [ ] Completed practical assessment
- [ ] Supervisor verification

### Trainee Acknowledgment

By completing this training, I confirm that I:

- Understand that purchase orders and prices live in the ERP, not here
- Will keep lead times and safety stock honest, because planning reads them
- Will raise supplier problems formally rather than by phone alone
- Understand that I raise supplier quality issues and QA settles them

### Recording the qualification

Create a **Training Record** under **Quality** > **Training**, as in [Operator
training](operator.md#recording-the-qualification).

---

## Quick Reference Card

### Yours
- Expected deliveries: load, chase, short-close, cancel
- Supplier qualification (raise), approved supplier list
- Sourcing: lead time, preferred supplier, safety stock
- Supplier companies and their contacts
- SCARs against suppliers
- Storage locations

### Not yours
- Purchase orders, prices, spend approval → **your ERP**
- Approve a supplier qualification → QA Manager
- Reject a whole lot → QA
- Approve a disposition → QA Manager
- A part's definition or drawing → Engineering

### The scorecard
- Reject rate · CoC compliance · on-time delivery · open SCARs
- Standing: Qualified / Conditional / Not qualified
- It **recommends** — *"Review: suspend"* means act now
- "No lots received yet" ≠ poor performance

### Quiet failures to watch
- Wrong lead time → buy recommendations at the wrong moment
- Expired supplier qualification → blocked receipt
- Item never marked expected → nothing can tell you it's late
- OTD scored against the **first** promise, so re-promising doesn't repair it

---

## Next Steps

- [Purchasing role guide](../roles/purchasing.md)
- [Supply](../workflows/supply/overview.md) — the full reference
- [Receiving](receiving.md) — the dock
- [Part Approvals](../workflows/supply/part-approvals.md)
- [Companies](../admin/setup/companies.md) — suppliers and their contacts
