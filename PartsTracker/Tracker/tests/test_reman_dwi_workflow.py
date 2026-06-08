"""
Tests for Reman DWI integration — Phases R2 + R4.

R2 (Core.step + advance_core_step + auto-coordination):
- advance_core_step routes Cores through teardown Steps
- R5 auto-coordination: Core status flips RECEIVED → IN_DISASSEMBLY on first step,
  IN_DISASSEMBLY → DISASSEMBLED on terminal step.
- WorkOrder completion cascade includes Cores (Parts AND Cores must all be terminal).

R4 (HarvestedComponentCapture backend service):
- create_harvested_components_from_capture writes one HarvestedComponent per row
- SCRAP grade dispatches scrap_component in the same transaction
- Validation errors surface before any partial write
- Missing rows are tracked separately from created rows
"""

from datetime import date

from django.test import TestCase

from Tracker.models import (
    Companies,
    Core,
    PartTypes,
    Processes,
    ProcessStep,
    Steps,
    Tenant,
    User,
    WorkOrder,
    WorkOrderStatus,
)
from Tracker.models.mes_lite import StepEdge, StepExecution
from Tracker.services.mes.cores import advance_core_step, begin_core_step_execution
from Tracker.utils.tenant_context import (
    reset_current_tenant,
    set_current_tenant_id,
)


class _RemanDwiBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name="Reman Shop", slug="reman-dwi-shop")
        cls._cv = set_current_tenant_id(cls.tenant.id)
        cls.user = User.objects.create_user(
            username="op", email="op@test.com", password="pw", tenant=cls.tenant,
        )
        cls.customer = Companies.objects.create(name="Cust", tenant=cls.tenant)
        cls.core_type = PartTypes.objects.create(
            name="Injector Core", ID_prefix="INJ", tenant=cls.tenant,
        )

    @classmethod
    def tearDownClass(cls):
        token = getattr(cls, '_cv', None)
        if token is not None:
            reset_current_tenant(token)
            cls._cv = None
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self._test_cv = set_current_tenant_id(self.tenant.id)

    def tearDown(self):
        token = getattr(self, '_test_cv', None)
        if token is not None:
            reset_current_tenant(token)
            self._test_cv = None
        super().tearDown()

    def _make_process(self, steps_spec):
        """Build a Process with the given list of (name, is_terminal) tuples.

        Returns (process, [steps]). Steps are linked in order via DEFAULT edges.
        """
        process = Processes.objects.create(
            name="Teardown Process",
            part_type=self.core_type,
            tenant=self.tenant,
        )
        steps = []
        for i, (name, is_terminal) in enumerate(steps_spec):
            step = Steps.objects.create(
                name=name,
                is_terminal=is_terminal,
                terminal_status='completed' if is_terminal else '',
                part_type=self.core_type,
                tenant=self.tenant,
            )
            ProcessStep.objects.create(
                process=process, step=step, order=i + 1,
            )
            steps.append(step)

        # Link with DEFAULT edges
        for a, b in zip(steps, steps[1:]):
            StepEdge.objects.create(
                process=process,
                from_step=a,
                to_step=b,
                edge_type='DEFAULT',
            )
        return process, steps

    def _make_wo(self, process):
        return WorkOrder.objects.create(
            ERP_id="WO-CORE-001",
            workorder_status=WorkOrderStatus.IN_PROGRESS,
            process=process,
            quantity=1,
            tenant=self.tenant,
        )

    def _make_core(self, work_order=None, step=None, status='RECEIVED', number="CORE-1"):
        return Core.objects.create(
            tenant=self.tenant,
            core_number=number,
            core_type=self.core_type,
            received_date=date.today(),
            received_by=self.user,
            condition_grade='B',
            status=status,
            work_order=work_order,
            step=step,
        )


