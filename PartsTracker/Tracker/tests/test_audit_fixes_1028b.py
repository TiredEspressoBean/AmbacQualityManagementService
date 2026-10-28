"""Second round of docs-audit bugs (2026-10-28).

- Refusing a bypass request: the no-self-refusal rule and the required reason were
  the UI's alone (A2).
- The Tracker's order list had no order, so limit/offset paging could repeat or skip
  orders (A6).
- The order page's People card listed only the customer, never invited viewers (A10).
"""
from types import SimpleNamespace

from Tracker.models import OrderViewer, Orders
from Tracker.tests.base import TenantTestCase


class BypassRefusalRulesTests(TenantTestCase):

    def _pending(self, requested_by_id):
        from Tracker.models import OverrideStatus
        return SimpleNamespace(status=OverrideStatus.PENDING, requested_by_id=requested_by_id)

    def test_you_cannot_refuse_your_own_request(self):
        from Tracker.services.mes.step_override import reject_step_override
        with self.assertRaisesMessage(ValueError, "your own"):
            reject_step_override(self._pending(self.user_a.id), self.user_a, reason="no")

    def test_a_refusal_needs_a_reason(self):
        from Tracker.services.mes.step_override import reject_step_override
        with self.assertRaisesMessage(ValueError, "Say why"):
            reject_step_override(self._pending(self.user_b.id), self.user_a, reason="   ")


class TrackerOrderingTests(TenantTestCase):

    def test_pages_neither_repeat_nor_skip(self):
        for i in range(5):
            Orders.objects.create(tenant=self.tenant_a, name=f"ORD-{i}", order_status="PENDING")
        self.authenticate_superuser(self.tenant_a)
        seen = []
        for offset in (0, 2, 4):
            r = self.client.get(f"/api/TrackerOrders/?limit=2&offset={offset}")
            self.assertEqual(r.status_code, 200, r.content)
            seen += [o["name"] for o in r.json()["results"]]
        self.assertEqual(seen, [f"ORD-{i}" for i in reversed(range(5))])


class OrderViewersTests(TenantTestCase):

    def test_invited_viewers_are_listed(self):
        order = Orders.objects.create(tenant=self.tenant_a, name="ORD-V", order_status="PENDING")
        OrderViewer.objects.create(order=order, user=self.user_a)
        self.authenticate_superuser(self.tenant_a)
        r = self.client.get(f"/api/TrackerOrders/{order.id}/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual([v["name"] for v in r.json()["viewers"]], [self.user_a.display_name])
