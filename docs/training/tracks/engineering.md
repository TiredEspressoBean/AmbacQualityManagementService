# Engineering

Engineering's slice of [the shop day](../shop-day.md): changing an approved routing
under change control, defining what gets measured, and writing the instruction the
operator follows. Every exercise is on the training shop, and every record it names
is one the training seed creates.

**About 2 hours**, in one sitting. **Before you start:** the [Operator](operator.md)
track helps: you'll write what an operator reads.

!!! warning "On a training instance only"
    Every exercise writes real records: an approved change becomes the routing every
    new work order is built to. See the [training program](../index.md).

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
| **Jordan Reyes**, Engineering, `jordan.eng@demo.ambac.com` | Every module |

Every password is `demo123`.

---

## 1. Your desk

**You will:** read the engineering home page.

Log in as Jordan. Your home page shows **Change control** (requests, orders and
notices in flight), approvals under way, and the documents waiting on approval or due
for review.

**Production** > **Processes** lists the routings with their status: *Approved* is in
force; *Draft* is being worked on. A draft can sit beside the approved version it
will replace: that's the normal working state. Open one from its row's edit icon to
see the routing as a flow of steps, with *Pass* / *Fail* branches leaving each
inspection.

---

## 2. Change an approved routing

**You will:** change the `Injector Build` routing the controlled way, from request to
notice.

An approved routing is locked: *This process is locked.* Changes go through change
control so there's a record of what changed, why, and who agreed.

1. Open `Injector Build`. **Process Actions** (⋮) > **Propose Change**. You get an
   editable draft: *Working draft for PCR-… · DRAFT*. (**Duplicate as Template**
   makes a new routing for a new product, with no change trail: not for revisions.)
2. Turn on **Edit Mode**, select **Wash**, and change its description to add a rinse
   and air-dry. **Save**. Only the draft changes; the approved routing is untouched.
3. **Submit for approval**: a title, what's changing, why, and the risk. The
   difference from the approved version is captured with the request.
4. **View PCR** shows the request: what's proposed, the in-flight work orders it
   affects, and the changes.
5. **Approve**. This shop runs change control in *Simplified* mode: anyone with change
   approval can approve with one click, the author included. A shop that needs
   signed approval by someone else runs *Regulated* mode.
6. Approving opens a **change order** (*PCO*). **Implement** it and choose what
   happens to work already running: **keep all in-flight work orders on the old
   version**, **migrate them all**, or **migrate selected ones**, with your reason.
   For a wording change, keep running work where it is.
7. The routing's new version is now the approved one; work already started finishes
   on the old one. A **change notice** (*PCN*) is released. Open it and **Close**
   it with the evidence the change took hold: who was briefed, what was checked.

---

## 3. Define what's measured

**You will:** add a characteristic to a step.

Definitions are edited in the step, inside a change, so they're versioned with it.
**Data Management** > **Measurement Definitions** lists them all, read-only.

1. **Propose Change** on `Injector Build` again. In the draft, select **Wash** >
   **Configure measurements**: Wash already records *Bath Temperature*.
2. **Add Measurement**: **Rinse water conductivity**, numeric, unit `µS/cm`, nominal
   `20`, tolerances `30` above and `20` below nominal (so 0 to 50), **Required**.
   **Create**.

Name a characteristic for the feature, not its place on your drawing, and give it a
unit the operator's instrument reads. If it's pass/fail, make it pass/fail.

---

## 4. Write the instruction

**You will:** put the new check where the operator will meet it.

A defined measurement is only asked for where an instruction captures it.

1. Still on the draft's **Wash**, **Edit substeps**. Wash has *Load bodies into the
   washer* and *Run ultrasonic wash cycle*.
2. **Add substep**. Title it **Rinse and dry** and write the instruction: one action
   per substep, in the order it happens.
3. Add a **Measurement** block and link it to **Rinse water conductivity**: the label,
   limits and unit fill in from the definition. **Save draft**.
4. **Operator view** shows what the operator will see, inputs live.
5. **Back to process flow**, **Submit for approval**, approve and implement as in
   module 2. The new version, with *Rinse and dry*, is the one new work orders are
   built to.

---

## 5. What isn't yours

| Not yours | Whose |
|-----------|-------|
| Release a controlled document | Document controller |
| Decide a disposition or approve a CAPA | QA manager |
| Release work, solve the schedule | Planner, production manager |
| Machine eligibility and changeovers | Planner, production manager |

---

## Final task — observed

Your trainer regenerates the data, logs you in as Jordan, and says only: *"Body
Inspection needs to check the seat for nicks. Make it so."* Then they watch without
helping:

- propose a change to `Injector Build`
- add a required pass/fail characteristic to Body Inspection and a substep that
  captures it
- submit, approve and implement it, with a reason for what happens to running work
- close the change notice with evidence

Your trainer is watching for:

- [ ] You changed the routing through change control, not by duplicating it.
- [ ] The characteristic is named for the feature and captured in a substep.
- [ ] You decided what happens to running work, and said why.

## Recording your qualification

Passing the final task is the assessment. The record is a **training record**, which
your QA manager writes. See [Training Records](../../workflows/quality/training-records.md).
