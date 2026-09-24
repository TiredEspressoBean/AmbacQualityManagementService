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
    """A reman world shaped the way the shop floor builds it.

    The core type is the unit being rebuilt: its own reman process and released
    ASSEMBLY BOM (one recoverable housing), which is what a rebuild's work order runs.
    Two EXCHANGE cores wait in the bank, each expected to yield one usable housing
    (2 per core, 50% fallout). The new-build product (`self.asm`, from the parent
    fixture) consumes the same housing — so the two kinds of demand can be compared
    on one component.
    """

    def setUp(self):
        super().setUp()
        from Tracker.models import Core, DisassemblyBOMLine

        self.housing.can_recover = True
        self.housing.save(update_fields=["can_recover"])

        self.core_type = PartTypes.objects.create(tenant=self.tenant, name="Core Injector")
        self.core_bom = BOM.objects.create(
            tenant=self.tenant, part_type=self.core_type, revision="A",
            bom_type="ASSEMBLY", status="RELEASED", is_current_version=True)
        self.core_line = BOMLine.objects.create(
            tenant=self.tenant, bom=self.core_bom, component_type=self.housing,
            quantity=Decimal(1), source="BUY", line_number=1)
        # Not flagged is_disassembly: this is the route a rebuild's work order runs,
        # and keeping it apart from the teardown process keeps lead-time resolution
        # unambiguous in the tests that author one.
        self.reman_proc = Processes.objects.create(
            tenant=self.tenant, name="Reman", part_type=self.core_type,
            status="APPROVED", is_current_version=True)

        DisassemblyBOMLine.objects.create(
            tenant=self.tenant, core_type=self.core_type, component_type=self.housing,
            expected_qty=2, expected_fallout_rate=Decimal("0.50"))
        self.bank = [
            Core.objects.create(
                tenant=self.tenant, core_number=n, core_type=self.core_type,
                fulfilment_mode="EXCHANGE", status="RECEIVED",
                received_date=date.today() - timedelta(days=age), received_by=self.user)
            # RC-OLD waited longest, so a proposal commits it first.
            for n, age in (("RC-OLD", 10), ("RC-NEW", 1))
        ]
        self._n = 0

    def _rebuild(self, *, cores=1, mode="EXCHANGE", status="IN_REBUILD", start=None):
        """A reman work order carrying `cores` units at `status`."""
        from Tracker.models import Core
        self._n += 1
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id=f"RB-{self._n}",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=cores,
            process=self.reman_proc,
            expected_start=start or (date.today() + timedelta(days=60)))
        for i in range(cores):
            Core.objects.create(
                tenant=self.tenant, core_number=f"RB-{self._n}-{i}",
                core_type=self.core_type, fulfilment_mode=mode, status=status,
                work_order=wo, received_date=date.today(), received_by=self.user)
        return wo

    def _accept_recovered_housing(self):
        """A recovered housing, accepted to stock the normal way — off a donor core."""
        from Tracker.models import Core, HarvestedComponent
        from Tracker.services.reman.harvested_component import accept_component_to_inventory
        donor = Core.objects.create(
            tenant=self.tenant, core_number="DONOR-1", core_type=self.core_type,
            fulfilment_mode="EXCHANGE", status="DISASSEMBLED",
            received_date=date.today(), received_by=self.user)
        hc = HarvestedComponent.objects.create(
            tenant=self.tenant, core=donor, component_type=self.housing,
            condition_grade="A", disassembled_by=self.user)
        return accept_component_to_inventory(hc, self.user, transfer_life=False)

    def _row(self, lane, key, value):
        rows = [r for r in sourcing_requirements(self.tenant)[lane] if r[key] == value]
        return rows[0] if rows else None

    def _housing(self):
        return self._row('source', 'material', "Housing")

    def _recover(self):
        return self._row('recover', 'core_type', "Core Injector")


