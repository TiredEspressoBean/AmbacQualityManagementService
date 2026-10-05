# Teardown

Taking a core apart, recording what came out of it, and deciding what happens to
the unit next.

!!! info "There is no separate disassembly screen"
    Teardown used to have a standalone page. It doesn't any more: a core **is a
    part**, so teardown is ordinary work at a step, run in the operator's step
    player like any other operation. The old
    `/reman/cores/{id}/disassembly` link redirects to the core's page.

    That change is the point rather than a detail — the standalone screen
    skipped the process steps entirely, so teardown bypassed the training
    gates, sampling and quality records that every other operation runs
    through. See [Remanufacturing Overview](overview.md).

## Starting

From the core's page, or the work order's cores card:

| Core stage | Button | What it does |
|------------|--------|--------------|
| Received | **Start teardown** | Opens a teardown work order and takes you into the runtime |
| In disassembly | **Continue teardown** | Reopens the unit at the step it is at |
| In rebuild | **Continue rebuild** | Same, on the rebuild side |

!!! warning "Don't put a core on a work order before starting its teardown"
    **Start teardown** creates the teardown work order itself. A core that is
    already linked to one is refused — *"Core … is already linked to a work
    order"* — so planning it onto a work order first is the one thing that stops
    this working.

    The runtime opens a unit *at a step*, so **Continue teardown** and
    **Continue rebuild** do need the unit to be on a work order and placed at a
    step. That is the normal state after **Start teardown** has run.

## Recording what came out

Teardown's reman-specific work is a **harvested component** capture on the
substep. Its rows come from the core type's **disassembly BOM** — the components
that unit is expected to yield — so the capture is a worklist rather than a blank
form.

For each row, record whether the component came out and the grade it came out in.

!!! note "Strict mode is enforced by the server"
    A harvest capture can be set to **strict**, which requires every BOM row to
    be accounted for before the step completes. That is checked server-side, not
    just in the browser, so it holds however the capture is submitted.

Components you record become [harvested components](components.md), each
traceable back to this core.

## How teardown finishes

There is no *Finish teardown* button. Teardown ends when the unit **reaches the
end of its route** in the operator runtime — the last step is completed and the
core moves to **Disassembled** on its own.

That is why the stage is trustworthy: it records that the work was actually
done, step by step, rather than that someone said it was.

## Deciding the unit's exit

At **Disassembled** the core's part is **On Hold** —
not being worked, and deliberately not schedulable, until someone decides what
happens to it.

What you are offered depends on how the unit is being fulfilled:

=== "Repair and return"

    One button: **Release to rebuild**.

    The customer's own unit goes back to the customer, so rebuilding is the only
    exit. There is no harvest option, and the server refuses one — you cannot
    give away a unit that belongs to somebody else.

    Releasing takes you straight into the rebuild, opening the unit at its first
    in-scope operation.

=== "Exchange"

    Two buttons: **Rebuild to stock** and **Harvest for parts**.

    The unit belongs to the shop, so both exits are legitimate:

    - **Rebuild to stock** — the normal choice. It is rebuilt and shelved as
      finished goods, **keeping its own identity** rather than becoming an
      anonymous unit.
    - **Harvest for parts** — when its body has failed, or cores of this type are
      in surplus. Its usable components become stock in their own right and the
      unit itself ceases to exist.

!!! tip "Harvesting is not scrapping"
    A harvested unit reaches **Dismantled**, which is terminal but is *not*
    counted as something the shop produced — its value went into its components.
    Scrapping says the unit was rejected. Reach for scrap when there was nothing
    worth recovering.

## Waiting on the customer

A unit can be sent to **Awaiting authorisation** when the customer has to approve
work beyond what was sold. That is a lead's deliberate act; nothing sends a unit
there automatically.

**Authorise…** is on the work order's **cores card**, not the core's own page,
and it appears once the unit is **in rebuild** — after release, when the findings
have shown what the job actually needs.

