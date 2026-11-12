# First Piece Inspection (FPI)

First Piece Inspection ensures production setup is correct before running full batches. This guide covers FPI workflow in uqmes.

## What is First Piece Inspection?

FPI (also called First Article Inspection at setup level) is a quality check on
the **first parts** made at a step, bought off by QA before the rest of the run
may start. It is what catches a bad setup on part one instead of part two
hundred.

The first piece is the first **N** parts started at the step, where N is the
gate's **Pieces in the first piece**: 1 for most steps, or one per nest on a
fixture that makes several parts per cycle. Until QA buys it off, **only those
parts may start**. Every other part is refused at **Start Work**, so nothing
beyond the first piece is made on an unverified setup.

A step either requires it or it doesn't. The requirement is a gate on the step.
The gate's [First piece covers](#what-one-first-piece-covers) setting decides how
far one buy-off reaches: the whole work order, one shift, or one machine. A
tool change, an offset adjustment, a crash or a repair re-opens it only when
someone [declares a new setup](#a-new-setup).

## Enabling FPI

FPI is configured per process step:

1. Open the process in the **Process Flow** editor and turn on **Edit Mode**
2. Click the step, then open **Advanced**
3. Under **Gates**, **Add a gate** › **First piece**
4. Set **First piece covers**: what one first piece releases
5. Set **Pieces in the first piece**: *"The first parts started make up the
   first piece — one per fixture nest. Until QA buys it off, only these may
   start."*
6. Set **How the inspector signs the buy-off**

See [Gates](../../admin/processes/steps.md#gates).

### What one first piece covers

This setting decides what one passed or waived first piece releases. A part
can't start at the step until a first piece **for its context** is passed or
waived, unless it is one of that first piece's own parts.

| Covers | One buy-off releases | Work can't start when |
|-------|----------------------|---------------------|
| **Per work order** | The step for the whole work order | No first piece at the step on the work order has passed or been waived |
| **Per shift** | The step for one run of a shift on the work order: Day and Night on the same date are separate | The shift the part starts in has no passed or waived first piece. A pass on another shift does not release this one |
| **Per machine** | The step for one machine on the work order | The machine it runs on has no passed or waived first piece. A pass on another machine does not release this one |

Under **Per shift**, a part belongs to the shift its work **started** in, not
the shift that's on when it moves on. The shift is whichever started most
recently on the shift calendar, overtime runs included. During a handover the
incoming shift counts. Before or after every shift, the moment belongs to the
shift that just ended. A night shift past midnight keeps the date it started.
Editing a shift doesn't lose its first piece. With no shifts set up, it keys on
the plant date.

Under **Per machine**, the machine is the one the part is started on: the
machine picked at **Start Work**, or the planned machine (the live schedule's,
otherwise the one authored on the step). If no machine is planned, the start is
refused: *"&lt;step&gt; needs a first piece per machine, and no machine is planned
for &lt;part&gt;. Pick the machine at Start Work."*

A start refused for the first piece names the parts it is waiting on:
*"&lt;step&gt; is waiting on its first piece (&lt;part&gt;, &lt;part&gt;): QA buys it
off before &lt;part&gt; starts."*, with *Waiting on: QA to buy off the first
piece.* The banner, control-page cards and QA home name the machine or shift the
first piece is for.

## FPI Workflow

You meet FPI in three places. In the operator's step runtime, a banner that
changes with the inspection's state (below). On the work order's **control**
page, a *First piece waiting on QA* card for each pending first piece (titled
with the step and, under a narrower scope, its context — *&lt;step&gt; for &lt;shift&gt; on &lt;date&gt;*,
or *for the &lt;date&gt; shift* with no shift calendar), a *First piece failed at &lt;step&gt; for &lt;machine&gt; — run held* card for a
held step, and — for people who can sign off a first piece — a *First piece
waived at &lt;step&gt;* row for each waiver. On QA home, a *First piece waiting —
&lt;step&gt; for &lt;machine&gt;* banner whose **Start check** opens the control page. A quality report also
carries a **First Piece Inspection (FPI)** flag; it is set when a first piece
passes, or ticked by hand on the report form, and nothing waits on it.

!!! warning "There is no 'submit for FPI review' step"
    Nothing is submitted and nothing queues for review. The first piece becomes
    ready for buy-off by **finishing its own captures** — the same Complete step
    the operator would do anyway. QA then signs it off.

| State | What it says | What you can do |
|-------|--------------|-----------------|
| **Required** — no record yet | *First Piece Inspection Required* (with the context under a narrower scope, *…Required for &lt;machine&gt;*): *Starting the first part opens the first piece and calls QA; the rest wait for the buy-off.* | Start the first part: that opens the first piece and calls QA. **Start FPI** does the same from the banner. A sign-off holder can **Waive** before any part is made |
| **Machine not known** — Per machine step | *First Piece Inspection Required — machine not recorded*: *This step needs a first piece per machine. Pick the machine at Start Work; the first part started on it opens its first piece.* | Pick the machine at Start Work. A sign-off holder can **Waive for this machine** |
| **In progress** — pieces still to start or finish | *First Piece Inspection in progress*: *N more part(s) can start as part of the first piece; the rest wait for QA's buy-off. First piece: 1 of 2 parts started (&lt;part&gt;).* Once all are started: *Complete the first piece (&lt;parts&gt;) inspection below — other parts can't start until it's bought off.* | Start the remaining pieces and complete their captures |
| **Ready for buy-off** | *First piece ready for buy-off*: *Review the first piece (&lt;parts&gt;) results below, then sign off to release the run.* | **Sign off & pass**, **Fail**, or **Waive** — if you hold `sign_off_fpi`. Everyone else sees *awaiting buy-off* and a **Get QA sign-off** button |
| **Satisfied** | *First Piece Inspection signed off*: *Setup verified — all parts can proceed through this step.* Or *…waived*: *Released without a first-piece buy-off — parts can proceed through this step.* | Parts start and move. **New setup** re-opens it. A sign-off holder can **Void pass** after a pass, or **Start a new first piece** after a waiver |

QA is notified as soon as the first piece opens, at its first start:
*First piece waiting: &lt;step&gt;*, naming the parts started so far and the work
order, with a link to the work order. The verdict goes back the same way:
*First piece passed: &lt;step&gt; … the run may go ahead*, or on a fail *correct
the setup and re-run the first piece; the run stays held.*

**Start FPI** is refused, with the reason shown, when no part of the context is
at the step yet (*No part has reached this step yet — start the FPI from a part
at the step.*).

### Signing off

**Sign off & pass** opens *Sign off First Piece Inspection*, which states what
you are attesting to: the setup is correct, the first piece (every part in it,
by serial) conforms, and this releases the run. Above the notes it lists the
**first piece readings** for each of its parts: each characteristic, the
reading, its limits, and who took it and when. Those readings are what you are
signing. It confirms with *FPI signed off — parts can now proceed.*

A first piece of several parts is bought off **whole**. Until every piece is
made, the buy-off is refused: *"The first piece is 1 more piece short — each
nest's piece is made before the buy-off."*

On a step with no inspection in its work instruction (no readings, checks or
sampling), QA buys off on sight. The dialog warns that nothing was recorded.

- **Notes** are optional — gauges used, observations.
- If the step's **First piece** gate is set to *Signature + password*, or its
  **QA sign-off** gate asks for a password, you re-enter **your own** password.

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

**Fail** asks **Which pieces failed?** (*"The ticked pieces get a failed
inspection; the others wait and release when the re-run first piece passes."*)
and a **Reason / findings**. **Record failure** confirms with *FPI failed —
correct the setup and re-run the first piece.* It does three things:

- Each ticked piece gets a FAIL quality report, with your reason as its
  description. It is **quarantined**, and a disposition opens for it, unassigned,
  in the QA queue (see [Dispositions](../quality/dispositions.md#where-a-disposition-comes-from)).
- The run stays held. The work order's control page shows **First piece failed
  at *step* — run held**, with who failed it and the reason. The untouched
  pieces wait, and are released when the re-run first piece passes.
- Correct the setup, then start the next part: it opens the new first piece,
  bought off like the first. **Start a new first piece** on the card does the
  same.

**Waive** releases the run without a first-piece verification: *"Waiving releases
the run without a first-piece buy-off. Say why — it stays on the record."* It
needs a **Reason for waiving** of at least 10 characters, and the waiver records
who, when and why. A first piece can be waived before any part is made, for a
qualified fixture that needs no first piece: **Waive** on the *Required* banner,
or **Waive for this machine** on a Per machine step.

### A new setup

When the setup the first piece verified changes during the run, anyone working
the step records it with **New setup** on the green banner: *"The setup the first
piece verified has changed. Its sign-off stays on record, marked superseded, and
the next part started is a new first piece for QA to buy off."* **What changed?**
is one of *Tool change*, *Offset adjusted*, *Crash*, *Repair* or *Other*, and a
note is kept with it. **Record new setup** confirms with *New setup recorded —
the next part started is a new first piece.*

- The pass (or waiver) is marked **Superseded**, with who recorded the new setup,
  when and why.
- Parts **started before** the new setup were made on the old setup. Its first
  piece covers them, and they move on as normal.
- Parts started after it wait for the new first piece.

If a crash or similar makes the parts made before it suspect, that's a quality
decision: quarantine them. The new setup doesn't hold them on its own.

### A first piece passed in error

Found after the buy-off that the first piece shouldn't have passed (the wrong gauge,
a reading misread)? Anyone who can sign off FPIs can **Void pass** on the FPI
banner, with a required reason:

- The pass stays on record, marked **Voided** with your reason. It is not deleted.
- That pass's release is withdrawn, and a **new first-piece inspection** opens.
  Under **Per shift** or **Per machine**, other shifts' or machines' passes
  stand.
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
control page a row *First piece waived at &lt;step&gt; — "&lt;reason&gt;"* with the same
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
| **Superseded** | A waiver replaced by a new first piece, or a pass or waiver ended by a new setup. It still covers the parts started before; it releases nothing new | — |

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
scope, each shift or machine) whose first piece is waiting on QA or has
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
| The **parts** that make up the first piece | Photos and scans taken during the work |
| Machine, or shift and its date (for the narrower scopes) | The operator's own sign-offs |
| Status, result, notes | |
| Who acknowledged it, and when | |
| Who bought it off, and when — or who waived it, with the reason | |
| The co-signer's drawn signature, where it was co-signed | |

So "show me the first-piece inspection" means the record **and** the travelers of
the first piece's parts for that step. The record tells you it was bought off and by
whom; the step tells you what was actually measured.

!!! note "The drawing is kept only when it is co-signed"
    A co-signing inspector draws a signature at the operator's station, and it
    is stored on the record once their email and password verify. A buy-off from
    the inspector's own session asks for no drawing. What identifies the signer
    in both cases is the re-authentication plus `inspected_by` and
    `inspected_at`.

## The run while the first piece is open

While the first piece is pending:

- Only the first piece's parts can start. Every other part at the step is
  refused at Start Work (under Per shift or Per machine, the parts of that shift
  or machine). The refusal says *Waiting on: QA to buy off the first piece.*
- The operator's home shows how many can start (*N can start until QA buys off
  the first piece*), and counts the jobs *waiting on QA to buy off a first
  piece* rather than offering them as ready work.
- The first piece's parts can't move on until it is bought off.
- On a step that runs in loads, every part in a load counts: a load with more
  parts than the first piece has places left is refused, and nothing starts. On
  a Per machine step, a load runs on one machine: *"A load at &lt;step&gt; runs on
  one machine; these parts are on &lt;machines&gt;. Load them separately."*

After it passes, the other parts can start, and the first piece's parts move on.

## Failed FPI Handling

When FPI fails:

1. **The failed pieces** are quarantined, each with a disposition
2. **The floor** is told: *First piece failed … correct the setup and re-run
   the first piece; the run stays held*
3. **Remaining parts** can't start; the untouched first-piece parts wait
4. **The next part started** after the adjustment is the new first piece
5. **QA buys off** the new first piece, which releases the run

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
| `add_fpirecord` | **Start FPI** from the banner |
| `add_substepcompletion` | Record a **New setup** (anyone who can work the step) |
| `sign_off_fpi` | Pass, fail, waive, void or acknowledge. Co-signable at another user's station. |

Starting the first part opens the first piece for whoever starts it. No extra
permission is needed beyond being able to start the work.

!!! note "Recording the verdict is not `add_fpirecord`"
    The record already exists by the time anyone signs: the first start, or
    **Start FPI**, created it. The buy-off is gated on `sign_off_fpi` alone,
    which is what makes it an independent authority rather than a continuation
    of the operator's work.

## Next Steps

- [Recording Measurements](../tracking/measurements.md) - Measurement capture
- [Quality Reports](../quality/quality-reports.md) - Handling failures
- [Process Configuration](../../admin/processes/overview.md) - Configure FPI
