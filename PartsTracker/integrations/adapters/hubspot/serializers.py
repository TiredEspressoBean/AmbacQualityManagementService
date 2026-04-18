"""
HubSpot adapter serializers.

HubSpotConfigSerializer: Validates provider-specific config fields.
    drf-spectacular generates the OpenAPI schema for the frontend settings form.

HubSpotDealInboundSerializer: Transforms HubSpot deal data into Orders.
    Handles field mapping, validation, and create/update with link records.
"""

import logging
import secrets

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from Tracker.models import Orders, Companies, User

logger = logging.getLogger(__name__)


class HubSpotConfigSerializer(serializers.Serializer):
    """Validates and describes the provider-specific config for HubSpot."""

    pipeline_id = serializers.CharField(
        required=False, allow_blank=True, default='',
        help_text="HubSpot pipeline ID to sync"
    )
    pipeline_tracking_enabled = serializers.BooleanField(
        default=False,
        help_text="Show pipeline progress UI (gate progress bars, stage dropdown)"
    )
    active_stage_prefix = serializers.CharField(
        required=False, default='', allow_blank=True,
        help_text="Stage name prefix for active pipeline filter (e.g. 'Gate')"
    )
    debug_mode = serializers.BooleanField(
        default=False,
        help_text="Only sync a single test deal"
    )
    debug_deal_name = serializers.CharField(
        required=False, default='Ghost Pepper',
        help_text="Deal name to sync in debug mode"
    )


class HubSpotDealInboundSerializer(serializers.Serializer):
    """
    Transforms a HubSpot deal dict into Order fields.

    Does NOT inherit from ModelSerializer — the deal data shape is HubSpot-specific
    and we handle create/update logic explicitly with transaction.atomic().

    Expected context:
        integration: IntegrationConfig instance
        deal_id: str — HubSpot deal ID
        current_stage: HubSpotPipelineStage instance or None
        company: Companies instance or None
        customer: User instance or None
    """

    # These map to deal.properties from the SDK.
    # HubSpot can send None, empty string, or missing for any property.
    dealname = serializers.CharField(required=False, allow_null=True, allow_blank=True, default='')
    closedate = serializers.CharField(required=False, allow_null=True, allow_blank=True, default=None)
    archived = serializers.BooleanField(required=False, allow_null=True, default=False)

    def validate_archived(self, value):
        """Treat None as False."""
        return bool(value)

    def validate_dealname(self, value):
        """Handle None/empty dealname and truncate to Orders.name max_length."""
        if not value:
            return ''
        # Truncate to Orders.name max_length (200)
        return value[:200]

    def _parse_closedate(self, value):
        """Parse HubSpot closedate (ISO datetime or date string) to date-only string."""
        if not value:
            return None
        # HubSpot sends ISO datetime like '2025-07-08T14:31:24.315Z'
        # Django DateField expects 'YYYY-MM-DD'
        from dateutil.parser import parse as dateparse
        try:
            return dateparse(value).date()
        except (ValueError, TypeError):
            return None

    def create(self, validated_data):
        """Create Order + HubSpotOrderLink atomically."""
        from integrations.models.links.hubspot import HubSpotOrderLink

        integration = self.context['integration']
        tenant = integration.tenant
        deal_id = self.context['deal_id']
        current_stage = self.context.get('current_stage')
        company = self.context.get('company')
        customer = self.context.get('customer')

        name = validated_data.get('dealname') or f'Deal {deal_id}'
        estimated_completion = self._parse_closedate(validated_data.get('closedate'))

        # Resolve native milestone from the HubSpot stage mapping
        mapped_milestone = current_stage.mapped_milestone if current_stage else None

        with transaction.atomic():
            order = Orders.objects.create(
                tenant=tenant,
                name=name,
                estimated_completion=estimated_completion,
                company=company,
                customer=customer,
                current_milestone=mapped_milestone,
                archived=validated_data.get('archived', False),
            )

            link = HubSpotOrderLink(
                order=order,
                integration=integration,
                deal_id=deal_id,
                current_stage=current_stage,
                last_synced_stage_name=current_stage.stage_name if current_stage else None,
                last_synced_at=timezone.now(),
            )
            link._skip_external_push = True
            link.save()

        return order

    def update(self, instance, validated_data):
        """Update existing Order + HubSpotOrderLink atomically."""
        integration = self.context['integration']
        current_stage = self.context.get('current_stage')
        company = self.context.get('company')
        customer = self.context.get('customer')

        name = validated_data.get('dealname') or instance.name
        estimated_completion = self._parse_closedate(validated_data.get('closedate')) or instance.estimated_completion

        # Resolve native milestone from the HubSpot stage mapping
        mapped_milestone = current_stage.mapped_milestone if current_stage else None

        with transaction.atomic():
            instance.name = name
            instance.estimated_completion = estimated_completion
            instance.archived = validated_data.get('archived', instance.archived)
            if company is not None:
                instance.company = company
            if customer is not None:
                instance.customer = customer
            instance.current_milestone = mapped_milestone
            instance.save()

            link = instance.hubspot_link
            link.current_stage = current_stage
            link.last_synced_stage_name = current_stage.stage_name if current_stage else None
            link.last_synced_at = timezone.now()
            link._skip_external_push = True
            link.save()

        return instance


