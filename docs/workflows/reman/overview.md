# Remanufacturing Overview

Remanufacturing takes a used unit — a **core** — and either rebuilds it or strips
it for the components other rebuilds need.

## A core is a part

This is the thing to understand first, because everything else follows from it.

A core is not a separate kind of record that shadows a part. **It is a part**,
with a reman *role* attached. The part carries the work order, the step, the
schedule, the digital work instructions, the sampling decisions and the quality
records — exactly as any other part does. The core role carries only what is
particular to reman: the stage, the condition grade, the source.

| Question | Where it lives |
|----------|----------------|
| Where is this unit, and can it be worked? | The **part** — work order, step, part status |
| Where is it in its reman life? | The **core role** — the reman stage |

The unit's identifier is the same on both sides: the part's ERP id **is** the
core number.

!!! tip "Why this matters day to day"
    A core in teardown appears on the work order like any other part, is
    scheduled like any other part, and runs its work in the ordinary operator
    runtime. There is no separate reman world to go and look in.

## Stage and status

A core has a **stage**; its part has a **status**. The status is *derived* from
the stage by one function, and written by the same call that moves the stage, so
the two cannot disagree — with one deliberate exception, below.

!!! important "Only the actions move a stage"
    A stage changes by doing the thing — starting a teardown, releasing a unit,
    scrapping it. There is no field to set it to, and setting one directly is
    refused rather than honoured.

    This is what keeps the pair honest. A stage written on its own would skip
    the service that derives the part status, and the unit would be in one place
    according to reman and another according to the scheduler — with nothing
    reporting the disagreement.

    The same holds for the unit's identity: the core number and core type are
    mirrored onto the part, so neither is an ordinary editable field.

!!! warning "Fulfilment mode is correctable, but only while the core is Received"
    It is not immutable — a mode set wrongly at receipt can be edited on the
    core, right up until teardown starts. After that it is refused:

    > Can only be changed while the core is Received — teardown has started, and
    > harvest, reservations and authorisation already follow from it.

    That is the honest line: before teardown nothing has been decided by it;
    after teardown, components have been reserved (or not), exits have been
    offered (or not), and an authorisation may already exist. Changing it then
    would rewrite decisions already made.

    So a clerk who picked the wrong mode has a window — and only that window.

!!! note "A quality hold outranks the derived status"
    The one case where stage and status legitimately differ: if the part is in a
    QA hold, a stage change does **not** overwrite its status unless the new one
    is an ending (scrapped, say). Quarantine is cleared by a disposition, never
    as a side effect of the unit moving on.

    So a quarantined core can read *In Rebuild* with its part still held. That
    is the hold doing its job, not a sync failure.

| Reman stage | Part status | Meaning |
|-------------|-------------|---------|
| **Received** (no work order) | Core Banked | In the bank, not yet planned |
| **Received** (on a work order) | Pending | Planned; waiting to be scheduled |
| **In disassembly** | In Progress | Being torn down |
| **Disassembled** | On Hold | Waiting on a release decision |
| **Awaiting customer authorisation** | On Hold | Waiting on the customer |
| **In rebuild** | In Progress | Being rebuilt |
| **Rebuilt — ready to return** | Completed | Rebuilt for its owner |
| **Rebuilt to stock** | In Stock | Finished goods on the shelf |
| **Scope declined** | Awaiting Pickup | Going back unrepaired |
| **Returned to customer** / **Returned unrepaired** | Shipped | Gone back to the customer |
| **Harvested to inventory** | Dismantled | Taken apart; its components are parts now |
| **Scrapped** | Scrapped | |

!!! note "Two statuses exist for reman's sake"
    **Dismantled** is terminal but is *not* output — a harvested unit no longer
    exists, and must not be counted as something the shop produced. **On Hold**
    is neither terminal nor schedulable, which is what a unit waiting on a
    decision needs: parking it in Core Banked would let the work order close
    around a unit still due to be rebuilt.

## The two fulfilment modes

What happens to a core after teardown depends on who owns it, and the difference
is decided at release.

**Repair and return** — the customer's own unit comes back to them. It is torn
down, rebuilt, and returned. **It is never harvested**: you cannot give someone
else's unit away for parts.

