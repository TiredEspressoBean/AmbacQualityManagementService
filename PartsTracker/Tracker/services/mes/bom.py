"""
BOM aggregate services.

Versioning operation for the BOM (Bill of Materials) model. Model method
delegates here so status-gate checks and child-row copy live in one place.
"""
from __future__ import annotations

from dataclasses import dataclass

from Tracker.models import BOM, BOMLine


# ── What a BUY line points at ────────────────────────────────────────────────
# A purchased component is EITHER a raw Material (consumables and stock that are
# never parts) OR a buyable PartType (`can_buy` — a part we normally make but are
# sourcing outside, or simply buy). Both are procured and both are stocked as
# MaterialLot rows; they differ only in which column the lot hangs off:
# `MaterialLot.material` vs `MaterialLot.material_type`.
#
# Keeping the two apart matters because only the PartType side carries the quality
# apparatus — receiving-inspection plans, supplier qualification, part approval,
# life limits are all keyed to PartTypes. Routing a purchased *part* through a raw
# Material is what makes it dock-to-stock with no gate.

@dataclass(frozen=True)
class BuyItem:
    """The purchased subject of a BUY line, normalized across both kinds."""
    kind: str               # 'MATERIAL' | 'PART_TYPE'
    id: object
    name: str
    lead_time_days: int | None
    safety_stock: float
    #: MaterialLot column this item's stock hangs off — 'material' or 'material_type'.
    lot_field: str

    @property
    def key(self):
        """Stable identity for dicts that mix both kinds. A Material and a PartType
        can never share a row, but they can share a uuid space, so the kind is part
        of the key."""
        return (self.kind, self.id)


def buy_line_item(line) -> BuyItem | None:
    """Resolve what a BUY line is asking us to purchase, or None when the line isn't
    a usable BUY line (MAKE, or a BUY line with no component set).

    Works on a BOMLine instance. `select_related('material', 'component_type')` on the
    caller's queryset keeps this free of extra queries.
    """
    if line.source != 'BUY':
        return None
    if line.material_id is not None:
        mat = line.material
        return BuyItem(
            kind='MATERIAL', id=line.material_id, name=mat.name,
            lead_time_days=mat.purchase_lead_time_days,
            safety_stock=float(mat.safety_stock or 0),
            lot_field='material',
        )
    if line.component_type_id is not None:
        pt = line.component_type
        # A part flagged make-only on a BUY line is an authoring mistake, not a
        # purchase instruction — surfacing it as buyable would quietly put a part we
        # can't actually source into the sourcing report.
        if not getattr(pt, 'can_buy', False):
            return None
        return BuyItem(
            kind='PART_TYPE', id=line.component_type_id, name=pt.name,
            lead_time_days=getattr(pt, 'purchase_lead_time_days', None),
            # PartTypes has no safety-stock field yet; treated as no buffer rather
            # than guessed. Adding the field makes this line pick it up unchanged.
            safety_stock=float(getattr(pt, 'safety_stock', None) or 0),
            lot_field='material_type',
        )
    return None


def buy_item_from_values(row) -> tuple | None:
    """`buy_line_item`'s key for a BOMLine `.values()` row (the scheduling material
    gate reads dicts, not model instances). Returns (kind, id) or None.

    The `.values()` call must select `material_id`, `component_type_id`,
    `component_type__can_buy` and `source`.
    """
    if row.get('source') != 'BUY':
        return None
    if row.get('material_id') is not None:
        return ('MATERIAL', row['material_id'])
    if row.get('component_type_id') is not None and row.get('component_type__can_buy'):
        return ('PART_TYPE', row['component_type_id'])
    return None


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
                component_type=line.component_type,  # in-house (MAKE)
                material=line.material,              # purchased (BUY)
                source=line.source,
                consumed_at_step=line.consumed_at_step,
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
