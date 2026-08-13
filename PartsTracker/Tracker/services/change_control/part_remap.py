"""Part step-remapping for process-change migration.

When a WorkOrder migrates to a new process version, each in-flight part must be
re-pointed from its current (old-version) step to the corresponding step in the
new version. Steps carry a stable ``identity_id`` copied across versions, so the
correspondence is simply the new-version step that shares the part's step's
``identity_id``:

- **Match found** (same row = unchanged, or a newer row = modified) → port the
  part over (a no-op when the row is unchanged).
- **No match** → the step was removed in the new version; the part is *stranded*
  and the caller must supply a resolution (RELOCATE / HOLD / SCRAP) or the whole
  migration is rejected (``StrandedPartsNeedResolution``).
"""
from __future__ import annotations

from typing import Any

from Tracker.models import Parts, PartsStatus

# Parts in these statuses are settled and not remapped.
_SETTLED = (PartsStatus.COMPLETED, PartsStatus.SCRAPPED, PartsStatus.CANCELLED)

# Resolution actions for a part stranded at a removed step.
RELOCATE = "RELOCATE"  # move the part to a chosen surviving step in the new version
HOLD = "HOLD"          # quarantine the part for manual routing; clear its step
SCRAP = "SCRAP"        # scrap the part (terminal); clear its step


class StrandedPartsNeedResolution(ValueError):
    """A migration would strand parts at removed steps with no resolution.

    ``.stranded`` is a list of ``{part_id, wo_id, step_id, step_name}`` — the
    parts the user must resolve before the migration can complete.
    """

    def __init__(self, stranded: list[dict[str, Any]]):
        self.stranded = stranded
        super().__init__(
            f"{len(stranded)} part(s) sit at a step removed in the new process "
            f"version and need a resolution (RELOCATE / HOLD / SCRAP)."
        )


def _new_steps_by_identity(new_process) -> dict:
    return {ps.step.identity_id: ps.step for ps in new_process.process_steps.all()}


def _in_flight_parts(wo):
    return (
        Parts.objects.filter(work_order=wo)
        .exclude(part_status__in=_SETTLED)
        .select_related("step")
    )


def _stranded_info(part, wo) -> dict[str, Any]:
    return {
        "part_id": str(part.id),
        "wo_id": str(wo.id),
        "step_id": str(part.step_id),
        "step_name": part.step.name,
    }


def classify_parts_for_migration(wo, new_process) -> dict:
    """Split a WO's in-flight parts into portable vs stranded for a migration to
    ``new_process``. Read-only — drives the migration-picker UI so it can prompt
    for resolutions on the stranded parts."""
    by_identity = _new_steps_by_identity(new_process)
    portable, stranded = 0, []
    for part in _in_flight_parts(wo):
        if part.step_id is None:
            continue  # not started at a step yet — nothing to remap
        if part.step.identity_id in by_identity:
            portable += 1
        else:
            stranded.append(_stranded_info(part, wo))
    return {"portable_count": portable, "stranded": stranded}


def remap_workorder_parts(wo, new_process, resolutions: dict | None) -> list[dict]:
    """Re-point a migrating WO's in-flight parts to ``new_process``.

    Ports every part whose step survives (matched by ``identity_id``; unchanged
    steps are a no-op), and applies the supplied resolution to each part stranded
    at a removed step. Returns the list of stranded parts that had **no**
    resolution — the caller aborts the migration if it is non-empty.

    ``resolutions`` maps ``str(part_id)`` → ``{"action": RELOCATE|HOLD|SCRAP,
    "target_step_id": <id>}`` (``target_step_id`` required for RELOCATE).
    """
    by_identity = _new_steps_by_identity(new_process)
    resolutions = resolutions or {}
    unresolved: list[dict] = []

    for part in _in_flight_parts(wo):
        if part.step_id is None:
            continue
        target = by_identity.get(part.step.identity_id)
        if target is not None:
            if part.step_id != target.id:  # modified step → real move
                part.step = target
                part.save(update_fields=["step", "updated_at"])
            continue
        # Stranded at a step removed in the new version.
        res = resolutions.get(str(part.id))
        if not res:
            unresolved.append(_stranded_info(part, wo))
            continue
        _apply_resolution(part, res, by_identity)

    return unresolved


def _apply_resolution(part, res: dict, by_identity: dict) -> None:
    action = (res.get("action") or "").upper()
    if action == RELOCATE:
        target_id = str(res.get("target_step_id") or "")
        target = next(
            (s for s in by_identity.values() if str(s.id) == target_id), None
        )
        if target is None:
            raise ValueError(
                f"RELOCATE target_step_id {target_id!r} is not a step in the new "
                f"process version."
            )
        part.step = target
        part.save(update_fields=["step", "updated_at"])
    elif action == HOLD:
        part.step = None
        part.part_status = PartsStatus.QUARANTINED
        part.save(update_fields=["step", "part_status", "updated_at"])
    elif action == SCRAP:
        part.step = None
        part.part_status = PartsStatus.SCRAPPED
        part.save(update_fields=["step", "part_status", "updated_at"])
    else:
        raise ValueError(
            f"Unknown stranded-part resolution action: {res.get('action')!r} "
            f"(expected {RELOCATE} / {HOLD} / {SCRAP})."
        )
