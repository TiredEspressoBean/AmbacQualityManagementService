"""
Base mixins for external system integrations.

These abstract base classes provide common patterns that any external
integration (HubSpot, Salesforce, NetSuite, etc.) can inherit from.
"""

from django.db import models
from django.utils import timezone


class ExternalSyncMixin(models.Model):
    """
    Base mixin for models that sync with external systems.

    Provides common fields and methods for tracking synchronization state.
    Subclass this for specific integrations (e.g., HubSpotSyncMixin).

    Abstract model - does not create a database table.
    """

    # Generic external system identifier
    external_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="ID from the external system (e.g., HubSpot deal ID, Salesforce opportunity ID)"
    )

    # Sync tracking
    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this record was last synchronized with the external system"
    )

    # Metadata for troubleshooting
    last_sync_error = models.TextField(
        null=True,
        blank=True,
        help_text="Last error message from sync attempt (if any)"
    )

    class Meta:
        abstract = True

    def mark_synced(self, error=None):
        """
        Mark this record as synced (or failed).

        Args:
            error: Optional error message if sync failed
        """
        self.last_synced_at = timezone.now()
        if error:
            self.last_sync_error = str(error)
        else:
            self.last_sync_error = None

    def is_synced_recently(self, hours=1):
        """
        Check if this record was synced recently.

        Args:
            hours: Number of hours to consider "recent"

        Returns:
            bool: True if synced within the specified hours
        """
        if not self.last_synced_at:
            return False

        from datetime import timedelta
        return timezone.now() - self.last_synced_at < timedelta(hours=hours)

    def push_to_external(self):
        """
        Push this record to the external system.

        Override in subclass to implement specific integration logic.
        Should delegate to a service class for actual API calls.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement push_to_external()"
        )

    def pull_from_external(self):
        """
        Pull updates from the external system.

        Override in subclass to implement specific integration logic.
        Should delegate to a service class for actual API calls.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement pull_from_external()"
        )


class ExternalPipelineMixin(models.Model):
    """
    Base mixin for models that track pipeline stages from external systems.

    Useful for Orders/Deals that progress through stages (Qualification,
    Proposal, Negotiation, Closed Won, etc.).

    Abstract model - does not create a database table.
    """

    # Stage tracking - implement as ForeignKey in subclass
    # external_stage = models.ForeignKey(...)

    last_stage_change = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the pipeline stage last changed"
    )

    class Meta:
        abstract = True

    def get_pipeline_progress(self):
        """
        Calculate progress through the pipeline.

        Override in subclass to implement specific pipeline logic.

        Returns:
            dict: Pipeline progress information
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement get_pipeline_progress()"
        )

    def mark_stage_changed(self):
        """Mark that the pipeline stage has changed."""
        self.last_stage_change = timezone.now()
