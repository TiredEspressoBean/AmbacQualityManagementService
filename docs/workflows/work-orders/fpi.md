# First Piece Inspection (FPI)

First Piece Inspection ensures production setup is correct before running full batches. This guide covers FPI workflow in uqmes.

## What is First Piece Inspection?

FPI (also called First Article Inspection at setup level) is a quality check on
the **first part** produced at a step, bought off by QA before the rest of the
run may proceed. It is what catches a bad setup on part one instead of part
two hundred.

A step either requires it or it doesn't — the requirement is a setting on the
step, not something a tool change or a shift handover raises on its own. The
step's [FPI scope](#fpi-scope) decides how far one buy-off reaches: the whole
work order, one shift day, or one machine.

## Enabling FPI

FPI is configured per process step:

1. Open the process in the **Process Flow** editor and turn on **Edit Mode**
2. Click the step, then open **Advanced**
3. Enable **Requires first-piece inspection**
4. Set the **FPI scope** — when the requirement resets

See [Step Configuration](../../admin/processes/steps.md).

When enabled, the first part at that step triggers FPI workflow.

### FPI scope

The scope decides what one passed or waived first piece releases. Each scope is a
real gate: a part at the step is held until a first piece **for its context** is
passed or waived.

| Scope | One buy-off releases | A part is held when |
|-------|----------------------|---------------------|
| **Per Work Order** | The step for the whole work order | No first piece at the step on the work order has passed or been waived |
| **Per Shift** | The step for one shift day on the work order, keyed by the shop-floor date | Today's shift has no passed or waived first piece. A pass on another day does not release today's run |
| **Per Equipment** | The step for one machine on the work order | The machine it runs on has no passed or waived first piece. A pass on another machine does not release this one |

Under **Per Equipment** the machine is the production machine on the part's visit
to the step — taken from the machine authored on the step or from the live
schedule, or set by the operator. A part with **no machine recorded is held**:
nothing says which first piece covers it. Record the machine, then start the FPI.

The context shows wherever the first piece does. The blocker on a held part reads
*First Piece Inspection required for <machine>: PENDING* (or *…for the
<date> shift…*), and the banner, control-page cards and QA home name the
machine or shift the first piece is for.

## FPI Workflow

You meet FPI in three places. In the operator's step runtime, a banner that
changes with the inspection's state (below). On the work order's **control**
page, a *First piece waiting on QA* card for each pending first piece (titled
with the step and, under a narrower scope, its context — *<step> for the <date>
shift*), a *First piece failed at <step> for <machine> — run held* card for a
held step, and — for people who can sign off a first piece — a *First piece
waived at <step>* row for each waiver. On QA home, a *First piece waiting —
<step> for <machine>* banner whose **Start check** opens the control page. A quality report also
carries a **First Piece Inspection (FPI)** flag; it is set when a first piece
passes, or ticked by hand on the report form, and nothing waits on it.

!!! warning "There is no 'submit for FPI review' step"
    Nothing is submitted and nothing queues for review. The first piece becomes
    ready for buy-off by **finishing its own captures** — the same Complete step
    the operator would do anyway. QA then signs it off.

| State | What it says | What you can do |
|-------|--------------|-----------------|
| **Required** — no record yet | *First Piece Inspection Required* (with the context under a narrower scope — *…Required for <machine>*) | **Start FPI** — designates the first piece and holds the run |
| **Machine not recorded** — Per Equipment step | *First Piece Inspection Required — machine not recorded*: *This step needs a first piece per machine. Record the machine this part runs on, then start the FPI.* | Record the machine first; **Start FPI** is not offered until then |
| **In progress** — first piece not finished | *First Piece Inspection in progress* | Nothing yet. Complete the first piece's captures; no buy-off is possible until they are in |
| **Ready for buy-off** | *First piece complete — ready for buy-off* | **Sign off & pass**, **Fail**, or **Waive** — if you hold `sign_off_fpi`. Everyone else sees *awaiting buy-off* and a **Get QA sign-off** button |
| **Satisfied** | Green — run released (*…signed off*, or *…waived* — both with the context, e.g. *…signed off for the <date> shift*) | Parts move. A sign-off holder can **Void pass** after a pass, or **Start a new first piece** after a waiver |

