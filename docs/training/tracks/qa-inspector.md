# QA Inspector

The inspector's slice of [the shop day](../shop-day.md): buying off a first piece,
inspecting the parts the plan selects, catching a nonconformance and seeing it
through to a decision, and reading a record back. Every exercise is on the training
shop, and every record it names is one the training seed creates.

**About 4 hours**, in one sitting or two. **Before you start:** know how an
operator works a step, because you will review what they record. See [Running
Work Instructions](../../workflows/dwi/running.md).

!!! warning "On a training instance only"
    Every exercise writes real records: a FAIL quarantines a part and opens a
    disposition, a sign-off releases a run, and signatures can't be undone. See the
    [training program](../index.md).

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

!!! warning "One trainee per instance at a time"
    Each exercise has one exhibit, and working it uses it up: a bought-off first
    piece can't be bought off again. Two trainees on one instance would spend each
    other's exhibits. Run trainees one at a time, or give each their own instance.

**Regenerating** (for the trainer): **Settings** > **Organization** > **Regenerate
demo data**, then type `REGENERATE` to confirm. It needs a staff login, appears only
on the training tenant, and replaces **everyone's** work on the instance. It runs in
the background and takes a few minutes; the card stops waiting after five, so if it
hasn't finished by then, reload the page later rather than pressing it again.

## Who you are

| You log in as | When |
|---------------|------|
| **Sarah Chen**, QA Inspector, `sarah.qa@demo.ambac.com` | Every module |
| **Casey Cross**, Shift Lead and inspector, `casey.dual@demo.ambac.com` | When a second inspector is needed |
| **Maria Santos**, QA Manager, `maria.qa@demo.ambac.com` | Co-signs a disposition at your screen |

Every password is `demo123`. You don't hold the authority to decide a disposition
on your own; Maria does. That is the point of module 5. Module 7 has you run one
operator step as Casey.

---

## 1. Start of shift — 07:30

**You will:** read the inspector's home page and know what each part of it asks of
you.

Log in as Sarah. The home page is the inspector's queue:

- **First piece waiting**: runs held until someone buys off their first piece. These
  block the floor, so they come first.
- **Inbox chips**: Receiving, OSP returns, In-process (sampled parts), QA sign-off.
- **My quality actions**: approvals, CAPA tasks and dispositions assigned to you.
- **Unassigned dispositions**: dispositions a failed inspection opened that nobody
  has taken yet, each with **Take it**.
- **Your gauges**: gauges you used in the last 7 days that are due for calibration.

**Exercise 1.1.** From the home page alone, say which runs are waiting on a first
piece, and what failed behind each unassigned disposition. Don't open anything yet.

**Exercise 1.2.** Type `INJ-QA-INSPECT-004` into the scan box, as you would scan its
traveler. A serial opens the work order it belongs to with **Start work on parts**
already open and that part ticked. Close it without starting: you'll inspect 004 in
module 3.

---

## 2. Buy off a first piece — 08:30

**You will:** buy off a first piece, fail one, waive one, and know why you can't
sign your own.

A first piece holds its run: no other part moves past the step until a second person
has judged it. The buy-off dialog shows the first piece's readings, who took them
and when. **The readings are what you are signing.**

**Watch, then do it:** `WO-QA-INSPECT-01`, first piece `INJ-QA-INSPECT-001` at Nozzle
Inspection.

1. Open the work order's **WO Control** (**Production** > **WO Control Center**,
   then `WO-QA-INSPECT-01`) and, on *First piece waiting on QA*, **I'm on it** (the floor sees it
   has been picked up; it decides nothing), then **Sign off**. The same buttons sit
   on your home page's *First piece waiting* rows.
2. Read the readings: *Bore Diameter 4 mm, limits 3.995–4.005*, taken by Mike on the CMM.
3. **Sign off** with a note of what you checked. The card clears and the run moves.

**Fail one:** `WO-QA-INSPECT-04`, first piece `INJ-QA-INSPECT-031`.

1. **Fail**, with a reason a shift lead can act on: what was wrong, what to correct.
2. The first piece is quarantined and a disposition opens in the unassigned queue,
   described as *Failed quality report:* followed by your reason.
3. WO Control shows **First piece failed — run held**, with your reason and **Start
   a new first piece**. The run stays held until a new first piece is bought off.

**Waive one:** `WO-QA-INSPECT-05`, first piece `INJ-QA-INSPECT-041`.

A waive releases the run with no buy-off, so the reason stays on the record. Waive
it as an identical setup re-run of yesterday's `WO-QA-INSPECT-02`, whose first piece
was bought off, and say so in the reason.

