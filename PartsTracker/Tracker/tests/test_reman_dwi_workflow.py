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
    PartsStatus,
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
        self.assertEqual(core.part.step, steps[1])

        self.assertEqual(advance_part_step(core.part, operator=self.user), "advanced")
        core.refresh_from_db()
        self.assertEqual(core.part.step, steps[2])

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

    def test_an_ordinary_part_ended_by_its_route_closes_its_order(self):
        """An ordinary part ends at any status its route can end in. This used to pin
        SHIPPED as NOT ending — but only because a 'SHIPPED' terminal step never
        produced SHIPPED (the terminal-status map was keyed lower-case, so every route
        ended COMPLETED). With that fixed (2026-10-05, customer shipping), a route
        ending at its Ship step ends SHIPPED, and an order whose units all shipped is
        done — as it was in practice. A unit still in work keeps it open."""
        from Tracker.models import Parts, PartsStatus
        from Tracker.services.mes.parts import _cascade_work_order_completion_for_subject
        process, steps = self._make_process([("Op", True)])
        wo = self._make_wo(process)
        Parts.objects.create(ERP_id="P-SHIP", work_order=wo, part_type=self.core_type,
                             step=steps[0], part_status=PartsStatus.SHIPPED,
                             tenant=self.tenant)
        busy = Parts.objects.create(ERP_id="P-BUSY", work_order=wo, part_type=self.core_type,
                                    step=steps[0], part_status=PartsStatus.IN_PROGRESS,
                                    tenant=self.tenant)
        _cascade_work_order_completion_for_subject(wo)
        wo.refresh_from_db()
        self.assertEqual(wo.workorder_status, WorkOrderStatus.IN_PROGRESS)
        busy.part_status = PartsStatus.IN_STOCK
        busy.save(update_fields=["part_status"])
        _cascade_work_order_completion_for_subject(wo)
        wo.refresh_from_db()
        self.assertEqual(wo.workorder_status, WorkOrderStatus.COMPLETED)

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


