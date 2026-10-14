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

### Taking over someone else's step

The same shape applies if the step is already assigned to another operator:
taking it over needs a supervisor's authorization and a reason, and the
handover is recorded alongside the competence check. Nothing is changed on the
record unless the authorization succeeds.

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
    Moving between substeps saves what you have entered as a **draft** — on
    *Confirm & next*, *Back*, the progress rail, or *Edit* from the review screen.
    So if the tablet is closed, the battery dies, or the job is handed to the next
    shift, reopening the step brings your entries back.

    Note it saves when you **leave a substep**, not on every keystroke.

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

## Marking a substep N/A

If a substep genuinely does not apply to the part in front of you:

1. Tap **Mark N/A**
2. Choose a reason code

The reason code is required — the dialog will not submit without one — and it stays
in the part's record.

!!! tip "Add a note if the reason code doesn't tell the whole story"
    Notes are optional and the N/A dialog does not ask for one, so if the *why*
    matters beyond the code, put it in the step's notes or a shift note. Nothing
    will prompt you for it.

!!! warning "Some substeps can never be N/A"
    Safety-critical substeps — torque on safety-critical fasteners, witnessed
    signoffs, final dimensional verification — cannot be marked N/A. If you
    can't complete one, raise it with your supervisor rather than working
    around it.

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
    Voiding requires the `void_substepcompletion` permission, held by **QA
    Inspector**, **QA Manager**, and **Tenant Admin**.

    It is deliberately withheld from **Operator**, **Shift Lead**, and
    **Production Manager** — including the operator whose own work is being
    retracted. Performing or supervising the work and adjudicating the record
    are different jobs. The Tenant Admin holds it so a tenant's administrator
    can correct a bad record without first granting themselves the permission
    to do it.

To void one:

1. **Work Orders** > the work order > **Control**
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

## Reman captures

Three substep types exist only for remanufacturing work. They look like any
other capture in the player, but each one writes to the reman records rather
than just recording an answer. If you are tearing down or rebuilding a core, the
work below is how it gets recorded — there is no separate reman screen to go to
afterwards.

### Harvested components — teardown

One row per component you take off the unit:

| Field | |
|-------|---|
| **Component type** | What it is |
| **Condition grade** | A, B, C or Scrap — **your** assessment, at the bench |
| **Position** | Where on the unit it came from |
| **Missing** | Tick when the position was empty |
| **Condition notes**, **original part number** | Optional detail |

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

### Component install — rebuild

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
