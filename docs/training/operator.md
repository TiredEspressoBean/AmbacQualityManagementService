# Production Operator Training Guide

**Duration:** 2-4 hours
**Prerequisites:** None
**Goal:** Learn to track parts through production steps and record measurements

!!! note "Role Name"
    This training is for the **Production_Operator** role in the system.

!!! info "Demo Environment Login"
    **Email:** mike.ops@demo.ambac.com
    **Password:** `demo123`

---

## Module 1: System Basics

### Learning Objectives

By the end of this module, you will:

1. Log into uqmes
2. Navigate the main interface
3. Understand your role and permissions

### 1.1 Logging In

**Concept:** uqmes uses secure login to track who does what.

**Steps:**

1. Open your browser (Chrome recommended)
2. Go to your company's uqmes URL
3. Enter your email and password
4. Click **Sign In**

!!! tip "Single Sign-On"
    If your company uses SSO, click the SSO button and use your company credentials.

**Why it matters:** Every action you take is recorded with your name and timestamp for quality traceability.

---

### 1.2 The Work Orders Page

**Concept:** The Work Orders page is your main workspace for finding and working on production orders.

**How you get your work:**

1. Your supervisor assigns you to specific work orders
2. You find those work orders on the Work Orders page
3. You work on the parts in that order, recording measurements and checks

**What you'll see:**

| Element | Purpose |
|---------|---------|
| Work order table | List of all work orders |
| Search/filter | Find your assigned work orders |
| Status column | Shows order progress |
| Actions | Open a work order, start work, record quality |

**Exercise 1.1:** Finding Your Work Order

1. Go to **Work Orders** in the sidebar
2. Use the search bar to find the work order your supervisor assigned
3. Click the work order row to see details
4. Note the work order number, part type, and current progress

**Expected result:** You see the work order details and can access parts to work on.

---

### 1.3 Understanding Parts

**Concept:** Each work order contains parts that move through production steps.

**Part information includes:**

- Serial number (unique identifier)
- Part type (what it is)
- Current step (where it is in the process)
- Status (in process, complete, on hold, quarantined)

**Exercise 1.2:** Viewing Part Details

1. From your work order, view the parts list
2. Click a part row to see details
3. Note the serial number and current step

---

### Knowledge Check: Module 1

1. Where do you go to find your assigned work orders?
2. How do you know what work order to work on?
3. Why is it important that your actions are logged?

---

## Module 2: Moving Parts Forward

### Learning Objectives

By the end of this module, you will:

- [ ] Start work on a set of parts
- [ ] Work through a step's substeps and complete the step
- [ ] Understand why a part might not advance

### 2.1 The Step Process

**Concept:** Parts move through a defined sequence of steps. You do not move
them yourself — you record the work at your step, and the system advances the
parts once the step's requirements are satisfied.

**Typical flow:**

```
Receiving → Inspection → Machining → Finishing → Final QC → Shipping
```

Each step may require:

- Measurements to record
- Documents to reference
- Equipment to use
- Training to have

---

### 2.2 Starting Work

You work a step from the work order, one part at a time.

**Steps:**

1. Navigate to **Production** > **Work Orders**
2. Open your assigned work order
3. Click **Start Work**
4. In the **Start work on parts** dialog, check the parts you'll work on, *in
   the order you'll work them*
5. Confirm — the step player opens on the first part

After you complete a part's step, the player moves to the next checked part
automatically, so you can work a batch without returning to the work order.

**Exercise 2.1:** Starting Work

1. Go to **Production** > **Work Orders**
2. Open your assigned work order
3. Click **Start Work**
4. Check two parts and confirm

**Expected result:** The step player opens on the first part you checked.

---

### 2.3 Working a Step

Reference: [Running Work Instructions](../workflows/dwi/running.md).

The player shows **one substep at a time**, with a progress rail along the top.

**Steps:**

1. Do what the substep asks — take a measurement, perform a check, sign off
2. Tap **Confirm & next**
3. If a substep genuinely does not apply, tap **Mark N/A** and choose a reason
4. After the last substep you get a **review screen** listing everything you
   recorded — tap any entry to jump back and fix it
5. Tap **Complete step**

**What happens:**

- Your entries are recorded against the part with your name and a timestamp
- The part advances if the step's requirements are met
- The player moves on to the next part you checked

**Exercise 2.2:** Completing a Step

1. In the player, work through each substep, tapping **Confirm & next**
2. On the review screen, check your entries
3. Tap **Complete step**

**Expected result:** The step completes and the player moves to your next part.

!!! tip "Your work is saved as you go"
    Each substep is sealed when you confirm it. If the tablet is closed or
    handed over, reopening the step resumes where you left off.

