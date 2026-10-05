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
away. Committing supersedes the previous live plan; older drafts are cleared.

**Discard is final** — a discarded draft is gone, not archived. If there is
anything in it worth keeping, commit it or write the numbers down first.

!!! note "The Live/Draft toggle only appears once a draft exists"
    It is not a permanent two-mode switch. Run **What-if** and the toggle
    appears; discard or commit and it goes away again.

### Comparing before you commit

The board compares the two and shows the difference — *"makespan X → Y h"*,
*"lateness X → Y"* and *"moves N tasks"*. Behind those it has, for each plan: solver status,
weighted lateness, makespan, task count, and **uncovered** (tasks needing an
operator that have none).

A task counts as *moved* when the draft gives it a different start or a
different machine, or adds it outright.

!!! tip "When to look before committing, rather than just committing"
    Commit freely when lateness drops and the move count is small. Look harder
    when:

    - **Moves are large relative to the plan.** Churn is felt on the floor, and
      a better lateness figure can cost more in disruption than it saves.
    - **Uncovered goes up.** The draft is better on paper but less staffable.
    - **Solver status is not optimal** — it hit its time limit, so this is the
      best it found rather than the best there is.
    - **Weighted lateness gets worse.** It happens when constraints changed;
      the question is whether the new plan is right, not whether the number is.

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

### When nobody can run a step

Before it plans anything, every solve checks that each training-gated step on the
remaining routes has at least one operator who could actually run it: qualified,
active, internal, rostered to a shift, holding an active tenant membership, and
in a shop-floor group — Operator or Shift Lead.

!!! note "A certified supervisor may not count"
    The shop-floor group condition keeps admins and office staff out of the
    schedule. So someone can hold the certification and still not satisfy this
    check, which is the case worth looking at first when the refusal surprises
    you. (The condition is skipped entirely if nobody is in a shop-floor
    group.)

If any step has **nobody**, the solve is refused outright. No schedule is
produced and the live plan stays exactly as it was. You get the reason, naming
the steps and what they need:

> *2 step(s) require training no rostered operator holds: Assembly needs
> Assembly Certification; …*

!!! warning "This is a staffing problem wearing a scheduling costume"
    No scheduling setting fixes it. The answer is to train someone, roster
    someone onto a shift, or change what the step requires.

!!! note "Scarce is not the same as absent"
    This only trips when *nobody* rostered holds the certification. One
    qualified operator for a busy step does not refuse the solve — the
    scheduler serialises that work and it lands late, which shows up as
    lateness rather than as a refusal.

    Steps with the labour model switched off are skipped entirely, since no
    crew is modelled for them.

The same check surfaces earlier, before you ever solve: an order routed through
an unstaffable step shows as **blocked** in [Pull in work](releasing.md), and
those parts appear in the Unscheduled panel as **No trained operator**.

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

## Who can touch the board

The board splits into two levels of authority, and they are not the same group.

| What | Needs | Held by |
|------|-------|---------|
| **Solve**, **What-if**, **Commit draft** | `add_scheduleresult` | Production Manager, Tenant Admin |
| **Move**, **Pin/Unpin**, **Merge/Break**, **Reassign**, **Dispatch** | `change_scheduledtask` | Production Manager, Tenant Admin, **QA Manager**, **Shift Lead** |

!!! note "A shift lead can work the board without being able to re-plan it"
    Direct manipulation is deliberately wider than solving. A shift lead
    covering a shift can pin, reassign and dispatch; committing a new plan for
    the whole shop stays with the planner roles. A QA manager has the same reach,
    for holding work on a quality problem.

## Moving a task by hand

Drag a task to reschedule it. The task is **pinned** at its new time, the
schedule is marked stale, and — this is the part to understand — **everything
downstream of it on that unit's route moves with it**.

A forward drag pushes the unit's later operations along ahead of it. You'll see
*"Task moved & pinned — N downstream operations shifted"*.

!!! tip "That is why a forward move doesn't bounce"
    The board used to refuse any move finishing after a successor starts — which
    is every forward move on a job with work already scheduled behind it, so the
    planner's most ordinary action was the one the board said no to. Now the
    route follows the move.

### Why a drop is refused

Two checks run on the drop itself, before anything ripples:

| Refusal | What it means |
|---------|---------------|
| *"That start is before the schedule horizon."* / *"That would push the task past the schedule horizon."* | The board only plans a fixed window. You cannot park work outside it. |
| *"That start is before the work order's release date (Mmm DD)."* | Nothing starts before its order is released. Move the release date if that is what you meant. |

Then the ripple runs, and it has two stops of its own:

