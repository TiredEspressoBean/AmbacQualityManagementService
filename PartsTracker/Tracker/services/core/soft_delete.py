"""Re-adding a row that was deleted.

DELETE on a SecureModel archives the row rather than removing it. Where the model has a
unique key — a step's timing, a (step, machine) eligibility, a changeover cell — the
archived row still holds that key, so adding the same thing again was refused as a
duplicate. Re-adding it revives the archived row instead: same row, same history, the
new values applied.
"""
from __future__ import annotations

from typing import Optional


def find_archived(model, tenant, key: dict):
    """The archived row of `model` in `tenant` holding `key`, or None.

    `key` maps field names (or `<fk>_id`) to values — the model's unique key.
    """
    return model.unscoped.filter(tenant=tenant, archived=True, **key).first()  # tenant-safe: explicit tenant filter


def revive(instance, changes: Optional[dict] = None):
    """Un-archive `instance`, applying `changes`, and save it."""
    for field, value in (changes or {}).items():
        setattr(instance, field, value)
    instance.archived = False
    instance.deleted_at = None
    instance.save()
    return instance
