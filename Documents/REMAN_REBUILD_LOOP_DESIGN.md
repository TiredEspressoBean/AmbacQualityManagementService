# Reman Rebuild Loop — Design

Status: **proposed** · Owner: cisherwood · Last updated: 2026-09-10

Companion docs: `REMAN_DWI_INTEGRATION.md` (teardown capture — implemented),
`RECEIVING_INSPECTION_DESIGN.md` (the other "incoming" flow),
`SCHEDULING_IMPLEMENTATION_PLAN.md` (routing + solver), `APS_ROADMAP.md`.

## 1. The gap

Teardown works end to end: a core is received, disassembled, and its components are
captured as `HarvestedComponent` rows with a condition grade, and an accepted component
becomes a `Parts` record in inventory (`services/reman/{core,teardown,harvested_component}.py`,
`CoreDisassemblyPage.tsx`).

Then the story stops. **Nothing creates the rebuild work order.** A graded core sits in
`DISASSEMBLED` with no demand attached to it, no route, no kit, and no way to find it
again except by remembering it exists. The loop is open.

## 2. Two senses of "disposition" — and why they must not share a surface

This is the framing decision this document exists to record, because the word collides
with an existing surface and the collision is not cosmetic.

**NCR disposition** — what `/production/dispositions` (`QaQuarantinePage`) does today.
A part deviated from spec, and someone decides use-as-is / rework / scrap / return. It is
an **exception**: unplanned, per-occurrence, and the record of it is evidence that
something went wrong.

**Grading disposition** — what happens at the grading bench in reman. A used component
comes out of a core and is assessed A / B / C / SCRAP. It is a **canonical step**: every
component gets one, every time, and the outcome is the normal input to what happens next.

Three consequences of keeping them separate:

1. **Wear is not nonconformance.** A Grade C injector body is exactly what a returned
   core is supposed to contain. Routing grading through the NCR surface would raise a
   nonconformance for essentially every core, and the NCR trend and Pareto — the data
   AS9100 expects to drive CAPA — would become noise. Nonconformance data has to mean
   something, and it stops meaning anything if the routine case is in it.

2. **Position in the flow is opposite.** An NCR disposition happens *after* a step
   fails. A grading disposition *is* the step. One is a branch off the nominal path;
   the other is the nominal path.

3. **It changes how routing has to treat the branch** (§5). Exceptions are not scheduled
   ahead of time; canonical outcomes must be, because RCCP and the solver need to plan
   the work that is actually going to happen.

**So: reman grading gets its own surface, on the core, in the reman section.** It does
not appear on `/production/dispositions`, and it does not create `QualityReports` rows.
Where this doc says "disposition" from here on, it means the canonical grading sense.

Worth noting that the industry uses "disposition" the same way we are about to
(§3): in IFS Component MRO an inspection produces **disposition lines**, and an approved
disposition line is what a shop order is created from. The word is right; it is the
*NCR* surface that has the narrower claim on it.

## 3. How the industry models this

Researched 2026-09-10. Two concepts recur across MRO/reman systems and both bear on the
design.

### 3.1 Repair codes — scope is composed, not selected

In IFS Component MRO, **repair codes** are *"groupings of material and operations
recorded in the repair structure and routing."* The flow is:

1. Inspection records **discrepancies** (findings) and modification tasks.
2. Repair codes are **generated automatically** from those findings.
3. The planner **includes or excludes** each generated code, and may add manual codes to
   extend scope. The included set *constitutes the repair work scope*.
4. A shop order is created from an **approved disposition line**, with *"material and
   operations predefined for the MRO shop order based on the repair code setup for the
   part."*

The important structural point: **work scope is the union of selected codes**, not the
selection of one path. Each finding contributes its own operations and materials, and
they compose.

SAP reaches the same place from a different direction — the PM **refurbishment order**
is the serialized repair analogue of a production order, carrying as-received and
as-delivered condition, created by a planner against repairable spares.

