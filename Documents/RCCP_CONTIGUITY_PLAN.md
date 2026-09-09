# RCCP contiguity plan

Making the rough-cut layer join up with the detailed solver and the material side,
so the three stop being islands that each re-derive the same facts differently.

## The one structural problem

**RCCP speaks only in hours-per-bucket. It has no notion of elapsed time.**

`_step_hours` returns work content; `_add_spread_load` smears it across buckets;
`build_capacity_load` sums. Nowhere does the module know how long anything *takes*.

Everything we want from it needs elapsed time:

| Want | Needs |
|---|---|
| planned release dates | lead time |
| honest CTP promises | lead time |
| vendor trips visible in the long view | OSP elapsed calendar time |
| material demand phased into buckets | when each op actually runs |

So the spine of this plan is: give RCCP an elapsed-time vocabulary, built from inputs
the solver **already has**. Establishing that took most of a session and the conclusion
was consistent — *nothing needs adding to the schema*. Every input exists.

## Inputs that already exist (do not re-invent)

| Component | Source | Consumed by |
|---|---|---|
| setup + run × qty | `StepTiming` → `rccp._step_hours` | RCCP ✅ |
| OSP vendor turnaround (calendar) | `data.get_outside_process_data` — 4-tier fallback: step → supplier → tenant config | solver only ❌ |
| parts currently at a vendor | same function's `return_min` | solver only ❌ |
| queue per step visit | `StepExecution.started_at − entered_at` | nobody ❌ |
| move between ops | `next.entered_at − prev.exited_at` | nobody ❌ |
| operator-vs-machine split | `StepTiming.attention_type`, `load_unload_per_piece` | nobody ❌ |

Two fields I proposed during design already exist in better form
(`Steps.outside_process_lead_days`, and per-operation queue as measurable history).
Anything that looks like a missing field should be checked against this table first.

---

## Status

Backend through Phase 2 is built; the rest is UI.

- ✅ **Horizon filter** — `get_active_workorders(tenant, within_horizon=False)`. RCCP/CTP
  were inheriting the solver's arithmetic guard, so the layer built to see past the
  detailed window couldn't, and CTP promised capacity without counting far-dated load.
- ✅ **Machine/labor split** — `_step_hours` returns `(machine_hours, labor_hours)` and
  calls `machine_wall_time` / `operator_attended_time` instead of hand-rolling one figure
  for both lanes.
- ✅ **`AttentionType.UNATTENDED`** (migration 0167) — robot/cobot-fed, setup only, and
  ignores a stale `load_unload_per_piece` rather than trusting it to be zero.
- ✅ **`StepTiming` exposed** — nested `timing` on `StepsSerializer`, and added to
  `create_new_step_version`'s child copies (versioning a step was orphaning its timings,
  which reads as a free step rather than an error).
- ✅ **Vendor time reaches RCCP** — `get_outside_process_step_days` extracted from
  `get_outside_process_data` so both layers share the four-tier chain.
- ✅ **Measured queue/move** — `planning/flow_times.py`, p75 per work centre from
  `StepExecution`, unmeasured centres omitted rather than guessed.
- ✅ **Lead days + planned release dates** — `_lead_days` (work content / rate + vendor
  days + measured waiting); `_load_span` returns a DATE, and `build_capacity_load`
  surfaces `planned_releases` with `overdue` and `is_estimate`.
- ✅ **CTP response typed** — was `OpenApiTypes.OBJECT`.

**Next is UI:** the "what must release soon" list beside the heatmap (`planned_releases`
is already on the response), then Phase 3 materials and Phase 4.

## Phase 0 — corrections (independent, do first)

Small, verified, and they stop the surface drifting while later phases build on it.

1. **CTP response schema.** `capable_to_promise` declares
   `responses={200: OpenApiTypes.OBJECT}` — an untyped blob — while `capacity_load`
   beside it is fully annotated. The hook layer then hand-writes `CtpQuote` and casts
   (`as never`, `as Promise<CtpQuote>`), so the contract lives in a Python dict literal
   and a TS type with nothing tying them. Give it an `inline_serializer`, regenerate
   schema + FE types, delete the hand-written type.
2. **`months` default mismatch** — 12 in the viewset, 24 in the service.
3. **Decide the `attention_type` question** (see Open questions). Blocks trusting any
   labor number, so decide before Phase 2 surfaces dates built on them.

## Phase 1 — lead time  ← keystone

A `lead_days(wo)` derivation. Everything downstream depends on it; nothing downstream
works without it.

```
lead_days = work_content(qty) / daily_rate      # StepTiming, already quantity-correct
          + Σ OSP elapsed calendar days         # get_outside_process_data, already written
          + Σ measured queue + move             # StepExecution history, per work centre
```

