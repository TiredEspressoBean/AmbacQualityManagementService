# Document Controller Training Guide

**Duration:** 3-4 hours
**Prerequisites:** None
**Goal:** Learn to manage controlled documents, revisions, approvals, and document compliance


!!! note "Training Data Setup"
    Exercises reference sample documents (e.g., "WI-TRAIN-001", "DOC-REJECT-TRAIN"). Your administrator should set up training data, or you can create test documents following the exercise patterns.

!!! info "Demo Environment Login"
    **Email:** lisa.docs@demo.ambac.com
    **Password:** `demo123`

---

## Module 1: Document Controller Role Overview

### Learning Objectives

By the end of this module, you will:

- [ ] Understand document control responsibilities
- [ ] Navigate document management screens
- [ ] Understand compliance requirements

### 1.1 Your Role

As a Document Controller, you:

- Upload and manage documents
- Control document revisions
- Route documents for approval
- Maintain document compliance
- Manage distribution
- Ensure proper retention

Document control is critical for quality certifications (ISO, AS9100, etc.).

---

### 1.2 Your Home page

Home answers *what needs me right now*. Walked 2026-10-12 as Lisa:

| Block | What it showed |
|-------|----------------|
| **Approvals in flight** | **5** — APR-2026-0003…0007, each with its type and due date |
| **Documents** | Needs my approval **0** · Pending approval **1** · Due for review **0** · Released **2** |
| **Training** | Current **22** · Expiring soon **1** · Expired **1** |

Every figure is a link into what it counts, and there is a scan box for looking up
a work order, serial, lot or location.

!!! important "Your approvals queue is mostly not documents"
    Of those five in flight, **four were CAPA Approvals** and one was a Document
    Release. That is the normal shape: a Document Controller is an **approvals
    operator**, not only a document operator.

    Read the **type** on every row before you work it. The habit of assuming the
    queue is yours-and-document-shaped is how a CAPA approval sits for a week.

### 1.3 Your Main Pages

| Page | Location | Purpose |
|------|----------|---------|
| **Documents** | Documents | Document dashboard |
| **Document List** | `/documents/list` | The full library, with status and classification |
| **Inbox** | Personal > Inbox | Pending approvals |
| **Approval History** | Approvals > History | Approval records |

**Exercise 1.1:** Read your Home

1. Count your approvals in flight, and say how many are **documents**
2. Open the Documents block — how many are pending approval, and how many are
   due for review?
3. Find one person whose training has expired

---

### 1.4 Document States

| State | Meaning |
|-------|---------|
| **Draft** | Being created, not yet submitted |
| **Under Review** | Submitted, approvers responding |
| **Approved** | Approvals complete — decided, but not yet in force |
| **Released** | In force; the revision people must work to |
| **Obsolete** | Superseded, kept for history |

!!! warning "Approved is not Released"
    A document can be approved and still not be the one the floor works to.
    Release is the separate act that puts it into force — which is what lets
    you approve a revision ahead of the training or tooling it depends on.

---

### Knowledge Check: Module 1

1. What is the purpose of document control?
2. What states can a document be in?
3. Where do you find documents pending approval?

---

## Module 2: Uploading Documents

### Learning Objectives

By the end of this module, you will:

- [ ] Upload documents with proper metadata
- [ ] Categorize documents correctly
- [ ] Set appropriate visibility

### 2.1 Document Metadata

**Required fields:**

| Field | Description |
|-------|-------------|
| **Title** | Clear, searchable name |
| **Document Type** | Category (WI, Spec, Drawing) |
| **Revision** | Version identifier |

**Optional fields:**

- Document Number (auto-generated if not provided)
- Description
- Keywords
- Related documents
- Expiration date

!!! note "Document Numbering"
    Document numbers may be auto-generated based on your organization's settings. Check with your administrator for your specific numbering scheme.

---

### 2.2 Uploading a New Document

**Steps:**