### 3.2 Over-and-above — findings can require authorization, not just planning

MRO systems treat work discovered beyond the original scope as its own controlled
process: it is documented, **priced**, and routed for **customer** authorization before
proceeding, with findings thresholds and escalation protocols. If findings change the
scope, the quotation is revised and resubmitted for approval.

This dimension is entirely absent from the current design and from the codebase. Whether
it applies depends on the business model (§10.1).

### 3.3 The two layers, and which one our process flow already is

The pattern above is not one representation but **two, at different layers**, and every
mature MRO system keeps both:

| | **Entry scope** (commercial) | **Accumulated scope** (execution) |
|---|---|---|
| Answers | what was quoted and sold | what was actually done to this unit |
| Shape | a named level | a union of codes |
| Examples | engine shop visit sold as minimum-touch / performance-restoration / full overhaul; LORA repair levels; graded automotive rebuild levels | IFS repair codes; SAP PM catalog codes on a refurbishment notification; aviation non-routine cards raised against a task-card workscope |
| Set by | the order, or the customer's programme | inspection findings, as they are discovered |
| Changes | at quote time | during the job — which is precisely §3.2 |

The gap between the two IS the over-and-above process. A shop visit starts as
"performance restoration", findings extend it, and the unit ships having had a set of
operations no tier name describes.

So tiers are not a small-shop simplification of codes, and the earlier framing in this
document that treated them as competing models was wrong. A tier is the **starting**
scope; codes are how it grows. A shop with three rebuild levels and no findings never
sees a code — but it is using the same mechanism with an empty accumulation, not a
different one.

**Which layer does our process flow already model?** More of it than the first draft of
this section credited. `Processes` + `ProcessStep` + `StepEdge` describe one authored
graph, but a part does not simply walk it in lockstep with its siblings — see §5.1.

**And the findings layer is already built.** This document previously listed
"finding→code mapping" as new capture work. It is not: the system already records, per
unit and per characteristic, whether a reading met its spec.

- `MeasurementDefinition` hangs off a `Steps` row with `nominal` / `upper_tol` /
  `lower_tol`, a `NUMERIC` or `PASS_FAIL` type, and `characteristic_number` — the
  AS9102 / control-plan balloon. The industry's own identifier for a characteristic is
  already a column.
- `MeasurementResult` (inspection grain, on `QualityReports`) and
  `StepExecutionMeasurement` (production-capture grain, on `StepExecution`) both carry
  `is_within_spec`, computed.
- `HarvestedComponent.condition_grade` already grades each component A/B/C/SCRAP.

So a repair code is a mapping from *(characteristic, out of spec)* or *(component,
grade)* to a set of operations. The left-hand side exists and is populated by work the
shop already does. That deletes most of what §5.1 listed as new, and it gives the
proposal real provenance: this code is here because THIS reading on THIS component was
out of tolerance — which is exactly what an over-and-above quote has to show a customer
(§3.2).

One wrinkle to settle when building: the two result models are parallel, both with
`is_within_spec` against the same `MeasurementDefinition`. Scope resolution must say
which it reads, or say it reads both and how it reconciles them.

## 4. The model

**Decided (2026-09-09):** component grades do two jobs at two levels — they roll up to a
core-level rebuild tier that selects the *branch* (which steps run), and they also drive
the *kit* per component (which parts those steps consume). Kit resolution is two-stage:

```
component grades ──rollup──▶ rebuild tier ──selects──▶ branch ──▶ the steps that run
                                                                        │
                                                                   BOM lines on
                                                                   those steps
                                                                        │
component grades ─────────────netting───────────────────────────▶ per line: reuse the
                                                                   harvested part, or
                                                                   consume a new one
```

The netting join is clean because both sides are already `PartTypes`:
`HarvestedComponent.component_type` ↔ `BOMLine.component_type`.

### 4.1 The fork §3.1 opens

The repair-code model does both of those jobs with **one** primitive instead of two, and
it is worth deciding between them before building, because they lead to different
routing work (§5).

