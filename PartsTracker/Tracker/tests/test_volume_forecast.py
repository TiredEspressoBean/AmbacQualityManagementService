"""Volume forecast and tentative demand — the outlook beyond firm orders (2026-11-02).

A forecast is part type × month × quantity. Firm orders and RFI deals CONSUME it, so a
month plans max(forecast, firm + tentative): the forecast adds only its unclaimed
remainder. RFI lines are tentative — planned for, shaded apart, and refused by
`plan_order_line` until the order moves past RFI.
"""
import io
from datetime import date, timedelta
from datetime import time as dtime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from Tracker.models import (
    BOM, BOMLine, Material, OrderLine, Orders, PartTypes, Processes, ProcessStatus,
    ProcessStep, Shift, Steps, StepTiming, Tenant, TenantGroup, UserRole, VolumeForecast,
    WorkCenter, WorkOrder,
)
from Tracker.services.mes.order_line import CannotPlan, plan_order_line
from Tracker.services.planning import forecast as fc
from Tracker.services.planning import rccp
from Tracker.tests.base import TenantContextMixin


class _ForecastFixture(TenantContextMixin):
    """One operator on a Mon-Fri 8h shift; a Widget built in one 60 min step, so one
    unit is one labor hour."""

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="FC", slug="forecast", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.user = get_user_model().objects.create_user(
            username="fc-planner", email="fc@c.test", password="x", tenant=self.tenant)
        shift = Shift.objects.create(
            tenant=self.tenant, code="DAY", name="Day", start_time=dtime(8, 0),
            end_time=dtime(16, 0), days_of_week="0,1,2,3,4", is_active=True)
        self.user.default_shift = shift
        self.user.save(update_fields=["default_shift"])
        self.wc = WorkCenter.objects.create(tenant=self.tenant, name="Cell A", code="A")
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Widget", ERP_id="W-100")
        self.process = Processes.objects.create(
            tenant=self.tenant, name="W", part_type=self.pt, status=ProcessStatus.APPROVED)
        self.step = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name="Cut",
                                         step_type="TASK", work_center=self.wc)
        StepTiming.objects.create(tenant=self.tenant, step=self.step, cycle_time_minutes=60)
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)
        self.this_month = fc.month_start(timezone.localdate())
        # Far enough out that lead time never pushes it into the past.
        self.month = fc.add_months(self.this_month, 6)

    def _line(self, qty, due, status="PENDING", n=1):
        order = Orders.objects.create(tenant=self.tenant, name=f"Order {n}", order_status=status)
        return OrderLine.objects.create(tenant=self.tenant, order=order, line_number=1,
                                        part_type=self.pt, quantity=qty, due_date=due)

    def _mid(self, month):
        return month + timedelta(days=14)


class ForecastCellTests(_ForecastFixture, TestCase):

    def test_set_update_unchanged_and_clear(self):
        set_ = lambda q: fc.set_forecast(tenant=self.tenant, part_type=self.pt,  # noqa: E731
                                         month=self._mid(self.month), quantity=q)
        self.assertEqual(set_(40), fc.CREATED)
        self.assertEqual(set_(40), fc.UNCHANGED)
        self.assertEqual(set_(55), fc.UPDATED)
        row = VolumeForecast.objects.get(part_type=self.pt, archived=False)
        self.assertEqual((row.month, row.quantity), (self.month, 55))   # stored as the 1st
        self.assertEqual(set_(None), fc.CLEARED)
        self.assertFalse(VolumeForecast.objects.filter(archived=False).exists())
        # The cleared row survives, archived: the trail keeps what the forecast said.
        self.assertTrue(VolumeForecast.unscoped.filter(tenant=self.tenant, archived=True).exists())
        self.assertEqual(set_(10), fc.CREATED, "a cleared cell can be set again")

    def test_months_as_planners_write_them(self):
        for text in ("2027-03", "3/2027", "Mar 2027", "March-27", "2027-03-15"):
            self.assertEqual(fc.parse_month(text), date(2027, 3, 1), text)
        self.assertIsNone(fc.parse_month("2027-13"))
        self.assertIsNone(fc.parse_month("soon"))