**Try to break it:** `WO-QA-INSPECT-03`, first piece `INJ-QA-INSPECT-021`. Sarah ran
this first piece's inspection. Open **Sign off**: before you can confirm, the dialog
says you signed this first piece's inspection, so another qualified inspector must
sign, and switches to their sign-in. Casey signs it off at your screen with their
own email, signature and password; the buy-off is recorded under Casey's name.

> **Why it refuses:** a buy-off is a second person's judgement. Whoever signed the
> first piece's inspection can't also release the run.

---

## 3. A sampled part — 09:00

**You will:** inspect a part the sampling plan selected, and answer "why this
part?".

`INJ-QA-INSPECT-004` waits at Body Inspection behind the first piece you bought
off. In Start Work it carries a **Sample** badge. Its history lists its **Sampling
decisions**: *Selected by every 4th part*.

**Exercise 3.1.** Before inspecting, find the sampling decision and say which rule
picked the part. Then inspect it through the work instruction, recording every
reading.

**Try to break it:** in **Equipment used during this inspection**, look for
`Micrometer MIC-2`. It is greyed: *out of service*, because it failed its
calibration this morning. A gauge that failed calibration can't be named on an
inspection; pick an in-service one.

---

## 4. What arrives — 09:30

**You will:** accept a purchased lot, reject a bad one, clear a paperwork hold, and
accept parts back from the plating subcontractor.

They all sit in one queue. **Incoming queue** on your home page opens **Incoming
Inspection**, whose **Source** column says whether each is a purchased lot or an
outside-process return.

**Receiving inspection:** `RCV-MAT-0002`. The plan tells you how many to inspect and
the accept and reject numbers. Record each sample, read the verdict the plan
reaches, and **Accept**.

**Reject part of a lot:** `RCV-MAT-0004`, 40 pieces, inspect 13, accept on 0
defective.

1. **Run Inspection**. Record an outer diameter of **25.08 mm** (limits 24.95–25.05),
   set the result to **Fail**, and sign.
2. On the review, the plan already counts the failing reading: *at least 1 from your
   readings*. You found 2 bad in the sample: set Outer Diameter's count to **2**. The
   verdict reads *will REJECT*, and **Accept lot** is disabled.
3. **Reject lot**, **Return to supplier**, **Some of them — these are bad, accept the
   rest**, 2 pieces. The 2 bad pieces split into their own lot, rejected with a
   disposition; the other 38 are accepted.

**Try to break it:** `RCV-MAT-0003`, 500 pieces. Record a failing outer diameter of
**24.91 mm** and choose **Reject whole lot**. Rejecting a whole lot back to the
supplier isn't yours to decide, so the button reads **Request whole-lot reject**:
the lot is held, and a QA manager decides. Log in as Maria and open the lot: she can
**Confirm: reject whole lot**, or **Decline request…** with a reason, which sends
the lot back to inspection. Once it is rejected, the lot offers **Raise SCAR**.

**A held lot:** `RCV-MAT-HOLD` is held for two reasons, and *each clears on its
own*. Enter the missing heat number: that hold clears. The other is an unqualified
supplier, which needs a quality manager's judgement, so it stays.

**An outside-process return:** shipment `OSP-2026-000002` is back from Apex Plating
Co (parts `OSP-DEMO-005` and `-006`). Inspect the return and **Accept return**: the
parts rejoin the line at their next step.

---

## 5. A failure, and its disposition — 10:00 to 11:00

**You will:** see a failure open a disposition, take it, mark the defect on the 3D
model, and decide it with the authority's co-sign.

**A reading out of spec.** `INJ-QA-INSPECT-012` waits at Flow Calibration. Run it and
record a flow rate of **95 mL/min** (limits 100–140). Nobody decides that this is a
failure; the spec does. The part is quarantined and a disposition opens, unassigned.

**Try to break it:** try to start `INJ-QA-INSPECT-012` again. Start Work lists it as
*quarantined — waiting on its disposition* and won't tick it: a quarantined part
waits for its disposition, and rework reaches it through the disposition, not a
fresh start.

**Take and annotate.** `INJ-QA-INSPECT-015` failed its visual inspection yesterday:
*Burr in bore*, a defect that must be marked on the part's model.

1. On your home page, **Take it** on its disposition. It moves to **My
   dispositions**.
2. Open it. **3D Annotations Required**: the disposition can't close until the
   defect is marked. **Go to Annotator** opens with its report already selected.
3. Mark the burr on the model, where the fuel passage breaks into the bore, with its
   defect type and severity, and save.
   A marker's severity rates that one finding. The disposition's severity
   (Minor, Major, Critical) rates the nonconformance the findings add up to, so
   the two needn't match.

**Try to break it:** before annotating, set it to **Closed** and save. It is
refused, naming everything still missing in one message: no decision yet, the 3D
annotation, and the containment a Major disposition needs.

