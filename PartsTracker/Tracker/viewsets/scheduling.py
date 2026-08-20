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
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from Tracker.models.scheduling import ScheduledTask, ScheduleResult
from Tracker.serializers.scheduling import (
    MoveBatchRequestSerializer, MoveRequestSerializer, PinBatchRequestSerializer,
    PinRequestSerializer, ScheduledTaskSerializer, ScheduleResultSerializer,
)
from Tracker.services.scheduling.manual_move import (
    MoveRejected, move_batch, move_task, pin_batch,
)
from Tracker.tasks import run_dispatch_task, run_solve_task
from .base import TenantScopedMixin

# Solve + dispatch run in the background (Celery) so they can take the minutes a large
# schedule needs to converge; the request returns a task id to poll. This time limit is
# passed to CP-SAT (best-so-far returned when it elapses).
_ASYNC_TIME_LIMIT_SECONDS = 180


class ScheduleViewSet(TenantScopedMixin, viewsets.GenericViewSet):
    """Run the solver / dispatch and read the active schedule."""
    queryset = ScheduleResult.unscoped.all()
    serializer_class = ScheduleResultSerializer
    action_permissions = {'run_dispatch': ['change_scheduledtask']}
    crud_exempt_actions = {'run_dispatch'}

    @extend_schema(request=None, responses={200: ScheduleResultSerializer})
    @action(detail=False, methods=['get'])
    def current(self, request):
        """The active schedule's run metadata, or 404 if none exists yet."""
        sched = self.get_queryset().filter(is_active=True).order_by('-created_at').first()
        if sched is None:
            return Response({'detail': 'No active schedule.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(self.get_serializer(sched).data)

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
        """Kick off the Layer-1 machine solve in the background. Returns a task id; poll
        `solve_status?task_id=` for state, then re-read `current`."""
        task = run_solve_task.delay(str(self.tenant.id), _ASYNC_TIME_LIMIT_SECONDS)
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
        task = run_dispatch_task.delay(str(self.tenant.id), _ASYNC_TIME_LIMIT_SECONDS)
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)


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
    }
    crud_exempt_actions = {'pin', 'move', 'move_batch', 'pin_batch'}

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