1. Navigate to **Documents**
2. Click **Upload Document**
3. Select file from your computer
4. Fill in metadata:
   - Title: Descriptive name
   - Document Number: Per scheme
   - Document Type: Select category
   - Revision: Initial revision (A or 1)
   - Description: Summary of content
5. Set visibility (Internal, Confidential)
6. Click **Upload**

**Exercise 2.1:** Upload a Document

1. Go to **Documents**
2. Click **Upload Document**
3. Select training file provided
4. Fill in:
   - Title: "Training Work Instruction - Widget Assembly"
   - Document Number: "WI-TRAIN-001"
   - Type: Work Instruction
   - Revision: A
   - Description: "Step-by-step assembly instructions for training widgets"
5. Upload

---

### 2.3 Document Numbering

**Follow your scheme consistently:**

Examples:
- Work Instructions: WI-XXX-NNN
- Specifications: SPEC-XXX-NNN
- Drawings: DWG-XXX-NNN
- Forms: FRM-XXX-NNN

**Tips:**

- Use leading zeros for sorting
- Include department or product codes
- Keep it meaningful but concise

---

### 2.4 Classification

**Classification is yours**, and you hold the top of it. Two different
permissions, and they are not held by the same people:

| Permission | Held by |
|------------|---------|
| `classify_documents` — set a document's tier | Tenant Admin, **QA Manager**, Document Controller |
| `view_secret_documents` — read the top tier | Tenant Admin, **Document Controller** |

There are **five** tiers, not three:

| Tier | Who can see it |
|------|----------------|
| **Public** | Everyone, including customers |
| **Internal** | All staff |
| **Confidential** | All staff (`view_confidential_documents`) |
| **Restricted** | All staff (`view_restricted_documents`) |
| **Secret** | **Tenant Admin and you** |

!!! warning "Confidential and Restricted are not manager-only"
    Every internal role — Operator and the dock included — holds both. Those
    tiers separate staff from **customers and auditors**, not managers from the
    floor. **Secret is the only tier that narrows it within the shop**, and you
    are one of only two roles that can read it.

!!! important "A QA Manager can classify Secret and then not be able to open it"
    They have `classify_documents` but not `view_secret_documents`. If someone
    says a document vanished after they filed it, this is why.

!!! important "Classification filters the queryset, not just the screen"
    A document above someone's tier is **excluded from their results**. They do
    not see it greyed out or get an error — it simply is not there.

    So "I can't find the drawing" from an engineer may be classification working
    exactly as designed. Check the tier before assuming something is lost.

!!! warning "An auditor is deliberately not given the top tiers"
    External auditors may not be authorised persons for export-controlled
    technical data, so the Auditor role gets neither `view_secret_documents` nor
    the export-control tier. If an auditor cannot see a document, that is the
    control, not a permissions mistake — find them a reader with the right
    clearance rather than reclassifying the document.

!!! note "You cannot practise the upper tiers on demo data"
    All four demo documents are **Internal**, so nothing exercises the filtering.
    You can set a classification and see it on the row; you cannot watch it hide
    a document from someone until your own data has tiers in it.

---

### Knowledge Check: Module 2

1. What metadata is required when uploading?
2. Why is consistent document numbering important?
3. When would you set a document to "Confidential"?

---

## Module 3: Document Revisions

### Learning Objectives

By the end of this module, you will:

- [ ] Create document revisions properly
- [ ] Document changes clearly
- [ ] Maintain revision history

### 3.1 When to Create a Revision

**Create a new revision when:**

- Content changes (any text, images)
- Process updates
- Corrections needed
- Format changes

**Don't overwrite!** Always create a new revision.

---

### 3.2 Creating a Revision

**Steps:**

1. Open existing document
2. Click **Create Revision**
3. Upload new file
4. Fill in revision details:
   - New Revision: Next in sequence (B, C or 2, 3)
   - Change Summary: What changed
   - Reason: Why the change
5. Submit for approval

**Exercise 3.1:** Create a Revision

