"""Equipment (machine) aggregate services.

An `Equipments` row is a *machine identity* that scheduling configuration hangs
off: its own `operating_shifts` M2M (per-machine calendar), the
`StepEquipmentAffinity` rows (which steps it can run, and how well), the
`WorkCenterChangeover` rows (sequence-dependent setup on it), its
`ContinuousMachine` profile, and the current work centres that list it in
`WorkCenter.equipment`. The scheduler reads all of these by equipment id.

The base `SecureModel.create_new_version` copies concrete columns into a NEW
row and flips the old one non-current — it skips M2Ms and knows nothing about
reverse references. Left alone, every content edit of a machine (rename, serial
number, calibration interval, an import) would drop its shift calendar and leave
its eligibility/setup configuration on the superseded row, so the solver's
machine world would silently drift. This service carries the configuration
forward, the way `services.mes.shifts` does for a Shift.

Deliberately NOT repointed — history stays where it happened:
`CalibrationRecord`, `DowntimeEvent`, `TimeEntry`, `StepExecutionEquipment`,
`QualityReportEquipment`, `FPIRecord`, `StepExecutionMeasurement`, and
`ScheduledTask.machine` (a solve's output, replaced wholesale by the next solve).

Also not repointed: `MeasurementDefinition.default_equipment` / `backup_equipment`.
MeasurementDefinition is itself a versioned spec, so rewriting its FK in place
would mutate a controlled row outside `create_new_version`.
"""
from __future__ import annotations

from django.db import transaction


def create_new_equipment_version(equipment, *, user=None, change_description=None,
                                 **field_updates):
    """Create a new version of an Equipments row and carry its configuration.

    - Copies the `operating_shifts` M2M (an explicit `operating_shifts=` in
      `field_updates` wins — M2M can't go through the base's `objects.create`).
    - Repoints `StepEquipmentAffinity`, `WorkCenterChangeover` and the
      `ContinuousMachine` profile to the new row.
    - Swaps the machine for its new version in the `equipment` list of every
      CURRENT work centre that holds it. Superseded work-centre versions keep
      the list they had — they are a record of that revision.
    """
    from Tracker.models import ContinuousMachine, Equipments

    shifts_override = field_updates.pop('operating_shifts', None)

    with transaction.atomic():
        new = super(Equipments, equipment).create_new_version(
            user=user, change_description=change_description, **field_updates,
        )
        new.operating_shifts.set(
            shifts_override if shifts_override is not None
            else equipment.operating_shifts.all()
        )

        # Configuration follows the machine identity to the new current row.
        # tenant-safe: reverse relations / rows keyed to an in-tenant equipment row.
        equipment.step_affinities.all().update(equipment=new.pk)
        equipment.changeovers.all().update(equipment=new.pk)
        ContinuousMachine.objects.filter(equipment=equipment).update(equipment=new.pk)

        for wc in equipment.work_centers.filter(is_current_version=True):
            wc.equipment.remove(equipment)
            wc.equipment.add(new)
    return new
