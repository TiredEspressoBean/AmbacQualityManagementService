# Supply

The **Supply** section covers everything inbound: material you buy, parts you
send out to subcontract vendors, and the suppliers behind both.

!!! info "Where to find it"
    **Supply** in the sidebar. It's collapsed by default — click the section
    header to expand it.

## The surfaces

| Page | Covers |
|------|--------|
| **Incoming Inspection** | The queue of everything awaiting inbound inspection |
| **[Outside Processing](outside-processing.md)** | Parts out at subcontract vendors |
| **Materials** | Material lots, by lifecycle status |
| **Receiving Inspection Plans** | What inspection to perform on receipt |
| **Supplier Quality** | Supplier scorecards |
| **Approved Suppliers** | Supplier qualifications |
| **[Part Approvals](part-approvals.md)** | PPAP / FAI approvals per part type and supplier |

## Materials

The **Materials** page is the material lot hub, segmented by where each lot is
in its life:

| Segment | Meaning |
|---------|---------|
| **On order** | Expected, not yet arrived |
| **Awaiting inspection** | Received, not yet inspected |
| **On hand** | Inspected and available |
| **Held** | Quarantined or otherwise not usable |

Actions: **Expect** a lot you know is coming, **Receive** one that has arrived,
and **Inspect** one that's waiting. Lots import and export as CSV or Excel.

See [Material Lot Tracking](../tracking/lot-tracking.md) for the underlying
concepts.

## Incoming Inspection

**Everything awaiting inbound inspection — purchased material and parts back
from a subcontract vendor — in one queue.**

This is deliberately one queue rather than two. Purchased material and returning
subcontract work both need the same thing on arrival, so **Inspect** opens the
same runtime for both. Filter by source or status to narrow it.

!!! tip "QA Inspectors get this on their Home page"
    If you're a QA Inspector, incoming work already appears on your Home queue,
    segmented into Receiving, OSP returns, and In-process. See the
    [QA Inspector Guide](../../roles/qa-inspector.md).

## Receiving Inspection Plans

A receiving inspection plan defines what to check when a lot arrives. Plans are
built from substeps, the same way work instructions are — see
[Authoring Work Instructions](../dwi/authoring.md).

Create with **New Plan**, then **Configure** to build the plan's substeps.

## Supplier Quality

**Receiving-inspection scorecards** per supplier:

| Metric | Shows |
|--------|-------|
| **Lots received** | Volume |
| **Accepted** / **Rejected** | Counts |
| **Reject rate** | Quality performance |
| **CoC compliance** | Whether certificates of conformance arrived |
| **On-time delivery** | Delivery performance |
| **Open SCARs** | Outstanding corrective actions |

Suppliers also show their qualification state — an unqualified supplier is
flagged here as **Not qualified**.

## Approved Suppliers

Supplier qualifications, with expiry. The Home page surfaces qualifications that
are expiring or expired, since an expired qualification affects what you're
allowed to receive.

## Next Steps

- **[Outside Processing](outside-processing.md)** - Sending work to vendors
- **[Part Approvals](part-approvals.md)** - PPAP / FAI
