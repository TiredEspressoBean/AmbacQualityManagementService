# Shift Lead Training Guide

**Duration:** 3-4 hours
**Prerequisites:** [Operator training](operator.md), completed and signed off
**Goal:** Learn the supervisory calls a Shift Lead owns — buy-offs, routing
decisions, training overrides, handover, and running the board for your shift

!!! note "Role Name"
    This training is for the **Shift Lead** role in the system.

!!! info "Demo Environment Login"
    **Email:** casey.dual@demo.ambac.com
    **Password:** `demo123`

    Casey Cross holds **Shift Lead and QA Inspector** in the demo, which is the
    normal shape — roles compose. If the screen shows more than this guide
    describes, that is the inspector role, not an error.

!!! warning "This guide assumes Operator training"
    It covers only what Shift Lead adds. Claiming work, running substeps,
    recording measurements and flagging issues are all in the [Operator
    guide](operator.md) and are not repeated here.

---

## Module 1: What Changes When You Lead

### Learning Objectives

By the end of this module, you will:

1. Name the five calls a Shift Lead owns that an operator cannot make
2. Explain why each one sits above the operator
3. Recognise what a Shift Lead deliberately does **not** hold

### 1.1 The five calls

An operator runs the work. You settle what the work runs into.

| Call | Why it isn't the operator's |
|------|------------------------------|
| **Sign off a First Piece Inspection** | Buying off the first part commits the rest of the run |
| **Resolve a manual decision point** | Choosing the routing branch changes where the unit goes |
| **Close a disposition** | Ends a nonconformance's open state |
| **Accept or reject a harvested component** | Puts a used part back into customer product, or destroys it |
| **Override the training gate** | Nobody can clear their own competency gap |

### 1.2 What you do not hold

This matters more than the list above, because assuming you hold something you
don't produces a job that stalls while everyone waits for you.

| Not yours | Whose |
|-----------|-------|
| **Void a substep completion** | QA Inspector, QA Manager, Tenant Admin |
| **Approve a disposition** | QA Manager |
| **Reject a whole lot (VDMR)** | QA |
| **Run or commit a schedule solve** | Planner, Production Manager, Tenant Admin |
| **Author processes or routings** | Engineering |
| **Cancel a work order** | Production Manager |

!!! note "Voiding a sign-off is a quality judgement, not a production override"
    Retracting a record of work someone else signed is withheld from Shift Lead
    *and* Production Manager on purpose. You can correct the work; the quality
    record is corrected by quality.

### Knowledge Check: Module 1

1. An operator asks you to undo a substep they completed by mistake. Can you?
2. A disposition needs approving before the unit can move. Is that your call?
3. Which of the five calls applies when a step asks which branch to take?

---

## Module 2: First Piece Inspection

### Learning Objectives

1. Explain what an FPI buy-off commits you to
2. Perform a buy-off
3. Decide when to fail one

### 2.1 Why setup verification is independent

FPI exists so that the person who *ran* the first piece is not the person who
*approves* it. That independence is the control; it is why the permission sits
with the lead, QA and manager tier and not with the operator.

When you buy off a first piece you are stating that the setup is correct and the
rest of the run may proceed on that basis.

### 2.2 Doing a buy-off

1. Open the work order's step with a pending FPI
2. Review the recorded measurements against the specification
3. Check the setup itself, not only the numbers
4. Pass, fail, or waive — with a reason

!!! warning "Waiving is not passing"
    A waiver is a recorded decision that the check was not performed. It is
    visible on the traveller and to an auditor. Use it when the check genuinely
    does not apply, never to save time.

### 2.3 When to fail one

Fail it when the setup is wrong, even if the first piece happens to be in
tolerance. An in-tolerance part off a wrong setup is luck, and the rest of the
run will not share it.

See [First Piece Inspection](../workflows/work-orders/fpi.md).

### Knowledge Check: Module 2

1. Why can't the operator who ran the first piece buy it off?
2. What is the difference between failing and waiving?
3. The first piece measures inside spec but the fixture is loose. What do you do?

---

## Module 3: Decision Points

### Learning Objectives

1. Tell a MANUAL decision point from a QA_RESULT one
2. Resolve a manual decision point
3. Understand what your choice commits

### 3.1 Two kinds, and only one waits for you

| Kind | Who resolves it |
|------|-----------------|
| **QA_RESULT** | Nobody — it routes automatically from the quality report |
| **MANUAL** | You, or QA / Production Manager |

If a step appears stuck at a decision, check which kind it is before looking for
a person. A QA_RESULT point waiting on a quality report is waiting on the
inspection, not on a signature.

### 3.2 Resolving one

Open the step, read the branches offered, and choose. The choice routes the unit
— it is not a comment, and the next operator will work whatever you select.

### Knowledge Check: Module 3

1. A decision point has been sitting for an hour. How do you tell whether it is
   waiting on you?
2. Who else can resolve a manual decision point?

---

## Module 4: The Training Gate

### Learning Objectives

1. Explain what the training gate stops and why
2. Override it correctly
3. Record a qualification so the override stops being needed

### 4.1 What the gate does

An operator who is not qualified for a step is warned and stopped at claim or
work-start. In the demo, **Dave Wilson** has an expired Flow Testing
certification and is blocked from that step.

### 4.2 Overriding it

You can push it through **with a reason**. The reason is recorded on the step
execution itself and stays there.

!!! danger "The override is logged, and that is the point"
    It is evidence under ISO 9001 §7.2 that the shop knowingly ran unqualified
    work and who authorised it. Use it when the job genuinely must move. Don't
    use it as a way around a training backlog — the record accumulates, and an
    auditor reads the pattern, not the single entry.

