# Equipment

Manage production equipment, machines, and measurement instruments.

## What is Equipment?

Equipment records represent:

- **Production machines** - CNC, presses, assembly stations
- **Measurement instruments** - CMMs, calipers, gauges
- **Tools** - Fixtures, molds, dies
- **Work centers** - Grouped equipment

## Creating Equipment

1. Navigate to **Data Management** > **Equipment**
2. Click **+ New Equipment**
3. Fill in details:

| Field | Description | Required |
|-------|-------------|----------|
| **Name** | Equipment identifier | Yes |
| **Equipment Type** | Category | Yes |
| **Serial Number** | Manufacturer serial | No |
| **Location** | Physical location | No |
| **Status** | Active, Maintenance, Retired | Yes |

4. Save

## Equipment Types

Define equipment categories:

| Type | Examples |
|------|----------|
| **CNC Machine** | Lathes, mills, routers |
| **Press** | Punch press, hydraulic press |
| **Assembly Station** | Manual assembly, automation |
| **CMM** | Coordinate measuring machines |
| **Gauge** | Go/no-go, thread gauges |
| **Caliper** | Digital, dial, vernier |
| **Test Equipment** | Functional testers |

### Creating Equipment Types

1. Navigate to **Data Management** > **Equipment Types**
2. Click **+ New**
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
| **Asset Number** | Your asset tag |
| **Manufacturer** | Equipment maker |
| **Model** | Model number |

### Location

| Field | Description |
|-------|-------------|
| **Building** | Facility |
| **Area** | Department/zone |
| **Station** | Specific location |

### Status

| Status | Meaning |
|--------|---------|
| **Active** | In service, available |
| **Maintenance** | Under repair/maintenance |
| **Calibration** | Out for calibration |
| **Retired** | No longer in service |

## Calibration Tracking

### Calibration Settings

Configure per equipment:

| Field | Description |
|-------|-------------|
| **Requires Calibration** | Yes/No |
| **Calibration Interval** | Days between calibrations |
| **Last Calibration** | Date of last cal |
| **Next Due** | Calculated due date |
| **Calibration Procedure** | Reference document |

### Calibration Status

| Status | Meaning | Color |
|--------|---------|-------|
| **Current** | Calibration valid | Green |
| **Due Soon** | Within 30 days | Yellow |
| **Overdue** | Past due date | Red |
| **Not Required** | No calibration needed | Gray |

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
| `view_equipment` | View equipment |
| `add_equipment` | Create equipment |
| `change_equipment` | Edit equipment |
| `delete_equipment` | Remove equipment |
| `record_calibration` | Record calibrations |

## Best Practices

1. **Unique identifiers** - Clear naming convention
2. **Track calibration** - Maintain compliance
3. **Record usage** - Build utilization data
4. **Attach documents** - Keep certs accessible
5. **Update status** - Reflect current state

## Next Steps

- [Equipment Types](equipment.md) - Configure categories
- [Measurement Definitions](../processes/measurements.md) - Link to measurements
- [Calibration Dashboard](../../workflows/tracking/measurements.md) - View status