class ForecastImportTests(_ForecastFixture, TestCase):

    def _import(self, text):
        return fc.import_forecast(tenant=self.tenant, file=io.BytesIO(text.encode()),
                                  filename="forecast.csv")

    def test_rows_land_and_a_bad_row_is_reported_not_fatal(self):
        out = self._import("Item*,Month*,Quantity*\nW-100,2027-03,40\nNOPE,2027-03,5\n"
                           "Widget,2027-04,12\nW-100,later,3\n")
        self.assertEqual((out["created"], out["errors"]), (2, 2))
        self.assertEqual(
            {(r.month, r.quantity) for r in VolumeForecast.objects.filter(archived=False)},
            {(date(2027, 3, 1), 40), (date(2027, 4, 1), 12)})
        self.assertIn("No part type 'NOPE'", out["rows"][1]["detail"])

    def test_rerun_replaces_the_months_it_names_and_leaves_the_rest(self):
        self._import("Item,Month,Quantity\nW-100,2027-03,40\nW-100,2027-04,12\n")
        out = self._import("Item,Month,Quantity\nW-100,2027-03,45\nW-100,2027-05,0\n")
        self.assertEqual((out["updated"], out["unchanged"]), (1, 1))
        self.assertEqual(
            {(r.month, r.quantity) for r in VolumeForecast.objects.filter(archived=False)},
            {(date(2027, 3, 1), 45), (date(2027, 4, 1), 12)})

    def test_a_zero_clears_a_month(self):
        self._import("Item,Month,Quantity\nW-100,2027-03,40\n")
        out = self._import("Item,Month,Quantity\nW-100,2027-03,0\n")
        self.assertEqual(out["cleared"], 1)
        self.assertFalse(VolumeForecast.objects.filter(archived=False).exists())


