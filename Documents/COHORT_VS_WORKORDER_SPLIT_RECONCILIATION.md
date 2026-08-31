# Cohort Split vs Work-Order Split — Reconciliation Decision

**Status:** VERIFIED — four read-only investigation agents (backend call-graph, frontend surfaces, semantics/tests, re-convergence) completed 2026-08-23. §4–§6 proposals are now ratified against how production actually behaves; §7 records verified findings and the correctness risks they surfaced.
**Scope:** How parts leave and rejoin a lot, across the two pre-existing split mechanisms and the new lock-step batch + `rejoin_cohort` work.

---

## 1. Why this doc exists

Building lock-step batches + `rejoin_cohort` surfaced a **second** "send parts out, bring them back" mechanism at a different granularity, plus a **third** "advance the lot together" mechanism. Before building UI we need an explicit division of labor and to fix the correctness gaps the coexistence creates.

## 2. The mechanisms

| | Grain | Send-out | Bring-back | Reasons | Provenance |
|---|---|---|---|---|---|
| **WO split** | moves parts to a **new child WorkOrder** | `split_work_order` — viewset `split` (`viewsets/mes_lite.py:1997`) | `undo_split` (`work_order.py:449`; viewset `:2020`; FE `SplitWorkOrderUndo.tsx`) | QUANTITY, OPERATION, REWORK | `WorkOrder.parent_workorder` + `WorkOrder.split_reason`/`split_at`/`split_by` |
| **Cohort split** | decouples a part **within the same WO** | `split_part_from_lot` (`splits.py:52`; viewset `:829`) | **`rejoin_cohort`** (NEW, `splits.py:180`) | QUARANTINE, REWORK, SCRAP | `Parts.split_from_cohort` + `split_reason`/`split_at` + **`rejoined_at`** (NEW) |
| **Lock-step** (NEW) | scheduling cohesion | solver **holds** WO while any part is cohort-split | releases when cohort reconverges | — | `WorkOrder.lockstep_batch`, `OptimizationConfig.default_lockstep_batch`, `ScheduleResult.held_lockstep_count` |

**Plus a third "advance the lot together" mechanism** discovered during verification: the legacy `requires_batch_completion` staging (`parts.py:271-345`, `pass_threshold` / `cohort_readiness_fraction`), which predates the new lot-cohesion COHORT engine (`advancement.py`) and expresses the same all-or-none intent. Lock-step/rejoin target the *new* engine and effectively supersede the legacy staging for split parts.

## 3. Verified: what production actually does

- **Canonical rework path = COHORT split, via QMS disposition.** A REWORK/REPAIR disposition (`decide_disposition` → `DispositionSerializer` routing) sets the part `REWORK_NEEDED` and, when the process has exactly one REWORK step, calls **`split_part_from_lot(reason=REWORK)`** (`qml/disposition.py:257-265`). Exit is auto-detected in `advance_part_step` and closes the disposition (`parts.py:387-419`). The `POST /api/Parts/{id}/split_from_lot/` endpoint is the manual equivalent (FE: per-part dropdown in `WorkOrderControlPage.tsx`).
- **WO-split REWORK is vestigial.** HTTP-reachable via `WorkOrderViewSet.split`, but **zero service/task/disposition callers and zero tests**. Its REWORK branch is semantically different (moves parts to a *different* `target_process`, resets to `PENDING`/`step=None`) — a manual "move units to a rework WO on another process," not the in-process loop-back QMS performs. QUANTITY/OPERATION are the plausibly-live uses of that endpoint.
- **No finished-goods regrouping exists.** Parts reach terminal status individually; only the WO-completion cascade waits for all parts+cores to be terminal (`parts.py:89-137`). Cross-WO pegging (`solver.py:552-574`) is *assembly* convergence (parent-behind-components), not batch reunification. `undo_split` reunifies at the WO grain via the `work_order` FK.

## 4. Decision — division of labor (RATIFIED)

**Principle: grain is chosen by whether rework changes the job's routing.**

- **Cohort split** = in-WO advancement decoupling for QA events that keep the part on its own WorkOrder + routing: QUARANTINE (hold), REWORK-in-place (redo a step on the *same* process), SCRAP (remove). Return: `rejoin_cohort`. **Lock-step operates here.** This is the canonical rework path.
- **WO split** = structural change to the shop-order set: QUANTITY (partial ship / priority), OPERATION (route a distinct subset), REWORK-to-a-different-process (rework needing its own routing). Return: `undo_split` or independent completion.

**Boundary rule for REWORK:** *same process → cohort split; dedicated rework process → WO split.* Production already follows this (disposition uses cohort split); WO-split-REWORK stays as the rare "different-process" tool.

## 5. Lock-step semantics & interaction decisions

