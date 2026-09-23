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

**UQMES authorises SCOPE, not money — and the commercial conversation is out of
bounds entirely.** This system is not an ERP and does not hold or carry financial
decisions. Specifically out of scope, and not to be built here:

- **quotes** as commercial documents,
- **quote approval** workflow,
- **purchase orders.**

`Orders` in this system is DEMAND, not accounting. The only financial touchpoints are
`Core`'s credit fields — information that may *inform* a real accounting system without
being one — and the APS, which needs enough cost sense to weigh a constraint.

So what this loop produces is the **scope**: these operations, these parts, on this
unit, with the finding behind each. Turning that into a price, a quote and an approval
is the ERP's job; UQMES exports the scope and records the answer that comes back.

That is why this document says "scope authorisation" where the industry says "quote".
The word matters: calling it a quote invites someone to add a price field, then a rate
table, then an approval workflow — and UQMES is quietly a costing system with none of
the controls one needs.

**What remains in bounds is the production gate**: a unit must not have out-of-scope
work done to it until someone says go. That is shop-floor control, not commerce. The
authorisation ARRIVES from outside; the hold that waits for it belongs here.

### 3.3 The two layers, and which one our process flow already is

The pattern above is not one representation but **two, at different layers**, and every
mature MRO system keeps both:

| | **Entry scope** (commercial) | **Accumulated scope** (execution) |
|---|---|---|
| Answers | what was sold | what was actually done to this unit |
| Shape | a named level | a union of codes |
| Examples | engine shop visit sold as minimum-touch / performance-restoration / full overhaul; LORA repair levels; graded automotive rebuild levels | IFS repair codes; SAP PM catalog codes on a refurbishment notification; aviation non-routine cards raised against a task-card workscope |
| Set by | the order, or the customer's programme | inspection findings, as they are discovered |
| Changes | when the job is sold | during the job — which is precisely §3.2 |

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
out of tolerance — which is exactly what an over-and-above authorisation has to show a
customer
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

**§6.4 later sharpens what a code IS**: a repair code is a slot resolution that emits
operations rather than demand. The code table and the kit are one model, so read this
section's decision as settling the *scope vocabulary*, and §6 as settling the thing that
produces it.

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
| Scope approval | scope authorisation → **customer** decision before work | internal planning only |
| Over-and-above (§3.2) | applies | does not apply |
| Cross-core reuse (§10.4) | **no** — the unit keeps its own parts | yes — harvest pools freely |
| Loop terminates at | an approved scope, then the rebuild | a WO |

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
order already — and §6.4 says where (b)'s included-step set comes from: it is the union of
the operations the unit's slot resolutions emitted, not a separately-authored list.

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

## 6. Slot resolution — the kit and the scope are one decision

A new service — `services/reman/rebuild.py` — resolving, for a core whose grading is
complete, what goes into it and what has to be done to it. It returns data and writes
nothing, so the same resolver answers "what would this core need?" for a core not yet
torn down (§8).

### 6.1 The shape: assignment, not netting

Classical kitting nets quantities against requirements because raw material is fungible —
3 kg of aluminium is 3 kg of aluminium. Reman is not that. A harvested nozzle carries its
own grade, its own accumulated life, its own provenance and possibly its own owner. Two
nozzles of the same part number are not interchangeable to the customer, to quality, or
to cost.

So the operation is **assignment of identified individuals to identified slots**, and
every shape decision below follows from that one.

### 6.2 Slots, not quantities

A BOM line "4 × nozzle" on a four-cylinder unit is not one requirement of quantity four.
It is **four slots** — Cyl 1, 2, 3, 4 — because position carries real information here:
whether the original goes back where it came from, positional wear patterns, and
yield-by-position, which is a question MRO shops actually ask.

`BOMLine` already carries the vocabulary: `reference_designator` is the position name and
`find_number` the drawing balloon. `DisassemblyBOMLine.positions` is the teardown twin,
already shipped. What is new is exploding a line into per-unit slots.

**Position must be optional from the start.** High-volume exchange does not care which of
four identical nozzles goes in which bore; an unpositioned line is the same structure with
N anonymous slots. Retrofitting optionality later is the expensive direction.

### 6.3 A slot states criteria; a candidate carries attributes

