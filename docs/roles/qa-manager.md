# QA Manager Guide

This guide is for Quality Assurance Managers who oversee quality operations, manage CAPAs, approve dispositions, and analyze quality data.

## Your Role

As a QA Manager, you:

- Oversee quality operations
- Approve dispositions for non-conforming parts
- Manage CAPA investigations and closure
- Review and approve documents
- Analyze quality data and trends
- Configure quality processes

## Getting Started

### First-Time Setup

1. Log in and review the system
2. Configure notification preferences
3. Review pending approvals

### Your Main Pages

| Page | Location | Purpose |
|------|----------|---------|
| **Quality Dashboard** | Quality > Dashboard | KPIs and overview |
| **CAPAs** | Quality > CAPAs | Corrective actions |
| **Quality Reports** | Quality > Quality Reports | All NCRs |
| **Inbox** | Personal > Inbox | Pending approvals |
| **Analytics** | Tools > Analytics | Trends and analysis |
| **Dispositions** | Production > Dispositions | Quarantine management |

## Daily Workflow

### 1. Check Dashboard

Start with the Quality Dashboard:

1. Review KPI cards (Open CAPAs, NCRs, Pending)
2. Check defect trends
3. Identify priority items
4. Note any critical issues

### 2. Process Approvals

1. Navigate to **Inbox**
2. Review pending approvals:
   - Disposition approvals
   - Document approvals
   - CAPA closures
3. Take action on each item

### 3. Review Quality Reports

1. Check new quality reports
2. Review severity assignments
3. Ensure appropriate disposition
4. Identify CAPA candidates

### 4. Manage CAPAs

1. Review open CAPAs
2. Check task progress
3. Follow up on overdue items
4. Verify effectiveness for closure

## Approving Dispositions

### Reviewing Disposition Requests

1. Navigate to **Inbox** or **Dispositions**
2. Open disposition request
3. Review:
   - Original NCR and issue
   - Proposed disposition
   - Justification
   - Affected parts
4. Make decision

### Approval Decision

| Decision | When to Use |
|----------|-------------|
| **Approve** | Disposition is appropriate |
| **Reject** | Need different disposition |
| **Request Info** | Need more details |

### Signing Approval

1. Click **Approve** or **Reject**
2. Add comments (especially for reject)
3. Enter password to sign
4. Submit

### High-Value Dispositions

For expensive scrap or customer deviations:
- May require additional approvers
- Document carefully
- Consider management notification

## Managing CAPAs

### CAPA Overview

1. Navigate to **Quality** > **CAPAs**
2. See all CAPAs by status
3. Filter by priority, owner, status

### Creating CAPAs

For significant issues:

1. Click **+ New CAPA** or create from NCR
2. Fill in:
   - Problem description
   - Priority
   - Owner assignment
   - Due dates
3. Assign team members
4. Submit

### Monitoring Progress

For each open CAPA:

1. Review task completion
2. Check for overdue tasks
3. Follow up with owners
4. Provide guidance as needed

### CAPA Verification

Before closure:

1. Review all corrective actions
2. Verify effectiveness evidence
3. Confirm preventive measures
4. Check documentation complete

### Closing CAPAs

1. Review verification data
2. Click **Request Closure**
3. Approve closure (or route to approver)
4. CAPA closes with audit trail

## Document Approvals

### Reviewing Documents

1. Navigate to **Inbox** or **Documents**
2. Open document pending approval
3. Review document content
4. Check revision notes
5. Verify accuracy

### Approval Actions

| Action | When |
|--------|------|
| **Approve** | Document is acceptable |
| **Reject** | Issues found, return to author |
| **Comment** | Need clarification |

### Electronic Signature

1. Click **Approve**
2. Review signature meaning
3. Enter password
4. Submit

## Quality Analytics

### Dashboard Review

Regular review of:

- **FPY Trend**: First pass yield over time
- **Defect Pareto**: Top defect types
- **NCR Aging**: Time to close NCRs
- **CAPA Metrics**: Open count, age, effectiveness

### Identifying Trends

Look for:
- Increasing defect rates
- Recurring error types
- Problem suppliers
- Process issues

### Taking Action

When trends indicate problems:

1. Create CAPA for systemic issues
2. Adjust sampling rules
3. Initiate process changes
4. Brief management

## SPC Review

### Capability Analysis

1. Navigate to **Analytics** > **SPC**
2. Review control charts for key characteristics
3. Check Cp/Cpk values
4. Identify out-of-control conditions

### Responding to Signals

When control charts show issues:

1. Investigate assignable cause
2. Document in CAPA if systemic
3. Adjust process if needed
4. Update control limits after improvement

## Audits and Compliance

### Preparing for Audits

1. Review audit scope
2. Generate compliance reports
3. Verify CAPA closure
4. Check document control

### Reports for Auditors

- CAPA summary report
- NCR trending
- Audit trail exports
- Training records

## Configuration Responsibilities

### Sampling Rules

Review and adjust:
- AQL levels per product
- Skip-lot qualifications
- Supplier quality levels

### Error Types

Maintain defect categories:
- Add new types as needed
- Retire unused types
- Ensure clear definitions

### Approval Templates

Configure workflows for:
- Document approvals
- Disposition approvals
- CAPA closure

## Managing Your Team

### Inspector Oversight

- Review inspection quality
- Provide training guidance
- Address capability gaps

### Workload Balance

- Monitor inspection queue
- Assign appropriately
- Avoid bottlenecks

## Weekly/Monthly Tasks

### Weekly

- [ ] Review quality dashboard
- [ ] Check CAPA status
- [ ] Follow up overdue items
- [ ] Review new NCRs

### Monthly

- [ ] Analyze quality trends
- [ ] Management quality report
- [ ] SPC capability review
- [ ] Sampling rule effectiveness

## Quick Reference

| Task | Location |
|------|----------|
| Approve disposition | Inbox → Disposition → Approve |
| Create CAPA | Quality > CAPAs → + New |
| Close CAPA | CAPA detail → Request Closure |
| Approve document | Inbox → Document → Approve |
| View analytics | Tools > Analytics |

## Related Documentation

- [CAPA Overview](../workflows/capa/overview.md)
- [Dispositions](../workflows/quality/dispositions.md)
- [Document Approval](../workflows/documents/approval.md)
- [Dashboard](../analysis/dashboard.md)
- [SPC Charts](../analysis/spc.md)
- [Compliance Reports](../compliance/reports.md)
