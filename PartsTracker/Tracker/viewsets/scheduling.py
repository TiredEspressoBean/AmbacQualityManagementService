# viewsets/scheduling.py - CP-SAT scheduling API (Phase 4)
"""
ViewSets for the scheduler:
- ScheduleViewSet: run the solver / operator dispatch, read the active schedule.
- ScheduledTaskViewSet: read the scheduled tasks (Gantt rows) + pin/unpin.

Both solve and dispatch run synchronously with a modest time cap — fine for dev and
small tenants; moving them to Celery tasks (nightly beat + an async trigger) is the
follow-on for large solves. Gating reuses the model-permission system: solve creates a
ScheduleResult (POST -> add_scheduleresult); dispatch and pin mutate tasks
(change_scheduledtask) and are CRUD-exempt so POST doesn't demand add.
"""
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter, extend_schema, inline_serializer,
)
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from Tracker.models import LaborCalendarBlock, OvertimeWindow, PlantCalendarException
from Tracker.models.scheduling import (
    Fixture, OptimizationConfig, ScheduledTask, ScheduleResult,
)
from Tracker.serializers.scheduling import (
    BatchMembershipRequestSerializer, BulkReassignMachineRequestSerializer,
    BulkReassignOperatorRequestSerializer, ExplodeWorkOrderInputSerializer,
    FixtureSerializer, LaborCalendarBlockSerializer, MoveBatchRequestSerializer,
    MoveRequestSerializer, OptimizationConfigSerializer, OvertimeWindowSerializer,
    PinBatchRequestSerializer, PinRequestSerializer, PlanWorkOrderInputSerializer,
    PlantCalendarExceptionSerializer, ReassignMachineRequestSerializer,
    ReassignOperatorRequestSerializer, ScheduledTaskSerializer, ScheduleResultSerializer,
)
from Tracker.services.scheduling.manual_move import (
    MoveRejected, move_batch, move_task, pin_batch,
)
from Tracker.services.scheduling.scenario import (
    commit_draft, compare_draft, discard_draft,
)
from Tracker.tasks import run_dispatch_task, run_solve_task
from .base import TenantScopedMixin
from .core import ExcelExportMixin, ListMetadataMixin

# Solve/dispatch time cap lives on `OptimizationConfig.solver_time_limit_seconds`
# (default 180s, editable from the scheduling settings dialog); CP-SAT returns
# best-so-far when it elapses. See ScheduleViewSet._time_limit.