| | **Tier → branch** (decided) | **Repair codes** (industry) |
|---|---|---|
| Scope is | one branch selected by a rollup | the union of codes generated per finding |
| Needs a rollup rule | yes — §10.2 | no; findings map to codes directly |
| Combinations | one branch per tier must be authored | codes compose freely |
| Human control | override the tier | include/exclude each code, add manual ones |
| Routing need | conditional branch selection (§5) | operation-subset assembly (§5) |

The scalability argument is the sharp one. A core with a dozen graded components has far
more than three meaningful scopes, and tier-branching forces every meaningful
combination to be authored as its own path, or forces tiers coarse enough to be
inaccurate. Repair codes compose without authoring the combination.

The counter-argument is that repair codes are a **new authoring concept** — a code table,
each code carrying operations + materials, plus finding→code mapping — where tiers reuse
the routing you already have. It is more machinery for a shop that may genuinely only
have three rebuild levels.

**Decision: repair codes, with the entry scope as a named preset over them (§3.3). The
fork is false, and counting one shop's scopes was the wrong way to resolve it.**

UQMES is deployed by shops we have not met. A model chosen to fit the number of rebuild
scopes at the reference customer is a model that fits nobody else by construction — and
the earlier version of this section asked exactly that question, which was a mistake.

The two options are not alternatives. **A tier is a named, pre-composed set of repair
codes.** Build the composing mechanism and a three-scope shop authors three presets and
never sees a code; build tiers and a twelve-scope shop has to author every meaningful
combination as its own routing path, or accept tiers coarse enough to be wrong. One
direction degrades gracefully and the other is a migration.

The genuine objection to codes survives, but it is about the AUTHORING BURDEN on a small
shop, not about the data model — and burden is answered with seeded presets and a
sensible authoring default, not by storing scope differently.

§3.1's *human curation* step is adopted regardless: auto-generate the proposal, let a
person include/exclude it.

What §3.3 adds is that the **entry scope survives as a first-class thing** rather than
as a convenience for small shops. A tenant configures named scopes ("Standard rebuild",
"Full overhaul") as presets over the code set; a core starts with one, and findings
extend it. The three-scope shop authors three presets and never opens the code table.
The twelve-scope shop gets the same presets as starting points and lets findings do the
rest. One mechanism, two entry costs.

### 4.2 Two fulfilment modes, and they are both in scope

**Decided (2026-09-10): the shop does both.** A core either goes back to the customer it
came from, or it goes into stock and the customer receives a different rebuilt unit.
These are not variations on one flow — they differ on identity, on approval, and on what
may be reused.

| | **Repair & return** (their unit) | **Exchange / stock** |
|---|---|---|
| Unit identity | serial preserved end to end | pooled; customer gets *a* unit |
| Scope approval | quote → **customer** authorization before work | internal planning only |
| Over-and-above (§3.2) | applies | does not apply |
| Cross-core reuse (§10.4) | **no** — the unit keeps its own parts | yes — harvest pools freely |
| Loop terminates at | an approved quote, then a WO | a WO |

**This needs a field on `Core`.** `SOURCE_TYPE_CHOICES` (`CUSTOMER_RETURN` / `PURCHASED`
/ `WARRANTY` / `TRADE_IN`) records where a core *came from*, which is not the same
question as where it is *going* — a customer return can be either a unit to repair and
send back, or a core surrendered against an exchange. So: a `fulfilment_mode` choice
field (`REPAIR_RETURN` / `EXCHANGE`) alongside `source_type`, set at receipt.

It has to exist early (§11.1), because almost every later behaviour branches on it. The
mode is also the reason serial tracking matters here at all: under `REPAIR_RETURN` the
serial-bearing part is the customer's property and the chain from teardown to shipment
has to prove it went back into the same unit. This is exactly what SAP's refurbishment
order is carrying when it records as-received and as-delivered condition against a serial.

