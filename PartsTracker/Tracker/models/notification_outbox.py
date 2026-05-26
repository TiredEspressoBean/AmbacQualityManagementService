"""
NotificationOutbox — persisted record of every dispatched notification.

Phase 1 schema. Source of truth for delivery status, retries, and audit.
Resolution of the underlying business issue is tracked on the source
record (NCR, CAPA, etc.), not on the outbox row.

Fields described in detail in `Documents/NOTIFICATION_SYSTEM_DESIGN.md`
under "NotificationOutbox". The Phase 1 model omits rule / template / user
FKs since rule resolution lands in Phase 3 and templates in Phase 2; the
columns are present but nullable to avoid a future schema migration when
those phases ship.
"""
from __future__ import annotations

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from .core import SecureModel


class NotificationStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    SENT = 'sent', 'Sent'
    FAILED = 'failed', 'Failed'
    RETRYING = 'retrying', 'Retrying'
    SUPPRESSED = 'suppressed', 'Suppressed'
    CANCELLED = 'cancelled', 'Cancelled'


class NotificationOutbox(SecureModel):
    """One row per dispatched notification. Status transitions:
    pending → sent | failed | retrying → sent | failed.
    """

    event_code = models.CharField(max_length=64, db_index=True)

    # Phase 1: rule resolution lands in Phase 3. Nullable so we don't need a
    # second migration when that ships.
    rule = models.ForeignKey(
        'Tracker.NotificationRule',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='outbox_rows',
    )

    # Exactly one recipient per row. `user` set for internal recipients
    # (in-app + email to tenant users); `external_contact` set for outbound
    # customer-scoped routing (Phase 3 customer rules → ExternalContacts).
    # Mutually exclusive — exactly one is populated per row.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notification_outbox_rows',
    )
    external_contact = models.ForeignKey(
        'Tracker.ExternalContact',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notification_outbox_rows',
    )

    channel = models.CharField(max_length=32)  # 'console', 'email', 'in_app', ...

    # `template` FK reserved for Phase 2 (NotificationTemplate). Skipping the
    # column entirely until that model ships.

    payload = models.JSONField(default=dict)
    correlation_id = models.CharField(max_length=128, db_index=True, blank=True)

    # GenericForeignKey back to the source record (the NCR, CAPA, ApprovalRequest,
    # etc. that this notification is about). Nullable because older rows pre-date
    # the field and events without an ack registration can't resolve their source.
    # Populated by the dispatcher from the ack registry's source_model binding.
    # Used by admin tooling that surfaces "all notifications about this source",
    # and reserved for a future per-contact pseudonymization workflow (Phase 6+).
    source_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )
    source_object_id = models.CharField(max_length=64, blank=True, default='')
    source_record = GenericForeignKey('source_content_type', 'source_object_id')

    rendered_subject = models.CharField(max_length=512, blank=True)
    rendered_body_text = models.TextField(blank=True)
    rendered_body_html = models.TextField(blank=True)
    rendered_action_url = models.CharField(max_length=1024, blank=True)

    # JSON list of AttachmentRef dicts; copied from payload at dispatch time.
    attachments = models.JSONField(default=list, blank=True)

    status = models.CharField(
        max_length=16,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
        db_index=True,
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)

    # In-app channel UI state. Null for email/console/etc.
    read_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    idempotency_key = models.CharField(max_length=255)
    is_test = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['event_code', 'idempotency_key'],
                name='notification_outbox_event_idempotency_unique',
            ),
        ]
        indexes = [
            # Hot path: pending/retrying rows the dispatcher worker picks up.
            models.Index(
                fields=['tenant', 'status'],
                name='notif_outbox_tenant_status',
                condition=models.Q(status__in=['pending', 'retrying']),
            ),
            # Activity log lookups.
            models.Index(fields=['tenant', 'event_code', 'created_at']),
            # In-app inbox query: user's unread, newest first.
            models.Index(fields=['user', 'read_at', 'created_at']),
            # Cross-row joins by source record.
            models.Index(fields=['correlation_id']),
            # Cooldown lookup at dispatch time: "did this rule fire to this
            # user within the last N seconds?" — Phase 3 min_gap_seconds check.
            models.Index(fields=['rule', 'user', 'created_at']),
            # PII redaction lookup: "which outbox rows fired for this source?"
            models.Index(
                fields=['source_content_type', 'source_object_id'],
                name='notif_outbox_source_idx',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.event_code} → {self.channel} [{self.status}]'
