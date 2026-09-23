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


class _RecoverableFixture(_BuyPartTypeFixture):
    """A recoverable housing, a core type that yields it, and two cores in the bank.

    Separate from the assertions so the later classes inherit the SETUP only —
    subclassing a TestCase that carries tests re-runs every one of them.
    """

    def setUp(self):
        super().setUp()
        from Tracker.models import Core, DisassemblyBOMLine

        self.housing.can_recover = True
        self.housing.save(update_fields=["can_recover"])

        self.core_type = PartTypes.objects.create(tenant=self.tenant, name="Core Injector")
        DisassemblyBOMLine.objects.create(
            tenant=self.tenant, core_type=self.core_type, component_type=self.housing,
            expected_qty=2, expected_fallout_rate=Decimal("0.50"))
        # 2 cores x (2 expected - 50% fallout) = 2 housings the bank could yield.
        for n in ("RC-1", "RC-2"):
            Core.objects.create(
                tenant=self.tenant, core_number=n, core_type=self.core_type,
                fulfilment_mode="EXCHANGE", status="RECEIVED",
                received_date=date.today(), received_by=self.user)

    def _housing_row(self):
        rows = [r for r in sourcing_requirements(self.tenant)['source']
                if r['material'] == "Housing"]
        self.assertEqual(len(rows), 1)
        return rows[0]


class SourcingShowsTheRecoverableLaneTests(_RecoverableFixture):
    """Material planning counts stock and purchase orders and has no idea teardown is
    about to PRODUCE the component it is calling short — so a planner buys parts the
    shop was going to harvest.

    The lane REPORTS; it does not net. Recoverable supply is a forecast (teardown has
    not happened); on-hand and on-order are facts. Subtracting it from `qty_short`
    would let a planner skip an order on stock that does not exist yet, and the error
    is asymmetric: over-counting future supply stops a line, under-counting only buys
    a part you could have harvested.
    """

    def test_the_bank_shows_up_beside_the_shortfall(self):
        self._work_order(qty=5, start=date.today() + timedelta(days=60))
        row = self._housing_row()
        self.assertEqual(row['recoverable'], 2.0)
        self.assertEqual(row['recoverable_cores'], 2)

    def test_it_is_never_subtracted_from_what_to_buy(self):
        """The whole point of the lane. If `qty_short` dropped to 3, a planner would
        order 3 and the line would stop when teardown yielded less than forecast."""
        self._work_order(qty=5, start=date.today() + timedelta(days=60))
        self.assertEqual(self._housing_row()['qty_short'], 5)

    def test_it_names_which_cores_the_forecast_came_from(self):
        """A planner who cannot see the basis of a forecast cannot judge whether to
        trust it, and an untrusted number is just noise on the sheet."""
        self._work_order(qty=5, start=date.today() + timedelta(days=60))
        sources = self._housing_row()['recoverable_sources']
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]['core_type'], "Core Injector")
        self.assertEqual(sources[0]['cores'], 2)

    def test_an_expendable_reports_no_recoverable_supply(self):
        """`can_recover` is the item master's answer. A seal never comes out of a core
        reusable, whatever the bank holds."""
        self.housing.can_recover = False
        self.housing.save(update_fields=["can_recover"])
        self._work_order(qty=5, start=date.today() + timedelta(days=60))
        row = self._housing_row()
        self.assertEqual(row['recoverable'], 0.0)
        self.assertEqual(row['recoverable_sources'], [])

    def test_a_raw_material_line_carries_the_lane_but_empty(self):
        """You cannot harvest sealant. The key is MATERIAL, not PART_TYPE, so the lane
        is never even looked up — but the field must still be present, or the row
        shape differs between kinds and the client has to special-case it."""
        mat = Material.objects.create(
            tenant=self.tenant, name="Sealant", purchase_lead_time_days=7)
        BOMLine.objects.create(
            tenant=self.tenant, bom=self.bom, material=mat, quantity=Decimal(1),
            source="BUY", line_number=9)
        self._work_order(qty=5, start=date.today() + timedelta(days=60))
        rows = [r for r in sourcing_requirements(self.tenant)['source']
                if r['material'] == "Sealant"]
        self.assertEqual(rows[0]['recoverable'], 0.0)

    def test_a_customers_own_unit_is_not_available_supply(self):
        """A repair-and-return core is committed to its owner — it cannot be counted
        as supply for somebody else's work order."""
        from Tracker.models import Core
        Core.objects.filter(tenant=self.tenant).update(fulfilment_mode="REPAIR_RETURN")
        self._work_order(qty=5, start=date.today() + timedelta(days=60))
        self.assertEqual(self._housing_row()['recoverable'], 0.0)