| slot declares | candidate carries |
|---|---|
| part type | identity |
| permitted provenance set | provenance |
| minimum condition grade | condition grade |
| "must be the original from this unit" | life remaining |
| | cost, availability, claim status |

Permitted sources and minimum grade are the same kind of thing — **acceptance criteria on
a slot** — which is why they are one feature and not two. The three provenances are: new
purchased; used purchased (bought from a core specialist who does the teardowns — aviation
regulates this as USM, and diesel and hydraulics buy it routinely); and recovered
in-house, from this core or from the pool.

All three already have somewhere to live. `MaterialLot` carries `material_type`,
`supplier`, `supplier_lot_number`, `erp_po_number` and `certificate_of_conformance`, so a
purchased recovered component is an ordinary BUY line with the existing
supplier-qualification and part-approval gates on it. In-house recovery lands in `Parts`
via `accept_component_to_inventory`.

The candidate list is a **read-model**, not a table: a union over `MaterialLot`, `Parts`
and `HarvestedComponent` projected into a common shape. It needs no schema.

### 6.4 A resolution can emit operations — which collapses §4 and §5.1 into this

The options for any slot are:

- **reuse as-is** — this instance is serviceable
- **reuse after repair** — emits operations, maybe consumables
- **replace from recovered stock**
- **replace new**

In MRO the second is the normal case: you do not replace the housing, you machine it.
"Recondition the nozzle" and "replace the nozzle" are two resolutions of the *same slot* —
one emits operations, the other emits demand.

**So scope and kit are not sequential steps. They are one decision per slot with two
outputs.** A repair code (§4.1) *is* a slot resolution that emits operations; the per-unit
included-step set (§5.1(b)) is the union of the operations its slot resolutions emitted.
Three parts of this document — the code table, the included-step set, and the kit — are
one model. Treating them as three is what made the kit look like a query in earlier
revisions of this section.

### 6.5 The binding has a lifecycle, and it is one row

Between "the resolver proposes nozzle X" and "the operator installed nozzle X" there is
authorisation, customer approval, picking and the bench. Nothing else may take nozzle X
in that
window. So a binding is a claim with states:

**proposed → reserved → issued → installed**, with **released** and **removed** as the
reverses — a component installed and then found bad returns its slot to unresolved.

Four things otherwise built separately become the same row at different times:

| question | when | state |
|---|---|---|
| what would this cost? | before teardown | proposed |
| what does this need? | after grading | reserved |
| what do I install where? | at the bench | issued |
| what went in, and from where? | after | installed |

The as-built record is not a separate artifact — it is the final state of the slot table,
and it is the only place "where did this component come from" can be answered once the
unit has shipped.

Two consequences worth stating: **the over-and-above authorisation is a projection of unresolved
slots** (§3.2), so it needs no separate model; and **curation is per-slot override with a
reason** (§3.1), which is what makes the proposal reviewable rather than a wall of
defaults.

### 6.6 Translating onto what exists

**Already fits.** `BOMLine.reference_designator` / `find_number` (slot vocabulary);
`DisassemblyBOMLine.positions` (teardown twin); per-unit rows as house style (DWI decision
R1). Most of all, **`MaterialUsage` is nearly the binding row already** — it points at
`lot`, `harvested_component` *and* `part`, plus `work_order`, `step`, `qty_consumed`,
`is_substitute` and `substitution_reason`. The override-with-a-reason field exists.

**One thing wearing two names.** `MaterialUsage` and `AssemblyUsage` are the *issued* and
*installed* states of the same claim — both say "this identified thing went into that
unit", one as a draw and one as an install. `AssemblyUsage` adds `bom_line`, the parent
link and removal tracking; `MaterialUsage` adds the candidate FKs and the reason. A later
increment decides whether one grows into the binding row and the other becomes a
projection, or a new table takes over and both become projections.

**Genuinely new:** the slot rows, the acceptance-criteria columns, the binding state. That
is all.

**Conflicts, and they are the real work:**

- **The pick layer is quantity-shaped end to end.** `staging_list`, `consolidated_pick`
  and `record_pick` deal in `material` / `material_type` + qty + `picked_lots` JSON.
  `MaterialStagingLine` cannot name a specific instance, so a reman kit is inexpressible —
  and nothing reserves a `Parts` or `HarvestedComponent` for a job at all, so two rebuilds
  resolving at the same moment both see the same nozzle as free. Either that layer grows
  instance-awareness or reman forks a parallel pick path, which is how a shop ends up with
  two kitting systems.
