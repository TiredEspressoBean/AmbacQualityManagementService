"""An import that moves an order's promised date records the move, as a form edit does
(user decision 2026-10-28, B14): the first promise is kept for on-time scoring."""
from datetime import date

from Tracker.models import Orders
from Tracker.serializers.csv_import import ImportMode, OrdersCSVImportSerializer
from Tracker.tests.base import TenantTestCase


class OrderImportDateMoveTests(TenantTestCase):

    def test_an_import_that_moves_the_date_keeps_the_original(self):
        order = Orders.objects.create(tenant=self.tenant_a, name="ORD-IMP", order_status="PENDING",
                                      estimated_completion=date(2026, 11, 2))
        serializer = OrdersCSVImportSerializer(user=self.user_a, mode=ImportMode.UPDATE)
        instance, created, _ = serializer.import_row(
            {"id": str(order.id), "name": "ORD-IMP", "estimated_completion": "2026-11-20"})
        self.assertFalse(created)
        order.refresh_from_db()
        self.assertEqual(order.estimated_completion, date(2026, 11, 20))
        self.assertEqual(order.original_completion_date, date(2026, 11, 2))

    def test_a_later_move_keeps_the_first_promise(self):
        order = Orders.objects.create(tenant=self.tenant_a, name="ORD-IMP2", order_status="PENDING",
                                      estimated_completion=date(2026, 11, 2),
                                      original_completion_date=date(2026, 10, 30))
        serializer = OrdersCSVImportSerializer(user=self.user_a, mode=ImportMode.UPDATE)
        serializer.import_row({"id": str(order.id), "name": "ORD-IMP2", "estimated_completion": "2026-12-01"})
        order.refresh_from_db()
        self.assertEqual(order.original_completion_date, date(2026, 10, 30))
