"""Rework routing + close lifecycle (Y):
- 2b: the REWORK/REPAIR *decision* routes the part to the in-process rework step
  (split + moved there), leaving the disposition IN_PROGRESS.
- 2d: a rework target must carry an inspection substep, else routing is refused.
- 2e: when the reworked part leaves the rework step (re-inspected), the open
  disposition is closed.
"""
from django.contrib.auth import get_user_model

from Tracker.models import (
    PartTypes,
    Parts,
    Processes,
    ProcessStep,
    QuarantineDisposition,
    Steps,
    Substep,
    Tenant,
    WorkOrder,
    WorkOrderStatus,
)
from Tracker.tests.base import TenantContextMixin, VectorTestCase


class DispositionReworkRoutingTests(TenantContextMixin, VectorTestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(
            name="Rework Route", slug="rework-route", tier="PRO"
        )
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        self.user = User.objects.create_user(
            username="qa-route", email="qa@route.test", password="x", tenant=self.tenant,
        )
        self.part_type = PartTypes.objects.create(tenant=self.tenant, name="Widget")
        self.process = Processes.objects.create(
            tenant=self.tenant, name="P", part_type=self.part_type,
        )
        self.task_step = Steps.objects.create(
            tenant=self.tenant, part_type=self.part_type, name="Inspect", step_type="TASK",
        )
        self.rework_step = Steps.objects.create(
            tenant=self.tenant, part_type=self.part_type, name="Rework", step_type="REWORK",
        )
        # Re-inspection lives on the rework step as an inspection-point substep (2d).
        Substep.objects.create(
            tenant=self.tenant, step=self.rework_step, order=0,
            title="Re-inspect rework", is_inspection_point=True,
        )
        ProcessStep.objects.create(process=self.process, step=self.task_step, order=1)
        ProcessStep.objects.create(process=self.process, step=self.rework_step, order=2)
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-RR-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=1, process=self.process,
        )
        self.part = Parts.objects.create(
            tenant=self.tenant, ERP_id="P-RR-1", part_type=self.part_type,
            work_order=self.wo, step=self.task_step,
        )

    def _rework_disposition(self):
        # MINOR severity → no containment gate, so close succeeds and we test routing.
        return QuarantineDisposition.objects.create(
            tenant=self.tenant, part=self.part, step=self.task_step,
            disposition_type="REWORK", severity="MINOR", description="rework route test",
        )

    def test_decision_routes_part_and_keeps_disposition_open(self):
        """2b (Y): the REWORK decision routes the part to the rework step (split),
        and the disposition stays IN_PROGRESS — it closes only on re-inspection."""
        from Tracker.services.qms.disposition import route_part_to_rework_if_needed

        disp = self._rework_disposition()
        self.part.refresh_from_db()
        self.assertEqual(self.part.part_status, "REWORK_NEEDED")  # cascade on type-set

        route_part_to_rework_if_needed(disp, self.user)

        self.part.refresh_from_db()
        self.assertEqual(self.part.step_id, self.rework_step.id)  # routed to rework
        self.assertTrue(self.part.split_from_cohort)  # pulled off the lot
        disp.refresh_from_db()
        self.assertEqual(disp.current_state, "IN_PROGRESS")  # NOT closed by routing

    def test_no_route_when_process_has_no_rework_step(self):
        # Drop the rework step from the process → routing no-ops, leaving the part
        # REWORK_NEEDED at its current step for manual routing (2c).
        from Tracker.services.qms.disposition import route_part_to_rework_if_needed

        ProcessStep.objects.filter(process=self.process, step=self.rework_step).delete()
        disp = self._rework_disposition()

        route_part_to_rework_if_needed(disp, self.user)

        self.part.refresh_from_db()
        self.assertEqual(self.part.step_id, self.task_step.id)  # unchanged
        self.assertFalse(self.part.split_from_cohort)
        self.assertEqual(self.part.part_status, "REWORK_NEEDED")

    def test_disposition_closes_when_part_leaves_rework_step(self):
        """2e: once the reworked part leaves the rework step (re-inspection passed),
        its open REWORK disposition is closed."""
        from Tracker.services.mes.parts import _close_open_rework_disposition

        disp = self._rework_disposition()  # IN_PROGRESS, MINOR (no containment gate)
        _close_open_rework_disposition(self.part, self.user)

        disp.refresh_from_db()
        self.assertEqual(disp.current_state, "CLOSED")
        self.assertTrue(disp.resolution_completed)

    def test_rework_target_without_inspection_substep_is_rejected(self):
        """2d: routing to a rework step that has no inspection substep is refused —
        a reworked part must be re-inspectable."""
        from django.core.exceptions import ValidationError
        from Tracker.models import PartSplitReason
        from Tracker.services.mes.splits import split_part_from_lot

        bad_step = Steps.objects.create(
            tenant=self.tenant, part_type=self.part_type,
            name="Rework (no inspection)", step_type="REWORK",
        )
        with self.assertRaises(ValidationError):
            split_part_from_lot(
                part=self.part, reason=PartSplitReason.REWORK, user=self.user,
                rework_target_step=bad_step,
            )
        self.part.refresh_from_db()
        self.assertFalse(self.part.split_from_cohort)  # rejected before any mutation
        self.assertEqual(self.part.step_id, self.task_step.id)
