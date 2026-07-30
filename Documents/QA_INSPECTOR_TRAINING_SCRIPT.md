# UQMES — QA Inspector Training Script

**Audience:** New QA inspectors learning to use UQMES on the shop floor.
**Not a sales demo** — this teaches the software, not the pitch. Assume the
trainee knows *inspection* and needs to learn *this tool*.
**Runtime:** ~45 min for the full walk; each journey ~5 min.
**Format:** classroom or 1:1 at a workstation with a real barcode reader and
a printed traveler + printed part labels in hand.
**Style:** click-runbook. Each step tells you which button to press and where
you'll land. The trainer follows the doc literally.

> **Before class:** run `python manage.py seed_demo` and log in fresh once —
> the seed invalidates open sessions. All serials and WO numbers below are
> deterministic, so what's printed matches what's on screen.

> **Screenshots** live in `Documents/screenshots/qa_inspector_training/`.
> One representative shot per journey — see the *Refreshing screenshots*
> block in the trainer prep. If a screenshot no longer matches what the
> trainee sees, the screenshot is wrong, not the software.

---

## Trainer preparation checklist

Do these 15 min before the trainee arrives. Not one of them survives being
done live.

- [ ] `python manage.py seed_demo` on the training instance. Wait for clean
      finish, confirm no red errors in the output.
- [ ] Log in fresh as **`sarah.qa@demo.ambac.com`** (`demo123`). Confirm the
      home page shows the FPI banner (WO-2024-0048-A, Nozzle Inspection)
      and an Inbox with rows. If the FPI banner is missing, re-seed.
- [ ] Print the **Traveler** for **WO-2024-0042-A**: open the WO detail
      (`/workorder/$workOrderId`) → **Traveler** button in the header.
      Verify the header barcode scans on your reader.
- [ ] Print the **Part Labels** batch for WO-2024-0042-A: open the WO
      control page (`/workorder/$workOrderId/control`) → **Part Labels**
      button next to *Pick List*. Cut apart the five you'll teach against
      (018, 021, 017, 019, 023). Keep the rest of the sheet as a
      "wrong-scan" pile for Journey 11.
- [ ] Spare barcode reader if you've got one — the primary can fail and a
      class stalled on hardware loses attention fast.
- [ ] Optional: second browser or incognito window logged in as an
      operator (`mike.ops@demo.ambac.com`, `demo123`) if you want to
      demonstrate the operator/inspector hand-off.
- [ ] Spot-check three UI paths on the training instance:
      - Journey 4: saving a disposition with type=REWORK actually flips the
        part's status to REWORK_IN_PROGRESS.
      - Journey 5: the part-detail page's "Dispositions" and "Quality
        Reports" widgets both populate for INJ-0042-017 and INJ-0042-019.
      - Journey 9: clicking through a Cleaning-step entry reaches a batch
        record UI.
      Any that misbehave, adjust the expectation before class rather than
      during it.
- [ ] Read *What to skip in inspector training* at the bottom of this doc
      so you can defer out-of-scope questions cleanly.

### Refreshing screenshots

Screenshots live in `Documents/screenshots/qa_inspector_training/`. To
refresh:

1. Start dev servers (`bun run dev`, `python manage.py runserver`).
2. Fresh `seed_demo`. Log in as **Sarah**.
3. Capture at **1440×900** viewport — the training standard.
4. One shot per numbered filename referenced in the doc.
5. Crop tight. Full-page screenshots waste trainee attention on chrome.
6. The demo tenant is safe (fictional customers), but glance before you
   commit to catch any accidental real names.

---

## What you'll teach against

All five training serials live on **WO-2024-0042-A** (Midwest Fleet, 24
injectors, In Progress).

| Serial | Journey | State the trainee will see |
|---|---|---|
| INJ-0042-018 | 3 — Sampled inspection | IN_PROGRESS @ Final Test |
| INJ-0042-021 | 3 — Sampled inspection | AWAITING_QA @ Flow Testing (sampling flag) |
| INJ-0042-017 | 4 — Fail + disposition | QUARANTINED, FAIL Flow Testing, live open disposition |
| INJ-0042-019 | 5 — Rework in flight | REWORK_IN_PROGRESS, disposition IN_PROGRESS |
| INJ-0042-023 | 6 — Closed record | SCRAPPED |

Plus **WO-2024-0048-A** (Northern Trucking, PENDING) for Journey 8 — First
Piece Inspection.

---

## Journey 1 — Log in and read your home page

**Why:** Everything starts here. Before we touch a scanner, the trainee
should recognize each block on the home page and know what it means.

**Setup:** you (the trainer) are already logged in as Sarah.

**You see, from top to bottom:**

- **Scan box** — one input field. Anything you type or scan resolves to a
  work order.
- **FPI banner** (red border, Siren icon) — appears when there's a First
  Piece Inspection waiting. "First piece waiting — Nozzle Inspection ·
  WO-2024-0048-A". Age timer on the right ("14d waiting"). Buttons: **I'm
  on it** (acknowledge) and **Start check** (jump to the WO's control
  page).
- **Chips** — filter the Inbox by row type:
  - **All** (count) — everything.
  - **Receiving** — incoming lots awaiting incoming inspection.
  - **OSP returns** — parts back from outside processes, need inspection
    before rejoining the routing.
  - **In-process** — parts parked mid-routing waiting on QA (AWAITING_QA
    status, sampling firings).
