"""Two order last-miles.

- Removing parts from an order: it was an unreachable endpoint that used a queryset
  `.update()` (no audit entry) and fell back to add_orders.
- The delivery-date slip: `original_completion_date` was displayed ("Originally …")
  and written by nothing.
"""
import datetime

from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType

from Tracker.models import Orders, Parts, PartTypes, WorkOrder
from Tracker.services.mes.orders import note_completion_change
from Tracker.tests.base import TenantTestCase


class RemovePartsFromOrderTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        self.order = Orders.objects.create(tenant=self.tenant_a, name="Fleet order")
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Injector")
        self.wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id="WO-RM-1", quantity=2)
        self.parts = [Parts.objects.create(tenant=self.tenant_a, ERP_id=f"RM-{i}", part_type=pt,
                                           order=self.order, work_order=self.wo) for i in range(2)]

    def _remove(self, perms):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, perms + ['full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        return self.client.post(f"/api/Orders/{self.order.id}/parts/bulk-remove/",
                                {"ids": [str(self.parts[0].id)]}, format="json")

    def test_removal_needs_change_orders(self):
        resp = self._remove(['view_orders', 'add_orders'])
        self.assertEqual(resp.status_code, 403, resp.content)

    def test_removal_clears_only_the_order_link_and_is_audited(self):
        resp = self._remove(['view_orders', 'change_orders'])
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["removed"], 1)
        part = Parts.objects.get(pk=self.parts[0].pk)
        self.assertIsNone(part.order_id)
        self.assertEqual(part.work_order_id, self.wo.id)
        self.assertEqual(Parts.objects.get(pk=self.parts[1].pk).order_id, self.order.id)
        self.assertTrue(LogEntry.objects.filter(
            content_type=ContentType.objects.get_for_model(Parts),
            object_pk=str(part.pk), changes__has_key='order').exists())


class DeliveryDateSlipTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        self.first = datetime.date(2026, 11, 1)
        self.order = Orders.objects.create(tenant=self.tenant_a, name="Slip order",
                                           estimated_completion=self.first)

    def _move(self, to):
        previous = self.order.estimated_completion
        self.order.estimated_completion = to
        self.order.save(update_fields=['estimated_completion'])
        note_completion_change(self.order, previous)
        self.order.refresh_from_db()

    def test_the_first_move_keeps_the_original_and_later_moves_never_overwrite_it(self):
        self._move(datetime.date(2026, 11, 8))
        self.assertEqual(self.order.original_completion_date, self.first)
        self._move(datetime.date(2026, 11, 20))
        self.assertEqual(self.order.original_completion_date, self.first)

    def test_a_first_date_is_not_a_slip(self):
        order = Orders.objects.create(tenant=self.tenant_a, name="No date yet")
        note_completion_change(order, None)
        order.refresh_from_db()
        self.assertIsNone(order.original_completion_date)

    def test_an_edit_through_the_api_stamps_it(self):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_orders', 'change_orders', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        resp = self.client.patch(f"/api/Orders/{self.order.id}/",
                                 {"estimated_completion": "2026-11-15"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["original_completion_date"], "2026-11-01")

    def test_a_later_work_order_cascading_up_counts_as_a_slip(self):
        WorkOrder.objects.create(tenant=self.tenant_a, ERP_id="WO-SLIP-1", quantity=1,
                                 related_order=self.order,
                                 expected_completion=datetime.date(2026, 12, 1))
        self.order.refresh_from_db()
        self.assertEqual(self.order.estimated_completion, datetime.date(2026, 12, 1))
        self.assertEqual(self.order.original_completion_date, self.first)
