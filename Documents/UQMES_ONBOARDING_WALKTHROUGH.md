# UQMES onboarding walk — a QA inspector's day

**Who this is for.** A QA inspector who has just been given UQMES access
and needs a concrete, click-by-click walk of the actions their day is
built around. Read it start-to-finish once; refer back by section
later.

**What this is not.** A training curriculum for a trainer to teach
with (see `QA_INSPECTOR_TRAINING_SCRIPT.md` for that — it carries the
role-play, checkpoints, and gotcha essays). This is a self-serve
reference: shorter, first-person, with fewer exits into pedagogy.

**What you'll be walking.** A dedicated demo work order, `WO-QA-INSPECT-01`
(Midwest Fleet Services · Common Rail Injector · 8 parts), is seeded
into the Demo Company tenant specifically for this walk. Each part is
pre-staged into the state a section walks against so the exhibits are
always there. Re-run `python manage.py seed_demo` before each demo run
to reset state.

**Scannable traveler PDF for the walk:**
[`artifacts/WO-QA-INSPECT-01_traveler.pdf`](artifacts/WO-QA-INSPECT-01_traveler.pdf).
Print it (or open it on a phone) if you want to physically scan the
header barcode / QR to open the live WO — the scan resolves to the
same WO Detail page you'd reach by clicking. The PDF also includes
the full 12-operation routing table with sign-off blocks, giving the
walker a paper counterpart to what appears on screen. To regenerate
after a reseed, open the WO Detail (`/workorder/$id`) → **Traveler**
button → **Download PDF**; save the new file over the checked-in
copy so the barcode encodes the current WO id.

**Roles you'll play.** Passwords are `demo123`.

| Email | Name | Role | Where you play it |
|---|---|---|---|
| `sarah.qa@demo.ambac.com` | Sarah Chen | QA Inspector | Every section |
| `maria.qa@demo.ambac.com` | Maria Santos | QA Manager | Section 6 — approve disposition (if requested by permission gate) |

Sarah has QA Inspector permissions. A handful of decisions in the walk
(closing a MAJOR disposition, waiving an FPI) may require a QA
Manager. Log in as Maria for those; the walk calls it out where
needed.

**The parts on WO-QA-INSPECT-01, and where each is used:**

| Part | Where it sits in the seed | Section |
|---|---|---|
| `INJ-QA-INSPECT-001` | Nozzle Inspection · PENDING FPI · first piece designated | 3 |
| `INJ-QA-INSPECT-002` | Nozzle Inspection · AWAITING_QA · sampled ("Post-repair verification") | 4 |
| `INJ-QA-INSPECT-003` | Flow Testing · IN_PROGRESS · fresh, ready for a live FAIL | 5 |
| `INJ-QA-INSPECT-004` | Flow Testing · AWAITING_QA · visit 2, historical FAIL QR + CLOSED REWORK disposition already on file | 7 |
| `INJ-QA-INSPECT-005` | Nitride Coating · RETURNED from Apex Plating · awaiting return inspection | 8 |
| `INJ-QA-INSPECT-006` | Assembly · QUARANTINED · bare OPEN NCR assigned to Sarah | Section 1 (background) |
| `INJ-QA-INSPECT-007`, `INJ-QA-INSPECT-008` | Cleaning / Disassembly · IN_PROGRESS | filler, not walked |

---

## 1. Your home page — orient yourself

Log in as `sarah.qa@demo.ambac.com`. You land on `/` — Sarah's QA home.

**Top-left header.** `Welcome back, Sarah` and an `Incoming queue`
button that jumps to `/production/incoming`.

**Scan box.** A single input labeled *"Scan or type a work order /
part number…"* with a `Go` button. Scans always resolve to the parent
work order and drop you on WO Detail (`/workorder/$id`) — the shared
work surface where you can pick up any part on that WO. Part scans
go to the part's parent WO, not to the part detail.

**FPI banner block (red border).** Every pending First Piece Inspection
in your tenant surfaces here as a row: step name, work order, part
(if designated), and how long it's been waiting. Two buttons per row:
- **I'm on it** — acknowledges the pending FPI so the operator sees
  QA is on the way. After you click it, the row reads *"Seen by
  Sarah"*.
