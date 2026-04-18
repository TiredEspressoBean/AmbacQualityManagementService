"""
Integration app serializers.

IntegrationConfigSerializer: CRUD for integration management (admin).
HubSpotOrderLinkSerializer: Nested read-only on Order detail.
HubSpotCompanyLinkSerializer: Nested read-only on Company detail.
IntegrationSyncLogSerializer: Sync history display.
MilestoneTemplateSerializer / MilestoneSerializer: Milestone management.
"""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from integrations.models import (
    IntegrationConfig, IntegrationSyncLog,
    HubSpotOrderLink, HubSpotCompanyLink, HubSpotPipelineStage,
)
from integrations.services.registry import get_adapter, discover_capabilities


class IntegrationConfigSerializer(serializers.ModelSerializer):
    """
    Admin serializer for managing integrations.
    Credentials are write-only (never returned in responses).
    Capabilities and provider display name are computed from the adapter.
    """
    provider_display = serializers.CharField(source='get_provider_display', read_only=True)
    capabilities = serializers.SerializerMethodField()

    class Meta:
        model = IntegrationConfig
        fields = [
            'id', 'tenant', 'provider', 'provider_display', 'display_name',
            'is_enabled', 'sync_status',
            'api_key', 'oauth_refresh_token', 'webhook_secret', 'api_url',
            'config',
            'last_synced_at', 'last_sync_error', 'last_sync_stats',
            'capabilities',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'tenant', 'provider_display', 'sync_status',
            'last_synced_at', 'last_sync_error', 'last_sync_stats',
            'capabilities', 'created_at', 'updated_at',
        ]
        extra_kwargs = {
            'api_key': {'write_only': True},
            'oauth_refresh_token': {'write_only': True},
            'webhook_secret': {'write_only': True},
        }

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_capabilities(self, obj):
        try:
            adapter = get_adapter(obj.provider)
            return sorted(discover_capabilities(adapter))
        except (ValueError, ImportError):
            return []


class IntegrationConfigListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing integrations (no credentials)."""
    provider_display = serializers.CharField(source='get_provider_display', read_only=True)
    capabilities = serializers.SerializerMethodField()
    has_credentials = serializers.SerializerMethodField()

    class Meta:
        model = IntegrationConfig
        fields = [
            'id', 'provider', 'provider_display', 'display_name',
            'is_enabled', 'sync_status', 'has_credentials',
            'last_synced_at', 'last_sync_error', 'last_sync_stats',
            'capabilities',
        ]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_capabilities(self, obj):
        try:
            adapter = get_adapter(obj.provider)
            return sorted(discover_capabilities(adapter))
        except (ValueError, ImportError):
            return []

    @extend_schema_field(serializers.BooleanField())
    def get_has_credentials(self, obj):
        return bool(obj.api_key or obj.oauth_refresh_token)


class IntegrationSyncLogSerializer(serializers.ModelSerializer):
    """Sync log history."""
    sync_type_display = serializers.CharField(source='get_sync_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    duration_seconds = serializers.FloatField(source='duration', read_only=True)

    class Meta:
        model = IntegrationSyncLog
        fields = [
            'id', 'integration', 'sync_type', 'sync_type_display',
            'status', 'status_display',
            'started_at', 'completed_at', 'duration_seconds',
            'records_processed', 'records_created', 'records_updated',
            'error_message', 'details',
        ]
        read_only_fields = fields


class HubSpotPipelineStageSerializer(serializers.ModelSerializer):
    """Pipeline stages for a HubSpot integration."""
    customer_display_name = serializers.SerializerMethodField()

    class Meta:
        model = HubSpotPipelineStage
        fields = [
            'id', 'stage_name', 'api_id', 'pipeline_id',
            'display_order', 'include_in_progress',
            'customer_display_name', 'mapped_milestone',
            'last_synced_at',
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.CharField())
    def get_customer_display_name(self, obj):
        return obj.get_customer_display_name()


class HubSpotOrderLinkSerializer(serializers.ModelSerializer):
    """Nested read-only serializer for Order detail pages."""
    current_stage_name = serializers.CharField(
        source='current_stage.stage_name', read_only=True, allow_null=True
    )
    provider = serializers.CharField(source='integration.provider', read_only=True)

    class Meta:
        model = HubSpotOrderLink
        fields = [
            'deal_id', 'provider', 'current_stage', 'current_stage_name',
            'last_synced_at', 'last_sync_error',
        ]
        read_only_fields = fields


class HubSpotCompanyLinkSerializer(serializers.ModelSerializer):
    """Nested read-only serializer for Company detail pages."""
    provider = serializers.CharField(source='integration.provider', read_only=True)

    class Meta:
        model = HubSpotCompanyLink
        fields = ['hubspot_company_id', 'provider', 'created_at']
        read_only_fields = fields
