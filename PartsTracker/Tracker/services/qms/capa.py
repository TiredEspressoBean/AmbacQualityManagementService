"""
CAPA aggregate services.

Business operations for CAPA, CapaTasks, and CapaVerification. Phase 3b
extraction from model methods — the model methods now delegate here so
logic lives in one place.

Function signatures take model instances rather than IDs, matching how
the callers (viewsets, tests, the model methods themselves) already
operate. Callers run inside a request or TenantTestCase, so auto-scoping
provides tenant safety. Services are plain functions for now;
SecureService-style base class is a Phase 5 decision.
"""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.utils import timezone

from Tracker.models import (
    ApprovalRequest,
    ApprovalTemplate,
    CAPA,
    CapaStatus,
    CapaStatusTransition,
    CapaTaskCompletionMode,
    CapaTaskStatus,
    CapaTaskType,
    CapaTaskAssignee,
    CapaTasks,
    CapaVerification,
    EffectivenessResult,
    RcaReviewStatus,
)


def transition_capa(capa: CAPA, new_status, user, notes: str | None = None) -> CAPA:
    """
    Transition a CAPA to a new status with validation.

    Valid transitions:
        OPEN -> IN_PROGRESS, CANCELLED
        IN_PROGRESS -> PENDING_VERIFICATION, CANCELLED
        PENDING_VERIFICATION -> CLOSED, IN_PROGRESS (reopen), CANCELLED
        CLOSED -> (terminal)
        CANCELLED -> (terminal)

    Args:
        capa: CAPA instance to transition
        new_status: Target status (CapaStatus enum value or string)
        user: User performing the transition
        notes: Optional notes/reason for the transition

    Raises:
        ValueError: If transition is not allowed or requirements not met
    """
    # Normalize new_status to enum value (accept string or enum)
    if isinstance(new_status, str):
        try:
            new_status = CapaStatus[new_status]
        except KeyError:
            new_status = CapaStatus(new_status.lower())

    allowed_transitions = {
        CapaStatus.OPEN: [CapaStatus.IN_PROGRESS, CapaStatus.CANCELLED],
        CapaStatus.IN_PROGRESS: [CapaStatus.PENDING_VERIFICATION, CapaStatus.CANCELLED],
        CapaStatus.PENDING_VERIFICATION: [
            CapaStatus.CLOSED,
            CapaStatus.IN_PROGRESS,
            CapaStatus.CANCELLED,
        ],
        CapaStatus.CLOSED: [],
        CapaStatus.CANCELLED: [],
    }

    current = CapaStatus(capa.status) if isinstance(capa.status, str) else capa.status
    allowed = allowed_transitions.get(current, [])

    if new_status not in allowed:
        raise ValueError(
            f"Cannot transition from {current.value} to {new_status.value}. "
            f"Allowed transitions: {[s.value for s in allowed]}"
        )

    # Validate requirements for specific transitions
    if new_status == CapaStatus.PENDING_VERIFICATION:
        if not capa.rca_complete():
            raise ValueError("Cannot move to PENDING_VERIFICATION: RCA not completed")

    if new_status == CapaStatus.CLOSED:
        blockers = capa.get_blocking_items()
        if blockers:
            raise ValueError(f"Cannot close CAPA: {', '.join(blockers)}")

    capa.status = new_status.value
    if new_status == CapaStatus.CLOSED:
        capa.completed_date = timezone.now().date()
    capa.save()

    # tenant auto-filled from ContextVar via SecureModel.save() — no
    # need for explicit tenant= here. The ContextVar equals capa.tenant
    # in normal flow (middleware/tenant_context set it to the current
    # request/task tenant).
    CapaStatusTransition.objects.create(
        capa=capa,
        from_status=current.value,
        to_status=new_status.value,
        transitioned_by=user,
        notes=notes or '',
    )
    return capa


def complete_capa_task(
    task: CapaTasks,
    user,
    notes: str,
    signature_data: str | None = None,
    password: str | None = None,
) -> CapaTasks:
    """
    Complete a CAPA task with validation.

    Behavior depends on task.completion_mode:
        SINGLE_OWNER: Task completed directly
        ANY_ASSIGNEE: Any one assignee can complete
        ALL_ASSIGNEES: All assignees must complete

    If task.requires_signature is True, signature_data and password are
    required and the password is verified against the user's credentials.

    Raises:
        ValueError: If signature requirements are unmet or password invalid
    """
    if task.requires_signature:
        if not signature_data:
            raise ValueError("Signature is required for this task")
        if not password:
            raise ValueError("Password is required for identity verification")
        if not user.check_password(password):
            raise ValueError("Invalid password")

    if task.completion_mode == CapaTaskCompletionMode.SINGLE_OWNER:
        task.status = CapaTaskStatus.COMPLETED
        task.completed_date = timezone.now().date()
        task.completed_by = user
        task.completion_notes = notes
        if task.requires_signature:
            task.completion_signature = signature_data
        task.save()
    else:
        # Multi-assignee modes use CapaTaskAssignee rows. tenant is
        # auto-filled by SecureModel.save() on the create branch.
        assignee, _ = CapaTaskAssignee.objects.get_or_create(
            task=task,
            user=user,
        )
        assignee.status = CapaTaskStatus.COMPLETED
        assignee.completed_at = timezone.now()
        assignee.completion_notes = notes
        assignee.save()

        assignees = task.assignees.all()

        if task.completion_mode == CapaTaskCompletionMode.ANY_ASSIGNEE:
            if assignees.filter(status=CapaTaskStatus.COMPLETED).exists():
                task.status = CapaTaskStatus.COMPLETED
                task.completed_date = timezone.now().date()
                task.completed_by = user
                if task.requires_signature:
                    task.completion_signature = signature_data
        elif task.completion_mode == CapaTaskCompletionMode.ALL_ASSIGNEES:
            total = assignees.count()
            completed = assignees.filter(status=CapaTaskStatus.COMPLETED).count()
            if total > 0 and completed == total:
                task.status = CapaTaskStatus.COMPLETED
                task.completed_date = timezone.now().date()
                task.completed_by = user
                if task.requires_signature:
                    task.completion_signature = signature_data

        if task.status == CapaTaskStatus.COMPLETED:
            task.save()

    # Phase 3 TODO: next-stage notification trigger (currently noop in both
    # the old model method and here).
    return task


