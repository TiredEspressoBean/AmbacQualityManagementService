# Operator

The operator's slice of [the shop day](../shop-day.md): starting a shift, finding the
next job, working a step by its instruction, recording what you measure, working a
batch and an assembly, and knowing what to do when something stops you. Every
exercise is on the training shop, and every record it names is one the training seed
creates.

**About 3 hours**, in one sitting. **Before you start:** nothing. This is the first
track for anyone who works on the floor.

!!! warning "On a training instance only"
    Every exercise writes real records: a completed step moves a part on, a reading
    becomes part of its history, and a signature can't be undone. See the [training
    program](../index.md).

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
    Each exercise has one exhibit, and working it uses it up: a finished step can't be
    finished again. Run trainees one at a time, or give each their own instance.

**Regenerating** (for the trainer): **Settings** > **Organization** > **Regenerate
demo data**, then type `REGENERATE` to confirm. It needs a staff login, appears only
on the training tenant, and replaces **everyone's** work on the instance. It runs in
the background and takes a few minutes; the card stops waiting after five, so if it
hasn't finished by then, reload the page later rather than pressing it again.

## Who you are

| You log in as | When |
|---------------|------|
| **Mike Rodriguez**, Operator, `mike.ops@demo.ambac.com` | Every module |
| **Casey Cross**, Shift Lead, `casey.dual@demo.ambac.com` | Signs in on your screen when a supervisor is needed |
| **Sarah Chen**, QA Inspector, `sarah.qa@demo.ambac.com` | Corrects a record for you in module 10 |

Every password is `demo123`. Dave Wilson, another operator, appears in the records:
he started the wash load you take over in module 5.

---

## 1. Start of shift

**You will:** clock in and read what your lead left for this shift.

Log in as Mike. Your home page says *Not clocked in*.

1. **Clock in.** Before you start, any note your lead marked *must acknowledge*
   comes up first: Casey has written that Flow Test Stand #2 is down until 10:00.
   Read it and press **Got it**. You can't close it without acknowledging; the
   record keeps your name and the time.
2. **Shift notes** shows the rest of what your lead left. Notes that don't need an
   acknowledgement can be dismissed with **Got it** once read.

**Break**, **Lunch** and **Clock out** are beside the clock, and your lead approves
your hours.

---

## 2. What's next

**You will:** read your home page and choose your next job.

Your home page is your queue, for the stations you work at. The station box at the
top chooses which: **Wash Line** is your usual station, and **All my stations**
shows everything.

- **Up next**: the job to do now, ranked by priority, then due date, then how long
  it has waited.
- **Then**: the jobs behind it.
- **In progress**: a job you started and haven't finished. **Resume** takes you back.
- **Scan**: type or scan a work order, serial, lot or location.

**Exercise 2.1.** Switch the station to **Machine Shop**. Say what's up next and why
it's ahead of `WO-OPS-01`, which waits under **Then**.

---

## 3. Find the unit in your hand

**You will:** go straight to the part you're holding.

Type `INJ-OPS-021` into **Scan** and press **Go**, as you would scan its traveler.
A serial opens its work order with **Start work on parts** open and that part
ticked. Close it for now: you'll assemble 021 in module 6.

---

## 4. Work a step and record as you go

**You will:** follow a step's instruction, record a measurement, and catch your own
mistake before it counts.

`WO-OPS-01` is four new injector bodies waiting at Machining.

1. Open `WO-OPS-01` from **Then** (station: Machine Shop), **Start Work**, tick
   `INJ-OPS-001`, and **Start**.
2. Read the instruction. Each field shows its target and limits: **Body OD** is
   6 mm ± 0.01.
3. The gauge is **Micrometer MIC-1**, marked *calibration overdue*. You can still
   record the reading, and you're told to let QA know.

**Try to break it:** type **6.02**. The field says **Out of spec**. You misread
the micrometer: correct it to **6.004**, and it says **In spec**. A reading you
correct before you complete the step never becomes a nonconformance.

4. Set **Body result** to **Pass**, then **Confirm & review**. The review lists
   everything you recorded, with the gauge. **Complete step**.

The part is recorded, but it doesn't move yet: the bodies on a work order move on
together, so 001 waits for 002 to 004. The message says so.

---

## 5. Take over a batch

**You will:** finish a batch step another operator started.

The Wash cleans a whole basket at once, so it's recorded once for the load, not per
body. Dave loaded `WO-OPS-02`'s four bodies and was moved to the flow bench.

1. Scan `WO-OPS-02`, **Start Work**, select all four, and **Start**. The parts are
   Dave's: *Assigned to someone else — currently assigned to Dave Wilson*.
2. Taking over another operator's work needs a supervisor. Casey signs in on your
   screen with their own email and password, and gives the reason.
3. In the wash cycle, record the **Bath Temperature** (60 °C ± 5), tick **Cycle
   complete**, and sign the **Cycle release** with your signature and password.
4. **Confirm for batch**, then **Seal batch**. Sealing moves the whole load on: all
   four bodies go to Body Inspection.

---

## 6. Assemble

**You will:** assemble two injectors and see what's recorded against them.

`WO-OPS-03`'s two bodies are back from the plater and waiting at Assembly.

1. Scan `INJ-OPS-021` and **Start**. Fit the nozzle, control valve and solenoid with
   new seals, record the **Assembly Torque** (25 Nm ± 2) and confirm the seals.
