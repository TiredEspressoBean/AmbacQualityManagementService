# A core is a part — "core" is a role it plays

Status: design, 2026-09-24. Dev-only data, so migration can reseed where simpler.

## 1. The problem

UQMES models a core as its own kind of unit, beside `Parts`. Every piece of generic
shop-floor machinery therefore has to be built twice or cores go without it, and the
evidence is in the code:

- `models/reman.py` carries a section headed *"WORKFLOW ENGINE METHODS (mirror of
  Parts)"* — `_check_cycle_limit`, `_get_edge`, and a `step` field that "mirrors
  Parts.step".
- Four generic tables point at *a part or a core*: `StepExecution`
  (`step_execution_one_subject`), `ScheduledTask` (`scheduledtask_part_xor_core`),
  `StepTransitionLog`, `AssemblyUsage` (`assemblyusage_one_parent`).
- Twelve part-vs-core branches in services; the scheduler's warm start skips core tasks
  ("no pin/warm-start in v1"); staging skipped cores outright until 2026-09-23.
- **The operator's DWI runtime cannot run a core at all.** The core step engine
  (`begin_core_step_execution`, `advance_core_step`) is tested but no endpoint reaches
  it, so teardown runs on a standalone screen that skips the process steps entirely.
  Dev has 21 cores and **zero** step executions on any of them.

The last point is what forced the question. Operators need their directions and their
data capture through DWI for any unit they work on — teardown and rebuild alike — and
building a parallel core path through the runtime would add one more mirror.

## 2. The decision

**The unit on the floor is a `Parts` row. "Core" is a role that part plays**, held on
the existing `Core` table, one-to-one with the part.

This is how MRO systems model it: the unit that arrives is a serialized part on a work
order; "core" is its commercial role — exchange, credit, whose it is. `PartsStatus`
already has `CORE_BANKED` ("Reman: stored as core"): the part model was designed to hold
cores before the separate model was built beside it.

Not a material: materials here are fungible, tracked by lot and quantity. A core is
individually identified (serial, condition at receipt, owner, credit per unit), a
repair-and-return unit is *this* unit going back, and harvested components trace to the
specific core. Its material-like behaviour — counted by type, supply for planning — is a
*view* of banked parts, which parts already provide.

Not a third hybrid kind: that makes every feature handle three subjects instead of two.

**Bulk receipt is the exception, and it is only a way in** (§6): cores that arrive
unidentified are received as a material lot and given an identity — become parts — when
someone pulls one.

## 3. Shape

```
Parts  (the unit: part_type = the core type, ERP_id, part_status, work_order, step, …)
  ▲ 1:1
Core   (the reman role: core_number, serial_number, customer, fulfilment_mode,
        condition_grade, source, credit, receipt, return, teardown timestamps,
        status = the reman STAGE)
```

- **`Core.part`** — new `OneToOneField(Parts, on_delete=PROTECT, related_name='core_role')`.
- **Generic machinery runs on the part.** `StepExecution.core`, `ScheduledTask.core`,
  `StepTransitionLog.core` and `AssemblyUsage.assembly_core` are removed; their XOR
  constraints collapse to "part required". Anything that needs the role reads
  `part.core_role`.
- **Reman-specific relations stay on the role.** `HarvestedComponent.core`,
  `RebuildSlotOverride.core` and `Parts.reserved_for_core` keep pointing at `Core` — they
  are about the reman role, not generic machinery. This is what keeps the blast radius
  bounded.
- **Duplicated fields move to the part.** `Core.work_order` and `Core.step` are removed;
  `Core` keeps read-through properties during the transition so call sites migrate in
  their own time.
- **The mirrored workflow engine is deleted.** `Core.advance_step`, `_check_cycle_limit`,
  `_get_edge` and `services/mes/cores.py` collapse into the part engine, keeping only the
  reman-specific pieces as hooks: the rebuild-scope skip (`_skip_to_in_scope`) and the
  teardown/rebuild completion at the terminal step.
- **The API keeps `/api/Cores/`** as the role's API. The serializer reads `work_order`,
  `step` and part status through the part, so most of the 27 frontend files barely move.

## 4. Status: part status vs reman stage

Two fields, two questions, one writer:

- `Parts.part_status` answers *can this unit be worked, and where is it in the flow* —
  what the scheduler, gates and queues read.
- `Core.status` (the reman stage) answers *where is it in its reman life* — what the
  reman services read.

**The part status is derived from the stage** by one function, `part_status_for(core)`,
and written by the same service call that moves the stage, so the two cannot disagree.
An invariant test walks every stage.