---

### 2.4 Individual Part Quality Reports

For individual parts requiring quality documentation or in-process checks:

**Steps:**

1. From your work order, find the part in the parts list
2. Click the **Quality Report** button
3. Fill in the quality report form:
   - Operator (your name)
   - Machine/equipment used
   - Measurements
   - Pass/fail status
4. Submit the form

**When to use:** When recording in-process measurements or quality data for specific parts during your operation.

---

### 2.5 When Parts Don't Advance

A part will not move on if:

- Required captures are missing or incomplete
- The step's First Piece Inspection is still pending
- You don't have training for that step
- The part is quarantined
- The previous step isn't complete
- **Another part in the lot still has outstanding work**

!!! note "Parts move as a lot"
    Parts that have not been split advance together — all parts at the same work
    order and step, or none. So a part of yours can be finished and still not
    move, because a different part in the same lot isn't done. That is normal,
    not a fault.

!!! warning "First Piece Inspection blocks the whole step"
    If the step's FPI hasn't been signed off, no part at that step advances.
    **Complete step** becomes the buy-off action for whoever can sign it.

---

### Knowledge Check: Module 2

1. What actually causes a part to move to the next step?
2. How do you start work on a set of parts?
3. Name two reasons a finished part might still not advance.

---

## Module 3: Recording Measurements

### Learning Objectives

By the end of this module, you will:

- [ ] Understand measurement requirements
- [ ] Enter measurement values correctly
- [ ] Recognize pass/fail indicators

### 3.1 Why Measurements Matter

**Concept:** Measurements prove that parts meet specifications. They're required for quality certification and customer confidence.

Types of measurements:

| Type | Example |
|------|---------|
| Dimensional | Length: 25.4 mm |
| Visual | Surface finish: Pass |
| Functional | Torque test: 15 Nm |
| Attribute | Color: Blue |

---

### 3.2 Entering Measurements

**Using the Quality Report form:**

1. Click **Quality Report** on a part
2. The quality report form opens
3. Fill in required fields:
   - Operator (your name)
   - Machine/equipment used
   - Measurement values
   - Status (pass/fail)
4. Submit the form

**Exercise 3.1:** Recording a Measurement

1. Find a part requiring measurement
2. Click **Quality Report**
3. Enter the measurement values
4. Set the appropriate status
5. Submit the form

---

### 3.3 Out-of-Tolerance Measurements

**Concept:** When a measurement is outside the acceptable range, the system alerts you.

**What to do:**

1. Verify your measurement (re-measure if needed)
2. If still out of tolerance:
   - The system may block advancing
   - Or require you to flag an issue
3. Notify your supervisor or QA

!!! warning "Don't Falsify Data"
    Always enter actual measured values. Entering false data is a serious violation that can affect product safety and company certifications.

---

### 3.4 Measurement Best Practices

- Use calibrated equipment
- Measure consistently (same method each time)
- Double-check unusual readings
- Ask if unsure about measurement method
- Record what you actually measure, not what you expect

---

### Knowledge Check: Module 3

1. Where do you enter measurements?
2. What should you do if a measurement is out of tolerance?
3. Why is it important to enter accurate measurements?

---

## Module 4: Reporting Quality Issues

### Learning Objectives

By the end of this module, you will:

- [ ] Recognize when to report a quality issue
- [ ] Create a quality report for a defective part
- [ ] Understand what happens after reporting

### 4.1 When to Report Issues

**Report a quality issue when:**

- Part has visible defect
- Measurement is out of spec
- Something doesn't look right
- You're unsure if part is good

**Don't ignore problems.** It's better to report and have QA verify than to let a bad part continue.

---

### 4.2 Creating a Quality Report for Issues

Issues are reported through the same **Quality Report** form used for measurements, but with a FAIL status.

**Steps:**

1. From your work order, find the part in the parts list
2. Click **Quality Report**
3. Fill in the form:
   - Select your name as Operator
   - Select the equipment/machine used
   - Set Status to **FAIL**
   - Select the Error Type that best matches the defect
   - Add a description of what you observed
4. Submit

**What happens:**

- Quality report is created with FAIL status
- Part may be quarantined depending on severity
- QA is notified
- Part cannot advance until resolved

**Exercise 4.1:** Reporting a Quality Issue

1. From your work order, find a part in the parts list
2. Click **Quality Report**
3. Set Status to FAIL
4. Select error type "Visual Defect"
5. Add description: "Training exercise - surface scratch observed"
6. Submit the report

---

### 4.3 After Reporting

Once you report an issue:

- **Your job is done** - QA takes over
- Part shows updated status (may be quarantined)
- QA will inspect and decide disposition
- You may be asked for more information

