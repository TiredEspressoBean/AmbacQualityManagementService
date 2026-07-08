# Operator & QA Landing Experience — Design + Roadmap

*(2026-07-08. Distills the multi-session design arc: four research rounds across ~60
MES/QMS/ERP/connected-worker/QC products, four prototype generations across three
surfaces, and the MES maturity discussion. Companion to
`RECEIVING_INSPECTION_DESIGN.md`. §12 backlog is the single source of truth for
remaining work.)*

---

## 1. The problem & the insight

UQMES's home was "Welcome back, use the sidebar." The operator's real path to work ran
list → detail → dialog → runtime — the **four-clicks-before-working disease**. The
research's sharpest finding (user-observed, data-confirmed): **nobody in this market
wins on the landing page** — even strong products are equally bad or worse at
time-to-work (Epicor users complain about Work Queue friction; Fusion Ops lands on a
32-button grid; enterprise MES ships no canonical operator home at all). The products
that don't have the problem (Odoo tap-card-to-start, MRPeasy top-item Start, Plex/Tulip
station context, Steelhead "priorities already set") all solved it by **collapsing
tiers, not polishing them**.

**Positioning metric: clicks-to-first-part.** Design budget: *one tap from home to
working; two from anywhere.* Cheap to demo, brag-able, and the incumbents lose it.

## 2. Hard constraints (decided)

- **No scheduling/dispatch exists** — nothing may rely on assignment. `assigned_to` on
  StepExecution stays untouched (an attribution-on-start edit was made and deliberately
  reverted; semantics reserved for a future assignment design).
- **No reliable workstation model** — `WorkCenter`/`Shift`/`ScheduleSlot` are skeleton
  models with no mappings. Scope/filter concepts must be client-side lenses until the
  mapping layer exists.
- Guardrail carried from receiving (§11 there): mid-market <200 heads; implement the
  floor, don't grow an enterprise tier. Full APS is explicitly out (see §10).

## 3. Architecture: three tiers, tiers are fallbacks not waypoints

```
HOME  (persona tiles)   → "what needs me RIGHT NOW"   (one hero action)
  ↓ scan / Start / row tap
QUEUE (list page)       → "everything I could work on" (readiness buckets, lenses)
  ↓ row tap
TRAVELER (WO detail, operator mode) → "this WO: progress + Start"
```

The happy path skips the middle: **UP NEXT's Start goes directly into the runtime**
(auto-resolve first queued part; StartWorkDialog demoted to the ambiguous case). The
queue exists for "the top pick is wrong"; the traveler for "tell me about this WO."
Old surfaces reassigned: `/production/work-orders` (`QaWorkOrdersPage`) is a fossil of
the pre-MES in-process-check product — its unique WO-level "x/y checks" rollup is
reborn inside the queue's Checks-due lens; the page itself retires by replacement.
The WO **control page is a lead/manager surface** — operators never route through it.

## 4. The five workflows (the landing page's acceptance contract)

Each has a **tap budget**; wiring is accepted/rejected against these, not style opinions.

| # | Workflow | Flow | Budget |
|---|---|---|---|
| 1 | **Tell me what to do** | clock in → shift notes glance → UP NEXT → Start → runtime | **1 tap** (post clock-in) |
| 2 | **Thing in my hand** | scan traveler/part → operator work surface at current step → Start | **scan + 1 tap** |
| 3 | **I was interrupted** | Resume strip (run + progress) → back where I was | **1 tap** |
| 4 | **Can't run this** | "Can't run this?" → reason → hero swaps to next job; blocker born owned | **2 taps to next job** |
| 5 | **Something's wrong** | Report a problem → machine/job branch → reason → routed; back to work | **2–3 taps** |

Excluded by design: browse-and-choose (the fallback *inside* #1 — frequent browsing
means the ranking failed); completion/quantity capture (runtime's contract); everything
lead-shaped (release, nudging, short-close → lead landing variant, later).

**Distance (2026-07-08, vs the real app):** #2 ~70% (scan works; wrong destination),
#5 ~50% (DowntimeEvent exists, no capture UI; lead-ping missing), #3 ~40% (stopgap =
localStorage, ½ day; durable version awaits attribution decision), #1 ~35% (needs queue
aggregate + hero + relevance layers, ~4–5 d), #4 ~15% (needs the blocker aggregate,
~3–4 d). **≈2 focused weeks to all five at v1** — an integration problem, not a
platform problem.

