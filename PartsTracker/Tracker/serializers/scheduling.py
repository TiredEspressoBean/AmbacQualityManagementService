"""Serializers for the scheduling API (Phase 4).

Read-only display shapes for the solver's output — `ScheduleResult` (run metadata)
and `ScheduledTask` (the Gantt rows, with resolved display names). Nullable method
fields are annotated `allow_null=True` so the generated FE zod client accepts nulls
(a part-vs-core task, an unassigned operator, an unattended step).
"""
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from Tracker.models.scheduling import ScheduledTask, ScheduleResult


class ScheduleResultSerializer(serializers.ModelSerializer):
    task_count = serializers.SerializerMethodField()

    class Meta:
        model = ScheduleResult
        fields = (
            'id', 'horizon_start', 'horizon_end', 'solver_status', 'solve_time_ms',
            'objective_value_cents', 'relaxed_pin_count', 'is_active', 'is_stale',
            'created_at', 'task_count',
        )
        read_only_fields = fields

    @extend_schema_field(serializers.IntegerField())
    def get_task_count(self, obj) -> int:
        return obj.tasks.count()


class ScheduledTaskSerializer(serializers.ModelSerializer):
    """One Gantt row: a unit (part or core) + step on a machine, with the operator
    assignment and resolved display names."""
    part_erp = serializers.SerializerMethodField()
    core_number = serializers.SerializerMethodField()
    step_name = serializers.SerializerMethodField()
    machine_name = serializers.SerializerMethodField()
    operator_name = serializers.SerializerMethodField()
    work_order = serializers.SerializerMethodField()
    work_center = serializers.SerializerMethodField()

    class Meta:
        model = ScheduledTask
        fields = (
            'id', 'schedule', 'part', 'part_erp', 'core', 'core_number',
            'step', 'step_name', 'machine', 'machine_name',
            'assigned_operator', 'operator_name', 'requires_operator',
            'work_order', 'work_center',
            'start_time', 'end_time', 'is_pinned', 'fence_zone',
        )
        read_only_fields = fields

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_part_erp(self, obj):
        return obj.part.ERP_id if obj.part_id else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_core_number(self, obj):
        return obj.core.core_number if obj.core_id else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_step_name(self, obj):
        return obj.step.name if obj.step_id else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_machine_name(self, obj):
        return obj.machine.name if obj.machine_id else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_operator_name(self, obj):
        u = obj.assigned_operator
        if u is None:
            return None
        return (f"{u.first_name or ''} {u.last_name or ''}".strip() or u.get_username())

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_work_order(self, obj):
        wo = (obj.part.work_order if obj.part_id
              else obj.core.work_order if obj.core_id else None)
        return wo.ERP_id if wo else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_work_center(self, obj):
        wc = obj.step.work_center if obj.step_id else None
        return wc.name if wc else None


class PinRequestSerializer(serializers.Serializer):
    is_pinned = serializers.BooleanField()
