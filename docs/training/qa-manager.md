# QA Manager Training Guide

**Duration:** 4-6 hours
**Prerequisites:** QA Inspector training recommended
**Goal:** Learn to oversee quality operations, approve dispositions, manage CAPAs, and analyze quality data

!!! note "Training Data Setup"
    Exercises in this guide reference sample data (e.g., "DISP-TRAIN-001", "CAPA-TRAIN-COMPLETE"). Your administrator should set up this training data before you begin. If specific records aren't available, create your own test records following the exercise patterns.

---

## Module 1: QA Manager Role Overview

### Learning Objectives

By the end of this module, you will:

- [ ] Understand QA Manager responsibilities
- [ ] Navigate management-level screens
- [ ] Understand approval authority

### 1.1 Your Role

As a QA Manager, you:

- Approve dispositions for non-conforming material
- Manage CAPA investigations
- Review and approve documents
- Analyze quality trends
- Configure quality processes
- Oversee inspection team

You have authority to make disposition decisions that affect product, cost, and customer relationships.

---

### 1.2 Your Main Pages

| Page | Location | Purpose |
|------|----------|---------|
| **Quality Dashboard** | Quality > Dashboard | KPIs and overview |
| **CAPAs** | Quality > CAPAs | Corrective actions |
| **Quality Reports** | Quality > Quality Reports | All NCRs |
| **Inbox** | Personal > Inbox | Pending approvals |
| **Analytics** | Tools > Analytics | Trends |

**Exercise 1.1:** Dashboard Review

1. Navigate to Quality Dashboard
2. Review each KPI card
3. Note current open CAPAs, NCRs
4. Identify any critical items

---

### 1.3 Approval Authority

**You approve:**

| Item | Threshold |
|------|-----------|
| Dispositions | All (especially scrap over $X) |
| Customer deviations | All |
| Document revisions | Per template |
| CAPA closures | All |

---

### Knowledge Check: Module 1

1. What are the main approval responsibilities of a QA Manager?
2. Where do you find items waiting for your approval?
3. What does the Quality Dashboard show?

---

## Module 2: Approving Dispositions

### Learning Objectives

By the end of this module, you will:

- [ ] Review disposition requests effectively
- [ ] Make informed approval decisions
- [ ] Use electronic signature properly

### 2.1 The Approval Queue

**Finding pending approvals:**

1. Navigate to **Inbox**
2. Look for "Disposition Approval" items
3. Or go to **Quality Reports** and filter by "Pending Approval"

**Exercise 2.1:** Review Approval Queue

1. Go to Inbox
2. Count disposition requests pending
3. Identify the oldest pending item
4. Note priority indicators

---

### 2.2 Reviewing a Disposition Request

**Before approving, review:**

1. **Original issue:** What was wrong?
2. **Evidence:** Photos, measurements, data
3. **Affected parts:** How many? Which ones?
4. **Proposed disposition:** What's recommended?
5. **Justification:** Why this disposition?
6. **Cost impact:** Value of parts, rework cost
7. **Customer impact:** Will it affect delivery?

**Exercise 2.2:** Review Practice

1. Open disposition request "DISP-TRAIN-001"
2. Review all sections listed above
3. Note any questions you would ask

---

### 2.3 Disposition Decisions

| Decision | When to Use |
|----------|-------------|
| **Approve** | Disposition is appropriate and justified |
| **Reject** | Need different disposition or more info |
| **Request More Info** | Missing evidence or justification |

**Rejection requires:** Clear comments explaining why and what's needed.

---

### 2.4 Electronic Signature

**Signing a disposition:**

1. Review complete
2. Click **Approve** (or **Reject**)
3. Add comments (required for reject)
4. Enter your password
5. System records: your name, timestamp, decision

!!! warning "Signature Meaning"
    Your signature means you've reviewed the information and agree with the disposition. This is a quality record.

**Exercise 2.3:** Approve a Disposition

1. Open disposition "DISP-TRAIN-002"
2. Review the request
3. Click **Approve**
4. Enter your password
5. Observe the audit trail update

---

### 2.5 High-Value Decisions

**Extra scrutiny for:**

- Scrap value over threshold
- Customer deviation requests
- Safety-related issues
- Recurring problems

These may require:

- Additional approvers
- Documentation
- Management notification
- Customer communication

---

### Knowledge Check: Module 2

1. What should you review before approving a disposition?
2. When would you reject a disposition request?
3. What does your electronic signature mean?

---

## Module 3: CAPA Management

### Learning Objectives

By the end of this module, you will:

- [ ] Create and configure CAPAs
- [ ] Monitor CAPA progress
- [ ] Verify effectiveness and close CAPAs

### 3.1 CAPA Overview

**Corrective and Preventive Action (CAPA):** Systematic process to investigate problems, identify root causes, and prevent recurrence.

