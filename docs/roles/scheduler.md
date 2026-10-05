# Scheduler

**Running the board.** Turning the plan into who does what, on which machine,
today and this week.

!!! info "There is no Scheduler group either"
    Like [Planner](planner.md), this is a job rather than a group.

    **Solving and committing** a schedule need `add_scheduleresult` — **Production
    Manager** or **Tenant Admin**. **Working the board** — moving, pinning,
    reassigning, dispatching — needs `change_scheduledtask`, which **QA Manager**
    and **Shift Lead** hold as well.

    So a shift lead can run the board for their shift without being able to
    re-plan the shop. See [Who can touch the
    board](../workflows/scheduling/gantt.md#who-can-touch-the-board).

## Scheduler or planner?

They are different horizons, and confusing them produces confident wrong answers.

| | Planner | Scheduler |
|---|---------|-----------|
| **Horizon** | Months to weeks | Days to hours |
| **Question** | Can we take it, and what do we release? | Where does it run, in what order, and who does it? |
| **Surfaces** | Capacity Planning, Requirements, Releasing | **Schedule (Gantt)**, Dispatch, Staging |

If you are being asked whether a date is achievable, that is
[Planner](planner.md) work.

## The loop

1. **Solve** — the solver places every task it can
2. Read **Not scheduled** — what it couldn't place, and why
3. **Dispatch** — assign operators to the placed work
4. Adjust by hand where you know something the solver doesn't
5. Re-solve when the shop moves

### Solve, and what the figures mean

The header carries solver status, task count, **makespan**, **weighted
lateness** and how long the solve took. **What-if** explores a change without
touching the live schedule; **Commit draft** makes it real.

!!! tip "Judge a draft by disruption, not only by lateness"
    The board compares the two — *makespan X → Y h*, *lateness X → Y*, *moves N
    tasks*. A better lateness figure that moves 500 tasks can cost more in
    disruption than it saves. See [Comparing before you
    commit](../workflows/scheduling/gantt.md#comparing-before-you-commit).

### Why isn't my job on the board?

**Not scheduled** answers it directly, grouped by reason, each row naming the
work order, how many units were placed, and the fix. Twelve reasons, from *On
hold* and *Not released* through *No trained operator* and *Material short* to
*Added since the last solve*.

Several resolve themselves on the next solve, and the dialog says so when the
schedule is stale.

### Dispatch

Dispatch assigns operators to placed tasks, **per lot rather than per piece**.
Until it runs, late tasks read *Uncovered — no operator assigned*, which is a
one-click problem rather than a training one.

### Moving something by hand

Drag a task and the rest of that unit's route **ripples with it**. Two checks run
first — the schedule horizon and the work order's release date — and a **pinned
successor** stops a ripple and is named.

**Merge** and **Break** decide whether an order's units travel as one lot or
separately. **Unpin** is what a pinned-successor refusal is asking for.

Everything here is in [Schedule (Gantt)](../workflows/scheduling/gantt.md).

## When the shop fights the plan

| Symptom | Look at |
|---------|---------|
| Dates look too comfortable | [Step Timings](../workflows/scheduling/setup.md#step-timings) — an operation with no cycle time contributes no load |
| Work lands on the wrong machine | [Machine Eligibility](../workflows/scheduling/setup.md#machine-eligibility) |
| The solver interleaves similar jobs | [Changeovers](../workflows/scheduling/setup.md#changeovers) |
| A promise failed on people, not machines | The training matrix — a binding resource can be a certification |

## Next Steps

- [Schedule (Gantt)](../workflows/scheduling/gantt.md) — the board in full
- [Planner](planner.md) — the horizon above this one
- [Scheduling Setup](../workflows/scheduling/setup.md) — what the solver believes
