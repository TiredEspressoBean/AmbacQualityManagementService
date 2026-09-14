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
