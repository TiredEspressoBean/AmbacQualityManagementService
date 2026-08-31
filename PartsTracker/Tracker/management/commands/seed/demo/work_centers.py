"""Demo seeder for WorkCenters — station-level layout.

Runs AFTER manufacturing/receiving/outside_process so it can walk existing
Steps and map them to work-centers. Also populates WorkCenter.equipment and
creates User↔WorkCenter memberships for the demo users, scoped to their role.

Stations, not kind-buckets: a WorkCenter is a physical cell where steps run
(Teardown Bay, Wash Line, Test Cell, ...), with `kind` as the orthogonal
surface discriminator — many PRODUCTION stations, one each of INSPECTION /
RECEIVING / OSP for the demo shop. This is what makes per-station readiness,
dispatch steering, and staging pick lists expressible; the old one-WC-per-kind
layout collapsed every production step into a single "Production Floor".
PROD-01 is kept only as the catch-all for steps no station names (the
"unmapped goes somewhere visible" bucket).

Real customers model their own layout via the UI once we ship the bulk
step→station mapping editors (work-center Phase 0).
"""
from Tracker.models import (
    Equipments, StepEquipmentAffinity, Steps, User, UserWorkCenterMembership,
    WorkCenter, WorkCenterKind,
)

from ..base import BaseSeeder


# The demo shop's stations. step_names map Steps by exact name; equipment_names
# place machines/gauges at the station (augmented by StepEquipmentAffinity —
# any machine eligible for a step is also placed at that step's station).
_STATIONS = (
    # code, name, kind, description, step_names, equipment_names
    ("TEAR-01", "Teardown Bay", WorkCenterKind.PRODUCTION,
     "Core intake and disassembly of incoming reman cores.",
     ("Core Receiving", "Disassembly"),
     ("Disassembly Press DP-1",)),
    ("GRADE-01", "Grading Bench", WorkCenterKind.PRODUCTION,
     "Harvested-component grading and disposition.",
     ("Component Grading",),
     ("Grading Bench GB-1",)),
    ("WASH-01", "Wash Line", WorkCenterKind.PRODUCTION,
     "Ultrasonic cleaning of disassembled components.",
     ("Cleaning",),
     ("Ultrasonic Cleaner UC-1",)),
    ("TEST-01", "Test Cell", WorkCenterKind.PRODUCTION,
     "Flow testing, nozzle inspection, and final functional test.",
     ("Flow Testing", "Nozzle Inspection", "Final Test"),
     ("Flow Test Stand #1", "Flow Test Stand #2", "Final Test Bench FTB-1")),
    ("ASSY-01", "Assembly Cell", WorkCenterKind.PRODUCTION,
     "Injector reassembly with new seals and consumables.",
     ("Assembly",),
     ("Torque Wrench TW-25", "Torque Wrench TW-26")),
    ("RWK-01", "Rework Bay", WorkCenterKind.PRODUCTION,
     "Rework of failed test/inspection parts.",
     ("Rework",),
     ("Rework Station RW-1",)),
    ("PACK-01", "Pack & Ship", WorkCenterKind.PRODUCTION,
     "Final packaging and shipment staging.",
     ("Packaging", "Complete"),
     ("Packaging Station PK-1",)),
    ("INSP-01", "Inspection Bench", WorkCenterKind.INSPECTION,
     "Dedicated QA inspection station (dimensional / visual). Inspection in the "
     "demo routing is substep-level, so no whole steps map here — the measurement "
     "gear does.",
     (),
     ("CMM Zeiss-1", "Keyence Vision IM-7020",
      "Digital Caliper CAL-1", "Digital Caliper CAL-2",
      "Micrometer MIC-1", "Micrometer MIC-2",
      "Go/No-Go Pin Gauge Set", "Go/No-Go Thread Gauge M8x1")),
    ("RECV-01", "Receiving Dock", WorkCenterKind.RECEIVING,
     "Incoming purchased-material inspection.",
     ("Receiving Inspection",),
     ()),
    ("OSP-01", "OSP Dispatch", WorkCenterKind.OSP,
     "Outside-processing shipment dispatch and return.",
     ("Nitride Coating",),
     ()),
    # Catch-all: steps no station names land here (visible, not lost). Empty in
    # a healthy demo — its population is the "unmapped steps" signal.
    ("PROD-01", "Production Floor", WorkCenterKind.PRODUCTION,
     "General production floor — catch-all for steps not mapped to a station.",
     (),
     ()),
)

# Which demo roles get eligibility at which work-center kinds. Broad by
# default — small shop, everyone flexible; QA gets Inspection; receiving
# roles get Receiving. A kind grants membership at EVERY station of that kind.
_ROLE_MEMBERSHIPS = {
    'Tenant Admin':        {'PRODUCTION', 'INSPECTION', 'RECEIVING', 'OSP'},
    'Production Manager':  {'PRODUCTION', 'OSP'},
    'Operator':            {'PRODUCTION'},
    'QA Manager':          {'INSPECTION', 'PRODUCTION'},
    'QA Inspector':        {'INSPECTION'},
    'Document Controller': set(),  # not a floor role
}

# Primary-station kind per role. Operators' primaries are spread round-robin
# across the PRODUCTION stations (multi-station shop: each operator has a home
# cell); single-station kinds just take that station.
_PRIMARY_BY_ROLE = {
    'Tenant Admin':       'PRODUCTION',
    'Production Manager': 'PRODUCTION',
    'Operator':           'PRODUCTION',
    'QA Manager':         'INSPECTION',
    'QA Inspector':       'INSPECTION',
}


