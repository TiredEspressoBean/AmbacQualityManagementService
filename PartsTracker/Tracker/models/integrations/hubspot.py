"""
HubSpot integration implementation.

ARCHITECTURE NOTE - Composition over Inheritance:
=================================================

CURRENT STATE (Option 4 - Pragmatic Composition):
- HubSpot fields are inline in Orders/Companies models (nullable/optional)
- Methods delegate to services or external functions
- Simple, explicit, no circular imports

FUTURE MIGRATION PATH (Option 1 - True Composition):
When you want cleaner separation, refactor to:

    class HubSpotOrderSync(SecureModel):
        '''Separate model for HubSpot integration data'''
        order = models.OneToOneField('Orders', related_name='hubspot')
        deal_id = models.CharField(max_length=60, unique=True)
        current_gate = models.ForeignKey('ExternalAPIOrderIdentifier', ...)
        last_synced_stage = models.CharField(...)
        last_synced_at = models.DateTimeField(...)

        def push_to_hubspot(self):
            # All HubSpot logic encapsulated here
            pass

    # Usage: order.hubspot.push_to_hubspot()

Benefits of migration:
- Orders can exist without HubSpot data (true optional)
- Easy to add other integrations (Salesforce, NetSuite) without touching Orders
- Query HubSpot sync data independently: HubSpotOrderSync.objects.filter(...)
- No impact on Orders queries that don't need HubSpot data

For now, we keep it simple with inline fields.

Models:
- HubSpotSyncLog: Tracks sync operations for debugging

Services (future):
- HubSpotOrderService: Encapsulates HubSpot operations for Orders
- HubSpotCompanyService: Encapsulates HubSpot operations for Companies
"""

from django.db import models
from django.utils import timezone

# NOTE: ExternalAPIOrderIdentifier moved to core.py to avoid circular imports


class HubSpotSyncLog(models.Model):
    """
    Tracks HubSpot sync operations for debugging and monitoring.

    Records each sync attempt with timing, counts, and error details.
    Useful for audit trails and identifying sync issues.
    """

    SYNC_TYPE_CHOICES = [
        ('full', 'Full Sync'),
        ('incremental', 'Incremental Sync'),
        ('single', 'Single Deal Sync'),
    ]

    STATUS_CHOICES = [
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    sync_type = models.CharField(max_length=20, choices=SYNC_TYPE_CHOICES, default='full')
    """Type of sync operation performed."""

    started_at = models.DateTimeField(auto_now_add=True)
    """When the sync operation began."""

    completed_at = models.DateTimeField(null=True, blank=True)
    """When the sync operation finished (null if still running)."""

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    """Current status of the sync operation."""

    deals_processed = models.IntegerField(default=0)
    """Total number of deals processed during this sync."""

    deals_created = models.IntegerField(default=0)
    """Number of new orders created from HubSpot deals."""

    deals_updated = models.IntegerField(default=0)
    """Number of existing orders updated from HubSpot deals."""

    error_message = models.TextField(null=True, blank=True)
    """Error details if the sync failed."""

    class Meta:
        verbose_name = "HubSpot Sync Log"
        verbose_name_plural = "HubSpot Sync Logs"
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['-started_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        duration = ""
        if self.completed_at:
            delta = self.completed_at - self.started_at
            duration = f" ({delta.total_seconds():.1f}s)"
        return f"{self.get_sync_type_display()} - {self.get_status_display()} at {self.started_at}{duration}"

    @property
    def duration(self):
        """Calculate sync duration in seconds."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


# ============================================================================
# LEGACY MIXINS - DEPRECATED (kept for reference)
# ============================================================================
#
# NOTE: These mixins are NO LONGER USED. We use composition instead (inline fields).
# Mixins caused circular import issues and tight coupling.
#
# HubSpot fields are now directly in Orders/Companies models as nullable fields.
# This is true composition - models can exist with or without HubSpot integration.
#
# If you need these patterns, consider:
# - Create HubSpotOrderService for behavior (composition via services)
# - Create HubSpotOrderSync model for data (composition via OneToOneField)
#
# ============================================================================

# Mixins are deprecated - see note above
# All mixin code has been removed to avoid circular imports
# HubSpot fields are now inline in Orders/Companies models