class RemanDemandByStageTests(_RecoverableFixture):
    """A reman work order's demand is read per core from where each core is — not its
    process BOM times its quantity, which asked for a full rebuild kit per core."""

    def test_an_exchange_teardown_is_supply_not_demand(self):
        """The original over-count: exchange cores being harvested read as a full
        rebuild kit each. They are what the recovered pool is MADE from."""
        self._rebuild(cores=3, status="IN_DISASSEMBLY")
        self.assertIsNone(self._housing())

    def test_a_disassembled_exchange_core_asks_for_nothing_yet(self):
        """Rebuild or harvest is undecided until someone releases it."""
        self._rebuild(cores=2, status="DISASSEMBLED")
        self.assertIsNone(self._housing())

    def test_an_exchange_rebuild_needs_what_its_plan_replaces(self):
        """Nothing recovered from these units and no pool on the shelf, so the plan
        resolves each housing slot to a purchase: 3 units, 3 housings."""
        self._rebuild(cores=3)
        self.assertEqual(self._housing()['qty_short'], 3)

    def test_a_repair_return_rebuild_reuses_its_own_part(self):
        """The unit's own housing came out serviceable: REUSE, so no demand at all.
        Consumption and the pick sheet already treated it that way; the buy list now
        agrees."""
        from Tracker.models import HarvestedComponent
        wo = self._rebuild(cores=1, mode="REPAIR_RETURN")
        HarvestedComponent.objects.create(
            tenant=self.tenant, core=wo.cores.get(), component_type=self.housing,
            condition_grade="A", disassembled_by=self.user)
        self.assertIsNone(self._housing())

    def test_an_unopened_repair_return_unit_is_a_forecast(self):
        """Four units not yet torn down, 50% fallout: 2 expected replacements —
        reported beside the buy figure, never in it."""
        self._rebuild(cores=4, mode="REPAIR_RETURN", status="RECEIVED")
        row = self._housing()
        self.assertEqual(row['qty_short'], 0)
        self.assertEqual(row['forecast_short'], 2.0)

    def test_the_forecast_assumes_the_worst_without_an_authored_rate(self):
        """No fallout authored: every slot is a possible replacement, as the rebuild
        plan assumes for an unopened unit. Safe, because a forecast is not bought."""
        from Tracker.models import DisassemblyBOMLine
        DisassemblyBOMLine.objects.filter(tenant=self.tenant).delete()
        self._rebuild(cores=3, mode="REPAIR_RETURN", status="RECEIVED")
        self.assertEqual(self._housing()['forecast_short'], 3.0)

    def test_expendables_are_firm_even_before_teardown(self):
        """A seal is replaced every time, opened or not — that part of the kit is not
        a guess."""
        seal = PartTypes.objects.create(tenant=self.tenant, name="Seal", can_buy=True,
                                        can_recover=False)
        BOMLine.objects.create(tenant=self.tenant, bom=self.core_bom, component_type=seal,
                               quantity=Decimal(2), source="BUY", line_number=2)
        self._rebuild(cores=3, mode="REPAIR_RETURN", status="RECEIVED")
        row = self._row('source', 'material', "Seal")
        self.assertEqual(row['qty_short'], 6)
        self.assertEqual(row['forecast_short'], 0.0)

    def test_a_finished_unit_needs_nothing(self):
        self._rebuild(cores=2, status="REBUILT")
        self.assertIsNone(self._housing())


class SourcingShowsTheRecoverableLaneTests(_RecoverableFixture):
    """The bank's yield, reported beside the buy figure — and only where some exchange
    rebuild could use it, since anywhere else it is no help to the line."""

    def test_the_bank_shows_up_beside_the_shortfall(self):
        self._rebuild(cores=5)
        row = self._housing()
        self.assertEqual(row['recoverable'], 2.0)
        self.assertEqual(row['recoverable_cores'], 2)

    def test_it_is_never_subtracted_from_what_to_buy(self):
        """If `qty_short` dropped to 3, a planner would order 3 and the line would stop
        when teardown yielded less than forecast."""
        self._rebuild(cores=5)
        self.assertEqual(self._housing()['qty_short'], 5)

    def test_it_names_which_cores_the_forecast_came_from(self):
        self._rebuild(cores=5)
        sources = self._housing()['recoverable_sources']
        self.assertEqual([(s['core_type'], s['cores']) for s in sources],
                         [("Core Injector", 2)])

    def test_a_repair_return_shortfall_is_offered_no_bank_supply(self):
        """A repair-and-return unit is never offered the pool, so the bank cannot help
        its shortfall and saying otherwise would invite a planner to wait on it."""
        self._rebuild(cores=5, mode="REPAIR_RETURN")
        self.assertEqual(self._housing()['recoverable'], 0.0)

    def test_a_new_build_is_offered_no_bank_supply(self):
        """Recovered stock does not go into new builds (decided 2026-09-24)."""
        self._work_order(qty=5)
        self.assertEqual(self._housing()['recoverable'], 0.0)


