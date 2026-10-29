# QA Manager

The QA manager's slice of [the shop day](../shop-day.md): the decisions an inspector
can't make alone. You decide dispositions, rule on what arrives at the dock, decide
which nonconformances get corrective action, approve and verify CAPAs, act on a
supplier's standing, and answer for the gauges, the sampling plans and the people's
qualifications. Every exercise is on the training shop, and every record it names
is one the training seed creates.

**About 5 hours**, in two sittings. **Before you start:** take the [QA
Inspector](qa-inspector.md) track, or know it. Most of what reaches you is an
inspector's work, and you review it.

!!! warning "On a training instance only"
    Every exercise writes real records: a decision releases a part, an approval lets
    corrective work start, a suspension holds a supplier's lots, and signatures can't
    be undone. See the [training program](../index.md).

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
    Each exercise has one exhibit, and working it uses it up: a decided disposition
    can't be decided again. Run trainees one at a time, or give each their own
    instance.

**Regenerating** (for the trainer): **Settings** > **Organization** > **Regenerate
demo data**, then type `REGENERATE` to confirm. It needs a Tenant Admin login, appears only
on the training tenant, and replaces **everyone's** work on the instance. It runs in
the background and takes a few minutes; the card stops waiting after five, so if it
hasn't finished by then, reload the page later rather than pressing it again.

## Who you are

| You log in as | When |
|---------------|------|
| **Maria Santos**, QA Manager, `maria.qa@demo.ambac.com` | Every module |

Every password is `demo123`. You are the shop's only QA manager. That matters twice:
a CAPA plan you raise has nobody else to approve it, so you approve it yourself with
a written justification, and work you did yourself is work you can't verify.

---

## 1. Start of shift

**You will:** read the QA manager's home page and know what each part of it asks of
you.

Log in as Maria. The home page is a list of decisions waiting on you:

- **Needs attention**: a whole-lot reject an inspector has asked for, a repair unit
  waiting on its customer's answer, parts in quarantine, CAPAs waiting for their
  effectiveness check.
- **Quality**: open NCRs, parts under disposition, active and overdue CAPAs, first
  pass yield.
- **Overdue calibrations**: every gauge past its due date, shop-wide.
- **Supplier qualifications expiring**, **Competency coverage** and **Training**.
- **Approvals in flight**, and **My quality actions**: what is assigned to you.

**Exercise 1.1.** From the home page alone, say which gauges are overdue and by how
long, which lot is waiting on your decision and why, and how many approvals are
waiting for you. Don't open anything yet.

**Exercise 1.2.** Open **Approvals**. **Awaiting my approval** lists what you
decide; **My submitted requests** lists what you asked others for. Find
`CAPA-2024-004` and say who raised it.

---

## 2. Decide a disposition

**You will:** decide what happens to a nonconforming part, and record the evidence
the decision rests on.

`INJ-QA-MANAGE-002`'s bore measured **4.007 mm** against a maximum of 4.005.
Sarah failed it at Body Inspection, contained it (the other bodies from that grinder
setup were re-checked) and assigned the decision to you. Find it in your **Inbox** >
**Dispositions**.

1. Open it. Read the failed report it carries: the reading, the limits, and the
   defect Sarah recorded.
2. The bore is 0.002 mm over, the seat finish is good, and engineering has issued
   concession `ENG-CONC-0041`. Choose **Use As Is**.

**Try to break it:** submit without a concession reference. Use As Is accepts a
nonconforming part, so it is refused until a customer or design concession is
recorded.

3. Tick **Requires approval** and **Approval received**, enter `ENG-CONC-0041` as
   the reference, and say in the resolution notes what the decision rests on.
   Submit. The decision is recorded as yours, and the part leaves quarantine.
4. Set **Current state** to **Closed** and submit. Closing records who resolved it,
   and when.

**A finding that wasn't.** `INJ-QA-INSPECT-052` was failed for a burr that turned
out to be a reflection. Sarah voided the finding and re-inspected it as a pass ([QA
Inspector](qa-inspector.md), module 10). Its disposition is yours: open it and
choose **Not a nonconformance (result voided)**. It closes with Sarah's void reason in
the notes and releases the part. It's refused until the re-inspection is on record as
a pass, so the close rests on evidence, not on the inspector's word.

