# Shift Lead

The shift lead's slice of [the shop day](../shop-day.md): reading the shift, putting
people on work, clearing what stops a job, making the calls an operator can't, and
handing over. Every exercise is on the training shop, and every record it names is
one the training seed creates.

**About 3 hours**, in one sitting. **Before you start:** the [Operator](operator.md)
track. Claiming work, running a step and recording a reading are there, not here.

!!! warning "On a training instance only"
    Every exercise writes real records: a reassignment moves someone's work, a
    training record lets someone past the gate, and a harvest consumes a unit. See the
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
    Each exercise has one exhibit, and working it uses it up: a cleared hold can't be
    cleared again. Run trainees one at a time, or give each their own instance.

**Regenerating** (for the trainer): **Settings** > **Organization** > **Regenerate
demo data**, then type `REGENERATE` to confirm. It needs a Tenant Admin login, appears only
on the training tenant, and replaces **everyone's** work on the instance. It runs in
the background and takes a few minutes; the card stops waiting after five, so if it
hasn't finished by then, reload the page later rather than pressing it again.

## Who you are

| You log in as | When |
|---------------|------|
| **Casey Cross**, Shift Lead, `casey.dual@demo.ambac.com` | Every module |

Every password is `demo123`. Casey is an inspector by day and covers as shift lead,
so the account holds both roles. Mike Rodriguez and Dave Wilson are the operators on
the shift.

---

## 1. Your shift at a glance

**You will:** land on the shift lead's home page and say what needs you.

Log in as Casey. You land on the **QA Inspector** home: Casey's last choice. The
picker at the top (**QA Inspector**) switches the landing; choose **Shift Lead**. The
choice is kept for next time, per person.

The Shift Lead home:

- **Biggest fire**: the job most needing you, with its due date and a link to its
  control center.
- **Work orders**, **Jobs going late**, **Work orders on hold**.
- **Needs attention**: parts in quarantine, CAPAs pending verification.
- **Outside processing**, and **Training**: current, expiring soon, expired.

**Exercise 1.1.** Say what the biggest fire is, when it's due, and which work order is
on hold.

The picker also offers **Operator**, a role Casey doesn't hold. That's a supervisory
preview: it shows you the operator's home, not the operator's permissions.

---

## 2. Cover a job

**You will:** find who can cover an absence, and put them on the work.

Dave Wilson has called in sick. Before you move his work, find out who can do it.

**Quality** > **Training** > **Matrix**: one row per person, one column per skill.
Hover a cell to read it: *Dave Wilson — Assembly Certification: Qualified*. The
footer counts how many people are qualified (L3 and up) for each skill, so a column
with one is a single point of failure. A cell marked *Expires 2026-10-29* lapses
then, and after that date the plan won't give that person the step.

**Scheduling** > **Schedule (Gantt)**, then **People**: one row per operator, with
the work the plan gives them, and **— Unassigned —** for work nobody could be given.

1. Open a single task (a part at one step). The panel shows the work order, machine,
   operator, times and fence zone.
2. **Reassign — applies now, re-solve to optimize**: choose another operator. The
   list is the shop-floor crew who are qualified for the step. If it's empty, that's
   a training problem, not a scheduling one.

The toolbar has **Dispatch**, **New WO** and **Undo**, but no **Solve** or
**What-if**: re-planning the shop is your planner's or production manager's. When
the board says *stale — re-solve*, tell them.

---

## 3. Clear what stops a job

**You will:** read the exceptions, and record a machine going down.

**Production** > **WO Control Center** > **Exceptions** pairs every open problem
with the work it stops: quarantined parts, CAPAs and downtime, each with its age,
owner and *Impacts N WO*. Work the ones stopping a job first, whatever their
severity.

1. **Report exception**. Type **Downtime**, the machine (**Ultrasonic Cleaner
   UC-1**), the category, a reason (*Transducer fault*) and what happened. **Record
   downtime**. It starts now and shows in the list.
