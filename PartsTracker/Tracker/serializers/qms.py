# serializers/qms.py - Quality Management System serializers
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from Tracker.models import (
    # QMS models
    QualityErrorsList, MeasurementResult, QualityReports,
    QuarantineDisposition,
    # CAPA models
    CAPA, CapaTasks, CapaTaskAssignee, RcaRecord, FiveWhys, Fishbone, RootCause, CapaVerification,
    # CAPA enums
    CapaType, CapaSeverity, CapaStatus, CapaTaskType, CapaTaskStatus,
    RcaMethod, RootCauseCategory, EffectivenessResult,
    # MES Lite models
    MeasurementDefinition, Steps, WorkOrder,
    # MES Standard models
    SamplingRule, SamplingRuleSet, SamplingRuleType, SamplingAnalytics,
    SamplingAuditLog, SamplingTriggerState,
    # Core models
    NotificationTask,
)

from .core import SecureModelMixin


# ===== QUALITY AND ERROR SERIALIZERS =====

class QualityErrorsListSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Quality errors list serializer"""
    part_type_name = serializers.CharField(source="part_type.name", read_only=True)

    class Meta:
        model = QualityErrorsList
        fields = ["id", "error_name", "error_example", "part_type", "part_type_name", "requires_3d_annotation", "archived"]


class ErrorTypeSerializer(serializers.ModelSerializer):
    """Legacy error type serializer"""
    part_type_name = serializers.CharField(source="part_type.name", read_only=True)

    class Meta:
        model = QualityErrorsList
        fields = ["id", "error_name", "error_example", "part_type", "part_type_name", "requires_3d_annotation", "archived"]


# ===== MEASUREMENT SERIALIZERS =====

class MeasurementDefinitionSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Measurement definition serializer"""
    step_name = serializers.SerializerMethodField()

    class Meta:
        model = MeasurementDefinition
        fields = ["id", "label", "step_name", "unit", "nominal", "upper_tol", "lower_tol", "required", "type", "step", "archived"]
        read_only_fields = ["id", "step"]

    @extend_schema_field(serializers.CharField())
    def get_step_name(self, obj) -> str | None:
        return obj.step.name if obj.step else None


class MeasurementResultSerializer(serializers.ModelSerializer, SecureModelMixin):
    report = serializers.CharField(read_only=True)
    is_within_spec = serializers.BooleanField(read_only=True)
    created_by = serializers.IntegerField(read_only=True)

    class Meta:
        model = MeasurementResult
        fields = ["report", "definition", "value_numeric", "value_pass_fail", "is_within_spec", "created_by", "archived"]


# ===== QUALITY REPORTS SERIALIZERS =====

class QualityReportsSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Quality reports serializer"""
    measurements = MeasurementResultSerializer(many=True, write_only=True)

    # Display fields for related models
    part_info = serializers.SerializerMethodField()
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
                  "part_info", "step_info", "machine_info", "operators_info", "errors_info", "file_info", "archived"]
        read_only_fields = ("report_number", "created_at")

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
        measurements_data = validated_data.pop("measurements", [])
        report = super().create(validated_data)

        for m in measurements_data:
            MeasurementResult.objects.create(report=report, definition_id=m['definition'].id,
                                             value_numeric=m.get('value_numeric'),
                                             value_pass_fail=m.get('value_pass_fail'),
                                             created_by=self.context["request"].user)

        return report


# ===== SAMPLING RULE SERIALIZERS =====

class SamplingRuleSerializer(serializers.ModelSerializer, SecureModelMixin):
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

class SamplingRuleSetSerializer(serializers.ModelSerializer, SecureModelMixin):
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
        fields = ('id', 'name', 'origin', 'active', 'version', 'is_fallback', 'fallback_threshold', 'fallback_duration',
                  'part_type', 'part_type_info', 'process', 'process_info', 'step', 'step_info', 'rules',
                  'created_by', 'created_at', 'modified_by', 'updated_at', 'part_type_name', 'process_name', 'archived')
        read_only_fields = (
            'created_at', 'updated_at', 'rules', 'part_type_info', 'process_info', 'step_info',
            'part_type_name', 'process_name')

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
        fields = ["id", "name", "rules", "fallback_threshold", "fallback_duration"]


class StepWithResolvedRulesSerializer(serializers.ModelSerializer):
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

    def get_part_type_info(self, obj):
        """Return basic part type info"""
        if obj.part_type:
            return {"id": obj.part_type.id, "name": obj.part_type.name}
        return {}

    @extend_schema_field(ResolvedSamplingRuleSetSerializer)
    def get_active_ruleset(self, step):
        """Use model method for resolved sampling rules"""
        resolved = step.get_resolved_sampling_rules()
        return resolved.get('active_ruleset')

    @extend_schema_field(ResolvedSamplingRuleSetSerializer)
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
    """Serializer for updating step sampling rules"""
    rules = SamplingRuleUpdateSerializer(many=True)
    fallback_rules = SamplingRuleUpdateSerializer(many=True, required=False)
    fallback_threshold = serializers.IntegerField(required=False)
    fallback_duration = serializers.IntegerField(required=False)

    def update_step_rules(self, step):
        """Use model method for applying sampling rules"""
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None

        return step.apply_sampling_rules_update(rules_data=self.validated_data['rules'],
                                                fallback_rules_data=self.validated_data.get('fallback_rules', []),
                                                fallback_threshold=self.validated_data.get('fallback_threshold'),
                                                fallback_duration=self.validated_data.get('fallback_duration'),
                                                user=user)


class StepSamplingRulesWriteSerializer(serializers.Serializer):
    """Write serializer for step sampling rules"""
    rules = SamplingRuleWriteSerializer(many=True)
    fallback_rules = SamplingRuleWriteSerializer(many=True, required=False)
    fallback_threshold = serializers.IntegerField(required=False)
    fallback_duration = serializers.IntegerField(required=False)

    def save(self, step: Steps):
        """Use the model method for applying sampling rules"""
        user = self.context["request"].user

        rules = self.validated_data["rules"]
        fallback_data = self.validated_data.get("fallback_rules", [])
        threshold = self.validated_data.get("fallback_threshold")
        duration = self.validated_data.get("fallback_duration")

        return step.apply_sampling_rules_update(rules_data=rules, fallback_rules_data=fallback_data,
                                                fallback_threshold=threshold, fallback_duration=duration, user=user)


class StepSamplingRulesResponseSerializer(serializers.Serializer):
    """Response serializer for sampling rules updates"""
    detail = serializers.CharField()
    ruleset_id = serializers.UUIDField()
    step_id = serializers.UUIDField()


# ===== SAMPLING ANALYTICS SERIALIZERS =====

class SamplingAnalyticsSerializer(serializers.ModelSerializer, SecureModelMixin):
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


class SamplingTriggerStateSerializer(serializers.ModelSerializer):
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


# ===== NOTIFICATION SERIALIZERS =====

class NotificationScheduleSerializer(serializers.Serializer):
    """
    Nested serializer for notification schedule configuration.
    Handles both fixed and deadline-based interval types.
    """
    interval_type = serializers.ChoiceField(choices=['fixed', 'deadline_based'])

    day_of_week = serializers.IntegerField(min_value=0, max_value=6, required=False, allow_null=True,
                                          help_text="0=Monday, 6=Sunday")
    time = serializers.TimeField(required=False, allow_null=True, help_text="Time in user's local timezone")
    interval_weeks = serializers.IntegerField(min_value=1, required=False, allow_null=True,
                                             help_text="Number of weeks between sends")

    escalation_tiers = serializers.ListField(
        child=serializers.ListField(child=serializers.FloatField(), min_length=2, max_length=2),
        required=False,
        allow_null=True,
        help_text="List of [threshold_days, interval_days] tuples"
    )

    def validate(self, attrs):
        """Validate that correct fields are present for each interval_type."""
        interval_type = attrs.get('interval_type')

        if interval_type == 'fixed':
            required_fields = ['day_of_week', 'time', 'interval_weeks']
            missing = [f for f in required_fields if not attrs.get(f)]
            if missing:
                raise serializers.ValidationError(
                    f"Fixed interval requires: {', '.join(missing)}"
                )

        elif interval_type == 'deadline_based':
            if not attrs.get('escalation_tiers'):
                raise serializers.ValidationError(
                    "Deadline-based interval requires escalation_tiers"
                )

        return attrs


class NotificationPreferenceSerializer(serializers.ModelSerializer, SecureModelMixin):
    """
    Serializer for user notification preferences.

    Handles timezone conversion:
    - INPUT: User sends time in their local timezone
    - STORED: Time converted to UTC in database
    - OUTPUT: Time converted back to user's local timezone
    """
    schedule = NotificationScheduleSerializer(required=False)
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    channel_type_display = serializers.CharField(source='get_channel_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    next_send_at_display = serializers.SerializerMethodField()
    last_sent_at_display = serializers.SerializerMethodField()

    class Meta:
        model = NotificationTask
        fields = (
            'id', 'notification_type', 'notification_type_display', 'channel_type', 'channel_type_display',
            'status', 'status_display', 'schedule', 'next_send_at', 'next_send_at_display',
            'last_sent_at', 'last_sent_at_display', 'attempt_count', 'max_attempts',
            'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'notification_type_display', 'channel_type_display', 'status', 'status_display',
            'next_send_at', 'next_send_at_display', 'last_sent_at', 'last_sent_at_display',
            'attempt_count', 'created_at', 'updated_at'
        )

    @extend_schema_field(serializers.DateTimeField(allow_null=True))
    def get_next_send_at_display(self, obj):
        """Convert next_send_at from UTC to user's timezone."""
        if not obj.next_send_at:
            return None

        request = self.context.get('request')
        if request and hasattr(request, 'user') and hasattr(request.user, 'timezone'):
            import pytz
            user_tz = pytz.timezone(request.user.timezone) if request.user.timezone else pytz.UTC
            return obj.next_send_at.astimezone(user_tz).isoformat()

        return obj.next_send_at.isoformat()

    @extend_schema_field(serializers.DateTimeField(allow_null=True))
    def get_last_sent_at_display(self, obj):
        """Convert last_sent_at from UTC to user's timezone."""
        if not obj.last_sent_at:
            return None

        request = self.context.get('request')
        if request and hasattr(request, 'user') and hasattr(request.user, 'timezone'):
            import pytz
            user_tz = pytz.timezone(request.user.timezone) if request.user.timezone else pytz.UTC
            return obj.last_sent_at.astimezone(user_tz).isoformat()

        return obj.last_sent_at.isoformat()

    def to_representation(self, instance):
        """Convert schedule fields to nested format for output."""
        data = super().to_representation(instance)

        schedule = {
            'interval_type': instance.interval_type,
        }

        if instance.interval_type == 'fixed':
            schedule['day_of_week'] = instance.day_of_week
            schedule['interval_weeks'] = instance.interval_weeks

            if instance.time:
                request = self.context.get('request')
                if request and hasattr(request, 'user') and hasattr(request.user, 'timezone'):
                    import pytz
                    from datetime import datetime
                    user_tz = pytz.timezone(request.user.timezone) if request.user.timezone else pytz.UTC
                    dt = datetime.combine(datetime.now().date(), instance.time)
                    dt_utc = pytz.UTC.localize(dt)
                    dt_local = dt_utc.astimezone(user_tz)
                    schedule['time'] = dt_local.time().isoformat()
                else:
                    schedule['time'] = instance.time.isoformat()

        elif instance.interval_type == 'deadline_based':
            schedule['escalation_tiers'] = instance.escalation_tiers

        data['schedule'] = schedule
        return data

    def create(self, validated_data):
        """Create notification preference with timezone conversion."""
        schedule_data = validated_data.pop('schedule', {})
        request = self.context.get('request')

        validated_data['recipient'] = request.user
        validated_data['interval_type'] = schedule_data.get('interval_type')

        if validated_data['interval_type'] == 'fixed':
            validated_data['day_of_week'] = schedule_data.get('day_of_week')
            validated_data['interval_weeks'] = schedule_data.get('interval_weeks')

            time_local = schedule_data.get('time')
            if time_local and hasattr(request.user, 'timezone'):
                import pytz
                from datetime import datetime
                user_tz = pytz.timezone(request.user.timezone) if request.user.timezone else pytz.UTC
                dt_local = user_tz.localize(datetime.combine(datetime.now().date(), time_local))
                dt_utc = dt_local.astimezone(pytz.UTC)
                validated_data['time'] = dt_utc.time()
            else:
                validated_data['time'] = time_local

        elif validated_data['interval_type'] == 'deadline_based':
            validated_data['escalation_tiers'] = schedule_data.get('escalation_tiers')

        notification = NotificationTask(**validated_data)
        notification.next_send_at = notification.calculate_next_send()
        notification.save()

        return notification

    def update(self, instance, validated_data):
        """Update notification preference with timezone conversion."""
        schedule_data = validated_data.pop('schedule', {})
        request = self.context.get('request')

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if schedule_data:
            instance.interval_type = schedule_data.get('interval_type', instance.interval_type)

            if instance.interval_type == 'fixed':
                instance.day_of_week = schedule_data.get('day_of_week', instance.day_of_week)
                instance.interval_weeks = schedule_data.get('interval_weeks', instance.interval_weeks)

                time_local = schedule_data.get('time')
                if time_local and hasattr(request.user, 'timezone'):
                    import pytz
                    from datetime import datetime
                    user_tz = pytz.timezone(request.user.timezone) if request.user.timezone else pytz.UTC
                    dt_local = user_tz.localize(datetime.combine(datetime.now().date(), time_local))
                    dt_utc = dt_local.astimezone(pytz.UTC)
                    instance.time = dt_utc.time()
                elif time_local:
                    instance.time = time_local

            elif instance.interval_type == 'deadline_based':
                instance.escalation_tiers = schedule_data.get('escalation_tiers', instance.escalation_tiers)

            instance.next_send_at = instance.calculate_next_send()

        instance.save()
        return instance