- **Grade is lost on accept.** `Parts` has no grade or condition field. It is recoverable
  via `part.harvested_from.condition_grade` — a join, not an attribute, and only for that
  provenance.
- **`MaterialLot` has no grade at all**, so a used component bought from a core specialist
  cannot be graded on receipt. Purchased-used is currently a second-class source that
  cannot be compared against harvested stock. See §10.7.
- **Accepted components sit in `PENDING`** where `_available_supply` counts only
  `IN_STOCK` (§6.7).

Slot-aware explosion also fixes something already broken:
`reports/adapters/pick_list.py` explodes the **whole released BOM** regardless of route,
so on any branched process it over-picks every branch's parts on every job. Route- and
slot-aware resolution is needed for reman and is a correctness fix for the general case.

### 6.7 Two prerequisites, both small and both blocking

- **Accepted components are invisible as supply.** `accept_component_to_inventory` creates
  the `Parts` row with `part_status=PENDING`, while `_available_supply` counts only
  `IN_STOCK`. The exchange premise — teardown feeds stock, rebuild consumes it — connects
  at neither end. Whether acceptance should land in `IN_STOCK` directly or pass an
  inspection state first is a real question; that it currently lands where nothing counts
  it is not.
- **Nothing creates an `AssemblyUsage`.** `services/mes/assembly_usage.py` holds
  `remove_assembly_usage` and nothing else; the only way a row exists is a raw REST POST.
  The install half was never written.

### 6.8 The first increment

**Slots and resolutions, read-only.** Explode the route's BOM lines into positioned slots,
build the candidate read-model, propose a resolution per slot with its reason, return it.
It writes nothing, so it cannot break consumption or scheduling, and it is what every
later piece reads: the authorisation, the kit list, the pick, the as-built.

Curation comes second, and it needs **overrides, not persisted slots**: a row per
DEVIATION from the computed proposal, not a row per slot. Thirty rows a unit that
mostly agree with the computation would be persisting a guess, and the proposal is
cheap to recompute.

Binding states come third, with the as-built record, and that is where the
`MaterialUsage` / `AssemblyUsage` question gets decided — by which point there is a
real issued component to attach it to rather than a proposal.

### 6.9 What I expect to be wrong

- **Row volume.** A slot row per component per unit is 30 × 100/day for a busy exchange
  shop. Consistent with the per-unit-rows philosophy and almost certainly fine, but it is
  the assumption that is expensive to reverse, so it deserves a sanity check before
  committing.
- **Slot identity across a BOM revision.** Slots are per-unit and `BOM` is versioned. If
  the BOM revises mid-rebuild, does the unit keep the slot set it started with, or
  re-explode? Same class of question as a process change mid-Op, and it should get the
  same answer for the same reasons.

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

   ~~Its hard half — `Parts` carry no serial number.~~ **Withdrawn; the question does
   not arise.** Under `REPAIR_RETURN` the core never becomes a `Parts` row: it stays the
   routing subject through the rebuild, because `StepExecution.core`, `Core.step` and
   `advance_core_step` already let a core walk any process (§5.1). `Core.serial_number`
   is never lost because nothing ever hands off. Under `EXCHANGE` the rebuilt unit is a
   new `Parts` row with its own `ERP_id` and the core's serial is irrelevant by
   definition — the customer is not getting their unit back. Serial continuity needs no
   new field and no carry mechanism; it falls out of the §5.2 split.

   (For the record, `Parts` are individually identified — `create_parts_batch` mints
   `{WO}-{prefix}{seq:04d}` per unit. Worth knowing before leaning on it: `ERP_id` has no
   unique constraint at the database level, so it is unique by generation discipline.)
6. **Does a declined scope have a path back?** Under `REPAIR_RETURN`, if the customer
   declines the over-and-above work, the unit has to go somewhere: returned unrepaired,
   repaired to a reduced scope, or scrapped with consent. That is a terminal state the
   core lifecycle (`RECEIVED` / `IN_DISASSEMBLY` / `DISASSEMBLED` / `SCRAPPED`) has no
   room for today.

