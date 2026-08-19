"""Demo seeder for the CP-SAT scheduler's inputs.

The base manufacturing seed gives steps + equipment but nothing that ties them
together for scheduling, so the solver had no machine to assign and everything ran
in parallel at t=0. This fills that in for the injector line so a solve produces a
real machine schedule:

  - flags the production machines schedulable (Cleaner, Flow stands, Torque, Test
    bench) — handhelds/overdue gear stay unschedulable;
  - StepEquipmentAffinity mapping each production step to its machine(s) (Flow
    Testing gets two stands, so the solver has a machine *choice* + contention);
  - decomposed StepTiming (setup / cycle / load-unload / attention) so durations and
    multi-machine tending are realistic;
  - measuring devices per step: the specific stations (CMM, Keyence) are wired as
    finite *secondary resources* the solver reserves across steps; go/no-go gauges
    and handhelds are recorded for traceability but stay unschedulable;
  - one Day shift (machine availability windows + a lunch break);
  - a sequence-dependent changeover on the shared flow stand;
  - rosters the internal operators onto the Day shift so Layer-2 dispatch can cover.

Runs after manufacturing + outside_process + work_centers (needs the steps and
equipment). Idempotent.
"""
from datetime import time
from decimal import Decimal

from Tracker.models import (
    Equipments, MeasurementDefinition, PartTypes, Shift, Steps,
    StepEquipmentAffinity, StepTiming, User, WorkCenterChangeover,
)
from Tracker.models.scheduling import AttentionType

from ..base import BaseSeeder

_INJECTOR_PART_TYPE = "Common Rail Injector"

# Machines that are finite, scheduled resources. (Torque Wrench TW-25 is left off —
# it's calibration-overdue, so is_operational already excludes it; TW-26 covers it.)
_SCHEDULABLE = [
    "Ultrasonic Cleaner UC-1", "Flow Test Stand #1", "Flow Test Stand #2",
    "Torque Wrench TW-26", "Final Test Bench FTB-1",
]

# step name -> [(equipment name, affinity)]
_AFFINITIES = {
    "Cleaning":          [("Ultrasonic Cleaner UC-1", "dialed_in")],
    "Nozzle Inspection": [("Flow Test Stand #1", "eligible")],
    "Flow Testing":      [("Flow Test Stand #1", "preferred"),
                          ("Flow Test Stand #2", "eligible")],
    "Assembly":          [("Torque Wrench TW-26", "preferred")],
    "Final Test":        [("Final Test Bench FTB-1", "dialed_in")],
}

# step name -> (setup, cycle, load_unload, attention)
_TIMINGS = {
    "Cleaning":          (15, 30, 2, AttentionType.LOAD_UNLOAD),  # unattended wash
    "Nozzle Inspection": (5, 15, 1, AttentionType.FULL),
    "Flow Testing":      (10, 20, 1, AttentionType.FULL),
    "Assembly":          (20, 45, 3, AttentionType.FULL),
    "Final Test":        (10, 25, 1, AttentionType.FULL),
}

# Measuring devices used at a step (MeasurementDefinition.default_equipment). A
# schedulable device (CMM/Keyence) becomes a finite *secondary resource* the solver
# reserves one-at-a-time across steps; a non-schedulable one (go/no-go, caliper) is
# recorded for traceability/calibration but never scheduled.
# (step name, measurement label, type, equipment name)
_GAUGE_MEASUREMENTS = [
    ("Component Grading", "Body Bore Diameter",  "NUMERIC",   "CMM Zeiss-1"),              # specific station → secondary resource
    ("Nozzle Inspection", "Spray Angle",         "NUMERIC",   "Keyence Vision IM-7020"),   # specific station → secondary resource
    ("Assembly",          "Thread Fit Go/No-Go", "PASS_FAIL", "Go/No-Go Thread Gauge M8x1"),  # plentiful → not scheduled
    ("Cleaning",          "Post-Clean Bore Dia", "NUMERIC",   "Digital Caliper CAL-1"),    # handheld → not scheduled
]


