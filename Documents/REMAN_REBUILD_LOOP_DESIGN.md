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

**Recommendation: repair codes, but only if the shop really does have more than a
handful of distinct scopes.** That is a question about Ambac's actual rebuild practice
(§10.3), not about the software. Either way, §3.1's *human curation* step is worth
adopting immediately — auto-generate the proposal, let a person include/exclude it.

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

## 6. Kit resolution

A new service — `services/reman/rebuild.py` — resolving, for a core whose grading is
complete:

1. **Scope** — tier, or set of repair codes (§4).
2. **Route** for that scope, via the existing `resolve_route`.
3. **BOM lines on that route** — `BOMLine.consumed_at_step` already ties a line to the
   step that consumes it, so "the kit for this scope" is a query that exists today and
   nothing currently asks.
4. **Netting** — for each line, is there a reusable `HarvestedComponent` of that
   `component_type` from *this* core? If yes, peg its `component_part`; if no, the line
   becomes ordinary demand against stock.

Step 3 fixes something already broken: `reports/adapters/pick_list.py` explodes the
**whole released BOM** regardless of route. On any branched process that over-picks —
every branch's parts on every job. Route-aware kit resolution is needed for reman and is
a correctness fix for the general case.

The service returns data and writes nothing, so the same resolver can answer "what would
this core need?" for a core not yet torn down (§8).

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

1. **How is `fulfilment_mode` set?** (§4.2) Chosen at core receipt, defaulted per
   customer, or implied by the order it arrived against? Defaulting per customer is
   likely right — an exchange programme is usually a commercial arrangement, not a
   per-unit decision — but that means the default lives on the customer/company record
   and needs an override at receipt for the exception case.
2. **The rollup rule** (only if §4 lands on tier-branch). How component grades produce a
   tier. Proposal: the grader **chooses**, with a computed suggestion shown alongside;
   promote to configuration once real grading data shows what the rule is. Avoids
   inventing an unvalidated threshold, and matches §9.
3. **How many distinct rebuild scopes does Ambac actually have?** The §4.1 decision turns
   on this. A handful → tiers. Many, varying by which components failed → repair codes.
4. **Tier vocabulary.** A/B/C are *component condition* grades. Reusing those letters for
   a core-level tier will be confusing at the bench; tiers want their own names.
5. **What exactly is "the same unit"** under `REPAIR_RETURN`? Cross-core reuse is barred
   (§4.2), but that bar is really about the *serial-bearing* part — the housing or body
   the customer's identity attaches to. Whether every internal component must also be
   the original, where serviceable, is a customer-commitment question rather than a
   technical one, and it has real cost consequences at the bench.
6. **Does a rejected quote have a path back?** Under `REPAIR_RETURN`, if the customer
   declines the over-and-above work, the unit has to go somewhere: returned unrepaired,
   repaired to a reduced scope, or scrapped with consent. That is a terminal state the
   core lifecycle (`RECEIVED` / `IN_DISASSEMBLY` / `DISASSEMBLED` / `SCRAPPED`) has no
   room for today.

## 11. Build order

1. **`Core.fulfilment_mode`** (§4.2) — field, migration, set at receipt, shown on the
   core. Small, and first because nearly everything downstream branches on it.
2. **Scope resolution + curation UI** on the core — proposal generated, human
   include/exclude, no routing change (works under either §4 model).
3. **Kit resolution service** — scope → route → BOM lines → netted against harvest,
   with cross-core reuse gated by mode. Returns data; writes nothing.
4. **UI 1–3** on `CoreDisassemblyPage`, on the §5 one-process-per-scope stopgap.
5. **UI 4–5** — core return link, ready-to-rebuild queue.
6. **`EXCHANGE` path closes here.** Everything above is a complete loop for stock
   rebuilds, and it is worth shipping and using before starting §7.
7. **`REPAIR_RETURN` gate** — quote from the proposed scope, customer approval before
   work, decline path (§10.6), serial continuity through the rebuild.
8. **Resolve §4.1**, then build the corresponding routing support (categorical edges, or
   the repair-code table + per-WO route assembly) and migrate off the stopgap.
9. **Staging reuse-vs-new** (shared with the bought-parts-staging item).
10. **Fallout forecast** into the RCCP material lane.

The split at step 6 is the useful shape: `EXCHANGE` needs no quoting, no customer
approval and no serial continuity, so it closes the loop with strictly less machinery.
Ship it, run cores through it, and both §10.3 (how many distinct scopes there really
are) and the §7 quoting requirements will be answerable from evidence rather than
guessed at up front.
