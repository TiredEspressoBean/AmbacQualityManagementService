# Core Workflows

This section covers the day-to-day operations in Ambac Tracker. Each workflow represents a key business process.

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

## Role-Based Quick Reference

| If you are a... | Start with... |
|-----------------|---------------|
| **Production Operator** | [Tracker Overview](tracking/tracker-overview.md), [Moving Parts](tracking/moving-parts.md) |
| **QA Inspector** | [Quality Reports](quality/quality-reports.md), [Measurements](tracking/measurements.md) |
| **QA Manager** | [CAPA Overview](capa/overview.md), [Dispositions](quality/dispositions.md) |
| **Production Planner** | [Work Orders](work-orders/basics.md), [Order Status](orders/order-status.md) |
| **Document Controller** | [Document Library](documents/library.md), [Revisions](documents/revisions.md) |
