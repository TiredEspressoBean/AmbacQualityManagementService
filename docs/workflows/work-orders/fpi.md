# First Piece Inspection (FPI)

First Piece Inspection ensures production setup is correct before running full batches. This guide covers FPI workflow in uqmes.

## What is First Piece Inspection?

FPI (also called First Article Inspection at setup level) is a quality check on
the **first part** produced at a step, bought off by QA before the rest of the
run may proceed. It is what catches a bad setup on part one instead of part
two hundred.

A step either requires it or it doesn't — the requirement is a setting on the
step, not something a tool change or a shift handover raises on its own. See
[Scope is per work order](#scope-is-per-work-order) for what the scope setting
does and does not do.

## Enabling FPI

FPI is configured per process step:

1. Open the process in the **Process Flow** editor and turn on **Edit Mode**
2. Click the step, then open **Advanced**
3. Enable **Requires first-piece inspection**
4. Set the **FPI scope** — when the requirement resets

See [Step Configuration](../../admin/processes/steps.md).

When enabled, the first part at that step triggers FPI workflow.

### Scope is per work order

**One buy-off releases the step for the whole work order.** Once a first piece is
signed off at a step, every part at that step may proceed — regardless of shift
change, machine change or who is running it.

!!! warning "The narrower scope settings do not hold work"
    A step carries an FPI *scope* setting with four options — **per work order**,
    **per shift**, **per equipment** and **per operator**. The setting does
    change which inspection **records** get created: a new shift, a different
    machine or a different operator mints its own. But the gate that actually
    holds parts ignores it — one PASSED or WAIVED inspection satisfies the step
    for the entire work order, whichever scope is set.

    So the extra records read as per-shift control that is not enforced. **Do not
    rely on it.** If a shift or machine change genuinely needs re-verification,
    make it a separate step or a check in the work instruction, where it will
    actually hold.

## FPI Workflow

There is **one** FPI control — a banner — and it changes shape with the state of
the inspection. You meet it on the work order **control** page, in the QA home
**pending FPI** panel, and inside the operator's step runtime. It is the same
banner and the same four states everywhere.

!!! warning "There is no 'submit for FPI review' step"
    Nothing is submitted and nothing queues for review. The first piece becomes
    ready for buy-off by **finishing its own captures** — the same Complete step
    the operator would do anyway. QA then signs it off.

| State | What it says | What you can do |
|-------|--------------|-----------------|
| **Required** — no record yet | *First Piece Inspection Required* | **Start FPI** — designates the first piece and holds the run |
| **In progress** — first piece not finished | *First Piece Inspection in progress* | Nothing yet. Complete the first piece's captures; no buy-off is possible until they are in |
| **Ready for buy-off** | *First piece complete — ready for buy-off* | **Sign off & pass**, **Fail**, or **Waive** — if you hold `sign_off_fpi`. Everyone else sees *awaiting buy-off* and a **Get QA sign-off** button |
| **Satisfied** | Green — run released | Nothing; parts move |

### Signing off

**Sign off & pass** opens a dialog that states what you are attesting to: the
setup is correct, the first piece conforms, and this releases the run.

- **Notes** are optional — gauges used, observations.
- If the step is authored to need a **verified** signature, you re-enter **your
  own** password.
- You cannot buy off a first piece whose work you signed yourself. The server
  refuses it: the buy-off is a second person's judgement.

!!! tip "An operator does not have to go and find QA"
    If you lack `sign_off_fpi`, the button reads **Get QA sign-off** and opens
    the same dialog with a co-sign section. An authorized inspector enters their
    **email and password at your station** — you stay logged in, and the record
    carries **their** name as the authority, not yours.

**Fail** holds the run, and the first piece goes into the quality workflow.
Adjust the setup, produce a new first piece, and the inspection repeats.

**Waive** releases the run without a first-piece verification. It needs a reason
of at least 10 characters, and the waiver records who, when and why.

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
| **Pending** | First piece not yet inspected | Yellow |
| **Passed** | FPI approved, batch released | Green |
| **Failed** | FPI rejected, setup adjustment needed | Red |
| **Waived** | FPI requirement bypassed (with approval) | Gray |

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

Use sparingly - FPI catches setup errors early.

## Viewing FPI Status

### On Work Order
The work order shows FPI status for each step:

```
Step: Machining
FPI: Passed ✓
Parts released: 10/10
```

### On Tracker
Orders with pending FPI show a badge or indicator.

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

- Other parts at that step are held
- Cannot proceed to next step
- Clear visual indicator on Tracker
- "Waiting for FPI" status

After FPI passes:

- All held parts are released
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

Track FPI performance:

- **First-time pass rate**: FPIs passed on first attempt
- **FPI duration**: Time from submission to approval
- **Repeat FPI rate**: How often FPI must be repeated

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
