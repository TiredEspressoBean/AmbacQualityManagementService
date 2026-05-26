"""
Process change control lifecycle services — PCR → PCO → PCN.

These services orchestrate state transitions across the three-stage
artifact chain. Validation rules and side effects (ApprovalRequest
creation, version creation, WO migration, PCN auto-generation) live
here, not on the model. Models hold data and `__str__` / `is_open`
accessors only.

Mode-conditional behavior:

- SIMPLIFIED: PCO and PCN auto-generate from upstream approvals/
  implementations and downstream services proceed without separate
  signature collection.
- REGULATED: PCO requires explicit author + approve gates with
  separation-of-duties enforcement. PCN requires explicit release.

Mode is passed as a parameter — the viewset layer reads tenant config
to determine which to pass. Tenants in REGULATED mode that haven't
configured PCO_APPROVAL / PCN_RELEASE templates will get a clear
ValueError at the affected lifecycle transition.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from Tracker.models import (
    ApprovalRequest,
    ApprovalTemplate,
    Processes,
    ProcessChangeRequest,
    ProcessChangeOrder,
    ProcessChangeNotice,
    ProcessChangeMigrationDisposition,
    WorkOrder,
)
from Tracker.services.change_control.impact_analysis import (
    list_affected_workorders,
    snapshot_affected_workorders,
)
from Tracker.services.change_control.sequencing import next_artifact_number
from Tracker.services.mes.processes import (
    approve_process,
    create_new_process_version,
)


# ---------------------------------------------------------------------------
# Mode constants
# ---------------------------------------------------------------------------

class ChangeControlMode:
    SIMPLIFIED = 'SIMPLIFIED'
    REGULATED = 'REGULATED'


# ---------------------------------------------------------------------------
# PCR — ProcessChangeRequest lifecycle
# ---------------------------------------------------------------------------

def submit_pcr(
    pcr: ProcessChangeRequest,
    *,
    user,
) -> ApprovalRequest:
    """Submit a draft PCR for review.

    Transitions DRAFT → SUBMITTED, snapshots affected in-flight WOs,
    captures the baseline_version_id, and creates an ApprovalRequest
    via the tenant's PCR_APPROVAL template.

    Raises:
        ValueError: PCR is not in DRAFT, missing required fields, or
            the PCR_APPROVAL template is not configured for the tenant.
    """
    if pcr.status != ProcessChangeRequest.Status.DRAFT:
        raise ValueError(
            f"Cannot submit PCR with status {pcr.status}. Must be DRAFT."
        )

    _require_text(pcr, ('title', 'proposed_change', 'justification', 'risk_analysis'))

    if pcr.target_process_id is None:
        raise ValueError("PCR must reference a target process.")

    try:
        template = ApprovalTemplate.objects.get(
            approval_type='PCR_APPROVAL',
            tenant=pcr.tenant,
            archived=False,
        )
    except ApprovalTemplate.DoesNotExist:
        raise ValueError(
            "PCR_APPROVAL approval template not found. "
            "Please configure approval templates."
        )

    with transaction.atomic():
        pcr.affected_workorders_snapshot = snapshot_affected_workorders(pcr.target_process)
        pcr.baseline_version_id = pcr.target_process_id
        pcr.submitted_at = timezone.now()
        pcr.submitted_by = user
        pcr.status = ProcessChangeRequest.Status.SUBMITTED
        pcr.save(update_fields=[
            'affected_workorders_snapshot',
            'baseline_version_id',
            'submitted_at',
            'submitted_by',
            'status',
            'updated_at',
        ])

        approval_request = ApprovalRequest.create_from_template(
            content_object=pcr,
            template=template,
            requested_by=user,
            reason=f"PCR Submission: {pcr.artifact_number} — {pcr.title}",
        )

    return approval_request


def approve_pcr(
    pcr: ProcessChangeRequest,
    *,
    user,
    mode: str = ChangeControlMode.SIMPLIFIED,
) -> ProcessChangeOrder:
    """Approve a submitted PCR and create the downstream PCO.

    Called when the PCR's ApprovalRequest reaches its approved state.
    Transitions SUBMITTED → APPROVED and triggers PCO creation
    (auto-approved + DRAFT version pre-created in SIMPLIFIED mode;
    DRAFT-only in REGULATED mode awaiting explicit author).

    Raises:
        ValueError: PCR is not in SUBMITTED status.
    """
    valid_pre_states = (
        ProcessChangeRequest.Status.SUBMITTED,
        ProcessChangeRequest.Status.UNDER_REVIEW,
    )
    if pcr.status not in valid_pre_states:
        raise ValueError(
            f"Cannot approve PCR with status {pcr.status}. "
            f"Must be SUBMITTED or UNDER_REVIEW."
        )

    with transaction.atomic():
        pcr.status = ProcessChangeRequest.Status.APPROVED
        pcr.save(update_fields=['status', 'updated_at'])

        pco = create_pco_from_approved_pcr(pcr, user=user, mode=mode)

    return pco


def reject_pcr(
    pcr: ProcessChangeRequest,
    *,
    user,
    reason: str,
) -> ProcessChangeRequest:
    """Reject a submitted PCR with a reason.

    Terminal state. Retry requires a new PCR; the rejected one can
    optionally be linked from the new attempt via
    `superseded_by_request_*`.

    Raises:
        ValueError: PCR is not in a rejectable status, or reason blank.
    """
    valid_pre_states = (
        ProcessChangeRequest.Status.SUBMITTED,
        ProcessChangeRequest.Status.UNDER_REVIEW,
    )
    if pcr.status not in valid_pre_states:
        raise ValueError(
            f"Cannot reject PCR with status {pcr.status}. "
            f"Must be SUBMITTED or UNDER_REVIEW."
        )
    if not reason or not reason.strip():
        raise ValueError("Rejection reason is required.")

    pcr.status = ProcessChangeRequest.Status.REJECTED
    pcr.rejected_reason = reason.strip()
    pcr.save(update_fields=['status', 'rejected_reason', 'updated_at'])

    return pcr


def cancel_pcr(
    pcr: ProcessChangeRequest,
    *,
    user,
    reason: str = '',
) -> ProcessChangeRequest:
    """Cancel a PCR before approval. Terminal.

    Raises:
        ValueError: PCR has already been approved (use a new PCR to
            reverse the change instead) or already in a terminal state.
    """
    valid_pre_states = (
        ProcessChangeRequest.Status.DRAFT,
        ProcessChangeRequest.Status.SUBMITTED,
        ProcessChangeRequest.Status.UNDER_REVIEW,
    )
    if pcr.status not in valid_pre_states:
        raise ValueError(
            f"Cannot cancel PCR with status {pcr.status}. "
            f"Must be pre-approval (DRAFT / SUBMITTED / UNDER_REVIEW)."
        )

    pcr.status = ProcessChangeRequest.Status.CANCELLED
    if reason and reason.strip():
        pcr.rejected_reason = f"Cancelled: {reason.strip()}"
    pcr.save(update_fields=['status', 'rejected_reason', 'updated_at'])

    return pcr


# ---------------------------------------------------------------------------
# PCO — ProcessChangeOrder lifecycle
# ---------------------------------------------------------------------------

def create_pco_from_approved_pcr(
    pcr: ProcessChangeRequest,
    *,
    user,
    mode: str = ChangeControlMode.SIMPLIFIED,
) -> ProcessChangeOrder:
    """Create a PCO from an approved PCR (Pattern C).

    Always creates a DRAFT process version copying the current state of
    target_process and links it via `pco.draft_process_version`. The
    DRAFT is the artifact PCO authors edit and PCO approvers sign off
    on (in REGULATED mode).

    SIMPLIFIED mode: PCO is auto-approved at creation. The user goes
    straight to editing the DRAFT version + implementing.

    REGULATED mode: PCO sits in DRAFT awaiting `author_pco` + then
    `approve_pco` by a different user (separation of duties).

    Raises:
        ValueError: PCR is not APPROVED, or PCO already exists for it.
    """
    if pcr.status != ProcessChangeRequest.Status.APPROVED:
        raise ValueError(
            f"Cannot create PCO from PCR in status {pcr.status}. Must be APPROVED."
        )

    if hasattr(pcr, 'order') and pcr.order is not None:
        raise ValueError(
            f"PCO already exists for PCR {pcr.artifact_number}: "
            f"{pcr.order.artifact_number}."
        )

    with transaction.atomic():
        draft_version = create_new_process_version(
            pcr.target_process,
            user=user,
            change_description=(
                f"PCR {pcr.artifact_number}: {pcr.title}\n\n"
                f"{pcr.proposed_change}\n\n"
                f"Justification: {pcr.justification}"
            ),
        )

        artifact_number = next_artifact_number(
            tenant_id=pcr.tenant_id,
            artifact_type='PCO',
        )

        pco = ProcessChangeOrder(
            tenant=pcr.tenant,
            artifact_number=artifact_number,
            request=pcr,
            draft_process_version=draft_version,
            implementation_plan=_default_implementation_plan(pcr),
            created_by=user,
            data_origin=pcr.data_origin,
        )

        if mode == ChangeControlMode.SIMPLIFIED:
            pco.status = ProcessChangeOrder.Status.APPROVED
            pco.approved_at = timezone.now()
            pco.approved_by = user
        else:
            pco.status = ProcessChangeOrder.Status.DRAFT

        pco.save()

    return pco


def author_pco(
    pco: ProcessChangeOrder,
    *,
    user,
    implementation_plan: Optional[str] = None,
    effective_date=None,
) -> ProcessChangeOrder:
    """Update a draft PCO's authoring fields (REGULATED mode).

    The PCO author edits the linked draft_process_version separately
    via the existing process editor; this service captures the textual
    implementation plan and the planned effective date.

    Raises:
        ValueError: PCO is not in DRAFT.
    """
    if pco.status != ProcessChangeOrder.Status.DRAFT:
        raise ValueError(
            f"Cannot author PCO with status {pco.status}. Must be DRAFT."
        )

    update_fields = ['updated_at']
    if implementation_plan is not None:
        pco.implementation_plan = implementation_plan
        update_fields.append('implementation_plan')
    if effective_date is not None:
        pco.effective_date = effective_date
        update_fields.append('effective_date')

    pco.save(update_fields=update_fields)
    return pco


def approve_pco(
    pco: ProcessChangeOrder,
    *,
    user,
) -> ApprovalRequest:
    """Submit a drafted PCO for separate approval (REGULATED mode).

    Creates an ApprovalRequest from the tenant's PCO_APPROVAL template.
    The PCO does not transition until the ApprovalRequest is fully
    signed; the final transition runs through `mark_pco_approved`.

    Separation of duties: the PCO author cannot also be the approver.
    The check is enforced at signature collection time on the
    ApprovalRequest, but we also block the request creation here if
    the same user is attempting to approve their own PCO.

    Raises:
        ValueError: PCO is not in DRAFT, the PCO_APPROVAL template is
            missing, or the same user authored the implementation_plan.
    """
    if pco.status != ProcessChangeOrder.Status.DRAFT:
        raise ValueError(
            f"Cannot submit PCO with status {pco.status} for approval. "
            f"Must be DRAFT."
        )

    if not pco.implementation_plan or not pco.implementation_plan.strip():
        raise ValueError("PCO must have an implementation_plan before approval.")

    if pco.draft_process_version_id is None:
        raise ValueError(
            "PCO must reference a draft_process_version before approval."
        )

    try:
        template = ApprovalTemplate.objects.get(
            approval_type='PCO_APPROVAL',
            tenant=pco.tenant,
            archived=False,
        )
    except ApprovalTemplate.DoesNotExist:
        raise ValueError(
            "PCO_APPROVAL approval template not found. "
            "Please configure approval templates."
        )

    return ApprovalRequest.create_from_template(
        content_object=pco,
        template=template,
        requested_by=user,
        reason=f"PCO Approval: {pco.artifact_number}",
    )


def mark_pco_approved(
    pco: ProcessChangeOrder,
    *,
    user,
) -> ProcessChangeOrder:
    """Transition a DRAFT PCO to APPROVED.

    Called when the PCO's ApprovalRequest is fully approved
    (REGULATED mode). Separation-of-duties: the approver `user` must
    not be the same as `pco.created_by` or the PCO author.

    Raises:
        ValueError: PCO not in DRAFT, or separation-of-duties violated.
    """
    if pco.status != ProcessChangeOrder.Status.DRAFT:
        raise ValueError(
            f"Cannot approve PCO with status {pco.status}. Must be DRAFT."
        )

    if user is not None and pco.created_by_id == getattr(user, 'id', None):
        raise ValueError(
            "Separation of duties: the PCO author cannot also be the approver."
        )

    pco.status = ProcessChangeOrder.Status.APPROVED
    pco.approved_at = timezone.now()
    pco.approved_by = user
    pco.save(update_fields=['status', 'approved_at', 'approved_by', 'updated_at'])

    return pco


def implement_pco(
    pco: ProcessChangeOrder,
    *,
    user,
    migration_disposition: str,
    migration_reason: str = '',
    selected_workorder_ids: Optional[list[UUID]] = None,
    mode: str = ChangeControlMode.SIMPLIFIED,
) -> ProcessChangeNotice:
    """Implement an approved PCO.

    Runs:
      1. `approve_process` on the linked DRAFT version, flipping it
         to APPROVED via the existing process versioning service.
      2. WO migrations per the disposition (Path A action: in-place
         update of WorkOrder.process to the new version, audited via
         auditlog on the FK change).
      3. PCO transitions APPROVED → IN_IMPLEMENTATION → IMPLEMENTED.
      4. Auto-creates the downstream PCN (auto-released in
         SIMPLIFIED mode, drafted in REGULATED).

    migration_disposition values:
      - MIGRATE_ALL: every in-flight WO on the old version migrates.
      - MIGRATE_SELECTED: only WOs in `selected_workorder_ids` migrate.
      - KEEP_ALL: no WOs migrate; they remain pinned to the old version.

    Raises:
        ValueError: PCO not APPROVED; disposition invalid;
            disposition=MIGRATE_SELECTED but selected_workorder_ids
            empty/missing; PCO has no draft_process_version.
    """
    if pco.status != ProcessChangeOrder.Status.APPROVED:
        raise ValueError(
            f"Cannot implement PCO with status {pco.status}. Must be APPROVED."
        )

    if pco.draft_process_version_id is None:
        raise ValueError("PCO has no linked draft_process_version to implement.")

    if migration_disposition not in ProcessChangeMigrationDisposition.values:
        raise ValueError(
            f"Invalid migration_disposition: {migration_disposition!r}. "
            f"Expected one of {ProcessChangeMigrationDisposition.values}."
        )
    if migration_disposition == ProcessChangeMigrationDisposition.PENDING:
        raise ValueError(
            "migration_disposition cannot remain PENDING at implementation."
        )

    if migration_disposition == ProcessChangeMigrationDisposition.MIGRATE_SELECTED:
        if not selected_workorder_ids:
            raise ValueError(
                "selected_workorder_ids required when "
                "migration_disposition=MIGRATE_SELECTED."
            )

    pcr = pco.request

    with transaction.atomic():
        pco.status = ProcessChangeOrder.Status.IN_IMPLEMENTATION
        pco.save(update_fields=['status', 'updated_at'])

        new_version = approve_process(pco.draft_process_version, user=user)

        migrated_ids = _apply_workorder_migrations(
            old_version=pcr.target_process,
            new_version=new_version,
            disposition=migration_disposition,
            selected_workorder_ids=selected_workorder_ids or [],
        )

        pco.migration_disposition = migration_disposition
        pco.migration_reason = migration_reason or ''
        pco.migrated_workorder_ids = [str(wid) for wid in migrated_ids]
        pco.status = ProcessChangeOrder.Status.IMPLEMENTED
        pco.implemented_at = timezone.now()
        pco.implemented_by = user
        pco.save(update_fields=[
            'migration_disposition',
            'migration_reason',
            'migrated_workorder_ids',
            'status',
            'implemented_at',
            'implemented_by',
            'updated_at',
        ])

        pcn = create_pcn_from_implemented_pco(pco, user=user, mode=mode)

    return pcn


def cancel_pco(
    pco: ProcessChangeOrder,
    *,
    user,
    reason: str = '',
) -> ProcessChangeOrder:
    """Cancel a DRAFT or APPROVED PCO before implementation. Terminal.

    Does NOT delete the linked DRAFT process version — that remains in
    the database for audit. Cleanup of orphan DRAFTs (if desired) is a
    separate concern.

    Raises:
        ValueError: PCO already implemented or already in a terminal state.
    """
    valid_pre_states = (
        ProcessChangeOrder.Status.DRAFT,
        ProcessChangeOrder.Status.APPROVED,
    )
    if pco.status not in valid_pre_states:
        raise ValueError(
            f"Cannot cancel PCO with status {pco.status}. "
            f"Must be DRAFT or APPROVED."
        )

    pco.status = ProcessChangeOrder.Status.CANCELLED
    pco.save(update_fields=['status', 'updated_at'])
    return pco


# ---------------------------------------------------------------------------
# PCN — ProcessChangeNotice lifecycle
# ---------------------------------------------------------------------------

def create_pcn_from_implemented_pco(
    pco: ProcessChangeOrder,
    *,
    user,
    mode: str = ChangeControlMode.SIMPLIFIED,
) -> ProcessChangeNotice:
    """Create a PCN from an implemented PCO.

    SIMPLIFIED mode: auto-released. Notification dispatch fires via
    existing `notify()` infrastructure on `PCN_RELEASED` event (when
    that event registry entry is wired up; for Phase 1 the release
    state transition is recorded but no event is emitted).

    REGULATED mode: PCN sits in DRAFT awaiting `release_pcn` by the
    quality manager (separate signature).

    Raises:
        ValueError: PCO not IMPLEMENTED, or PCN already exists.
    """
    if pco.status != ProcessChangeOrder.Status.IMPLEMENTED:
        raise ValueError(
            f"Cannot create PCN from PCO in status {pco.status}. "
            f"Must be IMPLEMENTED."
        )

    if hasattr(pco, 'notice') and pco.notice is not None:
        raise ValueError(
            f"PCN already exists for PCO {pco.artifact_number}: "
            f"{pco.notice.artifact_number}."
        )

    pcr = pco.request

    artifact_number = next_artifact_number(
        tenant_id=pco.tenant_id,
        artifact_type='PCN',
    )

    pcn = ProcessChangeNotice(
        tenant=pco.tenant,
        artifact_number=artifact_number,
        order=pco,
        notice_content=_default_notice_content(pcr, pco),
        created_by=user,
        data_origin=pco.data_origin,
    )

    if mode == ChangeControlMode.SIMPLIFIED:
        pcn.status = ProcessChangeNotice.Status.RELEASED
        pcn.released_at = timezone.now()
        pcn.released_by = user
    else:
        pcn.status = ProcessChangeNotice.Status.DRAFT

    pcn.save()
    return pcn


def release_pcn(
    pcn: ProcessChangeNotice,
    *,
    user,
) -> ProcessChangeNotice:
    """Release a drafted PCN (REGULATED mode).

    Separation-of-duties: the PCN releaser must not be the same user
    who approved the upstream PCO.

    Raises:
        ValueError: PCN not in DRAFT, separation-of-duties violated,
            or PCN_RELEASE template not configured.
    """
    if pcn.status != ProcessChangeNotice.Status.DRAFT:
        raise ValueError(
            f"Cannot release PCN with status {pcn.status}. Must be DRAFT."
        )

    if user is not None and pcn.order.approved_by_id == getattr(user, 'id', None):
        raise ValueError(
            "Separation of duties: the PCN releaser cannot be the same user "
            "who approved the upstream PCO."
        )

    pcn.status = ProcessChangeNotice.Status.RELEASED
    pcn.released_at = timezone.now()
    pcn.released_by = user
    pcn.save(update_fields=['status', 'released_at', 'released_by', 'updated_at'])

    return pcn


def close_pcn(
    pcn: ProcessChangeNotice,
    *,
    user,
    closure_evidence: str,
) -> ProcessChangeNotice:
    """Close a released PCN with effectiveness verification evidence.

    Terminal. Records the user-supplied closure_evidence narrative.
    Phase 5 will add structured effectiveness metrics.

    Raises:
        ValueError: PCN not RELEASED, or closure_evidence blank.
    """
    if pcn.status != ProcessChangeNotice.Status.RELEASED:
        raise ValueError(
            f"Cannot close PCN with status {pcn.status}. Must be RELEASED."
        )
    if not closure_evidence or not closure_evidence.strip():
        raise ValueError("closure_evidence is required.")

    pcn.status = ProcessChangeNotice.Status.CLOSED
    pcn.closure_evidence = closure_evidence.strip()
    pcn.closed_at = timezone.now()
    pcn.closed_by = user
    pcn.save(update_fields=[
        'status',
        'closure_evidence',
        'closed_at',
        'closed_by',
        'updated_at',
    ])

    return pcn


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _require_text(obj, field_names: tuple[str, ...]) -> None:
    missing = [f for f in field_names if not (getattr(obj, f, '') or '').strip()]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")


def _default_implementation_plan(pcr: ProcessChangeRequest) -> str:
    return (
        f"Implementation of PCR {pcr.artifact_number}: {pcr.title}\n\n"
        f"Proposal:\n{pcr.proposed_change}\n\n"
        f"Justification:\n{pcr.justification}"
    )


def _default_notice_content(
    pcr: ProcessChangeRequest,
    pco: ProcessChangeOrder,
) -> str:
    return (
        f"Notice of approved process change.\n\n"
        f"Source PCR: {pcr.artifact_number} — {pcr.title}\n"
        f"Authorizing PCO: {pco.artifact_number}\n"
        f"Effective: {pco.effective_date or 'on release'}\n\n"
        f"Summary of change:\n{pcr.proposed_change}"
    )


def _apply_workorder_migrations(
    *,
    old_version: Processes,
    new_version: Processes,
    disposition: str,
    selected_workorder_ids: list[UUID],
) -> list[UUID]:
    """Apply WO process FK migrations per the disposition.

    Returns the list of WO IDs actually migrated. Each migration is a
    direct FK update with `wo.save()`, which auditlog records as a
    field change on WorkOrder.process — the per-WO migration audit
    trail flows through that mechanism.
    """
    if disposition == ProcessChangeMigrationDisposition.KEEP_ALL:
        return []

    qs = list_affected_workorders(old_version)

    if disposition == ProcessChangeMigrationDisposition.MIGRATE_SELECTED:
        selected_set = {str(wid) for wid in selected_workorder_ids}
        qs = [wo for wo in qs if str(wo.id) in selected_set]

    migrated: list[UUID] = []
    for wo in qs:
        wo.process = new_version
        wo.save(update_fields=['process', 'updated_at'])
        migrated.append(wo.id)

    return migrated