class StrictHarvestIsEnforcedOnTheServerTests(_RemanDwiBase):
    """Strict teardown capture: every component the unit is EXPECTED to give up — its
    core type's disassembly BOM, per position — must be graded or marked missing.

    The client sends only the rows the operator recorded, so only the server can
    compare them with what was expected; this is the authoritative check.
    """

    def setUp(self):
        super().setUp()
        from Tracker.models import DisassemblyBOMLine, Substep
        process, steps = self._make_process([("Strip", False)])
        wo = self._make_wo(process)
        self.core = self._make_core(work_order=wo, step=steps[0], status='IN_DISASSEMBLY')
        self.execution = StepExecution.objects.create(
            part=self.core.part, step=steps[0], status='IN_PROGRESS', tenant=self.tenant)
        self.substep = Substep.objects.create(step=steps[0], title="Capture", order=1,
                                              tenant=self.tenant)
        self.nozzle = PartTypes.objects.create(name="Nozzle", ID_prefix="NZL",
                                               tenant=self.tenant)
        DisassemblyBOMLine.objects.create(
            tenant=self.tenant, core_type=self.core_type, component_type=self.nozzle,
            expected_qty=2, positions=["Cyl 1", "Cyl 2"])
        self.substep.body_blocks = {"type": "doc", "content": [{
            "type": "harvestedComponentCapture",
            "attrs": {"node_id": "hc-1", "strict_enumeration": True, "required": False},
        }]}
        self.substep.save(update_fields=["body_blocks"])

    def _missing(self, rows):
        from Tracker.services.dwi.operator_capture import find_missing_required
        return find_missing_required(
            self.substep, [{"node_id": "hc-1", "kind": "harvested_components", "rows": rows}],
            step_execution=self.execution)

    def _row(self, position, **extra):
        return {"component_type_id": str(self.nozzle.id), "position": position, **extra}

    def test_every_expected_position_recorded_passes(self):
        self.assertEqual(self._missing([
            self._row("Cyl 1", condition_grade="A"),
            self._row("Cyl 2", is_missing=True),
        ]), [])

    def test_a_position_left_out_is_refused(self):
        missing = self._missing([self._row("Cyl 1", condition_grade="A")])
        self.assertEqual(len(missing), 1)
        self.assertIn("1 expected component", missing[0]["reason"])

    def test_it_binds_even_when_the_node_is_not_required(self):
        """Strict is its own requirement: a partial record is not allowed even on an
        optional node."""
        self.assertTrue(self._missing([]))


    def _submit(self, rows):
        from Tracker.services.dwi.operator_capture import submit_substep
        return submit_substep(
            substep=self.substep, step_execution=self.execution, user=self.user,
            captures=[{"node_id": "hc-1", "kind": "harvested_components", "rows": rows}])

    def test_resubmitting_the_same_teardown_records_it_once(self):
        """The runtime reseeds a resumed substep from what was stored, so a resubmit
        is a replay — it must not record every component a second time."""
        from Tracker.models import HarvestedComponent
        rows = [self._row("Cyl 1", condition_grade="A"), self._row("Cyl 2", condition_grade="B")]
        self._submit(rows)
        self._submit(rows)
        self.assertEqual(HarvestedComponent.objects.filter(core=self.core).count(), 2)

    def test_resubmitting_different_rows_is_refused(self):
        from django.core.exceptions import ValidationError
        from Tracker.models import HarvestedComponent
        self._submit([self._row("Cyl 1", condition_grade="A"), self._row("Cyl 2", is_missing=True)])
        with self.assertRaises(ValidationError):
            self._submit([self._row("Cyl 1", condition_grade="C"), self._row("Cyl 2", is_missing=True)])
        self.assertEqual(
            list(HarvestedComponent.objects.filter(core=self.core).values_list("condition_grade", flat=True)),
            ["A"])

    def test_a_resumed_teardown_shows_what_was_recorded(self):
        from Tracker.services.dwi.operator_capture import build_capture_state
        rows = [self._row("Cyl 1", condition_grade="A"), self._row("Cyl 2", is_missing=True)]
        self._submit(rows)
        state = build_capture_state(self.execution)
        self.assertEqual(state[str(self.substep.id)]["hc-1"], {"rows": rows})


