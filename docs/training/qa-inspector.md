# QA Inspector Training Guide

**Duration:** 4-6 hours
**Prerequisites:** None (Operator training recommended)
**Goal:** Learn to perform inspections, record results, create quality reports, and manage dispositions

---

## Module 1: Inspector Role Overview

### Learning Objectives

By the end of this module, you will:

- [ ] Understand the QA Inspector's responsibilities
- [ ] Navigate QA-specific screens
- [ ] Understand the quality workflow

### 1.1 Your Role

As a QA Inspector, you:

- Perform quality inspections
- Record inspection results
- Create quality reports (NCRs)
- Recommend dispositions
- Ensure product conformance

Your work directly impacts product quality and customer satisfaction.

---

### 1.2 QA Screens

**Main pages you'll use:**

| Page | Location | Purpose |
|------|----------|---------|
| **QA Work Orders** | Quality > Work Orders | Your inspection queue |
| **Quality Reports** | Quality > Quality Reports | NCR management |
| **Tracker** | Portal > Tracker | Part status overview |
| **Inbox** | Personal > Inbox | Your notifications |

**Exercise 1.1:** Navigate QA Pages

1. Log into the training environment
2. Visit each page listed above
3. Note what information is displayed on each

---

### 1.3 Quality Workflow

```
Part flagged/sampled → Inspector reviews →
Pass: Release part
Fail: Create NCR → Recommend disposition → QA Manager approves → Execute disposition
```

---

### Knowledge Check: Module 1

1. What are the main responsibilities of a QA Inspector?
2. Where do you find parts waiting for inspection?
3. What happens after you fail a part?

---

## Module 2: Work Order Inspection

### Learning Objectives

By the end of this module, you will:

- [ ] Find parts requiring inspection
- [ ] Perform first piece inspection (FPI)
- [ ] Complete sampling inspections
- [ ] Record inspection results

### 2.1 QA Work Orders Page

**Concept:** The QA Work Orders page shows orders needing quality attention.

**Information displayed:**

- Work order number
- Order details
- Current status
- Parts requiring inspection
- Priority indicators

**Exercise 2.1:** Review QA Queue

1. Navigate to **Quality** > **Work Orders**
2. Identify orders with pending inspections
3. Note the priority indicators
4. Click an order to see details

---

### 2.2 First Piece Inspection (FPI)

**Concept:** FPI verifies the first part of a batch before production continues. It catches setup issues early.

**When FPI is required:**

- First part of a new work order
- After setup changes
- After process adjustments
- When specified by process

**Steps:**

1. Open work order with FPI required
2. Find the first piece part
3. Click **Perform FPI**
4. Complete all required measurements
5. Record pass or fail
6. If pass: Production can continue
7. If fail: Stop production, investigate

**Exercise 2.2:** Complete an FPI

1. Find work order "TRAIN-FPI-001" in QA Work Orders
2. Locate the first piece
3. Click **Perform FPI**
4. Enter the measurement values provided
5. Submit the FPI result

---

### 2.3 Sampling Inspection

**Concept:** Sampling inspects a subset of parts per statistical rules (e.g., AQL tables).

**How sampling works:**

1. System determines sample size based on:
   - Lot size
   - AQL level
   - Inspection level
2. You inspect the required sample
3. Accept/reject lot based on results

**Exercise 2.3:** Sampling Inspection

1. Find an order with sampling requirement
2. Note the sample size displayed
3. Inspect the specified parts
4. Record results
5. System calculates accept/reject

---

### 2.4 Recording Inspection Results

**For each inspection:**

1. Identify the characteristic being inspected
2. Perform the measurement or check
3. Enter the result
4. System compares to specification
5. Pass/fail is determined

**Tips:**

- Use calibrated equipment
- Follow standard inspection methods
- Document any anomalies
- Be consistent

---

### Knowledge Check: Module 2

1. What is the purpose of First Piece Inspection?
2. What happens if FPI fails?
3. How does the system determine sample size?

---

## Module 3: Creating Quality Reports

### Learning Objectives

By the end of this module, you will:

- [ ] Understand when to create a quality report
- [ ] Create an NCR with complete information
- [ ] Link parts to quality reports

### 3.1 When to Create a Quality Report

**Create a quality report (NCR) when:**

- Part fails inspection
- Operator flags an issue
- Customer complaint received
- Non-conformance discovered

**Don't create duplicate reports** - check if one already exists for the issue.

---

### 3.2 Quality Report Fields

