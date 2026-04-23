"""
Part ID Label — batch (multi-label PDF).

Emits one 4"×2" thermal label per Part on its own page. Accepts either:
  - `part_ids`: explicit list of Part UUIDs, OR
  - `work_order_id`: expand to every Part attached to that WO

The template iterates `data.labels` and pagebreaks between entries so the
PDF feeds cleanly into a Zebra-style thermal printer's print-N-copies
behavior. Label rendering is identical to part_id_label.typ — both read
the same PartIdLabelContext per entry via `build_part_id_label_context`.

Defense-in-depth: every ORM query inside build_context() filters by
tenant explicitly, in addition to the param serializer's upstream check.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel
from rest_framework import serializers

from Tracker.reports.adapters.base import ReportAdapter
from Tracker.reports.adapters.part_id_label import (
    PartIdLabelContext,
    build_part_id_label_context,
)


# ---------------------------------------------------------------------------
# Pydantic context model
# ---------------------------------------------------------------------------


class PartIdLabelBatchContext(BaseModel):
    """Top-level shape passed to the part_id_label_batch.typ template."""

    labels: list[PartIdLabelContext]


# ---------------------------------------------------------------------------
# DRF param serializer
# ---------------------------------------------------------------------------


class PartIdLabelBatchParamsSerializer(serializers.Serializer):
    """
    Accepts either:
      - {"part_ids": [uuid, uuid, ...]}  — explicit list
      - {"work_order_id": <uuid>}        — expand to all parts of a WO

    Exactly one of the two must be provided. Every returned id is
    re-verified against the requesting user's tenant; adapter re-queries
    with an explicit tenant filter for defense-in-depth.
    """

    part_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=False,
        max_length=500,
    )
    work_order_id = serializers.UUIDField(required=False)

    def validate(self, attrs):
        from Tracker.models.mes_lite import Parts, WorkOrder

        part_ids = attrs.get("part_ids")
        work_order_id = attrs.get("work_order_id")
        if bool(part_ids) == bool(work_order_id):
            raise serializers.ValidationError(
                "Provide exactly one of 'part_ids' or 'work_order_id'."
            )

        user = self.context.get("user") or (
            getattr(self.context.get("request"), "user", None)
        )
        if user is None:
            raise serializers.ValidationError("Authenticated user required.")

        tenant = getattr(user, "_current_tenant", None) or getattr(user, "tenant", None)
        if tenant is None:
            raise serializers.ValidationError("No tenant context on user.")

        if part_ids:
            found = set(
                Parts.objects.filter(
                    id__in=part_ids, tenant=tenant,
                ).values_list("id", flat=True)
            )
            missing = [str(pid) for pid in part_ids if pid not in found]
            if missing:
                raise serializers.ValidationError(
                    f"Parts not found in tenant: {', '.join(missing)}"
                )
            attrs["_resolved_part_ids"] = list(part_ids)
        else:
            wo_exists = WorkOrder.objects.filter(
                id=work_order_id, tenant=tenant,
            ).exists()
            if not wo_exists:
                raise serializers.ValidationError(
                    f"Work order {work_order_id} not found."
                )
            resolved = list(
                Parts.objects.filter(
                    work_order_id=work_order_id, tenant=tenant,
                ).values_list("id", flat=True)
            )
            if not resolved:
                raise serializers.ValidationError(
                    "Work order has no parts to label."
                )
            attrs["_resolved_part_ids"] = resolved

        return attrs


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class PartIdLabelBatchAdapter(ReportAdapter):
    """Renders a multi-page PDF of Part ID labels, one label per page."""

    name = "part_id_label_batch"
    title = "Part ID Labels (Batch)"
    template_path = "part_id_label_batch.typ"
    context_model_class = PartIdLabelBatchContext
    param_serializer_class = PartIdLabelBatchParamsSerializer

    def build_context(self, validated_params, user, tenant) -> PartIdLabelBatchContext:
        from Tracker.models.mes_lite import Parts

        part_ids = validated_params["_resolved_part_ids"]

        # tenant-safe: explicit tenant filter (defense-in-depth)
        parts = list(
            Parts.objects
            .filter(tenant=tenant, id__in=part_ids)
            .select_related("part_type", "work_order", "tenant")
        )

        # Preserve requested ordering for explicit part_ids input.
        if validated_params.get("part_ids"):
            by_id = {p.id: p for p in parts}
            parts = [by_id[pid] for pid in part_ids if pid in by_id]
        else:
            parts.sort(key=lambda p: (p.ERP_id or "", str(p.id)))

        labels = [build_part_id_label_context(p, tenant) for p in parts]
        return PartIdLabelBatchContext(labels=labels)

    def get_filename(self, validated_params) -> str:
        wo_id = validated_params.get("work_order_id")
        if wo_id:
            return f"part_labels_wo_{wo_id}.pdf"
        count = len(validated_params.get("part_ids") or [])
        return f"part_labels_batch_{count}.pdf"
