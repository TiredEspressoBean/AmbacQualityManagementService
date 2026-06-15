# UQMES — Demo Walkthrough Script

**Audience:** A coworker presenting UQMES to a prospect (or internally).
**Goal:** Tell one story end-to-end through four marquee surfaces — the process
flow editor, the DWI editor (authoring), the DWI operator interface, and 3D part
annotation + the defect heatmap.
**Runtime:** full storyline ~12–15 min; or run any single scene standalone as a
~3–5 min quick demo (see *Two ways to run it* below).

> **Status: ready to run.** All four scenes are built, seeded, and verified against
> the live UI (2026-06-14). Talk-tracks below are final. Run `seed_demo` before a
> demo for clean, deterministic data — it invalidates open sessions, so log in
> fresh afterward.
>
> **Demo storyline cast** — every object is tagged `SHOWCASE` and threaded by one
> hero injector, so a single search surfaces the whole path:
> - **`INJ-SHOWCASE-001`** — the hero part, parked at Nozzle Inspection with a live
>   (open, IN_PROGRESS) step execution. Threads scenes 3 → 4.
> - **`WO-SHOWCASE-01`** / **`ORD-SHOWCASE`** — its work order + order on Injector Reman.
> - **"Injector Reman — Authoring Draft (SHOWCASE)"** — an editable DRAFT clone of
>   the approved process for the authoring scene.
> - **`QR-SHOWCASE-001`** — a FAIL quality report on the hero part, wired to a
>   `requires_3d_annotation` error type (drives the Scene 4 annotator).
>
> **Model note:** the 3D model is a Benchy GLB standing in for the injector — by
> design for the demo. The defect *labels* and callout text are injector-correct
> (nozzle-tip scoring, spray-hole erosion, seat-face pitting); keep the talk-track
> on the data and the trend, not the mesh shape. If a prospect asks: "stand-in
> model for the demo." IDs are time-based UUIDs that change every reseed, so
> navigate via the UI / search the `SHOWCASE` tag rather than hardcoding URLs.

---

## The one-sentence pitch

> "UQMES is the manufacturing operating system for the shops that are too complex
> for spreadsheets but too pragmatic for SAP — built compliance-first, deployable
> on-prem, with conditional reman routing and 3D visual quality the big QMS vendors
> can't match."

## The narrative spine — follow one injector through reman

Everything in the demo hangs on a single thread so it never feels like a feature
tour. We follow a **remanufactured common-rail diesel injector** through the
**Injector Reman** process:

1. **Define the work** → *Process Flow Editor.* The real, seeded routing —
   including the conditional rework loop a linear MES can't model — viewed and
   governed through the actual editor (not a canned demo overlay).
2. **Instruct the work** → *DWI Editor.* Zoom into one step (Nozzle Inspection)
   and show how we tell the operator *exactly* what to do — with 3D callouts and
   spec-bound measurement capture.
3. **Execute the work** → *DWI Operator Interface.* What the person on the floor
   actually sees: guided, mistake-proofed, signed.
4. **Learn from the work** → *3D Annotation + Heatmap.* When a part fails, the
   inspector marks *where* on a 3D model. Across hundreds of parts, patterns
   emerge and feed a CAPA.

That arc is Plan → Do → Check → Act — a quality manager will recognize it
instantly.

## Two ways to run it

- **Full storyline (~12–15 min):** scenes 1 → 2 → 3 → 4 in order, threaded by the
  hero injector `INJ-SHOWCASE-001`. Use the cross-scene callbacks in the
  talk-tracks ("here's the same step from the floor…"). This is the deep-dive cut.
- **Quick demo (~3–5 min, pick one scene):** each scene is **self-contained** — its
  own login, entry point, and talk-track — so you can show just one surface on
  request ("show me the operator interface," "show me the heatmap"). When running a
  scene standalone, **drop the cross-scene callbacks** and skip the threading
  language; lead with that scene's own "Why it matters." Best standalone picks:
  Scene 1 (process flexibility), Scene 3 (operator mistake-proofing), Scene 4 (3D
  defect intelligence).

**Personas — two logins** (one switch, real role boundary):
- **Administrator** (`admin@demo.ambac.com`) — Scenes 1 & 2 (define the process +
  author the work instruction).