2. **Complete step**. You don't scan the components: the nozzle, valve, solenoid,
   spring and seals are drawn from stock and recorded against this injector when you
   complete the step.
3. 021 waits for its lot-mate. Do the same for `INJ-OPS-022`: when it's complete,
   both move on together.

---

## 7. When you can't run a job

**You will:** know what to do when something stops you.

Missing material, a broken fixture, a part you think is bad, or anything else that
stops the job: **go to your lead** and tell them. Don't work around it, and don't
leave a part half-done without saying so.

The **Can't run this?** and **Report a problem** buttons on your home page aren't in
use yet. Don't rely on them.

---

## 8. A step you're not trained for

**You will:** meet the training gate, and the supervisor who can authorise past it.

`WO-OPS-02`'s bodies are now at Body Inspection, and you're the only operator free.

1. Open `WO-OPS-02`, **Start Work**, tick `INJ-OPS-011`, and **Start**. You're
   refused: *Not qualified for this step — Dimensional Inspection Certification,
   level 1, needs level 2*.
2. Casey signs in on your screen and authorises it, with the reason. The record keeps
   who worked it, who authorised it, why, and what training was missing.

Body Inspection holds the run for a **first piece** check: the first body's
inspection is bought off by an inspector before the rest go through. That's the
inspector's job, in the [QA Inspector](qa-inspector.md) track.

---

## 9. Send a part back for rework

**You will:** take one bad part out of its lot and send it to rework, and leave a
record of why.

You've spotted a flaw in `INJ-OPS-004`'s turned diameter: a fault in the bar stock.
It shouldn't go on with the rest of the lot.

1. Open `WO-OPS-01`'s control page (**View in Control Center** on the work order).
   Tick `INJ-OPS-004` only.
2. **Rework**, choose the **Rework** step, and say why.

**Try to break it:** leave the reason empty. **Send to rework** stays disabled: a
part can't go to rework without a reason.

3. **Send to rework**. 004 is split from its lot and goes straight to Rework, so the
   rest of the lot isn't held up. Your reason is recorded as a failed quality report
   under your name, and a disposition opens for QA to review. If QA had already
   opened one on the part, your report joins theirs.

---

## 10. Getting a record corrected

**You will:** know what to do when you find you recorded something wrong after
completing the step.

You recorded `INJ-OPS-001`'s Body OD, then realised you measured it before the body
had cooled. The reading needs taking again.

1. **Try to break it:** on `WO-OPS-01`'s control page, open 001's history (**Show
   history**) and its **Checks**. You can see your record, but there's no way for you
   to void it. Tell QA.
2. Log in as Sarah. On the same record, **Void**, with the reason. The record stays
   on file, marked void with the reason, and Machining reopens for 001.
3. Log back in as Mike. Scan `INJ-OPS-001` and **Start**: the step opens with what
   you recorded before. Measure again, enter the new reading, and **Complete step**.

A completed record is evidence: only quality can void one, and the original stays on
file.

---

## 11. When the terminal is down

There is no offline mode. If the terminal or scanner is down, record on the paper
traveler, and enter it when the terminal is back. The system records when you enter
it, not when you did the work, so say on the traveler when the work was done.

---

## 12. Your training

**Quality** > **Training** > **My Training** lists your qualifications, their levels
and when each expires. Mike's Dimensional Inspection and Nozzle Inspection
certifications are level 1, and both expire within the month.

---

## Final task — observed

Your trainer regenerates the data, logs you in as Mike, and says only: *"Start your
shift."* Then they watch without helping:

- clock in, and acknowledge what your lead left
- take over Dave's wash load on `WO-OPS-02` and seal it
- assemble `WO-OPS-03`'s two injectors
- machine `INJ-OPS-001`

Your trainer is watching for:

- [ ] You read the instruction and the limits before recording.
- [ ] You checked each reading against its limits before completing the step.
- [ ] You went to your lead when something stopped you, instead of working around it.
- [ ] When the system refused something, you read the refusal and acted on it.

## If your shop remanufactures

Everything above is new manufacture. A shop that also remanufactures adds this
module; a new-build-only shop skips it. See the [shop day's reman
moments](../shop-day.md#if-your-shop-remanufactures).

### R1. Tear down a core and grade what comes out

**You will:** take a used injector apart and grade each component as it comes out.

`CORE-240220-0003` and `CORE-240220-0004` are used injectors Dave received this
morning, checked in and signed off. They wait at Disassembly.

1. Scan `CORE-240220-0003` and **Start**.
2. Scan the core's identity band, and photograph the teardown layout if your bench
   has a camera.
3. **Grade each component as it comes out.** The list is what this injector should
   contain: body, nozzle and control valve. Give each a grade: **A** or **B** if it's
   serviceable, **C** if it needs reconditioning, **Scrap** if it's beyond saving.
   This injector's body and valve are good (A); the nozzle needs reconditioning (C).
   *When in doubt, grade down.*
4. A component that isn't there is **Missing**. One you didn't expect goes under
   **Found something unexpected?**

**Try to break it:** press **Confirm & review** before grading anything. You stay
on the step, and the line above the button says what's missing: every expected
component must be graded or marked missing.

5. **Complete step**. Each component is recorded with its grade, under your name.
   0003 waits for its lot-mate: tear down 0004 the same way.

## Recording your qualification

Passing the final task is the assessment. The record that lets you do the work is a
**training record**, which your QA manager writes; until it exists, the training
gate still refuses you. See [Training Records](../../workflows/quality/training-records.md).
