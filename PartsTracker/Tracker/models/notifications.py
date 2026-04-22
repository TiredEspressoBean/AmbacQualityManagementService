"""
Event-driven notification rules.

A NotificationRule binds an event type (e.g. STEP_FAILURE) to a recipient
spec. When `services.core.notification.notify()` fires for that event type,
the dispatcher finds matching rules, resolves recipients, applies the
per-rule cooldown, and creates NotificationTask records that the existing
Celery pipeline sends.

Rules are tenant-scoped (SecureModel). The GFK `scope` must point at an
object in the same tenant; this is enforced in `clean()`.
"""
from __future__ import annotations

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models

from .core import SecureModel, TenantGroup


class NotificationEventType(models.TextChoices):
    STEP_FAILURE = 'STEP_FAILURE', 'Part failed at step'
    WORK_ORDER_HELD_TOO_LONG = 'WORK_ORDER_HELD_TOO_LONG', 'Work order held too long'
    WORK_ORDER_STALLED = 'WORK_ORDER_STALLED', 'Work order stalled'
    WORK_ORDER_OVERDUE = 'WORK_ORDER_OVERDUE', 'Work order overdue'
    # Future: MEASUREMENT_OOS, SPC_VIOLATION, LIFE_LIMIT_REACHED, ...


class NotificationRule(SecureModel):
    """
    Declarative rule: "when <event> happens on <scope>, notify <recipients>
    via <channel>, no more often than every <cooldown> seconds per recipient."

    Recipient sources are additive — static users, static tenant groups, and
    a named role resolver are all unioned. At least one must yield a user
    for the rule to fire.
    """

    CHANNEL_TYPES = [
        ('EMAIL', 'Email'),
        ('IN_APP', 'In-App Notification'),
    ]

    name = models.CharField(
        max_length=200,
        help_text='Admin-friendly label shown in the rule list.'
    )
    description = models.TextField(blank=True)

    event_type = models.CharField(
        max_length=50,
        choices=NotificationEventType.choices,
        db_index=True,
    )

    # Scope: optional GFK narrowing this rule to a specific object
    # (e.g. a particular Step). Null scope means "every event of this type
    # in the tenant".
    scope_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='notification_rules',
    )
    scope_object_id = models.CharField(max_length=64, null=True, blank=True)
    scope = GenericForeignKey('scope_content_type', 'scope_object_id')

    # Recipients — any combination, unioned at dispatch time.
    recipient_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='notification_rules_as_recipient',
    )
    recipient_groups = models.ManyToManyField(
        TenantGroup,
        blank=True,
        related_name='notification_rules',
    )
    recipient_resolver_key = models.CharField(
        max_length=64,
        blank=True,
        help_text=(
            'Name of a registered role resolver (e.g. "step_execution_assignee"). '
            'Resolver takes the event payload and returns an iterable of Users.'
        ),
    )

    channel_type = models.CharField(
        max_length=20,
        choices=CHANNEL_TYPES,
        default='EMAIL',
    )

    min_gap_seconds = models.PositiveIntegerField(
        default=3600,
        help_text=(
            'Per-(rule, recipient) cooldown. A recipient will not receive '
            'another notification from this rule until this many seconds '
            'have passed. 0 disables dedup.'
        ),
    )

    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['tenant', 'event_type', 'is_active']),
            models.Index(fields=['scope_content_type', 'scope_object_id']),
        ]

    def __str__(self):
        return f'{self.name} [{self.event_type}]'

    def clean(self):
        super().clean()
        # Tenant match on the GFK target. Without this, a rule saved via
        # raw SQL or a bug could match triggers in another tenant.
        if self.scope_content_type_id and self.scope_object_id:
            scope = self.scope
            if scope is None:
                raise ValidationError({'scope_object_id': 'Scope object not found.'})
            scope_tenant_id = getattr(scope, 'tenant_id', None)
            # full_clean() runs before SecureModel.save() auto-injects
            # tenant_id on a new row, so fall back to the ContextVar when
            # the attribute isn't set yet.
            expected_tenant_id = self.tenant_id
            if expected_tenant_id is None:
                from Tracker.utils.tenant_context import current_tenant_var
                expected_tenant_id = current_tenant_var.get()
            # ContextVar stores tenant_id as str; SecureModel.tenant_id
            # is UUID. Normalize both to str for comparison.
            if scope_tenant_id is not None and expected_tenant_id is not None \
                    and str(scope_tenant_id) != str(expected_tenant_id):
                raise ValidationError('Scope object belongs to a different tenant.')

    def save(self, *args, **kwargs):
        # full_clean runs clean() so the GFK tenant-match check always fires
        # on save, even for code paths that skip admin/serializer validation.
        # M2M validation (recipients-exist-in-tenant) happens at the
        # serializer layer via TenantScopedPrimaryKeyRelatedField.
        self.full_clean(exclude=['recipient_users', 'recipient_groups'])
        super().save(*args, **kwargs)
