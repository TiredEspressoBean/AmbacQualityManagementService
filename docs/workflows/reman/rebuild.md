# Rebuild

Putting a unit back together: what goes into each position, what has to be done
to it, and how the scope grows past what was sold.

## The rebuild plan

**Remanufacturing** > a core > **Rebuild plan** (`/reman/cores/{id}/rebuild`)

The plan is a **proposal**, not a schedule. Nothing is committed by opening it,
and it can be looked at for a unit nobody has decided to rebuild yet. A person
curates it.

### What is on the page

In order down the screen:

| Panel | What it is |
|-------|------------|
| **Findings to decide** | Components the bench graded worse than teardown did. Apply or Dismiss. |
| **Proposed, not committed** | The plan's **warnings** — everything the resolver wants to tell you |
| **Operations** | The work this rebuild needs, each with the reason it is there |
| **Slots** | One row per position, headed *"N need a decision · M settled"* |

Operations come before slots deliberately: what we will *do* to the unit is the
bigger commitment.

!!! tip "The warnings panel is the diagnostic channel"
    Every caveat on this page — a kit that over-states, lines dropped as out of
    scope, a pool that isn't offered — surfaces there and nowhere else. If a
    number looks wrong, read it before anything else.

### Slots, not quantities

A rebuild BOM does not explode into quantities — it explodes into **slots**, one
per position, each of quantity one, each bound to an identified individual part.

That is the difference between reman and ordinary kitting. Raw material is
fungible; a harvested nozzle is not. It carries its own grade, its own
accumulated life and its own provenance, and two of the same part number are
**not** interchangeable — not to the customer, not to quality, not to cost.

So the question a slot answers is *which one goes in this position*, never *how
many do we need*.

### How a slot resolves

The grade teardown gave a component decides what happens to it:

| Grade found | Resolution (as the screen reads it) | What it means |
|-------------|------------------------------------|---------------|
| **A** or **B** | **Reuse as-is** | Serviceable; goes back in as it came out |
| **C** | **Recondition** | Fit only after work — the slot raises an operation |
| **Scrap**, or missing | **Replace — recovered stock** / **Replace — buy** | Something else fills the position |

!!! warning "This is one shop-wide default, not a per-line rule"
    A/B serviceable and C reconditionable is a single policy applied to every
    slot. There is no per-BOM-line acceptance criterion — a line cannot say
    *"grade C is fine for this position"*. The only per-line control today is
    whether harvested parts are allowed at all.

    So don't go looking for a setting to tune it. If your shop needs a different
    rule for a particular position, that is a change to make, not a field to
    find.

!!! note "A slot can emit work instead of demand"
    *Recondition the nozzle* and *replace the nozzle* resolve the same slot: one
    is an operation, the other is a part. That is why scope and kit are decided
    together here rather than in two passes — you cannot know what the job needs
    doing until you know what is going back into it.

### Two kinds of replace

| | Where the part comes from |
|---|---|
| **Replace — recovered stock** | A component harvested from *another* core |
| **Replace — buy** | Purchased |

