"""
Staging List adapter — the materials handler's walk sheet.

A different document from the Pick List. The Pick List is per WORK ORDER: the whole
BOM for a job, printed at release. This is per STATION over a time window: everything
arriving at each bench in the next few hours, drawn from the live schedule.

Printed because plenty of shops still work the floor on paper, and because a sheet
survives a dead tablet battery. It carries the same facts as the screen — what to pick,
how much, which lot, where from, where it goes — plus a tick box, so a handler can work
it and hand it over.

Lots come from the same `plan_draw` the real consumption uses, so the sheet names the
lots the system will record. Picking a different one leaves the traceability record
disagreeing with the shelf.
"""
from __future__ import annotations

import datetime
from typing import Optional

from pydantic import BaseModel, Field
from rest_framework import serializers

from Tracker.reports.adapters.base import ReportAdapter


class StagingMaterialRow(BaseModel):
    """One component to pick for one job."""
    material: str
    qty: str
    lots: str
    storage_location: str
    is_short: bool
    short_qty: str


class StagingJobRow(BaseModel):
    """One job arriving at a station."""
    erp_id: str
    step_name: str
    part_type: str
    units: int
    starts_at: str          # already formatted for the sheet
    machine: str
    fixtures: str
    staged: bool
    materials: list[StagingMaterialRow] = Field(default_factory=list)


class StagingStationBlock(BaseModel):
    name: str
    job_count: int
    short_count: int
    jobs: list[StagingJobRow] = Field(default_factory=list)


class StagingListContext(BaseModel):
    window_hours: int
    window_from: str
    window_to: str
    station_filter: str          # "" when every station is included
    is_stale: bool
    note: str                    # e.g. "No active schedule" — empty when there's a plan
    unmapped: list[str] = Field(default_factory=list)
    stations: list[StagingStationBlock] = Field(default_factory=list)
    total_jobs: int
    total_short: int
    tenant_name: str
    generated_date: datetime.date


class StagingListParamsSerializer(serializers.Serializer):
    """Optional station and window. Both have sane defaults so the report can be run
    with no parameters at all — a handler printing "the next shift" shouldn't have to
    fill in a form."""
    work_center = serializers.UUIDField(required=False, allow_null=True)
    hours = serializers.IntegerField(required=False, min_value=1, max_value=72)


class StagingListAdapter(ReportAdapter):
    """Renders the staging list for one station, or all of them, as a walk sheet."""

    # `name` is the API identifier and stays put; `title` is what people read.
    # This is the Kit Sheet — the second half of the round, after the Pick Sheet
    # (pick_sheet) has pulled everything from the shelves in one walk.
    name = "staging_list"
    title = "Kit Sheet"
    template_path = "staging_list.typ"
    context_model_class = StagingListContext
    param_serializer_class = StagingListParamsSerializer

    def build_context(self, validated_params, user, tenant) -> StagingListContext:
        from Tracker.models import WorkCenter
        from Tracker.services.mes.staging import staging_list

        wc_id = validated_params.get("work_center")
        hours = validated_params.get("hours") or 8
        data = staging_list(tenant, str(wc_id) if wc_id else None, hours)

        station_name = ""
        if wc_id:
            # tenant-safe: explicit tenant filter (defense-in-depth)
            wc = WorkCenter.objects.filter(tenant=tenant, id=wc_id).first()
            station_name = wc.name if wc else ""

        def _fmt_dt(value) -> str:
            return value.strftime("%b %d %H:%M") if value else ""

        stations: list[StagingStationBlock] = []
        for st in data["stations"]:
            jobs: list[StagingJobRow] = []
            for j in st["jobs"]:
                mats = [
                    StagingMaterialRow(
                        material=m["material"],
                        qty=_num(m["needed"]),
                        lots=", ".join(l["lot_number"] for l in m.get("lots", [])),
                        storage_location=next(
                            (l["storage_location"] for l in m.get("lots", [])
                             if l["storage_location"]), ""),
                        is_short=m["short"] > 0,
                        short_qty=_num(m["short"]) if m["short"] > 0 else "",
                    )
                    for m in j["materials"]
                ]
                jobs.append(StagingJobRow(
                    erp_id=j["erp_id"], step_name=j["step_name"],
                    part_type=j.get("part_type") or "",
                    units=j["units"], starts_at=_fmt_dt(j["starts_at"]),
                    machine=j.get("machine") or "",
                    fixtures=", ".join(j.get("fixtures") or []),
                    staged=bool(j.get("staged_at")),
                    materials=mats,
                ))
            stations.append(StagingStationBlock(
                name=st["name"], job_count=len(jobs),
                short_count=st["short_count"], jobs=jobs,
            ))

        return StagingListContext(
            window_hours=data["window_hours"],
            window_from=_fmt_dt(data["from"]),
            window_to=_fmt_dt(data["to"]),
            station_filter=station_name,
            is_stale=bool(data["is_stale"]),
            note=data.get("note") or "",
            unmapped=[f"{u['erp_id']} — {', '.join(u['components'])}"
                      for u in data.get("unmapped", [])],
            stations=stations,
            total_jobs=sum(s.job_count for s in stations),
            total_short=sum(s.short_count for s in stations),
            tenant_name=tenant.name,
            generated_date=datetime.date.today(),
        )

    def get_filename(self, validated_params) -> str:
        return f"staging_list_{datetime.date.today():%Y%m%d}.pdf"


def _num(value) -> str:
    """Whole numbers without a trailing .0 — a sheet reads '11', not '11.0'."""
    f = float(value)
    return str(int(f)) if f == int(f) else str(f)
