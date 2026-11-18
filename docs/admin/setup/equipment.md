# Equipment

Manage production equipment, machines, and measurement instruments.

## What is Equipment?

Equipment records represent:

- **Production machines** - CNC, presses, assembly stations
- **Measurement instruments** - CMMs, calipers, gauges, torque tools

!!! note "Tooling for scheduling, equipment for life"
    Shared tooling has its own editor — **Data Management** > **Tooling**
    (`/editor/tooling`) — with a kind (Fixture, Cutting tool, Die / mold, NC
    program, Other), a quantity, and the steps that require it. The scheduler
    holds back operations that need a tool while every one of it is in use.

    A tool, die or fixture whose **life** is tracked is also recorded here, as
    equipment: one record per physical item, of an equipment type that has a
    life limit. Its **Life** section shows what it has used against each limit,
    with **Reset** and **Request an extension**. See [Tool and fixture
    life](../../workflows/tracking/life-tracking.md#tool-and-fixture-life).

    To make the scheduler count those items instead of a typed quantity, set
    the tooling entry's **Tracked as equipment** to their equipment type:
    *"For tooling recorded item by item (each die, each fixture), pick its
    equipment type: the scheduler then counts those in service and within their
    life."* The form then shows *Available now: &lt;n&gt; in service and within
    life*, and **Quantity** isn't used. An item that goes out of service, or
    reaches its life limit, stops counting at once, and the tooling list shows the
    entry's quantity as *&lt;n&gt; (tracked)*. Left as *Not tracked — use the
    quantity*, the entry keeps its typed quantity.

!!! note "Equipment does not belong to a work centre"
    A **work centre** groups **steps**, not machines — it is a property of the
    routing. An individual machine is placed at a **location**, and the
    scheduler reaches it through the step. Looking for a work-centre field on
    the equipment record will not find one.

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
| **Schedulable resource** | Whether the scheduler may plan work onto it. Turning it on reveals the scheduling fields below, from **Operating shifts** down to **Batch mode** | No |
| **Requires calibration** | **Follow the equipment type**, **Yes — this item is calibrated** or **No — not for this item**. *Overrides the type's setting for this one item.* Always shown | No |
| **Calibration interval (days)** | Blank uses the equipment type's default interval. Always shown | No |
| **Operating shifts** | *The shifts this machine runs. None ticked follows the plant's shift calendar.* Shown only once shifts exist | No |
| **Batch capacity** | How many jobs or parts it handles at once. `1` — the default — is an ordinary one-at-a-time machine. Above 1 makes it a batch resource, and then **batch mode** decides how it behaves. | No |
| **Batch mode** | Only meaningful above a capacity of 1. **Concurrent** — that many independent jobs run side by side, like a bank of wash tanks. **Cycle** — one load at a time of up to that many parts, like a furnace or oven. | No |
| **Lights-out (unattended running)** | Whether it keeps running between staffed shifts: **Use facility default**, **Lights-out (runs 24/7)**, or **Attended (on shift only)**. The default follows the shop-wide scheduling setting; the other two override it for this machine. | No |
| **Notes** | Free text | No |

!!! note "Batch capacity above 1 changes how work is planned onto it"
    Concurrent and cycle are not interchangeable. A bank of stations running four
    separate jobs at once is concurrent; an oven taking one load of up to forty
    parts is cycle. Getting it the wrong way round gives a schedule that cannot be
    worked — either four ovens that do not exist, or one wash tank where there are
    four.

4. Click **Create Equipment**

!!! tip "Schedulable resource"
    Only equipment marked schedulable is planned onto by the scheduler. A gauge
    or hand tool is usually not schedulable; a test stand or press is.

## Equipment Types

An equipment type is a category you define — *CMM*, *Torque tools*, *Ultrasonic
cleaner*. None ship; you create the ones your shop has.

The type is where **calibration policy** lives, which is the reason to bother
with it: say once that torque tools need calibrating every 180 days, and every
torque wrench inherits it.

### Creating Equipment Types

1. Navigate to **Admin** > **Data Management** > **Equipment Types**
2. Click **New Equipment Types**
3. Fill in:

| Field | Description |
|-------|-------------|
| **Name** | The category |
| **Description** | Free text |
| **Requires Calibration** | Whether items of this type are calibrated at all. Off by default |
| **Default Calibration Interval (days)** | How often, unless an item overrides it |
| **Portable** | Recorded, but nothing reads it |
| **Track Downtime** | Off for a type that is not a production resource — handhelds, torque tools. Downtime cannot be recorded against equipment of that type; uqmes refuses the event. Equipment with no type is treated as tracked |

4. Click **Create Equipment Type**

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
| **Lights-out (unattended running)** | Can run without an operator present |
| **Batch mode** and **batch capacity** | Whether it processes a batch, and how large |
| **Operating shifts** | Which shifts it runs. None ticked follows the plant's shift calendar |

All but **Schedulable resource** are shown only while it is on.

## Calibration Tracking

### Calibration Settings

Configure per equipment:

| Field | Description |
|-------|-------------|
| **Requires calibration** | Set on the **equipment type**. Each item inherits it — **Follow the equipment type** — and can override it either way with **Yes — this item is calibrated** or **No — not for this item** |
| **Default calibration interval** | Days, set on the equipment type |
| **Calibration interval (days)** | Per-item override of the type's interval; blank uses the type's |

!!! tip "Set the rule on the type, the exception on the item"
    Both calibration settings work the same way: the type carries the policy for
    its category, and an individual machine overrides it only where it genuinely
    differs. Leaving the item's override unset is what keeps a change to the
    type's interval reaching everything of that type.

Dates are not fields on the equipment. Each calibration is a **calibration
record** carrying its own **calibration date**, **due date**, result,
certificate number, standards used, whether it was found in tolerance, and any
adjustments made. The next due date comes from the most recent record.

### Calibration Status

A calibration record's status is derived, not chosen:

| Status | Meaning |
|--------|---------|
| **Failed** | The calibration result was Fail — this wins over any date |
| **Overdue** | Past its due date |
| **Due soon** | Due within 30 days |
| **Current** | Everything else |

!!! note "Failed is checked before the dates"
    A gauge whose last calibration failed reads **Failed** even if that
    calibration's due date is months away. A failure is a statement about the
    instrument, not a deadline, so it cannot be aged out of.

A gauge's calibrations carry across its versions, and the status shown is its
latest record's. When two records share a calibration date, the one entered
later counts, so an after-repair Pass recorded the same day as a Fail returns
the gauge to service. A gauge whose latest calibration failed is listed as
**Failed**, not Overdue, here and on the Calibration Due report.

Overdue and Failed both stop use. A gauge in either state, or one that was never
calibrated, can't record a reading: the pickers grey it out with the reason. A
production machine past its calibration due date can't start work at a step with
the **Machine in service** gate (*"&lt;machine&gt; is past its calibration — it
can't run work until it is calibrated."*), and QA Manager is notified along with
the Shift Lead and Production Manager. A failed calibration takes the machine out
of service, so it's refused as out of service.

### Recording Calibration

A calibration is its own record, written from **Quality** > **Calibrations**, not
from the machine:

1. Go to **Quality** > **Calibrations**
2. Click **Record New Calibration** (or, from **View All Calibration Records**,
   **New Calibration Records**)
3. Pick the equipment and fill in:

    | Field | Notes |
    |-------|-------|
    | **Calibration date** and **due date** | Both are entered; the due date is not calculated for you |
    | **Result** | **Pass**, **Fail**, or **Limited / restricted use** |
    | **Calibration type** | Scheduled, Initial, After repair, After adjustment, or Verification check |
    | **Performed by** / **External lab** | Free text — who did it, and the lab if it went out |
    | **Certificate number** and **standards used** | The traceability chain |
    | **As-Found Status** | Whether it was *in* tolerance when it arrived |
    | **Adjustments made** | Whether it was adjusted |

4. Click **Create Calibration Record**

The machine's own form carries a **Calibration** card showing its latest records
read-only, with a link through to record a new one. The next due date comes from
the most recent record.

!!! important "Say honestly whether it was found in tolerance"
    That field is not bookkeeping. A gauge found **out** of tolerance means
    everything it measured since its last good calibration is suspect, and the
    record's **exposure list** is what turns that into a list to assess: the
    inspection records it was used on, and the visits where an operator picked it for
    a reading in the work instructions. Recording a pass because the gauge passed *after* adjustment
    destroys the only evidence that there was anything to go back for.

    See [Measurements](../../workflows/tracking/measurements.md).

### Correcting a calibration record

Open the record from **Quality** > **Calibrations** > **Records** and edit it. When
the change is to its **outcome, dates, or who or what it covers** (the result,
the calibration or due date, the equipment, who performed it), the form asks for a
**Reason for the correction** and won't save without one. The reason is kept
beside the field it changed.

Only the gauge's latest calibration puts it in or out of service. Correcting the
**result** of the latest record re-applies it: a Fail corrected to Pass returns
the gauge to service, and the reverse takes it out. Correcting an older record
changes nothing.

## What equipment was used

A step can include an **Equipment + roles** capture, which records the machine
actually used against that part's record as the operator works. That is the only
place equipment use is captured, and it is per substep.

What it gives you is **traceability** — which machine touched which part — not a
utilisation figure. See [Authoring Work
Instructions](../../workflows/dwi/authoring.md).

## Changeovers

The equipment form carries a **Changeovers** table: the minutes it takes to
reconfigure this machine when it switches from one step to another. Switching
back the other way is its own row, because it is often not the same number.

The scheduler uses these to decide the order work runs in — a sequence that
avoids changeovers finishes sooner than the same jobs in a different order.

## Equipment Documents

!!! note "There is no Documents tab on equipment"
    A document is attached from the document's own **Link To** field rather than
    from the machine. Manuals, maintenance procedures and calibration
    certificates all go on that way. See [Uploading
    Documents](../../workflows/documents/uploading.md).

    A calibration **record** takes documents the same way, which is where a
    certificate PDF usually belongs.

## Calibration overview

Equipment due and overdue for calibration is listed under
**Quality** > **Calibrations**.

## Downtime

A machine being down is recorded as a **downtime event** against the equipment,
the work centre, or both. Record one from a work order's **Report…** dialog, or
from the operator's **Machine problem**, which opens the same dialog: choose
**Downtime (equipment / resource)**, pick the machine and a category, and give a
reason. The event starts when you record it and ends when someone resolves it
from the exceptions list. The categories are:

**Planned maintenance** · **Unplanned / breakdown** · **Changeover / setup** ·
**Calibration** · **No work available** · **No operator available** · **Waiting
for material** · **Quality issue** · **Other**

Open events show on the work order control pages and on the operator's home.

While a machine's downtime is open, no work starts on it at a step with the
**Machine in service** gate: *"&lt;machine&gt; is down (&lt;reason&gt;) since
&lt;date&gt; &lt;time&gt; — it can't run work until the downtime is resolved."* The
Start Work machine picker (at a step with a choice of machines) and the work queue
treat it as unavailable too. The
Shift Lead and Production Manager are notified of the refused start. Resolving
the event frees the machine.
Equipment whose type has **Track Downtime** off is not offered in the dialog,
and uqmes refuses an event against it from anywhere else.

**Recorded it wrong?** The wrong machine, category or times: **Correct…** on the
event's row in **WO Control Center** > **Exceptions** (turn off **Open only** to
find a resolved one). A resolved row names who resolved it (*… · &lt;reporter&gt; ·
resolved by &lt;name&gt;*), and **Correct…** shows both (*Reported by … · resolved by
…*). Change what was wrong, give a **reason**, and each change is kept on the
event with it. The downtime totals below follow the corrected times.

### Where downtime adds up

The **Downtime** card on **Analytics** totals the period's events: hours lost
and event counts **by cause** and **by machine**, largest first. An event still
open counts up to now, and an event with no machine is grouped under its work
centre.

The percentage beside each machine is its share of the period's **calendar**
time spent down — not of its scheduled time. It is lost time, not OEE: there is
no availability or OEE figure.

!!! note "No scheduled maintenance"
    uqmes records **calibration** due dates, not maintenance ones. There is no
    PM schedule, no service-interval field, and no specification fields for
    accuracy or capacity. A planned maintenance downtime event records that it
    happened; nothing tells you it was coming.

## Permissions

| Permission | Allows |
|------------|--------|
| `view_equipments` | View equipment |
| `add_equipments` | Create equipment |
| `change_equipments` | Edit equipment |
| `delete_equipments` | Remove equipment |
| `view_equipmenttype` | View equipment types |
| `add_equipmenttype` / `change_equipmenttype` | Create and edit equipment types — held by Tenant Admin, QA Manager, Production Manager and Document Controller when an organisation is created |
| `delete_equipmenttype` | Remove equipment types — the same four groups |
| `add_calibrationrecord` | Record a calibration |

An equipment type carries calibration policy for every item of that type, so it
is manager-tier; other staff roles can add and edit the equipment itself.

## Next Steps

- [Measurement Definitions](../processes/measurements.md) - Link to measurements
- [Calibration overview](#calibration-overview) - Calibration status at a glance
- [Recording Measurements](../../workflows/tracking/measurements.md) - Which gauges can record a reading