- **QA Inspector** (`sarah.qa@demo.ambac.com`) — Scenes 3 & 4 (run the inspection
  on the floor + annotate the defect / review the heatmap).

Both use password `demo123`. **Switch once, between Scene 2 and Scene 3.** The QA
Inspector role genuinely has the permissions to run inspection substeps and
annotate (verified) — note the trimmed sidebar vs. Admin to make the role boundary
visible.

---

## Before you start (presenter prep)

**Reseed the demo tenant** (gives deterministic data; invalidates any open
session, so log in fresh afterward). Two ways:

- **From the UI (no terminal needed):** as Admin, go to
  **`/settings/organization`** (sidebar **Admin → Settings**, then the
  **Organization** section) → the **"Regenerate Demo Data"** card → click
  **Regenerate demo data**, type **`REGENERATE`** to confirm. It wipes and
  reseeds the demo tenant from the preset state (async; the page reloads when it
  finishes). *This card only appears on the `demo` tenant.* This is the easiest
  way to reset to a clean fixture right before a demo.
- **From the terminal:**
  ```
  cd PartsTracker && python manage.py seed_demo
  ```

Either way, the reseed invalidates your session — log in fresh afterward.

**Logins** (all password `demo123`):

| Persona | Email | Use in scene |
|---|---|---|
| Administrator | `admin@demo.ambac.com` | Scenes 1 & 2 (define + author) |
| QA Inspector | `sarah.qa@demo.ambac.com` | Scenes 3 & 4 (run + annotate) |
| Customer (portal) | `tom.bradley@midwestfleet.com` | optional add-on only |

