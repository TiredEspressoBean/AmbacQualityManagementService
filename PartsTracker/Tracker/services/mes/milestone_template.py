"""
MilestoneTemplate aggregate services.

Versioning operation for the MilestoneTemplate model. Model method
delegates here so child-copy logic lives in one place.

Orders.current_milestone pinning decision
-----------------------------------------
When a MilestoneTemplate is versioned, existing Milestone rows stay
attached to v1 (historical pinning). New Milestone rows are created
with `template=new_version`.

`Orders.current_milestone` is a live FK that points to a specific
Milestone row. After versioning, Orders that were created against v1
continue to point at v1's Milestones. This is correct and intentional:
each Order sees the roadmap that was current when it launched.

DO NOT migrate existing Orders.current_milestone FKs to v2's
Milestones on versioning. That would retroactively rewrite history —
an Order mid-way through v1's gate sequence would suddenly resolve
against v2's (potentially renamed / reordered) milestones.

New Orders created after v2 becomes effective will have their
current_milestone set from v2's Milestone rows.

`Orders.get_gate_info()` reads `self.current_milestone.template.milestones.all()`,
so pinned Orders see v1's full roadmap; new Orders see v2's. No
cross-version walking is needed.
"""
from __future__ import annotations

from Tracker.models.mes_lite import MilestoneTemplate, Milestone


def create_new_milestone_template_version(
    template: MilestoneTemplate,
    *,
    user=None,
    change_description: str,
    **field_updates,
) -> MilestoneTemplate:
    """Create a new version of a MilestoneTemplate.

    MilestoneTemplate is a pure configuration model (no approval
    workflow / status field), so there is no status gate and no
    DRAFT-successor guard. Any current, non-archived template can be
    revised.

    New version inherits all scalar fields. Milestone child rows are
    copied to the new version (new PKs, new `template` FK, all other
    fields preserved). v1's Milestone rows stay untouched (historical
    pinning — see module docstring for the Orders.current_milestone
    rationale).

    MilestoneTemplate has no GenericRelation Documents field, so no
    Document GFK copy loop is needed.

    The `revision_created` signal fires via the base
    `SecureModel.create_new_version` call.

    Args:
        template: The current version to revise.
        user: User triggering the revision (forwarded to signal).
        change_description: Required human narrative of what changed
            and why. ISO 9001 4.4 audit trail.
        **field_updates: Optional field overrides for the new version.

    Raises:
        ValueError: change_description blank; base-inherited (not
            current, archived).
    """
    from django.db import transaction

    if not change_description or not change_description.strip():
        raise ValueError(
            "change_description is required when creating a new "
            "MilestoneTemplate version (ISO 9001 4.4 audit trail)."
        )

    with transaction.atomic():
        # Base handles: row lock, current-version guard, archived guard,
        # scalar field copy (tenant, name, description, is_default),
        # version increment, previous_version link, flipping old row's
        # is_current_version, and firing the revision_created signal
        # post-commit.
        new_version = super(MilestoneTemplate, template).create_new_version(
            user=user,
            change_description=change_description,
            **field_updates,
        )

        for milestone in template.milestones.all():
            Milestone.objects.create(
                template=new_version,
                name=milestone.name,
                customer_display_name=milestone.customer_display_name,
                display_order=milestone.display_order,
                description=milestone.description,
                is_active=milestone.is_active,
                tenant=new_version.tenant,
            )

    return new_version
