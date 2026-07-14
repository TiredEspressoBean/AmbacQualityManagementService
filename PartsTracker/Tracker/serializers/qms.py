# serializers/qms.py - Quality Management System serializers
import logging

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from Tracker.models import (
    # QMS models
    QualityErrorsList, MeasurementResult, QualityReports,
    QualityReportEquipment, QualityReportPersonnel,
    QuarantineDisposition, SupplierQualification, PartApproval,
    # CAPA models
    CAPA, CapaTasks, CapaTaskAssignee, RcaRecord, FiveWhys, Fishbone, RootCause, CapaVerification,
    # CAPA enums
    CapaType, CapaSeverity, CapaStatus, CapaTaskType, CapaTaskStatus,
    RcaMethod, RootCauseCategory, EffectivenessResult,
    # MES Lite models
    MeasurementDefinition, Steps, WorkOrder,
    # MES Standard models
    SamplingRule, SamplingRuleSet, SamplingRuleType, SamplingAnalytics,
    SamplingAuditLog, SamplingSeverityState, SamplingTriggerState,
    # Manufacturing / supplier
    PartTypes, Companies,
    # Core models
    NotificationTask,
)

from .core import SecureModelMixin
from .fields import TenantScopedPrimaryKeyRelatedField

logger = logging.getLogger(__name__)


# ===== QUALITY AND ERROR SERIALIZERS =====

class QualityErrorsListSerializer(SecureModelMixin):
    """Quality errors list serializer.

    QualityErrorsList is a versioned defect-catalog entry. Any content edit
    (name, example text, part-type link, annotation flag) routes through
    `create_new_version` so changes are auditable. Archiving goes through
    a plain save because it is a soft-delete, not a content change.
    """
    # `part_type` FK is nullable on the model (tenant-wide error types are
    # part-type-agnostic), so the derived `part_type_name` must allow null
    # or zodios rejects the response on the frontend.
    part_type_name = serializers.CharField(source="part_type.name", read_only=True, allow_null=True)

    class Meta:
        model = QualityErrorsList
        fields = ["id", "error_name", "error_example", "part_type", "part_type_name",
                  "requires_3d_annotation", "archived", "version"]
        read_only_fields = ("version",)

    _NON_VERSIONING_FIELDS = frozenset({'archived'})

    def update(self, instance, validated_data):
        from Tracker.services.core.versioning import apply_versioned_update
        return apply_versioned_update(
            instance, validated_data,
            non_versioning_fields=self._NON_VERSIONING_FIELDS,
            default_update=super().update,
        )


class ErrorTypeSerializer(SecureModelMixin):
    """Legacy error type serializer"""
    part_type_name = serializers.CharField(source="part_type.name", read_only=True, allow_null=True)

    class Meta:
        model = QualityErrorsList
        fields = ["id", "error_name", "error_example", "part_type", "part_type_name", "requires_3d_annotation", "archived"]


# ===== MEASUREMENT SERIALIZERS =====

class MeasurementDefinitionSerializer(SecureModelMixin):
    """Measurement definition serializer with versioning support.

    Content edits (label, type, unit, nominal, tolerances, required,
    spc_enabled) create a new version via `create_new_version`.
    Archive-only updates go through a plain save.
    """
    step_name = serializers.SerializerMethodField()
    default_equipment_name = serializers.CharField(
        source="default_equipment.name", read_only=True, allow_null=True)
    backup_equipment_name = serializers.CharField(
        source="backup_equipment.name", read_only=True, allow_null=True)

    # Fields whose edits are soft-delete / metadata only and should NOT
    # trigger a new version.
    _NON_VERSIONING_FIELDS = frozenset({'archived'})

    class Meta:
        model = MeasurementDefinition
        fields = [
            "id", "label", "step_name", "unit", "nominal",
            "upper_tol", "lower_tol", "required", "type", "step",
            "spc_enabled", "archived", "characteristic_number",
            "default_equipment", "default_equipment_name",
            "backup_equipment", "backup_equipment_name",
            "version", "is_current_version", "previous_version",
        ]
        # `step` is writable on create (a measurement must be attached to a
        # step) but the form always sends the owning step, so versioned
        # updates carry it forward unchanged.
        read_only_fields = ["id", "version", "is_current_version",
                            "previous_version"]

    @extend_schema_field(serializers.CharField())
    def get_step_name(self, obj) -> str | None:
        return obj.step.name if obj.step else None

    def update(self, instance, validated_data):
        """Route content edits through `create_new_version`; let
        archive toggles through as a plain save."""
        from Tracker.services.core.versioning import apply_versioned_update
        return apply_versioned_update(
            instance, validated_data,
            non_versioning_fields=self._NON_VERSIONING_FIELDS,
            default_update=super().update,
        )


class MeasurementResultSerializer(SecureModelMixin):
    report = serializers.CharField(read_only=True)
    is_within_spec = serializers.BooleanField(read_only=True)
    created_by = serializers.IntegerField(read_only=True, source='created_by_id')

    class Meta:
        model = MeasurementResult
        fields = ["report", "definition", "value_numeric", "value_pass_fail", "is_within_spec", "created_by", "archived"]


# ===== QUALITY REPORTS SERIALIZERS =====

class QualityReportEquipmentSerializer(SecureModelMixin):
    """Nested row of (equipment, role) on a QualityReports record."""

    equipment_name = serializers.CharField(source='equipment.name', read_only=True)

    class Meta:
        model = QualityReportEquipment
        fields = ['id', 'equipment', 'equipment_name', 'role', 'notes']


class QualityReportPersonnelSerializer(serializers.ModelSerializer):
    """Nested row of (user, role, signed_at) on a QualityReports record."""

    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = QualityReportPersonnel
        fields = ['id', 'user', 'username', 'full_name', 'role', 'signed_at', 'notes']

    @extend_schema_field(serializers.CharField())
    def get_full_name(self, obj) -> str:
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username


class QualityReportsSerializer(SecureModelMixin):
    """Quality reports serializer"""
    measurements = MeasurementResultSerializer(many=True, required=False)
    # New role-tagged shapes (read-only for now — operator-runtime phase
    # will accept them on write through dedicated capture endpoints).
    equipment_links = QualityReportEquipmentSerializer(many=True, read_only=True)
    personnel_links = QualityReportPersonnelSerializer(many=True, read_only=True)

    # Display fields for related models
    part_info = serializers.SerializerMethodField()
    part_display = serializers.SerializerMethodField()
    step_info = serializers.SerializerMethodField()
    machine_info = serializers.SerializerMethodField()
    operators_info = serializers.SerializerMethodField()
    errors_info = serializers.SerializerMethodField()
    file_info = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    detected_by_info = serializers.SerializerMethodField()
    verified_by_info = serializers.SerializerMethodField()

    class Meta:
        model = QualityReports
        fields = ["id", "report_number", "step", "part", "machine", "operators", "sampling_method", "status",
                  "status_display", "description", "file", "created_at", "errors", "measurements", "sampling_audit_log",
                  "detected_by", "detected_by_info", "verified_by", "verified_by_info",
                  "is_first_piece",  # First Piece Inspection flag
                  "material_lot", "osp_shipment", "sample_size", "accept_number", "reject_number",  # Receiving / OSP inspection
                  "step_execution", "substep", "batch_execution",  # Inspection-event provenance (which visit/batch, which substep)
                  "equipment_links", "personnel_links",  # New role-tagged shape
                  "part_info", "part_display", "step_info", "machine_info", "operators_info", "errors_info", "file_info", "archived"]
        # Provenance is written by the capture services (inline_capture /
        # operator_capture), never by an API client hand-filing a report.
        read_only_fields = ("report_number", "created_at",
                            "material_lot", "osp_shipment", "sample_size", "accept_number", "reject_number",
                            "step_execution", "substep", "batch_execution")

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_part_info(self, obj):
        if obj.part:
            return {
                'id': obj.part.id,
                'erp_id': obj.part.ERP_id,
                'status': obj.part.part_status,
                'part_type_name': obj.part.part_type.name if obj.part.part_type else None,
            }
        return None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_part_display(self, obj):
        """Return a friendly part identifier: ERP ID and part type name."""
        if obj.part:
            part_type = obj.part.part_type.name if obj.part.part_type else None
            if part_type:
                return f"{obj.part.ERP_id} ({part_type})"
            return obj.part.ERP_id
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_step_info(self, obj):
        if obj.step:
            # Get process name from part's work_order
            process_name = None
            if obj.part and obj.part.work_order and obj.part.work_order.process:
                process_name = obj.part.work_order.process.name
            return {
                'id': obj.step.id,
                'name': obj.step.name,
                'process_name': process_name,
            }
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_machine_info(self, obj):
        if obj.machine:
            return {
                'id': obj.machine.id,
                'name': obj.machine.name,
                'type': obj.machine.equipment_type.name if obj.machine.equipment_type else None,
            }
        return None

    @extend_schema_field(serializers.ListField())
    def get_operators_info(self, obj):
        return [
            {
                'id': op.id,
                'username': op.username,
                'full_name': f"{op.first_name} {op.last_name}".strip() or op.username,
            }
            for op in obj.operators.all()
        ]

    @extend_schema_field(serializers.ListField())
    def get_errors_info(self, obj):
        return [
            {
                'id': err.id,
                'name': err.error_name,
            }
            for err in obj.errors.all()
        ]

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_file_info(self, obj):
        if obj.file:
            return {
                'id': obj.file.id,
                'file_name': obj.file.file_name,
                'classification': obj.file.classification,
            }
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_detected_by_info(self, obj):
        if obj.detected_by:
            return {
                'id': obj.detected_by.id,
                'username': obj.detected_by.username,
                'full_name': f"{obj.detected_by.first_name} {obj.detected_by.last_name}".strip() or obj.detected_by.username,
            }
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_verified_by_info(self, obj):
        if obj.verified_by:
            return {
                'id': obj.verified_by.id,
                'username': obj.verified_by.username,
                'full_name': f"{obj.verified_by.first_name} {obj.verified_by.last_name}".strip() or obj.verified_by.username,
            }
        return None

    def create(self, validated_data):
        from Tracker.services.qms.quality_report import record_quality_report_side_effects

        measurements_data = validated_data.pop("measurements", [])
        report = super().create(validated_data)

        for m in measurements_data:
            MeasurementResult.objects.create(report=report, definition_id=m['definition'].id,
                                             value_numeric=m.get('value_numeric'),
                                             value_pass_fail=m.get('value_pass_fail'),
                                             created_by=self.context["request"].user)

        record_quality_report_side_effects(report)
        return report


