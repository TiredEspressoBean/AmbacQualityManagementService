# serializers/training.py - Training Management Serializers
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from Tracker.models import TrainingType, TrainingRecord, TrainingRequirement
from .core import SecureModelMixin


class TrainingTypeSerializer(serializers.ModelSerializer, SecureModelMixin):
    """
    Serializer for TrainingType model.

    Represents a type of training or qualification that personnel can hold.
    """

    class Meta:
        model = TrainingType
        fields = [
            'id', 'name', 'description', 'validity_period_days',
            'created_at', 'updated_at', 'archived'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')


class TrainingRecordSerializer(serializers.ModelSerializer, SecureModelMixin):
    """
    Serializer for TrainingRecord model.

    Records that a user has completed a specific training.
    Includes computed status property and related info fields.
    """
    # Display/info fields
    user_info = serializers.SerializerMethodField()
    training_type_info = serializers.SerializerMethodField()
    trainer_info = serializers.SerializerMethodField()
    status = serializers.CharField(read_only=True)
    is_current = serializers.BooleanField(read_only=True)

    class Meta:
        model = TrainingRecord
        fields = [
            'id', 'user', 'user_info', 'training_type', 'training_type_info',
            'completed_date', 'expires_date', 'trainer', 'trainer_info',
            'notes', 'status', 'is_current',
            'created_at', 'updated_at', 'archived'
        ]
        read_only_fields = ('id', 'status', 'is_current', 'created_at', 'updated_at')

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


class TrainingRequirementSerializer(serializers.ModelSerializer, SecureModelMixin):
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
    scope = serializers.CharField(read_only=True)
    scope_display = serializers.SerializerMethodField()

    class Meta:
        model = TrainingRequirement
        fields = [
            'id', 'training_type', 'training_type_info',
            'step', 'step_info', 'process', 'process_info',
            'equipment_type', 'equipment_type_info',
            'notes', 'scope', 'scope_display',
            'created_at', 'updated_at', 'archived'
        ]
        read_only_fields = ('id', 'scope', 'scope_display', 'created_at', 'updated_at')

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

    @extend_schema_field(serializers.CharField())
    def get_scope_display(self, obj) -> str:
        """Return human-readable scope description like 'Step: Machining' or 'Process: Assembly'."""
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
        return str(target)
