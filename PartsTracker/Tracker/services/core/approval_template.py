"""
ApprovalTemplate aggregate services.

Versioning operations for the ApprovalTemplate model. Model method
delegates here so M2M-copy logic and cross-aggregate writes live in
one place.
"""
from __future__ import annotations

from Tracker.models.core import ApprovalTemplate


def create_new_approval_template_version(
    template: ApprovalTemplate,
    *,
    user=None,
    change_description: str,
    **field_updates,
) -> ApprovalTemplate:
    """Create a new version of an ApprovalTemplate.

    ApprovalTemplate has no status lifecycle field (only `deactivated_at`,
    a soft-deactivation datetime, not an approval gate). There is therefore
    no status gate and no DRAFT-successor guard — any current, non-archived
    template can be revised at any time. This mirrors the LifeLimitDefinition
    pattern rather than the Processes/BOM pattern.

    Scalar fields are copied forward by the base `SecureModel.create_new_version`
    call. M2M memberships (`default_approvers`, `default_groups`) are then
    re-created on the new version via `.set()`, which inserts fresh
    through-table rows pointing at the same User/TenantGroup on the other side.
    Historical pinning is preserved: the original version's through rows still
    point at the original ApprovalTemplate row; new through rows point at the
    new one. The two sets can diverge independently after creation.

    NOT copied: ApproverAssignment / GroupApproverAssignment — those through
    models are children of ApprovalRequest, not ApprovalTemplate. Each
    ApprovalRequest builds its own assignment set when it is created from the
    template.

    ApprovalTemplate has no GenericRelation Documents field, so no Document
    GFK copy loop is needed.

    The `revision_created` signal fires via the base
    `SecureModel.create_new_version` call.

    Args:
        template: The current version to revise.
        user: User triggering the revision (forwarded to signal).
        change_description: Required human narrative of what changed
            and why. ISO 9001 4.4 / MIL-HDBK-61A CCB process audit trail.
        **field_updates: Optional field overrides for the new version.

    Raises:
        ValueError: change_description blank; base-inherited (not current,
            archived).
    """
    from django.db import transaction

    if not change_description or not change_description.strip():
        raise ValueError(
            "change_description is required when creating a new "
            "ApprovalTemplate version (ISO 9001 4.4 / MIL-HDBK-61A CCB audit trail)."
        )

    # M2M overrides can't be forwarded as `field_updates` to the base
    # `create_new_version` (Django raises on direct M2M assignment) —
    # pop them here and apply via `.set()` after the new row exists.
    approvers_override = field_updates.pop('default_approvers', None)
    groups_override = field_updates.pop('default_groups', None)

    with transaction.atomic():
        # Base handles: row lock, current-version guard, archived guard,
        # scalar field copy (tenant, template_name, approval_type,
        # approval_flow_type, delegation_policy, approval_sequence,
        # allow_self_approval, default_due_days, escalation_days,
        # default_threshold, auto_assign_by_role, escalate_to,
        # deactivated_at), version increment, previous_version link,
        # flipping old row's is_current_version, and firing the
        # revision_created signal post-commit.
        new_version = super(ApprovalTemplate, template).create_new_version(
            user=user,
            change_description=change_description,
            **field_updates,
        )

        # M2M assignment. When the caller passed explicit overrides
        # (PATCH from the editor with the full intended membership), use
        # them. Otherwise carry the existing membership forward from the
        # source version.
        new_version.default_approvers.set(
            approvers_override
            if approvers_override is not None
            else template.default_approvers.all()
        )
        new_version.default_groups.set(
            groups_override
            if groups_override is not None
            else template.default_groups.all()
        )

    return new_version


def make_default(template: ApprovalTemplate) -> ApprovalTemplate:
    """Make `template` the default for its approval type, unsetting the previous default
    in the same transaction (one current default per tenant and type; user decision
    2026-10-29). Not a content edit — no new version."""
    from django.db import transaction
    with transaction.atomic():
        # tenant-safe: scoped by the template's own tenant
        ApprovalTemplate.objects.filter(
            tenant_id=template.tenant_id, approval_type=template.approval_type,
            is_current_version=True, is_default=True,
        ).exclude(pk=template.pk).update(is_default=False)
        if not template.is_default:
            ApprovalTemplate.objects.filter(pk=template.pk).update(is_default=True)  # tenant-safe: pk
            template.is_default = True
    return template