**When to initiate CAPA:**

- Significant quality issue
- Recurring problem (same defect multiple times)
- Customer complaint
- Audit finding
- Safety issue

---

### 3.2 Creating a CAPA

**Steps:**

1. Navigate to **Quality** > **CAPAs**
2. Click **+ New CAPA**
3. Fill in details:

| Field | Description |
|-------|-------------|
| **Title** | Clear problem statement |
| **Source** | Where issue originated |
| **Priority** | Low, Medium, High, Critical |
| **Owner** | Person responsible |
| **Due Date** | Target completion |
| **Problem Description** | Detailed issue description |

4. Link related quality reports
5. Assign team members
6. Save

**Exercise 3.1:** Create a CAPA

1. Go to CAPAs
2. Click **+ New CAPA**
3. Create with:
   - Title: "Recurring dimensional failures on part type PT-100"
   - Priority: High
   - Owner: (assign to yourself for training)
   - Problem: "Over the past month, 15 parts of type PT-100 have failed dimensional inspection for outer diameter. Failures occurred across 3 work orders."
4. Save

---

### 3.3 CAPA Tasks

**Typical CAPA phases:**

1. **Containment:** Immediate actions to contain problem
2. **Investigation:** Root cause analysis
3. **Corrective Action:** Fix the problem
4. **Preventive Action:** Prevent recurrence
5. **Verification:** Confirm effectiveness

**Creating tasks:**

1. Open CAPA
2. Go to **Tasks** section
3. Click **+ Add Task**
4. Define: task description, assignee, due date
5. Save

**Exercise 3.2:** Add CAPA Tasks

Add these tasks to your training CAPA:

1. "Containment: Quarantine all PT-100 parts in WIP" - Due: Today
2. "Investigation: Analyze measurement data for trends" - Due: +3 days
3. "Investigation: Interview operators" - Due: +3 days
4. "Root Cause: Complete 5-Why analysis" - Due: +5 days

---

### 3.4 Monitoring Progress

**On CAPAs page:**

- Status shows overall progress
- Overdue tasks highlighted
- Filter by owner, status, priority

**Your oversight tasks:**

- Review open CAPAs weekly
- Follow up on overdue items
- Provide guidance to owners
- Remove blockers

**Exercise 3.3:** Monitor CAPAs

1. Go to CAPAs
2. Filter to "Open" status
3. Identify any overdue tasks
4. Note which CAPAs need attention

---

### 3.5 CAPA Verification

**Before closing, verify:**

- [ ] Root cause identified and documented
- [ ] Corrective actions completed
- [ ] Preventive actions implemented
- [ ] Evidence of effectiveness collected
- [ ] No recurrence of issue

**Verification evidence examples:**

- Measurement data showing improvement
- Process audit results
- Time period without recurrence
- Training records

---

### 3.6 Closing a CAPA

**Steps:**

1. Open CAPA
2. Verify all tasks complete
3. Review verification evidence
4. Click **Request Closure**
5. Add closure summary
6. Approve closure (signature)

**Exercise 3.4:** Close a CAPA

1. Open CAPA "CAPA-TRAIN-COMPLETE"
2. Review all completed tasks
3. Review verification evidence
4. Click **Request Closure**
5. Add summary: "Root cause identified as worn tooling. Tools replaced and inspection frequency increased. No recurrence in 30 days."
6. Approve closure

---

### Knowledge Check: Module 3

1. What triggers a CAPA?
2. What are the main phases of a CAPA?
3. What must be verified before closing a CAPA?

---

## Module 4: Document Approval

### Learning Objectives

By the end of this module, you will:

- [ ] Review documents for approval
- [ ] Approve or reject with appropriate feedback
- [ ] Understand document control requirements

### 4.1 Documents Requiring Approval

**Types you may approve:**

- Work instructions
- Inspection procedures
- Quality specifications
- Process documents
- CAPA documentation

---

### 4.2 Reviewing Documents

**Before approving, verify:**

1. **Content accuracy:** Is information correct?
2. **Completeness:** Are all sections filled?
3. **Format:** Follows template?
4. **Change notes:** What changed and why?
5. **Impact:** Does this affect other processes?

---

### 4.3 Document Approval

**Steps:**

1. Open document from Inbox or Documents
2. Read the document
3. Review revision notes
4. Check any linked items
5. Approve or reject
6. Enter password to sign

**Exercise 4.1:** Approve a Document

1. Find document "WI-TRAIN-001" pending approval
2. Review the content
3. Check revision notes
4. Approve with signature

---

### 4.4 Rejection with Feedback

**When rejecting:**

1. Be specific about issues
2. Explain what needs to change
3. Offer guidance
4. Set expectations for resubmission

---

## Module 5: Quality Analytics

### Learning Objectives

By the end of this module, you will:

