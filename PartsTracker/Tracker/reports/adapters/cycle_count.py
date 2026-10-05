"""
Cycle count paperwork — the count sheet to walk the location with, and the discrepancy
report of what didn't match.

A blind count's sheet leaves the expected quantities off, so the counter counts what's
there rather than confirming a number. The discrepancy report is what gets keyed into
the stock register (Glovia); it carries no values, only quantities.

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


class CountLine(BaseModel):
    label: str
    item: str = ""
    unit: str = ""
    expected: Optional[float] = None
    counted: Optional[float] = None
    difference: Optional[float] = None
    what: str = ""
    elsewhere: Optional[str] = None
    note: str = ""


class CycleCountContext(BaseModel):
    our_org: str
    count_number: str
    location: str
    status: str
    blind: bool
    started_by: Optional[str] = None
    submitted_by: Optional[str] = None
    lines: list[CountLine] = []
    issued_date: date


class CycleCountParamsSerializer(serializers.Serializer):
    """{"count_id": <uuid>}"""
    count_id = serializers.UUIDField()

    def validate_count_id(self, value):
        from Tracker.models import CycleCount
        user = self.context.get("user") or getattr(self.context.get("request"), "user", None)
        if user is None:
            raise serializers.ValidationError("Authenticated user required.")
        tenant = getattr(user, "_current_tenant", None) or getattr(user, "tenant", None)
        if tenant is None:
            raise serializers.ValidationError("No tenant context on user.")
        # tenant-safe: explicit tenant filter
        if not CycleCount.unscoped.filter(id=value, tenant=tenant).exists():
            raise serializers.ValidationError(f"Count {value} not found.")
        return value


_WHAT = {"SHORT": "Short", "OVER": "Over", "MISSING": "Not found", "FOUND_HERE": "Found here"}


def _name(u):
    return ((u.get_full_name() or "").strip() or u.email) if u is not None else None


def build_cycle_count_context(count, tenant, *, differences_only: bool) -> CycleCountContext:
    """Caller is responsible for tenant filtering on the count query."""
    from Tracker.services.mes.cycle_count import variances
    if differences_only:
        lines = [CountLine(label=v["label"], item=v.get("item", ""), unit=v.get("unit", ""),
                           expected=v.get("expected"), counted=v.get("counted"),
                           difference=v.get("difference"), what=_WHAT[v["variance"]],
                           elsewhere=v.get("system_location") if v["variance"] == "FOUND_HERE" else None,
                           note=v.get("note", "")) for v in variances(count)]
    else:
        lines = [CountLine(label=l["label"], item=l.get("item", ""), unit=l.get("unit", ""),
                           expected=None if count.blind else l.get("expected"))
                 for l in sorted(count.lines, key=lambda l: (l["kind"], l["label"]))]
    return CycleCountContext(
        our_org=tenant.name, count_number=count.count_number, location=count.location.name,
        status=count.get_status_display(), blind=count.blind,
        started_by=_name(count.started_by), submitted_by=_name(count.submitted_by),
        lines=lines, issued_date=tenant_today(tenant))


class _CycleCountAdapter(ReportAdapter):
    context_model_class = CycleCountContext
    param_serializer_class = CycleCountParamsSerializer
    differences_only = False

    def build_context(self, validated_params, user, tenant) -> CycleCountContext:
        from Tracker.models import CycleCount
        # tenant-safe: explicit tenant filter (defense-in-depth)
        count = (CycleCount.unscoped.filter(tenant=tenant)
                 .select_related("started_by", "submitted_by").get(id=validated_params["count_id"]))
        return build_cycle_count_context(count, tenant, differences_only=self.differences_only)


class CycleCountSheetAdapter(_CycleCountAdapter):
    """The sheet to count a location with — expected quantities left off when blind."""
    name = "cycle_count_sheet"
    title = "Count Sheet"
    template_path = "cycle_count_sheet.typ"

    def get_filename(self, validated_params) -> str:
        return f"count_sheet_{validated_params.get('count_id', 'unknown')}.pdf"


class CycleCountReportAdapter(_CycleCountAdapter):
    """What didn't match, for keying into the stock register."""
    name = "cycle_count_report"
    title = "Count Differences"
    template_path = "cycle_count_report.typ"
    differences_only = True

    def get_filename(self, validated_params) -> str:
        return f"count_differences_{validated_params.get('count_id', 'unknown')}.pdf"
