"""Change records store the trusted client address (user decision 2026-10-28).
django-auditlog's middleware took the first X-Forwarded-For entry, which the client
sends; a spoofed header put any address on a change record."""
from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory, SimpleTestCase, override_settings

from Tracker.audit_middleware import TrustedIPAuditlogMiddleware
from Tracker.models import Orders
from Tracker.tests.base import TenantTestCase

# Behind one trusted proxy that appends the real client to X-Forwarded-For.
BEHIND_PROXY = dict(TRUSTED_CLIENT_IP_HEADER='HTTP_X_FORWARDED_FOR', NUM_PROXIES=1)


@override_settings(**BEHIND_PROXY)
class TrustedAddressTests(SimpleTestCase):

    def test_a_spoofed_first_entry_is_ignored(self):
        request = RequestFactory().get("/", HTTP_X_FORWARDED_FOR="6.6.6.6, 10.0.0.9",
                                       REMOTE_ADDR="172.16.0.1")
        self.assertEqual(TrustedIPAuditlogMiddleware._get_remote_addr(request), "10.0.0.9")

    @override_settings(TRUSTED_CLIENT_IP_HEADER='')
    def test_with_no_trusted_header_the_socket_address_is_used(self):
        request = RequestFactory().get("/", HTTP_X_FORWARDED_FOR="6.6.6.6", REMOTE_ADDR="172.16.0.1")
        self.assertEqual(TrustedIPAuditlogMiddleware._get_remote_addr(request), "172.16.0.1")


@override_settings(**BEHIND_PROXY)
class ChangeRecordAddressTests(TenantTestCase):

    def test_a_change_made_through_the_api_records_the_trusted_address(self):
        order = Orders.objects.create(tenant=self.tenant_a, name="ORD-IP", order_status="PENDING")
        self.grant_tenant_permissions(self.user_a, self.tenant_a,
                                      ['view_orders', 'change_orders', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        r = self.client.patch(f"/api/Orders/{order.id}/", {"name": "ORD-IP-2", "order_status": "PENDING"},
                              format="json", HTTP_X_FORWARDED_FOR="6.6.6.6, 10.0.0.9")
        self.assertEqual(r.status_code, 200, r.content)
        entry = (LogEntry.objects.filter(content_type=ContentType.objects.get_for_model(Orders),
                                         object_pk=str(order.pk), action=LogEntry.Action.UPDATE)
                 .order_by('-timestamp').first())
        self.assertIsNotNone(entry)
        self.assertEqual(entry.remote_addr, "10.0.0.9")
