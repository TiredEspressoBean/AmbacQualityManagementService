# QA Manager Guide

This guide is for Quality Assurance Managers who oversee quality operations, manage CAPAs, approve dispositions, and analyze quality data in uqmes.

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
| **Home** | Home | Your role's landing page — what needs you today |
| **Quality Dashboard** | Quality > Dashboard | CAPA counts, your approvals, your CAPA tasks |
| **CAPAs** | Quality > CAPAs | Corrective actions |
| **Quality Reports** | Quality > Quality Reports | All NCRs |
| **Inbox** | Personal > Inbox | Pending approvals and CAPA tasks |
| **Approvals** | Approvals > Overview | All pending approval requests |
| **Analytics** | Analytics | Quality KPIs — yield, scrap, rework — and top defects |
| **NCR Analysis** | From Analytics or Home, or `/quality/ncrs` | NCR trend, aging, disposition breakdown |
| **Dispositions** | Quality > Dispositions | Quarantine management |

## Daily Workflow

### 1. Check Dashboard

1. **Home** shows what needs you today
2. **Quality** > **Dashboard** has the CAPA picture: open, overdue, pending
   verification and closed, with your approvals and your CAPA tasks
3. **Analytics** has yield, scrap and rework against target, and the top
   defects — the place to spot a trend
4. Note any critical issues

### 2. Process Approvals

1. Navigate to **Personal > Inbox**
2. Review what is actually assigned to you — typically **document releases** and
   **CAPA approvals** (the authorisation a Major or Critical CAPA needs *before*
   work begins), plus process changes if your facility routes them here
3. Take action on each item

Two things that look like they should be in this queue and are not:
**dispositions**, which are recorded directly rather than requested — see below
— and **CAPA closure**, which follows from verification and has no approval step
of its own.

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

## Dispositions

There is no queue of disposition *requests* waiting on you. Whoever is
authorized records the decision directly, and recording it **is** the
authorized act. Your involvement takes one of two forms:

- **You record it yourself** — **Quality** > **Dispositions**, or the
  *Exceptions on this WO* list on the work order's control page.
- **You co-sign someone else's.** An inspector without `approve_disposition`
  presses *Update Disposition* and the editor opens **Authorize disposition
  decision**. You supply your email, signature and password on their screen.
  The record carries **your** name as the authority, with them as the caller.

Before either, review the originating NCR, the justification, and the affected
parts.

### The three decisions

Every approval in uqmes offers the same three, whatever the subject:

| Decision | When to Use |
|----------|-------------|
| **Approved** | It is acceptable as submitted |
| **Rejected** | It is not — say why in the comments |
| **Delegated** | Pass it to another eligible approver |

There is **no "Request more information"** decision. If you need more before you
can decide, leave the request open and ask outside it, or reject with comments
saying what is missing.

### Signing Approval

1. Click **Submit Response**
2. Choose a **Decision** — Approved, Rejected, or Delegated
3. Add comments (especially when rejecting)
4. Sign if the approval template requires it
5. Submit the response

### Expensive or customer-facing dispositions

uqmes holds no costs, so nothing routes a disposition differently by its value.
Where your procedure wants more than one signature on an expensive scrap or a
deviation the customer must accept, that is your procedure: record the customer's
approval on the disposition, and document the rest in its justification.

## Bypass requests

