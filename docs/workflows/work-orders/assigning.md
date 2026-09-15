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

The system can validate operator qualifications:

- **Training**: Operator trained on the process
- **Certification**: Current certifications for the step

!!! warning "Qualification Check"
    If training records are enforced, operators without required training may be blocked from executing certain steps.

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

| Permission | Allows |
|------------|--------|
| `change_workorder` | Assign/reassign work orders |
| `view_equipments` | See equipment options |
| `view_user` | See operator options |

## Best Practices

1. **Assign early** - Helps planning visibility
2. **Check availability** - Avoid conflicts
3. **Verify qualifications** - Ensure training current
4. **Update on change** - Keep assignments accurate
5. **Use notes** - Communicate special instructions

## Next Steps

- [Work Order Progress](progress.md) - Tracking completion
- [First Piece Inspection](fpi.md) - FPI workflow
- [Equipment Setup](../../admin/setup/equipment.md) - Configure equipment
