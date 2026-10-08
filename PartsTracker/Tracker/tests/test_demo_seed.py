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

from Tracker.models import Core, Parts, Processes, Steps, Substep, Tenant, WorkOrder
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
            self.assertTrue(Core.objects.filter(status="DISASSEMBLED").exists())

    def test_both_fulfilment_modes_leave_teardown_their_own_way(self):
        with tenant_context(self.tenant.id):
            repair = Core.objects.get(fulfilment_mode="REPAIR_RETURN")
            self.assertEqual((repair.core_number, repair.status), ("CORE-240210-0007", "IN_REBUILD"))
            self.assertEqual(Core.objects.get(core_number="CORE-240215-0005").status, "HARVESTED")
            # A bench finding waits on a lead, so the pending-findings card has a row.
            self.assertTrue(repair.harvested_components.exclude(proposed_grade="").exists())

    def test_reman_capture_nodes_are_authored(self):
        with tenant_context(self.tenant.id):
            bodies = json.dumps(list(Substep.objects.values_list("body_blocks", flat=True)))
            for node in ("harvestedComponentCapture", "componentInstallCapture", "rebuildFindingCapture"):
                self.assertIn(f'"{node}"', bodies, node)