class ForecastConsumptionTests(_ForecastFixture, TestCase):
    """max(forecast, firm + tentative), by part type and month due."""

    def _cell(self):
        return fc.unclaimed_forecast(self.tenant, self.month, self.month)[(self.pt.id, self.month)]

    def test_firm_and_tentative_orders_use_up_the_forecast(self):
        fc.set_forecast(tenant=self.tenant, part_type=self.pt, month=self.month, quantity=50)
        self._line(20, self._mid(self.month), n=1)
        self._line(10, self._mid(self.month), status="RFI", n=2)
        cell = self._cell()
        self.assertEqual({k: cell[k] for k in ('forecast', 'firm', 'tentative', 'unclaimed')},
                         {'forecast': 50, 'firm': 20, 'tentative': 10, 'unclaimed': 20})

    def test_a_cell_reports_the_true_total_ordered_beside_what_it_lost(self):
        """"N ordered" is what orders due that month ask for, in full — even beyond the
        forecast — not the capped consumption."""
        fc.set_forecast(tenant=self.tenant, part_type=self.pt, month=self.month, quantity=50)
        self._line(100, self._mid(self.month), n=1)
        self._line(20, self._mid(self.month), status="RFI", n=2)
        cell = self._cell()
        self.assertEqual((cell["ordered_firm"], cell["ordered_tentative"]), (100, 20))
        self.assertEqual((cell["firm"], cell["tentative"], cell["unclaimed"]), (50, 0, 0))

    def test_over_forecast_is_judged_after_consumption(self):
        """Orders a later month's forecast covers aren't "over"; only what no forecast in
        the window could absorb is."""
        nxt = fc.add_months(self.month, 1)
        fc.set_forecast(tenant=self.tenant, part_type=self.pt, month=self.month, quantity=50)
        fc.set_forecast(tenant=self.tenant, part_type=self.pt, month=nxt, quantity=50)
        self._line(80, self._mid(self.month))
        self.assertEqual(self._cell()["over_forecast"], 0, "30 covered by next month")
        self._line(70, self._mid(self.month), n=2)
        self.assertEqual(self._cell()["over_forecast"], 50, "150 asked, 100 reachable")

    def test_an_archived_part_types_forecast_neither_loads_nor_shows(self):
        fc.set_forecast(tenant=self.tenant, part_type=self.pt, month=self.month, quantity=50)
        PartTypes.objects.filter(pk=self.pt.pk).update(archived=True)
        self.assertEqual(fc.unclaimed_forecast(self.tenant, self.month, self.month), {})
        self.assertEqual(fc.grid(self.tenant, self.this_month, 12)["rows"], [])

    def test_orders_beyond_the_forecast_leave_nothing_unclaimed(self):
        fc.set_forecast(tenant=self.tenant, part_type=self.pt, month=self.month, quantity=10)
        self._line(30, self._mid(self.month))
        self.assertEqual(self._cell()['unclaimed'], 0)

    def test_work_on_a_line_is_not_counted_twice_but_a_stock_build_counts(self):
        fc.set_forecast(tenant=self.tenant, part_type=self.pt, month=self.month, quantity=50)
        line = self._line(20, self._mid(self.month))
        WorkOrder.objects.create(tenant=self.tenant, ERP_id="WO-PEG", quantity=20,
                                 process=self.process, order_line=line,
                                 expected_completion=self._mid(self.month))
        WorkOrder.objects.create(tenant=self.tenant, ERP_id="WO-STOCK", quantity=5,
                                 process=self.process, expected_completion=self._mid(self.month))
        self.assertEqual(self._cell()['firm'], 25)

    def test_a_reman_line_claims_no_new_build_forecast_from_entry(self):
        """The line's fulfilment decides, when it is entered — not the day its cores
        arrive (an exchange's core may come after the due date)."""
        fc.set_forecast(tenant=self.tenant, part_type=self.pt, month=self.month, quantity=50)
        for n, mode in ((1, "REPAIR_RETURN"), (2, "EXCHANGE")):
            line = self._line(20, self._mid(self.month), n=n)
            OrderLine.objects.filter(pk=line.pk).update(fulfilment=mode)
        self._line(10, self._mid(self.month), n=3)            # a new build: claims
        self.assertEqual((self._cell()["firm"], self._cell()["unclaimed"]), (10, 40))

    def test_reman_work_on_no_line_claims_nothing(self):
        fc.set_forecast(tenant=self.tenant, part_type=self.pt, month=self.month, quantity=50)
        reman = Processes.objects.create(tenant=self.tenant, name="Reman", part_type=self.pt,
                                         status=ProcessStatus.APPROVED, is_remanufactured=True)
        WorkOrder.objects.create(tenant=self.tenant, ERP_id="WO-RM", quantity=5, process=reman,
                                 expected_completion=self._mid(self.month))
        self.assertEqual(self._cell()["unclaimed"], 50)

    def test_received_cores_on_a_new_build_line_raise_a_warning_not_the_rule(self):
        from Tracker.models import Companies
        from Tracker.services.mes.order_line import fulfilment_warning
        from Tracker.services.reman.core_part import create_core
        fc.set_forecast(tenant=self.tenant, part_type=self.pt, month=self.month, quantity=50)
        line = self._line(20, self._mid(self.month))
        create_core(tenant=self.tenant, core_number="C-1", core_type=self.pt, order=line.order,
                    fulfilment_mode="REPAIR_RETURN", status="RECEIVED",
                    customer=Companies.objects.create(tenant=self.tenant, name="Fleet"),
                    received_date=timezone.localdate(), received_by=self.user)
        self.assertEqual(self._cell()["firm"], 20, "still claims: the line says new build")
        self.assertIn("Repair & return", fulfilment_warning(line))
        OrderLine.objects.filter(pk=line.pk).update(fulfilment="REPAIR_RETURN")
        line.refresh_from_db()
        self.assertIsNone(fulfilment_warning(line))

    def test_cancelled_orders_and_teardowns_claim_nothing(self):
        fc.set_forecast(tenant=self.tenant, part_type=self.pt, month=self.month, quantity=50)
        self._line(20, self._mid(self.month), status="CANCELLED")
        teardown = Processes.objects.create(tenant=self.tenant, name="Tear", part_type=self.pt,
                                            status=ProcessStatus.APPROVED, is_disassembly=True)
        WorkOrder.objects.create(tenant=self.tenant, ERP_id="WO-TD", quantity=5, process=teardown,
                                 expected_completion=self._mid(self.month))
        self.assertEqual(self._cell()['unclaimed'], 50)