When it proposes recovered stock it says how many are available (*"1
available"*). When it proposes a buy, the reason tells you which kind of buy it
is:

- **Before teardown** — *"teardown may yet recover this — costed as a purchase"*.
  The unit isn't open yet, so nothing has been recovered from it. Every slot
  reads as a purchase.
- **After teardown** — *"nothing serviceable available"*. The unit is open and
  the answer is settled.

!!! warning "A repair-and-return unit is never offered the pool"
    Recovered stock comes from other people's cores. On a unit that goes back to
    its own customer, that pool is not merely empty — it is never consulted, so
    **every replace is a buy**. The plan says so:

    > *Control Valve Assembly at unpositioned: this unit goes back to its
    > customer, so recovered stock from other cores is not offered.*

    This is the mirror of [Reserved parts](#reserved-parts) below. That rule
    stops this unit's components going to other jobs; this one stops other
    jobs' components coming here. Same principle, both directions.

### What needs your attention

The screen opens on the slots that need a decision. **Reuse is the unremarkable
outcome** — the part came out serviceable and goes back — so everything *else*
is surfaced, because everything else costs money or time.

You can override any proposal with **Change**. Two things to know:

- **A reason is required.** *"Say why — an override with no reason cannot be
  told from a misclick later."* The dialog's button is **Record decision**,
  which is what it is.
- **It moves the work, not just the row.** Overrides are applied *before* scope
  is derived, so changing a slot from replace to recondition changes which
  repair codes are raised. Expect the **Expected repairs** panel below to
  change too — and with it, which branches the route's checks will take.

The plan keeps what it would have done alongside what you chose: "the planner
disagreed" only means something next to what they disagreed with. **Back to the
proposed resolution** on the row clears an override again.

## Entry scope and accumulated scope

Two layers, and the gap between them is the story of the job.

**Entry scope** is what was sold before anything was opened up — a tier, a
service level, "performance restoration". **Accumulated scope** is what the
findings added: each slot resolution raises a **repair code**, and the codes
compose into the actual work.

A unit ships having had a set of operations no tier name describes. That gap is
the over-and-above story, and it is what
[authorisation](disassembly.md#waiting-on-the-customer) exists to decide.

### Every repair says why it is there

The **Expected repairs** panel is the point of the whole arrangement. Its
columns are **Repair**, **Code**, **At check**, **Approval** and **Because**:

| Repair | Code | At check | Approval | Because |
|--------|------|----------|----------|---------|
| Nozzle Recondition | NZL-RECON | Nozzle Inspection | Pre-approved | Injector Nozzle Assembly: Grade C, from this unit |
| Nozzle Replacement | NZL-REPLACE | Nozzle Inspection | Needs approval | Injector Nozzle Assembly: Grade D, from this unit |

!!! important "These are branches, not the route"
    **Every operation on the route runs.** The rebuild route is one approved
    process and the unit walks all of it. What this panel lists is the
    *repairs* that route's checks will send this unit to — each one because a
    finding or the rebuild level raised its code.

    A repair that isn't raised is a branch not taken, and that is what the
    traveler shows. Nothing is skipped and nothing is omitted.

The **Because** column carries the provenance, which is the whole reason the
panel is worth reading. Three ways a repair gets raised:

- **the entry scope** — *"Standard rebuild"*, sold up front
- **a finding** — *"{position}: {what was found}"*, raised by a slot resolution
- **always** — see below

Without it you would see a list of repairs with no way to challenge any of
them. With it, a customer asking "why am I being charged for nitride coating"
has an answer attached to the repair.

!!! warning "Read the Approval column before the unit gets there"
    A repair marked **Needs approval** holds the unit at its check until
    somebody answers — a lead on an exchange unit, or the customer on their
    own unit. The panel shows you that in advance, so the answer can be sought
    before the unit is standing still waiting for it.

    **Pre-approved** means the repair goes ahead on the inspector's finding.
    That is set per edge on the approved process, so the same repair can be
    routine at teardown and need an answer at final test.

!!! note "A third source: ALWAYS codes"
    Some repair codes are marked to be raised on **every** unit of that type,
    whatever the entry scope and whatever the findings — cleaning, final test,
    packaging. They show as *always*.

    So the two-layer story has a floor under it. Base scope is neither sold nor
    found; it is a property of the code.

A repair code with **no component type** means *whatever the component* —
whole-unit work like a final test, raised by any slot taking that resolution.

!!! info "Where the master data lives"
    **Repair Codes** and **Rebuild Levels** are authored under the
    Remanufacturing section. They are what scope resolves against.

    A core type with neither is still released to rebuild perfectly well — the
    unit walks its main line and no repair branch is ever offered. What release
    actually requires is that **the route continues past teardown**: *"… has no
    next step on its route after teardown — check the work order's process
    continues past teardown."*

!!! warning "A released assembly BOM is the hard prerequisite"
    Repair codes decide the *work*; the assembly BOM decides the *positions*.
    With no **released** BOM for the core type there are no slots at all, and
    the page says so:

    > No slots — there is no released assembly BOM for this core type.

    A core type with codes and no released BOM produces a plan with operations
    and an empty kit, which looks like a bug and isn't. Release the BOM.

## Why the kit is shorter than the BOM

Every operation on the main line runs, so a BOM line consumed at one is
**always in the kit**. What gets dropped is narrower: a line consumed at a
**Repair node** is in the kit only when that repair is expected — when a
finding or the rebuild level raised its code. A branch this unit won't take
takes its parts with it.

A line with no consuming step at all stays, because there is nowhere to place
it and dropping it would hide it. The plan tells you how many went:

> N BOM line(s) are consumed at repairs this unit isn't expected to need and
> are not in the kit.

!!! note "No repairs expected is normal, not a warning about the kit"
    When nothing raised a code you'll see:

    > No repair codes matched this unit's findings, so no repairs are expected.
    > Every operation on its route still runs.

    That second sentence is the part to read. The unit is not under-scoped and
    the kit is not over-stated — it simply needs no repair branches, and the
    main line covers it.

!!! warning "A kit priced before teardown is a worst case, not a kit"
    Open the plan on a unit that hasn't finished teardown and every slot reads
    as a purchase, because nothing has been recovered from it yet:

    > This core has not finished teardown, so nothing has been recovered from
    > it yet and every slot reads as a purchase. Useful as a worst-case
    > estimate of what a rebuild would cost — not as a kit.

    Read it as the ceiling on the job, and expect it to come down once the
    findings land.

!!! note "Raw material never becomes a slot"
    A BOM line with no component type — bulk material, consumables — has no
    individual identity to assign, so it is skipped. Slots exist only for things
    the shop can point at.

## Doing the work

Rebuild runs in the operator's step player, like teardown. Two captures do the
reman-specific parts:

| Capture | Records |
|---------|---------|
| **Component install** | What actually went into each slot |
| **Rebuild finding** | A component found worse than teardown graded it |

Install capture is what closes the loop: the plan proposed an individual for a
position, and this records the individual that went in.

!!! warning "You cannot install another core's harvested component directly"
    A harvested record belongs to the core it came out of, and install refuses
    one from anywhere else: *"… came out of a different core."* A pool fill is
    not an exception to this — it goes in as the **part** that was accepted into
    stock, not as the harvested record. If the bench is refusing a component you
    were told to fit, that is usually why.

### Fitted the wrong component

The core's page has an **As built** card: each component fitted, by whom and when.
**Remove** the wrong one, with a required reason. It is struck through on the
record, not deleted, and is free to be fitted elsewhere, or here again through the
rebuild (**Continue rebuild** on the core's page).

If the unit was already *Rebuilt* (or *Rebuilt to stock*), removing a component
sends it back to *In Rebuild*. It is not ready to ship until the slot is filled
again. A unit that has already gone back to its customer, or shipped, can't have
components removed here.

Findings are proposals a lead decides — see [Harvested
Components](components.md#findings-a-component-found-worse-at-the-bench).
Applying one re-resolves the plan from the new grade, exactly as it would have
resolved at teardown.

## Reserved parts

A component recovered from a **repair-and-return** core belongs to that
customer, and once accepted into stock it looks like any other part.

The system records that it is spoken for, and refuses to let it be attached to
anyone else's job. Without that, the first rebuild to come along would quietly
consume a part the customer is owed.

!!! warning "A part can be unavailable while appearing in stock"
    If a slot won't accept a part that plainly exists, check whether it is
    reserved to its own core. This is deliberate, not a bug — and it applies
    only to repair-and-return units, since an exchange core's components belong
    to the shop.

    The refusal ends *"Release the reservation first if the arrangement has
    changed."* **There is no control for that yet** — the operation exists in
    the system but has no button. If an arrangement genuinely changed, that is
    currently a job for an administrator rather than something you can do from
    this screen.

## Ready to Rebuild

**Remanufacturing** > **Ready to Rebuild** (`/reman/rebuild-queue`)

!!! warning "The label is misleading"
    This lists units that are **already in rebuild** — released, with work to
    do. It is not a queue of torn-down units awaiting a release decision.

    Units waiting on that decision sit at *Disassembled*; you'll find them on
    the core list or the work order's cores card. See
    [Teardown](disassembly.md#deciding-the-units-exit).

## Finishing

As with teardown, there is no *Finish rebuild* button: the unit reaches the end
of its route in the operator runtime and the stage moves on its own.

!!! note "Nothing is skipped"
    Every unit walks the whole main line of its rebuild route. Scope decides
    which **repair branches** the route's checks send it down, not which
    operations it performs — so there is no such thing as a skipped operation
    on a rebuild, and nothing is recorded as Skipped.

    If a repair you expected didn't happen, the answer is in the
    [Expected repairs panel](#every-repair-says-why-it-is-there): no finding and
    no rebuild level raised that code, so the branch was never offered.

    This replaced an earlier arrangement where a unit's route was built from the
    operations its codes named. It is worth knowing why, because the failure was
    quiet: an operation nothing happened to name was walked past — a nozzle
    inspection could vanish because no code mentioned it — and a decision point
    walked past with no result left the unit deadlocked.

Where a rebuilt unit goes depends on how it was being fulfilled:

- **Repair and return** → *Rebuilt — ready to return*, then **Return** ships it
  back to its customer, from the Cores card or the Shipping board
- **Exchange** → *Rebuilt to stock*, shelved as finished goods, keeping its own
  identity. Once it is on an order it ships from the Shipping board and ends at
  *Shipped on exchange*

See [Remanufacturing Overview](overview.md) for the full stage list.

## Next Steps

- [Teardown](disassembly.md) — where the findings and the release decision happen
- [Harvested Components](components.md) — grading, acceptance and findings
- [Remanufacturing Overview](overview.md) — stages, statuses and fulfilment modes