7. ~~**Does the authorisation carry a price?**~~ **Answered: no.** UQMES is not an ERP
   and does not hold or carry financial decisions (§3.2). The artifact is a scope
   authorisation — these operations, these parts, approve or decline — and pricing is the
   ERP's, reached through `integrations/`. This is the answer that sizes step 6: without
   it the gate would have needed a costing model (rates, material cost, margin) larger
   than the entire rebuild loop has been.

   What remains under it is smaller and still open: **how the customer's decision gets
   back.** `Order.customer` is a User FK and `for_user` already scopes by
   `Order.customer` / `Order.viewers`, so a portal answer is possible; the existing
   `ApprovalRequest` machinery is another; and out-of-band — a planner records what the
   customer said — is the common reality and the cheapest. Pick one before building the
   surface, not during.

8. **Can a purchased used component be graded?** `MaterialLot` has no condition or
   grade field, so a component bought from a core specialist arrives ungraded while an
   in-house harvested one carries A/B/C. Until that is settled, purchased-used is a
   second-class source the resolver cannot rank against harvested stock (§6.6). The
   options are a grade on the lot, a grade on the receiving-inspection record, or a
   decision that used-purchased is always treated as one nominal grade. This blocks the
   candidate read-model, not the slot model.

9. **Slot identity across a BOM revision.** Slots are per-unit, `BOM` is versioned. Does
   an in-flight unit keep the slot set it was exploded with, or re-explode on revision?
   Same class as a process change mid-Op, and it should get the same answer.

## 11. Build order

Each step is a deliverable, not a layer: the UI a step needs is part of that step
rather than a row of its own. An earlier revision numbered the five §7.1 surfaces
separately from the services behind them, which made one feature read as three
items and the whole loop look bigger than it is.

1. **`Core.fulfilment_mode`** (§4.2) — **shipped.** Field, migration, set at receipt
   from the customer's standing arrangement, shown on the core, list and receipt
   surfaces.

2. **The proposal: slot + scope resolution, read-only** (§6.8) — **shipped.** Route →
   BOM lines → positioned slots → candidate read-model → a resolution per slot with
   its reason, and the operations those resolutions raise (§6.4). Writes nothing, so
   it cannot disturb consumption or scheduling. Carries UI 2 (kit preview, on
   `/reman/cores/$id/rebuild`) and UI 5 (ready-to-rebuild queue), plus the authoring
   surfaces for repair codes and rebuild levels.

3. **Curation** (§3.1, UI 1) — the proposal becomes overridable. Store **overrides,
   not slots**: a small table saying *for this core, this slot, the resolution is X
   because Y*. The proposal stays computed and the deltas are what persist — storing
   thirty rows a unit that mostly agree with the computation would be persisting a
   guess. The as-built record is a different thing and arrives at step 4, when there
   is something real to record.

4. **Commit: create the rebuild work order** (UI 3, UI 4) — `plan_work_order` already
   does the work; point it at the rebuild process, peg the core, allocate the
   reusable harvested `Parts`. Needs two rebuild states on `Core` (it stops at
   `DISASSEMBLED`) and the return link on `CoreDetailPage` — "rebuilt as WO-1234" —
   because the core's story currently ends at disassembled and that round trip is the
   traceability claim an audit actually tests.

   Two prerequisites underneath it, both one-liners (§6.7): accepted components land
   in `PENDING` where `_available_supply` counts only `IN_STOCK`, and nothing writes
   an `AssemblyUsage`.

5. **`EXCHANGE` path closes here.** Steps 1–4 are a complete loop for stock rebuilds.
   Ship it and run cores through it before starting step 6 — both the §7 authorisation
   requirements and how many distinct scopes a shop really has become answerable from
   evidence rather than guessed up front.

6. **Rebuild execution** — **shipped.** The half that actually does the work, and the
   half nobody had named. A core released into rebuild sits at its first in-scope operation and
   then nothing moves it: `advance_core_step` walks DEFAULT edges and knows nothing
   about scope, so it would carry the unit into operations its findings never called
   for. Two ways out, and the first works today:

   - the §5 stopgap — author the route so it matches the scope, one process per
     common scope;
   - scope-aware advancement — the unit walks to the next INCLUDED step and the
     passed-over ones land as `SKIPPED` (§5.1(b)).

   This is also where the **as-built record** belongs: what actually went into the
   unit, slot by slot. `AssemblyUsage` cannot hold it as modelled — both `assembly`
   and `component` are non-null FKs to `Parts`, while a repair-and-return rebuild has
   a Core as parent and `HarvestedComponent`s as children, since those components are
   the customer's property and never become stock. The fix is the nullable-pair +
   CheckConstraint shape already used for `StepExecution.part`/`core`.