class RecoverLaneTests(_RecoverableFixture):
    """Teardown proposed to refill the recovered pool — one row per CORE TYPE."""

    def test_it_proposes_the_oldest_cores_first(self):
        self._rebuild(cores=1)
        row = self._recover()
        self.assertEqual(row['cores_to_tear_down'], 1)
        self.assertEqual([c['core_number'] for c in row['candidate_cores']], ["RC-OLD"])

    def test_it_is_capped_at_what_is_in_the_bank(self):
        """5 housings needed at 1 per core wants 5 cores; 2 exist."""
        self._rebuild(cores=5)
        row = self._recover()
        self.assertEqual(row['cores_to_tear_down'], 2)
        comp = row['components'][0]
        self.assertEqual((comp['needed'], comp['covered_by_teardown'], comp['still_short']),
                         (5.0, 2.0, 3.0))

    def test_one_core_type_is_one_row_however_many_components_it_yields(self):
        """Housings need 2 cores (1 each), bodies need 1 (2 each): tear down 2, not 3 —
        the bodies ride along with the housings."""
        from Tracker.models import DisassemblyBOMLine
        body = PartTypes.objects.create(tenant=self.tenant, name="Body", can_buy=True,
                                        can_recover=True)
        BOMLine.objects.create(tenant=self.tenant, bom=self.core_bom, component_type=body,
                               quantity=Decimal(1), source="BUY", line_number=2)
        DisassemblyBOMLine.objects.create(
            tenant=self.tenant, core_type=self.core_type, component_type=body,
            expected_qty=2, expected_fallout_rate=Decimal("0"))
        self._rebuild(cores=2)
        rows = sourcing_requirements(self.tenant)['recover']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['cores_to_tear_down'], 2)
        covered = {c['component']: c['covered_by_teardown'] for c in rows[0]['components']}
        self.assertEqual(covered, {"Housing": 2.0, "Body": 2.0})

    def test_recovered_stock_on_the_shelf_is_used_first(self):
        """One recovered housing already on the shelf and one unit to rebuild: nothing
        to tear down."""
        self._accept_recovered_housing()
        self._rebuild(cores=1)
        self.assertIsNone(self._recover())

    def test_a_repair_return_rebuild_raises_no_proposal(self):
        """Its replacements are always purchases — it keeps its own parts and is never
        offered the pool — so tearing down cores for it would help nobody."""
        self._rebuild(cores=3, mode="REPAIR_RETURN")
        self.assertIsNone(self._recover())

    def test_a_new_build_raises_no_proposal(self):
        self._work_order(qty=5)
        self.assertIsNone(self._recover())

    def test_mixed_demand_proposes_for_the_exchange_share_only(self):
        """1 exchange rebuild and 4 new builds: 5 short, but only the rebuild's housing
        may come from teardown."""
        self._rebuild(cores=1)
        self._work_order(qty=4)
        self.assertEqual(self._housing()['qty_short'], 5)
        row = self._recover()
        self.assertEqual(row['cores_to_tear_down'], 1)
        self.assertEqual(row['components'][0]['covered_by_teardown'], 1.0)

    def test_a_made_in_house_component_is_still_pool_demand(self):
        """A recovered part replaces a MADE one as well as a bought one. Pool demand was
        once recorded only on BUY lines, which left the lane blind wherever the
        recoverable parts are built in-house — the dev dataset's nozzles, for one."""
        BOMLine.objects.filter(pk=self.core_line.pk).update(source="MAKE")
        self._rebuild(cores=1)
        row = self._recover()
        self.assertEqual(row['cores_to_tear_down'], 1)
        self.assertEqual(row['components'][0]['component'], "Housing")
        self.assertIsNone(self._housing())   # a MAKE line is not on the buy list

    def test_a_line_forbidding_harvested_parts_raises_no_proposal(self):
        """A line override can forbid harvested parts — a customer contract, say. That
        demand is a purchase even on an exchange rebuild."""
        BOMLine.objects.filter(pk=self.core_line.pk).update(allow_harvested=False)
        self._rebuild(cores=2)
        self.assertIsNone(self._recover())
        self.assertEqual(self._housing()['qty_short'], 2)

    def test_no_authored_teardown_duration_means_no_start_by_date(self):
        """A made-up lead time reads as authored fact and gets scheduled against. This
        fixture authors no teardown process, so the date is absent, not guessed."""
        self._rebuild(cores=1)
        row = self._recover()
        self.assertIsNone(row['start_by'])
        self.assertIsNone(row['lead_time_days'])