| Field | Description | Required |
|-------|-------------|----------|
| **Title** | Brief description of issue | Yes |
| **Error Type** | Category of defect | Yes |
| **Severity** | Minor, Major, Critical | Yes |
| **Description** | Detailed explanation | Yes |
| **Parts Affected** | Link to specific parts | Yes |
| **Evidence** | Photos, measurements | Recommended |

---

### 3.3 Creating a Quality Report

**Steps:**

1. Navigate to **Quality** > **Quality Reports**
2. Click **+ New Report**
3. Fill in required fields:
   - Title: Clear, specific description
   - Error Type: Select from list
   - Severity: Based on impact
   - Description: What, where, when, how found
4. Link affected parts
5. Attach evidence (photos, data)
6. Save

**Exercise 3.1:** Create a Quality Report

1. Go to Quality Reports
2. Click **+ New Report**
3. Create report for:
   - Title: "Surface scratch on housing - TRAIN-101"
   - Error Type: Visual Defect
   - Severity: Minor
   - Description: "Visible scratch approximately 2cm on outer surface of housing. Found during final inspection."
4. Link to part "TRAIN-101-003"
5. Save the report

---

### 3.4 Quality Report Best Practices

**Good title:** "Diameter out of spec - 25.42mm vs 25.00±0.05"
**Bad title:** "Part is bad"

**Good description:** "During sampling inspection of lot 2024-0042, measurement of inner diameter on part SN-1234 was 25.42mm. Specification is 25.00mm ±0.05mm. Part is 0.37mm over maximum tolerance. Measured with micrometer ID-456, last calibrated 2024-01-15."

**Bad description:** "Part doesn't fit"

---

### Knowledge Check: Module 3

1. What should a quality report title include?
2. What makes a good description?
3. Why is it important to link specific parts?

---

## Module 4: Quarantine and Disposition

### Learning Objectives

By the end of this module, you will:

- [ ] Understand quarantine status
- [ ] Know the disposition options
- [ ] Recommend appropriate dispositions

### 4.1 Quarantine

**Concept:** Quarantine isolates non-conforming parts from production flow until a decision is made.

**When parts enter quarantine:**

- Operator flags an issue
- Inspector fails part
- Quality report created
- Out-of-spec measurement recorded

**Quarantined parts cannot:**

- Advance through production
- Ship to customer
- Return to stock without disposition

---

### 4.2 Disposition Options

| Disposition | When to Use | Requires Approval |
|-------------|-------------|-------------------|
| **Use As-Is** | Defect acceptable, no impact | Sometimes |
| **Rework** | Can be fixed and re-inspected | Sometimes |
| **Scrap** | Cannot be salvaged | Yes (if value threshold) |
| **Return to Supplier** | Incoming material issue | Yes |
| **Deviation** | Customer accepts non-conformance | Yes + Customer |

---

### 4.3 Recommending Disposition

**Your role:** Recommend the appropriate disposition based on:

- Nature of defect
- Impact on function/safety
- Cost considerations
- Customer requirements

**Steps:**

1. Open the quality report
2. Review all information
3. Click **Recommend Disposition**
4. Select disposition type
5. Provide justification
6. Submit for approval

**Exercise 4.1:** Recommend a Disposition

1. Find quality report "QR-TRAIN-001"
2. Review the issue details
3. Click **Recommend Disposition**
4. Select "Rework"
5. Justification: "Surface scratch can be polished out without affecting dimensions or function. Recommend rework and re-inspection."
6. Submit

---

### 4.4 After Disposition Approval

Once QA Manager approves:

| Disposition | Next Steps |
|-------------|------------|
| Use As-Is | Release part from quarantine |
| Rework | Return to production, re-inspect after |
| Scrap | Mark scrapped, update counts |
| Return to Supplier | Initiate RMA process |

---

### Knowledge Check: Module 4

1. What is the purpose of quarantine?
2. Who approves dispositions?
3. What disposition would you recommend for a part with a minor cosmetic defect that doesn't affect function?

---

## Module 5: Documentation and Evidence

### Learning Objectives

By the end of this module, you will:

- [ ] Attach evidence to reports
- [ ] Take effective photos
- [ ] Reference relevant documents

### 5.1 Why Documentation Matters

Good documentation:

- Supports disposition decisions
- Provides audit trail
- Helps root cause analysis
- Protects the company
- Satisfies customer requirements

---

### 5.2 Attaching Evidence

**Types of evidence:**

- Photos of defect
- Measurement data
- Calibration records
- Process logs

**Steps:**

