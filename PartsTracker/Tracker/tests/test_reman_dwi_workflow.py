"""
Tests for Reman DWI integration — Phases R2 + R4.

R2 — a core is a PART (Documents/CORE_AS_PART_DESIGN.md), so it routes on the part
engine, `advance_part_step`, with reman hooks (services/reman/core_steps.py):
- the core's part walks the teardown process like any part
- the first step started (or completed) on a RECEIVED core starts teardown; reaching
  the end of the route completes it — DISASSEMBLED
- the work order closes only when every unit has actually ENDED. A disassembled core is
  waiting on a release decision (ON_HOLD), not finished.

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
from Tracker.services.mes.lifecycle import start_execution
from Tracker.services.mes.parts import advance_part_step
from Tracker.utils.tenant_context import (
    reset_current_tenant,
    set_current_tenant_id,
)
from Tracker.services.reman.core_part import create_core


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
        return create_core(
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
    """A core routes on the part engine — the one every part uses."""

    def test_advance_through_multi_step_process(self):
        process, steps = self._make_process([
            ("Inspect", False),
            ("Disassemble", False),
            ("Final Check", True),
        ])
        wo = self._make_wo(process)
        core = self._make_core(work_order=wo, step=steps[0])
        StepExecution.objects.create(
            part=core.part, step=steps[0], status='IN_PROGRESS', tenant=self.tenant,
        )

        self.assertEqual(advance_part_step(core.part, operator=self.user), "advanced")
        core.refresh_from_db()
        self.assertEqual(core.step, steps[1])

        self.assertEqual(advance_part_step(core.part, operator=self.user), "advanced")
        core.refresh_from_db()
        self.assertEqual(core.step, steps[2])

    def test_completing_the_first_step_starts_teardown(self):
        """A RECEIVED core whose first step completes without having been "started"
        still began its teardown — the engine's first hook."""
        process, steps = self._make_process([("Inspect", False), ("Final", True)])
        wo = self._make_wo(process)
        core = self._make_core(work_order=wo, step=steps[0], status='RECEIVED')
        advance_part_step(core.part, operator=self.user)
        core.refresh_from_db()
        self.assertEqual(core.status, 'IN_DISASSEMBLY')

    def test_the_end_of_the_route_completes_teardown(self):
        process, steps = self._make_process([
            ("Disassemble", False),
            ("Final", True),
        ])
        wo = self._make_wo(process)
        core = self._make_core(work_order=wo, step=steps[1], status='IN_DISASSEMBLY')
        StepExecution.objects.create(
            part=core.part, step=steps[1], status='IN_PROGRESS', tenant=self.tenant,
        )

        self.assertEqual(advance_part_step(core.part, operator=self.user), "completed")
        core.refresh_from_db()
        self.assertEqual(core.status, 'DISASSEMBLED')
        self.assertIsNotNone(core.disassembly_completed_at)
        self.assertEqual(core.disassembled_by, self.user)

    def test_a_disassembled_core_is_on_hold_not_finished(self):
        """Its part status comes from the stage, not the step's terminal status: the
        step says 'completed', but the unit is waiting on a release decision."""
        from Tracker.models import PartsStatus
        process, steps = self._make_process([("Final", True)])
        wo = self._make_wo(process)
        core = self._make_core(work_order=wo, step=steps[0], status='IN_DISASSEMBLY')
        advance_part_step(core.part, operator=self.user)
        core.part.refresh_from_db()
        self.assertEqual(core.part.part_status, PartsStatus.ON_HOLD)

    def test_starting_a_step_on_a_received_core_starts_teardown(self):
        process, steps = self._make_process([("Inspect", False)])
        wo = self._make_wo(process)
        core = self._make_core(work_order=wo, step=steps[0], status='RECEIVED')
        execution = StepExecution.objects.create(
            part=core.part, step=steps[0], status='PENDING', tenant=self.tenant,
        )

        start_execution(execution, self.user)

        core.refresh_from_db()
        self.assertEqual(core.status, 'IN_DISASSEMBLY')
        self.assertIsNotNone(core.disassembly_started_at)
        execution.refresh_from_db()
        self.assertEqual(execution.status, 'IN_PROGRESS')

    def test_starting_a_step_is_idempotent_for_teardown(self):
        process, steps = self._make_process([("Inspect", False)])
        wo = self._make_wo(process)
        core = self._make_core(work_order=wo, step=steps[0], status='IN_DISASSEMBLY')
        execution = StepExecution.objects.create(
            part=core.part, step=steps[0], status='PENDING', tenant=self.tenant,
        )
        start_execution(execution, self.user)
        core.refresh_from_db()
        self.assertEqual(core.status, 'IN_DISASSEMBLY')


