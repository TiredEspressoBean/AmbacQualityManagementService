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
| `sarah.qa@demo.ambac.com` | Sarah Chen | QA Inspector | Every section — the walker's identity. |
| `maria.qa@demo.ambac.com` | Maria Santos | QA Manager | Section 6 — approve disposition (if requested by a permission gate). |
| `mike.ops@demo.ambac.com` | Mike Rodriguez | Operator | Section 3 — the seed pre-signs the first-piece substeps as Mike so Sarah (playing QA) can sign off the FPI without hitting the segregation-of-duties gate. You don't log in as Mike; his signatures are already on the seed exhibit. |

Sarah's QA Inspector role has `sign_off_fpi` (Section 3),
`close_disposition` (Section 6), and every other permission this walk
uses — you don't need to switch to Maria for the happy path. Maria's
row is here for two edge cases: (a) `approve_disposition` is SOD-
restricted to QA Manager / Tenant Admin, so anything that needs a
formal approval (e.g. a USE_AS_IS with customer concession routing)
would need her; (b) if your tenant's role config narrows any of the
above to QA Manager only, log in as Maria — the walk still works.

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
part number…"* with a `Go` button (disabled until you type or scan
something). Scans always resolve to the parent work order and drop
you on WO Detail (`/workorder/$id`) — the shared work surface where
you can pick up any part on that WO. Part scans go to the part's
parent WO, not to the part detail.

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
grouped by four filter chips: *All · Receiving · OSP returns ·
In-process*. Each chip carries its row count and the age of its
oldest item (`Receiving 5 · 3d`), with a tooltip spelling that out
(*"oldest: 3d"*). Rows are clickable — clicking navigates you to the
appropriate work surface for that row's type.

**"Urgent" is a badge, not a chip.** A red `Urgent 1` pill sits after
the four chips, counting anything past its own age threshold. It is
plain text, not a button — you cannot filter by it, so don't go
hunting for the click target.

For this walk the Inbox shows (among others):
- Receiving lots from Great Lakes Diesel and Bargain Bolts (Section 2).
- OSP-return shipments from Apex Plating. Yours for Section 8 shows as
  `OSP-2026-000003` — the UI displays the sequential shipment number,
  not the seeder's `reference` (see 8a).
- An in-process row for `WO-QA-INSPECT-01 · Nozzle Inspection · 1 pcs`
  — that's `INJ-QA-INSPECT-002`, the sampled part for Section 4.

**My Quality Actions.** Three tiles counting your assigned items:
*Approvals* (approvals waiting for your signature), *CAPA tasks*
(Containment / Corrective / Preventive actions assigned to you), and
*My dispositions* (Quarantine dispositions assigned to you). Where
each one actually takes you is worth knowing, because two of the
three share a destination:
- *Approvals* → `/inbox`
- *CAPA tasks* → `/inbox`
- *My dispositions* → `/production/dispositions`, **unfiltered** —
  the tile counts your 3, but the page it opens lists every
  quarantined part in the tenant (see 6a).

