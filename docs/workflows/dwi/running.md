# Running Work Instructions

This guide covers the operator's side of Digital Work Instructions — the step
player. See [Digital Work Instructions](overview.md) for the concepts.

## Starting work

1. Navigate to **Production** > **Work Orders**
2. Open your assigned work order
3. Click **Start Work**
4. In the **Start work on parts** dialog, check the parts you'll work on, *in
   the order you'll work them*
5. Confirm

The player opens on the first part you checked. After you complete a part's
step, it moves to the next checked part automatically, so you can work through
a batch without going back to the work order.

## If you're not qualified for the step

Steps can carry training requirements. If you don't hold the training, the
system **stops you** and names what is missing — it does not quietly let the
work proceed and flag it later.

This is a competence control (ISO 9001 **7.2**), and the check runs at the
moment work starts, not when it is signed off.

### A supervisor can authorize you anyway

The gap is not a dead end. A supervisor holding `override_training_gate` — a
Shift Lead or manager tier, deliberately **not** the Operator — can authorize
you to run the step:

1. The supervisor enters **their own email and password** on the override
2. They give a **reason** — the override is rejected without one

The password step is real second-person verification, not a confirmation
dialog: it must be a *different*, active user, and repeated failures are
throttled. You cannot clear your own competency gap.

!!! note "The override is recorded on the work, permanently"
    The authorization is written onto the step execution itself and stays with
    the record: **what training was missing**, **who was authorized**, **who
    authorized it**, **the reason**, and **when**.

    That snapshot is the audit answer to "who did this work and were they
    qualified?" long after the shift. An override is a legitimate, recorded
    business decision — it is not a way to make the requirement disappear, and
    a reviewer will see every one of them.

    It shows on the **part's traveller** (work order control page → the part's
    history), as an amber line under the step it was used on.

    To review every override over a period, open **Training Overrides** from the
    Training dashboard's Quick Actions (`/quality/training/overrides`). It lists
    when, who worked, who authorised, the step and part, the missing training
    and the reason, for a date range (the last 30 days by default). It needs
    `view_auditlog`, held by default by QA Manager, Document Controller, Auditor
    and Tenant Admin.

### Taking over someone else's step

