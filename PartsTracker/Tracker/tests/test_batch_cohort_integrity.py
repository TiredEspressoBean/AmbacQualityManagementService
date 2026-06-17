"""3c/3d: batch cohort integrity, the disjoint-membership guard, terminal
part exclusion + per-load independent advancement, and the large-cohort
async seal dispatch.

A single WO at one step legitimately runs as several concurrent batches
(furnace/wash/autoclave loads). These cover:
  - seal reconciles membership (drops parts that went terminal after start);
  - a part is in at most one OPEN batch per step (disjoint membership), but
    multiple open batches per (WO, step) are allowed;
  - each sealed load advances on its own, without waiting for the others;
  - the lot-cohesion engine never blocks/advances a terminal part;
  - a large cohort defers seal-triggered advancement to Celery.
"""
from unittest import mock
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from Tracker.models import (
    BatchExecution,
    PartTypes,
    Parts,
    PartsStatus,
    Processes,
    ProcessStep,
    StepExecution,
    Steps,
    Substep,
    Tenant,
    WorkOrder,
    WorkOrderStatus,
)
from Tracker.services.dwi.batch_lifecycle import (
    assert_no_open_batch_overlap,
    seal_batch,
)
from Tracker.services.dwi.operator_capture import submit_substep
from Tracker.services.mes.advancement import try_advance_lot
from Tracker.tests.base import TenantContextMixin, VectorTestCase


class BatchCohortIntegrityTests(TenantContextMixin, VectorTestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Cohort", slug="cohort", tier="PRO")
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        self.user = User.objects.create_user(
            username="op-cohort", email="c@c.test", password="x", tenant=self.tenant,
        )
        self.part_type = PartTypes.objects.create(tenant=self.tenant, name="Widget")
        self.process = Processes.objects.create(
            tenant=self.tenant, name="P", part_type=self.part_type,
        )
        self.step = Steps.objects.create(
            tenant=self.tenant, part_type=self.part_type, name="Heat Treat", step_type="TASK",
        )
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)
        self.batch_substep = Substep.objects.create(
            tenant=self.tenant, step=self.step, order=0, title="Confirm cycle",
            scope="batch", is_optional=False,
        )
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-CI-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=2, process=self.process,
        )
        self.parts = [
            Parts.objects.create(
                tenant=self.tenant, ERP_id=f"P-CI-{i}", part_type=self.part_type,
                work_order=self.wo, step=self.step,
            )
            for i in range(2)
        ]

    def _open_batch(self, parts):
        batch = BatchExecution.objects.create(
            tenant=self.tenant, work_order=self.wo, step=self.step, started_by=self.user,
        )
        batch.parts.set(parts)
        return batch

    def _capture_batch_substep(self, batch):
        submit_substep(
            substep=self.batch_substep,
            batch_execution=batch,
            user=self.user,
            captures=[{"node_id": str(uuid4()), "kind": "attestation", "confirm": True}],
        )

    # ----- 3c(a): seal reconciles membership -----
    def test_seal_drops_scrapped_member(self):
        batch = self._open_batch(self.parts)
        self._capture_batch_substep(batch)

        scrapped = self.parts[0]
        scrapped.part_status = PartsStatus.SCRAPPED
        scrapped.save(update_fields=["part_status"])

        seal_batch(batch=batch, user=self.user)
        batch.refresh_from_db()
        self.assertIsNotNone(batch.sealed_at)
        member_ids = set(batch.parts.values_list("id", flat=True))
        self.assertNotIn(scrapped.id, member_ids)
        self.assertIn(self.parts[1].id, member_ids)

    def test_seal_fails_when_all_members_terminal(self):
        batch = self._open_batch(self.parts)
        self._capture_batch_substep(batch)
        for p in self.parts:
            p.part_status = PartsStatus.SCRAPPED
            p.save(update_fields=["part_status"])
        with self.assertRaises(ValidationError):
            seal_batch(batch=batch, user=self.user)

    # ----- 3c(b): disjoint membership; multiple open batches allowed -----
    def test_disjoint_open_batches_allowed(self):
        self._open_batch([self.parts[0]])
        # A second open batch at the same (WO, step) with a DIFFERENT part is
        # fine — the guard only objects to overlapping membership.
        assert_no_open_batch_overlap(step=self.step, parts=[self.parts[1]])
        self._open_batch([self.parts[1]])
        open_count = BatchExecution.objects.filter(
            work_order=self.wo, step=self.step, sealed_at__isnull=True,
        ).count()
        self.assertEqual(open_count, 2)

    def test_overlapping_open_batch_rejected(self):
        self._open_batch([self.parts[0]])
        with self.assertRaises(ValidationError):
            assert_no_open_batch_overlap(step=self.step, parts=[self.parts[0]])

    def test_overlap_allowed_after_seal(self):
        first = self._open_batch([self.parts[0]])
        self._capture_batch_substep(first)
        seal_batch(batch=first, user=self.user)
        # Sealed batches don't reserve membership — no raise.
        assert_no_open_batch_overlap(step=self.step, parts=[self.parts[0]])

    # ----- 3c: advancement never touches a terminal part -----
    def test_advance_excludes_terminal_parts(self):
        for p in self.parts:
            p.part_status = PartsStatus.SCRAPPED
            p.save(update_fields=["part_status"])
        result = try_advance_lot(
            work_order_id=str(self.wo.id),
            step_id=str(self.step.id),
            tenant_id=str(self.tenant.id),
            operator=self.user,
        )
        self.assertEqual(result.status, "noop")
        self.assertEqual(result.reason, "no_parts_at_step")

    # ----- 3c: each sealed load advances independently -----
    def test_sealed_load_advances_without_waiting_for_other_load(self):
        next_step = Steps.objects.create(
            tenant=self.tenant, part_type=self.part_type, name="Quench", step_type="TASK",
        )
        ProcessStep.objects.create(process=self.process, step=next_step, order=2)
        # Each part needs an active StepExecution to advance.
        for p in self.parts:
            StepExecution.objects.create(
                tenant=self.tenant, part=p, step=self.step, visit_number=1, status="IN_PROGRESS",
            )
        load_a = self._open_batch([self.parts[0]])
        self._open_batch([self.parts[1]])  # load B — left unsealed
        self._capture_batch_substep(load_a)

        seal_batch(batch=load_a, user=self.user)

        self.parts[0].refresh_from_db()
        self.parts[1].refresh_from_db()
        # Load A's part advanced; load B's part stays put (its batch isn't sealed).
        self.assertEqual(self.parts[0].step_id, next_step.id)
        self.assertEqual(self.parts[1].step_id, self.step.id)

    # ----- 3d: large-cohort seal defers advancement to Celery -----
    def test_large_cohort_seal_dispatches_async(self):
        batch = self._open_batch(self.parts)
        self._capture_batch_substep(batch)
        with mock.patch(
            "Tracker.services.dwi.batch_lifecycle.ASYNC_ADVANCE_THRESHOLD", 1
        ), mock.patch("Tracker.tasks.advance_lot_task.delay") as delay:
            with self.captureOnCommitCallbacks(execute=True):
                seal_batch(batch=batch, user=self.user)
        delay.assert_called_once()
        _, kwargs = delay.call_args
        self.assertEqual(kwargs["work_order_id"], str(self.wo.id))
        self.assertEqual(kwargs["step_id"], str(self.step.id))