class CoreAdvanceStepTests(_RemanDwiBase):
    def test_advance_through_multi_step_process(self):
        process, steps = self._make_process([
            ("Inspect", False),
            ("Disassemble", False),
            ("Final Check", True),
        ])
        wo = self._make_wo(process)
        core = self._make_core(work_order=wo, step=steps[0])
        StepExecution.objects.create(
            core=core, step=steps[0], status='IN_PROGRESS', tenant=self.tenant,
        )

        result = advance_core_step(core, operator=self.user)
        self.assertEqual(result, "advanced")
        core.refresh_from_db()
        self.assertEqual(core.step, steps[1])

        result = advance_core_step(core, operator=self.user)
        self.assertEqual(result, "advanced")
        core.refresh_from_db()
        self.assertEqual(core.step, steps[2])

    def test_terminal_step_triggers_complete_disassembly(self):
        process, steps = self._make_process([
            ("Disassemble", False),
            ("Final", True),
        ])
        wo = self._make_wo(process)
        core = self._make_core(work_order=wo, step=steps[1], status='IN_DISASSEMBLY')
        StepExecution.objects.create(
            core=core, step=steps[1], status='IN_PROGRESS', tenant=self.tenant,
        )

        result = advance_core_step(core, operator=self.user)
        self.assertEqual(result, "completed")
        core.refresh_from_db()
        self.assertEqual(core.status, 'DISASSEMBLED')
        self.assertIsNotNone(core.disassembly_completed_at)
        self.assertEqual(core.disassembled_by, self.user)

    def test_begin_step_execution_auto_starts_disassembly(self):
        process, steps = self._make_process([("Inspect", False)])
        wo = self._make_wo(process)
        core = self._make_core(work_order=wo, step=steps[0], status='RECEIVED')
        execution = StepExecution.objects.create(
            core=core, step=steps[0], status='PENDING', tenant=self.tenant,
        )

        begin_core_step_execution(execution, operator=self.user)

        core.refresh_from_db()
        self.assertEqual(core.status, 'IN_DISASSEMBLY')
        self.assertIsNotNone(core.disassembly_started_at)
        execution.refresh_from_db()
        self.assertEqual(execution.status, 'IN_PROGRESS')

    def test_begin_step_execution_idempotent(self):
        process, steps = self._make_process([("Inspect", False)])
        wo = self._make_wo(process)
        core = self._make_core(work_order=wo, step=steps[0], status='IN_DISASSEMBLY')
        execution = StepExecution.objects.create(
            core=core, step=steps[0], status='IN_PROGRESS', tenant=self.tenant,
        )

        # Second call is a no-op; status stays IN_DISASSEMBLY (not double-started).
        begin_core_step_execution(execution, operator=self.user)
        core.refresh_from_db()
        self.assertEqual(core.status, 'IN_DISASSEMBLY')


class WorkOrderCascadeTests(_RemanDwiBase):
    def test_cores_only_wo_completes_when_all_disassembled(self):
        process, steps = self._make_process([("Final", True)])
        wo = self._make_wo(process)
        core_a = self._make_core(work_order=wo, step=steps[0],
                                 status='IN_DISASSEMBLY', number="CORE-A")
        core_b = self._make_core(work_order=wo, step=steps[0],
                                 status='IN_DISASSEMBLY', number="CORE-B")
        StepExecution.objects.create(core=core_a, step=steps[0],
                                     status='IN_PROGRESS', tenant=self.tenant)
        StepExecution.objects.create(core=core_b, step=steps[0],
                                     status='IN_PROGRESS', tenant=self.tenant)

        # Complete only core A — WO should NOT complete yet.
        advance_core_step(core_a, operator=self.user)
        wo.refresh_from_db()
        self.assertEqual(wo.workorder_status, WorkOrderStatus.IN_PROGRESS)

        # Complete core B — WO should now complete.
        advance_core_step(core_b, operator=self.user)
        wo.refresh_from_db()
        self.assertEqual(wo.workorder_status, WorkOrderStatus.COMPLETED)

    def test_cores_only_wo_cancels_when_all_scrapped(self):
        from Tracker.services.reman.core import scrap_core
        from Tracker.services.mes.parts import _cascade_work_order_completion_for_subject

        process, steps = self._make_process([("Final", True)])
        wo = self._make_wo(process)
        core_a = self._make_core(work_order=wo, step=steps[0], number="CORE-A")
        core_b = self._make_core(work_order=wo, step=steps[0], number="CORE-B")

        scrap_core(core_a, reason="cracked housing")
        scrap_core(core_b, reason="cracked housing")
        _cascade_work_order_completion_for_subject(wo)

        wo.refresh_from_db()
        self.assertEqual(wo.workorder_status, WorkOrderStatus.CANCELLED)

    def test_mixed_wo_waits_for_parts_and_cores(self):
        """A WO with both Parts and Cores requires every subject in terminal state."""
        from Tracker.models import Parts, PartsStatus, Orders
        from Tracker.services.reman.core import complete_core_disassembly
        from Tracker.services.mes.parts import _cascade_work_order_completion_for_subject

        process, steps = self._make_process([("Op", True)])

        order = Orders.objects.create(
            name="O-1", company=self.customer, tenant=self.tenant,
        )
        wo = WorkOrder.objects.create(
            ERP_id="WO-MIX-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS,
            process=process,
            related_order=order,
            quantity=1,
            tenant=self.tenant,
        )
        part = Parts.objects.create(
            ERP_id="P-1",
            work_order=wo,
            part_type=self.core_type,
            step=steps[0],
            part_status=PartsStatus.IN_PROGRESS,
            tenant=self.tenant,
        )
        core = self._make_core(
            work_order=wo, step=steps[0], status='IN_DISASSEMBLY', number="CORE-MIX",
        )

        # Complete the core but leave the part active: WO should NOT complete.
        complete_core_disassembly(core, self.user)
        _cascade_work_order_completion_for_subject(wo)
        wo.refresh_from_db()
        self.assertEqual(wo.workorder_status, WorkOrderStatus.IN_PROGRESS)

        # Complete the part: WO should now complete.
        part.part_status = PartsStatus.COMPLETED
        part.save()
        _cascade_work_order_completion_for_subject(wo)
        wo.refresh_from_db()
        self.assertEqual(wo.workorder_status, WorkOrderStatus.COMPLETED)


