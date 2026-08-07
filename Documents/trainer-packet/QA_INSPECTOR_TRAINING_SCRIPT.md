# UQMES — QA Inspector Training Script

**Audience:** New QA inspectors (and their leads) learning to use UQMES on the
shop floor.
**Not a sales demo** — this teaches the software, not the pitch. Assume the
trainee knows *inspection*; they need to learn *this tool*.
**Runtime:** ~50 min for the inspector journeys (1–11); the manager gates and
authoring are a separate, optional block.
**Format:** classroom or 1:1 at a workstation, with a printed traveler and part
labels in hand and a barcode reader if you have one.
**Style:** click-runbook. Each journey tells you which button to press and
where you'll land. It is the **trainer's companion to
`UQMES_ONBOARDING_WALKTHROUGH.md`** — same demo work order, same exhibits; the
walkthrough is the self-serve read, this is the taught version. Section
cross-references (§N) point into the walkthrough.

> **Before class:** run `python manage.py seed_demo` and log in fresh once — the
> seed invalidates open sessions. All serials and record numbers are
> deterministic per reseed, *except* the auto-generated `DISP-2026-####` /
> `QR-2026-####` / `OSP-2026-####` numbers, which rotate — teach to the **part
> and journey**, never to a specific auto-number.

> **Screenshots:** this script was rebuilt onto the WO-QA-INSPECT-01 scenario
> and its screenshots have **not been recaptured yet** — see *Refreshing
> screenshots* at the bottom. Until then, teach from the live screen, not from
> images.

---

## Trainer preparation checklist

Do these ~15 min before the trainee arrives. None survive being done live.

- [ ] `python manage.py seed_demo` on the training instance. Wait for a clean
      finish, no red errors.
- [ ] Log in fresh as **`sarah.qa@demo.ambac.com`** (`demo123`). Confirm the
      home page shows the **FPI banner** (two "First piece waiting" rows —
      `WO-2024-0048-A` and `WO-QA-INSPECT-01 · INJ-QA-INSPECT-001`) and an Inbox
      with rows. If the FPI banner is missing, re-seed.
- [ ] Have **Maria's** login ready — `maria.qa@demo.ambac.com` (`demo123`). You
      need her to co-sign the disposition decision in Journey 6; she's the QA
      Manager. Journey 6 does not complete on Sarah's login alone.
- [ ] Print the **Traveler** for **WO-QA-INSPECT-01**: WO Detail
      (`/workorder/$workOrderId`) → **Traveler** button. Verify the header
      barcode scans. (A pre-generated copy lives at
      `artifacts/WO-QA-INSPECT-01_traveler.pdf`.)
- [ ] Print the **Part Labels**: WO Control (`/workorder/$workOrderId/control`)
      → **Part Labels** next to *Pick List*. Cut apart the ones you'll teach
      against: **001, 002, 003, 004, 005, 006**. Also grab **one label from a
      different work order** (a `WO-2024-0048-A` part) — that's the deliberate
      "wrong scan" for Journey 10; a leftover WO-QA-INSPECT-01 label (007/008)
      won't work, since it resolves to this same WO.
- [ ] Spare barcode reader if you have one — a class stalled on hardware loses
      attention fast.
- [ ] Optional: a second browser/incognito window logged in as an operator
      (`mike.ops@demo.ambac.com`, `demo123`) to show the operator/inspector
      hand-off.
- [ ] Spot-check three paths on the training instance so you adjust
      expectations *before* class, not during:
      - Journey 4 (FPI): part **001**'s runtime shows "2 of 2 confirmed" and the
        **Sign off & pass / Fail / Waive** banner.
      - Journey 6 (fail → disposition): entering an out-of-spec flow value on
        **003** derives a FAIL and quarantines it; opening its disposition and
        setting a type as **Sarah** raises the **co-sign** dialog. **This is
        destructive** — it consumes 003's fresh state, the exact state class
        Journey 6 needs.
      - Journey 9 (CAPA): `CAPA-2024-002`'s Verification tab and a
        MAJOR CAPA's Approval tab both load.
- [ ] **Reseed after spot-checking.** The Journey 6 spot-check failed part 003,
      so run `seed_demo` once more and log back in as **Sarah** — the class must
      start with 003 fresh. (Do this last; the reseed also invalidates the
      logged-in sessions.)
