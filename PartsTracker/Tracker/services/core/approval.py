"""
Approval workflow services.

Covers both `ApprovalRequest` (the parent — approvers, status tallying,
notifications, escalation) and `ApprovalResponse` (decision submission
and delegation). The two aggregates call each other internally (a
submitted response drives the request's status update → cascade to
content object → notification), so they live in one module to keep
that flow visible in one place.

Plain functions; no service class. The per-call `request` or `response`
is the state; nothing is shared across calls.

Sequencing note: `_check_sequential_status` is module-private and only
consumed by `check_approval_status`. Not re-exported.
"""
from __future__ import annotations

from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from Tracker.models import (
    Approval_Status_Type,
    ApprovalDecision,
    ApprovalDelegation,
    ApprovalFlows,
    ApprovalRequest,
    ApprovalResponse,
    ApprovalTemplate,
    ApproverAssignment,
    ApproverAssignmentSource,
    GroupApproverAssignment,
    NotificationTask,
    SequenceTypes,
    User,
    VerificationMethod,
)


# =========================================================================
# ApprovalRequest — approver assignment
# =========================================================================

def add_approver(
    request: ApprovalRequest,
    user,
    is_required: bool = True,
    sequence_order=None,
    assignment_source=None,
    assigned_by=None,
):
    """Add an approver with full audit trail."""
    if assignment_source is None:
        assignment_source = ApproverAssignmentSource.MANUAL

    return ApproverAssignment.objects.get_or_create(
        approval_request=request,
        user=user,
        defaults={
            'is_required': is_required,
            'sequence_order': sequence_order,
            'assignment_source': assignment_source,
            'assigned_by': assigned_by,
        }
    )


def remove_approver(request: ApprovalRequest, user):
    """Remove an approver from this request."""
    return ApproverAssignment.objects.filter(
        approval_request=request,
        user=user,
    ).delete()


def set_approvers(
    request: ApprovalRequest,
    users,
    is_required: bool = True,
    assignment_source=None,
    assigned_by=None,
):
    """Replace all approvers of a given type with a new list."""
    if assignment_source is None:
        assignment_source = ApproverAssignmentSource.MANUAL

    ApproverAssignment.objects.filter(
        approval_request=request,
        is_required=is_required,
    ).delete()

    for i, user in enumerate(users):
        ApproverAssignment.objects.create(
            approval_request=request,
            user=user,
            is_required=is_required,
            sequence_order=i if request.sequence_type == SequenceTypes.SEQUENTIAL else None,
            assignment_source=assignment_source,
            assigned_by=assigned_by,
        )


# =========================================================================
# ApprovalRequest — factory
# =========================================================================

def create_approval_from_template(
    content_object,
    template: ApprovalTemplate,
    requested_by,
    reason: str | None = None,
) -> ApprovalRequest:
    """Create an approval request from a template with auto-assignment.

    Assigns users, groups, and role-based approvers per the template,
    then immediately notifies pending approvers. Notification is done
    here rather than via signal because post_save fires before M2M
    assignments are written.
    """
    tenant = getattr(content_object, 'tenant', None) or getattr(requested_by, 'tenant', None)

    approval = ApprovalRequest.objects.create(
        approval_number=ApprovalRequest.generate_approval_number(tenant),
        tenant=tenant,
        content_object=content_object,
        approval_type=template.approval_type,
        requested_by=requested_by,
        reason=reason,
        flow_type=template.approval_flow_type,
        sequence_type=template.approval_sequence,
        threshold=template.default_threshold if template.approval_flow_type == ApprovalFlows.THRESHOLD else None,
        delegation_policy=template.delegation_policy,
        escalation_day=timezone.now().date() + timedelta(days=template.escalation_days) if template.escalation_days else None,
        escalate_to=template.escalate_to,
        due_date=timezone.now() + timedelta(days=template.default_due_days),
    )

    set_approvers(
        approval,
        template.default_approvers.all(),
        is_required=True,
        assignment_source=ApproverAssignmentSource.TEMPLATE_DEFAULT,
    )

    for group in template.default_groups.all():
        GroupApproverAssignment.objects.create(
            approval_request=approval,
            group=group,
            assignment_source=ApproverAssignmentSource.TEMPLATE_GROUP,
        )

    if template.auto_assign_by_role:
        role_users = User.objects.filter(
            user_roles__group__name=template.auto_assign_by_role,
            user_roles__group__tenant=tenant,
        )
        for user in role_users:
            add_approver(
                approval,
                user,
                is_required=True,
                assignment_source=ApproverAssignmentSource.TEMPLATE_GROUP,
            )

    notify_approvers(approval)
    return approval


