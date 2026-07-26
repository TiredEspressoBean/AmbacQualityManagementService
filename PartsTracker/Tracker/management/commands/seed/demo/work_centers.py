"""Demo seeder for WorkCenters.

Runs AFTER manufacturing/receiving/outside_process so it can walk existing
Steps and map them to work-centers by (step_type, is_outside_process). Also
creates User↔WorkCenter memberships for the demo users, scoped to their role.

Deliberately minimal — 4 work-centers cover the demo shop. Real customers
model their own layout via the UI once we ship editors for this.
"""
from Tracker.models import (
    Steps, User, UserWorkCenterMembership, WorkCenter, WorkCenterKind,
)

from ..base import BaseSeeder


# Which demo roles get eligibility at which work-center kinds. Broad by
# default — small shop, everyone flexible; QA gets Inspection; receiving
# roles get Receiving.
_ROLE_MEMBERSHIPS = {
    'Tenant Admin':        {'PRODUCTION', 'INSPECTION', 'RECEIVING', 'OSP'},
    'Production Manager':  {'PRODUCTION', 'OSP'},
    'Operator':            {'PRODUCTION'},
    'QA Manager':          {'INSPECTION', 'PRODUCTION'},
    'QA Inspector':        {'INSPECTION'},
    'Document Controller': set(),  # not a floor role
}

_PRIMARY_BY_ROLE = {
    'Tenant Admin':       'PRODUCTION',
    'Production Manager': 'PRODUCTION',
    'Operator':           'PRODUCTION',
    'QA Manager':         'INSPECTION',
    'QA Inspector':       'INSPECTION',
}


class DemoWorkCenterSeeder(BaseSeeder):
    """Creates the 4-WC demo layout and back-fills Step.work_center + user memberships."""

    def seed(self):
        self.log("Creating demo work-centers + mapping steps + user memberships...")

        # 1. Create the four work-centers.
        wcs = {}
        for kind, code, name, desc in (
            (WorkCenterKind.PRODUCTION, "PROD-01", "Production Floor",
             "Default production work-center — assembly, machining, cleaning, testing."),
            (WorkCenterKind.INSPECTION, "INSP-01", "Inspection Bench",
             "Dedicated QA inspection station."),
            (WorkCenterKind.RECEIVING, "RECV-01", "Receiving Dock",
             "Incoming material inspection."),
            (WorkCenterKind.OSP, "OSP-01", "OSP Dispatch",
             "Outside-processing shipment dispatch and return."),
        ):
            wc, created = WorkCenter.objects.get_or_create(
                tenant=self.tenant, code=code,
                defaults={'name': name, 'description': desc, 'kind': kind},
            )
            # Idempotent: if it already exists but kind is stale, fix it.
            if not created and wc.kind != kind:
                wc.kind = kind
                wc.save(update_fields=['kind'])
            wcs[kind] = wc
        self.log(f"  Work-centers: {', '.join(wc.code for wc in wcs.values())}")

        # 2. Back-fill Step.work_center by (step_type, is_outside_process).
        # Existing seeds don't have inspection-dedicated steps — inspection is
        # substep-level; the Inspection Bench WC is created but unmapped.
        mapped = {'PRODUCTION': 0, 'RECEIVING': 0, 'OSP': 0, 'SKIPPED': 0}
        for step in Steps.objects.filter(tenant=self.tenant, work_center__isnull=True):
            if step.step_type == 'RECEIVING':
                step.work_center = wcs[WorkCenterKind.RECEIVING]
                mapped['RECEIVING'] += 1
            elif getattr(step, 'is_outside_process', False):
                step.work_center = wcs[WorkCenterKind.OSP]
                mapped['OSP'] += 1
            elif step.step_type in ('TASK', 'START', 'DECISION', 'REWORK', 'TIMER', 'TERMINAL'):
                step.work_center = wcs[WorkCenterKind.PRODUCTION]
                mapped['PRODUCTION'] += 1
            else:
                mapped['SKIPPED'] += 1
                continue
            step.save(update_fields=['work_center'])
        self.log(f"  Step mapping: {mapped}")

        # 3. User memberships (role-scoped; admin gets everything).
        member_count = 0
        for user in User.objects.filter(tenant=self.tenant):
            roles = set(user.get_tenant_group_names(tenant=self.tenant) or [])
            wanted_kinds: set[str] = set()
            for role in roles:
                wanted_kinds |= _ROLE_MEMBERSHIPS.get(role, set())
            if not wanted_kinds:
                continue

            # Primary: pick from the role that spelled the strongest primary.
            primary_kind = None
            for role in roles:
                if role in _PRIMARY_BY_ROLE:
                    primary_kind = _PRIMARY_BY_ROLE[role]
                    break

            for kind_str in wanted_kinds:
                wc = wcs[WorkCenterKind(kind_str)]
                UserWorkCenterMembership.objects.get_or_create(
                    tenant=self.tenant, user=user, work_center=wc,
                    defaults={'is_primary': kind_str == primary_kind},
                )
                member_count += 1
        self.log(f"  User memberships: {member_count}")

        return {'work_centers': wcs, 'step_mapping': mapped, 'memberships': member_count}