| Reman stage | Part status | Why |
|---|---|---|
| RECEIVED, on no work order | `CORE_BANKED` | in the bank, not being worked |
| RECEIVED, on a work order | `PENDING` | planned: the scheduler must place it |
| IN_DISASSEMBLY | `IN_PROGRESS` | |
| DISASSEMBLED | `ON_HOLD` (**new**) | waiting on a release decision, not being worked |
| AWAITING_AUTHORISATION | `ON_HOLD` | waiting on the customer — **deliberately unschedulable** (today it is scheduled) |
| IN_REBUILD | `IN_PROGRESS` | |
| REBUILT | `COMPLETED` | |
| DECLINED | `AWAITING_PICKUP` | going back unrepaired |
| RETURNED, RETURNED_UNREPAIRED | `SHIPPED` | |
| HARVESTED | `DISMANTLED` (**new**) | the unit no longer exists as one; its components are parts now |
| SCRAPPED | `SCRAPPED` | |

Two new part statuses. **`DISMANTLED`** — nothing existing fits: `SCRAPPED` says the unit
was rejected, `COMPLETED` says it was built (and would count as output). **`ON_HOLD`** —
added during implementation, correcting the first draft of this table, which parked a
waiting unit in `CORE_BANKED`. `CORE_BANKED` is *terminal* (`TERMINAL_PART_STATUSES`, and
counted as a completed part), so a disassembled repair-and-return unit would have let the
work-order cascade close the order before its rebuild. Waiting must be neither terminal
nor schedulable, and nothing existing was both.

## 5. Identity

- `Parts.ERP_id` = `Core.core_number` — the shop's identifier, unique per tenant by
  constraint (`core_tenant_number_uniq`); no existing part ERP id collides with one. `serial_number` stays on the role for now; `Parts` has no serial field, and
  adding one is its own decision beyond reman.
- Part type = `Core.core_type`. A core type is a `PartTypes` row already.

## 6. Bulk receipt and assigning identity

Some cores arrive individually identified; some arrive in bulk, counted, with no serials.

- **Individually identified** — received straight in as a core part (today's flow,
  `bulk_create`), status `CORE_BANKED`.
- **In bulk** — received as a `MaterialLot` with `material_type` = the core type and a
  quantity. `MaterialLot` already carries lot number, received date/by, quantity,
  quantity remaining, storage location and parent lot.
- **Assigning identity** — `assign_core_identity(lot, *, core_number, serial, user)`
  mints the part and its role, decrements `quantity_remaining`, and links
  `Parts.received_in_lot` (new FK) so the unit traces to its bulk receipt. From there it
  is an ordinary core.
- **Only exchange cores may stay in bulk.** Repair-and-return means *this* unit goes
  back, which needs an identity at receipt: a bulk lot can only be received as exchange.
  That is definitional, not shop policy, so it is enforced.
- **When** an exchange core gets its identity is the shop's call — at receiving
  inspection, when pulled for teardown, any time. Nothing forces a point.
- **The core bank** = banked core parts + unassigned quantity in core lots. The
  recoverable-supply forecast and the RECOVER lane count both; accepting a teardown
  proposal from a lot assigns identities as it commits units.

## 7. What changes, by area

| Area | Change |
|---|---|
| Models | `Core.part` (1:1); drop 4 generic `core` FKs and their XOR constraints; `Parts.received_in_lot`; `PartsStatus.DISMANTLED`; `Core.work_order`/`step` become read-through, then go |
| Step engine | core engine collapses into the part engine; reman hooks for scope skip and terminal completion |
| DWI runtime | runs a core part like any part; teardown and rebuild both go through it. HarvestedComponentCapture binds via `part.core_role`. A rebuild **install** capture node is added (which component went into which slot) |
| Scheduling | `CoreData`/`scheduledtask.core` path removed; core parts are parts |
| Staging, consumption, material gate, requirements | "is reman" / "takes pooled parts" read `part.core_role` |
| Reman services | re-keyed to read the unit through `core.part` |
| Shared part logic (17 files reading part status) | audited one by one — §8 |
| API | `/api/Cores/` kept; read-through fields; new identity-assignment endpoint |
| Frontend | entry points open the DWI runtime; the standalone disassembly screen is retired (redirected) |
| Seed data | seeders mint core parts; dev reseeds rather than migrating in place where simpler |

## 8. The 17 shared files — default is "cores included"

A core part becomes visible to everything that reads parts. Default: **included**, since
that is the point — sampling, gates and quality records apply to a unit being worked
whatever its role. Excluded only where a rule is about *building new product*:

- `services/mes/bom.py`, `makeup.py`, `work_order.py` — BOM explosion and quantities:
  a teardown work order's quantity is its cores, not units to build.
- Throughput/completion metrics that mean "units produced" must not count a harvested
  (`DISMANTLED`) core as output.

