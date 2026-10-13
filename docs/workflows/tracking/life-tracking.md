# Life Tracking

!!! note "No dedicated screen yet"
    Life tracking is implemented in the backend — life limit definitions, usage
    accumulation, and shelf life — and is available via the API and the data
    editors. A dedicated life tracking screen is planned for a future release.

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
- Multiple definitions can apply to one part type

!!! note "Planned Feature"
    The **required** flag is recorded but nothing reads it. Marking a definition
    required does not cause a tracking record to be created for a new part, and
    nothing refuses a part that is missing one. Until it is wired up, create the
    tracking record yourself for any part you need tracked.

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

Nothing creates a life tracking record when a part is made — not even for a
definition marked required. Create the record against the part yourself, and
when you do:

1. Pick the definition that applies to the part type
2. Enter the initial accumulated value
3. Set the reference date for calendar-based items
4. Select the data source

There are two places tracking *is* created for you, and only two: shelf life on
a material lot, and the transfer from a core to a component harvested from it
during reman.

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

!!! note "Planned Feature"
    There is no life tracking screen anywhere in the application yet — not on
    part details, and not as a list of parts approaching or past their limits.
    The records, the status calculation and the warning and expired states all
    exist on the server; nothing surfaces them. Until a screen is built, read
    life status through the API.

## Limit Overrides

!!! note "API only"
    An override extends the limits for one specific part — engineering approval
    to run past the definition's figure — and leaves the definition itself
    untouched. There is no button for it. It is an API action on the life
    tracking record, taking the new limit values, a justification reason and the
    approving user.

## Resetting Life

!!! note "API only"
    A reset is what you do after a rebuild or overhaul: accumulated value back
    to zero, source set to `RESET`, previous value kept in the reset history,
    reason recorded. Like an override, it exists only as an API action on the
    life tracking record — there is no control for it in the interface.

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