# =========================================================================
# ApprovalRequest — status resolution
# =========================================================================

def check_approval_status(request: ApprovalRequest):
    """Classify an approval request's current status from its responses.

    Returns (status, pending_approvers).
    Any rejection short-circuits to REJECTED regardless of flow type.
    """
    responses = request.responses.all()

    if responses.filter(decision=ApprovalDecision.REJECTED).exists():
        return (Approval_Status_Type.REJECTED, [])

    approvals = responses.filter(decision=ApprovalDecision.APPROVED)

    if request.sequence_type == SequenceTypes.SEQUENTIAL:
        return _check_sequential_status(request, approvals)

    if request.flow_type == ApprovalFlows.ANY:
        if approvals.exists():
            return (Approval_Status_Type.APPROVED, [])
        return (Approval_Status_Type.PENDING, list(request.get_pending_approvers()))

    if request.flow_type == ApprovalFlows.THRESHOLD:
        threshold = request.threshold or 0
        if threshold > 0 and approvals.count() >= threshold:
            return (Approval_Status_Type.APPROVED, [])
        return (Approval_Status_Type.PENDING, list(request.get_pending_approvers()))

    # Default: ALL_REQUIRED (parallel)
    approved_by = set(approvals.values_list('approver_id', flat=True))
    required = set(request.required_approvers.values_list('id', flat=True))
    pending_ids = required - approved_by

    if not pending_ids:
        return (Approval_Status_Type.APPROVED, [])

    pending = User.objects.filter(id__in=pending_ids)
    return (Approval_Status_Type.PENDING, list(pending))


def _check_sequential_status(request: ApprovalRequest, approvals):
    """In sequential mode, only the next unapproved assignee may proceed."""
    assignments = request.approver_assignments.filter(
        is_required=True,
    ).order_by('sequence_order', 'assigned_at')

    approved_by = set(approvals.values_list('approver_id', flat=True))

    for assignment in assignments:
        if assignment.user_id not in approved_by:
            return (Approval_Status_Type.PENDING, [assignment.user])

    return (Approval_Status_Type.APPROVED, [])


def update_approval_status(request: ApprovalRequest) -> ApprovalRequest:
    """Recompute status from responses, persist, and cascade to the
    content object if the status changed."""
    new_status, _pending = check_approval_status(request)

    if new_status != request.status:
        request.status = new_status
        if new_status in [Approval_Status_Type.APPROVED, Approval_Status_Type.REJECTED]:
            request.completed_at = timezone.now()
        request.save()
        trigger_content_object_update(request, new_status)

    return request


def trigger_content_object_update(request: ApprovalRequest, status):
    """Cascade the approval outcome to the referenced content object.

    Delegates to `apply_approval_decision_to_content_object` — kept for
    backward compatibility with callers that imported this name directly.
    """
    apply_approval_decision_to_content_object(request, status)


def apply_approval_decision_to_content_object(request: ApprovalRequest, status):
    """Cascade an APPROVED or REJECTED decision to the content object.

    Handles three content-object types:
    - Documents: sets status/approved_by/approved_at or reverts to DRAFT.
    - CAPA: sets approval_status/approved_by/approved_at or resets to
      REJECTED and clears approval_required so re-submission is possible.
    - Processes: delegates to the model's approve()/reject_approval()
      methods (those models manage their own state machine).

    No-op when `content_object` is None or an unrecognised type.
    """
    obj = request.content_object
    if not obj:
        return

    obj_type = type(obj).__name__

    if obj_type == 'Documents':
        if status == Approval_Status_Type.APPROVED:
            obj.status = 'APPROVED'
            obj.approved_by = request.get_primary_approver()
            obj.approved_at = request.completed_at
            obj.save(update_fields=['status', 'approved_by', 'approved_at'])
        elif status == Approval_Status_Type.REJECTED:
            obj.status = 'DRAFT'
            obj.save(update_fields=['status'])

    elif obj_type == 'CAPA':
        if status == Approval_Status_Type.APPROVED:
            obj.approval_status = 'APPROVED'
            obj.approved_by = request.get_primary_approver()
            obj.approved_at = request.completed_at
            obj.save(update_fields=['approval_status', 'approved_by', 'approved_at'])
        elif status == Approval_Status_Type.REJECTED:
            obj.approval_status = 'REJECTED'
            obj.approval_required = False
            obj.save(update_fields=['approval_status', 'approval_required'])

    elif obj_type == 'Processes':
        if status == Approval_Status_Type.APPROVED:
            obj.approve(user=request.get_primary_approver())
        elif status == Approval_Status_Type.REJECTED:
            obj.reject_approval()


