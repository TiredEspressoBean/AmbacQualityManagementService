# serializers/life_tracking.py - Life Tracking Serializers
"""
Serializers for life tracking models:
- LifeLimitDefinition: Tenant-defined tracking rules
- PartTypeLifeLimit: Links definitions to part types
- LifeTracking: Actual tracking records for entities
"""
from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType

from Tracker.models import (
    LifeLimitDefinition, PartTypeLifeLimit, LifeTracking,
)
from .core import SecureModelMixin


class LifeLimitDefinitionSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Life limit definition serializer"""

    class Meta:
        model = LifeLimitDefinition
        fields = (
            'id', 'name', 'unit', 'unit_label',
            'is_calendar_based', 'soft_limit', 'hard_limit',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = ('created_at', 'updated_at')


class LifeLimitDefinitionSelectSerializer(serializers.ModelSerializer):
    """Lightweight serializer for dropdowns"""

    class Meta:
        model = LifeLimitDefinition
        fields = ('id', 'name', 'unit_label', 'is_calendar_based')


class PartTypeLifeLimitSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Part type life limit junction serializer"""
    part_type_name = serializers.CharField(source='part_type.name', read_only=True)
    definition_name = serializers.CharField(source='definition.name', read_only=True)
    definition_unit = serializers.CharField(source='definition.unit_label', read_only=True)

    class Meta:
        model = PartTypeLifeLimit
        fields = (
            'id', 'part_type', 'part_type_name',
            'definition', 'definition_name', 'definition_unit',
            'is_required',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = ('created_at', 'updated_at')


class LifeTrackingSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Life tracking record serializer"""
    definition_name = serializers.CharField(source='definition.name', read_only=True)
    definition_unit = serializers.CharField(source='definition.unit_label', read_only=True)
    content_type_model = serializers.SerializerMethodField()
    current_value = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    remaining = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    remaining_to_soft_limit = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    percent_used = serializers.FloatField(read_only=True)
    status = serializers.CharField(read_only=True)
    is_blocked = serializers.BooleanField(read_only=True)
    effective_hard_limit = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    effective_soft_limit = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = LifeTracking
        fields = (
            'id', 'content_type', 'content_type_model', 'object_id',
            'definition', 'definition_name', 'definition_unit',
            'accumulated', 'reference_date', 'source',
            'current_value', 'remaining', 'remaining_to_soft_limit',
            'percent_used', 'status', 'is_blocked',
            'effective_hard_limit', 'effective_soft_limit',
            'hard_limit_override', 'soft_limit_override',
            'override_reason', 'override_approved_by',
            'reset_history', 'cached_status',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = (
            'created_at', 'updated_at', 'cached_status',
            'current_value', 'remaining', 'remaining_to_soft_limit',
            'percent_used', 'status', 'is_blocked',
            'effective_hard_limit', 'effective_soft_limit',
        )

    def get_content_type_model(self, obj):
        return f"{obj.content_type.app_label}.{obj.content_type.model}"


class LifeTrackingListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for lists"""
    definition_name = serializers.CharField(source='definition.name', read_only=True)
    definition_unit = serializers.CharField(source='definition.unit_label', read_only=True)
    current_value = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    status = serializers.CharField(read_only=True)
    percent_used = serializers.FloatField(read_only=True)

    class Meta:
        model = LifeTracking
        fields = (
            'id', 'object_id', 'definition', 'definition_name', 'definition_unit',
            'accumulated', 'current_value', 'status', 'percent_used', 'cached_status'
        )


class LifeTrackingIncrementSerializer(serializers.Serializer):
    """Serializer for incrementing life tracking"""
    value = serializers.DecimalField(max_digits=12, decimal_places=2)


class LifeTrackingResetSerializer(serializers.Serializer):
    """Serializer for resetting life tracking (after overhaul)"""
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class LifeTrackingOverrideSerializer(serializers.Serializer):
    """Serializer for applying per-instance limit overrides"""
    hard_limit = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    soft_limit = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    reason = serializers.CharField(required=True)
