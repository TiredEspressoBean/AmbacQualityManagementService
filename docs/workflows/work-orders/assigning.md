# Assigning Work Orders

Work order assignment in Ambac Tracker operates at the **step execution level** rather than the work order level. This provides more granular control over who performs each operation.

!!! info "Step-Level Assignment"
    Equipment and operator assignments are made when executing individual steps, not on the work order as a whole. This allows different operators and equipment to be used for different steps in the process.

## How Assignment Works

### Step Execution Assignment

When an operator begins work on a step:

1. Navigate to the work order or part
2. Start the step execution
3. The system records:
   - **Operator**: The user performing the work
   - **Equipment**: The machine/tool used (if applicable)
   - **Timestamp**: When work began

### Recording Equipment Used

Equipment is captured during step completion:

1. Complete the step measurements or quality report
2. Select the equipment/machine used
3. This links the work to a specific piece of equipment

## Operator Qualifications

The system can validate operator qualifications:

- **Training**: Operator trained on the process
- **Certification**: Current certifications for the step

!!! warning "Qualification Check"
    If training records are enforced, operators without required training may be blocked from executing certain steps.

## Viewing Assignment History

### On Part Detail
View the step execution history to see:

- Which operator performed each step
- What equipment was used
- When each step was completed

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
| `view_equipment` | See equipment options |
| `view_users` | See operator options |

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
