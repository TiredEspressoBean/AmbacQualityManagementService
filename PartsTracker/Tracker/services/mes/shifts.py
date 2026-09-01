"""Shift aggregate services.

A Shift is a *working-window identity* live rows hang off: `User.default_shift`
(rostering), `OvertimeWindow.shift` (extra runs), and `Equipments.operating_shifts`
(attended-machine windows). The base `SecureModel.create_new_version` copies
scalars into a NEW row and flips the old one non-current — it does not know
about those references, so an unwrapped edit (rename, hours, break windows)
would strand the roster/overtime/machines on the superseded row and silently
change the solver's world. This service carries the live world forward.
"""
from __future__ import annotations

from django.db import transaction


def create_new_shift_version(shift, *, user=None, change_description=None, **field_updates):
    """Create a new version of a Shift and migrate its live references:
    rostered users (default_shift), overtime windows, and the machines whose
    operating_shifts include it.

    Deliberately NOT repointed: `ScheduleSlot.shift` (PROTECT). Slots are
    dated historical assignments — "who was slotted under which shift
    definition" — so they stay on the version that was current when they
    were written, like any other point-in-time record.
    """
    from Tracker.models import Shift, User

    with transaction.atomic():
        new = super(Shift, shift).create_new_version(
            user=user, change_description=change_description, **field_updates,
        )
        # Live references follow the shift identity to the new current row.
        # tenant-safe: reverse relations / rows already scoped to the shift's tenant.
        User.objects.filter(default_shift=shift).update(default_shift=new)
        shift.overtime_windows.all().update(shift=new)
        for eq in shift.equipment.all():  # Equipments.operating_shifts M2M (related_name)
            eq.operating_shifts.remove(shift)
            eq.operating_shifts.add(new)
    return new
