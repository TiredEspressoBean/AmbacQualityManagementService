"""Channel adapter tests — EmailChannel + InAppChannel."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings

from Tracker.models import (
    NotificationOutbox,
    NotificationStatus,
    Tenant,
    TenantNotificationBranding,
)
from Tracker.services.core.notifications.channels.email import EmailChannel
from Tracker.services.core.notifications.channels.in_app import InAppChannel
from Tracker.tests.base import TenantContextMixin

User = get_user_model()


def make_row(tenant, user, *, channel='email', **overrides):
    defaults = dict(
        tenant=tenant,
        user=user,
        event_code='ncr.opened',
        channel=channel,
        payload={'part_number': 'P-1'},
        rendered_subject='NCR Opened',
        rendered_body_text='Body text',
        rendered_body_html='<p>Body HTML</p>',
        idempotency_key=f'test-{channel}',
        status=NotificationStatus.PENDING,
    )
    defaults.update(overrides)
    return NotificationOutbox.objects.create(**defaults)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='noreply@example.com',
)
class EmailChannelTests(TenantContextMixin, TestCase):

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name='Email Tenant', slug='email-tenant')
        self.set_tenant_context(self.tenant)
        self.user = User.objects.create_user(
            email='recipient@example.com',
            username='recipient@example.com',
            tenant=self.tenant,
        )
        self.channel = EmailChannel()
        mail.outbox = []

    def test_sends_email_to_user(self):
        row = make_row(self.tenant, self.user)
        self.channel.send(row)

        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ['recipient@example.com'])
        self.assertEqual(msg.subject, 'NCR Opened')
        self.assertEqual(msg.body, 'Body text')

    def test_attaches_html_alternative(self):
        row = make_row(self.tenant, self.user)
        self.channel.send(row)

        msg = mail.outbox[0]
        self.assertEqual(len(msg.alternatives), 1)
        html, mime = msg.alternatives[0]
        self.assertEqual(mime, 'text/html')
        self.assertIn('<p>Body HTML</p>', html)

    def test_from_address_uses_tenant_email_from_name(self):
        TenantNotificationBranding.objects.create(
            tenant=self.tenant, email_from_name='Acme QA',
        )
        row = make_row(self.tenant, self.user)
        self.channel.send(row)

        msg = mail.outbox[0]
        self.assertIn('Acme QA', msg.from_email)
        self.assertIn('noreply@example.com', msg.from_email)

    def test_skips_row_with_no_user(self):
        """Phase 2 only delivers to internal users; rows without user are skipped, not raised."""
        row = make_row(self.tenant, None)
        self.channel.send(row)
        self.assertEqual(len(mail.outbox), 0)

    def test_raises_when_user_has_no_email(self):
        self.user.email = ''
        self.user.save(update_fields=['email'])
        row = make_row(self.tenant, self.user)

        with self.assertRaises(ValueError):
            self.channel.send(row)


class InAppChannelTests(TenantContextMixin, TestCase):

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name='InApp Tenant', slug='in-app-tenant')
        self.set_tenant_context(self.tenant)
        self.user = User.objects.create_user(
            email='inbox@example.com',
            username='inbox@example.com',
            tenant=self.tenant,
        )

    def test_send_is_noop_does_not_raise(self):
        """The row IS the notification — no wire delivery, no exception."""
        channel = InAppChannel()
        row = make_row(self.tenant, self.user, channel='in_app')

        result = channel.send(row)
        self.assertIsNone(result)

    def test_supports_attachments_false(self):
        self.assertFalse(InAppChannel().supports_attachments())
