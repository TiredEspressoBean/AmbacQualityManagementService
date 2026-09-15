# Production Operator Training Guide

**Duration:** 2-4 hours
**Prerequisites:** None
**Goal:** Learn to track parts through production steps and record measurements

!!! abstract "Curriculum revision"
    **Rev A — 2026-09-15.** Cite this revision on the training record, so the
    competence evidence names what was actually taught. Reference documentation
    changes continuously; this curriculum is revised deliberately.


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

### 2.4 Where Quality Data Goes

**Concept:** You do not raise quality records separately from your work. The
substeps you complete *are* the quality record.

When a step carries an **inspection point** substep, what you record there —
the pass/fail status, any defects against their error types, your signature —
is written as a Quality Report as well as a substep completion. One entry,
both records.

!!! warning "There is no Quality Report button on a part"
    Older instructions described clicking **Quality Report** on a part in the
    parts list. That button does not exist. Quality data is captured in the
    step player, and issues found outside it are raised from the work order —
    see Module 4.

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

Measurements are **substeps in the step player**. You reach them by working the
step, not by opening a form against a part.

**Steps:**

1. Work through the step's substeps until you reach a measurement capture
2. Read the specification shown with it
3. Enter the measured value
4. The system evaluates it against the spec immediately and shows pass or fail
5. Tap **Confirm & next**

The value is sealed when you confirm it. Your name, the timestamp, and the
equipment in play are recorded with it — that is what makes it usable as
evidence later.

**Exercise 3.1:** Recording a Measurement

1. Start work on a part and work to a measurement substep
2. Enter the measured value
3. Note whether the system shows pass or fail, and the spec it used
4. Tap **Confirm & next**

**Expected result:** The value is recorded against the part and the player
advances to the next substep.

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

### 4.2 How to Raise an Issue

Where a problem goes depends on where you find it. Full detail:
[Flagging Issues](../workflows/tracking/flagging-issues.md).

| Where you are | What to do |
|---------------|------------|
| Working the step, and it has an inspection substep | Record the fail status and the defect there, then confirm |
| The part is past that step | Tick it in the parts list, click **Quarantine** |
| The problem is the machine, the batch, or the process | Open the work order, click **Report…** |

**Quarantining from the parts list:**

1. Open the work order's **control** page
2. Tick the affected part or parts
3. Click **Quarantine**

!!! warning "Quarantine applies to everything you ticked"
    It is a bulk action on the selection, not on one row. Check what is ticked
    before you click, or you will hold parts nobody meant to hold.

**Exercise 4.1:** Reporting a Quality Issue

1. Open your work order's control page
2. Tick one part in the parts list
3. Click **Quarantine**
4. Confirm the part's status changes to Quarantined
5. Open the work order's **Report…** dialog and look at the three exception
   types available — do not submit one

**Expected result:** The part is held, and you have seen where process-level
exceptions are raised.

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

### Task 2: Recording a Measurement

1. Start work on a part and work to a measurement substep
2. Enter the measured value
3. Confirm the system evaluated it against the specification
4. Tap **Confirm & next**

### Task 3: Issue Reporting

1. Open your work order's **control** page
2. Tick one part in the parts list
3. Click **Quarantine**
4. Confirm the part now shows as Quarantined and explain, to your assessor,
   why the rest of its lot is affected

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

## Quick Reference Card

Print this for your workstation:

### Starting Work
1. **Production** → **Work Orders** → open your work order
2. **Start Work** → in **Start work on parts**, check your parts *in the order
   you'll work them* → Confirm

### Completing a Step
1. The player shows **one substep at a time**
2. Do the work, record what it asks for, tap **Confirm & next**
3. The part advances when its required substeps are done

!!! warning "There is no Pass button"
    Parts are not passed along by hand. Completing the required substeps is
    what moves a part — that is the whole mechanism. If a part hasn't moved,
    something is still outstanding on it or on another part in its lot.

### Recording a Measurement
1. Step player → measurement substep → enter value → **Confirm & next**

### Reporting Issues
1. In the player → record fail status + defect on the inspection substep
2. Part already past the step → tick it in the parts list → **Quarantine**
3. Machine, batch or process → open the work order → **Report…**

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