class ComponentInstallCaptureTests(_RemanDwiBase):
    """The rebuild half: what went into each slot, recorded through install_component."""

    def setUp(self):
        super().setUp()
        from Tracker.models import HarvestedComponent, Substep
        process, steps = self._make_process([("Assemble", False)])
        wo = self._make_wo(process)
        self.core = self._make_core(work_order=wo, step=steps[0], status='IN_REBUILD')
        self.execution = StepExecution.objects.create(
            part=self.core.part, step=steps[0], status='IN_PROGRESS', tenant=self.tenant)
        self.substep = Substep.objects.create(step=steps[0], title="Fit", order=1,
                                              tenant=self.tenant)
        nozzle = PartTypes.objects.create(name="Nozzle", ID_prefix="NZL", tenant=self.tenant)
        self.own = HarvestedComponent.objects.create(
            tenant=self.tenant, core=self.core, component_type=nozzle,
            condition_grade="A", disassembled_by=self.user)

    def _install(self, rows):
        from Tracker.services.dwi.component_install_capture import install_components_from_capture
        return install_components_from_capture(
            step_execution=self.execution, substep=self.substep, rows=rows, user=self.user)

    def test_the_units_own_component_goes_back_into_its_part(self):
        from Tracker.models import AssemblyUsage
        result = self._install([{"harvested_id": str(self.own.id), "position": "Cyl 1"}])
        usage = AssemblyUsage.objects.get(id=result["assembly_usage_ids"][0])
        self.assertEqual(usage.assembly_id, self.core.part_id)
        self.assertEqual(usage.component_harvested_id, self.own.id)
        self.assertEqual(usage.step_id, self.execution.step_id)

    def test_a_row_must_name_exactly_one_source(self):
        with self.assertRaises(ValueError):
            self._install([{"position": "Cyl 1"}])
        with self.assertRaises(ValueError):
            self._install([{"harvested_id": str(self.own.id), "part_id": str(self.own.id)}])

    def test_another_cores_component_is_refused_and_nothing_is_written(self):
        """The install rules live in install_component; a slot it refuses fails the
        whole capture rather than leaving the unit half-recorded."""
        from Tracker.models import AssemblyUsage, HarvestedComponent
        other = self._make_core(status='DISASSEMBLED', number="CORE-OTHER")
        theirs = HarvestedComponent.objects.create(
            tenant=self.tenant, core=other, component_type=self.own.component_type,
            condition_grade="A", disassembled_by=self.user)
        with self.assertRaises(ValueError):
            self._install([
                {"harvested_id": str(self.own.id)},
                {"harvested_id": str(theirs.id)},
            ])
        self.assertEqual(AssemblyUsage.objects.filter(assembly=self.core.part).count(), 0)

    def test_it_refuses_a_step_that_is_not_on_a_core(self):
        from Tracker.models import Parts, PartsStatus
        part = Parts.objects.create(tenant=self.tenant, ERP_id="P-X", part_type=self.core_type,
                                    part_status=PartsStatus.IN_PROGRESS)
        plain = StepExecution.objects.create(part=part, step=self.execution.step,
                                             status='IN_PROGRESS', tenant=self.tenant)
        from Tracker.services.dwi.component_install_capture import install_components_from_capture
        with self.assertRaises(ValueError):
            install_components_from_capture(step_execution=plain, substep=self.substep,
                                            rows=[{"harvested_id": str(self.own.id)}],
                                            user=self.user)

    def test_the_part_api_says_which_core_role_a_part_plays(self):
        """The runtime reaches the unit's rebuild plan through this."""
        from Tracker.serializers.mes_lite import PartsSerializer
        self.assertEqual(PartsSerializer(self.core.part).data["core_role"], self.core.id)
        from Tracker.models import Parts
        plain = Parts.objects.create(tenant=self.tenant, ERP_id="P-PLAIN", part_type=self.core_type)
        self.assertIsNone(PartsSerializer(plain).data["core_role"])

    def test_resubmitting_the_same_install_fits_it_once(self):
        from Tracker.models import AssemblyUsage
        from Tracker.services.dwi.operator_capture import submit_substep
        self.substep.body_blocks = {"type": "doc", "content": [{
            "type": "componentInstallCapture", "attrs": {"node_id": "ci-1", "required": True}}]}
        self.substep.save(update_fields=["body_blocks"])
        cap = {"node_id": "ci-1", "kind": "component_install",
               "rows": [{"harvested_id": str(self.own.id), "position": "Cyl 1"}]}
        for _ in range(2):
            submit_substep(substep=self.substep, step_execution=self.execution,
                           user=self.user, captures=[cap])
        self.assertEqual(AssemblyUsage.objects.filter(assembly=self.core.part).count(), 1)