class QuarantineDispositionSerializer(serializers.ModelSerializer, SecureModelMixin):
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

    class Meta:
        model = QuarantineDisposition
        fields = (
            # Core fields
            'id', 'disposition_number', 'current_state', 'disposition_type', 'severity', 'severity_display',
            'assigned_to', 'description', 'resolution_notes',
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
            'part', 'step', 'step_info', 'rework_attempt_at_step',
            'rework_limit_exceeded', 'quality_reports',
            # Computed
            'assignee_name', 'choices_data', 'annotation_status',
            'can_be_completed', 'completion_blockers',
            'archived',
        )

        read_only_fields = (
            'disposition_number', 'assignee_name', 'choices_data', 'step_info', 'rework_limit_exceeded',
            'annotation_status', 'can_be_completed', 'completion_blockers',
            'severity_display', 'containment_completed_by_name', 'scrap_verified_by_name',
        )

    @extend_schema_field(serializers.CharField())
    def get_assignee_name(self, obj):
        """Get formatted full name or fallback to username"""
        if obj.assigned_to:
            return f"{obj.assigned_to.first_name} {obj.assigned_to.last_name}".strip() or obj.assigned_to.username
        else:
            return ""

    @extend_schema_field(serializers.CharField())
    def get_resolution_completed_by_name(self, obj):
        if obj.resolution_completed_by:
            return f"{obj.resolution_completed_by.first_name} {obj.resolution_completed_by.last_name}".strip() or obj.resolution_completed_by.username
        else:
            return ""

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
        if obj.containment_completed_by:
            return f"{obj.containment_completed_by.first_name} {obj.containment_completed_by.last_name}".strip() or obj.containment_completed_by.username
        return ""

    @extend_schema_field(serializers.CharField())
    def get_scrap_verified_by_name(self, obj):
        """Get name of user who verified scrap"""
        if obj.scrap_verified_by:
            return f"{obj.scrap_verified_by.first_name} {obj.scrap_verified_by.last_name}".strip() or obj.scrap_verified_by.username
        return ""

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