**Decided wrong?** Until it's closed, a decision can be changed. **Scrap** asks you
to confirm, because the part is scrapped as soon as you save. Change a Scrap to
another decision and you're asked why: the part comes back out of scrap, and both
decisions and your reason stay in the resolution notes. Closed by mistake?
**Reopen** it, with a reason. It's *In progress* again, to re-decide or close again,
and the decision stands until you do. Your reason goes into the resolution notes.

---

## 3. Rule on what arrives

**You will:** release a hold that needs judgement, and decide an inspector's request
to reject a whole lot.

**A whole-lot reject request:** `RCV-MAT-0007`, from **Needs attention**. Sarah found
corrosion on every piece she sampled and asked to send all 300 back. Rejecting a
whole lot is your decision, not hers, so the lot is held until you make it. The hold
panel shows who asked and why.

1. Read her reason and open the inspection behind it.
2. You've looked at the cartons: the spotting is on the bottom layer only.
   **Decline request…**, and say why. The lot goes back to inspection, where the
   affected pieces can be rejected on their own.

Had the whole lot been bad, **Confirm: reject whole lot** would have rejected it
back to the supplier.

**A judgement hold:** `RCV-MAT-HOLD` is held for two reasons, and each clears on its
own. Its missing heat number is paperwork, and receiving can clear it. The other is
yours: the lot comes from **Bargain Bolts LLC**, an unqualified supplier.

3. **Release this hold…** on the unqualified-supplier hold, with the basis: the
   qualification audit is booked, and you accept this lot on its certificate and a
   100% visual. The heat-number hold stays.

---

## 4. Which nonconformances get a CAPA

**You will:** decide, for each failed report, whether it needs corrective action,
and record why when it doesn't.

ISO 9001 10.2.1(b) asks you to *evaluate* whether action is needed to stop a
nonconformance recurring. The evaluation is the record. **Open NCRs** on your home page
opens **NCR & Disposition Analysis**. **Awaiting a CAPA decision** lists failed reports nobody has
decided on yet. **Repeat defects** lists defects on three or more failed reports in
30 days.

**A one-off:** `QR-0038-010-NI`, a spray angle of 20 degrees on a part that was
scrapped.

1. Open it. Under **CAPA decision**, choose **No CAPA needed** and say why: one
   part, damaged in handling, with nothing like it since. **Record decision**. The
   record keeps your name, the time and your reason, and the report leaves the
   list.

**A pattern:** **Repeat defects** shows *Flow rate out of spec*, three times at Flow
Calibration.

2. Open `QR-0042-017-FT` and **Create CAPA**. The report comes linked. Make it a
   Major corrective action, state the problem (three injectors below the 100 mL/min
   limit in 30 days), record the containment already in place, and assign it to
   Jennifer.

A Major or Critical CAPA's plan is approved before work starts. Until then, only
containment can be worked; corrective and preventive tasks and the root-cause
analysis wait.

3. Open the new CAPA's **Approval** tab and **Submit Response**. A Major CAPA's plan
   is a QA Manager's to approve, and you are the only one, so nobody else can decide
   it. The dialog says so: *You requested this approval, and nobody else can decide
   it. You may decide it yourself; it's recorded as self-approved, with your
   justification.* **Approve**, write the justification, sign, and enter your
   password.

**Try to break it:** give a justification of a few words. It is refused:
*You're deciding your own request: give the justification (at least 10 characters).* Where someone
else can approve, the person who raised the CAPA can't: the request waits for them.

---

## 5. Approve, then verify, a CAPA

**You will:** give a CAPA its go-ahead, approve its root cause, and decide whether it
worked.

**The go-ahead:** `CAPA-2024-004`, raised by Jennifer, is waiting for your approval.
Its containment is already in progress, which is allowed.

1. Read the problem and the containment. **Approval** > **Submit Response** >
   **Approve**, with your signature and password.

**The root cause:** `CAPA-2024-003` is approved and in progress. Jennifer has
finished a fishbone analysis.

2. **Root Cause** tab: read the six branches and the identified cause. **Approve**,
   noting what you checked it against. Approving records you as the verifier. A
   verified root cause is required before the CAPA can go to verification.

