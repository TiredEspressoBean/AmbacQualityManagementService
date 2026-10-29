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

### Committed one by mistake

After a commit from a what-if, the board reads *This plan was committed from a
what-if* with **Restore the previous plan**. Give a reason, and the plan it
replaced goes live again, while the one you committed becomes a draft once more,
to commit later or discard. It goes **one step back only**, and the reason is kept
on the schedule.

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

The bar also shows **solver gap** for each side, *"X% live · Y% draft"*: how far
each solve could still be from the best possible schedule when it stopped (0%
means proven optimal). When a makespan or lateness difference is no bigger than
the larger gap, it warns *"Differences this small are within the solvers' gap —
they may not be real."*

!!! tip "When to look before committing, rather than just committing"
    Commit freely when lateness drops and the move count is small. Look harder
    when:

    - **Moves are large relative to the plan.** Churn is felt on the floor, and
      a better lateness figure can cost more in disruption than it saves.
    - **Uncovered goes up.** The draft is better on paper but less staffable.
    - **Solver status is not optimal** — it hit its time limit, so this is the
      best it found rather than the best there is.
    - **Solver status reads Quick plan** — the optimizer found no plan in time,
      and this one ignores crew limits and changeovers. Re-solve with more time
      rather than committing it.
    - **Weighted lateness gets worse.** It happens when constraints changed;
      the question is whether the new plan is right, not whether the number is.

## Solving

**Solve** runs the scheduler. It places work onto resources subject to the hard
constraints — machine availability and no-overlap, sequence-dependent
changeover, cumulative capacity, operator shifts, route precedence, and each
work order's earliest release date.

**What-if** explores a change without committing to it.

### How long a solve runs

You decide, in **Scheduling settings** (the gear):

- **Solve time limit (seconds)** is the longest a solve may run. A few minutes
  suits a re-plan during the day; an overnight run can be given hours.
- **Relative gap limit** stops a solve early once its plan is proven within that
  distance of the best possible: *0.02* stops within 2%. At *0* it runs to the
  time limit unless it proves the plan is the best there is.

A solve stops at whichever comes first. **Solve**, **What-if** and the automatic
re-solve of a stale plan all use these settings.

### When there's more work than the window holds

