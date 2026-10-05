# Releasing Work

**Deciding what to let onto the shop floor** — the planning half of the APS,
upstream of everything the [Schedule board](gantt.md) does.

## Two release modes

Release mode is a **tenant-wide setting**, not something set per order:

| Mode | Behaviour |
|------|-----------|
| **Automatic** | The scheduler plans everything that is open and due. Date-driven |
| **Manual** | A work order is not schedulable until a planner releases it |

Under manual mode each order carries a **released** marker, which the solver
consults. Under automatic mode that marker is ignored — so switching modes
changes the behaviour of the whole shop, not of individual orders.

Manual release gives you a **pre-shop pool**: orders exist, but the scheduler
cannot see them yet. The gate is a marker on the work order, not a separate
object — there is no planned-order-to-production-order conversion step to
perform.

!!! tip "Why this is a flag and not a chain of order types"
    Larger ERPs model release as planned → firm planned → production → released,
    each a separate record to convert. At 50–500 people the same person plans
    and schedules, so a second object to convert is pure ceremony. The mode
    changes the behaviour; nothing else changes shape.

### Where this is set

On the [Schedule board](gantt.md), **Scheduling settings** (the gear) → *What
the scheduler may plan* → **Release gate**, as *Date-driven (schedule everything
open)* or *Planner-released*. It is a tenant setting and applies on the next
Solve, What-if or Dispatch.

!!! warning "The pacing controls are hidden until the gate is planner-released"
    **What paces release** and **Release ceiling (% of capacity)** — the policy
    and the norm this page spends the rest of its length on — only appear in
    that dialog once **Release gate** is set to planner-released. Under
    date-driven there is no pre-shop pool to pace, so the controls are not
    merely defaulted, they are absent.

    If you came looking for them and the section isn't there, that is why.

## Pull in work

Under manual mode, the primary planning act is not *creating* a work order — it
is deciding which of the ones that already exist should go on the schedule.

That queue lives on the **Schedule board** itself, under **Pull in work**, for
the same reason: at this size the planner and the scheduler are the same person
looking at the same screen. Creating a work order stays available there as the
secondary, rush-order path.

Each row shows the order's id and part type, its open units and due date, and
any **blockers** or **warnings**. A priority badge appears only for Urgent and
High. Readiness shows as the absence of blockers rather than as a marker of its
own.

## The recommendation

Alongside the queue, the system recommends **which orders to release now**.

It walks the pool in priority order. For each order it looks for the first
gating resource that order would push past its norm — if there is one, that
order is held and the resource is named.

!!! important "The walk does not stop at the first order it holds"
    It carries on down the pool, so a smaller order further down can still fit
    and be recommended. "First breach" is per order, not the end of the walk.

    This matters because the opposite behaviour — halting at the first big job
    — would leave capacity unused behind it.

!!! note "What you see of the reasoning"
    Internally each verdict carries its blocking resource and the hours that
    order would add. On screen that arrives as the **Load if released** panel
    for your current selection — which names the policy and the ceiling inline,
    as *"Workload control @ 85%"*, and lists the four most-loaded resources —
    not as a per-row explanation. The blockers and warnings on a row are a
    separate readiness check, not the workload verdict.

**Recommend** pre-selects the recommended rows; nothing is released until you
confirm. **Select all ready** is there because overriding the norms is a
legitimate thing to do. Releasing an order that is *not* ready requires an
override reason.

Utilisation is shown as a banded colour rather than a smooth gradient, because
the decision changes at the boundaries and a ramp makes 88% and 104% look alike.
The bands are colour only — there is no badge naming them:

| Load against norm | Reads as |
|-------------------|----------|
| Up to 85% | room |
| Over 85% | tight |
| Over 100% | over |

!!! info "Advisory, always"
    The recommendation releases nothing. It proposes a set and says why; you
    accept, edit or ignore it.

    This is deliberate and not a missing feature. The workload-control
    literature warns that automatic order release can improve shop-floor
    metrics while making *total delivery* worse — and every dashboard here
    watches the shop floor. Enforcing it automatically waits until
    time-in-system is measured.

## Two policies

| Policy | Gates on |
|--------|----------|
| **Workload control** | Every resource, at a percentage of its capacity in the window |
| **Constraint-focused** | Only work centres flagged as a constraint |

Choose constraint-focused when one resource genuinely governs output. Balancing
every resource loses its advantage once a strong bottleneck exists, and pacing
release to the constraint wins instead.

!!! note "Constraint-focused is half of drum-buffer-rope"
    It is the drum — release paced by the constraint. The rope's time buffer,
    releasing material a fixed lead ahead of the constraint rather than just
    capping its queue, is not modelled. Call it constraint-focused release
    rather than DBR.

    If no work centre is flagged as a constraint it falls back to gating
    everything, since a policy gating on nothing would release the whole pool.
    The settings dialog warns you about this when you pick the policy: mark the
    governing station as the bottleneck under **Admin → Work Centers**, or it
    behaves identically to balancing.

## Two traps the gate is built to avoid

**Premature idleness.** Holding an order back while a resource sits idle is
strictly worse than releasing it: the shop loses hours it can never recover and
the order is late for nothing. So the norms have a floor under them — for each
gating resource with **zero** committed load, the first held order that would
load that resource is released anyway, one per starving resource. It re-checks
after each, because one order often feeds a work centre and the crew pool at
once.

!!! note "It is a floor against idleness, not an underload rule"
    A resource at 5% of its norm gets nothing extra. Only *no work at all*
    triggers this. If you want more work on a lightly loaded resource, that is
    your override to make.

**Lead time syndrome.** The classic MRP failure is planned lead times inflating
to cover queues, which releases work earlier, which lengthens queues, which
inflates the planned lead times again — actual lead time becomes a
self-fulfilling consequence of the planned one.

!!! warning "Release never reads a planned or configured lead time"
    The release decision is driven by **measured load against capacity**. No
    planned lead time enters it, so there is no configured quantity that can
    spiral.

    The system does compute lead times elsewhere — capacity planning
    back-schedules undated orders to work out when they must start. But those
    are derived from measured queue time and work content, never from a number
    someone set. See [How the numbers are made](how-the-numbers-are-made.md).

    If you find yourself wanting to pad a lead time to make dates come out
    right, that is the syndrome starting.

## Where this sits

| Question | Surface |
|----------|---------|
| Can we absorb the next 12 months? | [Capacity Planning](capacity.md) |
| **What should we let in now?** | **Pull in work** (this page) |
| Where does it run, and in what order? | [Schedule board](gantt.md) |

Release decides admission; the scheduler decides sequence. Handing the scheduler
six weeks of work for a two-week window is what the gate exists to prevent.

## Next Steps

- [Schedule (Gantt)](gantt.md) — where released work is placed
- [Capacity Planning](capacity.md) — the long view above release
- [Scheduling Overview](overview.md) — the other surfaces