## 5. Routing implications

`StepEdge` supports conditional routing, but only on a **measurement**:
`condition_measurement` (FK to `MeasurementDefinition`) + `condition_operator`
(`gte`/`lte`/`eq`) + `condition_value` (decimal). A grade is **categorical**, and
encoding A/B/C/SCRAP as numbers to squeeze it through a threshold comparison would be a
lie written into the routing that every later reader has to decode.

The deeper problem is edge semantics. `EdgeType` is `DEFAULT` / `ALTERNATE` /
`ESCALATION`, and `services/scheduling/routing.py::resolve_route` walks **DEFAULT edges
only**, by explicit design:

> The nominal route follows **DEFAULT** edges only. ALTERNATE (rework/fail) and
> ESCALATION (max-visits) branches are exceptions — not scheduled up front.

Correct for rework, wrong for a disposition outcome, which is not an exception but one of
several *normal* paths.

**The escape, under either model in §4, is that the decision is already made by the time
the work exists.** Grading precedes the rebuild WO, so the WO is created with its route
*already resolved*, and the scheduler's DEFAULT-only walk is correct as-is. No solver
change either way.

What differs is what "resolved" means:

- **Tier → branch** needs the process graph to *contain* the branches, so it needs
  categorical conditions on `StepEdge` and an authoring UI for them — or the stopgap
  below.
- **Repair codes** need something the system does not have at all: a **per-WO operation
  subset**, since the route is assembled from the selected codes rather than walked from
  a fixed graph. That is architecturally cleaner (no conditional edges anywhere) but
  touches how a WO's route is established, which today comes wholly from the process.

**Stopgap available to both: one process per tier / per common scope.** No model change,
works today, and duplicates shared steps across processes — the classic
routing-maintenance trap. Fine as a deliberate stopgap, dangerous as an accident, so it
is named here as the former.

### 5.1 The operation subset, against the flow system we have

With §4.1 decided, the shape is specific. **The rebuild process is authored as the
SUPERSET route** — every operation the shop can perform on that core type, as one
ordinary `Processes` graph. A resolved scope then selects the operations this unit
actually performs.

**The engine already routes per unit.** The first draft of this section did not check,
and the next one asserted the opposite. `Parts.get_next_step` resolves the next step for
*that part*: a `QA_RESULT` decision reads that part's latest `QualityReports.status`; a
`MEASUREMENT` decision compares that part's own reading against the edge's
`condition_value`; `MANUAL` takes an explicit resolution; `AGGREGATE` reads the gate
firing. `try_advance_lot` then cascades **each distinct next step**, with the comment
saying why in as many words — "advanced parts may have routed to DIFFERENT next steps (a
decision step branches per part)". Divergent routing within one work order is not a gap
to build. It ships, and it is driven by exactly the measurement data §3.3 describes.

That leaves two candidate implementations of a composed scope, not one:

**(a) Bypass edges.** Each repair code becomes a decision point with its operation on
`DEFAULT` and a skip on `ALTERNATE`. Zero new routing machinery — it is the existing DAG
used as authored. Costs: the graph grows a decision node per code, the traveler and the
board get noisy, and every code's decision needs a resolution source at runtime rather
than being settled once up front.

**(b) A per-unit included-step set.** Scope resolved once after grading and recorded on
the unit; advancement walks to the next *included* step and marks the passed-over ones
`SKIPPED`. Cleaner at a dozen codes, and it keeps the authored graph readable. Costs:
new state, and advancement has to consult it.

(a) is the right stopgap and (b) the right destination, which happens to match the build
order already: (a) needs nothing beyond authoring, so it can carry steps 2–7 while real
cores establish how many codes there actually are. Neither needs `split_from_lot` —
worth saying because that flag is for a part taking a DETOUR (quarantine, rework, scrap)
and carries genealogy meaning. A planned scope difference is the nominal route for that
unit, not a detour, and overloading the flag would corrupt a quality record.

Either way the rest holds:

