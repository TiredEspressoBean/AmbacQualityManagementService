# Equipment

Manage production equipment, machines, and measurement instruments.

!!! example "Demo Equipment"
    In demo mode, these equipment items are configured:

    - **Flow Test Stand #1** (FTS-001): Primary injector flow testing, calibration current
    - **Flow Test Stand #2** (FTS-002): Secondary flow testing station
    - **Ultrasonic Cleaner UC-100**: Parts cleaning, 40 kHz frequency
    - **Torque Wrench TW-25**: Assembly torquing, **calibration overdue** (demonstrates alert)
    - **Coordinate Measuring Machine CMM-001**: Dimensional inspection, Zeiss model
    - **Spray Pattern Analyzer SPA-01**: Visual spray pattern verification

## What is Equipment?

Equipment records represent:

- **Production machines** - CNC, presses, assembly stations
- **Measurement instruments** - CMMs, calipers, gauges
- **Tools** - Fixtures, molds, dies
- **Work centers** - Grouped equipment

## Creating Equipment

1. Navigate to **Admin** > **Data Management** > **Equipment**
2. Click **New Equipments**
3. Fill in details:

| Field | Description | Required |
|-------|-------------|----------|
| **Equipment Name** | Equipment identifier | Yes |
| **Equipment Type** | Category | No |
| **Serial Number** | Manufacturer serial | No |
| **Manufacturer** | Who made it | No |
| **Model Number** | Model | No |
| **Location** | Where it is — a location record, from the picker | No |
| **Status** | Operational status | No |
| **Schedulable resource** | Whether the scheduler may plan work onto it | No |
| **Batch capacity** | How many jobs or parts it handles at once. `1` — the default — is an ordinary one-at-a-time machine. Above 1 makes it a batch resource, and then **batch mode** decides how it behaves. | No |
| **Batch mode** | Only meaningful above a capacity of 1. **Concurrent** — that many independent jobs run side by side, like a bank of wash tanks. **Cycle** — one load at a time of up to that many parts, like a furnace or oven. | No |
| **Runs unattended** | Whether it runs lights-out between staffed shifts. Left unset it inherits the facility default; set explicitly it overrides that for this machine. | No |
| **Notes** | Free text | No |

!!! note "Batch capacity above 1 changes how work is planned onto it"
    Concurrent and cycle are not interchangeable. A bank of stations running four
    separate jobs at once is concurrent; an oven taking one load of up to forty
    parts is cycle. Getting it the wrong way round gives a schedule that cannot be
    worked — either four ovens that do not exist, or one wash tank where there are
    four.

Submit with **Create Equipment**.

!!! tip "Schedulable resource"
    Only equipment marked schedulable is planned onto by the scheduler. A gauge
    or hand tool is usually not schedulable; a test stand or press is.

4. Save

## Equipment Types

Define equipment categories:

| Type | Examples |
|------|----------|
| **Flow Test Stand** | Injector flow testers (FTS-001, FTS-002) |
| **Ultrasonic Cleaner** | Parts cleaning systems (UC-100) |
| **CMM** | Coordinate measuring machines (CMM-001) |
| **Torque Tools** | Torque wrenches, drivers (TW-25) |
| **Spray Analyzer** | Spray pattern verification (SPA-01) |
| **Assembly Station** | Manual assembly, automation |
| **Gauge** | Go/no-go, thread gauges |
| **Caliper** | Digital, dial, vernier |

### Creating Equipment Types

1. Navigate to **Admin** > **Data Management** > **Equipment Types**
2. Click **New Equipments**
3. Enter type name and description
4. Set calibration requirements
5. Save

## Equipment Fields

### Identification

| Field | Description |
|-------|-------------|
| **Name** | Your identifier |
| **Equipment Type** | Category |
| **Serial Number** | Manufacturer's number |
| **Manufacturer** | Equipment maker |
| **Model Number** | Model |

There is no asset-number field.

### Location

**Location** is a **location record**, chosen from the same picker used on
receiving and moves — not free text. Locations nest, so the building/area/station
breakdown comes from the tree rather than from separate fields.

