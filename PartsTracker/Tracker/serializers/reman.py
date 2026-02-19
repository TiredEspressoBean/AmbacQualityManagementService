# serializers/reman.py - Remanufacturing Serializers
"""
Serializers for remanufacturing models:
- Core: Incoming used units
- HarvestedComponent: Disassembled components
- DisassemblyBOMLine: Expected disassembly yields
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from Tracker.models import (
    Core, HarvestedComponent, DisassemblyBOMLine,
    PartTypes, Companies, User, WorkOrder,
)
from .core import SecureModelMixin


# ===== CORE SERIALIZERS =====

class CoreSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Remanufacturing core serializer"""
    core_type_name = serializers.CharField(source='core_type.name', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True, allow_null=True)
    received_by_name = serializers.SerializerMethodField()
    disassembled_by_name = serializers.SerializerMethodField()
    harvested_component_count = serializers.IntegerField(read_only=True)
    usable_component_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Core
        fields = (
            'id', 'core_number', 'serial_number',
            'core_type', 'core_type_name',
            'received_date', 'received_by', 'received_by_name',
            'customer', 'customer_name', 'source_type', 'source_reference',
            'condition_grade', 'condition_notes',
            'status', 'disassembly_started_at', 'disassembly_completed_at',
            'disassembled_by', 'disassembled_by_name',
            'core_credit_value', 'core_credit_issued', 'core_credit_issued_at',
            'work_order',
            'harvested_component_count', 'usable_component_count',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = (
            'created_at', 'updated_at',             'received_by', 'disassembled_by',
            'disassembly_started_at', 'disassembly_completed_at',
            'core_credit_issued_at', 'harvested_component_count', 'usable_component_count'
        )

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_received_by_name(self, obj):
        return obj.received_by.get_full_name() if obj.received_by else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_disassembled_by_name(self, obj):
        return obj.disassembled_by.get_full_name() if obj.disassembled_by else None


class CoreListSerializer(serializers.ModelSerializer):
    """Lightweight core serializer for lists"""
    core_type_name = serializers.CharField(source='core_type.name', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True, allow_null=True)

    class Meta:
        model = Core
        fields = (
            'id', 'core_number', 'core_type', 'core_type_name',
            'customer_name', 'status', 'condition_grade', 'received_date'
        )


class CoreScrapSerializer(serializers.Serializer):
    """Serializer for scrapping a core"""
    reason = serializers.CharField(required=False, allow_blank=True, default="")


# ===== HARVESTED COMPONENT SERIALIZERS =====

class HarvestedComponentSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Harvested component serializer"""
    core_number = serializers.CharField(source='core.core_number', read_only=True)
    component_type_name = serializers.CharField(source='component_type.name', read_only=True)
    component_part_erp_id = serializers.CharField(source='component_part.ERP_id', read_only=True, allow_null=True)
    disassembled_by_name = serializers.SerializerMethodField()
    scrapped_by_name = serializers.SerializerMethodField()

    class Meta:
        model = HarvestedComponent
        fields = (
            'id', 'core', 'core_number',
            'component_type', 'component_type_name',
            'component_part', 'component_part_erp_id',
            'disassembled_at', 'disassembled_by', 'disassembled_by_name',
            'condition_grade', 'condition_notes',
            'is_scrapped', 'scrap_reason', 'scrapped_at', 'scrapped_by', 'scrapped_by_name',
            'position', 'original_part_number',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = (
            'created_at', 'updated_at',             'disassembled_at', 'disassembled_by', 'scrapped_at', 'scrapped_by',
            'is_scrapped', 'scrap_reason', 'component_part'
        )

    @extend_schema_field(serializers.CharField())
    def get_disassembled_by_name(self, obj):
        return obj.disassembled_by.get_full_name() if obj.disassembled_by else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_scrapped_by_name(self, obj):
        return obj.scrapped_by.get_full_name() if obj.scrapped_by else None


class HarvestedComponentScrapSerializer(serializers.Serializer):
    """Serializer for scrapping a harvested component"""
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class HarvestedComponentAcceptSerializer(serializers.Serializer):
    """Serializer for accepting a component to inventory"""
    erp_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)


# ===== DISASSEMBLY BOM LINE SERIALIZERS =====

class DisassemblyBOMLineSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Disassembly BOM line serializer"""
    core_type_name = serializers.CharField(source='core_type.name', read_only=True)
    component_type_name = serializers.CharField(source='component_type.name', read_only=True)
    expected_usable_qty = serializers.FloatField(read_only=True)

    class Meta:
        model = DisassemblyBOMLine
        fields = (
            'id', 'core_type', 'core_type_name',
            'component_type', 'component_type_name',
            'expected_qty', 'expected_fallout_rate', 'expected_usable_qty',
            'notes', 'line_number',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = ('created_at', 'updated_at', 'expected_usable_qty')