- **`StepEdge` needs no new semantics for the grade itself.** Scope is resolved from
  findings before the rebuild work exists; no edge is asked to compare a categorical
  grade.
- **`resolve_route`'s DEFAULT-only walk stays correct** for scheduling, since the route
  is settled before the WO.
- **`ProcessStep` already shares Steps across processes and versions**, so codes
  reference steps rather than duplicating them — the trap the stopgap above walks into.
- **`BOMLine.consumed_at_step`** already yields the kit for a step set (§6).
- **`StepExecution.status` already has `SKIPPED`**, so under (b) an excluded step lands
  truthfully rather than vanishing — which matters when the record has to prove what a
  customer's unit did and did not receive.

**What is genuinely new**, now that findings (§3.3) and per-unit routing are struck off:
the code table itself — code → operations, and the mapping from
`(MeasurementDefinition, out of spec)` / `(component type, grade)` to codes — plus the
named entry-scope presets of §3.3, plus (for (b)) the included-step set and a
scope-aware advancement walk.

### 5.2 Work-order grain: one per core, or not

An earlier revision of this section asserted that rebuild work orders must be one per
core, because cohort advancement assumes parts at a `(WorkOrder, Step)` share a route.
**That was wrong, and it was wrong because it reasoned from the model docstrings instead
of the advancement code.** `try_advance_lot` handles the cohort *and* split parts, and
routes each advanced part to its own next step; divergence inside one WO is a supported
case with a comment explaining it.

So the grain is a real choice rather than a forced one:

- **One WO per core** is what a SAP refurbishment order and an aviation shop visit are,
  and it makes serial continuity under `REPAIR_RETURN` trivial at the WO grain. It costs
  many more work orders on the planner's board.
- **A batched rebuild WO** is viable on the engine as it stands, with units diverging by
  scope the way they already diverge at a decision point.

Defer it. It does not gate steps 2–6, the engine supports both, and the answer will be
obvious once a shop has run cores through and knows whether rebuild batches usefully
share anything.

## 6. Kit resolution

A new service — `services/reman/rebuild.py` — resolving, for a core whose grading is
complete:

1. **Scope** — the entry scope plus the codes the findings raised (§3.3, §4.1).
2. **Route** for that scope, via the existing `resolve_route`.
3. **BOM lines on that route** — `BOMLine.consumed_at_step` already ties a line to the
   step that consumes it, so "the kit for this scope" is a query that exists today and
   nothing currently asks.
4. **Sourcing** — for each line, which of the permitted sources can actually cover it
   (§6.1), and what is short.

Step 3 fixes something already broken: `reports/adapters/pick_list.py` explodes the
**whole released BOM** regardless of route. On any branched process that over-picks —
every branch's parts on every job. Route-aware kit resolution is needed for reman and is
a correctness fix for the general case.

The service returns data and writes nothing, so the same resolver can answer "what would
this core need?" for a core not yet torn down (§8).

### 6.1 A component has a provenance, and the line has a policy

The earlier draft of this section assumed one alternative to buying: a component
harvested from *this* core. That is one source of three, and the three are not
interchangeable to a customer or an auditor:

| source | where it lives today | notes |
|---|---|---|
| **New purchased** | `MaterialLot(material=…)` or `MaterialLot(material_type=<PartTypes>)` | the ordinary BUY line |
| **Used purchased** | the same — `MaterialLot` already carries `supplier`, `supplier_lot_number`, `erp_po_number`, `certificate_of_conformance` | bought from a core specialist who does the teardowns; aviation regulates this as USM (Used Serviceable Material) and it is a real commercial channel in diesel and hydraulics too |
| **Recovered in-house** | `Parts`, created by `accept_component_to_inventory`, back-linked via `HarvestedComponent.component_part` | from *this* core, or from the pool |

All three already have homes in the schema. What is missing is that the BOM line says
only `allow_harvested` — one boolean spanning "used purchased" and "recovered in-house"
and saying nothing about *whose* core the recovered one came from.

