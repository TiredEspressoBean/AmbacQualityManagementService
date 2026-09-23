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
    RepairCode, RebuildScopePreset, RebuildSlotOverride,
    PartTypes, Companies, User, WorkOrder,
)
from .core import SecureModelMixin


# ===== CORE SERIALIZERS =====

class CoreSerializer(SecureModelMixin):
    """Remanufacturing core serializer"""
    core_type_name = serializers.CharField(source='core_type.name', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True, allow_null=True)
    # Derived from fulfilment_mode. Exposed so the UI states the consequence ("this unit
    # goes back to them") rather than re-deriving it from the enum and risking a
    # different answer than the backend's.
    returns_to_customer = serializers.BooleanField(read_only=True)
    # The core's story currently ends at "disassembled". Core <-> WO has to be
    # navigable BOTH ways, because that round trip is the traceability claim an audit
    # actually tests — "show me what happened to the unit I sent you".
    work_order_erp_id = serializers.CharField(
        source='work_order.ERP_id', read_only=True, allow_null=True)
    work_order_status = serializers.CharField(
        source='work_order.workorder_status', read_only=True, allow_null=True)
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
            'fulfilment_mode', 'returns_to_customer',
            'work_order_erp_id', 'work_order_status',
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
            'core_credit_issued_at', 'harvested_component_count', 'usable_component_count',
            'returns_to_customer', 'work_order_erp_id', 'work_order_status',
        )

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_received_by_name(self, obj):
        return obj.received_by.display_name if obj.received_by else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_disassembled_by_name(self, obj):
        return obj.disassembled_by.display_name if obj.disassembled_by else None


class CoreListSerializer(SecureModelMixin):
    """Lightweight core serializer for lists.

    Includes the fields the cores list page renders as columns
    (source/credit/component counts) so the table doesn't show
    blank cells for fields the OpenAPI schema doesn't promise.
    """
    core_type_name = serializers.CharField(source='core_type.name', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True, allow_null=True)
    harvested_component_count = serializers.IntegerField(read_only=True)
    usable_component_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Core
        fields = (
            'id', 'core_number', 'core_type', 'core_type_name',
            # On the LIST too: this is where somebody scans a shelf of cores, and
            # "which of these go back to a customer" is precisely the question you
            # want answered before anyone starts pulling one apart.
            'fulfilment_mode',
            'customer_name', 'status', 'condition_grade', 'received_date',
            'source_type', 'core_credit_value', 'core_credit_issued',
            # The rebuild queue sorts and ages on this: how long a torn-down core has
            # been sitting is the question that surface exists to answer, and showing
            # `received_date` next to a teardown-ordered list just reads as broken.
            'disassembly_completed_at',
            'harvested_component_count', 'usable_component_count',
        )


class CoreScrapSerializer(serializers.Serializer):
    """Serializer for scrapping a core"""
    reason = serializers.CharField(required=False, allow_blank=True, default="")


# ===== HARVESTED COMPONENT SERIALIZERS =====

class HarvestedComponentSerializer(SecureModelMixin):
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
        return obj.disassembled_by.display_name if obj.disassembled_by else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_scrapped_by_name(self, obj):
        return obj.scrapped_by.display_name if obj.scrapped_by else None


class HarvestedComponentScrapSerializer(serializers.Serializer):
    """Serializer for scrapping a harvested component"""
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class HarvestedComponentAcceptSerializer(serializers.Serializer):
    """Serializer for accepting a component to inventory"""
    erp_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)


# ===== DISASSEMBLY BOM LINE SERIALIZERS =====

