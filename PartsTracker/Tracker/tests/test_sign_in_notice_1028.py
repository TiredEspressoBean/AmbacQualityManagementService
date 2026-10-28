"""The system-use notice at sign-in (NIST 800-171 3.1.9; user decision 2026-10-28).
Per tenant in Tenant.settings; empty changes nothing; when required, a sign-in must
carry the acknowledgement and each acknowledged sign-in is recorded."""
from auditlog.models import LogEntry
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

from Tracker.tests.base import TenantTestCase

NOTICE = "Authorised use only. Activity is monitored."


@override_settings(DEDICATED_MODE=False)
class SignInNoticeTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        cache.clear()  # the login throttle
        self.client = APIClient(HTTP_X_TENANT_ID=self.tenant_a.slug)

    def _set(self, text, requires_ack):
        self.tenant_a.settings = {**(self.tenant_a.settings or {}),
                                  'sign_in_notice': text, 'sign_in_notice_requires_ack': requires_ack}
        self.tenant_a.save()

    def _login(self, **extra):
        return self.client.post('/auth/login/', {'email': self.user_a.email, 'password': 'testpass123',
                                                 **extra}, format='json')

    def _acks(self):
        return LogEntry.objects.filter(action=LogEntry.Action.ACCESS,
                                       changes__action_type='notice_acknowledged',
                                       actor=self.user_a)

    def test_no_notice_shows_nothing_and_changes_nothing(self):
        r = self.client.get('/auth/sign-in-notice/')
        self.assertEqual(r.json(), {'text': '', 'requires_ack': False})
        self.assertEqual(self._login().status_code, 200)
        self.assertFalse(self._acks().exists())

    def test_the_notice_is_public_for_the_sign_in_tenant(self):
        self._set(NOTICE, True)
        r = self.client.get('/auth/sign-in-notice/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {'text': NOTICE, 'requires_ack': True})

    def test_a_shown_but_not_required_notice_does_not_block(self):
        self._set(NOTICE, False)
        self.assertEqual(self._login().status_code, 200)
        self.assertFalse(self._acks().exists())

    def test_a_required_notice_refuses_sign_in_without_the_tick(self):
        self._set(NOTICE, True)
        r = self._login()
        self.assertEqual(r.status_code, 400, r.content)
        self.assertEqual(r.json()['code'], 'notice_not_acknowledged')
        self.assertEqual(self._login(acknowledged_notice=False).status_code, 400)

    def test_an_acknowledged_sign_in_is_recorded(self):
        self._set(NOTICE, True)
        r = self._login(acknowledged_notice=True)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self._acks().count(), 1)

    def test_a_failed_sign_in_records_no_acknowledgement(self):
        self._set(NOTICE, True)
        r = self.client.post('/auth/login/', {'email': self.user_a.email, 'password': 'wrong',
                                              'acknowledged_notice': True}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertFalse(self._acks().exists())

    def test_blank_text_with_the_flag_on_is_no_notice(self):
        self._set("   ", True)
        self.assertEqual(self._login().status_code, 200)


class OrganizationSaveWithBlanksTests(TenantTestCase):
    """The page sends null for a cleared contact email / website (the generated client
    refuses ""); null clears rather than hitting the not-null column."""

    def test_null_clears_the_organization_fields_and_the_notice_saves(self):
        self.tenant_a.contact_email = "qa@example.com"
        self.tenant_a.website = "https://example.com"
        self.tenant_a.save()
        self.grant_tenant_permissions(self.user_a, self.tenant_a, ['change_tenantgroup'])
        self.authenticate_as(self.user_a, self.tenant_a)
        r = self.client.patch('/api/tenant/settings/', {
            'contact_email': None, 'website': None, 'contact_phone': None, 'address': None,
            'settings': {'sign_in_notice': NOTICE, 'sign_in_notice_requires_ack': True},
        }, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.tenant_a.refresh_from_db()
        self.assertEqual((self.tenant_a.contact_email, self.tenant_a.website), ("", ""))
        self.assertEqual(self.tenant_a.settings['sign_in_notice'], NOTICE)
