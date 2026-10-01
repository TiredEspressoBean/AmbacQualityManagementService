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
    Material, MaterialLot, MaterialUsage, StorageLocation, TimeEntry,
    BOM, BOMLine, AssemblyUsage,
    Equipments, PartTypes, Parts, WorkOrder, Steps, User, Companies,
)
from .core import SecureModelMixin, UserSelectSerializer


# ===== WORK CENTER SERIALIZERS =====

from Tracker.models.mes_standard import (
    PURCHASE_UNIT_CHOICES, SHORT_RECEIPT_CHOICES, SOURCE_TYPE_CHOICES,
)


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
            'is_constraint', 'is_critical', 'step_count', 'member_count',
            'created_at', 'updated_at', 'archived', 'version',
        )
        read_only_fields = ('created_at', 'updated_at', 'equipment_names',
                            'step_count', 'member_count', 'version')

    # `equipment` is station *placement* (operational master data, like
    # Steps.work_center) — editing what's at a station shouldn't fork a new
    # configuration version. Identity/config fields (name, code, kind,
    # capacity, cost center) still version.
    #
    # `is_constraint` joins them: it's a planning judgement about which station
    # currently governs output, and the answer changes when you buy a machine or
    # win a contract. Versioning the work centre every time a planner revises that
    # would bury real configuration history under scheduling opinion.
    #
    # `is_critical` is weaker still — it only decides whether the centre appears on the
    # rough-cut heatmap. A planner narrowing their view is not a configuration change.
    _NON_VERSIONING_FIELDS = frozenset({'archived', 'equipment', 'is_constraint',
                                        'is_critical'})

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
            'purchase_lead_time_days', 'safety_stock',
            'preferred_supplier', 'preferred_supplier_name',
            'purchase_unit', 'units_per_purchase_unit', 'requires_coc', 'requires_heat_number',
            'requires_supplier_qualification', 'commodity',
            'is_active', 'created_at', 'updated_at', 'archived',
        )
        read_only_fields = ('created_at', 'updated_at')


class StorageLocationSerializer(SecureModelMixin):
    """A managed place stock is kept. Optional — receiving takes free text without it."""

    class Meta:
        model = StorageLocation
        fields = ('id', 'name', 'description', 'is_active', 'created_at', 'updated_at', 'archived')
        read_only_fields = ('created_at', 'updated_at')

    def validate_name(self, value):
        # The (tenant, name) constraint is invisible to DRF (tenant isn't a field), so a
        # duplicate reached the database as a 500. Checked here, ignoring case — "Rack 3"
        # and "rack 3" are one place, which is the point of keeping the list.
        name = (value or '').strip()
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        clash = StorageLocation.unscoped.filter(tenant=tenant, name__iexact=name)  # tenant-safe: explicit tenant filter
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if tenant is not None and clash.exists():
            raise serializers.ValidationError(f'There is already a location called "{name}".')
        return name