- **Start check** — jumps to `/workorder/$id/control` (the Control
  page). Note: Control is where you land, but the FPI **sign-off**
  actually happens inside the operator substep runtime — see Section 3.

For this walk the FPI banner shows two rows: the pre-existing
`WO-2024-0048-A` row (from a different demo storyline) and your
`WO-QA-INSPECT-01 · INJ-QA-INSPECT-001` row. The 001 row is Section 3.

**Inbox with chips.** A flat list of everything QA owes a decision on,
grouped by filter chips: *All · Receiving · OSP returns · In-process*.
An *Urgent* chip highlights anything overdue past its own age
threshold. Rows are clickable — clicking navigates you to the
appropriate work surface for that row's type.

For this walk the Inbox shows (among others):
- Receiving lots from Great Lakes Diesel and Bargain Bolts (Section 2).
- OSP-return shipments (some existing, plus the new `OSP-QA-INSPECT-01`
  from Apex Plating for Section 8).
- An in-process row for `WO-QA-INSPECT-01 · Nozzle Inspection · 1 pcs`
  — that's `INJ-QA-INSPECT-002`, the sampled part for Section 4.

**My Quality Actions.** Three tiles counting your assigned items:
*Approvals* (approvals waiting for your signature), *CAPA tasks*
(Containment / Corrective / Preventive actions assigned to you), and
*My dispositions* (Quarantine dispositions assigned to you). Each
tile is a link to the surface where you work those items.

The *My dispositions* tile currently reads `3` — that includes the
pre-existing DISP-QAI-006-OPEN on `INJ-QA-INSPECT-006`, the CLOSED
DISP-QAI-004-REW on `INJ-QA-INSPECT-004`, plus any others already
assigned to you across the tenant. The 006-OPEN row is your
background reminder that a disposition is already sitting in your
queue — a real-day exhibit; the walk doesn't work it directly.

**Your Gauges.** Calibration status on gauges you've used recently.
Currently reads *"Torque Wrench TW-25 — overdue 15d"*. Real day: a
gauge overdue for calibration should not be used until re-calibrated;
a link to `/quality/calibrations` sits here to check status.

You will return to this home page repeatedly through the walk. It's
your dashboard.

---

## 2. Receiving inspection — a lot of injectors arrives

In real day terms: a pallet of Common Rail Injectors from Great Lakes
Diesel has arrived at the receiving dock. You need to sample and
inspect it against the sampling plan before it becomes available
inventory.

### 2a — Reach the receiving queue

Either click the **Receiving** chip on your home Inbox (it reads
`Receiving 5 · 4d` — 5 rows, oldest 4 days), or navigate to
`/production/receiving-inspection` directly from the URL bar.

**You land on:** `/production/receiving-inspection` — the *Receiving
Inspection Queue*, a table with columns *Lot # · Material · Supplier
· Qty · Status · Actions*. Every row has an **Inspect** button.

Rows include several `RCV-INJ-000#` lots from Great Lakes Diesel in
`AWAITING_INSPECTION`, and one `RCV-INJ-HOLD` from Bargain Bolts in
`QUARANTINE` with reason *"Unqualified supplier"* — that row exists
to illustrate the supplier-hold state; don't inspect it.

### 2b — Open a lot

Click **Inspect** on `RCV-INJ-0001` (Great Lakes Diesel, 250 EA).

**You land on:** `/production/receiving-inspection/$lotId` — the lot
detail page.

**You see:**
- Header: `RCV-INJ-0001` · status `AWAITING_INSPECTION` · **Documents**
  button (attach cert of conformance, packing slips, etc.).
- Subheader: `Common Rail Injector · Great Lakes Diesel · qty 250`.
- **"No Certificate of Conformance captured for this lot."** with an
  **Upload CoC** button. In a real receiving workflow the CoC is
  uploaded here first; the demo lets you proceed either way.
