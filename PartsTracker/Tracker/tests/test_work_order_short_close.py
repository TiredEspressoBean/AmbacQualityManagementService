"""Short-closing a work order: Completed with fewer built than planned, on purpose.

Every unfinished unit is scrapped or moved to another open work order on the same
process; the order is flagged short_closed with the reason, and the customer order's
cascade treats it as terminal. Same permission as Cancel.

Two consequences are the closer's to answer, never defaulted: raise a receiving work
order's quantity, and give the unbuilt units back to the order line.
"""
from django.contrib.contenttypes.models import ContentType

from Tracker.models import (
    OrderLine, Orders, OrdersStatus, Parts, PartTypes, Processes, RecordEdit, Steps, WorkOrder,
)
from Tracker.tests.base import TenantTestCase


class ShortCloseTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        self.pt = pt = PartTypes.objects.create(tenant=self.tenant_a, name="Injector")
        self.process = Processes.objects.create(tenant=self.tenant_a, name="Build", part_type=pt)
        self.step = Steps.objects.create(tenant=self.tenant_a, name="Assemble", part_type=pt)
        self.order = Orders.objects.create(tenant=self.tenant_a, name="Fleet order")
        self.wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id="WO-SC-1", quantity=4,
                                           process=self.process, related_order=self.order,
                                           workorder_status="IN_PROGRESS")
        self.other = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id="WO-SC-2", quantity=2,
                                              process=self.process, workorder_status="PENDING")

        def part(n, status, step=None):
            return Parts.objects.create(tenant=self.tenant_a, ERP_id=f"SC-{n}", part_type=pt,
                                        work_order=self.wo, order=self.order, part_status=status,
                                        step=step)
        self.done = [part(1, "COMPLETED"), part(2, "COMPLETED")]
        self.to_scrap = part(3, "IN_PROGRESS", self.step)
        self.to_move = part(4, "IN_PROGRESS", self.step)

    def _post(self, body, perms=('view_workorder', 'cancel_workorder')):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, list(perms) + ['full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        return self.client.post(f"/api/WorkOrders/{self.wo.id}/short_close/", body, format="json")

    def _body(self, **over):
        body = {"reason": "Customer accepted 2 of 4; the rest go to the next batch",
                "dispositions": [
                    {"part": str(self.to_scrap.id), "action": "SCRAP"},
                    {"part": str(self.to_move.id), "action": "MOVE", "target_work_order": str(self.other.id)},
                ],
                "raise_targets": [{"work_order": str(self.other.id), "raise_quantity": False}]}
        body.update(over)
        return body

    def test_short_close_scraps_moves_and_completes_the_order(self):
        resp = self._post(self._body())
        self.assertEqual(resp.status_code, 200, resp.content)
        self.wo.refresh_from_db()
        self.assertEqual(self.wo.workorder_status, "COMPLETED")
        self.assertTrue(self.wo.short_closed)
        self.assertEqual(self.wo.short_closed_by_id, self.user_a.id)
        self.assertIn("Customer accepted", self.wo.short_close_reason)
        self.assertIsNotNone(self.wo.true_completion)

        self.to_scrap.refresh_from_db()
        self.assertEqual(self.to_scrap.part_status, "SCRAPPED")
        self.to_move.refresh_from_db()
        self.assertEqual(self.to_move.work_order_id, self.other.id)
        self.assertEqual(self.to_move.step_id, self.step.id)

        ct = ContentType.objects.get_for_model(Parts)
        self.assertTrue(RecordEdit.objects.filter(content_type=ct, object_id=self.to_scrap.id,
                                                  field_name="part_status").exists())
        self.assertTrue(RecordEdit.objects.filter(content_type=ct, object_id=self.to_move.id,
                                                  field_name="work_order").exists())

        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrdersStatus.COMPLETED)

    def test_a_mistaken_short_close_is_reopened_and_the_scrap_stays(self):
        """Corrections #41 (user decision 2026-10-26): the PM reopens it; the order
        reopens; scrapped stays scrapped, moved stays moved."""
        self._post(self._body())
        url = f"/api/WorkOrders/{self.wo.id}/reopen/"
        self.assertEqual(self.client.post(url, {"reason": ""}, format="json").status_code, 400)
        resp = self.client.post(url, {"reason": "Closed the wrong WO"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.wo.refresh_from_db()
        self.order.refresh_from_db()
        self.to_scrap.refresh_from_db()
        self.to_move.refresh_from_db()
        self.assertEqual((self.wo.workorder_status, self.wo.short_closed), ("IN_PROGRESS", False))
        self.assertIsNone(self.wo.true_completion)
        self.assertEqual(self.order.order_status, OrdersStatus.IN_PROGRESS)
        self.assertEqual(self.to_scrap.part_status, "SCRAPPED")
        self.assertEqual(self.to_move.work_order_id, self.other.id)
        self.assertEqual(self.client.post(url, {"reason": "again"}, format="json").status_code, 400)

    def test_cancel_permission_is_required(self):
        resp = self._post(self._body(), perms=('view_workorder', 'change_workorder'))
        self.assertEqual(resp.status_code, 403, resp.content)

    def test_a_reason_is_required(self):
        self.assertEqual(self._post(self._body(reason="  ")).status_code, 400)

    def test_every_unfinished_unit_needs_a_choice(self):
        resp = self._post(self._body(dispositions=[{"part": str(self.to_scrap.id), "action": "SCRAP"}]))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("SC-4", resp.json()["detail"])
        self.wo.refresh_from_db()
        self.assertFalse(self.wo.short_closed)

    def test_nothing_built_is_a_cancel_not_a_short_close(self):
        Parts.objects.filter(pk__in=[p.pk for p in self.done]).update(part_status="IN_PROGRESS")
        resp = self._post(self._body())
        self.assertEqual(resp.status_code, 400)
        self.assertIn("cancel", resp.json()["detail"])

    def test_a_unit_only_moves_to_a_work_order_on_the_same_process(self):
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Pump")
        elsewhere = Processes.objects.create(tenant=self.tenant_a, name="Other", part_type=pt)
        self.other.process = elsewhere
        self.other.save(update_fields=["process"])
        resp = self._post(self._body())
        self.assertEqual(resp.status_code, 400)
        self.to_scrap.refresh_from_db()
        self.assertEqual(self.to_scrap.part_status, "IN_PROGRESS")  # nothing applied

    def test_a_quarantined_unit_is_not_scrapped_here(self):
        self.to_scrap.part_status = "QUARANTINED"
        self.to_scrap.save(update_fields=["part_status"])
        resp = self._post(self._body())
        self.assertEqual(resp.status_code, 400)
        self.assertIn("quarantined", resp.json()["detail"])

    # --- Customer scope (user decision 2026-10-19: same customer, or work on no order;
    #     a customer's own unit only to that customer's work).

    def _customers(self):
        from Tracker.models import Companies
        acme = Companies.objects.create(tenant=self.tenant_a, name="Acme")
        globex = Companies.objects.create(tenant=self.tenant_a, name="Globex")
        Orders.objects.filter(pk=self.order.pk).update(company=acme)
        return acme, globex

    def _give_other_to(self, company):
        order = Orders.objects.create(tenant=self.tenant_a, name=f"{company.name} order", company=company)
        WorkOrder.objects.filter(pk=self.other.pk).update(related_order=order)

    def test_a_unit_does_not_move_to_another_customers_work(self):
        _, globex = self._customers()
        self._give_other_to(globex)
        resp = self._post(self._body())
        self.assertEqual(resp.status_code, 400)
        self.assertIn("different customer", resp.json()["detail"])

    def test_a_unit_moves_to_the_same_customers_work(self):
        acme, _ = self._customers()
        self._give_other_to(acme)
        self.assertEqual(self._post(self._body()).status_code, 200)

    def test_a_unit_moves_to_work_on_no_order(self):
        self._customers()
        self.assertEqual(self._post(self._body()).status_code, 200)

    def test_the_targets_offered_follow_the_rule(self):
        _, globex = self._customers()
        self._give_other_to(globex)
        self.grant_tenant_permissions(self.user_a, self.tenant_a, ['view_workorder', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        body = self.client.get(f"/api/WorkOrders/{self.wo.id}/short_close_targets/").json()
        self.assertEqual([t["ERP_id"] for t in body["targets"]], ["WO-SC-2"])
        self.assertEqual(body["allowed"][str(self.to_move.id)], [])

    def test_a_customers_own_unit_stays_with_them(self):
        from datetime import date
        from Tracker.services.reman.core_part import create_core
        acme, _ = self._customers()
        core = create_core(tenant=self.tenant_a, work_order=self.wo, step=self.step, core_number="RR-1",
                           core_type=self.pt, received_date=date.today(), received_by=self.user_a,
                           condition_grade='B', customer=acme, fulfilment_mode="REPAIR_RETURN")
        Parts.objects.filter(pk=self.to_move.pk).update(work_order=self.other)  # out of the way
        body = self._body(dispositions=[
            {"part": str(self.to_scrap.id), "action": "SCRAP"},
            {"part": str(core.part_id), "action": "MOVE", "target_work_order": str(self.other.id)},
        ])
        resp = self._post(body)  # WO-SC-2 is on no order: fine for stock, not for Acme's own core
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("customer's own unit", resp.json()["detail"])

    def test_moving_units_needs_an_answer_on_the_receiving_quantity(self):
        resp = self._post(self._body(raise_targets=[]))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("WO-SC-2", resp.json()["detail"])

    def test_raising_the_receiving_quantity_is_recorded(self):
        resp = self._post(self._body(raise_targets=[{"work_order": str(self.other.id), "raise_quantity": True}]))
        self.assertEqual(resp.status_code, 200, resp.content)
        self.other.refresh_from_db()
        self.assertEqual(self.other.quantity, 3)
        self.assertTrue(RecordEdit.objects.filter(
            content_type=ContentType.objects.get_for_model(WorkOrder), object_id=self.other.id,
            field_name="quantity", old_value="2", new_value="3").exists())

    def test_leaving_the_receiving_quantity_alone(self):
        self.assertEqual(self._post(self._body()).status_code, 200)
        self.other.refresh_from_db()
        self.assertEqual(self.other.quantity, 2)


class ShortCloseOrderLineTests(ShortCloseTests):
    """On an order line, the closer also answers whether the unbuilt units go back to it."""

    def setUp(self):
        super().setUp()
        self.line = OrderLine.objects.create(tenant=self.tenant_a, order=self.order, line_number=1,
                                             part_type=self.pt, quantity=7)
        WorkOrder.objects.filter(pk__in=[self.wo.pk, self.other.pk]).update(order_line=self.line)

    def _body(self, **over):
        over.setdefault("return_shortfall", False)
        return super()._body(**over)

    def test_the_give_back_question_must_be_answered(self):
        resp = self._post(self._body(return_shortfall=None))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("order line", resp.json()["detail"])

    def test_giving_back_returns_only_what_no_raised_work_order_plans(self):
        # 4 planned, 2 built: 1 scrapped, 1 moved onto WO-SC-2 (same line) which is raised.
        resp = self._post(self._body(
            return_shortfall=True,
            raise_targets=[{"work_order": str(self.other.id), "raise_quantity": True}]))
        self.assertEqual(resp.status_code, 200, resp.content)
        self.wo.refresh_from_db()
        self.assertEqual(self.wo.short_close_returned_quantity, 1)
        self.line.refresh_from_db()
        self.assertEqual(self.line.planned_quantity, 4 + 3 - 1)
        self.assertEqual(self.line.remaining_quantity, 1)

    def test_not_giving_back_leaves_the_line_planned(self):
        self.assertEqual(self._post(self._body(return_shortfall=False)).status_code, 200)
        self.wo.refresh_from_db()
        self.assertEqual(self.wo.short_close_returned_quantity, 0)
        self.line.refresh_from_db()
        self.assertEqual(self.line.planned_quantity, 6)
