# Assigning Work Orders

Work order assignment in uqmes operates at the **step execution level** rather than the work order level. This provides more granular control over who performs each operation.

!!! info "Step-Level Assignment"
    Equipment and operator assignments are made when executing individual steps, not on the work order as a whole. This allows different operators and equipment to be used for different steps in the process.

## How Assignment Works

There are two routes: the scheduler plans assignments ahead, and the operator's
own action records who actually did the work.

### Planned: dispatch

**Dispatch** is the second pass of scheduling. The solve schedules *machines*;
dispatch then assigns an *operator* to each attended operation, taking the
machine schedule as given — start and end times do not move.

Two properties matter:

- It assigns **per lot, not per piece**. A work order's parts sitting at one
  step ran as a single machine occupancy and need one operator, so they are
  grouped and assigned together.
- An operator is only given a step they are **qualified for**, at the required
  training level. Training gaps surface here as unassignable work.

See [Schedule (Gantt)](../scheduling/gantt.md#dispatch).

### Actual: step execution

When an operator begins work on a step, the system records who is doing it:

1. Open the work order and click **Start Work**
2. Check the parts to be worked
3. The step player records the **operator** and **timestamps** as each substep
   is confirmed

### Recording Equipment Used

Equipment is captured as part of the work instructions: a step can include an
**Equipment + roles** capture, which records what was actually used against
that part's record. See
[Authoring Work Instructions](../dwi/authoring.md).

A step can also carry an **equipment affinity**, which tells the scheduler
which equipment the step prefers or requires.

## Operator Qualifications

The check is not optional and it is not a warning. An operator whose record does
not meet a step's training requirement is **refused at the moment work starts**,
and told exactly what is missing — *"Level 1, needs Level 2"*.

A certification that has lapsed no longer counts: the gate reads the **current**
level, meaning the highest the person holds that is still in date.

### Taking over someone else's step

Starting a step already assigned to another operator raises a gate naming the
current owner. Both this and the training gate are cleared the same way: a
**supervisor signs in on the operator's own screen**, with their own password
and a reason.

The authorisation is written onto the step execution and stays there — who was
authorised, who authorised it, what was missing, and when. It is a recorded
business decision, not a way to make the requirement disappear.

You can see it on the **part's traveller** — the work order's control page →
the part's history — as an amber line under the step it was used on: who worked
it, what training they lacked, who authorised it, when, and the reason.

!!! note "You cannot clear your own gap"
    The override needs a *different*, active user, and repeated password
    failures are throttled. See [Running Work
    Instructions](../dwi/running.md#if-youre-not-qualified-for-the-step).

## Viewing Assignment History

### On Part Detail
The **Activity History** section on the part's detail page records each change
with the actor and a timestamp. See [Part
History](../tracking/part-history.md).

### On Work Order
The work order shows overall progress and which parts are at which steps.

## Shift Considerations

For multi-shift operations:

- Work orders can span shifts
- Different operators complete different steps
- Step execution history provides full traceability

## Permissions

| Permission | Allows | Held by |
|------------|--------|---------|
| `change_scheduledtask` | Dispatch, and reassign a task on the board by hand | Planner, Production Manager, QA Manager, Shift Lead, Tenant Admin |
| `override_training_gate` | Authorise an operator to start work their record doesn't cover | Shift Lead, QA Manager, Production Manager, Tenant Admin |
| `view_equipments` | See equipment options | Every staff role |
| `view_user` | See operator options | Every staff role |

*Held by* is the groups that hold it when an organisation is created. Group permissions can be changed, so check your own in [Roles & Groups](../../admin/users/roles.md).

!!! note "There is nothing to assign *on the work order*"
    `change_workorder` edits the job — priority, dates, notes — not who works
    it. Assignment lives on the **scheduled task** (planned) and the **step
    execution** (actual), which is why a Shift Lead can reassign work on their
    shift without being able to re-plan the shop.

## Next Steps

- [Work Order Progress](progress.md) - Tracking completion
- [First Piece Inspection](fpi.md) - FPI workflow
- [Equipment Setup](../../admin/setup/equipment.md) - Configure equipment
