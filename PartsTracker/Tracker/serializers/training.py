# serializers/training.py - Training Management Serializers
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from Tracker.models import TrainingType, TrainingRecord, TrainingRequirement, JobRole
from .core import SecureModelMixin


class JobRoleSerializer(SecureModelMixin):
    """Serializer for JobRole — the HR/organizational role competency hangs off."""

    class Meta:
        model = JobRole
        fields = [
            'id', 'name', 'description', 'active',
            'created_at', 'updated_at', 'archived',
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')


# ===== COMPETENCE MATRIX (read-only aggregate) =====

class TrainingMatrixColumnSerializer(serializers.Serializer):
    """A training type used as a matrix column."""
    id = serializers.CharField()
    name = serializers.CharField()


class TrainingMatrixCellSerializer(serializers.Serializer):
    """One operator's standing on one training type."""
    training_type = serializers.CharField()
    level = serializers.IntegerField()
    level_display = serializers.CharField()
    status = serializers.CharField()
    expires_date = serializers.DateField(allow_null=True)
    required_level = serializers.IntegerField()   # 0 = not required by the operator's role
    gap = serializers.BooleanField()              # held level below role requirement


class TrainingMatrixOperatorSerializer(serializers.Serializer):
    """A matrix row: an operator, their role, and their cells."""
    id = serializers.IntegerField()
    name = serializers.CharField()
    job_role = serializers.CharField(allow_null=True)
    job_role_name = serializers.CharField(allow_blank=True)
    required_count = serializers.IntegerField()
    gap_count = serializers.IntegerField()
    cells = TrainingMatrixCellSerializer(many=True)


class TrainingMatrixCoverageSerializer(serializers.Serializer):
    """Per-training-type coverage — how many operators are qualified / expiring."""
    training_type = serializers.CharField()
    qualified_count = serializers.IntegerField()
    expiring_count = serializers.IntegerField()


class TrainingMatrixSerializer(serializers.Serializer):
    """Operators x training-types competency matrix."""
    qualified_at = serializers.IntegerField()
    job_roles = TrainingMatrixColumnSerializer(many=True)   # {id, name} of active roles, for filtering
    training_types = TrainingMatrixColumnSerializer(many=True)
    operators = TrainingMatrixOperatorSerializer(many=True)
    coverage = TrainingMatrixCoverageSerializer(many=True)


class TrainingTypeSerializer(SecureModelMixin):
    """
    Serializer for TrainingType model.

    TrainingType is a versioned curriculum-spec entry. Any content edit
    (name, description, validity period) routes through `create_new_version`
    so changes are auditable. Archiving goes through a plain save because
    it is a soft-delete, not a content change.
    """

    class Meta:
        model = TrainingType
        fields = [
            'id', 'name', 'description', 'validity_period_days',
            'created_at', 'updated_at', 'archived', 'version'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at', 'version')

    _NON_VERSIONING_FIELDS = frozenset({'archived'})

    def update(self, instance, validated_data):
        from Tracker.services.core.versioning import apply_versioned_update
        return apply_versioned_update(
            instance, validated_data,
            non_versioning_fields=self._NON_VERSIONING_FIELDS,
            default_update=super().update,
        )


class TrainingRecordSerializer(SecureModelMixin):
    """
    Serializer for TrainingRecord model.

    Records that a user has completed a specific training.
    Includes computed status property and related info fields.
    """
    # Display/info fields
    user_info = serializers.SerializerMethodField()
    training_type_info = serializers.SerializerMethodField()
    trainer_info = serializers.SerializerMethodField()
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    status = serializers.CharField(read_only=True)
    is_current = serializers.BooleanField(read_only=True)

    class Meta:
        model = TrainingRecord
        fields = [
            'id', 'user', 'user_info', 'training_type', 'training_type_info',
            'completed_date', 'level', 'level_display', 'expires_date',
            'trainer', 'trainer_info',
            'notes', 'status', 'is_current',
            'created_at', 'updated_at', 'archived'
        ]
        read_only_fields = ('id', 'level_display', 'status', 'is_current', 'created_at', 'updated_at')

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_user_info(self, obj):
        """Return user details for the trainee."""
        if obj.user:
            return {
                'id': obj.user.id,
                'username': obj.user.username,
                'full_name': f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username,
                'email': obj.user.email,
            }
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_training_type_info(self, obj):
        """Return training type details."""
        if obj.training_type:
            return {
                'id': obj.training_type.id,
                'name': obj.training_type.name,
                'validity_period_days': obj.training_type.validity_period_days,
            }
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_trainer_info(self, obj):
        """Return trainer details."""
        if obj.trainer:
            return {
                'id': obj.trainer.id,
                'username': obj.trainer.username,
                'full_name': f"{obj.trainer.first_name} {obj.trainer.last_name}".strip() or obj.trainer.username,
            }
        return None


class TrainingRequirementSerializer(SecureModelMixin):
    """
    Serializer for TrainingRequirement model.

    Links a TrainingType to work activities (Step, Process, or EquipmentType).
    Includes scope_display for human-readable target description.
    """
    # Display/info fields
    training_type_info = serializers.SerializerMethodField()
    step_info = serializers.SerializerMethodField()
    process_info = serializers.SerializerMethodField()
    equipment_type_info = serializers.SerializerMethodField()
    job_role_info = serializers.SerializerMethodField()
    min_level_display = serializers.CharField(source='get_min_level_display', read_only=True)
    scope = serializers.CharField(read_only=True)
    scope_display = serializers.SerializerMethodField()

    class Meta:
        model = TrainingRequirement
        fields = [
            'id', 'training_type', 'training_type_info',
            'min_level', 'min_level_display',
            'step', 'step_info', 'process', 'process_info',
            'equipment_type', 'equipment_type_info',
            'job_role', 'job_role_info',
            'notes', 'scope', 'scope_display',
            'created_at', 'updated_at', 'archived'
        ]
        read_only_fields = ('id', 'min_level_display', 'scope', 'scope_display', 'created_at', 'updated_at')

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_training_type_info(self, obj):
        """Return training type details."""
        if obj.training_type:
            return {
                'id': obj.training_type.id,
                'name': obj.training_type.name,
                'validity_period_days': obj.training_type.validity_period_days,
            }
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_step_info(self, obj):
        """Return step details if this requirement is for a step."""
        if obj.step:
            return {
                'id': obj.step.id,
                'name': obj.step.name,
            }
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_process_info(self, obj):
        """Return process details if this requirement is for a process."""
        if obj.process:
            return {
                'id': obj.process.id,
                'name': obj.process.name,
            }
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_equipment_type_info(self, obj):
        """Return equipment type details if this requirement is for equipment."""
        if obj.equipment_type:
            return {
                'id': obj.equipment_type.id,
                'name': obj.equipment_type.name,
            }
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_job_role_info(self, obj):
        """Return job role details if this requirement is for a role."""
        if obj.job_role:
            return {
                'id': str(obj.job_role.id),
                'name': obj.job_role.name,
            }
        return None

    @extend_schema_field(serializers.CharField())
    def get_scope_display(self, obj) -> str:
        """Return human-readable scope like 'Step: Machining' or 'Role: CMM Inspector'."""
        target = obj.target
        if not target:
            return "Unknown"

        scope = obj.scope
        if scope == 'step':
            return f"Step: {target.name}"
        elif scope == 'process':
            return f"Process: {target.name}"
        elif scope == 'equipment_type':
            return f"Equipment Type: {target.name}"
        elif scope == 'job_role':
            return f"Role: {target.name}"
        return str(target)