**Tabs to pre-open** (so you're never waiting on a cold load mid-pitch):
- `/process-flow` → pick **Injector Reman** (the real process, not the `demo` overlay)
- `/process-flow` → pick **Injector Reman — Authoring Draft (SHOWCASE)** → click
  Nozzle Inspection → **View substeps** (Scene 2 editable editor)
- the operator run for **`INJ-SHOWCASE-001`** at Nozzle Inspection (Scene 3 — open
  it from `/workorders` → `WO-SHOWCASE-01`, or via the part)
- `/heatmap` → **Common Rail Injector**

**Product/naming note:** the product is **UQMES**. The "Ambac" in the URLs and
the demo tenant is the reference customer — don't call the product "Ambac" on the
call.

---

## Scene 1 — Define the work: the Process Flow Editor (~3 min)

**Route:** `/process-flow?id={injectorRemanProcessId}` — selects the **real,
seeded Injector Reman process**, NOT the `demo` pseudo-process.
**Log in as:** Administrator (stays logged in through Scene 2).
**Sidebar → page:** in the left sidebar, under **Production**, click **Processes**
(opens the process list). On the **Injector Reman** row, click the **flow icon**
(the little branching-workflow glyph, tooltip "Edit Process") → that opens the real
flow view. *(There is no "Process Flow" item in the sidebar — it's only reached by
the flow icon on a process row.)*

> **Use the real process, not the overlay.** `/process-flow` defaults to a
> built-in `demo` pseudo-process with canned Part Journey / bottleneck / work-order
> overlays. **We don't use that** — it's a static animation, not the system
> working. We open the actual seeded process by id, which renders the real DAG
> from the database and exposes the real editing + change-control lifecycle.

**Do this:**
1. Open `/process-flow?id={injectorRemanProcessId}` (or pick *Injector Reman* in
   the selector). The graph is the real 11-step process: Core Receiving →
   Disassembly → Component Grading → Cleaning → **Nozzle Inspection** → Flow Testing →
   Assembly → Final Test → Packaging → Complete, plus a **Rework** station.
2. Point out the **conditional rework loop** that's genuinely in the data:
   Nozzle Inspection (and Flow Testing, and Final Test) have a *fail-path* edge to
   **Rework**, and Rework routes back into Nozzle Inspection. Decision steps and
   the terminal step are visually distinct node types.
3. Click the **Nozzle Inspection** node to open the Step Details panel and show
   the real attributes (all verified in view mode): **DECISION** / Decision Type
   **QA_RESULT**, **Max Visits (Rework Limit): 2**, Requires QA Signoff: Yes,
   Sampling Required: Yes, **Min Sampling Rate: 25%**. The panel also shows live
   counts — Measurements: 2, Sampling Rules: 1, Substeps: 2 — each with a
   **View** button (the "View substeps" button is the bridge into Scene 2).
4. (Optional, sells the governance story) Open the **⋮** menu next to the process
   selector — real options are **Deprecate**, **Propose Change** ("File a PCR +
   fork an editable draft"), and **Duplicate as Template** ("Clone for a new
   product (no change trail)"). This is the real change-control lifecycle and the
   bridge into Scene 2.

**Say this:**
> "This is the real process our injectors run — not a diagram, the live routing the
> floor executes. Most systems assume a straight line. Reman isn't: watch the
> Nozzle Inspection step — pass continues down the line, fail routes to a rework
> station and re-enters inspection. That branching is native here. And every step
> carries real control logic — this one samples 25% of parts, blocks the line on an
> out-of-spec measurement, and caps rework at two visits before it escalates to a
> QA manager. It's also approved and locked — I can't quietly edit a released
> process; I'd file a change request. That's the control auditors look for."

**Why it matters (differentiator):** DAG-based conditional routing with real,
per-step control logic. Many MES tools don't treat the rework loop as a
first-class conditional path — that's the reman wedge.

✅ **VERIFIED (2026-06-14):** selecting *Injector Reman* renders the real 11-step
DAG with three QA-decision nodes (Nozzle Inspection / Flow Testing / Final Test)
each routing **Fail → Rework**, and Rework looping back into Nozzle Inspection.
Header shows the **APPROVED** badge + "This process is locked. Duplicate to make
changes." The overlay tabs (Part Journey etc.) are correctly *absent* for a real
process. **Note:** step/process IDs are time-based UUIDs that change on every
reseed — the presenter must navigate via the picker → node → *View substeps*,
**not** a hardcoded `?id=` URL (the `?id=` form is real but the value is not
stable).

---

## Scene 2 — Instruct the work: the DWI Editor (authoring) (~4 min)

**Route:** the substep editor for **Nozzle Inspection**
(`/editor/processes/{processId}/steps/{stepId}/substeps`).
**Log in as:** Administrator (same login as Scene 1 — no switch).
**Sidebar → page:** **Production → Processes**, then click the **flow icon** on the
**"Injector Reman — Authoring Draft (SHOWCASE)"** row (search "SHOWCASE" in the
process list if needed). In the flow view, click the **Nozzle Inspection** node →
in the Step Details panel on the right, click **View substeps** → the editable
substep editor. *(The substep editor has no direct sidebar link — it's reached
through the flow view's node panel.)*

> **Why a draft process:** the seeded *Injector Reman* is **Approved**, so its
> substep editor is **read-only** (the change-control guarantee — you can't
> silently edit a released process). To *show authoring*, open the seeded editable
> draft, or fork one live:
>
> - **Path A — Standalone DRAFT (seeded):** in the process selector, **search
>   "SHOWCASE"** (don't type the em-dash name) and pick *Injector Reman — Authoring
>   Draft (SHOWCASE)* → its substep editor is fully editable. Cleanest for "watch me
>   author." Use this for the short demo.
> - **Path B — PCR draft (live):** on the approved process, use the **⋮ → Propose
>   Change** to fork an editable draft revision. Shows the *real* change-control
>   workflow (PCR → edit → route for approval). Use this for the compliance-heavy
>   audience.

**Do this:**
1. Open the **Visual nozzle inspection** substep in the editor (the draft's editor
   is fully editable — no read-only banner).
2. Show the TipTap document: a caution callout, then the **3D part callouts** node
   — three numbered points pinned to the model (nozzle tip, spray-hole bank, seat
   face), each with its own saved camera angle.
3. Hit `/` for the **slash menu** (or the ribbon's 3D tab) and drop in a **Defect
   annotation (3D)** node on a fresh substep — show that the tool **automatically
   flips the substep to an Inspection point and pulls in the quality-report fields**
   (Pass/Fail result, equipment, sign-off, defect findings). That's the "keeps the
   author honest" beat.
4. Show the **measurement capture** on the second substep, wired to the real
   *Spray Angle* spec (nominal/tolerance from the measurement definition,
   characteristic N-12) plus the **inspector signature** gate.

**Say this:**
> "To show authoring I'll open a draft of that process. This is how we tell the
> operator exactly what to do. These callouts are pinned to points in 3D space on
> the part — nozzle tip, spray-hole bank, seat face — each with its own saved
> camera angle. This measurement field is bound to the engineering spec, so the
> value the operator types is checked against tolerance live. And notice — the
> moment I drop in a defect annotator, the tool automatically makes this an
> inspection point and adds the quality-report fields, because a defect you can't
> record to a report is worthless. The system keeps the author honest."

**Why it matters (differentiator):** Work instructions are structured, spatial,
and spec-bound — not documents; authoring is gated by change control; and the
editor won't let you build an inspection capture that fails to record to a QR.

✅ **DONE:** the standalone DRAFT — **"Injector Reman — Authoring Draft
(SHOWCASE)"** — is seeded and its substep editor is fully editable (verified). The
annotator → inspection-point + QR-bundle coupling is live (verified in the editor).
Path B (**⋮ → Propose Change**) is available on the approved process for the
change-control cut.

---

## Scene 3 — Execute the work: the DWI Operator Interface (~3 min)

**Route:** `/operator/steps/{stepId}/substeps?part=…&workOrder=…&execution=…`
**Log in as:** QA Inspector (`sarah.qa`) — **the one login switch**, from Admin;
stays on through Scene 4.
**Sidebar → page:** under **Production**, click **WO Control Center** → open
**WO-SHOWCASE-01** → on the work-order detail, click **Start Work** → tick
**INJ-SHOWCASE-001** → the operator runtime opens at Nozzle Inspection.

**Do this:**
1. Open the operator run for **`INJ-SHOWCASE-001`**: `/workorders` →
   **`WO-SHOWCASE-01`** → work-order detail → **Start Work** → check
   `INJ-SHOWCASE-001` → the runtime opens. *(Pre-open this tab in prep so you
   don't navigate the Start-Work dialog live.)*
2. Walk the guided substep: read the instruction, step through the **3D callout
   walkthrough** (Next/Prev) so the model flies to each inspection point.
3. Enter the **spray-angle measurement** — show the in-spec/out-of-spec feedback.
4. If the part's good, mark the result **Pass** and sign off. To show the failure
   path, mark a defect on the model (it links to the inspection report) and the
   result derives to **Fail**.

**Say this:**
> "Here's the same step on the floor, on a real injector — INJ-SHOWCASE-001, parked
> at Nozzle Inspection. The operator isn't reading a binder: the instruction walks
> them through each inspection point on the 3D model, the measurement tells them
> immediately if they're out of spec, and the step won't complete until the
> required fields and sign-off are done. If the part's good, they pass it — nothing
> to annotate. If they find a defect, they mark it right on the model, and it's
> linked to the inspection report automatically. Mistake-proofing built into the
> workflow, not bolted on as a checklist."

**Why it matters (differentiator):** The authored DWI *is* the runtime — same
nodes, now interactive and enforced. Required captures + e-signature gate
completion. Defect annotation is optional —
captured only when there's an actual defect — and auto-derives the Pass/Fail.

✅ **DONE / VERIFIED (2026-06-14):** `INJ-SHOWCASE-001` is parked at Nozzle
Inspection with an open StepExecution; launching the operator run shows the callout
walkthrough, the live measurement, **required-field gating** (Pass/Fail result +
equipment + sign-off), and the defect annotator **"Linked to inspection report:
…"** — a placed defect records to the QR. Annotation/defect list stay optional.

---

## Scene 4 — Learn from the work: 3D Annotation + Heatmap (~4 min)

**Route:** annotator at `/partAnnotator/{modelId}/{partId}`, then `/heatmap`.
**Log in as:** QA Inspector (`sarah.qa`) (same login as Scene 3 — no switch).
**Sidebar → page:** for the heatmap, under **Quality**, click **Heat Map** (direct
link) → pick **Common Rail Injector**. For the annotator, under **Quality** click
**Quality Reports**, open the FAIL **QR-SHOWCASE-001**, and launch its 3D
annotation (or reach it from the operator inspection in Scene 3).

**Do this:**
1. Start from a **failed** inspection that requires 3D annotation. Open the
   annotator, rotate the injector, **click to place a defect marker** where the
   scoring is, set severity, add a note.
2. Jump to `/heatmap` for the Common Rail Injector. Show the GPU heatmap — the
   ~10 seeded defects across multiple parts bloom into a red cluster on the nozzle
   tip / spray-hole region.
3. Tie it to **CAPA-2024-003** (the in-progress nozzle-defect CAPA): the spatial
   pattern is the evidence that drove the corrective action.

**Say this:**
> "When a part fails, the inspector doesn't type 'nozzle defect' into a box — they
> mark *exactly where*, how severe, how many. Now multiply that across hundreds of
> parts. This heatmap is every nozzle defect we've logged, rendered on the GPU. See
> the cluster on the nozzle tip and spray-hole region? That's not anecdote — it's a
> spatial trend, and it's the evidence behind an open corrective action. Spatial
> defect intelligence that a text-log QMS just can't give you."

**Why it matters (differentiator):** 3D click-to-annotate + GPU heatmaps =
historical, spatial defect analysis. Commercial QMS tools do text or 2D photos.

✅ **DONE / VERIFIED (2026-06-14):** Heatmap shows **10 of 10 defects** (LOW 5 /
MEDIUM 3 / HIGH 2), now labeled with **injector defects** — Nozzle tip scoring,
Spray-hole erosion, Seat face pitting. The annotator opens on the real model + the
hero part. **`QR-SHOWCASE-001`** is a FAIL wired to a `requires_3d_annotation`
error type, so it drives the annotator. *(Note: the QR's auto-launch popup from the
QR-completion flow wasn't click-tested; opening the annotator by route works.)*

---

## Closing pitch (end here)

The demo ends on Scene 4 — close with this:

> "So in twelve minutes we defined a non-linear process, authored a spatial work
> instruction under change control, ran it on the floor with mistake-proofing and
> a signature, and turned a failure into a spatial trend that drove a CAPA — all
> in one system, all on-prem. That's the loop UQMES runs every day. The big QMS
> vendors sell you pieces of that; nobody sells the whole loop at mid-market price,
> on-prem."

---

## Optional add-ons (only if the room wants more — e.g. defense/ITAR audience)

Not part of the standard flow; reach for these only if asked.

- **Customer portal** (log in as `tom.bradley`): the customer sees their order's
  real status without a phone call.

> "And all of this — the 3D, the data, the workflow — runs on-premises. For a
> defense or ITAR shop, that's not a nice-to-have, it's the only way they're allowed
> to run it."

---

## Staging — ✅ DONE (seeded by `seed_demo`, verified 2026-06-14)

1. ✅ **Scene 2 — DRAFT authoring:** "Injector Reman — Authoring Draft (SHOWCASE)"
   seeded, substep editor editable. Path B (**⋮ → Propose Change**) available live.
2. ✅ **Scene 3 — parked operator run:** `INJ-SHOWCASE-001` on `WO-SHOWCASE-01` at
   Nozzle Inspection with an open StepExecution; operator run resolves live, QR
   binds, defects link.
3. ✅ **Scene 4 — failure for the annotator:** `QR-SHOWCASE-001` FAIL on the hero
   part, wired to a `requires_3d_annotation` error type. Heatmap relabeled to
   injector defects.
4. ✅ **Verify-only:** real Injector Reman DAG renders with the rework loop + real
   per-step control flags (no overlay); sampling reads **25%** (fraction-display
   bug fixed); heatmap clusters the nozzle annotations; CAPA-2024-003 exists.

**Reminder:** IDs regenerate on every reseed — navigate via the UI and the
`SHOWCASE` search tag; don't hardcode URLs.

## Format decisions (locked)

- **Personas:** two logins, one switch — **Administrator** for Scenes 1 & 2,
  **QA Inspector** for Scenes 3 & 4 (switch once, between Scene 2 and Scene 3).
- **Two cuts:** full storyline (1→2→3→4 threaded) for deep dives; individual
  self-contained scenes for quick demos.
- **Ends on Scene 4** + Closing pitch. The customer portal is an optional add-on,
  only if the room wants more. *(AI coworker is intentionally excluded — not
  working right now.)*