- **Sample plan (C0, level III, TIGHTENED)** panel:
  `Inspect 29 of 250 · Accept ≤ 0 · Reject ≥ 1`. Zero-acceptance
  sampling at inspection level III, tightened switching — a single
  defect rejects the whole lot.
- A note: *"This receiving step has digital work instructions. Run
  the inspection through the operator runtime."*
- **Run Inspection (DWI)** button.

### 2c — Run the DWI

Click **Run Inspection (DWI)**.

**You land on:** `/operator/steps/$stepId/substeps?execution=…&material_lot=$lotId&at=0`
— the operator substep runtime, scoped to this lot.

**You see** the DWI-guided *Inspect incoming material* form. Fields:
- **Scan the lot / packing slip** — barcode / QR input, optional.
- **Outer Diameter** (`RCV-01`) — required, spec `25 +0.05 / −0.05 mm`.
- **Incoming inspection result** — required, buttons Pass / Fail /
  Pending.
- **Inspection sign-off** — required, "Sign as detected by" button.
- **Defects found** — "No defects found." with "Add defect" button.
  Only used on FAIL.

The footer bar tells you what's still missing and disables **Confirm
& next** / **Confirm & review** until you're done.

### 2d — Pass the lot

Enter a passing value and sign:
- **Outer Diameter**: `25.01` (well within spec).
- **Incoming inspection result**: click **Pass**.
- **Sign as detected by**: click to sign.

Click **Confirm & review** (or **Confirm & next** if there are more
substeps), then **Complete** on the review pane.

**What happens on the backend:** the lot leaves `AWAITING_INSPECTION`
and becomes stock available for a work order. The
`SamplingTriggerManager` records a PASS. The receiving audit log
appends the completion event.

Fail flow: click **Fail** instead of Pass, add a defect (Type +
Description), then complete. That opens the Reject disposition
dialog for type + severity + quantity. This walk doesn't drive that
path here — Sarah's in-process fail path is Section 5.

---

## 3. First Piece Inspection buy-off — INJ-QA-INSPECT-001

Real day terms: on a WO's first pass through a step, one part is
designated as the **first piece**. Operators run the DWI on that
piece, then QA reviews the inspection result and signs off before
the rest of the batch can be run through the step. The FPI is a
production gate: a failed or missing FPI blocks the whole batch.

### 3a — Spot the FPI on your home

Your home page's red-bordered **First piece waiting** block shows
your pending FPI row: `WO-QA-INSPECT-01 · INJ-QA-INSPECT-001`,
Nozzle Inspection, ~6h waiting.

Click **I'm on it** first — this acknowledges the pending FPI, so
the operator sees you're on the way. The row updates to read
*"Seen by Sarah"*.

### 3b — Jump into the operator runtime

Click **Start check**.

**You land on:** `/workorder/$id/control` for WO-QA-INSPECT-01 (the
Control page). **The FPI panel itself doesn't render here** — the
`FpiStatusBanner` component only surfaces inside the operator
substep runtime.

To reach the runtime, find `INJ-QA-INSPECT-001` in Control's Step
Status table (Nozzle Inspection · IN_PROGRESS), click into WO Detail
(`/workorder/$id`) → Parts tab → open the 001 row's runtime, or
navigate directly:
`/operator/steps/$stepId/substeps?workOrder=$woId&part=$partId`.

**You see** a banner at the top of the runtime reading **"First
Piece Inspection in progress · Complete the first piece
INJ-QA-INSPECT-001 inspection below — the run is held until it's
bought off."** Below the banner is the Nozzle Inspection DWI —
substeps like *Visual nozzle inspection* with 3D callouts (nozzle tip,
spray-hole bank, seat face), a *Mark any defects* 3D annotator, an
equipment field, and sign-off.

### 3c — Run the DWI on the first piece

In real production, the *operator* runs these substeps and QA only
does the buy-off. In this walk you play both roles.

Enter passing values on the visual inspection substeps:
- **Visual nozzle inspection**: `Pass`.
- **Equipment used during this inspection**: pick any bench (this
  field appears blank in the seed; click Add equipment and select).
- Sign-off: "Sign as detected by" → click to sign.
- No defects.