The location's page shows a **Machines** card listing the equipment placed there,
so the relationship reads from both ends. See [Locations & Cycle
Counts](../../workflows/supply/locations.md).

!!! note "Equipment import needs the location to exist"
    Unlike a stock import, which creates any location its sheet names, an
    equipment import must name one that is already there. Create it first — from
    any picker, or in Data Management.

### Status

| Status | Meaning |
|--------|---------|
| **In Service** | Available for use (the default) |
| **Out of Service** | Not available |
| **In Calibration** | Out for calibration |
| **In Maintenance** | Under repair or maintenance |
| **Retired** | No longer in service |

### Scheduling

| Field | Description |
|-------|-------------|
| **Schedulable resource** | Whether the scheduler plans work onto it |
| **Runs unattended** | Can run without an operator present |
| **Batch mode** and **batch capacity** | Whether it processes a batch, and how large |
| **Operating shifts** | Which shifts it runs |
| **Work centers** | Which work centers it belongs to |

## Calibration Tracking

### Calibration Settings

Configure per equipment:

| Field | Description |
|-------|-------------|
| **Requires calibration** | Set on the **equipment type**, not the individual item |
| **Default calibration interval** | Days, set on the equipment type |
| **Calibration interval (days)** | Per-item override of the type's interval |

Dates are not fields on the equipment. Each calibration is a **calibration
record** carrying its own **calibration date**, **due date**, result,
certificate number, standards used, whether it was found in tolerance, and any
adjustments made. The next due date comes from the most recent record.

### Calibration Status

| Status | Meaning | Color |
|--------|---------|-------|
| **Current** | Calibration valid | Green |
| **Due Soon** | Within 30 days | Yellow |
| **Overdue** | Past due date | Red |
| **Not Required** | No calibration needed | Gray |

!!! warning "Demo: Overdue Calibration Alert"
    In demo mode, **Torque Wrench TW-25** shows as overdue (last calibrated 200 days ago with 180-day interval). Production Manager Jennifer Walsh sees this in her dashboard alerts, demonstrating how the system flags equipment needing attention before use.

### Recording Calibration

1. Open equipment
2. Go to **Calibration** tab
3. Click **Record Calibration**
4. Enter:
   - Calibration date
   - Performed by
   - Results (pass/fail)
   - Certificate number
   - Attachments
5. Save

Next due date updates automatically.

## Equipment Usage Tracking

Track equipment utilization:

### Per Part Transition
When parts move through steps:
- Equipment can be recorded
- Builds utilization history
- Links parts to equipment

### Usage Reports
- Parts produced per equipment
- Utilization percentage
- Downtime tracking

## Equipment Capabilities

Define what equipment can do:

### Linked Processes
- Which process steps use this equipment
- Routing decisions
- Capacity planning

### Specifications
- Accuracy/precision
- Capacity (size, weight)
- Capabilities

## Equipment Documents

Attach related documents:

- Manuals
- Maintenance procedures
- Calibration certificates
- Specifications

1. Go to **Documents** tab
2. Upload or link documents

## Equipment Maintenance

Track maintenance (basic tracking):

- Scheduled maintenance dates
- Maintenance history
- Downtime records

For full maintenance management, consider specialized CMMS integration.

## Equipment Dashboard

If calibration dashboard is configured:

- Equipment due for calibration
- Overdue equipment
- Calibration schedule
- Status overview

Navigate to **Quality** > **Calibrations**.

## Permissions

| Permission | Allows |
|------------|--------|
| `view_equipments` | View equipment |
| `add_equipments` | Create equipment |
| `change_equipments` | Edit equipment |
| `delete_equipments` | Remove equipment |
| `add_calibrationrecord` | Record a calibration |

## Next Steps

- [Equipment Types](equipment.md) - Configure categories
- [Measurement Definitions](../processes/measurements.md) - Link to measurements
- [Calibration Dashboard](../../workflows/tracking/measurements.md) - View status
