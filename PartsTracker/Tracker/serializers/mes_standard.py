# serializers/mes_standard.py - MES Standard Tier Serializers
"""
Serializers for MES Standard tier models:
- Scheduling: WorkCenter, Shift, ScheduleSlot
- Downtime: DowntimeEvent
- Traceability: MaterialLot, MaterialUsage, BOM, BOMLine, AssemblyUsage
- Labor: TimeEntry
"""
import re
from decimal import Decimal

from rest_framework import serializers
from Tracker.serializers.fields import TenantScopedPrimaryKeyRelatedField
from drf_spectacular.utils import extend_schema_field

from Tracker.models import (
    WorkCenter, Shift, ScheduleSlot, DowntimeEvent,
    Material, MaterialLot, MaterialUsage, TimeEntry,
    BOM, BOMLine, AssemblyUsage,
    Equipments, PartTypes, Parts, WorkOrder, Steps, User, Companies,
)
from .core import SecureModelMixin, UserSelectSerializer


# ===== WORK CENTER SERIALIZERS =====

class WorkCenterSerializer(SecureModelMixin):
    """Work center serializer with equipment list.

    WorkCenter is a versioned configuration record. Content edits
    (name, code, description, capacity, cost center) route through
    `create_new_version`. Archiving goes through a plain save.
    """
    equipment_names = serializers.SerializerMethodField()
    step_count = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = WorkCenter
        fields = (
            'id', 'name', 'code', 'description', 'kind', 'capacity_units',
            'default_efficiency', 'equipment', 'equipment_names', 'cost_center',
            'step_count', 'member_count',
            'created_at', 'updated_at', 'archived', 'version',
        )
        read_only_fields = ('created_at', 'updated_at', 'equipment_names',
                            'step_count', 'member_count', 'version')

    # `equipment` is station *placement* (operational master data, like
    # Steps.work_center) — editing what's at a station shouldn't fork a new
    # configuration version. Identity/config fields (name, code, kind,
    # capacity, cost center) still version.
    _NON_VERSIONING_FIELDS = frozenset({'archived', 'equipment'})

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_equipment_names(self, obj):
        return [eq.name for eq in obj.equipment.all()]

    @extend_schema_field(serializers.IntegerField())
    def get_step_count(self, obj):
        # Current routing steps stationed here. tenant-safe: reverse FK from an
        # in-tenant WorkCenter row.
        return obj.steps.filter(is_current_version=True).count()

    @extend_schema_field(serializers.IntegerField())
    def get_member_count(self, obj):
        # tenant-safe: reverse FK from an in-tenant WorkCenter row.
        return obj.member_memberships.count()

    def update(self, instance, validated_data):
        """Route content edits through `create_new_version`; let
        archive toggles through as a plain save."""
        from Tracker.services.core.versioning import apply_versioned_update
        return apply_versioned_update(
            instance, validated_data,
            non_versioning_fields=self._NON_VERSIONING_FIELDS,
            default_update=super().update,
        )


class WorkCenterSelectSerializer(serializers.ModelSerializer):
    """Lightweight serializer for dropdowns"""
    class Meta:
        model = WorkCenter
        fields = ('id', 'code', 'name')


