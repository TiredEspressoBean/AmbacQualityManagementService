"""The Audit Log exports, behind export_auditlog (user decision 2026-10-28). The perm
was defined and granted but checked nowhere, and the page had export switched off."""
import csv
import io

from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType

from Tracker.models import Orders
from Tracker.tests.base import TenantTestCase

BROWSE = ['view_auditlog', 'view_logentry', 'view_orders', 'full_tenant_access']


class AuditLogExportTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        ct = ContentType.objects.get_for_model(Orders)
        for name, action in (("ORD-A", LogEntry.Action.CREATE), ("ORD-B", LogEntry.Action.UPDATE),
                             ("ORD-C", LogEntry.Action.UPDATE)):
            order = Orders.objects.create(tenant=self.tenant_a, name=name, order_status="PENDING")
            LogEntry.objects.create(content_type=ct, object_pk=str(order.pk), object_repr=name,
                                    action=action, changes={"name": [None, name]}, actor=self.user_a)

    def _export(self, perms, **params):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, perms)
        self.authenticate_as(self.user_a, self.tenant_a)
        return self.client.get("/api/auditlog/export/csv/", params)

    @staticmethod
    def _records(response):
        rows = list(csv.DictReader(io.StringIO(response.content.decode('utf-8-sig'))))
        return sorted(r['Record'] for r in rows)

    def test_a_holder_exports_the_entries(self):
        r = self._export(BROWSE + ['export_auditlog'])
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self._records(r), ["ORD-A", "ORD-B", "ORD-C"])

    def test_view_auditlog_alone_is_refused(self):
        r = self._export(BROWSE)
        self.assertEqual(r.status_code, 403, r.content)

    def test_the_export_respects_filters(self):
        r = self._export(BROWSE + ['export_auditlog'], action=LogEntry.Action.UPDATE)
        self.assertEqual(self._records(r), ["ORD-B", "ORD-C"])

    def test_each_export_is_itself_recorded(self):
        self._export(BROWSE + ['export_auditlog'])
        self.assertTrue(LogEntry.objects.filter(object_repr__startswith="Export csv: Audit log",
                                                actor=self.user_a).exists())
