# Outside Processing

**Dispatch parts to subcontract vendors and track what's out.**

**Supply** > **Outside Processing** (`/production/outside-processing`)

This is the shipper's board: every work order's outside processing in one
place. The same send-out and receive-back are also on each work order's
**control** page, for one job at a time.

## What it's for

Some operations happen off-site — plating, coating, heat treat, specialist
machining. Outside processing (OSP) covers sending parts out to a vendor for one
of those steps and tracking them until they come back.

## The two lists

| List | Contains |
|------|----------|
| **Ready to ship** | Parts that have reached an outside-processing step and are waiting to go |
| **At vendor** | Shipments currently out, each with **Receive back** |

## Shipping parts out

Work is **grouped by step and vendor across work orders**, so parts heading to
the same vendor for the same operation batch together even when they belong to
different jobs. That's what lets you build one pallet rather than shipping
piecemeal.

1. Open **Ready to ship**
2. Find the step/vendor group you're shipping
3. Click **Send out**

If the step names a **Special process**, the vendor must hold an active
qualification for it, or send-out is refused and nothing moves — see [Step
Configuration](../../admin/processes/steps.md#outside-processing).

The parts move to **At vendor**, and the schedule reflects that they're off-site.

## Getting parts back

When a shipment comes back, use **Receive back** on its row under **At vendor**
(or on the work order's control page). That:

1. Records the shipment as **returned**, with who received it and when
2. Moves its parts to **Awaiting QA**
3. Opens the **return inspection**

The inspection itself is the same one purchased material gets, and if you
leave it, it waits for you in **Supply** > **Incoming Inspection** — both kinds
of arrival share one queue and one inspection runtime. See
[Supply](overview.md#incoming-inspection).

!!! note "Send-out is not an operator's job"
    It belongs to whoever ships — shipping, materials or a lead — which is why
    it lives on this board and the control page rather than in the step player.

!!! note "OSP on the schedule"
    The Gantt board shows outside processing as its own dispatch row, marked
    while parts are at a vendor, so time off-site is visible in the plan rather
    than appearing as an unexplained gap.

## Next Steps

- **[Supply Overview](overview.md)** - The rest of the inbound picture
- **[Schedule (Gantt)](../scheduling/gantt.md)** - How OSP time appears in the plan