class ConsumptionWindowTests(_ForecastFixture, TestCase):
    """An order uses up forecast in nearby months: its own first, then earlier months
    nearest first, then later — within the tenant's window, never below zero."""

    def _set(self, month, qty):
        fc.set_forecast(tenant=self.tenant, part_type=self.pt, month=month, quantity=qty)

    def _cells(self):
        lo, hi = fc.add_months(self.month, -3), fc.add_months(self.month, 3)
        return {m: c for (pt, m), c in fc.unclaimed_forecast(self.tenant, lo, hi).items()}

    def _window(self, months):
        from Tracker.models import OptimizationConfig
        OptimizationConfig.objects.update_or_create(
            tenant=self.tenant, defaults={"forecast_consumption_window_months": months})

    def test_an_order_with_no_forecast_in_its_month_consumes_the_month_before_then_after(self):
        before, after = fc.add_months(self.month, -1), fc.add_months(self.month, 1)
        self._set(before, 10)
        self._set(after, 10)
        self._line(15, self._mid(self.month))
        cells = self._cells()
        self.assertEqual(cells[before]["unclaimed"], 0, "earlier month first")
        self.assertEqual(cells[after]["unclaimed"], 5, "then the later one")
        self.assertEqual(cells[before]["claimed_from"],
                         [{"band": "firm", "quantity": 10, "from_month": f"{self.month:%Y-%m}"}])

    def test_an_order_larger_than_its_month_spills_into_the_window(self):
        after = fc.add_months(self.month, 1)
        self._set(self.month, 20)
        self._set(after, 20)
        self._line(30, self._mid(self.month), status="RFI")
        cells = self._cells()
        self.assertEqual((cells[self.month]["unclaimed"], cells[self.month]["tentative"]), (0, 20))
        self.assertEqual((cells[after]["unclaimed"], cells[after]["tentative"]), (10, 10))

    def test_nothing_goes_below_zero_and_nothing_reaches_past_the_window(self):
        far = fc.add_months(self.month, 2)
        self._set(far, 10)
        self._line(500, self._mid(self.month))
        self.assertEqual(self._cells()[far]["unclaimed"], 10, "two months out is past a 1-month window")

    def test_window_zero_is_same_month_only(self):
        before = fc.add_months(self.month, -1)
        self._set(before, 10)
        self._line(15, self._mid(self.month))
        self._window(0)
        self.assertEqual(self._cells()[before]["unclaimed"], 10)


class ConsumptionAnchorTests(_ForecastFixture, TestCase):
    """Consumption is computed from the current month and then sliced, so a cell reads
    the same whichever range is asked about; past-due orders consume nothing."""

    def _cell(self, month, first, last):
        return fc.unclaimed_forecast(self.tenant, first, last)[(self.pt.id, month)]["unclaimed"]

    def test_a_cell_does_not_depend_on_the_range_asked_about(self):
        m1, m2, m3 = (fc.add_months(self.this_month, k) for k in (1, 2, 3))
        for m in (m1, m2, m3):
            fc.set_forecast(tenant=self.tenant, part_type=self.pt, month=m, quantity=10)
        # M1's order takes M1 then spills into M2; M2's order, finding M2 gone, takes M3.
        self._line(25, self._mid(m1), n=1)
        self._line(10, self._mid(m2), n=2)
        narrow = self._cell(m3, m3, m3)
        wide = self._cell(m3, self.this_month, fc.add_months(m3, 3))
        self.assertEqual((narrow, wide), (0, 0))

    def test_a_past_due_order_consumes_no_forecast(self):
        nxt = fc.add_months(self.this_month, 1)
        fc.set_forecast(tenant=self.tenant, part_type=self.pt, month=self.this_month, quantity=30)
        fc.set_forecast(tenant=self.tenant, part_type=self.pt, month=nxt, quantity=30)
        self._line(20, self.this_month - timedelta(days=10))   # due last month: overdue
        cells = fc.unclaimed_forecast(self.tenant, self.this_month, nxt)
        self.assertEqual((cells[(self.pt.id, self.this_month)]["unclaimed"],
                          cells[(self.pt.id, nxt)]["unclaimed"]), (30, 30))