A held part's owner can ask for a one-time bypass of a quality block. Requests
arrive in your inbox under **Bypass requests**: the block, the part and step,
the reason, and who asked. **Approve** or **Refuse**; a refusal needs a reason.
Nobody decides their own. See [Requesting a
bypass](../workflows/tracking/moving-parts.md#requesting-a-bypass).

## Managing CAPAs

### CAPA Overview

1. Navigate to **Quality** > **CAPAs**
2. See all CAPAs by status
3. Filter by priority, owner, status

### Creating CAPAs

For significant issues:

1. Click **New CAPAs** or create from NCR
2. Fill in:
   - Problem statement
   - **Severity** — Critical, Major or Minor
   - Owner assignment
   - Due date
3. Assign team members
4. Submit

A **Critical** or **Major** CAPA raises its approval as it is created — work on
it waits for that approval. See [Creating CAPAs](../workflows/capa/creating.md).

### Monitoring Progress

For each open CAPA:

1. Review task completion
2. Check for overdue tasks
3. Follow up with owners
4. Provide guidance as needed

### Approving root causes

On a CAPA's **RCA** tab, **Approve** an unverified or disputed RCA once you
accept its root cause. You cannot approve one you conducted, unless the CAPA
allows self-verification. Then you must write at least ten characters of
justification.

Nothing gets to Pending Verification, and no effectiveness check is accepted,
until the root cause is approved. See [Approving the root
cause](../workflows/capa/overview.md#approving-the-root-cause).

### CAPA Verification

Before closure:

1. Review all corrective actions
2. Verify effectiveness evidence
3. Confirm preventive measures
4. Check documentation complete

### Closing CAPAs

1. Open the CAPA's **Verification** tab
2. Record the effectiveness check against the verification criteria
3. Choose **Confirmed effective** — this closes the CAPA in the same action

There is no separate closure request or closure approval. The gate is
`verify_capa`; if you don't hold it, an authorised colleague can co-sign inline
with their email and password and the closure is attributed to them.

!!! warning "By default you cannot verify a CAPA you initiated or were assigned"
    Effectiveness is judged by someone other than the person who did the work.
    If you are the CAPA's **initiator or its assignee** — and assigning one to
    yourself is routine — the server refuses:

    > Self-verification is not permitted for this CAPA

    **There is a deliberate exception, set per CAPA.** `allow_self_verification`
    is a toggle on the CAPA itself, off by default, meant for minor issues or
    where nobody independent exists. With it on, you may verify your own — but
    you must supply **at least ten characters of justification**, and that text
    is kept as the record of why it was acceptable.

    Otherwise a colleague holding `verify_capa` co-signs, and the closure is
    attributed to them.

    This is the commonest way the step fails, and it fails at the end, after the
    evidence is assembled. Check who the CAPA is assigned to before you gather
    it.

!!! warning "Closed is the end of the line"
    A closed CAPA cannot be reopened. If the check shows the action did *not*
    work, record **Not effective** instead. That does three things rather than
    one: the CAPA returns to **In Progress**, its root-cause analysis is flagged
    for review — on the grounds that an ineffective action usually means the
    cause was wrong — and a follow-up **corrective task is raised automatically,
    due in 30 days**.

    So "not effective" is not a dead end or a failure to record; it is the
    restart, and it leaves someone holding a dated task.

## Document Approvals

### Reviewing Documents

1. Navigate to **Personal > Inbox** or **Documents**
2. Open document pending approval
3. Review document content
4. Check revision notes
5. Verify accuracy

### Approval Actions

The same three decisions as everywhere else — **Approved**, **Rejected**,
**Delegated**. Comments travel with whichever you choose; they are not a
decision of their own.

### Electronic Signature

1. Click **Submit Response** and choose **Approved**
2. Review the signature meaning
3. Sign as the template requires
4. Submit

## Quality Analytics

### Dashboard Review

Regular review of:

- **FPY trend** and **top defects** — on Analytics
- **NCR aging** and trend — on NCR Analysis
- **CAPA counts** — on the Quality dashboard

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

1. Navigate to **Analytics**, then select **SPC**
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

- CAPA report and NCR report — PDFs from the record itself
- Training records report
- The audit log, read on screen — it has no export
- NCR trend and aging, from NCR Analysis

## Configuration Responsibilities

### Sampling Rules

Review and adjust:
- AQL and inspection level per rule set
- Which suppliers get their own rule set
- Whether a fallback (tightened) set is wired in

A supplier's Z1.4 severity — normal, tightened, reduced — switches itself on lot
history; you do not set it. See [Sampling Rules](../admin/setup/sampling-rules.md).

### Error Types

Maintain defect categories:
- Add new types as needed
- Retire unused types
- Ensure clear definitions

### Approval Templates

A template decides, per approval *type*, who is assigned, whether self-approval
is allowed, how long it has and when it escalates. The types that are raised are
**Document Release**, the CAPA approvals — **Critical CAPA** and **Major CAPA**
by severity, with the general **CAPA Approval** as their fallback — and the
process-change set (PCR, PCO, PCN).

**Dispositions and CAPA closure are not among them** — a disposition is recorded
and co-signed in place, and closure follows verification. Neither has a template
to configure.

This is also where you change *who* approves what: the assignment comes from the
template, not from anyone's role. See [Approval
Templates](../admin/setup/approval-templates.md).

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
| Record a disposition decision | Quality > Dispositions → open it → set the type |
| Co-sign someone else's | On *their* screen — they press Update Disposition, you supply email, signature and password |
| Create CAPA | Quality > CAPAs → **New CAPAs** |
| Close CAPA | CAPA detail → Verification → **Confirmed effective** |
| Approve document | Inbox → Document → **Submit Response** → Approved |
| View analytics | Analytics |

## Related Documentation

- [CAPA Overview](../workflows/capa/overview.md)
- [Dispositions](../workflows/quality/dispositions.md)
- [Document Approval](../workflows/documents/approval.md)
- [Dashboard](../analysis/dashboard.md)
- [SPC Charts](../analysis/spc.md)
- [Compliance Reports](../compliance/reports.md)