**Start FPI** is refused, with the reason shown, when the machine isn't recorded
on a Per Equipment step (*This step needs a first piece per machine, and the
machine this part runs on isn't recorded. Set the machine, then start the FPI.*)
or when no part of the context is at the step yet (*No part has reached this step
yet — start the FPI from a part at the step.*).

### Signing off

**Sign off & pass** opens a dialog that states what you are attesting to: the
setup is correct, the first piece conforms, and this releases the run. Above the
notes it lists the **first piece's readings**: each characteristic, the reading,
its limits, and who took it and when. Those readings are what you are signing.

- **Notes** are optional — gauges used, observations.
- If the step is authored to need a **verified** signature, you re-enter **your
  own** password.

!!! warning "You can't buy off a first piece you signed"
    The buy-off is a second person's judgement. If you signed any of the first
    piece's inspection, the dialog says so before you can confirm, and switches
    to a second inspector's sign-in: they enter their email, signature and
    password at your screen. The buy-off is recorded under **their** name, with
    you as the person at the station. The same applies to **Fail** and
    **Waive**.

!!! tip "An operator does not have to go and find QA"
    If you lack `sign_off_fpi`, the button reads **Get QA sign-off** and opens
    the same dialog with a co-sign section. An authorized inspector enters their
    **email and password at your station** — you stay logged in, and the record
    carries **their** name as the authority, not yours.

**Fail** needs a reason, and does three things:

- The first piece gets a FAIL quality report, with your reason as its
  description. It is **quarantined**, and a disposition opens for it, unassigned,
  in the QA queue (see [Dispositions](../quality/dispositions.md#where-a-disposition-comes-from)).
- The run stays held. The work order's control page shows **First piece failed
  at *step* — run held**, with who failed it and the reason.
- **Start a new first piece** on that card raises the next inspection. Correct
  the setup first; the new first piece is bought off like the first.

**Waive** releases the run without a first-piece verification. It needs a reason
of at least 10 characters, and the waiver records who, when and why.

### A first piece passed in error

Found after the buy-off that the first piece shouldn't have passed (the wrong gauge,
a reading misread)? Anyone who can sign off FPIs can **Void pass** on the FPI
banner, with a required reason:

- The pass stays on record, marked **Voided** with your reason. It is not deleted.
- The step's release is withdrawn, and a **new first-piece inspection** opens.
  Parts not yet past the step wait until the piece is re-inspected and bought off.
- Parts already past the step are **not** pulled back. If they need looking at,
  that is a quality decision about them, made separately.

A passed first piece is corrected only this way. **Start FPI** after a pass is
refused: *The first piece has passed. If the pass was given in error, void it;
that opens the re-inspection.* A fail needs no correcting — it already holds the
run, and **Start a new first piece** on its card is the recovery.

### A waiver given in error

A waiver is corrected by a **new first piece**. After a waiver the runtime banner
is green, titled *First Piece Inspection waived*, with *Released without a
first-piece buy-off — parts can proceed through this step.* People who can sign
off a first piece see **Start a new first piece** there, and on the work order's
control page a row *First piece waived at <step> — "<reason>"* with the same
button. The dialog says what follows:

> The waiver stays on record, marked superseded. The run holds until the new
> first piece is passed or waived. Parts already past this step are not pulled
> back.

- The waiver's status becomes **Superseded**. Who waived it, when and why are kept.
- A new first piece opens, and the run holds — for the waiver's context under a
  narrower scope — until it is passed or waived.
- Parts already past the step are **not** pulled back.

The control page confirms with *New first piece started — the waiver is marked
superseded.* Only someone who can sign off a first piece can replace a waiver.

### Conditional Pass

!!! note "Planned Feature — do not look for it"
    Conditional Pass exists as a value the record *could* hold, but **nothing
    writes it**. Pass and fail each set their own result outright, and the only
    outcomes you can record today are **pass**, **fail**, **waive** and
    **acknowledge**.

    If a setup is acceptable to run but something should be re-checked, pass it
    and say so in the notes.

## FPI Status Indicators

| Status | Meaning | Icon |
|--------|---------|------|
| **Not Required** | FPI not enabled for this step | — |
| **Pending** | First piece not yet bought off | Amber |
| **Passed** | FPI approved, batch released | Green |
| **Failed** | FPI rejected, setup adjustment needed | Red |
| **Waived** | Released without first-piece verification, with a reason | Green |
| **Superseded** | A waiver replaced by a new first piece; it releases nothing | — |

### Acknowledging

A QA inspector can **acknowledge** a pending FPI — an "I'm on it" against the
record, so the floor can see the call has been picked up. It is not a verdict
and it does not release anything; the buy-off still has to be made. It needs
`sign_off_fpi`.

### Waiving FPI

In some cases, FPI can be waived:

1. Click the **Waive** button on the FPI banner
2. Enter a reason (minimum 10 characters)
3. Confirm the waiver

Parts are released without first piece verification.

Waivers are logged with:
- Who waived
- When waived
- Reason for waiver

Use sparingly - FPI catches setup errors early. A waiver given in error is
corrected by a new first piece — see
[A waiver given in error](#a-waiver-given-in-error).

## Viewing FPI Status

The work order's control page shows a card for each step (and, under a narrower
scope, each shift day or machine) whose first piece is waiting on QA or has
failed. Once passed, nothing is shown there. A waived first piece shows as a row,
with **Start a new first piece**, to people who can sign off a first piece.

## What the first piece is inspected against

There is no separate FPI measurement form. The first piece is inspected by
**running the step's own work instruction** — its measurement captures, checks
and sign-off blocks are the inspection. That is why the buy-off is refused until
the captures are in: there would be nothing to review.

If a step needs inspection points beyond what the operator records, author them
into the step's substeps. See
[Authoring Work Instructions](../dwi/authoring.md).

## FPI Documentation

The FPI record itself is thin, because the inspection evidence lives on the
step, not on it:

| On the FPI record | On the step execution |
|-------------------|------------------------|
| Work order, step, part type | **The measurements** and every other capture |
| The **designated part** | Photos and scans taken during the work |
| Equipment and shift date (for the scoped variants) | The operator's own sign-offs |
| Status, result, notes | |
| Who acknowledged it, and when | |
| Who bought it off, and when — or who waived it, with the reason | |
| The co-signer's drawn signature, where it was co-signed | |

So "show me the first-piece inspection" means the record **and** the designated
part's traveler for that step. The record tells you it was bought off and by
whom; the step tells you what was actually measured.

!!! note "The drawing is kept only when it is co-signed"
    A co-signing inspector draws a signature at the operator's station, and it
    is stored on the record once their email and password verify. A buy-off from
    the inspector's own session asks for no drawing. What identifies the signer
    in both cases is the re-authentication plus `inspected_by` and
    `inspected_at`.

## Batch Hold During FPI

While FPI is pending:

- Other parts at that step are held — under Per Shift or Per Equipment, the
  parts of that shift day or machine
- Cannot proceed to next step
- The banner and control-page card say the run is held

After FPI passes:

- The held parts it covers are released
- Can proceed normally
- Batch production continues

## Failed FPI Handling

When FPI fails:

1. **First piece** enters quality workflow (possibly quarantine)
2. **Operator** notified to adjust
3. **Remaining parts** stay held
4. **New first piece** produced after adjustment
5. **Repeat FPI** on new first piece

!!! note "Nothing counts the failures for you"
    Each failure is recorded and emits an `fpi.decided` event, but no escalation
    is built in — nothing notifies on the second failure or places a hold on the
    third. Repeated failures are a judgement someone makes from the record.

    If you want to be told, that is a [notification
    rule](../../admin/setup/notification-rules.md) on `fpi.decided`. The hold, if one
    is warranted, is still placed by hand.

## FPI Metrics

There are no FPI metrics. Each record keeps its status, who bought it off and
when, so a pass rate can be worked out from the records.

## FPI vs FAI

| Concept | Scope | Timing |
|---------|-------|--------|
| **FPI** | Setup verification | Each production run |
| **FAI** | Full design validation | New part number, first production |

FPI is routine; FAI is comprehensive qualification.

## Permissions

| Permission | Allows |
|------------|--------|
| `view_fpirecord` | See FPI status and records |
| `add_fpirecord` | Start an FPI — designate the first piece |
| `sign_off_fpi` | Pass, fail, waive or acknowledge. Co-signable at another user's station. |

!!! note "Recording the verdict is not `add_fpirecord`"
    The record already exists by the time anyone signs — **Start FPI** created
    it. The buy-off is gated on `sign_off_fpi` alone, which is what makes it an
    independent authority rather than a continuation of the operator's work.

## Next Steps

- [Recording Measurements](../tracking/measurements.md) - Measurement capture
- [Quality Reports](../quality/quality-reports.md) - Handling failures
- [Process Configuration](../../admin/processes/overview.md) - Configure FPI
