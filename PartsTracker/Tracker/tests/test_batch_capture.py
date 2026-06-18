"""3a: batch-scope substep capture write path.

A BATCH-scope substep's capture binds to a BatchExecution (not a per-part
StepExecution), which is exactly what seal_batch requires. Before the write
path existed, seal always failed; now a batch capture lands a SubstepCompletion
on the batch and the batch can seal.
"""
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from Tracker.models import (
    BatchExecution,
    PartTypes,
    Parts,
    Processes,
    ProcessStep,
    Steps,
    Substep,
    SubstepCompletion,
    Tenant,
    WorkOrder,
    WorkOrderStatus,
)
from Tracker.services.dwi.batch_lifecycle import seal_batch
from Tracker.services.dwi.operator_capture import submit_substep
from Tracker.tests.base import TenantContextMixin, VectorTestCase


class BatchCaptureWritePathTests(TenantContextMixin, VectorTestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(
            name="Batch Cap", slug="batch-cap", tier="PRO"
        )
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        self.user = User.objects.create_user(
            username="op-batch", email="b@b.test", password="x", tenant=self.tenant,
        )
        self.part_type = PartTypes.objects.create(tenant=self.tenant, name="Widget")
        self.process = Processes.objects.create(
            tenant=self.tenant, name="P", part_type=self.part_type,
        )
        self.step = Steps.objects.create(
            tenant=self.tenant, part_type=self.part_type, name="Heat Treat", step_type="TASK",
        )
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)
        # A required BATCH-scope substep — the once-per-lot capture.
        self.batch_substep = Substep.objects.create(
            tenant=self.tenant, step=self.step, order=0, title="Confirm cycle",
            scope="batch", is_optional=False,
        )
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-BC-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=2, process=self.process,
        )
        self.parts = [
            Parts.objects.create(
                tenant=self.tenant, ERP_id=f"P-BC-{i}", part_type=self.part_type,
                work_order=self.wo, step=self.step,
            )
            for i in range(2)
        ]
        self.batch = BatchExecution.objects.create(
            tenant=self.tenant, work_order=self.wo, step=self.step, started_by=self.user,
        )
        self.batch.parts.set(self.parts)

    def test_seal_fails_without_batch_completion(self):
        with self.assertRaises(ValidationError):
            seal_batch(batch=self.batch, user=self.user)

    def test_batch_capture_writes_completion_and_enables_seal(self):
        result = submit_substep(
            substep=self.batch_substep,
            batch_execution=self.batch,
            user=self.user,
            captures=[{"node_id": str(uuid4()), "kind": "attestation", "confirm": True}],
        )
        self.assertIsNotNone(result.completion_id)
        self.assertIsNone(result.quality_report_id)  # batch substeps don't make a QR

        # The completion binds to the batch, not a step_execution.
        comp = SubstepCompletion.objects.get(
            batch_execution=self.batch, substep=self.batch_substep,
        )
        self.assertIsNone(comp.step_execution_id)
        self.assertFalse(comp.is_voided)

        # With the completion present, the batch now seals.
        seal_batch(batch=self.batch, user=self.user)
        self.batch.refresh_from_db()
        self.assertIsNotNone(self.batch.sealed_at)

    def test_batch_submit_rejects_measurement_capture(self):
        with self.assertRaises(ValidationError):
            submit_substep(
                substep=self.batch_substep,
                batch_execution=self.batch,
                user=self.user,
                captures=[{"node_id": str(uuid4()), "kind": "measurement",
                           "measurement_definition_id": None, "value_numeric": 1.0}],
            )