The *My dispositions* tile currently reads `3`. The tile filters
out CLOSED rows client-side (`useMyDispositions.ts:32`), so it only
shows OPEN + IN_PROGRESS dispositions assigned to you. The three
you see on a fresh seed:
- `DISP-QAI-006-OPEN` — OPEN, no type yet, on
  `INJ-QA-INSPECT-006` (my seed's background exhibit; the walk
  doesn't drive it).
- `DISP-2026-000007` — OPEN SCRAP on `INJ-0042-019` (the escalation-
  staged SCRAP dispo from the older training seed).
- `DISP-2026-000002` — IN_PROGRESS SCRAP on `INJ-0038-007` (from the
  completed WO-2024-0038-A storyline).

The 004 rework disposition (`DISP-QAI-004-REW`) is CLOSED and does
NOT contribute to this count, even though it's assigned to Sarah —
that's by design; a closed disposition isn't work waiting.

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

**Two queues, and they are not the same page.** Worth getting straight
before you start, because the home page and this section send you to
different ones:
- `/production/receiving-inspection` — the *Receiving Inspection
  Queue*. **Purchased lots only**; 5 rows on a fresh seed.
- `/production/incoming` — *Incoming Inspection*, the unified queue:
  purchased lots **and** parts back from a subcontract vendor, 7 rows,
  with a *Source* column and *All sources* / *All statuses* filters.
  This is where the home page's **Incoming queue** button goes, and
  where Section 8 picks up the OSP return.

Both open the same inspection runtime; the unified one is just a wider
net. This section uses the receiving-only queue.

**You land on:** `/production/receiving-inspection` — a table with
columns *Lot # · Material · Supplier · Qty · Status · Actions*. Every
row has an **Inspect** button, and the header carries **Import** /
**Export** plus a *Search receiving inspection queue…* box.

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

Top of the runtime carries stepper navigation — **Jump to substep 1:
&lt;name&gt;** for each substep plus **Jump to review**. This lot's DWI has
one substep, so you'll see one of each.

**The footer does not block you.** It names what's outstanding —
*"3 required fields missing — Outer Diameter, Incoming inspection
result, …"* — but **Confirm & review stays enabled**. Clicking it with
fields missing scrolls you to the first one rather than submitting
(its tooltip reads *"Tap to scroll to: …"*). Only **Back** is disabled,
because this is the first substep. So an unfilled form doesn't produce
a dead button; it produces a jump.

### 2d — Pass the lot

Enter a passing value and sign:
- **Outer Diameter**: `25.01` (well within spec).
- **Incoming inspection result**: click **Pass**.
- **Sign as detected by**: click to sign.

Click **Confirm & review**. On the review pane, click **Accept lot**
(receiving-specific verb; the general operator runtime uses
"Complete step", but receiving shows **Accept lot** / **Reject lot**
to match the domain).

**Toast:** *"Lot accepted"* — you land back on the lot detail page,
which now reflects the completed inspection.

**What happens on the backend:** the lot leaves `AWAITING_INSPECTION`
and becomes stock available for a work order. The
`SamplingTriggerManager` records a PASS. The receiving audit log
appends the acceptance event.

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

### 3b — Reach the runtime

1. Click **Start check** on your home's FPI banner row. You land on
   `/workorder/$id/control` — the Control page. **The FPI panel
   itself doesn't render here**; the `FpiStatusBanner` component only
   surfaces inside the operator substep runtime.
2. Go to WO Detail (`/workorder/$id`) and click **Start Work**
   (top-right).
3. In the dialog, check the `INJ-QA-INSPECT-001` row under Nozzle
   Inspection and click **Start**.
4. The runtime opens. Every inspection substep already carries a
   `SubstepCompletion` **signed by Mike** — the seed pre-populates
   those so the walker (Sarah, playing QA) can go straight to the
   buy-off.

**What the runtime will look like, so it doesn't alarm you.** The
header reads *"0 of 2 confirmed"* and the footer *"3 required fields
missing"*, and the measurement fields are empty. That is expected and
**not** a seed gap: the runtime's "confirmed" counter is *fresh-session*
state — it starts empty and only counts substeps confirmed in the current
session; it never replays prior `SubstepResponse` rows on load. So it
would read "0 of 2" even if the seed captured full values, and no seed
change alters it (making it hydrate stored responses would be a frontend
feature, out of scope here). Mike's `SubstepCompletion` signatures are
real in the database. You do not need to fill the form in to buy off the
FPI — the banner is independent of it.

**If you arrive by pasting a runtime URL, include `workOrder`.** The
FPI banner is rendered only when the URL carries a `workOrder` query
param (`OperatorSubstepRuntimePage` gates it on `search.workOrder`).
Reaching the runtime any other way — a bare
`/operator/steps/$stepId/substeps?execution=…` — shows the DWI with
no FPI banner at all and no error explaining why. Going through
**Start Work** sets the param for you.

**Segregation-of-duties (SOD) note:** the person who signed the
first-piece substeps cannot also sign off the FPI. That's why the
seed uses Mike (operator) for the substeps and expects Sarah (QA)
for the buy-off. If you re-sign any substep yourself, the FPI Pass
endpoint will return `400: "Segregation of duties: this user signed
one or more of the first piece's inspection substeps. FPI buy-off
must be signed by a different qualified inspector."`

### 3c — Sign off the FPI

On the runtime, the FpiStatusBanner shows three action buttons:
**Sign off & pass** · **Fail** · **Waive**.

Choose:
- **Sign off & pass** — records the FPI as PASSED. Opens a
  confirmation dialog with an optional notes field: *"By signing off
  you attest that the setup is correct and the first piece
  (INJ-QA-INSPECT-001) conforms. This is recorded against your name
  and releases the run."* Click **Confirm sign-off**. The batch is
  released; other parts can now run through Nozzle Inspection.
- **Fail** — records FAILED. The batch is blocked pending
  investigation. A FAILED FPI usually indicates a setup problem and
  often triggers a CAPA.
- **Waive** — records WAIVED with a required reason (≥10 characters).
  Rare; a waived FPI still counts as a documented decision.

For this walk: click **Sign off & pass**, optionally add a note like
*"Nozzle geometry matches drawing rev; spray-hole bank clear."*,
click **Confirm sign-off**. Toast: *"FPI signed off — parts can now
proceed."*

**What happens on the backend:**
1. `FPIRecord.status` → PASSED, `inspected_by` = you, `inspected_at`
   set, `quality_report` linked to the first piece's QR.
2. A `QaApproval` is created for (step, work_order, qa_staff = you) —
   the FPI Pass IS the step-level QA signoff for the first-piece run.
   Without this, the step would stay blocked on "QA signoff required
   but not received" (the QaApproval has no other user-facing creation
   path in the running app).
3. `fpi.decided` notification fires.
4. `check-status` for this (WO, step) now returns
   `satisfied: true`, `message: "FPI passed"`.
5. The FPI banner disappears from your home page; on the runtime,
   after a reload, the banner turns green: *"First Piece Inspection
   signed off · Setup verified — all parts can proceed through this
   step."*

**Permission note.** The Pass / Fail / Waive buttons and the API
endpoint are gated server-side on the `sign_off_fpi` permission. If
your instance restricts sign-off to QA Manager only, log out and
back in as `maria.qa@demo.ambac.com`. To Sarah without that
permission, the banner reads *"awaiting buy-off"* but the buttons
don't appear.

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
**Confirm & next** through to the review pane. On the review pane
click **Complete step**. Toast: *"Step complete — lot advanced (1
part moved)."*

**What happens:** the part transitions `AWAITING_QA` → `IN_PROGRESS`
on the next step in the process. The sampling rule records this
inspection outcome against the ruleset for post-repair verification
analytics.

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

Click **Confirm & review** → **Complete step**.

**Toast:** *"FAIL recorded — part held for disposition"* (red/error
toast) with the description line listing the specific blockers —
*"Part is quarantined and step blocks on quarantine; QA signoff
required but not received; One or more measurements are out of
specification"*. The system distinguishes hard-fail states from
awaiting-signoff states in the toast heading, so you can tell at a
glance a fail was recorded (not a benign timing wait).

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

**Contrast with a seed exhibit.** The QR and disposition you just
created have full audit trail — `created_by` = Sarah, timestamps
match your click, the `ncr.opened` event fired live. Seeded records
(the pre-closed `DISP-QAI-004-REW`, the QR on 004, terminal
0042-023) don't — see Section 12c for the two seed quirks that
show up on those.

---

## 6. Working the disposition

Real day terms: you filed a FAIL. Now you have to decide what to do
with the part — rework, scrap, use as-is with concession, return to
supplier, etc. That decision goes on the disposition record.

### 6a — Open the disposition

Two paths, either works:
- From **My dispositions** tile on your home → `/production/dispositions`.
  Be ready for what this opens: the page is titled **Quarantined
  Parts** and it is a *parts* list, not a disposition list — ERP ID ·
  Status · Step · Part Type · Process · Created At · Details ·
  Actions, with *Archived / Requires Sampling / Needs QA / Exclude
  Terminal* filters. It is **not** filtered to you despite the tile's
  count, so search for `INJ-QA-INSPECT-003`. Each row's action is
  either **Disposition** (no disposition yet — creates one) or
  **Edit Disposition** (one exists). You want Edit Disposition.
- From the part detail page → **Dispositions** widget → edit icon on
  the OPEN row. Fewer rows to wade through; prefer this one.

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