7. **`REPAIR_RETURN` gate** (UI 8) — **shipped**, and it was a small step because most of what
   the industry puts here is out of bounds (§3.2). No quote, no approval workflow, no
   purchase order. What is left:

   - the **scope export** — the unresolved slots and the findings behind them, in a
     form something else can price;
   - a **hold** on the unit while the answer is outstanding. `Core` has no state for
     this, and the work order cannot hold because it may carry other cores;
   - **recording the answer**, out of band: a planner enters what the customer said.
     The conversation happens elsewhere; this is the production record of its outcome;
   - the **decline path** — one terminal status. "Reduced scope" is not a terminal
     state but a loop back through curation, and "scrapped with consent" is the
     existing `SCRAPPED` plus a reason. What the remaining harvest does — returned,
     scrapped, or held — needs no decision here: the services already support all
     three, and which one applies is contract, not MES.

   Serial continuity is NOT on this list — the core stays the routing subject through
   the rebuild, so it needs nothing (§10.5).

8. **Return to customer** — **shipped.** The end of every repair-and-return job, and
   it had been missing entirely. A rebuilt unit has nowhere to go: the only shipment model in the
   system is `OutsideProcessShipment`, which is subcontract dispatch, and `Core` has
   no shipped state. Needed: a terminal status and a dispatch record — when it left,
   who released it, and the reference someone else can trace.

   NOT carrier integration, rates or labels (§3.2): UQMES records that the unit left
   and when. Serves the decline path too, since a unit returned unrepaired leaves the
   same way.

   As built, three things landed differently from the plan above. The as-built record
   went into `AssemblyUsage` widened with a nullable parent/child pair plus two
   CheckConstraints, rather than a reman-specific table. `complete_rebuild` does NOT
   assert every slot was filled — the record is what WENT IN, and checking it against
   the proposal would make the proposal authoritative over the bench. And one dispatch
   service serves both endings, with the distinction in the terminal status rather
   than in two code paths.

9. **Routing support for composed scope** (§5.1, UI 6) — superset process, and the
   move from bypass edges (a) to a per-unit included-step set (b) with a scope-aware
   advancement walk. Deferrable while the stopgap in step 6 carries execution, and
   worth doing once a shop has enough codes that authoring a route per scope stops
   scaling. WO grain (§5.2) is a deferred choice, not a prerequisite.

10. **Staging reuse-vs-new** (UI 7) — **partly shipped, and the gap was bigger than
    the FK.** The diagnosis here was that `MaterialStagingLine.material` is a hard
    `Material` FK so a harvested `Parts` cannot be staged. True, but secondary:
    `staging_list` SKIPPED core-subject tasks outright — "cores and unstationed steps
    aren't staged" — so a bench rebuilding a customer's unit got no kit list at all,
    for the one job where getting the kit wrong is least recoverable.

    Shipped: core-subject tasks now produce staging jobs, and a line a rebuild will
    satisfy from its own teardown is FLAGGED rather than listed as a pick. Without
    that the pick list and `consume_for_step` disagreed about the same line — the
    picker pulls a part that is then never issued.

    Also shipped: **recovered stock is visible at all.** `onhand` was built from
    `MaterialLot` alone, but acceptance from teardown mints a `Parts` row — so a shelf
    of recovered nozzles read as ZERO and the sheet called the line short while the
    part sat in the rack. Recovered Parts now count, and are reported SEPARATELY as
    well as merged: which to pull is a shop decision (a customer contract may forbid
    recovered stock in their unit), so the sheet says what is there rather than
    choosing. Anything `reserved_for_core` is excluded — it is on the shelf and it is
    not available.

    Still open, and the original diagnosis: `record_pick` records `picked_lots`, which
    is lot-shaped, so CONFIRMING "I took this specific recovered nozzle" is still
    inexpressible — the sheet can now show recovered stock but the pick cannot name
    the instance. That remains shared with the parked bought-parts-staging item.

