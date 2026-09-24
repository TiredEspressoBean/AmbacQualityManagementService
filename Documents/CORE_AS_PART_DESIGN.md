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
| DISASSEMBLED | `CORE_BANKED` | waiting on a release decision, not being worked |
| AWAITING_AUTHORISATION | `CORE_BANKED` | waiting on the customer — **deliberately unschedulable** (today it is scheduled) |
| IN_REBUILD | `IN_PROGRESS` | |
| REBUILT | `COMPLETED` | |
| DECLINED | `AWAITING_PICKUP` | going back unrepaired |
| RETURNED, RETURNED_UNREPAIRED | `SHIPPED` | |
| HARVESTED | `DISMANTLED` (**new**) | the unit no longer exists as one; its components are parts now |
| SCRAPPED | `SCRAPPED` | |

`DISMANTLED` is the one new part status. Nothing existing fits: `SCRAPPED` says the unit
was rejected, `COMPLETED` says it was built.

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

## 9. Rollout

Each phase ships green on its own.

1. **Link.** `Core.part` added; every core mints a part (data migration); receipt and
   `bulk_create` write both. Nothing reads the link yet.
2. **Generic machinery onto the part.** Step execution, transition log, scheduling and
   assembly usage run on `core.part`; the four FKs and XOR constraints go; the mirrored
   engine collapses; `part_status_for` + invariant test.
3. **DWI for teardown and rebuild.** The runtime runs core parts; install capture node;
   entry points repointed; standalone disassembly screen redirected.
4. **Reman services and staging re-keyed**, the 17-file audit, `Core.work_order`/`step`
   removed.
5. **Bulk lots and assigning identity**, bank and RECOVER lane counting lots.

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