class GenericPartServicesFollowTheStageTests(_RemanDwiBase):
    """A core's part status is DERIVED from its reman stage. Generic part services that
    write a status directly — bulk set, lot split, quantity reduction, rework split,
    make-up, rollback, the parts API — must move the stage instead, or refuse."""

    def setUp(self):
        super().setUp()
        self.process, self.steps = self._make_process([("Strip", False), ("Clean", False)])
        self.wo = self._make_wo(self.process)

    def _core(self, status='IN_DISASSEMBLY', number="CORE-G1", **kw):
        kw.setdefault('work_order', self.wo)
        kw.setdefault('step', self.steps[0])
        return self._make_core(status=status, number=number, **kw)

    def _reload(self, core):
        core.refresh_from_db()
        core.part.refresh_from_db()
        return core

    # --- bulk set status ---------------------------------------------------------------

    def test_bulk_scrap_scraps_the_core(self):
        from Tracker.services.mes.parts import bulk_set_status
        core = self._core()
        [r] = bulk_set_status(self.tenant.id, [core.part_id], PartsStatus.SCRAPPED, self.user)
        self.assertTrue(r.ok, r.error)
        core = self._reload(core)
        self.assertEqual(core.status, 'SCRAPPED')
        self.assertEqual(core.part.part_status, PartsStatus.SCRAPPED)

    def test_bulk_completing_a_core_is_refused(self):
        from Tracker.services.mes.parts import bulk_set_status
        core = self._core()
        [r] = bulk_set_status(self.tenant.id, [core.part_id], PartsStatus.COMPLETED, self.user)
        self.assertFalse(r.ok)
        self.assertIn("reman stage", r.error)
        self.assertEqual(self._reload(core).part.part_status, PartsStatus.IN_PROGRESS)

    def test_bulk_reopening_an_ended_core_is_refused_even_when_elevated(self):
        from Tracker.services.mes.parts import bulk_set_status
        core = self._core(status='HARVESTED', number="CORE-G2")
        [r] = bulk_set_status(self.tenant.id, [core.part_id], PartsStatus.IN_PROGRESS,
                              self.user, allow_terminal_exit=True)
        self.assertFalse(r.ok)
        self.assertEqual(self._reload(core).part.part_status, PartsStatus.DISMANTLED)

    def test_bulk_quarantine_is_allowed_like_any_part(self):
        from Tracker.services.mes.parts import bulk_set_status
        core = self._core()
        [r] = bulk_set_status(self.tenant.id, [core.part_id], PartsStatus.QUARANTINED, self.user)
        self.assertTrue(r.ok, r.error)
        core = self._reload(core)
        self.assertEqual(core.part.part_status, PartsStatus.QUARANTINED)
        self.assertEqual(core.status, 'IN_DISASSEMBLY')

    # --- lot split, quantity, rework split, make-up, rollback -------------------------

    def test_a_scrap_split_scraps_the_core(self):
        from Tracker.models import PartSplitReason
        from Tracker.services.mes.splits import split_part_from_lot
        core = self._core()
        split_part_from_lot(part=core.part, reason=PartSplitReason.SCRAP, user=self.user)
        self.assertEqual(self._reload(core).status, 'SCRAPPED')

    def test_shrinking_a_teardown_order_banks_the_core_rather_than_cancelling_it(self):
        from Tracker.services.mes.work_order import reduce_work_order_quantity
        self._core(status='RECEIVED', number="CORE-G3")
        spare = self._core(status='RECEIVED', number="CORE-G4")
        self.wo.quantity = 2
        self.wo.save(update_fields=['quantity'])
        self.assertEqual(reduce_work_order_quantity(self.wo, 1, self.user), 1)
        spare = self._reload(spare)
        self.assertIsNone(spare.part.work_order_id)
        self.assertEqual(spare.status, 'RECEIVED')
        self.assertEqual(spare.part.part_status, PartsStatus.CORE_BANKED)

    def test_a_rework_split_of_a_core_is_refused(self):
        from Tracker.models import WorkOrderSplitReason
        from Tracker.services.mes.work_order import split_work_order
        core = self._core()
        with self.assertRaises(ValueError):
            split_work_order(self.wo, WorkOrderSplitReason.REWORK, self.user,
                             new_erp_id="WO-CORE-RW", part_ids=[core.part_id])
        self.assertEqual(self._reload(core).part.work_order_id, self.wo.id)

    def test_a_reman_order_owes_no_make_up(self):
        from Tracker.services.mes.makeup import work_order_shortfall
        self._core(status='SCRAPPED', number="CORE-G5")
        self.wo.quantity = 1
        self.wo.save(update_fields=['quantity'])
        self.assertEqual(work_order_shortfall(self.wo)['shortfall'], 0)

    def test_rollback_past_the_end_of_a_teardown_is_refused(self):
        from Tracker.services.mes.parts import rollback_part_step
        core = self._core(status='DISASSEMBLED', number="CORE-G6")
        with self.assertRaisesRegex(ValueError, "teardown or rebuild is under way"):
            rollback_part_step(core.part, operator=self.user, reason="operator mis-scan")

    # --- the parts API -------------------------------------------------------------------

    def _patch(self, core, **data):
        from Tracker.serializers.mes_lite import PartsSerializer
        return PartsSerializer(core.part, data=data, partial=True)

    def test_the_parts_api_refuses_to_scrap_or_move_a_core_part(self):
        core = self._core()
        s = self._patch(core, part_status=PartsStatus.SCRAPPED)
        self.assertFalse(s.is_valid())
        self.assertIn('part_status', s.errors)
        other = WorkOrder.objects.create(
            ERP_id="WO-CORE-002", workorder_status=WorkOrderStatus.IN_PROGRESS,
            process=self.process, quantity=1, tenant=self.tenant)
        s = self._patch(core, work_order=str(other.id))
        self.assertFalse(s.is_valid())
        self.assertIn('work_order', s.errors)

    def test_the_parts_api_allows_a_hold_on_a_core_part(self):
        core = self._core()
        s = self._patch(core, part_status=PartsStatus.QUARANTINED)
        self.assertTrue(s.is_valid(), s.errors)


