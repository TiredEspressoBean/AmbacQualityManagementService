# Schedule (Gantt)

The Gantt board is where the plan lives: what runs on which resource, in what
order, and what's going to be late.

**Scheduling** > **Schedule (Gantt)**

## Views

Three ways to look at the same plan:

| View | Rows are |
|------|----------|
| **Machines** | Work centers and equipment, with their loaded hours |
| **People** | Operators |
| **Work orders** | Jobs |

A **Not scheduled** counter shows work that hasn't been placed.

## Live and Draft

The board has two modes:

- **Live** — the plan the floor is working to
- **Draft** — a working copy you can change without affecting anyone

Draft is what makes the board safe to experiment on. Change things, look at the
result, then either **Commit draft** to make it live or **Discard** to throw it
away.

## Solving

**Solve** runs the scheduler. It places work onto resources subject to the hard
constraints — machine availability and no-overlap, sequence-dependent
changeover, cumulative capacity, operator shifts, route precedence, and each
work order's earliest release date.

**What-if** explores a change without committing to it.

### When the solve can't place anything

If the scheduler returns no plan at all, the board tells you *why* rather than
showing an empty week. The usual cause is arithmetic: every operation admitted
to the planning window must also finish inside it, so asking for more hours than
the window holds yields no assignment at all. The diagnostic names the resources
that overflowed.

The fix is normally to extend the horizon, move demand out, or add capacity —
not to re-run the solve.

## Dispatch

**Solve** schedules *machines*. **Dispatch** is a second pass that assigns an
*operator* to each attended operation, taking the machine schedule as given —
start and end times don't move.

Two things worth knowing:

- Dispatch assigns **per lot, not per piece**. A work order's parts sitting at
  one step ran as a single machine occupancy and need one operator, so they're
  grouped and assigned together.
- An operator is only given a step they're **qualified** for, based on their
  training records at the required level. Training gaps show up here as
  unassignable work.

## Moving a task by hand

Drag a task to reschedule it. On drop, three cheap local checks run immediately:

1. Does it still fall inside the planning horizon?
2. Does it respect the work order's earliest release date?
3. Does it respect route precedence against this unit's scheduled neighbours?

An obviously bad drop snaps back with a reason. If the checks pass, the task is
**pinned** at its new time and the schedule is marked stale.

!!! note "The next Solve is the authority"
    A hand-placed task isn't fully validated on drop — only those three local
    checks run. The global constraints (machine no-overlap, changeover,
    cumulative capacity, operator shifts) are re-checked on the next solve,
    which may relax your pin if it turns out to be infeasible.

## Why the schedule goes stale

A stale schedule is normal, not an error. Two different things cause it:

**Drift** — the world changed under the plan: a quality hold, new demand, lost
capacity, a material receipt.

**The roll** — nothing happened at all. The detailed window is anchored at the
moment of the solve, so a plan solved with a 30-day horizon covers only 20 days
of future a week and a half later, while work that was beyond the window has
since come into it. The plan doesn't go *wrong*; it runs out.

This is why pages derived from the schedule — the [staging
list](overview.md#staging-list) especially — warn when they're working from a
stale solve.

## Why an order is late

Every task finishing after its work order's due date is tagged with the single
constraint that best explains it:

| Cause | Meaning |
|-------|---------|
| **Material** | Waiting on material availability |
| **Labor** | No qualified operator capacity |
| **Machine contention** | The resource was busy |
| **Release date** | Couldn't start earlier |
| **Lead time** | The work itself doesn't fit before the due date |

This is a heuristic that picks the highest-priority binding reason, not a formal
critical-path proof — treat it as a pointer to where to look, not a verdict.

## Next Steps

- **[Scheduling Overview](overview.md)** - The other scheduling surfaces
- **[Capacity Planning](capacity.md)** - The long-range view