# ===== SAMPLING RULE SERIALIZERS =====

class SamplingRuleSerializer(SecureModelMixin):
    """Enhanced sampling rule serializer"""
    rule_type_display = serializers.CharField(source='get_rule_type_display', read_only=True)
    ruleset_info = serializers.SerializerMethodField()

    # Legacy compatibility fields
    ruletype_name = serializers.SerializerMethodField()
    ruleset_name = serializers.CharField(source="ruleset.name", read_only=True)

    class Meta:
        model = SamplingRule
        fields = (
        'id', 'rule_type', 'rule_type_display', 'value', 'order', 'algorithm_description', 'last_validated', 'ruleset',
        'ruleset_info', 'created_by', 'created_at', 'modified_by', 'updated_at', 'ruletype_name',
        'ruleset_name', 'archived')
        read_only_fields = ('created_at', 'updated_at', 'ruleset_info', 'ruletype_name', 'ruleset_name')

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_ruleset_info(self, obj):
        if obj.ruleset:
            return {'id': obj.ruleset.id, 'name': obj.ruleset.name, 'version': obj.ruleset.version}
        return None

    @extend_schema_field(serializers.CharField())
    def get_ruletype_name(self, obj) -> str:
        return obj.get_rule_type_display()


# ===== SAMPLING RULESET SERIALIZERS =====

class SamplingSeverityStateSerializer(SecureModelMixin):
    """Read-only runtime Z1.4 severity state, with the switching-procedure
    position spelled out so the inspector-facing badge ("Tightened since X ·
    N more accepts returns to Normal") derives from the engine's own
    thresholds. Mutations belong exclusively to the switching engine."""
    step_name = serializers.CharField(source="step.name", read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True, allow_null=True)
    rejects_in_window = serializers.SerializerMethodField()
    next_severity_on_accepts = serializers.SerializerMethodField()
    accepts_needed = serializers.SerializerMethodField()

    class Meta:
        model = SamplingSeverityState
        fields = (
            'id', 'step', 'step_name', 'supplier', 'supplier_name',
            'severity', 'severity_since', 'discontinued',
            'consecutive_accepts', 'lots_in_regime',
            'rejects_in_window', 'next_severity_on_accepts', 'accepts_needed',
            'updated_at',
        )
        read_only_fields = fields

    def _status(self, obj) -> dict:
        from Tracker.services.qms.severity_switching import switching_status
        return switching_status(obj)

    @extend_schema_field(serializers.IntegerField())
    def get_rejects_in_window(self, obj) -> int:
        return self._status(obj)["rejects_in_window"]

    @extend_schema_field(serializers.CharField())
    def get_next_severity_on_accepts(self, obj) -> str:
        return self._status(obj)["next_severity_on_accepts"]

    @extend_schema_field(serializers.IntegerField(allow_null=True))
    def get_accepts_needed(self, obj):
        return self._status(obj)["accepts_needed"]


class SamplingRuleSetSerializer(SecureModelMixin):
    """Enhanced sampling ruleset serializer"""
    rules = serializers.SerializerMethodField()
    part_type_info = serializers.SerializerMethodField()
    process_info = serializers.SerializerMethodField()
    step_info = serializers.SerializerMethodField()

    # Legacy compatibility fields
    part_type_name = serializers.CharField(source="part_type.name", read_only=True)
    process_name = serializers.CharField(source="process.name", read_only=True)

    class Meta:
        model = SamplingRuleSet
        fields = ('id', 'name', 'origin', 'active', 'version', 'is_fallback', 'fallback_duration',
                  'part_type', 'part_type_info', 'process', 'process_info', 'step', 'step_info', 'rules',
                  'supplier', 'aql', 'inspection_level', 'severity', 'strategy',  # acceptance sampling
                  'gate_metric', 'gate_threshold', 'gate_window', 'gate_window_n', 'gate_min_sample',  # quality gate
                  'gate_actions', 'gate_capa_type', 'gate_capa_severity', 'gate_approval_template',
                  'created_by', 'created_at', 'modified_by', 'updated_at', 'part_type_name', 'process_name', 'archived')
        read_only_fields = (
            'created_at', 'updated_at', 'rules', 'part_type_info', 'process_info', 'step_info',
            'part_type_name', 'process_name', 'version')

    @extend_schema_field(serializers.ListField())
    def get_rules(self, obj):
        return obj.get_rules_summary() if hasattr(obj, 'get_rules_summary') else list(
            obj.rules.all().values('id', 'rule_type', 'value', 'order', 'algorithm_description', 'last_validated'))

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_part_type_info(self, obj):
        if obj.part_type:
            return {'id': obj.part_type.id, 'name': obj.part_type.name}
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_process_info(self, obj):
        if obj.process:
            return {'id': obj.process.id, 'name': obj.process.name}
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_step_info(self, obj):
        if obj.step:
            return {'id': obj.step.id, 'name': obj.step.name}
        return None


class ResolvedSamplingRuleSetSerializer(serializers.ModelSerializer):
    """Resolved sampling ruleset serializer"""
    rules = SamplingRuleSerializer(many=True, read_only=True)

    class Meta:
        model = SamplingRuleSet
        fields = ["id", "name", "rules", "fallback_duration"]


# Schema shape for Step.get_resolved_sampling_rules() output. The model method
# returns a stub object with null fields when there is no bound ruleset, so the
# shape diverges from the model-backed serializer above (which assumes a real row).
_RESOLVED_RULE_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "format": "uuid"},
        "rule_type": {"type": "string"},
        "value": {"type": "integer", "nullable": True},
        "order": {"type": "integer"},
    },
}

_RESOLVED_ACTIVE_RULESET_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "format": "uuid", "nullable": True},
        "name": {"type": "string", "nullable": True},
        "rules": {"type": "array", "items": _RESOLVED_RULE_SCHEMA},
        "fallback_duration": {"type": "integer", "nullable": True},
        "tighten_after": {"type": "integer", "nullable": True},
        "gate_metric": {"type": "string"},
        "gate_threshold": {"type": "string", "nullable": True},
        "gate_window": {"type": "string"},
        "gate_window_n": {"type": "integer", "nullable": True},
        "gate_min_sample": {"type": "integer", "nullable": True},
        "gate_actions": {"type": "array", "items": {"type": "string"}},
        "gate_capa_type": {"type": "string"},
        "gate_capa_severity": {"type": "string"},
        "gate_approval_template": {"type": "string", "format": "uuid", "nullable": True},
        "aql": {"type": "string", "nullable": True},
        "inspection_level": {"type": "string"},
        "severity": {"type": "string"},
        "strategy": {"type": "string"},
    },
}