class HarvestedCoreCountsAsDoneOnProgressTests(_RemanDwiBase):
    """A teardown order's job is to take its units apart, so a harvested (DISMANTLED)
    core is done on the order's progress — though never counted as produced."""

    def test_an_order_of_harvested_cores_reads_complete(self):
        from Tracker.models import Orders, OrdersStatus
        from Tracker.serializers.mes_lite import CustomerOrderSerializer, OrdersSerializer
        order = Orders.objects.create(tenant=self.tenant, name="ORD-TEAR",
                                      company=self.customer,
                                      order_status=OrdersStatus.IN_PROGRESS)
        for n in ("CORE-H1", "CORE-H2"):
            core = self._make_core(status='HARVESTED', number=n)
            core.part.order = order
            core.part.save(update_fields=['order'])
        self.assertEqual(OrdersSerializer(order).data['parts_summary']['completed_parts'], 2)
        summary = CustomerOrderSerializer(order).data['parts_summary']
        self.assertEqual((summary['completed_parts'], summary['progress_percent']), (2, 100.0))


class RebuildFindingsAreProposedThenDecidedTests(_RemanDwiBase):
    """A component found worse after teardown: the operator records it, a lead decides.
    Nothing about the grade — and so the scope — changes until someone applies it."""

    def setUp(self):
        super().setUp()
        from Tracker.models import HarvestedComponent, Substep
        process, steps = self._make_process([("Assemble", False)])
        self.core = self._make_core(work_order=self._make_wo(process), step=steps[0],
                                    status='IN_REBUILD')
        self.execution = StepExecution.objects.create(
            part=self.core.part, step=steps[0], status='IN_PROGRESS', tenant=self.tenant)
        self.substep = Substep.objects.create(step=steps[0], title="Test", order=1,
                                              tenant=self.tenant)
        self.nozzle = HarvestedComponent.objects.create(
            tenant=self.tenant, core=self.core, disassembled_by=self.user, condition_grade="A",
            component_type=PartTypes.objects.create(name="Nozzle", ID_prefix="NZL",
                                                    tenant=self.tenant))

    def _record(self, grade="C", finding="Spray pattern out of limits on bench test"):
        from Tracker.services.reman.findings import record_finding
        return record_finding(self.nozzle, grade=grade, finding=finding, user=self.user)

    def test_recording_proposes_and_changes_nothing(self):
        self._record()
        self.nozzle.refresh_from_db()
        self.assertEqual((self.nozzle.condition_grade, self.nozzle.proposed_grade), ("A", "C"))

    def test_one_pending_finding_at_a_time_and_it_must_differ(self):
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self._record(grade="A")
        self._record()
        with self.assertRaises(ValidationError):
            self._record(grade="SCRAP")

    def test_applying_regrades_and_keeps_the_story(self):
        from Tracker.services.reman.findings import apply_finding
        self._record()
        apply_finding(self.nozzle, user=self.user)
        self.nozzle.refresh_from_db()
        self.assertEqual((self.nozzle.condition_grade, self.nozzle.proposed_grade), ("C", ""))
        self.assertIn("A → C", self.nozzle.condition_notes)
        self.assertIn("Spray pattern", self.nozzle.condition_notes)

    def test_applying_a_scrap_finding_scraps_the_component(self):
        from Tracker.services.reman.findings import apply_finding
        self._record(grade="SCRAP", finding="Cracked tip")
        apply_finding(self.nozzle, user=self.user)
        self.nozzle.refresh_from_db()
        self.assertTrue(self.nozzle.is_scrapped)

    def test_dismissing_needs_a_reason_and_keeps_the_grade(self):
        from django.core.exceptions import ValidationError
        from Tracker.services.reman.findings import dismiss_finding
        self._record()
        with self.assertRaises(ValidationError):
            dismiss_finding(self.nozzle, user=self.user, reason=" ")
        dismiss_finding(self.nozzle, user=self.user, reason="Rig out of calibration; retested OK")
        self.nozzle.refresh_from_db()
        self.assertEqual((self.nozzle.condition_grade, self.nozzle.proposed_grade), ("A", ""))
        self.assertIn("retested OK", self.nozzle.condition_notes)

    def test_the_dwi_capture_records_proposals_on_this_units_components_only(self):
        from django.core.exceptions import ValidationError
        from Tracker.models import HarvestedComponent
        from Tracker.services.dwi.operator_capture import submit_substep
        self.substep.body_blocks = {"type": "doc", "content": [{
            "type": "rebuildFindingCapture", "attrs": {"node_id": "rf-1", "required": False}}]}
        self.substep.save(update_fields=["body_blocks"])
        other = self._make_core(status='DISASSEMBLED', number="CORE-OTHER")
        theirs = HarvestedComponent.objects.create(
            tenant=self.tenant, core=other, component_type=self.nozzle.component_type,
            condition_grade="A", disassembled_by=self.user)

        def submit(rows):
            return submit_substep(substep=self.substep, step_execution=self.execution,
                                  user=self.user, captures=[{
                                      "node_id": "rf-1", "kind": "rebuild_finding", "rows": rows}])
        with self.assertRaises(ValidationError):
            submit([{"harvested_id": str(theirs.id), "grade": "C", "finding": "x"}])
        submit([{"harvested_id": str(self.nozzle.id), "grade": "C", "finding": "Worn seat"}])
        self.nozzle.refresh_from_db()
        self.assertEqual((self.nozzle.condition_grade, self.nozzle.proposed_grade), ("A", "C"))


