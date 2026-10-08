# Receiving Training Guide

**Duration:** 3-4 hours
**Prerequisites:** None
**Goal:** Learn to take in a delivery, inspect it, deal with holds, send back
what's wrong, and put away stock you can find again

!!! note "Role Name"
    This training is for the **Receiving** role in the system.

!!! info "Demo Environment Login"
    **Email:** admin@demo.ambac.com
    **Password:** `demo123`

    The demo has no account whose only group is Receiving. Alex Demo is
    **Tenant Admin**, which holds every receiving permission plus more.

!!! warning "Receiving has no Home landing yet"
    If your live account holds only Receiving, Home will be empty. Reach your
    work through the **Supply** section of the sidebar.

---

## Module 1: The Dock's Day

### Learning Objectives

1. Find what is coming, what arrived, what is stuck and what goes back
2. Tell Receiving apart from Purchasing

### 1.1 Five questions, five places

| Question | Where |
|----------|-------|
| What is coming? | **Materials → On order**, and **Late** |
| What just arrived? | **Receive**, or batch receive for a lorry-load |
| What is stuck? | **Materials → Held**, and incoming inspection |
| What goes back? | **Materials → Rejected** |
| Where did I put it? | [Locations](../workflows/supply/locations.md) |

### 1.2 Receiving is not Purchasing

| | [Purchasing](purchasing.md) | Receiving |
|---|-----------|-----------|
| **Owns** | The supplier relationship and the order | The physical delivery |
| **Does** | Places it, chases it, qualifies the supplier | Takes it in, inspects it, puts it away |

One person often holds both. They are still different jobs.

### 1.3 What the dock does not settle

!!! warning "You raise problems; QA closes them"
    **Rejecting a whole lot (a VDMR)** and **approving a disposition** are QA's
    call, not yours. You can reject the bad pieces and you can raise a SCAR — you
    cannot decide the lot's fate.

### Knowledge Check: Module 1

1. A lot is three days overdue. Whose job is it to ring the supplier?
2. You believe an entire pallet is scrap. What can you do, and who decides?

---

## Module 2: Knowing What to Expect

### Learning Objectives

1. Explain where expected deliveries come from
2. Record a chase without distorting supplier performance

### 2.1 Expected deliveries

Lots **on order** are created by **Import expected deliveries** from your ERP's
open PO lines, or added one at a time.

!!! note "Until it is expected, nothing can tell you it is late"
    An item nobody loaded is not late — it is invisible. That is the most common
    reason a shortage surprises everyone.

### 2.2 Late, and chasing

**Late** is anything overdue or due within three days. **Chase…** records what
the supplier said and any new promised date.

!!! important "Chasing never moves the goalposts"
    A new date changes what you are waiting for, but supplier on-time performance
    is still scored against the **first** promise. That is deliberate — otherwise
    a supplier who re-promises five times scores perfectly.

### Knowledge Check: Module 2

1. A supplier re-promises for the third time. What does that do to their on-time
   score?
2. Where do expected deliveries usually come from?

---

## Module 3: Receiving a Delivery

### Learning Objectives

1. Receive against an expected delivery
2. Handle short and over receipts correctly
3. Capture the evidence that travels with the goods

### 3.1 The receive dialog

It handles what a dock actually meets:

- **Counting in by box or pound**, with the conversion shown as you type
- **Heat number** and **Source**
- **A photo of the CoC or packing slip**, taken at the dock
- **Putaway**, defaulting to the receiving dock location

### 3.2 Short and over

!!! warning "A short delivery is a decision, never an assumption"
    You say whether more is coming or that's all. uqmes will not guess, because
    guessing either strands a balance forever or closes a line that is still
    owed.

**Over-receipts** keep the ordered figure: the lot reads *Ordered 100 · 10 over*.

### 3.3 A lorry-load

Use the **paste grid** at `/production/material-lots/receive` rather than
receiving twenty lines one at a time.

### 3.4 Lot numbers are issued here

