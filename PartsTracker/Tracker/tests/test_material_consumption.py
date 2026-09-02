"""Material consumption on step completion.

`MaterialUsage` and its stock deduction existed for a long time with nothing creating
a row, so `quantity_remaining` only ever grew. Two features already trusted that
number — the solver's material gate and the staging list — which made "on hand" a
figure that drifted high forever.

These tests pin the call site, and in particular the three judgement calls:
consumption never blocks a finished part from advancing, stock leaves oldest-expiry
first, and an unattributable (automated) advance records nothing rather than inventing
a consumer.
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from Tracker.models import (
    BOM, BOMLine, Material, MaterialLot, MaterialUsage, Parts, PartTypes, Processes,
    ProcessStep, Steps, Tenant, WorkOrder, WorkOrderStatus,
)
from Tracker.services.mes.consumption import consume_for_step
from Tracker.services.mes.parts import advance_part_step
from Tracker.tests.base import TenantContextMixin


class MaterialConsumptionTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="MC", slug="mat-consume", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.operator = get_user_model().objects.create_user(
            username="mc-op", email="mc@c.test", password="x", tenant=self.tenant)

        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Injector")
        self.process = Processes.objects.create(
            tenant=self.tenant, name="P", part_type=self.pt)
        self.step1 = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Assemble", step_type="TASK")
        self.step2 = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Test", step_type="TASK")
        ProcessStep.objects.create(process=self.process, step=self.step1, order=1)
        ProcessStep.objects.create(process=self.process, step=self.step2, order=2)

        self.seal = Material.objects.create(tenant=self.tenant, name="Seal Kit")
        self.bom = BOM.objects.create(
            tenant=self.tenant, part_type=self.pt, bom_type='ASSEMBLY',
            status='RELEASED', version=1)
        BOMLine.objects.create(
            tenant=self.tenant, bom=self.bom, material=self.seal, quantity=2,
            source='BUY', consumed_at_step=self.step1)

        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-MC", quantity=1, process=self.process,
            workorder_status=WorkOrderStatus.IN_PROGRESS)
        self.part = Parts.objects.create(
            tenant=self.tenant, ERP_id="WO-MC-P0", part_type=self.pt,
            work_order=self.wo, step=self.step1)

    def _lot(self, qty, expires_in_days=None, number="L1"):
        return MaterialLot.objects.create(
            tenant=self.tenant, material=self.seal, lot_number=number,
            quantity=Decimal(str(qty)), quantity_remaining=Decimal(str(qty)),
            unit_of_measure="EA", received_date=timezone.localdate(),
            received_by=self.operator, status='ACCEPTED',
            expiration_date=(timezone.localdate() + timedelta(days=expires_in_days)
                             if expires_in_days is not None else None))

    # --- the call site ------------------------------------------------------

    def test_advancing_a_step_records_what_it_consumed(self):
        """The gap this closes: before, finishing a step drew nothing and stock never
        went down."""
        lot = self._lot(10)
        advance_part_step(self.part, operator=self.operator)

        usages = MaterialUsage.objects.filter(part=self.part)
        self.assertEqual(usages.count(), 1)
        self.assertEqual(usages.first().qty_consumed, Decimal('2'))
        lot.refresh_from_db()
        self.assertEqual(lot.quantity_remaining, Decimal('8'))

    def test_consumption_is_attributed_for_traceability(self):
        """The point of the table: which lot went into which unit, drawn by whom."""
        self._lot(10)
        advance_part_step(self.part, operator=self.operator)
        u = MaterialUsage.objects.get(part=self.part)
        self.assertEqual(u.consumed_by, self.operator)
        self.assertEqual(u.step, self.step1)
        self.assertEqual(u.work_order, self.wo)

    def test_only_lines_consumed_at_this_step_are_drawn(self):
        """A BOM line consumed at Test must not be drawn when Assemble completes."""
        other = Material.objects.create(tenant=self.tenant, name="Test Fluid")
        BOMLine.objects.create(
            tenant=self.tenant, bom=self.bom, material=other, quantity=1,
            source='BUY', consumed_at_step=self.step2)
        MaterialLot.objects.create(
            tenant=self.tenant, material=other, lot_number="F1",
            quantity=Decimal('5'), quantity_remaining=Decimal('5'),
            unit_of_measure="EA", received_date=timezone.localdate(),
            received_by=self.operator, status='ACCEPTED')
        self._lot(10)

        advance_part_step(self.part, operator=self.operator)
        drawn = {u.lot.material_id for u in MaterialUsage.objects.filter(part=self.part)}
        self.assertEqual(drawn, {self.seal.id})

    # --- FEFO ---------------------------------------------------------------

    def test_stock_leaves_oldest_expiry_first(self):
        """Dated stock is the stock that can spoil, so it goes first — otherwise the
        shop expires material it was holding while newer lots got used."""
        late = self._lot(10, expires_in_days=90, number="LATE")
        early = self._lot(10, expires_in_days=10, number="EARLY")
        advance_part_step(self.part, operator=self.operator)
        early.refresh_from_db(); late.refresh_from_db()
        self.assertEqual(early.quantity_remaining, Decimal('8'))
        self.assertEqual(late.quantity_remaining, Decimal('10'))

    def test_undated_stock_is_used_after_dated_stock(self):
        undated = self._lot(10, number="NODATE")
        dated = self._lot(10, expires_in_days=30, number="DATED")
        advance_part_step(self.part, operator=self.operator)
        dated.refresh_from_db(); undated.refresh_from_db()
        self.assertEqual(dated.quantity_remaining, Decimal('8'))
        self.assertEqual(undated.quantity_remaining, Decimal('10'))

    def test_a_draw_spans_lots_when_one_cannot_cover_it(self):
        a = self._lot(1, expires_in_days=10, number="A")
        b = self._lot(5, expires_in_days=20, number="B")
        advance_part_step(self.part, operator=self.operator)
        a.refresh_from_db(); b.refresh_from_db()
        self.assertEqual(a.quantity_remaining, Decimal('0'))
        self.assertEqual(b.quantity_remaining, Decimal('4'))
        self.assertEqual(a.status, 'CONSUMED')

    # --- never blocks the floor --------------------------------------------

    def test_insufficient_stock_still_advances_the_part(self):
        """The part was physically built; refusing to advance would punish the
        operator for a stock-accuracy error and teach people to work around the
        system. The material GATE prevents starting without material — not this."""
        self._lot(1)   # need 2
        result = advance_part_step(self.part, operator=self.operator)
        self.assertEqual(result, "advanced")
        self.part.refresh_from_db()
        self.assertEqual(self.part.step, self.step2)

    def test_a_shortfall_is_reported_rather_than_raised(self):
        self._lot(1)
        r = consume_for_step(self.part, self.step1, self.operator)
        self.assertEqual(len(r.shortfalls), 1)
        self.assertEqual(r.shortfalls[0]['short'], 1.0)

    def test_no_stock_at_all_still_advances(self):
        result = advance_part_step(self.part, operator=self.operator)
        self.assertEqual(result, "advanced")
        self.assertFalse(MaterialUsage.objects.filter(part=self.part).exists())

    def test_stock_is_never_driven_negative(self):
        lot = self._lot(1)
        advance_part_step(self.part, operator=self.operator)
        lot.refresh_from_db()
        self.assertGreaterEqual(lot.quantity_remaining, Decimal('0'))

    # --- attribution --------------------------------------------------------

    def test_an_automated_advance_records_nothing(self):
        """`consumed_by` is required and traceability is the whole point — an advance
        with no operator has nobody to attribute the draw to, so it records nothing
        rather than inventing an actor."""
        lot = self._lot(10)
        advance_part_step(self.part, operator=None)
        self.assertFalse(MaterialUsage.objects.filter(part=self.part).exists())
        lot.refresh_from_db()
        self.assertEqual(lot.quantity_remaining, Decimal('10'))

    # --- idempotency --------------------------------------------------------

    def test_one_visit_draws_once(self):
        """Re-running the advance for the same visit must not double-draw."""
        lot = self._lot(10)
        consume_for_step(self.part, self.step1, self.operator)
        from Tracker.services.mes.parts import _consume_step_material
        _consume_step_material(self.part, self.step1, self.operator)
        lot.refresh_from_db()
        self.assertEqual(MaterialUsage.objects.filter(part=self.part).count(), 1)
        self.assertEqual(lot.quantity_remaining, Decimal('8'))
