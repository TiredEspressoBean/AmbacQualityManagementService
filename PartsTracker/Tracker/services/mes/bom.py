"""
BOM aggregate services.

Versioning operation for the BOM (Bill of Materials) model. Model method
delegates here so status-gate checks and child-row copy live in one place.
"""
from __future__ import annotations

from Tracker.models import BOM, BOMLine


def create_new_bom_version(
    bom: BOM,
    *,
    user,
    change_description: str,
    **field_updates,
) -> BOM:
    """Create a new version of a RELEASED or OBSOLETE BOM.

    New version starts in DRAFT with approved_at/approved_by cleared.
    Scalar fields, tenant, part_type, bom_type, description, revision,
    and effective/obsolete dates carry forward via the base scalar-copy
    mechanism. BOMLine rows are copied to the new BOM (same component_type
    FK — PartTypes are independently versioned and historically pinned; we
    carry the reference forward, not a clone).

    BOM has no GenericRelation Documents, so no document copy is performed.

    The `revision_created` signal fires via the base
    `SecureModel.create_new_version` call.

    Args:
        bom: The current version to revise.
        user: User triggering the revision (forwarded to signal).
        change_description: Required human narrative of what changed
            and why. ISO 9001 4.4 / AIAG PPAP #3 / IATF 16949 8.5.6.1
            compliance.
        **field_updates: Optional field overrides for the new DRAFT.

    Raises:
        ValueError: change_description blank; status not RELEASED/OBSOLETE;
            a DRAFT successor already exists; base-inherited (not current,
            archived).
    """
    from django.db import transaction

    if not change_description or not change_description.strip():
        raise ValueError(
            "change_description is required when creating a new BOM "
            "version (ISO 9001 4.4 / AIAG PPAP #3 / IATF 16949 8.5.6.1 "
            "audit trail)."
        )

    # Status gate: RELEASED maps to APPROVED semantics; OBSOLETE maps to
    # DEPRECATED semantics. DRAFT is edited in place — a new version from
    # DRAFT would break the linear history chain.
    if bom.status not in ('RELEASED', 'OBSOLETE'):
        raise ValueError(
            f"Cannot create a new version from a BOM in status "
            f"{bom.status!r}. Only RELEASED or OBSOLETE BOMs can be "
            f"revised; DRAFT is edited in place."
        )

    # tenant-safe: previous_version FK constrains to BOMs in the same tenant
    # as `bom` (versioning chains never cross tenants).
    existing_draft = BOM.all_tenants.filter(
        previous_version=bom,
        status='DRAFT',
    ).first()
    if existing_draft:
        raise ValueError(
            f"A draft revision (v{existing_draft.version}) already exists "
            f"for this BOM. Complete or discard it before creating "
            f"another revision."
        )

    with transaction.atomic():
        # Base handles: row lock, current-version guard, archived guard,
        # scalar field copy (tenant, part_type, revision, bom_type,
        # description, effective_date, obsolete_date), version increment,
        # previous_version link, flipping old row's is_current_version,
        # and firing the revision_created signal post-commit.
        new_version = super(BOM, bom).create_new_version(
            user=user,
            change_description=change_description,
            # Reset lifecycle state on the new draft.
            status='DRAFT',
            approved_at=None,
            approved_by=None,
            **field_updates,
        )

        for line in bom.lines.all():
            # tenant-safe: scoped via bom FK (BOM is tenant-scoped)
            BOMLine.objects.create(
                bom=new_version,
                component_type=line.component_type,
                quantity=line.quantity,
                unit_of_measure=line.unit_of_measure,
                find_number=line.find_number,
                reference_designator=line.reference_designator,
                is_optional=line.is_optional,
                allow_harvested=line.allow_harvested,
                notes=line.notes,
                line_number=line.line_number,
            )

    return new_version