class DisassemblyBOMLineSerializer(SecureModelMixin):
    """Disassembly BOM line serializer.

    DisassemblyBOMLine is a VERSIONED controlled record. Any content
    edit (quantities, fallout rate, notes, line number, FK reassignment)
    routes through `create_new_version` so reman yield spec changes are
    auditable. Archiving goes through a plain save.
    """
    core_type_name = serializers.CharField(source='core_type.name', read_only=True)
    component_type_name = serializers.CharField(source='component_type.name', read_only=True)
    expected_usable_qty = serializers.FloatField(read_only=True)

    class Meta:
        model = DisassemblyBOMLine
        fields = (
            'id', 'core_type', 'core_type_name',
            'component_type', 'component_type_name',
            'expected_qty', 'expected_fallout_rate', 'expected_usable_qty',
            'notes', 'positions', 'line_number',
            'created_at', 'updated_at', 'archived', 'version'
        )
        read_only_fields = ('created_at', 'updated_at', 'expected_usable_qty', 'version')

    # Fields whose edits are soft-delete / metadata only and should NOT
    # trigger a new version.
    _NON_VERSIONING_FIELDS = frozenset({'archived'})

    def validate(self, attrs):
        # If both positions and expected_qty are set, their lengths must match
        # (Q4 — refuse the edit instead of silently truncating/padding labels).
        positions = attrs.get('positions') if 'positions' in attrs else (
            self.instance.positions if self.instance else None
        )
        expected_qty = attrs.get('expected_qty') if 'expected_qty' in attrs else (
            self.instance.expected_qty if self.instance else None
        )
        if positions and expected_qty is not None and len(positions) != expected_qty:
            raise serializers.ValidationError({
                'positions': (
                    f"positions length ({len(positions)}) must equal expected_qty "
                    f"({expected_qty}). Clear positions before changing expected_qty, "
                    "or supply a matching-length list."
                ),
            })
        return super().validate(attrs)

    def update(self, instance, validated_data):
        """Route content edits through `create_new_version`; let
        archive toggles through as a plain save."""
        from Tracker.services.core.versioning import apply_versioned_update
        return apply_versioned_update(
            instance, validated_data,
            non_versioning_fields=self._NON_VERSIONING_FIELDS,
            default_update=super().update,
        )


class RebuildCandidateSerializer(serializers.Serializer):
    """Something that could fill a slot, whatever supply world it lives in."""
    kind = serializers.CharField()
    id = serializers.CharField()
    label = serializers.CharField()
    grade = serializers.CharField(allow_null=True)
    detail = serializers.CharField(allow_blank=True)


class RebuildSlotSerializer(serializers.Serializer):
    """One position on the rebuild and what we propose to put in it.

    `finding` and `reason` are separate on purpose: the first is what teardown found,
    the second is why that leads to this resolution. A planner confirming "grade B,
    from this unit — serviceable as found" is doing something different from one
    confirming a blank default, and the over-and-above quote has to show a customer
    why a line costs money.
    """
    position = serializers.CharField(allow_blank=True)
    # Set when a person overrode the proposal; `proposed_resolution` keeps what the
    # system would have done, since "the planner disagreed" only means something next
    # to what they disagreed with.
    is_overridden = serializers.BooleanField()
    proposed_resolution = serializers.CharField(allow_blank=True)
    override_id = serializers.CharField(allow_blank=True)
    component_type_id = serializers.CharField()
    component_type_name = serializers.CharField()
    bom_line_id = serializers.CharField(allow_null=True)
    finding = serializers.CharField()
    resolution = serializers.CharField()
    reason = serializers.CharField()
    needs_decision = serializers.BooleanField()
    candidates = RebuildCandidateSerializer(many=True)


class ScopedOperationSerializer(serializers.Serializer):
    """One operation the rebuild needs, and what put it there.

    `because` is the point: a planner who cannot see why an operation is on the job
    cannot challenge it, and the over-and-above quote has to show a customer which
    finding drove which cost.
    """
    step_id = serializers.CharField()
    step_name = serializers.CharField()
    code = serializers.CharField()
    code_name = serializers.CharField()
    because = serializers.ListField(child=serializers.CharField())


