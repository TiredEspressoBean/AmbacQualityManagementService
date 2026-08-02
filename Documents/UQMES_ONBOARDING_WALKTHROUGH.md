# UQMES onboarding walkthrough — a fresh work order, end to end

**What this is.** A click-by-click walk of one full work order lifecycle
on the Demo Company tenant, from a lot arriving at receiving through
the last part shipping. Written for someone who has just been given
UQMES access and needs a concrete "here is what the day looks like"
tour. Every URL, button label, and toast in this doc was verified
against the running instance; if you spot a mismatch, the software
changed after this was written.

**What it isn't.** A training curriculum, a certification checklist, or
a manual of edge cases. Fails and gotchas appear only when they're
part of the arc you're walking. For the QA-inspector training frame
with role-play, sampling archetypes, and checkoff sheets, see
`QA_INSPECTOR_TRAINING_SCRIPT.md`.

**Arc:**
1. Setup — logins and where each role lands
2. Receiving inspection — a lot of Common Rail Injectors arrives
3. Create a work order against the incoming stock
4. First Piece Inspection gate — the WO's first step opens
5. Happy path — the first serial through the early process steps
6. OSP send-out — Nitride Coating goes out to Apex Plating
7. OSP return + inspection — the shipment comes back
8. Fail path — a serial fails Flow Testing
9. Working the disposition — QA picks REWORK and signs
10. Rework loop and re-inspection — the failed serial passes on visit 2
11. Closing the WO — last parts complete, traveler prints
12. Glossary

**Roles you'll play.** All passwords are `demo123`.

| Email | Name | Role | Uses in this walk |
|---|---|---|---|
| `admin@demo.ambac.com` | Alex Demo | Tenant Admin | Section 3 — create the WO |
| `mike.ops@demo.ambac.com` | Mike Rodriguez | Operator | Sections 5, 6, 7, 8, 10 |
| `sarah.qa@demo.ambac.com` | Sarah Chen | QA Inspector | Sections 2, 4, 8, 9 |
| `maria.qa@demo.ambac.com` | Maria Santos | QA Manager | Section 9 sign-off (if needed) |
| `jennifer.mgr@demo.ambac.com` | Jennifer Walsh | Production Manager | Section 11 — WO close |

---

## 1. Setup — log in, note where each role lands

Log out (top-right avatar → **Log out**) and re-log in as each role
below in turn to see the landing pages before the walk begins. You'll
switch users repeatedly through this doc; keeping the landings
familiar avoids "wait, why am I looking at a different page?" moments
later.

**Sarah (QA Inspector)** — `sarah.qa@demo.ambac.com` — lands on the
**QA home** at `/`. You'll see: scan box, an FPI banner if any
first-piece is pending, a compact **Inbox** with chips (All /
Receiving / OSP returns / In-process), a **My Quality Actions** block
with approvals / CAPA tasks / dispositions counts, and a **Your
Gauges** tile for calibration status.

**Mike (Operator)** — `mike.ops@demo.ambac.com` — lands on the
**Operator home** at `/`. Different from QA's home: a work-order
queue in shop priority order, a scan box that resolves to WO Detail,
and personal actions.

**Alex (Tenant Admin)** — `admin@demo.ambac.com` — lands on a generic
tracker home; use the sidebar to reach `/production/work-orders/new`
when Section 3 asks.

**Jennifer (Production Manager)** — `jennifer.mgr@demo.ambac.com` —
lands on the WO Control Center (`/workorders`) — the cross-WO
oversight lens.

**Maria (QA Manager)** — `maria.qa@demo.ambac.com` — same home
surface as Sarah with different permissions (can sign off FPI, can
approve dispositions).