- [ ] Read *What to skip in inspector training* at the bottom so you can defer
      out-of-scope questions cleanly.

---

## Roles you'll play

All demo logins use password **`demo123`**.

| Login | Name | Role | You play them in |
|---|---|---|---|
| `sarah.qa@demo.ambac.com` | Sarah Chen | QA Inspector | Everything — the trainee's identity |
| `maria.qa@demo.ambac.com` | Maria Santos | QA Manager | The co-sign in Journey 6; the manager block |
| `mike.ops@demo.ambac.com` | Mike Rodriguez | Operator | Not logged into — his signatures are pre-seeded on part 001's first-piece substeps |

---

## What you'll teach against

One demo work order, **WO-QA-INSPECT-01** (order *QA Inspector Onboarding
Walkthrough* / `ORD-2024-QA-INSPECT`, customer **Midwest Fleet Services**,
Common Rail Injector, Injector Reman process). Each part is parked at the exact
state its journey needs; a reseed restores all of it. (Full detail:
`WO-QA-INSPECT-01_reference.md`.)

| Serial | Journey | State the trainee sees |
|---|---|---|
| `INJ-QA-INSPECT-001` | 4 — FPI buy-off | IN_PROGRESS @ Nozzle Inspection, first piece complete, **PENDING FPI** |
| `INJ-QA-INSPECT-002` | 5 — Sampled inspection | AWAITING_QA @ Nozzle Inspection, **Sample** ("Post-repair verification") |
| `INJ-QA-INSPECT-003` | 6 — Fail + disposition | IN_PROGRESS @ Flow Testing, fresh — you fail it **live** |
| `INJ-QA-INSPECT-004` | 7 — Re-inspection | AWAITING_QA @ Flow Testing, visit 2 (historical FAIL QR + CLOSED REWORK disposition) |
| `INJ-QA-INSPECT-005` | 8 — OSP return | AWAITING_QA @ Nitride Coating, RETURNED from Apex Plating |
| `INJ-QA-INSPECT-006` | 1 (background) | QUARANTINED @ Assembly, bare OPEN disposition on Sarah |

**Two states WO-QA-INSPECT-01 doesn't stage** — a part mid-rework and a
scrapped closed record — are borrowed from the older demo storyline, exactly as
the walkthrough's §12b does:

| Serial | Journey | State |
|---|---|---|
| `INJ-0042-019` | 11 — Rework in flight | REWORK_IN_PROGRESS, disposition IN_PROGRESS |
| `INJ-0042-023` | 11 — Closed record | SCRAPPED, CLOSED SCRAP disposition + FAIL QR trail |

---

## Journey 1 — Log in and read the home page  (walkthrough §1)

**Why:** Everything starts here. Before touching a scanner, the trainee should
recognize each block on the home page and know what it's telling them.

**Setup:** you're already logged in as Sarah, on `/` (the QA home; it also
answers at `/quality/inbox`).

**You see, top to bottom:**
- **Scan box** — one field; anything typed or scanned resolves to a work order
  and drops you on WO Detail.
