"""
HubSpot-specific link models.

Per-provider link tables (not generic) because each provider has different
field names and semantics. HubSpot has deals with pipeline stages,
Salesforce has opportunities with forecast categories, QuickBooks has invoices
with line items.
"""

import re

from django.db import models
from django.utils import timezone
from model_utils import FieldTracker
from uuid_utils.compat import uuid7

from integrations.models.config import IntegrationConfig


class HubSpotPipelineStage(models.Model):
    """
    Maps HubSpot pipeline stage IDs to human-readable names.

    Provider-specific because pipeline stages are a HubSpot concept.
    Salesforce would have SalesforceOpportunityStage with different properties.
    """

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    integration = models.ForeignKey(
        IntegrationConfig, on_delete=models.CASCADE,
        related_name='hubspot_pipeline_stages'
    )
    stage_name = models.CharField(max_length=100)
    api_id = models.CharField(max_length=50)
    pipeline_id = models.CharField(max_length=50, null=True, blank=True)
    display_order = models.IntegerField(default=0)
    include_in_progress = models.BooleanField(
        default=False,
        help_text="Include in customer-facing pipeline progress tracking"
    )
    last_synced_at = models.DateTimeField(null=True, blank=True)

    # Maps this HubSpot stage to a native Milestone in the Tracker app.
    # Used by sync to set order.current_milestone.
    mapped_milestone = models.ForeignKey(
        'Tracker.Milestone', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='hubspot_stages'
    )

    class Meta:
        db_table = 'integrations_hubspot_pipeline_stage'
        ordering = ['pipeline_id', 'display_order']
        constraints = [
            models.UniqueConstraint(
                fields=['integration', 'api_id'],
                name='hubspot_stage_integration_apiid_uniq'
            ),
        ]

    def __str__(self):
        return self.stage_name

    def get_customer_display_name(self):
        """
        Remove 'Gate [Word] ' prefix for customer-facing display.

        Examples:
            'Gate One Quotation' -> 'Quotation'
            'Gate Two Design Review' -> 'Design Review'
            'Gate Five' -> 'Gate Five' (no content after prefix)
            'Closed Won' -> 'Closed Won' (no prefix)
        """
        cleaned = re.sub(r'^Gate\s+\w+\s+', '', self.stage_name)
        return cleaned if cleaned != self.stage_name else self.stage_name


class HubSpotOrderLink(models.Model):
    """
    Links a local Order to a HubSpot Deal.

    OneToOneField because an order comes from one external system.
    PROTECT on integration prevents silent orphaning when an integration is deleted.
    """

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    order = models.OneToOneField(
        'Tracker.Orders', on_delete=models.CASCADE,
        related_name='hubspot_link'
    )
    integration = models.ForeignKey(
        IntegrationConfig, on_delete=models.PROTECT,
        related_name='hubspot_order_links'
    )

    deal_id = models.CharField(max_length=60)
    current_stage = models.ForeignKey(
        HubSpotPipelineStage, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='linked_orders'
    )
    last_synced_stage_name = models.CharField(max_length=100, null=True, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_sync_error = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    # Track changes to current_stage for the post_save signal
    stage_tracker = FieldTracker(fields=['current_stage'])

    class Meta:
        db_table = 'integrations_hubspot_order_link'
        constraints = [
            models.UniqueConstraint(
                fields=['integration', 'deal_id'],
                name='hubspot_order_link_integration_dealid_uniq'
            ),
        ]

    def __str__(self):
        return f"Order {self.order_id} <-> hubspot:{self.deal_id}"


class HubSpotCompanyLink(models.Model):
    """
    Links a local Company to a HubSpot Company.

    FK (not OneToOne) because a company could also be linked from other providers
    (QuickBooksCompanyLink, etc.) on the same Company instance.
    """

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    company = models.ForeignKey(
        'Tracker.Companies', on_delete=models.CASCADE,
        related_name='hubspot_links'
    )
    integration = models.ForeignKey(
        IntegrationConfig, on_delete=models.PROTECT,
        related_name='hubspot_company_links'
    )
    hubspot_company_id = models.CharField(max_length=50)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'integrations_hubspot_company_link'
        constraints = [
            models.UniqueConstraint(
                fields=['integration', 'hubspot_company_id'],
                name='hubspot_company_link_integration_companyid_uniq'
            ),
        ]

    def __str__(self):
        return f"Company {self.company_id} <-> hubspot:{self.hubspot_company_id}"
