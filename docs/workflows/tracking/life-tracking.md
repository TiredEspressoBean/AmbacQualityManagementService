# Life Tracking

Life tracking monitors accumulated usage, cycles, or calendar time against defined limits. This is essential for:

- **Aerospace** - Life Limited Parts (LLPs), rotables, time-controlled items
- **Automotive** - Tool and die life, shot counts
- **Manufacturing** - Equipment hours, calibration intervals
- **Materials** - Shelf life, expiration dates

## Key Concepts

### Life Limit Definitions

A **definition** describes what you're tracking:

| Field | Description | Example |
|-------|-------------|---------|
| **Name** | Display name | "Flight Cycles" |
| **Unit** | What's measured | "cycles" |
| **Unit Label** | Display label | "Cycles" |
| **Soft Limit** | Warning threshold | 18,000 |
| **Hard Limit** | Absolute limit | 20,000 |
| **Calendar Based** | Time-based tracking | False |

**Calendar-Based Tracking**: For shelf life and expiration tracking. Instead of incrementing a counter, the system calculates elapsed time from a reference date.

### Part Type Life Limits

Links definitions to part types. When a part type has life limits:

- Parts of that type can have life tracking records
- If marked "required", tracking must be created
- Multiple definitions can apply to one part type

### Life Tracking Records

The actual tracking data for a specific part:

| Field | Description |
|-------|-------------|
| **Definition** | Which limit definition applies |
| **Accumulated** | Current value (cycles, hours, etc.) |
| **Reference Date** | For calendar-based: start date |
| **Source** | Where the data came from |
| **Status** | OK, WARNING, or EXPIRED |

## Status Levels

| Status | Meaning | Action |
|--------|---------|--------|
| **OK** | Below soft limit | Normal operation |
| **WARNING** | At or above soft limit, below hard limit | Plan for overhaul/replacement |
| **EXPIRED** | At or above hard limit | Part must be removed from service |

## Data Sources

Track where life data originated:

| Source | Use When |
|--------|----------|
| **OEM** | From manufacturer records |
| **Customer** | Customer-provided documentation |
| **Logbook** | From aircraft/equipment logbooks |
| **Calculated** | Computed from known usage |
| **Estimated** | Best estimate when records incomplete |
| **Transferred** | Transferred from core during reman |
| **Reset** | Reset to zero after rebuild |

## Creating Life Tracking

### For New Parts

When creating parts with life-limited types:

1. Part type determines applicable definitions
2. For required definitions, tracking is created automatically
3. Enter initial accumulated value
4. Set reference date for calendar-based items
5. Select data source

### From Harvested Components

When accepting components to inventory:

1. Life tracking from the source core transfers automatically
2. Source is marked as `TRANSFERRED`
3. Accumulated values are preserved
4. Maintains traceability to original core

## Incrementing Life

As parts are used, increment their life:

1. After each operation/cycle/flight
2. Enter the amount to add
3. System updates accumulated value
4. Status recalculates automatically

For calendar-based items, no incrementing is needed - elapsed time is calculated automatically.

## Viewing Life Status

### On Part Details

Each part displays its life tracking:

- Current value vs limits
- Percentage used
- Status indicator
- Remaining until limit

### Warning and Expired Lists

View parts approaching or exceeding limits:

1. Navigate to life tracking reports
2. Filter by status (WARNING, EXPIRED)
3. Review parts needing attention

## Limit Overrides

For specific parts that receive engineering approval for extended limits:

1. Open the life tracking record
2. Click **Apply Override**
3. Enter new limit values
4. Provide justification reason
5. Record approving user

Overrides apply only to that specific part, not the definition.

## Resetting Life

After rebuild/overhaul, reset accumulated value:

1. Open the life tracking record
2. Click **Reset**
3. Enter reason for reset
4. Accumulated resets to zero
5. Source changes to `RESET`
6. Previous value saved in reset history

## Calendar-Based Tracking

For materials with shelf life:

### Setup

1. Create definition with `is_calendar_based = true`
2. Set hard limit in days (or months/years)
3. Link to appropriate part types

### How It Works

- Reference date = manufacture or receipt date
- Current value = elapsed time since reference
- Status calculated from elapsed vs limits
- No manual incrementing needed

### Example: 365-Day Shelf Life

| Definition | Value |
|------------|-------|
| Name | Shelf Life |
| Unit | days |
| Hard Limit | 365 |
| Calendar Based | Yes |

If reference date is Jan 1 and today is July 1, current value = 181 days.

## Best Practices

1. **Set realistic limits** - Use manufacturer or engineering specifications
2. **Document sources** - Record where life data came from
3. **Review warnings** - Act on WARNING status before expiration
4. **Track overrides** - Require engineering approval for extensions
5. **Audit regularly** - Review expired items for proper disposition
6. **Maintain traceability** - Link back to source documentation

## Integration Points

### CAPA

Life exceedances can trigger CAPAs:

- Parts used beyond limits
- Missing life tracking for required items
- Incorrect life data discovered

### Quality Reports

Create quality reports when:

- Part found at or beyond hard limit
- Life data accuracy in question
- Override approval needed

### Reman Module

Life tracking transfers during disassembly:

- Core life records examined
- Applicable records transfer to components
- Maintains life continuity through remanufacturing

## Permissions

| Permission | Allows |
|------------|--------|
| `view_lifetracking` | View life tracking records |
| `add_lifetracking` | Create tracking records |
| `change_lifetracking` | Update values, apply overrides |
| `view_lifelimitdefinition` | View definitions |
| `add_lifelimitdefinition` | Create definitions (admin) |
| `change_lifelimitdefinition` | Modify definitions (admin) |

## Troubleshooting

### No Life Tracking Available

- Check if part type has PartTypeLifeLimit configured
- Verify life limit definitions exist
- Ensure user has view permissions

### Incorrect Status

- Verify accumulated value is correct
- Check soft/hard limits on definition
- Look for per-instance overrides

### Cannot Increment

- Ensure tracking record exists
- Check user permissions
- Verify value is valid number

## Related Topics

- [Reman - Component Management](../reman/components.md) - Life transfer during disassembly
- [Part History](part-history.md) - Viewing part tracking history