_RESOLVED_FALLBACK_RULESET_SCHEMA = {
    "type": "object",
    "nullable": True,
    "properties": {
        "id": {"type": "string", "format": "uuid", "nullable": True},
        "name": {"type": "string", "nullable": True},
        "rules": {"type": "array", "items": _RESOLVED_RULE_SCHEMA},
    },
}


class StepWithResolvedRulesSerializer(SecureModelMixin):
    """Step with resolved sampling rules (for flow editor)"""
    active_ruleset = serializers.SerializerMethodField()
    fallback_ruleset = serializers.SerializerMethodField()
    part_type_name = serializers.CharField(source="part_type.name", read_only=True)
    part_type_info = serializers.SerializerMethodField()

    class Meta:
        model = Steps
        fields = ["id", "name", "description", "expected_duration", "part_type", "part_type_name",
                  "part_type_info", "active_ruleset", "fallback_ruleset", "sampling_required",
                  "min_sampling_rate", "created_at", "updated_at", "archived"]

    @extend_schema_field({
        "type": "object",
        "properties": {
            "id": {"type": "string", "format": "uuid"},
            "name": {"type": "string"},
        },
    })
    def get_part_type_info(self, obj):
        """Return basic part type info"""
        if obj.part_type:
            return {"id": obj.part_type.id, "name": obj.part_type.name}
        return {}

    @extend_schema_field(_RESOLVED_ACTIVE_RULESET_SCHEMA)
    def get_active_ruleset(self, step):
        """Use model method for resolved sampling rules"""
        resolved = step.get_resolved_sampling_rules()
        return resolved.get('active_ruleset')

    @extend_schema_field(_RESOLVED_FALLBACK_RULESET_SCHEMA)
    def get_fallback_ruleset(self, step):
        """Use model method for resolved sampling rules"""
        resolved = step.get_resolved_sampling_rules()
        return resolved.get('fallback_ruleset')


# ===== SAMPLING RULES UPDATE SERIALIZERS =====

class SamplingRuleUpdateSerializer(serializers.Serializer):
    """Serializer for updating sampling rules on steps"""
    rule_type = serializers.ChoiceField(choices=SamplingRuleType.choices)
    value = serializers.IntegerField(allow_null=True, required=False)
    order = serializers.IntegerField()


class SamplingRuleWriteSerializer(serializers.Serializer):
    """Write serializer for sampling rules"""
    rule_type = serializers.ChoiceField(choices=SamplingRuleType.choices)
    value = serializers.IntegerField(allow_null=True, required=False)
    order = serializers.IntegerField()
    is_fallback = serializers.BooleanField(required=False)


class StepSamplingRulesUpdateSerializer(serializers.Serializer):
    """Update a step's sampling rules — plus its quality gate and acceptance plan,
    so the flow-editor dialog persists everything in one atomic call."""
    rules = SamplingRuleUpdateSerializer(many=True)
    fallback_rules = SamplingRuleUpdateSerializer(many=True, required=False)
    fallback_duration = serializers.IntegerField(required=False)
    tighten_after = serializers.IntegerField(
        required=False, allow_null=True,
        help_text="Consecutive failures before tightening to the fallback ruleset "
                  "(sets a CONSECUTIVE_FAILS + TIGHTEN_SAMPLING gate).")
    # Quality gate (set on the resulting primary ruleset).
    gate_metric = serializers.CharField(required=False, allow_blank=True)
    gate_threshold = serializers.DecimalField(max_digits=7, decimal_places=3, required=False, allow_null=True)
    gate_window = serializers.CharField(required=False, allow_blank=True)
    gate_window_n = serializers.IntegerField(required=False, allow_null=True)
    gate_min_sample = serializers.IntegerField(required=False, allow_null=True)
    gate_actions = serializers.ListField(child=serializers.CharField(), required=False)
    gate_capa_type = serializers.CharField(required=False, allow_blank=True)
    gate_capa_severity = serializers.CharField(required=False, allow_blank=True)
    gate_approval_template = serializers.UUIDField(required=False, allow_null=True)
    # Acceptance sampling (RECEIVING steps).
    aql = serializers.DecimalField(max_digits=5, decimal_places=3, required=False, allow_null=True)
    inspection_level = serializers.CharField(required=False, allow_blank=True)
    severity = serializers.CharField(required=False, allow_blank=True)
    strategy = serializers.CharField(required=False, allow_blank=True)
    variables_characteristic = serializers.UUIDField(required=False, allow_null=True)
    # Supplier scope for the (step, supplier) ruleset — Receiving Inspection Plans.
    # Null/absent = the supplier-agnostic plan (flow-editor steps + "all suppliers" RIPs).
    supplier = serializers.UUIDField(required=False, allow_null=True)

    def update_step_rules(self, step):
        """Use model method for applying sampling rules"""
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        vd = self.validated_data

        gate = {
            'gate_metric': vd.get('gate_metric', ''),
            'gate_threshold': vd.get('gate_threshold'),
            'gate_window': vd.get('gate_window', ''),
            'gate_window_n': vd.get('gate_window_n'),
            'gate_min_sample': vd.get('gate_min_sample'),
            'gate_actions': vd.get('gate_actions'),
            'gate_capa_type': vd.get('gate_capa_type', ''),
            'gate_capa_severity': vd.get('gate_capa_severity', ''),
            'gate_approval_template': vd.get('gate_approval_template'),
        }
        # Only treat acceptance as "provided" when at least one field was sent,
        # so editing a non-receiving step's rules doesn't wipe a plan.
        acceptance = None
        if any(k in vd for k in ('aql', 'inspection_level', 'severity', 'strategy', 'variables_characteristic')):
            acceptance = {
                'aql': vd.get('aql'),
                'inspection_level': vd.get('inspection_level', ''),
                'severity': vd.get('severity', ''),
                'strategy': vd.get('strategy', ''),
                'variables_characteristic': vd.get('variables_characteristic'),
            }

        return step.apply_sampling_rules_update(
            rules_data=vd['rules'],
            fallback_rules_data=vd.get('fallback_rules', []),
            fallback_duration=vd.get('fallback_duration'),
            tighten_after=vd.get('tighten_after'),
            gate=gate, acceptance=acceptance, user=user,
            supplier=str(vd['supplier']) if vd.get('supplier') else None)


class StepSamplingRulesWriteSerializer(serializers.Serializer):
    """Write serializer for step sampling rules"""
    rules = SamplingRuleWriteSerializer(many=True)
    fallback_rules = SamplingRuleWriteSerializer(many=True, required=False)
    fallback_duration = serializers.IntegerField(required=False)
    tighten_after = serializers.IntegerField(
        required=False, allow_null=True,
        help_text="Consecutive failures before tightening to the fallback ruleset "
                  "(sets a CONSECUTIVE_FAILS + TIGHTEN_SAMPLING gate).")

    def save(self, step: Steps):
        """Use the model method for applying sampling rules"""
        user = self.context["request"].user

        rules = self.validated_data["rules"]
        fallback_data = self.validated_data.get("fallback_rules", [])
        duration = self.validated_data.get("fallback_duration")

        return step.apply_sampling_rules_update(rules_data=rules, fallback_rules_data=fallback_data,
                                                fallback_duration=duration,
                                                tighten_after=self.validated_data.get("tighten_after"),
                                                user=user)


class StepSamplingRulesResponseSerializer(serializers.Serializer):
    """Response serializer for sampling rules updates"""
    detail = serializers.CharField()
    ruleset_id = serializers.UUIDField()
    step_id = serializers.UUIDField()


# ===== SAMPLING ANALYTICS SERIALIZERS =====

class SamplingAnalyticsSerializer(SecureModelMixin):
    """Enhanced sampling analytics serializer using model properties"""
    ruleset_info = serializers.SerializerMethodField()
    work_order_info = serializers.SerializerMethodField()
    effectiveness = serializers.FloatField(source='sampling_effectiveness', read_only=True)
    is_compliant = serializers.BooleanField(read_only=True)

    # Legacy compatibility fields
    ruleset_name = serializers.CharField(source="ruleset.name", read_only=True)
    work_order_erp = serializers.CharField(source="work_order.ERP_id", read_only=True)
    sampling_effectiveness = serializers.FloatField(read_only=True)

    class Meta:
        model = SamplingAnalytics
        fields = ('id', 'parts_sampled', 'parts_total', 'defects_found', 'actual_sampling_rate', 'target_sampling_rate',
                  'variance', 'effectiveness', 'is_compliant', 'ruleset', 'ruleset_info', 'work_order',
                  'work_order_info', 'created_at', 'ruleset_name', 'work_order_erp',
                  'sampling_effectiveness', 'archived')
        read_only_fields = (
            'created_at', 'effectiveness', 'is_compliant', 'ruleset_info', 'work_order_info',
            'ruleset_name', 'work_order_erp', 'sampling_effectiveness')

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_ruleset_info(self, obj):
        if obj.ruleset:
            return {'id': obj.ruleset.id, 'name': obj.ruleset.name, 'version': obj.ruleset.version}
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_work_order_info(self, obj):
        if obj.work_order:
            return {'id': obj.work_order.id, 'ERP_id': obj.work_order.ERP_id, 'status': obj.work_order.workorder_status}
        return {}


