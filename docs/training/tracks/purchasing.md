# Purchasing

Purchasing's slice of [the shop day](../shop-day.md): knowing what's short and
what's late, chasing it, keeping the sourcing facts planning relies on, and raising
the supplier-quality records QA settles. Every exercise is on the training shop, and
every record it names is one the training seed creates.

**About 1½ hours**, in one sitting. **Before you start:** nothing. The
[Receiving](receiving.md) track is the other half: you own the order, they own the
delivery.

!!! danger "No purchase orders here"
    UQMES doesn't hold purchase orders, prices, quotes or spend approvals. It holds
    what you're expecting, from whom and when, and what's waiting on it. The PO lives
    in your ERP. If you find yourself looking for a place to type a price, you're in
    the wrong system.

!!! warning "On a training instance only"
    Every exercise writes real records: an expected delivery you record is incoming
    supply the planner counts on. See the [training program](../index.md).

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
demo data**, then type `REGENERATE` to confirm. It needs a staff login, appears only
on the training tenant, and replaces **everyone's** work on the instance. It runs in
the background and takes a few minutes; the card stops waiting after five, so if it
hasn't finished by then, reload the page later rather than pressing it again.

## Who you are

| You log in as | When |
|---------------|------|
| **Priya Nair**, Purchasing, `priya.buy@demo.ambac.com` | Every module |

Every password is `demo123`.

---

## 1. Your desk

**You will:** read the purchasing home page.

Log in as Priya. **Purchasing** links **Shortages**, **Expected receipts**,
**Supplier quality** and **Supplier qualifications**.

- **Late deliveries**: what's overdue or due within days. Each row names the
  supplier and whom to chase there (*Great Lakes Diesel (Dana Fischer)*), the PO and
  line, the first promise if it's been moved, and what was said last time.
- **Supplier qualifications expiring**: an expired qualification doesn't announce
  itself; it holds the next delivery at the dock. `Lakeshore Seals Inc` has already
  expired.

---

## 2. What to buy

**You will:** find a shortage and record that it's ordered.

1. **Shortages** (**Scheduling** > **Requirements**). **Source (buy)** lists what
   open work needs that stock plus what's expected won't cover: *Control Valve
   Assembly · short 8*, from Precision Castings, with its lead time, need-by and
   order-by dates. *Order now* means the order-by date has passed.
2. Place the order in the ERP. Then tick the row and **Add expected delivery**:
   *Record what you've ordered in the ERP so planning counts it as incoming. Nothing
   is purchased here.*
3. Enter the PO number and line, the quantity, and the supplier's promised date (it
   defaults to today plus the lead time). **Record 1 expected receipt**.

The line leaves the list: the shortage is now covered by something expected. Until
an order is recorded here, nothing can tell anyone it's late, and the shortage
surprises the floor instead.

---

## 3. Chase a late delivery

**You will:** record what the supplier said.

1. On **Late deliveries**, `PO-2026-EXP0102` line 1: 150 Common Rail Injectors, 3
   days late. **Chase…** offers **Email Dana Fischer**.
2. Under **What they said**, write what Dana told you. Give the **new promised
   date** if there is one. **Record chase**.

The delivery leaves the late list if its new date is more than a few days out. The
supplier's on-time score doesn't move: it's always measured against the **first**
promise, so re-promising can't improve a record.

---

## 4. Keep the sourcing facts right

**You will:** change a bought part's supplier and lead time.

**Data Management** > **Part Types** > `Control Valve Assembly` > **Sourcing**: *Who
it's bought from and how long they take, as the ERP has it, and the safety stock
planning holds back. The part itself isn't changed.* Set **Preferred supplier** and
**Lead time (days)**, and **Save**.

A wrong lead time fails quietly. It moves every order-by date on the shortages list,
and the shortage shows up later as a job that can't start. You own where a part
comes from; what the part *is* (its drawing, its specs) is Engineering's.

---

## 5. Supplier quality

**You will:** read a scorecard, raise a qualification, and raise a SCAR.

1. **Supplier Quality**: per supplier, the lots received, accepted and rejected, the
   reject rate, CoC compliance, on-time delivery and open SCARs. Great Lakes Diesel
   reads *Rating C · Review: suspend*. The recommendation is the useful part.
   Suspending a supplier is the QA manager's decision; you take the recommendation
   to them.
2. **Approved Suppliers** > **New qualification**: Lakeshore Seals Inc, part type
   Common Rail Injector, basis **AUDIT**, with a note of when the audit is booked.
   **Create**: *Qualification created (PENDING)*.
3. In that row's menu, try **Grant…**. It's refused: *You do not have permission to
   perform this action.* You raise a qualification; the QA manager grants it.
4. A rejected lot is where a SCAR starts. When a lot is rejected, its inspection
   page offers **Raise SCAR**: a corrective action the supplier must answer.
   **View SCARs** on the supplier's card lists what they owe you an answer on:
   Great Lakes has one, for `RCV-MAT-0006`. Look there before raising another, as
   nothing stops a second SCAR on the same lot.

---

## What isn't yours

| Not yours | Whose |
|-----------|-------|
| The purchase order, the price, the invoice | Your ERP |
| Grant a supplier qualification, suspend a supplier | QA manager |
| Reject a whole lot, decide a disposition | QA |
| Book in what arrives | Receiving |

---

## Final task — observed

Your trainer regenerates the data, logs you in as Priya, and says only: *"What are
we short of, and is it ordered? And Great Lakes owe us an answer on 0103."* Then
they watch without helping:

- find the shortage, and record an expected delivery for it with a PO, line and
  promised date
- chase `PO-2026-EXP0103` and record what was said
- say what the Great Lakes scorecard recommends, and who decides it

Your trainer is watching for:

- [ ] Nothing was "ordered" in UQMES: the order went to the ERP, and UQMES got the
      expected delivery.
- [ ] The chase recorded what the supplier said, not just a new date.
- [ ] You took the suspend recommendation to the QA manager instead of acting on it.

## Recording your qualification

Passing the final task is the assessment. The record is a **training record**, which
your QA manager writes. See [Training Records](../../workflows/quality/training-records.md).
