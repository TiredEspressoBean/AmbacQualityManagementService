# Demo Seed — What the Scripts and the Audit Need

**Status: live requirements list, not design history.** Unlike most of
`Documents/`, this file is meant to be acted on and then updated. Every item below
was measured against the demo tenant on the date given — not inferred from code.

**Why this exists.** The role-workflow audit (`ROLE_WORKFLOW_AUDIT.md`) walks every
role's workflows in the browser. A row that cannot be walked is usually not a
missing feature — it is a **missing subject**: the mechanism is built and tested,
and the demo has nothing to point it at. Those gaps are collected here so the seed
rewrite closes them deliberately instead of one-at-a-time whenever a walk stalls.

**The principle, from the script-first framing:** the training scripts and the audit
rows are the specification. The seed's job is to make every one of them walkable by
a person sitting down cold. A capability with no demo subject is, for a trainee, a
capability that does not exist.

---

## The test to apply

For each item: **can someone follow the script to the end without a developer?**
Not "does the record exist" — the audit kept finding rows where a record existed
and the action it was for still could not be performed.

---

## 1. Six roles have no demo user

**Measured 2026-10-13: 9 users on the demo tenant.**

| Present | Missing |
|---|---|
| Tenant Admin, QA Manager, QA Inspector ×2, Shift Lead, Operator ×2, Production Manager, Document Controller, Customer | **Auditor, Engineering, Planner, Purchasing, Receiving, Shipping** |

(Casey Cross holds QA Inspector + Shift Lead — the composition case, worth keeping.)

**Blocks:** six training tracks, Home launchpad verification per role, and Operator
R3. A trainee for those roles currently has to sign in as Tenant Admin, which
defeats the point of the track — the launchpad, the sidebar and the permission
errors are all different for the real role, and those differences are most of what
the track is teaching.

**Needs:** one user per preset, in that preset's group only, with work actually
assigned to them — an empty Home page teaches nothing.

## 2. No First Piece Inspection can be signed

**Measured 2026-10-13. Both pending FPIs are unsignable, for different reasons:**

| Work order | Designated part | Why it refuses |
|---|---|---|
| `WO-2024-0048-A` | **none** | `"No first piece has reached this step yet - nothing to inspect."` |
| `WO-QA-INSPECT-01` | `INJ-QA-INSPECT-001` | part is QUARANTINED and its measurement is 15.0000, `is_within_spec=False` |

**Blocks:** QA Manager row 4 — the FPI co-sign. This is one of only **two** surfaces
in the product with a real signature pad (the other is the Inbox approval), and it
is an ISO control: a second person attesting that a setup is correct before a run is
released. It has never been demonstrated end to end.

**Needs:** a work order whose FPI has a designated first piece that is **not**
quarantined, with its captures complete and **in spec**. Keep the two blocked ones —
they are good negative exhibits — but add one that succeeds.

**Note:** this gap also masked a UI defect for days. The panel offers *Get QA
sign-off* regardless, and only refuses after collecting a signature and the QA
inspector's password. Being unable to seed a success is how that stayed hidden.

## 3. The export-control denial side cannot fire

**Measured 2026-10-13: 9 of 9 users are `us_person=True`; 1 ITAR-controlled part
type, 0 ITAR-controlled parts.**

**Blocks:** Shipping C1's denial half. `for_export_control()` is verified in
isolation, but nothing in the demo makes it deny anything.

**Needs:** a non-US-person account. **Do not** flip an existing persona — that
silently changes what that user sees everywhere else, including in other scripts.
Add a separate account whose only purpose is to watch the filter fire.

**Also unresolved (rework, not seed):** `can_access_itar_data` falls back to
`getattr(user, 'itar_authorized', False)`, and `itar_authorized` exists **only** in
that `getattr` default — no field, no migration, nothing sets it. A non-US person
holding a TAA or export licence can never be granted access.

## 4. No core is awaiting customer authorisation