Click **Confirm & next** through each substep, then **Confirm &
review** on the last one. On the review pane, click **Complete**.

### 3d — Sign off the FPI

Once the inspection substeps are complete, the FpiStatusBanner
transitions to state 3: **"First piece inspection complete · awaiting
buy-off"** with **Pass** / **Fail** / **Waive** buttons.

Choose:
- **Pass** — records the FPI as PASSED. The batch is released; other
  parts can now run through Nozzle Inspection.
- **Fail** — records FAILED. The batch is blocked pending
  investigation. Usually indicates a setup problem; a FAILED FPI
  often triggers a CAPA.
- **Waive** — records WAIVED with a required reason (≥10 characters).
  Use rarely; a waived FPI still counts as a documented decision.

**Permission note.** The Pass / Fail / Waive buttons are gated
server-side on the `sign_off_fpi` permission. If your instance
restricts sign-off to QA Manager only, log out and back in as
`maria.qa@demo.ambac.com`. To Sarah without that permission, the
banner reads *"awaiting buy-off"* but the buttons don't appear.

For this walk: click **Pass**, add a note like *"Nozzle geometry
matches drawing rev; spray-hole bank clear."*, submit.

**What happens:** the FPI record transitions PENDING → PASSED,
`inspected_by` becomes you (or Maria), an `fpi.decided` notification
fires, and any parts blocked pending the FPI are released to run
through the step. The FPI row disappears from your home banner. On
the runtime, the banner now shows green: *"First Piece Inspection
signed off · Setup verified — all parts can proceed through this
step."*

---

## 4. A sampled part comes to you — INJ-QA-INSPECT-002

Real day terms: sampling rules flag certain parts for QA inspection
mid-process. This part is flagged with reason *"Post-repair
verification"* — it had earlier rework at an earlier step, so the
sampling rule marked it for extra scrutiny when it reached its next
QA-gated step (Nozzle Inspection).

### 4a — Find it on your Inbox

On your home page, click the **In-process** chip (or leave it on
All). The row *"Nozzle Inspection · 1 pcs · Common Rail Injector ·
WO-QA-INSPECT-01 · WO due 2026-08-10"* is INJ-QA-INSPECT-002.

Click the row.

**You land on:** `/workorder/$id/control` for WO-QA-INSPECT-01 — the
Control page. In the Step Status table, INJ-QA-INSPECT-002 is at
Nozzle Inspection · `AWAITING_QA` · flagged **Sample**. Its
`sampling_context` reads `Post-repair verification`.

### 4b — Open the part detail

From Control, the per-part table row's serial is plain text — Control
doesn't link out to part detail. To reach detail, switch to WO Detail
(`/workorder/$id`), open the Parts tab, and click the ExternalLink
icon on the INJ-QA-INSPECT-002 row.

**You land on:** `/details/Parts/$id` — the part detail page.

**You see:**
- Header: `INJ-QA-INSPECT-002 · Common Rail Injector`.
- **General**: Status `AWAITING_QA`.
- **Production**: Order (link to Orders detail), Current Step
  `Nozzle Inspection` (link to Steps detail), Work Order
  (`WO-QA-INSPECT-01`, link — this jumps to Control, not Detail).
- **Quality Control**: `Sampling Required · Yes`,
  `Sampling Reason · post repair verification` (the UI renders the
  underlying `POST_REPAIR_VERIFICATION` enum in lowercase). `Rework
  Passes · 1` reflects an earlier rework cycle at another step.

### 4c — Run the inspection

**Order matters:** Section 3 signed off the Nozzle Inspection FPI.
If you haven't done Section 3 yet, do it first — the FPI banner
gates the whole step, and you'll see *"First Piece Inspection in
progress"* on part 002's runtime too, blocking your sampled
inspection.

From the part detail, or from the Control Step Status row's runtime
launch, open the operator substep runtime for this part's current
step-execution.

The DWI at Nozzle Inspection walks: visual inspection points on the
3D model (nozzle tip / spray-hole bank / seat face), a pass/fail
verdict, an equipment field (which visual bench/scope was used), and
a sign-off. Value the visuals PASS, sign as detected by, and
**Confirm & next** through to the review pane.