class UserWorkCenterMembershipSerializer(SecureModelMixin):
    """Which stations a user is eligible at (ISA-95 PersonnelClass-style).
    See Documents/WORK_CENTER_DESIGN.md."""
    work_center_name = serializers.CharField(source='work_center.name', read_only=True, allow_null=True)
    work_center_code = serializers.CharField(source='work_center.code', read_only=True, allow_null=True)
    work_center_kind = serializers.CharField(source='work_center.kind', read_only=True, allow_null=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        from Tracker.models import UserWorkCenterMembership as _UWCM
        model = _UWCM
        fields = (
            'id', 'user', 'user_name',
            'work_center', 'work_center_name', 'work_center_code', 'work_center_kind',
            'is_primary', 'created_at',
        )
        read_only_fields = (
            'id', 'user_name', 'work_center_name', 'work_center_code',
            'work_center_kind', 'created_at',
        )

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.email if obj.user_id else None


# ===== SHIFT SERIALIZERS =====

class ShiftSerializer(SecureModelMixin):
    """Shift definition serializer.

    Shift is a versioned configuration record. Content edits (name,
    code, start/end time, days of week) route through
    `create_new_version`. Archiving and active-flag toggles go through
    a plain save.
    """

    class Meta:
        model = Shift
        fields = (
            'id', 'name', 'code', 'start_time', 'end_time',
            'days_of_week', 'break_windows', 'is_active',
            'created_at', 'updated_at', 'archived', 'version',
        )
        read_only_fields = ('created_at', 'updated_at', 'version')

    # is_active is a scheduling on/off toggle, not a structural content change.
    _NON_VERSIONING_FIELDS = frozenset({'archived', 'is_active'})

    _HHMM = re.compile(r'^([01]\d|2[0-3]):[0-5]\d$')

    def validate_break_windows(self, value):
        """Shape-check the JSONField: the solver iterates it as a list of
        {'start': 'HH:MM', 'end': 'HH:MM'} dicts (`data.py::get_break_windows`);
        anything else accepted here would 500 every subsequent solve. Strict on
        extra keys — the only writer is our own shifts editor."""
        if value in (None, []):
            return value or []
        if not isinstance(value, list):
            raise serializers.ValidationError(
                'break_windows must be a list of {"start": "HH:MM", "end": "HH:MM"} objects.')
        for i, br in enumerate(value):
            if not isinstance(br, dict) or set(br.keys()) != {'start', 'end'}:
                raise serializers.ValidationError(
                    f'break_windows[{i}] must be an object with exactly "start" and "end".')
            for key in ('start', 'end'):
                if not isinstance(br[key], str) or not self._HHMM.match(br[key]):
                    raise serializers.ValidationError(
                        f'break_windows[{i}].{key} must be a 24-hour "HH:MM" string.')
            if br['start'] >= br['end']:
                raise serializers.ValidationError(
                    f'break_windows[{i}]: start must be before end.')
        return value

    def update(self, instance, validated_data):
        """Route content edits through `create_new_version`; let
        archive and active-flag changes through as a plain save."""
        from Tracker.services.core.versioning import apply_versioned_update
        return apply_versioned_update(
            instance, validated_data,
            non_versioning_fields=self._NON_VERSIONING_FIELDS,
            default_update=super().update,
        )


# ===== SCHEDULE SLOT SERIALIZERS =====

class ScheduleSlotSerializer(SecureModelMixin):
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

class DowntimeEventSerializer(SecureModelMixin):
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
        return obj.reported_by.display_name if obj.reported_by else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_resolved_by_name(self, obj):
        return obj.resolved_by.display_name if obj.resolved_by else None

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_duration_minutes(self, obj):
        if obj.duration:
            return obj.duration.total_seconds() / 60
        return None


# ===== MATERIAL LOT SERIALIZERS =====

class MaterialSerializer(SecureModelMixin):
    """Purchased item — raw material / bought component (distinct from in-house PartTypes).
    Holds the purchase lead time used by the sourcing report."""
    preferred_supplier_name = serializers.CharField(
        source='preferred_supplier.name', read_only=True, allow_null=True)

    class Meta:
        model = Material
        fields = (
            'id', 'name', 'part_number', 'description', 'unit_of_measure',
            'purchase_lead_time_days', 'preferred_supplier', 'preferred_supplier_name',
            'is_active', 'created_at', 'updated_at', 'archived',
        )
        read_only_fields = ('created_at', 'updated_at')


class MaterialLotSerializer(SecureModelMixin):
    """Material lot serializer.

    MaterialLot is physical inventory, not a controlled document (de-versioned —
    see Documents/SCHEDULING_IMPLEMENTATION_PLAN.md #1), so edits are plain
    in-place updates; auditlog records field changes and the CoC is a separately
    controlled Document. ``quantity_remaining`` stays read-only (written only by
    the consumption/split services).
    """
    # A lot is stock of a buyable part (material_type → PartTypes) XOR a raw
    # material (material → Material). item_name is the subject-agnostic label.
    material_type_name = serializers.CharField(source='material_type.name', read_only=True, allow_null=True)
    material_name = serializers.CharField(source='material.name', read_only=True, allow_null=True)
    item_name = serializers.CharField(read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True, allow_null=True)
    parent_lot_number = serializers.CharField(source='parent_lot.lot_number', read_only=True, allow_null=True)
    child_lot_count = serializers.SerializerMethodField()
    # Live calendar shelf-life status (OK/WARNING/EXPIRED), or null when the lot
    # has no shelf life. Reads the LifeTracking record, not the raw scalar.
    shelf_life_status = serializers.SerializerMethodField()

    class Meta:
        model = MaterialLot
        fields = (
            'id', 'lot_number', 'parent_lot', 'parent_lot_number',
            'material_type', 'material_type_name',
            'material', 'material_name', 'item_name', 'material_description',
            'supplier', 'supplier_name', 'supplier_lot_number',
            'erp_po_number', 'promised_date',
            'received_date', 'received_by',
            'quantity', 'quantity_remaining', 'unit_of_measure',
            'status', 'hold_reason', 'manufacture_date', 'expiration_date',
            'shelf_life_status',
            'certificate_of_conformance', 'storage_location',
            'child_lot_count',
            'created_at', 'updated_at', 'archived',
        )
        read_only_fields = (
            'created_at', 'updated_at', 'quantity_remaining',
            'parent_lot_number', 'child_lot_count', 'received_by',
            'hold_reason',
        )

    @extend_schema_field(serializers.IntegerField())
    def get_child_lot_count(self, obj):
        return obj.child_lots.count()

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_shelf_life_status(self, obj):
        from Tracker.services.life_tracking.shelf_life import shelf_life_status
        return shelf_life_status(obj)


class MaterialLotSplitSerializer(serializers.Serializer):
    """Serializer for splitting a lot"""
    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=4,
        min_value=Decimal('0.0001'),
        help_text="Quantity to split off (must be positive)"
    )
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class ExtendShelfLifeSerializer(serializers.Serializer):
    """Governed shelf-life extension: a re-tested lot gets a new use-by date,
    with a required reason (and the approver taken from the request user)."""
    new_expiration_date = serializers.DateField(
        help_text="New use-by date after re-test/re-certification."
    )
    reason = serializers.CharField(
        allow_blank=False,
        help_text="Justification / evidence reference for the extension (required)."
    )