class WorkOrderCascadeTests(_RemanDwiBase):
    """A work order closes when every unit has ENDED — and a core is a part, so there
    is one list of units to check."""

    def test_disassembly_alone_does_not_close_the_order(self):
        """This used to complete the order the moment its cores were DISASSEMBLED —
        closing a repair-and-return order before the rebuild it was opened for. A
        disassembled unit is waiting on a decision, not finished."""
        process, steps = self._make_process([("Final", True)])
        wo = self._make_wo(process)
        cores = [self._make_core(work_order=wo, step=steps[0], status='IN_DISASSEMBLY',
                                 number=n) for n in ("CORE-A", "CORE-B")]
        for core in cores:
            advance_part_step(core.part, operator=self.user)
        wo.refresh_from_db()
        self.assertEqual(wo.workorder_status, WorkOrderStatus.IN_PROGRESS)

    def test_the_order_closes_when_every_core_is_harvested(self):
        from Tracker.services.reman.release import release_core_to_inventory
        process, steps = self._make_process([("Final", True)])
        wo = self._make_wo(process)
        cores = [self._make_core(work_order=wo, step=steps[0], status='IN_DISASSEMBLY',
                                 number=n) for n in ("CORE-A", "CORE-B")]
        for core in cores:
            advance_part_step(core.part, operator=self.user)

        release_core_to_inventory(cores[0], self.user)
        wo.refresh_from_db()
        self.assertEqual(wo.workorder_status, WorkOrderStatus.IN_PROGRESS)

        cores[1].refresh_from_db()
        release_core_to_inventory(cores[1], self.user)
        wo.refresh_from_db()
        self.assertEqual(wo.workorder_status, WorkOrderStatus.COMPLETED)

    def test_cores_only_wo_cancels_when_all_scrapped(self):
        from Tracker.services.reman.core import scrap_core

        process, steps = self._make_process([("Final", True)])
        wo = self._make_wo(process)
        core_a = self._make_core(work_order=wo, step=steps[0], number="CORE-A")
        core_b = self._make_core(work_order=wo, step=steps[0], number="CORE-B")

        scrap_core(core_a, reason="cracked housing")
        scrap_core(core_b, reason="cracked housing")

        wo.refresh_from_db()
        self.assertEqual(wo.workorder_status, WorkOrderStatus.CANCELLED)

    def test_mixed_wo_waits_for_every_unit(self):
        """A WO with ordinary parts and cores closes only when every one has ended."""
        from Tracker.models import Parts, PartsStatus, Orders
        from Tracker.services.reman.release import release_core_to_inventory
        from Tracker.services.mes.parts import _cascade_work_order_completion_for_subject

        process, steps = self._make_process([("Op", True)])
        order = Orders.objects.create(name="O-1", company=self.customer, tenant=self.tenant)
        wo = WorkOrder.objects.create(
            ERP_id="WO-MIX-1", workorder_status=WorkOrderStatus.IN_PROGRESS,
            process=process, related_order=order, quantity=1, tenant=self.tenant,
        )
        part = Parts.objects.create(
            ERP_id="P-1", work_order=wo, part_type=self.core_type, step=steps[0],
            part_status=PartsStatus.IN_PROGRESS, tenant=self.tenant,
        )
        core = self._make_core(work_order=wo, step=steps[0], status='IN_DISASSEMBLY',
                               number="CORE-MIX")

        # The core ends (harvested); the part is still being worked.
        advance_part_step(core.part, operator=self.user)
        core.refresh_from_db()
        release_core_to_inventory(core, self.user)
        wo.refresh_from_db()
        self.assertEqual(wo.workorder_status, WorkOrderStatus.IN_PROGRESS)

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
            part=core.part, step=steps[0], status='IN_PROGRESS', tenant=self.tenant,
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