Click **Update Disposition**. Toast: *"Disposition updated"*.

**What happens on the backend when you save with type = REWORK:**
1. The disposition's `current_state` auto-transitions `OPEN` →
   `IN_PROGRESS` (built into `QuarantineDisposition.save()`).
2. The cascade fires: `apply_disposition_to_part` sees the part is
   at `QUARANTINED` (a routable status), so it advances
   `part.part_status` → `REWORK_NEEDED` and increments
   `total_rework_count` by 1.
3. If the part had already moved past `QUARANTINED` (e.g. someone
   dispositioned an already-reworked part after the fact), the
   cascade would skip — REWORK is a paper record, not a routing
   directive.

### 6c — The doors, briefly

- **REWORK** — send back through the rework loop. Most common. Part
  status cascades to `REWORK_NEEDED` (only if the part is currently
  QUARANTINED or PENDING — see the design note below). Rework count
  increments.
- **REPAIR** — accept with repair outside normal spec; may not fully
  conform (AS9100). Same cascade behavior as REWORK.
- **USE_AS_IS** — accept the non-conformance under a customer
  concession. Requires an approval; do not use as a shortcut.
- **SCRAP** — terminal. Part status cascades to `SCRAPPED` from any
  state (terminal-rank precedence still applies — a SCRAPPED part
  can't be pulled back by a later REWORK).
- **RETURN_TO_SUPPLIER** — return under SCAR to the original
  supplier. Terminal for internal; part status cascades to
  `CANCELLED` from any state.

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

**How this connects to Section 6d.** You just closed the disposition
on INJ-QA-INSPECT-003. Section 7 walks a *different* part
(INJ-QA-INSPECT-004) that's already been through that same close in
the seed — its `DISP-QAI-004-REW` is pre-CLOSED and the rework has
been done offline. This is what a real re-inspection looks like the
day the reworked part comes back to your bench.

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

Click **Confirm & review** → **Complete step**. Toast: *"Step
complete — lot advanced (1 part moved)."*

**What happens.** A second QR (PASS) is written for visit 2. The
part status transitions `AWAITING_QA` → `IN_PROGRESS` on the next
step in the process (Assembly, per the Flow Testing → Assembly edge).
The rework arc is now paper-complete: FAIL QR → CLOSED REWORK →
reworked → PASS QR at visit 2. The **Rework Passes** counter stays
at `1` — that counter was incremented when the REWORK disposition
was applied (Section 6), not on this re-inspection pass. It's a
running tally of *how many rework cycles this part has been through*,
not of how many re-inspection PASS-es.

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

Click **Confirm & review**. On the review pane the action buttons are
**Accept return** / **Reject** (domain-specific — the OSP step uses
Accept/Reject rather than the generic "Complete step" the operator
runtime uses on non-OSP steps). Click **Accept return**.

Toast: *"Accepted — parts advanced past the outside-process step."*
You land on `/production/outside-processing` — the OSP board — and
the part on the shipment has moved to the next step in the process
(Final Test).

**What happens.** The shipment's return-inspection execution completes.
The part's `part_status` transitions from `AT_OUTSIDE_PROCESS` (or
`AWAITING_QA`, depending on how `receive_parts_back` set it) into
the next step of the process — Final Test, per the routing seeded
by the OSP seeder. The shipment record stays as `RETURNED` with
the inspection now recorded.

---

## 9. Working a CAPA task — CAPA-2024-002 and CAPA-2024-004

Real day terms: a disposition handles *this part right now*. A CAPA
(Corrective And Preventive Action) handles *the pattern* — why is
this happening again, what will we change so it stops. Sections 5
through 7 walked one failed part. This section walks the parallel
system that catches the pattern behind repeated failures.

QA inspectors don't own CAPA *closure* (`verify_capa` is gated to
the QA Manager), but they do the legwork: work assigned tasks,
record verification data, and — when a QR reveals a systemic issue
rather than a one-off — initiate a new CAPA.

Sarah has pre-seeded work across the five demo CAPAs. This section
walks two of them.

### 9a — Find your CAPA work

On the home page, the **My quality actions** panel holds three
counters: **Approvals**, **CAPA tasks**, and **My dispositions**.
The **CAPA tasks** count (backed by `useMyCapaTasks`) covers every
task Sarah owns — as the primary `assigned_to`, or as a row on
`CapaTaskAssignee` for a multi-person task. Expect five or six on a
fresh seed; the exact number shifts because due dates are seeded
relative to today, so don't treat it as a fixed expectation.

Sidebar → **Quality → CAPAs** (`/quality/capas`) opens the full
list: four stat cards (Active / Pending Verification / Overdue /
Closed) above a table. Controls are a **Search capas…** box, a
**Sort by…** dropdown, **New CAPAs**, a **Needs My Approval**
toggle, and a **View CAPA** button on each row. There is no
"assigned to me" filter, so read the *Assigned To* column.

**The Status column is computed, not stored.** `CAPASerializer`
returns `CAPA.computed_status`, which derives the status from the
underlying facts — verification confirmed → Closed, all tasks done
+ RCA complete → Pending Verification, any task or RCA started →
In Progress, nothing yet → Open. So a CAPA that has tasks never
displays as Open, whatever its stored `status` field says. What
you'll actually see:
- **CAPA-2024-002** — Pending Verification, Preventive Action,
  Minor. Assigned to Sarah, all tasks complete. This is the
  verification exhibit.
- **CAPA-2024-003** — In Progress, Corrective Action, Major.
  Nozzle batch defects; Sarah owns two multi-assignee tasks.
- **CAPA-2024-004** — In Progress, Corrective Action, Major.
  Contamination investigation; Sarah has *"Conduct contamination
  analysis"*, Not Started.
- **CAPA-2024-005** — In Progress, Corrective Action, Major.
  Customer return, assigned to Sarah; no RCA yet.

### 9b — Complete an assigned task (CAPA-2024-004)

**Two places can complete a task**, and they now behave identically:
- the **Inbox**, which lists only *your* outstanding tasks — the
  fastest route when you're working your own queue;
- the CAPA detail **Tasks** tab, which lists *every* task on the
  CAPA grouped by type (Containment / Corrective / Preventive).
  Each row carries three controls, all icon-only and easy to miss:
  a **checkbox** on the left that opens the completion dialog, and
  a **pencil** (edit) and **trash** (delete) at the right. Use this
  when you're looking at the CAPA as a whole.

