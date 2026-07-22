"""The in-app notification feed (/api/notifications/feed/).

The reader for what InAppChannel writes: self-scoped rows, unread count,
idempotent mark-read. Awareness surface — distinct from /inbox commitments.
"""
from django.utils import timezone
from rest_framework.test import APIClient

from Tracker.tests.base import TenantTestCase
from Tracker.models import NotificationOutbox


class NotificationFeedTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        from django.contrib.auth import get_user_model
        self.other = get_user_model().objects.create_user(
            username='other', email='other@example.com', password='x', tenant=self.tenant_a)

        self._seq = 0
        self.mine_unread = self._row(self.user_a, "First piece waiting - Final Test")
        self.mine_read = self._row(self.user_a, "CAPA assigned", read=True)
        self._row(self.user_a, "Held work order", channel="email")   # wrong channel
        self._row(self.other, "Someone else's notification")          # wrong user

        self.client = APIClient()
        self.client.force_authenticate(user=self.user_a)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant_a.id))

    def _row(self, user, subject, channel="in_app", read=False):
        self._seq += 1
        return NotificationOutbox.objects.create(
            tenant=self.tenant_a,
            event_code="fpi.requested",
            user=user,
            channel=channel,
            status="sent",
            rendered_subject=subject,
            rendered_action_url="/quality/inbox",
            read_at=timezone.now() if read else None,
            idempotency_key=f"test-{self._seq}",
        )

    def test_feed_lists_only_my_in_app_rows(self):
        response = self.client.get('/api/notifications/feed/')
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        rows = body.get('results', body)
        subjects = {r['rendered_subject'] for r in rows}
        self.assertEqual(subjects, {"First piece waiting - Final Test", "CAPA assigned"})

    def test_unread_filter_and_count(self):
        response = self.client.get('/api/notifications/feed/?unread=true')
        rows = response.json().get('results', response.json())
        self.assertEqual([r['rendered_subject'] for r in rows],
                         ["First piece waiting - Final Test"])

        count = self.client.get('/api/notifications/feed/unread-count/')
        self.assertEqual(count.json(), {'unread': 1})

    def test_mark_read_is_idempotent(self):
        url = f'/api/notifications/feed/{self.mine_unread.id}/mark-read/'
        first = self.client.post(url)
        self.assertEqual(first.status_code, 200, first.content)
        stamp = first.json()['read_at']
        self.assertIsNotNone(stamp)

        second = self.client.post(url)
        self.assertEqual(second.json()['read_at'], stamp)

    def test_mark_all_read(self):
        response = self.client.post('/api/notifications/feed/mark-all-read/')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json(), {'marked': 1})
        count = self.client.get('/api/notifications/feed/unread-count/')
        self.assertEqual(count.json(), {'unread': 0})

    def test_cannot_mark_someone_elses_row(self):
        theirs = NotificationOutbox.objects.filter(user=self.other).first()
        response = self.client.post(f'/api/notifications/feed/{theirs.id}/mark-read/')
        self.assertEqual(response.status_code, 404)

    def test_feed_is_read_only(self):
        response = self.client.post('/api/notifications/feed/', {})
        self.assertIn(response.status_code, (403, 405))