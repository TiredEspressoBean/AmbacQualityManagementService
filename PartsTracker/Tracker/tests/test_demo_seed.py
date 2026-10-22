"""The demo seed produces the flows a demo walks (2026-10-07).

Nothing exercised `seed_demo` before, so it drifted: every unit finished at a
COMPLETED terminal, so the shipping queue was empty by construction; there was no
new-build route; Rework had nothing to inspect. This runs the whole seed once and
checks the flows exist — walked through the real services, not set by hand.
"""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

import json

from Tracker.models import (
    Core, Parts, Processes, QuarantineDisposition, Steps, Substep, Tenant, WorkOrder,
)
from Tracker.services.mes.shipping import is_ship_step, ready_to_ship
from Tracker.utils.tenant_context import tenant_context


class DemoSeedFlowsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())
        cls.tenant = Tenant.objects.get(slug="demo")

    def test_new_builds_have_their_own_route_ending_at_ship(self):
        with tenant_context(self.tenant.id):
            build = Processes.objects.get(name="Injector Build")
            self.assertFalse(build.is_remanufactured)
            ship = Steps.objects.get(name="Ship")
            self.assertTrue(is_ship_step(ship))
            self.assertTrue(build.process_steps.filter(step=ship).exists())
            customer_wos = WorkOrder.objects.filter(ERP_id__in=["WO-2024-0042-A", "WO-2024-0038-A"])
            self.assertEqual({wo.process_id for wo in customer_wos}, {build.id})

    def test_every_terminal_step_says_what_it_ends_as(self):
        with tenant_context(self.tenant.id):
            blank = Steps.objects.filter(is_terminal=True, terminal_status="").values_list("name", flat=True)
            self.assertEqual(list(blank), [])

    def test_the_shipping_queue_has_work_and_history(self):
        with tenant_context(self.tenant.id):
            queue = {g["order_number"]: len(g["parts"]) for g in ready_to_ship(self.tenant)}
            self.assertEqual(queue.get("ORD-2024-0042"), 6)
            great_lakes = Parts.objects.filter(ERP_id__startswith="INJ-0038-")
            self.assertEqual(great_lakes.filter(part_status="SHIPPED", customer_shipment__isnull=False).count(), 11)
            # 0038-010 was scrapped at inspection; a scrapped unit never went out.
            self.assertEqual(list(great_lakes.exclude(part_status="SHIPPED").values_list("ERP_id", "part_status")),
                             [("INJ-0038-010", "SCRAPPED")])
            self.assertFalse(Parts.objects.filter(part_status="SCRAPPED", customer_shipment__isnull=False).exists())
            self.assertEqual(WorkOrder.objects.get(ERP_id="WO-2024-0038-A").workorder_status, "COMPLETED")
            self.assertEqual(Parts.objects.filter(ERP_id__startswith="INJ-0042-", part_status="SHIPPED").count(), 10)

    def test_rework_and_machining_have_work_instructions(self):
        with tenant_context(self.tenant.id):
            for name in ("Rework", "Machining"):
                self.assertTrue(Substep.objects.filter(step__name=name, is_inspection_point=True).exists(), name)

    def test_every_core_mid_teardown_is_on_a_work_order(self):
        # Teardown is completed and released from the work order; a core in those
        # states off one can never leave them.
        with tenant_context(self.tenant.id):
            stranded = Core.objects.filter(status__in=["IN_DISASSEMBLY", "DISASSEMBLED"],
                                           part__work_order__isnull=True)
            self.assertEqual(list(stranded.values_list("core_number", flat=True)), [])
            # Teardown runs on the reman route, entering at Core Receiving — not on
            # the new-build route, which a name-ordered pick once chose.
            teardown = Core.objects.filter(part__work_order__isnull=False)
            self.assertEqual(set(teardown.values_list("part__work_order__process__name", flat=True)),
                             {"Injector Reman"})
            self.assertFalse(teardown.filter(part__step__name="Machining").exists())
            self.assertTrue(Core.objects.filter(status="DISASSEMBLED").exists())

    def test_both_fulfilment_modes_leave_teardown_their_own_way(self):
        with tenant_context(self.tenant.id):
            repair = Core.objects.get(core_number="CORE-240210-0007")
            self.assertEqual((repair.fulfilment_mode, repair.status), ("REPAIR_RETURN", "IN_REBUILD"))
            # The over-and-above exhibit: a repair unit whose finding needs the
            # customer's answer, so it waits (release.request_authorisation).
            self.assertEqual(Core.objects.get(core_number="CORE-240212-0009").status,
                             "AWAITING_AUTHORISATION")
            self.assertEqual(Core.objects.get(core_number="CORE-240215-0005").status, "HARVESTED")
            # A unit that goes back to its customer was received against their order.
            for number, order in (("CORE-240210-0007", "ORD-2024-0044"),
                                  ("CORE-240212-0009", "ORD-2024-0046")):
                core = Core.objects.select_related("part__order").get(core_number=number)
                self.assertEqual(core.part.order.order_number, order, number)
            # No finding waits on the repair unit: the operator records it at Nozzle
            # Inspection, where its repair is pre-approved and applies at once.
            self.assertFalse(repair.harvested_components.exclude(proposed_grade="").exists())

    def test_reman_capture_nodes_are_authored(self):
        with tenant_context(self.tenant.id):
            bodies = json.dumps(list(Substep.objects.values_list("body_blocks", flat=True)))
            for node in ("harvestedComponentCapture", "componentInstallCapture", "rebuildFindingCapture"):
                self.assertIn(f'"{node}"', bodies, node)

    def test_no_open_disposition_on_a_part_that_has_left(self):
        # A shipped or scrapped part's nonconformance was decided before it left.
        # The seed once left contradictory twins open on them (a Rework on a
        # shipped part, a Use As Is on a scrapped one). The one open record such a
        # part may carry is the Scrap decision that scrapped it, waiting for its close
        # (the Production Manager's exhibit, WO-PM-MAKEUP-01).
        from Tracker.models import QuarantineDisposition
        with tenant_context(self.tenant.id):
            stray = (QuarantineDisposition.objects.active()
                     .filter(is_current_version=True,
                             part__part_status__in=("SHIPPED", "COMPLETED", "SCRAPPED"))
                     .exclude(current_state="CLOSED")
                     .exclude(disposition_type="SCRAP", part__part_status="SCRAPPED")
                     .values_list("disposition_number", "part__ERP_id"))
            self.assertEqual(list(stray), [])

    def test_a_finding_waits_for_the_lead(self):
        # The Shift Lead's pending finding: recorded at Nozzle Inspection, where a
        # replacement isn't pre-approved, so it waits and the unit holds at the check.
        from Tracker.models import Core
        with tenant_context(self.tenant.id):
            core = Core.objects.select_related("part__step", "part__order").get(
                core_number="CORE-240214-0010")
            self.assertEqual(core.part.step.name, "Nozzle Inspection")
            self.assertEqual(core.part.order.order_number, "ORD-2024-0047")
            pending = core.harvested_components.exclude(proposed_grade="")
            self.assertEqual([(c.component_type.name, c.proposed_grade) for c in pending],
                             [("Injector Nozzle Assembly", "SCRAP")])

    def test_makeup_exhibit_is_one_short(self):
        # The Production Manager tops up a job after scrap: one body scrapped through a
        # decided, verified Scrap disposition, the job one good unit short.
        from Tracker.models import QuarantineDisposition, WorkOrder
        from Tracker.services.mes.makeup import work_order_shortfall
        with tenant_context(self.tenant.id):
            wo = WorkOrder.objects.get(ERP_id="WO-PM-MAKEUP-01")
            self.assertEqual(work_order_shortfall(wo)["shortfall"], 1)
            scrap = QuarantineDisposition.objects.get(part__work_order=wo)
            self.assertEqual((scrap.disposition_type, scrap.current_state, scrap.scrap_verified),
                             ("SCRAP", "IN_PROGRESS", True))

    def test_major_capas_route_through_the_severity_template(self):
        # The demo keeps a real tenant's approval templates, so a Major CAPA's go-ahead
        # is a CAPA_MAJOR request, and work under way means it was approved.
        from Tracker.models import ApprovalRequest, CAPA
        with tenant_context(self.tenant.id):
            capa = CAPA.objects.get(capa_number="CAPA-2024-003", is_current_version=True)
            self.assertEqual(capa.approval_status, "APPROVED")
            self.assertNotEqual(capa.approved_by_id, capa.initiated_by_id)
            self.assertTrue(ApprovalRequest.objects.filter(
                object_id=str(capa.id), approval_type="CAPA_MAJOR", status="APPROVED").exists())


