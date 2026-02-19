"""
HubSpot integration serializers.

Provides serializers for HubSpot-specific models like ExternalAPIOrderIdentifier
and HubSpotSyncLog.
"""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from Tracker.models.core import ExternalAPIOrderIdentifier
from Tracker.models.integrations.hubspot import HubSpotSyncLog
from ..core import SecureModelMixin


class ExternalAPIOrderIdentifierSerializer(serializers.ModelSerializer, SecureModelMixin):
    """
    Serializer for ExternalAPIOrderIdentifier (HubSpot pipeline stages).

    Provides customer-facing display names and full stage information.
    """

    customer_display_name = serializers.SerializerMethodField()

    class Meta:
        model = ExternalAPIOrderIdentifier
        fields = "__all__"

    @extend_schema_field(serializers.CharField())
    def get_customer_display_name(self, obj) -> str:
        """Get customer-facing display name (Gate prefix removed)"""
        return obj.get_customer_display_name()


class HubSpotSyncLogSerializer(serializers.ModelSerializer):
    """
    Serializer for HubSpot sync operation logs.

    Tracks sync attempts, timing, and results for debugging.
    """

    duration_seconds = serializers.SerializerMethodField()
    sync_type_display = serializers.CharField(source='get_sync_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = HubSpotSyncLog
        fields = [
            'id',
            'sync_type',
            'sync_type_display',
            'started_at',
            'completed_at',
            'status',
            'status_display',
            'deals_processed',
            'deals_created',
            'deals_updated',
            'error_message',
            'duration_seconds',
        ]
        read_only_fields = [
            'id',
            'started_at',
            'completed_at',
            'duration_seconds',
        ]

    def get_duration_seconds(self, obj):
        """Get sync duration in seconds"""
        return obj.duration