**Complete** the review.

**What happens:** the part transitions `AWAITING_QA` → next state per
the process. The sampling rule records this inspection outcome against
the ruleset for post-repair verification analytics.

---

## 5. A part fails your inspection — INJ-QA-INSPECT-003

Real day terms: you're inspecting a part at Flow Testing. You take
the flow rate reading and it's out of spec. The system records the
FAIL and immediately quarantines the part.

### 5a — Reach the runtime

From your Inbox, click any WO-QA-INSPECT-01 row (or use the scan box
with `WO-QA-INSPECT-01`) to reach the WO Detail. Parts tab → find
INJ-QA-INSPECT-003 (Flow Testing · IN_PROGRESS). Open its runtime
via the **Start Work** button, or via the ExternalLink icon → runtime
from part detail.

### 5b — Enter an out-of-spec value

You see the *Flow test* substep with, top-to-bottom:
- A green **"First Piece Inspection signed off · Setup verified"**
  banner (seeded PASSED FPI on this step, so you're not blocked).
- **Rework attempt 0 of 2** counter — this WO's rework escalation
  threshold.
- Decision point notice: *"Auto · QA result — routes automatically
  from the inspection result when you complete the step — pass takes
  Assembly, fail takes Rework."*
- **Scan the part barcode** — required (Barcode / QR).
- **Flow Rate** (`F-04`) — required, spec `120 +20 −20 mL/min` (i.e.
  LSL 100, USL 140).
- **Flow bench in-calibration** confirmation — required checkbox.
- **Flow test result** — required, Pass / Fail / Pending buttons.
- Sign-off + defect fields.

Enter values to trigger the FAIL:
- **Scan the part barcode**: any string like `INJ-QA-INSPECT-003`.
- **Flow Rate**: `98`. Inline validation flags red — below LSL.
- **Flow bench in-calibration**: check the confirmation.
- **Flow test result**: click **Fail**.
- Add a defect: Type `Flow rate out of spec`, Description *"Flow rate
  98 mL/min - below LSL of 100 mL/min. Awaiting disposition."*
- Sign as detected by.

Click **Confirm & review** → **Complete**.

### 5c — Backend effects (what just happened)

- A new **Quality Report** (`QR-2026-#####`) is created with
  `status=FAIL`, linked to INJ-QA-INSPECT-003, at Flow Testing.
- The QR's `post_save` signal auto-creates a **Quarantine Disposition**
  in `OPEN` state with no type yet, description
  *"Auto-created for failed quality report: …"*, assigned to a QA
  Manager / QA Inspector on the tenant.
- The part's `part_status` flips to `QUARANTINED`.
- An `ncr.opened` notification fires through the escalation path.

Sarah's home now shows the disposition on the *My dispositions*
tile (count goes up), and the part's detail page has:
- Latest Inspection: `FAIL · 1 open defect`.
- Has Open Defect: `Yes`.
- Quality Reports: 1 row (`QR-…`) linked to your just-filed FAIL.
- Dispositions: 1 row (`DISP-…`, OPEN, no type yet) linked to that QR.

You just caused the disposition Section 6 walks against.

---

## 6. Working the disposition

Real day terms: you filed a FAIL. Now you have to decide what to do
with the part — rework, scrap, use as-is with concession, return to
supplier, etc. That decision goes on the disposition record.

### 6a — Open the disposition

Two paths, either works:
- From **My dispositions** tile on your home → `/production/dispositions`
  filtered to your dispositions → click the OPEN row for
  INJ-QA-INSPECT-003.
- From the part detail page → **Dispositions** widget → edit icon on
  the OPEN row.

**You land on:** `/dispositions/edit/$id` — the disposition editor.

**You see:**
- Header with disposition number and part.
- **Disposition Details** form top-to-bottom:
  - **Current State** — dropdown, currently `OPEN`. Setting a
    Disposition Type below auto-transitions this to `IN_PROGRESS`
    on save.
  - **Disposition Type** — dropdown, currently empty. See 6c for what
    each type means.
  - **Severity** — dropdown, default `MAJOR`, with the label
    *"Severity classification of the nonconformance"* underneath.
  - **Assigned To** — pre-set to whoever was assigned at auto-create.
  - **Description** — auto-populated from the QR.
  - **Containment Action** — free text. **Required to close** for
    MAJOR/CRITICAL severity.
  - **Resolution Notes** — free text for what you decided and why.
  - **Requires Customer Approval** — checkbox; auto-set for USE_AS_IS
    and REPAIR, both of which need a customer concession.
  - **Related** — links to the linked Quality Report(s) and 3D
    Annotations widget.

### 6b — Fill in the decision

For this walk, pick **REWORK**:

- **Disposition Type**: `REWORK`.
- **Severity**: `MAJOR`.
- **Containment Action**: *"Part quarantined and segregated pending
  rework at Flow Testing."*
- **Resolution Notes**: *"Retest after cleaning; suspect fouling in
  the seat."*

Click **Update Disposition**.

### 6c — The doors, briefly

- **REWORK** — send back through the rework loop. Most common. Part
  status cascades to `REWORK_NEEDED` (only if the part is currently
  QUARANTINED or PENDING — see the design note below). Rework count
  increments.
- **REPAIR** — accept with repair outside normal spec; may not fully
  conform (AS9100). Same cascade behavior as REWORK.
- **USE_AS_IS** — accept the non-conformance under a customer
  concession. Requires an approval; do not use as a shortcut.
- **SCRAP** — terminal. Part status cascades to `SCRAPPED`.
- **RETURN_TO_SUPPLIER** — return under SCAR to the original
  supplier. Terminal for internal; part status cascades to `CANCELLED`.

**Design note on the cascade.** REWORK/REPAIR change the part's
status to REWORK_NEEDED only when the part is at `QUARANTINED` or
`PENDING` — states that are "held awaiting a decision". Once an
operator has moved the part on (AWAITING_QA at visit 2, IN_PROGRESS
at a step, etc.), the disposition is a documented decision, not a
routing directive; the part stays put. This matches how QMS/MES
systems separate "paper decision" from "physical routing".

### 6d — Close the disposition

After you click Update, the disposition transitions to `IN_PROGRESS`.
Once the rework has been done and re-inspected (Section 7 walks
that), the disposition is closed via a second edit:
- Fill **Resolution Notes** if not already filled.
- Set **Current State** to `CLOSED`.
- Click **Update Disposition**.

**What happens on close.** The `complete_disposition_resolution`
service runs. Blocker checks include: containment_action must be
present for MAJOR/CRITICAL; any pending 3D annotations must be
resolved. If clear, the disposition closes with `resolution_completed`
and stamped `resolution_completed_by/at`.

---

## 7. Re-inspecting a reworked part — INJ-QA-INSPECT-004

Real day terms: a part that previously failed has been reworked and
is back at the same step for a second inspection (visit 2). The
audit trail on the part detail shows the full arc: the original
FAIL QR, the CLOSED REWORK disposition, and now this visit-2
inspection.

### 7a — Find it

Two clean paths:
- From your home Inbox — the WO-QA-INSPECT-01 In-process rows include
  another one at Flow Testing. That's INJ-QA-INSPECT-004.
- Or navigate to `/workorder/$WO-QA-INSPECT-01/control` and find the
  004 row in the Step Status table.

### 7b — Read the part's history first

Open the part detail (via the WO Detail Parts tab's ExternalLink
icon). You see:
- **Status**: `AWAITING_QA` (Flow Testing).
- **Quality Reports**: 1 row — `QR-QA-INSPECT-004-FT · FAIL · Flow
  Testing`, description *"Flow rate 98 mL/min - below LSL of 100
  mL/min. Reworked and returned for re-inspection."* — click to open
  the failing report.
- **Dispositions**: 2 rows.
  1. `DISP-QAI-004-REW · CLOSED · REWORK · MAJOR` — the signed rework
     decision, with resolution notes describing the nozzle
     replacement. **This is the record to read.**
  2. `DISP-…-000### · OPEN · (empty type)` — the bare NCR auto-
     created by the FAIL QR's post-save signal. It's a seed
     tag-along; ignore it. (This is the same "double-disposition"
     quirk as INJ-0038-010 in the older seed.)
- **Rework Passes**: `1` — the rework counter incremented once, from
  the original REWORK cascade.

### 7c — Run the re-inspection

Open the runtime for INJ-QA-INSPECT-004's current step-execution
(visit 2 at Flow Testing). Enter a passing value:
- **Flow rate**: `121` mL/min.
- **Flow test result**: **Pass**.
- Sign as detected by.
- No defects.

Click **Confirm & review** → **Complete**.

**What happens.** A second QR (PASS) is written for visit 2. The
part status moves out of AWAITING_QA to the next state in the flow
(READY_FOR_NEXT_STEP → the process routing continues). The rework
arc is now paper-complete: FAIL QR → CLOSED REWORK → reworked → PASS
QR at visit 2. Rework Passes counter increments to 1 (or higher on
subsequent reworks; the seed starts you at 1).

---

## 8. OSP return inspection — INJ-QA-INSPECT-005

Real day terms: parts sent out to a subcontractor (Apex Plating, for
Nitride Coating) have returned. Before accepting them back into the
process, QA runs a receiving-style inspection on the outgoing/incoming
characteristics — most importantly **Coating Thickness**.

### 8a — Find the returned shipment

Click the **OSP returns** chip on your home Inbox. The most-recent
`Nitride Coating · OSP-2026-000003 · Apex Plating Co · returned`
row is your shipment. (Shipment numbers auto-generate per tenant; the
demo seeder tags this one with `reference=OSP-QA-INSPECT-01`
internally, but the UI displays the sequential `OSP-2026-000003`.
Older seed shipments — `OSP-2026-000001`, `-000002` — are separate
storylines.)

Click the row.

**You land on:** `/production/incoming` (the incoming queue) with the
shipment visible.

Alternatively, reach the shipment directly from the WO Detail: a
small **"1 at outside process"** badge next to the WO header links
to Control, where the Outside processing panel lists the shipment
with an **Inspect** button.

### 8b — Open the return inspection

From either surface, click **Inspect** on the OSP-2026-000003 row.

**You land on:** the operator substep runtime scoped to the
shipment: `/operator/steps/$stepId/substeps?execution=…&osp_shipment=$shipmentId&at=0`.

**You see** the return-inspection DWI, one substep titled *"Return
inspection (post-coating)"* with:
- **Coating Thickness** (`OSP-01`) — required, spec `12 +3 −2 µm`.
- **Photograph the coated surface** — optional image capture (tap to
  capture or upload).
- **Return inspection result** — required, Pass / Fail / Pending
  buttons.
- **Return inspection sign-off** — required, Signature field
  (*"Click to sign"*).

Enter a passing value:
- **Coating Thickness**: `12.5`.
- **Return inspection result**: **Pass**.
- **Return inspection sign-off**: click to sign.

Click **Confirm & review** → **Complete**.

**What happens.** The shipment's return-inspection execution completes.
The part's `part_status` transitions from `AT_OUTSIDE_PROCESS` (or
`AWAITING_QA`, depending on how `receive_parts_back` set it) into
the next step of the process — Final Test, per the routing seeded
by the OSP seeder. The shipment record stays as `RETURNED` with
the inspection now recorded.