The same shape applies if the step is already assigned to another operator:
taking it over needs a supervisor's authorization and a reason, and the
handover is recorded alongside the competence check. Nothing is changed on the
record unless the authorization succeeds. A supervisor can also move the step
to you directly — see [Picking work back up](#picking-work-back-up).

## Batch steps: running a load

Some steps act on a whole load at once — a wash basket, an oven, a bar-fed lathe
running out a batch. A step like that shows a **Batch step** panel above its
instructions, counting the loads open for this work order — *N loading · N
running*:

*"Parts advance by load. Load the units going through this op together and do
the loading checks, then seal: the machine runs and you can leave it. Come back
to finish the load's checks and complete it. Each completed load moves on
independently."*

A load has three phases:

1. **Loading.** **Start a load — select its units**: tick the units going in and
   **Start load**. A held unit is greyed out and can't be loaded. Then do the
   **Loading checks — captured once for the whole load** and **Confirm for
   batch**.
2. **Running.** The load seals at the point the instruction says — the panel
   tells you which: *Confirming “Start the wash cycle” seals the load.* —
   and confirming it reads *Captured "Start the wash cycle": the load is sealed
   and running.* Where no substep is marked, **Seal load** after the last
   loading check does it: *Load sealed: the machine runs.* A sealed load can't
   take more units or change its loading checks. You can leave it; it stays in
   your open work as *Load · N parts · Running · sealed … ago*.
3. **Completing.** When the run is done, come back to the load (**Resume**, or
   **Continue work** on the work order), do the **Completion checks — once the
   run is done, before Complete load**, **Confirm for batch**, then **Complete
   load**: *Load complete: its parts move on.*

**The parts move on only when the load is completed** — never at seal, so
nothing reaches the next step mid-run. Asking for it early is refused: *"The load
isn't complete yet"*, naming the check still missing.

Completing the load finishes the step for its parts, but a part still moves on
with the rest of its lot. If some can't yet — a lot-mate is on hold, say — you're
told which and why: *"Load complete, but its parts didn't move: Done at Cleaning —
the lot waits for CORE-240212-0009 (on hold). Split it from the lot to let the rest
move."*, or *"Load complete: N moved on, M waiting"* when some did.

Each check is recorded once, for the load. A confirmed check shows **Captured**
with its value, and what you enter is kept as a draft in each phase the same way
as part-by-part work.

The panel shows only the open loads. Loads already completed for this work order
sit behind **Show N completed loads** (read-only, **Hide completed loads** to
fold them away); with nothing open it says *No load open at this step for this
work order.*

### Correcting what's in the load

Until the parts' step is completed — while the load is loading **or** running —
what's in the load can be put right, with no reason asked:

- Each part in an open load shows as a chip. **×** on a chip takes it out —
  *"Take it out of the load — it wasn't put in"* — and it waits at the step for a
  load of its own: *Taken out of the load*. The load's only part has no ×.
- **Add parts** lists the other units at the step on this work order that aren't
  held and aren't in another open load: *"In the basket but not on the load? Tick
  them. They ride this load's cycle."* **Add N to the load** puts them in, and
  they carry the load's checks: *Added to the load*. It isn't shown when there's
  nothing to add.

Each change is listed under the chips — *"INJ-OPS-014 taken out by Mike Rodriguez
· …"*, *"… added by …"* — and kept in the record. Once the parts' step is
completed the load is final; taking a part out after that is a correction on the
part's traveller (**Take this part out**, with a reason), and it rolls the part
back to the step.

### Discarding a load

A load started by mistake can be thrown away while it's still **loading** —
never once it's sealed. **Discard load** on its row asks *"Discard this load?"*:

- **Discard load** — its parts go back to the step, unloaded, ready for a new
  load, and anything captured for it is voided: *Load discarded: its parts are
  back at the step*. You stay on the step.
- **Discard and release the parts** — the same, and the parts' steps go back to
  the queue, unassigned and not started, as if nobody had picked them up: *Load
  discarded and its parts released to the queue*. You're taken home.

The discarded load is kept, archived, with who discarded it and when.

!!! warning "A failed completion check holds the whole load"
    A completion check out of limits — a bath that ran hot — fails the cycle,
    and every unit in the load that is still in production is quarantined
    together, with one disposition opened for the batch. See [A whole load
    quarantined at once](../quality/quarantine.md#a-whole-load-quarantined-at-once).

## Picking work back up

A step you started and haven't finished stays yours, with its entries saved,
until you complete it or a supervisor moves it.

**Resume** is only for work you **started and haven't finished**:

- a step you started whose substeps aren't all done, and
- a load you're working that isn't completed — loading, or running
  (*Load · N parts · Running · sealed … ago*).

Steps assigned to you but not started, the Ship step, and steps where your part
is done and the step is **waiting on someone else** — QA's buy-off, an approval,
a disposition, a hold — aren't in it. Those are counted instead, under the
button: *"7 of yours done and waiting: 4 on QA or an approval · 3 on a
disposition."* A part that's in a load shows as the load, not on its own.

The **In progress** tile names the most recent unfinished item — *"Nozzle
Inspection · INJ-SHOWCASE-001 · Running · started 18 minutes ago · +2 more to
finish"*. **Resume** goes straight back when there's one; with several, it opens
**Pick up where you left off**: *your unfinished steps and loads*, most recently
started first, each with its step, the part (or *Load · N parts*), the work
order, how long ago, and how far it got — *2 of 3 done* counts substeps confirmed
or drafted. Pick one; it opens at its first substep not yet done. With nothing
left: *"Nothing left unfinished. Scan a traveler to start work."*

On a work order, **Continue work (N)** — beside **Start Work**, shown only when
you have unfinished work on that order — opens the same list narrowed to it,
titled **Continue work on this order**. That is the way back after leaving a
job part-way: go to its traveller and carry on.

**A load goes with its parts.** It belongs to whoever holds its parts' steps, and
when they change hands — taken over through Start Work's supervisor override, or
by a supervisor below — the whole load moves together.

### Supervisors: taking over and handing off

A **Shift Lead**, **Production Manager**, **QA Manager** or **QA Inspector**
(and Tenant Admin) holds `reassign_stepexecution`. Their home page has a **Work
in progress** card — *"Steps and loads started across the plant and not yet
finished. Take one over, or hand it to someone."* — with **Work in progress
(N)**, which opens the list for the whole plant, and an amber **Off the clock
(N)**, which opens it narrowed to work whose holder isn't clocked in. On a break
or at lunch counts as on the clock.

In the list they can switch between **Mine** and **Everyone's**: each row on
Everyone's shows who holds it, and an amber **Off the clock** badge when that
person isn't clocked in. **Off the clock only** narrows the list to those. A
work order's **Continue work** shows for a supervisor whenever anyone has work
open on it, and opens on Everyone's when none of it is theirs.

Under someone else's step:

- **Take over** — *Take over this step*: give a reason (**Why**), and it is
  yours, with its progress.
- **Hand off…** — *Hand off this step*: pick who it goes to (**Hand to**) and
  say why. It then appears in their own list. **Hand to** lists staff who can
  work steps, those trained for it first — *"Dave Wilson — trained · at this
  station"*, *"… not trained for this step"*.

No second person signs: the supervisor is the one signed in, and the record
keeps who it moved from and to, who moved it, why, and when. A load row has the
same **Take over** and **Hand off…**, and moves as one — the dialog says *load of
N parts, all moving together*.

!!! important "Whoever ends up holding the step must be trained for it"
    A supervisor who isn't trained for the step can't take it over — *"You
    aren't trained for this step (missing: &lt;training&gt;). A second person
    can authorize you through Start Work's supervisor override."* Handing it to
    an untrained operator records the supervisor's own [training
    override](#a-supervisor-can-authorize-you-anyway); a QA Inspector, who
    doesn't hold that override, can only hand a step to someone already
    trained.

## The player

The player shows **one substep at a time**, with a progress rail across the top
showing which substeps are done, which is current, and which are still ahead.

For each substep:

1. Read the instruction and do the work
2. Record whatever the substep asks for — a measurement, a photo, a scan, a
   signature
3. Tap **Confirm & next**

Your entry is saved when you move off it, and the player advances.

!!! tip "Your work is saved as you go"
    What you enter is saved as a **draft** as you work — a moment after you stop
    typing, and whenever you move between substeps, leave the step for any other
    page, switch away from the tab or close it, or log out. So if the tablet is
    closed, the battery dies, or the job is handed to the next shift, reopening
    the step brings your entries back.

    Reopening it lands on the **first substep not yet done**, not necessarily
    the one you were last on — so nothing earlier is skipped.

    Only whoever holds the step can save to it. If it has been handed to someone
    else while you still have it open, you're told: *"Your entries aren't being
    saved — This step is now &lt;name&gt;'s. What you entered here wasn't
    saved."*

!!! warning "A draft is not a record — Complete step is"
    Nothing is official until you tap **Complete step**. That is what writes the
    captures, and only then can a failed measurement raise a report or hold the
    unit. A value you fix before completing the step never becomes a
    nonconformance.

    It also means an unfinished step records nothing. If you want the work on the
    record, finish the step.

!!! warning "You can only sign as yourself"
    A signature substep records **you**, taken from your session rather than
    from anything the tablet sends. The time is the server's at the moment the
    signature is written, not the tablet's clock.

    Trying to sign in someone else's name is refused outright: *"You can only
    sign as yourself."* So a signature cannot be collected on a colleague's
    behalf — if a step needs a QA buy-off, that person signs it on the device.

    Two consequences worth knowing at the bench:

    - **Re-saving a step does not re-stamp your signature.** Sign, go back,
      change something else, complete the step: your signature keeps the time
      you actually signed.
    - **Somebody else's signature survives your edit.** A QA sign-off already
      in the step is carried through unchanged when you save, so an operator
      re-saving a step cannot wipe the inspector's slot — or quietly take it
      over.

## Signing a block

Some blocks ask you to sign rather than tick. You sign them **as you work through
the substep**, not at the end: draw your signature, then enter **your own**
password. What you signed for is the block's label, and the time is the server's.

- **Wrong password** — the prompt comes back with your drawing still there; only
  the password is cleared.
- **Too many wrong passwords** — signing locks for 15 minutes. Ask a lead.
- **Cancel** — nothing is recorded, and the block stays unsigned.

### Undoing a signature

A signature is provisional until you submit the substep, so **Undo signature**
clears it and you can sign again. That is for the ordinary case of signing the
wrong block or the wrong unit.

Once the substep is submitted the signature stands. From there only QA can retract
it, by voiding the completion with a reason — which re-opens the substep and asks
for a fresh signature.

!!! note "If someone signs and goes off shift"
    A supervisor can clear another person's signature while the substep is still
    unsubmitted, so the work isn't stuck waiting for someone who has gone home.
    They cannot touch a signature once it has been submitted.

You can't complete a substep while one of its signature blocks is unsigned — it
tells you which one.

## A substep you can't do

Every substep you're shown is one the author requires, unless it's marked
**optional**. If you genuinely can't perform a required one, stop and raise it
with your supervisor or whoever authored the step. There is no skip.

## Finishing the step

After the last substep you get a **review screen** listing everything you
recorded. Tap any entry to jump back and correct it.

When it's right, tap **Complete step**.

This is the last easy place to fix a mistyped measurement, so it's worth the
few seconds to read down the list.

## Voiding a completion

Sometimes a substep was completed in good faith but the record is wrong — the
gauge turns out to have been out of calibration, the wrong test method was
used, a value was miscalculated. The completion can be **voided** after the
fact.

!!! info "Who can void"
    Voiding requires the `void_substepcompletion` permission, by default held by **QA
    Inspector**, **QA Manager**, and **Tenant Admin**.

    It is deliberately left out of the default **Operator**, **Shift Lead**, and
    **Production Manager** groups — including the operator whose own work is being
    retracted. Performing or supervising the work and adjudicating the record
    are different jobs. The Tenant Admin holds it so a tenant's administrator
    can correct a bad record without first granting themselves the permission
    to do it.

To void one:

1. Open the work order's control page: **View in Control Center →** on the work
   order's **Overview** tab, or click its row in **Production** > **WO Control
   Center**
2. Expand the part in the parts list — the chevron at the far left of the row,
   not the checkbox
3. In the **Traveler** table, find the step and expand **Checks (N)** in the
   last column
4. Click **Void** on the wrong record and give a **reason** — the void is
   rejected without one

!!! tip "No Checks control means nothing was recorded"
    A step only shows **Checks** if something was actually recorded there.
    Its absence means no completion exists at that step — *not* that you lack
    permission to see one. Users who cannot void still see the rows; they just
    get no Void button.

### Per-part work and shared cycles

The list holds two different kinds of record, and the difference decides how
far a void reaches.

| Kind | Covers | A void affects |
|------|--------|----------------|
| **Per-part** | One operator's work on one part | That part only |
| **Shared cycle** | A batch the part rode through — ultrasonic wash, heat treat, plating | **Every part in the load** |

!!! danger "Voiding a shared cycle retracts it for every part in the load"
    Shared-cycle records are grouped under a header that says so — *"shared by
    6 parts — voiding affects all of them"* — and the confirmation dialog
    repeats the count.

    Read it before confirming. You opened one part's traveler, but the record
    you are retracting belongs to the whole load: void the wash cycle and all
    six parts lose it, and all six block until the cycle is redone. This is
    usually correct — one bad wash cycle really does invalidate everything in
    the tank — but it is not a per-part fix and must not be used as one.

### Rework and visits

A traveler row is per **step**, not per attempt, so a part that has been
reworked has several executions collapsed into one row. Per-part completions
are grouped by execution and labelled **Visit #1**, **Visit #2** when there is
more than one.

Check the visit before voiding — voiding a completion from the wrong visit
retracts the wrong attempt.

### What voiding does

!!! warning "The part blocks — and so does its lot"
    A voided completion no longer satisfies its substep. The advancement gate
    ignores it, so the part stops at that step until the work is redone and a
    fresh completion lands.

    Because unsplit parts advance as a cohort, that **holds the whole lot**.
    The operator-facing symptom is "my lot has stopped moving". If a lot stalls
    with no obvious blocker, check the traveler for a voided check.

On a step running in **sequential** mode, voiding an earlier substep blocks that
substep only. Sequencing is checked when a capture is *written*, so it stops you
recording substep 3 before substep 2 — it does not retract substep 3 once it
exists. Completions already made further down the step stay valid, and only the
voided one has to be redone.

!!! note "Voiding retracts and annotates; it never removes"
    A voided completion stays in the list, struck through, showing **who voided
    it, when, and the reason**. The collapsed traveler row carries a red
    **"N voided"** badge, so retracted work is visible without expanding every
    step. An already-voided row offers no Void button.

    Retracting a record is itself a recorded event. Nothing is deleted.

### Capturing it again

A part with a voided completion is redone at that step: start it again with
**Start Work** and capture what was voided. This works even when the part is
**quarantined** because of the voided result, since that re-capture is the one
piece of work a held part may take. If the person who did the work isn't the one
to redo it, a lead reassigns it the usual way. The new capture is a new record; the
voided one stays beside it.

**An inspection result** is the same, with its report:

- Voiding the capture **supersedes** its quality report. The report is kept,
  marked superseded, with the void's reason, and the re-capture records a **new**
  report.
- If the voided result was a **FAIL** that opened a disposition, re-inspecting does
  not close it. The part stays held until the disposition is decided. When the
  finding was simply wrong and the new result is a PASS, a QA manager (not the
  inspector who recorded or voided it) closes it as **Not a nonconformance** —
  see [Dispositions](../quality/dispositions.md#when-the-finding-was-wrong-not-a-nonconformance).

**The wrong part:** a capture recorded against the wrong unit is voided on that
unit, and captured on the right one.

## Reman captures

Three substep types exist only for remanufacturing work. They look like any
other capture in the player, but each one writes to the reman records rather
than just recording an answer. If you are tearing down or rebuilding a core, the
work below is how it gets recorded — there is no separate reman screen to go to
afterwards.

### Harvested components — teardown

One row per component the unit should give up, already listed:

| Field | |
|-------|---|
| Component and position | Filled in from what the unit should give up. One you didn't expect is added with **Found something unexpected?** |
| **Grade** | A, B, C or Scrap — **your** assessment, at the bench |
| **Missing** | Switch on when the position was empty |
| **Notes** | Optional detail |

Submitting creates the harvested component records, and anything graded **Scrap**
is scrapped in the same action — you do not scrap it separately afterwards.

The grade you give here is what the rebuild plan resolves against, so it decides
whether the part goes back in, gets reconditioned, or has to be replaced. See
[Harvested Components](../reman/components.md).

!!! warning "Missing is a real answer — record it"
    Tick **Missing** rather than leaving a position blank. A blank says nothing;
    *missing* says someone looked.

    If the capture was authored in **strict** mode, this is enforced: every row
    on the disassembly BOM must be accounted for before the step completes, and
    it is checked server-side. Strict is opt-in per capture, so not every
    teardown will hold you to it — record it properly either way.

### Components installed — rebuild

One row per slot, naming what you actually fitted:

- **the unit's own component**, back into the unit it came out of, or
- **a recovered part from stock** — exchange rebuilds only. A repair-and-return
  unit is refused anyone else's part.

**Purchased replacements are not recorded here.** A bought component is drawn
from its lot by material consumption when the step completes, which is already
its traceability.

!!! note "The capture is all or nothing"
    A slot that cannot be installed fails the whole submission rather than
    leaving the unit half-recorded. Fix the row it names and submit again.

### Rebuild finding — rebuild

For a component that turns out **worse than teardown graded it**. You propose a
new grade and say what you found; a lead applies or dismisses it.

You are not changing the plan yourself — applying a finding re-grades the
component and re-resolves the rebuild plan from it, which is a decision that
belongs to whoever owns the scope. See [the findings
section](../reman/components.md#findings-a-component-found-worse-at-the-bench).

Four things it will refuse:

| Refusal | Why |
|---------|-----|
| *"Say what was found — a finding with no description can't be judged."* | A grade with no evidence isn't actionable |
| *"… is already scrapped."* | Nothing left to re-grade |
| *"… already has a finding waiting on a lead's decision"* | One at a time; the first must be applied or dismissed |
| *"… is already grade X; a finding proposes a different grade."* | A finding is a *change* |

Findings are recorded per row and the whole capture is one transaction, so one
bad row rejects the submission and names its position.

## What happens next

Completing the step is the event that lets the part advance. If the step's
requirements are satisfied, the part moves on by itself and the player takes you
to your next checked part.

If the part doesn't move, it's for one of these reasons:

| Reason | What to do |
|--------|------------|
| A required capture is missing or incomplete | The review screen shows which |
| The step's First Piece Inspection is still pending | Wait for the buy-off |
| **Another part in the lot still has work outstanding** | Normal — see below |
| You don't have training for the step | Raise with your supervisor |
| The part is quarantined | Disposition decides what happens next |

!!! note "Parts move as a lot"
    Parts that haven't been split advance **together** — all parts at the same
    work order and step, or none of them. So your part can be finished and still
    not move, because a different part in the same lot isn't done. That is
    normal, not a fault.

!!! warning "First Piece Inspection holds the whole step"
    If the step's FPI hasn't been signed off, no part at that step advances.
    **Complete step** stays where it is — it is what commits your captures, and the
    buy-off is refused until they are in. A separate **Sign off first piece** /
    **Get QA sign-off** button appears beside it once the first piece is ready, for
    whoever is authorised to sign.

## When the terminal or scanner is down

**There is no offline mode.** The player needs the server, so if the tablet,
network or scanner is out, work does not stop — the **paper traveller** does.

Print the traveller for the work order before you need it. It carries, per
operation, **Operator / Date**, **Inspector / Date**, **Acc**, **Rej** and
**Remarks** write-in columns, a **Sign-off Key** for initials, and the header
barcode.

!!! important "Paper is a fallback, not a second record"
    The traveller says so itself: *"The digital work order is the system of
    record"*, and *"paper sign-offs are a fallback; the authoritative sign-off is
    the digital one."*

    So the paper does not replace the record — it **holds** it until someone can
    enter it.

### Catching up afterwards

1. Scan the header barcode, or type the work order, to get back to the job
2. Work each substep as normal, entering the values from the sheet
3. Note on the sheet who signed each operation — the Sign-off Key initials are
   the record of that, and the paper stays in the binder

!!! warning "A catch-up is stamped with YOU and with NOW — it cannot be backdated"
    Every entry records **the person typing it** and **the moment it is typed**.
    You cannot enter a substep under a colleague's name, and you cannot record
    Tuesday's date for work done on Tuesday: `completed_by` is always the signed-in
    user and `completed_at` is set by the server as the row is written.

    So a catch-up traveller will legitimately disagree with the binder on both
    names and times, and an auditor will see both. **That is why the paper is the
    record of who did the work and when** — keep the sheet, reference it in the
    notes, and do not expect the digital entry to reproduce it.

    If attribution matters for a particular operation — a witnessed sign-off, a
    QA buy-off — have **that person** enter it themselves rather than catching it
    up on their behalf.

!!! tip "Scanning still works on paper"
    The header carries the work-order barcode precisely so the sheet can take
    you back to the right job without typing. See
    [Scanning](../supply/locations.md#scanning).

## Next Steps

- **[Digital Work Instructions](overview.md)** - Concepts
- **[Moving Parts Forward](../tracking/moving-parts.md)** - How advancement works
- **[Operator Guide](../../roles/operator.md)** - Your role guide
