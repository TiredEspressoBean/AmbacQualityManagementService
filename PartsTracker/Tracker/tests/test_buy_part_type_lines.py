"""BUY lines that point at a buyable PartType rather than a raw Material.

The BOM's two component columns and its `source` flag are independent:

    component_type + MAKE -> build it here (spawns a pegged child work order)
    component_type + BUY  -> buy the part (requires PartTypes.can_buy)
    material       + BUY  -> buy the raw material / consumable

The third row was the only one planning understood, which forced every purchased
component onto `Material`. That matters beyond tidiness: receiving-inspection plans,
supplier qualification, part approval and life limits are all keyed to PartTypes, so a
purchased *part* routed through Material dock-to-stocks with no quality gate at all.

These tests pin the BUY-on-a-PartType path across every consumer: the sourcing report,
the per-work-order readout, BOM explosion (which must NOT spawn a work order for
something we're buying), and the scheduler's material gate.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from Tracker.models import (
    BOM, BOMLine, Material, MaterialLot, PartTypes, Processes, Tenant,
    WorkOrder, WorkOrderStatus,
)
from Tracker.services.mes.bom import buy_line_item
from Tracker.services.mes.requirements import (
    sourcing_requirements, work_order_material_requirements,
)
from Tracker.tests.base import TenantContextMixin


class _BuyPartTypeFixture(TenantContextMixin, TestCase):
    """An assembly whose BOM buys a part (not a raw material) from a supplier."""

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="BuyPT", slug="buy-pt", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.user = get_user_model().objects.create_user(
            username="b", email="b@c.test", password="x", tenant=self.tenant)
        self.asm = PartTypes.objects.create(tenant=self.tenant, name="Injector")
        self.proc = Processes.objects.create(
            tenant=self.tenant, name="P", part_type=self.asm,
            status="APPROVED", is_current_version=True)
        self.bom = BOM.objects.create(
            tenant=self.tenant, part_type=self.asm, revision="A",
            bom_type="ASSEMBLY", status="RELEASED", is_current_version=True)
        # A housing we could make, but are sourcing outside.
        self.housing = PartTypes.objects.create(
            tenant=self.tenant, name="Housing", can_make=True, can_buy=True,
            purchase_lead_time_days=21)
        self.line = BOMLine.objects.create(
            tenant=self.tenant, bom=self.bom, component_type=self.housing,
            quantity=Decimal(1), source="BUY", line_number=1)

    def _work_order(self, qty=5, start=None):
        return WorkOrder.objects.create(
            tenant=self.tenant, ERP_id=f"WO-{qty}",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=qty,
            process=self.proc, expected_start=start or (date.today() + timedelta(days=60)))

    def _lot(self, qty, status="ACCEPTED", lot_number="PT-L1", promised=None):
        """Stock of a bought PART hangs off material_type, not material."""
        return MaterialLot.objects.create(
            tenant=self.tenant, lot_number=lot_number, material_type=self.housing,
            received_date=date.today(), received_by=self.user,
            quantity=Decimal(qty), quantity_remaining=Decimal(qty),
            unit_of_measure="EA", status=status, promised_date=promised)


class BuyLineResolutionTests(_BuyPartTypeFixture):
    def test_resolves_a_buyable_part_type(self):
        item = buy_line_item(self.line)
        self.assertIsNotNone(item)
        self.assertEqual(item.kind, "PART_TYPE")
        self.assertEqual(item.name, "Housing")
        self.assertEqual(item.lead_time_days, 21)
        self.assertEqual(item.lot_field, "material_type")

    def test_make_only_part_on_a_buy_line_is_not_purchasable(self):
        """An authoring mistake, not a purchase instruction — surfacing it as buyable
        would put a part we can't actually source into the sourcing report."""
        self.housing.can_buy = False
        self.housing.save(update_fields=["can_buy"])
        self.assertIsNone(buy_line_item(self.line))

    def test_make_line_is_not_a_buy_line(self):
        self.line.source = "MAKE"
        self.line.save(update_fields=["source"])
        self.assertIsNone(buy_line_item(self.line))

    def test_raw_material_still_resolves(self):
        mat = Material.objects.create(
            tenant=self.tenant, name="O-Ring", purchase_lead_time_days=14,
            safety_stock=Decimal(5))
        line = BOMLine.objects.create(
            tenant=self.tenant, bom=self.bom, material=mat, quantity=Decimal(2),
            source="BUY", line_number=2)
        item = buy_line_item(line)
        self.assertEqual(item.kind, "MATERIAL")
        self.assertEqual(item.lot_field, "material")
        self.assertEqual(item.safety_stock, 5.0)

    def test_the_two_kinds_do_not_collide_in_one_key_space(self):
        """A Material and a PartType could in principle carry the same uuid; the kind
        is part of the key so one can never mask the other."""
        mat = Material.objects.create(tenant=self.tenant, name="Housing")
        line = BOMLine.objects.create(
            tenant=self.tenant, bom=self.bom, material=mat, quantity=Decimal(1),
            source="BUY", line_number=3)
        self.assertNotEqual(buy_line_item(self.line).key, buy_line_item(line).key)