# An expected receipt against its promised date (services.mes.material_lot.delivery_state).
# Shared by the lot's field and the late-deliveries list, so both name one enum.
DELIVERY_STATES = [('OVERDUE', 'Overdue'), ('DUE_SOON', 'Due soon')]


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
    # Customer property: whose it is, when it isn't ours.
    owner_name = serializers.CharField(source='owner.name', read_only=True, allow_null=True)
    parent_lot_number = serializers.CharField(source='parent_lot.lot_number', read_only=True, allow_null=True)
    # Who booked the material in. Null while a lot is ON_ORDER — nobody has received it.
    received_by_name = serializers.SerializerMethodField()
    child_lot_count = serializers.SerializerMethodField()
    # Live calendar shelf-life status (OK/WARNING/EXPIRED), or null when the lot
    # has no shelf life. Reads the LifeTracking record, not the raw scalar.
    shelf_life_status = serializers.SerializerMethodField()
    # OVERDUE / DUE_SOON for an ON_ORDER lot against its promised date, else null.
    delivery_state = serializers.SerializerMethodField()
    # Declared, not derived: as a read-only model field DRF drops allow_blank, so the
    # schema offered only BACKORDERED/CLOSED and the FE client rejected the "" every
    # full delivery carries — every lot list failed in the browser.
    # The item's receiving controls, so a receive screen can count in the buying unit
    # and say which paperwork the lot will be held for. Null for an ad-hoc lot.
    item_purchase_unit = serializers.SerializerMethodField()
    item_units_per_purchase_unit = serializers.SerializerMethodField()
    item_requires_coc = serializers.SerializerMethodField()
    item_requires_heat_number = serializers.SerializerMethodField()
    # Rejected, with an open return-to-supplier disposition: waiting for the dock to
    # ship it back. The list annotates it; a lone lot asks.
    awaiting_return = serializers.SerializerMethodField()
    short_receipt = serializers.ChoiceField(
        choices=SHORT_RECEIPT_CHOICES, allow_blank=True, read_only=True,
        help_text="For a short delivery: the remainder stays on order (BACKORDERED) or "
                  "nothing more is expected (CLOSED) — UQMES stops expecting it; the ERP's "
                  "PO line is the ERP's to close. Blank for a full delivery.")

    class Meta:
        model = MaterialLot
        fields = (
            'id', 'lot_number', 'parent_lot', 'parent_lot_number',
            'material_type', 'material_type_name',
            'material', 'material_name', 'item_name', 'material_description',
            'supplier', 'supplier_name', 'supplier_lot_number',
            'erp_po_number', 'erp_po_line', 'promised_date', 'delivery_state',
            'ordered_quantity', 'short_receipt',
            'received_date', 'received_by', 'received_by_name',
            'quantity', 'quantity_remaining', 'unit_of_measure',
            'status', 'hold_reason', 'manufacture_date', 'expiration_date',
            'shelf_life_status',
            'certificate_of_conformance', 'storage_location',
            'heat_number', 'source_type', 'received_as_quantity', 'received_as_unit',
            'owner', 'owner_name',
            'item_purchase_unit', 'item_units_per_purchase_unit',
            'item_requires_coc', 'item_requires_heat_number', 'awaiting_return',
            'child_lot_count',
            'created_at', 'updated_at', 'archived',
        )
        read_only_fields = (
            'created_at', 'updated_at', 'quantity_remaining',
            'parent_lot_number', 'child_lot_count', 'received_by',
            'hold_reason',
            # Set by receiving a short delivery, not edited.
            'ordered_quantity', 'short_receipt',
            # Moved only by the services — receiving routing, inspection, reject,
            # ship-back. Writable, a POST of ACCEPTED skipped inspection and a PATCH
            # put a RETURNED lot back in stock.
            'status',
        )

    def validate_lot_number(self, value):
        """A clash is a 400 naming the number — the unique constraint raised an
        IntegrityError, which reached the dock as an unexplained failure."""
        from Tracker.models import MaterialLot
        value = (value or "").strip()
        tenant = getattr(self.context.get('request'), 'tenant', None)
        clash = MaterialLot.objects.filter(lot_number__iexact=value)  # tenant-safe: .objects auto-scopes; narrowed to the tenant below
        if tenant is not None:
            clash = clash.filter(tenant=tenant)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError(
                f"Lot number {value} is already in use. Leave it blank to have one assigned; "
                f"the supplier's number goes in Supplier lot.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        # Counted in the buying unit ("3 boxes"): the stock quantity is derived from it,
        # and both are kept. In the stock unit, the entered quantity stands as it is.
        amount = attrs.get('received_as_quantity')
        unit = attrs.get('received_as_unit') or ''
        if amount is not None and unit not in ('', 'STOCK'):
            from Tracker.services.mes.material_lot import to_stock_quantity
            item = (attrs.get('material_type') or attrs.get('material')
                    or (self.instance.item if self.instance else None))
            if item is None:
                raise serializers.ValidationError(
                    {'received_as_unit': 'Pick the material or part before counting in its buying unit.'})
            try:
                attrs['quantity'] = to_stock_quantity(item, amount, unit)
            except ValueError as e:
                raise serializers.ValidationError({'received_as_quantity': str(e)})
        # A received lot's quantity changes through adjust-quantity (reason on record,
        # remaining kept in step), not an edit: a PATCH moved `quantity` and left
        # `quantity_remaining` where it was.
        if self.instance is not None and \
                attrs.get('quantity', self.instance.quantity) != self.instance.quantity:
            raise serializers.ValidationError(
                {'quantity': "Change a lot's quantity with Adjust quantity, which records why."})
        return attrs

    @extend_schema_field(serializers.ChoiceField(choices=PURCHASE_UNIT_CHOICES, allow_null=True))
    def get_item_purchase_unit(self, obj):
        return getattr(obj.item, 'purchase_unit', None) if obj.item is not None else None

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=4, allow_null=True))
    def get_item_units_per_purchase_unit(self, obj):
        v = getattr(obj.item, 'units_per_purchase_unit', None) if obj.item is not None else None
        return None if v is None else f"{v:.4f}"

    @extend_schema_field(serializers.BooleanField())
    def get_awaiting_return(self, obj):
        if obj.status != 'REJECTED':
            return False
        annotated = getattr(obj, '_awaiting_return', None)
        if annotated is not None:
            return bool(annotated)
        return obj.dispositions.filter(
            disposition_type='RETURN_TO_SUPPLIER').exclude(current_state='CLOSED').exists()

    @extend_schema_field(serializers.BooleanField())
    def get_item_requires_coc(self, obj):
        return bool(getattr(obj.item, 'requires_coc', False))

    @extend_schema_field(serializers.BooleanField())
    def get_item_requires_heat_number(self, obj):
        return bool(getattr(obj.item, 'requires_heat_number', False))

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_received_by_name(self, obj):
        return obj.received_by.display_name if obj.received_by_id else None

    @extend_schema_field(serializers.IntegerField())
    def get_child_lot_count(self, obj):
        return obj.child_lots.count()

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_shelf_life_status(self, obj):
        from Tracker.services.life_tracking.shelf_life import shelf_life_status
        return shelf_life_status(obj)

    @extend_schema_field(serializers.ChoiceField(choices=DELIVERY_STATES, allow_null=True))
    def get_delivery_state(self, obj):
        from Tracker.services.mes.material_lot import delivery_state
        if obj.status != 'ON_ORDER':
            return None
        # The plant's day, resolved once per response rather than once per row.
        today = self.context.get('_tenant_today')
        if today is None:
            from Tracker.services.core.clock import tenant_today
            today = tenant_today(obj.tenant_id)
            self.context['_tenant_today'] = today
        return delivery_state(obj, today)

