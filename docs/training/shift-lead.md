# Shift Lead Training Guide

**Duration:** 4-5 hours
**Prerequisites:** [Operator training](operator.md), completed and signed off
**Goal:** Run a shift — read its state, put people on jobs, triage what stops,
make the calls only you can make, and hand over cleanly

!!! note "Role Name"
    This training is for the **Shift Lead** role in the system.

!!! info "Demo Environment Login"
    **Email:** casey.dual@demo.ambac.com
    **Password:** `demo123`

    Casey Cross is seeded deliberately as a dual-role persona — *"Inspector by
    day, Shift Lead when covering"*. Logging in lands you on the **QA Inspector**
    home. Use the **Switch landing** picker at the top to choose **Shift Lead**.

!!! warning "This guide assumes Operator training"
    Claiming work, running substeps, recording measurements and flagging issues
    are in the [Operator guide](operator.md) and are not repeated here.

---

## Module 1: Your Shift at a Glance

### Learning Objectives

1. Read the Shift Lead home and act from it
2. Find what is going late without hunting
3. Understand why you may land on a different page than you expect

### 1.1 The landing picker

You may hold more than one role. Casey holds **Shift Lead and QA Inspector**, and
the system lands her on whichever persona she last chose — **stored per user**,
so two people in the same group can legitimately see different home pages.

!!! important "Three things that follow"
    - A person can hold **several roles**. Guides that read as though you have
      exactly one are simplifying.
    - **Landing is a choice and it persists.** "Everyone with role X sees Y" is
      not true.
    - The picker may offer a role you are **not** a member of — Casey is offered
      **Operator**. That is a *supervisory preview*: it grants the **view**, not
      the permissions. Seeing the Operator landing does not let you do operator
      actions.

### 1.2 The hero

One screen, and **every number is a link into the thing it counts**:

| Block | What it answers |
|-------|-----------------|
| **Biggest fire** | The single job most needing you, with days overdue and a direct link to its control center |
| **Work orders** | Everything open, newest first, each with **Open** |
| **Jobs going late** | What will miss, flagged **Overdue** |
| **Needs attention** | Parts in quarantine · CAPAs pending verification |
| **Outside processing** | Out at vendors · Ready to ship |
| **Training** | Current · Expiring soon · Expired |

A live example, walked 2026-10-12:

> **Biggest fire** — WO-SHOWCASE-01, high, **3 days overdue** · *Open control center*
> **Work orders 12** · **Jobs going late 2** · **Needs attention 2**
> Parts in quarantine **13** · CAPAs pending verification **3**
> Outside processing: out at vendors 1, ready to ship 1
> Training: current **22**, expiring soon **1**, expired **1**

There is also a **scan box** — type or scan a work order, serial, lot or location
to jump straight to it.

### 1.3 Watching what is going late

Two surfaces, and you want both:

- **Jobs going late** on the home page — the short list, with *Overdue* badges
- The **Control Center** filters — **Due today**, **Overdue**, **Expedited**

### Knowledge Check: Module 1

1. You log in and see the QA Inspector page. What happened, and what do you do?
2. Your picker offers Operator but you are not an operator. Why?
3. Where do you look for everything overdue, rather than just the worst one?

---

## Module 2: Triage — the Exceptions Tab

### Learning Objectives

1. Work the unified exception list
2. Decide what to handle and what to escalate
3. Explain why this is a lead's view rather than a quality view

### 2.1 Where it lives

**WO Control Center** (`/workorders`) → the **Exceptions** tab. It carries a
count beside it, so you know before you click.

### 2.2 What a row tells you

Walked 2026-10-12 — **Unified · 22 items**, each carrying:

- **Source** — Quarantine, CAPA
- **Severity** — LOW / HIGH
- **State** — In Progress, Pending Verification
- **Age** — *357h ago*, *142h ago*
- **Owner** — Sarah Chen, Maria Santos, or *—* when unowned
- The finding itself — *"Flow rate 138 mL/min - SPC rule violation detected"*
- **Impacts 1 WO: WO-2024-0038-A** — a button straight to the job
- **Open disposition** — the action

!!! tip "\"Impacts N WO\" is the whole point"
    A quality view lists findings. **A lead's view lists findings with the job
    they are stopping.** That column is what lets you triage by production
    impact rather than by severity alone.

### 2.3 Working the list