1. Open quality report
2. Go to **Attachments** section
3. Click **Add Attachment**
4. Select file or take photo
5. Add description
6. Save

---

### 5.3 Taking Good Defect Photos

**Tips:**

- Include scale reference (ruler)
- Good lighting
- Multiple angles
- Clear focus on defect
- Include part number in frame

**Exercise 5.1:** Documentation Practice

1. Open quality report "QR-TRAIN-002"
2. Attach the sample image provided
3. Add description: "Close-up of surface defect, 10mm scale reference shown"

---

### 5.4 Referencing Documents

When creating quality reports, reference:

- Applicable specification
- Drawing revision
- Work instruction
- Customer requirements

This creates traceability.

---

## Module 6: SPC and Trends

### Learning Objectives

By the end of this module, you will:

- [ ] Understand SPC basics
- [ ] Read control charts
- [ ] Identify trends requiring action

### 6.1 What is SPC?

**Statistical Process Control (SPC):** Using data to monitor process stability and capability.

**Key concepts:**

- **Control limits:** Expected process variation
- **Specification limits:** What's acceptable
- **Cp/Cpk:** Process capability indices

---

### 6.2 Reading Control Charts

**Chart elements:**

- **UCL:** Upper control limit
- **LCL:** Lower control limit
- **Center line:** Process average
- **Data points:** Individual measurements

**What to look for:**

| Signal | Meaning |
|--------|---------|
| Point outside limits | Out of control |
| 7 points trending | Process shift |
| 7 points one side | Process shift |
| Erratic pattern | Unstable process |

---

### 6.3 When to Escalate

**Alert QA Manager when:**

- Control chart shows out-of-control signals
- Cpk drops below threshold
- Trend indicates deterioration
- Process needs adjustment

---

### Knowledge Check: Module 6

1. What do control limits represent?
2. What does it mean if a point is outside the control limits?
3. Who should you notify if you see an SPC trend?

---

## Module 7: Daily Inspector Workflow

### Learning Objectives

By the end of this module, you will:

- [ ] Follow a structured daily routine
- [ ] Prioritize work effectively
- [ ] Maintain accurate records

### 7.1 Start of Shift

1. **Log in** to Ambac Tracker
2. **Check Inbox** for notifications
3. **Review QA Work Orders** queue
4. **Verify equipment** calibration status
5. **Plan your inspections**

---

### 7.2 Prioritization

**Inspect in this order:**

1. FPI for waiting production (blocking work)
2. High-priority orders
3. Rush orders
4. Orders approaching due date
5. Standard queue

---

### 7.3 During Shift

- Complete inspections promptly
- Record results immediately
- Create quality reports as needed
- Communicate blockers
- Stay organized

---

### 7.4 End of Shift

- [ ] All inspections recorded
- [ ] Quality reports complete
- [ ] Handoff to next shift if needed
- [ ] Update any pending items

---

## Practical Assessment

Complete these tasks to demonstrate competency:

### Task 1: FPI Completion

1. Find work order "ASSESS-QA-001"
2. Complete the First Piece Inspection
3. Record all measurements

### Task 2: Sampling Inspection

1. Find work order "ASSESS-QA-002"
2. Perform sampling inspection
3. Record accept/reject

### Task 3: Quality Report Creation

1. For the failed part in Task 2
2. Create a quality report
3. Include all required fields
4. Attach evidence (use training image)

### Task 4: Disposition Recommendation

1. For the quality report created
2. Recommend appropriate disposition
3. Provide justification

---

## Training Completion

### Sign-Off Requirements

- [ ] Completed all modules
- [ ] Passed knowledge checks
- [ ] Completed practical assessment
- [ ] Demonstrated on actual parts (supervised)
- [ ] Supervisor sign-off

### Competencies Verified

- [ ] Can perform FPI correctly
- [ ] Can complete sampling inspections
- [ ] Creates thorough quality reports
- [ ] Recommends appropriate dispositions
- [ ] Understands SPC basics
- [ ] Follows documentation standards

---

## Quick Reference Card

### FPI Process
1. QA Work Orders → Find order → **Perform FPI** → Enter measurements → Submit

### Quality Report
1. Quality Reports → **+ New** → Fill details → Link parts → Attach evidence → Save

### Disposition
1. Open report → **Recommend Disposition** → Select type → Justify → Submit

### Quarantine Check
1. Look for "Quarantine" status on parts
2. Part needs quality report and disposition

---

## Next Steps

After completing this training:

1. Shadow experienced inspector
2. Perform supervised inspections
3. Review with QA Manager
4. Independent inspection work

