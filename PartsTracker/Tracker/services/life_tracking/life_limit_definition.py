"""
LifeLimitDefinition aggregate services.

Versioning operations for the LifeLimitDefinition model. Model method
delegates here so child-copy logic and cross-aggregate writes live in
one place.
"""
from __future__ import annotations

from Tracker.models.life_tracking import LifeLimitDefinition, PartTypeLifeLimit


def create_new_life_limit_definition_version(
    instance: LifeLimitDefinition,
    *,
    user=None,
    change_description: str,
    **field_updates,
) -> LifeLimitDefinition:
    """Create a new version of a LifeLimitDefinition.

    LifeLimitDefinition is a pure specification model (no approval workflow
    / status field), so there is no status gate and no DRAFT-successor guard.
    Any current, non-archived definition can be revised.

    New version inherits all scalar fields. PartTypeLifeLimit junction rows
    are copied to the new version (same part_type FKs — historical pinning).
    LifeTracking transactional records are NOT copied — they remain
    referenced to the version they were recorded against.

    LifeLimitDefinition has no GenericRelation Documents field, so no
    Document GFK copy loop is needed.

    The `revision_created` signal fires via the base
    `SecureModel.create_new_version` call.

    Args:
        instance: The current version to revise.
        user: User triggering the revision (forwarded to signal).
        change_description: Required human narrative of what changed
            and why. AS9100D §8.3 / ISO 9001 4.4 audit trail.
        **field_updates: Optional field overrides for the new version.

    Raises:
        ValueError: change_description blank; base-inherited (not current,
            archived).
    """
    from django.db import transaction

    if not change_description or not change_description.strip():
        raise ValueError(
            "change_description is required when creating a new "
            "LifeLimitDefinition version (AS9100D §8.3 audit trail)."
        )

    with transaction.atomic():
        # Base handles: row lock, current-version guard, archived guard,
        # scalar field copy (tenant, name, unit, unit_label,
        # is_calendar_based, soft_limit, hard_limit), version increment,
        # previous_version link, flipping old row's is_current_version,
        # and firing the revision_created signal post-commit.
        new_version = super(LifeLimitDefinition, instance).create_new_version(
            user=user,
            change_description=change_description,
            **field_updates,
        )

        for link in instance.part_type_links.all():
            PartTypeLifeLimit.objects.create(
                definition=new_version,
                part_type=link.part_type,
                is_required=link.is_required,
            )

    return new_version