Either way completion goes through the `complete-task` endpoint and
the `complete_capa_task` service, so `completion_mode` and any
signature requirement apply the same from both.

Walking it from the Inbox:

1. Sidebar → **Inbox** (or the **CAPA tasks** counter on the home
   page). Header reads *"1 overdue, 8 total items"*.
2. Tabs across the top: **All**, **Tasks**, **Approvals**,
   **Dispositions**. Cards are grouped by urgency — **Overdue**,
   **This Week**, **Upcoming** — and those headings are collapsible
   buttons, so not every card is on screen at once. If a task you
   expect is missing, expand the other groups before concluding it
   isn't there.
3. Find *"Conduct contamination analysis"* — badged *Corrective
   Action*, referencing CAPA-2024-004, *assigned to Sarah Chen*,
   Not Started, *Due in 6 days*. Each card offers **View** and
   **Complete**.
4. Click **Complete**. The **Complete Task** dialog opens —
   *"Mark this task as complete and add any notes about what was
   done."* Fill **Completion Notes** (placeholder: *"Describe what
   was done to complete this task…"*). **Attach Evidence** is
   available if you have a measurement printout or photo.
5. Click **Complete Task**. `completed_date` and `completed_by` are
   stamped by the `complete_capa_task` service and the CAPA's
   progress percentage ticks up.

**A third task you didn't expect.** CAPA-2024-004's Tasks tab shows
**three** rows, not the two the seed lists: `T001` is
*"Containment: Increased cleaning solution filtration and
monitoring"*, auto-created by the `create_initial_containment_task`
signal from the CAPA's `immediate_action`. Every CAPA with an
immediate action gets one. Harmless here, but see the note at the
end of 9c — it used to break the verification exhibit.

**Multi-person tasks (CAPA-2024-003).** Open CAPA-2024-003's Tasks
tab (the tab beside it is labelled **Root Cause**, not RCA). Two of
Sarah's tasks are multi-person:
- *"Update incoming inspection procedure"* — `completion_mode` =
  `ALL_ASSIGNEES` (Sarah AND Maria both must sign off).
- *"Implement tightened sampling for nozzles"* — `completion_mode`
  = `ANY_ASSIGNEE` (Sarah OR Jennifer, whichever gets there first).

The `complete_capa_task` service enforces the mode: completing an
ALL_ASSIGNEES task records *your* `CapaTaskAssignee` row as
COMPLETED but leaves the task itself open until every assignee has
done the same; ANY_ASSIGNEE closes on the first. The Tasks tab shows
the mode per row (*Single Owner* on the ordinary ones), and the
completion dialog says so up front for an ALL_ASSIGNEES task rather
than letting you discover it afterwards.

So on T005 *"Update incoming inspection procedure"*: Sarah
completing it leaves the row **Not Started** with her assignee
signoff recorded and Maria's still outstanding. That's correct, not
a failed click.

### 9c — Record verification data (CAPA-2024-002)

CAPA-2024-002 shows **Pending Verification** — all tasks done and
RCA complete, so someone now has to check whether the correction
actually worked. Progress reads 75%.

Verification is **two stages**: you write the *plan* (how you'll
measure it) first, and the outcome is recorded against that plan
afterwards. You can't record a result for a measurement you never
defined — which is the point.

1. Open **CAPA-2024-002** and click the **Verification** tab. It's
   headed *"Effectiveness Verification — Verify that
   corrective/preventive actions have been effective"*, and on a
   fresh seed reads *"No verifications have been recorded yet."*
2. Click **Add Verification**. The **Add Verification Plan** dialog
   opens — *"Define how you will verify the effectiveness of
   corrective actions."*
3. Fill both required fields:
   - **Verification Method** — *"How will effectiveness be
     verified? (e.g., process audit, data review, etc.)"* For this
     CAPA: "Monitor next 30 days of receiving for missing-document
     holds."
   - **Success Criteria** — *"What defines success? (e.g., zero
     defects over 30 days, process capability > 1.33)"* Here: "Zero
     missing-document holds over a 30-day window."
4. Click **Create**. (**Create** stays disabled until both fields
   have content.)

The effectiveness outcome — `effectiveness_result` (CONFIRMED /
NOT_EFFECTIVE / INCONCLUSIVE) plus notes — is recorded against the
plan once the monitoring window has actually elapsed. CAPA-2024-001
is the worked example: open its Verification tab to see a completed
plan with a CONFIRMED result.

**Segregation of Duties on verification.** Sarah can add and edit
the verification record (`add_capaverification`,
`change_capaverification`). She *cannot* perform the final verify
that closes the CAPA — `verify_capa` is gated to the QA Manager.
`capa.ready_for_verification` routes to the QA Manager group;
Jennifer reviews the recorded data and signs off (or reopens it).

**What happens on QA Manager verify.** If CONFIRMED, the
`verify_capa_effectiveness` service closes the CAPA and logs a
`CapaStatusTransition`. If NOT_CONFIRMED, it reopens the CAPA to
IN_PROGRESS, marks the RCA `for review`, and auto-creates a
30-day follow-up task. The escalation loop is built in — a
correction that didn't stick doesn't quietly close.

### 9c-bis — The other four tabs

Sections 9b and 9c cover Tasks and Verification. The rest, briefly,
so nothing on the page is a surprise:

- **Root Cause** — on a CAPA with no RCA yet this reads *"No root
  cause analysis has been performed yet"* with a **Start RCA**
  button. Worth knowing that an RCA is not optional decoration: the
  computed status can't reach Pending Verification without one (see
  9a), so a CAPA whose tasks are all done but which still shows
  In Progress is usually missing its RCA.
- **Approval** — for a MAJOR/CRITICAL CAPA this shows an
  *"Awaiting Approval — This CAPA is pending management approval.
  Work cannot begin until approved."* banner plus an Approval
  History list. Read-only for Sarah; approving is a QA Manager
  action. A MINOR CAPA shows *Not Required* instead.
- **Documents** — **Attach Document**: a file picker, a
  **Classification** dropdown (PUBLIC / INTERNAL / CONFIDENTIAL /
  RESTRICTED / SECRET, defaulting to INTERNAL) and **Upload**. This
  is where inspection evidence lives if you didn't attach it from
  the completion dialog.