# =========================================================================
# ApprovalRequest — notifications & escalation
# =========================================================================

def notify_approvers(request: ApprovalRequest):
    """Send a notification task to each pending approver."""
    from Tracker.services.core.notification import enqueue_approval_notification

    for approver in request.get_pending_approvers():
        enqueue_approval_notification(approver, request)


def notify_status_change(request: ApprovalRequest, new_status):
    """Notify the requester that a decision has been made."""
    from Tracker.services.core.notification import enqueue_decision_notification

    enqueue_decision_notification(request.requested_by, request)


def escalate_approval(request: ApprovalRequest):
    """Queue an escalation notification for the configured escalate_to user.

    No-op when no escalate_to is configured on the request.
    """
    if not request.escalate_to:
        return

    from Tracker.services.core.notification import enqueue_escalation_notification

    enqueue_escalation_notification(request.escalate_to, request)


# =========================================================================
# ApprovalResponse — submission and delegation
# =========================================================================

def submit_approval_response(
    approval_request: ApprovalRequest,
    approver,
    decision,
    comments: str | None = None,
    signature_data: str | None = None,
    signature_meaning: str | None = None,
    password: str | None = None,
    ip_address: str | None = None,
) -> ApprovalResponse:
    """Record an approval decision with signature capture + password
    re-auth. After creating the response, recomputes the parent
    request's status (which may cascade to the content object).

    Raises:
        PermissionDenied: approver is not authorized for this request.
        ValidationError: duplicate response, self-approval not permitted
            (or insufficient justification), or password verification failed.
    """
    if not approval_request.can_approve(approver):
        raise PermissionDenied("You are not authorized to approve this request")

    if ApprovalResponse.objects.filter(
        approval_request=approval_request,
        approver=approver,
    ).exists():
        raise ValidationError("You have already responded to this approval")

    is_self_approval = (approval_request.requested_by == approver)
    if is_self_approval:
        template = approval_request.get_template()
        if not template or not template.allow_self_approval:
            raise ValidationError("Self-approval is not permitted for this approval type")
        if not comments or len(comments.strip()) < 10:
            raise ValidationError("Justification required for self-approval (minimum 10 characters)")

    verification_method = VerificationMethod.NONE
    verified_at = None
    if password:
        if not approver.check_password(password):
            raise ValidationError("Password incorrect. Identity verification failed.")
        verification_method = VerificationMethod.PASSWORD
        verified_at = timezone.now()

    response = ApprovalResponse.objects.create(
        approval_request=approval_request,
        approver=approver,
        decision=decision,
        comments=comments,
        signature_data=signature_data,
        signature_meaning=signature_meaning,
        verified_at=verified_at,
        verification_method=verification_method,
        ip_address=ip_address,
        self_approved=is_self_approval,
    )

    update_approval_status(approval_request)
    return response


def delegate_approval(response: ApprovalResponse, delegatee, reason: str):
    """Delegate an approval to another user with full audit trail.

    Creates a new ApproverAssignment for the delegatee linked to the
    original (via delegated_from) and removes the original assignment.
    The response is flipped to DELEGATED with the reason as comments.

    Raises:
        ValidationError: delegation not allowed by the template policy.
    """
    if response.approval_request.delegation_policy == ApprovalDelegation.DISABLED:
        raise ValidationError("Delegation not allowed for this approval type")

    response.decision = ApprovalDecision.DELEGATED
    response.delegated_to = delegatee
    response.comments = reason
    response.save()

    request = response.approval_request

    try:
        original_assignment = ApproverAssignment.objects.get(
            approval_request=request,
            user=response.approver,
        )
        ApproverAssignment.objects.create(
            approval_request=request,
            user=delegatee,
            is_required=original_assignment.is_required,
            sequence_order=original_assignment.sequence_order,
            assignment_source=ApproverAssignmentSource.DELEGATION,
            assigned_by=response.approver,
            delegated_from=original_assignment,
        )
        original_assignment.delete()
    except ApproverAssignment.DoesNotExist:
        add_approver(
            request,
            delegatee,
            is_required=True,
            assignment_source=ApproverAssignmentSource.DELEGATION,
            assigned_by=response.approver,
        )

    return response