That distinction is not bookkeeping. Under `REPAIR_RETURN` a customer may accept a
component recovered from their own unit and refuse one a third party pulled out of
somebody else's engine, and there is no way to express the difference today. So the line
carries a **permitted source set** rather than a boolean, and the resolver picks among
the permitted sources by availability, recording which it used.

`AssemblyUsage` is where the answer lands: it already models
(assembly, component, bom_line, installed_at, installed_by, step) — the as-built record
of which component instance went into which unit. Once a unit ships that row is the only
place "where did this part come from" can be answered. Nothing creates one today (§6.3).

### 6.2 What this makes SIMPLER

Provenance looks like more machinery and is mostly less, because it turns four
reman-specific special cases into one general mechanism:

- **The `is_reman` carve-out disappears.** `consume_for_step` branches on
  `work_order.cores.exists()` and then `continue`s past any `allow_harvested` line —
  and `services/scheduling/data.py` duplicates the same branch for the material gate. If
  a line declares its permitted sources, there is nothing reman-specific left: an
  ordinary job is a job whose lines permit only new-purchased. **Two carve-outs and a
  duplicated `is_reman` detection delete.**
- **`Core.allows_pooled_harvest` stops being a rule and becomes a default.** Today it is
  a bespoke property that a kit resolver would have to remember to consult. Under source
  policy it is one entry in the permitted set — "recovered in-house, any core" — so the
  general mechanism enforces it and the property survives only as the thing that seeds
  the default.
- **The reservation rule collapses into the same filter.** `Parts.reserved_for_core` +
  `assert_work_order_allowed` is a negative rule bolted on the side: it forbids a wrong
  use. As a source filter it is positive and needs no separate enforcement — a reserved
  part is simply a candidate whose provenance is "recovered from core X", admissible
  only on a line that permits that. Same behaviour, one place.
- **`fulfilment_mode` stops branching the code.** Repair-and-return and exchange differ
  in which sources are permitted, not in what the resolver does. The mode picks a default
  policy; it does not fork the kit path.

Net: one selection step over a candidate list, instead of a BUY branch, a MAKE branch, a
reman skip, a reservation prohibition and a pooling property.

What it costs: an authoring surface wider than a checkbox. Mitigated by defaulting the
policy per part type (and seeding it from `fulfilment_mode`), so an engineer sets it only
where it differs — and by keeping `allow_harvested` as the migration source for the
default set.

### 6.3 Two prerequisites, both small and both blocking

Neither source path works end-to-end today:

- **Accepted components are invisible as supply.** `accept_component_to_inventory`
  creates the `Parts` row with `part_status=PENDING`, while `_available_supply`
  (`bom_explosion.py`) counts only `IN_STOCK`. So the exchange model's premise — teardown
  feeds stock, rebuild consumes it — does not connect at either end. Whether acceptance
  should land in `IN_STOCK` directly or pass an inspection state first is a real
  question; that it currently lands somewhere nothing counts is not.
- **Nothing creates an `AssemblyUsage`.** `services/mes/assembly_usage.py` contains
  `remove_assembly_usage` and nothing else; the only way a row exists is a raw REST POST.
  The install half was never written, so there is no as-built record to put provenance in.

## 7. UI changes

### 7.1 Reman-local

| # | Surface | Change |
|---|---------|--------|
| 1 | `CoreDisassemblyPage` | **Proposed-scope panel.** Today: a list of graded components and a Complete-disassembly button. Needed: the derived scope — tier, or generated repair codes — **with include/exclude and manual additions** (§3.1). The industry does this curation at the line level, and a person is the authority (§9). |
| 2 | `CoreDisassemblyPage` | **Kit preview before committing.** Row per component: grade · reuse-or-replace · source (harvested part / stock / short). A shortage surfacing here rather than at the bench is most of the value of the feature. |
| 3 | `CoreDisassemblyPage` | **"Create rebuild work order"** as the terminal action. Creates the WO on the resolved scope, pegged to the core, with reusable harvested `Parts` allocated. |
| 4 | `CoreDetailPage` | **Return link** — "rebuilt as WO-1234" with status. The core's story currently ends at *disassembled*; core ↔ WO must be navigable both ways, because that round trip is the traceability claim an audit actually tests. |
| 5 | `RemanDashboardPage` | **"Ready to rebuild" queue** — cores graded with no rebuild WO. Without it a graded core is invisible until someone remembers it. |