---

## 9. Reading the audit trail

Real day terms: an auditor asks you to reconstruct the history of a
specific part. Or an operator on the shop floor hands you a physical
part and asks "what's the story on this one?" You need to be able
to answer without going into engineering.

### 9a — A rich in-flight arc (INJ-QA-INSPECT-004)

Open `/details/Parts/…` for INJ-QA-INSPECT-004. Reading top-to-bottom:
- **Status** tells you where the part is *right now*.
- **Current Step** tells you where in the process.
- **Latest Inspection** rolls up the most recent QR verdict.
- **Quality Reports** widget lists every inspection (PASS and FAIL)
  in chronological order. Each row links to the QR detail with the
  measurement values.
- **Dispositions** widget lists every disposition on the part with
  state, type, severity, and links to the disposition editor.
- **Activity History** appends every state change with timestamp
  and actor.

For INJ-QA-INSPECT-004 you can narrate: *fail at Flow Testing on
[date] (link to QR); REWORK decision signed by [name] on [date]
(link to disposition); reworked (implicit — no operator UI record);
returned to Flow Testing visit 2; awaiting Sarah's re-inspection*.

### 9b — A closed terminal record (INJ-0042-023)

Open `/details/Parts/…` for `INJ-0042-023` (existing seed, from
Journey 6 of the training script).