- **Open only** — hide what is already settled
- **All sources** / **Any severity** / **Oldest first** — narrow and sort
- **Select all open** plus **Bulk resolve downtime** — clear a batch at once
- **Report exception** — raise something the list does not already know about

### 2.4 Unblocking a stopped job

Most of what you do here is not "manage quality" — it is **get a stopped job
moving again**. The Exceptions tab is the fastest route because it is the only
place that pairs the blocker with the job it is blocking.

The working order:

1. Find the exception impacting the job — the **Impacts N WO** button takes you
   straight there
2. Identify **what kind** of blocker it is, because that decides who clears it

| Blocker | Who clears it |
|---------|---------------|
| A disposition waiting on a decision | You can **close** it; **approving** it is QA Manager |
| A manual decision point | You |
| The record says the operator isn't qualified | You authorise it (second supervisor signs in) — then enter the record |
| A missing first-piece buy-off | You |
| A lot held at receiving for missing paperwork | The dock, by supplying it |
| A lot held on a **judgement** (unqualified supplier) | QA Manager |
| No operator assigned | Dispatch, or assign by hand on the board |
| Material short | Your planner / buyer |

!!! tip "Say what you did, not just that you did it"
    A job that stops twice for the same reason is a pattern. Note the cause in
    the handover even when you cleared it in two minutes — that is how the second
    occurrence gets noticed as a CAPA rather than as bad luck.

### 2.5 Escalating

**Report exception** is also how you escalate what the shift cannot solve. An
item you raise carries the same source and severity fields, so it lands in the
same queue the rest of the plant is working.

!!! warning "Escalate the thing, not the feeling"
    A raised exception is read by people who were not on your shift. Name the
    job it impacts and what you already tried.

### Knowledge Check: Module 2

1. Two findings: one HIGH severity impacting nothing, one LOW impacting a job due
   today. Which do you work first, and what told you?
2. What does *Open only* hide?
3. How do you raise something that is not already in the list?

---

## Module 3: Putting People on Jobs

### Learning Objectives

1. Reassign work on the schedule board
2. Cover an absence
3. Know exactly where your schedule authority stops

### 3.1 Finding the board

**Scheduling → Schedule (Gantt)**, or `/production/schedule`.

!!! tip "The sidebar groups start collapsed"
    **Scheduling**, **Supply** and **Remanufacturing** are collapsed by default,
    so they look empty until you click the heading. If you cannot find the board,
    that is usually why.

### 3.2 What you can do

The board shows every resource as a lane — Assembly Cell, CNC Lathe, Teardown
Bay, Flow Test Stand, OSP Dispatch — with each task as a draggable bar carrying
its work order and step.

You can **drag**, **pin**, **reassign** and **dispatch**. Clicking a task opens a
panel with its work order, due date, machine, work centre, operator, start/end,
**fence zone** (Frozen / Slushy / Liquid), live status and material state.

!!! important "The operator picker is filtered by eligibility"
    It offers only people qualified and rostered for that work centre — not a
    flat list of everyone. Covering an absence is therefore a short list, and the
    shortness is information: if it is empty, this is a **training** problem, not
    a scheduling one.

Reassign is honest about what it does: *"Reassign — applies now, re-solve to
optimize."*

### 3.3 Where your authority stops

Walked as Casey 2026-10-12 — the toolbar offers **Not scheduled**, **New WO**,
**Undo** and **Dispatch**. It does **not** offer **Solve** or **What-if**.

!!! warning "You can work the board; you cannot re-plan the shop"
    Running and committing a solve needs `add_scheduleresult` — **Planner**,
    **Production Manager** or **Tenant Admin**. So does authoring what the solver
    believes: shifts, calendars, changeovers, rostering.

    If Solve and What-if are not there for you, that is the design, not a fault.

### 3.4 Reading the header

Even without Solve, the header tells you the state of the plan:

> FEASIBLE · within 99% · **569 tasks** · makespan 315.9 h · lateness 844,620
> (priority-wtd) · solved in 181439 ms (machine 72572 · people 108867 ms) ·
> ⏰ **2 late order(s)** · **stale — re-solve**

!!! note "\"stale — re-solve\" is a hint, not an alarm"
    It means the world changed under the plan — new demand, a cancelled job, lost
    capacity. It is **deliberately not** tripped by routine step advances, because
    a flag that is always on means nothing. Tell your planner; don't work around it.

### Knowledge Check: Module 3