1. Open document "WI-TRAIN-001"
2. Click **Create Revision**
3. Upload revised file
4. Fill in:
   - New Revision: B
   - Change Summary: "Added safety note to step 3"
   - Reason: "Safety review recommendation"
5. Submit

---

### 3.3 Revision Best Practices

**Good change summary:**
"Updated torque specifications in Section 4.2 per Engineering Change EC-2024-015. Changed measurement tolerance in Table 3."

**Bad change summary:**
"Updated"

**Always include:**

- What sections changed
- What the change was
- Reference to change request (if applicable)

---

### 3.4 Revision Sequences

**Common schemes:**

| Scheme | Example | Usage |
|--------|---------|-------|
| Letters | A, B, C | Pre-release drafts |
| Numbers | 1, 2, 3 | Released versions |
| Combined | A1, A2, B1 | Draft within release |

Follow your organization's standard.

---

### Knowledge Check: Module 3

1. When should you create a revision vs. editing in place?
2. What makes a good change summary?
3. What happens to the old revision when a new one is approved?

---

## Module 4: Approval Workflow

### Learning Objectives

By the end of this module, you will:

- [ ] Submit documents for approval
- [ ] Track approval status
- [ ] Handle rejections

### 4.0 Working a mixed queue

Before the document-specific steps: **your approvals queue is not document-only.**

Walked 2026-10-12 — of five approvals in flight, **four were CAPA Approvals**
(APR-2026-0004…0007, all due the next day) and **one was a Document Release**
(APR-2026-0003).

| Read first | Then |
|-----------|------|
| The **type** on the row | Whether it is yours to decide or yours to chase |
| The **due date** | Four sharing one due date is a batch, not a coincidence |

!!! warning "The commonest failure in this role is queue blindness"
    Assuming everything in the queue is a document means CAPA approvals age
    quietly. They carry the same urgency and the same audit consequence.

### 4.1 Submitting for Approval

**Steps:**

1. Open document (Draft or new revision)
2. Verify content is complete
3. Click **Submit for Approval**
4. Select approval template (if options)
5. Add submission notes (optional)
6. Submit

**What happens:**

- Document status changes to "Pending Approval"
- Approvers are notified
- Workflow begins

**Exercise 4.1:** Submit for Approval

1. Open document revision created earlier
2. Click **Submit for Approval**
3. Select "Standard Review" template
4. Add note: "Ready for review"
5. Submit

---

### 4.2 Tracking Approval

**View approval status:**

1. Open document
2. Go to **Approvals** section
3. See status for each approver:
   - Pending: Not yet reviewed
   - Approved: Signed off
   - Rejected: Returned with comments

---

### 4.3 Following Up

**If approval is delayed:**

1. Check who hasn't approved
2. Send reminder (per your process)
3. Escalate if needed
4. Document any delays

---

### 4.4 Handling Rejections

**When a document is rejected:**

1. Review rejection comments
2. Understand required changes
3. Make corrections
4. Create new revision
5. Resubmit for approval

**Exercise 4.2:** Review Rejection

1. Open document "DOC-REJECT-TRAIN"
2. Review rejection comments
3. Note what needs to change

---

### Knowledge Check: Module 4

1. What happens when you submit for approval?
2. How do you see who has approved?
3. What do you do when a document is rejected?

---

## Module 5: Managing the Library

### Learning Objectives

By the end of this module, you will:

- [ ] Organize documents effectively
- [ ] Find documents quickly
- [ ] Manage obsolete documents

### 5.1 Document Organization

**Organize by:**

- Document type
- Product line
- Department
- Process

Use consistent naming and metadata for easy finding.

---

### 5.2 Searching Documents

**Search methods:**

1. **Quick search:** Title or number
2. **Filters:** Type, status, date, author
3. **Browse:** By category

**Exercise 5.1:** Finding Documents

1. Search for "inspection"
2. Filter to only "Released" documents
3. Filter to "Work Instruction" type
4. Find the most recent

---