class MaterialLotSplitSerializer(serializers.Serializer):
    """Serializer for splitting a lot"""
    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=4,
        min_value=Decimal('0.0001'),
        help_text="Quantity to split off (must be positive)"
    )
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class ExpectedReceiptSerializer(serializers.Serializer):
    """Stock ordered but not yet delivered, so planning can see it as incoming supply.

    Purchasing itself lives in the ERP — `erp_po_number` is a reference, not an order.
    The stock is a raw material (`material`) or a bought part (`material_type`), one of
    the two — the same either/or a lot holds."""
    material = TenantScopedPrimaryKeyRelatedField(
        queryset=Material.unscoped.all(), required=False, allow_null=True)
    material_type = TenantScopedPrimaryKeyRelatedField(
        queryset=PartTypes.unscoped.all(), required=False, allow_null=True,
        help_text="A bought part, instead of a material.")
    quantity = serializers.DecimalField(
        max_digits=12, decimal_places=4, min_value=Decimal('0.0001'),
        help_text="Quantity on order.")
    promised_date = serializers.DateField(
        help_text="Supplier's promised delivery date. Required — an undated receipt "
                  "cannot be placed in a planning bucket, so it would count as cover "
                  "without ever landing anywhere.")
    supplier = TenantScopedPrimaryKeyRelatedField(
        queryset=Companies.unscoped.all(), required=False, allow_null=True,
        help_text="Defaults to the material's preferred supplier.")
    erp_po_number = serializers.CharField(required=False, allow_blank=True, default="")
    erp_po_line = serializers.CharField(required=False, allow_blank=True, default="", max_length=20)
    unit_of_measure = serializers.CharField(required=False, allow_blank=True, default="")
    lot_number = serializers.CharField(
        required=False, allow_blank=True, default="",
        help_text="Usually unknown until the supplier ships. Left blank, a placeholder "
                  "is generated and replaced with the real number at receipt.")

    def validate(self, attrs):
        if bool(attrs.get('material')) == bool(attrs.get('material_type')):
            raise serializers.ValidationError("Give the material or the part on order — one of the two.")
        return attrs


