"""
Integration configuration and operational models.

IntegrationConfig: Per-tenant integration credentials and settings.
IntegrationSyncLog: History of sync operations.
ProcessedWebhook: Idempotency guard for webhook dedup.
"""

from django.db import models
from django.utils import timezone
from encrypted_model_fields.fields import EncryptedCharField
from uuid_utils.compat import uuid7


class IntegrationConfig(models.Model):
    """
    One row per integration per tenant. Stores credentials (encrypted),
    provider-specific config, and sync status.

    Follows the TenantLLMProvider pattern (Tracker/models/core.py).
    """

    class Provider(models.TextChoices):
        HUBSPOT = 'hubspot', 'HubSpot CRM'
        SALESFORCE = 'salesforce', 'Salesforce CRM'
        QUICKBOOKS = 'quickbooks', 'QuickBooks Online'
        XERO = 'xero', 'Xero'

    class SyncStatus(models.TextChoices):
        IDLE = 'IDLE', 'Idle'
        SYNCING = 'SYNCING', 'Syncing'
        ERROR = 'ERROR', 'Error'

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    tenant = models.ForeignKey(
        'Tracker.Tenant', on_delete=models.CASCADE, related_name='integrations'
    )
    provider = models.CharField(max_length=30, choices=Provider.choices)
    display_name = models.CharField(
        max_length=100, blank=True,
        help_text="Optional custom label (e.g. 'Production HubSpot')"
    )

    # State
    is_enabled = models.BooleanField(
        default=False,
        help_text="Disabled until credentials are entered and verified"
    )
    sync_status = models.CharField(
        max_length=10, choices=SyncStatus.choices, default=SyncStatus.IDLE
    )

    # Credentials — encrypted at rest
    # API key auth (HubSpot, etc.)
    api_key = EncryptedCharField(max_length=500, blank=True, default='')
    # OAuth2 auth (QuickBooks, Salesforce, etc.)
    oauth_refresh_token = EncryptedCharField(max_length=500, blank=True, default='')
    oauth_token_expires_at = models.DateTimeField(null=True, blank=True)
    # Webhook
    webhook_secret = EncryptedCharField(max_length=500, blank=True, default='')
    # Optional API URL override (e.g. sandbox environments)
    api_url = models.URLField(blank=True, default='')

    # Provider-specific configuration (validated by per-provider DRF serializer)
    # HubSpot: {"pipeline_id": "...", "debug_mode": false, "pipeline_tracking_enabled": true, ...}
    # QuickBooks: {"company_id": "...", "sandbox": true}
    config = models.JSONField(default=dict, blank=True)

    # Sync tracking
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_sync_error = models.TextField(null=True, blank=True)
    last_sync_stats = models.JSONField(
        default=dict, blank=True,
        help_text="Last sync result: created, updated, errors, duration"
    )

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'integrations_config'
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'provider'],
                name='integrations_config_tenant_provider_uniq'
            ),
        ]
        ordering = ['provider']

    def __str__(self):
        return f"{self.get_provider_display()} ({self.tenant.name})"


class IntegrationSyncLog(models.Model):
    """
    Records each sync operation for an integration.
    Used for troubleshooting, compliance auditing, and the admin UI sync status dashboard.

    IntegrationConfig.last_sync_stats is a denormalized convenience field for quick
    "is this integration healthy?" checks. This table is the real history.
    """

    class SyncType(models.TextChoices):
        FULL = 'FULL', 'Full Sync'
        INCREMENTAL = 'INCREMENTAL', 'Incremental Sync'
        SINGLE = 'SINGLE', 'Single Record Sync'
        PUSH = 'PUSH', 'Outbound Push'

    class Status(models.TextChoices):
        RUNNING = 'RUNNING', 'Running'
        SUCCESS = 'SUCCESS', 'Success'
        FAILED = 'FAILED', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    integration = models.ForeignKey(
        IntegrationConfig, on_delete=models.CASCADE, related_name='sync_logs'
    )
    sync_type = models.CharField(
        max_length=20, choices=SyncType.choices, default=SyncType.FULL
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.RUNNING
    )
    # Using default=timezone.now (not auto_now_add) to allow explicit set during data migration
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    records_processed = models.IntegerField(default=0)
    records_created = models.IntegerField(default=0)
    records_updated = models.IntegerField(default=0)
    error_message = models.TextField(null=True, blank=True)
    details = models.JSONField(
        default=dict, blank=True,
        help_text="Provider-specific details (e.g. pipeline stages synced, contacts created)"
    )

    class Meta:
        db_table = 'integrations_sync_log'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['-started_at']),
            models.Index(fields=['integration', 'status']),
        ]

    def __str__(self):
        duration = ""
        if self.completed_at:
            delta = self.completed_at - self.started_at
            duration = f" ({delta.total_seconds():.1f}s)"
        return f"{self.get_sync_type_display()} - {self.get_status_display()}{duration}"

    @property
    def duration(self):
        """Sync duration in seconds."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class ProcessedWebhook(models.Model):
    """Idempotency guard — don't process the same webhook event twice."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    tenant = models.ForeignKey('Tracker.Tenant', on_delete=models.CASCADE)
    integration = models.ForeignKey(IntegrationConfig, on_delete=models.CASCADE)
    external_event_id = models.CharField(max_length=200)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'integrations_processed_webhook'
        constraints = [
            models.UniqueConstraint(
                fields=['integration', 'external_event_id'],
                name='integrations_webhook_idempotency'
            ),
        ]

    def __str__(self):
        return f"{self.integration.provider}:{self.external_event_id}"