Each file is checked in phase 2 and the result recorded in its commit.

### 8a. The audit (phase 4, 2026-09-24)

The "17" was an estimate; the real set is every service, serializer and viewset that
reads or writes `part_status` — about 40 files. They split by whether they WRITE it.

**Readers — included, unchanged.** Sampling, quality gates and reports, the inspection
inbox, batch lifecycle, outside processing (its statuses are in-flow and QA holds),
change-control impact analysis, dispatch lists, exports, dashboards, scheduling and
release. A core is a unit being worked; these apply to it as to any part.

**Writers of an ENDING — each now asks `core_part` first.** Writing a terminal status
straight onto a core's part leaves its stage behind (the core still "in teardown"), and
the next stage write revives the part. So:

| Writer | For a core |
|---|---|
| Disposition SCRAP | `scrap_if_core` — scrapped by its stage |
| Lot split SCRAP (both paths) | `scrap_if_core` |
| Change-control remap SCRAP | `scrap_if_core` |
| Bulk set status | scrap → the stage; any other ending, or reopening an ended core, refused (`assert_status_settable`) |
| Parts API PATCH | ending or scrap refused (scrap it from the core); moving its work order refused (teardown planning places cores) |
| Work-order quantity reduction | NOT cancelled — back to the bank (`release_from_order_if_core`) |
| Rework work-order split | refused — a core is reworked inside its teardown or rebuild |
| Step rollback | allowed only while teardown or rebuild is under way |
| Step-end in `advance_part_step` | already `finish_route` (phase 2) |

QA holds (quarantine, rework-needed) and in-flow statuses stay settable on a core's part
as on any part; `sync_part_status` preserves a hold across stage changes.

**Excluded — building new product.** Make-up planning: a reman order owes no make-up,
since a scrapped customer unit cannot be replaced by spawning another. BOM explosion
already plans reman demand through `services/reman/demand.py`.

**Order progress counts a harvested core as done** (`PROGRESS_DONE_STATUSES`,
decided 2026-09-24): a teardown order's job is to take its units apart. It is still not
output. Noted, not changed: progress counts only COMPLETED/DISMANTLED, so a unit that
went on to SHIPPED reads as unfinished — pre-existing for ordinary parts too.

## 9. Rollout

Each phase ships green on its own.

1. **Statuses.** `ON_HOLD`, `DISMANTLED`, and `part_status_for` with its invariant test.
2. **The cutover** — linking and moving the machinery in ONE step. (The first draft had
   "link first, nothing reads it yet"; that cannot hold, because the moment a core's part
   exists the generic machinery sees it — the scheduler reads `wo.parts`, so a planned
   teardown would be scheduled twice, and completion, sampling and part lists would
   count it.) `Core.part` added and every core given a part; Step execution, transition log, scheduling and
   assembly usage run on `core.part`; the four FKs and XOR constraints go; the mirrored
   engine collapses; `part_status_for` + invariant test.
3. **DWI for teardown and rebuild.** The runtime runs core parts; install capture node;
   entry points repointed; standalone disassembly screen redirected.
4. **Reman services and staging re-keyed**, the 17-file audit, `Core.work_order`/`step`
   removed.
5. **Bulk lots and assigning identity**, bank and RECOVER lane counting lots.

## 9a. Status (2026-09-24)

- **Phase 1 — statuses: shipped** (`b3a1920`).
- **Phase 2 — the cutover: shipped** (`0e01dab`). Generic machinery runs on the part;
  the mirrored core engine is deleted; the scheduler, completion cascade, pick sheet,
  release readiness, diagnostics, RCCP and workload control count a core once, as a
  part. Work-order completion was reworked with care — see its commit and the tests in
  `test_reman_dwi_workflow.WorkOrderCompletionIsJudgedRightTests`.
- **Phase 3 — DWI for teardown and rebuild: in progress.** Every reman entry point opens
  the unit in the operator runtime; the standalone disassembly screen redirects. Two
  findings on the way: the harvest node's operator view was a placeholder (operators
  would have typed component-type ids), and **nothing sent its captures to the server**
  — DWI teardown capture had never worked end to end. Both fixed, with strict
  enumeration now enforced server-side against the authored node. A rebuild install
  node records what went into each slot through `install_component`. The server's
  capture allow-list had never included the harvest node, so its required check never
  saw it; both reman nodes are on it now, and a resumed substep reseeds from what was
  stored. Because these two captures create records (harvested components, installs),
  an identical resubmit is a no-op and a different one is refused.
- **Dispositions on a core's part move the stage.** A SCRAP disposition goes through
  `scrap_core`; written straight to the part, the core would have stayed "in teardown"
  and the next stage write revived it. `DISMANTLED` joins the terminal ranks, so a
  later USE_AS_IS can't revive a harvested unit.
