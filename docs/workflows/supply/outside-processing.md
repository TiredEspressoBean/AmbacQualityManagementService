# Outside Processing

**Dispatch parts to subcontract vendors and track what's out.**

**Supply** > **Outside Processing**

## What it's for

Some operations happen off-site — plating, coating, heat treat, specialist
machining. Outside processing (OSP) covers sending parts out to a vendor for one
of those steps and tracking them until they come back.

## The two lists

| List | Contains |
|------|----------|
| **Ready to ship** | Parts that have reached an outside-processing step and are waiting to go |
| **At vendor** | Shipments currently out |

## Shipping parts out

Work is **grouped by step and vendor across work orders**, so parts heading to
the same vendor for the same operation batch together even when they belong to
different jobs. That's what lets you build one pallet rather than shipping
piecemeal.

1. Open **Ready to ship**
2. Find the step/vendor group you're shipping
3. Click **Send out**

The parts move to **At vendor**, and the schedule reflects that they're off-site.

## Getting parts back

Returning parts are **not** received here. They go into the same inbound queue
as purchased material:

**Supply** > **Incoming Inspection**

Both purchased material and returning subcontract work need inspection on
arrival, so they share one queue and one inspection runtime. See
[Supply](overview.md#incoming-inspection).

!!! note "OSP on the schedule"
    The Gantt board shows outside processing as its own dispatch row, marked
    while parts are at a vendor, so time off-site is visible in the plan rather
    than appearing as an unexplained gap.

## Next Steps

- **[Supply Overview](overview.md)** - The rest of the inbound picture
- **[Schedule (Gantt)](../scheduling/gantt.md)** - How OSP time appears in the plan