**Status** is `SCRAPPED`. **Quality Reports** has one row — the
originating FAIL QR at Final Test with description *"Nozzle tip shows
visible porosity at seat face; failed hold pressure at 2450 psi (min
2800). Casting defect, not reworkable."* **Dispositions** has the
CLOSED SCRAP row (`DISP-QR-0042-023-FT`, severity CRITICAL,
resolution notes citing QP-007). Together those three records ARE
the audit trail: cause, decision, terminal state.

If a scrapped part ever shows a status of `SCRAPPED` with **no**
linked QR or disposition, that itself is a red flag — how did the
part reach a terminal state without a paper trail? Ask before
touching.

### 9c — Two seed quirks worth knowing

**Double disposition on some parts.** When a FAIL QR fires, its
post-save signal auto-creates a bare OPEN disposition (no type). The
demo seeder's `_enrich_auto_dispositions` pass then gives those bare
NCRs a round-robin type and lifecycle so the demo isn't a wall of
identical OPENs. Result: some parts (INJ-0038-010, INJ-QA-INSPECT-004,
INJ-0042-023 with our seed fix) have two dispositions — the intended
one (SCRAP or REWORK) and an unrelated enriched tag-along. Read the
intended one; ignore the tag-along.

**Sparse Activity History in the seed.** Many seeded parts show *"No
audit history"* in the Activity History section because the seed
writes state directly rather than going through the operator runtime.
The trail lives on the linked QRs and dispositions in that case.
Live parts (those you work during a real day) accumulate a normal
history.

