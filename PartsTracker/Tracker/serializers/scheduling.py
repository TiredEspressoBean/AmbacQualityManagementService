"""Serializers for the scheduling API (Phase 4).

Read-only display shapes for the solver's output — `ScheduleResult` (run metadata)
and `ScheduledTask` (the Gantt rows, with resolved display names). Nullable method
fields are annotated `allow_null=True` so the generated FE zod client accepts nulls
(a part-vs-core task, an unassigned operator, an unattended step).
"""
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from Tracker.serializers.core import SecureModelMixin
from Tracker.models import LaborCalendarBlock, OvertimeWindow, PlantCalendarException
from Tracker.models.scheduling import (
    Fixture, OptimizationConfig, ScheduledTask, ScheduleResult,
)


class FixtureSerializer(serializers.ModelSerializer):
    """A shared, quantity-limited scheduling resource — fixture / cutting tool / die / NC
    program. `steps` is the set of operations that require it; the solver serializes ops
    against the `quantity` available (cumulative capacity). `steps` validates against the
    tenant-scoped Steps manager, so a cross-tenant step id is rejected."""
    step_names = serializers.SerializerMethodField()

    class Meta:
        model = Fixture
        fields = ('id', 'name', 'kind', 'quantity', 'lead_time_days', 'steps', 'step_names')
        read_only_fields = ('id', 'step_names')

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_step_names(self, obj):
        return [s.name for s in obj.steps.all()]


class PlanWorkOrderInputSerializer(serializers.Serializer):
    """Input for the Gantt 'add work' action — create a WO + spawn its parts."""
    process = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)
    erp_id = serializers.CharField(required=False, allow_blank=True, max_length=100)
    priority = serializers.IntegerField(required=False)
    expected_start = serializers.DateField(required=False, allow_null=True)
    expected_completion = serializers.DateField(required=False, allow_null=True)


class OptimizationConfigSerializer(serializers.ModelSerializer):
    """The tenant's solver knobs — read + PATCH from the scheduling settings dialog.
    All fields are editable except the identity/version bookkeeping."""

    class Meta:
        model = OptimizationConfig
        fields = (
            'id',
            'solver_time_limit_seconds', 'relative_gap_limit',
            'frozen_zone_days', 'slushy_zone_days',
            'default_outside_process_turnaround_days', 'default_machine_unattended',
            'match_operators', 'default_labor_model', 'default_lockstep_batch',
            'shop_rate_per_hour', 'overtime_multiplier', 'pfd_allowance_pct',
            'late_penalty_urgent', 'late_penalty_high',
            'late_penalty_normal', 'late_penalty_low',
            'staging_buffer_minutes', 'job_change_minutes', 'default_move_minutes',
            'release_mode',
            'auto_resolve', 'auto_resolve_min_interval_minutes',
        )
        read_only_fields = ('id',)