**Decide one.** Now the 10:00 failure: take `INJ-QA-INSPECT-012`'s disposition the
same way.

1. Record the **containment action**: what was done so nothing else like it escapes.
2. **Try to break it first:** choose **Use As Is** and leave the approval reference
   empty. You don't hold the authority, so the co-sign dialog opens; Maria signs in
   at your screen, and the decision is still refused: use-as-is accepts
   nonconforming product, and needs a recorded customer or design approval. Don't
   enter a reference to get past it.
3. Choose **Rework**, with the justification. Maria co-signs again, and the decision
   is recorded under Maria's name as the authority, with you as the caller.

---

## 6. Re-inspect after rework — 11:30

**You will:** read a part's history before inspecting it again.

`INJ-QA-INSPECT-013` failed Flow Calibration yesterday, was decided Rework on Maria's
authority, and waits at the Rework step.

**Exercise 6.1.** Open its traveler first and narrate it: which reading failed,
which disposition, who authorised it. Then work the Rework step: record the defect
corrected, inspect the repair, and sign it off. Completing it closes the
disposition, and the part goes back into Body Inspection to run the route again.

---

## 7. A gauge past due

**You will:** recognise the overdue-gauge warning from the floor's side, and what
QA does with it.

Body OD at Machining is measured with `Micrometer MIC-1`, which is past its
calibration due date. An overdue gauge isn't evidence the gauge is wrong, so a
reading on it is recorded, with a warning.

**Exercise 7.1.** Log in as Casey, who is running Machining on `INJ-0042-024`. Open
its step: the gauge picker reads *Micrometer MIC-1 (default) — calibration overdue*.
Record a Body OD of **6.002 mm** and a Pass, and complete the step. The warning
reads: *past its calibration due date — the reading was recorded; tell QA so the
gauge gets recalibrated.*

**Exercise 7.2.** As Sarah, find MIC-1 on **Quality** > **Calibrations** and say what
the shop should do about the readings taken with it since its due date.

---

## 8. A CAPA task

**You will:** work a task assigned to you on a corrective action.

`CAPA-2024-003` has two tasks for Sarah: updating the incoming inspection procedure,
and tightening sampling for nozzles. Open one from **My quality actions**, record
what you did, and complete it.

---

## 9. Read a record backward

**You will:** follow a finished part's record from the end to the start.

Open the traveler of any shipped part on `WO-2024-0038-A` and narrate it backward:
when it shipped, every step, every inspection and who signed it.

**What to look for:** a part QUARANTINED or SCRAPPED with no report or disposition
behind it is a broken record, not a finished one.

---

## Final task — observed

Your trainer regenerates the data, logs you in as Sarah, and says only: *"It's
08:30. Work your queue."* Then they watch without helping. The shift's work, in the
order you judge right:

- the first piece waiting on `WO-QA-INSPECT-01`
- the sampled part behind it, and why it was selected
- the purchased lot `RCV-MAT-0002`
- `INJ-QA-INSPECT-012` at Flow Calibration (record **95 mL/min**), through to its
  disposition decided with Maria's co-sign
- the unassigned disposition on `INJ-QA-INSPECT-015`, marked on the model
- `INJ-QA-INSPECT-013`'s record, narrated backward before you re-inspect it

Your trainer is watching for:

- [ ] You read the readings before signing anything.
- [ ] You went to blocking work (a first piece) before other work.
- [ ] Each reason you wrote would make sense to someone who wasn't there.
- [ ] When the system refused something, you read the refusal and acted on it.
- [ ] You never signed for work you did yourself.

## If your shop remanufactures

Everything above is new manufacture. A shop that also remanufactures adds this
module; a new-build-only shop skips it. See the [shop day's reman
moments](../shop-day.md#if-your-shop-remanufactures).

### R1. A harvested component — 16:30

**You will:** accept or scrap a component taken from a torn-down core.

A core torn down as a parts source yields components, each graded at teardown.
**Remanufacturing** > **Components** lists them with their grades. Core
`CORE-240215-0006` was torn down for parts:

1. Its **Injector Body** is grade A. From its menu, **Accept to Inventory**: it goes
   to stock as a part with its own serial, ready for a rebuild.
2. Its **Injector Nozzle Assembly** was graded scrap at teardown and is waiting for
   someone to scrap it. From its menu, **Scrap Component**, with the reason.

A customer's own repair-and-return unit is never harvested: its components go back
into that unit only.

## Recording your qualification

Passing the final task is the assessment. The record that lets you do the work is a
**training record**, which your QA manager writes; until it exists, the training
gate still refuses you. See [Training Records](../../workflows/quality/training-records.md).
