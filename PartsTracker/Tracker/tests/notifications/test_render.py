"""Render tests — template resolution, branding context, bleach sanitization, fallback."""
from __future__ import annotations

from django.test import TestCase

from Tracker.models import (
    NotificationOutbox,
    NotificationStatus,
    NotificationTemplate,
    Tenant,
    TenantNotificationBranding,
)
from Tracker.services.core.notifications.render import (
    render_outbox_row,
    sanitize_tenant_html,
)
from Tracker.tests.base import TenantContextMixin
from Tracker.utils.tenant_context import set_current_tenant_id, reset_current_tenant


def make_system_template(**fields):
    """Upsert a NotificationTemplate with tenant=NULL.

    SecureModel.save() auto-fills tenant_id from the ContextVar; we have
    to drop the ContextVar around the upsert so tenant stays NULL, which
    is how 'system default' templates are identified.

    Uses update_or_create so it doesn't collide with templates loaded by
    `setup_system_templates()` at post_migrate.
    """
    from Tracker.models import NotificationTemplate
    token = set_current_tenant_id(None)
    try:
        key_fields = {
            'tenant': None,
            'event_code': fields.pop('event_code'),
            'channel': fields.pop('channel'),
            'language': fields.pop('language', 'en'),
        }
        obj, _ = NotificationTemplate.unscoped.update_or_create(
            defaults=fields, **key_fields,
        )
        return obj
    finally:
        reset_current_tenant(token)


def clear_system_templates():
    """Hard-delete all system (tenant=NULL) NotificationTemplate rows.

    `setup_system_templates()` runs on post_migrate and seeds the test DB,
    so tests that assume "no templates exist" must explicitly clear first.
    Uses raw SQL to bypass SecureModel's soft-delete (which would otherwise
    leave the rows in place with `archived=True`, blocking update_or_create).
    Rolled back at the end of each test by TestCase's transaction.
    """
    from django.db import connection
    from Tracker.models import NotificationTemplate
    table = NotificationTemplate._meta.db_table
    with connection.cursor() as cursor:
        # Quote the identifier so Postgres preserves the table's mixed case
        # (default db_table is "Tracker_notificationtemplate"; unquoted it
        # folds to lowercase and the relation isn't found).
        cursor.execute(f'DELETE FROM "{table}" WHERE tenant_id IS NULL')


def make_row(tenant, *, event_code='ncr.opened', channel='email'):
    return NotificationOutbox(
        tenant=tenant,
        event_code=event_code,
        channel=channel,
        payload={'part_number': 'P-9', 'opened_by_name': 'Jane'},
        idempotency_key='render-test',
        status=NotificationStatus.PENDING,
    )


class RenderFallbackTests(TenantContextMixin, TestCase):

    def setUp(self):
        super().setUp()
        clear_system_templates()
        self.tenant = Tenant.objects.create(name='Render Tenant', slug='render-tenant')
        self.set_tenant_context(self.tenant)

    def test_fallback_when_no_template(self):
        """No template authored AND no wildcard → renderer's hardcoded
        fallback: subject=event label, body=payload dump."""
        row = make_row(self.tenant)
        render_outbox_row(row, row.payload, language='en')

        self.assertEqual(row.rendered_subject, 'Nonconformance Opened')
        self.assertIn('part_number=P-9', row.rendered_body_text)
        self.assertIn('opened_by_name=Jane', row.rendered_body_text)
        self.assertEqual(row.rendered_body_html, '')