Work that doesn't fit inside the planning horizon is left off the board, and the
rest of the shop still gets a plan. It's listed in [Not
scheduled](#why-isnt-this-scheduled) as **Doesn't fit in the horizon**:

> *2 unit(s) don't fit before Nov 26: the work ahead of them fills the horizon.*
> → Add capacity (overtime, another eligible machine), move lower-priority work
> out, or widen the planning horizon.

Re-running the solve won't change it; the shop is full for the window.

### When the solver runs out of time

Each solve has a time limit. If it runs out before finding any plan:

- **With no live plan yet, or on a What-if,** the board gets a quick rule-based
  plan, and the status badge reads **Quick plan · re-solve with more time**. It
  keeps each part's route order and holds frozen and pinned work where it is, and
  plans machine time around downtime and closures. It doesn't check the crew
  limit or changeovers, and assigns no operators (**Dispatch** can). Re-solve with
  more time for a full plan.
- **With a live plan already,** that plan stays on the board, marked out of date.
  A full earlier plan is better than a quick new one.

### When a re-solve can't keep held work

The scheduler never moves frozen or pinned work to make a plan fit (see [Fence
zones](#fence-zones-how-near-term-work-is-protected)). If held work can't all be
kept, the re-solve fails: the live plan stays on the board, marked out of date,
and the board tells you why. Only a person moves held work: unpin it, drag it, or
fix what's in its way.

### When nobody can run a step

Every solve checks that each training-gated step on the remaining routes has at
least one operator who could actually run it: qualified, active, internal,
rostered to a shift, holding an active tenant membership, and in a shop-floor
group — Operator or Shift Lead.

!!! note "A certified supervisor may not count"
    The shop-floor group condition keeps admins and office staff out of the
    schedule. So someone can hold the certification and still not satisfy this
    check, which is the case worth looking at first when the result surprises
    you. (The condition is skipped entirely if nobody is in a shop-floor
    group.)

If a step has **nobody**, the rest of the shop is still planned. Each unit whose
route passes through that step is planned up to the step before it; that step and
everything after it wait. They're listed in [Not
scheduled](#why-isnt-this-scheduled) as **No qualified operator rostered**, naming
the step and the training it needs:

> *No qualified operator rostered: "Assembly" needs Assembly Certification.
> Planned up to the step before it; it and what follows wait.*
> → Certify or roster a qualified operator, or set the step's labor model to off.

A step whose every machine is down for the whole window is handled the same way,
as **No machine available**. A step with **no eligible machine at all** is
different: it's planned with no machine, so it's on the board but in no machine's
lane, and nothing in **Not scheduled** points at it. See [Machine
Eligibility](setup.md#machine-eligibility).

!!! warning "This is a staffing problem wearing a scheduling costume"
    No scheduling setting fixes it. The answer is to train someone, roster
    someone onto a shift, or change what the step requires.

!!! note "Scarce is not the same as absent"
    This only trips when *nobody* rostered holds the certification. One
    qualified operator for a busy step is planned for: the scheduler serialises
    that work and it lands late, which shows up as lateness.

    Steps with the labour model switched off are skipped entirely, since no
    crew is modelled for them. A unit already running at the step stays on the
    plan; it's already staffed.

The same check surfaces earlier, before you ever solve: an order routed through
an unstaffable step shows as **blocked** in [Pull in work](releasing.md).

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
| **Solve**, **What-if**, **Commit draft** | `add_scheduleresult` | Production Manager, Tenant Admin, **Planner** |
| **Move**, **Pin/Unpin**, **Reassign**, **Dispatch** | `change_scheduledtask` | Production Manager, Tenant Admin, **QA Manager**, **Shift Lead**, **Planner** |
| **Merge**, **Break** | `change_parts` | See [Working on several tasks](#working-on-several-tasks) |

*Held by* is the groups that hold it when an organisation is created. Group permissions can be changed, so check your own in [Roles & Groups](../../admin/users/roles.md).

!!! note "A shift lead can work the board without being able to re-plan it"
    Direct manipulation is deliberately wider than solving. A shift lead
    covering a shift can pin, reassign and dispatch; committing a new plan for
    the whole shop stays with the planner roles. A QA manager has the same reach,
    for holding work on a quality problem.

    The **Planner** is the role whose whole job this is — owning the plan, and so
    holding both levels.

## Editing a work order from the board

**Edit WO** on a task's or a batch's detail opens the **Edit work order**
dialog: **Priority**, **Quantity**, **Earliest start** and **Due date**. The
changes apply to the plan and take effect on the next **Solve**; a quantity
increase adds parts, a decrease cancels unstarted ones.

Changing **Priority** adds a required field, *Why change priority from
&lt;old&gt; to &lt;new&gt;?* — *"Recorded with the change, so the reason is on
file when someone asks later."* **Save** stays disabled until it is filled. The
dialog closes only once the save succeeds; a refused save leaves it open. This
is the same rule as the work order form — see [Changing priority needs a
reason](../work-orders/basics.md#changing-priority-needs-a-reason).

## Moving a task by hand

Drag a task to reschedule it. The task is **pinned** at its new time, the
schedule is marked stale, and — this is the part to understand — **everything
downstream of it on that unit's route moves with it**.

A forward drag pushes the unit's later operations along ahead of it. You'll see
*"Task moved & pinned — N downstream operations shifted"*.

!!! tip "That is why a forward move doesn't bounce"
    Almost every forward move on a job ends after a successor's planned start,
    because there is usually work scheduled behind it. If that refused the move,
    the planner's most ordinary action would be the one the board said no to —
    so the route follows the move instead.

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
    into slack ahead of it reports no count at all — just *"Task moved &
    pinned"*, with the *"N downstream operation(s) shifted"* half omitted. That
    is the ripple finding nothing to do, not the ripple failing.

!!! note "Rippling can create overlaps on purpose"
    Its scope is the **route**, not the resource — so a rippled task can land on
    top of another on the same machine. That contention is recorded and left for
    the next solve to resolve, rather than blocking the move.

    Global constraints (machine no-overlap, changeover, cumulative capacity,
    operator shifts) are re-checked then. If your pin can't stand, it's released
    with its reason, like any held task.

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

## What the solver books, and what it doesn't

The schedule books the **nominal route** — the default path from where each part
stands now. Branches that may never be taken are **not** booked in advance:

- **Rework and escalation** branches, which exist for parts that fail
- **Repair branches on a reman unit**, which are reached only when a teardown
  raises that repair code

A reman core therefore books its whole main line, and the repair work hanging
off it books nothing until it is actually called for. A re-solve picks up the
reality once a part fails or a repair is raised.

!!! note "This is deliberate, and it means the board under-states reman"
    Booking every branch a part might take would reserve capacity for work that
    mostly will not happen. The cost is that a shop with heavy repair content
    sees a plan lighter than its real load, and leans on re-solving.

## Did the floor follow the plan?

Each scheduled task records an **actual start**, when work on the step is started
(not when the unit arrives and waits), and an **actual end** when it leaves the
step. Click a bar on the live board and the task panel shows them beside the plan.

### Plan vs actual

**Plan vs actual**, at the end of Machines / People / Work orders, shows the last 7
days against the plan, opening on the hour scale at now. **By machine** or **By
person** chooses the rows. It shows the live plan only, not a draft.

| On the board | Means |
|--------------|-------|
| A bar drawn where the work **actually** ran, coloured by its finish against its planned end | Green: within **On time within ±**. Blue: finished early, beyond it. Amber: late. Red: later than **Very late after** |
| A bar from its actual start to now (▶) | Running |
| A red dashed outline at the planned slot | **Due, never started**: its slot has passed and the work wasn't started. A unit that arrived and is waiting counts here |
| Grey, *Started before planned* | Work already under way before any plan had it. It can't be judged, so it's left out of the figure |
| Uncoloured, to the right of now | To come, from the live plan |

The headline counts each kind, and gives *Adherence: N% of M ops due in the last 7
days finished on time or early*. Click a bar for the detail, for example *planned
9:00–9:45 · actual 10:20–11:05 · +80 min*. A cycle several units shared is one bar,
*×N*.

!!! important "Each op is judged on the plan it started on"
    A re-solve moves the plan, and a running op is re-placed at "now", so judging
    work against the latest plan would make every slip vanish at the next solve.
    Each op instead keeps its planned finish as it stood **when it started**, and
    is judged against that. Finished work stays on the view after a re-solve too:
    it is drawn from every plan that was live while it ran.

**Early is a deviation too.** Blue can mean the floor ran something ahead of its
turn, so the job that should have run then is late, or that the step's standard time
is padded. **Mark out-of-order starts** flags ops started well ahead of plan.

The two thresholds start at 15 and 60 minutes each time the view opens, and a
change applies only to your view until you leave it. Compare adherence figures
only at the same thresholds, or the percentage moves for reasons that have nothing
to do with the floor.

!!! important "Capture records; it does not react"
    Stamping an actual deliberately **does not** re-time the plan or mark the
    schedule stale. The solver already pins in-progress operations when it
    solves, and a drift recorded on every single advance would leave the
    staleness flag permanently on — and therefore meaningless.

!!! warning "An empty view usually means the sequence, not a fault"
    Work can only be judged against a plan that existed when it started. The
    first plan a shop solves has nothing behind it, so work already running then
    shows as *Started before planned*, and the view fills as work starts after a
    solve.

## Fence zones — how near-term work is protected

The legend carries **Fence: Frozen · Slushy · Liquid**, and every task panel
names the zone its task sits in. The zone comes from **when the task starts**,
measured from the moment of the solve:

| Zone | When it starts | What it means |
|------|----------------|---------------|
| **Frozen** | Within the frozen window — **2 days** by default | Held. A re-solve keeps its machine, its operator and its place in the machine's queue |
| **Slushy** | After that, within the slushy window — **7 further days** by default | Moves cost something. The solver moves one only when that buys a real improvement, and the header shows what moving slushy work cost |
| **Liquid** | Everything later | Freely re-planned on every solve |

Both windows are settings, not constants — a shop that commits further ahead
widens the frozen zone.

!!! note "Frozen holds the order, not the clock"
    A held task keeps its machine, operator and order, but its start can slide
    **later** when the work ahead of it runs late. It never jumps ahead of the
    queue to fill a gap. That's what lets the floor act on tomorrow's plan: the
    sequence people set up for doesn't change under them on a re-solve.

A held task is re-planned only when it can't happen where it is, and it says why:

- its machine is down or out of service, or the plant is closed then;
- its work order can't start that early, or its material won't be in;
- its operator is off the crew, off shift or no longer qualified;
- the crew on shift is already full at that time;
- *its slot passed unstarted*: the time went by without the work starting, and it
  can't fit now.

The header counts them (*1 frozen task(s) re-planned · 85 held*). The scheduler
never moves held work for any other reason, such as to make room for something
else. If held work can't all be kept, the re-solve fails and the live plan stays
(see [When a re-solve can't keep held work](#when-a-re-solve-cant-keep-held-work)).

!!! warning "A what-if tells you which frozen tasks it re-planned"
    A draft that re-plans committed work for one of those reasons warns before you
    commit it, with the number of frozen tasks that moved. That count is the real
    cost of the change; read it beside the late orders, not after them.

A **planner pin** (📌) is a lock you place yourself, and it's held the same way,
whatever zone the task is in. See [Moving a task by hand](#moving-a-task-by-hand).
When something makes a pin impossible, it's released with its reason like any held
task.

## Why the schedule goes stale

A stale schedule is normal, not an error. It goes stale when the world changes
under the plan: a quality hold, new demand, lost capacity, a material receipt, or
a hand edit on the board. Pages derived from the schedule — the [staging
list](overview.md#staging-list) especially — warn when they're working from a
stale solve.

The plan also runs out without going stale. The detailed window is anchored at the
moment of the solve, so a plan solved with a 30-day horizon covers only 20 days of
future a week and a half later, while work that was beyond the window has since
come into it. Nothing marks this: re-solve to reach further. With **Live** auto
re-solve on, the plan re-solves by itself once two thirds of the window are left.

## Working on several tasks

Selecting tasks reveals a toolbar — *"N selected"* — with the actions that only
make sense in bulk. The toolbar appears for anyone with `change_scheduledtask`;
see [Who can touch the board](#who-can-touch-the-board).

!!! note "Merge and Break are gated on parts, not on the board"
    The button follows your board rights, but the server checks
    **`change_parts`** for these two — merging and breaking changes how the parts
    themselves are lotted, not just where a bar sits. Someone with board rights
    but no parts rights sees the buttons and is refused on use.

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
> WO-1042 · Common Rail Injector · 0/2 placed
> Releases Oct 22, past the Oct 21 horizon.
> → Pull the release date in, or widen the planning horizon.

The reasons, in the order they're checked (a work order shows the first that
applies):

| Reason | Means |
|--------|-------|
| **On hold** | The order is held |
| **Not released** | Under planner-released gating, nobody has released it |
| **No process assigned** | It has no routing to schedule against |
| **No units created yet** | The work order has no parts yet — add them |
| **Waiting to ship** | Its units are at the end of the route — ship them |
| **Nothing left to work** | Every unit is finished, shipped, scrapped or quarantined |
| **No routing to schedule** | The process has no steps |
| **No timings authored** | Steps exist with no cycle time — nothing to place |
| **No qualified operator rostered** | No one qualified could run a training-gated step; planned up to the step before (see [When nobody can run a step](#when-nobody-can-run-a-step)) |
| **No machine available** | Every machine eligible for a step is down for the whole window; planned up to the step before |
| **Starts past the horizon** | It releases beyond the planning window |
| **Waiting on material** | Gated until stock arrives |
| **Material short** | Nothing on hand, nothing on order |
| **Added since the last solve** | The schedule predates the order's current state — re-solve |
| **Doesn't fit in the horizon** | The shop is full: the work ahead of it fills the planning window |
| **Not placed by the last solve** | Nothing above explains it; the solve most likely ran out of time. Re-solve with a longer time limit |

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
    never staff appears in **Not scheduled** as *No qualified operator rostered* instead.
    They read alike and have different fixes.

This is a heuristic that picks the highest-priority binding reason, not a formal
critical-path proof — treat it as a pointer to where to look, not a verdict.

## Next Steps

- **[Scheduling Overview](overview.md)** - The other scheduling surfaces
- **[Capacity Planning](capacity.md)** - The long-range view
