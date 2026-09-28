"""DWI ComponentInstallCapture — record what went into each slot of a rebuild.

The rebuild half of reman capture; `harvested_component_capture` is the teardown half.
A core is a part (Documents/CORE_AS_PART_DESIGN.md), so the substep runs on the core's
part and the core is reached through its role. Each captured row names one slot and the
component the operator actually fitted:

- `harvested_id` — the unit's OWN component, back into the unit it came out of;
- `part_id` — a recovered part from stock (exchange rebuilds only — the reservation
  rules in `install_component` refuse a repair-and-return unit anyone else's part).

Purchased replacements are not recorded here: a bought component is drawn from its lot
by material consumption when the step completes, which is already its traceability.

Every row goes through `install_component`, which holds the rules — so this module adds
no second copy of them. The whole capture is one transaction: a slot that cannot be
installed fails the capture rather than leaving the unit half-recorded.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction


@dataclass(frozen=True)
class InstallRow:
    bom_line_id: str | None
    position: str
    harvested_id: str | None
    part_id: str | None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "InstallRow":
        return cls(
            bom_line_id=(d.get('bom_line_id') or None),
            position=str(d.get('position') or ''),
            harvested_id=(d.get('harvested_id') or None),
            part_id=(d.get('part_id') or None),
        )


@transaction.atomic
def install_components_from_capture(step_execution, substep, rows: list[dict], user) -> dict:
    """Install each captured component into the unit. Returns the created usage ids."""
    from Tracker.models import BOMLine, HarvestedComponent, Parts
    from Tracker.services.reman.core_steps import core_of
    from Tracker.services.reman.rebuild_execution import install_component

    core = core_of(step_execution.part) if step_execution.part_id else None
    if core is None:
        raise ValueError(
            "ComponentInstallCapture requires a step execution on a core — a part "
            "playing a core role"
        )

    parsed = [InstallRow.from_dict(r) for r in rows]
    for idx, row in enumerate(parsed):
        if bool(row.harvested_id) == bool(row.part_id):
            raise ValueError(
                f"row {idx}: name exactly one of the unit's own component (harvested_id) "
                "or a recovered part (part_id)"
            )

    usage_ids = []
    for idx, row in enumerate(parsed):
        # Looked up through the tenant-scoped managers, so a row naming another
        # tenant's component is simply not found.
        harvested = part = bom_line = None
        if row.harvested_id:
            harvested = HarvestedComponent.objects.filter(pk=row.harvested_id).first()  # tenant-safe: .objects auto-scopes to the request tenant
            if harvested is None:
                raise ValueError(f"row {idx}: harvested component not found")
        else:
            part = Parts.objects.filter(pk=row.part_id).first()  # tenant-safe: .objects auto-scopes to the request tenant
            if part is None:
                raise ValueError(f"row {idx}: part not found")
        if row.bom_line_id:
            bom_line = BOMLine.objects.filter(pk=row.bom_line_id).first()  # tenant-safe: .objects auto-scopes to the request tenant
        try:
            usage = install_component(
                core, harvested=harvested, part=part, user=user,
                bom_line=bom_line, step=step_execution.step,
            )
        except ValidationError as exc:
            raise ValueError(f"row {idx}: {' '.join(exc.messages)}") from exc
        usage_ids.append(str(usage.id))
    return {"assembly_usage_ids": usage_ids}