class WorkOrderCompletionIsJudgedRightTests(_RemanDwiBase):
    """What "ended" means, pinned case by case — including what must NOT change.

    An ordinary part has ended when its part status says so, exactly as before the
    core-as-part work. A core has ended when its reman stage says so: the work its order
    was opened for is done, or will not be done.
    """

    def _order_with(self, n, status='IN_DISASSEMBLY', mode='EXCHANGE'):
        process, steps = self._make_process([("Final", True)])
        wo = self._make_wo(process)
        cores = []
        for i in range(n):
            core = self._make_core(work_order=wo, step=steps[0], status=status,
                                   number=f"CORE-{i}")
            if mode != 'EXCHANGE':
                Core.objects.filter(pk=core.pk).update(fulfilment_mode=mode)
                core.refresh_from_db()
            cores.append(core)
        return wo, steps, cores

    def _set_stage(self, core, stage):
        from Tracker.services.reman.core_part import sync_part_status
        Core.objects.filter(pk=core.pk).update(status=stage)
        core.refresh_from_db()
        sync_part_status(core)

    def test_ordinary_parts_are_judged_exactly_as_before(self):
        """A part that ends SHIPPED (a 'shipped' terminal step) never closed its order
        before this work, and must not start to now: only COMPLETED, SCRAPPED and
        CANCELLED end an ordinary part."""
        from Tracker.models import Parts, PartsStatus
        from Tracker.services.mes.parts import _cascade_work_order_completion_for_subject
        process, steps = self._make_process([("Op", True)])
        wo = self._make_wo(process)
        Parts.objects.create(ERP_id="P-SHIP", work_order=wo, part_type=self.core_type,
                             step=steps[0], part_status=PartsStatus.SHIPPED,
                             tenant=self.tenant)
        _cascade_work_order_completion_for_subject(wo)
        wo.refresh_from_db()
        self.assertEqual(wo.workorder_status, WorkOrderStatus.IN_PROGRESS)

    def test_a_rebuilt_unit_ends_its_order_before_it_is_returned(self):
        """The work is done at REBUILT; sending it back is logistics after the work,
        as shipping a built part is."""
        wo, _, (core,) = self._order_with(1, status='IN_REBUILD', mode='REPAIR_RETURN')
        self._set_stage(core, 'REBUILT')
        wo.refresh_from_db()
        self.assertEqual(wo.workorder_status, WorkOrderStatus.COMPLETED)

    def test_returning_it_afterwards_does_not_move_the_completion_date(self):
        """The cascade runs again on the return. Re-closing a closed order would stamp
        the RETURN date as its completion date."""
        from datetime import timedelta
        wo, _, (core,) = self._order_with(1, status='IN_REBUILD', mode='REPAIR_RETURN')
        self._set_stage(core, 'REBUILT')
        earlier = date.today() - timedelta(days=5)
        WorkOrder.objects.filter(pk=wo.pk).update(true_completion=earlier)
        self._set_stage(core, 'RETURNED')
        wo.refresh_from_db()
        self.assertEqual(wo.workorder_status, WorkOrderStatus.COMPLETED)
        self.assertEqual(wo.true_completion, earlier)

    def test_a_declined_unit_ends_its_order(self):
        """No further work will be done on it; it only waits to go back."""
        wo, _, (core,) = self._order_with(1, status='AWAITING_AUTHORISATION',
                                          mode='REPAIR_RETURN')
        wo.refresh_from_db()
        self.assertEqual(wo.workorder_status, WorkOrderStatus.IN_PROGRESS)
        self._set_stage(core, 'DECLINED')
        wo.refresh_from_db()
        self.assertEqual(wo.workorder_status, WorkOrderStatus.COMPLETED)

    def _assert_stage_keeps_order_open(self, stage):
        wo, _, (core,) = self._order_with(1)
        self._set_stage(core, stage)
        wo.refresh_from_db()
        self.assertEqual(wo.workorder_status, WorkOrderStatus.IN_PROGRESS)

    def test_awaiting_a_release_decision_keeps_the_order_open(self):
        """An outstanding decision; an open order is how it stays visible."""
        self._assert_stage_keeps_order_open('DISASSEMBLED')

    def test_awaiting_customer_authorisation_keeps_the_order_open(self):
        self._assert_stage_keeps_order_open('AWAITING_AUTHORISATION')

    def test_a_qa_hold_survives_a_stage_change(self):
        """Quarantine is cleared by a disposition, never as a side effect of the unit
        moving on — the same rule the part engine applies to step transitions."""
        from Tracker.models import Parts, PartsStatus
        wo, _, (core,) = self._order_with(1)
        Parts.objects.filter(pk=core.part_id).update(part_status=PartsStatus.QUARANTINED)
        core.refresh_from_db()
        self._set_stage(core, 'DISASSEMBLED')
        core.part.refresh_from_db()
        self.assertEqual(core.part.part_status, PartsStatus.QUARANTINED)

    def test_but_an_ending_overrides_a_hold(self):
        from Tracker.models import Parts, PartsStatus
        wo, _, (core,) = self._order_with(1)
        Parts.objects.filter(pk=core.part_id).update(part_status=PartsStatus.QUARANTINED)
        core.refresh_from_db()
        self._set_stage(core, 'SCRAPPED')
        core.part.refresh_from_db()
        self.assertEqual(core.part.part_status, PartsStatus.SCRAPPED)
