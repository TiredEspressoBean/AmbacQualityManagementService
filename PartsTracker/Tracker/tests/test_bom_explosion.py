"""BOM explosion → in-house component work orders (make-side, net-first).

`plan_work_order` auto-explodes an assembly's released BOM: each MAKE line becomes a child
WO pegged to the parent (WO + BOM line), netted first against on-hand stock and already-
pegged component WOs. Multi-level BOMs recurse. BUY lines are recorded, not built. The
CP-SAT solver turns the pegs into cross-WO precedence (tested separately).
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from Tracker.models import (
    BOM,
    BOMLine,
    Material,
    Parts,
    PartsStatus,
    PartTypes,
    Processes,
    ProcessStep,
    Steps,
    Tenant,
    WorkOrder,
)
from Tracker.services.mes.bom_explosion import explode_work_order_tx
from Tracker.services.mes.work_order import plan_work_order
from Tracker.tests.base import TenantContextMixin

User = get_user_model()


class BOMExplosionTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="BX", slug="bomx", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.user = User.objects.create_user(
            username="planner", email="p@c.test", password="x", tenant=self.tenant)

    # --- helpers -----------------------------------------------------------

    def _part_type(self, name):
        return PartTypes.objects.create(tenant=self.tenant, name=name)

    def _process_with_step(self, part_type, name, *, status='APPROVED'):
        """An APPROVED, current process with one step — enough to plan a WO against."""
        proc = Processes.objects.create(
            tenant=self.tenant, name=name, part_type=part_type,
            status=status, is_current_version=True, is_disassembly=False)
        step = Steps.objects.create(tenant=self.tenant, part_type=part_type, name=f"{name}-Op")
        ProcessStep.objects.create(process=proc, step=step, order=1)
        return proc, step

    def _released_bom(self, part_type, rev='A'):
        return BOM.objects.create(
            tenant=self.tenant, part_type=part_type, revision=rev,
            bom_type='ASSEMBLY', status='RELEASED', is_current_version=True)

    def _instock_parts(self, part_type, n):
        """Finished in-house stock of a component — Parts marked IN_STOCK (MAKE components
        are PartTypes, so their on-hand supply is Parts, not MaterialLots)."""
        for i in range(n):
            Parts.objects.create(
                tenant=self.tenant, ERP_id=f"{part_type.name}-STK-{i}", part_type=part_type,
                part_status=PartsStatus.IN_STOCK)

    # --- tests -------------------------------------------------------------

    def test_make_line_creates_pegged_child_wo(self):
        asm = self._part_type("Injector")
        comp = self._part_type("Nozzle")
        asm_proc, _ = self._process_with_step(asm, "Assemble")
        comp_proc, _ = self._process_with_step(comp, "MakeNozzle")
        bom = self._released_bom(asm)
        line = BOMLine.objects.create(
            tenant=self.tenant, bom=bom, component_type=comp,
            quantity=Decimal(2), source='MAKE', line_number=1)

        parent = plan_work_order(tenant=self.tenant, process=asm_proc, quantity=3, user=self.user)

        children = WorkOrder.objects.filter(pegged_to_workorder=parent)
        self.assertEqual(children.count(), 1)
        child = children.first()
        self.assertEqual(child.quantity, 6)            # 2 per assembly × 3
        self.assertEqual(child.process_id, comp_proc.id)
        self.assertEqual(child.pegged_to_bom_line_id, line.id)
        # summary attached to the returned parent WO
        self.assertEqual(parent.explosion_summary['created_count'], 1)

    def test_open_draft_revision_does_not_hide_released_bom(self):
        """Opening a draft revision flips the RELEASED BOM to is_current_version=False.
        The floor still builds to the released BOM until the draft is itself released, so
        explosion must keep finding it — a draft must not silently erase the production BOM."""
        from Tracker.services.mes.bom import create_new_bom_version

        asm = self._part_type("Injector")
        comp = self._part_type("Nozzle")
        asm_proc, _ = self._process_with_step(asm, "Assemble")
        self._process_with_step(comp, "MakeNozzle")
        bom = self._released_bom(asm)
        BOMLine.objects.create(
            tenant=self.tenant, bom=bom, component_type=comp,
            quantity=Decimal(2), source='MAKE', line_number=1)

        # Engineering starts drafting the next revision → released row goes non-current.
        draft = create_new_bom_version(bom, user=self.user, change_description="WIP rev")
        bom.refresh_from_db()
        self.assertFalse(bom.is_current_version)      # released row is no longer the chain head
        self.assertTrue(draft.is_current_version)     # the DRAFT is
        self.assertEqual(draft.status, 'DRAFT')

        # Explosion still nets against the released BOM and pegs the child.
        parent = plan_work_order(tenant=self.tenant, process=asm_proc, quantity=3, user=self.user)
        children = WorkOrder.objects.filter(pegged_to_workorder=parent)
        self.assertEqual(children.count(), 1)
        self.assertEqual(children.first().quantity, 6)   # 2 × 3 — proves the released BOM was used

    def test_multi_level_recursion(self):
        asm = self._part_type("Injector")
        comp = self._part_type("Nozzle")
        sub = self._part_type("Tip")
        asm_proc, _ = self._process_with_step(asm, "Assemble")
        comp_proc, _ = self._process_with_step(comp, "MakeNozzle")
        self._process_with_step(sub, "MakeTip")
        asm_bom = self._released_bom(asm)
        BOMLine.objects.create(tenant=self.tenant, bom=asm_bom, component_type=comp,
                               quantity=Decimal(1), source='MAKE', line_number=1)
        comp_bom = self._released_bom(comp)
        BOMLine.objects.create(tenant=self.tenant, bom=comp_bom, component_type=sub,
                               quantity=Decimal(2), source='MAKE', line_number=1)

        parent = plan_work_order(tenant=self.tenant, process=asm_proc, quantity=1, user=self.user)

        nozzle_wo = WorkOrder.objects.get(pegged_to_workorder=parent)
        tip_wo = WorkOrder.objects.get(pegged_to_workorder=nozzle_wo)
        self.assertEqual(nozzle_wo.quantity, 1)
        self.assertEqual(tip_wo.quantity, 2)
        self.assertEqual(parent.explosion_summary['created_count'], 2)

    def test_net_first_onhand_suppresses_creation(self):
        asm = self._part_type("Injector")
        comp = self._part_type("Nozzle")
        asm_proc, _ = self._process_with_step(asm, "Assemble")
        self._process_with_step(comp, "MakeNozzle")
        bom = self._released_bom(asm)
        BOMLine.objects.create(tenant=self.tenant, bom=bom, component_type=comp,
                               quantity=Decimal(2), source='MAKE', line_number=1)
        self._instock_parts(comp, 10)  # plenty finished on hand → no build needed

        parent = plan_work_order(tenant=self.tenant, process=asm_proc, quantity=3, user=self.user)

        self.assertFalse(WorkOrder.objects.filter(pegged_to_workorder=parent).exists())
        self.assertEqual(parent.explosion_summary['created_count'], 0)
        self.assertEqual(len(parent.explosion_summary['netted']), 1)

    def test_reexplode_is_idempotent(self):
        asm = self._part_type("Injector")
        comp = self._part_type("Nozzle")
        asm_proc, _ = self._process_with_step(asm, "Assemble")
        self._process_with_step(comp, "MakeNozzle")
        bom = self._released_bom(asm)
        BOMLine.objects.create(tenant=self.tenant, bom=bom, component_type=comp,
                               quantity=Decimal(1), source='MAKE', line_number=1)

        parent = plan_work_order(tenant=self.tenant, process=asm_proc, quantity=4, user=self.user)
        self.assertEqual(WorkOrder.objects.filter(pegged_to_workorder=parent).count(), 1)
        # re-explode → the already-pegged child covers the need, nothing new created
        result = explode_work_order_tx(parent, user=self.user, create=True)
        self.assertEqual(result.as_summary()['created_count'], 0)
        self.assertEqual(WorkOrder.objects.filter(pegged_to_workorder=parent).count(), 1)

    def test_buy_line_records_no_wo(self):
        asm = self._part_type("Injector")
        oring = Material.objects.create(tenant=self.tenant, name="O-Ring")
        asm_proc, _ = self._process_with_step(asm, "Assemble")
        bom = self._released_bom(asm)
        BOMLine.objects.create(tenant=self.tenant, bom=bom, material=oring,
                               quantity=Decimal(4), source='BUY', line_number=1)

        parent = plan_work_order(tenant=self.tenant, process=asm_proc, quantity=2, user=self.user)

        self.assertFalse(WorkOrder.objects.filter(pegged_to_workorder=parent).exists())
        self.assertEqual(len(parent.explosion_summary['buy']), 1)
        self.assertEqual(parent.explosion_summary['buy'][0]['required'], 8.0)

    def test_make_line_without_build_process_is_short(self):
        asm = self._part_type("Injector")
        comp = self._part_type("Nozzle")  # no process defined for it
        asm_proc, _ = self._process_with_step(asm, "Assemble")
        bom = self._released_bom(asm)
        BOMLine.objects.create(tenant=self.tenant, bom=bom, component_type=comp,
                               quantity=Decimal(1), source='MAKE', line_number=1)

        parent = plan_work_order(tenant=self.tenant, process=asm_proc, quantity=1, user=self.user)

        self.assertFalse(WorkOrder.objects.filter(pegged_to_workorder=parent).exists())
        self.assertEqual(len(parent.explosion_summary['short']), 1)

    def test_bomline_requires_exactly_one_component(self):
        """A BOM line is EITHER an in-house component_type OR a purchased material."""
        from django.db import IntegrityError, transaction
        asm = self._part_type("Injector")
        ct = self._part_type("Nozzle")
        mat = Material.objects.create(tenant=self.tenant, name="O-Ring")
        bom = self._released_bom(asm)
        with self.assertRaises(IntegrityError), transaction.atomic():
            BOMLine.objects.create(  # both set → violates the check constraint
                tenant=self.tenant, bom=bom, component_type=ct, material=mat,
                quantity=Decimal(1), source='MAKE', line_number=1)

    def test_no_bom_is_noop(self):
        asm = self._part_type("Widget")
        asm_proc, _ = self._process_with_step(asm, "MakeWidget")
        parent = plan_work_order(tenant=self.tenant, process=asm_proc, quantity=2, user=self.user)
        self.assertFalse(WorkOrder.objects.filter(pegged_to_workorder=parent).exists())
        self.assertEqual(parent.explosion_summary['created_count'], 0)
        # the parent itself still got its parts
        self.assertEqual(Parts.objects.filter(work_order=parent).count(), 2)

    def test_dry_run_creates_nothing(self):
        asm = self._part_type("Injector")
        comp = self._part_type("Nozzle")
        asm_proc, _ = self._process_with_step(asm, "Assemble")
        self._process_with_step(comp, "MakeNozzle")
        bom = self._released_bom(asm)
        BOMLine.objects.create(tenant=self.tenant, bom=bom, component_type=comp,
                               quantity=Decimal(1), source='MAKE', line_number=1)
        # plan WITHOUT auto-explode, then preview
        parent = plan_work_order(tenant=self.tenant, process=asm_proc, quantity=2,
                                 user=self.user, auto_explode=False)
        result = explode_work_order_tx(parent, user=self.user, create=False)
        self.assertEqual(result.as_summary()['created'][0]['work_order_id'], None)
        self.assertFalse(WorkOrder.objects.filter(pegged_to_workorder=parent).exists())