class BulkExpectedReceiptSerializer(serializers.Serializer):
    """Several expected receipts at once, all or nothing — e.g. raised from shortages."""
    receipts = ExpectedReceiptSerializer(many=True, allow_empty=False)


class ExpectedReceiptImportRowResultSerializer(serializers.Serializer):
    row = serializers.IntegerField(help_text="1-based data row in the file (header excluded).")
    outcome = serializers.ChoiceField(
        choices=['CREATED', 'UPDATED', 'UNCHANGED', 'REOPENED', 'ERROR'])
    erp_po_number = serializers.CharField(allow_blank=True)
    erp_po_line = serializers.CharField(allow_blank=True)
    lot_number = serializers.CharField(allow_null=True)
    detail = serializers.CharField(allow_blank=True)


class ExpectedReceiptImportResultSerializer(serializers.Serializer):
    """What an expected-receipts import did, row by row. Rows that fail are reported and
    skipped; the rest still land — a person re-typed this sheet from the ERP, and one
    typo shouldn't throw the other ninety rows away."""
    created = serializers.IntegerField()
    updated = serializers.IntegerField()
    unchanged = serializers.IntegerField()
    reopened = serializers.IntegerField(
        help_text="Lines received before, expected again because the sheet shows them open.")
    errors = serializers.IntegerField()
    rows = ExpectedReceiptImportRowResultSerializer(many=True)


class LateDeliveryWorkOrderSerializer(serializers.Serializer):
    work_order_id = serializers.CharField()
    erp_id = serializers.CharField()
    expected_start = serializers.DateField(allow_null=True)


class LateDeliverySerializer(serializers.Serializer):
    """An expected receipt past, or near, its promised date, and the work it holds up."""
    lot_id = serializers.CharField()
    lot_number = serializers.CharField()
    item_name = serializers.CharField()
    supplier_name = serializers.CharField(allow_null=True)
    # Who to chase: the supplier's deliveries contact (or a general one).
    supplier_contact = serializers.CharField(allow_null=True)
    supplier_contact_email = serializers.CharField(allow_null=True)
    erp_po_number = serializers.CharField(allow_blank=True)
    erp_po_line = serializers.CharField(allow_blank=True)
    promised_date = serializers.DateField()
    days_late = serializers.IntegerField(
        help_text="Positive: days past the promised date. Zero or negative: due today or in that many days.")
    quantity = serializers.FloatField()
    unit_of_measure = serializers.CharField(allow_blank=True)
    state = serializers.ChoiceField(choices=DELIVERY_STATES)
    holding_up_count = serializers.IntegerField()
    holding_up = LateDeliveryWorkOrderSerializer(many=True)