### 5.3 Obsolete Documents

**When documents become obsolete:**

- New revision approved (automatic)
- Document retired (manual)

**Handling obsolete:**

- Not visible in normal views
- Marked clearly as obsolete
- Kept for historical reference
- Available for audits

---

### 5.4 Periodic Review

**Many standards require periodic review:**

1. Set review intervals per document type
2. System notifies when due
3. Review and either:
   - Confirm current (re-approve)
   - Update (new revision)
4. Document the review

Home carries a **Due for review** tile so the backlog is visible without going
looking for it.

!!! note "Dark on demo data"
    *Due for review* reads **0** in the demo, because no document has a review
    interval set. The loop is real; there is just nothing in it to show you. Set
    an interval on one of your own documents to see it populate.

### 5.5 Removing a document

Every row offers **Delete Document**, behind a confirmation. It is manager-tier
authority that you hold.

!!! warning "Deleting is archiving, and that is the point"
    uqmes soft-deletes — the record and its history stay, and an auditor can
    still reach them. What you are doing is taking it **out of circulation**, not
    destroying evidence.

    For a superseded document prefer **Obsolete**, which says *why* it left
    circulation. Reach for delete when something should never have been in the
    library at all — the wrong file, a duplicate, a test upload.

---

### Knowledge Check: Module 5

1. How do you filter to see only released documents?
2. What happens to old revisions when new one is released?
3. Why do we keep obsolete documents?

---

## Module 6: Compliance and Audits

### Learning Objectives

By the end of this module, you will:

- [ ] Understand compliance requirements
- [ ] Prepare for audits
- [ ] Generate compliance reports

### 6.1 Document Control Requirements

**Standards require:**

- Version control
- Approval records
- Change history
- Availability of current versions
- Prevention of unintended use of obsolete

uqmes handles these automatically.

---

### 6.2 Audit Preparation

**Be ready with:**

- Complete document inventory
- Revision histories
- Approval records
- Distribution evidence
- Review records

All available in the system.

---

### 6.3 Compliance Reports

**Available compliance information:**

1. Documents filtered by type and status
2. Pending reviews (via filtering)
3. Approval audit trail (on document detail pages)
4. Recent changes (via activity history)

!!! note "Reports Feature"
    Dedicated compliance report generation is planned for a future release. Currently, use the document library filters and export functionality to gather audit information.

**Exercise 6.1:** Gather Audit Information

1. Go to Documents
2. Filter to document type of interest
3. Review status and approval history
4. Export the filtered list if needed

---

### 6.4 Common Audit Questions

| Question | Where to Find Answer |
|----------|---------------------|
| "What revision is current?" | Document detail page |
| "Who approved it?" | Approval history |
| "What changed in this revision?" | Revision notes |
| "When was it last reviewed?" | Review records |

---

## Module 7: Daily Workflow

### Learning Objectives

By the end of this module, you will:

- [ ] Follow an effective daily routine
- [ ] Manage multiple requests
- [ ] Stay compliant

### 7.1 Daily Tasks

1. **Read Home** — approvals in flight, and how many are documents
2. **Check Inbox** for pending approvals (if you approve)
3. **Process upload requests** in queue
4. **Monitor pending approvals** on submitted docs
5. **Follow up** on stalled items
6. **Glance at Training** — expiring and expired

### 7.1a Training records are yours too

You hold the same training-record authority as a Shift Lead or QA Manager, and
Home shows **Current / Expiring soon / Expired** because of it.

This is not a stray permission. Competence evidence (ISO 9001 §7.2) is a
controlled record like any other, and it sits with the people who control
records. Writing one certifies somebody — so the **level** must be what they
actually demonstrated, not attendance.

See [Training Matrix](../workflows/tracking/training-matrix.md).

---

### 7.2 Managing Requests

**When users request documents:**

1. Verify requirements
2. Check if document exists
3. Upload or revise as needed
4. Submit for approval
5. Track to completion

---

### 7.3 Weekly Tasks

