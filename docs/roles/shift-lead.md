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

!!! note "A QA_RESULT decision point needs nobody"
    Decision points that route from a quality result resolve themselves from the
    QualityReport. Only **MANUAL** ones wait for you.

## The training gate

An operator who isn't yet qualified for a step gets a warning and a stop. You
can push it through — with a reason, which is **recorded on the step execution**
and stays there.

!!! warning "The override is logged, and that is the point"
    It is evidence under ISO 9001 §7.2 that the shop knowingly ran unqualified
    work and who authorised it. Use it when the job genuinely must move; don't
    use it as a way around a training backlog, because the record accumulates.

You can also **write training records**, which is how someone stops needing the
override. That is deliberately not an operator permission — it used to be, and
it let people certify themselves. See [Training
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
| **Reject a whole lot (VDMR)** | QA |
| **Approve a disposition** | QA Manager |
| **Solve / commit a schedule** | Planner, Production Manager, Tenant Admin |
| **Author processes, BOMs, specs** | Engineering, Document Controller |
| **Cancel a work order** | Production Manager |

!!! note "Voiding a sign-off is a quality judgement, not a production override"
    Retracting a record of work someone else signed is withheld from Shift Lead
    *and* Production Manager on purpose. You can correct the work; the quality
    record is corrected by quality.

## Previewing your floor

Home shows you the **Operator** landing as well as your own, so you can see what
your crew sees. See [Role Guides](index.md#your-home-page-follows-your-role).

## Next Steps

- [Operator](operator.md) — the base this role builds on
- [Shift Notes](../workflows/tracking/shift-notes.md)
- [First Piece Inspection](../workflows/work-orders/fpi.md)
- [Training Matrix](../workflows/tracking/training-matrix.md)
- [Dispositions](../workflows/quality/dispositions.md)