The lot number is created at receipt. See [Lot numbers are issued
here](../workflows/supply/overview.md#lot-numbers-are-issued-here).

### Knowledge Check: Module 3

1. 80 of 100 arrive and the rest are coming next week. What do you record?
2. Where does the CoC photo go, and why take it at the dock rather than later?

---

## Module 4: Holds

### Learning Objectives

1. Review and clear a hold
2. Explain why clearing one hold may change nothing

### 4.1 Several at once

A lot can be held for **several reasons at once** — missing CoC, missing heat
number, unqualified supplier, expired shelf life. **Review hold** opens them.

!!! important "The lot moves when the LAST hold goes"
    Clearing one and seeing nothing happen is normal, not a bug. Check what else
    is still open before escalating.

### 4.2 Two kinds of hold

| Kind | How it clears |
|------|---------------|
| **Missing information** — no CoC, no heat number | Supply it; the hold clears itself |
| **A judgement** — unqualified supplier, unapproved part | A quality manager releases it with a reason |

You can fix the first kind. The second needs QA.

See [Held at receiving](../workflows/supply/overview.md#held-at-receiving).

### Knowledge Check: Module 4

1. You add the missing heat number and the lot is still held. What now?
2. The supplier isn't qualified. Can you release it?

---

## Module 5: Incoming Inspection

### Learning Objectives

1. Perform an incoming inspection against its plan
2. Reject correctly

### 5.1 Inspection plans

Receiving inspection plans decide what gets checked and how much. Some checks are
**once per lot**; others are proportionate to quantity.

See [Receiving Inspection
Plans](../workflows/supply/overview.md#receiving-inspection-plans).

### 5.2 Rejecting

Reject the bad pieces. Rejecting the **whole** lot is a VDMR and needs the
permission QA holds.

A rejection can raise a **SCAR** against the supplier — a CAPA they are
answerable to.

See [Rejecting](../workflows/supply/overview.md#rejecting).

### Knowledge Check: Module 5

1. Twelve of fifty are out of tolerance. What do you reject?
2. What turns a rejection into something the supplier must formally answer?

---

## Module 6: Sending It Back

### Learning Objectives

1. Return goods to a supplier with the right paperwork
2. Keep planning informed about replacements

### 6.1 The return

Reject, then **Ship back** with the supplier's **RMA number**. Say whether
replacements are coming — an expected delivery is created and linked, **so
planning sees it**.

Print the **RTV sheet** to travel with the goods.

!!! tip "Saying replacements are coming is not admin"
    It is the only thing that tells the planner the shortage has an end date.

See [Sending it back](../workflows/supply/overview.md#sending-it-back).

### Knowledge Check: Module 6

1. What travels physically with returned goods?
2. What happens in the system if you say replacements are coming?

---

## Module 7: Putting It Away and Proving It

### Learning Objectives

1. Label, move and locate stock
2. Run a cycle count and know who applies it

### 7.1 Labels and moves

- **Print lot labels** at receipt, singly or for a whole batch
- **Move** lots by scanning, into locations that **nest**

A move is recorded in the location's ledger with who, when and from where — so
"where did it go" always has an answer.

### 7.2 Counting

Count one location at a time, **blind if you want an honest number**.

!!! warning "Submitting a count is not applying it"
    Submitting is the counter's job. **Applying** needs `apply_cyclecount` — a
    lead. The differences export as a spreadsheet for keying into the ERP.

See [Locations & Cycle Counts](../workflows/supply/locations.md).

### Knowledge Check: Module 7

1. Why count blind?
2. You counted and the system still shows the old number. Why?

---

## Module 8: How the Dock Is Doing

### Learning Objectives

1. Read the receiving metrics
2. Spot a scheduling problem disguised as an inspection one

Lots received, what is waiting, median days to a decision, rejects and PPM, over
30 / 60 / 90 days.

!!! tip "The number worth watching"
    *Median days to a decision* against *inspection itself*. If the first is days
    and the second is hours, material is waiting for someone to **start** — which
    is a scheduling problem, not an inspection one.

### Knowledge Check: Module 8

1. Decisions take 4 days; inspections take 2 hours. What is wrong?

---

## Practical Assessment

### Task 1: Receive a short delivery
Receive fewer than ordered and record whether the balance is coming.

### Task 2: Clear a multi-reason hold
Find a held lot, list every reason, clear the ones you can, and name who clears
the rest.

### Task 3: Inspect and reject
Perform an incoming inspection and reject the bad pieces. Explain why you cannot
reject the whole lot.

### Task 4: Return to supplier
Ship back a rejected lot with an RMA, flag replacements, and print the RTV sheet.

### Task 5: Put away and find again
Receive a lot, print its label, move it to a location, then find it in that
location's ledger.

### Task 6: Count
Run a blind count on one location, submit it, and say who applies it.

---

## Training Completion

### Sign-Off Requirements

- [ ] Completed all modules
- [ ] Passed knowledge checks
- [ ] Completed practical assessment
- [ ] Supervisor verification

### Trainee Acknowledgment

By completing this training, I confirm that I:

- Will record a short-delivery decision rather than leaving it to be assumed
- Will take the CoC photo at the dock, not from memory later
- Will check every open hold before escalating
- Understand that I raise lot problems and QA settles them

### Recording the qualification

Create a **Training Record** under **Quality** > **Training**, as in [Operator
training](operator.md#recording-the-qualification).

---

## Quick Reference Card

### At the dock
- Count in by box or pound — conversion shows as you type
- Heat number, source, CoC photo
- Short → say whether more is coming
- Over → ordered figure is kept

### Holds
- Several at once is normal
- Lot moves when the **last** one goes
- Missing info → you fix it. Judgement → QA releases it

### Returns
- Reject → Ship back with RMA → RTV sheet travels
- Flag replacements so planning sees the end date

### Not yours
- Reject a whole lot (VDMR) → QA
- Approve a disposition → QA Manager
- Apply a cycle count → a lead
- Chase the supplier commercially → Purchasing

---

## Next Steps

- [Receiving role guide](../roles/receiving.md)
- [Supply Overview](../workflows/supply/overview.md) — the full reference
- [Locations & Cycle Counts](../workflows/supply/locations.md)
- [Shipping Training](shipping.md) — the other direction
- [Purchasing Training](purchasing.md) — who owns the order
