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
    MeasurementDefinition,
    MeasurementResult,
    PartsStatus,
    PartTypes,
    Parts,
    Processes,
    ProcessStep,
    QualityReports,
    StepExecutionMeasurement,
    Steps,
    Substep,
    SubstepCompletion,
    Tenant,
    WorkOrder,
    WorkOrderStatus,
)
from Tracker.services.dwi.batch_lifecycle import seal_batch
from Tracker.services.dwi.operator_capture import submit_substep
from Tracker.tests.base import TenantContextMixin, TenantTestCase, VectorTestCase


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

    def test_batch_measurement_binds_to_batch_not_a_part(self):
        """Phase 2: a BATCH-scope measurement (one cycle reading for the whole
        load — wash temp, cure time) persists, keyed on the batch. It has no
        step_execution because it belongs to no single part."""
        md = MeasurementDefinition.objects.create(
            tenant=self.tenant, label="Bath temperature", type="NUMERIC",
            unit="C", nominal=60.0, upper_tol=5.0, lower_tol=5.0, step=self.step,
        )
        submit_substep(
            substep=self.batch_substep,
            batch_execution=self.batch,
            user=self.user,
            captures=[{"node_id": str(uuid4()), "kind": "measurement",
                       "measurement_definition_id": str(md.id), "value_numeric": 61.0}],
        )
        sem = StepExecutionMeasurement.objects.get(batch_execution=self.batch)
        self.assertIsNone(sem.step_execution_id)
        self.assertEqual(sem.batch_execution_id, self.batch.id)
        self.assertTrue(sem.is_within_spec)  # 61 within 60±5