class PlantMonthTests(_ForecastFixture, TestCase):
    """Buckets are the plant's months, matching the fence (which uses the plant's day)."""

    def test_buckets_follow_the_plant_month_not_utc(self):
        from datetime import datetime, timezone as dt_tz
        from unittest import mock
        self.tenant.default_timezone = "America/Chicago"
        self.tenant.save(update_fields=["default_timezone"])
        # 03:00 UTC on 1 December is still 30 November in Chicago.
        now = datetime(2026, 12, 1, 3, 0, tzinfo=dt_tz.utc)
        with mock.patch.object(rccp.timezone, "now", return_value=now):
            buckets = rccp.build_capacity_load(self.tenant, months=2)["buckets"]
        self.assertEqual(buckets, ["2026-11", "2026-12"])


class DemandTimeFenceTests(_ForecastFixture, TestCase):
    """Inside the fence only orders are planned: the forecast is shown, not loaded."""

    def setUp(self):
        super().setUp()
        fc.set_forecast(tenant=self.tenant, part_type=self.pt, month=self.this_month, quantity=40)

    def _forecast_units(self):
        return rccp.build_capacity_load(self.tenant, months=3)["forecast_demand"]["units"]

    def _fence(self, days):
        from Tracker.models import OptimizationConfig
        OptimizationConfig.objects.update_or_create(tenant=self.tenant,
                                                    defaults={"demand_time_fence_days": days})

    def test_a_fence_covering_the_rest_of_the_month_keeps_its_forecast_out_of_the_plan(self):
        # 31 days from today covers what is left of any month (the default 30 does on
        # every day but the 1st of a 31-day month).
        self._fence(31)
        cell = fc.unclaimed_forecast(self.tenant, self.this_month, self.this_month)[(self.pt.id, self.this_month)]
        self.assertTrue(cell["fenced"])
        self.assertEqual((cell["unclaimed"], cell["planned"]), (40, 0), "still shown, not planned")
        self.assertEqual(self._forecast_units(), 0)

    def test_fence_zero_plans_it_again(self):
        self._fence(0)
        self.assertEqual(self._forecast_units(), 40)

    def test_a_month_straddling_the_fence_plans_its_days_past_it(self):
        from Tracker.services.core.clock import tenant_today
        nxt = fc.add_months(self.this_month, 1)
        fc.set_forecast(tenant=self.tenant, part_type=self.pt, month=nxt, quantity=62)
        days_in = (fc.add_months(nxt, 1) - nxt).days
        self._fence((nxt - tenant_today(self.tenant)).days + 10)   # ends on the 11th
        cell = fc.unclaimed_forecast(self.tenant, nxt, nxt)[(self.pt.id, nxt)]
        held = round(62 * 10 / days_in)
        self.assertFalse(cell["fenced"], "only wholly fenced months are muted")
        self.assertEqual((cell["fenced_quantity"], cell["planned"]), (held, 62 - held))
        grid = fc.grid(self.tenant, self.this_month, 3)
        self.assertEqual(grid["fenced_months"], [f"{self.this_month:%Y-%m}"])


