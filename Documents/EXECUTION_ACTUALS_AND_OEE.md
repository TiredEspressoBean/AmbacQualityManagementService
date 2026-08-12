# Execution Actuals Capture & OEE

> **Status (2026-08-10): design — not started. Foundational; build first.**
> This is the shop-floor capture loop that makes durations and OEE *honest* —
> the execution feedback loop the scheduler is gated behind
> (OPERATOR_EXPERIENCE_DESIGN §10, rungs 2–3). One capture feed, three
> consumers: the CP-SAT scheduler's duration model
> (`SCHEDULING_IMPLEMENTATION_PLAN.md` / `DURATION_ESTIMATION.md`), OEE, and
> labor. Build this **before** the solver — it takes calendar time to season,
> and a solver on empty/dishonest actuals produces fiction.

## Why this is its own concern

The scheduler and OEE are only as good as the actuals underneath them, and
those actuals do not exist in usable form today (`StepTiming` empty, no machine
attribution on executions, no OEE rollup). Capturing them cleanly is a distinct
build from the scheduler — and a shared one: the *same* start/stop/count/downtime
feed powers duration-learning, OEE, and labor tracking. Design it once, feed all
three.

## Data-quality principle: garbage-in is impossible by construction

The goal is not "validate inputs" — it's that there is **no path to enter a
false timestamp in the first place**.

- **Immutable, system-captured timestamps.** Timestamps are emitted by the
  system from real events, never typed by a user. `StepExecution.entered_at` is
  already `auto_now_add`; `started_at` / `exited_at` are stamped by work events,
  not edited.
- **DWI submit *is* the exit event.** At the end of a DWI the operator submits
  their information, and that submit stamps the exit timestamp onto
  `StepExecution`. The timestamp is a byproduct of a **mandatory,
  advancement-gating** action — you cannot finish the step without submitting —
  not a discretionary "remember to clock out." This closes the biggest capture
  failure mode (the forgotten/late clock-out) by fusing the stamp to genuine
  work-completion intent.
- **No editing. Corrections are flagged, never overwrite.** There is no edit path
  for a captured timestamp. If a correction is genuinely needed, the original
  sample is **invalidated / marked "poison"** (excluded from duration-learning and
  OEE) and the vetted correction is recorded *alongside* it — the raw capture is
  preserved. Matches the repo grain: `django-auditlog`, `VoidableModel.void()`,
  and the existing `StepExecution.training_authorization` override snapshot
  (who / why / when, preserved not overwritten).
- **Separation of duties on corrections.** The correction permission sits **above
  operator** — a supervisor/vetter must approve, with a documented reason, that a
  change is warranted. Wire into the 3-paradigm permission system (a
  `change_*_timestamp`-style perm gated to a supervisor group + per-instance
  vetting).

### The honest limit of immutability

Immutability guarantees data is **un-tampered**, not that it is **true**. A
clean, unedited stamp can still be inaccurate (a late submit measures presence,
not work). The mitigations that matter are therefore about *when* and *at what
grain* capture fires, not about locking edits:

- **Submit promptness.** The advancement gate must bite **immediately** — a part
  that is "done but not submitted" must be blocked from moving forward *now*, so
  there is forward-pressure to submit at completion rather than batch-submitting
  at end of shift (which reintroduces late-stamp drift).
- **Start boundary + interior noise.** The DWI submit gives a tight *exit*; the
  *start* (`started_at`) and the interior (setup, waiting, interruptions) are as
  loose as whatever triggers them. See decomposition below.
- **Interruptions.** A single terminal stamp measures *elapsed*, not *run* time;
  a mid-step breakdown inflates the interval unless a `DowntimeEvent` interleaves
  and is netted out.

## Decomposition axis: routing granularity, not element-fields

Two ways to decompose an operation's time elements (setup / cycle / load-unload):
as **fields on `StepTiming`** (element decomposition within one op — the
`OR_TOOLS_INTEGRATION.md` model), or as **separate steps/substeps** in the
routing, each submit-stamped. **Pick one axis; do not do both.**

Decision: **decompose by routing/substep granularity.** Setup is its own
step/substep, load/unload can be too — each carries its own submit-stamped
`StepExecution`. Consequence:

- **`StepTiming.setup_minutes` becomes derivable**, not authored — it is just the
  setup-step's measured execution history. `StepTiming` is reserved for elements
  that are *not* separately observable.