**REVISED 2026-08-23 — lock-step is NOT a hold.** The first implementation dropped the *entire* WO from the plan whenever any part was split to rework ("whole lot waits"). That punishes the whole batch for one part's detour — worst at scale (one straggler parks ~1,999 of a 2,000-part lot) — and, combined with the unwired release (§7), parked lock-step WOs permanently. **Decision: the cohort keeps progressing; held parts are carved out.**

- **Lock-step = the WO's non-held parts schedule as one cohesive lot** — one occupancy per step, one synchronized start, moving the route together. This is the lot-grouping the scheduler already does; it stays. `lockstep_batch` (default on) is the WO toggle for it. Its future OFF meaning is "let the lot break into transfer batches to pipeline" (the 50-vs-2000 sizing lever; needs transfer-batching, deferred).
- **Held (`split_from_cohort`) parts are carved out of the cohort lot** — group by (step, split-state) so a rework part never merges into or drags the cohort. The rework part schedules as its **own** small lot (so the rework shows on the plan) and reconverges via `rejoin` when it catches up, else at finished goods (the WO-completion cascade already waits for all parts to be terminal).
- **The hold is removed** — `held_wo_ids` / the skip-the-WO logic / `held_lockstep_count` come out.
- **Physical batch steps** (furnace/plating — `requires_batch_completion`) still wait for the whole load; that's a real process constraint, untouched.
- **Lock-step ignores WO-split by design.** Parts leaving via WO-split are a separate job; the cohort isn't affected by them.
- **Child-WO inheritance:** child `lockstep_batch` = null (inherit tenant default); the parent's remaining cohort continues as its own lock-step lot.
- **Warn (soft) on splitting a lock-step WO** — you're deliberately dividing a keep-together batch.

## 6. Naming & consolidation (RATIFIED: standardize on "lot")

**Finding — it's one mechanism with drifted vocabulary.** "Cohort split" and "split from lot" are the same concept (a part's membership in its WO's synchronized flow): `split_part_from_lot` *sets* `split_from_cohort`, `rejoin_cohort` *clears* it — inverses on one field. But the codebase calls it both "lot" (`split_part_from_lot`, endpoint `split_from_lot`, FE `splitFromLot`, `try_advance_lot`, `LotAdvanceResult`) and "cohort" (field `split_from_cohort`, new `rejoin_cohort`, advancement internals). The pair `split_part_from_lot` / `rejoin_cohort` doesn't even match itself.