## 5. Research digest (4 rounds, ~60 products)

**Operator landing universals:** clock-in gates first; priority queue scoped to
station; one-tap start/stop; instructions one tap away; quality capture inline.
Deliberately absent: financials, KPI walls, scheduling tools, nav depth. Station beats
person for small shops ("my assignments" is a *filter*, not the default — L2L/Epicor;
Katana is the person-centric exception). Siemens Opcenter's operator cockpit is
literally "clutter-free tile-based" — the kiosk-tile bet matches the top vendor.

**Queue-page anatomy:** flat priority lists are the weakest variant. Winning structure:
**readiness buckets** (Epicor Active/Current/Available/Expected — "can I start this?"
vs "what's coming to stage"), scope-first (Odoo WC tabs, Fulcrum filter), a "My work"
lens on top. Cards beat rows once per-item action exists; **one state-dependent primary
button** + overflow (Odoo Mark-as-Done→Close; MRPeasy's Start button color = state).
**Late = flag/pinned hot section, never a separate page** (Cetec hot list, ProShop
green/yellow/red vs must-leave date). Radiology-worklist lesson: if operators must
trust "top = next," invest in the **ranking function and aging-escalation**, not row
styling.

**QA worklists:** *no product groups by work order* (rollups hide the global priority
order — the inspector's decision is "what do I touch next"). eQMS = flat merged task
list by record type with **count filter chips** (Net-Inspect pills, Qualio filter
stats); MES = flat stage/ship-date queues; overdue = RED universally (uniPoint).
Inline sign-off rare; batch sign-off nonexistent. Inspector = task-first; manager =
same list + metrics/reassignment. **Two panes, never merged**: production-prioritized
inspection queue + personal actions inbox.

**Connected-worker adds:** shift handoff is the loudest theme (Poka's feed exists for
cross-shift; Steelhead's comments travel with parts) → shift-notes read strip. Skills
gating (Dozuki/VKS) → cert locks on queue rows (UQMES already has
`TrainingRequirement` + `check_training_authorization`). Personal gamification is rarer
than marketing suggests — team wins at huddles; keep "Today: N completed"
non-comparative. **Pacing displays are a machine-data feature, not a person feature**
(every monitoring product shows job/machine pace; no one scores the human; no ERP/MES
puts pace on the operator entry view). Redzone caution: unused surfaces read as
clutter even in beloved apps — additions must earn their tile.

**Round 4 (2026-07-08, five targeted digests: connected-worker, mid-market MES
terminals, cross-industry next-task UX, eQMS dashboards, shop-floor QC tools):**

- **Aging without a scheduler** (Toast/Square KDS; Epic Brain): urgency = color
  thresholds on **time-in-ready-state**, painted on the artifact itself so peripheral
  vision does the prioritizing. Companion: acknowledge-on-breach (Epic) — a due-date
  breach demands a logged human ack, converting silent aging into an accountable event.
- **The flag lifecycle** (L2L Dispatch; anti-pattern = Tulip's dead-air red/green
  toggle): a raised blocker shows *routed → seen-by → resolved* with elapsed time and
  auto-escalates unacknowledged. Kills the "did anyone see this?" floor-walk.
- **Skip mechanics** (Zendesk Guided mode, DoorDash): reason **required**, as tap-chips
  not free text (Zendesk's own users filed for required); **blocker** (global, born
  owned) ≠ **personal skip** (job stays in others' queues; logged quietly for coaching);
  starting a THEN tile instead of UP NEXT is a *soft skip*, same data at zero friction.
  Show the **consequence preview before the tap** ("routes to Materials, leaves your
  queue, next job appears"); never import acceptance-rate scoring — documented
  resentment + gaming, and in a shop it incentivizes hiding problems.
- **Terminal mechanics** (ShopPulse/Epicor/JobBOSS²/VISUAL): badge-in interstitial
  (your work left, last-shift notes right, one Got-it); **Start forks setup→run** (the
  most-wanted job-shop labor analytic, captured for one tap); completion = good qty →
  scrap qty → forced reason if >0 → complete/incomplete fork (kills phantom-open ops);
  **scan = identity + job + labor start in one gesture** (scan *arms Start*, it doesn't
  navigate); undo window after Complete (Toast recall — cheap mistakes make fast
  operators); one-tap Break; status-color band + time-in-state — all derivable from our
  own events, no machine feed. Guardrail (Datanomix's whole brand): every mechanic ≤2
  taps or it gets ignored.
- **First piece is an andon call, not a worklist row** (ShopPulse FAI + andon TTR
  literature, 12min→2.5min with escalation): operator side = visible sent → seen-by-QA
  → verdict states; inspector side = pinned banner with a live **"machine waiting"
  timer**. A machine and operator idle behind it — economically unlike a shelf-aging lot.
- **Trust furniture:** evidence-bearing empty state — name the upstream jobs and where
  they're stuck (readiness derivation knows the cause; beats gig-app hotspots); the
  browsable **"See everything ready (N)"** self-serve list (Fulcrum) is what makes a
  system-picked hero acceptable; **"+N with this setup"** batching hint (Square all-day
  analog) gives a legitimate, visible reason to deviate from queue order.
- **eQMS landings are task inboxes, not metric dashboards** (near-unanimous; Qualio
  '26 split Home into My Actions + Watch List; charts pushed to reports). One flat list
  + clickable **count-filter chips**; four-state due dot (Veeva exactly: red overdue /
  orange ≤5d / green / gray — bucket, never raw day counts); **"Available to claim"**
  (Veeva: group-eligible, unclaimed, Accept moves it to mine) maps 1:1 onto
  ApprovalRequest group eligibility; audit-prep grid (QT9: missing + overdue across
  modules) = the quality-manager block and the weekly-meeting agenda; **no batch-approve
  anywhere** — per-item e-signature is the compliance norm; anti-pattern with
  paying-user evidence (Arena's top complaint): recently-visited ≠ needs-attention —
  never MRU, never a raw table. Mid-market ships ONE surface where role picks the
  default chips; forked persona dashboards are enterprise-priced.
- **QC-tool findings:** sampling rendered as **the answer** ("n=32 · Ac 0"), never the
  code tables (1factory); severity shown as a labeled badge **with the switch-back
  rule** — SAP hides the machinery and confuses users; *nobody* shows the
  return-to-Normal countdown → free differentiation for our severity engine; blocked
  rows **sink but stay counted** with reason chips (separates "inspector slow" from
  "upstream owes something" — protects inspectors from bad metrics); receiving triage
  by **needed-by-WO**, not FIFO (supplier risk drives sampling *depth*, never queue
  position); calibration gates at point of use — blocking with logged override, only
  possible when cal + capture live in one system (UQMES does) — plus the personal
  pre-empt ("N gauges you used this week are due"); no inspector-facing throughput
  stats anywhere — **blocked-time attribution** is the inspector-friendly stat; FAIR
  paperwork lifecycle stays out of the bench queue (measuring ≠ report assembly).

## 6. Landing page spec

**Operator (kiosk tiles, prototype at `/dev/operator-home`):**
header = greeting + **station-scope combobox** (searchable, per-scope ready counts —
the explicit relevance layer; persisted per user) + clock state + Clock out.
Tiles: **UP NEXT hero** (2×2: step, WO, qty, ~min/pc, order-progress bar, giant Start,
Instructions, quiet "Can't run this?") · Resume (run + n-of-m) · Scan · Shift notes
(inbound: lead + previous shift + blocker resolutions) · THEN (numbered operation
mini-tiles; cert-locked shown dimmed = personal state; blocked EXCLUDED = global state,
with trust caption "N jobs blocked — owners notified") · Report a problem (two-branch)
· Call my lead. Footer: "Today: N completed · M flagged" (own day only).

**v4 additions (round-4 lifts, all in the prototype):** aging tint by
time-in-ready-state on THEN tiles + "ready Nh · due X" on the hero; "+N with this
setup" batching hint; first-piece sent-for-check strip with QA acknowledgment; per-note
"Got it" on shift notes (ack logged); consequence preview + "→ owner" chips inside
"Can't run this?"; **your-flags strip** (routed → seen-by lifecycle for flags I
raised); evidence-bearing empty state (names upstream jobs + widen-scope); cert locks
offer "request sign-off"; "See everything ready (N)" trust link; undo/flag chip after
completion; Break button; tappable day-recap footer; Start forks setup→run; THEN-start
logged as a quiet soft-skip.

**Hero ranking function:** `up_next = ready ∩ certified ∩ scope(chosen ∪ inferred-from-
history)` ordered by WO priority → due → aging. Contract: *usually right with a
visible escape* — not divinely correct. Empty-at-scope degrades gracefully.

**QA inspector (prototype at `/dev/qa-home`):** pinned **first-piece queue-jumper**
banner (andon semantics: live "machine waiting" timer + Start check; the operator sees
seen/in-progress states on their side). Below it ONE flat inspection inbox —
count-filter chips (All / Receiving / In-process / Final / First piece + Overdue;
zero-count chips hide) over Overdue / Today / This-week horizons; rows carry the
four-state due dot, the sampling answer badge (`n=13 · Ac 1`), a severity badge that
explains itself on tap (tightened-since + switch-back countdown), a needed-by-WO
triage line, blocked rows sunk with reason chips, and a resume-mid-capture indicator
("7 of 13 samples · char 4/9"). Second block = "My quality actions" (uniPoint To-Do
semantics: due dots, deep links, Reassign from the row) + **Available to claim**
(group-eligible unclaimed approvals with Accept). Side tile: personal calibration nag
("N gauges you used this week due in 7d" — pre-empts the point-of-use gate). Footer
passive: today's counts + tappable **blocked-time attribution**. Quiet state = green
"audit-ready" confirmation (unoccupied market ground). Deliberately absent:
batch-approve, throughput-vs-goal, MRU lists. In-process checks still live on the
queue page's Checks-due lens; this page is the *task inbox* tier above it.

**Lead variant (later):** adds blockers-aging tile, release-to-floor, short-close
nags, team workload. All accountability visuals live here, not on the operator page.

## 7. Queue page spec (prototype at `/dev/work-queue`)

Lens tabs: **Work queue** | **Checks due** (persona-defaulted). Filter rail:
**work-center/step combobox** (searchable, counts) + product combobox + Late-only
toggle + free search; filters compose.

**Work-queue lens:** sections **Ready now** (late pinned first, red edge; cert-locked
dimmed with Start disabled) → **Waiting on upstream** (horizon buckets: arriving
today / this week / +N beyond; **Prep** action, waiting-on cue with ETA) → **Blocked**
(owned, aging badges amber→red ≥7d, reason · WO · owner, **Nudge**). "+N more" =
server pagination of the aggregate endpoint.

**Checks-due lens:** FLAT global-priority check rows (never WO-grouped), type-count
chips (All / Awaiting QA / Sampling / First piece), horizon headers (Overdue red /
Today / This week), WO as row attribute + Traveler link, Inspect / Sign off per row.
Backed today by: `AWAITING_QA` status, `needs_qa` filter, FPI pending queries.

## 8. Traveler (destination tier)

Not a new page: the existing WO detail page **already has** Start Work + Digital
Traveler + Documents. Operator mode = trim: traveler + Start dominate; stats demoted;
Hold/Cancel gated to leads; orient to the current step. Scan and all Start buttons land
here (or directly in the runtime when unambiguous).

## 9. Readiness, deviation & the blocker model

**Readiness is execution-time gating, not plan-time prediction** (scheduling predicts;
gates verify — and gates work with imperfect data):
`ready = upstream done ∧ certified ∧ no open downtime ∧ cal current ∧ not held ∧ not
manually blocked` — material readiness joins when the consumption hook lands.

**Downtime vs deviation:** "running Y instead of X" is NOT downtime. Two event
streams: `DowntimeEvent` (machine-scoped; exists) and the **operation blocker**
(job-scoped, NEW aggregate: subject execution/operation, reason code, opened/resolved,
optional `displaced_by`). The substitution is *derived* (plan-vs-actual diff), not
recorded. **Interlock:** blocker escalates to downtime only when nothing else is
runnable (starved). Pre-scheduling deviation event = **skip-with-reason** (only prompt
when skipping a late/high item).

**Cheap to record, expensive to ignore** (anti-three-year-WO machinery):
1. **Born owned** — reason code doubles as routing (material→Materials, tooling→Lead,
   quality→QA).
2. **Ages loudly** — Blocked bucket never evaporates; amber→red.
3. **Escalates automatically** — rides the existing `scan_work_order_holds_and_overdue`
   pattern (stale blocker > N days → event → owner; > 2N → up a level).
4. **Gates closure** — a WO cannot complete around open blockers without a formal
   **short-close** (explicit scrap/cancel/return disposition of the remainder, with
   reason + signature). Stale-WO scanner demands "resolve or short-close."
5. Blocker Pareto = the dataset that later justifies (or indicts) scheduling.

Operator UI of all this = two taps and a fresh hero; consequences route to lead
surfaces.

## 10. Scale (100+ WOs) & the maturity ladder

**Scale graduations** (architecture survives; options become load-bearing):
relevance scoping ships with v1 (not after); `PENDING→IN_PROGRESS` *is* the
release-to-floor gate — make release a deliberate lead action (WIP volume knob);
queue becomes scope-first with counted combobox; client-side assembly dies → **queue
aggregate endpoint** (WO×step rows, readiness, priority, server-ranked/paginated —
`wip_summary` is precedent); horizons cap unbounded sections.

**MES maturity ladder** (each rung pays for itself; landing page gets truthful
incrementally):

| Rung | Status today | Unlocks |
|---|---|---|
| 0. **Execution feedback loop** (consumption hook, labor, downtime reasons) | TimeEntry/DowntimeEvent exist; **consumption unwritten** (known gap — pays twice: traceability + material readiness) | material gates; honest inventory |
| 1. **BOM** | models exist, dormant | comes alive via rung 0 |
| 2. **Routing enrichment** | Processes/Steps/Edges ≈ 70% of routing | + per-op resource needs & std times → honest ~min/pc, ETAs |
| 3. **WorkCenter mapping** | skeleton models, unmapped | formal relevance signal; replaces the client-side lens |
| 4. **Lightweight scheduling** | nothing | due-date sequencing + rough-cut capacity view. **Full finite-capacity APS: permanently out** for this segment |

Interim relevance signals (pre-rung-3): history-inferred (`completed_by`), cert-gating
(exists), explicit "my steps" preference.

## 11. Prototypes & current state

- `/dev/operator-home` — kiosk tiles **v4**: v3 base (hero + deviation flow, verified
  2 taps → hero swap; scope combobox; shift notes; two-branch problem picker;
  blocked-count caption) + the round-4 lifts listed in §6 (aging tints, flag-lifecycle
  strip, FPI strip, notes ack, consequence preview, undo chip, setup hint, soft-skip,
  Break, setup→run fork).
- `/dev/work-queue` — v3 at-scale: readiness sections, blocked bucket w/ aging +
  Nudge, filter rail w/ comboboxes, horizon buckets; QA lens flat + chips + horizons.
- `/dev/qa-home` — **new**: the QA-inspector task inbox per §6 (FPI queue-jumper
  banner, chip-filtered flat inbox, severity badges w/ switch-back, claim queue,
  gauge nag, blocked-time footer).
- **Real app (committed):** role-gated home blocks (scan box → *currently the control
  page — retarget to operator surface*, WO queue w/ persona CTAs, inspection queue,
  quality actions), typecheck fixed & clean, seeded demo covers SQM/OSP/DWI.
- **Uncommitted at time of writing:** operator-home v4 delta, `/dev/qa-home` + its
  route, this doc refresh. (v3 prototypes + doc v1 are committed at `7724e76`.)

## 12. Backlog — single source of truth (build order)

**The ~2-week wiring plan (no scheduling, no workcenters touched):**
1. **Operator work surface** — WO detail operator-mode trim; retarget scan + all
   Starts. *(FE, 1–2 d — serves flows 2 & 1)*
2. **Queue aggregate endpoint** — WO×step, readiness conjunction, server ranking,
   pagination; + cert bulk-check exposure; station pref (client). *(BE 1–2 d)*
3. **UP NEXT hero + direct-start** on the real home; clock in/out UI. *(FE 1–2 d —
   completes flow 1)*
4. **Resume stopgap** — localStorage keyed by user. *(½ d — flow 3)*
5. **Problem capture** — downtime dialog + lead-ping event (notify Shift Lead group;
   proper who-is-my-lead later). *(1 d — flow 5)*
6. **Blocker aggregate + flow** — model/migration/RLS/serializer/viewset/schema, reason
   routing, hero "Can't run this?", queue Blocked bucket, escalation ride. *(3–4 d —
   flow 4; short-close + skip-with-reason in a second pass)*
7. **Real queue page** replacing `/production/work-orders` (retire by replacement).

**Named backend gaps (beyond the plan):** shift-notes model (author/body/audience/
expiry — the one new "social" aggregate); who-is-my-lead relationship; attribution
decision for durable Resume; consumption hook (rung 0 — also receiving §11 follow-up);
`split_from_cohort` missing on Parts serializer (runtime filter is a silent no-op).

**Round-4 additions (each wires with its host feature, not standalone):** FPI
request→ack→verdict states + notification (rides the blocker/owner plumbing; powers
the operator strip *and* the inspector banner); shift-note read-acknowledgment (field
on the shift-notes model — the ack is the QMS-friendly part); setup/run fork on the
labor session (a category on TimeEntry, one tap at Start); approval **claim** action
for group-eligible ApprovalRequests (Accept → assigned; the Veeva pattern);
per-user gauge-usage link (measurement equipment × user, recent window) to power the
personal cal nag; soft-skip event (THEN-start over UP NEXT) for coaching data;
time-became-ready timestamp on the queue aggregate (feeds the aging tint — falls out
of the readiness conjunction anyway).

**BE wiring inventory (verified against the codebase, 2026-07-08).** Two Explore
sweeps mapped every element of both prototypes to what exists. Net: cheaper than
budgeted; only the two §9 tables are genuinely new.

- *Tier 0 — exists, wire only:* TimeEntry `clock_in`/`clock_out` actions;
  **`entry_type` already has SETUP/PRODUCTION** (the setup→run fork is zero schema);
  Resume = my open TimeEntry (carries step/part/WO FKs — likely obsoletes the
  localStorage stopgap); undo = `StepExecution.ROLLED_BACK` + small service; ERP_id
  scan search; `check_training_authorization` (+ bulk variant); `my_pending`
  approvals / `my_tasks` CAPAs / disposition filters; minimal QualityReports POST
  (Log NC); DowntimeEvent + `resolve`.
- *Tier 1 — exposure (data exists, no API):* queue aggregate endpoint
  (**`StepExecution.entered_at` IS time-became-ready** — aging needs no new
  timestamp; `wip_summary` is the precedent); inspection-inbox aggregate (union of
  `build_incoming_rows` + `needs_qa` + FPI pending — all exist, nothing unions
  them); **SamplingSeverityState has zero serializer/endpoint** (severity_since +
  recent_outcomes + consecutive_accepts fully derive the badge + switch-back
  countdown); sampling badge + 7-of-13 via `MeasurementResult.sample_number`
  counts; approval claim = viewset action over the **existing ApprovalAssignment
  through-table** + claimable filter; gauge nag = `EquipmentUsage(operator,
  used_at)` × `CalibrationRecord.due_soon()` (*verify EquipmentUsage is actually
  written during capture*); new notification event types ride the registry
  (`fpi.*`, `training.signoff_requested`, `lead.ping` → Shift Lead *group*; no
  user→lead mapping exists, group-based is honest v1).
- *Tier 2 — thin fields:* `FPIRecord.acknowledged_by/at` (+ pending-list endpoint =
  the whole FPI loop, both surfaces); `MaterialLot.hold_reason` conventions
  (AWAITING_COC, GAUGE_UNAVAILABLE — free CharField); disposition `due_date`
  (absent; add or ship gray dot).
- *Tier 3 — new tables (only these):* OperationBlocker (+ `acknowledged_by/at` for
  the routed→seen strip; escalation = new scan riding tasks.py:1419 pattern);
  ShiftNote + read-ack through-table.
- *Deferrals confirmed:* "needed by WO-x" receiving triage — MaterialLot has **no
  forward demand linkage** (consumption hook now pays a third time); "+N with this
  setup" real version = rung 2 (part-type+step approximation for v1); ~min/pc =
  rung 2 std times.
- *Asymmetry:* QA home = pure exposure over existing QMS models, **zero new
  tables**; operator home owns both new aggregates; the FPI loop and
  OperationBlocker each serve both surfaces.

**Open decisions:** THEN-empty at narrow scope (leave sparse vs backfill nearby);
skip-with-reason prompting threshold; QA landing five-workflow treatment; shared-kiosk
operator switching (only if station tablets happen).
