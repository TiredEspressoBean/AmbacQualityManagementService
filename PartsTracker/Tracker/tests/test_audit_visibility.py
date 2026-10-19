"""Who reads which audit-log entries (services/core/audit_visibility.py).

Every staff role held view_logentry, and the endpoint filtered only by the actor's
tenant — so anyone could browse every record's field history, the record's own row
security notwithstanding, and a password change showed both hashes.
"""
from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType

from Tracker.models import Orders, Parts, PartTypes, User
from Tracker.tests.base import TenantTestCase

LINE = ['view_logentry', 'view_parts', 'full_tenant_access']


class AuditVisibilityTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        part_type = PartTypes.objects.create(tenant=self.tenant_a, name="Body")
        self.part = Parts.objects.create(tenant=self.tenant_a, ERP_id="AUD-1", part_type=part_type)
        self.part_ct = ContentType.objects.get_for_model(Parts)
        self.entry = LogEntry.objects.create(
            content_type=self.part_ct, object_pk=str(self.part.pk), object_repr="AUD-1",
            action=LogEntry.Action.UPDATE, changes={"part_status": ["PENDING", "IN_PROGRESS"]},
            actor=self.user_a)

    def _get(self, perms, url):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, perms)
        self.authenticate_as(self.user_a)
        return self.client.get(url)

    def _one_record(self, pk=None):
        return (f"/api/auditlog/?content_type={self.part_ct.pk}"
                f"&object_pk={pk or self.part.pk}")

    def test_a_line_role_reads_the_history_of_a_record_it_can_open(self):
        resp = self._get(LINE, self._one_record())
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual([e["id"] for e in resp.json()["results"]], [self.entry.id])

    def test_a_line_role_cannot_browse_the_trail(self):
        resp = self._get(LINE, "/api/auditlog/")
        self.assertEqual(resp.status_code, 403, resp.content)

    def test_the_browse_permission_opens_the_trail(self):
        resp = self._get(LINE + ['view_auditlog'], "/api/auditlog/")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertIn(self.entry.id, [e["id"] for e in resp.json()["results"]])

    def test_history_of_a_record_the_reader_cannot_open_is_hidden(self):
        """Without full_tenant_access a reader sees only parts on their own orders —
        and now only those parts' history."""
        resp = self._get(['view_logentry', 'view_parts'], self._one_record())
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["results"], [])

    def test_a_hidden_record_is_found_once_it_is_on_the_readers_order(self):
        order = Orders.objects.create(tenant=self.tenant_a, name="Mine", customer=self.user_a)
        self.part.order = order
        self.part.save(update_fields=["order"])
        resp = self._get(['view_logentry', 'view_parts'], self._one_record())
        self.assertEqual([e["id"] for e in resp.json()["results"]], [self.entry.id])

    def test_a_single_entry_for_a_hidden_record_is_not_found(self):
        resp = self._get(['view_logentry', 'view_parts'], f"/api/auditlog/{self.entry.id}/")
        self.assertEqual(resp.status_code, 404, resp.content)

    def test_a_stored_password_hash_is_masked_on_read(self):
        """Rows written before credentials were excluded are not rewritten; the API
        masks them."""
        user_ct = ContentType.objects.get_for_model(User)
        LogEntry.objects.create(
            content_type=user_ct, object_pk=str(self.user_a.pk), object_repr="a",
            action=LogEntry.Action.UPDATE,
            changes={"password": ["pbkdf2_sha256$old", "pbkdf2_sha256$new"]}, actor=self.user_a)
        resp = self._get(LINE + ['view_user', 'view_auditlog'],
                         f"/api/auditlog/?content_type={user_ct.pk}&object_pk={self.user_a.pk}")
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.content.decode()
        self.assertNotIn("pbkdf2_sha256", body)
        row = resp.json()["results"][0]
        self.assertEqual(row["changes"]["password"], ["[redacted]", "[redacted]"])
        self.assertIn({"field": "password", "old": "[redacted]", "new": "[redacted]"},
                      row["changes_display"])

    def test_a_new_password_change_is_not_logged(self):
        user_ct = ContentType.objects.get_for_model(User)
        self.user_a.set_password("a-new-password-123")
        self.user_a.save()
        latest = (LogEntry.objects.filter(content_type=user_ct, object_pk=str(self.user_a.pk))
                  .order_by("-timestamp").first())
        if latest is not None:
            self.assertNotIn("password", latest.changes_dict or {})