def resolve_company(company_id, company_dict, integration, tenant):
    """
    Resolve a HubSpot company ID to a local Companies instance.
    Creates the company if it doesn't exist.
    Optionally creates a HubSpotCompanyLink.
    """
    from integrations.models.links.hubspot import HubSpotCompanyLink

    company_info = company_dict.get(str(company_id))
    if not company_info:
        return None

    company_name = company_info.get('name') or f"Company {company_id}"
    company, _ = Companies.objects.get_or_create(
        tenant=tenant,
        name=company_name,
        defaults={'description': company_info.get('description', '')}
    )

    # Create/update link
    HubSpotCompanyLink.objects.update_or_create(
        integration=integration,
        hubspot_company_id=str(company_id),
        defaults={'company': company}
    )

    return company


def resolve_contact(contact_info, company_dict, integration, tenant):
    """
    Resolve a HubSpot contact to a local User instance.
    Creates the user if they don't exist, assigns to Customer group.
    """
    if not contact_info or not contact_info.get('email'):
        return None

    # Resolve the contact's associated company
    contact_company = None
    if contact_info.get('associated_company_id'):
        contact_company = resolve_company(
            contact_info['associated_company_id'],
            company_dict, integration, tenant
        )

    customer, created = User.objects.get_or_create(
        email=contact_info['email'],
        defaults={
            'first_name': contact_info.get('first_name', ''),
            'last_name': contact_info.get('last_name', ''),
            'username': contact_info['email'],
            'parent_company': contact_company,
            'tenant': tenant,
            'user_type': User.UserType.PORTAL,
            'is_active': True,
        }
    )

    if created:
        placeholder_password = f"HUBSPOT_PLACEHOLDER_{secrets.token_urlsafe(48)}"
        customer.set_password(placeholder_password)
        customer.save()
        logger.info(
            "Created user from HubSpot contact: %s company: %s",
            customer.email,
            contact_company.name if contact_company else 'None',
        )
    else:
        # User already exists — update name/company only if they belong to this tenant
        if customer.tenant == tenant:
            customer.first_name = contact_info.get('first_name', '') or customer.first_name
            customer.last_name = contact_info.get('last_name', '') or customer.last_name
            if contact_company is not None:
                customer.parent_company = contact_company
            customer.save(update_fields=['first_name', 'last_name', 'parent_company'])

    # Ensure user has a Customer role in this tenant (supports multi-tenant users)
    from Tracker.models import TenantGroup, UserRole
    customer_group, _ = TenantGroup.objects.get_or_create(
        tenant=tenant,
        name='Customer',
        defaults={'description': 'Customer portal users', 'is_custom': False},
    )
    UserRole.objects.get_or_create(
        user=customer,
        group=customer_group,
    )

    return customer