def verify_capa_effectiveness(
    verification: CapaVerification,
    user,
    confirmed: bool,
    notes: str,
) -> CapaVerification:
    """
    Complete the verification step for a CAPA.

    If confirmed=True, closes the CAPA and logs a status transition.
    If confirmed=False, moves the CAPA back to IN_PROGRESS, marks RCA
    for review, and creates a follow-up CORRECTIVE task due in 30 days.

    Raises:
        ValidationError: Self-verification rules violated (user is the
            initiator/assignee and either self-verification is disabled
            or justification notes are insufficient).
    """
    capa = verification.capa

    # Self-verification check
    is_self_verification = (user == capa.initiated_by or user == capa.assigned_to)
    if is_self_verification:
        if not capa.allow_self_verification:
            raise ValidationError("Self-verification is not permitted for this CAPA")
        if not notes or len(notes.strip()) < 10:
            raise ValidationError(
                "Justification required for self-verification (minimum 10 characters)"
            )

    verification.verified_by = user
    verification.verification_date = timezone.now().date()
    verification.effectiveness_result = (
        EffectivenessResult.CONFIRMED if confirmed else EffectivenessResult.NOT_EFFECTIVE
    )
    verification.effectiveness_decided_at = timezone.now()
    verification.verification_notes = notes
    verification.self_verified = is_self_verification
    verification.save()

    old_status = capa.status

    if verification.effectiveness_result == EffectivenessResult.CONFIRMED:
        capa.status = CapaStatus.CLOSED
        capa.completed_date = timezone.now().date()
        capa.save(update_fields=['status', 'completed_date'])

        CapaStatusTransition.objects.create(
            capa=capa,
            from_status=old_status,
            to_status=CapaStatus.CLOSED,
            transitioned_by=user,
            notes=f"Effectiveness verified: {notes}" if notes else "Effectiveness verified",
        )
    else:
        rca = capa.rca_records.first()
        if rca:
            rca.rca_review_status = RcaReviewStatus.REQUIRED
            rca.save()

        capa.status = CapaStatus.IN_PROGRESS
        capa.save()

        CapaStatusTransition.objects.create(
            capa=capa,
            from_status=old_status,
            to_status=CapaStatus.IN_PROGRESS,
            transitioned_by=user,
            notes=(
                f"Effectiveness not confirmed, reopened for review: {notes}"
                if notes
                else "Effectiveness not confirmed, reopened for review"
            ),
        )

        # Create follow-up task (task_number auto-generated by CapaTasks.save()).
        # tenant auto-filled from ContextVar.
        CapaTasks.objects.create(
            capa=capa,
            task_type=CapaTaskType.CORRECTIVE,
            description=f"Review and update RCA due to failed verification: {notes}",
            assigned_to=capa.assigned_to,
            due_date=timezone.now().date() + timezone.timedelta(days=30),
        )

    return verification


def auto_request_capa_approval(capa: CAPA) -> ApprovalRequest | None:
    """Create an approval request for a Critical/Major CAPA at creation time.

    Looks up the tenant's CAPA_APPROVAL template; returns None (silently)
    when no template is configured. Used by the post_save signal so the
    signal body stays thin.

    Sets approval_required=True and approval_status='PENDING' on the CAPA
    after creating the request.
    """
    try:
        template = ApprovalTemplate.objects.get(
            approval_type='CAPA_APPROVAL',
            tenant=capa.tenant,
        )
    except ApprovalTemplate.DoesNotExist:
        return None

    approval_request = ApprovalRequest.create_from_template(
        content_object=capa,
        template=template,
        requested_by=capa.initiated_by,
        reason=f"CAPA Approval: {capa.capa_number} - {capa.get_severity_display()}",
    )

    capa.approval_required = True
    capa.approval_status = 'PENDING'
    capa.save(update_fields=['approval_required', 'approval_status'])

    return approval_request


def request_capa_approval(capa: CAPA, user) -> ApprovalRequest:
    """Create an ApprovalRequest for a CAPA.

    Looks up the tenant's CAPA_APPROVAL template, spins up an approval
    request via `ApprovalRequest.create_from_template`, and flips the
    CAPA's approval fields to PENDING.

    Raises:
        ValueError: CAPA already approved / approval already pending /
            template not configured.
    """
    if capa.approval_status == 'APPROVED':
        raise ValueError("CAPA is already approved")
    if capa.approval_status == 'PENDING':
        raise ValueError("CAPA approval is already pending")

    try:
        template = ApprovalTemplate.objects.get(
            approval_type='CAPA_APPROVAL',
            tenant=capa.tenant,
        )
    except ApprovalTemplate.DoesNotExist:
        raise ValueError(
            "CAPA_APPROVAL template not found. Please configure approval templates."
        )

    approval_request = ApprovalRequest.create_from_template(
        content_object=capa,
        template=template,
        requested_by=user,
        reason=f"CAPA Approval: {capa.capa_number} - {capa.get_severity_display()}",
    )

    capa.approval_required = True
    capa.approval_status = 'PENDING'
    capa.save(update_fields=['approval_required', 'approval_status'])

    return approval_request
