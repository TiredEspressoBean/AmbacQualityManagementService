"""Sourcing & production requirements report (services/mes/requirements.py) — what open
demand needs to source (buy) or produce (make), with lead-time-driven order-by dates.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase

from Tracker.models import (
    BOM, BOMLine, Fixture, Material, PartTypes, Processes, Tenant, WorkOrder, WorkOrderStatus,
)
from Tracker.services.mes.requirements import (
    sourcing_requirements, work_order_material_requirements,
)
from Tracker.tests.base import TenantContextMixin


class SourcingRequirementsTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Req", slug="requirements", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.asm = PartTypes.objects.create(tenant=self.tenant, name="Injector")
        self.proc = Processes.objects.create(
            tenant=self.tenant, name="P", part_type=self.asm,
            status="APPROVED", is_current_version=True)
        self.bom = BOM.objects.create(
            tenant=self.tenant, part_type=self.asm, revision="A",
            bom_type="ASSEMBLY", status="RELEASED", is_current_version=True)

    def test_short_buy_material_appears_in_source_with_order_by(self):
        oring = Material.objects.create(
            tenant=self.tenant, name="O-Ring", purchase_lead_time_days=14)
        BOMLine.objects.create(
            tenant=self.tenant, bom=self.bom, material=oring, quantity=Decimal(2),
            source="BUY", line_number=1)
        need = date.today() + timedelta(days=30)
        WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-1", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=5, process=self.proc, expected_start=need)  # demand 10, none on hand

        req = sourcing_requirements(self.tenant)
        rows = [r for r in req['source'] if r['material'] == "O-Ring"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['qty_short'], 10)
        self.assertEqual(rows[0]['need_by'], need)
        self.assertEqual(rows[0]['order_by'], need - timedelta(days=14))

    def test_no_shortfall_when_covered(self):
        from datetime import date as _d
        from django.contrib.auth import get_user_model
        oring = Material.objects.create(tenant=self.tenant, name="Seal")
        BOMLine.objects.create(
            tenant=self.tenant, bom=self.bom, material=oring, quantity=Decimal(1),
            source="BUY", line_number=1)
        WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-2", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=3, process=self.proc)
        # 3 on hand covers demand of 3
        from Tracker.models import MaterialLot
        user = get_user_model().objects.create_user(
            username="r", email="r@c.test", password="x", tenant=self.tenant)
        MaterialLot.objects.create(
            tenant=self.tenant, lot_number="L1", material=oring, received_date=_d.today(),
            received_by=user, quantity=Decimal(3), quantity_remaining=Decimal(3),
            unit_of_measure="EA", status="ACCEPTED")
        req = sourcing_requirements(self.tenant)
        self.assertFalse(any(r['material'] == "Seal" for r in req['source']))

    def test_tooling_lists_zero_quantity_fixtures(self):
        Fixture.objects.create(tenant=self.tenant, name="Weld Jig", quantity=0, lead_time_days=7)
        req = sourcing_requirements(self.tenant)
        rows = [r for r in req['tooling'] if r['fixture'] == "Weld Jig"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['lead_time_days'], 7)

    def test_per_work_order_requirements(self):
        """The per-WO 'what this job needs' readout: BUY line short with an order-by date
        (need-by − lead time) bucketed by consumed-at-step; MAKE line short → build."""
        from Tracker.models import Steps
        comp = PartTypes.objects.create(tenant=self.tenant, name="Nozzle")
        oring = Material.objects.create(
            tenant=self.tenant, name="O-Ring", purchase_lead_time_days=10)
        step = Steps.objects.create(
            tenant=self.tenant, part_type=self.asm, name="Final Assembly")
        BOMLine.objects.create(
            tenant=self.tenant, bom=self.bom, component_type=comp,
            quantity=Decimal(1), source="MAKE", line_number=1)
        BOMLine.objects.create(
            tenant=self.tenant, bom=self.bom, material=oring, quantity=Decimal(2),
            source="BUY", line_number=2, consumed_at_step=step)
        need = date.today() + timedelta(days=20)
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-MR", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=3, process=self.proc, expected_start=need)

        rows = {r['component']: r for r in work_order_material_requirements(wo)['rows']}
        self.assertEqual(len(rows), 2)
        buy = rows["O-Ring"]
        self.assertEqual(buy['kind'], 'BUY')
        self.assertEqual(buy['short_qty'], 6)                       # 2 × 3, none on hand
        self.assertEqual(buy['status'], 'short')
        self.assertEqual(buy['consumed_at_step'], "Final Assembly")
        self.assertEqual(buy['order_by'], need - timedelta(days=10))
        make = rows["Nozzle"]
        self.assertEqual(make['kind'], 'MAKE')
        self.assertEqual(make['short_qty'], 3)                      # 1 × 3, nothing built
        self.assertEqual(make['status'], 'short')

    def test_incoming_excludes_already_accepted_lots(self):
        """A received-and-accepted lot (even with a promised_date) counts as on-hand only,
        never also as incoming — no double-count. A not-yet-accepted RECEIVED lot still
        counts as incoming."""
        from datetime import date as _d
        from django.contrib.auth import get_user_model
        from Tracker.models import MaterialLot
        mat = Material.objects.create(tenant=self.tenant, name="Bushing")
        BOMLine.objects.create(
            tenant=self.tenant, bom=self.bom, material=mat, quantity=Decimal(1),
            source="BUY", line_number=1)
        user = get_user_model().objects.create_user(
            username="i", email="i@c.test", password="x", tenant=self.tenant)
        MaterialLot.objects.create(
            tenant=self.tenant, lot_number="LA", material=mat, received_date=_d.today(),
            received_by=user, quantity=Decimal(5), quantity_remaining=Decimal(5),
            unit_of_measure="EA", status="ACCEPTED", promised_date=_d.today())
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-INC", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=2, process=self.proc)

        row = next(r for r in work_order_material_requirements(wo)['rows']
                   if r['component'] == "Bushing")
        self.assertEqual(row['on_hand'], 5.0)
        self.assertEqual(row['incoming'], 0.0)      # accepted lot NOT double-counted
        self.assertEqual(row['status'], 'ok')       # 5 on hand covers need of 2

        # A not-yet-accepted RECEIVED lot with a promise is legitimate incoming.
        MaterialLot.objects.create(
            tenant=self.tenant, lot_number="LB", material=mat, received_date=_d.today(),
            received_by=user, quantity=Decimal(4), quantity_remaining=Decimal(4),
            unit_of_measure="EA", status="RECEIVED", promised_date=_d.today())
        row2 = next(r for r in work_order_material_requirements(wo)['rows']
                    if r['component'] == "Bushing")
        self.assertEqual(row2['on_hand'], 5.0)      # unchanged
        self.assertEqual(row2['incoming'], 4.0)     # the RECEIVED lot counts

    def test_per_work_order_requirements_hidden_by_open_draft(self):
        """An open draft revision must NOT hide the released BOM from the per-WO readout."""
        from Tracker.services.mes.bom import create_new_bom_version
        oring = Material.objects.create(tenant=self.tenant, name="Gasket")
        BOMLine.objects.create(
            tenant=self.tenant, bom=self.bom, material=oring, quantity=Decimal(1),
            source="BUY", line_number=1)
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_user(
            username="d", email="d@c.test", password="x", tenant=self.tenant)
        create_new_bom_version(self.bom, user=user, change_description="wip")  # released → non-current
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-DR", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=1, process=self.proc)
        rows = work_order_material_requirements(wo)['rows']
        self.assertTrue(any(r['component'] == "Gasket" for r in rows))


class ConsumedComponentsTests(TenantContextMixin, TestCase):
    """A component a unit has already drawn from stock is gone from on-hand; it must be
    gone from demand too, or it counts twice and the shortage grows with floor progress
    (user-approved fix 2026-11-19). A work order of N whose K units drew their parts
    demands N−K, wherever the demand is read."""

    def setUp(self):
        super().setUp()
        from datetime import date as _d
        from django.contrib.auth import get_user_model
        from Tracker.models import MaterialLot, MaterialUsage, Parts, Steps
        self.tenant = Tenant.objects.create(name="Cons", slug="consumed", tier="PRO")
        self.set_tenant_context(self.tenant)
        asm = PartTypes.objects.create(tenant=self.tenant, name="Valve Body")
        proc = Processes.objects.create(tenant=self.tenant, name="P", part_type=asm,
                                        status="APPROVED", is_current_version=True)
        bom = BOM.objects.create(tenant=self.tenant, part_type=asm, revision="A",
                                 bom_type="ASSEMBLY", status="RELEASED", is_current_version=True)
        step = Steps.objects.create(tenant=self.tenant, part_type=asm, name="Assemble")
        self.valve = Material.objects.create(tenant=self.tenant, name="Control Valve",
                                             purchase_lead_time_days=5)
        BOMLine.objects.create(tenant=self.tenant, bom=bom, material=self.valve, quantity=Decimal(1),
                               source="BUY", line_number=1, consumed_at_step=step)
        user = get_user_model().objects.create_user(username="op", email="op@c.test", password="x",
                                                    tenant=self.tenant)
        # 10 received; the two draws below take 2 (recording a draw deducts it): 8 left.
        lot = MaterialLot.objects.create(
            tenant=self.tenant, lot_number="V1", material=self.valve, received_date=_d.today(),
            received_by=user, quantity=Decimal(10), quantity_remaining=Decimal(10),
            unit_of_measure="EA", status="ACCEPTED")
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-C", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=5, process=proc, expected_start=_d.today())
        for i in range(2):
            part = Parts.objects.create(tenant=self.tenant, ERP_id=f"P-{i}", part_type=asm,
                                        work_order=self.wo, step=step)
            MaterialUsage.objects.create(tenant=self.tenant, lot=lot, part=part, work_order=self.wo,
                                         qty_consumed=Decimal(1), consumed_by=user, step=step)
        # A work order with no units yet still demands its whole quantity.
        self.fresh = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-NEW", workorder_status=WorkOrderStatus.PENDING,
            quantity=4, process=proc, expected_start=_d.today())

    def test_the_per_job_readout_asks_only_for_what_is_still_to_be_drawn(self):
        row = next(r for r in work_order_material_requirements(self.wo)['rows']
                   if r['component'] == "Control Valve")
        self.assertEqual(row['on_hand'], 8.0)        # the 2 drawn left the shelf
        self.assertEqual(row['quantity'], 3.0)       # 5 ordered, 2 drawn
        self.assertEqual(row['short_qty'], 0.0)      # 8 on the shelf covers 3
        fresh = next(r for r in work_order_material_requirements(self.fresh)['rows']
                     if r['component'] == "Control Valve")
        self.assertEqual(fresh['quantity'], 4.0)

    def test_the_source_lane_counts_a_drawn_part_once(self):
        # 3 + 4 = 7 still to draw against 8 on the shelf: nothing to buy. Counting the
        # drawn 2 again (5 + 4 = 9) read short by 1.
        req = sourcing_requirements(self.tenant)
        self.assertFalse(any(r['material'] == "Control Valve" for r in req['source']))

    def test_the_material_lane_and_outlook_count_a_drawn_part_once(self):
        from django.utils import timezone
        from Tracker.services.planning.material_load import material_series
        from Tracker.services.planning.rccp import _month_buckets
        buckets = _month_buckets(self.tenant, timezone.now(), 1)
        rows = material_series(self.tenant, buckets, {self.wo.id: 0, self.fresh.id: 0})
        valve = next(m for m in rows if m['name'] == "Control Valve")
        self.assertEqual(valve['series'][0]['demand'], 7.0)