- **FPI banner** (red border, siren icon) — one row per pending First Piece
  Inspection: step, work order, part, and a waiting-age timer. Buttons **I'm on
  it** (acknowledge) and **Start check** (jump to the WO's Control page). Two
  rows here: the walk's own `INJ-QA-INSPECT-001` and a pre-existing
  `WO-2024-0048-A` row.
- **Inbox chips** — filter the flat list by type: **All · Receiving · OSP
  returns · In-process**. Each carries a count and the age of its oldest item.
- **Urgent** — a red count pill after the chips. It's plain text, *not* a
  filter — don't hunt for a click target.
- **My quality actions** — three tiles (Approvals, CAPA tasks, My dispositions)
  counting work assigned to Sarah; the "N overdue" badge is the signal.
- **Your gauges** — calibration status on gauges Sarah used recently
  (*Torque Wrench TW-25 — overdue*). A compliance cue.

**Watch for:**
- Trainee reads the Inbox count but ignores the chips. Read each chip aloud —
  the shape of the day depends on which one is full.
- Trainee ignores *Your gauges*. That's the compliance signal.

**Checkpoint:** trainee can name each block and say what it's telling them.

---

## Journey 2 — The scanner is your GPS  (walkthrough §1)

**Why:** The barcode reader isn't a data-entry tool; it's a navigator. Every
scan resolves to the **parent work order** and lands you on WO Detail — the
shared surface where exceptions live and the DWI capture path begins.

**You do:** scan the **header barcode** on the WO-QA-INSPECT-01 traveler (or
type `WO-QA-INSPECT-01` in the scan box).

**You land on:** `/workorder/$workOrderId` — **WO Detail** (same landing for QA
and operators).

**You see:** heading `WO-QA-INSPECT-01` with status/priority; an action bar
(**Traveler**, **Start Work**, **Hold**, **Cancel**); and **Overview** /
**Parts** tabs. Overview carries the exception badges (AWAITING QA / QUARANTINED
/ REWORK NEEDED), the OSP card, and the digital traveler; Parts is the
per-part drill-down.

**Then:** scan any `INJ-QA-INSPECT-###` label — you land on the **same** WO
Detail (part → parent WO). For the *part* detail (`/details/Parts/$id`), open it
from the Parts-tab row.

**Teaching point:** the WO is the anchor for scans; per-part detail is one click
away. The **Control** page (`/workorder/$id/control`) is a *different* lens —
lead/manager oversight, per-step status, print buttons, OSP actions — not a scan
destination.

**Checkpoint:** trainee scans the traveler and, unprompted, points at the
exception badges and says what each filters.

---

## Journey 3 — Receiving inspection  (walkthrough §2)

**Why:** Material comes in the door before it's ever a WO part. Receiving is
where a lot is accepted into stock or held.

**You do:** from the home Inbox, click the **Receiving** chip (or go to
`/production/receiving-inspection`).

**You see:** the **Receiving Inspection Queue** — *Lot # · Material · Supplier ·
Qty · Status · Actions*, purchased lots only (5 rows on a fresh seed), each with
**Inspect**. `RCV-INJ-HOLD` (Bargain Bolts, QUARANTINE, "Unqualified supplier")
is a hold exhibit — don't inspect it.

**You do:** **Inspect** `RCV-INJ-0001` (Great Lakes, 250 EA) → the lot detail
shows the CoC panel, the **Sample plan (C0, level III, TIGHTENED): Inspect 29 of
250 · Accept ≤ 0 · Reject ≥ 1**, and **Run Inspection (DWI)**.

**You do:** **Run Inspection (DWI)** → the operator runtime. Enter a passing
**Outer Diameter** (`25.01`), set the result **Pass**, sign, **Confirm &
review**, then **Accept lot**. Toast *"Lot accepted"*; the lot leaves
AWAITING_INSPECTION.

**Teaching point:** receiving uses **Accept lot / Reject lot** (not "Complete
step") — the domain verb. A **Fail** would open the reject-disposition dialog;
that's the supplier-quality path, out of scope for a new inspector.

**Watch for:** the footer names missing required fields but never blocks —
**Confirm & review** stays enabled and just scrolls you to the first gap.

**Checkpoint:** trainee can state the difference between the receiving-only
queue and the unified `/production/incoming` queue (purchased-only vs.
purchased + OSP returns).

---

## Journey 4 — First Piece Inspection buy-off  (walkthrough §3)

**Why:** On a step's first pass, one part is the **first piece**. The operator
runs the DWI on it; QA buys it off before the rest of the batch runs. A failed
or missing FPI blocks the whole batch — it's a production gate.

**You do:** on the home FPI banner, find the `INJ-QA-INSPECT-001 · Nozzle
Inspection` row. Click **I'm on it** (it reads *"Seen by Sarah"*).

**You reach the runtime:** WO Detail → **Start Work** → tick `INJ-QA-INSPECT-001`
under Nozzle Inspection → **Start**. The runtime opens with the inspection
substeps **already signed by Mike** (the operator) and reads **"2 of 2
confirmed"** — the first piece is complete and waiting on QA.

**You see the FPI banner** with three buttons: **Sign off & pass · Fail ·
Waive**.

**You do:** **Sign off & pass** → confirmation dialog (*"By signing off you
attest… conforms. This is recorded against your name and releases the run."*),
add a note, **Confirm sign-off**. The FPI flips to **PASSED**, recorded against
Sarah, and the banner turns green — *"Setup verified — all parts can proceed."*

**Teaching point (segregation of duties):** the substeps were signed by Mike;
Sarah signs the buy-off. Different people — that's the SoD rule. If Sarah had
also signed the substeps, the buy-off would refuse.

**Manager's side:** an inspector who *lacks* `sign_off_fpi` isn't stuck — the
banner offers an inline **co-signature** for an authorized colleague. (Sarah has
it, so she signs directly.)

**Checkpoint:** trainee explains why the FPI is a batch gate, not a per-part
check.

---

## Journey 5 — An inspection sampled to you  (walkthrough §4)

**Why:** Sampling triage is the most common daily task — a rule flags a part,
production parks it, it lands in your Inbox, you clear it.

**Order matters:** do Journey 4 first. The Nozzle Inspection FPI gates the whole
step — on a fresh seed, if 001's FPI isn't signed off yet, 002's runtime shows
*"First Piece Inspection in progress"* and blocks (walkthrough §4c).

**You do:** home Inbox → **In-process** chip → the `Nozzle Inspection · 1 pcs ·
WO-QA-INSPECT-01` row. That's `INJ-QA-INSPECT-002`.

**You see:** it lands on the WO **Control** page; in the Step Status table,
`INJ-QA-INSPECT-002` is `AWAITING_QA` at Nozzle Inspection with a **Sample**
flag. Its sampling reason is *"Post-repair verification"* — it had earlier
rework, so the rule pulls it for extra scrutiny. Open the part detail
(`/details/Parts/$id`) to show **Rework Passes 1**, **Sampling Required Yes**.

**You do:** run the inspection from **WO Detail → Start Work → tick 002 →
Start** (the Control table's rows route steps, they don't launch the runtime).
Work the Nozzle Inspection DWI — the visual points and the measurement — sign,
**Confirm & next** → **Complete step**. The part advances.

**Watch for:** trainee submits a measurement without confirming the gauge and
its cal state. Habit-build: "Which gauge? Is it in cal?" before every capture.

**Checkpoint:** trainee can answer "why this part?" by pointing at the Sample
flag and the sampling reason.

---

## Journey 6 — A live fail and its disposition  (walkthrough §5 → §6)

**Why:** The core of the job — a reading is out of spec, the system quarantines
the part, and someone has to decide what to do with it. This journey has the
one gate a lone inspector can't clear alone, so keep Maria's login ready.

### 6a — Fail it live

**You do:** WO Detail → **Start Work** → tick `INJ-QA-INSPECT-003` (Flow
Testing) → **Start**. (Flow Testing carries an FPI gate too, but the seed
pre-signs it, so 003 opens without an FPI block — you'll see a green
"First Piece Inspection signed off" banner.) On the runtime, enter an
**out-of-spec Flow Rate** — `98` (below the 100 LSL) — scan the part, tick the
flow-bench-in-cal attestation.

**Teaching point:** there's **no Pass/Fail button** here — the verdict is
*derived* from the measurement crossing its spec. The spec is the judge.

**You do:** **Confirm & review** → **Complete step**.

**What this triggers (walk it on screen):** the part goes **QUARANTINED**, a
**FAIL Quality Report** is written, and a **disposition is auto-created** (OPEN,
no type). Sarah's *My dispositions* count ticks up.

### 6b — Work the disposition (needs a co-sign)

**You do:** open the disposition (part detail → **Dispositions** widget → edit,
or `/production/dispositions` → find `INJ-QA-INSPECT-003`). In the editor set
**Disposition Type = REWORK**, **Severity = MAJOR**, a containment action and
resolution note, then **Update Disposition**.

**What happens:** because Sarah is a QA Inspector and lacks `approve_disposition`,
the editor **does not commit** — it opens the **Authorize disposition decision**
co-sign dialog. Choosing a disposition type is the authorized act (AS9100 8.7).

**You do:** enter **Maria's** email (`maria.qa@demo.ambac.com`), draw the
signature, tick *"I authorize this disposition decision,"* enter her password
(`demo123`), **Authorize**. The decision commits **recorded under Maria**, the
disposition goes IN_PROGRESS, and the part moves to REWORK_NEEDED
(rework count +1).

**Teaching point:** this is a *co-signature*, not a login switch — Maria never
logs in; she authenticates on Sarah's screen and the record carries her name. A
QA Manager working it directly commits without the dialog.

**Watch for:** trainee tries to finish on Sarah's login alone and reads the
co-sign dialog as an error. It isn't — it's the gate.

**Checkpoint:** trainee can say who the decision is recorded against, and why an
inspector co-signs rather than being blocked.

### 6c — Closing the disposition (this one's yours)

Note the split before moving on: the *decision* needed a co-sign, but **closing**
the disposition is the inspector's own — Sarah holds `close_disposition`. In the
live flow you'd close it once the rework is done and re-inspected (Journey 7):
from the editor set **Current State = CLOSED** (or the **Close** action). Closing
is refused unless the completion blockers are clear — containment recorded for
MAJOR/CRITICAL, a decision selected, no pending 3D annotations — and a rejected
close still saves your other edits, so you fix the blocker and retry (§6d).

**Teaching point:** authoring the *decision* (co-sign) and *closing* the record
(inspector) are two different permissions on the same disposition.

---

## Journey 7 — Re-inspecting a reworked part  (walkthrough §7)

**Why:** After rework, the part comes back to QA for a second look. Reading the
history *before* re-inspecting is the discipline.

**You do:** home Inbox → the `INJ-QA-INSPECT-004 · Flow Testing` row. Open the
part detail first: it carries the trail — an original **FAIL QR** (flow rate 98)
and a **CLOSED REWORK** disposition (`DISP-QAI-004-REW`), and it's **visit 2**.

**You do:** run the re-inspection from WO Detail → Start Work → 004 → Start.
Enter a passing value this time; complete the step. A second **PASS** QR is
written and the paper trail reads end to end: FAIL → CLOSED REWORK → reworked →
PASS.

**Checkpoint:** trainee reads the part's history and can narrate why it's back.

---

## Journey 8 — OSP return inspection  (walkthrough §8)

**Why:** Some steps are done by a subcontractor. Parts ship out, come back, and
must be re-inspected before rejoining the routing.

**You do:** home Inbox → **OSP returns** chip → the Apex Plating return for
`INJ-QA-INSPECT-005` (shipment `OSP-2026-####` — the number rotates; it's the
Nitride Coating return). Or reach it from `/production/incoming` (the unified
queue, which shows a *Source* column).

**You do:** open the return inspection and work it like any DWI capture.

**Teaching point:** the receiving-only queue is purchased material; the unified
**Incoming Inspection** queue adds OSP returns — same runtime, wider net.

**Checkpoint:** trainee can say why an OSP return needs inspection before it
rejoins the flow.

---

## Journey 9 — Working a CAPA task  (walkthrough §9)

**Why:** When a failure is systemic (a pattern, not a one-off part), it becomes
a CAPA — a structured investigation. Inspectors work assigned CAPA tasks and can
initiate one; the effectiveness verification and management approval are the QA
Manager's.

**You do:** home → *My quality actions → CAPA tasks* (or **CAPAs** in the rail →
`/quality/capas`). Open **CAPA-2024-002** (Pending Verification, 75%).

- **Verification tab** — *"Effectiveness Verification."* Sarah can author the
  verification **plan** (Add Verification → method + success criteria). Recording
  the **outcome** (Complete Verification → CONFIRMED / NOT_EFFECTIVE) needs
  `verify_capa` — a QA Manager, co-signable like the disposition.
- **Approval tab** — a MAJOR/CRITICAL CAPA shows *"Awaiting Approval — work
  cannot begin until approved."* Read-only for Sarah; approving is the QA
  Manager (Journey M below).
- **Initiate** — from a failed QR's **Create CAPA**, when a pattern warrants it.
  Don't open a CAPA for every fail — the disposition already handles *this* part.

**Checkpoint:** trainee can say the difference between a disposition (this part)
and a CAPA (the pattern).

---

## Journey 10 — Calibration, notifications, and the scanner's edges  (walkthrough §10–§11)

**Why:** The ambient signals — is my gauge in cal, what fired for me — and the
ways a scan can go sideways.

- **Calibration** (`/quality/calibrations`): the **Calibration Dashboard**
  (Equipment / Current / Due Soon / Overdue / Compliance). The home *Your
  gauges* tile is the point-of-use nag; a gauge overdue for cal shouldn't be
  used.
- **Notifications** (bell popover / `/notifications`): the feed of what fired
  for Sarah — CAPA assignments, `ncr.opened` on a fail, etc. Show *Mark all
  read* and the filters.
- **Wrong-scan drill:** scan a label from the leftover pile — a part from a
  *different* WO. It resolves to *that* WO, not this one. Teaching point: the
  scan always anchors on the scanned item's parent WO; if you land somewhere
  unexpected, you scanned the wrong label.

**Checkpoint:** trainee checks a gauge's cal state before using it, unprompted.

---

## Journey 11 — Reading finished records  (walkthrough §12)

**Why:** Half the job is *reading* records others created — a part mid-rework,
a scrapped part — and reconstructing the story.

- **Rework in flight:** open `INJ-0042-019` (part detail) — REWORK_IN_PROGRESS,
  a linked FAIL QR and an **IN_PROGRESS** disposition. The story is "failed,
  dispositioned to rework, currently being reworked."
- **Closed scrap record:** open `INJ-0042-023` — SCRAPPED, with a FAIL QR
  (porosity / failed hold pressure) and a **CLOSED SCRAP** disposition carrying
  scrap verification. The story reads backward from the terminal state.

(These two live on the older demo WO-2024-0042-A because WO-QA-INSPECT-01
doesn't stage a mid-rework or scrapped part — the walkthrough borrows the same
`INJ-0042-023` for its §12b.)

**Teaching point:** a part with no linked QR or disposition behind a
QUARANTINED/SCRAPPED status is a red flag — how did it get there without a
record?

**Checkpoint:** trainee opens a closed record and narrates the sequence that
produced it.

---

## Optional manager block  (walkthrough §13)

If a lead or QA Manager is in the room, show the *other side* of the gates the
inspector journeys handed up — log in as **Maria** (`maria.qa@demo.ambac.com`):

- **`/approvals`** — the approvals center: *Awaiting My Approval*, *By Type*,
  *My Submitted Requests*.
- **Authorize a disposition** directly (holds `approve_disposition` — no
  co-sign dialog).
- **Verify a CAPA's effectiveness** on `CAPA-2024-002` (Complete Verification →
  CONFIRMED / NOT_EFFECTIVE). Note the dependency: the verification *plan* must
  already exist (Journey 9 authors it) — on a truly fresh seed there's no plan
  yet, so no **Complete Verification** button appears until one is added (§9c/§13c).
- **Approve a MAJOR CAPA** — `CAPA-2024-005`, which sits in her queue; Submit
  Response → Approve with signature + password (§13d).
- The co-sign-vs-queue distinction (§13e): *is someone blocked at a gate right
  now (co-sign), or did a request land in my queue to action later (approval)?*

---

## What to skip in inspector training

Defer these cleanly — they're real but not a new inspector's job:

- **Process / DWI authoring** (walkthrough §14) — building processes,
  measurements, sampling rules, and substeps is a QA-manager / process-author
  task. If asked, point to §14 and move on.
- **Change control, supplier quality, part approvals** — adjacent QMS surfaces,
  not day-one inspection.
- **The manage-all-records editors** (`/editor/qualityReports`, etc.) — an
  inspector's QRs reach them through the part and disposition (§5/§6), not by
  trawling the register. The register itself is §15 reading, not a task.
- **Exact record numbers** — `DISP-2026-####` / `QR-2026-####` / `OSP-2026-####`
  rotate on reseed. Never make a trainee memorize one.

---

## Refreshing screenshots

This script was rebuilt onto the WO-QA-INSPECT-01 scenario; its screenshots have
not yet been recaptured and the inline image references were removed rather than
ship stale ones. To add them:

1. Start the dev servers; fresh `seed_demo`; log in as **Sarah**.
2. Capture at **1440×900** — the training standard.
3. One tight shot per journey (crop out browser chrome).
4. Save under `Documents/screenshots/qa_inspector_training/` and add the
   `![alt](…)` reference at the end of each journey.
5. The demo tenant is fictional, but glance for accidental real names before
   committing.
6. Rule of thumb: if a screenshot ever stops matching the live screen, the
   screenshot is wrong, not the software — recapture it.
