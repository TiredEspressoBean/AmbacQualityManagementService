"""`/api/StepExecutionMeasurements/bulk-record/` must go through the capture service.

The action used to call `StepExecutionMeasurement.objects.create()` itself,
which skipped `services.qms.inline_capture.record_dwi_measurement` -- the thing
that actually owns this write. That service does the Tier 1 / Tier 2 split in a
transaction: always the process datum, plus a QualityReports row and a
MeasurementResult when the substep is an inspection point, plus the report side
effects.

So a reading taken against an inspection-point substep through this endpoint
produced process data and no inspection record, while the same reading through
the operator runtime produced both. Two doors to one table, one of them quietly
doing less.

The Tier 2 artefact is what these tests assert, because that is precisely what a
direct write omits without erroring.
"""
from Tracker.models import (
    MeasurementDefinition, Parts, PartTypes, Processes, ProcessStep,
    QualityReports, StepExecution, StepExecutionMeasurement, Steps, Substep,
    WorkOrder, WorkOrderStatus,
)
from Tracker.tests.base import TenantTestCase


class BulkRecordRoutesThroughCaptureServiceTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        t = self.tenant_a
        pt = PartTypes.objects.create(tenant=t, name="Widget")
        process = Processes.objects.create(tenant=t, name="P-BULK", part_type=pt)
        self.step = Steps.objects.create(
            tenant=t, part_type=pt, name="Op-BULK", step_type="TASK",
        )
        ProcessStep.objects.create(process=process, step=self.step, order=1)
        wo = WorkOrder.objects.create(
            tenant=t, ERP_id="WO-BULK-1", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=1, process=process,
        )
        self.part = Parts.objects.create(
            tenant=t, ERP_id="P-BULK-1", part_type=pt, work_order=wo, step=self.step,
        )
        self.step_execution = StepExecution.objects.create(
            tenant=t, part=self.part, step=self.step, visit_number=1, status="IN_PROGRESS",
        )
        self.measurement_def = MeasurementDefinition.objects.create(
            tenant=t, label="Outer Diameter", type="NUMERIC", unit="in",
            nominal=1.247, upper_tol=0.002, lower_tol=0.002, step=self.step,
        )
        self.routine_substep = Substep.objects.create(
            tenant=t, step=self.step, order=1, title="Measure OD",
            is_inspection_point=False,
        )
        self.inspection_substep = Substep.objects.create(
            tenant=t, step=self.step, order=2, title="Verify OD",
            is_inspection_point=True,
        )

        self.authenticate_as(self.user_a, self.tenant_a)
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'add_stepexecutionmeasurement', 'view_stepexecutionmeasurement',
            'add_qualityreports', 'view_qualityreports', 'change_parts',
            'full_tenant_access',
        ])

    def _post(self, measurements):
        return self.client.post(
            '/api/StepExecutionMeasurements/bulk-record/',
            {'step_execution': str(self.step_execution.id), 'measurements': measurements},
            format='json',
        )

    def test_inspection_point_capture_creates_the_tier_2_record(self):
        """The regression: a direct write produced Tier 1 only, silently."""
        res = self._post([{
            'measurement_definition': str(self.measurement_def.id),
            'substep': str(self.inspection_substep.id),
            'value': 1.247,
        }])
        self.assertEqual(res.status_code, 201, getattr(res, 'data', res))
        self.assertEqual(res.data['created_count'], 1, getattr(res, 'data', res))

        self.assertEqual(StepExecutionMeasurement.objects.count(), 1)
        self.assertEqual(
            QualityReports.objects.count(), 1,
            "an inspection-point capture must also land a QualityReports row",
        )

    def test_routine_capture_stays_process_data_only(self):
        """The service's other branch still applies -- this is not 'always make a report'."""
        res = self._post([{
            'measurement_definition': str(self.measurement_def.id),
            'substep': str(self.routine_substep.id),
            'value': 1.247,
        }])
        self.assertEqual(res.status_code, 201, getattr(res, 'data', res))
        self.assertEqual(StepExecutionMeasurement.objects.count(), 1)
        self.assertEqual(QualityReports.objects.count(), 0)

    def test_spec_evaluation_still_happens(self):
        """is_within_spec is auto-evaluated on save; an out-of-spec value must show it."""
        res = self._post([{
            'measurement_definition': str(self.measurement_def.id),
            'substep': str(self.routine_substep.id),
            'value': 9.999,
        }])
        self.assertEqual(res.status_code, 201, getattr(res, 'data', res))
        self.assertFalse(StepExecutionMeasurement.objects.get().is_within_spec)

    def test_substep_is_required(self):
        """Without it there is no way to decide Tier 2, so the row is refused
        rather than written as process data by default."""
        res = self._post([{
            'measurement_definition': str(self.measurement_def.id),
            'value': 1.247,
        }])
        self.assertEqual(res.status_code, 201, getattr(res, 'data', res))
        self.assertEqual(res.data['created_count'], 0)
        self.assertIn('substep', str(res.data['errors']))
        self.assertEqual(StepExecutionMeasurement.objects.count(), 0)
