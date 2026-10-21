# serializers/reman.py - Remanufacturing Serializers
"""
Serializers for remanufacturing models:
- Core: Incoming used units
- HarvestedComponent: Disassembled components
- DisassemblyBOMLine: Expected disassembly yields
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field, inline_serializer

from Tracker.models import (
    Core, HarvestedComponent, DisassemblyBOMLine,
    RepairCode, RebuildScopePreset, RebuildSlotOverride,
    PartTypes, Companies, Orders,
)
from .core import SecureModelMixin
from .fields import TenantScopedPrimaryKeyRelatedField


# Each code a customer is (or would be) asked to authorise, its name and the findings
# behind it. One definition: two inline copies collide as schema components.
_AUTHORISATION_SCOPE = inline_serializer(name='AuthorisationScopeItem', many=True, fields={
    'code': serializers.CharField(), 'name': serializers.CharField(),
    'why': serializers.ListField(child=serializers.CharField())})


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
    # A core is a part; where it sits — its work order — is the part's. Read-only here:
    # a core is put on a work order by teardown planning, which moves its part.
    work_order = serializers.UUIDField(source='part.work_order_id', read_only=True, allow_null=True)
    work_order_erp_id = serializers.CharField(
        source='part.work_order.ERP_id', read_only=True, allow_null=True)
    work_order_status = serializers.CharField(
        source='part.work_order.workorder_status', read_only=True, allow_null=True)
    received_by_name = serializers.SerializerMethodField()
    awaiting_authorisation = serializers.SerializerMethodField(
        help_text="While the unit awaits the customer: each code they're asked about, its "
                  "name and the findings behind it. Empty otherwise.")
    authorisation_needed = serializers.SerializerMethodField(
        help_text="While a repair-and-return unit is in rebuild: what a request for the "
                  "customer's authorisation would ask about (code, name, findings). Empty "
                  "otherwise.")
    disassembled_by_name = serializers.SerializerMethodField()
    harvested_component_count = serializers.IntegerField(read_only=True)
    usable_component_count = serializers.IntegerField(read_only=True)
    pending_finding_count = serializers.IntegerField(
        read_only=True, help_text="Findings waiting on a lead's decision; the unit holds until each is decided.")
    # Repair codes approved for this unit since its process ran. Read-only: approvals
    # change only through approve_repair / record_authorisation. Declared so the
    # schema says list-of-codes, not "unknown".
    approved_repair_codes = serializers.ListField(
        child=serializers.CharField(), read_only=True)
    # The customer order this unit is here for. It lives on the core's PART, so it
    # follows the unit through teardown, split and rebuild. Required for a
    # repair-and-return core (`receipt_order_refusal`); set at receipt, and correctable
    # only while the core is still Received.
    order = TenantScopedPrimaryKeyRelatedField(
        source='part.order', queryset=Orders.unscoped.all(), required=False, allow_null=True)
    order_number = serializers.CharField(
        source='part.order.order_number', read_only=True, allow_null=True)

    class Meta:
        model = Core
        fields = (
            'id', 'core_number', 'serial_number',
            'core_type', 'core_type_name',
            'received_date', 'received_by', 'received_by_name',
            'customer', 'customer_name', 'source_type', 'source_reference',
            'fulfilment_mode', 'returns_to_customer',
            'work_order_erp_id', 'work_order_status',
            'returned_at', 'returned_by', 'return_reference',
            'condition_grade', 'condition_notes',
            'status', 'disassembly_started_at', 'disassembly_completed_at',
            'disassembled_by', 'disassembled_by_name',
            'core_credit_value', 'core_credit_issued', 'core_credit_issued_at',
            'work_order', 'part', 'order', 'order_number',
            'harvested_component_count', 'usable_component_count', 'pending_finding_count',
            'approved_repair_codes', 'awaiting_authorisation', 'authorisation_needed',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = (
            'created_at', 'updated_at',             'received_by', 'disassembled_by',
            'disassembly_started_at', 'disassembly_completed_at',
            'core_credit_issued_at', 'harvested_component_count', 'usable_component_count', 'pending_finding_count',
            'returns_to_customer', 'work_order_erp_id', 'work_order_status',
            'returned_at', 'returned_by',
            # The part this core IS — what the operator runtime opens. Minted with the
            # core, never set by a client.
            'part',
        )

    def create(self, validated_data):
        """Receive through the one creation path, so no core exists without its part."""
        from Tracker.services.reman.core_part import create_core
        order = validated_data.pop('part', {}).get('order')
        return create_core(tenant=validated_data.pop('tenant', None), order=order,
                           **validated_data)

    def update(self, instance, validated_data):
        part_fields = validated_data.pop('part', None)
        core = super().update(instance, validated_data)
        if part_fields is not None and 'order' in part_fields:
            core.part.order = part_fields['order']
            core.part.save(update_fields=['order', 'updated_at'])
        return core

    # Fields an EDIT may not change. The stage moves only through the reman services
    # (which keep the part's status derived from it); credit is recorded by
    # `issue_credit`, and the API is not an undo for it; core type and number are the
    # part's type and ERP id, so changing them here would split the unit from its part.
    _IMMUTABLE_ON_UPDATE = {
        'status': "the stage changes only through its actions (teardown, release, "
                  "rebuild, return, scrap)",
        'core_credit_issued': "credit is recorded by the Issue Credit action",
        'core_type': "the core type is its part's type",
        'core_number': "the core number is its part's identity",
    }

    def validate(self, attrs):
        attrs = super().validate(attrs)
        core = self.instance
        if core is None and not attrs.get('fulfilment_mode'):
            # A receipt that doesn't say takes the customer's standing arrangement — what
            # the receive screens show as "inherited" — not the model's EXCHANGE default,
            # or a repair-and-return customer's unit is quietly pooled into stock.
            from Tracker.services.reman.core import resolve_fulfilment_mode
            attrs['fulfilment_mode'], _ = resolve_fulfilment_mode(attrs.get('customer'))
        if core is None:
            self._validate_order(attrs, core)
            return attrs
        errors = {}
        for field, why in self._IMMUTABLE_ON_UPDATE.items():
            if field in attrs and attrs[field] != getattr(core, field):
                errors[field] = f"Can't be edited: {why}."
        # Fulfilment decides whether the unit may be harvested, whether its parts are
        # reserved to it, and whether scope needs the customer's authorisation — so it
        # can be corrected only before any of that has happened.
        if ('fulfilment_mode' in attrs and attrs['fulfilment_mode'] != core.fulfilment_mode
                and core.status != 'RECEIVED'):
            errors['fulfilment_mode'] = (
                "Can only be changed while the core is Received — teardown has started, "
                "and harvest, reservations and authorisation already follow from it.")
        if errors:
            raise serializers.ValidationError(errors)
        # After the stage guards, so an edit refused for the stage says so first.
        self._validate_order(attrs, core)
        return attrs

    def _validate_order(self, attrs, core):
        """The receipt's order against its customer and mode. On an edit, only when one
        of the three changes — a repair core received before orders were linked can
        still have its notes corrected."""
        from Tracker.services.reman.core import receipt_order_refusal
        touched = 'part' in attrs or 'customer' in attrs or 'fulfilment_mode' in attrs
        if core is not None and not touched:
            return
        if core is not None and 'part' in attrs and core.status != 'RECEIVED':
            raise serializers.ValidationError({'order': (
                "Can only be changed while the core is Received.")})
        order = (attrs['part'].get('order') if 'part' in attrs
                 else (core.part.order if core is not None else None))
        customer = attrs.get('customer', core.customer if core is not None else None)
        mode = attrs.get('fulfilment_mode',
                         core.fulfilment_mode if core is not None else 'EXCHANGE')
        why = receipt_order_refusal(order=order, customer=customer, fulfilment_mode=mode)
        if why:
            raise serializers.ValidationError({'order': why})

    @extend_schema_field(_AUTHORISATION_SCOPE)
    def get_awaiting_authorisation(self, obj):
        from Tracker.services.reman.release import pending_authorisation_scope
        return pending_authorisation_scope(obj)

    @extend_schema_field(_AUTHORISATION_SCOPE)
    def get_authorisation_needed(self, obj):
        if not obj.returns_to_customer:
            return []
        from Tracker.services.reman.release import pending_authorisation_scope
        return pending_authorisation_scope(obj, asking=True)

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
    pending_finding_count = serializers.IntegerField(
        read_only=True, help_text="Findings waiting on a lead's decision; the unit holds until each is decided.")

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
            'harvested_component_count', 'usable_component_count', 'pending_finding_count',
            # The part this core IS, so a list row can open the unit in the operator
            # runtime without a second fetch.
            'part',
        )
        read_only_fields = ('part',)


class CoreScrapSerializer(serializers.Serializer):
    """Serializer for scrapping a core"""
    reason = serializers.CharField(required=False, allow_blank=True, default="")


# ===== BULK CORE LOTS (Documents/CORE_AS_PART_DESIGN.md §6) =====

class CoreLotSerializer(serializers.Serializer):
    """A bulk core receipt: a MaterialLot of a core type, and how many of its units are
    still without an identity."""
    id = serializers.UUIDField(read_only=True)
    lot_number = serializers.CharField(read_only=True)
    core_type = serializers.UUIDField(source='material_type_id', read_only=True)
    core_type_name = serializers.CharField(source='material_type.name', read_only=True)
    customer = serializers.UUIDField(source='supplier_id', read_only=True, allow_null=True)
    customer_name = serializers.CharField(source='supplier.name', read_only=True, allow_null=True)
    source_reference = serializers.CharField(source='supplier_lot_number', read_only=True)
    received_date = serializers.DateField(read_only=True, allow_null=True)
    quantity = serializers.IntegerField(read_only=True)
    unidentified = serializers.IntegerField(source='quantity_remaining', read_only=True)
    status = serializers.CharField(read_only=True)
    storage_location = serializers.CharField(read_only=True)


class CoreLotReceiveSerializer(serializers.Serializer):
    core_type = TenantScopedPrimaryKeyRelatedField(queryset=PartTypes.unscoped.all())
    quantity = serializers.IntegerField(min_value=1)
    customer = TenantScopedPrimaryKeyRelatedField(
        queryset=Companies.unscoped.all(), required=False, allow_null=True)
    received_date = serializers.DateField(required=False, allow_null=True)
    lot_number = serializers.CharField(required=False, allow_blank=True)
    storage_location = serializers.CharField(required=False, allow_blank=True)
    source_reference = serializers.CharField(required=False, allow_blank=True)


class CoreAssignIdentitySerializer(serializers.Serializer):
    """Give one unit of a bulk lot its identity. The unit is graded by whoever is
    holding it, as at individual receipt."""
    lot = serializers.UUIDField()
    condition_grade = serializers.ChoiceField(choices=Core.CONDITION_GRADE_CHOICES)
    serial_number = serializers.CharField(required=False, allow_blank=True)
    condition_notes = serializers.CharField(required=False, allow_blank=True)
    source_type = serializers.ChoiceField(
        choices=Core.SOURCE_TYPE_CHOICES, required=False)


# ===== HARVESTED COMPONENT SERIALIZERS =====

class HarvestedComponentSerializer(SecureModelMixin):
    """Harvested component serializer"""
    core_number = serializers.CharField(source='core.core_number', read_only=True)
    component_type_name = serializers.CharField(source='component_type.name', read_only=True)
    component_part_erp_id = serializers.CharField(source='component_part.ERP_id', read_only=True, allow_null=True)
    disassembled_by_name = serializers.SerializerMethodField()
    scrapped_by_name = serializers.SerializerMethodField()
    proposed_by_name = serializers.SerializerMethodField()
    # Declared, not left to the model: it is BLANK whenever no finding is pending —
    # nearly always — and the inferred field was typed as the bare grade enum, so the
    # generated client would reject every harvested-component response. Explicit
    # allow_blank puts the blank in the schema.
    proposed_grade = serializers.ChoiceField(
        choices=HarvestedComponent.CONDITION_GRADE_CHOICES, allow_blank=True, read_only=True)

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
            # A finding raised after teardown, waiting on a lead (services/reman/findings).
            'proposed_grade', 'proposed_finding', 'proposed_at', 'proposed_by_name',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = (
            'created_at', 'updated_at',             'disassembled_at', 'disassembled_by', 'scrapped_at', 'scrapped_by',
            'is_scrapped', 'scrap_reason', 'component_part',
            # Written only by record/apply/dismiss_finding — never set directly.
            'proposed_grade', 'proposed_finding', 'proposed_at',
        )

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_proposed_by_name(self, obj):
        return obj.proposed_by.display_name if obj.proposed_by else None

    # Nullable: `disassembled_by` is SET_NULL, and an un-annotated-null field makes the
    # generated client reject the response the first time it is null.
    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_disassembled_by_name(self, obj):
        return obj.disassembled_by.display_name if obj.disassembled_by else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_scrapped_by_name(self, obj):
        return obj.scrapped_by.display_name if obj.scrapped_by else None


class HarvestedComponentFindingDismissSerializer(serializers.Serializer):
    reason = serializers.CharField()


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


class ExpectedRepairSerializer(serializers.Serializer):
    """One repair the rebuild is expected to take, and what put it there.

    `because` is the point: a planner who cannot see why a repair is on the job
    cannot challenge it, and the over-and-above quote has to show a customer which
    finding drove which cost. `needs_approval` flags a repair the check doesn't
    pre-approve, so its answer can be sought before the unit arrives.
    """
    step_id = serializers.CharField()
    step_name = serializers.CharField()
    code = serializers.CharField()
    code_name = serializers.CharField()
    because = serializers.ListField(child=serializers.CharField())
    check_name = serializers.CharField(allow_blank=True)
    needs_approval = serializers.BooleanField()


class RebuildPlanSerializer(serializers.Serializer):
    """A proposal. Nothing here is committed — see services/reman/rebuild.py."""
    core_id = serializers.CharField()
    core_number = serializers.CharField()
    fulfilment_mode = serializers.CharField()
    bom_revision = serializers.CharField(allow_null=True)
    entry_scope = serializers.CharField(allow_null=True)
    slots = RebuildSlotSerializer(many=True)
    expected_repairs = ExpectedRepairSerializer(many=True)
    warnings = serializers.ListField(child=serializers.CharField())


class RepairCodeSerializer(SecureModelMixin):
    """A repair raised by a slot resolution, done at the Repair nodes carrying it."""
    component_type_name = serializers.CharField(
        source='component_type.name', read_only=True, allow_null=True)
    # The Repair nodes that carry this code (Steps.repair_code) — where a check sends a
    # unit when the code is raised.
    repair_step_names = serializers.SerializerMethodField()

    class Meta:
        model = RepairCode
        fields = (
            'id', 'code', 'name', 'component_type', 'component_type_name',
            'trigger', 'repair_step_names', 'notes',
            'created_at', 'updated_at', 'archived', 'version',
        )
        read_only_fields = ('created_at', 'updated_at', 'version')

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_repair_step_names(self, obj):
        from Tracker.models import Steps
        return sorted({s.name for s in Steps.objects.filter(  # tenant-safe: .objects auto-scopes
            repair_code__code=obj.code, archived=False)})

    # Retiring a code is not a revision of it.
    _NON_VERSIONING_FIELDS = frozenset({'archived'})

    def update(self, instance, validated_data):
        """A content edit makes a new version; `archived` saves in place.

        This passed the request positionally where `apply_versioned_update` takes
        `non_versioning_fields` and `default_update` by keyword, so every edit of a
        repair code was a TypeError (500).
        """
        from Tracker.services.core.versioning import apply_versioned_update
        request = self.context.get('request')
        return apply_versioned_update(
            instance, validated_data,
            non_versioning_fields=self._NON_VERSIONING_FIELDS,
            default_update=super().update,
            version_kwargs={'user': getattr(request, 'user', None)})


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