**Measured 2026-10-13: 0 cores in `AWAITING_AUTHORISATION`.** Stages present are
DISASSEMBLED, HARVESTED, IN_DISASSEMBLY, IN_REBUILD, SCRAPPED.

**Blocks:** the over-and-above exhibit — the flow where a unit's scope exceeds what
was sold, work stops, and the customer's answer is recorded. This is where the
product boundary is clearest (UQMES produces the **scope**, records the **answer**,
and holds no price), so it is worth showing rather than describing.

**Needs:** one core parked in `AWAITING_AUTHORISATION` with the finding that pushed
it there, so Approved / Declined can both be walked from a standing start.

## 5. The change-control chain is unreachable on fresh data

A PCR must be `SUBMITTED` before approve → author → implement → release → close can
run. A fresh demo has no PCR at all, so the whole chain needs two hand-walked steps
before any of it can be shown.

**This is how a real bug hid.** The tenant was missing the `PCR_APPROVAL`,
`PCO_APPROVAL` and `PCN_RELEASE` templates entirely, and nothing surfaced it,
because nobody could get far enough down the chain to need them.

**Needs:** a PCR seeded in `SUBMITTED` with its structured diff captured and its
approval assigned, so the chain is enterable at the step the script starts on.

## 6. Reman repair branches need both approval paths

The repair-branch model routes a raised code to a Repair node, and the approval
required depends on the unit:

| Unit kind | Who approves a non-pre-approved repair |
|---|---|
| Customer's own (repair-and-return) | the **customer's** recorded answer |
| Exchange | a **lead** |

**Measured 2026-10-13:** `CORE-240210-0007` is the only unit in rebuild and it is
`REPAIR_RETURN`, so only the customer path is reachable. The exchange cores sit at
DISASSEMBLED and must be released by hand first, and neither has a finding that
raises the non-pre-approved code.

**Needs:** an exchange unit already in rebuild, carrying a finding that raises a
repair the process does **not** pre-approve, so *Approve {code}* can be walked.

**Watch the pool/buy fork:** a SCRAP finding resolves to `REPLACE_POOL` when
serviceable stock exists and `REPLACE_BUY` otherwise, and only one of those has a
Repair node in the demo. Whether a pooled component exists silently decides which
path a script reaches. Seed the stock deliberately and state which path is intended.

## 7. The repair-branch happy path has no subject

**Measured 2026-10-13, found by walking it.** `CORE-240210-0007` reaches Nozzle
Inspection and is held, because its only pending finding is on **Injector Body**
while both Repair nodes are scoped to **Injector Nozzle Assembly** — so nothing
matches and the unit takes the NCR branch.

The result: **the auto-route to a pre-approved repair, the central behaviour of the
repair-branch model, cannot be demonstrated at all.** The NCR branch is good and
worth keeping as an exhibit; it just cannot also be the happy path.

**Root cause was a silent seed bug, and it had two halves** (both fixed
2026-10-13). First, the per-core component lists named `Nozzle` and `Solenoid
Valve`, but the part types are `Injector Nozzle Assembly` and `Control Valve
Assembly`; unmatched names were **skipped without error**, so the core was seeded
with only its Body. Second, `_raise_finding` then fell back to **`components[0]`** —
the first component alphabetically, which is "Injector Body" — so the finding meant
for the nozzle silently landed on the body rather than failing.

Fixing only the first half would have left the second to mis-target the next time a
name drifted. Both lookups now match the exact part-type name, the fallback is gone,
and a missing component logs a warning and skips the finding. **Worth remembering as
a shape: the mismatch made the exhibit wrong, but the fallback made it invisible.**

**Needs:** a grade-C finding on the nozzle, giving the full sequence — hold on
*"waiting on a lead's decision"* → lead applies it on the rebuild plan → auto-routes
to Nozzle Recondition → rejoins at Flow Testing.

## 8. The lead-approval path on an exchange unit is unreachable