class ScheduleViewSet(TenantScopedMixin, viewsets.GenericViewSet):
    """Run the solver / dispatch and read the active schedule."""
    queryset = ScheduleResult.unscoped.all()
    serializer_class = ScheduleResultSerializer
    action_permissions = {
        'run_dispatch': ['change_scheduledtask'],
        'commit': ['add_scheduleresult'],
        'discard': ['add_scheduleresult'],
        # NOTE: 'config' is deliberately absent — it serves GET (anyone with
        # view_optimizationconfig, i.e. all staff) and PATCH (planner) from one
        # action, so the PATCH gate is enforced inside the action body.
        'plan_work_order': ['add_workorder'],
        'explode_work_order': ['add_workorder'],
    }
    crud_exempt_actions = {
        'run_dispatch', 'commit', 'discard', 'config', 'plan_work_order',
        'explode_work_order',
    }

    def _get_config(self):
        """The tenant's solver config, created with defaults on first access."""
        config, _ = OptimizationConfig.objects.get_or_create(tenant=self.tenant)
        return config

    def _time_limit(self) -> int:
        return self._get_config().solver_time_limit_seconds

    @extend_schema(
        methods=['GET'], request=None, responses={200: OptimizationConfigSerializer})
    @extend_schema(
        methods=['PATCH'], request=OptimizationConfigSerializer,
        responses={200: OptimizationConfigSerializer})
    @action(detail=False, methods=['get', 'patch'])
    def config(self, request):
        """The tenant's solver knobs (time limit, fence zones, penalties, labor model).
        GET reads them (any staff viewer — the Gantt renders fences from them);
        PATCH updates the subset provided, gated on change_optimizationconfig
        (the scheduling settings dialog). Method-split gate lives here because
        action_permissions applies per action, not per HTTP method."""
        config = self._get_config()
        if request.method == 'PATCH':
            if not request.user.has_tenant_perm('change_optimizationconfig'):
                return Response(
                    {"detail": "You don't have permission to change the solver configuration."},
                    status=403)
            ser = OptimizationConfigSerializer(config, data=request.data, partial=True)
            ser.is_valid(raise_exception=True)
            ser.save()
            return Response(ser.data)
        return Response(OptimizationConfigSerializer(config).data)

    @extend_schema(
        request=PlanWorkOrderInputSerializer,
        responses={201: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    @action(detail=False, methods=['post'], url_path='plan-work-order')
    def plan_work_order(self, request):
        """Add work: create a WO for a process and spawn its parts at the first step,
        so it schedules on the next Solve. The 'add work' half of Gantt planning."""
        from django.db import IntegrityError
        from Tracker.models import Processes
        from Tracker.services.mes.work_order import plan_work_order as plan_wo

        ser = PlanWorkOrderInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        process = Processes.objects.filter(pk=data['process']).first()
        if process is None:
            return Response({'detail': 'Unknown process.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            wo = plan_wo(
                tenant=self.tenant, process=process, user=request.user,
                quantity=data['quantity'], erp_id=(data.get('erp_id') or None),
                priority=data.get('priority'),
                expected_start=data.get('expected_start'),
                expected_completion=data.get('expected_completion'),
                apply_yield=True,  # New-WO quantity is GOOD parts wanted; gross up for scrap
            )
        except (ValueError, IntegrityError) as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                'id': str(wo.id), 'ERP_id': wo.ERP_id, 'quantity': wo.quantity,
                # BOM explosion ran in-line (auto): pegged component WOs created, plus
                # anything netted from stock, purchased (buy), or short.
                'explosion': getattr(wo, 'explosion_summary', None),
                # Yield gross-up: {target_good, started} when scrap inflated the count.
                'yield': getattr(wo, 'yield_summary', None),
            },
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=ExplodeWorkOrderInputSerializer, responses={200: OpenApiTypes.OBJECT})
    @action(detail=False, methods=['post'], url_path='explode-work-order')
    def explode_work_order(self, request):
        """(Re)explode an existing work order's BOM into pegged in-house component WOs.
        `create=false` previews (top-level, no writes). Net-first: existing stock + already-
        pegged component WOs offset the requirement, so re-running is idempotent."""
        from Tracker.models import WorkOrder
        from Tracker.services.mes.bom_explosion import explode_work_order_tx
        ser = ExplodeWorkOrderInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        # tenant-safe: .objects auto-scopes to the request tenant.
        wo = WorkOrder.objects.filter(pk=ser.validated_data['work_order_id']).first()
        if wo is None:
            return Response({'detail': 'Unknown work order.'}, status=status.HTTP_404_NOT_FOUND)
        result = explode_work_order_tx(wo, user=request.user, create=ser.validated_data['create'])
        return Response(result.as_summary())

    @extend_schema(request=None, responses={200: ScheduleResultSerializer})
    @action(detail=False, methods=['get'])
    def current(self, request):
        """The live (committed) schedule's run metadata, or 404 if none exists yet."""
        sched = self.get_queryset().filter(is_active=True).order_by('-created_at').first()
        if sched is None:
            return Response({'detail': 'No active schedule.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(self.get_serializer(sched).data)

    @extend_schema(request=None, responses={200: ScheduleResultSerializer})
    @action(detail=False, methods=['get'])
    def draft(self, request):
        """The current what-if draft, or 404 if none is pending review."""
        sched = self.get_queryset().filter(is_draft=True).order_by('-created_at').first()
        if sched is None:
            return Response({'detail': 'No draft.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(self.get_serializer(sched).data)

    @extend_schema(request=None, responses={200: OpenApiTypes.OBJECT})
    @action(detail=False, methods=['get'])
    def compare(self, request):
        """Live vs draft: each schedule's summary plus how many tasks the draft moves."""
        return Response(compare_draft(self.tenant))

    @extend_schema(request=None, responses={200: ScheduleResultSerializer, 404: OpenApiTypes.OBJECT})
    @action(detail=False, methods=['post'])
    def commit(self, request):
        """Promote the draft to the live schedule, superseding the previous live one."""
        promoted = commit_draft(self.tenant)
        if promoted is None:
            return Response({'detail': 'No draft to commit.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(ScheduleResultSerializer(promoted).data)

    @extend_schema(request=None, responses={200: OpenApiTypes.OBJECT})
    @action(detail=False, methods=['post'])
    def discard(self, request):
        """Throw the draft away, leaving the live schedule untouched."""
        return Response({'discarded': discard_draft(self.tenant)})

    @extend_schema(
        request=None,
        responses={200: inline_serializer(name='WorkingWindows', fields={
            'windows': serializers.ListField(child=inline_serializer(
                name='WorkingWindow', fields={
                    'start': serializers.DateTimeField(),
                    'end': serializers.DateTimeField(),
                })),
        })},
    )
    @action(detail=False, methods=['get'])
    def working_windows(self, request):
        """The tenant's working windows over the active schedule's horizon (shift
        calendar expanded to datetimes). The Gantt shades the complement — nights,
        weekends, non-shift hours. Empty list when no schedule or no shifts."""
        from Tracker.services.scheduling.data import get_working_windows
        sched = self.get_queryset().filter(is_active=True).order_by('-created_at').first()
        if sched is None:
            return Response({'windows': []})
        windows = get_working_windows(self.tenant, sched.horizon_start, sched.horizon_end)
        return Response({'windows': [{'start': s, 'end': e} for s, e in windows]})

    @extend_schema(request=None, responses={202: OpenApiTypes.OBJECT})
    @action(detail=False, methods=['post'])
    def solve(self, request):
        """Kick off the Layer-1 machine solve in the background, replacing the live
        schedule. Returns a task id; poll `solve_status?task_id=`, then re-read `current`."""
        task = run_solve_task.delay(str(self.tenant.id), self._time_limit())
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)

    @extend_schema(request=None, responses={202: OpenApiTypes.OBJECT})
    @action(detail=False, methods=['post'], url_path='solve-draft')
    def solve_draft(self, request):
        """Kick off a what-if solve in the background that produces a *draft* — the live
        schedule is untouched. Returns a task id; poll `solve_status?task_id=`, then read
        `draft` / `compare` and `commit` or `discard`."""
        task = run_solve_task.delay(str(self.tenant.id), self._time_limit(), draft=True)
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)

    @extend_schema(
        request=None,
        parameters=[OpenApiParameter('task_id', str, required=True)],
        responses={200: OpenApiTypes.OBJECT},
    )
    @action(detail=False, methods=['get'])
    def solve_status(self, request):
        """Poll a background solve/dispatch task. `state` is PENDING (queued/running),
        SUCCESS, or FAILURE; on SUCCESS `result` carries the task's return value."""
        from celery.result import AsyncResult
        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response({'detail': 'task_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        res = AsyncResult(task_id)
        data = {'task_id': task_id, 'state': res.state, 'ready': res.ready()}
        if res.successful():
            data['result'] = res.result
        elif res.failed():
            data['detail'] = str(res.result)[:500]
        return Response(data)

    @extend_schema(request=None, responses={202: OpenApiTypes.OBJECT})
    @action(detail=False, methods=['post'], url_path='dispatch')
    def run_dispatch(self, request):
        """Kick off Layer-2 operator dispatch in the background. Returns a task id; poll
        `solve_status?task_id=` for the coverage summary."""
        task = run_dispatch_task.delay(str(self.tenant.id), self._time_limit())
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)

    @extend_schema(
        parameters=[
            OpenApiParameter('start', OpenApiTypes.DATE, description="Range start (inclusive). Default: 7 days ago."),
            OpenApiParameter('end', OpenApiTypes.DATE, description="Range end (inclusive). Default: today."),
        ],
        responses={200: inline_serializer(
            name="OperatorHoursReport",
            fields={
                "rows": inline_serializer(
                    name="OperatorHoursRow",
                    fields={
                        "user_id": serializers.IntegerField(),
                        "name": serializers.CharField(),
                        "on_shift_hours": serializers.FloatField(),
                        "direct_hours": serializers.FloatField(),
                    },
                    many=True,
                ),
            },
        )},
    )
    @action(detail=False, methods=['get'], url_path='operator_hours')
    def operator_hours(self, request):
        """Shop hours worked per operator over a date range, from TimeEntry —
        `on_shift_hours` (attendance) and `direct_hours` (clocked onto jobs). Scoped to
        shop-floor operators (Operator / Shift Lead groups)."""
        from datetime import date, datetime, time, timedelta
        from django.utils import timezone
        from Tracker.services.mes.labor_report import operator_hours as _report

        def _parse(s, default):
            if not s:
                return default
            try:
                return date.fromisoformat(s)
            except ValueError:
                return default

        today = timezone.localdate()
        start_d = _parse(request.query_params.get('start'), today - timedelta(days=7))
        end_d = _parse(request.query_params.get('end'), today)
        start_dt = timezone.make_aware(datetime.combine(start_d, time.min))
        end_dt = timezone.make_aware(datetime.combine(end_d + timedelta(days=1), time.min))
        return Response({'rows': _report(self.tenant, start_dt, end_dt)})

    @extend_schema(responses={200: inline_serializer(
        name="SourcingRequirements",
        fields={
            "source": inline_serializer(name="SourceRequirement", many=True, fields={
                "material": serializers.CharField(),
                "qty_short": serializers.IntegerField(),
                "need_by": serializers.DateField(allow_null=True),
                "lead_time_days": serializers.IntegerField(allow_null=True),
                "order_by": serializers.DateField(allow_null=True),
                "incoming_date": serializers.DateField(allow_null=True),
            }),
            "produce": inline_serializer(name="ProduceRequirement", many=True, fields={
                "work_order": serializers.CharField(),
                "component": serializers.CharField(),
                "qty": serializers.IntegerField(),
                "need_by": serializers.DateField(allow_null=True),
                "status": serializers.CharField(),
            }),
            "tooling": inline_serializer(name="ToolingRequirement", many=True, fields={
                "fixture": serializers.CharField(),
                "kind": serializers.CharField(),
                "need_by": serializers.DateField(allow_null=True),
                "lead_time_days": serializers.IntegerField(allow_null=True),
                "order_by": serializers.DateField(allow_null=True),
            }),
        },
    )})
    @action(detail=False, methods=['get'], url_path='requirements')
    def requirements(self, request):
        """Sourcing & production requirements for open demand — what to buy (source),
        what to make (produce), and tooling to acquire, with lead-time-driven order-by
        dates."""
        from Tracker.services.mes.requirements import sourcing_requirements
        return Response(sourcing_requirements(self.tenant))


class ScheduledTaskViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Read the scheduled tasks (Gantt rows); pin/unpin a task."""
    queryset = ScheduledTask.unscoped.select_related(
        'part__work_order', 'core__work_order', 'step__work_center',
        'machine', 'assigned_operator')
    serializer_class = ScheduledTaskSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['schedule', 'machine', 'assigned_operator', 'is_pinned', 'fence_zone']
    ordering_fields = ['start_time', 'end_time']
    ordering = ['start_time']
    action_permissions = {
        'pin': ['change_scheduledtask'], 'move': ['change_scheduledtask'],
        'move_batch': ['change_scheduledtask'], 'pin_batch': ['change_scheduledtask'],
        'batch_membership': ['change_parts'],
        'reassign_machine': ['change_scheduledtask'],
        'reassign_operator': ['change_scheduledtask'],
        'bulk_reassign_machine': ['change_scheduledtask'],
        'bulk_reassign_operator': ['change_scheduledtask'],
    }
    crud_exempt_actions = {
        'pin', 'move', 'move_batch', 'pin_batch', 'batch_membership',
        'reassign_machine', 'reassign_operator', 'reassign_options',
        'bulk_reassign_machine', 'bulk_reassign_operator',
    }

    @extend_schema(request=PinRequestSerializer, responses={200: ScheduledTaskSerializer})
    @action(detail=True, methods=['post'])
    def pin(self, request, pk=None):
        """Pin or unpin a task (planner override); marks the schedule stale so the
        next solve is known to be needed."""
        task = self.get_object()
        body = PinRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        task.is_pinned = body.validated_data['is_pinned']
        task.save(update_fields=['is_pinned'])
        ScheduleResult.objects.filter(pk=task.schedule_id).update(is_stale=True)  # tenant-safe: .objects auto-scopes; task came from the tenant-scoped queryset
        return Response(ScheduledTaskSerializer(task).data)

    @extend_schema(
        request=MoveRequestSerializer,
        responses={200: ScheduledTaskSerializer, 422: OpenApiTypes.OBJECT},
    )
    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        """Drag-to-reschedule (Layer 1). Validates the drop against the cheap local
        constraints (horizon, release, route precedence); on success pins the task at
        the new time and marks the schedule stale so the next Solve reflows the rest.
        Returns 422 with a reason when the drop violates a local constraint."""
        task = self.get_object()
        body = MoveRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            move_task(task, body.validated_data['start_time'])
        except MoveRejected as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        return Response(ScheduledTaskSerializer(task).data)

    @extend_schema(
        request=MoveBatchRequestSerializer,
        responses={200: OpenApiTypes.OBJECT, 422: OpenApiTypes.OBJECT},
    )
    @action(detail=False, methods=['post'])
    def move_batch(self, request):
        """Re-anchor a work-order batch (a WO's parts at one operation) to a new start;
        every part shifts by the same delta, keeping the batch's spacing. Validated per
        part; 422 (whole move refused) if any part breaks a local constraint."""
        body = MoveBatchRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        tasks = list(self.get_queryset().filter(pk__in=body.validated_data['task_ids']))
        if not tasks:
            return Response({'detail': 'No matching tasks.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            moved = move_batch(tasks, body.validated_data['start_time'])
        except MoveRejected as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        return Response({'moved': moved})

    @extend_schema(request=PinBatchRequestSerializer, responses={200: OpenApiTypes.OBJECT})
    @action(detail=False, methods=['post'])
    def pin_batch(self, request):
        """Pin/unpin every part of a work-order batch; marks the schedule stale."""
        body = PinBatchRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        tasks = list(self.get_queryset().filter(pk__in=body.validated_data['task_ids']))
        if not tasks:
            return Response({'detail': 'No matching tasks.'}, status=status.HTTP_404_NOT_FOUND)
        pinned = pin_batch(tasks, body.validated_data['is_pinned'])
        return Response({'pinned': pinned})

    @extend_schema(request=BatchMembershipRequestSerializer, responses={200: OpenApiTypes.OBJECT})
    @action(detail=False, methods=['post'], url_path='batch-membership')
    def batch_membership(self, request):
        """Direct-manipulation batch control. `merge=true` → rejoin the WO+step cohort:
        unpin the parts (the solver batches the unpinned cohort) and snap them onto the
        cohort's slot so the ×N cell collapses now. `merge=false` → break apart: lay the
        parts in separate slots and PIN them (separate fixed bars). Applies immediately and
        marks the schedule stale; the next Solve forms/optimizes the batch."""
        from Tracker.services.scheduling.manual_move import regroup_batch
        body = BatchMembershipRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        tasks = list(self.get_queryset().filter(
            pk__in=body.validated_data['task_ids'], part__isnull=False,
        ))
        if not tasks:
            return Response(
                {'detail': 'No matching part tasks (cores have no lot).'},
                status=status.HTTP_404_NOT_FOUND,
            )
        changed = regroup_batch(tasks, merge=body.validated_data['merge'], user=request.user)
        return Response({'changed': changed, 'merged': body.validated_data['merge']})

    @extend_schema(request=None, responses={200: OpenApiTypes.OBJECT})
    @action(detail=True, methods=['get'], url_path='reassign-options')
    def reassign_options(self, request, pk=None):
        """Machines eligible for this task's step + operators qualified for it — the
        options the detail dialog's reassign dropdowns show."""
        from Tracker.models import StepEquipmentAffinity
        from Tracker.services.training import get_qualified_users_for_step
        task = self.get_object()
        machines = [
            {'id': str(a.equipment_id), 'name': a.equipment.name}
            for a in StepEquipmentAffinity.objects.filter(step_id=task.step_id)
            .select_related('equipment')
        ]
        operators = [
            {'id': str(u.id), 'name': (u.get_full_name() or u.username)}
            for u in get_qualified_users_for_step(task.step, tenant=self.tenant)
        ]
        return Response({'machines': machines, 'operators': operators})

    @extend_schema(request=ReassignMachineRequestSerializer, responses={200: OpenApiTypes.OBJECT})
    @action(detail=True, methods=['post'], url_path='reassign-machine')
    def reassign_machine(self, request, pk=None):
        """Put this task on a specific machine (planner override) + pin it. Applies now;
        the next Solve keeps it there (machine-pin). Warns if the machine isn't eligible."""
        from Tracker.models import Equipments
        from Tracker.services.scheduling.manual_move import reassign_machine as svc
        task = self.get_object()
        body = ReassignMachineRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        # tenant-safe: .objects auto-scopes to the current tenant (request context).
        machine = Equipments.objects.filter(pk=body.validated_data['machine_id']).first()
        if machine is None:
            return Response({'detail': 'Unknown machine.'}, status=status.HTTP_400_BAD_REQUEST)
        result = svc(task, machine, user=request.user)
        return Response({**result, **ScheduledTaskSerializer(task).data})

    @extend_schema(request=ReassignOperatorRequestSerializer, responses={200: OpenApiTypes.OBJECT})
    @action(detail=True, methods=['post'], url_path='reassign-operator')
    def reassign_operator(self, request, pk=None):
        """Assign / re-assign / clear (null) the operator on this task (manual coverage).
        Applies now; warns if the operator isn't qualified for the step."""
        from django.contrib.auth import get_user_model
        from Tracker.services.scheduling.manual_move import reassign_operator as svc
        User = get_user_model()
        task = self.get_object()
        body = ReassignOperatorRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        op_id = body.validated_data['operator_id']
        operator = None
        if op_id is not None:
            operator = User.objects.filter(pk=op_id, tenant=self.tenant).first()
            if operator is None:
                return Response({'detail': 'Unknown operator.'}, status=status.HTTP_400_BAD_REQUEST)
        result = svc(task, operator, user=request.user)
        return Response({**result, **ScheduledTaskSerializer(task).data})

    @extend_schema(request=BulkReassignMachineRequestSerializer, responses={200: OpenApiTypes.OBJECT})
    @action(detail=False, methods=['post'], url_path='bulk-reassign-machine')
    def bulk_reassign_machine(self, request):
        """Move several selected tasks onto one machine (planner override) + pin them.
        Applies now; returns {changed, warnings} (a warning per distinct step the machine
        isn't authored for). The next Solve keeps them there (machine-pin)."""
        from Tracker.models import Equipments
        from Tracker.services.scheduling.manual_move import bulk_reassign_machine as svc
        body = BulkReassignMachineRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        # tenant-safe: .objects auto-scopes to the current tenant (request context).
        machine = Equipments.objects.filter(pk=body.validated_data['machine_id']).first()
        if machine is None:
            return Response({'detail': 'Unknown machine.'}, status=status.HTTP_400_BAD_REQUEST)
        tasks = list(self.get_queryset().filter(
            pk__in=body.validated_data['task_ids']).select_related('step', 'schedule'))
        if not tasks:
            return Response({'detail': 'No matching tasks.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(svc(tasks, machine, user=request.user))

    @extend_schema(request=BulkReassignOperatorRequestSerializer, responses={200: OpenApiTypes.OBJECT})
    @action(detail=False, methods=['post'], url_path='bulk-reassign-operator')
    def bulk_reassign_operator(self, request):
        """Assign / clear (null) one operator across several selected tasks — bulk manual
        coverage. Applies now; returns {changed, warnings} (warns, listing steps the
        operator isn't trained for)."""
        from django.contrib.auth import get_user_model
        from Tracker.services.scheduling.manual_move import bulk_reassign_operator as svc
        User = get_user_model()
        body = BulkReassignOperatorRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        op_id = body.validated_data['operator_id']
        operator = None
        if op_id is not None:
            operator = User.objects.filter(pk=op_id, tenant=self.tenant).first()
            if operator is None:
                return Response({'detail': 'Unknown operator.'}, status=status.HTTP_400_BAD_REQUEST)
        tasks = list(self.get_queryset().filter(
            pk__in=body.validated_data['task_ids']).select_related('step', 'schedule'))
        if not tasks:
            return Response({'detail': 'No matching tasks.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(svc(tasks, operator, user=request.user))


class FixtureViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """CRUD for shared, quantity-limited scheduling resources — fixtures, cutting tools,
    dies, and NC programs. Assigning a resource to steps makes the solver serialize those
    operations against the quantity available (cumulative capacity)."""
    queryset = Fixture.unscoped.all().prefetch_related('steps')
    serializer_class = FixtureSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = ['kind']
    search_fields = ['name']
    ordering_fields = ['name', 'kind', 'quantity']
    ordering = ['name']


class PlantCalendarExceptionViewSet(TenantScopedMixin, ListMetadataMixin,
                                    ExcelExportMixin, viewsets.ModelViewSet):
    """CRUD for plant-wide closures — holidays, shutdowns, inventory days. The solver
    blocks every machine and treats operators as absent during these."""
    queryset = PlantCalendarException.unscoped.all()
    serializer_class = PlantCalendarExceptionSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = ['kind', 'is_active']
    search_fields = ['name']
    ordering_fields = ['start_time', 'name', 'kind']
    ordering = ['start_time']


class LaborCalendarBlockViewSet(TenantScopedMixin, ListMetadataMixin,
                                ExcelExportMixin, viewsets.ModelViewSet):
    """CRUD for operator non-working time — PTO / sick / training / meetings / breaks,
    one-off or weekly, company-wide (user null) or per person. Operators only; machines
    keep running (only PlantCalendarException stops machines)."""
    queryset = LaborCalendarBlock.unscoped.all().select_related('user')
    serializer_class = LaborCalendarBlockSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = ['kind', 'recurrence', 'user', 'is_active']
    search_fields = ['reason']
    ordering_fields = ['start_time', 'kind', 'recurrence']
    ordering = ['start_time']


class OvertimeWindowViewSet(TenantScopedMixin, ListMetadataMixin,
                            ExcelExportMixin, viewsets.ModelViewSet):
    """CRUD for additive shop-open time — overtime / extra / weekend shifts, one-off or
    weekly, company-wide. The solver adds these to operator + attended-machine
    availability (plant closures still win)."""
    queryset = OvertimeWindow.unscoped.all().select_related('shift')
    serializer_class = OvertimeWindowSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = ['recurrence', 'shift', 'is_active']
    search_fields = ['reason']
    ordering_fields = ['start_date', 'recurrence']
    ordering = ['start_date']