# ===== CAPA SERIALIZERS =====

class RootCauseSerializer(serializers.ModelSerializer, SecureModelMixin):
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


class FiveWhysSerializer(serializers.ModelSerializer, SecureModelMixin):
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


class FishboneSerializer(serializers.ModelSerializer, SecureModelMixin):
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


class RcaRecordSerializer(serializers.ModelSerializer, SecureModelMixin):
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

    def create(self, validated_data):
        five_whys_data = validated_data.pop('five_whys_data', None)
        fishbone_data = validated_data.pop('fishbone_data', None)

        # Create the RCA record
        rca_record = super().create(validated_data)

        # Create FiveWhys if data provided and method is FIVE_WHYS
        if five_whys_data and rca_record.rca_method == 'FIVE_WHYS':
            FiveWhys.objects.create(rca_record=rca_record, **five_whys_data)

        # Create Fishbone if data provided and method is FISHBONE
        if fishbone_data and rca_record.rca_method == 'FISHBONE':
            # Convert string causes to lists for JSON fields
            for field in ['man_causes', 'machine_causes', 'material_causes',
                          'method_causes', 'measurement_causes', 'environment_causes']:
                if field in fishbone_data and fishbone_data[field]:
                    # Split by newlines or commas for multi-item input
                    causes_str = fishbone_data[field]
                    if causes_str:
                        fishbone_data[field] = [c.strip() for c in causes_str.replace('\n', ',').split(',') if c.strip()]
                    else:
                        fishbone_data[field] = []
                else:
                    fishbone_data[field] = []
            Fishbone.objects.create(rca_record=rca_record, **fishbone_data)

        return rca_record

    def update(self, instance, validated_data):
        five_whys_data = validated_data.pop('five_whys_data', None)
        fishbone_data = validated_data.pop('fishbone_data', None)

        # Update the RCA record
        instance = super().update(instance, validated_data)

        # Update or create FiveWhys if data provided and method is FIVE_WHYS
        if five_whys_data and instance.rca_method == 'FIVE_WHYS':
            try:
                five_whys = instance.five_whys
                for key, value in five_whys_data.items():
                    setattr(five_whys, key, value)
                five_whys.save()
            except FiveWhys.DoesNotExist:
                FiveWhys.objects.create(rca_record=instance, **five_whys_data)

        # Update or create Fishbone if data provided and method is FISHBONE
        if fishbone_data and instance.rca_method == 'FISHBONE':
            # Convert string causes to lists for JSON fields
            for field in ['man_causes', 'machine_causes', 'material_causes',
                          'method_causes', 'measurement_causes', 'environment_causes']:
                if field in fishbone_data and fishbone_data[field]:
                    causes_str = fishbone_data[field]
                    if causes_str:
                        fishbone_data[field] = [c.strip() for c in causes_str.replace('\n', ',').split(',') if c.strip()]
                    else:
                        fishbone_data[field] = []
                else:
                    fishbone_data[field] = []

            try:
                fishbone = instance.fishbone
                for key, value in fishbone_data.items():
                    setattr(fishbone, key, value)
                fishbone.save()
            except Fishbone.DoesNotExist:
                Fishbone.objects.create(rca_record=instance, **fishbone_data)

        return instance

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


