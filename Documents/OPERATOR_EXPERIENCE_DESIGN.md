# Operator & QA Landing Experience — Design + Roadmap

*(2026-07-08. Distills the multi-session design arc: three research rounds across ~45
MES/QMS/ERP/connected-worker products, three prototype generations, and the MES maturity
discussion. Companion to `RECEIVING_INSPECTION_DESIGN.md`. §12 backlog is the single
source of truth for remaining work.)*

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

## 5. Research digest (3 rounds, ~45 products)

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

**Hero ranking function:** `up_next = ready ∩ certified ∩ scope(chosen ∪ inferred-from-
history)` ordered by WO priority → due → aging. Contract: *usually right with a
visible escape* — not divinely correct. Empty-at-scope degrades gracefully.

**QA inspector:** two panes — inspection queue (incoming, exists) + "My quality
actions" merged inbox (approvals + CAPA tasks + my dispositions; overdue red). In-
process checks live on the queue page's Checks-due lens; receiving QA stays in
Incoming Inspection.

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

- `/dev/operator-home` — kiosk tiles v3: hero + deviation flow (verified: 2 taps →
  hero swap), scope combobox (verified: Assembly Line scoping), shift notes, two-branch
  problem picker, blocked-count caption.
- `/dev/work-queue` — v3 at-scale: readiness sections, blocked bucket w/ aging +
  Nudge, filter rail w/ comboboxes, horizon buckets; QA lens flat + chips + horizons.
- **Real app (committed):** role-gated home blocks (scan box → *currently the control
  page — retarget to operator surface*, WO queue w/ persona CTAs, inspection queue,
  quality actions), typecheck fixed & clean, seeded demo covers SQM/OSP/DWI.
- **Uncommitted at time of writing:** both /dev prototypes, this doc.

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

**Open decisions:** THEN-empty at narrow scope (leave sparse vs backfill nearby);
skip-with-reason prompting threshold; QA landing five-workflow treatment; shared-kiosk
operator switching (only if station tablets happen).
