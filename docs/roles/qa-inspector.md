# QA Inspector Guide

This guide is for Quality Assurance Inspectors who perform inspections, record measurements, create quality reports, and manage sampling in uqmes.

!!! tip "Learning the role"
    The [QA Inspector training track](../training/tracks/qa-inspector.md) walks
    every workflow on this page on a training instance, with exercises.

## Your Role

As a QA Inspector, you:

- Perform inspections at quality gates
- Record measurements and inspection data
- Create quality reports (NCRs) for non-conformances
- Document defects with annotations
- Record disposition decisions

!!! note "You record decisions; you don't recommend them"
    There is no *recommend then wait* step. Choosing the disposition type **is**
    the authorized act, and the record stores who authorized it and when. If you
    don't hold the permission, an approver co-signs on your screen — see
    [Dispositions](../workflows/quality/dispositions.md#who-can-decide-and-co-signing).

!!! note "Sampling is decided for you"
    A rule flags the part and the plan is calculated — *"Inspect 29 of 250 ·
    Accept ≤ 0 · Reject ≥ 1"*. Your job is to answer **"why this part?"** from
    the Sample flag and its reason, not to choose the sample size.

## Getting Started

### First-Time Setup

1. Log in and review [Navigation Tour](../getting-started/navigation.md)
2. Familiarize yourself with Quality section
3. Understand your inspection assignments

### Your Main Pages

| Page | Location | Purpose |
|------|----------|---------|
| **Home** | Home | Your inspection queue — first pieces, incoming, OSP returns |
| **Incoming Inspection** | Supply > Incoming Inspection | Purchased lots **and** OSP returns, one queue |
| **Work Orders** | Production > Work Orders | Work order detail and history |
| **Quality Reports** | Quality > Quality Reports | NCRs you've created |
| **Dispositions** | Quality > Dispositions | Quarantined parts |
| **Inbox** | Personal > Inbox | CAPA tasks and pending approvals |
| **Heat Map** | Quality > Heat Map | Visual defect analysis |

## Daily Workflow

### 1. Check Your Queue

**Your Home page is your queue.** When you log in as a QA Inspector, Home shows
the inspection work waiting on you rather than a generic dashboard:

- **First piece waiting** — parts held until you sign off the first piece, each
  with **I'm on it** and **Start check**
- **Incoming queue**, segmented into **Receiving**, **OSP returns**, and
  **In-process**, with counts and age
- Counters for **Approvals**, **CAPA tasks**, and **My dispositions**
- **Unassigned dispositions** — ones a failure opened that nobody has taken yet,
  each with **Take it**
- **Your gauges** — gauges you used in the last 7 days that are due for
  calibration, with **Review calibrations**

Work the oldest and most urgent items first — each segment shows its age.

!!! note "Reaching the queue from elsewhere"
    If your Home shows a different landing (because you hold several roles), the
    same surface is always available at `/quality/inbox`.

### 2. Perform Inspections

For each inspection point:

1. Open the work order requiring inspection
2. Identify parts to inspect
3. Apply sampling (if applicable)
4. Perform measurements/checks
5. Record results
6. Disposition any part that fails

Parts that pass need no further action from you — once the step's requirements
are met, they advance automatically.

### 3. Document Issues

When problems are found:

1. A failure on an inspection does it for you: a reading out of spec, or your
   **Fail** on the inspection's result. On a report you raise yourself, set it to
   **FAIL**, either when you create it or by editing a Pending one. Either way the
   part is quarantined, the step is alerted, and a disposition opens, unassigned
2. Add annotations (if 3D model available)
3. Notify appropriate parties

## Performing Inspections

### At Inspection Steps

1. Open the work order from **Production** > **Work Orders**
2. See parts waiting at the inspection step — the rule has already decided
   which ones those are
3. Inspect the parts presented to you
4. Record results

### Recording Measurements

Where you record depends on what you are inspecting.

**In-process, on parts** — measurements are substeps inside the step player.
Work the step's inspection-point substep and enter the value there; the system
evaluates it against the specification as you confirm, and writes it to a
Quality Report alongside the completion.

**Incoming lots** — receiving inspection has its own surface. Open the lot from
the receiving inspection queue and use **Record Measurements** there.

!!! note "There is no Record Measurements button on a part"
    There is no per-part measurement button. For parts,
    the step player is the recording surface. See [Recording
    Measurements](../workflows/tracking/measurements.md).

### Measurement Best Practices

- Use calibrated equipment only
- Verify equipment is in calibration
- Record actual values (don't round inappropriately)
- Document measurement conditions if relevant

## Sampling Inspections

### When Sampling Applies

1. The sampling rule selects the parts; they are the ones waiting at the step
2. Inspect them
3. Record results
4. The rule's accept/reject criteria decide the lot outcome

!!! note "You do not choose the sample"
    Sampling is decided for you by the rule attached to the step. Your job is
    to answer *"why this part?"* from the record — not to size or pick the
    sample.

### AQL Sampling

Based on lot size and AQL level:
- System calculates sample size
- Accept number (Ac) and Reject number (Re) shown
- If defects ≤ Ac: Accept lot
- If defects ≥ Re: Reject lot

### After Lot Decision

**If Accepted:**
- Parts move forward
- Sample results recorded

**If Rejected:**
- Options: 100% inspect, scrap, RTV
- Create quality report
- Disposition required

## Creating Quality Reports (NCRs)

### When to Create

- Any non-conformance found
- Failed measurements
- Visual defects
- Material issues
- Customer complaints

### Creating the Report

1. Select affected part(s)
2. Click **Create Quality Report**
3. Fill in required fields:

| Field | What to Enter | Required |
|-------|---------------|----------|
| **Status** | Where the report stands | **Yes — the only one** |
| **Part** | The affected part | No |
| **Process Step** | Where it was found | No |
| **Description** | Detailed explanation | No |

4. **Add each defect separately** — error type, count, location and severity
   belong to the defect, not to the report
5. Attach evidence (photos, data)
6. Submit

!!! note "There is no Immediate Action field"
    Containment and root cause belong to the CAPA raised from the report, not
    to the report itself.

### Severity Guidelines

| Severity | Use When |
|----------|----------|
| **Minor** | Cosmetic, no functional impact |
| **Major** | Out of spec, affects function |
| **Critical** | Safety risk, regulatory violation |

A new defect defaults to **Major** — set it deliberately.

## Annotating Defects

If 3D models are configured:

### Adding Annotations

An annotation belongs to a **quality report**, so choose the report first:

1. On the work order's page, select the part — the **QA panel** on the right
   shows its model; or open the **Annotator** (`/annotator`) and pick the
   report; or use the step's **Part annotation** capture if it has one
2. Click the location of the defect on the model
3. Fill in **Error Type**, **Severity Level** and **Notes**
4. Save

!!! note "Two severity scales"
    An annotation's severity is **Low, Medium, High or Critical** — a different
    scale from the defect's Minor / Major / Critical on the report itself. A
    marker rates one finding where it sits on the part; the report and the
    disposition rate the nonconformance the findings add up to.

!!! info "Some defects must be marked before the disposition can close"
    A defect type can require a 3D annotation. Its disposition then shows **3D
    Annotations Required**, and **Go to Annotator** opens with the report already
    selected.

!!! important "Delete misplaced markers before you finish the report"
    While the report is still Pending you can delete an annotation and place it
    again. Once the report is **Pass** or **Fail**, the annotation is inspection
    evidence and only the quality team can delete it — by default QA Inspector,
    QA Manager and Tenant Admin, so you can, but your operators cannot. See
    [Annotations](../3d-models/annotations.md).

### Why Annotate

- Builds heat map data over time
- Visual communication of issues
- Pattern identification
- Training reference

## Managing Quarantine

### Taking a disposition

A failure's disposition opens **unassigned**. It waits on your Home page under
*Unassigned dispositions* until someone presses **Take it**; it then moves to
that person's **My dispositions**.

While it waits, the part can't be started: the start is refused, naming the
disposition. Rework reaches the part through the disposition.

### Working it

1. Record the **containment action**
2. Mark the defect on the model, if the disposition asks for it
3. Choose the decision; an approver co-signs on your screen if you don't hold
   `approve_disposition`
4. After rework, re-inspect the part; close the disposition once the work is
   done. See [Dispositions](../workflows/quality/dispositions.md)

## First Piece Inspection (FPI)

On a step's first pass, one part is the **first piece**. The operator runs the
work instruction on it; you buy it off before the rest of the batch runs.

!!! important "It is a batch gate, not a per-part check"
    The work order's control page says so plainly: *"No part moves past these
    steps until the first piece is bought off."* A missing or failed FPI holds
    the whole batch.

### Where it appears

A pending FPI shows on your **Home** page as a red banner — one row per waiting
first piece, with the step, work order, part and a waiting-age timer — offering
**I'm on it** (acknowledge) and **Start check**.

### Two routes, with different options

| Route | What you get |
|-------|--------------|
| **The runtime** — work order → Start Work → tick the part → Start | **Sign off & pass · Fail · Waive** |
| **The control page** — *First piece waiting on QA* card | **Sign off · Fail · Waive** |

Both routes use the same dialog, which lists the first piece's readings — each
characteristic, reading, limits, and who took it when. Both offer the co-sign when
you don't hold `sign_off_fpi`. **Waive** asks for a reason of at least 10
characters. Sign off and Waive meet the step's password assurance; Fail does not
need it.

**Fail** asks for the reason. The first piece is quarantined with a FAIL report
carrying your reason, and its disposition opens, unassigned. The run stays held:
the control page shows **First piece failed — run held**, with **Start a new first
piece** for after the setup is corrected.

### Signing off

![The FPI sign-off confirmation](../assets/qa-inspector/qa-03-fpi-signoff.png)

The dialog states what you are attesting to:

> By signing off you attest that the setup is correct and the first piece
> conforms, and this releases the run. It is recorded against your name.

Add notes — gauges used, observations — and confirm. The banner turns green and
the run is released.

!!! important "Separation of duties"
    The operator signed the inspection substeps; **you** sign the buy-off. They
    must be different people. If you signed *any* substep on the first piece's
    current step execution, the dialog says so before you can confirm, and
    switches to a second inspector's sign-in at your screen; the verdict is then
    recorded under their name.

    That applies to **all three outcomes**, not just the pass: Fail and Waive are
    blocked for the same person too. A waive additionally needs a reason of at
    least ten characters — it releases the run as surely as a pass does.

    An inspector who lacks `sign_off_fpi` is not stuck: the banner offers an
    inline co-signature for an authorized colleague, the same pattern as a
    [disposition decision](../workflows/quality/dispositions.md#who-can-decide-and-co-signing).

## Incoming Inspection

For material from suppliers:

1. Identify lot to inspect
2. Apply incoming sampling rule
3. Perform inspection
4. Record results
5. Accept or reject lot

### Rejected Incoming Material

Reject from the lot itself — **the disposition is opened with it**, on every
branch, so there is no separate "raise an NCR then mark the lot" sequence.

| What you reject | What happens |
|-----------------|--------------|
| **Part of the lot** | The bad pieces split off and the rest is accepted |
| **The whole lot** | Needs `reject_whole_lot` — see below |

!!! important "Your whole-lot reject may be a request, not a rejection"
    Rejecting an entire lot back to a vendor is a VDMR, and it sits with the QA
    Manager tier. **Without that permission your whole-lot reject becomes a
    request that holds the lot** rather than rejecting it — which is the correct
    outcome, not a failure, but it means the lot is waiting on a manager and
    will not move until one acts.

    Some facilities grant it to their inspectors' group. Check which yours does
    before assuming a lot you rejected has gone anywhere.

Once a lot is genuinely rejected, **Ship back** appears for the return: RMA
number, printed RTV sheet, carrier and tracking, and the replacement delivery is
raised automatically. Any credit is settled in your ERP, not here.

## Supporting CAPA

You may be assigned CAPA tasks:

1. Check **Personal** > **Inbox** for assigned CAPA tasks
2. Perform assigned investigation
3. Document findings
4. Complete task with evidence
5. Mark task complete

## End of Shift

### Clear the gates before you clear your desk

Most of your work leaves nothing hanging — each inspection is its own record
with your name on it, and the next inspector picks up the queue as it stands.
**Two things are different, because somebody is stopped behind them.**

**A pending First Piece Inspection is an andon call, not a queue item.** A
machine and an operator may be idle waiting on it, and no part moves past that
step until it is bought off. Do not leave one unresolved at the end of a shift
without telling the lead.

**An acknowledged FPI with no verdict is worse than an unacknowledged one.**
*I'm on it* tells the floor somebody is handling it — if that was you and you
have gone home, the batch is blocked *and* nobody is looking for an inspector.
Either finish it or say so.

### Before you go

- **A held lot is still held.** Paperwork holds clear themselves when the
  paperwork arrives; a judgement hold needs a quality manager, so hand it over
  rather than leaving it to age.
- **Dispositions you opened but did not decide** stay on your name. Check *My
  dispositions* on Home.

## Quick Reference

| Task | Steps |
|------|-------|
| Record measurement | On a part: step player → inspection substep → enter value → **Confirm & next** · On an incoming lot: receiving inspection → **Record Measurements** |
| Create NCR | Select part → Create Quality Report → Fill form → Submit |
| Add annotation | Work order page → select part → QA panel, or **Annotator** → choose the report → click the defect → Save |
| Buy off a first piece | Home red banner → **Start check** → review captures → **Sign off & pass** (or Fail / Waive) |
| Accept lot | Complete sampling → Record results → System calculates |

## What You CAN'T Do

Typically you cannot:

- Approve dispositions (QA Manager) — you *record* the decision; an approver
  co-signs on your screen if you don't hold it
- Verify that a CAPA worked, which is the act that closes it (QA Manager)
- Approve a root-cause analysis (`review_rca` — QA Manager)
- Override the training gate for an unqualified operator (Shift Lead, QA
  Manager, Production Manager — deliberately not QA Inspector)
- Manage users (Tenant Admin)
- Classify documents, or read the Secret tier (QA Manager classifies; Document
  Controller and Tenant Admin read Secret)

Escalate to QA Manager as needed.

!!! note "You can do more than you might expect"
    The shared staff base is broad: a QA Inspector **can** create orders and work
    orders, upload documents, and move parts. Whether you *should* is your shop's
    procedure, not a permission.

## Troubleshooting

### Measurement equipment shows overdue or failed

The two are handled differently, and the system tells you which you have:

- **Failed** calibration, or out of service — the gauge is greyed in the picker
  and the capture is **refused**. Pick a different gauge; this one cannot be used
  until a passing calibration is recorded.
- **Overdue** — marked *calibration overdue* in the picker, and the reading **is
  accepted**, with a warning. An overdue check is
  a scheduling lapse, not evidence the gauge is wrong. Record the work, then
  get it calibrated.

Either way, tell whoever owns calibration.

### Can't find part to inspect

- Check filters
- Verify work order assignment
- Part may be at different step

### Quality report won't submit

- Check required fields
- Ensure parts are selected
- Verify you have permission

## Related Documentation

- [Quality Reports](../workflows/quality/quality-reports.md)
- [Recording Measurements](../workflows/tracking/measurements.md)
- [Sampling Rules](../workflows/quality/sampling.md)
- [Creating Annotations](../3d-models/annotations.md)
- [Heat Maps](../analysis/heatmaps.md)
