# Scheduling Setup

Three tables decide what the scheduler believes about your shop: how long an
operation takes, which machines can run it, and what it costs to switch a
machine between jobs.

They are reached from [**Data Management**](../../admin/data/data-management.md)
(`/Edit`), listed under **Processes** and **Equipment**, rather than from the
sidebar — they are configuration you revisit occasionally, not a daily surface.

!!! important "These are the inputs every other number rests on"
    Capacity heatmaps, release-by dates and delivery promises are all computed
    from what is in these three tables. An operation with no timing contributes
    **no load** — so the shop looks emptier than it is, dates come out too late
    and promises come out too generous.

    If the planning views look implausibly comfortable, start here rather than
    with the solver. See [How the numbers are
    made](how-the-numbers-are-made.md).

## Step Timings

**Data Management** > **Step Timings** (`/production/step-timings`)

*A step's standard times — what the scheduler and rough-cut capacity size every
operation from. One row per step.*

| Column | Means |
|--------|-------|
| **Setup** | Once per run, before pieces start |
| **Cycle / piece** | The per-piece run time |
| **Load / unload / piece** | Handling per piece, on top of cycle |
| **External setup** | Setup that can happen off the machine, while it still runs the previous job |
| **Attention** | Whether the operation needs an operator throughout (*Full attention*) or only to load and unload |

**Attention** is the one with consequences beyond arithmetic: it decides whether
the operation consumes an operator for its whole duration or only at the ends,
which is what lets one person tend several machines.

!!! note "The step is the row's key"
    A timing belongs to exactly one step, so the step cannot be changed on an
    existing row. If you picked the wrong step, delete it and add the right one.

## Machine Eligibility

**Data Management** > **Machine Eligibility** (`/production/step-equipment-affinities`)

*Which machines can run a step, and how well.*

Each row pairs a machine with a step it is allowed to run, and grades the pairing
— *Dialed in (proven best)* down to a machine that merely can. The solver prefers
the better pairing when it has a choice.

| Column | Means |
|--------|-------|
| **Affinity** | How well that machine runs that step |
| **Cycle override** | This machine's own cycle time, when it differs. *Step standard* means it uses the step's. |

!!! tip "A cycle override is how you model an old machine"
    Two machines can run the same step at different speeds. Setting an override
    on the slower one keeps the step's standard honest instead of averaging the
    two into a figure neither machine achieves.

!!! warning "Eligibility is also a constraint"
    A step with no eligible machine cannot be scheduled on one. If work is
    landing in **Not scheduled**, check here before assuming a capacity problem.

## Changeovers

**Data Management** > **Changeovers** (`/production/work-center-changeovers`)

*Minutes to reconfigure a machine when it switches from running one step to
another. One row per machine, from step and to step.*

The matrix is **directional** — going from Nozzle Inspection to Flow Testing need
not cost the same as the reverse — and it is per machine, because the same
switch is not equally expensive everywhere.

This is what makes the solver group similar work rather than interleaving it.
With no changeover rows it has no reason to, and will happily alternate between
two jobs that each cost half an hour to set up.

!!! note "There is also a flat job-change setup"
    **Scheduling settings** carries a *Job-change setup (min)* charged whenever a
    resource switches work order on the same operation. That is the general case;
    these rows are the specific one.

## Editing them

Each page lists its rows, lets you **edit** or **delete** one, and carries
[Import/Export](../../admin/data/import-export.md) for bulk work. A **Show
archived** toggle reveals deleted rows.

!!! important "New rows are made on the owning record, not here"
    There is no *New* button on these three. A row belongs to something else, and
    that is where it is created:

    | Table | Authored on |
    |-------|-------------|
    | Step Timings | the step — its **Timing** section |
    | Machine Eligibility | the machine's **Steps it can run**, or the step's **Machines** |
    | Changeovers | the machine's **Changeovers** section |

    These pages are the place to **see the whole set at once** — which is what
    you want when checking for gaps — and to load one in bulk.

Import is the practical route for a matrix: a changeover table is *machines ×
from × to*, which is a spreadsheet job rather than a form-at-a-time job.

!!! note "Delete archives, and re-adding restores"
    Deleting a row stops it applying. Adding the same key back — the same step,
    or the same machine/from/to — restores the original row rather than creating a
    duplicate.

## Next Steps

- [How the Numbers Are Made](how-the-numbers-are-made.md) — what these feed
- [Schedule (Gantt)](gantt.md) — the plan they produce
- [Capacity Planning](capacity.md) — the long-range view
