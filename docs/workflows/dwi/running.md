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

Your entry is sealed when you confirm it, and the player advances.

!!! tip "Your work is saved as you go"
    Each substep is sealed on confirm rather than at the end. If the tablet is
    closed, the battery dies, or the job is handed to the next shift, reopening
    the step resumes where you left off — the URL carries your position.

## Marking a substep N/A

If a substep genuinely does not apply to the part in front of you:

1. Tap **Mark N/A**
2. Choose a reason code
3. Add a note explaining why

Both the reason and the note are required, and both stay in the part's record.

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

On a step running in **sequential** mode, voiding an earlier substep also
re-blocks the substeps after it — the work downstream of the retracted record
has to be redone too, in order.

!!! note "Voiding retracts and annotates; it never removes"
    A voided completion stays in the list, struck through, showing **who voided
    it, when, and the reason**. The collapsed traveler row carries a red
    **"N voided"** badge, so retracted work is visible without expanding every
    step. An already-voided row offers no Void button.

    Retracting a record is itself a recorded event. Nothing is deleted.

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
    **Complete step** becomes the buy-off action for whoever is authorised to
    sign it.

## Next Steps

- **[Digital Work Instructions](overview.md)** - Concepts
- **[Moving Parts Forward](../tracking/moving-parts.md)** - How advancement works
- **[Operator Guide](../../roles/operator.md)** - Your role guide