class AParkedUnitIsNotWorkedTests(_RemanDwiBase):
    """A unit a lead sent for the customer's authorisation waits for their answer:
    nothing is started, captured or advanced on it — and no supervisor can wave it on."""

    def setUp(self):
        super().setUp()
        from Tracker.models import Substep
        process, self.steps = self._make_process([("Assemble", False), ("Test", False)])
        self.core = self._make_core(work_order=self._make_wo(process), step=self.steps[0],
                                    status='AWAITING_AUTHORISATION')
        self.execution = StepExecution.objects.create(
            part=self.core.part, step=self.steps[0], status='PENDING', tenant=self.tenant)
        self.substep = Substep.objects.create(step=self.steps[0], title="Fit", order=1,
                                              tenant=self.tenant)

    def test_a_step_cannot_be_started(self):
        from django.core.exceptions import ValidationError
        with self.assertRaisesRegex(ValidationError, "customer's authorisation"):
            start_execution(self.execution, self.user)

    def test_nothing_can_be_captured(self):
        from django.core.exceptions import ValidationError
        from Tracker.services.dwi.operator_capture import submit_substep
        with self.assertRaises(ValidationError):
            submit_substep(substep=self.substep, step_execution=self.execution,
                           user=self.user, captures=[])

    def test_it_does_not_advance(self):
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            advance_part_step(self.core.part, operator=self.user)

    def test_once_authorised_it_can_be_worked(self):
        from Tracker.services.reman.release import record_authorisation
        record_authorisation(self.core, approved=True, user=self.user)
        start_execution(self.execution, self.user)
        self.execution.refresh_from_db()
        self.assertEqual(self.execution.status, 'IN_PROGRESS')