- **A pinned successor.** *"'X' is pinned at … Unpin it, or move it first."* —
  **Unpin** is on the selection toolbar (see [Working on several
  tasks](#working-on-several-tasks)).
- **The horizon again.** A ripple that would push a downstream operation out of
  the window is refused and names it: *"That would push 'X' past the schedule
  horizon."*

Nothing may start before its predecessor, either — that check always stands, and
no amount of rippling downstream changes it.

Tasks that shift as a consequence are **not** pinned. They moved because
something else did, not because you decided where they go.

!!! note "A small nudge may shift nothing"
    Only successors that would *otherwise overlap* are pushed. A forward move
    into slack ahead of it reports **0 downstream operations shifted** — that is
    the ripple finding nothing to do, not the ripple failing.

!!! note "Rippling can create overlaps on purpose"
    Its scope is the **route**, not the resource — so a rippled task can land on
    top of another on the same machine. That contention is recorded and left for
    the next solve to resolve, rather than blocking the move.

    Global constraints (machine no-overlap, changeover, cumulative capacity,
    operator shifts) are re-checked then, and your pin is relaxed if it turns
    out to be infeasible.

### Undo

**Undo** on the board reverses the last manual move *including everything it
pushed* — the whole cascade is snapshotted, not just the task you dragged.

### Dragging to a different lane

In the **Machines** and **People** views, dropping a task on a different lane
reassigns it — the machine or the operator — and applies immediately.

!!! warning "Reassignment warns but does not block"
    Dropping onto a machine the step isn't authored for, or an operator without
    the required training, **is allowed**. You get a warning, not a refusal.

    So a lane drag can put work somewhere the solver would never have placed it.
    That is the point — you know something it doesn't — but it is on you.

Lane changes do nothing in the **Work orders** view, which groups by order
rather than by resource.

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

## Working on several tasks

Selecting tasks reveals a toolbar — *"N selected"* — with the actions that only
make sense in bulk. It needs `change_scheduledtask`; see [Who can touch the
board](#who-can-touch-the-board).

| Action | What it does |
|--------|--------------|
| **Merge** | Schedule the selected parts as their work order's **lot** — one bar. Needs two or more. |
| **Break** | The opposite: schedule each part as its own bar. |
| **Pin** | Hold the selected tasks where they are, so the next solve works around them. |
| **Unpin** | Release them again. **This is what a pinned-successor refusal is asking for.** |
| **Reassign…** | Set a machine and/or an operator for everything selected at once. |

!!! tip "Merge and Break are the lot-size decision"
    Dispatch assigns per lot, not per piece. Merging says *these units travel
    together*; breaking says *schedule them independently*. It is the same
    decision either way — whether the shop treats the order as one job or many.

## Why isn't this scheduled?

**Not scheduled** on the toolbar opens *Why isn't this scheduled?* — the answer
to "my job isn't on the board". It reads *"N of M open work order(s) aren't fully
on the board"* and groups them by reason, each row naming the work order, how
many of its units were placed (*"0/2 placed"*), the specific detail, and the fix:

> **STARTS PAST THE HORIZON — 1**
> DEMO-PLAN-RR · Common Rail Injector · 0/2 placed
> Releases Oct 22, past the Oct 21 horizon.
> → Pull the release date in, or widen the planning horizon.

The reasons:

| Reason | Means |
|--------|-------|
| **On hold** | The order is held |
| **Not released** | Under planner-released gating, nobody has released it |
| **No process assigned** | It has no routing to schedule against |
| **No routing to schedule** | The process has no steps |
| **No timings authored** | Steps exist with no cycle time — nothing to place |
| **Nothing left to work** | Every unit is finished, shipped, scrapped or quarantined |
| **No trained operator** | No one qualified could run a training-gated step |
| **Material short** | Nothing on hand, nothing on order |
| **Waiting on material** | Gated until stock arrives |
| **Starts past the horizon** | It releases beyond the planning window |
| **Added since the last solve** | The schedule predates the order's current state — re-solve |
| **Not placed by the last solve** | The solver ran and left it out |

**Re-check** re-runs the diagnosis. If the board is stale the dialog says so,
because several of these resolve themselves on the next solve.

## Why an order is late

Every task finishing after its work order's due date is tagged with the single
constraint that best explains it:

| What the task reads | What it means | Where to go |
|---------------------|---------------|-------------|
| **Material short — no incoming receipt** | Nothing on hand and nothing on order | Supply |
| **Uncovered — no operator assigned** | The step needs an operator and hasn't got one | **Dispatch** — this is usually one click, not a training problem |
| **Machine contention — *machine* busy** | It queued behind other work on that resource | The machine's lane |
| **Late release — WO released *Mmm DD*** | It couldn't start earlier than it did | The order's release date |
| **Tight lead time vs due date** | The work itself doesn't fit before the date | The date, or the routing |

!!! warning "Uncovered is not a training gap"
    *Uncovered* means no operator is **assigned** — which is what you get before
    Dispatch has run, or when it left the task uncovered. A task the board could
    never staff appears in **Not scheduled** as *No trained operator* instead.
    They read alike and have different fixes.

This is a heuristic that picks the highest-priority binding reason, not a formal
critical-path proof — treat it as a pointer to where to look, not a verdict.

## Next Steps

- **[Scheduling Overview](overview.md)** - The other scheduling surfaces
- **[Capacity Planning](capacity.md)** - The long-range view