class SourcingIncludesBoughtPartsTests(_BuyPartTypeFixture):
    def test_short_bought_part_appears_in_the_sourcing_report(self):
        need = date.today() + timedelta(days=60)
        self._work_order(qty=5, start=need)          # demand 5, nothing on hand

        rows = [r for r in sourcing_requirements(self.tenant)['source']
                if r['material'] == "Housing"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['qty_short'], 5)
        self.assertEqual(rows[0]['buy_kind'], 'PART_TYPE')
        self.assertEqual(rows[0]['order_by'], need - timedelta(days=21))

    def test_stock_of_the_bought_part_covers_it(self):
        self._work_order(qty=5)
        self._lot(5)
        self.assertFalse(any(r['material'] == "Housing"
                             for r in sourcing_requirements(self.tenant)['source']))

    def test_on_order_stock_of_a_bought_part_counts_as_incoming(self):
        self._work_order(qty=5)
        self._lot(5, status="ON_ORDER", lot_number="PT-PO-1",
                  promised=date.today() + timedelta(days=10))
        self.assertFalse(any(r['material'] == "Housing"
                             for r in sourcing_requirements(self.tenant)['source']))

    def test_per_work_order_readout_lists_it_as_a_buy_line(self):
        wo = self._work_order(qty=5)
        self._lot(2)
        row = next(r for r in work_order_material_requirements(wo)['rows']
                   if r['component'] == "Housing")
        self.assertEqual(row['kind'], 'BUY')
        self.assertEqual(row['buy_kind'], 'PART_TYPE')
        self.assertEqual(row['on_hand'], 2.0)
        self.assertEqual(row['short_qty'], 3.0)
        self.assertEqual(row['lead_time_days'], 21)


class ExplosionDoesNotBuildBoughtPartsTests(_BuyPartTypeFixture):
    def test_bought_part_is_recorded_as_buy_not_exploded_into_a_work_order(self):
        """The whole point of source=BUY on a part: we could make it, but this time
        we're buying it, so no child work order."""
        from Tracker.services.mes.bom_explosion import explode_work_order
        wo = self._work_order(qty=5)

        result = explode_work_order(wo, user=self.user)

        self.assertEqual([b['component'] for b in result.buy], ["Housing"])
        self.assertEqual(result.buy[0]['buy_kind'], 'PART_TYPE')
        self.assertEqual(result.created, [])
        self.assertFalse(
            WorkOrder.objects.filter(tenant=self.tenant, pegged_to_bom_line=self.line).exists(),
            "buying a part must not spawn a work order to build it")

    def test_make_only_part_on_a_buy_line_is_reported_short_not_silently_dropped(self):
        from Tracker.services.mes.bom_explosion import explode_work_order
        self.housing.can_buy = False
        self.housing.save(update_fields=["can_buy"])
        wo = self._work_order(qty=5)

        result = explode_work_order(wo, user=self.user)
        self.assertEqual(result.buy, [])
        self.assertEqual(len(result.short), 1)
        self.assertIn("no purchasable component", result.short[0]['reason'])


class MaterialGateSeesBoughtPartsTests(_BuyPartTypeFixture):
    def test_gate_flags_a_short_bought_part(self):
        """The scheduler's material gate reads BOM lines as `.values()` dicts, so it
        needs its own resolution path — this is the one most likely to silently skip."""
        from Tracker.services.scheduling.data import get_material_gates, get_schedule_horizon
        # Due imminently with nothing on hand and no receipt → past the order-by date.
        wo = self._work_order(qty=5, start=date.today())

        horizon = get_schedule_horizon(self.tenant)
        release, short, detail = get_material_gates(self.tenant, horizon)
        keys = [k for k in detail if k[0] == wo.id]
        self.assertTrue(keys, "a short bought part should reach the gate detail")
        self.assertIn("Housing", detail[keys[0]])

    def test_gate_clears_when_the_bought_part_is_in_stock(self):
        from Tracker.services.scheduling.data import get_material_gates, get_schedule_horizon
        wo = self._work_order(qty=5, start=date.today())
        self._lot(5)

        horizon = get_schedule_horizon(self.tenant)
        _release, short, detail = get_material_gates(self.tenant, horizon)
        self.assertFalse([k for k in detail if k[0] == wo.id])
        self.assertFalse([k for k in short if k[0] == wo.id])