- **Phase 4 — the audit: done** (§8a). Every direct writer of an ending asks
  `core_part` first; `Core.work_order`/`step` read-through removed — a core's position
  is read from its part only.
- **Phase 5 — bulk core lots: done.** `services/reman/core_lot.py`:
  `receive_core_lot` (exchange only — a repair-and-return customer is refused),
  `assign_core_identity` (the unit is graded by whoever holds it; lot locked, so two
  people can't overdraw it; `Parts.received_in_lot` traces it back), `bank_lots`. A core
  type is one cores were received as, or one with a disassembly BOM, so a type first
  seen in bulk still qualifies; the lot itself must be `holds_cores`. The recoverable forecast and the teardown banks count
  unidentified lot units; the RECOVER lane proposes identified cores first, then draws
  on lots (`candidate_lots`). API: `/api/Cores/receive_lot/`, `/assign_identity/`,
  `/lots/`. UI: `/reman/core-lots`. A core lot is marked `MaterialLot.holds_cores`
  (set only at bulk receipt): the first cut treated any lot of a core type as cores, and
  the browser check showed the dev tenant's 1000 PURCHASED Common Rail Injectors in the
  core bank — a reman shop's core type is usually the part number it sells.
  **Decided 2026-09-24:** accepting a proposal commits only identified cores; lot
  units are identified by hand first. This supersedes §6's "accepting assigns identities
  as it commits units": an identity carries a condition grade, and industry practice
  grades a core at inspection, by someone handling it — not at planning. Planning runs
  on counts, which the lane already does. If the extra step chafes, the next step is to
  let a proposal RESERVE lot quantity on the teardown work order and identify units at
  induction (the scheduler and completion cascade would then count reservations).

## 9b. Findings after teardown, and the authorisation hold (2026-09-24)

Kept human by decision: people decide, the system records. Automation can come later,
once there is data on how these are decided.

- **Findings are proposals.** The DWI `rebuildFindingCapture` node lets an operator flag
  one of the unit's own components as worse than teardown graded it (new grade + what
  was found). That sets `HarvestedComponent.proposed_*` and changes nothing else. A lead
  applies it on the rebuild plan (the component takes the grade; the plan and scope
  re-resolve, as they would from a teardown grade) or dismisses it with a reason. Both
  are recorded in `condition_notes` and the audit log. Deciding is gated on
  `accept_component` — a disposition, lead tier — not the operator's `grade_component`.
- **Authorisation stays a lead's act** (`request_authorisation`), but a parked unit is
  now actually parked: `core_steps.assert_workable` refuses to start, capture on or
  advance a unit at `AWAITING_AUTHORISATION`. Not a start-gate refusal, so no supervisor
  override can wave it on — a supervisor cannot answer for the customer.
- **Deferred:** the over-and-above scope document for the customer/pricing system, and
  recording which codes an authorisation covered. Both matter once gating is automatic.

## 9c. Exchange cores are rebuilt to stock (2026-09-24)

Industry norm — diesel reman (the body carries the unit's identity; it is rebuilt
around its own serviceable parts, pooled recovered ones and new) and aerospace rotable
exchange (the returned unit is overhauled as itself into the pool) — is that an
exchange core is normally REBUILT, to stock; harvesting is the fallback for a failed
body or surplus cores. UQMES refused to release an exchange core into rebuild at all,
while planning already planned exchange rebuilds against the recovered pool.

- **Exits by mode.** Repair-and-return: rebuild → `REBUILT` → returned to its customer
  (never harvested). Exchange: rebuild → **`REBUILT_TO_STOCK`** (part `IN_STOCK`,
  reman finished goods), or harvest → `HARVESTED`. A planner picks at release.
- **Identity is kept** (decided): the rebuilt unit is the same part, core number = ERP id.
- **Not component stock.** A rebuilt exchange unit is excluded from component supply
  (`bom._available_parts`), or a build consuming its part type would draw a reman unit
  as if it were new.

## 10. Defaults taken — overrule any of these

These were open; each default prevents nothing, so work proceeds on them.

1. **The stage → part-status mapping in §4**, including `AWAITING_AUTHORISATION` becoming
   unschedulable, and the new `DISMANTLED` status.
2. **Identity:** `ERP_id` = `core_number`; serial stays on the role.
3. **Shared files:** cores included by default (§8).
4. **Bulk credit:** credit is recorded per unit when it is given an identity; a lot
   records count only. (Informational either way — UQMES holds no financials.)
5. **Standalone disassembly screen:** redirected to the DWI runtime, file kept until you
   confirm deletion (CLAUDE.md: ask before deleting files).