- **History** — *"Timeline of changes and updates to this CAPA."*
  On the seeded CAPAs this reads *"No audit history."* for the same
  reason the seeded parts do (see Section 12c): the seeder writes
  rows directly rather than going through the runtime.

### 9d — Initiate a CAPA from a failed QR

Sarah has `add_capa` (the CRUD gate — every staff role has it)
plus `initiate_capa` (the business-verb gate that layers on top
via `CAPAViewSet.action_permissions`). Together those let her
create new CAPAs. Operators have `add_capa` but *not*
`initiate_capa`, so they can help edit a CAPA draft someone else
opened but can't POST a new one — formal CAPA initiation sits
with QA staff and supervisors, matching the sibling pattern used
by `close_capa` / `approve_capa` / `verify_capa`.

Initiating is the right move when a QR reveals a systemic issue,
not a one-off part defect. From `/quality/capas` click
**New CAPA**. Required inputs: problem statement, capa_type
(CORRECTIVE/PREVENTIVE), severity (MINOR/MAJOR/CRITICAL), initial
`assigned_to`. Optional: linked quality reports (link the failing
QR you're reacting to), work order, step, part.

On save, `post_save` fires:
- If severity is MAJOR or CRITICAL → `auto_request_capa_approval`
  runs, blocking work until an approver signs off.
- An initial CONTAINMENT task is auto-created.
- `capa.assigned` event routes a notification to the assignee.

**When to open one.** Don't create a CAPA for every failed QR —
the disposition already records what to do with *this part*. Open
a CAPA when there's a pattern: "we've seen this three times in a
month," "customer complaint traced to a systemic gap,"
"supplier's process changed and we missed it." Section 5's
disposition on INJ-QA-INSPECT-003 was a one-off; CAPA-2024-003
was the right response to the *fifth* nozzle failure in an
order.

### 9e — CAPAs you didn't open (quality gates)

Not every CAPA in your queue was raised by a person. A step can
carry a **quality gate** (`SamplingRuleSet.gate_metric` +
`gate_threshold`): when an aggregate signal crosses its threshold
— say fail rate over a rolling window — the gate fires the actions
configured in `gate_actions`. One of those is `RAISE_CAPA_SCAR`.

A gate-raised CAPA looks different from one you filed:
- **Initiated By is empty**, and notification templates render it
  as *"System"*. That's deliberate — the gate raised it, no human
  did. The trip is automatic and doesn't depend on anyone holding
  `initiate_capa`; an operator's permissions can't suppress a
  quality gate.
- **The problem statement names the gate and the numbers** —
  *"Auto-raised by quality gate 'RS-Nozzle' at step Nozzle
  Inspection: FAIL_RATE_PCT = 25.000 crossed threshold 10.000."*
  With no initiator to ask, the record has to explain itself.
- **It's assigned to a QA Manager** (falling back to a QA
  Inspector), so it lands in a real queue and fires
  `capa.assigned` rather than sitting unnoticed.
- **`gate_capa_type='SUPPLIER'` makes it a SCAR** against the
  lot's supplier instead of an internal CORRECTIVE.

**Reconstructing why it fired.** The `StepGateFiring` row records
the ruleset, metric, computed value, threshold, actions taken, and
`triggered_by_report` — the QR that tripped it. That report's
`detected_by` is the person who was working when the threshold
crossed. So even with no initiator on the CAPA, the chain
CAPA ← firing → report → inspector reconstructs the full story.
Don't read `detected_by` as "the person who caused this" — they
filed one inspection; the gate fired on the aggregate.

---

## 10. Calibration awareness

Real day terms: every measurement is only as good as the gauge you
took it with. If the flow bench you used yesterday was drifting
out of tolerance, everything you signed against it is suspect.
UQMES tracks calibration state and surfaces it in three places for
QA inspectors.

**The current enforcement scope.** UQMES blocks measurements written
against equipment whose status is `OUT_OF_SERVICE` — the picker hides
those options, and `_handle_measurement` refuses the write at the
server (raising `ValidationError` with the equipment name and
reason) even if a stale client somehow selects one. `OUT_OF_SERVICE`
is set by `apply_calibration_result_to_equipment` on a FAIL
calibration.

What's NOT blocked: a measurement written against a gauge that's
still `IN_SERVICE` but whose calibration is *due-soon* or *overdue*.
That's a softer signal — the gauge-nag tile flags those on the home
page as an awareness prompt, but the picker doesn't hide them. If
you find out after the fact that a gauge you used was overdue, use
the QR void flow to walk the reading back.

### 10a — Your gauge-nag tile on the home page

The home page has a **Your gauges** tile (`GaugeNagTile`, backed
by `useGaugeNag`), sitting beside the **My quality actions** panel.
It counts gauges Sarah used in the last 7 days whose calibration is
due within 7 days or already overdue — both windows are
`DEFAULT_USED_WITHIN_DAYS` / `DEFAULT_DUE_WITHIN_DAYS` in
`services/qms/gauge_nag.py`.

Empty state reads *"Nothing you've used in the last 7 days is due
for calibration."* Populated, it reads *"N gauges you used in the
last 7 days need calibration within 7 days"* with the top 3 listed
inline — overdue rows render red as "overdue Nd", due-soon rows as
"due in Nd". On a fresh seed you'll see exactly one:
*"Torque Wrench TW-25 — overdue 15d"*. The **Review calibrations**
button navigates to `/quality/calibrations`.

### 10b — The calibration dashboard

`/quality/calibrations` (`CalibrationDashboardPage`) is the full
QA view.

**Top row — five stat cards** (fresh-seed values in brackets):
- **Equipment** — with calibration records [5].
- **Current** — in calibration [4].
- **Due Soon** — within 30 days [2].
- **Overdue** — past due [1].
- **Compliance** — percent in compliance [80%].

**Below — three panels:**
- **Quick Actions** — three links:
  - *View All Calibration Records* → `/quality/calibrations/records`.
  - *Record New Calibration* → `/CalibrationRecordForm/new`.
  - *Manage Equipment* → `/editor/equipment`.
- **Due Soon** — top 5 records due within 30 days.
- **Overdue** — top 5 records past due, rendered with destructive
  styling and "N days overdue" counter.

