# Operator Training Guide

**Duration:** 2-4 hours
**Prerequisites:** None
**Goal:** Learn to track parts through production steps and record measurements

---

## Module 1: System Basics

### Learning Objectives

By the end of this module, you will:

1. Log into Ambac Tracker
2. Navigate the main interface
3. Understand your role and permissions

### 1.1 Logging In

**Concept:** Ambac Tracker uses secure login to track who does what.

**Steps:**

1. Open your browser (Chrome recommended)
2. Go to your company's Ambac Tracker URL
3. Enter your email and password
4. Click **Sign In**

!!! tip "Single Sign-On"
    If your company uses SSO, click the SSO button and use your company credentials.

**Why it matters:** Every action you take is recorded with your name and timestamp for quality traceability.

---

### 1.2 The Tracker Page

**Concept:** The Tracker is your main workspace showing orders and parts.

**What you'll see:**

| Element | Purpose |
|---------|---------|
| Order cards | Each card is a customer order |
| Progress bar | Shows completion percentage |
| Search bar | Find specific orders or parts |
| Filters | Narrow down what you see |

**Exercise 1.1:** Finding an Order

1. Go to **Tracker**
2. Use the search bar to find order "TRAIN-001"
3. Click the order card to expand it
4. Note the order number, customer, and progress

**Expected result:** You see the order details and a list of parts.

---

### 1.3 Understanding Parts

**Concept:** Each order contains parts that move through production steps.

**Part information includes:**

- Serial number (unique identifier)
- Part type (what it is)
- Current step (where it is in the process)
- Status (in process, complete, on hold)

**Exercise 1.2:** Viewing Part Details

1. In the expanded order, find a part
2. Click the part row to see details
3. Note the serial number and current step

---

### Knowledge Check: Module 1

1. Where do you go to see orders and parts?
2. What does the progress bar on an order card show?
3. Why is it important that your actions are logged?

---

## Module 2: Moving Parts Forward

### Learning Objectives

By the end of this module, you will:

- [ ] Pass parts to the next step
- [ ] Understand step requirements
- [ ] Record that work is complete

### 2.1 The Step Process

**Concept:** Parts move through a defined sequence of steps. You pass a part to the next step when your work is done.

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

### 2.2 Passing Parts (Order-Level)

The primary way to move parts forward is at the order level, passing all parts at a specific step.

**Steps:**

1. Navigate to **QA Work Orders** page
2. Find your order in the table
3. Click the **Pass** button on the order row
4. The "Pass Part by Step" dialog opens
5. Select the step you completed (shows step name and part count)
6. Click **Submit**

**What happens:**

- All parts at that step move to the next step
- Your name and timestamp are recorded
- Progress updates automatically
- Toast message confirms: "Part passed to next step."

**Exercise 2.1:** Passing Parts

1. Go to **QA Work Orders**
2. Find order "TRAIN-001"
3. Click **Pass**
4. In the dialog, select the step showing parts you completed
5. Click **Submit**

**Expected result:** Parts move to next step, progress updates.

---

### 2.3 Individual Part Quality Reports

For individual parts requiring quality documentation:

**Steps:**

1. Find the part in the QA Parts table
2. Click the **Quality Report** button
3. Fill in the quality report form:
   - Operator
   - Machine/equipment used
   - Measurements
   - Pass/fail status
4. Submit the form

**When to use:** When you need to record detailed measurements or quality data for specific parts.

---

### 2.4 When Parts Can't Be Passed

A part cannot be passed if:

- Required measurements are missing
- You don't have training for that step
- The part is quarantined
- Previous step isn't complete

!!! note "Blocked Parts"
    If you can't pass a part, the system tells you why. Contact your supervisor if you need help.

---

### Knowledge Check: Module 2

1. What happens when you pass parts to the next step?
2. Where do you click the "Pass" button?
3. What might prevent parts from being passed?

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

## Module 4: Flagging Issues

### Learning Objectives

By the end of this module, you will:

- [ ] Recognize when to flag an issue
- [ ] Create a quality flag on a part
- [ ] Understand what happens after flagging

### 4.1 When to Flag

**Flag an issue when:**

- Part has visible defect
- Measurement is out of spec
- Something doesn't look right
- You're unsure if part is good

**Don't ignore problems.** It's better to flag and have QA verify than to let a bad part continue.

---

### 4.2 Creating a Quality Flag

**Steps:**

1. Select the part
2. Click **Flag Issue** (or flag icon)
3. Select the error type that best matches
4. Add description of what you observed
5. Submit

**What happens:**

- Part is quarantined
- QA is notified
- Part cannot advance until resolved

**Exercise 4.1:** Flagging a Part

1. Find part "TRAIN-003-001"
2. Click **Flag Issue**
3. Select error type "Visual Defect"
4. Add description: "Training exercise - surface scratch observed"
5. Submit the flag

---

### 4.3 After Flagging

Once you flag a part:

- **Your job is done** - QA takes over
- Part shows "Quarantine" status
- QA will inspect and decide disposition
- You may be asked for more information

---

### Knowledge Check: Module 4

1. Give three examples of when you should flag a part.
2. What happens to a part after you flag it?
3. Who decides what to do with a flagged part?

---

## Module 5: Daily Workflow

### Learning Objectives

By the end of this module, you will:

- [ ] Understand a typical daily workflow
- [ ] Know where to find your work
- [ ] Follow best practices

### 5.1 Starting Your Shift

1. **Log in** to Ambac Tracker
2. **Check your work area** for parts to process
3. **Find your orders** on Tracker
4. **Review any notes** or special instructions

---

### 5.2 During Production

As you work:

1. Complete your operation on the parts
2. Take required measurements
3. Pass parts to the next step in the system
4. Flag any issues immediately
5. Move to next batch

**Stay in sync:** Pass parts as you complete them, not at end of shift.

---

### 5.3 Best Practices

| Do | Don't |
|----|-------|
| Pass parts promptly | Wait until end of shift |
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

## Practical Assessment

Complete these tasks to demonstrate competency:

### Task 1: Part Tracking

1. Find order "ASSESS-001" on QA Work Orders
2. Click **Pass** on the order
3. Select the step with parts to pass
4. Submit

### Task 2: Quality Report

1. Find a part in the QA Parts table
2. Click **Quality Report**
3. Fill in measurements and status
4. Submit the form

### Task 3: Issue Flagging

1. Find part "ASSESS-003-002"
2. Flag it with error type "Dimensional"
3. Add appropriate description

### Task 4: Navigation

1. Use search to find order "ASSESS-004"
2. View the order details
3. Identify which parts are complete

---

## Training Completion

### Sign-Off Requirements

- [ ] Completed all modules
- [ ] Passed knowledge checks
- [ ] Completed practical assessment
- [ ] Supervisor verification

### Trainee Acknowledgment

By completing this training, I confirm that I:

- Understand how to use Ambac Tracker for my role
- Will enter accurate data
- Will flag quality issues promptly
- Will ask for help when needed

---

## Quick Reference Card

Print this for your workstation:

### Passing Parts (Batch)
1. QA Work Orders → Find order → **Pass** → Select step → **Submit**

### Quality Report (Individual)
1. QA Parts → Find part → **Quality Report** → Fill form → **Submit**

### Flagging Issues
1. Select part → **Flag Issue** → Select type → Describe → **Submit**

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

