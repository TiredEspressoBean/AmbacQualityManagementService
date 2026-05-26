"""
Phase 2 notification preference + branding + template models.

Schemas from Documents/NOTIFICATION_SYSTEM_DESIGN.md. These models layer on
top of NotificationOutbox (Phase 1) to provide:

- TenantNotificationDefault — admin-controlled defaults for which channels
  are enabled per (event, channel). With a nullable `role` FK, defaults can
  be tenant-wide (role IS NULL) or role-scoped (role = TenantGroup).
- UserNotificationPreference — per-user override layer. Always-write
  semantics: every explicit toggle records a row that wins over every
  default layer.
- TenantNotificationBranding — one row per tenant, white-label fields
  applied to outbound emails (logo, colors, signature, from-name).
- NotificationTemplate — system-authored, code-shipped via loaddata.
  Tenant overrides reserved for future use.

Resolution precedence (most specific wins; first match short-circuits):
    1. UserNotificationPreference (this user, this event, this channel)
    2. TenantNotificationDefault where role ∈ user's TenantGroups (union: any-enabled wins)
    3. TenantNotificationDefault where role IS NULL (tenant-wide)
    4. EVENT_REGISTRY[event_code].default_channels (codebase default)
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

from .core import SecureModel


# =============================================================================
# TenantNotificationDefault
# =============================================================================

class TenantNotificationDefault(SecureModel):
    """Admin-controlled defaults for which channels fire per (event, channel).

    Two row variants distinguished by `role`:
      - role IS NULL  → tenant-wide default
      - role = FK     → role-scoped default; overrides tenant-wide for users in that role

    Seeded on tenant creation by walking EVENT_REGISTRY (tenant-wide rows only).
    Role-scoped rows are authored by admins via the matrix grid UI's role
    selector.
    """

    event_code = models.CharField(max_length=64, db_index=True)
    channel = models.CharField(max_length=32)
    role = models.ForeignKey(
        'Tracker.TenantGroup',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_index=True,
        related_name='notification_defaults',
        help_text='Null = tenant-wide default; FK = role-scoped default.',
    )
    enabled = models.BooleanField(default=False)

    class Meta:
        constraints = [
            # Postgres ≥15: treat NULL role as a single value for uniqueness so
            # the tenant-wide row cannot duplicate.
            models.UniqueConstraint(
                fields=['tenant', 'event_code', 'channel', 'role'],
                name='notification_default_unique',
                nulls_distinct=False,
            ),
        ]
        indexes = [
            # Resolver hot path: lookup by user's tenant + event + channel,
            # filtering on role (NULL or user's role_ids).
            models.Index(fields=['tenant', 'event_code', 'channel']),
        ]

    def __str__(self) -> str:
        scope = self.role.name if self.role_id else 'tenant-wide'
        return f'{self.event_code}/{self.channel} ({scope}) = {self.enabled}'


# =============================================================================
# UserNotificationPreference
# =============================================================================

class UserNotificationPreference(SecureModel):
    """Per-user override layer — the most specific layer in channel resolution.

    Stored as a JSONField for fast read at dispatch time. Always-write
    semantics: any explicit toggle persists, even when matching the
    inherited state. Later changes to role/tenant defaults do not
    silently flip user-set values.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
    )
    # Shape: {event_code: {channel: bool}}
    # Absent entries fall through to the role/tenant/registry layer.
    preferences = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['tenant', 'user']),
        ]

    def __str__(self) -> str:
        return f'NotificationPreference<user={self.user_id}>'


# =============================================================================
# TenantNotificationBranding
# =============================================================================

class TenantNotificationBranding(SecureModel):
    """White-label branding fields applied to outbound notifications.

    Single row per tenant. Tenant-controlled HTML fields (`email_signature`,
    `footer_disclaimer`) are sanitized via bleach with a tight allow-list
    before render. `logo_url` restricted to allow-listed URL schemes.
    """

    company_name = models.CharField(max_length=128, blank=True)
    logo_url = models.CharField(max_length=512, blank=True)
    primary_color = models.CharField(max_length=16, default='#003366')
    support_email = models.EmailField(blank=True)
    support_phone = models.CharField(max_length=32, blank=True)
    email_from_name = models.CharField(max_length=128, default='UQMES')
    email_signature = models.TextField(blank=True, max_length=2000)
    footer_disclaimer = models.TextField(blank=True, max_length=500)
    default_language = models.CharField(max_length=8, default='en')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant'],
                name='notification_branding_one_per_tenant',
            ),
        ]

    def __str__(self) -> str:
        return f'NotificationBranding<{self.company_name or self.tenant_id}>'


# =============================================================================
# NotificationTemplate
# =============================================================================

class NotificationTemplate(SecureModel):
    """System-authored, code-shipped templates.

    Loaded via `loaddata` on deploy. Tenant overrides supported by FK
    nullability — `tenant IS NULL` is the system default; a tenant row
    overrides for that tenant. Resolution at dispatch:
        tenant template (tenant, event_code, channel, language)
        → system default (tenant=NULL, event_code, channel, language)
        → English fallback (tenant=NULL, event_code, channel, language='en')

    Not a VersionedModel — system templates ship as code, not via
    DRAFT→RELEASED. `version` is a flat audit integer incremented on each
    loaddata.
    """

    event_code = models.CharField(max_length=64, db_index=True)
    channel = models.CharField(max_length=32)
    language = models.CharField(max_length=8, default='en')

    subject = models.CharField(max_length=255)
    body_text = models.TextField(blank=True)
    body_html = models.TextField(blank=True)
    severity = models.CharField(
        max_length=16,
        choices=(
            ('info', 'Info'),
            ('warn', 'Warning'),
            ('critical', 'Critical'),
        ),
        default='info',
    )
    action_url_template = models.CharField(max_length=512, blank=True)
    icon = models.CharField(max_length=64, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'event_code', 'channel', 'language'],
                name='notification_template_unique',
                nulls_distinct=False,  # tenant IS NULL is "system default"
            ),
        ]
        indexes = [
            # Resolver lookup: by event + channel + language, filtering by tenant.
            models.Index(fields=['event_code', 'channel', 'language']),
        ]

    def __str__(self) -> str:
        scope = self.tenant_id or 'system'
        return f'Template<{self.event_code}/{self.channel}/{self.language} @ {scope}>'
