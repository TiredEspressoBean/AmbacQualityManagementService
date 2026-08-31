"""WorkCenter aggregate services.

A WorkCenter is a *station identity* that live operational rows hang off:
`Steps.work_center` (routing), `UserWorkCenterMembership` (eligibility),
`ScheduleSlot` / `DowntimeEvent` / `TimeEntry` (operational records), and the
`equipment` M2M (what's physically at the station).

The base `SecureModel.create_new_version` copies scalar fields into a NEW row
and flips the old one non-current — it does not know about those references.
Left alone, a rename would strand every step/membership on the superseded row
and silently break work-queue routing (the queue filters by the step's
work-center, which would no longer be the current version). This service wraps
versioning to carry the live world forward onto the new row.
"""
from __future__ import annotations

from django.db import transaction


def create_new_work_center_version(work_center, *, user=None, change_description=None,
                                   **field_updates):
    """Create a new version of a WorkCenter and migrate its live references.

    - Copies the `equipment` M2M (the base's scalar copy skips M2Ms; an explicit
      `equipment=` override in `field_updates` wins).
    - Repoints live FKs — steps, memberships, schedule slots, downtime events,
      time entries — to the new current row, so routing/eligibility follow the
      station identity rather than freezing on the superseded version.
    """
    from Tracker.models import WorkCenter

    # M2M can't be forwarded to the base create_new_version (Django raises on
    # direct M2M assignment) — pop and apply via .set() after the row exists.
    equipment_override = field_updates.pop('equipment', None)

    with transaction.atomic():
        new = super(WorkCenter, work_center).create_new_version(
            user=user, change_description=change_description, **field_updates,
        )
        new.equipment.set(
            equipment_override if equipment_override is not None
            else work_center.equipment.all()
        )
        # Live references follow the station identity to the new current row.
        # tenant-safe: reverse relations of an in-tenant WorkCenter row.
        for rel in ('steps', 'member_memberships', 'schedule_slots',
                    'downtime_events', 'time_entries'):
            getattr(work_center, rel).all().update(work_center=new.pk)
    return new