class HarvestedComponentCaptureTests(_RemanDwiBase):
    """R4 — backend service that bridges DWI substep submits to HC rows."""

    def _setup_core_at_step(self):
        from Tracker.models import Substep
        process, steps = self._make_process([("Inspect", False)])
        wo = self._make_wo(process)
        core = self._make_core(work_order=wo, step=steps[0], status='IN_DISASSEMBLY')
        execution = StepExecution.objects.create(
            core=core, step=steps[0], status='IN_PROGRESS', tenant=self.tenant,
        )
        substep = Substep.objects.create(
            step=steps[0],
            title="Capture components",
            order=1,
            tenant=self.tenant,
        )
        return core, execution, substep

    def _component_type(self, name="Nozzle"):
        return PartTypes.objects.create(
            name=name, ID_prefix=name[:3].upper(), tenant=self.tenant,
        )

    def test_creates_one_hc_per_row(self):
        from Tracker.models import HarvestedComponent
        from Tracker.services.dwi.harvested_component_capture import (
            create_harvested_components_from_capture,
        )

        _, execution, substep = self._setup_core_at_step()
        nozzle = self._component_type("Nozzle")

        result = create_harvested_components_from_capture(
            step_execution=execution,
            substep=substep,
            rows=[
                {"component_type_id": str(nozzle.id), "condition_grade": "A",
                 "position": "Cyl 1"},
                {"component_type_id": str(nozzle.id), "condition_grade": "B",
                 "position": "Cyl 2", "condition_notes": "minor wear"},
            ],
            user=self.user,
        )
        self.assertEqual(len(result["harvested_component_ids"]), 2)
        self.assertEqual(result["missing_component_type_ids"], [])
        self.assertEqual(HarvestedComponent.objects.count(), 2)

    def test_scrap_grade_dispatches_scrap_component(self):
        from Tracker.models import HarvestedComponent
        from Tracker.services.dwi.harvested_component_capture import (
            create_harvested_components_from_capture,
        )

        _, execution, substep = self._setup_core_at_step()
        nozzle = self._component_type("Nozzle")

        result = create_harvested_components_from_capture(
            step_execution=execution,
            substep=substep,
            rows=[{"component_type_id": str(nozzle.id), "condition_grade": "SCRAP",
                   "condition_notes": "cracked tip"}],
            user=self.user,
        )
        hc = HarvestedComponent.objects.get(id=result["harvested_component_ids"][0])
        self.assertTrue(hc.is_scrapped)
        self.assertEqual(hc.scrap_reason, "cracked tip")
        self.assertIsNotNone(hc.scrapped_at)
        self.assertEqual(hc.scrapped_by, self.user)

    def test_missing_rows_skipped_and_reported(self):
        from Tracker.models import HarvestedComponent
        from Tracker.services.dwi.harvested_component_capture import (
            create_harvested_components_from_capture,
        )

        _, execution, substep = self._setup_core_at_step()
        nozzle = self._component_type("Nozzle")

        result = create_harvested_components_from_capture(
            step_execution=execution,
            substep=substep,
            rows=[
                {"component_type_id": str(nozzle.id), "condition_grade": "A"},
                {"component_type_id": str(nozzle.id), "is_missing": True},
            ],
            user=self.user,
        )
        self.assertEqual(len(result["harvested_component_ids"]), 1)
        self.assertEqual(result["missing_component_type_ids"], [str(nozzle.id)])
        self.assertEqual(HarvestedComponent.objects.count(), 1)

    def test_invalid_grade_rolls_back_all_rows(self):
        from Tracker.models import HarvestedComponent
        from Tracker.services.dwi.harvested_component_capture import (
            create_harvested_components_from_capture,
        )

        _, execution, substep = self._setup_core_at_step()
        nozzle = self._component_type("Nozzle")

        with self.assertRaises(ValueError):
            create_harvested_components_from_capture(
                step_execution=execution,
                substep=substep,
                rows=[
                    {"component_type_id": str(nozzle.id), "condition_grade": "A"},
                    {"component_type_id": str(nozzle.id), "condition_grade": "BOGUS"},
                ],
                user=self.user,
            )
        self.assertEqual(HarvestedComponent.objects.count(), 0)

    def test_refuses_part_scoped_step_execution(self):
        from Tracker.models import Parts, PartsStatus, Substep
        from Tracker.services.dwi.harvested_component_capture import (
            create_harvested_components_from_capture,
        )

        process, steps = self._make_process([("Op", False)])
        wo = self._make_wo(process)
        part = Parts.objects.create(
            ERP_id="P-CAP-1", work_order=wo, part_type=self.core_type,
            step=steps[0], part_status=PartsStatus.IN_PROGRESS, tenant=self.tenant,
        )
        execution = StepExecution.objects.create(
            part=part, step=steps[0], status='IN_PROGRESS', tenant=self.tenant,
        )
        substep = Substep.objects.create(
            step=steps[0], title="Capture", order=1, tenant=self.tenant,
        )

        with self.assertRaises(ValueError):
            create_harvested_components_from_capture(
                step_execution=execution,
                substep=substep,
                rows=[],
                user=self.user,
            )
