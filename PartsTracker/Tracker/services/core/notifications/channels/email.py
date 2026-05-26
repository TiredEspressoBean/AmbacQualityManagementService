"""EmailChannel — Phase 2 email delivery via Django core mail.

Reads the rendered fields off the outbox row, builds an
EmailMultiAlternatives, and hands off to the configured SMTP backend.
Failures raise so the Celery task retries with backoff (see tasks.py).

Phase 2 scope:
    - HTML + text body
    - Tenant `email_from_name` controls display name; from-address comes
      from DEFAULT_FROM_EMAIL deployment setting
    - Attachments resolved per AttachmentRef on the row (Phase 2 v1 only
      handles `type='generated_report'`; other types extend this adapter
      as their events ship)
    - No unsubscribe header in Phase 2 — added in Phase 4 alongside the
      signed-token unsubscribe page
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

if TYPE_CHECKING:
    from Tracker.models import NotificationOutbox

logger = logging.getLogger(__name__)


class EmailChannel:
    code = 'email'

    def send(self, outbox_row: 'NotificationOutbox') -> None:
        if not outbox_row.user_id:
            # Phase 2 only delivers to internal users (have a User FK).
            # ExternalContact recipients land with Phase 3.
            logger.info('email channel: outbox %s has no user; skipping', outbox_row.id)
            return

        from Tracker.models import TenantNotificationBranding

        user = outbox_row.user
        to_addr = user.email
        if not to_addr:
            raise ValueError(f'user {user.id} has no email address')

        # From-name from tenant branding, fall back to the registered Django default.
        branding = TenantNotificationBranding.objects.filter(tenant_id=outbox_row.tenant_id).first()
        from_name = (branding.email_from_name if branding else None) or 'UQMES'
        from_email = settings.DEFAULT_FROM_EMAIL
        if from_name and not from_email.startswith(from_name):
            from_address = f'{from_name} <{from_email}>'
        else:
            from_address = from_email

        subject = outbox_row.rendered_subject or '(no subject)'
        body_text = outbox_row.rendered_body_text or ''
        body_html = outbox_row.rendered_body_html

        msg = EmailMultiAlternatives(
            subject=subject,
            body=body_text,
            from_email=from_address,
            to=[to_addr],
        )
        if body_html:
            msg.attach_alternative(body_html, 'text/html')

        for attachment_ref in (outbox_row.attachments or []):
            try:
                self._attach_artifact(msg, attachment_ref, outbox_row)
            except Exception:
                logger.exception('email channel: failed to attach %s on outbox %s', attachment_ref, outbox_row.id)
                # Don't fail the send for a missing attachment — the body
                # may still be useful. Surface in logs.

        # send() raises on transport failure — propagate so the celery task retries.
        msg.send(fail_silently=False)

    def supports_attachments(self) -> bool:
        return True

    def max_body_length(self) -> int | None:
        return None  # no hard cap on SMTP body length

    # -------- attachment resolvers --------

    def _attach_artifact(self, msg: EmailMultiAlternatives, ref: dict, outbox_row: 'NotificationOutbox') -> None:
        """Resolve an AttachmentRef to bytes and attach.

        v1 only handles `type='generated_report'`. Adding new artifact
        types is a localized change here — no central registry.
        """
        ref_type = ref.get('type')
        ref_id = ref.get('id')
        if not ref_type or ref_id is None:
            return

        if ref_type == 'generated_report':
            # GeneratedReport lookup — keep import local to avoid cycles.
            try:
                from Tracker.models import GeneratedReport  # type: ignore
            except ImportError:
                logger.warning('email channel: GeneratedReport model not available; skipping attachment')
                return
            report = GeneratedReport.objects.filter(id=ref_id, tenant_id=outbox_row.tenant_id).first()
            if not report or not report.pdf_bytes:
                return
            filename = getattr(report, 'filename', None) or f'report-{ref_id}.pdf'
            msg.attach(filename, report.pdf_bytes, 'application/pdf')
            return

        logger.warning('email channel: unknown attachment type %s on outbox %s', ref_type, outbox_row.id)