2. When the machine is back, **Resolve** it. The record keeps when it went down and
   came back, who reported it and who resolved it.

**Recorded it wrong?** The wrong machine, or the wrong times? **Correct…** on its row
(turn off **Open only** to find a resolved one). Fix the machine, category, times or
what happened, and say why. Each change and your reason stay on the record.

A quarantine or a CAPA is raised on its own form, not here.

---

## 4. Hold a job, and let it go

**You will:** release a work order that was held.

`WO-TRAIN-HOLD` was put on hold by the production manager for a quality concern.

1. Open it from **Work orders on hold** on your home page. The banner says why it's
   held, who placed the hold and when: *On hold · Quality hold*.
2. **Start Work** is disabled while it's held, and says why.
3. **Resume**: *Clear the hold and resume?* restates the hold. A quality or tooling
   hold needs **What resolved it**; **Clear hold** stays disabled until you say.
4. Write what resolved it and **Clear hold**. The order goes back to where it was,
   and **Hold history** keeps the hold, who cleared it and your note.

A hold put on the wrong order comes off the same way: **Resume**, and say it was
placed in error. The history keeps both.

---

## 5. Jump a job to the front

**You will:** expedite a work order, with the reason on record.

There's no Expedite button: *expedited* means the work order's priority is
**Urgent**.

1. Edit `WO-OPS-03` and set **Priority** to **Urgent**.

**Try to break it:** save without a reason. It refuses: *Say why the priority is
changing.*

2. Give the reason and save. **Priority changes** lists it: *Normal → Urgent*, your
   name, the time and your reason.

---

## 6. Someone isn't qualified

**You will:** authorise past the training gate, and then fix the record.

When the record says an operator isn't qualified, the start is refused with the
training that's missing. You sign in on their screen with your own email, password
and a reason, and the step is logged against your name. You did this in the
[Operator](operator.md) track from the operator's side.

The override is the exception. If they're genuinely trained, write the record:

1. **Quality** > **Training** > **Training Records** > **New Training Records**.
2. **Trainee**: type a name to search. Mike Rodriguez. **Training Type**: Nozzle
   Inspection Certification. **Completion Date**: the day they were assessed.
   **Competency Level**: what they demonstrated, not what the course was. **Trainer**:
   who assessed them.
3. **Create Training Record**. The expiry comes from the training type's validity.
   Next shift, the gate lets them through.

**Training overrides**, the list of every override, is the QA manager's review,
not yours: it needs the audit-log permission. An override on one part shows on that
part's steps.

---

## 7. Hand over

**You will:** leave the next shift a note they must read.

**Production** > **Shift notes**.

1. Choose the **Audience** (Operator), write what happened and what the next shift
   should do, and tick **High priority** and **Requires acknowledgment** when it
   matters. **Post note**.
2. Your notes list below with their acknowledgement count: *Acknowledged 0 of 2*.
   Operators get a must-acknowledge note at clock-in and can't dismiss it unread.

A note is not a quality record: a part that looked wrong goes in a quality report.

Then approve the shift's hours: **Scheduling** > **Operator Hours**. It shows on-shift
and direct (job) hours per operator, and **Awaiting approval** lists each finished
entry: shift, break, lunch, or production against a work order. **Approve** one, or
**Approve all**. Your own entries read *Your time*: someone else approves those.

Someone clocked out late, or forgot to clock in on time? **Correct times** on their
entry, before you approve it. Change the clock-in or clock-out, say why, and the hours
recalculate. Approve the hours only once they're right: an approved entry can't be
corrected here.

---

## 8. Send a part back a step

**You will:** undo a step that was finished too soon.

Have Mike finish Machining on all four bodies of `WO-OPS-01` (they move on to
Precision Grinding together), then find out the micrometer he used was overdue: one
body needs measuring again.

1. **Production** > **WO Control Center**, open `WO-OPS-01`. On `INJ-OPS-001`'s row,
   **Previous step**.
