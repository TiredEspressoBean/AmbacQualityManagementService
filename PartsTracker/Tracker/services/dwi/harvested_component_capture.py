"""
DWI HarvestedComponentCapture service (Reman DWI R4).

Bridges DWI substep response shape to reman-specific writes. When a teardown
operator fills out the HarvestedComponentCapture node and submits the substep,
this service creates one HarvestedComponent row per filled row and dispatches
`scrap_component` for SCRAP-graded rows in the same transaction.

Genuinely necessary as a distinct service (not collapsible into generic substep
completion handling) because:
- HarvestedComponent is a reman-specific aggregate with its own schema.
- SCRAP-grade dispatch is a reman-specific side effect.
- The substep response shape `harvested_components` is reman-specific.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.db import transaction

from Tracker.models import (
    Core,
    HarvestedComponent,
    PartTypes,
    StepExecution,
    Substep,
)
from Tracker.services.reman.harvested_component import scrap_component


@dataclass(frozen=True)
class HarvestedComponentRow:
    """Operator-supplied row from the HarvestedComponentCapture node."""

    component_type_id: str
    condition_grade: str  # 'A' | 'B' | 'C' | 'SCRAP'
    position: str = ""
    condition_notes: str = ""
    is_missing: bool = False
    original_part_number: str = ""

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "HarvestedComponentRow":
        return cls(
            component_type_id=str(row.get("component_type_id") or ""),
            condition_grade=str(row.get("condition_grade") or "").upper(),
            position=str(row.get("position") or ""),
            condition_notes=str(row.get("condition_notes") or ""),
            is_missing=bool(row.get("is_missing", False)),
            original_part_number=str(row.get("original_part_number") or ""),
        )


VALID_GRADES = {"A", "B", "C", "SCRAP"}


def create_harvested_components_from_capture(
    step_execution: StepExecution,
    substep: Substep,
    rows: list[dict[str, Any]],
    user,
) -> dict[str, list[str]]:
    """Persist HarvestedComponent rows from a capture submission.

    Args:
        step_execution: Must be linked to a Core (`step_execution.core_id` set).
        substep: The Substep that contained the capture node.
        rows: Operator-supplied rows (see HarvestedComponentRow.from_dict).
        user: Operator performing the capture.

    Returns:
        {
          "harvested_component_ids": [<uuid>, ...],
          "missing_component_type_ids": [<uuid>, ...]
        }

    Raises:
        ValueError: when step_execution is not Core-scoped, or a row has an
            invalid grade, or component_type_id is missing.
    """
    if step_execution.core_id is None:
        raise ValueError(
            "HarvestedComponentCapture requires a Core-scoped StepExecution"
        )

    core: Core = step_execution.core
    tenant = core.tenant

    parsed_rows = [HarvestedComponentRow.from_dict(r) for r in rows]

    # Validate up-front so a bad row doesn't partial-write before erroring.
    for idx, row in enumerate(parsed_rows):
        if row.is_missing:
            if not row.component_type_id:
                raise ValueError(f"row {idx}: component_type_id required for missing marker")
            continue
        if not row.component_type_id:
            raise ValueError(f"row {idx}: component_type_id required")
        if row.condition_grade not in VALID_GRADES:
            raise ValueError(
                f"row {idx}: condition_grade must be one of {sorted(VALID_GRADES)}"
            )

    created_ids: list[str] = []
    missing_ids: list[str] = []

    with transaction.atomic():
        # Pre-fetch component types in one query (validates existence + tenant scope).
        ct_ids = {r.component_type_id for r in parsed_rows if r.component_type_id}
        component_types = {
            str(ct.id): ct
            for ct in PartTypes.objects.filter(id__in=ct_ids)  # tenant-safe: SecureManager auto-scopes via ContextVar
        }
        for ct_id in ct_ids:
            if ct_id not in component_types:
                raise ValueError(f"component_type {ct_id} not found in this tenant")

        for row in parsed_rows:
            if row.is_missing:
                missing_ids.append(row.component_type_id)
                continue

            hc = HarvestedComponent.objects.create(
                tenant=tenant,
                core=core,
                component_type=component_types[row.component_type_id],
                disassembled_by=user,
                condition_grade=row.condition_grade,
                condition_notes=row.condition_notes,
                position=row.position,
                original_part_number=row.original_part_number,
            )
            created_ids.append(str(hc.id))

            if row.condition_grade == "SCRAP":
                scrap_component(hc, user, reason=row.condition_notes)

    return {
        "harvested_component_ids": created_ids,
        "missing_component_type_ids": missing_ids,
    }
