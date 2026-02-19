# serializers/mes_standard.py - MES Standard Tier Serializers
"""
Serializers for MES Standard tier models:
- Scheduling: WorkCenter, Shift, ScheduleSlot
- Downtime: DowntimeEvent
- Traceability: MaterialLot, MaterialUsage, BOM, BOMLine, AssemblyUsage
- Labor: TimeEntry
"""
from decimal import Decimal

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from Tracker.models import (
    WorkCenter, Shift, ScheduleSlot, DowntimeEvent,
    MaterialLot, MaterialUsage, TimeEntry,
    BOM, BOMLine, AssemblyUsage,
    Equipments, PartTypes, Parts, WorkOrder, Steps, User, Companies,
)
from .core import SecureModelMixin, UserSelectSerializer


# ===== WORK CENTER SERIALIZERS =====

class WorkCenterSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Work center serializer with equipment list"""
    equipment_names = serializers.SerializerMethodField()

    class Meta:
        model = WorkCenter
        fields = (
            'id', 'name', 'code', 'description', 'capacity_units',
            'default_efficiency', 'equipment', 'equipment_names', 'cost_center',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = ('created_at', 'updated_at', 'equipment_names')

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_equipment_names(self, obj):
        return [eq.name for eq in obj.equipment.all()]


class WorkCenterSelectSerializer(serializers.ModelSerializer):
    """Lightweight serializer for dropdowns"""
    class Meta:
        model = WorkCenter
        fields = ('id', 'code', 'name')


# ===== SHIFT SERIALIZERS =====

class ShiftSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Shift definition serializer"""
    class Meta:
        model = Shift
        fields = (
            'id', 'name', 'code', 'start_time', 'end_time',
            'days_of_week', 'is_active',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = ('created_at', 'updated_at')


# ===== SCHEDULE SLOT SERIALIZERS =====

class ScheduleSlotSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Production schedule slot serializer"""
    work_center_name = serializers.CharField(source='work_center.name', read_only=True)
    shift_name = serializers.CharField(source='shift.name', read_only=True)
    work_order_erp_id = serializers.CharField(source='work_order.ERP_id', read_only=True)

    class Meta:
        model = ScheduleSlot
        fields = (
            'id', 'work_center', 'work_center_name', 'shift', 'shift_name',
            'work_order', 'work_order_erp_id', 'scheduled_date',
            'scheduled_start', 'scheduled_end', 'actual_start', 'actual_end',
            'status', 'notes',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = ('created_at', 'updated_at')


# ===== DOWNTIME EVENT SERIALIZERS =====

class DowntimeEventSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Equipment/work center downtime serializer"""
    equipment_name = serializers.CharField(source='equipment.name', read_only=True, allow_null=True)
    work_center_name = serializers.CharField(source='work_center.name', read_only=True, allow_null=True)
    reported_by_name = serializers.SerializerMethodField()
    resolved_by_name = serializers.SerializerMethodField()
    duration_minutes = serializers.SerializerMethodField()

    class Meta:
        model = DowntimeEvent
        fields = (
            'id', 'equipment', 'equipment_name', 'work_center', 'work_center_name',
            'category', 'reason', 'description',
            'start_time', 'end_time', 'duration_minutes',
            'work_order', 'reported_by', 'reported_by_name',
            'resolved_by', 'resolved_by_name',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = ('created_at', 'updated_at', 'duration_minutes', 'reported_by', 'resolved_by')

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_reported_by_name(self, obj):
        return obj.reported_by.get_full_name() if obj.reported_by else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_resolved_by_name(self, obj):
        return obj.resolved_by.get_full_name() if obj.resolved_by else None

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_duration_minutes(self, obj):
        if obj.duration:
            return obj.duration.total_seconds() / 60
        return None


# ===== MATERIAL LOT SERIALIZERS =====

class MaterialLotSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Material lot serializer with full details"""
    material_type_name = serializers.CharField(source='material_type.name', read_only=True, allow_null=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True, allow_null=True)
    parent_lot_number = serializers.CharField(source='parent_lot.lot_number', read_only=True, allow_null=True)
    child_lot_count = serializers.SerializerMethodField()

    class Meta:
        model = MaterialLot
        fields = (
            'id', 'lot_number', 'parent_lot', 'parent_lot_number',
            'material_type', 'material_type_name', 'material_description',
            'supplier', 'supplier_name', 'supplier_lot_number',
            'received_date', 'received_by',
            'quantity', 'quantity_remaining', 'unit_of_measure',
            'status', 'manufacture_date', 'expiration_date',
            'certificate_of_conformance', 'storage_location',
            'child_lot_count',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = (
            'created_at', 'updated_at', 'quantity_remaining',
            'parent_lot_number', 'child_lot_count', 'received_by'
        )

    @extend_schema_field(serializers.IntegerField())
    def get_child_lot_count(self, obj):
        return obj.child_lots.count()


class MaterialLotSplitSerializer(serializers.Serializer):
    """Serializer for splitting a lot"""
    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=4,
        min_value=Decimal('0.0001'),
        help_text="Quantity to split off (must be positive)"
    )
    reason = serializers.CharField(required=False, allow_blank=True, default="")


# ===== MATERIAL USAGE SERIALIZERS =====

class MaterialUsageSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Material consumption record serializer"""
    lot_number = serializers.CharField(source='lot.lot_number', read_only=True, allow_null=True)
    part_erp_id = serializers.CharField(source='part.ERP_id', read_only=True)
    consumed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = MaterialUsage
        fields = (
            'id', 'lot', 'lot_number', 'harvested_component',
            'part', 'part_erp_id', 'work_order', 'step',
            'qty_consumed', 'consumed_at', 'consumed_by', 'consumed_by_name',
            'is_substitute', 'substitution_reason',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = ('created_at', 'updated_at', 'consumed_at')

    @extend_schema_field(serializers.CharField())
    def get_consumed_by_name(self, obj):
        return obj.consumed_by.get_full_name() if obj.consumed_by else None


# ===== TIME ENTRY SERIALIZERS =====

class TimeEntrySerializer(serializers.ModelSerializer, SecureModelMixin):
    """Labor time entry serializer"""
    user_name = serializers.SerializerMethodField()
    duration_hours = serializers.SerializerMethodField()
    work_order_erp_id = serializers.CharField(source='work_order.ERP_id', read_only=True, allow_null=True)
    part_erp_id = serializers.CharField(source='part.ERP_id', read_only=True, allow_null=True)

    class Meta:
        model = TimeEntry
        fields = (
            'id', 'entry_type', 'start_time', 'end_time',
            'user', 'user_name', 'duration_hours',
            'part', 'part_erp_id', 'work_order', 'work_order_erp_id',
            'step', 'equipment', 'work_center',
            'notes', 'downtime_reason',
            'approved', 'approved_by', 'approved_at',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = ('created_at', 'updated_at', 'duration_hours', 'user', 'approved_by', 'approved_at')

    @extend_schema_field(serializers.CharField())
    def get_user_name(self, obj):
        return obj.user.get_full_name() if obj.user else None

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_duration_hours(self, obj):
        return obj.duration_hours


class ClockInSerializer(serializers.Serializer):
    """Serializer for clocking in"""
    entry_type = serializers.ChoiceField(choices=TimeEntry.ENTRY_TYPE_CHOICES)
    work_order = serializers.PrimaryKeyRelatedField(queryset=WorkOrder.objects.all(), required=False, allow_null=True)
    part = serializers.PrimaryKeyRelatedField(queryset=Parts.objects.all(), required=False, allow_null=True)
    step = serializers.PrimaryKeyRelatedField(queryset=Steps.objects.all(), required=False, allow_null=True)
    equipment = serializers.PrimaryKeyRelatedField(queryset=Equipments.objects.all(), required=False, allow_null=True)
    work_center = serializers.PrimaryKeyRelatedField(queryset=WorkCenter.objects.all(), required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


# ===== BOM SERIALIZERS =====

class BOMLineSerializer(serializers.ModelSerializer, SecureModelMixin):
    """BOM line item serializer"""
    component_type_name = serializers.CharField(source='component_type.name', read_only=True)

    class Meta:
        model = BOMLine
        fields = (
            'id', 'bom', 'component_type', 'component_type_name',
            'quantity', 'unit_of_measure', 'find_number', 'reference_designator',
            'is_optional', 'allow_harvested', 'notes', 'line_number',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = ('created_at', 'updated_at')


class BOMSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Bill of Materials serializer"""
    part_type_name = serializers.CharField(source='part_type.name', read_only=True)
    lines = BOMLineSerializer(many=True, read_only=True)
    line_count = serializers.SerializerMethodField()

    class Meta:
        model = BOM
        fields = (
            'id', 'part_type', 'part_type_name', 'revision', 'bom_type',
            'status', 'description', 'effective_date', 'obsolete_date',
            'approved_by', 'approved_at',
            'lines', 'line_count',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = ('created_at', 'updated_at', 'approved_by', 'approved_at', 'effective_date', 'obsolete_date')

    @extend_schema_field(serializers.IntegerField())
    def get_line_count(self, obj):
        return obj.lines.count()


class BOMListSerializer(serializers.ModelSerializer):
    """Lightweight BOM serializer for lists"""
    part_type_name = serializers.CharField(source='part_type.name', read_only=True)
    line_count = serializers.SerializerMethodField()

    class Meta:
        model = BOM
        fields = ('id', 'part_type', 'part_type_name', 'revision', 'bom_type', 'status', 'line_count')

    @extend_schema_field(serializers.IntegerField())
    def get_line_count(self, obj):
        return obj.lines.count()


# ===== ASSEMBLY USAGE SERIALIZERS =====

class AssemblyUsageSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Assembly component usage serializer"""
    assembly_erp_id = serializers.CharField(source='assembly.ERP_id', read_only=True)
    component_erp_id = serializers.CharField(source='component.ERP_id', read_only=True)
    installed_by_name = serializers.SerializerMethodField()
    is_installed = serializers.BooleanField(read_only=True)

    class Meta:
        model = AssemblyUsage
        fields = (
            'id', 'assembly', 'assembly_erp_id', 'component', 'component_erp_id',
            'quantity', 'bom_line',
            'installed_at', 'installed_by', 'installed_by_name', 'step',
            'removed_at', 'removed_by', 'removal_reason',
            'is_installed',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = (
            'created_at', 'updated_at', 'installed_at', 'installed_by',
            'removed_at', 'removed_by', 'removal_reason', 'is_installed'
        )

    @extend_schema_field(serializers.CharField())
    def get_installed_by_name(self, obj):
        return obj.installed_by.get_full_name() if obj.installed_by else None


class AssemblyRemoveSerializer(serializers.Serializer):
    """Serializer for removing a component from assembly"""
    reason = serializers.CharField(required=False, allow_blank=True, default="")
