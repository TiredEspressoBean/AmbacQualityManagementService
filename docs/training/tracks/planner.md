# Planner

The planner's slice of [the shop day](../shop-day.md): releasing work onto the
schedule, solving it and finding out why work isn't on it, keeping the calendar the
plan is built on, and getting tomorrow's work staged. Every exercise is on the
training shop, and every record it names is one the training seed creates.

**About 2 hours**, in one sitting. **Before you start:** the
[Production Manager](production-manager.md) track's modules 3–6 (promising a date,
releasing, the schedule, what to release) use the same pages, from the manager's
side.

!!! warning "On a training instance only"
    Every exercise writes real records: a release puts work on the plan, a solve
    replaces it, and a closure moves everyone's work. See the [training
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

**Regenerating** (for the trainer): **Settings** > **Organization** > **Regenerate
demo data**, then type `REGENERATE` to confirm. It needs a staff login, appears only
on the training tenant, and replaces **everyone's** work on the instance. It runs in
the background and takes a few minutes; the card stops waiting after five, so if it
hasn't finished by then, reload the page later rather than pressing it again.

!!! note "The schedule needs its worker"
    Solving runs in the background. With no worker running, the schedule page says
    *queued, waiting for a worker* and nothing happens. Ask whoever runs the
    instance to start it before the session.

## Who you are

| You log in as | When |
|---------------|------|
| **Sam Okafor**, Planner, `sam.plan@demo.ambac.com` | Every module |

Every password is `demo123`.

---

## 1. Your desk

**You will:** read the planner's home page.

Log in as Sam. Your home page has the planning pages one click away: the **Schedule
board**, **Requirements**, **Capacity**, the **Calendar** and **Staging**. Below them:
jobs going late, work orders on hold, and **Late deliveries**, inbound material a
supplier is late with, with **Chase…** to record when you chased it and what they
said.

**Exercise 1.1.** Say which inbound delivery is late, and what the supplier said
when it was last chased.

---

## 2. Release work

**You will:** release work onto the plan, and see what happens to work you haven't
released.

This shop plans **released work only**. Releasing is a decision: it says the work
may now take machine and operator time.

1. **Scheduling** > **Schedule (Gantt)**. **Pull in work** (with a count) lists the
   work orders waiting to be released: `WO-TRAIN-PM-001` and `WO-ASSESS-PM-001`.
2. Tick `WO-TRAIN-PM-001` and **Release**. *Released 1 — re-solve to plan them.*
   Releasing doesn't move anything by itself.
3. **Not scheduled** now says why each piece of open work isn't on the board:
   `WO-TRAIN-PM-001` was *added since the last solve*; `WO-ASSESS-PM-001` is *not
   released* (*Release it from the planning queue*); `WO-TRAIN-HOLD` is *on hold*;
   `WO-2024-0048-A` has *no units created yet*.

---

## 3. Solve, and pin what must stay put

**You will:** solve the plan, and keep one task where you put it.

1. Open a single task (a part at one step), for example `INJ-0042-021` at Final
   Test. The panel shows its machine, operator, times and **fence zone**. **Pin** it:
   *Task pinned*.
2. **Solve**. It runs in the background; the header then shows whether it found a
   plan (*FEASIBLE*), its late orders and how long it took. Judge it by the late
   orders: *within N%* includes the cost of keeping work already under way in
   place, so on a re-solve it isn't a quality score.
3. Open the task again: it's where you pinned it. **Not scheduled** no longer lists
   the work you released.

**Dispatch** puts named operators on the plan's work, and **What-if** solves a
draft beside it to compare: see the Production Manager track, module 5.

---

## 4. The calendar the plan is built on

**You will:** close the plant for a day and check the plan moved around it.

**Scheduling** > **Calendar** holds the non-working time the scheduler plans around:
plant closures, recurring blocks (the weekly meeting), absences, and overtime. Each
working day shows how many of the crew are in.

1. Click a working day next week, **Add closure**, name it, choose the kind (*Plant
   shutdown*) and **Save**. *Closure added.*
2. Back on the schedule, the header says *stale — re-solve*: the plan no longer
   matches the calendar.
3. **Solve**. That day carries no work; the day after picks it up.

A stale calendar breaks the plan on day one, so the person who owns the plan owns
the calendar.

---

## 5. Stage tomorrow's work

**You will:** see what each bench needs before the operator gets there.

**Scheduling** > **Staging List** shows the next 8 hours of scheduled work by
station, with the material each job needs and whether it's staged. **Pick Sheet** and
**Kit Sheet** print it. When the plan is stale it says so: re-solve before staging
to it.

On a closure day the 8-hour view is empty: widen the window before concluding
anything is broken.

---

## Final task — observed

Your trainer regenerates the data, logs you in as Sam, and says only: *"Close the
plant next Thursday for power work, and get the assessment order onto the plan."*
Then they watch without helping:

- add the closure
- release `WO-ASSESS-PM-001`
- solve, and show that Thursday is empty and the order is placed

Your trainer is watching for:

- [ ] You checked **Not scheduled** before and after.
- [ ] You re-solved after changing the calendar and releasing.
- [ ] You checked the plan actually honoured what you changed.

## Recording your qualification

Passing the final task is the assessment. The record is a **training record**, which
your QA manager writes. See [Training Records](../../workflows/quality/training-records.md).