Why this shape (settled during design, don't relitigate):

- **Never store a lead time per part or process.** Lead time scales with quantity; a
  stored constant cannot. SAP and IFS both split lot-size-*dependent* (run × qty) from
  lot-size-*independent* (setup, queue, move) for exactly this reason.
- **Never store queue as a planning input.** A fixed per-operation queue inflates short
  jobs (12 ops × 1 day on a 3-hour job) and drives *lead-time syndrome* — padded lead
  times cause earlier release, which raises WIP, which lengthens queues, which appears
  to justify the padding. Measurement can't self-confirm that way.
- **Queue belongs to the resource, not the step.** The same op behind a busy machine and
  an idle one queues differently. Aggregate per work centre.

Work: a queue/move aggregation over `StepExecution`, and a `lead_days` service that
combines the three terms. Call `get_outside_process_data` rather than re-deriving.

> This is the same **time-in-system** measurement WLC needs before enforcement can move
> off advisory. One piece of work, three consumers: lead times, WLC, CTP dates.

## Phase 2 — planned start dates

RCCP already computes a start position and throws it away: `_load_span` returns
`(lo, hi)` bucket indices and `lo` is discarded into `_add_spread_load`.

- Replace the span heuristic with `planned_start = due_date − lead_days`. Currently the
  span is `ceil(work_hours / capacity)`, which treats work content as elapsed time and
  assumes zero queue — so it under-estimates lead time and advises releasing *later than
  is safe*, the wrong direction for a surface meant to prevent surprises.
- Emit `planned_start` as a **date** on the RCCP response. A bucket label ("2027-03")
  isn't actionable; a date is, and bucket placement falls out of it for free via
  `_bucket_index`. One derivation, two uses.
- Add a **"what must release soon"** list beside the heatmap — the actionable companion
  the page currently lacks. The heatmap says where it's tight; this says what to do.
- **Do not auto-write `expected_start`.** It is the first branch of the placement rule,
  so writing back makes the system self-referential — the next run reads its own guess as
  authoritative and never re-evaluates. Firming is an explicit planner act, as release
  already is (`released_at` is read-only on the serializer with its own gated endpoint).

## Phase 3 — materials as a third lane

- Time-phase `mes/requirements.sourcing_requirements` into RCCP's buckets. Today it
  aggregates every open work order into **one** total per material and **one** earliest
  need-by — so it answers "short 400 seals, order by Mar 3" and cannot answer
  "100 in March, 200 in June".
- Place material demand at the **planned start** from Phase 2, not the work order due
  date. This is why lead time comes first.
- Render as a third lane beside Labor and work centres.
- Bucketing machinery already exists (`_month_buckets`, `_bucket_index`); BOM explosion
  and lead-time-offset netting already exist in `requirements.py`. This phase is joining
  two working halves, not building either.

*Out of scope, note it and move on:* projected available balance (rolling stock forward
bucket by bucket, netting gross requirements, offsetting to planned order releases).
Without it far-bucket material numbers are a BOM multiplication rather than a plan.
Real, but a separate piece of work.

## Phase 4 — from report to planning tool

Only worth building on numbers Phases 1–3 make trustworthy.

- **Drill-down**: a hot cell names the orders making it hot. Currently terminal — you
  learn Cell A is 140% in 2027-03 and have nowhere to go.
- **What-if on capacity**: the page already tells planners the remedy is *"overtime, an
  extra shift, or subcontract"* and offers no way to test any of them.
- **CTP quote persistence**: a promise currently reserves nothing, so the next quote is
  blind to it. Same shape as the material reservation gap.

---

## Open questions (need answers, not assumptions)

1. ~~Is the labor overstatement deliberate?~~ **Answered — it's a defect with an existing
   fix.** `TimingData.operator_attended_time(qty)` already implements the policy
   (`full` → whole machine run; `load_unload` → setup + touch per piece; `unattended` →
   setup only). `ref.timings` holds those very DTOs, and `_step_hours` calls neither
   accessor — it reaches into the fields and hand-rolls `machine_wall_time` inline, then
   uses that one figure for BOTH the machine lane and the labor lane.

   **Fix:** `_route_hours` should call `machine_wall_time(qty)` for the work centre and
   `operator_attended_time(qty)` for labor. The solver already decided the policy; RCCP
   just doesn't ask. Fold into Phase 1.

2. **Untimed steps return `0.0` silently.** A routing nobody has timed reads as free
   rather than unknown. `TimingData.cycle_source` (`'timing' | 'history' | 'expected' |
   'none'`) already carries the provenance, so RCCP *can* distinguish "no work" from "not
   measured" — it just doesn't. Should it surface untimed steps rather than absorb them?

   Note `load_unload_per_piece` has no equivalent provenance, which is why a zero there
   was ambiguous between "a robot does it" and "nobody filled it in". `AttentionType.
   UNATTENDED` now states the first case explicitly.

3. **Queue with no history** — fallback when a work centre has too few executions to
   aggregate? Tenant default, global median, or omit the term and say so?

4. **Queue granularity** — per work centre, or per (work centre, step type)?

## Sequencing

`0 → 1 → 2 → 3`, with `4` after `2`. Phase 0 is independent and can land immediately.
Phase 1 is the keystone; 2 and 3 are both blocked on it.

## Verification

- `python manage.py test Tracker.tests.test_planning_rccp Tracker.tests.test_planning_api
  Tracker.tests.test_scheduling_horizon --noinput` per phase.
- Any `serializers/`/`viewsets/` change → `spectacular --file schema.yaml --fail-on-warn`
  → `bun run generate-api` → `bun run typecheck`.
- Tests summing `load_hours` across buckets need tolerance: the response rounds each
  bucket to 0.1, so an order spread over N buckets can drift ~0.05 × N.
- `_RccpFixture` is a mixin, not a base TestCase — subclassing a TestCase to reuse setUp
  re-runs all its tests in the subclass.