class SamplingAuditLogSerializer(serializers.ModelSerializer):
    """Sampling audit log serializer"""
    part_erp_id = serializers.CharField(source="part.ERP_id", read_only=True)
    rule_type = serializers.CharField(source="rule.rule_type", read_only=True)
    work_order_erp = serializers.CharField(source="part.work_order.ERP_id", read_only=True)

    class Meta:
        model = SamplingAuditLog
        fields = ["id", "part", "part_erp_id", "rule", "rule_type", "hash_input", "hash_output", "sampling_decision",
                  "timestamp", "ruleset_type", "work_order_erp"]
        read_only_fields = ["id", "timestamp"]


class SamplingTriggerStateSerializer(SecureModelMixin):
    """Sampling trigger state serializer"""
    ruleset_name = serializers.CharField(source="ruleset.name", read_only=True)
    work_order_erp = serializers.CharField(source="work_order.ERP_id", read_only=True)
    step_name = serializers.CharField(source="step.name", read_only=True)
    triggered_by_status = serializers.CharField(source="triggered_by.status", read_only=True)

    class Meta:
        model = SamplingTriggerState
        fields = ["id", "ruleset", "ruleset_name", "work_order", "work_order_erp", "step", "step_name", "active",
                  "triggered_by", "triggered_by_status", "triggered_at", "success_count", "fail_count",
                  "parts_inspected"]
        read_only_fields = ["id", "triggered_at"]


# Legacy NotificationScheduleSerializer + NotificationPreferenceSerializer
# removed. The only consumer was `NotificationPreferenceViewSet` (also
# removed); the customer-facing weekly setup now uses the
# `NotificationSchedule` system via per-scope serializers in
# `Tracker.serializers.notification_schedule`.


class QuarantineDispositionSerializer(SecureModelMixin):
    disposition_number = serializers.CharField(read_only=True)
    assignee_name = serializers.SerializerMethodField()
    choices_data = serializers.SerializerMethodField()
    resolution_completed_by_name = serializers.SerializerMethodField()
    step_info = serializers.SerializerMethodField()
    rework_limit_exceeded = serializers.SerializerMethodField()
    annotation_status = serializers.SerializerMethodField()
    can_be_completed = serializers.SerializerMethodField()
    completion_blockers = serializers.SerializerMethodField()
    # Phase 1 enhancement fields
    severity_display = serializers.SerializerMethodField()
    containment_completed_by_name = serializers.SerializerMethodField()
    scrap_verified_by_name = serializers.SerializerMethodField()
    work_order_id = serializers.SerializerMethodField()
    work_order_erp_id = serializers.SerializerMethodField()

    class Meta:
        model = QuarantineDisposition
        fields = (
            # Core fields
            'id', 'disposition_number', 'current_state', 'disposition_type', 'severity', 'severity_display',
            'assigned_to', 'due_date', 'description', 'resolution_notes',
            # Resolution tracking
            'resolution_completed', 'resolution_completed_by', 'resolution_completed_by_name',
            'resolution_completed_at',
            # Containment tracking
            'containment_action', 'containment_completed_at', 'containment_completed_by',
            'containment_completed_by_name',
            # Customer approval tracking
            'requires_customer_approval', 'customer_approval_received',
            'customer_approval_reference', 'customer_approval_date',
            # Scrap verification (Phase 2 UI, but fields included)
            'scrap_verified', 'scrap_verification_method', 'scrap_verified_by',
            'scrap_verified_by_name', 'scrap_verified_at',
            # Relationships
            'part', 'batch_execution', 'step', 'step_info', 'rework_attempt_at_step',
            'rework_limit_exceeded', 'quality_reports',
            # WO denormalization (for frontend exception → WO linking)
            'work_order_id', 'work_order_erp_id',
            # Computed
            'assignee_name', 'choices_data', 'annotation_status',
            'can_be_completed', 'completion_blockers',
            'archived',
        )

        read_only_fields = (
            'disposition_number', 'assignee_name', 'choices_data', 'step_info', 'rework_limit_exceeded',
            'annotation_status', 'can_be_completed', 'completion_blockers',
            'severity_display', 'containment_completed_by_name', 'scrap_verified_by_name',
            'work_order_id', 'work_order_erp_id',
        )

    @extend_schema_field(serializers.CharField(allow_null=True))
    def _work_order(self, obj):
        # Part dispositions carry the WO through the part; batch dispositions
        # (part is null) carry it through the batch execution.
        if obj.part_id and getattr(obj.part, 'work_order_id', None):
            return obj.part.work_order
        if obj.batch_execution_id:
            return obj.batch_execution.work_order
        return None

    @extend_schema_field(serializers.UUIDField(allow_null=True))
    def get_work_order_id(self, obj):
        wo = self._work_order(obj)
        return str(wo.id) if wo else None

    def get_work_order_erp_id(self, obj):
        wo = self._work_order(obj)
        return wo.ERP_id if wo else None

    def create(self, validated_data):
        instance = super().create(validated_data)
        self._route_if_rework(instance)
        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        self._route_if_rework(instance)
        return instance

    def _route_if_rework(self, instance):
        """2b (lifecycle Y): when QA's decision is REWORK/REPAIR, route the part to
        its in-process rework step now — it's split off the lot and moved there.
        The disposition stays IN_PROGRESS until the rework is re-inspected (2e
        closes it then). Idempotent + best-effort: a routing failure (e.g. the
        rework step lacks an inspection substep, per 2d) must not fail the save —
        the part stays REWORK_NEEDED for manual routing via the control page."""
        if instance.disposition_type not in ('REWORK', 'REPAIR'):
            return
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user is None:
            return
        from Tracker.services.qms.disposition import route_part_to_rework_if_needed
        try:
            route_part_to_rework_if_needed(instance, user)
        except Exception:
            logger.exception("Rework routing failed for disposition %s", instance.pk)

    @extend_schema_field(serializers.CharField())
    def get_assignee_name(self, obj):
        """Get formatted full name or fallback to username"""
        if obj.assigned_to:
            return f"{obj.assigned_to.first_name} {obj.assigned_to.last_name}".strip() or obj.assigned_to.username
        else:
            return ""

    @extend_schema_field(serializers.CharField())
    def get_resolution_completed_by_name(self, obj):
        return obj.resolution_completed_by.display_name if obj.resolution_completed_by else ""

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_choices_data(self, obj):
        return {
            'state_choices': QuarantineDisposition.STATE_CHOICES,
            'disposition_type_choices': QuarantineDisposition.DISPOSITION_TYPES,
            'severity_choices': QuarantineDisposition.SEVERITY_CHOICES,
        }

    @extend_schema_field(serializers.CharField())
    def get_severity_display(self, obj):
        """Get human-readable severity label"""
        return obj.get_severity_display() if obj.severity else ""

    @extend_schema_field(serializers.CharField())
    def get_containment_completed_by_name(self, obj):
        """Get name of user who completed containment action"""
        return obj.containment_completed_by.display_name if obj.containment_completed_by else ""

    @extend_schema_field(serializers.CharField())
    def get_scrap_verified_by_name(self, obj):
        """Get name of user who verified scrap"""
        return obj.scrap_verified_by.display_name if obj.scrap_verified_by else ""

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_step_info(self, obj):
        if obj.step:
            return {'id': obj.step.id, 'name': obj.step.name, 'description': obj.step.description}
        return None

    @extend_schema_field(serializers.BooleanField())
    def get_rework_limit_exceeded(self, obj):
        """Check if rework limit is exceeded for this step"""
        return obj.check_rework_limit_exceeded()

    @extend_schema_field(serializers.DictField())
    def get_annotation_status(self, obj):
        """Get 3D annotation status for this disposition"""
        has_pending, pending_reports = obj.has_pending_annotations()
        return {
            'has_pending': has_pending,
            'pending_count': len(pending_reports),
            'pending_report_ids': pending_reports,
        }

    @extend_schema_field(serializers.BooleanField())
    def get_can_be_completed(self, obj):
        """Check if disposition can be completed/closed"""
        return obj.can_be_completed()

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_completion_blockers(self, obj):
        """Get list of reasons preventing completion"""
        return obj.get_completion_blockers()


# ===== SUPPLIER QUALIFICATION (ASL) =====