!!! important "There has to be something to authorise"
    The request is refused when nothing on the unit goes beyond the rebuild level
    that was sold: *"Nothing on … goes beyond the rebuild level that was sold, so
    there is nothing to authorise."*

    That is the whole idea rather than an obstacle — authorisation exists for
    **over-and-above** work. If the rebuild is within scope, there is no decision
    for the customer to make and the unit should simply proceed.

### Recording the answer

The same card carries **Approved** and **Declined** once the unit is waiting.

- **Approved** — work resumes.
- **Declined** — the unit moves to *Scope declined*, and goes back unrepaired.

A **Return** button then dispatches the unit back to its customer, from either
*Rebuilt* or *Scope declined*. That is what moves a unit to *Returned to
customer* or *Returned unrepaired*.

!!! danger "The authorisation hold cannot be overridden"
    A unit awaiting authorisation cannot be started, captured on, or advanced,
    and **no supervisor override bypasses it**. This is unlike the training
    gate, where a supervisor can authorise an unqualified operator through with
    a recorded reason.

    The difference is deliberate: a training gate protects work the shop
    controls, and an authorisation hold protects a decision that is not the
    shop's to make.

## Scrapping a core

**Scrap** is on the core's page, at any stage while the unit is still in the
shop — Received, In Disassembly, Disassembled, In Rebuild, or Awaiting
authorisation. It disappears once a unit has ended.

A reason is required. The stage moves to Scrapped, the condition grade is set to
Scrap, and the part is scrapped with it; the work order closes if nothing else
on it is open.

!!! warning "On a repair-and-return unit, the reason goes to the customer"
    You are scrapping something that belongs to them. The dialog says as much —
    write the reason for that reader, not as a shop note.

Scrapping goes through the core's stage, not the part — as do all of a core's
endings. Nothing writes a core part's status directly.

## Disassembly BOM

What a core type is expected to yield:

| Field | Description |
|-------|-------------|
| **Component Type** | The component expected |
| **Expected Qty** | How many per core |
| **Fallout Rate** | The proportion typically unusable |

It drives the teardown capture's rows and feeds component-availability planning.

## Life tracking transfer

When a component is accepted into stock, life-tracking records from the core are
examined, those applicable to the component type transfer with it, and the source
is marked `TRANSFERRED`. Accumulated life follows the component rather than being
lost with the unit.

## Troubleshooting

### Can't start a teardown

- The core must be at **Received**
- It must **not** already be on a work order — **Start teardown** creates one,
  and refuses a core that has one already
- Check your permissions

There also has to be a teardown route to put it on. Two config gaps refuse the
start, and neither is something an operator can fix:

- **No disassembly process for that core type** — *"No eligible disassembly
  Process found for core_type X"*. A `Process` has to be approved and flagged as
  a disassembly process. Ask an administrator.
- **More than one, with no default** — the system will not guess. Pick the
  process explicitly from the teardown action on the **Cores** list, or have a
  default set for that core type.

### Nothing happens on "Continue teardown"

The unit is probably not at a step. A core on a work order but never scheduled
has no step to open at, and the runtime needs one to open.

### Component type not found

Component types come from Part Types. Ask an administrator to add it.

!!! danger "Never record a component under a different type"
    Not even temporarily, and not to keep the job moving. The component type is
    what carries life-limit tracking and traceability for the rest of that
    part's service life — a component logged under the wrong type inherits the
    wrong life limit and cannot be found when its real type is recalled or
    superseded.

    Hold the work and get the part type added. A stalled teardown is a
    scheduling problem; a mis-typed component is a traceability failure that
    surfaces years later.

### Life tracking not transferring

Life tracking only transfers where the component type has a `PartTypeLifeLimit`.
Check the definitions apply to that type.

## Next Steps

- [Rebuild](rebuild.md) — what happens to a unit released to rebuild
- [Harvested Components](components.md) — grading, acceptance, and findings
- [Remanufacturing Overview](overview.md) — stages, statuses and fulfilment modes
- [Running Work Instructions](../dwi/running.md) — the runtime teardown runs in