Two reports available from the header: **Calibration Due** and
**Checking Aids**.

**The records list** (`/quality/calibrations/records`) is the
browse view behind that first Quick Action. Columns: *Equipment,
Result, Status, Calibration Date, Due Date, Type, Certificate #,
Actions*. It has a **Search calibration records…** box, a
**Sort by…** dropdown, **New Calibration Records**, and per-row
**Edit** / **Delete**. On a fresh seed there are five rows — the
same five gauges as the dashboard's Equipment card, with
*Torque Wrench TW-25* showing Result *Pass* but Status **Overdue**.
That pairing is worth pausing on: the gauge passed its *last*
calibration, it's simply due for the next one. Result and Status
answer different questions.

### 10c — Recording a new calibration

*Record New Calibration* opens the `EditCalibrationRecordFormPage`
in create mode. Fields on `CalibrationRecord`:
- **equipment** (FK) — which piece of equipment this event is for.
- **calibration_date** / **due_date** — when it happened, when
  it's due next.
- **result** — PASS / FAIL / LIMITED.
- **calibration_type** — SCHEDULED / INITIAL / AFTER_REPAIR / etc.
- **performed_by** — user reference.
- **external_lab** / **certificate_number** — if calibrated
  outside.
- **standards_used** — traceability chain.
- **as_found_in_tolerance** — boolean, whether it was already
  within spec before adjustment.
- **adjustments_made** — free-text description.
- **notes**.

On save, if `result=FAIL`, the `apply_calibration_result_to_equipment`
signal sets `Equipments.status = OUT_OF_SERVICE` — a paper flag
you'll see on the equipment detail. It does not block that gauge
from being selected in the measurement picker today; treat the
status as an advisory.

### 10d — The gauge picker during measurement

Section 4c walks a measurement substep. On any substep node
backed by a `MeasurementInput` component, an **Equipment**
dropdown sits next to the value field, pre-populated from the
`MeasurementDefinition` on the definition:
- **Default** equipment (tagged "default" in the picker).
- **Backup** equipment (tagged "backup"), if one is configured.

The choice rides along with the reading — the response persisted
to `StepExecutionMeasurement.equipment` is the actual gauge used,
not the definition's default. That's the audit trail hook: three
months from now you can trace a measurement back to the specific
gauge that produced it, and if that gauge later shows a FAIL
calibration event, you can walk backwards and find every reading
that rode along with it.

**Out-of-service filtering.** Any option whose equipment is
`OUT_OF_SERVICE` at authoring time is hidden from the operator
picker; the configured default falls back to nothing (no auto-
selection) if that default is itself OUT_OF_SERVICE. On the
server side, `_handle_measurement` refuses the write with a
`ValidationError` if `equipment.status == OUT_OF_SERVICE` — so
even a stale client that offers a bad option gets rejected at
the source, not silently accepted. Due-soon and overdue gauges
that are still IN_SERVICE remain selectable and rely on the
gauge-nag tile for awareness.

### 10e — Seeded records on the QA walk exhibits

The demo seed (`seed/demo/manufacturing.py`) creates real
`CalibrationRecord` rows for the equipment used by WO-QA-INSPECT-01
steps (flow bench, torque wrenches, gauges) with dates driven by
an `EQUIPMENT_SPECS.calibration_days` offset — a negative value
means the record is intentionally overdue for demo purposes.
That's why the *Overdue* panel and the gauge-nag tile aren't
empty on a fresh reseed.

---

## 11. The notification bell and inbox

Real day terms: while you're working on one QR, four other things
happen around the shop that you should know about. UQMES pushes
those to two related but distinct surfaces:
- **Inbox** — things you *have to do*: assigned tasks, approvals
  waiting on you, dispositions in your queue. Two related
  surfaces: `/inbox` (`InboxPage`) is a generic tabbed personal
  inbox — CAPA tasks, dispositions, approvals — that anyone with
  commitments can reach; `/quality/inbox` (`QaHomeRoute`) is the
  QA persona's home page, which is broader than a pure inbox
  (adds the gauge-nag tile and the My Actions panel alongside
  the inbox list).
- **Notification feed** (bell → `/notifications`) — things you
  should be *aware of*: events that fired system-wide and your
  subscriptions routed to you.

The distinction matters. Inbox is your work list; missing something
there blocks the shop. The bell is your awareness surface;
missing something there just means you didn't see it.

### 11a — The bell popover