class RenderTemplateResolutionTests(TenantContextMixin, TestCase):
    """Tenant → system-default-language → system-default-en → wildcard."""

    def setUp(self):
        super().setUp()
        clear_system_templates()
        self.tenant = Tenant.objects.create(name='Render Tenant', slug='render-tenant')
        self.set_tenant_context(self.tenant)

    def test_system_default_template_used_when_tenant_has_none(self):
        make_system_template(
            event_code='ncr.opened',
            channel='email',
            language='en',
            subject='System: {{ payload.part_number }}',
            body_text='System body for {{ payload.opened_by_name }}',
        )
        row = make_row(self.tenant)
        render_outbox_row(row, row.payload, language='en')

        self.assertEqual(row.rendered_subject, 'System: P-9')
        self.assertEqual(row.rendered_body_text, 'System body for Jane')

    def test_tenant_template_wins_over_system(self):
        make_system_template(
            event_code='ncr.opened',
            channel='email',
            language='en',
            subject='SYS',
            body_text='sys body',
        )
        NotificationTemplate.objects.create(
            tenant=self.tenant,
            event_code='ncr.opened',
            channel='email',
            language='en',
            subject='TENANT: {{ payload.part_number }}',
            body_text='tenant body',
        )
        row = make_row(self.tenant)
        render_outbox_row(row, row.payload, language='en')

        self.assertEqual(row.rendered_subject, 'TENANT: P-9')
        self.assertEqual(row.rendered_body_text, 'tenant body')

    def test_english_fallback_when_requested_language_missing(self):
        make_system_template(
            event_code='ncr.opened',
            channel='email',
            language='en',
            subject='EN subject',
            body_text='english',
        )
        row = make_row(self.tenant)
        render_outbox_row(row, row.payload, language='es')

        self.assertEqual(row.rendered_subject, 'EN subject')

    def test_wildcard_fallback_when_event_has_no_template(self):
        """Wildcard system template (event_code='*') catches events with
        no curated template — replaces the hardcoded payload-dump fallback."""
        make_system_template(
            event_code='*',
            channel='email',
            language='en',
            subject='Generic: {{ event.label }}',
            body_text='Wildcard body for {{ event.code }}',
        )
        row = make_row(self.tenant)  # ncr.opened, no specific template
        render_outbox_row(row, row.payload, language='en')

        self.assertEqual(row.rendered_subject, 'Generic: Nonconformance Opened')
        self.assertEqual(row.rendered_body_text, 'Wildcard body for ncr.opened')

    def test_event_specific_template_wins_over_wildcard(self):
        make_system_template(
            event_code='*',
            channel='email',
            language='en',
            subject='Generic',
            body_text='generic body',
        )
        make_system_template(
            event_code='ncr.opened',
            channel='email',
            language='en',
            subject='Specific NCR',
            body_text='specific body',
        )
        row = make_row(self.tenant)
        render_outbox_row(row, row.payload, language='en')

        self.assertEqual(row.rendered_subject, 'Specific NCR')


class RenderBrandingTests(TenantContextMixin, TestCase):

    def setUp(self):
        super().setUp()
        clear_system_templates()
        self.tenant = Tenant.objects.create(name='Branded Tenant', slug='branded-tenant')
        self.set_tenant_context(self.tenant)

    def test_branding_context_interpolates_into_template(self):
        TenantNotificationBranding.objects.create(
            tenant=self.tenant,
            company_name='Acme Co',
            email_from_name='Acme',
            email_signature='<p>From <strong>Acme</strong></p>',
        )
        make_system_template(
            event_code='ncr.opened',
            channel='email',
            language='en',
            subject='[{{ branding.company_name }}] NCR',
            body_html='Hello.{{ branding.email_signature_html|safe }}',
        )
        row = make_row(self.tenant)
        render_outbox_row(row, row.payload, language='en')

        self.assertEqual(row.rendered_subject, '[Acme Co] NCR')
        self.assertIn('<strong>Acme</strong>', row.rendered_body_html)


class SanitizeTenantHtmlTests(TestCase):

    def test_strips_script_tags(self):
        """bleach strips the <script> tag — inner text remains as literal text,
        not executable, which is the actual XSS defense."""
        out = sanitize_tenant_html('<p>Hi</p><script>alert(1)</script>')
        self.assertNotIn('<script', out)
        self.assertIn('<p>Hi</p>', out)

    def test_preserves_allowed_tags(self):
        html = '<p><strong>bold</strong> <em>em</em> <a href="https://x">link</a></p>'
        out = sanitize_tenant_html(html)
        self.assertIn('<strong>bold</strong>', out)
        self.assertIn('<em>em</em>', out)
        self.assertIn('href="https://x"', out)

    def test_strips_javascript_protocol(self):
        out = sanitize_tenant_html('<a href="javascript:alert(1)">x</a>')
        self.assertNotIn('javascript:', out)

    def test_empty_input_returns_empty(self):
        self.assertEqual(sanitize_tenant_html(''), '')
        self.assertEqual(sanitize_tenant_html(None), '')