class _TeardownProcessFixture(_RecoverableFixture):
    """Adds an approved teardown process with authored durations (10 h + 14 h)."""

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


class TeardownLeadTimeTests(_TeardownProcessFixture):
    """Teardown lead time is summed from the authored step durations of the process a
    planned teardown would actually use — the same numbers scheduling plans against."""

    def test_lead_time_is_the_sum_of_authored_step_durations(self):
        from Tracker.services.reman.recovery import teardown_lead_days
        # 10h + 14h = 24h = 1 day.
        self.assertEqual(teardown_lead_days(self.core_type, tenant=self.tenant), 1)

    def test_a_part_day_still_occupies_a_whole_day(self):
        """Rounding down would promise the components a day earlier than the shop can
        produce them."""
        from datetime import timedelta as _td
        from Tracker.models import Steps
        from Tracker.services.reman.recovery import teardown_lead_days
        Steps.objects.filter(tenant=self.tenant, name="Teardown 2").update(
            expected_duration=_td(hours=1))
        self.assertEqual(teardown_lead_days(self.core_type, tenant=self.tenant), 1)

    def test_the_proposal_carries_a_start_by_date(self):
        need = date.today() + timedelta(days=60)
        self._rebuild(cores=1, start=need)
        row = self._recover()
        self.assertEqual(row['lead_time_days'], 1)
        self.assertEqual(row['start_by'], need - timedelta(days=1))

    def test_it_follows_the_core_types_chosen_process(self):
        """With two teardown processes, the lead time is the one `plan_teardown` would
        use — the core type's default — not whichever sorts first."""
        from datetime import timedelta as _td
        from Tracker.models import ProcessStep, Steps
        from Tracker.services.reman.recovery import teardown_lead_days
        slow = Processes.objects.create(
            tenant=self.tenant, name="Deep strip", part_type=self.core_type,
            status="APPROVED", is_current_version=True, is_disassembly=True)
        step = Steps.objects.create(tenant=self.tenant, name="Deep", part_type=self.core_type,
                                    expected_duration=_td(days=5))
        ProcessStep.objects.create(process=slow, step=step, order=1)
        PartTypes.objects.filter(pk=self.core_type.pk).update(default_disassembly_process=slow)
        self.core_type.refresh_from_db()
        self.assertEqual(teardown_lead_days(self.core_type, tenant=self.tenant), 5)

    def test_an_ambiguous_process_yields_no_lead_time(self):
        """Two teardown processes and no default: `plan_teardown` would refuse to
        guess, so the lead time does not guess either."""
        from Tracker.services.reman.recovery import teardown_lead_days
        Processes.objects.create(
            tenant=self.tenant, name="Other", part_type=self.core_type,
            status="APPROVED", is_current_version=True, is_disassembly=True)
        self.assertIsNone(teardown_lead_days(self.core_type, tenant=self.tenant))

    def test_a_process_with_no_durations_yields_no_lead_time(self):
        """Blank durations are an unanswered question, not a zero-day teardown."""
        from Tracker.models import Steps
        from Tracker.services.reman.recovery import teardown_lead_days
        Steps.objects.filter(tenant=self.tenant, name__startswith="Teardown").update(
            expected_duration=None)
        self.assertIsNone(teardown_lead_days(self.core_type, tenant=self.tenant))


