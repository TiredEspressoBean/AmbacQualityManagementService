"""QA sign-off of a step for a work order — the step-level gate `requires_qa_signoff`.

`Steps.can_advance_from_step` blocks a QA-gated step until a `QaApproval` exists for
(step, work order). Until 2026-10-07 the only runtime path that created one was FPI
pass/waive (`services.qms.fpi._ensure_qa_approval`, whose docstring said as much:
"no other runtime path creates QaApproval records"). Any QA-gated step without first
piece inspection — reman Core Receiving, say — told the operator "awaiting QA
sign-off" while no inspector had anything to sign: the unit parked, invisibly.

- ``pending_signoffs`` — (work order, step) pairs waiting: units at a QA-gated step
  whose work has been submitted (a substep completion, or the step has no substeps),
  with no QaApproval yet. FPI-gated steps are left to their first-piece buy-off. Read by the inspector inbox and the work order page.
- ``sign_off_step`` — the inspector's act. Same authority as FPI buy-off
  (`sign_off_fpi`), refused to whoever signed the step's own substeps, then the lot
  is re-evaluated for advancement at once.
"""
from __future__ import annotations

from django.db.models import Count, Exists, Min, OuterRef


def pending_signoffs(work_order=None) -> list[dict]:
    """[{work_order_id, work_order, step_id, step, units, oldest_entered_at}] —
    QA-gated steps whose submitted work is waiting for a sign-off."""
    from Tracker.models import QaApproval, StepExecution, Substep, SubstepCompletion
    submitted = SubstepCompletion.objects.filter(  # tenant-safe: correlated to a scoped execution
        step_execution=OuterRef("pk"), is_voided=False)
    has_substeps = Substep.objects.filter(step=OuterRef("step"))  # tenant-safe: correlated to a scoped step
    signed = QaApproval.objects.filter(  # tenant-safe: correlated to a scoped execution
        step=OuterRef("step"), work_order=OuterRef("part__work_order"), archived=False)
    qs = (StepExecution.objects  # tenant-safe: .objects auto-scopes (request / tenant_context)
          .filter(exited_at__isnull=True, step__requires_qa_signoff=True,
                  part__isnull=False, part__archived=False, part__work_order__isnull=False)
          # An FPI-gated step is signed off by its first-piece buy-off (fpi.pass_fpi
          # writes the QaApproval) and already has its own inbox row.
          .exclude(step__requires_first_piece_inspection=True)
          .annotate(_submitted=Exists(submitted), _has_substeps=Exists(has_substeps), _signed=Exists(signed))
          .filter(_signed=False)
          .exclude(_has_substeps=True, _submitted=False))
    if work_order is not None:
        qs = qs.filter(part__work_order=work_order)
    groups = (qs.values("part__work_order", "part__work_order__ERP_id", "step", "step__name")
              .annotate(units=Count("id"), oldest=Min("entered_at"))
              .order_by("oldest"))
    return [{"work_order_id": str(g["part__work_order"]), "work_order": g["part__work_order__ERP_id"],
             "step_id": str(g["step"]), "step": g["step__name"], "units": g["units"],
             "oldest_entered_at": g["oldest"]} for g in groups]


def sign_off_step(work_order, step, user):
    """Record the QA sign-off of ``step`` for ``work_order`` and re-run advancement.
    Returns the advancement result. Raises ValueError when there is nothing to sign
    or the signer did the work."""
    from django.db import transaction
    from Tracker.models import QaApproval, SubstepCompletion
    from Tracker.services.mes.advancement import try_advance_lot

    if not step.requires_qa_signoff:
        raise ValueError(f"{step.name} doesn't require a QA sign-off.")
    if step.requires_first_piece_inspection:
        raise ValueError(f"{step.name} is signed off through its first piece inspection.")
    if QaApproval.objects.filter(step=step, work_order=work_order, archived=False).exists():  # tenant-safe: scoped FKs
        raise ValueError(f"{step.name} is already signed off for {work_order.ERP_id}.")
    # Segregation of duties, as for FPI buy-off: whoever signed this step's
    # substeps on this work order can't also sign it off.
    if SubstepCompletion.objects.filter(  # tenant-safe: scoped FKs
            step_execution__part__work_order=work_order, step_execution__step=step,
            step_execution__exited_at__isnull=True, completed_by=user, is_voided=False).exists():
        raise ValueError("Segregation of duties: you completed work on this step — a different "
                         "qualified inspector has to sign it off.")
    with transaction.atomic():
        QaApproval.objects.create(tenant=work_order.tenant, step=step, work_order=work_order, qa_staff=user)
    return try_advance_lot(work_order_id=str(work_order.id), step_id=str(step.id),
                           tenant_id=str(work_order.tenant_id), operator=user)