2. *Roll back 1 part(s) to the previous step?* Give the reason. **Roll back**.
3. *1 part(s) rolled back.* The body is back at Machining on a second visit; its
   Grinding visit is marked rolled back, not deleted. The other three wait at
   Grinding: the lot moves together, so it waits for this one.

A step can be undone directly for a short while after it's finished; each step sets
how long. After that, or where the step requires it, the rollback is sent for
approval instead, and the page says so.

---

## 9. What isn't yours

| Not yours | Whose |
|-----------|-------|
| Void a recorded step | QA inspector, QA manager |
| Decide a disposition | QA manager |
| Solve or commit the schedule | Planner, production manager |
| Cancel a work order | Production manager |
| Review all training overrides | QA manager |

Casey also holds QA Inspector. When you void a record as Casey, you're doing it as
an inspector, not as a lead.

---

## Final task — observed

Your trainer regenerates the data, logs you in as Casey, and says only: *"You're
covering the shift."* Then they watch without helping:

- say what the biggest fire is, and what's on hold
- record the cleaner going down, then resolve it
- release `WO-TRAIN-HOLD`, saying what resolved it
- expedite `WO-OPS-03` with a reason
- leave the next shift a must-acknowledge note

Your trainer is watching for:

- [ ] You worked what stops a job before what's merely severe.
- [ ] Every override, expedite and release carried a real reason.
- [ ] You fixed the record rather than relying on overrides.
- [ ] When the system refused something, you read the refusal and acted on it.

## If your shop remanufactures

Everything above is new manufacture. A shop that also remanufactures adds these
modules; a new-build-only shop skips them.

### R1. Decide a finding

**You will:** decide a component an operator found worse than teardown graded it.

`CORE-240214-0010` is Northern Trucking's own injector, here for repair under
`ORD-2024-0047`. At Nozzle Inspection, Mike found the nozzle beyond repair. A
replacement isn't pre-approved at that check, so his finding waits for you, and the
unit holds there until you decide.

1. Your home page's **Needs attention** has *Finding to decide: CORE-240214-0010*.
   It opens the unit's rebuild plan: **1 finding to decide**: *Injector Nozzle Assembly · Grade B → SCRAP*,
   with Mike's words and the time.
2. **Apply** re-grades the component and the plan re-resolves from it; a scrap grade
   also scraps the component, so you're asked to confirm. **Dismiss** keeps the
   teardown grade and needs a reason. Either way the decision goes on the
   component's notes.
3. **Apply**. *Expected repairs* now lists *Nozzle Replacement · NZL-REPLACE · Needs
   approval*, with the finding behind it.

### R2. Ask the customer about extra work

**You will:** send a customer's own unit for their answer on work beyond what they
bought.

Replacing the nozzle on `CORE-240214-0010` is more than the standard rebuild
Northern Trucking bought, and it's their unit, so they decide.

1. On the core (or its work order's **Cores** card), **Authorise…**. It lists the
   repairs it will send and the finding behind each. **Send for authorisation**.
2. *Sent for customer authorisation.* The core waits, *Awaiting customer
   authorisation*, until someone records their answer (the
   [Production Manager](production-manager.md) track, R1).

UQMES produces the scope: what work, and the finding behind it. The price is agreed
in the system that owns it.

### R3. Decide a torn-down core's exit

**You will:** choose what happens to a core once it's apart.

`CORE-240215-0006` is an exchange unit, torn down and graded: fair, with
significant corrosion. **Remanufacturing** > **Cores**, open it.

- **Plan rebuild** / **Rebuild to stock**: the unit is rebuilt and stocked.
- **Harvest for parts**: its usable components go to stock and the unit is
  consumed. It asks you to confirm, because it can't be undone.
- **Scrap**: with a reason.

A unit that goes back to its customer offers only rebuild: it isn't yours to
harvest. Harvest this one: its grade and corrosion make a rebuild a poor bet.

## Recording your qualification

Passing the final task is the assessment. The record is a **training record**, which
your QA manager writes. See [Training Records](../../workflows/quality/training-records.md).