1. Someone has not turned up. Walk through covering their first job.
2. The operator picker is empty for a step. What kind of problem is that?
3. The board says *stale — re-solve* and you have no Solve button. What do you do?

---

## Module 4: Qualification

### Learning Objectives

1. Override the training gate correctly
2. Record a qualification so the override stops being needed
3. Find who is qualified for what

### 4.1 The gate

An operator the **record** says isn't qualified is warned and stopped at claim or
work-start, with the missing training named. In the demo, **Dave Wilson's Flow
Testing Certification expired on 2026-09-23**, and he is blocked from that step.

!!! important "The gate reads the record, not the person"
    A certification earned on Friday and not yet entered looks exactly like one
    that was never earned. The gate can only see what is recorded — which is why
    the override exists.

### 4.2 Authorising it

The usual case is the honest one: **they are trained, the system doesn't know
yet.** You authorise the start, and then the record catches up.

!!! note "It already takes two people"
    You cannot wave this through from the operator's screen. A **supervisor signs
    in separately** — the dialog says *"logged against their name"* — so the
    authorisation carries a second person, a reason and a timestamp, recorded on
    the step execution itself.

    That second signature is the control. It is not a confession.

!!! tip "Then close the loop"
    An override that is never followed by a training record is the thing worth
    noticing — not the override itself. If someone is genuinely trained, enter it,
    and the next shift doesn't need a supervisor at all.

### 4.3 The real fix

You can **write training records**, which is how someone stops needing the
override. That is deliberately not an operator permission — it used to be, and it
let people certify themselves.

| Field | Set it to |
|-------|-----------|
| **Training type** | The qualification being awarded |
| **Completed date** | The date of the assessment, not today |
| **Level** | The competency level actually demonstrated |
| **Trainer** | Whoever conducted and assessed it |
| **Expires** | Blank only if the qualification genuinely never lapses |

!!! note "Level is an assessed result, not attendance"
    Recording everyone at the same level because they sat the course defeats the
    control, and the training matrix supervisors plan from becomes fiction.

### 4.4 Seeing the coverage

The **training matrix** shows who is qualified for what, and the home page
summarises **current / expiring soon / expired**. Expiring is the one to work —
expired is already costing you.

See [Training Matrix](../workflows/tracking/training-matrix.md).

### Knowledge Check: Module 4

1. Where is an override reason stored?
2. Dave needs to run Flow Testing tonight. Two options — which is better and why?
3. Why can't an operator write their own training record?

---

## Module 5: The Calls That Are Yours

### Learning Objectives

1. Name the calls an operator cannot make, and make them
2. Tell a MANUAL decision point from a QA_RESULT one

### 5.1 The list

| Call | Why it isn't the operator's |
|------|------------------------------|
| **Sign off a First Piece Inspection** | Buying off the first part commits the rest of the run |
| **Resolve a manual decision point** | Choosing the routing branch changes where the unit goes |
| **Close a disposition** | Ends a nonconformance's open state |
| **Accept or reject a harvested component** | Puts a used part back into customer product, or destroys it |

### 5.2 First piece buy-off

FPI exists so the person who **ran** the first piece is not the person who
**approves** it. Review the measurements *and the setup*, then pass, fail or
waive — with a reason.

!!! warning "Waiving is not passing"
    A waiver records that the check was **not performed**. It shows on the
    traveller and to an auditor. Use it when the check genuinely does not apply.

Fail it when the setup is wrong even if the first piece happens to be in
tolerance — an in-tolerance part off a wrong setup is luck, and the rest of the
run will not share it.

### 5.3 Decision points

| Kind | Who resolves it |
|------|-----------------|
| **QA_RESULT** | Nobody — it routes automatically from the quality report |
| **MANUAL** | You, or QA / Production Manager |

If a step looks stuck at a decision, check which kind it is before looking for a
person. A QA_RESULT point is waiting on the **inspection**, not a signature.

### Knowledge Check: Module 5

1. Why can't the operator who ran the first piece buy it off?
2. A decision point has sat for an hour. How do you tell if it is waiting on you?

---

## Module 6: Handover

### Learning Objectives

1. Write a shift note the next crew can act on
2. Use audience, priority and acknowledgement

### 6.1 Shift notes are a real handover tool

They are **not** a free-text scratchpad. They carry **audience targeting**,
**priority**, and **acknowledgement tracking** — so you can tell whether the next
shift actually read the thing that mattered.