class CapaTaskAssigneeSerializer(serializers.ModelSerializer, SecureModelMixin):
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


class CapaTasksSerializer(serializers.ModelSerializer, SecureModelMixin):
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
        """Get summary of attached documents"""
        docs = obj.documents.all()
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


class CapaVerificationSerializer(serializers.ModelSerializer, SecureModelMixin):
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


class CAPASerializer(serializers.ModelSerializer, SecureModelMixin):
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
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = (
            'capa_number', 'status', 'status_display', 'completed_date',
            'approval_required', 'approved_by', 'approved_at', 'approval_status_display',
            'completion_percentage', 'is_overdue', 'blocking_items',
            'created_at', 'updated_at', 'archived'
        )

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


class StepOverrideSerializer(serializers.ModelSerializer, SecureModelMixin):
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


class FPIRecordSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Serializer for First Piece Inspection records."""
    from Tracker.models import FPIRecord

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    result_display = serializers.CharField(source='get_result_display', read_only=True)
    work_order_info = serializers.SerializerMethodField()
    step_info = serializers.SerializerMethodField()
    part_type_info = serializers.SerializerMethodField()
    designated_part_info = serializers.SerializerMethodField()
    inspected_by_info = serializers.SerializerMethodField()
    waived_by_info = serializers.SerializerMethodField()
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
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = (
            'status', 'result', 'inspected_by', 'inspected_at',
            'waived', 'waived_by', 'waive_reason',
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
    def get_equipment_info(self, obj):
        if obj.equipment:
            return {
                'id': str(obj.equipment.id),
                'name': obj.equipment.name,
            }
        return None


class StepExecutionMeasurementSerializer(serializers.ModelSerializer, SecureModelMixin):
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
            'measurement_definition', 'measurement_definition_info',
            'value', 'string_value',
            'is_within_spec', 'spec_status',
            'recorded_by', 'recorded_by_info',
            'recorded_at',
            'equipment', 'equipment_info',
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
