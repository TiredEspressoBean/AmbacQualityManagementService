"""FPI scopes are real gates, and a waiver is corrected by a new first piece
(user decisions 2026-10-28, B1 and B2).

- Per Work Order: one buy-off releases the step for the work order (unchanged).
- Per Shift: a pass on another shift day doesn't release today's run.
- Per Equipment: a pass on another machine doesn't release this one; a part with no
  machine recorded is held, and Start FPI says why.
- Per Operator is gone; steps that had it become Per Work Order.
- After a waiver a buy-off authority starts a new first piece: the waiver is marked
  SUPERSEDED and the run holds until the new one passes. After a pass nothing starts.
- FPI records can't be deleted or patched through the API.
"""
import importlib
from datetime import timedelta

from Tracker.models import (
    Equipments, FPIRecord, FPIStatus, PartTypes, Parts, RecordEdit, StepExecution, Steps,
    WorkOrder,
)
from Tracker.models.qms import EquipmentRole, StepExecutionEquipment
from Tracker.services.core.clock import tenant_today
from Tracker.services.qms.fpi import start_fpi
from Tracker.tests.base import TenantTestCase


class FpiScopeTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        t = self.tenant_a
        self.pt = PartTypes.objects.create(tenant=t, name="Body", ID_prefix="B")
        self.step = Steps.objects.create(tenant=t, part_type=self.pt, name="Turn", step_type="TASK",
                                         requires_first_piece_inspection=True)
        self.wo = WorkOrder.objects.create(tenant=t, ERP_id="WO-SCOPE", quantity=2)
        self.part = Parts.objects.create(tenant=t, ERP_id="B-1", part_type=self.pt,
                                         work_order=self.wo, step=self.step)
        self.se = StepExecution.objects.create(tenant=t, part=self.part, step=self.step,
                                               visit_number=1, status="IN_PROGRESS")
        self.cnc1 = Equipments.objects.create(tenant=t, name="CNC-1")
        self.cnc2 = Equipments.objects.create(tenant=t, name="CNC-2")
        self.grant_tenant_permissions(self.user_a, t, ['sign_off_fpi', 'view_fpirecord',
                                                        'add_fpirecord', 'full_tenant_access'])

    def _scope(self, scope):
        Steps.objects.filter(pk=self.step.pk).update(fpi_scope=scope)
        self.step.refresh_from_db()

    def _record(self, status, **ctx):
        return FPIRecord.objects.create(tenant=self.tenant_a, work_order=self.wo, step=self.step,
                                        part_type=self.pt, designated_part=self.part,
                                        status=status, **ctx)

    def _gate(self):
        return self.step.get_fpi_status(self.wo, part=self.part)['status']

    def _runs_on(self, machine):
        StepExecutionEquipment.objects.create(step_execution=self.se, equipment=machine,
                                              role=EquipmentRole.PRODUCTION)

    # ── Per Work Order ──────────────────────────────────────────────────────────
    def test_per_work_order_one_pass_releases(self):
        self._record(FPIStatus.PASSED)
        self.assertEqual(self._gate(), FPIStatus.PASSED)

    # ── Per Shift ───────────────────────────────────────────────────────────────
    def test_per_shift_holds_a_new_shift_until_it_passes(self):
        self._scope('PER_SHIFT')
        today = tenant_today(self.tenant_a)
        self._record(FPIStatus.PASSED, shift_date=today - timedelta(days=1))
        self.assertEqual(self._gate(), FPIStatus.PENDING)
        _, blockers = self.step.can_advance_from_step(self.se, self.wo)
        self.assertTrue(any(b.startswith(f"First Piece Inspection required for the {today:%d %b} shift")
                            for b in blockers), blockers)
        self._record(FPIStatus.PASSED, shift_date=today)
        self.assertEqual(self._gate(), FPIStatus.PASSED)

    # ── Per Equipment ───────────────────────────────────────────────────────────
    def test_per_equipment_holds_another_machine_until_it_passes(self):
        self._scope('PER_EQUIPMENT')
        self._runs_on(self.cnc1)
        self._record(FPIStatus.PASSED, equipment=self.cnc2)
        self.assertEqual(self._gate(), FPIStatus.PENDING)
        self._record(FPIStatus.PASSED, equipment=self.cnc1)
        self.assertEqual(self._gate(), FPIStatus.PASSED)

    def test_per_equipment_start_takes_the_parts_machine(self):
        self._scope('PER_EQUIPMENT')
        self._runs_on(self.cnc1)
        fpi, created = start_fpi(self.wo, self.step, self.user_a, part=self.part)
        self.assertTrue(created)
        self.assertEqual(fpi.equipment_id, self.cnc1.id)
        self.assertEqual(fpi.designated_part_id, self.part.id)

    def test_per_equipment_with_no_machine_holds_and_says_why(self):
        self._scope('PER_EQUIPMENT')
        self._record(FPIStatus.PASSED, equipment=self.cnc1)
        self.assertEqual(self._gate(), FPIStatus.PENDING)
        with self.assertRaisesMessage(ValueError, "isn't recorded"):
            start_fpi(self.wo, self.step, self.user_a, part=self.part)

    def test_start_fpi_endpoint_accepts_the_part(self):
        """A8: Start FPI on a Per Equipment step used to 400 ("equipment required")."""
        self._scope('PER_EQUIPMENT')
        self._runs_on(self.cnc1)
        self.authenticate_as(self.user_a, self.tenant_a)
        r = self.client.post("/api/FPIRecords/get-or-create/", {
            "work_order": str(self.wo.id), "step": str(self.step.id), "part": str(self.part.id),
        }, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["fpi"]["equipment"], str(self.cnc1.id))
        r = self.client.get(f"/api/FPIRecords/check-status/?work_order={self.wo.id}"
                            f"&step={self.step.id}&part={self.part.id}")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual((r.json()["context_label"], r.json()["has_pending"]), ("CNC-1", True))

    # ── Per Operator removed ────────────────────────────────────────────────────
    def test_migration_maps_per_operator_to_per_work_order(self):
        Steps.objects.filter(pk=self.step.pk).update(fpi_scope='PER_OPERATOR')
        mig = importlib.import_module('Tracker.migrations.0268_fpi_scope_per_operator_removed')
        from django.apps import apps
        mig.per_operator_to_per_workorder(apps, None)
        self.step.refresh_from_db()
        self.assertEqual(self.step.fpi_scope, 'PER_WORKORDER')

    # ── B2: correcting a waiver ─────────────────────────────────────────────────
    def test_a_waiver_is_corrected_by_a_new_first_piece(self):
        waiver = self._record(FPIStatus.WAIVED)
        self.assertEqual(self._gate(), FPIStatus.WAIVED)
        fresh, created = start_fpi(self.wo, self.step, self.user_a, part=self.part)
        self.assertTrue(created)
        waiver.refresh_from_db()
        self.assertEqual(waiver.status, FPIStatus.SUPERSEDED)
        self.assertTrue(RecordEdit.objects.filter(object_id=waiver.id, field_name='status',
                                                  new_value=FPIStatus.SUPERSEDED).exists())
        self.assertEqual(self._gate(), FPIStatus.PENDING)          # the run holds again
        FPIRecord.objects.filter(pk=fresh.pk).update(status=FPIStatus.PASSED)
        self.assertEqual(self._gate(), FPIStatus.PASSED)           # and releases on the pass

    def test_only_a_buy_off_authority_replaces_a_waiver(self):
        self._record(FPIStatus.WAIVED)
        with self.assertRaisesMessage(ValueError, "Only someone who can sign off"):
            start_fpi(self.wo, self.step, self.user_b, part=self.part)

    def test_nothing_starts_after_a_pass(self):
        self._record(FPIStatus.PASSED)
        with self.assertRaisesMessage(ValueError, "has passed"):
            start_fpi(self.wo, self.step, self.user_a, part=self.part)

    def test_records_cannot_be_deleted_or_patched(self):
        waiver = self._record(FPIStatus.WAIVED)
        # A superuser passes every permission gate, so a refusal here is the missing
        # route itself, not a permission.
        self.authenticate_superuser(self.tenant_a)
        self.assertEqual(self.client.delete(f"/api/FPIRecords/{waiver.id}/").status_code, 405)
        self.assertEqual(self.client.patch(f"/api/FPIRecords/{waiver.id}/", {"archived": True},
                                           format="json").status_code, 405)
        waiver.refresh_from_db()
        self.assertFalse(waiver.archived)
