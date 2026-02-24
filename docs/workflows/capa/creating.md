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
2. Click **+ New CAPA**
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

| Field | Description |
|-------|-------------|
| **Problem Statement** | Clear description of the issue |
| **Discovery Date** | When problem was found |
| **Discovery Method** | How it was found (inspection, customer, audit) |
| **Products Affected** | Part types, orders involved |
| **Scope** | Quantity, date range, locations |
| **Impact** | Customer, cost, safety implications |

### Initial Assessment

| Field | Description |
|-------|-------------|
| **Severity** | Impact assessment |
| **Likelihood of Recurrence** | Based on initial review |
| **Initial Root Cause Hypothesis** | First theory |

## Linking Records

Connect related items:

### Quality Reports
1. In the **Related NCRs** section
2. Click **Add**
3. Search for quality reports
4. Select to link

### Parts
1. In the **Affected Parts** section
2. Link specific parts or part types
3. Parts show CAPA association

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
Assign additional team members:

1. Click **Add Team Member**
2. Select user
3. Assign role (Investigator, SME, Approver)

### Stakeholders
Notify stakeholders without assigning work:

- Management
- Customer contact
- Affected departments

## Containment Actions (D3)

Document immediate actions:

1. Go to **Containment** section
2. Click **Add Action**
3. Describe the action:
   - What was done
   - When
   - Who did it
4. Mark complete when done

Common containment actions:

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

After completing initial setup:

1. Review all sections
2. Click **Submit** or **Activate**
3. CAPA moves to Open status
4. Team is notified
5. Investigation begins

## Draft CAPAs

Save as draft to:

- Gather more information
- Consult with team
- Complete in multiple sessions

Drafts don't trigger notifications or appear on dashboards as active.

## CAPA Templates

For recurring CAPA types, templates pre-fill:

- Standard sections
- Common containment actions
- Default assignments
- Typical timelines

Ask your administrator about available templates.

## Notifications

On CAPA creation:

| Recipient | Notification |
|-----------|--------------|
| Owner | Assignment notification |
| Team members | Team assignment |
| Quality manager | New CAPA alert |
| Stakeholders | Awareness notification |

## Permissions

| Permission | Allows |
|------------|--------|
| `add_capa` | Create CAPAs |
| `change_capa` | Edit CAPAs |
| `assign_capa` | Assign team members |

## Best Practices

1. **Clear problem statement** - Specific, measurable
2. **Right priority** - Drives response urgency
3. **Appropriate team** - Include needed expertise
4. **Realistic timeline** - Achievable dates
5. **Link everything** - Connect related records

## Next Steps

- [CAPA Tasks](tasks.md) - Creating action items
- [Verification & Closure](verification.md) - Completing CAPAs
- [CAPA Overview](overview.md) - 8D process reference
