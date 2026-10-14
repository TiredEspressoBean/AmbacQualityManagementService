# Role Guides

uqmes serves different roles in your organization. Find your role below for a tailored guide covering your specific workflows and responsibilities.

!!! info "Roles compose"
    These are **groups you can be put in**, and holding more than one is normal
    rather than exceptional — a QA Inspector who is also a Shift Lead gets both
    sets of permissions, added together. Nothing here is exclusive.

    Every guide below corresponds to a real group, one for one.

!!! note "Looking for Scheduler?"
    There isn't a separate one. Planning and scheduling are **one role** here —
    the same surface, behind the same gates. Sequencing on the board is part of
    planning, not a separate trade. See [Running the
    board](planner.md#running-the-board).

## On the floor

### [Operator](operator.md)
Production floor workers moving parts through manufacturing steps. Learn to work a step's substeps, record measurements, and flag quality issues.

### [Shift Lead](shift-lead.md)
Operator plus supervisor authority: FPI sign-off, manual decision points, training-gate overrides, shift notes, and the board for your shift.

## Quality

### [QA Inspector](qa-inspector.md)
Quality inspection, measurements, and NCR creation. Learn to perform inspections, create quality reports, and record dispositions.

### [QA Manager](qa-manager.md)
Quality oversight, CAPA management, approvals, and analytics. Learn to approve dispositions, manage CAPAs, and analyze quality trends.

## Planning & production

### [Production Manager](production-manager.md)
Order and work order management, and production oversight. Learn to create orders, manage work orders, and monitor progress.

### [Planner](planner.md)
Release work onto the floor, promise dates against real capacity, decide what to buy, build or recover, run the schedule, and decide a core's exit after teardown.

### [Engineering](engineering.md)
Define what the shop builds and how: part types, processes, routings, work instructions, specs, life limits and cycle times.

## Supply

### [Purchasing](purchasing.md)
Supplier relationships, qualification, expected deliveries and sourcing facts. Purchase orders stay in your ERP.

### [Receiving](receiving.md)
The dock — expected deliveries, receiving, holds, returns and cycle counts.

### [Shipping](shipping.md)
Getting finished work out, with the right paperwork, on time.

## Governance

### [Document Controller](document-controller.md)
Document management, revisions, and approvals. Learn to upload documents, manage revisions, and route for approval.

### [Auditor](auditor.md)
Read everything, change nothing. A seat for internal and external audits, with no write permission of any kind.

### [Administrator](administrator.md)
System configuration, users, and setup. Learn to manage users, configure processes, and maintain system settings.

## External

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

### Every role has a Home surface

All 13 staff groups have their own Home arrangement, each led by a launchpad for
the role: **Operator**, **QA Inspector**, **QA Manager**, **Production Manager**,
**Shift Lead**, **Engineering**, **Document Controller**, **Purchasing**,
**Planner**, **Receiving**, **Shipping**, **Auditor** and **Tenant Admin**.

What you see on Home is the set of cards defined for *your* role, in that role's
order — which is why two people with different groups see different Homes.

### Late deliveries

**Purchasing**, **Planner**, **Receiving** and **Tenant Admin** get a **Late
deliveries** card. A plain Production Manager does not — the card is allowed to
their permission set but is not part of the Production Manager Home order, and
Home only shows what your role's order lists. Each row names the item, quantity, supplier and PO/line, with
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

**Purchasing** also gets **Supplier qualifications expiring**, alongside its
launchpad and the late-deliveries card.

---

## Role Comparison

### What every staff role can already do

The table below only shows what **tells the roles apart**. Before reading it,
know that every internal role — Operator and Shipping included — shares a common
base and can already:

- view orders, work orders, parts and their histories
- run steps, record measurements and complete work
- raise a quality report (NCR)
- upload documents
- create orders and work orders
- see the whole tenant's data

!!! warning "The shared base is broad"
    Several of those are wider than the job title suggests — an Operator can
    create an order. If your facility needs a tighter floor role, build a custom
    group rather than assuming the preset is already narrow. See
    [Permissions](../admin/users/permissions.md).

**[Customer](customer.md) is the exception** and shares none of it: no tenant-wide
visibility, no write access to production, and row filtering that limits them to
their own orders.

### What tells the roles apart

| Capability | Op | Lead | QA&nbsp;Insp | QA&nbsp;Mgr | Prod&nbsp;Mgr | Planner | Eng | Purch | Recv | Ship | Doc&nbsp;Ctl | Audit | Admin |
|------------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Sign off an FPI | – | Yes | Yes | Yes | Yes | – | – | – | – | – | – | – | Yes |
| Resolve a manual decision point | – | Yes | Yes | Yes | Yes | – | – | – | – | – | – | – | Yes |
| Override the training gate | – | Yes | – | Yes | Yes | – | – | – | – | – | – | – | Yes |
| Write training records | – | Yes | – | Yes | Yes | – | Yes | – | – | – | Yes | – | Yes |
| Close a disposition | – | Yes | Yes | Yes | Yes | – | – | – | – | – | – | – | Yes |
| **Approve** a disposition | – | – | – | Yes | – | – | – | – | – | – | – | – | Yes |
| Initiate a CAPA | – | Yes | Yes | Yes | Yes | – | – | Yes | Yes | – | – | – | Yes |
| **Approve** a CAPA | – | – | – | Yes | – | – | – | – | – | – | – | – | Yes |
| Classify documents | – | – | – | Yes | – | – | – | – | – | – | Yes | – | Yes |
| Author processes & routings | – | – | – | Yes | Yes | – | Yes | – | – | – | Yes | – | Yes |
| Cancel a work order | – | – | – | – | Yes | – | – | – | – | – | – | – | Yes |
| Run / commit a solve | – | – | – | – | Yes | Yes | – | – | – | – | – | – | Yes |
| Work the board by hand | – | Yes | – | Yes | Yes | Yes | – | – | – | – | – | – | Yes |
| **Approve** a supplier qualification | – | – | – | Yes | – | – | – | – | – | – | – | – | Yes |
| Manage users | – | – | – | – | – | – | – | – | – | – | – | – | Yes |

!!! note "Approve is always narrower than do"
    Notice the pattern: many roles can *raise* a nonconformance, a CAPA or a
    supplier qualification, and only QA Manager can **approve** one. That
    separation is the point — it is what an auditor checks, and it is why
    Receiving can start a supplier problem but not settle it.

**Auditor holds no write permission at all**, by design. An empty row across the
Audit column is the feature.

## Finding Your Role

Not sure which guide applies to you? Check with your administrator or look at your group membership in your profile.

Your effective permissions come from the groups you're assigned to. You may have capabilities from multiple roles.