11. **RECOVER as a supply lane** — **shipped (reporting half).** The material lane counted
    purchased stock and on-hand, and has no idea teardown is about to PRODUCE the
    component it is calling short — so a planner buys parts the shop was going to
    harvest.

    The industry shape is not a forecast but a plan: teardown is raised like any other
    supply. "We need 50 nozzles in week 6, yield is ~85%, so schedule 59 teardowns in
    week 4." The core bank is the raw material and the constraint;
    `expected_fallout_rate` is the yield. `bom_explosion` already raises child WOs for
    MAKE lines, so raising a teardown WO for a RECOVER requirement is the same
    machinery on the same data.

    **Only exchange cores are available to it.** A repair-and-return core is committed
    to its owner — `allows_pooled_harvest` already says so — so the bank RECOVER draws
    on is the pooled part of it. You cannot tear down a customer's unit for someone
    else's job.

    Two limits worth stating: this is noise below real volume (a 15% fallout rate on
    three cores a week predicts nothing), and **nothing reconciles the authored rate
    against actual yield** even though both numbers are already in the system —
    reconciliation surfaces the drift, it does not silently re-author an engineering
    spec.

    As shipped it REPORTS, it does not net: `recoverable` is its own column beside
    on-hand and incoming, never folded into `short_qty`. Teardown has not happened, so
    it is a forecast sitting beside facts, and netting it would let a planner skip an
    order on stock that does not exist yet.

    The reporting half now reaches BOTH planning surfaces, not just the per-work-order
    one. `sourcing_requirements` — the shop-wide buy list, and the one purchasing
    actually works from — carried no recoverable column at all, so the sheet said "buy
    12 nozzles" with no hint the bank could yield 8. It now carries `recoverable`,
    `recoverable_cores` and `recoverable_sources` on every source row, on screen, in
    the CSV, and in the PDF. Sources are named because a planner who cannot see which
    cores a forecast came from cannot judge whether to trust it, and an untrusted
    number is just noise on the sheet.

    One implementation note worth keeping: `recoverable_supply` now takes an EXPLICIT
    tenant, matching the shop-wide callers, which take a tenant as an argument rather
    than reading the request ContextVar. `.objects` without a context raises
    `TenantContextRequired` rather than returning an empty bank, so this is not
    guarding against a silent wrong answer — it is removing an ambient dependency the
    caller never passed, so a report generated from a task cannot be the thing that
    discovers it.

    **The active half is now shipped, as a PROPOSAL.** A `recover` lane sits between
    Source and Produce — the order the decision is actually made in: the buy list says
    a line is short, the recover lane says how much of it the core bank could cover
    instead. Per component it gives the teardown count by core type (capped at what is
    physically in the bank), how much that covers, how much is still a purchase, and a
    start-by date.

    It proposes; it does not raise the work order. Creating a teardown WO commits
    physical cores out of the bank on the strength of a forecast, and unlike a MAKE
    child WO there is no cheap undo — the unit is in pieces. So a planner accepts a
    line through the normal work-order path. Note which way this cuts: **nothing here
    prevents auto-raising later, whereas auto-raising now would prevent NOT
    auto-raising.** That asymmetry is the whole reason for the choice, not caution.

    Teardown lead time is summed from the disassembly process's authored step
    durations — the same numbers scheduling plans against, so the sheet and the board
    cannot disagree about how long a teardown takes. When a core type has no authored
    duration the start-by date is OMITTED rather than defaulted: a made-up lead time
    reads as authored fact on the sheet and a planner schedules against it. Steps with
    blank durations are an unanswered question, not a zero-day teardown.

    What is still not built is the part that needs volume to mean anything: nothing
    reconciles the authored `expected_fallout_rate` against actual recorded yield, and
    the lane is noise below real throughput. Both were already flagged above and
    neither is a code gap.

**Scope boundary for planning.** UQMES plans from what it can SEE AND CONTROL: cores in
the building, work on the board, yield it recorded itself. It does not predict what has
not arrived. So the core bank is in scope and forecasting core ARRIVALS is not — that
needs sales volume × return rate × lag, and sales volume is not ours. UQMES can supply
the historical return rate as an input to someone else's forecast; it does not own the
forecast. Same test as §3.2: does UQMES own the data?

Steps 10 and 11 reach outside reman and stay separate deliberately: both pay off
across the system rather than only in this loop.