class BatchInspectionRecordTests(TenantContextMixin, VectorTestCase):
    """Phase 2: a BATCH-scope *inspection* substep now produces a QualityReports
    keyed on the batch. Before, `not is_batch` skipped report creation and a
    batch inspection recorded nothing."""

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Batch Insp", slug="batch-insp", tier="PRO")
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        self.user = User.objects.create_user(
            username="op-bi", email="bi@b.test", password="x", tenant=self.tenant,
        )
        self.part_type = PartTypes.objects.create(tenant=self.tenant, name="Widget")
        self.process = Processes.objects.create(
            tenant=self.tenant, name="P", part_type=self.part_type,
        )
        self.step = Steps.objects.create(
            tenant=self.tenant, part_type=self.part_type, name="Passivate", step_type="TASK",
        )
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)
        self.batch_insp = Substep.objects.create(
            tenant=self.tenant, step=self.step, order=0, title="Bath verification",
            scope="batch", is_optional=False, is_inspection_point=True,
        )
        self.md = MeasurementDefinition.objects.create(
            tenant=self.tenant, label="Bath pH", type="NUMERIC",
            unit="pH", nominal=7.0, upper_tol=0.5, lower_tol=0.5, step=self.step,
        )
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-BI-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=3, process=self.process,
        )
        self.parts = [
            Parts.objects.create(
                tenant=self.tenant, ERP_id=f"P-BI-{i}", part_type=self.part_type,
                work_order=self.wo, step=self.step,
            )
            for i in range(3)
        ]
        self.batch = BatchExecution.objects.create(
            tenant=self.tenant, work_order=self.wo, step=self.step, started_by=self.user,
        )
        self.batch.parts.set(self.parts)

    def test_batch_inspection_creates_report_keyed_on_batch(self):
        result = submit_substep(
            substep=self.batch_insp,
            batch_execution=self.batch,
            user=self.user,
            captures=[{"node_id": str(uuid4()), "kind": "measurement",
                       "measurement_definition_id": str(self.md.id), "value_numeric": 7.1}],
        )
        self.assertIsNotNone(result.quality_report_id)

        qr = QualityReports.objects.get(batch_execution=self.batch, substep=self.batch_insp)
        self.assertIsNone(qr.step_execution_id)   # batch provenance, not part
        self.assertIsNone(qr.part_id)
        self.assertEqual(qr.status, "PASS")       # 7.1 within 7.0±0.5
        # The reading promoted to a MeasurementResult under the batch report.
        self.assertEqual(MeasurementResult.objects.filter(report=qr).count(), 1)

    def test_failing_batch_cycle_fails_report_but_quarantines_no_part(self):
        """A bad cycle marks the report FAIL, but the part-scoped side-effect
        machinery (auto-quarantine) is skipped — there's no single part."""
        submit_substep(
            substep=self.batch_insp,
            batch_execution=self.batch,
            user=self.user,
            captures=[{"node_id": str(uuid4()), "kind": "measurement",
                       "measurement_definition_id": str(self.md.id), "value_numeric": 9.0}],  # out of spec
        )
        qr = QualityReports.objects.get(batch_execution=self.batch, substep=self.batch_insp)
        self.assertEqual(qr.status, "FAIL")
        for p in self.parts:
            p.refresh_from_db()
            self.assertNotEqual(p.part_status, PartsStatus.QUARANTINED)

    def test_repeat_capture_converges_on_one_batch_report(self):
        for ph in (7.0, 7.2):
            submit_substep(
                substep=self.batch_insp, batch_execution=self.batch, user=self.user,
                captures=[{"node_id": str(uuid4()), "kind": "measurement",
                           "measurement_definition_id": str(self.md.id), "value_numeric": ph}],
            )
        self.assertEqual(
            QualityReports.objects.filter(batch_execution=self.batch, substep=self.batch_insp).count(),
            1,
        )

    def test_constraint_refuses_both_provenance_modes(self):
        from django.db import IntegrityError, transaction
        se = self.parts[0].step_executions.create(
            tenant=self.tenant, step=self.step, visit_number=1,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            QualityReports.objects.create(
                tenant=self.tenant, step=self.step, detected_by=self.user, status="PENDING",
                step_execution=se, batch_execution=self.batch, substep=self.batch_insp,
            )

    def test_measurement_target_constraint_refuses_neither(self):
        from django.db import IntegrityError, transaction
        with self.assertRaises(IntegrityError), transaction.atomic():
            StepExecutionMeasurement.objects.create(
                tenant=self.tenant, measurement_definition=self.md, value=7.0,
                recorded_by=self.user,  # no step_execution, no batch_execution
            )


class BatchQueryableApiTests(TenantTestCase):
    """Phase 2.5: batch reports/measurements are reachable over the API — by
    batch id, and (the traveler read pattern) by a member part. Before this,
    the QR/SEM viewsets had no batch filter, so batch data was write-only.

    Authenticated as superuser to isolate filter behavior from the permission
    gate (a separate concern), scoped to tenant_a via the X-Tenant-ID header.
    """

    def setUp(self):
        super().setUp()
        t = self.tenant_a
        self.part_type = PartTypes.objects.create(tenant=t, name="Widget")
        self.process = Processes.objects.create(tenant=t, name="P", part_type=self.part_type)
        self.step = Steps.objects.create(
            tenant=t, part_type=self.part_type, name="Passivate", step_type="TASK",
        )
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)
        self.substep = Substep.objects.create(
            tenant=t, step=self.step, order=0, title="Bath check",
            scope="batch", is_inspection_point=True,
        )
        self.md = MeasurementDefinition.objects.create(
            tenant=t, label="pH", type="NUMERIC", unit="pH",
            nominal=7.0, upper_tol=0.5, lower_tol=0.5, step=self.step,
        )
        self.wo = WorkOrder.objects.create(
            tenant=t, ERP_id="WO-BQ", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=2, process=self.process,
        )
        self.parts = [
            Parts.objects.create(
                tenant=t, ERP_id=f"P-BQ-{i}", part_type=self.part_type,
                work_order=self.wo, step=self.step,
            )
            for i in range(2)
        ]
        self.batch = BatchExecution.objects.create(
            tenant=t, work_order=self.wo, step=self.step, started_by=self.user_a,
        )
        self.batch.parts.set(self.parts)
        submit_substep(
            substep=self.substep, batch_execution=self.batch, user=self.user_a,
            captures=[{"node_id": str(uuid4()), "kind": "measurement",
                       "measurement_definition_id": str(self.md.id), "value_numeric": 7.1}],
        )
        self.batch_qr = QualityReports.objects.get(
            batch_execution=self.batch, substep=self.substep,
        )
        self.authenticate_superuser(tenant=t)

    def _rows(self, resp):
        data = resp.json()
        return data["results"] if isinstance(data, dict) and "results" in data else data

    def test_report_queryable_by_batch(self):
        resp = self.client.get(f"/api/QualityReports/?batch_execution={self.batch.id}")
        self.assertEqual(resp.status_code, 200)
        ids = [row["id"] for row in self._rows(resp)]
        self.assertIn(str(self.batch_qr.id), ids)

    def test_report_queryable_by_member_part(self):
        # The traveler's read: "batch reports for this part" via the members M2M.
        resp = self.client.get(f"/api/QualityReports/?batch_execution__parts={self.parts[0].id}")
        self.assertEqual(resp.status_code, 200)
        ids = [row["id"] for row in self._rows(resp)]
        self.assertIn(str(self.batch_qr.id), ids)

    def test_batch_report_absent_from_part_scoped_query(self):
        # A batch report has part=null, so the pre-existing WO-scoped query
        # (part__work_order) does NOT surface it — which is exactly why the
        # batch filter had to be added.
        resp = self.client.get(f"/api/QualityReports/?part__work_order={self.wo.id}")
        self.assertEqual(resp.status_code, 200)
        ids = [row["id"] for row in self._rows(resp)]
        self.assertNotIn(str(self.batch_qr.id), ids)

    def test_measurement_queryable_by_batch(self):
        resp = self.client.get(f"/api/StepExecutionMeasurements/?batch_execution={self.batch.id}")
        self.assertEqual(resp.status_code, 200)
        rows = self._rows(resp)
        self.assertGreaterEqual(len(rows), 1)
        self.assertTrue(all(row["batch_execution"] == str(self.batch.id) for row in rows))