class CapableToPromiseForecastTests(_ForecastFixture, TestCase):
    """CTP sees everything planned — order lines (firm and RFI) and unclaimed forecast,
    not only work orders — and a candidate the forecast already expected consumes that
    forecast instead of adding load. One unit is one labor hour here, against roughly
    176 h a month of one operator."""

    def setUp(self):
        super().setUp()
        from Tracker.models import Equipments
        machine = Equipments.objects.create(tenant=self.tenant, name="M-1",
                                            is_schedulable=True, runs_unattended=False)
        self.wc.equipment.add(machine)
        # Another product on the same crew and cell, to carry load the candidate can't use.
        self.gadget = PartTypes.objects.create(tenant=self.tenant, name="Gadget")
        proc = Processes.objects.create(tenant=self.tenant, name="G", part_type=self.gadget,
                                        status=ProcessStatus.APPROVED)
        step = Steps.objects.create(tenant=self.tenant, part_type=self.gadget, name="Cut G",
                                    step_type="TASK", work_center=self.wc)
        StepTiming.objects.create(tenant=self.tenant, step=step, cycle_time_minutes=60)
        ProcessStep.objects.create(process=proc, step=step, order=1)
        # The fence is in days from today, so with it on, next month's plannable share
        # depends on the date the test runs. These tests are about CTP, not the fence.
        from Tracker.models import OptimizationConfig
        OptimizationConfig.objects.update_or_create(tenant=self.tenant,
                                                    defaults={"demand_time_fence_days": 0})
        self.target_month = fc.add_months(self.this_month, 2)
        self.due = fc.add_months(self.target_month, 1) - timedelta(days=1)

    def _quote(self, qty=100):
        return rccp.capable_to_promise(self.tenant, str(self.pt.id), qty, self.due)

    def _forecast(self, part_type, qty):
        for k in (1, 2):
            fc.set_forecast(tenant=self.tenant, part_type=part_type,
                            month=fc.add_months(self.this_month, k), quantity=qty)

    def test_with_no_lines_and_no_forecast_the_answer_is_unchanged(self):
        q = self._quote()
        self.assertTrue(q["feasible"])
        self.assertEqual((q["forecast_absorbed"], q["needs_capacity_quantity"]), (0, 100))

    def test_unclaimed_forecast_alone_can_refuse_a_promise(self):
        self._forecast(self.gadget, 600)
        q = self._quote()
        self.assertFalse(q["feasible"])
        labor = next(b for b in q["binding_resources"] if b["resource"] == "Labor")
        self.assertGreater(labor["load_by_band"].get("forecast", 0), 1000)

    def test_a_candidate_inside_an_earlier_months_unclaimed_forecast_is_promisable(self):
        """Last month's forecast is placed before the due month: its hours stand."""
        earlier = fc.add_months(self.this_month, 1)
        fc.set_forecast(tenant=self.tenant, part_type=self.pt, month=earlier, quantity=600)
        q = self._quote()
        self.assertTrue(q["feasible"], q.get("binding_resources"))
        self.assertEqual((q["forecast_absorbed"], q["needs_capacity_quantity"]), (100, 0))
        self.assertEqual(q["forecast_absorbed_from"],
                         [{"month": f"{earlier:%Y-%m}", "quantity": 100, "rebooked": False}])
        self.assertEqual(q["work_content_hours"]["labor"], 100.0, "the whole order's content")

    def test_a_later_months_forecast_is_never_used(self):
        later = fc.add_months(self.target_month, 1)
        fc.set_forecast(tenant=self.tenant, part_type=self.pt, month=later, quantity=600)
        q = self._quote()
        self.assertEqual((q["forecast_absorbed"], q["needs_capacity_quantity"]), (0, 100))

    def test_the_due_months_forecast_must_fit_by_the_due_date(self):
        """The reported case: a big order due on the 5th rode on its month's forecast,
        whose hours were placed at month end — "feasible, needs capacity 0" on hours that
        come after the due date. Same-month units are re-booked to fit by the due date."""
        fc.set_forecast(tenant=self.tenant, part_type=self.pt, month=self.target_month, quantity=600)
        due = self.target_month + timedelta(days=4)
        q = rccp.capable_to_promise(self.tenant, str(self.pt.id), 500, due)
        self.assertEqual((q["forecast_absorbed"], q["forecast_rebooked_before_due"],
                          q["needs_capacity_quantity"]), (500, 500, 500))
        self.assertTrue(q["forecast_absorbed_from"][0]["rebooked"])
        # ~1.1 months of one operator's hours can't carry 500 h of work.
        self.assertFalse(q["feasible"])

    def test_an_rfi_lines_hours_count_against_the_promise(self):
        order = Orders.objects.create(tenant=self.tenant, name="Deal", order_status="RFI")
        OrderLine.objects.create(tenant=self.tenant, order=order, line_number=1,
                                 part_type=self.gadget, quantity=1200, due_date=self.due)
        q = self._quote()
        self.assertFalse(q["feasible"])
        labor = next(b for b in q["binding_resources"] if b["resource"] == "Labor")
        self.assertIn("tentative", labor["load_by_band"])


