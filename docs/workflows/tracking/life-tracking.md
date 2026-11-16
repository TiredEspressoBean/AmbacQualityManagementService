# Life Tracking

Life tracking monitors accumulated usage, cycles, or calendar time against defined limits. A part, tool or fixture at its hard limit can't **start** work at a step that carries the **Life limit** or **Tool life** gate. This is essential for:

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
| **Tooling type** | For a tool, die or fixture: the equipment type it applies to. *None — a part limit* otherwise | Stamping die |

**Calendar-Based Tracking**: For shelf life and expiration tracking. Instead of incrementing a counter, the system calculates elapsed time from a reference date.

**Tooling type**: *"For a tool, die or fixture: every item of this type is
tracked against the limit. Count it in parts, cycles or hours."* See [Tool and
fixture life](#tool-and-fixture-life).

Revising a definition makes a new version. Items and parts move to the current
version's limits, carrying what they had used. The older version's records stay
on file but no longer limit anything.

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

Tracking *is* created for you in four places:
- shelf life on a material lot;
- the transfer from a core to a component harvested from it during reman;
- a core's **reman cycles**, when it's received (see [Reman
  cycles](#reman-cycles));
- each tool or fixture of a life-limited equipment type.

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

!!! important "You cannot type a new accumulated value"
    `accumulated` is not directly editable. An attempt is refused:

    > Accumulated life can't be edited — record usage with increment, or reset
    > it after an overhaul.

    That is deliberate. Life accumulated is evidence about a physical part, and
    the two legitimate ways it changes — **use** and **overhaul** — each leave
    their own trace: an increment adds to the running total, a reset keeps the
    previous value in the reset history with a reason. Allowing the field to be
    overwritten would lose both.

    So a wrong figure is corrected by incrementing the difference, or by a reset
    with the reason recorded — never by editing the number.

## Viewing Life Status

A tool or fixture's **Life** section is on its equipment page (the equipment
editor): *"What it has used against each limit. At the hard limit no work starts
with it until it's reset after refurbishment or an extension is approved."* A
part's detail page has the same section for the part's own limits and its
core's, labelled *&lt;limit&gt; (Core &lt;serial&gt;)*.

Each row reads *&lt;limit&gt; — N used · soft S · hard H &lt;unit&gt;*, with its status
(OK, WARNING or EXPIRED), the last reset (*Last reset &lt;date&gt; by &lt;name&gt; —
&lt;reason&gt;*) and the last extension (*Extended to N, approved by &lt;name&gt; —
&lt;reason&gt;*). Limits from a revised definition's earlier versions are folded
under *Earlier versions of these limits (n)*.

There is no list of everything approaching or past its limit.

## Life limits stop work starting

At a step carrying **Life limit**, a part at its hard limit can't start: work
started inside the limit may finish, and the next step's start catches it. At a
step carrying **Tool life**, no work starts with a tool or fixture at its hard
limit. The refusal says what to do, and notifies whoever clears it (Engineering
and QA Manager for a part; Engineering and Shift Lead for a tool).

## Extending a limit

An extension raises the hard limit for one item or part, leaving the definition
untouched. It takes **two people**. **Request an extension** on the Life row:
*"Asks for this item's hard limit to be raised (now N). Someone with life-limit
authority, other than you, approves it; the limit rises only then. Say why it's
safe to run longer."* It confirms with *Extension requested — waiting for
approval*, and the row reads *Extension to N requested (APR-…) — waiting for
approval.*

The request goes to the inboxes of the groups with life-limit authority, by
default **QA Manager, QA Inspector, Engineering and Tenant Admin**, titled
*&lt;limit&gt;: raise to N*. One of them, not the requester, opens it to the item's
**Extension approval** panel (*"Approve to raise this item's hard limit; reject
to leave it as it is."*) and responds with a signature and password. On approval
the limit rises, with the approver recorded. A rejection needs a comment and
changes nothing. The requester doesn't see Sign or Respond on their own request.

Any staff member can request one. A **Production Manager can't approve** one:
running past a published life is an engineering and quality call. There is no
way to raise a life limit without the approval. Material shelf-life extension
is separate (see [lot tracking](lot-tracking.md)).

## Resetting Life

A reset is what you do after a rebuild, overhaul or refurbishment: **Reset** on
the Life row, *"Puts what it has used back to zero — after refurbishment or
overhaul. Say what was done."* A reason is required; it confirms with *Life
reset*. The source becomes `RESET`, and the previous value is kept in the reset
history with who reset it and why. It needs life-limit authority, by default
**QA Manager, QA Inspector, Engineering and Tenant Admin**.

The previous value being kept is the point: a reset is a claim that the item
was overhauled, and the figure it replaced is what makes that claim checkable.

## Tool and fixture life

Durable tooling (fixtures, dies, molds, jigs) is equipment. Give a life-limit
definition a **Tooling type**, and every item of that equipment type is tracked
against it. Consumable tooling such as inserts and drills is material, with no
life tracking.

The tools a step uses are the ones authored on the step for it, plus any a work
instruction captures. Life is counted by the definition's unit:

| Unit | Counted |
|------|---------|
| **parts** | Each distinct part started with the tool. A part's repeat visit isn't counted again |
| **cycles** | Each run: a load counts once, however many parts it holds |
| **hours** | The run's time, added when it completes |

At the soft limit, the tool's owners get *Tool near its life limit: &lt;tool&gt;*
(*"&lt;limit&gt;: N used, soft limit S, hard limit H. Plan the refurbishment."*),
linking to the tool. At the hard limit, a work instruction refuses to record it
as used, and a step with the **Tool life** gate won't start with it, until it's
reset or an extension is approved. No supervisor can override it.

When a step names several interchangeable tools (dialed in or preferred), work
starts as long as one of them is within life. The start uses the first usable
one, and only that one is counted. The start is refused only when every one of
them is at its limit, and the refusal names them. A tool recorded on the work
itself is refused at its limit. A tool reaching its limit, or being reset or
extended, marks the plan for a re-solve.

## Reman cycles

To limit how many times a unit may be remanufactured, give its core type a
definition whose unit is **remans**. When a core is received, its count starts
at the number of earlier cores with the same serial and type whose teardown
began. Starting the reman adds one. A limit of 3 allows three remans: the fourth
is refused before teardown, waiting on an approved extension. Whether to scrap
the unit or bank the core is a person's decision, made separately.

Correcting a core's serial before its teardown starts recounts its earlier
remans.

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

Life tracking transfers when a harvested component is accepted to inventory:

- Core life records examined
- Records whose definition is linked to the component's part type transfer to the new part
- Maintains life continuity through remanufacturing

## Permissions

| Permission | Allows |
|------------|--------|
| `view_lifetracking` | View life tracking records |
| `add_lifetracking` | Create tracking records, record usage (increment), and request an extension |
| `change_lifetracking` | Update a record's reference date and source |
| `view_lifelimitdefinition` | View definitions |
| `add_lifelimitdefinition` | Create definitions (admin) |
| `change_lifelimitdefinition` | Modify definitions (admin). Also: reset life, and approve someone else's extension request (QA Manager, QA Inspector, Engineering, Tenant Admin) |

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