class ReceiveExpectedLotSerializer(serializers.Serializer):
    """Book in an ON_ORDER lot that has physically arrived."""
    supplier_lot_number = serializers.CharField(
        required=False, allow_blank=True, max_length=100,
        help_text="The supplier's lot/batch number, as printed on the delivery. May repeat.")
    lot_number = serializers.CharField(
        required=False, allow_blank=True, max_length=100,
        help_text="Our lot number, when the shop labels its own. Blank (usual): one is "
                  "assigned (LOT-<year>-00001).")
    quantity = serializers.DecimalField(
        max_digits=12, decimal_places=4, min_value=Decimal('0.0001'),
        required=False, allow_null=True,
        help_text="Quantity actually delivered, when it differs from what was ordered. "
                  "Omit to keep the ordered quantity.")
    received_date = serializers.DateField(required=False, allow_null=True)
    storage_location = serializers.CharField(
        required=False, allow_blank=True, max_length=100,
        help_text="Where it was put away. Omit to keep what the expected receipt recorded.")
    remainder = serializers.ChoiceField(
        choices=SHORT_RECEIPT_CHOICES,
        required=False, allow_null=True,
        help_text="Required when fewer arrived than were on order: BACKORDERED keeps the "
                  "rest on order as a new expected lot; CLOSED expects nothing more (the "
                  "ERP's PO line is closed in the ERP).")
    received_as_quantity = serializers.DecimalField(
        max_digits=12, decimal_places=4, min_value=Decimal('0.0001'),
        required=False, allow_null=True,
        help_text="What was counted, in `received_as_unit`. Converted to the stock quantity "
                  "(and replaces `quantity`) when that is the item's buying unit.")
    received_as_unit = serializers.ChoiceField(
        choices=PURCHASE_UNIT_CHOICES, required=False, allow_blank=True, default='')
    heat_number = serializers.CharField(required=False, allow_blank=True, max_length=64)
    source_type = serializers.ChoiceField(
        choices=SOURCE_TYPE_CHOICES, required=False, allow_blank=True)


# Where rejected material goes, decided at rejection (use-as-is is a later concession).
LOT_REJECT_DISPOSITIONS = [('RETURN_TO_SUPPLIER', 'Return to supplier'), ('SCRAP', 'Scrap')]


class RejectLotSerializer(serializers.Serializer):
    """The inspector's reject: how many pieces are bad (or the whole lot), where they go,
    and why. Omitting both `rejected_quantity` and `whole_lot` rejects the whole lot."""
    disposition_type = serializers.ChoiceField(
        choices=LOT_REJECT_DISPOSITIONS, default='RETURN_TO_SUPPLIER')
    severity = serializers.ChoiceField(
        choices=[('CRITICAL', 'Critical'), ('MAJOR', 'Major'), ('MINOR', 'Minor')], default='MAJOR')
    description = serializers.CharField(required=False, allow_blank=True, default='')
    rejected_quantity = serializers.DecimalField(
        max_digits=12, decimal_places=4, min_value=Decimal('0.0001'), required=False, allow_null=True,
        help_text="Pieces found bad, in the stock unit. Fewer than the lot splits them off; "
                  "the rest is accepted.")
    whole_lot = serializers.BooleanField(
        default=False,
        help_text="Reject the whole lot back to the vendor. Needs reject_whole_lot; without "
                  "it the lot is held as a request for someone who has it.")


class RejectLotResponseSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=['PARTIAL', 'WHOLE_LOT', 'WHOLE_LOT_REQUESTED'])
    lot = MaterialLotSerializer(help_text="The lot that was rejected — for a partial "
                                          "reject, the new lot of the bad pieces.")
    disposition_id = serializers.CharField()
    disposition_number = serializers.CharField()


class LotDecisionSerializer(serializers.Serializer):
    """A later whole-lot decision on stock already accepted (reject the remainder)."""
    disposition_type = serializers.ChoiceField(
        choices=LOT_REJECT_DISPOSITIONS, default='RETURN_TO_SUPPLIER')
    description = serializers.CharField(allow_blank=False)


class ShipBackSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default='',
                                 help_text="Carrier, tracking, RMA number from the supplier…")


class TracePartSerializer(serializers.Serializer):
    part_id = serializers.CharField()
    erp_id = serializers.CharField()
    part_type = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    work_order_id = serializers.CharField(allow_null=True)
    work_order = serializers.CharField(allow_null=True)
    order_id = serializers.CharField(allow_null=True)
    order = serializers.CharField(allow_null=True)
    customer = serializers.CharField(allow_null=True)


