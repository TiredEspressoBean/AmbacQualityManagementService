"""
Hold / quarantine tag — the removable tag that goes ON nonconforming material.

ISO 9001 §8.7.1: nonconforming output is identified so it isn't used by mistake. The
system identifies a held lot or part; this is the physical identification. The
permanent labels (part_id_label, material_lot_label) deliberately carry no status —
"Awaiting inspection" on a lot accepted last week is worse than no label — and say
status is carried by a separate hold tag. This is that tag.

One tag for a material lot or a part. It reads the existing hold state, and nothing
else: the lot's status and hold reasons, the part's status, the open disposition
behind either (its NCR / VDMR number and description), and who set the status and when
(from the audit log). No new model, no auto-print.

    HOLD        a lot held for a named reason (no CoC, unqualified supplier, …), or a
                part on hold
    QUARANTINE  a quarantined lot or part, waiting for its disposition
    REJECTED    a rejected lot, or a part dispositioned scrap

Refused for an item that isn't held: a tag that says HOLD on good material is the
same mistake in the other direction.

Defense-in-depth: build_context() filters by tenant explicitly, in addition to the
param serializer's upstream check.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel
from rest_framework import serializers

from Tracker.reports.adapters.base import ReportAdapter
from Tracker.services.core.clock import tenant_today

# What a receiving hold code means, in words a person reads off the tag.
HOLD_REASON_LABELS = {
    "SUPPLIER_UNQUALIFIED": "Unqualified supplier",
    "PART_UNAPPROVED": "Part not approved from this supplier",
    "SHELF_LIFE_EXPIRED": "Shelf life expired",
    "AWAITING_COC": "Awaiting certificate of conformance",
    "AWAITING_HEAT_NUMBER": "Awaiting heat number",
    "GAUGE_UNAVAILABLE": "Inspection gauge unavailable",
    "QUALITY_GATE": "Held by a quality gate",
}

LOT_HELD = {"QUARANTINE": "QUARANTINE", "REJECTED": "REJECTED"}
PART_HELD = {"QUARANTINED": "QUARANTINE", "ON_HOLD": "HOLD",
             "REWORK_NEEDED": "HOLD", "SCRAPPED": "REJECTED"}


class HoldTagContext(BaseModel):
    heading: str                       # HOLD / QUARANTINE / REJECTED
    kind: str                          # "Material lot" / "Part"
    item_name: str
    part_number: Optional[str] = None
    identifier_label: str              # "Lot" / "Serial"
    identifier: str
    quantity: str
    location: Optional[str] = None
    work_order: Optional[str] = None
    step: Optional[str] = None
    reasons: list[str] = []
    record_number: Optional[str] = None   # the NCR / VDMR (disposition) number
    record_note: str = ""                 # what the disposition says
    report_numbers: list[str] = []        # the failed quality reports behind it
    placed_by: Optional[str] = None
    placed_at: Optional[str] = None       # the plant's local time, "2026-11-01 09:40"
    tenant_name: str
    print_date: date


def _resolve_tenant(context):
    user = context.get("user") or getattr(context.get("request"), "user", None)
    if user is None:
        raise serializers.ValidationError("Authenticated user required.")
    tenant = getattr(user, "_current_tenant", None) or getattr(user, "tenant", None)
    if tenant is None:
        raise serializers.ValidationError("No tenant context on user.")
    return tenant


class HoldTagParamsSerializer(serializers.Serializer):
    """{"lot_id": <uuid>} or {"part_id": <uuid>} — exactly one, and it must be held."""

    lot_id = serializers.UUIDField(required=False)
    part_id = serializers.UUIDField(required=False)

    def validate(self, attrs):
        from Tracker.models import MaterialLot, Parts
        if bool(attrs.get("lot_id")) == bool(attrs.get("part_id")):
            raise serializers.ValidationError("Give exactly one of lot_id or part_id.")
        tenant = _resolve_tenant(self.context)
        if attrs.get("lot_id"):
            # tenant-safe: explicit tenant filter
            lot = MaterialLot.unscoped.filter(id=attrs["lot_id"], tenant=tenant).first()
            if lot is None:
                raise serializers.ValidationError(f"Lot {attrs['lot_id']} not found.")
            if lot.status not in LOT_HELD:
                raise serializers.ValidationError(
                    f"Lot {lot.lot_number} isn't held ({lot.get_status_display()}) — nothing to tag.")
        else:
            # tenant-safe: explicit tenant filter
            part = Parts.unscoped.filter(id=attrs["part_id"], tenant=tenant).first()
            if part is None:
                raise serializers.ValidationError(f"Part {attrs['part_id']} not found.")
            if part.part_status not in PART_HELD:
                raise serializers.ValidationError(
                    f"{part.ERP_id} isn't held ({part.get_part_status_display()}) — nothing to tag.")
        return attrs


def _num(v) -> str:
    text = f"{v:f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def _who(user) -> Optional[str]:
    if user is None:
        return None
    return (user.get_full_name() or "").strip() or getattr(user, "email", None) or str(user)


def _local(when, tenant) -> Optional[str]:
    """A timestamp on the plant's clock, as the floor reads it."""
    if when is None:
        return None
    from django.utils import timezone
    from Tracker.services.core.clock import plant_tz
    return timezone.localtime(when, plant_tz(tenant)).strftime("%Y-%m-%d %H:%M")