Explicitly **not** a change to `/production/dispositions` (§2).

### 7.2 Reaching outside reman

| # | Surface | Change |
|---|---------|--------|
| 6 | Process / step editor, **or** WO creation | Depends on §4. Tier-branch → **categorical `StepEdge` conditions** + authoring UI. Repair codes → a **code table** (operations + materials per code) and finding→code mapping, plus per-WO route assembly. Deferrable either way via the §5 stopgap. |
| 7 | Staging / Material Requisition | **Reuse vs. new as distinct row types.** A harvested component is a `Parts` record, not a `Material`, and `MaterialStagingLine.material` is a hard `Material` FK. Same root cause as the "bought parts can't be staged" backlog item — fixing it once covers both. |
| 8 | Quoting / order surface | **`REPAIR_RETURN` only** (§4.2). Pricing the proposed scope and routing it for customer approval before work proceeds, plus the decline path (§10.6). Overlaps the parked `OrderLine` work. Under `EXCHANGE` this surface is skipped entirely. |

## 8. Planning hook (already half-built)

`DisassemblyBOMLine` is a **reverse BOM**: per core type, the component types expected
out of a teardown, with `expected_qty` and `expected_fallout_rate`.

That is a demand forecast nobody is reading. Expected fallout × planned core intake gives
**predicted replacement-part demand** before a single core is torn down, which is exactly
the shape the RCCP material lane already consumes
(`services/planning/material_load.py`, `build_capacity_load`). Per-core grading then trues
the forecast up to actuals.

This is the reason §6 is specified as a resolver returning data rather than a WO writer.

## 9. Authority

Researched 2026-09-09.

- **Conventional ERP/MES practice** puts work-order creation with the planner and
  execution with the operator. `STAFF_OPERATIONAL_WRITE` currently grants `add_workorder`
  to everyone with operational write, which is looser than that norm. IFS and SAP both
  put refurbishment/MRO order creation with a planner.
- **It is not a named segregation-of-duties violation.** Canonical toxic combinations are
  financial (vendor master + payment, PO creation + goods receipt). "Create WO + execute
  WO" is not on those lists, and the completing half is separately gated here anyway:
  release is `MANUAL` and only released work reaches the schedule.
- **What AS9100 / AS9110 actually require** is a control process with *defined
  responsibilities and authorities for reviewing and assigning dispositions*. The
  authority that must be controlled is the **disposition decision**, not the clerical act
  of creating a WO afterwards. IFS agrees structurally: the gate is an *approved
  disposition line*, and the shop order follows from it.

**Therefore:** the rebuild WO can be created by whoever completes and approves the
scope. The control that is currently missing is that `grade_component` /
`accept_component` / `reject_component` sit in the same general grant as
`add_stepexecution` and `add_timeentry`. Those codenames already exist as distinct
grants; splitting them into a QA-held bundle is a presets change with no schema impact,
and it is the thing an auditor would ask about. Tracked separately — **not a blocker**
for this loop.

## 10. Open questions

1. ~~**How is `fulfilment_mode` set?**~~ **Answered, and shipped.** Chosen at receipt,
   defaulting from `Companies.default_core_fulfilment_mode` — the standing arrangement —
   with an explicit override for the exception case. `resolve_fulfilment_mode` returns
   the provenance of its answer alongside it, so the screen can distinguish the
   customer's recorded arrangement from a fallback.