- **Urgent** — highlighted rows across all types.
- **MY QUALITY ACTIONS** — approvals, CAPA tasks, dispositions assigned
  to you personally. The "N OVERDUE" badge is the important part.
- **YOUR GAUGES** — recent calibration status on gauges Sarah has used.
  "Torque Wrench TW-25 — overdue 16d" is a compliance problem waiting.

**Watch for:**
- Trainee reads the Inbox count but ignores the chips. Slow them down and
  read each chip aloud — the shape of your day depends on which chip is
  full.
- Trainee ignores YOUR GAUGES. That's the compliance signal.

**Checkpoint:** trainee can name all five blocks and say what each is
telling them.

![Sarah's home page — scan box, FPI banner, Inbox with chips, quality
actions, gauges](screenshots/qa_inspector_training/01-qa-home.png)

---

## Journey 2 — Scanner as your GPS

**Why:** The barcode reader is not a data-entry tool; it's a navigator.
The QA-flavored scanner drops you straight on the working surface — no
extra clicks to hunt for the exceptions list.

### 2a — Scan the traveler header

**You do:** point the reader at the **Code 128 barcode on the header** of
the WO-2024-0042-A traveler in your hand. Pull the trigger.

**You land on:** `/workorder/$workOrderId/control` — the **WO Control**
page. (Operators scanning the same barcode land on `/workorder/$id`;
your Home page's ScanBox is configured with `dest="control"` so QA gets
the inspection surface directly.)

**You see:**
- Heading: `WO-2024-0042-A` · badges: `In Progress` · `High` priority
- **Pick List** and **Part Labels** print buttons (top-right).
- **Outside processing** panel — lots at vendors, with **Inspect** /
  **Send out** / **Receive back** actions.
- **Exceptions on this WO** — every open quarantine on this work order,
  one card each, with an **Open disposition** button. This is where the
  bulk of QA click-work starts.
- **Step status** — the shop-floor grid: per-part rows with current
  step, status, operator, sampling flag, controls.

### 2b — Scan a part label

**You do:** scan any INJ-0042-* label. Pull the trigger.

**You land on:** the same page — `/workorder/$workOrderId/control`.
UQMES resolves the part → its parent work order → drops you on the
Control page. **Part scans and WO scans both anchor on the WO Control
page for QA.**

**Teaching point:** the WO is the anchor. Per-part detail is one click
away from the Step Status table row.

**Checkpoint:** trainee scans the traveler and, unprompted, identifies
the Exceptions panel and the Step Status grid.

![WO-2024-0042-A control page — outside processing, exceptions,
step-status
grid](screenshots/qa_inspector_training/02-wo-control-page.png)

---

## Journey 3 — Working an inspection that was sampled to you (INJ-0042-021)

**Why:** Sampling triage is the most common daily task. A rule fires,
production parks the part, it lands in your Inbox, you clear it.

### 3a — Find it in your Inbox

**Go to:** home page (click the sidebar logo).

**You see:** the Inbox. Click the **In-process** chip.

**You find:** a row for **Flow Testing · 1 pcs · Common Rail Injector ·
WO-2024-0042-A · WO due 2026-07-31**. That's INJ-0042-021.

### 3b — Click into the WO Control page

**You click:** the Inbox row.

**You land on:** `/workorder/$workOrderId/control` — you already saw this
page in Journey 2.

**You see, in the Step Status table:**
- INJ-0042-021 · step **6. Flow Testing** · status **Awaiting QA** ·
  **Sample** flag in the flags column.

The **Sample** flag is the sampling reason surfaced. If a trainee asks
"why me, why this part?" — this is the answer.

### 3c — Open the part

**You click:** the ExternalLink icon on the INJ-0042-021 row (or the row
chevron to expand step history inline — teach both).

**You land on:** `/details/Parts/{id}` — the part detail page.

**You see:**
- Header: **INJ-0042-021 · Common Rail Injector** (no UUIDs, ever).
- **General**: Serial, Status, Part Type (clickable).
- **Production**: Order (clickable), Current Step (`Flow Testing`,
  clickable), Work Order (`WO-2024-0042-A`, clickable — goes to Control).
- **Quality Control**:
  - Latest Inspection — either "PASS · 0 open defects" (if the flow test
    already passed the last time) or "—" (no QR yet).
  - Has Open Defect · Needs QA · QA Completed · Rework Passes ·
    Sampling Required · Sampling Reason.
