"""
Pick Sheet adapter — the shelf sweep.

The first of the two material documents, and the one that saves the legs:
everything to be pulled from stores for the next N hours, one row per MATERIAL
across every job, ordered by where it lives.

It is not a rival to the Kit Sheet, it is the other half of the same round:

    Pick Sheet   -> pull, by material, one trip per bin        (this document)
    Kit Sheet    -> sort and deliver, by kit, one per bench    (staging_list)

Batch-picking a material once for six jobs beats six walks to the same bin. The
entire price of that is sortation, which is why every row prints its `drops` —
the kits each portion belongs to. A picker holding 200 seals and no split has been
made faster at the cost of being unable to finish.

Note on traceability: because batching commingles, the lot a unit actually received
is recorded at the SORT (on the Kit Sheet), not here. This sheet names the lots the
combined draw will take; it does not claim which kit got which lot.
"""
from __future__ import annotations

import datetime
from typing import Optional

from pydantic import BaseModel, Field
from rest_framework import serializers

from Tracker.reports.adapters.base import ReportAdapter


class PickDrop(BaseModel):
    """Where one portion of a material row is going — the sortation instruction."""
    qty: str
    station: str
    erp_id: str
    step_name: str
    staged: bool


class PickSheetRow(BaseModel):
    """One material to pull, totalled across every job in the window."""
    material: str
    qty: str
    storage_location: str
    lots: str
    is_short: bool
    short_qty: str
    drops: list[PickDrop] = Field(default_factory=list)


class PickSheetContext(BaseModel):
    window_hours: int
    window_from: str
    window_to: str
    station_filter: str          # "" when every station is included
    is_stale: bool
    note: str                    # e.g. "No active schedule" — empty when there's a plan
    rows: list[PickSheetRow] = Field(default_factory=list)
    unmapped: list[str] = Field(default_factory=list)
    total_lines: int
    total_short: int
    total_kits: int
    tenant_name: str
    generated_date: datetime.date


class PickSheetParamsSerializer(serializers.Serializer):
    """Station and window both optional — a picker printing "the next shift" should
    not have to fill in a form."""
    work_center = serializers.UUIDField(required=False, allow_null=True)
    hours = serializers.IntegerField(required=False, min_value=1, max_value=72)


class PickSheetAdapter(ReportAdapter):
    """Renders the consolidated shelf pull for a time window."""

    name = "pick_sheet"
    title = "Pick Sheet"
    template_path = "pick_sheet.typ"
    context_model_class = PickSheetContext
    param_serializer_class = PickSheetParamsSerializer

    def build_context(self, validated_params, user, tenant) -> PickSheetContext:
        from Tracker.models import WorkCenter
        from Tracker.services.mes.staging import consolidated_pick

        wc_id = validated_params.get("work_center")
        hours = validated_params.get("hours") or 8
        data = consolidated_pick(tenant, str(wc_id) if wc_id else None, hours)

        station_name = ""
        if wc_id:
            # tenant-safe: explicit tenant filter (defense-in-depth)
            wc = WorkCenter.objects.filter(tenant=tenant, id=wc_id).first()
            station_name = wc.name if wc else ""

        def _fmt_dt(value) -> str:
            return value.strftime("%b %d %H:%M") if value else ""

        rows = [
            PickSheetRow(
                material=r["material"],
                qty=_num(r["needed"]),
                storage_location=r["storage_location"],
                lots=", ".join(l["lot_number"] for l in r["lots"]),
                is_short=r["short"] > 0,
                short_qty=_num(r["short"]) if r["short"] > 0 else "",
                drops=[
                    PickDrop(qty=_num(d["qty"]), station=d["station"],
                             erp_id=d["erp_id"], step_name=d["step_name"],
                             staged=d["staged"])
                    for d in r["drops"]
                ],
            )
            for r in data.get("materials", [])
        ]

        kits = {(d.erp_id, d.step_name) for r in rows for d in r.drops}

        return PickSheetContext(
            window_hours=data["window_hours"],
            window_from=_fmt_dt(data["from"]),
            window_to=_fmt_dt(data["to"]),
            station_filter=station_name,
            is_stale=bool(data["is_stale"]),
            note=data.get("note") or "",
            rows=rows,
            unmapped=[f"{u['erp_id']} — {', '.join(u['components'])}"
                      for u in data.get("unmapped", [])],
            total_lines=len(rows),
            total_short=sum(1 for r in rows if r.is_short),
            total_kits=len(kits),
            tenant_name=tenant.name,
            generated_date=datetime.date.today(),
        )

    def get_filename(self, validated_params) -> str:
        return f"pick_sheet_{datetime.date.today():%Y%m%d}.pdf"


def _num(value) -> str:
    """Whole numbers without a trailing .0 — a sheet reads '11', not '11.0'."""
    f = float(value)
    return str(int(f)) if f == int(f) else str(f)
