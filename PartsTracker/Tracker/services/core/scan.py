"""What a scanned code is.

A handheld scanner is a keyboard: it types the code and presses Enter. So scanning
needs no driver — only one place that turns whatever was typed into the thing it names.
That place is here, and every scan field asks it.

A code can be:
- one of our own URLs, from a label's QR code — the path is the answer;
- ``LOC:<name>``, from a location label;
- a lot number, a serial (part ERP id), a work-order number, or a location name,
  matched exactly (case-insensitive), tried in that order.

Supplier barcodes are deliberately not parsed (decided 2026-09-30: too varied to trust).
"""
from __future__ import annotations

import re
from urllib.parse import quote, unquote, urlparse

from Tracker.services.mes.locations import LOCATION_PREFIX

_LOT_PATH = re.compile(r"^/production/material-lots/([0-9a-f-]{36})/?$", re.I)
_LOCATION_PATH = re.compile(r"^/production/locations/([^/]+)/?$", re.I)


def _lot(lot) -> dict:
    return {"kind": "LOT", "id": str(lot.id), "label": lot.lot_number,
            "detail": lot.item_name or "", "path": f"/production/material-lots/{lot.id}",
            "item_id": str(lot.material_id or lot.material_type_id or "") or None}


def _location(name: str) -> dict:
    return {"kind": "LOCATION", "id": name, "label": name, "detail": "",
            "path": f"/production/locations/{quote(name, safe='')}", "item_id": None}


def resolve_scan(tenant, code: str) -> dict | None:
    """What ``code`` names in ``tenant``, or None."""
    from Tracker.models import MaterialLot, Parts, StorageLocation, WorkOrder

    text = (code or "").strip()
    if not text:
        return None

    if text.lower().startswith(("http://", "https://")):
        path = urlparse(text).path
        m = _LOT_PATH.match(path)
        if m:
            lot = MaterialLot.objects.filter(tenant=tenant, id=m.group(1)).first()  # tenant-safe: explicit tenant filter
            return _lot(lot) if lot is not None else None
        m = _LOCATION_PATH.match(path)
        if m:
            return _location(unquote(m.group(1)))
        return {"kind": "URL", "id": "", "label": path, "detail": "", "path": path, "item_id": None}

    if text.upper().startswith(LOCATION_PREFIX):
        return _location(text[len(LOCATION_PREFIX):].strip())

    lot = (MaterialLot.objects.filter(tenant=tenant, archived=False, lot_number__iexact=text)  # tenant-safe: explicit tenant filter
           .select_related("material", "material_type").first())
    if lot is not None:
        return _lot(lot)
    part = (Parts.objects.filter(tenant=tenant, archived=False, ERP_id__iexact=text)  # tenant-safe: explicit tenant filter
            .select_related("part_type").first())
    if part is not None:
        return {"kind": "PART", "id": str(part.id), "label": part.ERP_id,
                "detail": part.part_type.name if part.part_type_id else "",
                "path": f"/workorder/{part.work_order_id}" if part.work_order_id else "",
                "item_id": str(part.part_type_id) if part.part_type_id else None,
                "work_order_id": str(part.work_order_id) if part.work_order_id else None}
    wo = WorkOrder.objects.filter(tenant=tenant, archived=False, ERP_id__iexact=text).first()  # tenant-safe: explicit tenant filter
    if wo is not None:
        return {"kind": "WORK_ORDER", "id": str(wo.id), "label": wo.ERP_id, "detail": "",
                "path": f"/workorder/{wo.id}", "item_id": None}
    loc = StorageLocation.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, archived=False, name__iexact=text).first()
    if loc is not None:
        return _location(loc.name)
    # Typed by hand, part of a number: answer only when exactly one work order fits.
    near = list(WorkOrder.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, archived=False, ERP_id__icontains=text)[:2])
    if len(near) == 1:
        return {"kind": "WORK_ORDER", "id": str(near[0].id), "label": near[0].ERP_id, "detail": "",
                "path": f"/workorder/{near[0].id}", "item_id": None}
    return None