**Exchange** — the customer gets a unit from stock, and theirs joins the pool.
It has two exits:

- **Rebuild to stock** — rebuilt and shelved as finished goods, keeping its own
  identity
- **Harvest for parts** — stripped, its components becoming stock in their own
  right

The planner chooses at release: **Release to rebuild** for repair-and-return;
**Rebuild to stock** or **Harvest for parts** for exchange.

## The Remanufacturing dashboard

**Remanufacturing > Dashboard** (`/reman`) is the section's front door, and the
only place the receive paths are linked from.

Four counts across the top — **Total Cores**, **Awaiting Disassembly**, **In
Disassembly**, **Usable Components** (shown as usable of total) — then two cards
with pre-filtered links: cores awaiting disassembly, cores in progress, usable
components, and components **pending inventory acceptance**.

Its header carries the three entry points:

| Button | For |
|--------|-----|
| **Receive Core** | One unit — see [Receiving Cores](receiving.md) |
| **Receive Cores** | Several at once, as a paste-from-spreadsheet grid |
| **Core Lots** | Counted but unidentified units — see [Bulk core lots](receiving.md#bulk-core-lots) |

!!! note "Two buttons, one letter apart"
    **Receive Core** and **Receive Cores** are the single form and the batch
    grid. Check which you opened.

## Where the work happens

Teardown and rebuild are **ordinary work at a step**, run in the operator's
digital work instruction runtime — not on a separate reman screen. Three reman
capture types do the reman-specific parts:

| Capture | Where | Records |
|---------|-------|---------|
| **Harvested component** | Teardown | Which components came out, and their grade |
| **Component install** | Rebuild | What went into each slot of the rebuild plan — see [Rebuild](rebuild.md) |
| **Rebuild finding** | Rebuild | A component found worse than teardown graded it |

See [Running Work Instructions](../dwi/running.md).

## Findings are proposals, not corrections

When a rebuilder finds a component worse than teardown said it was, that is
recorded as a **proposed** regrade — it does not change the grade by itself.

A lead applies or dismisses each proposal on the rebuild plan page, which
requires the `accept_component` permission. This is deliberate: a regrade moves
inventory value and affects what other rebuilds can be promised, so it stays a
human decision.

## The authorisation hold

A unit at **Awaiting authorisation** is waiting on the customer, and is
genuinely stopped: it cannot be started, captured on, or advanced. **No
supervisor override bypasses this** — unlike the training gate, which a
supervisor can authorise past.

Sending a unit for authorisation is a lead's deliberate act, not something the
system does on its own.

## Key concepts

### Cores

A used unit received for remanufacturing. Carries a unique core number, a
condition grade, and a source. Its core credit value is **informational only** —
it may inform an accounting system, but nothing here prices or invoices.

### Harvested components

Components recovered during teardown. Each is graded, and an accepted one
becomes stock with traceability back to the core it came from. Life tracking can
transfer from core to component.

### Disassembly BOM

What a core type is expected to yield, with expected fallout. It is what the
teardown capture lists as rows to work through.

Strictness is a property of the **capture**, not of the BOM — see
[Teardown](disassembly.md).

### Bulk core lots

Cores can also arrive counted but unidentified, as a lot. See
[Receiving Cores](receiving.md).

## Permissions

| Permission | Allows |
|------------|--------|
| `view_core` | View cores and their stages |
| `add_core` | Receive cores |
| `change_core` | Move a core through its stages |
| `complete_disassembly` | **Release a torn-down unit** — to rebuild, to stock, or to harvest |
| `grade_component` | Record or edit a harvested component |
| `accept_component` | Accept components into stock, and apply or dismiss findings |
| `reject_component` | Scrap a harvested component |

## Related Topics

- [Receiving Cores](receiving.md) — single units and bulk lots
- [Disassembly](disassembly.md) — teardown in the runtime
- [Rebuild](rebuild.md) — the rebuild plan, slots, scope and install
- [Harvested Components](components.md) — grading, acceptance, findings
- [Running Work Instructions](../dwi/running.md) — the runtime the work happens in
