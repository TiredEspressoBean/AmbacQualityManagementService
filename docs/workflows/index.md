# Core Workflows

This section covers the day-to-day operations in uqmes. Each workflow represents a key business process.

## Workflow Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Orders    │────▶│ Work Orders │────▶│   Tracker   │
│  (Customer  │     │  (Process   │     │   (Part     │
│   Request)  │     │   Assigned) │     │  Movement)  │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                    ┌──────────────────────────┤
                    │                          │
                    ▼                          ▼
            ┌─────────────┐            ┌─────────────┐
            │   Quality   │            │  Complete   │
            │   Reports   │            │   (Ship)    │
            │   (Issues)  │            └─────────────┘
            └─────────────┘
                    │
                    ▼
            ┌─────────────┐
            │    CAPA     │
            │  (Improve)  │
            └─────────────┘
```

## Workflow Sections

### [Orders & Parts](orders/creating-orders.md)
Managing customer orders and the parts they contain.

- [Creating Orders](orders/creating-orders.md) - Start new customer orders
- [Adding Parts](orders/adding-parts.md) - Add parts to track
- [Order Status](orders/order-status.md) - Monitor progress
- [Order Documents](orders/order-documents.md) - Attach files

### [Parts Tracking](tracking/tracker-overview.md)
Moving parts through production steps.

- [Tracker Overview](tracking/tracker-overview.md) - The main tracking interface
- [Moving Parts Forward](tracking/moving-parts.md) - Advancing through steps
- [Recording Measurements](tracking/measurements.md) - Capturing inspection data
- [Flagging Issues](tracking/flagging-issues.md) - Reporting problems
- [Part History](tracking/part-history.md) - Viewing audit trail
- [Life Tracking](tracking/life-tracking.md) - Monitoring cycles, hours, and shelf life
- [Lot Tracking](tracking/lot-tracking.md) - Material lot traceability
- [Training Matrix](tracking/training-matrix.md) - Competency coverage and staffing risk
- [Shift Notes](tracking/shift-notes.md) - Handing off to the floor

### [Digital Work Instructions](dwi/overview.md)
How work is actually presented and recorded at the station.

- [DWI Overview](dwi/overview.md) - Substeps, captures and sign-offs
- [Authoring Work Instructions](dwi/authoring.md) - Building them
- [Running Work Instructions](dwi/running.md) - Working a step

### [Scheduling & Planning](scheduling/overview.md)
What runs, when, and whether the shop can take it.

- [Scheduling Overview](scheduling/overview.md) - Calendar, staging, requirements
- [Schedule (Gantt)](scheduling/gantt.md) - The board
- [Releasing Work](scheduling/releasing.md) - Admitting work to the floor
- [Capacity Planning](scheduling/capacity.md) - Can we take this order?
- [Scheduling Setup](scheduling/setup.md) - What the solver believes

### [Supply](supply/overview.md)
Inbound material, outbound shipments and suppliers.

- [Supply Overview](supply/overview.md) - Receiving, holds, returns, supplier quality
- [Shipping](supply/shipping.md) - Getting finished work out
- [Locations & Cycle Counts](supply/locations.md) - Where stock is, and proving it
- [Outside Processing](supply/outside-processing.md) - Subcontract send-out and return
- [Part Approvals](supply/part-approvals.md) - Approving a bought part

### [Approvals & Change Control](approvals/overview.md)
Authorisation, and changing the process itself.

- [Approvals Overview](approvals/overview.md) - How requests are raised, routed and closed
- [Change Control](change-control/overview.md) - PCR, PCO and PCN

### [Work Orders](work-orders/basics.md)
Managing production assignments.

- [Work Order Basics](work-orders/basics.md) - Understanding work orders
- [Assigning Work Orders](work-orders/assigning.md) - Equipment and operators
- [Work Order Progress](work-orders/progress.md) - Tracking completion
- [First Piece Inspection](work-orders/fpi.md) - FPI workflow

### [Quality Control](quality/quality-reports.md)
Handling non-conformances and dispositions.

- [Quality Reports](quality/quality-reports.md) - Creating NCRs
- [Dispositions](quality/dispositions.md) - Making decisions
- [Quarantine](quality/quarantine.md) - Managing held parts
- [Sampling Rules](quality/sampling.md) - Inspection sampling

### [CAPA](capa/overview.md)
Corrective and preventive action management.

- [CAPA Overview](capa/overview.md) - Understanding the process
- [Creating a CAPA](capa/creating.md) - Starting investigations
- [CAPA Tasks](capa/tasks.md) - Managing action items
- [Verification & Closure](capa/verification.md) - Completing CAPAs

### [Documents](documents/library.md)
Document control and management.

- [Document Library](documents/library.md) - Browsing documents
- [Uploading Documents](documents/uploading.md) - Adding new files
- [Document Revisions](documents/revisions.md) - Version control
- [Document Approval](documents/approval.md) - Review workflows

### [Remanufacturing](reman/overview.md)
Taking a used unit in, deciding what it becomes, and putting it back together.

- [Reman Overview](reman/overview.md) - Understanding the reman workflow
- [Receiving Cores](reman/receiving.md) - Logging incoming cores
- [Disassembly](reman/disassembly.md) - Teardown and grading
- [Rebuild](reman/rebuild.md) - Scope, findings and putting it back together
- [Component Management](reman/components.md) - Managing harvested parts

## Role-Based Quick Reference

These are the reference pages. For what your job actually involves, start from
your [role guide](../roles/index.md) instead — it maps the decisions you own to
the page each is made on.

| If you are a... | Start with... |
|-----------------|---------------|
| **Operator** | [Running Work Instructions](dwi/running.md), [Moving Parts](tracking/moving-parts.md) |
| **Shift Lead** | [FPI](work-orders/fpi.md), [Shift Notes](tracking/shift-notes.md), [Dispositions](quality/dispositions.md) |
| **QA Inspector** | [Quality Reports](quality/quality-reports.md), [Dispositions](quality/dispositions.md) |
| **QA Manager** | [CAPA Overview](capa/overview.md), [Verification & Closure](capa/verification.md) |
| **Planner** | [Schedule (Gantt)](scheduling/gantt.md), [Releasing Work](scheduling/releasing.md), [Capacity](scheduling/capacity.md) |
| **Production Manager** | [Work Order Basics](work-orders/basics.md), [Order Status](orders/order-status.md) |
| **Engineering** | [DWI Authoring](dwi/authoring.md), [Change Control](change-control/overview.md) |
| **Purchasing** | [Supply Overview](supply/overview.md), [Part Approvals](supply/part-approvals.md) |
| **Receiving** | [Supply Overview](supply/overview.md), [Locations & Cycle Counts](supply/locations.md) |
| **Shipping** | [Shipping](supply/shipping.md), [Outside Processing](supply/outside-processing.md) |
| **Document Controller** | [Document Library](documents/library.md), [Revisions](documents/revisions.md) |