---

### Knowledge Check: Module 4

1. Give three examples of when you should report a quality issue.
2. How do you indicate a part has failed inspection?
3. Who decides what to do with a failed part?

---

## Module 5: Daily Workflow

### Learning Objectives

By the end of this module, you will:

- [ ] Understand a typical daily workflow
- [ ] Know where to find your work
- [ ] Follow best practices

### 5.1 Starting Your Shift

1. **Get your assignment** from your supervisor (work order number and operation)
2. **Log in** to uqmes
3. **Go to Work Orders** page
4. **Find your assigned work order** using search or filters
5. **Review any special instructions** in the work order details

!!! tip "Know Your Assignment First"
    Your supervisor tells you what to work on. The system helps you track progress and record quality data—it doesn't assign work to you.

---

### 5.2 During Production

As you work on your assigned work order:

1. **Open your work order** on the Work Orders page
2. **Complete your operation** on the parts
3. **Record measurements** as substeps inside the step player
4. **Complete the step** when your operation is done — parts advance on their own
5. **Flag any issues** immediately using the quality report function

**Stay in sync:** Complete steps as you finish them, not at end of shift — a lot can't advance until every part in it is done.

---

### 5.3 Best Practices

| Do | Don't |
|----|-------|
| Complete steps promptly | Wait until end of shift |
| Enter actual measurements | Guess or estimate |
| Flag issues immediately | Hope someone else notices |
| Ask when unsure | Make assumptions |
| Keep workstation organized | Let parts pile up |

---

### 5.4 End of Shift

Before leaving:

- [ ] All completed parts passed to next step
- [ ] Any issues flagged and communicated
- [ ] Work area organized
- [ ] Supervisor informed of any problems

---

## SPC Awareness

!!! tip "Additional Training: SPC Fundamentals"
    Complete the [SPC Fundamentals](spc-fundamentals.md) module (1-2 hours) to understand control charts and process variation.

### Why Operators Should Know SPC

Your measurements feed into SPC charts that help detect process problems early. Understanding SPC helps you:

- **Recognize when to alert QA** - Red-highlighted points mean something is wrong
- **Understand why consistent measurements matter** - They reveal true process behavior
- **Contribute to quality improvement** - Your data drives decisions

### What to Know

| If You See | What It Means | What To Do |
|------------|---------------|------------|
| Green chart | Process is stable | Continue working |
| Yellow warning | Process may be drifting | Pay closer attention |
| Red signals | Process is out of control | Stop and notify supervisor/QA |

### Demo Example

In demo mode, the Flow Rate measurement at Flow Testing shows an SPC violation. This type of alert would appear on your workstation dashboard, prompting you to notify QA Inspector Sarah Chen.

---

## Practical Assessment

Complete these tasks to demonstrate competency:

### Task 1: Part Tracking

1. Go to **Production** > **Work Orders** and open your assigned work order
2. Click **Start Work** and check a part
3. Work through the step's substeps, tapping **Confirm & next**
4. On the review screen, tap **Complete step**

### Task 2: Quality Report

1. From your work order, find a part in the parts list
2. Click **Quality Report**
3. Fill in measurements and status
4. Submit the form

### Task 3: Issue Reporting

1. From your work order, find a part
2. Click **Quality Report**
3. Set status to FAIL, select error type "Dimensional"
4. Add appropriate description and submit

### Task 4: Navigation

1. Go to **Work Orders** and use search to find a specific work order
2. View the work order details
3. Identify which parts are complete vs. in progress

---

## Training Completion

### Sign-Off Requirements

- [ ] Completed all modules
- [ ] Passed knowledge checks
- [ ] Completed practical assessment
- [ ] Supervisor verification

### Trainee Acknowledgment

By completing this training, I confirm that I:

- Understand how to use uqmes for my role
- Will enter accurate data
- Will flag quality issues promptly
- Will ask for help when needed

---

## Quick Reference Card

Print this for your workstation:

### Starting Work
1. Get assignment from supervisor → **Work Orders** → Find your work order

### Passing Parts (Batch)
1. Work Orders → Find work order → **Pass** → Select step → **Submit**

### Quality Report / In-Process Check
1. Work Orders → Find work order → Find part → **Quality Report** → Fill form → **Submit**

### Reporting Issues
1. From work order → Find part → **Quality Report** → Set FAIL status → Select error type → Describe → **Submit**

### Need Help?
- Check the part's current step and requirements
- Ask your supervisor
- Contact QA for quality questions

---

## Next Steps

After completing this training:

1. Practice in training environment
2. Shadow experienced operator
3. Begin supervised production work
4. Full independent work after sign-off

