"""Phase 0 scheduling models — CRUD, StepTiming accessors, constraints, and the
six field additions on existing models. No solver code yet.
"""
from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from Tracker.models import (
    BOM,
    BOMLine,
    ContinuousMachine,
    Equipments,
    Fixture,
    OptimizationConfig,
    Parts,
    PartTypes,
    Processes,
    ProcessStep,
    ScheduledTask,
    ScheduleResult,
    StepEdge,
    StepEquipmentAffinity,
    StepExecution,
    Steps,
    StepTiming,
    Tenant,
    WorkCenterChangeover,
    WorkOrder,
    WorkOrderStatus,
)
from Tracker.models.scheduling import AttentionType, FenceZone, SolverStatus
from Tracker.tests.base import TenantContextMixin
from django.test import TestCase


class SchedulingModelTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Sched", slug="sched-models", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Injector")
        self.process = Processes.objects.create(tenant=self.tenant, name="P", part_type=self.pt)
        self.step1 = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name="Turn", step_type="TASK")
        self.step2 = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name="Mill", step_type="TASK")
        ProcessStep.objects.create(process=self.process, step=self.step1, order=1)
        ProcessStep.objects.create(process=self.process, step=self.step2, order=2)
        self.machine = Equipments.objects.create(tenant=self.tenant, name="CNC-1")

    # ---- StepTiming + accessors -------------------------------------------

    def test_step_timing_full_attention_accessors(self):
        t = StepTiming.objects.create(
            tenant=self.tenant, step=self.step1,
            setup_minutes=10, cycle_time_minutes=2, load_unload_per_piece=1,
            attention_type=AttentionType.FULL, external_setup_minutes=3,
        )
        self.assertEqual(t.machine_wall_time(5), 10 + 2 * 5)        # 20
        self.assertEqual(t.first_piece_done(), 10 + 2 + 1)          # 13
        # Full attention: operator tied to the whole machine run.
        self.assertEqual(t.operator_attended_time(5), 20)

    def test_step_timing_load_unload_attention(self):
        t = StepTiming.objects.create(
            tenant=self.tenant, step=self.step2,
            setup_minutes=10, cycle_time_minutes=2, load_unload_per_piece=1,
            attention_type=AttentionType.LOAD_UNLOAD,
        )
        # Load/unload only: setup + a touch per piece (machine runs unattended).
        self.assertEqual(t.operator_attended_time(5), 10 + 1 * 5)   # 15
        self.assertLess(t.operator_attended_time(5), t.machine_wall_time(5))

    def test_step_timing_is_one_to_one(self):
        StepTiming.objects.create(tenant=self.tenant, step=self.step1, cycle_time_minutes=1)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                StepTiming.objects.create(tenant=self.tenant, step=self.step1, cycle_time_minutes=2)

    # ---- affinity / changeover constraints --------------------------------

    def test_affinity_unique_per_step_equipment(self):
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=self.step1, equipment=self.machine,
            affinity=StepEquipmentAffinity.Affinity.PREFERRED, cycle_time_override=1.5,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                StepEquipmentAffinity.objects.create(
                    tenant=self.tenant, step=self.step1, equipment=self.machine,
                )

    def test_changeover_unique(self):
        WorkCenterChangeover.objects.create(
            tenant=self.tenant, equipment=self.machine,
            from_step=self.step1, to_step=self.step2, changeover_minutes=30,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                WorkCenterChangeover.objects.create(
                    tenant=self.tenant, equipment=self.machine,
                    from_step=self.step1, to_step=self.step2, changeover_minutes=45,
                )

    # ---- fixture / continuous / config ------------------------------------

    def test_fixture_m2m(self):
        f = Fixture.objects.create(tenant=self.tenant, name="Vise A", quantity=2)
        f.steps.add(self.step1, self.step2)
        self.assertEqual(f.steps.count(), 2)
        self.assertIn(f, self.step1.fixtures.all())

    def test_continuous_machine_one_to_one(self):
        ContinuousMachine.objects.create(
            tenant=self.tenant, equipment=self.machine, parts_per_hour=120,
            bar_change_interval_hours=8, bar_change_duration_minutes=15,
        )
        self.assertEqual(self.machine.continuous_profile.parts_per_hour, 120)

    def test_optimization_config_one_per_tenant(self):
        OptimizationConfig.objects.create(tenant=self.tenant)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                OptimizationConfig.objects.create(tenant=self.tenant)

    # ---- ScheduleResult / ScheduledTask -----------------------------------

    def test_schedule_result_and_tasks(self):
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-SCH-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=1, process=self.process,
        )
        part = Parts.objects.create(
            tenant=self.tenant, ERP_id="P-SCH-1", part_type=self.pt, work_order=wo, step=self.step1,
        )
        now = timezone.now()
        sched = ScheduleResult.objects.create(
            tenant=self.tenant, horizon_start=now, horizon_end=now + timedelta(days=7),
            solver_status=SolverStatus.OPTIMAL, solve_time_ms=1234, objective_value_cents=500000,
            is_active=True,
        )
        task = ScheduledTask.objects.create(
            tenant=self.tenant, schedule=sched, part=part, step=self.step1, machine=self.machine,
            start_time=now, end_time=now + timedelta(hours=1), fence_zone=FenceZone.FROZEN, is_pinned=True,
        )
        self.assertEqual(sched.tasks.count(), 1)
        self.assertEqual(task.machine, self.machine)
        self.assertTrue(task.is_pinned)

    # ---- the six field additions ------------------------------------------

    def test_step_and_edge_scheduling_fields(self):
        self.step1.max_continuous_minutes = 45
        self.step1.save(update_fields=["max_continuous_minutes"])
        self.step1.refresh_from_db()
        self.assertEqual(self.step1.max_continuous_minutes, 45)

        edge = StepEdge.objects.create(
            process=self.process, from_step=self.step1, to_step=self.step2,
            tech_continuity="DIFFERENT",
        )
        self.assertEqual(edge.tech_continuity, "DIFFERENT")

    def test_step_execution_equipment_fk(self):
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-SCH-2",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=1, process=self.process,
        )
        part = Parts.objects.create(
            tenant=self.tenant, ERP_id="P-SCH-2", part_type=self.pt, work_order=wo, step=self.step1,
        )
        ex = StepExecution.objects.create(
            tenant=self.tenant, part=part, step=self.step1, visit_number=1,
            status="IN_PROGRESS", equipment=self.machine,
        )
        ex.refresh_from_db()
        self.assertEqual(ex.equipment, self.machine)
        self.assertIn(ex, self.machine.step_executions.all())

    def test_bomline_source_and_workorder_peg(self):
        bom = BOM.objects.create(tenant=self.tenant, part_type=self.pt, bom_type="ASSEMBLY")
        line = BOMLine.objects.create(
            tenant=self.tenant, bom=bom, component_type=self.pt,
            quantity=Decimal("1"), source="MAKE",
        )
        self.assertEqual(line.source, "MAKE")

        parent = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-PARENT",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=1, process=self.process,
        )
        child = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-CHILD",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=1, process=self.process,
            pegged_to_workorder=parent, pegged_to_bom_line=line,
        )
        child.refresh_from_db()
        self.assertEqual(child.pegged_to_workorder, parent)
        self.assertEqual(child.pegged_to_bom_line, line)
        # Distinct from split provenance.
        self.assertIsNone(child.parent_workorder)
        self.assertIn(child, parent.component_pegs.all())