- [ ] Review pending reviews due
- [ ] Check for expired documents
- [ ] Update document inventory
- [ ] Clear approval backlogs
- [ ] Audit compliance status

---

## Practical Assessment

### Task 1: Document Upload

1. Upload new document "WI-ASSESS-001"
2. Complete all metadata correctly
3. Set appropriate visibility

### Task 2: Create Revision

1. Open existing document "DOC-ASSESS-REV"
2. Create new revision
3. Document changes properly
4. Submit for approval

### Task 3: Track Approval

1. Find document pending approval
2. Identify pending approvers
3. Check approval history

### Task 4: Audit Readiness

1. Generate document status report
2. Find all documents due for review
3. Export approval history for a document

### Task 5: Read your queue (row 4)

Open Home. Report how many approvals are in flight, **how many are documents and
how many are CAPAs**, and which you would work first.

### Task 6: Classify (row 7)

Set a classification on a document and say who can now see it and who cannot.
Then explain what an engineer would experience if a drawing were above their
tier — and why an auditor is deliberately not given the top tiers.

### Task 7: Remove something (row C1)

A duplicate file has been uploaded by mistake. Decide between **Obsolete** and
**Delete**, do it, and justify the choice. Say what survives either way.

### Task 8: Certify someone (row 8)

Create a training record. Explain why the **level** field is an assessed result
rather than a record of attendance.

---

## Training Completion

### Sign-Off Requirements

- [ ] Completed all modules
- [ ] Passed knowledge checks
- [ ] Completed practical assessment
- [ ] Demonstrated with supervisor

### Competencies Verified

- [ ] Can upload documents correctly
- [ ] Can create revisions properly
- [ ] Understands approval workflow
- [ ] Can maintain document library
- [ ] Understands compliance requirements

---


### Recording the qualification

Ticking the boxes above is the *assessment*. It is not the record.

A signed-off trainee is not yet qualified in the system, and the difference is
operational, not clerical: training requirements gate who may start a step, so
until the record exists the person is still refused the work they were just
signed off to do. That refusal surfaces downstream as a part nobody can pick
up — see [Parts stuck at a
step](../troubleshooting/common-issues.md).

To close it out, create a **Training Record** for the trainee under **Quality**
> **Training**:

| Field | Set it to |
|-------|-----------|
| **Training type** | The qualification being awarded |
| **Completed date** | The date of the assessment, not today |
| **Level** | The competency level actually demonstrated |
| **Trainer** | Whoever conducted and assessed it |
| **Expires** | Leave blank only if the qualification genuinely never lapses |
| **Documents** | Attach the signed sign-off sheet as evidence |

!!! note "Level is an assessed result, not attendance"
    The competency level is clause 7.2 evidence of what the person can actually
    do. Recording everyone at the same level because they sat the course
    defeats the control, and the training matrix that supervisors plan from
    becomes fiction.

## Quick Reference

### Upload Document
Documents → **Upload Document** → Select file → Fill metadata → **Upload**

### Create Revision
Open document → **Create Revision** → Upload new file → Fill change notes → **Submit**

### Submit for Approval
Open document → **Submit for Approval** → Select template → **Submit**

### Check Status
Open document → **Approvals** section → View status

### Classification tiers
Public → Internal → Confidential → Restricted → **Secret**
You and QA Manager hold the top tier. It **filters the queryset** — people don't
see a locked document, they see no document.

### Your queue is mixed
Read the **type** on every row. Most of what's in flight is usually **CAPA
approvals**, not documents.

### Obsolete vs Delete
**Obsolete** — superseded, says why it left circulation.
**Delete** — it should never have been there. Soft-delete: history survives.

### Approved ≠ Released
Approved is decided. **Released** is in force. That gap is what lets you approve
a revision ahead of the training or tooling it depends on.

---

## Next Steps

After completing this training:

1. Shadow current Document Controller
2. Handle uploads with oversight
3. Manage revisions independently
4. Full document control responsibility