2. ~~**The rollup rule**~~ **Moot.** It existed only under tier-branch, which §4.1 no
   longer selects: findings map to codes directly and no rollup is needed. The principle
   behind it stands and applies to the code proposal instead — the system suggests, the
   grader decides (§9), rather than a threshold we invented before seeing grading data.
3. ~~**How many distinct rebuild scopes does Ambac actually have?**~~ **Withdrawn.** It
   was the wrong question: this is a product other shops deploy, so no single tenant's
   count can decide the model. §4.1 now resolves to repair codes on the grounds that
   tiers are a special case of them, and a per-tenant preset covers the small shop.
4. ~~**Tier vocabulary.**~~ **Moot.** Tiers are no longer a modelled kind (§4.1) — they
   are entry-scope presets a tenant names itself, so the naming is theirs and cannot
   collide with the A/B/C condition grades unless they choose it.
5. **What exactly is "the same unit"** under `REPAIR_RETURN`? Still a
   customer-commitment question with real cost at the bench — but §6.1 makes it
   *expressible* rather than binary. The answer is now a permitted source set: the
   customer's own recovered components always; new purchased presumably; used purchased
   from a core specialist, and in-house recovered from OTHER cores, are the two a
   customer may well refuse in their own unit. What was one unanswerable question is now
   two checkboxes on a policy, and the commitment can differ per customer or per line.

   Its hard half remains: **`Parts` carry no serial number.** Identity is `ERP_id`,
   machine-generated as `{WO}-{prefix}{seq}`. `Core.serial_number` exists and there is no
   mechanism to carry it onto anything rebuilt, so serial continuity under
   `REPAIR_RETURN` currently has nothing to ride on.
6. **Does a rejected quote have a path back?** Under `REPAIR_RETURN`, if the customer
   declines the over-and-above work, the unit has to go somewhere: returned unrepaired,
   repaired to a reduced scope, or scrapped with consent. That is a terminal state the
   core lifecycle (`RECEIVED` / `IN_DISASSEMBLY` / `DISASSEMBLED` / `SCRAPPED`) has no
   room for today.

## 11. Build order

1. **`Core.fulfilment_mode`** (§4.2) — field, migration, set at receipt, shown on the
   core. Small, and first because nearly everything downstream branches on it.
2. **Scope resolution + curation UI** on the core — entry-scope preset applied (§3.3),
   proposal generated from findings, human include/exclude. Still no routing change: the
   resolved scope is recorded and read by step 3, not yet enforced during execution.
3. **Kit resolution service** — scope → route → BOM lines → netted against harvest,
   with cross-core reuse gated by mode. Returns data; writes nothing.
4. **UI 1–3** on the teardown surface, on the §5 one-process-per-scope stopgap. (The
   design named `CoreDisassemblyPage`; teardown is to become a DWI surface rather than a
   page of its own, so this lands wherever that work puts it.)
5. **UI 4–5** — core return link, ready-to-rebuild queue.
6. **`EXCHANGE` path closes here.** Everything above is a complete loop for stock
   rebuilds, and it is worth shipping and using before starting §7.
7. **`REPAIR_RETURN` gate** — quote from the proposed scope, customer approval before
   work, decline path (§10.6), serial continuity through the rebuild.
8. **Routing support for composed scope** (§5.1) — superset process, repair-code table,
   and the move from bypass edges (a) to a per-unit included-step set (b) with a
   scope-aware advancement walk. WO grain (§5.2) is a deferred choice, not a
   prerequisite. No longer gated on resolving §4.1; that is decided.
9. **Staging reuse-vs-new** (shared with the bought-parts-staging item).
10. **Fallout forecast** into the RCCP material lane.

The split at step 6 is the useful shape: `EXCHANGE` needs no quoting, no customer
approval and no serial continuity, so it closes the loop with strictly less machinery.
Ship it, run cores through it, and both §10.3 (how many distinct scopes there really
are) and the §7 quoting requirements will be answerable from evidence rather than
guessed at up front.