class PlanTeardownTests(_TeardownProcessFixture):
    """Accepting a proposal plans a teardown: cores committed, nothing started."""

    def _plan(self, cores, start_by=None):
        from Tracker.services.reman.teardown import plan_teardown
        return plan_teardown(cores, self.user, start_by=start_by)

    def test_it_plans_a_pending_work_order_dated_to_start_by(self):
        start = date.today() + timedelta(days=20)
        wo = self._plan(self.bank, start_by=start)
        self.assertEqual(wo.workorder_status, WorkOrderStatus.PENDING)
        self.assertEqual(wo.expected_start, start)
        self.assertEqual(wo.process, self.dis_proc)
        self.assertEqual(wo.quantity, 2)

    def test_it_commits_the_cores_without_starting_them(self):
        """Linked to the work order, still RECEIVED: disassembly begins when an
        operator starts the first step, not when a planner accepts."""
        wo = self._plan(self.bank)
        for core in self.bank:
            core.refresh_from_db()
            self.assertEqual(core.work_order_id, wo.id)
            self.assertEqual(core.status, "RECEIVED")

    def test_an_accepted_core_is_not_proposed_again(self):
        """Counted as yield on its way instead. Without this, accepting would make the
        same proposal reappear."""
        self._rebuild(cores=5)
        self._plan([self.bank[0]])
        row = self._recover()
        self.assertEqual(row['cores_in_flight'], 1)
        self.assertEqual([c['core_number'] for c in row['candidate_cores']], ["RC-NEW"])
        self.assertEqual(row['components'][0]['in_flight'], 1.0)

    def test_accepting_everything_needed_clears_the_proposal(self):
        self._rebuild(cores=1)
        self._plan([self.bank[0]])
        self.assertIsNone(self._recover())

    def test_it_refuses_a_core_that_is_not_waiting(self):
        from Tracker.models import Core
        Core.objects.filter(pk=self.bank[0].pk).update(status="IN_DISASSEMBLY")
        self.bank[0].refresh_from_db()
        with self.assertRaisesMessage(ValueError, "is not RECEIVED"):
            self._plan(self.bank)

    def test_it_refuses_a_core_already_committed(self):
        self._plan([self.bank[0]])
        self.bank[0].refresh_from_db()
        with self.assertRaisesMessage(ValueError, "already linked"):
            self._plan([self.bank[0]])

    def test_two_plans_in_one_second_get_distinct_ids(self):
        """The ERP id carries microseconds: accepting two proposals back to back used
        to be able to mint the same id."""
        a = self._plan([self.bank[0]])
        b = self._plan([self.bank[1]])
        self.assertNotEqual(a.ERP_id, b.ERP_id)

    def test_a_planned_teardown_is_scheduled_from_its_first_step(self):
        """The scheduler already handles a unit that has not started: it enters at the
        process's first step. Pinned so "planned" keeps meaning "on the board"."""
        from Tracker.services.scheduling.data import get_active_workorders
        wo = self._plan(self.bank, start_by=date.today() + timedelta(days=3))
        jobs = [j for j in get_active_workorders(self.tenant) if j.wo_id == wo.id]
        self.assertEqual(len(jobs), 1)
        self.assertEqual(len(jobs[0].cores), 2)


class UsableStockPartsTests(_RecoverableFixture):
    """The one place coverage counts finished parts. Three things sit on the shelf and
    are not available: archived rows, parts reserved to a customer's core, and — for
    anything that does not take pooled parts — recovered parts."""

    def setUp(self):
        super().setUp()
        from Tracker.models import Parts, PartsStatus
        self._Parts, self._IN_STOCK = Parts, PartsStatus.IN_STOCK

    def _part(self, erp, **extra):
        return self._Parts.objects.create(
            tenant=self.tenant, ERP_id=erp, part_type=self.housing,
            part_status=self._IN_STOCK, **extra)

    def _count(self, for_reman):
        from Tracker.services.mes.bom import usable_stock_parts
        return usable_stock_parts(self.housing.id, tenant=self.tenant,
                                  for_reman=for_reman).count()

    def test_ordinary_stock_counts_for_either(self):
        self._part("H-NEW-1")
        self.assertEqual(self._count(for_reman=False), 1)
        self.assertEqual(self._count(for_reman=True), 1)

    def test_archived_stock_counts_for_neither(self):
        self._part("H-ARCH-1", archived=True)
        self.assertEqual(self._count(for_reman=False), 0)
        self.assertEqual(self._count(for_reman=True), 0)

    def test_a_part_reserved_to_a_core_counts_for_neither(self):
        self._part("H-RES-1", reserved_for_core=self.bank[0])
        self.assertEqual(self._count(for_reman=False), 0)
        self.assertEqual(self._count(for_reman=True), 0)

    def test_recovered_stock_counts_only_where_pooled_parts_are_taken(self):
        self._accept_recovered_housing()
        self.assertEqual(self._count(for_reman=False), 0)
        self.assertEqual(self._count(for_reman=True), 1)