class DemoWorkCenterSeeder(BaseSeeder):
    """Creates the station-level demo layout: work-centers, step mapping,
    equipment placement, and user memberships."""

    def seed(self):
        self.log("Creating demo work-center stations + step/equipment mapping + memberships...")

        # 1. Create the stations.
        wcs = {}            # code -> WorkCenter
        by_kind = {}        # kind -> [WorkCenter] (spec order)
        step_targets = {}   # step name -> WorkCenter
        for code, name, kind, desc, step_names, _equip in _STATIONS:
            wc, created = WorkCenter.objects.get_or_create(
                tenant=self.tenant, code=code,
                defaults={'name': name, 'description': desc, 'kind': kind},
            )
            # Idempotent: refresh identity fields on reseed (an existing DB may
            # carry the old one-per-kind names on reused codes).
            dirty = []
            for field, value in (('name', name), ('kind', kind), ('description', desc)):
                if getattr(wc, field) != value:
                    setattr(wc, field, value)
                    dirty.append(field)
            if dirty:
                wc.save(update_fields=dirty)
            wcs[code] = wc
            by_kind.setdefault(kind, []).append(wc)
            for sname in step_names:
                step_targets[sname] = wc
        self.log(f"  Stations: {', '.join(wcs)}")

        # 2. Map steps to stations by name; fall back to the old kind heuristic
        # so steps future seeders add don't silently go unmapped. Remaps ALL
        # current steps (not just null) so reseeding an old-layout DB migrates it.
        catch_all = wcs["PROD-01"]
        mapped = {'BY_NAME': 0, 'FALLBACK': 0, 'SKIPPED': 0}
        for step in Steps.objects.filter(tenant=self.tenant):
            target = step_targets.get(step.name)
            if target is not None:
                mapped['BY_NAME'] += 1
            else:
                if step.step_type == 'RECEIVING':
                    target = wcs["RECV-01"]
                elif getattr(step, 'is_outside_process', False):
                    target = wcs["OSP-01"]
                elif step.step_type in ('TASK', 'START', 'DECISION', 'REWORK', 'TIMER', 'TERMINAL'):
                    target = catch_all
                else:
                    mapped['SKIPPED'] += 1
                    continue
                mapped['FALLBACK'] += 1
            if step.work_center_id != target.id:
                step.work_center = target
                step.save(update_fields=['work_center'])
        self.log(f"  Step mapping: {mapped}")

        # 3. Place equipment at stations: the spec's explicit list (gauges and
        # measurement gear have no step affinity, so they must be named) UNION
        # affinity-derived placement (a machine eligible for a step belongs at
        # that step's station).
        placement = {}  # wc.id -> set of equipment ids
        equip_by_name = {e.name: e for e in Equipments.objects.filter(tenant=self.tenant)}
        for code, _n, _k, _d, _steps, equip_names in _STATIONS:
            ids = {equip_by_name[n].id for n in equip_names if n in equip_by_name}
            if ids:
                placement.setdefault(wcs[code].id, set()).update(ids)
        for aff in StepEquipmentAffinity.objects.filter(tenant=self.tenant).select_related('step'):
            wc_id = aff.step.work_center_id
            if wc_id is not None:
                placement.setdefault(wc_id, set()).add(aff.equipment_id)
        placed = 0
        for wc in wcs.values():
            ids = placement.get(wc.id, set())
            wc.equipment.set(ids)
            placed += len(ids)
        self.log(f"  Equipment placed: {placed} assignments")

        # 4. User memberships: eligibility at every station of the role's kinds;
        # primary station spread round-robin across PRODUCTION for floor roles.
        prod_stations = [wc for wc in by_kind.get(WorkCenterKind.PRODUCTION, [])
                         if wc.code != "PROD-01"]  # nobody's home cell is the catch-all
        member_count = 0
        rr = 0  # round-robin cursor over production stations
        for user in User.objects.filter(tenant=self.tenant).order_by('username'):
            roles = set(user.get_tenant_group_names(tenant=self.tenant) or [])
            wanted_kinds: set[str] = set()
            for role in roles:
                wanted_kinds |= _ROLE_MEMBERSHIPS.get(role, set())
            if not wanted_kinds:
                continue

            primary_kind = None
            for role in roles:
                if role in _PRIMARY_BY_ROLE:
                    primary_kind = _PRIMARY_BY_ROLE[role]
                    break
            primary_wc = None
            if primary_kind == 'PRODUCTION' and prod_stations:
                primary_wc = prod_stations[rr % len(prod_stations)]
                rr += 1
            elif primary_kind:
                kind_list = by_kind.get(WorkCenterKind(primary_kind), [])
                primary_wc = kind_list[0] if kind_list else None

            for kind_str in wanted_kinds:
                for wc in by_kind.get(WorkCenterKind(kind_str), []):
                    want_primary = primary_wc is not None and wc.id == primary_wc.id
                    m, _created = UserWorkCenterMembership.objects.get_or_create(
                        tenant=self.tenant, user=user, work_center=wc,
                        defaults={'is_primary': want_primary},
                    )
                    # Idempotent on reseed: correct primaries left over from the
                    # old one-per-kind layout (primary is singular in the UI).
                    if m.is_primary != want_primary:
                        m.is_primary = want_primary
                        m.save(update_fields=['is_primary'])
                    member_count += 1
        self.log(f"  User memberships: {member_count}")

        return {'work_centers': wcs, 'step_mapping': mapped, 'memberships': member_count}
