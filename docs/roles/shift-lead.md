# Shift Lead

**The floor supervisor.** You run work like an operator, and on top of that you
see the whole shift and carry the calls an operator can't make alone.

!!! info "Shift Lead is Operator plus authority"
    Everything in the [Operator guide](operator.md) applies to you — claiming
    work, running substeps, recording measurements, flagging issues. This page
    covers only what you hold *in addition*.

    Roles compose. Holding Shift Lead alongside QA Inspector is normal and the
    permissions add up rather than conflicting.

## The calls that are yours

An operator runs the work; you settle what the work runs into.

| Call | Where | Why it isn't the operator's |
|------|-------|------------------------------|
| **Sign off a First Piece Inspection** | The step's FPI panel | Buying off the first part commits the rest of the run |
| **Resolve a manual decision point** | The step, when it asks for a branch | Choosing the routing branch is a supervisor call |
| **Close a disposition** | [Dispositions](../workflows/quality/dispositions.md) | Ends a nonconformance's open state |
| **Accept or reject a harvested component** | [Components](../workflows/reman/components.md) | Puts a used part back into customer product, or destroys it |
| **Override the training gate** | At claim / work-start | Nobody clears their own competency gap |
| **Clear somebody else's unsubmitted signature** | The substep they signed | Unblocks work when the signer has gone home |
| **Apply a cycle count** | [Locations & Cycle Counts](../workflows/supply/locations.md) | Counting is the counter's job; changing stock on the strength of it isn't |
| **Approve operators' time** | [Operator Hours](../workflows/scheduling/overview.md#approving-time) → *Awaiting approval* | Nobody approves their own hours |

!!! note "Clearing a signature is narrower than it sounds"
    A signature inside a substep is **provisional until the substep is
    submitted** — the person who signed can always undo their own, no permission
    needed. Yours is the other case: an operator signs a block, goes off shift,
    and the work has to move.

    **Once the substep is submitted this stops applying.** The signature is part
    of the record then, and retracting it is a void — which is QA's, not yours.
    See *What you deliberately don't hold*.

!!! note "Counting and applying are deliberately two people"
    Anyone on the dock can run a count, including a blind one. **Applying** it —
    writing the difference onto the stock figure — is a lead's. The differences
    export as a spreadsheet for keying into the ERP.

!!! note "A QA_RESULT decision point needs nobody"
    Decision points that route from a quality result resolve themselves from the
    QualityReport. Only **MANUAL** ones wait for you.

## The training gate

An operator the **record** says isn't qualified gets a warning and a stop. You
can authorise it — and the common reason is the honest one: *they are trained,
the system doesn't know yet.*

!!! important "The gate reads the record, not the person"
    A certification earned on Friday and not yet entered looks identical to one
    that was never earned. The gate can only see the record, so the override
    exists for the case where you know better.

!!! note "It already takes two people"
    You can't wave it through from the operator's screen. A **supervisor signs in
    separately** to authorise — *"logged against their name"* — so the
    authorisation carries a second person, their reason and a timestamp, recorded
    on the step execution. It shows afterwards as an amber line on the part's
    traveller, under that step.

    Then **enter the training record**, so the next person doesn't need you.

You can also **write training records**, which is how someone stops needing the
override. That is deliberately not an operator permission — an operator who could write
training records could certify themselves. See [Training
Matrix](../workflows/tracking/training-matrix.md).

## Your shift's board

You can **move, pin, reassign and dispatch** scheduled tasks — the Gantt's
direct-manipulation verbs — so you can run your shift against reality without
waiting on a planner.

!!! warning "You can work the board; you cannot re-plan the shop"
    **Running and committing a solve** is [Planner](planner.md), Production
    Manager or Tenant Admin. So is authoring what the solver believes — shifts,
    calendars, changeovers, rostering.

    If Solve and Commit aren't there for you, that is the design, not a fault.

## Pushing a job up the queue

There is **no Expedite action**. Jumping a job to the front means setting the
work order's **priority** to **Urgent** — *Expedited* on the control centre is
not a state you set, it is simply what priority Urgent looks like.

!!! important "A priority change asks why, and keeps the answer"
    Changing priority on **Data Management > Work Orders > edit** requires a
    reason — *"Why change priority from Normal to Urgent?"* — and will not save
    without one. The reason is stored with the change, and the edit form lists
    the last five: *Normal → Urgent · who, when*, with the reason beneath.

    So the trail answers *what, who, when* **and** *why*. Setting a priority when you first create the work order needs no
    reason; there is nothing to explain yet.

!!! note "Changing priority by import"
    A CSV import or the master workbook's **Work Orders** sheet asks the same:
    put the reason in a `priority_reason` column beside `priority`. A row that
    changes priority without one is refused, and the reason is kept with the
    change as it is from the edit form.

## Speaking to the next shift

**Shift notes** are yours to write and edit — the handover record for what the
next crew needs to know. See [Shift Notes](../workflows/tracking/shift-notes.md).

## Raising a CAPA

You can **initiate a CAPA** when something needs more than a disposition — a
recurring defect, a process that keeps producing the same finding. Initiating is
not owning it; see [CAPA Overview](../workflows/capa/overview.md).

## What you deliberately don't hold

| Not yours | Whose |
|-----------|-------|
| **Void a substep completion** | QA Inspector, QA Manager, Tenant Admin |
| **Reject a whole lot (VDMR)** | QA Manager, Tenant Admin |
| **Approve a disposition** | QA Manager |
| **Solve / commit a schedule** | Planner, Production Manager, Tenant Admin |
| **Author processes, BOMs, specs** | Engineering, QA Manager, Production Manager, Document Controller, Tenant Admin |
| **Cancel or short-close a work order** | Production Manager, Tenant Admin |
| **Approve a gate bypass** | QA Manager, Tenant Admin — you can *request* one from the part's page |

These are the default groups an organisation starts with. Group permissions can be changed, so check your own in [Roles & Groups](../admin/users/roles.md).

!!! note "Voiding a sign-off is a quality judgement, not a production override"
    Retracting a record of work someone else signed is withheld from Shift Lead
    *and* Production Manager on purpose. You can correct the work; the quality
    record is corrected by quality.

## Previewing your floor

Home shows you the **Operator** landing as well as your own, so you can see what
your crew sees. See [Role Guides](index.md#your-home-page-follows-your-role).

## If you got something wrong

Most floor corrections are yours, each with a reason:

- A part moved on too soon: **Previous step**. A wrong part in a shared cycle:
  **Take this part out**. Past the step's window, both go to QA for approval.
- A draw against the wrong lot: **Wrong lot?** on that lot's page.
- Clock times: **Correct times**, before you approve them.
- Downtime recorded wrong: **Correct…** in Exceptions.
- An override you shouldn't have given: **Flag for QA review**.
- A hold placed in error: **Resume**, and say so.

The full list, including what isn't yours, is [Putting a Mistake
Right](../workflows/fixing-mistakes.md#on-the-floor).

## Next Steps

- [Operator](operator.md) — the base this role builds on
- [Shift Notes](../workflows/tracking/shift-notes.md)
- [First Piece Inspection](../workflows/work-orders/fpi.md)
- [Training Matrix](../workflows/tracking/training-matrix.md)
- [Dispositions](../workflows/quality/dispositions.md)