class RebuildPlanReadsTheUnitsRealStateTests(_RecoverableFixture):
    """Two defects in the rebuild plan that the buy list now depends on."""

    def _plan(self, wo):
        from Tracker.services.reman.rebuild import resolve_rebuild_plan
        return resolve_rebuild_plan(wo.cores.get())

    def test_a_unit_in_rebuild_is_not_told_it_has_not_been_torn_down(self):
        """`torn_down` read `status == 'DISASSEMBLED'`, so a unit already IN_REBUILD got
        "has not finished teardown … every slot reads as a purchase" on the very page
        its rebuild is run from."""
        plan = self._plan(self._rebuild(cores=1))
        self.assertFalse([w for w in plan.warnings if "not finished teardown" in w])

    def test_an_unopened_unit_still_is(self):
        plan = self._plan(self._rebuild(cores=1, mode="REPAIR_RETURN", status="RECEIVED"))
        self.assertTrue([w for w in plan.warnings if "not finished teardown" in w])

    def test_a_recovered_part_no_longer_in_stock_is_not_a_pool_candidate(self):
        """Pool candidates filtered on reserved and archived only, so a recovered part
        already installed elsewhere could still be offered."""
        from Tracker.models import Parts, PartsStatus
        part = self._accept_recovered_housing()
        wo = self._rebuild(cores=1)
        self.assertEqual(self._plan(wo).slots[0].resolution, "REPLACE_POOL")

        other = [s for s in PartsStatus.values if s != PartsStatus.IN_STOCK][0]
        Parts.objects.filter(pk=part.pk).update(part_status=other)
        slot = self._plan(wo).slots[0]
        self.assertEqual(slot.resolution, "REPLACE_BUY")
        self.assertFalse([c for c in slot.candidates if c.kind == "HARVESTED_POOL"])


class PerWorkOrderViewAgreesTests(_RecoverableFixture):
    """The single-job readout reads reman demand the same way the buy list does, so
    the two cannot tell a planner different things about one order."""

    def _housing(self, wo):
        return [r for r in work_order_material_requirements(wo)['rows']
                if r['component'] == "Housing"][0]

    def test_an_exchange_teardown_needs_no_housings(self):
        self.assertEqual(self._housing(self._rebuild(cores=3, status="IN_DISASSEMBLY"))['quantity'], 0.0)

    def test_an_exchange_rebuild_needs_its_replacements(self):
        row = self._housing(self._rebuild(cores=3))
        self.assertEqual(row['quantity'], 3.0)
        self.assertEqual(row['recoverable'], 2.0)

    def test_an_unopened_repair_return_unit_is_a_forecast(self):
        row = self._housing(self._rebuild(cores=4, mode="REPAIR_RETURN", status="RECEIVED"))
        self.assertEqual(row['quantity'], 0.0)
        self.assertEqual(row['forecast'], 2.0)
        self.assertEqual(row['short_qty'], 0.0)
        self.assertEqual(row['recoverable'], 0.0)

    def test_a_new_build_is_unchanged(self):
        wo = self._work_order(qty=4)
        rows = [r for r in work_order_material_requirements(wo)['rows']
                if r['component'] == "Housing"]
        self.assertEqual(rows[0]['quantity'], 4.0)
        self.assertEqual(rows[0]['forecast'], 0.0)
        self.assertEqual(rows[0]['recoverable'], 0.0)