---

## 10. Glossary — 15 terms

- **AWAITING_QA** — part state meaning "an operator finished a step
  but a rule says QA looks at it before it moves on." Parked;
  production can't advance it.
- **CAPA** — Corrective And Preventive Action. Structured
  investigation and fix for recurring or high-severity defects. QA
  managers own authoring; inspectors feed data in.
- **CoC** — Certificate of Conformance. Supplier's paperwork stating
  a lot meets the ordered spec. Attached at receiving.
- **DWI** — Digital Work Instruction. On-screen guided capture the
  operator (and inspector) follows step-by-step.
- **ERP id** — the human-readable identifier (WO-QA-INSPECT-01,
  INJ-QA-INSPECT-004) shown on labels and travelers.
- **FPI** — First Piece Inspection. First part off a new step,
  inspected to verify setup before production runs the batch.
- **LSL / USL** — Lower / Upper Spec Limit. Outside these, the part
  fails.
- **NCR** — Non-Conformance Report. Formal record of a
  nonconformity. In UQMES an NCR is a `QuarantineDisposition`.
- **OSP** — Outside Processing. A step run by a subcontractor. Parts
  are shipped out, worked, returned, and re-inspected.
- **Quarantine** — physical or logical hold on a part while its
  disposition is decided.
- **QR** — Quality Report. The record of a single inspection outcome
  (PASS / FAIL / PENDING).
- **SamplingTriggerManager** — the service that decides which parts
  to sample based on the WO's sampling ruleset (AQL, n-of-K,
  post-repair verification, etc.).
- **Step execution** — one visit to one step by one part.
  `visit_number > 1` means a rework re-visit.
- **Traveler** — the printed WO packet that accompanies the physical
  parts through the shop. Print it from WO Detail's Traveler button.
- **WO** — Work Order. A single production run of a specific
  quantity of one part type for one Order.
