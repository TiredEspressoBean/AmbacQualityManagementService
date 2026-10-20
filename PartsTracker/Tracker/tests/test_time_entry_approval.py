"""Labour time approval: Shift Lead / Production Manager sign off hours, never their own.

`approved` used to be writable on the serializer, so anyone who could edit an entry
could approve it; now only the approve action (approve_timeentry) sets it.
"""
import datetime

from django.contrib.auth import get_user_model
from django.utils import timezone

from Tracker.models import TimeEntry
from Tracker.tests.base import TenantTestCase


class TimeEntryApprovalTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        self.operator = get_user_model().objects.create_user(
            username='op_time', email='op_time@tenant-a.com', password='x', tenant=self.tenant_a)
        start = timezone.now() - datetime.timedelta(hours=3)
        self.entry = TimeEntry.objects.create(
            tenant=self.tenant_a, user=self.operator, entry_type='PRODUCTION',
            start_time=start, end_time=start + datetime.timedelta(hours=2))

    def _as_lead(self, perms):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, perms + ['full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)

    def _approve(self, entry=None):
        return self.client.post(f"/api/TimeEntries/{(entry or self.entry).id}/approve/")

    def test_a_holder_approves_someone_elses_finished_entry(self):
        self._as_lead(['view_timeentry', 'approve_timeentry'])
        resp = self._approve()
        self.assertEqual(resp.status_code, 200, resp.content)
        self.entry.refresh_from_db()
        self.assertTrue(self.entry.approved)
        self.assertEqual(self.entry.approved_by_id, self.user_a.id)
        self.assertIsNotNone(self.entry.approved_at)

    def test_without_the_permission_it_is_refused(self):
        self._as_lead(['view_timeentry', 'change_timeentry', 'add_timeentry'])
        self.assertEqual(self._approve().status_code, 403)

    def test_nobody_approves_their_own_time(self):
        self._as_lead(['view_timeentry', 'approve_timeentry'])
        start = timezone.now() - datetime.timedelta(hours=2)
        own = TimeEntry.objects.create(tenant=self.tenant_a, user=self.user_a, entry_type='PRODUCTION',
                                       start_time=start, end_time=start + datetime.timedelta(hours=1))
        resp = self._approve(own)
        self.assertEqual(resp.status_code, 400, resp.content)
        own.refresh_from_db()
        self.assertFalse(own.approved)

    def test_a_running_entry_cannot_be_approved(self):
        self._as_lead(['view_timeentry', 'approve_timeentry'])
        self.entry.end_time = None
        self.entry.save(update_fields=['end_time'])
        self.assertEqual(self._approve().status_code, 400)

    def test_approved_cannot_be_set_by_editing_the_entry(self):
        self._as_lead(['view_timeentry', 'change_timeentry'])
        resp = self.client.patch(f"/api/TimeEntries/{self.entry.id}/", {"approved": True}, format="json")
        self.assertIn(resp.status_code, (200, 400), resp.content)
        self.entry.refresh_from_db()
        self.assertFalse(self.entry.approved)

    def test_the_period_filter_reads_the_queue(self):
        self._as_lead(['view_timeentry'])
        day = self.entry.start_time.date()
        resp = self.client.get("/api/TimeEntries/", {
            "approved": "false", "end_time__isnull": "false",
            "start_time__gte": f"{day}T00:00:00Z",
            "start_time__lt": f"{day + datetime.timedelta(days=2)}T00:00:00Z"})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertIn(str(self.entry.id), [r["id"] for r in resp.json()["results"]])