**Good note:** names the job, what happened, what the next shift should do.
**Poor note:** "Had problems on the line."

!!! warning "A shift note is not a quality record"
    A nonconformance goes in a quality report. A note saying "a few parts looked
    off" instead of raising an NCR hides the finding from every system that would
    otherwise act on it.

See [Shift Notes](../workflows/tracking/shift-notes.md).

### 6.2 Raising a CAPA

When something needs more than a disposition — a recurring defect, a process
producing the same finding repeatedly — you can **initiate a CAPA**. Initiating
is not owning. See [CAPA Overview](../workflows/capa/overview.md).

### Knowledge Check: Module 6

1. What does acknowledgement tracking get you that a whiteboard doesn't?
2. When does a repeated defect stop being a disposition and become a CAPA?

---

## Module 7: Remanufacturing Decisions

!!! info "Skip this module if your shop does not reman"

### Learning Objectives

1. Decide a pending finding
2. Request customer authorisation for over-and-above work
3. Decide a torn-down unit's exit

### 7.1 Pending findings

A finding raised at the bench after teardown waits for you on the
**Pending findings** card:

> *"1 finding to decide — Raised at the bench after teardown. Nothing below has
> changed the plan yet — applying one re-grades the component, and this plan
> re-resolves from it."*

A real one: **Injector Body, Grade A → B**, *"Light pitting on the seat face,
visible only after cleaning"*, attributed with a timestamp.

**Apply** re-grades the component and the rebuild plan re-resolves from it.
**Dismiss** takes a reason. Either way the decision is appended to the
component's notes as a trail.

### 7.2 Over-and-above

From a unit in rebuild, **Authorise…** sets it to *Awaiting customer
authorisation*.

!!! note "It refuses when there is nothing to authorise"
    If nothing in the resolved scope exceeds the rebuild level that was sold, you
    get *"Nothing on … goes beyond the rebuild level that was sold, so there is
    nothing to authorise"*. That is the system comparing scope against the sold
    preset — not a fault.

!!! warning "uqmes does not price this"
    It produces the **scope** — what work, what parts, the finding behind each —
    and records the customer's answer. The price happens in the system that owns it.

### 7.3 A core's exit

A **DISASSEMBLED** core waits on hold until you choose its exit. What you are
offered depends on how the unit is being fulfilled:

**Repair and return** — one button, **Release to rebuild**. It is the customer's
own unit, so rebuilding is the only exit. The server refuses a harvest: you
cannot give away a unit that belongs to somebody else.

**Exchange** — two exits, because the unit belongs to the shop:

- **Rebuild to stock** — identity kept, stocked as reman finished goods
- **Harvest for parts** — components accepted as stock, the core consumed

!!! warning "The same harvest exit is labelled two different ways"
    On the unit's own work screen the button reads **Harvest for parts**; on the
    work order's cores card it reads **Release to inventory**. They are the same
    operation with the same result. Do not go looking for a third exit.

**Return** is *not* an exit from Disassembled. It dispatches an already-rebuilt
or scope-declined unit back to its customer.

!!! danger "Harvest ends the unit"
    It becomes *Dismantled* — terminal, and explicitly not counted as output.
    Choose it when the body has failed or cores of that type are in surplus, never
    when you are unsure.

### Knowledge Check: Module 7

1. You apply a grade change from A to B. What else moves?
2. **Authorise…** refuses. What does that tell you?

---

## Module 8: Edge Cases and Honest Limits

### Learning Objectives

1. Expedite a job, and know what is not recorded
2. Take a machine out of service
3. Know what you cannot do

### 8.1 Jumping a job to the front

**There is no Expedite button.** *Expedited* is **derived** — it means the work
order's priority is **Urgent**. To jump a job, set its priority on the work
order; the Control Center's **Expedited** tile counts it.

!!! warning "\"With a reason\" is not supported here"
    There is no reason field on the work order's priority. `django-auditlog`
    records **who, when and what** — `priority: 2 → 1`, actor, timestamp — but
    **not why**.

    That is a real inconsistency: hold, scrap, reject, ship-back and rollback all
    take a reason. Priority does not. Put your justification in a **shift note**
    so it survives, and know the audit trail will not carry it for you.

### 8.2 A machine out of service

You hold `change_equipments`, so you can take a machine down. **Re-planning
around it is a solve**, which is your planner's job — tell them, because the
board will not re-optimise on its own.

