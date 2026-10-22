# Receiving

Receiving's slice of [the shop day](../shop-day.md): taking in what arrives, checking
it, clearing what holds it, sending back what's wrong, and putting away stock you can
find again. Every exercise is on the training shop, and every record it names is one
the training seed creates.

**About 2½ hours**, in one sitting. **Before you start:** nothing. The
[Purchasing](purchasing.md) track is the other half of the supplier relationship.

!!! warning "On a training instance only"
    Every exercise writes real records: a lot you accept becomes stock that
    production draws from. See the [training program](../index.md).

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
| **Luis Ortega**, Receiving, `luis.recv@demo.ambac.com` | Every module |

Every password is `demo123`.

---

## 1. Your desk

**You will:** read the receiving home page.

Log in as Luis. **Receiving dock** links what you do every day: **Receive a
delivery**, **Incoming**, **Receiving inspection**, **Material lots** and **Cycle
counts**.

**Late deliveries** lists what's overdue or due soon. Each row names the supplier and
whom to chase there (*Great Lakes Diesel (Dana Fischer)*), the PO and line, and what
was said the last time somebody chased it. Chasing is [Purchasing's](purchasing.md);
the card tells you what's coming and when.

**Supply** > **Materials** is the same picture by status: **On order**, **Late**,
**Awaiting inspection**, **On hand**, **Held**, **Rejected**.

---

## 2. Receive a delivery

**You will:** book in a short delivery against what was expected.

1. **Materials** > **On order**. `RCV-EXP-0102` is 150 Common Rail Injectors on
   `PO-2026-EXP0102`, overdue.
2. **Receive** on its row. Enter the supplier's lot number (`GLD-24-8812`), a
   quantity of **120**, and a heat number (`H-55021`).
3. A short delivery asks a question: *30 fewer than the 150 on order. What does the
   packing slip say?* Choose **More coming**: the other 30 stay on order with the
   same supplier, PO and promised date. **That's all** stops planning on them;
   closing the PO line is done in the ERP.
4. **Receive lot**: *Lot LOT-2026-00001 received — waiting on incoming inspection.*

**On order** now shows the 30 still owed, still overdue.

!!! important "The system never guesses a short delivery"
    Guessing either strands a balance forever or closes a line that's still owed.
    The packing slip tells you which; you say it.

A heat number is required where the material needs one: without it the lot is held
until it's entered (module 4). Photograph the CoC and packing slip into the dialog at
the dock, while they're in your hand.

**Keyed the quantity wrong?** `RCV-MAT-0005` was booked in as 120; the packing slip
says 12. On its row's menu, **Correct receipt…**, enter what actually arrived and
why. The receipt itself changes, and what's on hand with it, so the sheet for the
ERP (module 8) carries 12. It's offered only while nothing has been taken from the
lot. **Adjust quantity…** is something else: stock that's gone missing since it
arrived, where the receipt was right.

---

## 3. Inspect it

**You will:** run an incoming inspection and accept the lot.

1. **Awaiting inspection** > `LOT-2026-00001` > **Inspect**. The sample plan says
   what to check: *Inspect 20 of 120 · Accept ≤ 0 · Reject ≥ 1*.
2. **Run Inspection (DWI)**. Record the Outer Diameter (`25.01`, in spec), set
   **Pass**, and **Sign as detected by**.
3. **Confirm & review**. The review asks for defects found in the sample of 20 and
   says what that means: *Total defective: 0 … will ACCEPT*.
4. **Accept lot**.

**Incoming Inspection** (in **Supply**) is the same queue with parts back from a
subcontract vendor mixed in; **Inspect** opens the same runtime for both.

---

## 4. Holds

**You will:** clear the hold you can, and recognise the one you can't.

`RCV-MAT-HOLD` (Bargain Bolts LLC) is *Held for 2 reasons — each clears on its own*:

| Hold | Who clears it |
|------|---------------|
| *Awaiting heat number* | You: enter it from the mill certificate. |
| *Unqualified supplier* | *A quality manager can release this hold.* |

1. **Review hold**. Enter heat number `BB-7731` and **Save**: *Heat number saved —
   the hold has cleared.*
2. The lot is still held. That's normal: it moves on when the **last** hold goes.
   There's no release button for the supplier hold, because it's a judgement, not
   missing paperwork.

`RCV-MAT-0007` reads *Whole-lot reject requested*: an inspector asked to reject the
whole delivery and the QA manager decides. Rejecting a whole lot isn't yours either.

---

## 5. Send it back

**You will:** return a rejected lot and tell planning a replacement is coming.

1. **Rejected** > `RCV-MAT-0006` > **Ship back**. *Returning to Great Lakes Diesel.
   Send the RTV sheet with the goods. Any credit is settled in your ERP.*
2. Enter the supplier's RMA (`RMA-GLD-4471`) and the carrier and tracking.
   **Print RTV sheet** to go in the box.
3. Tick **The supplier is sending replacements** and give the promised date.
4. **Mark shipped back**.

**On order** now lists 80 replacements on `PO-2026-0006` for that date. That line is
the only thing that tells the planner the shortage has an end.

---

## 6. Put it away, and count it

**You will:** move a lot into stores and run a blind count.

1. **Supply** > **Locations** > **Main Stores**. Scan or type `LOT-2026-00001` into
   *Scan a lot or unit to put it in Main Stores…* and **Put here**: *Lot
   LOT-2026-00001 → Main Stores*. Each location keeps who moved what in and out.
2. Turn on **Blind** and **Count this location**. The count sheet lists the lots
   without their quantities.
3. Count each one: everything as expected except **Seal & O-Ring Kit**, where you
   find **396**. **Submit count**.
4. **Differences**: `STOCK-CRI-SEAL` 400 expected, 396 counted, −4, *Short*. *A lead
   applies the count to UQMES.* **For the ERP** is the same difference to key into
   the ERP.

Count blind when you want an honest number: a counter who can see the figure tends to
find it.

---

## 7. Stage the bench

**You will:** put out what the next jobs need.

**Scheduling** > **Staging List** reads the solved schedule and lists, per station,
what each job consumes, from which lot and where it is.

1. If the next 8 hours show no materials, widen it to **next 24h**. A window with
   nothing to stage is usually the window, not a fault.
2. **Assembly Cell** > `WO-TRAIN-BOTTLE` · Assembly: five lines, from the
   `STOCK-CRI-*` lots in Main Stores. **Confirm** the Control Valve Assembly line: it
   reads *took 2*.
3. When you picked a different lot from the one suggested, **Took another** records
   the lot you actually took. That keeps the trace honest.

*The schedule is stale — these times may have moved* means re-solve before staging.
That isn't yours: tell the planner.

---

## 8. Hand the receipts to the ERP

**You will:** produce the sheet the ERP is keyed from, and mark it done.

The ERP holds the purchase orders, so it needs to know what arrived. **Materials** >
**Receipts for ERP**: *One row per delivery, by PO line: what was received,
accepted, rejected or is still awaiting a decision. Key it into the ERP, then mark it
posted here.*

1. **Download** the sheet and key it into the ERP.
2. **Mark N as posted**: *deliveries marked as posted to the ERP.* The next sheet
   holds only what's new.

Deliveries still *awaiting a decision* stay off the sheet until inspection decides
them.

---

## R. Cores (reman shops)

!!! info "Skip this section if your shop doesn't reman"

### R1. A core arrives with its identity

1. **Remanufacturing** > **Cores** > **Receive**. Serial `CRI-77821-MF`, type Common
   Rail Injector, **Customer Return** from **Midwest Fleet Services**, **This unit
   goes back to them**, for order `ORD-2024-0044`. Note what you see in **Condition
   Notes**. **Receive Core**.
2. The core is *Received · Returns to customer*. **Start teardown** opens its first
   step, the check-in: scan the identity band, photograph it as it arrived, set the
   arrival condition, and sign. *Cores arrive as-is from the field — record what you
   see, don't clean yet.*
3. **Complete step**: *Step submitted — awaiting QA sign-off.* It goes on to
   Disassembly when QA signs.

### R2. A pallet arrives without serials

1. **Core Lots** > **Receive in bulk**: Common Rail Injector, **40** units. *Received
   CORELOT-2026-0001: 40 × Common Rail Injector*, 40 / 40 unidentified.
2. **Identify a unit**: grade it, give the serial it carries, **Identify and next**.
   Each one gets the next core number (*CORE-2026-0002 identified from
   CORELOT-2026-0001*) and the count drops: 39, then 38.

A unit with no identity on arrival can't be somebody's own unit coming back, so it is
an exchange core by definition.

---

## What isn't yours

| Not yours | Whose |
|-----------|-------|
| Release a supplier or approval hold | QA manager |
| Reject a whole lot | QA manager |
| Apply a cycle count | A lead |
| Chase the supplier, change a lead time | Purchasing |
| Re-solve a stale schedule | Planner |

---

## Final task — observed

Your trainer regenerates the data, logs you in as Luis, and says only: *"The truck
brought `PO-2026-EXP0101`: 180 of the 200, and the slip says that's the lot. Get it
into stores, and send back what we rejected last week."* Then they watch without
helping:

- receive the 180 and record that nothing more is coming on that line
- inspect and accept it, then put it away in Main Stores
- ship back `RCV-MAT-0006` with an RMA, saying whether replacements are coming
- name who clears `RCV-MAT-HOLD`'s supplier hold

Your trainer is watching for:

- [ ] You read the packing slip before answering the short-delivery question.
- [ ] The lot went into stores only after it was accepted.
- [ ] You said who decides the holds that aren't yours.

## Recording your qualification

Passing the final task is the assessment. The record is a **training record**, which
your QA manager writes. See [Training Records](../../workflows/quality/training-records.md).
