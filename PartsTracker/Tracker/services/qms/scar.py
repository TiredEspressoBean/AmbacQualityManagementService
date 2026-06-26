"""Supplier Corrective Action Request (SCAR).

A SCAR rides the existing CAPA engine: a CAPA with ``capa_type='SUPPLIER'`` tagged
with the ``supplier`` it's raised against (and optionally linked to the triggering
receiving QualityReport). This keeps the full CAPA lifecycle (root cause, tasks,
verification, closure) without a parallel model.
"""
from __future__ import annotations

from django.db import transaction


def open_scar(*, supplier, problem_statement, severity="MAJOR",
              quality_report=None, material_lot=None, user=None):
    """Open a SCAR (a supplier-tagged CAPA). Returns the CAPA.

    Args:
        supplier: Companies the SCAR is against.
        problem_statement: required CAPA problem text.
        severity: CapaSeverity (CRITICAL/MAJOR/MINOR).
        quality_report: optional triggering receiving QualityReport to link.
        material_lot: optional lot for a default problem statement.
        user: initiator.
    """
    from Tracker.models import CAPA

    if supplier is None:
        raise ValueError("A SCAR requires a supplier.")

    with transaction.atomic():
        capa = CAPA.objects.create(
            tenant=supplier.tenant,
            capa_type="SUPPLIER",
            supplier=supplier,
            severity=severity,
            status="OPEN",
            problem_statement=problem_statement,
            initiated_by=user if (user and getattr(user, "is_authenticated", False)) else None,
        )
        if quality_report is not None:
            capa.quality_reports.add(quality_report)
    return capa


def open_scar_for_lot(lot, user=None, severity="MAJOR"):
    """Convenience: raise a SCAR for a rejected/received lot's supplier, linking the
    lot's most recent receiving QualityReport."""
    if lot.supplier_id is None:
        raise ValueError("Lot has no supplier; cannot raise a SCAR.")
    report = lot.quality_reports.order_by("-created_at").first()
    problem = (
        f"Receiving inspection issue on lot {lot.lot_number} "
        f"({lot.material_type.name if lot.material_type else lot.material_description})."
    )
    return open_scar(supplier=lot.supplier, problem_statement=problem,
                     severity=severity, quality_report=report, material_lot=lot, user=user)
