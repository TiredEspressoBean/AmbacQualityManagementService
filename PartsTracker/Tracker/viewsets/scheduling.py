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
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from Tracker.models.scheduling import ScheduledTask, ScheduleResult
from Tracker.serializers.scheduling import (
    PinRequestSerializer, ScheduledTaskSerializer, ScheduleResultSerializer,
)
from Tracker.services.scheduling.dispatch import dispatch_operators
from Tracker.services.scheduling.solver import solve_schedule
from .base import TenantScopedMixin

_SYNC_TIME_LIMIT_SECONDS = 30   # sync request cap for solve + dispatch; async is the follow-on


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

    @extend_schema(request=None, responses={201: ScheduleResultSerializer})
    @action(detail=False, methods=['post'])
    def solve(self, request):
        """Run the Layer-1 machine solver, superseding the previous active schedule."""
        result = solve_schedule(self.tenant, time_limit_seconds=_SYNC_TIME_LIMIT_SECONDS)
        return Response(ScheduleResultSerializer(result).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=None,
        responses={200: inline_serializer(name='DispatchResult', fields={
            'schedule': serializers.UUIDField(),
            'attended': serializers.IntegerField(),
            'covered': serializers.IntegerField(),
            'uncovered': serializers.IntegerField(),
        })},
    )
    @action(detail=False, methods=['post'], url_path='dispatch')
    def run_dispatch(self, request):
        """Assign operators to the active schedule's attended tasks (Layer 2)."""
        summary = dispatch_operators(self.tenant, time_limit_seconds=_SYNC_TIME_LIMIT_SECONDS)
        if summary is None:
            return Response({'detail': 'No active schedule to dispatch.'},
                            status=status.HTTP_404_NOT_FOUND)
        return Response({
            'schedule': summary.schedule_id, 'attended': summary.attended,
            'covered': summary.covered, 'uncovered': summary.uncovered,
        })


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
    action_permissions = {'pin': ['change_scheduledtask']}
    crud_exempt_actions = {'pin'}

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
