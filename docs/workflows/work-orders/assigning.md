# Assigning Work Orders

Assign work orders to equipment, work centers, and operators for production planning and tracking.

## Equipment Assignment

### Assigning Equipment

1. Open the work order
2. Click **Assign Equipment** or edit the work order
3. Select the equipment from the dropdown
4. Save

### Equipment Considerations

- **Capability**: Equipment must be able to perform the process
- **Availability**: Check current utilization
- **Calibration**: Equipment must be in calibration
- **Maintenance**: Not scheduled for maintenance

### Multiple Equipment

If work is spread across machines:

1. Different steps may use different equipment
2. Track equipment per step transition
3. See equipment utilization reports

## Operator Assignment

### Assigning Operators

1. Open the work order
2. Click **Assign Operator** or edit
3. Select the operator(s)
4. Save

### Operator Qualifications

The system can validate:

- **Training**: Operator trained on the process
- **Certification**: Current certifications
- **Authorization**: Approved for equipment type

!!! warning "Qualification Check"
    If training records are enforced, operators without required training may be blocked from assignment.

## Work Center Assignment

If your facility uses work centers:

1. Assign to work center (group of equipment)
2. Specific equipment selected at runtime
3. Balances load across machines

## Assignment Methods

### Manual Assignment
Planner assigns specific equipment and operators.

### Self-Assignment
Operators claim available work orders:

1. View available work orders
2. Click **Claim** or **Start**
3. Work order is assigned to you

### Automatic Assignment (if configured)
Based on rules:

- Shortest queue
- Best fit (equipment capability)
- Load balancing

## Viewing Assignments

### By Work Order
Open work order to see current assignments.

### By Equipment
Navigate to **Equipment** to see:

- Current work order
- Queue of upcoming work
- Utilization metrics

### By Operator
In user management or dashboards:

- Current assignments
- Workload
- Completed work

## Reassignment

To change assignments:

1. Open the work order
2. Click **Reassign**
3. Select new equipment/operator
4. Enter reason for change
5. Save

Previous assignments are logged in history.

## Capacity Planning

Use assignment data for planning:

### Equipment Utilization
```
Utilization = Active time / Available time
```

View on equipment dashboard.

### Operator Workload
- Parts assigned
- Estimated hours
- Current vs. capacity

### Queue Depth
Work orders waiting per equipment.

## Shift Assignments

For multi-shift operations:

1. Work orders can span shifts
2. Different operators per shift
3. Handoff notes between shifts

## Notifications

Assignment triggers notifications:

| Event | Who is Notified |
|-------|-----------------|
| Work order assigned to you | Operator |
| Work order reassigned away | Previous assignee |
| Rush work order assigned | Operator + supervisor |
| Equipment assignment conflict | Planner |

## Tracking Time

Time tracking by assignment:

- **Clock in/out** on work order
- **Automatic** based on transitions
- **Duration** per operator

Used for:

- Labor costing
- Efficiency metrics
- Capacity planning

## Assignment Conflicts

The system detects:

- Equipment double-booked
- Operator overloaded
- Conflicting shifts

Warnings appear but may not block (configurable).

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