class SupplierQualificationSerializer(SecureModelMixin):
    qualification_number = serializers.CharField(read_only=True)
    supplier = TenantScopedPrimaryKeyRelatedField(queryset=Companies.unscoped.all())
    part_type = TenantScopedPrimaryKeyRelatedField(
        queryset=PartTypes.unscoped.all(), required=False, allow_null=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    scope_display = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = SupplierQualification
        fields = (
            'id', 'qualification_number', 'supplier', 'supplier_name',
            'scope_type', 'part_type', 'scope_label', 'scope_display',
            'status', 'status_display', 'basis', 'effective_date', 'expiry_date',
            'approval_request', 'qualified_by', 'notes',
            'created_at', 'updated_at', 'archived',
        )
        read_only_fields = (
            'qualification_number', 'status', 'approval_request', 'qualified_by',
            'created_at', 'updated_at',
        )


class QualificationStatusSerializer(serializers.Serializer):
    """Resolved supplier standing for a scope (the `status` action response)."""
    qualified = serializers.BooleanField()
    status = serializers.CharField(allow_null=True)
    basis = serializers.CharField(allow_null=True)
    expiry_date = serializers.DateField(allow_null=True)
    days_to_expiry = serializers.IntegerField(allow_null=True)
    record_id = serializers.CharField(allow_null=True)


# ===== PART APPROVAL (PPAP / FAI) =====

class PartApprovalSerializer(SecureModelMixin):
    approval_number = serializers.CharField(read_only=True)
    part_type = TenantScopedPrimaryKeyRelatedField(queryset=PartTypes.unscoped.all())
    supplier = TenantScopedPrimaryKeyRelatedField(queryset=Companies.unscoped.all())
    part_type_name = serializers.CharField(source='part_type.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    approval_type_display = serializers.CharField(source='get_approval_type_display', read_only=True)

    class Meta:
        model = PartApproval
        fields = (
            'id', 'approval_number', 'part_type', 'part_type_name',
            'supplier', 'supplier_name',
            'approval_type', 'approval_type_display', 'reference',
            'status', 'status_display', 'effective_date', 'expiry_date',
            'approval_request', 'approved_by', 'notes',
            'created_at', 'updated_at', 'archived',
        )
        read_only_fields = (
            'approval_number', 'status', 'approval_request', 'approved_by',
            'created_at', 'updated_at',
        )


class PartApprovalStatusSerializer(serializers.Serializer):
    """Resolved (part_type, supplier) approval standing (the `status` action response)."""
    approved = serializers.BooleanField()
    status = serializers.CharField(allow_null=True)
    approval_type = serializers.CharField(allow_null=True)
    expiry_date = serializers.DateField(allow_null=True)
    days_to_expiry = serializers.IntegerField(allow_null=True)
    record_id = serializers.CharField(allow_null=True)


# ===== CAPA SERIALIZERS =====

class RootCauseSerializer(SecureModelMixin):
    """Root cause serializer"""
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    rca_record_info = serializers.SerializerMethodField()

    class Meta:
        model = RootCause
        fields = (
            'id', 'rca_record', 'rca_record_info',
            'description', 'category', 'category_display',
            'role', 'role_display', 'sequence',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = ('created_at', 'updated_at')

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_rca_record_info(self, obj):
        if obj.rca_record:
            return {
                'id': obj.rca_record.id,
                'rca_method': obj.rca_record.rca_method,
                'capa_number': obj.rca_record.capa.capa_number if obj.rca_record.capa else None
            }
        return None


class FiveWhysSerializer(SecureModelMixin):
    """5 Whys RCA serializer"""
    rca_record_info = serializers.SerializerMethodField()

    class Meta:
        model = FiveWhys
        fields = (
            'id', 'rca_record', 'rca_record_info',
            'why_1_question', 'why_1_answer',
            'why_2_question', 'why_2_answer',
            'why_3_question', 'why_3_answer',
            'why_4_question', 'why_4_answer',
            'why_5_question', 'why_5_answer',
            'identified_root_cause',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = ('created_at', 'updated_at')

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_rca_record_info(self, obj):
        if obj.rca_record:
            return {
                'id': obj.rca_record.id,
                'capa_number': obj.rca_record.capa.capa_number if obj.rca_record.capa else None
            }
        return None


class FishboneSerializer(SecureModelMixin):
    """Fishbone diagram RCA serializer"""
    rca_record_info = serializers.SerializerMethodField()

    class Meta:
        model = Fishbone
        fields = (
            'id', 'rca_record', 'rca_record_info',
            'problem_statement',
            'man_causes', 'machine_causes', 'material_causes',
            'method_causes', 'measurement_causes', 'environment_causes',
            'identified_root_cause',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = ('created_at', 'updated_at')

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_rca_record_info(self, obj):
        if obj.rca_record:
            return {
                'id': obj.rca_record.id,
                'capa_number': obj.rca_record.capa.capa_number if obj.rca_record.capa else None
            }
        return None


class FiveWhysNestedSerializer(serializers.ModelSerializer):
    """Nested writable serializer for 5 Whys (used in RcaRecord create/update)"""
    class Meta:
        model = FiveWhys
        fields = (
            'why_1_question', 'why_1_answer',
            'why_2_question', 'why_2_answer',
            'why_3_question', 'why_3_answer',
            'why_4_question', 'why_4_answer',
            'why_5_question', 'why_5_answer',
            'identified_root_cause',
        )
        extra_kwargs = {
            'why_1_question': {'required': False, 'allow_blank': True, 'allow_null': True},
            'why_1_answer': {'required': False, 'allow_blank': True, 'allow_null': True},
            'why_2_question': {'required': False, 'allow_blank': True, 'allow_null': True},
            'why_2_answer': {'required': False, 'allow_blank': True, 'allow_null': True},
            'why_3_question': {'required': False, 'allow_blank': True, 'allow_null': True},
            'why_3_answer': {'required': False, 'allow_blank': True, 'allow_null': True},
            'why_4_question': {'required': False, 'allow_blank': True, 'allow_null': True},
            'why_4_answer': {'required': False, 'allow_blank': True, 'allow_null': True},
            'why_5_question': {'required': False, 'allow_blank': True, 'allow_null': True},
            'why_5_answer': {'required': False, 'allow_blank': True, 'allow_null': True},
            'identified_root_cause': {'required': False, 'allow_blank': True, 'allow_null': True},
        }


class FishboneNestedSerializer(serializers.ModelSerializer):
    """Nested writable serializer for Fishbone (used in RcaRecord create/update)"""
    # Accept string input for causes, will be converted to list in RcaRecordSerializer.create()
    man_causes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    machine_causes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    material_causes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    method_causes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    measurement_causes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    environment_causes = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Fishbone
        fields = (
            'problem_statement',
            'man_causes', 'machine_causes', 'material_causes',
            'method_causes', 'measurement_causes', 'environment_causes',
            'identified_root_cause',
        )
        extra_kwargs = {
            'problem_statement': {'required': False, 'allow_blank': True, 'allow_null': True},
            'identified_root_cause': {'required': False, 'allow_blank': True, 'allow_null': True},
        }


class RcaRecordSerializer(SecureModelMixin):
    """RCA record serializer"""
    rca_method_display = serializers.CharField(source='get_rca_method_display', read_only=True)
    rca_review_status_display = serializers.CharField(source='get_rca_review_status_display', read_only=True)
    root_cause_verification_status_display = serializers.CharField(source='get_root_cause_verification_status_display', read_only=True)
    capa_info = serializers.SerializerMethodField()
    conducted_by_info = serializers.SerializerMethodField()
    root_cause_verified_by_info = serializers.SerializerMethodField()
    root_causes = RootCauseSerializer(many=True, read_only=True)
    five_whys = FiveWhysSerializer(read_only=True, allow_null=True)
    fishbone = FishboneSerializer(read_only=True, allow_null=True)
    # Writable nested fields for create/update
    five_whys_data = FiveWhysNestedSerializer(write_only=True, required=False)
    fishbone_data = FishboneNestedSerializer(write_only=True, required=False)

    class Meta:
        model = RcaRecord
        fields = (
            'id', 'capa', 'capa_info', 'rca_method', 'rca_method_display',
            'problem_description', 'root_cause_summary',
            'conducted_by', 'conducted_by_info', 'conducted_date',
            'rca_review_status', 'rca_review_status_display',
            'root_cause_verification_status', 'root_cause_verification_status_display',
            'root_cause_verified_at', 'root_cause_verified_by', 'root_cause_verified_by_info',
            'self_verified',
            'quality_reports', 'dispositions',
            'root_causes', 'five_whys', 'fishbone',
            'five_whys_data', 'fishbone_data',  # write-only fields
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = ('root_cause_verified_at', 'created_at', 'updated_at', 'self_verified')

    # Fishbone cause fields that arrive as strings and get split into lists.
    _FISHBONE_CAUSE_FIELDS = (
        'man_causes', 'machine_causes', 'material_causes',
        'method_causes', 'measurement_causes', 'environment_causes',
    )

    def _normalize_fishbone_causes(self, fishbone_data):
        """Input shape: cause fields arrive as newline/comma-separated strings.
        Storage shape: JSONField lists. Split here so the service receives
        already-normalized data."""
        if not fishbone_data:
            return fishbone_data
        for field in self._FISHBONE_CAUSE_FIELDS:
            causes_str = fishbone_data.get(field)
            if causes_str:
                fishbone_data[field] = [
                    c.strip()
                    for c in causes_str.replace('\n', ',').split(',')
                    if c.strip()
                ]
            else:
                fishbone_data[field] = []
        return fishbone_data

    def create(self, validated_data):
        from Tracker.services.qms.rca import create_rca_record
        five_whys_data = validated_data.pop('five_whys_data', None)
        fishbone_data = self._normalize_fishbone_causes(
            validated_data.pop('fishbone_data', None)
        )
        return create_rca_record(
            validated_data,
            five_whys_data=five_whys_data,
            fishbone_data=fishbone_data,
        )

    def update(self, instance, validated_data):
        from Tracker.services.qms.rca import update_rca_record
        five_whys_data = validated_data.pop('five_whys_data', None)
        fishbone_data = self._normalize_fishbone_causes(
            validated_data.pop('fishbone_data', None)
        )
        return update_rca_record(
            instance,
            validated_data,
            five_whys_data=five_whys_data,
            fishbone_data=fishbone_data,
        )

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_capa_info(self, obj):
        if obj.capa:
            return {
                'id': obj.capa.id,
                'capa_number': obj.capa.capa_number,
                'problem_statement': obj.capa.problem_statement
            }
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_conducted_by_info(self, obj):
        if obj.conducted_by:
            from .core import UserSelectSerializer
            return UserSelectSerializer(obj.conducted_by).data
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_root_cause_verified_by_info(self, obj):
        if obj.root_cause_verified_by:
            from .core import UserSelectSerializer
            return UserSelectSerializer(obj.root_cause_verified_by).data
        return None


class CapaTaskAssigneeSerializer(SecureModelMixin):
    """CAPA task assignee serializer"""
    user_info = serializers.SerializerMethodField()
    task_info = serializers.SerializerMethodField()

    class Meta:
        model = CapaTaskAssignee
        fields = (
            'id', 'task', 'task_info', 'user', 'user_info',
            'status', 'completed_at', 'completion_notes',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = ('completed_at', 'created_at', 'updated_at')

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_user_info(self, obj):
        if obj.user:
            from .core import UserSelectSerializer
            return UserSelectSerializer(obj.user).data
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_task_info(self, obj):
        if obj.task:
            return {
                'id': obj.task.id,
                'task_number': obj.task.task_number,
                'description': obj.task.description
            }
        return None


class CapaTasksSerializer(SecureModelMixin):
    """CAPA tasks serializer"""
    task_number = serializers.CharField(read_only=True)
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    completion_mode_display = serializers.CharField(source='get_completion_mode_display', read_only=True)
    capa_info = serializers.SerializerMethodField()
    assigned_to_info = serializers.SerializerMethodField()
    completed_by_info = serializers.SerializerMethodField()
    assignees = CapaTaskAssigneeSerializer(many=True, read_only=True)
    is_overdue = serializers.SerializerMethodField()
    documents_info = serializers.SerializerMethodField()

    class Meta:
        model = CapaTasks
        fields = (
            'id', 'task_number', 'capa', 'capa_info',
            'task_type', 'task_type_display', 'description',
            'assigned_to', 'assigned_to_info', 'assignees',
            'completion_mode', 'completion_mode_display',
            'due_date', 'requires_signature', 'status', 'status_display',
            'completed_by', 'completed_by_info', 'completed_date', 'completion_notes', 'completion_signature',
            'is_overdue', 'documents_info', 'created_at', 'updated_at', 'archived'
        )
        read_only_fields = ('task_number', 'completed_date', 'completed_by', 'completion_signature', 'created_at', 'updated_at')

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_capa_info(self, obj):
        if obj.capa:
            return {
                'id': obj.capa.id,
                'capa_number': obj.capa.capa_number,
                'problem_statement': obj.capa.problem_statement
            }
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_assigned_to_info(self, obj):
        if obj.assigned_to:
            from .core import UserSelectSerializer
            return UserSelectSerializer(obj.assigned_to).data
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_completed_by_info(self, obj):
        if obj.completed_by:
            from .core import UserSelectSerializer
            return UserSelectSerializer(obj.completed_by).data
        return None

    @extend_schema_field(serializers.BooleanField())
    def get_is_overdue(self, obj):
        """Check if task is overdue"""
        from django.utils import timezone
        if not obj.due_date:
            return False
        if obj.status == 'COMPLETED':
            return False
        return obj.due_date < timezone.now().date()

    @extend_schema_field(serializers.DictField())
    def get_documents_info(self, obj):
        """Get summary of attached documents (primary GFK + secondary links)."""
        from Tracker.services.core.documents import documents_attached_to
        docs = documents_attached_to(obj)
        return {
            'count': docs.count(),
            'items': [
                {
                    'id': doc.id,
                    'file_name': doc.file_name,
                    'file_url': doc.file.url if doc.file else None,
                    'upload_date': doc.upload_date.isoformat() if doc.upload_date else None,
                }
                for doc in docs[:5]  # Limit to first 5 for list views
            ]
        }


class CapaVerificationSerializer(SecureModelMixin):
    """CAPA verification serializer"""
    effectiveness_result_display = serializers.CharField(source='get_effectiveness_result_display', read_only=True)
    capa_info = serializers.SerializerMethodField()
    verified_by_info = serializers.SerializerMethodField()

    class Meta:
        model = CapaVerification
        fields = (
            'id', 'capa', 'capa_info',
            'verification_method', 'verification_criteria', 'verification_date',
            'verified_by', 'verified_by_info',
            'effectiveness_result', 'effectiveness_result_display',
            'effectiveness_decided_at', 'verification_notes',
            'self_verified',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = ('effectiveness_decided_at', 'created_at', 'updated_at', 'self_verified')

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_capa_info(self, obj):
        if obj.capa:
            return {
                'id': obj.capa.id,
                'capa_number': obj.capa.capa_number,
                'problem_statement': obj.capa.problem_statement
            }
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_verified_by_info(self, obj):
        if obj.verified_by:
            from .core import UserSelectSerializer
            return UserSelectSerializer(obj.verified_by).data
        return None


class CAPASerializer(SecureModelMixin):
    """CAPA main serializer"""
    capa_number = serializers.CharField(read_only=True)
    capa_type_display = serializers.CharField(source='get_capa_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    status = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    approval_status_display = serializers.CharField(source='get_approval_status_display', read_only=True)
    initiated_by_info = serializers.SerializerMethodField()
    assigned_to_info = serializers.SerializerMethodField()
    verified_by_info = serializers.SerializerMethodField()
    approved_by_info = serializers.SerializerMethodField()
    tasks = CapaTasksSerializer(many=True, read_only=True)
    rca_records = RcaRecordSerializer(many=True, read_only=True)
    verifications = CapaVerificationSerializer(many=True, read_only=True)
    completion_percentage = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    blocking_items = serializers.SerializerMethodField()
    work_order_ids = serializers.SerializerMethodField()

    class Meta:
        model = CAPA
        fields = (
            'id', 'capa_number', 'capa_type', 'capa_type_display',
            'severity', 'severity_display', 'status', 'status_display',
            'problem_statement', 'immediate_action',
            'initiated_by', 'initiated_by_info', 'initiated_date',
            'assigned_to', 'assigned_to_info',
            'due_date', 'completed_date',
            'verified_by', 'verified_by_info',
            'approval_required', 'approval_status', 'approval_status_display',
            'approved_by', 'approved_by_info', 'approved_at',
            'allow_self_verification',
            'part', 'step', 'work_order',
            'quality_reports', 'dispositions',
            'tasks', 'rca_records', 'verifications',
            'completion_percentage', 'is_overdue', 'blocking_items',
            'work_order_ids',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = (
            'capa_number', 'status', 'status_display', 'completed_date',
            'approval_required', 'approved_by', 'approved_at', 'approval_status_display',
            'completion_percentage', 'is_overdue', 'blocking_items', 'work_order_ids',
            'created_at', 'updated_at', 'archived'
        )

    @extend_schema_field(serializers.ListField(child=serializers.UUIDField()))
    def get_work_order_ids(self, obj):
        """Collect all WO ids linked via capa.work_order, capa.part, dispositions.part, quality_reports.part."""
        wo_ids: set = set()
        if obj.work_order_id:
            wo_ids.add(obj.work_order_id)
        if obj.part_id and getattr(obj.part, 'work_order_id', None):
            wo_ids.add(obj.part.work_order_id)
        for d in obj.dispositions.all():
            if d.part_id and getattr(d.part, 'work_order_id', None):
                wo_ids.add(d.part.work_order_id)
        for qr in obj.quality_reports.all():
            if qr.part_id and getattr(qr.part, 'work_order_id', None):
                wo_ids.add(qr.part.work_order_id)
        return list(wo_ids)

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_initiated_by_info(self, obj):
        if obj.initiated_by:
            from .core import UserSelectSerializer
            return UserSelectSerializer(obj.initiated_by).data
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_assigned_to_info(self, obj):
        if obj.assigned_to:
            from .core import UserSelectSerializer
            return UserSelectSerializer(obj.assigned_to).data
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_verified_by_info(self, obj):
        if obj.verified_by:
            from .core import UserSelectSerializer
            return UserSelectSerializer(obj.verified_by).data
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_approved_by_info(self, obj):
        if obj.approved_by:
            from .core import UserSelectSerializer
            return UserSelectSerializer(obj.approved_by).data
        return None

    @extend_schema_field(serializers.FloatField())
    def get_completion_percentage(self, obj):
        """Get completion percentage from model method"""
        return obj.calculate_completion_percentage()

    @extend_schema_field(serializers.BooleanField())
    def get_is_overdue(self, obj):
        """Check if CAPA is overdue"""
        return obj.is_overdue()

    @extend_schema_field(serializers.ListField())
    def get_blocking_items(self, obj):
        """Get list of blocking items preventing closure"""
        return obj.get_blocking_items()

    @extend_schema_field(serializers.CharField())
    def get_status(self, obj):
        """Return computed status from model property"""
        return obj.computed_status

    @extend_schema_field(serializers.CharField())
    def get_status_display(self, obj):
        """Return display name for computed status"""
        from Tracker.models.qms import CapaStatus
        status_displays = dict(CapaStatus.choices)
        return status_displays.get(obj.computed_status, obj.computed_status)


class StepOverrideSerializer(SecureModelMixin):
    """Serializer for step override requests."""
    from Tracker.models import StepOverride

    block_type_display = serializers.CharField(source='get_block_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    requested_by_info = serializers.SerializerMethodField()
    approved_by_info = serializers.SerializerMethodField()
    step_execution_info = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()

    class Meta:
        from Tracker.models import StepOverride
        model = StepOverride
        fields = (
            'id',
            'step_execution', 'step_execution_info',
            'block_type', 'block_type_display',
            'requested_by', 'requested_by_info',
            'requested_at',
            'reason',
            'approved_by', 'approved_by_info',
            'approved_at',
            'status', 'status_display',
            'expires_at', 'is_expired',
            'used', 'used_at',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = (
            'requested_at', 'approved_at', 'used_at',
            'created_at', 'updated_at'
        )

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_requested_by_info(self, obj):
        if obj.requested_by:
            from .core import UserSelectSerializer
            return UserSelectSerializer(obj.requested_by).data
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_approved_by_info(self, obj):
        if obj.approved_by:
            from .core import UserSelectSerializer
            return UserSelectSerializer(obj.approved_by).data
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_step_execution_info(self, obj):
        if obj.step_execution:
            return {
                'id': str(obj.step_execution.id),
                'part_id': str(obj.step_execution.part_id) if obj.step_execution.part_id else None,
                'part_erp_id': obj.step_execution.part.ERP_id if obj.step_execution.part else None,
                'step_name': obj.step_execution.step.name if obj.step_execution.step else None,
                'status': obj.step_execution.status,
            }
        return None

    @extend_schema_field(serializers.BooleanField())
    def get_is_expired(self, obj):
        """Check if override has expired."""
        from django.utils import timezone
        if not obj.expires_at:
            return False
        return obj.expires_at < timezone.now()


class FPIRecordSerializer(SecureModelMixin):
    """Serializer for First Piece Inspection records."""
    from Tracker.models import FPIRecord

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    # Explicit so the schema carries allow_blank: the model field is blank=True
    # ("" = undecided, PENDING records) — without this the generated client's
    # strict enum rejects every pending FPI at runtime.
    result = serializers.ChoiceField(
        choices=FPIRecord._meta.get_field('result').choices,
        allow_blank=True, read_only=True,
    )
    result_display = serializers.CharField(source='get_result_display', read_only=True)
    work_order_info = serializers.SerializerMethodField()
    step_info = serializers.SerializerMethodField()
    part_type_info = serializers.SerializerMethodField()
    designated_part_info = serializers.SerializerMethodField()
    inspected_by_info = serializers.SerializerMethodField()
    waived_by_info = serializers.SerializerMethodField()
    acknowledged_by_info = serializers.SerializerMethodField()
    equipment_info = serializers.SerializerMethodField()

    class Meta:
        from Tracker.models import FPIRecord
        model = FPIRecord
        fields = (
            'id',
            'work_order', 'work_order_info',
            'step', 'step_info',
            'part_type', 'part_type_info',
            'designated_part', 'designated_part_info',
            'equipment', 'equipment_info',
            'shift_date',
            'status', 'status_display',
            'result', 'result_display',
            'inspected_by', 'inspected_by_info',
            'inspected_at',
            'waived', 'waived_by', 'waived_by_info',
            'waive_reason',
            'acknowledged_by', 'acknowledged_by_info', 'acknowledged_at',
            'quality_report',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = (
            'status', 'result', 'inspected_by', 'inspected_at',
            'waived', 'waived_by', 'waive_reason',
            'acknowledged_by', 'acknowledged_at',
            'quality_report',
            'created_at', 'updated_at'
        )

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_work_order_info(self, obj):
        if obj.work_order:
            return {
                'id': str(obj.work_order.id),
                'erp_id': obj.work_order.ERP_id,
                'status': obj.work_order.workorder_status,
            }
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_step_info(self, obj):
        if obj.step:
            return {
                'id': str(obj.step.id),
                'name': obj.step.name,
            }
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_part_type_info(self, obj):
        if obj.part_type:
            return {
                'id': str(obj.part_type.id),
                'name': obj.part_type.name,
            }
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_designated_part_info(self, obj):
        if obj.designated_part:
            return {
                'id': str(obj.designated_part.id),
                'erp_id': obj.designated_part.ERP_id,
            }
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_inspected_by_info(self, obj):
        if obj.inspected_by:
            from .core import UserSelectSerializer
            return UserSelectSerializer(obj.inspected_by).data
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_waived_by_info(self, obj):
        if obj.waived_by:
            from .core import UserSelectSerializer
            return UserSelectSerializer(obj.waived_by).data
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_acknowledged_by_info(self, obj):
        if obj.acknowledged_by:
            from .core import UserSelectSerializer
            return UserSelectSerializer(obj.acknowledged_by).data
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_equipment_info(self, obj):
        if obj.equipment:
            return {
                'id': str(obj.equipment.id),
                'name': obj.equipment.name,
            }
        return None


class StepExecutionMeasurementSerializer(SecureModelMixin):
    """Serializer for step execution measurements."""
    from Tracker.models import StepExecutionMeasurement

    step_execution_info = serializers.SerializerMethodField()
    measurement_definition_info = serializers.SerializerMethodField()
    recorded_by_info = serializers.SerializerMethodField()
    equipment_info = serializers.SerializerMethodField()
    spec_status = serializers.SerializerMethodField()

    class Meta:
        from Tracker.models import StepExecutionMeasurement
        model = StepExecutionMeasurement
        fields = (
            'id',
            'step_execution', 'step_execution_info',
            'batch_execution',  # set instead of step_execution for BATCH-scope readings
            'measurement_definition', 'measurement_definition_info',
            'value', 'string_value',
            'is_within_spec', 'spec_status',
            'recorded_by', 'recorded_by_info',
            'recorded_at',
            'equipment', 'equipment_info',
            # DWI — when this measurement was captured from a substep MeasurementInput
            'substep',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = ('is_within_spec', 'recorded_at', 'created_at', 'updated_at')

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_step_execution_info(self, obj):
        if obj.step_execution:
            return {
                'id': str(obj.step_execution.id),
                'part_id': str(obj.step_execution.part_id) if obj.step_execution.part_id else None,
                'part_erp_id': obj.step_execution.part.ERP_id if obj.step_execution.part else None,
                'step_name': obj.step_execution.step.name if obj.step_execution.step else None,
                'status': obj.step_execution.status,
            }
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_measurement_definition_info(self, obj):
        if obj.measurement_definition:
            defn = obj.measurement_definition
            return {
                'id': str(defn.id),
                'label': defn.label,
                'type': defn.type,
                'unit': defn.unit,
                'nominal': float(defn.nominal) if defn.nominal else None,
                'upper_tol': float(defn.upper_tol) if defn.upper_tol else None,
                'lower_tol': float(defn.lower_tol) if defn.lower_tol else None,
                'required': defn.required,
            }
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_recorded_by_info(self, obj):
        if obj.recorded_by:
            from .core import UserSelectSerializer
            return UserSelectSerializer(obj.recorded_by).data
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_equipment_info(self, obj):
        if obj.equipment:
            return {
                'id': str(obj.equipment.id),
                'name': obj.equipment.name,
            }
        return None

    @extend_schema_field(serializers.CharField())
    def get_spec_status(self, obj):
        """Human-readable spec status."""
        if obj.is_within_spec is None:
            return 'N/A'
        return 'PASS' if obj.is_within_spec else 'FAIL'

    def create(self, validated_data):
        """Set recorded_by from request context."""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['recorded_by'] = request.user
        return super().create(validated_data)


class StepExecutionMeasurementWriteSerializer(serializers.Serializer):
    """Lightweight serializer for recording measurements."""
    measurement_definition = serializers.UUIDField()
    value = serializers.DecimalField(max_digits=12, decimal_places=4, required=False, allow_null=True)
    string_value = serializers.CharField(max_length=100, required=False, allow_blank=True)
    equipment = serializers.UUIDField(required=False, allow_null=True)


class BulkMeasurementSerializer(serializers.Serializer):
    """Serializer for recording multiple measurements at once."""
    step_execution = serializers.UUIDField()
    measurements = StepExecutionMeasurementWriteSerializer(many=True)


# ===== RECEIVING INSPECTION (purchased material, Flow A) =====

class ReceivingMeasurementInputSerializer(serializers.Serializer):
    """One measurement captured during receiving inspection."""
    definition = serializers.UUIDField()
    value_numeric = serializers.FloatField(required=False, allow_null=True)
    value_pass_fail = serializers.ChoiceField(
        choices=[('PASS', 'Pass'), ('FAIL', 'Fail')], required=False, allow_null=True)


class RecordInspectionRequestSerializer(serializers.Serializer):
    """Request body for recording receiving-inspection measurement results."""
    measurements = ReceivingMeasurementInputSerializer(many=True)


class ReceivingSampleUnitSerializer(serializers.Serializer):
    """One sampled unit's measurements within an acceptance-sampling inspection."""
    sample_number = serializers.IntegerField(min_value=1)
    measurements = ReceivingMeasurementInputSerializer(many=True)


class RecordUnitsRequestSerializer(serializers.Serializer):
    """Request body for recording per-unit measurements across the sample."""
    units = ReceivingSampleUnitSerializer(many=True)


class RecordBulkRequestSerializer(serializers.Serializer):
    """Request body for bulk/attribute capture: defectives found across the sample."""
    defectives_found = serializers.IntegerField(min_value=0)


class ReceivingCharacteristicSerializer(serializers.Serializer):
    """A measurement definition to capture during receiving inspection."""
    id = serializers.UUIDField()
    label = serializers.CharField()
    unit = serializers.CharField(allow_blank=True)
    type = serializers.CharField()
    nominal = serializers.FloatField(allow_null=True)
    upper_tol = serializers.FloatField(allow_null=True)
    lower_tol = serializers.FloatField(allow_null=True)


class SamplePlanResponseSerializer(serializers.Serializer):
    """Response: the acceptance_sampling.SamplePlan DTO + the RECEIVING step's characteristics,
    plus the routing info the UI needs to launch a DWI run (step id, whether the step has
    substeps, and the open StepExecution for this lot if one exists)."""
    sample_size = serializers.IntegerField()
    accept_number = serializers.IntegerField()
    reject_number = serializers.IntegerField()
    strategy = serializers.CharField()
    inspection_level = serializers.CharField()
    severity = serializers.CharField()
    # Z1.9 variables: blank/null for attribute (C0/Z14) plans.
    method = serializers.CharField(allow_blank=True, required=False)
    k = serializers.FloatField(allow_null=True, required=False)
    variables_characteristic_id = serializers.UUIDField(allow_null=True, required=False)
    characteristics = ReceivingCharacteristicSerializer(many=True)
    step_id = serializers.UUIDField(allow_null=True)
    has_substeps = serializers.BooleanField()
    step_execution_id = serializers.UUIDField(allow_null=True)


class IncomingInspectionRowSerializer(serializers.Serializer):
    """One row of the unified incoming-inspection worklist — a purchased MaterialLot
    or an OutsideProcessShipment, normalized to a shared shape (SAP QM QA32-style,
    `source` = the inspection-lot origin). See services.qms.incoming_inspection."""
    source = serializers.ChoiceField(choices=["PURCHASED_LOT", "OUTSIDE_PROCESS"])
    id = serializers.UUIDField()
    reference = serializers.CharField(allow_blank=True)
    item = serializers.CharField(allow_blank=True)
    supplier = serializers.CharField(allow_blank=True)
    quantity = serializers.FloatField(allow_null=True)
    status = serializers.CharField()
    status_display = serializers.CharField()
    received_at = serializers.CharField(allow_null=True)
    step_id = serializers.UUIDField(allow_null=True)


class InspectionInboxSeveritySerializer(serializers.Serializer):
    """The severity badge on a receiving inbox row (see SamplingSeverityStateSerializer
    for the full read model)."""
    severity = serializers.ChoiceField(choices=["NORMAL", "TIGHTENED", "REDUCED"])
    severity_since = serializers.CharField(allow_null=True)
    discontinued = serializers.BooleanField()
    rejects_in_window = serializers.IntegerField()
    next_severity_on_accepts = serializers.CharField()
    accepts_needed = serializers.IntegerField(allow_null=True)


# Named for ENUM_NAME_OVERRIDES — a bare "type" field otherwise collides with
# MeasurementDefinition.type and renames the long-exported TypeEnum.
INSPECTION_INBOX_TYPES = ["fpi", "receiving", "outside_process", "in_process"]


class InspectionInboxRowSerializer(serializers.Serializer):
    """One row of the inspector's task inbox — flat across every inspection
    source, never grouped by work order. See services.qms.inspection_inbox."""
    type = serializers.ChoiceField(choices=INSPECTION_INBOX_TYPES)
    subject_kind = serializers.ChoiceField(choices=["fpi_record", "material_lot", "shipment", "operation"])
    id = serializers.CharField()
    title = serializers.CharField(allow_blank=True)
    detail = serializers.CharField(allow_blank=True)
    wo = serializers.CharField(allow_null=True)
    quantity = serializers.FloatField(allow_null=True)
    age_hours = serializers.FloatField(allow_null=True)
    due_tone = serializers.ChoiceField(choices=["red", "orange", "green", "gray"])
    due_label = serializers.CharField(allow_blank=True)
    plan = serializers.CharField(allow_null=True)
    severity = InspectionInboxSeveritySerializer(allow_null=True)
    resume = serializers.CharField(allow_null=True)
    blocked_reason = serializers.CharField(allow_null=True)


class MaterialLotBulkRowSerializer(serializers.Serializer):
    """One row of a bulk lot-receive (paste-grid)."""
    lot_number = serializers.CharField(max_length=100)
    received_date = serializers.DateField()
    material_type = TenantScopedPrimaryKeyRelatedField(
        queryset=PartTypes.unscoped.all(), required=False, allow_null=True)
    material_description = serializers.CharField(max_length=200, required=False, allow_blank=True)
    supplier = TenantScopedPrimaryKeyRelatedField(
        queryset=Companies.unscoped.all(), required=False, allow_null=True)
    supplier_lot_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    erp_po_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    promised_date = serializers.DateField(required=False, allow_null=True)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=4)
    unit_of_measure = serializers.CharField(max_length=20, required=False, allow_blank=True)
    manufacture_date = serializers.DateField(required=False, allow_null=True)
    expiration_date = serializers.DateField(required=False, allow_null=True)
    storage_location = serializers.CharField(max_length=100, required=False, allow_blank=True)


class MaterialLotBulkCreateSerializer(serializers.Serializer):
    """Bulk lot-receive payload for the paste-grid screen."""
    lots = MaterialLotBulkRowSerializer(many=True)
