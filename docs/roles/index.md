# Role Guides

uqmes serves different roles in your organization. Find your role below for a tailored guide covering your specific workflows and responsibilities.

## Available Role Guides

### [Operator](operator.md)
Production floor workers moving parts through manufacturing steps. Learn to work a step's substeps, record measurements, and flag quality issues.

### [QA Inspector](qa-inspector.md)
Quality inspection, measurements, and NCR creation. Learn to perform inspections, create quality reports, and recommend dispositions.

### [QA Manager](qa-manager.md)
Quality oversight, CAPA management, approvals, and analytics. Learn to approve dispositions, manage CAPAs, and analyze quality trends.

### [Production Manager](production-manager.md)
Order and work order management, and production oversight. Learn to create orders, manage work orders, and monitor progress.

### [Planner](planner.md)
Planning. Release work onto the floor, promise dates against real capacity, decide what to buy, build or recover, and decide a core's exit after teardown. Running the board day to day is [Scheduler](scheduler.md).

### [Scheduler](scheduler.md)
Runs the board day to day: solve, dispatch, and fix what didn't schedule.

### [Receiving](receiving.md)
The dock — expected deliveries, receiving, holds, returns and cycle counts.

### [Shipping](shipping.md)
Getting finished work out, with the right paperwork, on time.

### [Document Controller](document-controller.md)
Document management, revisions, and approvals. Learn to upload documents, manage revisions, and route for approval.

### [Administrator](administrator.md)
System configuration, users, and setup. Learn to manage users, configure processes, and maintain system settings.

### [Customer Portal](customer.md)
External customers viewing order status. Learn to track orders, view progress, and access shared documents.

---

## Your Home Page Follows Your Role

uqmes decides what to show on **Home** from the groups you belong to. An
Operator, a QA Inspector, and a Production Manager each land on a different
surface built for their work — not a shared dashboard.

If you belong to more than one group, a **Switch landing** picker appears at the
top of Home so you can choose which one to see.

Supervisors can also preview the floor landings of the people they oversee:

| Your role | Landings you can preview |
|-----------|--------------------------|
| Tenant Admin | Operator, QA Inspector |
| QA Manager | QA Inspector |
| Production Manager | Operator |
| Shift Lead | Operator |

This is why instructions in one role guide may not match what you see — check
which landing you are on before assuming a page is missing.

### Late deliveries

**Purchasing**, **Production Manager** and **Tenant Admin** get a **Late
deliveries** card. Each row names the item, quantity, supplier and PO/line, with
a **Nd late** / **due today** / **due in Nd** badge — and, more usefully, which
work orders it is *holding up*.

**The card is absent when nothing is late.** An empty space here means good news,
not a missing feature.

!!! note "\"Holding up\" is read from the production BOM"
    It means *this work needs that item*, not *this particular lot was earmarked
    for it*. Treat it as the answer to "who is waiting on this", not as an
    allocation.

Each row also names the supplier's **deliveries contact** and their email, so
chasing it doesn't start with looking someone up. See [Outside
contacts](../admin/setup/companies.md#outside-contacts).

**Purchasing** also gets **Supplier qualifications expiring**. Before this,
Purchasing had no Home blocks of its own.

---

## Role Comparison

| Capability | Operator | Inspector | QA Manager | Production | Doc Controller | Admin |
|------------|:--------:|:---------:|:----------:|:----------:|:--------------:|:-----:|
| View orders | Yes | Yes | Yes | Yes | Yes | Yes |
| Complete steps | Yes | Yes | Yes | Yes | - | Yes |
| Record measurements | Yes | Yes | Yes | - | - | Yes |
| Create NCRs | - | Yes | Yes | - | - | Yes |
| Approve dispositions | - | - | Yes | - | - | Yes |
| Manage CAPAs | - | - | Yes | - | - | Yes |
| Upload documents | - | Yes | Yes | Yes | Yes | Yes |
| Approve documents | - | - | Yes | - | Yes | Yes |
| Create orders | - | - | - | Yes | - | Yes |
| Manage users | - | - | - | - | - | Yes |
| Configure system | - | - | - | - | - | Yes |

## Finding Your Role

Not sure which guide applies to you? Check with your administrator or look at your group membership in your profile.

Your effective permissions come from the groups you're assigned to. You may have capabilities from multiple roles.