**Effectiveness:** `CAPA-2024-002`'s actions are complete, and it waits on
verification. Verification has two stages: the plan, then the result.

3. **Verification** > **Add Verification**: the method (review every receiving
   inspection for 30 days) and what counts as success (no lot held for missing
   paperwork).
4. **Complete Verification** > **Effective – Confirmed**, with what you found. The
   CAPA closes.

**Try to break it:** `CAPA-TRAIN-COMPLETE` is your own CAPA, raised and worked by
you. Add a verification plan and try to complete it. Self-verification is refused
unless the CAPA was set up to allow it.

---

## 6. A supplier's standing

**You will:** read a supplier's scorecard and act on it.

Open **Supply** > **Supplier Quality**. Each scorecard shows lots received,
accepted and rejected, the reject rate, CoC compliance, on-time delivery and open
SCARs. **Great Lakes Diesel** is rated C, with a recommendation to review for
suspension.

1. Read why: a rejected lot, low CoC compliance and an open SCAR.
2. **Suspend from the Approved Supplier List**, then from Great Lakes Diesel's row
   menu, **Suspend…**, with the reason. Their lots waiting at the dock
   (`RCV-MAT-0001` to `0004`) are held as *Unqualified supplier*, and so is anything
   they deliver until they're requalified. Stock already accepted isn't touched. You
   release a held lot on its merits, as in module 3.

The open SCAR, `CAPA-SU-2026-001`, is a CAPA of type Supplier: it takes the same
go-ahead and effectiveness check as module 5.

---

## 7. Gauges

**You will:** find everything a failed gauge measured, and record a calibration.

**A gauge that failed:** **Micrometer MIC-2** failed its calibration this morning
(it reads 0.012 mm high). Everything it measured since its last good calibration
may be wrong.

1. **Quality** > **Calibrations** > **View All Calibration Records**. Under MIC-2's
   failed result, **What it measured** lists every quality report it was used on
   since its last good calibration. Here, five bodies at Body Inspection.
2. Say what you would do about each. The list doesn't act: re-inspecting, accepting
   on other evidence, telling a customer or raising an NCR is your decision, made
   outside it.

**A gauge that's overdue:** **Torque Wrench TW-25** is past due (it's on your home
page).

3. **Record New Calibration** for TW-25: today's date, the next due date, the result
   (**Pass**), the as-found condition (**In tolerance**), who did it, the
   certificate number and the standard used. It is back in calibration.

---

## 8. Sampling and the control chart

**You will:** answer why a part was or wasn't inspected, tighten a plan, and read a
control chart.

**Why wasn't that part inspected?** On `WO-QA-INSPECT-01`, `INJ-QA-INSPECT-004` was
inspected at Body Inspection and `INJ-QA-INSPECT-002` wasn't.

1. On the work order, open each part's history (**Show history** on its row).
   Under its traveler, **Sampling decisions** say why: 004 was
   *selected by every 4th part*; 002 was *not selected: no rule in Standard
   Inspection - Body chose it*. That is the answer an auditor wants for an
   uninspected part.

**Tighten a plan:** after the burr found at Body Inspection, you want every second
body inspected, not every fourth.

2. **Data Management** > **Sampling Rule Sets**: open **Standard Inspection - Body** with
   the edit button on its row. Change the **Every Nth part** rule's N from 4 to 2. Rule changes save as
   you make them, and the next parts at Body Inspection are sampled under the new
   rule.

**A control chart:** **Analytics** > **SPC**.

3. Choose Injector Build, Flow Calibration, Flow Rate. Read the chart: the centre
   line, the control limits, and any point flagged against the rules. Control
   limits are the process's voice; the specification limits are the customer's.
   A point can be in spec and still out of control.

Here, SPC informs you; it doesn't stop work. With too little history, the page says
capability can't be judged yet.

---

## 9. People's qualifications

**You will:** find whose qualification lapses this month, and record a renewal.

1. **Quality** > **Training**. **Expiring Soon** lists qualifications expiring
   within 30 days: Mike Rodriguez's Dimensional Inspection and Nozzle Inspection
   certifications, both at level 1.
2. **Training Matrix** shows every person's level in every skill, who falls short of
   their role's requirement, and the skills only one person covers.

Mike has been reassessed on the CMM and now works to level 2, with his output still
checked.