Top-right of the app layout, the **Bell** icon
(`NotificationBell`) shows an unread count in a small red badge
(rendered `99+` if you're really behind).

Clicking opens a popover:
- Header: *"Notifications"* + **Mark all read** button (only when
  there are unread items).
- Body: last 7 items. Unread rows have a blue dot on the left and
  render in normal weight; read rows are muted. Each row shows
  subject + first line of body + relative time (*"just now"*,
  *"5m ago"*, *"2h ago"*, *"3d ago"*).
- Footer: **View all** navigates to `/notifications`.

Clicking a row marks it read *and* navigates to the item's
`rendered_action_url` — the deep link the event was wired with.
`ncr.opened` sends you to the disposition. `fpi.decided` sends
you to the FPI banner on the runtime. `capa.assigned` sends you
to the CAPA detail. If a row has no action URL, it just marks
read.

### 11b — The full feed at /notifications

`/notifications` (`NotificationFeedPage`) — same data as the
popover, up to 100 items, with a persistent **Unread only** filter
toggle. Header reads *"N unread"* or *"All caught up"* when
there's nothing to review. Same click-to-open-and-mark-read
behavior as the bell.

**Preferences** button (top right) navigates to
`/profile/notifications` (`MyNotificationsPage`) — the personal
surface where you can:
- Mute or unmute specific events per channel (in-app, email).
- Add personal subscriptions (*"ping me when X happens on records
  I own"*) — a lighter surface than the admin rule editor at
  `/settings/notifications`.
- Watch specific records to get every event that fires on them.

### 11c — What fires for a QA inspector

On a fresh seed Sarah's bell shows **2 unread**, both
`capa.assigned` — *"CAPA CAPA-2024-005 assigned to you / Major
CAPA, due 2026-08-17"* and the same for CAPA-2024-002. Those are
the only pre-seeded ones; the rest below fire as you work the
walkthrough rather than arriving with the seed.

Events that route to a QA inspector by default (via seeded starter
rules — backfill onto an existing tenant with
`python manage.py setup_notification_rules`):
- **`ncr.opened`** (Section 5c) — a FAIL QR just auto-created a
  quarantine disposition. Routes to the disposition assignee (a
  QA Manager or QA Inspector on the tenant).
- **`fpi.decided`** — an FPI was passed, failed, or waived on a
  step Sarah covers.
- **`capa.assigned`** (Section 9a) — a CAPA task was assigned to
  you. Fires from `post_save(CAPA)`.
- **`capa.ready_for_verification`** (Section 9c) — routes to the
  QA Manager group's inbox after an inspector saves verification
  data.

Non-QA events (production, escalations, receiving) also flow
through the same pipeline; you'll see them if a personal
subscription or a watched-records rule routes one to you.

### 11d — Which surface to check when

- Something specific you're supposed to *finish*? → **Inbox** (or
  the home page tiles, which are the same data grouped).
- Something changed and you want to know? → **Bell / feed**.
- No time to look at either right now? → glance at the bell's
  red badge count. If it's non-zero and stays that way, you're
  ignoring something.

---

## 12. Reading the audit trail

Real day terms: an auditor asks you to reconstruct the history of a
specific part. Or an operator on the shop floor hands you a physical
part and asks "what's the story on this one?" You need to be able
to answer without going into engineering.

### 12a — A rich in-flight arc (INJ-QA-INSPECT-004)

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

### 12b — A closed terminal record (INJ-0042-023)

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

### 12c — Two seed quirks worth knowing

**Double disposition on some parts.** When a FAIL QR fires, its
post-save signal auto-creates a bare OPEN disposition (no type). The
demo seeder's `_enrich_auto_dispositions` pass then gives those bare
NCRs a round-robin type and lifecycle so the demo isn't a wall of
identical OPENs. QR-to-Disposition is legitimately 1:many in QMS
practice (a single QR can spawn multiple lines for different
portions of nonconforming material), so the signal itself is
correct — the quirk is that the seed leaves both records visible
without any hint about which is which.

The QA-walk parts (INJ-QA-INSPECT-004) drop the tag-along at seed
time via `_drop_tag_along_dispositions` in `qa_walk.py`. Older
seed parts (INJ-0038-010 and similar) still show both; read the
intended one (has a `disposition_type` and a `resolution_notes`
paragraph) and ignore the auto-created one (empty type, a
description prefixed *"Auto-created for failed quality report:"*).

**Sparse Activity History in the seed.** Many seeded parts show *"No
audit history"* in the Activity History section because the seed
writes state directly rather than going through the operator runtime.
The trail lives on the linked QRs and dispositions in that case.
Live parts (those you work during a real day) accumulate a normal
history.

---

## 13. Glossary — 15 terms

- **AWAITING_QA** — part state meaning "an operator finished a step
  but a rule says QA looks at it before it moves on." Parked;
  production can't advance it.
- **CAPA** — Corrective And Preventive Action. Structured
  investigation and fix for recurring or high-severity defects.
  Inspectors can initiate CAPAs and work assigned tasks; the
  final effectiveness verification (`verify_capa`) is gated to
  the QA Manager. See Section 9.
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

---

## Appendix — verification status (2026-08-04)

Maintenance note for whoever picks this document up next. It records
*how much of this doc has been checked against the running app*, so the
next pass doesn't re-verify what's done or trust what isn't.

**Method matters, and it's the reason this appendix exists.** Sections
were originally walked by enumerating on-screen **text**, which is blind
to icon-only controls — a Radix checkbox renders as a
`<button role="checkbox">` with no text content, so a text-based sweep
reported "no completion control" on a tab that had three of them.
Re-walks enumerate by **ARIA role** instead, reporting both the
accessible name *and* the visible text, because the two can disagree: a
filter chip's tooltip masked its own visible label. The MCP
accessibility snapshot is more reliable than a hand-rolled DOM script —
it resolves `aria-labelledby` and wrapping `<label>` elements, which a
naive resolver misses.

**Failures cluster in claims about absence** — "there is no control
here", "the button is disabled until you finish", "filtered to your
dispositions", "an Urgent chip". Absence is exactly what a shallow probe
gets wrong, and it's what documentation states most confidently. Treat
every absence claim in this document as unverified until it has been
role-walked.

| Section | Status |
|---|---|
| 1 Home · 2 Receiving | role-verified |
| 3 FPI buy-off | role-walked; blocker found and fixed (`a7ed2b7`) |
| 4 Sampled part | role-verified (2026-08-05) |
| 5 Failed inspection | 5b fields + decision routing verified; 5c chain via tests/seed, live FAIL not driven |
| 6a Open disposition | role-verified |
| 6b–6d Disposition decision/close | role-verified (2026-08-05) |
| 7 Re-inspection | precondition arc verified (2026-08-05); live re-inspect not driven |
| 8 OSP · 9 CAPA · 10 Calibration · 11 Notifications | role-verified |
| 12 Audit trail | not walked (descriptive only) |

**Sections 4–7 role-walk (2026-08-05).** No new blockers. All absence /
structural claims held exactly:
- **4a** — "In-process" chip present (alongside All / Receiving / OSP
  returns / **Urgent**); the sampled row lands on `/workorder/$id/control`,
  where the part reads Awaiting QA · **Sample** · Rework ×1.
- **4b** — confirmed the absence claim: on Control the serial renders in a
  bare `<td>` with no link ancestor (Control does not link to part detail).
  Part detail shows Sampling Required Yes, Sampling Reason *post repair
  verification* (lowercased enum), Rework Passes 1.
- **6a** — `/production/dispositions` is titled **Quarantined Parts**, is a
  parts list with the documented 8 columns and 4 filters, and returned 25
  rows — confirming it is **not** filtered to the signed-in QA despite the
  home tile's count.
- **6b–6d** — editor carries every documented field (incl. Containment
  Action); the five doors are exactly Rework / Repair (AS9100) / Scrap /
  Use As Is / Return to Supplier; Current State offers Open / In Progress /
  Closed; the submit is **Update Disposition**.
- **5b / 7** — verified structurally rather than by driving mutations: the
  Flow-test substep defines barcode-scan + Flow Rate + calibration
  attestation (all required) and routes `QA_RESULT` DEFAULT→Assembly /
  ALTERNATE→Rework; part 004 sits in the reworked-awaiting-reinspection arc
  (AWAITING_QA, rework_count 1, one OPEN + one CLOSED REWORK disposition,
  a FAIL QR). The live FAIL (5c) and live re-inspection were not driven —
  part 003 has no StepExecution until Start Work creates it — but that
  backend chain is the most heavily tested path and is present on seed
  exhibits (006 QUARANTINED, 004's FAIL QR + auto disposition).

**Section 3 was impossible to complete as written.** The seed set
`StepExecution.assigned_to` to the operator, so QA's Start Work → Start
returned `409 assigned_to_other` and the runtime — and therefore the
buy-off — could never be reached. Root cause is a category mismatch:
`FPIRecord` is keyed on `(work_order, step, part_type, designated_part)`,
a **step-level** gate, but its only UI lives inside a **part-level
operator work session**, so QA had to take over the operator's session
to sign a QA gate. The 409, the `workOrder`-query-param dependency, and
the seed's `training_authorization` bypass are all symptoms of that one
mismatch. **Resolved:** the buy-off now takes a second-person
co-signature (operator's station) and there is a QA-native pending-FPI
panel on WO Control; the seed's fabricated `training_authorization` was
replaced with a genuine supervisor-override snapshot. See the
"second-person co-signature rollout" appendix.

**Known-unverified specifics**
- 9c stage 2 — recording the effectiveness *outcome* after the plan is
  created — was never observed; the form would not submit under
  automation.
- 9e describes gate-raised CAPAs. **Now demonstrable:** the Final Test
  sampling ruleset carries a `DEFECTIVE_COUNT ≥ 2` gate (whole work order)
  whose action is `RAISE_CAPA_SCAR` (CORRECTIVE / MAJOR) — the only seeded
  gate that raises a CAPA. A raw ORM-seeded failure does *not* fire it
  (gates fire through the QR service path); tripping a second failing
  final-test inspection in the app is what raises the CAPA. This is also
  the first time the four gate fixes (`45fb36c`, `5a0f089`, `b3369be`)
  run through a real trigger rather than only in tests.
- The FPI exhibit reads *"0 of 2 confirmed / 3 required fields missing"*.
  **This is not missing seed data** — it was investigated during the
  co-sign work and found to be the operator runtime's *fresh-session*
  counter: `confirmedIds` and `responsesBySubstepId` both start empty and
  are only filled by in-session captures; the runtime never hydrates prior
  `SubstepResponse` rows. So no seed change alters that display — the only
  fix would be a frontend feature (replay stored responses into the
  session on load), which is out of scope. Mike's `SubstepCompletion`
  signatures are real; the counter simply doesn't reflect them.
- The first-piece `StepExecution` no longer carries a fabricated
  `training_authorization` (the old `_source: demo_seed_bypass` tell is
  gone). Mike is genuinely not nozzle-qualified in the demo narrative
  (NOZ-CERT level 1, needs level 3), so the honest snapshot is an explicit
  **supervisor override** by Jennifer Walsh — the same shape the real
  start-gate override writes — rather than a pretend pass.

**Open items, not blocking the walk**
- No pattern-based CAPA triggering — repeat NCRs, a trending supplier,
  the same defect three times in a month all raise nothing. Only a
  configured quality gate does.
- RLS policies are registered in `setup_rls.py` but the command has not
  been run (`ENABLE_RLS` defaults false).
- Both tenant-isolation guards (the scoping lint and the RLS coverage
  test) are *detective*, not preventive — they fail after a gap ships.
  The same models were missed by both, so that has already happened.

---

## Appendix — second-person co-signature rollout (2026-08-05)

Section 3's blocker turned out to be an instance of a general pattern, so
the fix generalised into a mechanism. The shape, wherever it applies:

> The person at the keyboard has physically arrived at a step they lack
> the authority to complete. An authorized colleague authenticates
> **inline** at that same terminal, is never logged in, and the act is
> attributed to *them*.

This is the standard DWI / 21 CFR Part 11 second-person pattern, and the
repo already had one instance of it (the training-gate override). It now
lives in `services/core/second_person.verify_second_person`, reached by
viewsets through `SecondPersonMixin` and admitted through the permission
layer by a `cosign_actions` dict.

**Gates converted**

| Gate | Permission | Where the operator meets it |
|---|---|---|
| Training-gate override | `override_training_gate` | pre-existing; source of the extracted helper |
| FPI buy-off | `sign_off_fpi` | review stage of the operator runtime |
| MANUAL decision point | `resolve_step_decision` | `DecisionResolverPanel` in the runtime |

Both new conversions also gained a surface for the *authorized* role to
work their own queue without borrowing anyone's session — the pending-FPI
panel on WO Control being the FPI half.

**Two things worth knowing before converting a fourth.**

*Distinct throttle prefixes are not optional, and neither is the shared
tier.* The failure counter is keyed on the **authorizer's** email,
tenant-wide. With one shared prefix, a QA lead mistyping their password
five times at one station would 429 them out of every gate at every
station in the tenant for 15 minutes. With per-gate prefixes alone, N
gates on separate 5-caps hand an attacker 5×N attempts at one password.
Hence two tiers: a per-gate cap of 5 and a shared cap of 10.

*Authority and labor come apart.* `advance_part_step`'s `operator`
argument served two roles simultaneously — the transition's actor, and
(on a `revisit_assignment='same'` step) the next `StepExecution`'s
`assigned_to`. Under a co-signature those are different people, and
passing the cosigner would have handed a lead who merely walked past a
station the operator's next job. Any gate whose service takes a single
"who did this" argument needs the same audit before conversion.

**Not converted, and why.** The plan named three further targets that do
not survive contact with the code: `approve_disposition` and
`verify_capa` are group-eligibility *markers* consumed by approval
template binding, not action gates (there is no viewset action gated on
either), and OSP `accept`/`reject` are gated on
`change_outsideprocessshipment`, a plain CRUD permission with no
second-person concept. Reading permission *names* is not the same as
finding the gates — see the three-paradigm note in `CLAUDE.md`.