def _status_set(obj, field: str, value: str):
    """(who, when) the audit log says `field` last became `value` on `obj`."""
    from auditlog.models import LogEntry
    from django.contrib.contenttypes.models import ContentType
    entries = (LogEntry.objects.filter(  # tenant-safe: rows keyed to one in-tenant object
        content_type=ContentType.objects.get_for_model(obj.__class__), object_pk=str(obj.pk))
        .select_related("actor").order_by("-timestamp"))
    for e in entries:
        change = (e.changes_dict or {}).get(field)
        if change and len(change) == 2 and change[1] == value:
            return _who(e.actor), e.timestamp
    return None, None


def _open_disposition(tenant, **target):
    from Tracker.models import QuarantineDisposition
    qs = QuarantineDisposition.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, archived=False, **target)
    return (qs.filter(current_state__in=["OPEN", "IN_PROGRESS"]).order_by("-created_at").first()
            or qs.order_by("-created_at").first())


def _disposition_bits(disposition):
    if disposition is None:
        return None, "", []
    reports = sorted(disposition.quality_reports.filter(status="FAIL")
                     .values_list("report_number", flat=True))
    return disposition.disposition_number, (disposition.description or "").strip(), reports


def build_lot_tag(lot, tenant) -> HoldTagContext:
    from Tracker.services.qms import lot_holds
    item = lot.item
    disposition = _open_disposition(tenant, material_lot=lot)
    number, note, reports = _disposition_bits(disposition)
    reasons = [HOLD_REASON_LABELS.get(c, c.replace("_", " ").capitalize())
               for c in lot_holds.holds(lot)]
    heading = LOT_HELD[lot.status]
    if heading == "QUARANTINE" and reasons and disposition is None:
        heading = "HOLD"   # held for a named reason, no nonconformance decision pending
    who, when = _status_set(lot, "status", lot.status)
    return HoldTagContext(
        heading=heading, kind="Material lot",
        item_name=lot.item_name or "—",
        part_number=(getattr(item, "part_number", None) or getattr(item, "ERP_id", None) or None)
        if item is not None else None,
        identifier_label="Lot", identifier=lot.lot_number,
        quantity=f"{_num(lot.quantity_remaining)} {lot.unit_of_measure}".strip(),
        location=getattr(lot, "storage_location", None) or None,
        reasons=reasons, record_number=number, record_note=note, report_numbers=reports,
        placed_by=who, placed_at=_local(when, tenant),
        tenant_name=tenant.name, print_date=tenant_today(tenant),
    )


def build_part_tag(part, tenant) -> HoldTagContext:
    disposition = _open_disposition(tenant, part=part)
    number, note, reports = _disposition_bits(disposition)
    heading = PART_HELD[part.part_status]
    reasons = [part.get_part_status_display()]
    if disposition is not None and disposition.disposition_type:
        reasons.append(f"Disposition: {disposition.get_disposition_type_display()}")
    who, when = _status_set(part, "part_status", part.part_status)
    pt = part.part_type
    return HoldTagContext(
        heading=heading, kind="Part",
        item_name=pt.name if pt else "—",
        part_number=(pt.ERP_id or None) if pt else None,
        identifier_label="Serial", identifier=part.ERP_id,
        quantity="1",
        work_order=part.work_order.ERP_id if part.work_order_id else None,
        step=part.step.name if part.step_id else None,
        reasons=reasons, record_number=number, record_note=note, report_numbers=reports,
        placed_by=who, placed_at=_local(when, tenant),
        tenant_name=tenant.name, print_date=tenant_today(tenant),
    )


class HoldTagAdapter(ReportAdapter):
    """The hold / quarantine tag for one held lot or part."""

    name = "hold_tag"
    title = "Hold Tag"
    template_path = "hold_tag.typ"
    context_model_class = HoldTagContext
    param_serializer_class = HoldTagParamsSerializer

    def build_context(self, validated_params, user, tenant) -> HoldTagContext:
        from Tracker.models import MaterialLot, Parts
        if validated_params.get("lot_id"):
            # tenant-safe: explicit tenant filter (defense-in-depth)
            lot = (MaterialLot.unscoped.filter(tenant=tenant)
                   .select_related("material", "material_type").get(id=validated_params["lot_id"]))
            return build_lot_tag(lot, tenant)
        # tenant-safe: explicit tenant filter (defense-in-depth)
        part = (Parts.unscoped.filter(tenant=tenant)
                .select_related("part_type", "work_order", "step").get(id=validated_params["part_id"]))
        return build_part_tag(part, tenant)

    def get_filename(self, validated_params) -> str:
        target = validated_params.get("lot_id") or validated_params.get("part_id") or "unknown"
        return f"hold_tag_{target}.pdf"