The *"Approve {code}"* flow — a lead authorising a repair the process does not
pre-approve — has no subject. `CORE-240215-0005` goes to inventory carrying a
grade-B nozzle, so `CORE-240215-0006`'s scrapped nozzle fills from recovered stock
(`REPLACE_POOL`). A pooled replacement needs no approval, so no hold ever occurs and
there is nothing to approve.

This is the pool/buy fork from item 6 deciding the outcome invisibly: **what is
sitting in recovered stock silently determines whether an approval path exists.**

**Needs:** an exchange unit whose required repair resolves `REPLACE_BUY` — i.e. no
serviceable component of that type in stock — so the approval is actually demanded.

## 9. Reman inherits production concepts that do not mean the same thing there

**Measured 2026-10-13.** On `Injector Reman`, three steps carry
`requires_first_piece_inspection=True` with `fpi_scope=PER_WORKORDER` — Nozzle
Inspection, Flow Testing and Final Test — and five carry `requires_qa_signoff=True`.
Nothing in the DWI asks for this; the player renders a banner because the **Step**
declares it.

**The flag is coherent as data and questionable as process design.** First-piece
inspection is a *production-run* idea: prove the setup is right, then release the
batch of identical parts behind it. `PER_WORKORDER` says "the first unit through
this step proves the setup for the rest of the work order".

A reman work order is not that. Its units are **used cores, each different** — their
own wear, their own findings, their own resolved repair set. On the demo teardown WO
one core is a customer's repair-and-return unit and the others are exchange cores
bound for stock or harvest. There is no shared setup that inspecting the first one
validates for the others, and the per-unit inspection *is* the inspection.

That the same flag appears on all three check steps suggests it was inherited from
the production template rather than decided for reman.

**This is the general shape, and it is bigger than FPI:** the reman route reuses the
production `Steps` model wholesale, so every production concept — first-piece
inspection, batch/lot advancement, sampling, expected scrap and gross-up — arrives
switched on and meaning something subtly different, or nothing at all, on a route
where each unit is unique. The seed rewrite should decide **per concept** whether it
applies to reman, rather than letting the template decide by default.

Per the user (2026-10-13): *"someone did in fact set the requirement to true for FPI
and the issue is that this reman is being 'shared' with new production concepts which
would need to be modeled differently in the seed redo."*

**Needs:** an explicit decision per concept for reman routes — FPI off, or a scope
that means something there; likewise for sampling and scrap gross-up (a scrapped core
already owes no make-up, which is the same realisation applied to a different
concept). Where a concept stays on, the seed should say why.

## 10. There is no as-built exhibit until someone walks a rebuild by hand

**Measured 2026-10-13.** Before walking CORE-240210-0007 to REBUILT, the tenant held
**zero** `AssemblyUsage` rows. The walk created the only two that exist.

`AssemblyUsage` is the as-built record — what was actually fitted to a unit, captured
by the `componentInstallCapture` substep at Assembly. It is the evidence behind any
certificate describing what was replaced, and the thing a customer getting their own
unit back is entitled to see.

**Needs:** a rebuilt unit seeded with its component installs recorded, so the as-built
surface has a subject without someone first walking an entire reman route.

**Related product gap, recorded in the audit (Shipping R2), not fixable by seeding:**
even with the as-built record present there is nowhere to send it. The CoC and packing
list are built from a `CustomerShipment` (`reports/adapters/shipment_documents.py`),
and `return_to_customer` creates no shipment — so a repair-and-return unit goes back
with no document route at all. Seeding the exhibit makes the gap *visible*; it does
not close it.

---

## Standing rules for the rewrite

**Seed through services, never raw writes.** Phase 9 (`dark_exhibits.py`) set the
precedent and it is the reason those exhibits are trustworthy: a record written
straight to the table can be in a state the services would refuse, which teaches a
trainee a workflow that does not exist.

**An exhibit is a *state*, not a row.** Most of the gaps above are rows that exist
in the wrong state. "A core exists" is not "a core is awaiting authorisation".