**Session note.** Logging out ends the browser session; other tabs to
the app also lose auth. If you re-seed the database mid-walk (Section
11 doesn't need it), passwords are preserved but you'll need to
re-log in.

---

## 2. Receiving inspection — a lot of injectors arrives

Play as **Sarah (QA Inspector)**.

The demo seed has five open Common Rail Injector lots sitting in the
receiving queue. In a real day the person driving the forklift scans
the lot label as the pallet comes off the truck; in this walk, click
into a lot from the queue.

### 2a — Open the receiving queue

**You go to:** sidebar → *Production* → *Work Orders* is what you
want later — but for now, either type `/production/receiving-inspection`
into the URL bar, or on Sarah's home page click the **Receiving**
chip on the Inbox (it shows a count like *Receiving 5 · 7d*), which
takes you into the same queue filtered to receiving rows.

**You land on:** `/production/receiving-inspection` — the **Receiving
Inspection Queue**.

**You see:** a table with columns *Lot # · Material · Supplier · Qty ·
Status · Actions*. Each row has an **Inspect** button. The demo seed
shows:
- `RCV-INJ-HOLD` — Bargain Bolts LLC, 30 EA, **QUARANTINE** ("Unqualified
  supplier"). Not for this walk; that row exists to demonstrate the
  supplier-qualification hold state — see it and move on.
- `RCV-INJ-0001` through `RCV-INJ-0004` — Great Lakes Diesel, all
  **AWAITING_INSPECTION**, various quantities (250 / 60 / 500 / 40 EA).

### 2b — Open a lot for inspection

**You click:** **Inspect** on the `RCV-INJ-0001` row (250 EA, Great
Lakes Diesel).

**You land on:** `/production/receiving-inspection/$lotId` — the lot
detail page.

**You see:**
- Header: `RCV-INJ-0001` · status badge `AWAITING_INSPECTION` ·
  **Documents** button (attach cert of conformance, packing slips, etc.).
- Subheader: `Common Rail Injector · Great Lakes Diesel · qty 250`.
- **"No Certificate of Conformance captured for this lot."** with an
  **Upload CoC** button. In a real receiving workflow the CoC is
  uploaded here first, before the sample plan runs; the demo lets you
  proceed either way.
- **Sample plan (C0, level III, TIGHTENED)** panel showing:
  `Inspect 29 of 250 · Accept ≤ 0 · Reject ≥ 1`. This is a C=0 (zero-
  acceptance) sampling plan at inspection level III with tightened
  switching — any single defect rejects the whole lot. The 29 comes
  out of the AQL table for level III at this lot size.
- A note: **"This receiving step has digital work instructions. Run
  the inspection through the operator runtime."**
- **Run Inspection (DWI)** button.

### 2c — Run the DWI inspection

**You click:** **Run Inspection (DWI)**.

**You land on:** the operator substep runtime, scoped to the material
lot:
`/operator/steps/$stepId/substeps?execution=…&material_lot=$lotId&at=0`.

**You see:** the DWI-guided form for *Inspect incoming material*.
Fields, in order:
- **Scan the lot / packing slip** — barcode / QR input, optional.
- **Outer Diameter** (`RCV-01`) — required measurement, spec
  `25 +0.05 / −0.05 mm`, numeric input in mm.
- **Incoming inspection result** — required, three buttons: **Pass**,
  **Fail**, **Pending**.
- **Inspection sign-off** — required, "Sign as detected by" button.
- **Defects found** — optional, "Add defect" button. Only fill this
  in if you're rejecting.

The footer bar reminds you of missing required fields (e.g. *"3
required fields missing — Outer Diameter, Incoming inspection result,
…"*) and the **Confirm & review** button stays disabled until they're
all set.

### 2d — Pass the lot

For the walk, enter a passing value and sign:
- **Outer Diameter**: `25.01` (within spec).
- **Incoming inspection result**: **Pass**.
- **Sign as detected by**: click to sign as Sarah.

**You click:** **Confirm & review**, then the final **Complete**
button on the review pane.

**What happens on the backend:** the lot moves out of
`AWAITING_INSPECTION` and becomes stock available for a work order.
The `SamplingTriggerManager` updates its state (C=0 PASS), the
receiving audit log is written, and any downstream sampling
analytics increment.

### 2e — Confirm on the queue

**You go to:** sidebar → back to `/production/receiving-inspection`.

**You see:** `RCV-INJ-0001` is no longer `AWAITING_INSPECTION`; its
status has moved. The lot is now available inventory for Section 3.

**If you fail a lot instead** — click **Fail** in step 2d, add a
defect (Type + Description), and complete. That opens the Reject
disposition dialog which asks for a disposition type (e.g. RETURN_TO_
SUPPLIER) with severity and quantity. This walk doesn't use the fail
path for receiving; you'll see the fail path at Flow Testing in
Section 8.

---

## 3. Create a work order

_Section pending — will walk `/production/work-orders/new` and cover
product selection, quantity, priority, due date, and submit._

---

## 4. First Piece Inspection gate

_Section pending — operator starts the first serial, `FpiStatusBanner`
surfaces "Required · Start FPI", QA signs off, run releases._

---

## 5. Happy path — early process steps

_Section pending — Component Grading, Disassembly, Cleaning batch,
Assembly. In-spec captures, PASS at each QA gate._

---

## 6. OSP send-out — Nitride Coating

_Section pending — WO Control OSP panel, Send out to Apex Plating,
create shipment, track by shipment id._

---

## 7. OSP return and return inspection

_Section pending — receive shipment back, run return inspection via
`api_OutsideProcessShipments_sample_plan_retrieve`, complete._

---

## 8. Fail path — a serial fails Flow Testing

_Section pending — operator captures out-of-spec value, submits, FAIL
fires, part → QUARANTINED, auto-disposition appears on the part
detail._

---

## 9. Working the disposition (REWORK)

_Section pending — QA opens `/production/dispositions`, picks the
auto-created NCR, sets type=REWORK, containment action, resolution
notes, signs Update Disposition._

---

## 10. Rework loop and re-inspection

_Section pending — part re-visits Flow Testing (visit_number = 2),
operator captures in-spec value, PASSes, part → READY_FOR_NEXT_STEP._

---

## 11. Closing the work order

_Section pending — last parts complete, WO status flips to COMPLETED,
Traveler print button on WO Detail, final report generation._

---

## 12. Glossary

_Section pending — ~15 must-know terms trimmed from
`QA_INSPECTOR_TRAINING_SCRIPT.md`'s glossary. AWAITING_QA, CoC, CAPA,
Disposition, DWI, ERP id, FPI, LSL/USL, NCR, OSP, Quarantine, QR,
SamplingTriggerManager, StepExecution, Traveler._
