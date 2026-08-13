"""Part step-remapping when a WorkOrder migrates to a new process version.

Steps carry a stable `identity_id`. On migration, parts whose step survives
(unchanged → no-op, or modified → ported to the new row) auto-port by identity;
parts stranded at a *removed* step need a RELOCATE / HOLD / SCRAP resolution or
the migration is rejected (`StrandedPartsNeedResolution`).
"""
import uuid

from django.test import TestCase

from Tracker.models import (
    PartTypes,
    Parts,
    PartsStatus,
    Processes,
    ProcessStep,
    Steps,
    Tenant,
    WorkOrder,
    WorkOrderStatus,
)
from Tracker.services.change_control.part_remap import (
    HOLD,
    RELOCATE,
    SCRAP,
    StrandedPartsNeedResolution,
    remap_workorder_parts,
)
from Tracker.services.change_control.process_change import (
    ProcessChangeMigrationDisposition,
    _apply_workorder_migrations,
)
from Tracker.tests.base import TenantContextMixin


class ProcessMigrationRemapTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Mig", slug="mig-remap", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Widget")

        self.old_proc = Processes.objects.create(tenant=self.tenant, name="Proc-old", part_type=self.pt)
        self.new_proc = Processes.objects.create(tenant=self.tenant, name="Proc-new", part_type=self.pt)

        self.id_u = uuid.uuid4()  # unchanged
        self.id_m = uuid.uuid4()  # modified
        self.id_r = uuid.uuid4()  # removed

        def mkstep(name, ident):
            return Steps.objects.create(
                tenant=self.tenant, part_type=self.pt, name=name,
                step_type="TASK", identity_id=ident,
            )

        # Unchanged step: the SAME row in both versions.
        self.step_u = mkstep("Unchanged", self.id_u)
        # Modified step: distinct rows sharing an identity_id.
        self.step_m_old = mkstep("Modified", self.id_m)
        self.step_m_new = mkstep("Modified (v2)", self.id_m)
        # Removed step: old version only.
        self.step_r = mkstep("Removed", self.id_r)

        ProcessStep.objects.create(process=self.old_proc, step=self.step_u, order=1)
        ProcessStep.objects.create(process=self.old_proc, step=self.step_m_old, order=2)
        ProcessStep.objects.create(process=self.old_proc, step=self.step_r, order=3)
        ProcessStep.objects.create(process=self.new_proc, step=self.step_u, order=1)
        ProcessStep.objects.create(process=self.new_proc, step=self.step_m_new, order=2)

        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-MIG-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=3, process=self.old_proc,
        )

        def mkpart(erp, step):
            return Parts.objects.create(
                tenant=self.tenant, ERP_id=erp, part_type=self.pt,
                work_order=self.wo, step=step, part_status=PartsStatus.IN_PROGRESS,
            )

        self.part_u = mkpart("P-U", self.step_u)
        self.part_m = mkpart("P-M", self.step_m_old)
        self.part_r = mkpart("P-R", self.step_r)

    def test_ports_modified_leaves_unchanged_flags_removed(self):
        unresolved = remap_workorder_parts(self.wo, self.new_proc, None)

        self.part_u.refresh_from_db()
        self.part_m.refresh_from_db()
        self.assertEqual(self.part_u.step_id, self.step_u.id, "unchanged step is a no-op")
        self.assertEqual(self.part_m.step_id, self.step_m_new.id, "modified step ports to v2")
        self.assertEqual(len(unresolved), 1)
        self.assertEqual(unresolved[0]["part_id"], str(self.part_r.id))

    def test_relocate_resolution_moves_part(self):
        resolutions = {
            str(self.part_r.id): {"action": RELOCATE, "target_step_id": str(self.step_u.id)},
        }
        unresolved = remap_workorder_parts(self.wo, self.new_proc, resolutions)

        self.assertEqual(unresolved, [])
        self.part_r.refresh_from_db()
        self.assertEqual(self.part_r.step_id, self.step_u.id)

    def test_relocate_to_step_outside_new_version_rejected(self):
        # step_r is not in the new version — not a valid relocate target.
        resolutions = {
            str(self.part_r.id): {"action": RELOCATE, "target_step_id": str(self.step_r.id)},
        }
        with self.assertRaises(ValueError):
            remap_workorder_parts(self.wo, self.new_proc, resolutions)

    def test_hold_resolution_quarantines(self):
        remap_workorder_parts(self.wo, self.new_proc, {str(self.part_r.id): {"action": HOLD}})

        self.part_r.refresh_from_db()
        self.assertIsNone(self.part_r.step_id)
        self.assertEqual(self.part_r.part_status, PartsStatus.QUARANTINED)

    def test_scrap_resolution(self):
        remap_workorder_parts(self.wo, self.new_proc, {str(self.part_r.id): {"action": SCRAP}})

        self.part_r.refresh_from_db()
        self.assertIsNone(self.part_r.step_id)
        self.assertEqual(self.part_r.part_status, PartsStatus.SCRAPPED)

    def test_migration_rejected_when_stranded_unresolved(self):
        with self.assertRaises(StrandedPartsNeedResolution) as ctx:
            _apply_workorder_migrations(
                old_version=self.old_proc,
                new_version=self.new_proc,
                disposition=ProcessChangeMigrationDisposition.MIGRATE_ALL,
                selected_workorder_ids=[],
                resolutions=None,
            )
        self.assertEqual(len(ctx.exception.stranded), 1)
        self.assertEqual(ctx.exception.stranded[0]["part_id"], str(self.part_r.id))