3. **Record New Training**: Mike, Dimensional Inspection Certification, today, level
   2 (Assisted), with Sarah as trainer and a note of how he was assessed. The level
   is what he showed he can do, not that he attended.

A training record is what lets a person start a step that requires the training.
See [Training Records](../../workflows/quality/training-records.md).

---

## 10. The record for one serial

**You will:** produce the complete record of one part on demand.

A customer asks what was done to `INJ-QA-INSPECT-013`. Open the part and print its
**Traveler**: every step, who did it and when, what was measured, the lots it used,
how many visits each step took, and any training override. 013 failed Flow
Calibration and is waiting at Rework.

**Exercise 10.1.** From the Traveler alone, say who ran 013's Flow Calibration, what
it read against what limit, and where the part is now.

---

## Final task — observed

Your trainer regenerates the data, logs you in as Maria, and says only: *"Your
decisions are waiting."* Then they watch without helping. The work, in the order you
judge right:

- the whole-lot reject request on `RCV-MAT-0007`
- the disposition on `INJ-QA-MANAGE-002`
- the failed reports awaiting a CAPA decision, including the repeat flow-rate defect
- `CAPA-2024-004`'s go-ahead, and `CAPA-2024-002`'s effectiveness
- what MIC-2 measured before it failed, and what you'll do about it

Your trainer is watching for:

- [ ] You read the evidence (readings, reasons, reports) before deciding.
- [ ] Each reason you wrote would make sense to an auditor who wasn't there.
- [ ] You never approved or verified your own work.
- [ ] When the system refused something, you read the refusal and acted on it.
- [ ] You went to blocking work (a held lot, a held part) before reviews.

## If your shop remanufactures

Everything above is new manufacture. A shop that also remanufactures adds this
module; a new-build-only shop skips it. See the [shop day's reman
moments](../shop-day.md#if-your-shop-remanufactures).

### R1. The customer's answer on extra work

**You will:** record a customer's decision on repairs they didn't buy.

`CORE-240212-0009` is Great Lakes Diesel's own injector, sent for repair. Teardown
passed its nozzle, but at the bench a hairline crack showed under magnification. A
replacement nozzle isn't pre-approved and isn't part of the standard rebuild they
bought, so the unit waits for their answer. UQMES doesn't price or quote the work: it
records what was found and what the customer said.

1. **Needs attention** on your home page opens the core. It shows **Awaiting
   customer authorisation**.
2. The customer's fleet manager emailed approval. **Approved…** lists the repairs
   waiting on their answer, each ticked (here, replacing the nozzle). Record who
   answered, how, and the reference, then **Record answer**. The rebuild resumes.

Had they declined, **Declined…** would send the unit back unrepaired. A customer can
also decline single repairs: untick them in **Approved…**. Declining a repair your
shop marked required declines the unit; an optional one is left out of the rebuild.

### R2. A unit out of reworks

**You will:** decide a unit the routing has stopped retrying.

`CORE-240219-0014` failed Nozzle Inspection on spray angle twice, and was reworked
twice. The routing allows two visits to that check, so after the second rework the
unit didn't go back to it: it went to **MRB Review**, quarantined, with a disposition
opened for you. MRB Review is a holding step. Nothing runs there; your decision
moves the unit on.

1. **Dispositions to take** on your home page lists it, tagged **MRB**: *Visit cap
   reached at Nozzle Inspection (2 visit(s)). Decide: scrap, use as is on a
   concession, or one more rework.* Nobody has taken it yet. **Take it**: it leaves
   the queue for your **Inbox** > **Dispositions**. Open it from there.
2. It carries the last failed report, the finding that sent the unit round the loop.
   Read it, and the unit's earlier failures: what was out, by how much, and what each
   rework did. The second rework's own disposition is closed, pointing at this one.
3. Choose the decision:
   - **Rework** gives the unit one more try: it goes back to Rework.
   - **Use As Is**, on a concession, continues the unit past the check.
   - **Scrap** ends it.
4. Say in the resolution notes what the decision rests on, and update the
   disposition.

## Recording your qualification

Passing the final task is the assessment. The record that lets you do the work is a
**training record**, written by someone other than you. See [Training
Records](../../workflows/quality/training-records.md).
