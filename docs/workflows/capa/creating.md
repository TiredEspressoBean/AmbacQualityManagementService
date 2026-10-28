# Creating a CAPA

This guide covers how to initiate and set up a CAPA investigation.

## Starting a CAPA

### From Quality Report

1. Open the quality report
2. Click **Create CAPA**
3. CAPA is automatically linked to the NCR
4. Complete the CAPA form

### From CAPA List

1. Navigate to **Quality** > **CAPAs**
2. Click **New CAPAs**
3. Complete the form
4. Link related records manually

### From a pattern you spotted

There is **no suggestion engine** — nothing proposes a CAPA to you. Recurring
error types, several NCRs against one part type and worsening trends are all
visible on the dashboard and in [Defect Analysis](../../analysis/defects.md),
but noticing the pattern and deciding it warrants a CAPA is yours.

Once you have narrowed **Defect Records** to the pattern, its **Create CAPA**
opens the form with a drafted problem statement and the failed reports already
linked — see [Defect Analysis](../../analysis/defects.md). Otherwise raise it
from the CAPA list and link the reports it answers.

## CAPA Form

### Basic Information

| Field | Description | Required |
|-------|-------------|----------|
| **Type** | Corrective, Preventive, Customer Complaint, Internal Audit, Supplier | Yes |
| **Severity** | Critical, Major, Minor | Yes |
| **Problem Statement** | Clear description of the issue | Yes |
| **Due Date** | Target closure date | No |
| **Assigned To** | Responsible person | No |
| **Allow Self-Verification** | Lets the initiator or assignee verify their own work. Only someone with `verify_capa` (by default QA Manager and Tenant Admin) can set it; for anyone else it is disabled — *"Only QA (who can verify CAPAs) can turn this on."* See [Verification](verification.md) | No |

### Problem Definition

The problem is described in two free-text fields, not a structured
questionnaire. There is no discovery date, discovery method, scope, impact or
recurrence-likelihood field — if those matter, write them into the problem
statement.

| Field | Description |
|-------|-------------|
| **Problem Statement** | Clear description of the issue. Say what, where, when and how much here. |
| **Immediate Action** | Containment already taken, in one field. See [Containment Actions](#containment-actions) below. |

### Context Links

Everything else the CAPA knows about the problem is a link to a record that
already exists. All of these are optional:

| Field | Description |
|-------|-------------|
| **Part** | A representative part, if one part shows the problem |
| **Step** | The process step where the issue occurred |
| **Work Order** | The work order involved |
| **Supplier** | Set when the CAPA is raised as a SCAR from receiving; not on this form |
| **Quality Reports** | One or more NCRs this CAPA answers |
| **Dispositions** | Quarantine dispositions this CAPA answers |

## Deciding *not* to raise one

Not every nonconformance becomes a CAPA, and declining is a recorded decision
rather than silence. From a quality report you can record the outcome as:

| Decision | Means |
|----------|-------|
| **Not required** | This does not warrant corrective action |
| **Deferred** | It might, but not now |

Both demand a **written reason**, and that is the point: ISO 9001 **10.2.1**
asks you to evaluate whether action is needed, and an evaluation nobody wrote
down is indistinguishable from never having looked.

!!! tip "The reason is what an auditor reads"
    A list of reports with no CAPA and no explanation is the finding. A list
    with *"single occurrence, contained, supplier notified"* against each one is
    a quality system working.

## Linking Records

Connect related items:

### Quality Reports
1. On the create form, under **Linked Quality Reports**, search and select them

The CAPA's **Overview** tab lists them under **Linked Quality Reports**.

### Parts
1. In the **Part** field, pick a single representative part
2. There is no affected-parts list — if several parts are involved, link their
   quality reports and name the population in the problem statement

### Documents
1. On the **Documents** tab, upload evidence:
   - Photos
   - Test data
   - Customer communications
   - Procedures

An existing document is linked to the CAPA from the document itself: **Edit** >
**Link To**, choose **CAPA** and pick it.

## Assigning the Team

### CAPA Owner
Primary responsible person:

- Drives the investigation
- Ensures timely progress
- Reports status

### Team Members

!!! note "A CAPA has one assignee, not a team roster"
    There is no team-member list with roles. A CAPA carries a single
    **assigned_to** owner.

    To involve other people, create **CAPA tasks** and assign them
    individually — the set of task assignees is what functions as the team.
    See [CAPA Tasks](tasks.md).

## Containment Actions

Containment is recorded as a single **Immediate Action** field on the CAPA —
describe what was done to contain the problem while the root cause is
investigated. It is not a list of separately-tracked action items.

If containment needs tracked, assignable work, raise **CAPA tasks** for it.

Typical containment to describe:

- Quarantine suspect material
- Stop production
- Hold shipment
- 100% inspection
- Customer notification

## Setting Timeline

Establish milestones:

| Phase | Typical Timeline |
|-------|------------------|
| Containment | 24-48 hours |
| Root Cause | 1-2 weeks |
| Action Plan | 1 week |
| Implementation | 2-4 weeks |
| Verification | 2-4 weeks |
| Closure | As scheduled |

Due dates drive:

- Dashboard alerts
- Notifications
- Escalations

## Submitting the CAPA

There is no draft state and no separate activation step. **A CAPA is Open the
moment you save it** — `Open` is the default status, and the only statuses are
Open, In Progress, Pending Verification, Closed and Cancelled. If you are not
ready to commit to it, do not create it yet; there is nowhere to park a
half-finished one.

A **Critical** or **Major** CAPA additionally raises an approval request on
creation (its severity's template, else CAPA_APPROVAL). Until it is approved
only containment can be worked; corrective and preventive tasks and the
root-cause analysis wait. It is not the closure gate — see
[Verification & Closure](verification.md).

## Notifications

These notifications ship with a new CAPA:

| Recipient | Notification |
|-----------|--------------|
| The assignee | `capa.assigned` — in-app and email, on creation and on reassignment |
| QA Managers (Major/Critical only) | Approval request for the CAPA's plan |

Nothing else for a Minor CAPA. Beyond that approval request, no new-CAPA alert
goes to the QA Manager at creation; the QA Manager's CAPA rule is `capa.ready_for_verification`, which
fires later, when the tasks and RCA are complete. Your administrator can add
further rules.

## Permissions

| Permission | Allows | Held by |
|------------|--------|---------|
| `initiate_capa` | **Raise** a CAPA | QA Inspector, QA Manager, Shift Lead, Production Manager, Purchasing, Receiving, Tenant Admin |
| `add_capa` | The underlying create right — **not sufficient on its own** | Every staff role |
| `change_capa` | Edit a CAPA, including changing the assignee | Every staff role |

*Held by* is the groups that hold it when an organisation is created. Group permissions can be changed, so check your own in [Roles & Groups](../../admin/users/roles.md).

!!! important "Raising one takes more than the create permission"
    Creating a CAPA checks **both** `add_capa` and `initiate_capa`. Every staff
    role holds the first; only the roles above hold the second.

    So an **Operator** or an **Engineer** can open, read and help fill in a CAPA
    somebody else raised — and cannot raise one. That is deliberate: a CAPA
    commits the shop to root cause analysis, effectiveness verification and an
    audit trail, so starting one is a supervisory act. If you find something
    that warrants it, raise the quality report and ask a lead or QA to promote
    it.

## Next Steps

- [CAPA Tasks](tasks.md) - Creating action items
- [Verification & Closure](verification.md) - Completing CAPAs
- [CAPA Overview](overview.md) - Process reference