**Decision — standardize on "lot".** It is the manufacturing-standard term (lot control / lot traveler / lot split) and is already the *public* surface (endpoint + service + FE), so standardizing on it keeps the public API untouched; standardizing on "cohort" would force a breaking endpoint rename. "Consolidation" here means symmetric naming + co-location (split & rejoin are inverses — they can't merge into one function), not fewer functions.

**Rename set (all internal — no schema/FE break; field + reason are not FE-exposed):**

| From | To | Cost |
|---|---|---|
| `rejoin_cohort` (service) | `rejoin_part_to_lot` | **free now** (tests only; no production caller yet) |
| new endpoint (unbuilt) | `POST /Parts/{id}/rejoin_to_lot/` | build it named right |
| `Parts.split_from_cohort` (field) | `Parts.split_from_lot` | migration + ~6 internal files (advancement, solver, data, disposition, splits) |
| `Parts.split_reason` / `split_at` | `Parts.lot_split_reason` / `lot_split_at` | **also resolves the WorkOrder name collision** |
| `Parts.rejoined_at` | keep, or `rejoined_to_lot_at` | migration |
| advancement vars `cohort` / `split_parts` | `in_lot` / `split_parts` | comments/vars only |

**Timing:** `rejoin_cohort` has no production caller yet, so renaming it is free *only until it is wired*. Do the renames in the same pass as the P0 wiring (§8.1).

**Keep the WO grain separate — do NOT consolidate across grains.** `split_work_order` / `undo_split` is a different mechanism (WO grain). Keep the grain visible: **WO split** vs **lot split**. WorkOrder retains `split_reason`/`split_at` (`WorkOrderSplitReason`); the Part fields move to `lot_split_*` — this is what ends the collision. (Optional, cosmetic: `undo_split → merge_work_order` for WO-grain pair symmetry.)

**Regen watch:** ensure `spectacular` does not collapse the WorkOrder enum (QUANTITY/OPERATION/REWORK) and the Part lot-split enum (quarantine/rework/scrap) into one shared `SplitReasonEnum`.

## 7. Verified findings & correctness risks

Prioritized; each cites the confirming agent evidence.

### P0 — reshape lock-step (remove the hold) + wire re-convergence
- **Diagnosis:** the shipped lock-step held a WO out of the plan on any rework split, and `rejoin_cohort` (the only thing that clears `split_from_cohort`) has no production caller — so a reworked part stays split after `_close_open_rework_disposition` (`parts.py:387-419`) closes the NCR, and with `default_lockstep_batch=True` the held WO parks permanently (`held_lockstep_count` pinned).
- **Resolution (per §5 revision — the hold is removed, not repaired):** schedule the cohort *minus* held parts — group the WO's lots by step **and** split-state so a `split_from_cohort` part never merges into the cohort lot; carve rework parts into their own lots. Delete `held_wo_ids` / the skip-the-WO logic / `held_lockstep_count`. Then wire **`rejoin_part_to_lot`** into the rework-step exit in `advance_part_step` (fires once the part has caught up to its siblings — satisfying the sibling precondition) and expose a **`rejoin_from_lot`** viewset action mirroring `split_from_lot` for the manual case. Re-convergence is now about lot cohesion + reporting, not releasing a hold.

### P1 — data-integrity holes from the two mechanisms coexisting (WO-split path; currently manual-only since WO-split has no production caller)
- **Orphaned cohort flag on WO-split children.** `_select_parts_for_split` (`work_order.py:347-370`) applies no `split_from_cohort` exclusion, and the bulk `.update()` never resets the cohort fields — so a cohort-split part carried into a child WO rides `split_from_cohort=True` into a WO where it's meaningless (silently dropped from child cohort gating; for REWORK, orphaned at `step=None`/PENDING while still flagged). **Fix:** exclude cohort-split parts from WO-split selection, or reset the cohort fields on reassignment.
- **`undo_split` can't restore clean state.** Doesn't clear `split_from_cohort`/`split_reason`, doesn't restore the original step for REWORK splits (parts return at `step=None`/PENDING), doesn't clear `parent_workorder_id`. **Fix:** reset cohort fields + restore step on undo.
- **SCRAP is not reliably terminal via the split path.** `split_part_from_lot(reason=SCRAP)` writes only the cohort fields, **never `part_status=SCRAPPED`** (`splits.py:109-153`); SCRAPPED is set on a *different* path (disposition cascade). So a scrap-*split* part stays schedulable (`data.py:367-368`) **and rejoinable** — contradicting `rejoin_cohort`'s docstring. **Fix:** either have the SCRAP split set `SCRAPPED`, or have rejoin's terminal guard also reject `split_reason == scrap`.

### P1 — traceability (AS9100)
- **WO-split / undo_split bypass django-auditlog.** Part reassignment, step-nulling, and status resets go through bulk `Parts.unscoped.update(...)`, which fires no signals → **no LogEntry for parts moving between work orders** (only the child WO create/archive are logged). Serious for a traceability product. **Fix:** iterate + `save()`, or write explicit audit entries. (Pre-existing, independent of this work.)

### P2 — consistency / robustness
- **Divergent, under-gated authorization.** Cohort-split endpoint is gated by `add_parts` (semantic mismatch — splitting isn't creating); WO-split/undo by `add_workorder` with no service-level auth check; neither uses an action-specific perm. **Fix:** add `action_permissions` for split/rejoin/WO-split with a coherent "who may fragment a lot" perm.
- **WO-split has no idempotency** (retries create duplicate child WOs) — unlike the locked, guarded cohort-split.
- **`rejoin_cohort` sibling guard can't reunite a WO-split-relocated cohort** — fails closed (safe) but the rejection message misdescribes the cause.

### Test gaps
- **Zero tests for `split_work_order` / `undo_split`.**
- No cross-mechanism test (a part both cohort-split and WO-split).
- SCRAP terminality unasserted; permission gating of split endpoints untested; rejoin sibling-guard-after-WO-split untested.

## 8. Recommended build sequence

1. **P0 first — reshape lock-step + land the naming in the same pass:** (a) **remove the hold** — delete `held_wo_ids` / skip-the-WO / `held_lockstep_count`; (b) **carve out held parts** — group the WO's lots by step + split-state so the cohort schedules without the rework parts, which get their own lots; (c) **wire re-convergence** — call `rejoin_part_to_lot` at the rework-step exit in `advance_part_step` + add the `POST /Parts/{id}/rejoin_to_lot/` endpoint + FE action. **Fold in the §6 renames here** (`rejoin_cohort → rejoin_part_to_lot` while it's still free, `split_from_cohort → split_from_lot`, `split_reason/split_at → lot_split_reason/lot_split_at`) so the reshape and the vocabulary land together. Lock-step keeps the cohort as one cohesive lot; it no longer holds the batch for a straggler.
2. **P1 data-integrity fixes** to the WO-split/undo path (lot-flag reset, step restore, SCRAP terminality) — cheap and prevent latent corruption if that endpoint is ever used.
3. **(folded into §8.1)** — the naming rename now happens with the P0 wiring, not as a separate step.
4. **Auditlog fix** for WO-split/undo (traceability).
5. **P2 + tests** — permission coherence, idempotency, the missing test coverage.
6. **Then** the FE/serializer surfacing work (rejoin action, held indicator, genealogy badges, lock-step toggle) from the change list.

---

*This doc supersedes the earlier DRAFT. §4–§6 are decided; §7 is verified against the code with agent evidence.*
