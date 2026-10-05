"""
Location labels — a barcode for a shelf, cage, rack or bin.

The Code 128 carries ``LOC:<name>``, so a scanner tells a location from a lot or a
serial (services/core/scan.py). The QR opens the location's page. Same 4"×2" stock and
Letter-sheet layout as lot labels.

Labels are printed by name, so a location a shop has only ever typed (not on its
managed list) can still get one.
"""
from __future__ import annotations

from datetime import date
from typing import Optional
from urllib.parse import quote

from django.conf import settings
from pydantic import BaseModel
from rest_framework import serializers

from Tracker.reports.adapters.base import ReportAdapter
from Tracker.reports.services.barcodes import render_barcode_svg, render_qr_svg
from Tracker.services.core.clock import tenant_today
from Tracker.services.mes.locations import LOCATION_PREFIX

LAYOUTS = ("thermal", "sheet")


class LocationLabelContext(BaseModel):
    name: str
    description: Optional[str] = None
    barcode_svg: str
    qr_svg: str
    tenant_name: str
    print_date: date


class LocationLabelBatchContext(BaseModel):
    layout: str
    labels: list[LocationLabelContext]


class LocationLabelParamsSerializer(serializers.Serializer):
    """{"names": ["Rack 3", ...], "copies": 1, "layout": "thermal" | "sheet"}"""
    names = serializers.ListField(child=serializers.CharField(max_length=100), allow_empty=False,
                                  max_length=200)
    copies = serializers.IntegerField(min_value=1, max_value=50, default=1)
    layout = serializers.ChoiceField(choices=LAYOUTS, default="thermal")

    def validate_names(self, value):
        names = [v.strip() for v in value if v.strip()]
        if not names:
            raise serializers.ValidationError("Name at least one location.")
        return names


def build_location_label_context(name: str, description: Optional[str], tenant) -> LocationLabelContext:
    url = f"{settings.FRONTEND_URL.rstrip('/')}/production/locations/{quote(name, safe='')}"
    return LocationLabelContext(
        name=name, description=description or None,
        barcode_svg=render_barcode_svg(f"{LOCATION_PREFIX}{name}", module_height=8.0),
        qr_svg=render_qr_svg(url),
        tenant_name=tenant.name, print_date=tenant_today(tenant))


class LocationLabelAdapter(ReportAdapter):
    """Labels for storage locations, ``copies`` of each."""

    name = "location_label"
    title = "Location Label"
    template_path = "location_label.typ"
    context_model_class = LocationLabelBatchContext
    param_serializer_class = LocationLabelParamsSerializer

    def build_context(self, validated_params, user, tenant) -> LocationLabelBatchContext:
        from Tracker.models import StorageLocation
        # tenant-safe: explicit tenant filter (defense-in-depth)
        described = {s.name.casefold(): s.description for s in StorageLocation.unscoped.filter(tenant=tenant)}
        copies = validated_params.get("copies", 1)
        labels = [build_location_label_context(n, described.get(n.casefold()), tenant)
                  for n in validated_params["names"] for _ in range(copies)]
        return LocationLabelBatchContext(layout=validated_params.get("layout", "thermal"), labels=labels)

    def get_filename(self, validated_params) -> str:
        names = validated_params.get("names") or []
        return "location_label.pdf" if len(names) == 1 else f"location_labels_{len(names)}.pdf"