### 8.3 What you deliberately don't hold

| Not yours | Whose |
|-----------|-------|
| **Void a substep completion** | QA Inspector, QA Manager, Tenant Admin |
| **Approve a disposition** | QA Manager |
| **Reject a whole lot (VDMR)** | QA |
| **Solve / commit a schedule** | Planner, Production Manager, Tenant Admin |
| **Author processes or routings** | Engineering, QA Manager, Production Manager, Document Controller, Tenant Admin |
| **Cancel a work order** | Production Manager, Tenant Admin |

!!! note "Voiding a sign-off is a quality judgement, not a production override"
    It is withheld from Shift Lead *and* Production Manager on purpose. You can
    correct the work; the quality record is corrected by quality.

    **If you also hold QA Inspector** — as Casey does — you *can* void, but you
    are doing it as an inspector, not as a lead. Know which hat you have on.

### Knowledge Check: Module 8

1. You expedite a job. Where does your reason end up?
2. You also hold QA Inspector and void a completion. Which role did that?

---

## Practical Assessment

Each task maps to a workflow a shift lead must be able to perform.

### Task 1: Read your shift (row 1)
From the Shift Lead home, name the biggest fire, how overdue it is, how many jobs
are going late, and how many people have expired training. Open the biggest fire.

### Task 2: Triage (rows 4, 6)
On the Exceptions tab, find the oldest open item, say which work order it impacts,
and justify whether it goes before or after a higher-severity item impacting
nothing.

### Task 3: Escalate (row 10)
Raise an exception for something the list does not know about. State who will
read it.

### Task 4: Cover an absence (rows 2, 3)
On the schedule board, reassign a task to a different operator. Report how many
people the picker offered and why it was not everyone.

### Task 5: Authorise past the training gate (row 5)
Using Dave Wilson's expired Flow Testing certification, attempt to start the work,
then authorise it with a reason. Find where your reason was recorded.

### Task 6: Fix it properly (row 9)
Create the training record that removes the need for that override. Set the level
to what was actually demonstrated.

### Task 7: Buy off a first piece
Review a pending FPI — measurements **and** setup — then pass or fail it with a
reason, and explain your decision.

### Task 8: Hand over (row 8)
Write a shift note for a job that did not go to plan, targeted at the right
audience. Your assessor should be able to act on it without asking you anything.

### Task 9: Expedite, and notice the gap (row C1)
Raise a work order to Urgent. Confirm the Expedited tile counts it, then say where
your justification lives and why.

### Task 10 (reman only): Decide an exit (rows R1, R3)
Apply or dismiss a pending finding, then choose a disassembled core's exit and
state what the fulfilment type allowed and ruled out.

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

- Will triage by production impact, not severity alone
- Will give a real reason on every override, and record it where it survives
- Will raise quality findings as quality records, not as notes
- Understand which calls are mine, and will ask when one is above my authority

### Recording the qualification

Ticking the boxes above is the *assessment*, not the record. Create a **Training
Record** under **Quality** > **Training**, as in [Operator
training](operator.md#recording-the-qualification).

---

## Quick Reference Card

### Start of shift
1. Shift Lead home — biggest fire, jobs going late, training expired
2. Control Center → **Exceptions**, *Open only*, *Oldest first*
3. Schedule board — anything uncovered

### Yours to decide
- FPI buy-off (pass / fail / waive — always with a reason)
- Manual decision points
- Close a disposition
- Accept or reject a harvested component
- Training-gate override (logged, with a reason)
- Reman: pending findings, over-and-above, core exit

### Not yours
- Void a substep completion → QA
- Approve a disposition → QA Manager
- Reject a whole lot → QA
- Solve / commit the schedule → Planner or Production Manager
- Cancel a work order → Production Manager

### Gotchas
- Sidebar groups start **collapsed**
- *Expedited* is derived from **priority = Urgent**; there is **no reason field**
- *stale — re-solve* needs your planner, not you
- An empty operator picker is a **training** problem

---

## Next Steps

- [Shift Lead role guide](../roles/shift-lead.md)
- [Shift Notes](../workflows/tracking/shift-notes.md)
- [First Piece Inspection](../workflows/work-orders/fpi.md)
- [Training Matrix](../workflows/tracking/training-matrix.md)
- [Schedule (Gantt)](../workflows/scheduling/gantt.md)
- [SPC Fundamentals](spc-fundamentals.md) — recommended for all floor supervision