### 4.3 The real fix

You can **write training records**, which is how someone stops needing the
override. That is deliberately not an operator permission — it used to be, and
it let people certify themselves.

| Field | Set it to |
|-------|-----------|
| **Training type** | The qualification being awarded |
| **Completed date** | The date of the assessment, not today |
| **Level** | The competency level actually demonstrated |
| **Trainer** | Whoever conducted and assessed it |
| **Expires** | Leave blank only if the qualification genuinely never lapses |

!!! note "Level is an assessed result, not attendance"
    Recording everyone at the same level because they sat the course defeats the
    control, and the training matrix supervisors plan from becomes fiction.

See [Training Matrix](../workflows/tracking/training-matrix.md).

### Knowledge Check: Module 4

1. Where is an override reason stored?
2. Dave Wilson needs to run Flow Testing tonight. What are your two options, and
   which is better?
3. Why can't an operator write their own training record?

---

## Module 5: Handover

### Learning Objectives

1. Write a shift note the next crew can act on
2. Know what belongs in a note and what belongs in a record

### 5.1 Shift notes

Shift notes are yours to write and edit. They are the handover record — what the
next crew needs to know that isn't already on a work order.

**Good note:** names the job, what happened, and what the next shift should do.

**Poor note:** "Had problems on the line."

!!! warning "A shift note is not a quality record"
    A nonconformance goes in a quality report, not a note. A note that says "a
    few parts looked off" instead of raising an NCR hides the finding from every
    system that would otherwise act on it.

See [Shift Notes](../workflows/tracking/shift-notes.md).

### 5.2 Raising a CAPA

When something needs more than a disposition — a recurring defect, a process
producing the same finding repeatedly — you can **initiate a CAPA**.

Initiating is not owning. See [CAPA Overview](../workflows/capa/overview.md).

### Knowledge Check: Module 5

1. What is the difference between a shift note and a quality report?
2. When does a repeated defect stop being a disposition and become a CAPA?

---

## Module 6: Running the Board for Your Shift

### Learning Objectives

1. Move, pin, reassign and dispatch scheduled work
2. Know where your authority stops

### 6.1 What you can do

You hold the Gantt's direct-manipulation verbs: **move, pin, reassign and
dispatch**. You can run your shift against reality without waiting on a planner.

Dragging a task ripples the rest of that unit's route with it. Two checks run
first — the schedule horizon and the work order's release date — and a pinned
successor stops a ripple and is named.

### 6.2 Where it stops

!!! warning "You can work the board; you cannot re-plan the shop"
    **Running and committing a solve** is Planner, Production Manager or Tenant
    Admin. So is authoring what the solver believes — shifts, calendars,
    changeovers, rostering.

    If Solve and Commit aren't there for you, that is the design, not a fault.

See [Who can touch the board](../workflows/scheduling/gantt.md#who-can-touch-the-board).

### Knowledge Check: Module 6

1. A machine goes down. Can you move its work to another machine yourself?
2. The whole week's plan is now wrong. Who re-solves it?

---

## Practical Assessment

### Task 1: Buy off a first piece
Find a work order with a pending FPI. Review the measurements and the setup,
then pass or fail it with a reason. Explain your decision to your assessor.

### Task 2: Resolve a decision point
Locate a manual decision point. Identify which branches are offered and why you
chose the one you did.

### Task 3: Override a training gate
Using Dave Wilson's expired Flow Testing certification, attempt to start the
work, then authorise it with a reason. Afterwards, find where your reason was
recorded.

### Task 4: Record a qualification
Create a training record that would remove the need for that override. Set the
level to what was actually demonstrated.

### Task 5: Write a handover note
Write a shift note for a job that did not go to plan. Your assessor should be
able to act on it without asking you a question.

### Task 6: Work the board
Move a task to a different resource and confirm what rippled. Then find
something you are *not* permitted to do and say who is.

---

## Training Completion

### Sign-Off Requirements

- [ ] Operator training completed and signed off
- [ ] Completed all modules
- [ ] Passed knowledge checks
- [ ] Completed practical assessment
- [ ] Supervisor verification

### Trainee Acknowledgment

By completing this training, I confirm that I:

- Understand which calls are mine and which are not
- Will give a real reason on every override and record it
- Will raise quality findings as quality records, not as notes
- Will ask for help when a decision is above my authority

### Recording the qualification

Ticking the boxes above is the *assessment*. It is not the record — create a
**Training Record** under **Quality** > **Training**, as in [Operator
training](operator.md#recording-the-qualification).

---

## Quick Reference Card

### Yours to decide
- FPI buy-off (pass / fail / waive — always with a reason)
- Manual decision points
- Close a disposition
- Accept or reject a harvested component
- Training-gate override (logged, with a reason)

### Not yours
- Void a substep completion → QA
- Approve a disposition → QA Manager
- Reject a whole lot → QA
- Solve / commit the schedule → Planner or Production Manager
- Cancel a work order → Production Manager

### Where things live
- **Shift notes** — handover
- **Quality > Training** — records and the matrix
- **Schedule (Gantt)** — move, pin, reassign, dispatch

---

## Next Steps

- [Shift Lead role guide](../roles/shift-lead.md)
- [First Piece Inspection](../workflows/work-orders/fpi.md)
- [Training Matrix](../workflows/tracking/training-matrix.md)
- [Shift Notes](../workflows/tracking/shift-notes.md)
- [SPC Fundamentals](spc-fundamentals.md) — recommended for all floor supervision
