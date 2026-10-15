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

### From Dashboard Alert

1. Dashboard may suggest CAPA for:
   - Recurring error types
   - Multiple NCRs on same part type
   - Trend alerts
2. Click the suggestion to create

## CAPA Form

### Basic Information

| Field | Description | Required |
|-------|-------------|----------|
| **Type** | Corrective, Preventive, Customer Complaint, Internal Audit, Supplier | Yes |
| **Severity** | Critical, Major, Minor | Yes |
| **Problem Statement** | Clear description of the issue | Yes |
| **Due Date** | Target closure date | No |
| **Assigned To** | Responsible person | No |

### Problem Definition (D2)

The problem is described in two free-text fields, not a structured
questionnaire. There is no discovery date, discovery method, scope, impact or
recurrence-likelihood field — if those matter, write them into the problem
statement.

| Field | Description |
|-------|-------------|
| **Problem Statement** | Clear description of the issue. Say what, where, when and how much here. |
| **Immediate Action** | Containment already taken, in one field. See [Containment Actions](#containment-actions-d3) below. |

### Context Links

Everything else the CAPA knows about the problem is a link to a record that
already exists. All of these are optional:

| Field | Description |
|-------|-------------|
| **Part** | A representative part, if one part shows the problem |
| **Step** | The process step where the issue occurred |
| **Work Order** | The work order involved |
| **Supplier** | The supplier the CAPA is raised against (a SCAR) |
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
1. In the **Related NCRs** section
2. Click **Add**
3. Search for quality reports
4. Select to link

### Parts
1. In the **Part** field, pick a single representative part
2. There is no affected-parts list — if several parts are involved, link their
   quality reports and name the population in the problem statement

### Documents
1. In the **Documents** section
2. Upload or link evidence:
   - Photos
   - Test data
   - Customer communications
   - Procedures

## Assigning the Team (D1)

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

## Containment Actions (D3)

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
creation, if your tenant has a CAPA_APPROVAL template configured. That approval
does not block the investigation, and it is not the closure gate — see
[Verification & Closure](verification.md).

## Notifications

One notification ships with a new CAPA:

| Recipient | Notification |
|-----------|--------------|
| The assignee | `capa.assigned` — in-app and email, on creation and on reassignment |

There is nothing else. No new-CAPA alert goes to the QA Manager at creation; the
QA Manager's CAPA rule is `capa.ready_for_verification`, which fires later, when
the tasks and RCA are complete. Your administrator can add further rules.

## Permissions

| Permission | Allows |
|------------|--------|
| `add_capa` | Create CAPAs |
| `change_capa` | Edit CAPAs, including changing the assignee |

## Next Steps

- [CAPA Tasks](tasks.md) - Creating action items
- [Verification & Closure](verification.md) - Completing CAPAs
- [CAPA Overview](overview.md) - 8D process reference