class TraceUseSerializer(serializers.Serializer):
    # The lot drawn from: this one, or a lot split off it.
    lot_number = serializers.CharField()
    quantity = serializers.FloatField()
    consumed_at = serializers.DateTimeField()
    step = serializers.CharField(allow_null=True)
    work_order = serializers.CharField(allow_null=True)
    part = TracePartSerializer(allow_null=True)
    built_into = TracePartSerializer(many=True, help_text="Assemblies it went into, innermost first.")


class TraceSplitLotSerializer(serializers.Serializer):
    lot_id = serializers.CharField()
    lot_number = serializers.CharField()
    status = serializers.CharField()
    quantity = serializers.FloatField()


class TraceBackwardSerializer(serializers.Serializer):
    supplier = serializers.CharField(allow_null=True)
    supplier_lot_number = serializers.CharField(allow_null=True)
    heat_number = serializers.CharField(allow_null=True)
    source_type = serializers.CharField(allow_null=True)
    erp_po = serializers.CharField(allow_null=True)
    received_date = serializers.DateField(allow_null=True)
    parent_lot_id = serializers.CharField(allow_null=True)
    parent_lot_number = serializers.CharField(allow_null=True)
    split_lots = TraceSplitLotSerializer(many=True)


class LotTraceSerializer(serializers.Serializer):
    """Where a lot came from, and every part, assembly, order and customer it reached."""
    backward = TraceBackwardSerializer()
    forward = TraceUseSerializer(many=True)
    customers = serializers.ListField(child=serializers.CharField())


class DockReceiptDaySerializer(serializers.Serializer):
    date = serializers.DateField()
    lots = serializers.IntegerField()


class DockReasonCountSerializer(serializers.Serializer):
    reason = serializers.CharField()
    lots = serializers.IntegerField()


class DockMetricsSerializer(serializers.Serializer):
    """Receiving's own numbers over the last `days` days."""
    days = serializers.IntegerField()
    receipts = DockReceiptDaySerializer(many=True)
    lots_received = serializers.IntegerField()
    awaiting_decision = serializers.IntegerField()
    oldest_wait_days = serializers.IntegerField(allow_null=True)
    decided = serializers.IntegerField()
    median_inspection_hours = serializers.FloatField(allow_null=True)
    median_days_to_decision = serializers.FloatField(allow_null=True)
    held_now = DockReasonCountSerializer(many=True)
    holds_released = DockReasonCountSerializer(many=True)
    lots_rejected = serializers.IntegerField()
    pieces_rejected = serializers.FloatField()
    ppm_rejected = serializers.IntegerField(allow_null=True)


class ReleaseHoldSerializer(serializers.Serializer):
    """Lift a receiving hold. The reason is kept on record beside the decision."""
    reason = serializers.CharField(allow_blank=False)


class AdjustQuantitySerializer(serializers.Serializer):
    """Correct what's left of a lot to what is physically there."""
    quantity = serializers.DecimalField(
        max_digits=12, decimal_places=4, min_value=Decimal('0'),
        help_text="The quantity actually on hand now.")
    reason = serializers.CharField(allow_blank=False)


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
    """BOM line item serializer.

    Exactly one of `component_type` (a part) / `material` (a raw material) is set, and
    `source` is independent of that choice: a part can be MADE here or BOUGHT, and a
    raw material is only ever bought."""
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
        component_type = pick('component_type')
        material = pick('material')
        if (component_type is not None) == (material is not None):
            raise serializers.ValidationError(
                "Set exactly one of component_type (a part) or material (a raw material).")

        source = pick('source')
        if source == 'BUY' and component_type is not None and not component_type.can_buy:
            # Caught here rather than downstream: a BUY line on a make-only part resolves
            # to nothing purchasable, so it would silently vanish from the sourcing report
            # and the material gate instead of failing where it was authored.
            raise serializers.ValidationError(
                f"{component_type.name} isn't marked purchasable — set the part type's "
                f"'can buy' flag, or make this a MAKE line."
            )
        if source == 'MAKE' and material is not None:
            raise serializers.ValidationError(
                "A raw material can't be made in-house — use source=BUY, or point the "
                "line at a part type."
            )
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
