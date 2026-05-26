"""Template rendering for outbox rows.

Pipeline:
    1. Resolve the right `NotificationTemplate` row for (tenant, event, channel, language)
       with fallback: tenant template → system default → English system default.
    2. Render `subject`, `body_text`, `body_html`, `action_url_template` via Django
       templates (autoescape on) against the event payload + tenant branding context.
    3. Bleach-sanitize tenant-controlled HTML fields (`email_signature`,
       `footer_disclaimer`) before they're interpolated into `body_html`.
    4. Write the rendered values onto the outbox row.

If no template exists for the (event, channel) pair, the row gets a
minimal fallback render (subject = event label, body = payload dump) so
the pipeline doesn't break — templates are added incrementally as events
ship.
"""
from __future__ import annotations

from typing import Optional

import bleach
from django.template import Context, Template

from .registry import get_event


# Bleach allow-list for tenant-controlled HTML fields. Strict enough to
# prevent XSS, permissive enough for basic formatting and links.
TENANT_HTML_ALLOWED_TAGS = (
    'p', 'br', 'strong', 'em', 'u', 'a', 'ul', 'ol', 'li', 'span',
)
TENANT_HTML_ALLOWED_ATTRS = {
    'a': ['href', 'title'],
    'span': [],  # no inline style
}
TENANT_HTML_ALLOWED_PROTOCOLS = ('http', 'https', 'mailto')


def sanitize_tenant_html(html: str) -> str:
    """Strip dangerous tags/attrs from tenant-controlled HTML before it
    enters a rendered email body. Returns sanitized HTML safe for use
    inside the rendered template's autoescape-marked-safe slot."""
    if not html:
        return ''
    return bleach.clean(
        html,
        tags=TENANT_HTML_ALLOWED_TAGS,
        attributes=TENANT_HTML_ALLOWED_ATTRS,
        protocols=TENANT_HTML_ALLOWED_PROTOCOLS,
        strip=True,
    )


def _resolve_template(tenant_id, event_code: str, channel: str, language: str):
    """Find the most specific template row for (tenant, event, channel, language).

    Resolution order:
        1. Tenant-specific template at the requested language
        2. System default (tenant IS NULL) at the requested language
        3. System default in English
        4. Wildcard system template (event_code='*') — generic fallback that
           renders ANY event using branding + structured payload, much
           prettier than the renderer's hardcoded key=value dump
        5. None (caller uses the hardcoded fallback render)
    """
    from Tracker.models import NotificationTemplate

    # Use `unscoped` so system templates (tenant IS NULL) are reachable —
    # SecureManager.objects would filter them out under tenant auto-scope.
    # Exclude archived rows — soft-deleted templates shouldn't render.
    qs = NotificationTemplate.unscoped.filter(
        event_code=event_code, channel=channel, archived=False,
    )

    # 1. Tenant template at requested language
    row = qs.filter(tenant_id=tenant_id, language=language).first()
    if row:
        return row

    # 2. System default at requested language
    row = qs.filter(tenant__isnull=True, language=language).first()
    if row:
        return row

    # 3. System default in English
    if language != 'en':
        row = qs.filter(tenant__isnull=True, language='en').first()
        if row:
            return row

    # 4. Wildcard system template — generic shape that works for any event.
    wildcard = NotificationTemplate.unscoped.filter(
        event_code='*', channel=channel, tenant__isnull=True, language='en',
        archived=False,
    ).first()
    if wildcard:
        return wildcard

    return None


def _get_branding(tenant_id):
    """Return TenantNotificationBranding for the tenant, or None.

    Caller treats None as "no branding configured" and falls back to
    project-level defaults for from-name / footer / etc.
    """
    from Tracker.models import TenantNotificationBranding
    return TenantNotificationBranding.objects.filter(tenant_id=tenant_id).first()


def render_outbox_row(row, payload_dict: dict, *, language: str = 'en') -> None:
    """Populate the rendered_* fields on an unsaved (or saved) outbox row.

    Caller is responsible for `row.save(update_fields=[...])` afterwards.

    Args:
        row: NotificationOutbox instance (status='pending').
        payload_dict: serialized payload dict (already JSON-safe).
        language: recipient's preferred language; falls through to English.
    """
    event = get_event(row.event_code)
    template = _resolve_template(row.tenant_id, row.event_code, row.channel, language)
    branding = _get_branding(row.tenant_id)

    # Branding context. None-tolerant — if no branding row, every field is empty
    # and the template's default-handling shows defaults.
    branding_ctx = {
        'company_name': (branding.company_name if branding else '') or '',
        'logo_url': (branding.logo_url if branding else '') or '',
        'primary_color': (branding.primary_color if branding else '#003366'),
        'support_email': (branding.support_email if branding else '') or '',
        'support_phone': (branding.support_phone if branding else '') or '',
        'email_from_name': (branding.email_from_name if branding else 'UQMES'),
        'email_signature_html': sanitize_tenant_html(branding.email_signature if branding else ''),
        'footer_disclaimer_html': sanitize_tenant_html(branding.footer_disclaimer if branding else ''),
    }

    context_dict = {
        'event': {'code': event.code, 'label': event.label, 'domain': event.domain},
        'payload': payload_dict,
        'branding': branding_ctx,
    }

    if template:
        # Render action URL first so body templates can reference it via
        # {{ action_url }} for "View this …" links inside email bodies.
        action_url = (
            Template(template.action_url_template).render(Context(context_dict))
            if template.action_url_template else ''
        )
        ctx = Context({**context_dict, 'action_url': action_url})

        row.rendered_subject = Template(template.subject).render(ctx)
        row.rendered_body_text = Template(template.body_text).render(ctx) if template.body_text else ''
        row.rendered_body_html = Template(template.body_html).render(ctx) if template.body_html else ''
        row.rendered_action_url = action_url
    else:
        # No template authored AND no wildcard fallback row exists.
        # Subject = event label; body = payload key=value dump. With the
        # wildcard template loaded by `setup_system_templates`, this branch
        # only fires before the post_migrate setup runs (e.g., fresh test DB
        # for a non-templates test).
        row.rendered_subject = event.label
        row.rendered_body_text = _payload_summary(payload_dict)
        row.rendered_body_html = ''
        row.rendered_action_url = ''


def _payload_summary(payload_dict: dict) -> str:
    """Phase 2 fallback — same shape as the Phase 1 dispatcher stub."""
    skip = {'tenant_id', 'attachments'}
    return '\n'.join(f'{k}={v}' for k, v in payload_dict.items() if k not in skip)