**Prefer the least-used subject for anything global.** The ITAR flag went on the
*least*-used part type on purpose: the hero type carries 152 of 153 parts, so
flagging it would have made the entire demo export-controlled and emptied it the
moment a facility added a non-US user. The same caution applies to any flag that
filters.

**Assert each exhibit in `test_demo_seed.py`, naming the audit row it protects.**
That is what stops these going dark again unnoticed — the existing assertions were
added for exactly this reason.

**A lookup that matches nothing must never be silent.** This has now bitten three
times in three different subsystems, each time producing plausible-looking empty
state rather than an error:

| Where | The mismatch | What it looked like |
|---|---|---|
| Approval templates | `auto_assign_by_role` held `QA_Manager`; `TenantGroup.name` is `QA Manager` | 3 of 4 templates auto-assigned to **0 users**, silently |
| Seeded core components | list said `Nozzle`; the part type is `Injector Nozzle Assembly` | the component was **skipped**, and the finding meant for it landed on the Body |
| Auth payload (frontend) | code read `me.id`; the endpoint returns `pk` | every player signature stored `user_id: null` while showing the right name |

The shape is identical every time: a filter or lookup finds nothing, nothing raises,
and the absence reads as legitimate emptiness. **Seed code must log or raise on an
unmatched name** — the component-list fix now warns instead of skipping, and that is
the pattern. Where a seed asserts "this exhibit exists", assert the *linkage* too,
not just the row count.

**A later phase must not overwrite what an earlier phase authored.** Seeding runs in
phases, and a phase that *enriches* existing records can silently replace their real
values. Measured 2026-10-13:

- phase 2 (manufacturing) created **Spray Angle** at `15 ±3 degrees`;
- phase 3d (scheduling) wired default gauges with
  `update_or_create(step, label, defaults={..., 'mm', 10 ±0.05})` — and because that
  placeholder spec sat in `defaults`, it **overwrote the authored definition in
  place**;
- phase 4c (DWI) built the operator's node from manufacturing's in-memory object,
  which still held `15 ±3 degrees`.

Result: the work instruction showed the real spec and the database held the
placeholder, so an operator entering the nominal value was told "In spec" on screen
and recorded out of spec in the row — raising a nonconformance and quarantining the
unit, with nothing on screen to explain it.

**Rule:** placeholder or convenience values belong in `create_defaults`, never
`defaults`, so they apply only to a record nobody authored. An enrichment phase
should add what is missing (here, the default gauge) and touch nothing else. Any
`update_or_create` in the seed whose `defaults` carry *domain* values rather than
links is suspect — the same overwrite would have hit every NUMERIC measurement that
two phases both touch.

**The deeper rule, and the one that would have prevented it:** `MeasurementDefinition`
is a **versioned model** (`create_new_version()`, `version` / `previous_version` /
`is_current_version`), and CLAUDE.md is explicit — *versioned models mutate via
`create_new_version()`, never bypass with raw `.save()`*. `update_or_create` is a raw
write, so the seed edited a versioned row **in place**, which the architecture
forbids precisely because other records point at a specific version.

This is why the symptom was possible at all. In normal use a DWI node's copied spec
and the judged spec **cannot** diverge: an API edit creates a *new* definition row,
the old row never changes, and capture judges against the exact linked id. The node's
copy is a snapshot of a row that is itself immutable. **Only an in-place edit of a
versioned row can break that**, and only the seed does in-place edits.

*Recorded as a correction: this was first written up here as an architecture gap —
"the node copies the spec and nothing re-syncs it". That was wrong, and the user
caught it. It is a seed-integrity failure, and the versioning contract is what makes
the architecture sound.*

**Advancing flows is not the same as populating records.** Phase 9 deliberately
populates and does not advance. Several gaps here (a core in rebuild, an FPI with a
clean first piece, a submitted PCR) need the seed to *walk a unit forward* through
the services, which is a different and more expensive kind of seeding. Decide
explicitly which exhibits justify it.