# ===== MATERIAL USAGE SERIALIZERS =====

class MaterialUsageSerializer(SecureModelMixin):
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
        return obj.consumed_by.display_name if obj.consumed_by else None


# ===== TIME ENTRY SERIALIZERS =====

class TimeEntrySerializer(SecureModelMixin):
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
        return obj.user.display_name if obj.user else None

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_duration_hours(self, obj):
        return obj.duration_hours


class ClockInSerializer(serializers.Serializer):
    """Serializer for clocking in"""
    entry_type = serializers.ChoiceField(choices=TimeEntry.ENTRY_TYPE_CHOICES)
    work_order = TenantScopedPrimaryKeyRelatedField(queryset=WorkOrder.unscoped.all(), required=False, allow_null=True)
    part = TenantScopedPrimaryKeyRelatedField(queryset=Parts.unscoped.all(), required=False, allow_null=True)
    step = TenantScopedPrimaryKeyRelatedField(queryset=Steps.unscoped.all(), required=False, allow_null=True)
    equipment = TenantScopedPrimaryKeyRelatedField(queryset=Equipments.unscoped.all(), required=False, allow_null=True)
    work_center = TenantScopedPrimaryKeyRelatedField(queryset=WorkCenter.unscoped.all(), required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


# ===== BOM SERIALIZERS =====

class BOMLineSerializer(SecureModelMixin):
    """BOM line item serializer. A line's component is EITHER an in-house `component_type`
    (source=MAKE) OR a purchased `material` (source=BUY) — exactly one."""
    component_type_name = serializers.CharField(
        source='component_type.name', read_only=True, allow_null=True)
    material_name = serializers.CharField(
        source='material.name', read_only=True, allow_null=True)
    consumed_at_step_name = serializers.CharField(
        source='consumed_at_step.name', read_only=True, allow_null=True)

    class Meta:
        model = BOMLine
        fields = (
            'id', 'bom', 'component_type', 'component_type_name',
            'material', 'material_name', 'source',
            'consumed_at_step', 'consumed_at_step_name',
            'quantity', 'unit_of_measure', 'find_number', 'reference_designator',
            'is_optional', 'allow_harvested', 'notes', 'line_number',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = ('created_at', 'updated_at')

    def validate(self, attrs):
        def pick(name):
            return attrs.get(name, getattr(self.instance, name, None))
        has_ct = pick('component_type') is not None
        has_mat = pick('material') is not None
        if has_ct == has_mat:
            raise serializers.ValidationError(
                "Set exactly one of component_type (in-house/MAKE) or material (purchased/BUY).")
        return attrs


class BOMSerializer(SecureModelMixin):
    """Bill of Materials serializer.

    PATCH semantics: DRAFT BOMs are edited in place via super().update().
    RELEASED and OBSOLETE BOMs are immutable via PATCH — callers must POST
    to /api/boms/{id}/revisions/ to start a new DRAFT.
    """
    part_type_name = serializers.CharField(source='part_type.name', read_only=True, allow_null=True)
    lines = BOMLineSerializer(many=True, read_only=True)
    line_count = serializers.SerializerMethodField()

    class Meta:
        model = BOM
        fields = (
            'id', 'part_type', 'part_type_name', 'revision', 'bom_type',
            'status', 'description', 'effective_date', 'obsolete_date',
            'approved_by', 'approved_at',
            'lines', 'line_count',
            'version',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = (
            'created_at', 'updated_at', 'approved_by', 'approved_at',
            'effective_date', 'obsolete_date', 'version',
        )

    @extend_schema_field(serializers.IntegerField())
    def get_line_count(self, obj):
        return obj.lines.count()

    def update(self, instance, validated_data):
        if instance.status != 'DRAFT':
            raise serializers.ValidationError(
                "POST to /api/boms/{id}/revisions/ to create a new version."
            )
        return super().update(instance, validated_data)


class BOMListSerializer(SecureModelMixin):
    """Lightweight BOM serializer for lists"""
    part_type_name = serializers.CharField(source='part_type.name', read_only=True, allow_null=True)
    line_count = serializers.SerializerMethodField()

    class Meta:
        model = BOM
        fields = ('id', 'part_type', 'part_type_name', 'revision', 'bom_type', 'status', 'line_count')

    @extend_schema_field(serializers.IntegerField())
    def get_line_count(self, obj):
        return obj.lines.count()


# ===== ASSEMBLY USAGE SERIALIZERS =====

class AssemblyUsageSerializer(SecureModelMixin):
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
        return obj.installed_by.display_name if obj.installed_by else None


class AssemblyRemoveSerializer(serializers.Serializer):
    """Serializer for removing a component from assembly"""
    reason = serializers.CharField(required=False, allow_blank=True, default="")