- [ ] Interpret quality dashboards
- [ ] Identify trends requiring action
- [ ] Use data to drive improvement

### 5.1 Dashboard Metrics

**Key Performance Indicators:**

| Metric | What It Tells You |
|--------|-------------------|
| **FPY** | First pass yield - efficiency |
| **Open NCRs** | Current quality issues |
| **NCR Age** | Time to resolve issues |
| **Open CAPAs** | Systemic issues being addressed |
| **CAPA Age** | Time to correct problems |
| **Defect Rate** | Quality level |

---

### 5.2 Trend Analysis

**Use Analytics page to:**

- View defect trends over time
- Pareto analysis of defect types
- Process comparison
- Supplier quality tracking

**Exercise 5.1:** Trend Analysis

1. Go to Analytics
2. View defect trend for past 90 days
3. Identify top 3 defect types
4. Note any increasing trends

---

### 5.3 SPC Review

!!! note "SPC Feature Status"
    The SPC page provides measurement visualization and basic control charts. Advanced features like automated Cpk calculations, rule-based alerts, and control limit management are planned for future releases.

**Your responsibilities:**

- Review control charts periodically
- Monitor measurement trends visually
- Respond to out-of-control signals
- Work with engineering on process adjustments

**Exercise 5.2:** SPC Review

1. Go to Analytics > SPC
2. Select a measurement characteristic
3. Review the control chart visualization
4. Note any concerning trends

---

### 5.4 Taking Action on Data

**When trends indicate problems:**

1. Create CAPA for systemic issues
2. Adjust sampling rules
3. Initiate process improvement
4. Brief management
5. Update team

---

### Knowledge Check: Module 5

1. What does FPY measure?
2. How do you identify a defect requiring CAPA?
3. What action do you take when Cpk drops below threshold?

---

## Module 6: Configuration Responsibilities

### Learning Objectives

By the end of this module, you will:

- [ ] Configure sampling rules
- [ ] Manage error types
- [ ] Set up approval templates

### 6.1 Sampling Rules

**Configure based on:**

- Product risk level
- Customer requirements
- Historical quality
- Regulatory requirements

**Exercise 6.1:** Review Sampling Rules

1. Go to Data Management > Sampling Rules
2. Review current rules
3. Understand AQL settings
4. Note how sample sizes are calculated

---

### 6.2 Error Types

**Maintain defect categories:**

- Clear, specific definitions
- Appropriate hierarchy
- Severity guidelines
- Regular cleanup of unused types

---

### 6.3 Approval Templates

**Configure workflows for:**

- Who approves what
- Approval sequence
- Required signatures
- Escalation paths

---

## Module 7: Team Management

### Learning Objectives

By the end of this module, you will:

- [ ] Monitor inspector performance
- [ ] Balance workload
- [ ] Identify training needs

### 7.1 Inspector Oversight

**Monitor:**

- Inspection throughput
- Quality of findings
- Documentation completeness
- Timeliness

---

### 7.2 Workload Management

**Balance work by:**

- Monitoring queue depth
- Assigning based on skill
- Avoiding bottlenecks
- Planning for peak loads

---

### 7.3 Training and Development

**Identify needs through:**

- Inspection quality review
- Feedback from audits
- Employee requests
- System changes

---

## Practical Assessment

### Task 1: Disposition Approval

1. Find and review "DISP-ASSESS-001"
2. Make approval decision
3. Sign with appropriate comments

### Task 2: CAPA Creation

1. Create new CAPA for provided scenario
2. Add appropriate tasks
3. Assign to team members

### Task 3: CAPA Closure

1. Review "CAPA-ASSESS-READY"
2. Verify completion criteria met
3. Close the CAPA

### Task 4: Analytics Review

1. Review quality dashboard
2. Identify the top concern
3. Recommend action

---

## Training Completion

### Sign-Off Requirements

- [ ] Completed all modules
- [ ] Passed knowledge checks
- [ ] Completed practical assessment
- [ ] Demonstrated with senior manager

### Competencies Verified

- [ ] Can approve/reject dispositions appropriately
- [ ] Can create and manage CAPAs
- [ ] Can approve documents
- [ ] Understands quality metrics
- [ ] Can configure quality settings
- [ ] Can manage inspector team

---

## Quick Reference

### Disposition Approval
Inbox → Review request → Verify evidence → **Approve/Reject** → Sign

### CAPA Creation
CAPAs → **+ New** → Fill details → Add tasks → Assign team → Save

### CAPA Closure
Open CAPA → Verify complete → **Request Closure** → Add summary → Sign

### Document Approval
Inbox → Review document → Check changes → **Approve/Reject** → Sign

---

## Next Steps

After completing this training:

1. Shadow current QA Manager
2. Handle approvals with oversight
3. Lead CAPA with support
4. Full independent responsibilities

