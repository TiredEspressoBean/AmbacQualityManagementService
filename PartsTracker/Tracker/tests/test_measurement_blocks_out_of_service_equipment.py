"""A measurement captured against an OUT_OF_SERVICE gauge must be refused
at the source.

Background: `apply_calibration_result_to_equipment` sets
`Equipments.status = OUT_OF_SERVICE` on a FAIL calibration. Prior behavior:
the flag was set but nothing consumed it — the operator's substep capture
would still commit against a failed gauge, and the reading rode along on
`StepExecutionMeasurement.equipment`. That defeats the whole point of the
signal: parts measured with an out-of-cal gauge become suspect product
retroactively, and the system silently accepted them.

The fix: `_handle_measurement` in operator_capture.py now raises
ValidationError when the picked equipment is OUT_OF_SERVICE.
"""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from Tracker.models import (
    Equipments, EquipmentStatus, MeasurementDefinition, PartTypes, Parts,
    Processes, ProcessStep, StepExecution, Steps, Substep, Tenant, WorkOrder,
    WorkOrderStatus,
)
from Tracker.services.dwi.operator_capture import _handle_measurement
from Tracker.tests.base import TenantContextMixin, VectorTestCase


class OutOfServiceEquipmentBlocksMeasurementTests(TenantContextMixin, VectorTestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(
            name="Oos Gauge", slug="oos-gauge", tier="PRO",
        )
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        self.user = User.objects.create_user(
            username="oos-op", email="oos@op.test", password="x", tenant=self.tenant,
        )
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Widget")
        self.process = Processes.objects.create(
            tenant=self.tenant, name="P-OOS", part_type=self.pt,
        )
        self.step = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Measure",
            step_type="TASK",
        )
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-OOS-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=1, process=self.process,
        )
        self.part = Parts.objects.create(
            tenant=self.tenant, ERP_id='P-OOS-1', part_type=self.pt,
            work_order=self.wo, step=self.step,
        )
        self.step_execution = StepExecution.objects.create(
            tenant=self.tenant, part=self.part, step=self.step, visit_number=1,
            status="IN_PROGRESS",
            training_authorization={'authorized': True, 'missing': [], 'verified': []},
        )
        self.md = MeasurementDefinition.objects.create(
            tenant=self.tenant, step=self.step, label='Bore diameter',
            unit='mm', nominal=10.0, upper_tol=0.05, lower_tol=0.05,
            type='NUMERIC',
        )
        self.substep = Substep.objects.create(
            tenant=self.tenant, step=self.step, order=1,
            title='Measure bore', body_blocks={},
        )

    def _make_equipment(self, name, status):
        return Equipments.objects.create(
            tenant=self.tenant, name=name, status=status,
        )

    def test_measurement_against_out_of_service_gauge_is_refused(self):
        gauge = self._make_equipment('Broken Micrometer', EquipmentStatus.OUT_OF_SERVICE)
        cap = {
            'kind': 'measurement',
            'measurement_definition_id': self.md.pk,
            'value_numeric': 10.02,
            'value_string': '',
            'equipment_id': gauge.pk,
        }
        with self.assertRaises(ValidationError) as ctx:
            _handle_measurement(
                cap, substep=self.substep, step_execution=self.step_execution,
                user=self.user,
            )
        self.assertIn('OUT_OF_SERVICE', str(ctx.exception))
        self.assertIn('Broken Micrometer', str(ctx.exception))

    def test_measurement_against_in_service_gauge_proceeds(self):
        """Regression guard: only OUT_OF_SERVICE is blocked."""
        gauge = self._make_equipment('Good Micrometer', EquipmentStatus.IN_SERVICE)
        cap = {
            'kind': 'measurement',
            'measurement_definition_id': self.md.pk,
            'value_numeric': 10.02,
            'value_string': '',
            'equipment_id': gauge.pk,
        }
        _handle_measurement(
            cap, substep=self.substep, step_execution=self.step_execution,
            user=self.user,
        )

    def test_measurement_with_no_equipment_id_still_works(self):
        """Visual checks / free-form measurements without a gauge continue
        to work — the block only fires when equipment_id is set."""
        cap = {
            'kind': 'measurement',
            'measurement_definition_id': self.md.pk,
            'value_numeric': 10.02,
            'value_string': '',
            'equipment_id': None,
        }
        _handle_measurement(
            cap, substep=self.substep, step_execution=self.step_execution,
            user=self.user,
        )