- The `StepTiming` model in `SCHEDULING_IMPLEMENTATION_PLAN.md` Phase 0 should be
  trimmed accordingly once the substep grain is settled.

### Tensions this leaves open (design, not capture)

- **Sequence-dependent changeover is still separate.** A setup *step's* duration
  is context-free; real setup depends on the machine's prior job. The step yields
  *samples*, not the from→to *predictor* — you still need `WorkCenterChangeover`.
- **Internal vs external setup (SMED).** A sequential setup step implicitly forces
  setup to be *internal* (machine idle during it); it cannot express setup
  overlapping the prior run. Known trade-off — may pessimize the schedule.
- **Authoring consistency.** The decomposition is only as good as routings being
  authored to a *consistent* grain across the shop; mixed conventions give
  apples-to-oranges data.
- **Friction vs resolution.** Finer substeps = more submits per part. There is a
  practical floor before operators batch-submit and late-stamp drift returns.

## Machine attribution (#1) — a near-free win

Add `equipment` (FK→Equipments) to `StepExecution`. The DWI submit already
stamps `StepExecution`, so the FK turns every submit into **machine-attributed
coarse cycle time at zero extra operator friction** — the capture event already
exists, it just isn't recording which machine. This is the single field that
turns the existing submit flow into a per-machine duration/OEE feed. Tracked as
decision #1 in `SCHEDULING_IMPLEMENTATION_PLAN.md`.

## What capture buys, staged

- **Now (coarse, honest):** `exited_at − started_at`, captured immutably at
  submit, is a trustworthy "time at step." Feeds the scheduler's duration
  fallback (`StepExecution` historical average → `Steps.expected_duration`) and
  rung-2 "honest ~min/pc & ETAs." An honest early milestone — not all-or-nothing.
- **Later (decomposed, precise):** per-element (setup/cycle/load-unload via
  substeps), per-piece vs per-batch, interruption-netted run time. Higher rung;
  optional refinement. The coarse feed does not wait on it.

## OEE

**The math is trivial** (Availability × Performance × Quality). The entire
difficulty is *inputs*, not computation. The substrate is already OEE-shaped:

| OEE term | Formula intent | Source (exists today) |
|---|---|---|
| **Availability** | run time ÷ planned time | `Shift` (planned) − `DowntimeEvent` (categorized PLANNED/UNPLANNED/CHANGEOVER/CALIBRATION/NO_WORK/NO_OPERATOR/MATERIAL/QUALITY — already six-big-losses-shaped) + `TimeEntry` |
| **Performance** | (ideal cycle × count) ÷ run time | ideal cycle = `StepTiming.cycle_time_minutes` (**must be populated** — same gate as scheduler) + count (Parts are instance-tracked) + run time |
| **Quality** | good ÷ total | `QualityReports`, NCR/quarantine, `Parts` status, `StepExecution.decision_result` |

**To build:**
- An **OEE aggregation service** (greenfield, but trivial math once inputs exist).
  Nothing computes OEE today; `DowntimeEvent` only name-checks it.
- The **ideal-cycle baseline** (`StepTiming`) — the one shared prerequisite with
  the scheduler.
- **Plan-vs-actual variance** (schedule adherence): compare `ScheduledTask`
  (planned) against `StepExecution` / `TimeEntry` (actual) on a common key — ties
  to reconciliation decision #3 in the plan.

## The real long pole (not code)

Capture discipline. OEE and duration-learning are garbage-in-garbage-out; if
downtime isn't logged, or start/stops drift, or counts are wrong, the numbers lie
and the scheduler learns wrong durations. Making capture reliable is a **UX
problem** (near-zero-friction operator capture — the DWI-submit hook is the
lever), a **change-management problem** (people must actually do it), and a
**time problem** (accrue enough clean data to trust). No architecture shortcuts
it — which is exactly why this is the first build, not the last.

## Related docs

- `SCHEDULING_IMPLEMENTATION_PLAN.md` — consumer; #1/#3 decisions, `StepTiming` Phase 0.
- `OR_TOOLS_INTEGRATION.md` — where the actuals feed the solver; time-element model.
- `DURATION_ESTIMATION.md` — the learning layer this feed powers.
- `OPERATOR_EXPERIENCE_DESIGN.md` §10 — the maturity ladder / execution feedback rungs.
- Models: `dwi.py` (DWI submit), `mes_lite.py` `StepExecution`, `mes_standard.py` `DowntimeEvent` / `TimeEntry` / `Shift`.