class RebuildPlanSerializer(serializers.Serializer):
    """A proposal. Nothing here is committed — see services/reman/rebuild.py."""
    core_id = serializers.CharField()
    core_number = serializers.CharField()
    fulfilment_mode = serializers.CharField()
    bom_revision = serializers.CharField(allow_null=True)
    entry_scope = serializers.CharField(allow_null=True)
    slots = RebuildSlotSerializer(many=True)
    operations = ScopedOperationSerializer(many=True)
    warnings = serializers.ListField(child=serializers.CharField())


class RepairCodeSerializer(SecureModelMixin):
    """A slot resolution that emits operations — see the design's §6.4."""
    component_type_name = serializers.CharField(
        source='component_type.name', read_only=True, allow_null=True)
    step_names = serializers.SerializerMethodField()

    class Meta:
        model = RepairCode
        fields = (
            'id', 'code', 'name', 'component_type', 'component_type_name',
            'trigger', 'steps', 'step_names', 'notes',
            'created_at', 'updated_at', 'archived', 'version',
        )
        read_only_fields = ('created_at', 'updated_at', 'version')

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_step_names(self, obj):
        return [s.name for s in obj.steps.all()]

    def update(self, instance, validated_data):
        from Tracker.services.core.versioning import apply_versioned_update
        return apply_versioned_update(instance, validated_data, self.context.get('request'))


class RebuildScopePresetSerializer(SecureModelMixin):
    """A named rebuild level — the entry scope, before any finding."""
    core_type_name = serializers.CharField(source='core_type.name', read_only=True)
    code_labels = serializers.SerializerMethodField()

    class Meta:
        model = RebuildScopePreset
        fields = (
            'id', 'core_type', 'core_type_name', 'name', 'is_default',
            'codes', 'code_labels', 'notes',
            'created_at', 'updated_at', 'archived', 'version',
        )
        read_only_fields = ('created_at', 'updated_at', 'version')

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_code_labels(self, obj):
        return [c.code for c in obj.codes.all()]

    def validate(self, attrs):
        """Refuse a second default for a core type, with a message that names the
        first one.

        A partial unique index already enforces this — two concurrent writers must
        not both win — but a constraint reached through the API surfaces as a 500,
        and 'Request failed with status code 500' tells an engineer nothing about
        what they did or how to undo it. The index stays as the backstop; this is
        the part a person reads.
        """
        attrs = super().validate(attrs)
        is_default = attrs.get(
            'is_default', getattr(self.instance, 'is_default', False))
        core_type = attrs.get(
            'core_type', getattr(self.instance, 'core_type', None))
        if not is_default or core_type is None:
            return attrs

        clash = RebuildScopePreset.objects.filter(  # tenant-safe: .objects auto-scopes to the request tenant
            core_type=core_type, is_default=True,
            is_current_version=True, archived=False,
        )
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        existing = clash.first()
        if existing is not None:
            raise serializers.ValidationError({
                'is_default': (
                    f"'{existing.name}' is already proposed automatically for "
                    f"{core_type.name}. Clear it there first — a core type can only "
                    f"have one default rebuild level."
                )
            })
        return attrs

    def update(self, instance, validated_data):
        from Tracker.services.core.versioning import apply_versioned_update
        return apply_versioned_update(instance, validated_data, self.context.get('request'))


class RebuildSlotOverrideSerializer(SecureModelMixin):
    """A planner's decision that differs from the proposed one.

    `reason` is required at the model level and stays required here: an override with
    no reason cannot be told from a misclick later, and this is the row that answers
    why a unit was built the way it was.
    """
    core_number = serializers.CharField(source='core.core_number', read_only=True)
    overridden_by_name = serializers.CharField(
        source='overridden_by.get_full_name', read_only=True, allow_null=True)

    class Meta:
        model = RebuildSlotOverride
        fields = (
            'id', 'core', 'core_number', 'bom_line', 'position',
            'resolution', 'reason', 'overridden_by', 'overridden_by_name',
            'created_at', 'updated_at', 'archived',
        )
        read_only_fields = ('created_at', 'updated_at', 'overridden_by')