class ScheduleResultSerializer(serializers.ModelSerializer):
    task_count = serializers.SerializerMethodField()

    class Meta:
        model = ScheduleResult
        fields = (
            'id', 'horizon_start', 'horizon_end', 'solver_status', 'solve_time_ms',
            'machine_solve_ms', 'operator_solve_ms',
            'objective_value_cents', 'weighted_lateness', 'relaxed_pin_count', 'relative_gap',
            'is_active', 'is_stale', 'is_draft', 'created_at', 'task_count',
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
    work_order_id = serializers.SerializerMethodField()
    work_center = serializers.SerializerMethodField()
    due_date = serializers.SerializerMethodField()
    is_late = serializers.SerializerMethodField()
    is_makeup = serializers.SerializerMethodField()
    is_outside_process = serializers.SerializerMethodField()
    outside_supplier = serializers.SerializerMethodField()

    class Meta:
        model = ScheduledTask
        fields = (
            'id', 'schedule', 'part', 'part_erp', 'core', 'core_number',
            'step', 'step_name', 'machine', 'machine_name',
            'assigned_operator', 'operator_name', 'requires_operator',
            'work_order', 'work_order_id', 'work_center', 'due_date', 'is_late',
            'start_time', 'end_time', 'is_pinned', 'fence_zone', 'material_shortage',
            'material_detail', 'late_cause', 'in_progress', 'actual_start', 'actual_end',
            'is_makeup', 'cure_window_violation',
            'is_outside_process', 'outside_supplier',
        )
        read_only_fields = fields

    @extend_schema_field(serializers.UUIDField(allow_null=True))
    def get_work_order_id(self, obj):
        wo = self._work_order(obj)
        return str(wo.id) if wo else None

    @staticmethod
    def _work_order(obj):
        """The task's owning work order (via its part or core), or None."""
        return (obj.part.work_order if obj.part_id
                else obj.core.work_order if obj.core_id else None)

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
        wo = self._work_order(obj)
        return wo.ERP_id if wo else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_work_center(self, obj):
        wc = obj.step.work_center if obj.step_id else None
        return wc.name if wc else None

    @extend_schema_field(serializers.DateField(allow_null=True))
    def get_due_date(self, obj):
        wo = self._work_order(obj)
        return wo.expected_completion if wo else None

    @extend_schema_field(serializers.BooleanField())
    def get_is_late(self, obj):
        """True when this task is scheduled to finish after its work order's due
        date (end-of-day on expected_completion). False when there's no due date."""
        wo = self._work_order(obj)
        due = wo.expected_completion if wo else None
        if due is None or obj.end_time is None:
            return False
        return obj.end_time.date() > due

    @extend_schema_field(serializers.BooleanField())
    def get_is_makeup(self, obj):
        """True when this task's part is a make-up/replacement (spawned to cover scrap)."""
        return bool(obj.part.is_makeup) if obj.part_id else False

    @extend_schema_field(serializers.BooleanField())
    def get_is_outside_process(self, obj):
        """True when this op is subcontracted. Its span is VENDOR turnaround (elapsed
        calendar time), not shop capacity — so the board must not sum it into a work
        center's load, and its bars group by shipment rather than by machine slot."""
        return bool(obj.step.is_outside_process) if obj.step_id else False

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_outside_supplier(self, obj):
        """The subcontractor this op ships to — bars for the same vendor on the same
        day are one shipment."""
        if not obj.step_id or not obj.step.is_outside_process:
            return None
        sup = obj.step.outside_supplier
        return sup.name if sup else None


class PinRequestSerializer(serializers.Serializer):
    is_pinned = serializers.BooleanField()


class MoveRequestSerializer(serializers.Serializer):
    """Drag-to-reschedule: the new start; the task keeps its duration."""
    start_time = serializers.DateTimeField()


class MoveBatchRequestSerializer(serializers.Serializer):
    """Re-anchor a work-order batch: its earliest part moves to start_time, the rest
    shift by the same delta."""
    task_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
    start_time = serializers.DateTimeField()


class PinBatchRequestSerializer(serializers.Serializer):
    """Pin/unpin every part of a batch."""
    task_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
    is_pinned = serializers.BooleanField()


class BatchMembershipRequestSerializer(serializers.Serializer):
    """Planner batch control: merge selected tasks into one lot (`merge=true`) or break
    them apart into separate lots (`merge=false`)."""
    task_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
    merge = serializers.BooleanField()


class ReassignMachineRequestSerializer(serializers.Serializer):
    """Move a scheduled task onto a specific machine (planner override)."""
    machine_id = serializers.UUIDField()


class ReassignOperatorRequestSerializer(serializers.Serializer):
    """Assign / re-assign / clear (null) the operator on a scheduled task."""
    operator_id = serializers.UUIDField(allow_null=True)


class ExplodeWorkOrderInputSerializer(serializers.Serializer):
    """(Re)explode an existing work order's BOM. `create=false` previews without writing."""
    work_order_id = serializers.UUIDField()
    create = serializers.BooleanField(default=True)


class BulkReassignMachineRequestSerializer(serializers.Serializer):
    """Move several scheduled tasks onto one machine at once (planner override)."""
    task_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
    machine_id = serializers.UUIDField()


class BulkReassignOperatorRequestSerializer(serializers.Serializer):
    """Assign / clear (null) one operator across several scheduled tasks at once."""
    task_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
    operator_id = serializers.UUIDField(allow_null=True)


class PlantCalendarExceptionSerializer(serializers.ModelSerializer):
    """A dated, plant-wide non-working window — holiday / shutdown / inventory day.
    The solver blocks EVERY machine and treats operators as absent during it."""

    class Meta:
        model = PlantCalendarException
        fields = ('id', 'name', 'kind', 'start_time', 'end_time', 'recurrence', 'is_active')
        read_only_fields = ('id',)

    def validate(self, attrs):
        start = attrs.get('start_time', getattr(self.instance, 'start_time', None))
        end = attrs.get('end_time', getattr(self.instance, 'end_time', None))
        if start and end and end <= start:
            raise serializers.ValidationError({'end_time': 'End must be after start.'})
        return attrs


class LaborCalendarBlockSerializer(serializers.ModelSerializer):
    """Operator non-working time — PTO / sick / training / meeting / break — one-off
    (ONCE: start_time+end_time) or weekly (WEEKLY: days_of_week+window_start/end),
    company-wide (user null) or per person. Operators only; machines keep running.
    Validates the fields the chosen recurrence needs."""
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = LaborCalendarBlock
        fields = (
            'id', 'user', 'user_name', 'kind', 'recurrence',
            'start_time', 'end_time', 'days_of_week', 'window_start', 'window_end',
            'reason', 'is_active',
        )
        read_only_fields = ('id', 'user_name')

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_user_name(self, obj):
        u = obj.user
        if u is None:
            return None
        return (f"{u.first_name or ''} {u.last_name or ''}".strip() or u.get_username())

    def validate_user(self, value):
        """Keep a personal block inside the tenant — User is not tenant-scoped, so a
        stray cross-tenant id must be rejected explicitly. Null (company-wide) is fine."""
        if value is None:
            return value
        tenant = getattr(self.context.get('request'), 'tenant', None)
        if tenant is not None and getattr(value, 'tenant_id', None) != tenant.id:
            from Tracker.models import TenantMembership
            if not TenantMembership.objects.filter(tenant=tenant, user=value).exists():
                raise serializers.ValidationError('User is not a member of this tenant.')
        return value

    def validate(self, attrs):
        def pick(name):
            return attrs.get(name, getattr(self.instance, name, None))

        rec = pick('recurrence') or 'ONCE'
        if rec == 'ONCE':
            start, end = pick('start_time'), pick('end_time')
            if not start or not end:
                raise serializers.ValidationError(
                    'One-off blocks need start_time and end_time.')
            if end <= start:
                raise serializers.ValidationError({'end_time': 'End must be after start.'})
        else:  # WEEKLY
            if pick('window_start') is None or pick('window_end') is None:
                raise serializers.ValidationError(
                    'Weekly blocks need window_start and window_end.')
            if not (pick('days_of_week') or '').strip():
                raise serializers.ValidationError(
                    {'days_of_week': 'Weekly blocks need at least one day.'})
        return attrs


class OvertimeWindowSerializer(SecureModelMixin):
    """Additive shop-open time — an extra run of a `shift` (its hours + crew). ONCE runs
    it on [start_date, end_date]; WEEKLY on days_of_week. The solver adds it to that
    shift's operators + attended machines (closures still win). Validates the fields the
    recurrence needs."""
    shift_name = serializers.SerializerMethodField()

    class Meta:
        model = OvertimeWindow
        fields = (
            'id', 'shift', 'shift_name', 'recurrence',
            'start_date', 'end_date', 'days_of_week', 'reason', 'is_active',
        )
        read_only_fields = ('id', 'shift_name')

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_shift_name(self, obj):
        return obj.shift.name if obj.shift_id else None

    def validate(self, attrs):
        def pick(name):
            return attrs.get(name, getattr(self.instance, name, None))

        rec = pick('recurrence') or 'ONCE'
        if rec == 'ONCE':
            start, end = pick('start_date'), pick('end_date')
            if not start or not end:
                raise serializers.ValidationError(
                    'One-off overtime needs start_date and end_date.')
            if end < start:
                raise serializers.ValidationError({'end_date': 'End must not be before start.'})
        else:  # WEEKLY
            if not (pick('days_of_week') or '').strip():
                raise serializers.ValidationError(
                    {'days_of_week': 'Weekly overtime needs at least one day.'})
        return attrs