- **Documents**: DWG-CRI-8800 (the drawing for this part type).
- **Activity History** (may be sparse in the seed — read what's there).

### 3d — Open the DWI capture

**You do:** run the actual flow test on the bench. Read the value.

**You return to:** UQMES. From the part detail page, click the **Work
Order** link (`WO-2024-0042-A`) in the Production block. You land on
`/workorder/$workOrderId` — the Detail page (same destination QA scans
route to).

**On the Detail header, you click:** **Start Work**.

**A dialog opens:** parts grouped by step, actionability-sorted — the
group with **unstarted / next-in-line** work floats to the top, so the
row you want is right there:
- Group heading: **Flow Testing**.
- Row: **INJ-0042-021 · Awaiting QA · Sample**.

**You click the row** (or the Select button) and hit **Start**. The
dialog closes and navigates to `/operator/steps/{stepId}/substeps` — the
**Operator runtime**. That's the DWI capture surface.

**On the runtime you see:** the substep sequence for this step. Because
INJ-0042-021 is `AWAITING_QA` at Flow Testing, the sequence is the
sampled **inspection** substep set (not production instructions). Each
substep is either an instruction to acknowledge or a measurement to
capture. The header shows the part (`INJ-0042-021`), the step (`Flow
Testing`), and the substep count (`X of N`).

**You capture:** for each measurement substep, enter the value you read
on the bench. Pass/fail is evaluated against the spec attached to that
substep — you'll see the tolerance right on the substep. Advance with
**Next**. If a value is out of spec, the runtime surfaces the fail-path
disposition options at that substep — that's the branch Journey 7 covers
in more depth.

**Watch for:**
- Trainee submits a value without confirming which gauge they used and
  whether it's in cal. Habit-build: "Which gauge? Is it in cal?" before
  every capture.
- Trainee misreads spec tolerance display. `± 0.5` means the number can
  be nominal + or − that much, not "exactly this."
- Trainee clicks **Start Work** and gets a dialog that seems empty. That
  means every part is either already in flight elsewhere or none are
  claimable by them — check the exceptions chip first (below QA
  Progress) and the Parts tab filter.

**Alternative click path (from the Exceptions chip):** on Detail, the
**Exceptions on this WO** card lists a clickable **Awaiting QA · N**
chip. Click it → the left panel flips to the **Parts** tab, pre-filtered
to `AWAITING_QA`. Same INJ-0042-021 row, plus any other parts in that
queue. This is faster than Start Work when you already know which
queue you're working from.

**Checkpoint:** trainee can explain, in their own words, the difference
between "measurement in spec" and "part passed." If they conflate the
two, walk it again.

![Part detail with Quality Control section and linked
records](screenshots/qa_inspector_training/03-part-detail.png)

---

## Journey 4 — Working a fail with an open disposition (INJ-0042-017)

**Why:** When a part fails, the disposition is where "reject" turns into
"and here's what we do about it." Learn the click path to a live open
disposition.

### 4a — Reach the disposition

**Two paths — teach both:**

**Path A — via the Dispositions list (fastest when you're already
thinking "which quarantined parts do I have?"):**
1. **You go to:** *Production → Dispositions* in the sidebar →
   `/production/dispositions`. The page is titled **Quarantined Parts**
   and it lists every part that has an open or historical disposition.
2. **You find** the INJ-0042-017 row (Status: Quarantined, Step: Flow
   Testing).
3. **You click:** the **Edit Disposition** button on the right.

**Path B — via the part:**
1. **You open** the part detail page for INJ-0042-017.
2. **You see:** the **Dispositions** widget listing the linked
   dispositions with numbers, states, types.
3. **You click:** the current IN_PROGRESS disposition (DISP-2026-000015
   in the seed).

Both land you at: `/dispositions/edit/{id}` — the **Disposition editor**.

![INJ-0042-017 part detail — QUARANTINED status with linked Quality
Reports and Dispositions
widgets](screenshots/qa_inspector_training/04-part-017-quarantined.png)

### 4b — Read the disposition

**You see:**
- Heading: `Disposition #DISP-2026-000015` · state badge · severity
  badge.
- **NCR Report** / **Deviation Request** buttons — for escalating out.
- Form:
  - **Current State** (dropdown)
  - **Disposition Type** — the decision (REWORK / USE_AS_IS / SCRAP /
    REPAIR / RETURN_TO_SUPPLIER)
  - **Severity** (MINOR / MAJOR / CRITICAL)
  - **Assigned To** — who owns the decision
  - **Description** — pre-filled with the auto-created text
  - **Resolution Notes** — where the trainee writes what they did
  - **Resolution Completed By** / **at** — signed off when closed
  - **Related Part** and **Quality Reports** — the linked records
- Right sidebar: **Part Information** with serial, type, status, order.
- **Quality Reports (1)** panel — a link to the linked FAIL QR.
- **3D Annotations** — "All complete" or a link to annotate.

### 4c — Walk the three common doors

**Teaching moment (no submit — just read):**
- **REWORK** — send back through the rework loop. Journey 5 shows this
  in flight.
- **USE_AS_IS** — customer accepts with a concession. **Not a shortcut.**
  A concession reference must exist.
- **SCRAP** — terminal. Journey 6 shows one.

Two more doors exist in the enum but come up less often: **REPAIR** and
**RETURN_TO_SUPPLIER**.

### 4d — Decide (training exercise)

**You do:** pick **REWORK** in the Disposition Type dropdown. Fill in
Resolution Notes: `Retest after cleaning; suspect fouling in seat.`

**You click:** **Update Disposition**.

**You see:** the state auto-transitions to IN_PROGRESS (may already be
there from the auto-creation).

**You return to:** the part detail page — the Dispositions widget now
shows the updated type; the part's status is REWORK_IN_PROGRESS.

**Watch for:**
- Trainee reflexively picks USE_AS_IS to close the ticket faster. Stop
  them cold. Ask: "Where's the customer concession number?"
- Trainee writes vague resolution notes ("Reworked and OK"). Ask them:
  two years from now during a field-return investigation, would that
  note help or hurt?
- Trainee tries to edit the original FAIL QR to make it PASS. It doesn't
  work by design — the *asking* is the teaching moment. You add new
  records; you don't rewrite history.

**Checkpoint:** trainee can articulate the three common disposition
doors and describe what each **commits the shop to do next**, not just
recognize the names.

![Disposition editor for INJ-0042-017 —
form, part sidebar, linked
QR](screenshots/qa_inspector_training/04-disposition-editor.png)

---

## Journey 5 — Reading a rework in flight (INJ-0042-019)

**Why:** Sometimes you inherit a fail that's already been dispositioned.
Learn to read the trail so you know what QA still owes.

### 5a — Reach the part

**You click:** any INJ-0042-019 entry — Inbox, Exceptions panel on the
WO Control page, or scan the part label.

**You land on:** the part detail page or the disposition editor,
depending on where you started. Both are fine.

### 5b — Read the history

**On the part detail page you see:**
- Status: **REWORK_IN_PROGRESS**.
- Current Step: **Rework**.
- Quality Reports widget: the original FAIL at Nozzle Inspection.
- Dispositions widget: **DISP-QR-0042-019-NI · IN_PROGRESS · REWORK ·
  MAJOR** — the approved rework decision.

![INJ-0042-019 part detail — REWORK_IN_PROGRESS status with linked QR
and disposition](screenshots/qa_inspector_training/05-part-019-rework.png)

### 5c — Understand what's owed

- The rework step is currently owned by production. QA's job is the
  **re-inspection** at the same step the part originally failed at.
- Once the rework completes, the part re-enters the routing at that
  failed step. You inspect it again — this is a re-inspection, not a
  first inspection.
- **visit_number** on the step execution differentiates the original
  visit (1) from the re-inspection (2+). All visits stay in history.

### 5d — What if the re-inspection also fails?

Don't try to hide it. A fail after rework almost always becomes a scrap
decision — but that's the *next* disposition, not an edit of this one.

**Watch for:**
- Trainee sees IN_PROGRESS and assumes QA's job is done. It's not. The
  disposition tracks the *decision*; the *work* isn't done until the
  re-inspection passes.
- Trainee tries to re-inspect ignoring the original defect. Have them
  read the original fail *before* the re-inspection so they know
  specifically what to look at.

**Checkpoint:** trainee can explain what `visit_number` means and
describe what should happen if a re-inspection also fails.

---

## Journey 6 — Reading a closed scrap record (INJ-0042-023)

**Why:** Not every part comes back. Learn what a terminal record looks
like so you know when to stop looking for a way to save one.

### 6a — Find it

**You go to:** `/workorder/$workOrderId/control` for WO-2024-0042-A. In
the Step Status table, filter by status **Scrapped** (or find
INJ-0042-023 in the list).

**You click:** the ExternalLink icon on the row.

**You land on:** the part detail page.

**You see:**
- Header: **INJ-0042-023 · Common Rail Injector**.
- Status: **SCRAPPED**. Current Step: `-`.
- Dispositions widget: the terminal disposition with type=SCRAP.
- Quality Reports widget: the QR that led to the decision.
- Activity History: the trail.

![INJ-0042-023 part detail — SCRAPPED terminal record with linked scrap
disposition and QR](screenshots/qa_inspector_training/06-part-023-scrap.png)

### 6b — Read the trail

Walk it end-to-end. Every state change is timestamped and signed.

**Teaching point:**
- SCRAPPED is **terminal by design**. If a scrapped serial shows up on
  your bench, something's wrong (mislabel, wrong bin). Stop and ask.
- The record is still readable — you can see why it was scrapped, who
  decided, and when. That's the audit trail.

**Watch for:**
- Trainee treats the closed record as unimportant ("nothing to do
  here"). Wrong instinct. The scrap decision is a data point that feeds
  SPC and defect analysis — understanding *why* this one was scrapped
  informs whether the next one should be.
- Trainee asks "what if we could rework it?" — no. Terminal is terminal.
  If reworking a scrapped part were an option, the disposition would
  have been REWORK, not SCRAP.

**Checkpoint:** trainee can walk the scrapped part's history and
identify the specific quality report, disposition, and sign-off that
made it terminal.

---

## Journey 7 — Filing a fresh fail you caught yourself

**Why:** Scenes 4 and 5 worked from pre-existing FAIL records. In real
life, most FAILs are ones *you* discover. Learn to file one from scratch.

### 7a — Start the QR

**Two paths — pick one for the training exercise:**

**Path A — from a DWI capture:** during an inspection, enter a value
outside spec. The system flags it inline. Submit as FAIL and add a
description.

**Path B — freestanding QR:** sidebar → **Quality Reports** → **New
Quality Reports** button (top-right).

For the training exercise, use **Path B**.

### 7b — Fill the QR

**You land on:** `/editor/qualityReports/create`. Heading: **Create
Quality Report (NCR)**.

**You fill in, in this order:**
- **Status** (required, defaults to *Pending Review*). Change to **FAIL**
  — the form even reminds you: *"FAIL status indicates a Non-Conformance
  Report (NCR)."*
- **Part** — pick any INJ-0042-* that's IN_PROGRESS (not the archetype
  serials you're preserving for other journeys).
- **Process Step** — pick the inspection step the part is currently at.
- **Machine/Equipment** — optional. If you used a specific bench or
  gauge, put it here (Torque Wrench TW-25, Flow Test Stand #1, etc.).
- **Description** — specific. Not "bad." Try: "*Spray pattern shows 4
  of 6 holes emitting asymmetrically, ≈20° deflection on right side.*"
- **Detected By** — Sarah.
- **Verified By** — leave empty for now. A separate inspector fills this
  in when the FAIL is confirmed (four-eyes principle for major defects).
- **First Piece Inspection** checkbox — check this ONLY if the part is
  the designated FPI part for its step. Journey 8 covers FPI.
- **Archived** checkbox — leave unchecked. Archived hides the report
  from default views; you never want to hide a fresh FAIL.

**You click:** **Submit**.

**You land on:** the QR list — the new QR is at the top.

![Create Quality Report (NCR) form — status, part, step, equipment,
description, detected by,
FPI checkbox](screenshots/qa_inspector_training/07-qr-create.png)

### 7c — Add the defect type

**Important:** the QR *create* form has no defect-type picker. The
defect-type tagging happens on the **edit** page after creation.

**You click:** the pencil/Edit icon on your new QR's row, or navigate to
`/editor/qualityReports/edit/$id`.

**You add:** a defect type from the picker (Asymmetric spray pattern,
Flow rate out of spec, Spray angle drift, Hole blockage, Surface
porosity, etc.). Overusing "Other/Unknown" hides patterns from defect
analysis.

**You save.**

### 7c — See the disposition auto-create

**You go to:** the part detail page for that serial. The Dispositions
widget now shows a new **OPEN** or **IN_PROGRESS** disposition
auto-created by the system when the QR was saved as FAIL.

**Teaching moment:** the system creates the disposition *record* for
you; the *decision* is still yours. Same as Journey 4.

**Watch for:**
- Trainee starts a capture, sees an out-of-spec value, and quietly edits
  the reading to bring it into spec. **This is the single most
  dangerous shortcut a QA inspector can develop.** Zero tolerance. If
  you catch it in training, stop and reset expectations.
- Trainee files a FAIL without a defect type ("I'll come back to it").
  No they won't. Insist on the tag now.

**Checkpoint:** trainee files a FAIL, sees the auto-created disposition
on the part detail page, and can navigate back to their own QR from
that widget.

---

## Journey 8 — First Piece Inspection (WO-2024-0048-A)

**Why:** When a WO opens a new step for the first time, the first part
through is designated for FPI. Miss the FPI and every subsequent part
inherits any setup errors.

### 8a — Spot the banner

**You go to:** home page. The FPI banner at the top (red border, Siren
icon) shows the pending first piece — for WO-2024-0048-A, Nozzle
Inspection.

![First Piece Inspection banner on the QA home page — pending FPI for
WO-2024-0048-A with I'm on it / Start check
buttons](screenshots/qa_inspector_training/09-fpi-banner.png)

### 8b — Acknowledge or check

**Two buttons on the banner:**
- **I'm on it** — tells the operator you've seen it and are heading
  over. The banner then reads "Seen by Sarah."
- **Start check** — jumps to the WO control page for the FPI.

For the training exercise, click **Start check**.

**You land on:** `/workorder/$workOrderId/control` for WO-2024-0048-A.

### 8c — Read what an FPI captures

Locate the FPI record on the page (surfaced in a step-controls dropdown
or dedicated FPI panel — the exact location may vary; teach what's
there). It includes:
- Designated part (the specific serial being FPI'd)
- Equipment used (bench/gauge)
- Inspector
- Shift date
- Status (PENDING → PASSED / FAILED)
- Result

**Do not actually PASS the FPI.** WO-2024-0048-A stays PENDING so the
banner is a live training exhibit for the next class. Walk the fields
aloud instead.

### 8d — What a completed FPI looks like

For contrast, open **WO-2024-0042-A** — its three PASSED FPI records
(Nozzle Inspection, Flow Testing, Final Test) sit in the seed.

**Teaching moment:**
- FPI is a **production gate**, not paperwork. A PENDING or FAILED FPI
  blocks the whole batch, not just the one part.
- Equipment on the FPI record must match the equipment used for the
  batch. Setup verification is bench-specific.
- A FAILED FPI is a bigger deal than one bad part — it usually means
  the setup is wrong. WO-2024-0038-A's FAILED Flow Testing FPI is what
  triggered CAPA-2024-003.

**Watch for:**
- Trainee treats FPI as a checkbox. Ask: "If this FPI fails, what
  happens to the 23 parts behind it?"
- Trainee wants to skip FPI on a repeat WO. Every new WO needs new FPI
  at each step.

**Checkpoint:** trainee can describe the difference between a FAILED FPI
and a FAILED individual-part QR — specifically that the FPI blocks the
**batch** while a part QR blocks the **part**.

---

## Journey 9 — Batch step awareness (Cleaning loads)

**Why:** Cleaning is a batch step — parts are inspected as a *load* (bath
temperature, cycle time), not per-part. You need to know how to read a
batch record when a downstream fail traces back to a bad wash.

### 9a — Find a completed part

**You go to:** a part on WO-2024-0042-A that has passed Cleaning (any
COMPLETED serial from the parts table — INJ-0042-001 through -016).

**You click:** into its detail page.

### 9b — Reach the batch record

**You look at:** the Activity History or step history. Cleaning steps
reference a **batch execution**, not a per-part measurement. Click
through to the batch record.

*(Exact click path depends on how your instance surfaces the batch
link. Trainer: pin it down on your instance before class.)*

### 9c — Read the batch record

**You see:**
- Parts included in the load.
- Started at / sealed at timestamps.
- Bath temperature reading.

The seed includes one intentionally-hot batch (bath temp 71 °C, out of
the 55–65 °C range) — find it. Notice: the FAIL applies to the **batch**,
not any single part in it.

**Teaching moment:**
- A bad batch flags **every** part in the load. You can't disposition
  one part in a failed batch as good and the others as bad — they were
  all in the same tank at the same temperature.
- Batch records are one-to-many. One reading, N parts.
- You don't *run* batch steps (production does), but you *do* read them
  when investigating a downstream anomaly.

**Watch for:**
- Trainee looks for a per-part cleaning measurement. Point out the
  measurement lives on the batch, not the part.
- Trainee tries to quietly pass one part out of a failed batch. Not how
  it works — every part in the failed batch needs a disposition.

**Checkpoint:** trainee can navigate from a part → its batch → the
other parts in the same batch. Cross-batch navigation is the specific
skill that pays off during a real investigation.

---

## Journey 10 — Personal inbox: tasks, approvals, dispositions

**Why:** Approvals, CAPA tasks, and dispositions assigned to *you
personally* aren't per-part like the Journey 1 home Inbox — they're a
different queue. Learn to read it, because ignored items block other
people's work.

### 10a — Reach the personal inbox

**Two paths:**

**Path A — sidebar:**
1. **You click:** sidebar → **Inbox** (under the *Personal* section).
2. **You land on:** `/inbox`.

**Path B — from home page:**
1. **You look at:** the MY QUALITY ACTIONS block on the home page.
2. **You click:** any of the tiles (`N Approvals`, `N CAPA tasks`,
   `N My dispositions`). They all route to `/inbox` (dispositions
   routes to `/production/dispositions`).

**Note on the sidebar Approvals section:** it's a **collapsible** that
defaults to *closed* — you only see the "Approvals" header with a
chevron. Click the header to expand and reveal:
- **Overview** → `/approvals` (aggregate view)
- **History** → `/approvals/history` (past approvals audit trail)

When you have personal pending approvals, a **count badge appears on
the collapsed header** (e.g. "Approvals · 3"). No badge means no
personal work waiting — but there could still be items in the system
you can see on the Overview page.

![Sidebar Approvals collapsible with count
badge](screenshots/qa_inspector_training/sidebar-approvals-badge.png)

### 10b — Read the tabs

**You see:** heading "Inbox", counters ("2 overdue, 9 total items"),
and four tabs:
- **All** (count) — everything mixed together.
- **Tasks** (count) — CAPA tasks assigned to you. In the seed Sarah
  has 6 (a mix of Containment, Corrective, and Preventive actions).
- **Approvals** — approvals assigned to you. In the seed Sarah has 0;
  the tab reads "All caught up!" Walk it aloud even though empty so
  the trainee recognizes the shape.
- **Dispositions** (count) — dispositions assigned to you. Sarah has 3.

Within each tab, items group into **Overdue**, **This Week**, and
**Upcoming**.

![Personal Inbox — tabs for All / Tasks / Approvals / Dispositions with
Overdue / This Week /
Upcoming grouping](screenshots/qa_inspector_training/10-inbox.png)

### 10c — Work an item

**You click:** the **View** link on any row.

**You land on:** the detail page for that item (CAPA detail for a task,
disposition editor for a disposition, approval detail for an approval).

**You return** to the inbox via the sidebar or browser back to work the
next one.

### 10d — Overview page (secondary)

For the aggregate view, navigate directly to `/approvals`. You see:
- Counters: **Awaiting My Approval / Overdue / My Requests Pending /
  Recently Approved**.
- **Awaiting My Approval** section — "All caught up!" when the tab in
  `/inbox` is also empty.
- **By Type** breakdown.
- **My Submitted Requests** — approvals you've *asked* others for.

This page is worth showing so the trainee knows it exists, but the
daily driver is `/inbox`.

![Approvals overview page — counters, awaiting my approval, by-type
breakdown, my submitted
requests](screenshots/qa_inspector_training/10-approvals-overview.png)

**Teaching moment:**
- An approval is **a signature**. Approving = signing paper.
- Rejection sends the request back with a reason — that reason lives in
  the audit trail. Write for the reader.
- Approvals expire. Sitting on one past its deadline doesn't
  auto-approve — it escalates.
- CAPA tasks aren't optional. "Not Started" and "15 days overdue" are
  visible to whoever else is watching this queue (managers, auditors).

**Watch for:**
- Trainee bulk-completes CAPA tasks without reading them. Same problem
  as bulk-approving.
- Trainee ignores empty Approvals tab thinking "not my problem." Ask:
  "How would you know if one showed up here tomorrow?" (Answer: the
  count badge on the sidebar Inbox link.)

**Checkpoint:** trainee can navigate to the Inbox from two paths
(sidebar and home tile), name the four tabs, and identify at least one
row they would need to click **View** on today.

---

## Journey 11 — Wrong scans and other mistakes

**Why:** Everyone will scan the wrong thing eventually. Prove to them
the software doesn't punish it.

**You do, in order:**

1. **Scan a label from a different WO** (any WO-2024-0038-* from your
   spare pile). You land on WO-2024-0038-A instead of 0042-A. Not an
   error — just not where you meant to go. Back up and rescan.
2. **Scan gibberish** (type `NOT-A-REAL-ID` and press Enter). Toast:
   *"Nothing found for NOT-A-REAL-ID"*. No harm done.
3. **Scan the same part twice while it's already open.** No duplicate
   work — you just re-land on the same page.
4. **Complete a capture with a value outside spec.** Inline validation
   flags it before submit. If you force it through, you generate a FAIL
   — which is the correct outcome, not a submit error.

**Teaching point:** the scan box **never damages anything.** It's a
lookup, not a commit. Nothing you scan changes state. State only
changes when you actively submit a capture, sign off, or record a
disposition. So scan freely.

**Watch for:**
- Trainee freezes after a wrong-scan and asks "did I break something?"
  Repeat the wrong scan yourself to demonstrate it keeps not-breaking
  anything. Confidence with the scan box compounds through the day.

**Checkpoint:** trainee scans three different codes in a row (WO, part
from a different WO, gibberish) without hesitation and without asking
whether it's safe.

---

## Cheat sheet

**Log in as:** `sarah.qa@demo.ambac.com` / `demo123`. Multi-role
alternative: Casey Cross (`casey.dual@demo.ambac.com` / `demo123`) is
QA Inspector + Shift Lead.

**Home page blocks:**
- Scan box — WO or part number, always lands on the parent WO.
- FPI banner — red alert for pending first-piece inspections. **Start
  check** button jumps to the WO control page.
- Inbox with chips — **All / Receiving / OSP returns / In-process**.
  AWAITING_QA parts land as `in-process` rows.
- MY QUALITY ACTIONS — your approvals, CAPA tasks, dispositions.
- YOUR GAUGES — calibration status on gauges you've used recently.

**Where QA work actually lives:**
- Home page — knowing what's on your plate.
- **WO Control page (`/workorder/{id}/control`)** — the workhorse. Every
  quarantine, every in-flight part, all print buttons.
- Part detail page (`/details/Parts/{id}`) — deep info on one serial,
  with linked Quality Reports and Dispositions widgets.
- Disposition editor (`/dispositions/edit/{id}`) — the decision form.
- QR editor (`/editor/qualityReports/edit/{id}`) — the inspection
  record.
- Approvals overview (`/approvals`) — the sign-off queue.

**Part states you'll see:**
- `IN_PROGRESS` — production owns it.
- `AWAITING_QA` — parked for your inspection.
- `QUARANTINED` — failed, pending a disposition decision.
- `REWORK_IN_PROGRESS` — rework approved, being reworked; you'll
  re-inspect.
- `SCRAPPED` — terminal.
- `COMPLETED` — passed all steps.

**Disposition states:**
- `OPEN` — created, no type selected.
- `IN_PROGRESS` — type picked, work happening.
- `CLOSED` — done.

**Disposition types:**
- REWORK — through the rework loop.
- USE_AS_IS — requires customer concession.
- SCRAP — terminal.
- REPAIR / RETURN_TO_SUPPLIER — less common; ask.

**Things you cannot do (by design):**
- Un-sign an inspection.
- Skip a re-inspection after rework.
- Change a FAIL to a PASS after the fact. (You add a new inspection;
  the old one stays.)

**When you're stuck, the first three things to check:**
1. Is the part in my Inbox? If not, it's not mine yet.
2. What does the part's history say? (Every state change is timestamped.)
3. Is there an open disposition? Someone may be waiting on a decision.

---

## Glossary

- **AWAITING_QA** — part state meaning "an operator finished a step but a
  rule says QA looks at it before it moves on." Parked; production
  can't advance it.
- **Batch execution** — a record for a batch step (like Cleaning)
  covering multiple parts inspected as a load, not individually.
- **CAPA** — Corrective And Preventive Action. Structured investigation
  and fix for recurring/high-severity defects. QA managers own
  authoring; inspectors feed data in.
- **Concession** — a customer's written approval to accept parts outside
  spec on a specific occasion. Required for USE_AS_IS.
- **Deviation request** — pre-approved permission to run outside spec
  for a specific WO with documented reason. Ahead of time; disposition
  is after the fact.
- **Disposition** — the decision record for what to do with a failed
  part.
- **DWI** — Digital Work Instruction. On-screen guided capture the
  operator (and inspector) follows step-by-step.
- **ERP id** — the human-readable identifier (WO-2024-0042-A,
  INJ-0042-018) shown on labels and travelers.
- **FPI** — First Piece Inspection. First part off a new step,
  inspected to verify setup before production runs the batch.
- **LSL / USL** — Lower / Upper Spec Limit. Outside these, the part
  fails.
- **NCR** — Non-Conformance Report. Formal record of a nonconformity.
- **PENDING (on a QR)** — the report is created but has no PASS/FAIL
  verdict yet.
- **QR** — Quality Report. The record of an inspection outcome.
- **QUARANTINED** — part state meaning "failed, pending a disposition
  decision."
- **Rework loop** — the sub-flow where a failed part is returned to a
  rework step, then re-inspected.
- **SCAR** — Supplier Corrective Action Request. Supplier quality's
  domain, not shop-floor QA.
- **Step execution** — one visit to one step by one part.
- **Traveler** — the printed WO packet that accompanies the physical
  parts through the shop.
- **Visit number** — 1 for the first time a part visited a step, 2+ for
  rework re-visits. All visits stay in history.

---

## Trainee certification checkoff

Cleared to inspect solo when they can, without prompting, demonstrate
every item below.

### Navigation
- [ ] Scan a printed WO traveler barcode and land on the correct WO
      detail page.
- [ ] Scan a part label and land on the correct WO detail page.
- [ ] Navigate from a WO detail page to the WO Control page.
- [ ] Open the home Inbox and describe what each chip filters.
- [ ] Explain when to look at the FPI banner and what "Start check"
      does.

### Doing an inspection
- [ ] Complete a passing inspection through the DWI capture flow.
- [ ] Complete a failing inspection: out-of-spec value, description,
      defect type, submit as FAIL.
- [ ] File a fresh QR through `/editor/qualityReports/create` without a
      DWI capture.
- [ ] Explain in their own words the difference between "measurement in
      spec" and "part passed."

### Dispositions
- [ ] Read an OPEN disposition and identify the three common door
      options.
- [ ] Describe the **consequence** of each door.
- [ ] Name when USE_AS_IS is legitimate and when it isn't.
- [ ] Read a closed disposition and identify who signed, when, and why.

### Rework and re-inspection
- [ ] Read a REWORK_IN_PROGRESS part's history and identify the
      original defect.
- [ ] Explain what `visit_number` means.
- [ ] Describe the correct behavior when a re-inspection also fails.

### Batch and FPI
- [ ] Navigate from a part → its batch execution → the other parts in
      the same batch.
- [ ] Find an FPI record on a WO and describe what it gates.
- [ ] Explain the difference between a FAILED FPI and a FAILED
      individual-part QR.

### Approvals
- [ ] Locate `/approvals` and identify the "Awaiting My Approval" card
      (default view).
- [ ] Identify one approval they would NOT sign without more info, and
      articulate what info they'd want.

### Compliance discipline
- [ ] State the software's rule about editing a submitted QR (you
      don't — you add new records).
- [ ] Correct response when a coworker verbally pressures them to skip
      a sampling-parked inspection.
- [ ] How to verify a gauge is in cal before using it.
- [ ] How to check their own training expirations.

### Cadence awareness
- [ ] Name three things to check daily.
- [ ] Name two things to check weekly.
- [ ] Name two things to check monthly.

---

**Trainee:** _______________________________  **Date:** _______________

**Trainer:** _______________________________  **Date:** _______________

**Cleared for solo inspection on:** _______________________________________

*Retain this signed checkoff in the trainee's personnel file per the
training-records retention policy.*

---

## Beyond the daily loop

Journeys above cover the shift-work rhythm. But an inspector's job runs
on three different clocks. Teach the trainee to feel each one.

**Cadence pattern:**
- **Daily** — what needs me right now (queue, FPI, notifications,
  cal-before-use).
- **Weekly** — what's trending (SPC, defect analysis, NCR analysis, my
  expiring training).
- **Monthly** — what's holding up over time (calibration cycles, CAPA
  effectiveness, audit readiness, personal calibration).

### Daily (in the shift flow)

- **Notifications / Inbox.** First thing at start of shift — approval
  requests, mentions, dispositions.
- **First Piece Inspection.** FPI banner. Real gate, not a formality.
- **Receiving inspection** (`/production/receiving-inspection`). If
  incoming inspection is also your responsibility.
- **Gauge calibration check** (`/quality/calibrations/records`) before
  using an instrument. The software doesn't stop you; the audit trail
  shows which gauge was used.
- **3D annotation on defects.** When a defect type requires it, mark
  *where* on the 3D model — not just describe it. Feeds the heat map.
- **Batch step awareness.** Cleaning is inspected as a load. A bad
  reading flags every part in the batch.
- **Approval requests.** They land in your inbox. Ignoring stalls
  production; approving without inspecting is worse.
- **Deviation requests.** Rare — production running outside spec by
  agreement. QA often in the approval chain. Ahead of time, not
  after-the-fact.

### Weekly (what's trending)

- **SPC charts** (`/spc`). Control-limit violations, Westgard rules.
  Single OOS is a disposition problem; a **drift** is an SPC problem.
- **Defect analysis** (`/quality/defects`). Pareto + heat map. When
  your shift finds three of the same defect, look here for a pattern.
- **NCR analysis** (`/quality/ncrs`). NCR trend by product, cause,
  disposition.
- **CAPA verification.** QA sign-off on effectiveness. Look for linked
  CAPAs on failed parts you've inspected.
- **Training expirations** (`/quality/training/records`). Yours.
  Expiration day = hard block at the step. Don't find out mid-shift.
- **Change control** (`/quality/change-control`). Notice when a step
  you inspect has recently changed — acceptance criteria might have
  moved. "Why did this pass yesterday and fail today?" is often a
  change-control answer.
- **Sampling rule 'why.'** Not something you change, but be able to
  answer "why is this part in my queue?"

### Monthly (what's holding up over time)

- **Own training expiration horizon** (`/quality/training/records`).
  Anything expiring in 30–60 days, get it scheduled.
- **Team training matrix** (`/quality/training/matrix`). Know who else
  on shift is certified for what step.
- **Instrument re-calibration cycle** (`/quality/calibrations`). Flag
  anything due next month before it lapses.
- **Personal FAIL-rate sanity check.** Your QRs over the last month vs.
  peers'. Under- or over-rejecting is a monthly conversation, not a
  daily one.
- **Controlled-document currency.** Drawings and DWIs get revised. Once
  a month, sanity-check the rev you're inspecting against is the
  current one.
- **CAPA effectiveness at portfolio scale** (`/quality/capas`). CAPAs
  closed in the last 30 days — did the target failure modes actually
  drop?
- **Internal audit readiness.** Pull a random recently-shipped part and
  try to reconstruct its full history. If you can't, raise it before
  an external auditor finds it.
- **Sampling rule outcomes.** Did the sampled parts actually catch more
  defects than random? Zero fails = rule too loose OR process
  stable. Worth a conversation with the QA manager, not a change you
  make yourself.

### What to skip in inspector training

- **SCAR** (supplier corrective action) — supplier quality's job.
- **CAPA authoring** — QA managers own it; inspectors feed the data.
- **Process flow editor / DWI authoring** — engineering's job.
- **Outside-processing board** — production planning.
- **BOM reports** — not their concern.