class RecoverLaneProposesTeardownTests(_RecoverableFixture):
    """The `recoverable` column says the bank COULD yield 2. This lane says what to do
    about it: tear down N cores of which type, starting by when, covering this much of
    the shortfall and leaving that much to buy.

    It PROPOSES and does not raise the work order. Creating a teardown WO commits
    physical cores out of the bank on the strength of a forecast, and unlike a MAKE
    child WO there is no cheap undo — the unit is in pieces.
    """

    def _recover_row(self):
        rows = [r for r in sourcing_requirements(self.tenant)['recover']
                if r['component'] == "Housing"]
        self.assertEqual(len(rows), 1)
        return rows[0]

    def test_it_says_how_many_cores_to_tear_down(self):
        self._work_order(qty=5, start=date.today() + timedelta(days=60))
        row = self._recover_row()
        plan = row['cores'][0]
        self.assertEqual(plan['core_type'], "Core Injector")
        # 5 short at 1 usable housing per core would want 5 cores; only 2 are in the
        # bank, so the proposal is capped at what actually exists.
        self.assertEqual(plan['cores_to_tear_down'], 2)
        self.assertEqual(plan['cores_available'], 2)

    def test_it_splits_the_shortfall_into_teardown_and_buy(self):
        """The planner's actual decision. Teardown covers part of it; the rest is a
        purchase, and the sheet has to say which is which or it is not actionable."""
        self._work_order(qty=5, start=date.today() + timedelta(days=60))
        row = self._recover_row()
        self.assertEqual(row['covered_by_teardown'], 2.0)
        self.assertEqual(row['still_to_buy'], 3.0)
        self.assertEqual(row['qty_short'], 5)

    def test_no_authored_teardown_duration_means_no_start_by_date(self):
        """A made-up lead time is worse than none: it reads as authored fact on the
        sheet and a planner schedules against it. This fixture authors no disassembly
        process, so the date must be absent rather than guessed."""
        self._work_order(qty=5, start=date.today() + timedelta(days=60))
        row = self._recover_row()
        self.assertIsNone(row['start_by'])
        self.assertIsNone(row['cores'][0]['lead_time_days'])

    def test_a_component_the_bank_cannot_yield_raises_no_proposal(self):
        self.housing.can_recover = False
        self.housing.save(update_fields=["can_recover"])
        self._work_order(qty=5, start=date.today() + timedelta(days=60))
        self.assertEqual(
            [r for r in sourcing_requirements(self.tenant)['recover']
             if r['component'] == "Housing"], [])

    def test_a_covered_component_raises_no_proposal(self):
        """No shortfall, no source row, so nothing to propose tearing down for. The
        lane follows demand, not the contents of the bank."""
        self._lot(10)                                  # fully covered
        self._work_order(qty=5, start=date.today() + timedelta(days=60))
        self.assertEqual(sourcing_requirements(self.tenant)['recover'], [])

    def test_the_internal_join_key_does_not_leak_to_the_client(self):
        """The source rows carry a private key so the recover lane can join back to
        them. It is not part of the published contract."""
        self._work_order(qty=5, start=date.today() + timedelta(days=60))
        for row in sourcing_requirements(self.tenant)['source']:
            self.assertNotIn('_id', row)


class TeardownLeadTimeTests(_RecoverableFixture):
    """Teardown lead time is summed from the disassembly process's authored step
    durations — the same numbers scheduling plans against, so the planning sheet and
    the board cannot disagree about how long a teardown takes."""

    def setUp(self):
        super().setUp()
        from datetime import timedelta as _td
        from Tracker.models import ProcessStep, Steps

        self.dis_proc = Processes.objects.create(
            tenant=self.tenant, name="Teardown", part_type=self.core_type,
            status="APPROVED", is_current_version=True, is_disassembly=True)
        for i, hours in enumerate((10, 14), start=1):
            step = Steps.objects.create(
                tenant=self.tenant, name=f"Teardown {i}", part_type=self.core_type,
                expected_duration=_td(hours=hours))
            # ProcessStep carries no tenant of its own — it is scoped by its process.
            ProcessStep.objects.create(process=self.dis_proc, step=step, order=i)

    def test_lead_time_is_the_sum_of_authored_step_durations(self):
        from Tracker.services.reman.recovery import teardown_lead_days
        # 10h + 14h = 24h = 1 day.
        self.assertEqual(teardown_lead_days(self.core_type, tenant=self.tenant), 1)

    def test_a_part_day_still_occupies_a_whole_day(self):
        """Rounding down would quietly promise the components a day earlier than the
        shop can produce them."""
        from datetime import timedelta as _td
        from Tracker.services.reman.recovery import teardown_lead_days
        from Tracker.models import Steps
        Steps.objects.filter(tenant=self.tenant, name="Teardown 2").update(
            expected_duration=_td(hours=1))
        self.assertEqual(teardown_lead_days(self.core_type, tenant=self.tenant), 1)

    def test_the_proposal_carries_a_start_by_date(self):
        need = date.today() + timedelta(days=60)
        self._work_order(qty=5, start=need)
        row = [r for r in sourcing_requirements(self.tenant)['recover']
               if r['component'] == "Housing"][0]
        self.assertEqual(row['cores'][0]['lead_time_days'], 1)
        self.assertEqual(row['start_by'], need - timedelta(days=1))

    def test_an_unauthored_process_yields_no_lead_time(self):
        from Tracker.services.reman.recovery import teardown_lead_days
        other = PartTypes.objects.create(tenant=self.tenant, name="Untorn")
        self.assertIsNone(teardown_lead_days(other, tenant=self.tenant))

    def test_a_process_with_no_durations_yields_no_lead_time(self):
        """Authored steps with blank durations are not a zero-day teardown — they are
        an unanswered question, and the sheet says so by omitting the date."""
        from Tracker.services.reman.recovery import teardown_lead_days
        from Tracker.models import Steps
        Steps.objects.filter(tenant=self.tenant, part_type=self.core_type).update(
            expected_duration=None)
        self.assertIsNone(teardown_lead_days(self.core_type, tenant=self.tenant))