class DemoSeedDarkExhibitTests(TestCase):
    """Phase 9 lights the surfaces the role audit found built-but-empty.

    Each of these was verified working in code and then found with nothing to show
    in the browser, which is a worse failure than a bug: the feature looks absent.
    They are asserted here because a seed regression would put them back in the dark
    silently, and only a walk would notice.
    """

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())
        cls.tenant = Tenant.objects.get(slug="demo")

    def test_customer_orders_carry_dated_demand_lines(self):
        """Shipping row 9 — `delivery_performance` keys on
        `work_order__order_line__due_date`, so without dated lines no shipment can be
        attributed and the board reads "On time: —" beside shipped units."""
        from Tracker.models import OrderLine
        from Tracker.services.mes.shipping import delivery_performance
        with tenant_context(self.tenant):
            lines = OrderLine.objects.all()
            self.assertTrue(lines.exists(), "no order lines — OTD cannot be measured")
            self.assertFalse(lines.filter(due_date__isnull=True).exists(),
                             "an undated line measures nothing")
            self.assertTrue(WorkOrder.objects.filter(order_line__isnull=False).exists(),
                            "no work order is pegged to a line")
            perf = delivery_performance(self.tenant)
            self.assertGreater(perf["deliveries"], 0, "nothing to score")
            self.assertIsNotNone(perf["on_time_pct"])

    def test_material_usage_records_what_was_drawn(self):
        """Operator row 5 — with no usages the traveller's lots-drawn, recorded-values
        and overrides sections are dead for EVERY serial, and the backward trace from
        a part to its lots has nothing in it."""
        from Tracker.models import MaterialUsage
        with tenant_context(self.tenant):
            usages = MaterialUsage.objects.select_related("lot", "part", "step")
            self.assertTrue(usages.exists(), "no material was ever drawn")
            u = usages.first()
            self.assertIsNotNone(u.lot_id, "a usage with no lot traces nothing")
            self.assertIsNotNone(u.step_id, "a usage with no step can't reach a traveller row")
            self.assertGreater(u.qty_consumed, 0)

    def test_a_cycle_count_waits_to_be_applied(self):
        """Receiving row 8 — submitting is the counter's job and applying needs
        `apply_cyclecount`. A pre-applied count would teach neither half."""
        from Tracker.models import CycleCount
        with tenant_context(self.tenant):
            counts = CycleCount.objects.all()
            self.assertTrue(counts.exists(), "no cycle count to work")
            self.assertTrue(counts.filter(status="SUBMITTED").exists(),
                            "no count is waiting for a lead to apply it")

    def test_one_lot_is_a_customers_own_property(self):
        """Shipping row 8 — the board's customer-property half filters on
        `owner__isnull=False` (ISO 9001 8.5.3)."""
        from Tracker.models import MaterialLot
        with tenant_context(self.tenant):
            self.assertTrue(MaterialLot.objects.filter(owner__isnull=False).exists(),
                            "no customer property — that half of the board stays empty")

    def test_a_customer_requires_a_coc_on_every_shipment(self):
        """Shipping rows 3-4 — the badge the clerk reads before packing."""
        from Tracker.models import Companies
        with tenant_context(self.tenant):
            self.assertTrue(Companies.objects.filter(requires_coc_on_shipment=True).exists(),
                            "no CoC customer — the badge never renders")

    def test_document_control_has_a_review_and_a_classification_to_see(self):
        """Document Controller rows 6 and 7 — the review loop and the tiers are what
        the role is most distinctively for, and both were dark."""
        from Tracker.models import Documents
        with tenant_context(self.tenant):
            from django.utils import timezone
            self.assertTrue(Documents.objects.filter(review_date__lt=timezone.now().date()).exists(),
                            "nothing is due for review — the tile reads 0 forever")
            self.assertTrue(Documents.objects.filter(classification="SECRET").exists(),
                            "nothing at the Secret tier — the top of the filter is unobservable")
            above_internal = Documents.objects.exclude(
                classification__in=["", "public", "internal", "PUBLIC", "INTERNAL"])
            self.assertTrue(above_internal.exists(),
                            "every document is Internal — tier filtering is unobservable")

    def test_a_customer_sees_every_order_for_their_company(self):
        """The portal shows orders naming the customer, not their company's (Customer
        track, 2026-10-21): an order with no customer was invisible to Tom."""
        from Tracker.models import Documents, Orders, User
        with tenant_context(self.tenant):
            tom = User.objects.get(email="tom.bradley@midwestfleet.com")
            unnamed = Orders.objects.filter(company=tom.parent_company, customer__isnull=True)
            self.assertEqual(list(unnamed.values_list("order_number", flat=True)), [])
            shared = Documents.objects.for_user(tom).values_list("file_name", flat=True)
            self.assertIn("CERT Flow test results SHP-2026-000001", list(shared))
            self.assertEqual(WorkOrder.objects.get(ERP_id="WO-2024-0042-A").quantity,
                             Parts.objects.filter(work_order__ERP_id="WO-2024-0042-A").count())

    def test_a_late_delivery_names_whom_to_chase(self):
        from Tracker.models import Companies
        from Tracker.services.mes.late_deliveries import company_contact
        with tenant_context(self.tenant):
            gld = Companies.objects.get(name="Great Lakes Diesel")
            contacts = company_contact({gld.id}, ("EXPEDITING", "GENERAL"))
            self.assertEqual(contacts[gld.id][0], "Dana Fischer")

    def test_an_unstarted_visit_has_no_start(self):
        """The traveler credits a started visit's assignee as its operator, so a seeded
        start time on a visit nobody worked put a name on it (2026-10-21)."""
        from Tracker.models import StepExecution
        with tenant_context(self.tenant):
            self.assertFalse(StepExecution.objects.filter(
                status="PENDING", started_at__isnull=False).exists())

    def test_the_small_track_personas_exist(self):
        from Tracker.models import User
        with tenant_context(self.tenant):
            for email, group in [("priya.buy@demo.ambac.com", "Purchasing"),
                                 ("luis.recv@demo.ambac.com", "Receiving"),
                                 ("rosa.ship@demo.ambac.com", "Shipping"),
                                 ("alex.audit@demo.ambac.com", "Auditor")]:
                user = User.objects.get(email=email)
                self.assertTrue(user.user_roles.filter(group__name=group).exists(), email)

    def test_a_declined_unit_waits_to_go_back(self):
        """Shipping R1 (2026-10-21): a customer's own unit they declined to repair is on
        the shipping board for its order, to go back unrepaired."""
        with tenant_context(self.tenant.id):
            core = Core.objects.get(core_number="CORE-240215-0011")
            self.assertEqual(core.status, "DECLINED")
            self.assertIn("ORD-2024-0044", {g["order_number"] for g in ready_to_ship(self.tenant)})

    def test_requirements_has_a_shortage_to_buy(self):
        """Purchasing and Planner (2026-10-21): the Requirements page was empty, so
        nobody could practise reading or covering a shortage."""
        from Tracker.services.mes.requirements import sourcing_requirements
        with tenant_context(self.tenant.id):
            self.assertTrue(sourcing_requirements(self.tenant)["source"])

    def test_a_rebuilt_unit_waits_to_go_back(self):
        """Shipping R2 (2026-10-22): a customer's own unit walked through its whole
        rebuild by the real flow, on the shipping board under its order."""
        with tenant_context(self.tenant.id):
            core = Core.objects.get(core_number="CORE-240217-0013")
            self.assertEqual(core.status, "REBUILT")
            self.assertIn("ORD-2024-0047", {g["order_number"] for g in ready_to_ship(self.tenant)})

    def test_an_exchange_unit_has_a_harvest_or_buy_choice(self):
        """PM R2 (2026-10-22): an exchange unit in rebuild whose scrapped nozzle can come
        from recovered stock or be bought."""
        from Tracker.services.reman.rebuild import REPLACE_POOL, resolve_rebuild_plan
        with tenant_context(self.tenant.id):
            plan = resolve_rebuild_plan(Core.objects.get(core_number="CORE-240216-0012"))
            nozzle = next(s for s in plan.slots if s.component_type_name == "Injector Nozzle Assembly")
            self.assertEqual(nozzle.resolution, REPLACE_POOL)
            self.assertLessEqual({"HARVESTED_POOL", "PURCHASED"}, {c.kind for c in nozzle.candidates})

    def test_an_assembled_unit_draws_its_material_once(self):
        """Auditor walk (2026-10-22): the material-usage backfill drew again for parts
        whose advance had already drawn, so a traveler listed every lot twice."""
        from django.apps import apps
        MaterialUsage = apps.get_model("Tracker", "MaterialUsage")
        with tenant_context(self.tenant.id):
            part = Parts.objects.get(ERP_id="INJ-QA-INSPECT-011")
            lots = list(MaterialUsage.objects.filter(part=part, step__name="Assembly")
                        .values_list("lot_id", flat=True))
            self.assertTrue(lots)
            self.assertEqual(len(lots), len(set(lots)))

    def test_the_tenant_admin_is_not_platform_staff(self):
        """Administrator track (2026-10-22): is_staff grants cross-tenant read access, so
        the customer's admin persona must not hold it; only the platform admin does."""
        from Tracker.models import User
        self.assertFalse(User.objects.get(email="admin@demo.ambac.com").is_staff)

    def test_a_false_fail_waits_to_be_put_right(self):
        """QA Inspector / QA Manager corrections (2026-10-22): a body failed at Body
        Inspection for a burr that wasn't there, quarantined with an open disposition
        over its FAIL report."""
        with tenant_context(self.tenant.id):
            part = Parts.objects.get(ERP_id="INJ-QA-INSPECT-052")
            self.assertEqual(part.step.name, "Body Inspection")
            self.assertEqual(part.part_status, "QUARANTINED")
            disposition = QuarantineDisposition.objects.get(part=part, current_state="OPEN")
            self.assertEqual(list(disposition.quality_reports.values_list("status", flat=True)),
                             ["FAIL"])

    def test_a_unit_that_used_up_its_reworks_waits_in_mrb(self):
        """Shift Lead / PM escalation (2026-10-22): two reworks at Nozzle Inspection hit
        the visit cap, so the unit sits quarantined at MRB Review with an open decision."""
        with tenant_context(self.tenant.id):
            part = Parts.objects.get(ERP_id="CORE-240219-0014")
            self.assertEqual(part.step.name, "MRB Review")
            self.assertEqual(part.part_status, "QUARANTINED")
            mrb = QuarantineDisposition.objects.get(part=part, current_state="OPEN")
            self.assertEqual(mrb.escalated_from_step.name, "Nozzle Inspection")
            self.assertFalse(QuarantineDisposition.objects.filter(
                part=part, current_state="IN_PROGRESS").exists())