class ForecastPlanningTests(_ForecastFixture, TestCase):
    """The bands reach the capacity and material lanes."""

    def setUp(self):
        super().setUp()
        self.oring = Material.objects.create(tenant=self.tenant, name="O-Ring")
        bom = BOM.objects.create(tenant=self.tenant, part_type=self.pt, revision="A",
                                 bom_type="ASSEMBLY", status="RELEASED", is_current_version=True)
        BOMLine.objects.create(tenant=self.tenant, bom=bom, material=self.oring,
                               quantity=Decimal(2), source="BUY", line_number=1)

    def _load(self):
        return rccp.build_capacity_load(self.tenant, months=12)

    @staticmethod
    def _sum(series, key):
        return sum(b[key] for b in series)

    def test_unclaimed_forecast_loads_as_forecast(self):
        fc.set_forecast(tenant=self.tenant, part_type=self.pt, month=self.month, quantity=30)
        self._line(10, self._mid(self.month))
        out = self._load()
        labor = out["labor"]["series"]
        self.assertAlmostEqual(self._sum(labor, "order_line_hours"), 10.0, delta=0.5)
        self.assertAlmostEqual(self._sum(labor, "forecast_hours"), 20.0, delta=0.5)
        self.assertAlmostEqual(self._sum(labor, "load_hours"), 30.0, delta=0.5,
                               msg="max(forecast, firm): 30, not 30 + 10")
        self.assertEqual(out["forecast_demand"]["units"], 20)
        self.assertEqual(labor[0]["forecast_hours"], 0.0, "forecast six months out loads later")

    def test_rfi_lines_are_tentative(self):
        self._line(8, self._mid(self.month), status="RFI")
        out = self._load()
        labor = out["labor"]["series"]
        self.assertAlmostEqual(self._sum(labor, "tentative_hours"), 8.0, delta=0.5)
        self.assertEqual(self._sum(labor, "order_line_hours"), 0.0)
        self.assertEqual(out["unplanned_demand"]["tentative_lines"], 1)

    def test_material_carries_each_band(self):
        fc.set_forecast(tenant=self.tenant, part_type=self.pt, month=self.month, quantity=30)
        self._line(10, self._mid(self.month), n=1)
        self._line(5, self._mid(self.month), status="RFI", n=2)
        series = next(m for m in self._load()["materials"] if m["name"] == "O-Ring")["series"]
        totals: dict = {}
        for b in series:
            for band, q in b["demand_by_band"].items():
                totals[band] = totals.get(band, 0) + q
        # 10 firm + 5 tentative claim 15 of 30: 15 unclaimed. Two O-rings each.
        self.assertEqual(totals, {"firm": 20.0, "tentative": 10.0, "forecast": 30.0})

    def _oring(self):
        return next(m for m in self._load()["materials"] if m["name"] == "O-Ring")

    def test_a_shortage_only_forecast_causes_is_a_watch_not_an_order(self):
        fc.set_forecast(tenant=self.tenant, part_type=self.pt, month=self.month, quantity=30)
        m = self._oring()
        self.assertIsNone(m["order_by"])
        self.assertFalse(m["order_by_late"])
        self.assertEqual(m["watch_on"], "forecast")
        self.assertTrue(m["watch_from"])

    def test_a_shortage_an_rfi_causes_watches_on_rfi(self):
        self._line(5, self._mid(self.month), status="RFI")
        m = self._oring()
        self.assertIsNone(m["order_by"])
        self.assertEqual(m["watch_on"], "RFI")

    def test_a_firm_shortage_gets_an_order_by_and_no_watch(self):
        self._line(5, self._mid(self.month))
        fc.set_forecast(tenant=self.tenant, part_type=self.pt, month=self.month, quantity=30)
        m = self._oring()
        self.assertIsNotNone(m["order_by"])
        self.assertIsNone(m["watch_from"], "firm is short no later than the total")

    def test_forecast_for_a_part_type_with_no_routing_is_flagged(self):
        bare = PartTypes.objects.create(tenant=self.tenant, name="No Route")
        fc.set_forecast(tenant=self.tenant, part_type=bare, month=self.month, quantity=5)
        out = self._load()
        self.assertEqual(self._sum(out["labor"]["series"], "forecast_hours"), 0.0)
        self.assertEqual([u["part_type"] for u in out["forecast_demand"]["unplaceable"]], ["No Route"])
        # The units count what's IN the load — the same units the hours cost — and the
        # unplaceable ones are counted apart ("Includes 2780 units" read 3780 before).
        self.assertEqual((out["forecast_demand"]["units"],
                          out["forecast_demand"]["unplaceable_units"]), (0, 5))


class RfiPlanningRefusalTests(_ForecastFixture, TestCase):

    def test_an_rfi_line_cannot_be_planned_into_work(self):
        line = self._line(5, self._mid(self.month), status="RFI")
        with self.assertRaisesMessage(CannotPlan, "still an RFI"):
            plan_order_line(line, user=self.user)
        line.order.order_status = "PENDING"
        line.order.save(update_fields=["order_status"])
        line.refresh_from_db()
        self.assertEqual(plan_order_line(line, user=self.user).quantity, 5)