class DemoSchedulingSeeder(BaseSeeder):
    """Wires affinities / timings / shift / rostering so a solve produces a real
    machine schedule for the injector line."""

    def __init__(self, stdout, style, tenant, scale="small"):
        super().__init__(stdout, style, scale=scale)
        self.tenant = tenant

    def _machines(self):
        return {e.name: e for e in Equipments.objects.filter(
            tenant=self.tenant, name__in=_SCHEDULABLE)}

    def _steps(self, name):
        pt = PartTypes.objects.filter(tenant=self.tenant, name=_INJECTOR_PART_TYPE).first()
        qs = Steps.objects.filter(tenant=self.tenant, name=name, is_current_version=True)
        if pt:
            qs = qs.filter(part_type=pt)
        return list(qs)

    def seed(self):
        self.log("Seeding scheduler inputs (affinities, timings, shift, rostering)...")

        machines = self._machines()
        for m in machines.values():
            if not m.is_schedulable:
                m.is_schedulable = True
                m.save(update_fields=["is_schedulable"])

        aff_n = tim_n = 0
        for step_name, specs in _AFFINITIES.items():
            for step in self._steps(step_name):
                for eq_name, affinity in specs:
                    eq = machines.get(eq_name)
                    if eq is None:
                        continue
                    StepEquipmentAffinity.objects.update_or_create(
                        tenant=self.tenant, step=step, equipment=eq,
                        defaults={"affinity": affinity})
                    aff_n += 1
                if step_name in _TIMINGS:
                    setup, cycle, lu, attention = _TIMINGS[step_name]
                    StepTiming.objects.update_or_create(
                        tenant=self.tenant, step=step,
                        defaults={"setup_minutes": setup, "cycle_time_minutes": cycle,
                                  "load_unload_per_piece": lu, "attention_type": attention,
                                  "external_setup_minutes": 0})
                    tim_n += 1

        shift, _ = Shift.objects.get_or_create(
            tenant=self.tenant, code="DAY",
            defaults={"name": "Day Shift", "start_time": time(6, 0), "end_time": time(18, 0),
                      "days_of_week": "0,1,2,3,4", "is_active": True,
                      "break_windows": [{"start": "12:00", "end": "12:30"}]})

        # A sequence-dependent changeover on the shared flow stand (Nozzle ↔ Flow).
        fts1 = machines.get("Flow Test Stand #1")
        nozzle = next(iter(self._steps("Nozzle Inspection")), None)
        flow = next(iter(self._steps("Flow Testing")), None)
        if fts1 and nozzle and flow:
            WorkCenterChangeover.objects.update_or_create(
                tenant=self.tenant, equipment=fts1, from_step=nozzle, to_step=flow,
                defaults={"changeover_minutes": 15})

        # Measuring devices: wire each step's gauge. Schedulable stations (CMM/Keyence)
        # become secondary resources the solver serializes; go/no-go + handhelds are
        # recorded but not scheduled.
        sec_n = 0
        for step_name, label, mtype, eq_name in _GAUGE_MEASUREMENTS:
            eq = Equipments.objects.filter(tenant=self.tenant, name=eq_name).first()
            if eq is None:
                continue
            defaults = {"type": mtype, "default_equipment": eq}
            if mtype == "NUMERIC":
                defaults.update({"unit": "mm", "nominal": Decimal("10.000000"),
                                 "upper_tol": Decimal("0.050000"), "lower_tol": Decimal("0.050000")})
            for step in self._steps(step_name):
                MeasurementDefinition.objects.update_or_create(
                    tenant=self.tenant, step=step, label=label, defaults=defaults)
                if eq.is_schedulable:
                    sec_n += 1

        rostered = User.objects.filter(
            tenant=self.tenant, user_type="INTERNAL", is_active=True,
            default_shift__isnull=True).update(default_shift=shift)

        self.log(f"  {len(machines)} machines schedulable, {aff_n} affinities, "
                 f"{tim_n} timings, {sec_n} secondary-gauge resources, "
                 f"{rostered} operators rostered to {shift.code}.")
        return {"shift": shift, "machines": machines}