class ForecastApiTests(_ForecastFixture, TestCase):

    def _client(self, *perms):
        g = TenantGroup.objects.create(tenant=self.tenant, name=f"g-{len(perms)}", is_custom=True)
        g.permissions.add(*Permission.objects.filter(codename__in=[*perms, "full_tenant_access"]))
        UserRole.objects.create(user=self.user, group=g)
        c = APIClient()
        c.force_authenticate(user=self.user)
        c.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        return c

    def test_planner_sets_cells_and_reads_the_grid(self):
        c = self._client("view_volumeforecast", "add_volumeforecast", "change_volumeforecast")
        label = f"{self.month:%Y-%m}"
        r = c.post("/api/VolumeForecasts/set-cells/",
                   {"cells": [{"part_type": str(self.pt.id), "month": label, "quantity": 12}]},
                   format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["changed"], 1)
        grid = c.get("/api/VolumeForecasts/grid/").json()
        self.assertEqual(len(grid["months"]), 24)
        self.assertEqual(grid["rows"][0]["cells"][label],
                         {"forecast": 12, "firm": 0, "tentative": 0, "unclaimed": 12,
                          "ordered_firm": 0, "ordered_tentative": 0, "over_forecast": 0,
                          "fenced": False, "fenced_quantity": 0, "planned": 12,
                          "claimed_from": []})

    def test_a_superseded_part_type_is_refused(self):
        c = self._client("view_volumeforecast", "add_volumeforecast", "change_volumeforecast")
        old = PartTypes.objects.create(tenant=self.tenant, name="Old", is_current_version=False)
        r = c.post("/api/VolumeForecasts/set-cells/",
                   {"cells": [{"part_type": str(old.id), "month": "2027-03", "quantity": 5}]},
                   format="json")
        self.assertEqual(r.status_code, 400)
        self.assertFalse(VolumeForecast.objects.exists())

    def test_demand_settings_are_bounded(self):
        from Tracker.serializers.scheduling import OptimizationConfigSerializer
        from Tracker.models import OptimizationConfig
        cfg = OptimizationConfig.objects.create(tenant=self.tenant)
        ser = OptimizationConfigSerializer(cfg, data={"demand_time_fence_days": 366}, partial=True)
        self.assertFalse(ser.is_valid())
        ser = OptimizationConfigSerializer(cfg, data={"forecast_consumption_window_months": 12}, partial=True)
        self.assertTrue(ser.is_valid(), ser.errors)

    def test_a_stale_forecast_on_a_superseded_part_type_can_still_be_cleared(self):
        """Setting refuses a non-current part type, but a CLEAR always goes through — or
        a stale row could never be removed."""
        c = self._client("view_volumeforecast", "add_volumeforecast", "change_volumeforecast")
        old = PartTypes.objects.create(tenant=self.tenant, name="Old", is_current_version=False)
        VolumeForecast.objects.create(tenant=self.tenant, part_type=old,
                                      month=date(2027, 3, 1), quantity=5)
        r = c.post("/api/VolumeForecasts/set-cells/",
                   {"cells": [{"part_type": str(old.id), "month": "2027-03", "quantity": None}]},
                   format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertFalse(VolumeForecast.objects.filter(archived=False).exists())

    def test_viewer_cannot_edit(self):
        c = self._client("view_volumeforecast")
        r = c.post("/api/VolumeForecasts/set-cells/",
                   {"cells": [{"part_type": str(self.pt.id), "month": "2027-03", "quantity": 1}]},
                   format="json")
        self.assertEqual(r.status_code, 403)

    def test_a_bad_cell_changes_nothing(self):
        c = self._client("view_volumeforecast", "add_volumeforecast", "change_volumeforecast")
        r = c.post("/api/VolumeForecasts/set-cells/", {"cells": [
            {"part_type": str(self.pt.id), "month": "2027-03", "quantity": 4},
            {"part_type": str(self.pt.id), "month": "never", "quantity": 4}]}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertFalse(VolumeForecast.objects.exists())
