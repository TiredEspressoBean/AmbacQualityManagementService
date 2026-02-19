# viewsets/mes_standard.py - MES Standard Tier ViewSets
"""
ViewSets for MES Standard tier models:
- Scheduling: WorkCenter, Shift, ScheduleSlot
- Downtime: DowntimeEvent
- Traceability: MaterialLot, MaterialUsage, BOM, BOMLine, AssemblyUsage
- Labor: TimeEntry
"""
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from Tracker.models import (
    WorkCenter, Shift, ScheduleSlot, DowntimeEvent,
    MaterialLot, MaterialUsage, TimeEntry,
    BOM, BOMLine, AssemblyUsage,
)
from Tracker.serializers.mes_standard import (
    WorkCenterSerializer, WorkCenterSelectSerializer,
    ShiftSerializer,
    ScheduleSlotSerializer,
    DowntimeEventSerializer,
    MaterialLotSerializer, MaterialLotSplitSerializer,
    MaterialUsageSerializer,
    TimeEntrySerializer, ClockInSerializer,
    BOMSerializer, BOMListSerializer, BOMLineSerializer,
    AssemblyUsageSerializer, AssemblyRemoveSerializer,
)
from .base import TenantScopedMixin
from .core import ExcelExportMixin


# ===== WORK CENTER VIEWSETS =====

class WorkCenterViewSet(TenantScopedMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """Work center management"""
    queryset = WorkCenter.objects.all()
    serializer_class = WorkCenterSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'code', 'created_at']
    ordering = ['code']


class WorkCenterSelectViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Lightweight work center endpoint for dropdowns"""
    queryset = WorkCenter.objects.all()
    serializer_class = WorkCenterSelectSerializer
    pagination_class = None


# ===== SHIFT VIEWSETS =====

class ShiftViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Shift definition management"""
    queryset = Shift.objects.all()
    serializer_class = ShiftSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['is_active']
    ordering_fields = ['start_time', 'name']
    ordering = ['start_time']


# ===== SCHEDULE SLOT VIEWSETS =====

class ScheduleSlotViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Production schedule management"""
    queryset = ScheduleSlot.objects.select_related('work_center', 'shift', 'work_order')
    serializer_class = ScheduleSlotSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['work_center', 'shift', 'work_order', 'status', 'scheduled_date']
    ordering_fields = ['scheduled_date', 'scheduled_start']
    ordering = ['scheduled_date', 'scheduled_start']

    @extend_schema(
        request=inline_serializer(name="StartSlotInput", fields={}),
        responses={200: ScheduleSlotSerializer}
    )
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Mark schedule slot as started"""
        slot = self.get_object()
        if slot.status != 'scheduled':
            return Response(
                {'detail': f'Cannot start slot with status "{slot.status}"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        slot.status = 'in_progress'
        slot.actual_start = timezone.now()
        slot.save()
        return Response(ScheduleSlotSerializer(slot, context={'request': request}).data)

    @extend_schema(
        request=inline_serializer(name="CompleteSlotInput", fields={}),
        responses={200: ScheduleSlotSerializer}
    )
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark schedule slot as completed"""
        slot = self.get_object()
        if slot.status != 'in_progress':
            return Response(
                {'detail': f'Cannot complete slot with status "{slot.status}"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        slot.status = 'completed'
        slot.actual_end = timezone.now()
        slot.save()
        return Response(ScheduleSlotSerializer(slot, context={'request': request}).data)


# ===== DOWNTIME EVENT VIEWSETS =====

class DowntimeEventViewSet(TenantScopedMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """Equipment/work center downtime tracking"""
    queryset = DowntimeEvent.objects.select_related(
        'equipment', 'work_center', 'work_order', 'reported_by', 'resolved_by'
    )
    serializer_class = DowntimeEventSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['equipment', 'work_center', 'category', 'work_order']
    ordering_fields = ['start_time', 'end_time', 'category']
    ordering = ['-start_time']

    def perform_create(self, serializer):
        serializer.save(reported_by=self.request.user)

    @extend_schema(
        request=inline_serializer(name="ResolveDowntimeInput", fields={}),
        responses={200: DowntimeEventSerializer}
    )
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Mark downtime event as resolved"""
        event = self.get_object()
        if event.end_time:
            return Response(
                {'detail': 'Downtime event already resolved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        event.end_time = timezone.now()
        event.resolved_by = request.user
        event.save()
        return Response(DowntimeEventSerializer(event, context={'request': request}).data)


# ===== MATERIAL LOT VIEWSETS =====

class MaterialLotViewSet(TenantScopedMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """Material lot tracking with split capability"""
    queryset = MaterialLot.objects.select_related('material_type', 'supplier', 'parent_lot', 'received_by')
    serializer_class = MaterialLotSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    search_fields = ['lot_number', 'supplier_lot_number', 'material_description']
    filterset_fields = ['status', 'supplier', 'material_type']
    ordering_fields = ['received_date', 'lot_number', 'expiration_date']
    ordering = ['-received_date']

    def perform_create(self, serializer):
        # Auto-set received_by to current user, initialize quantity_remaining
        serializer.save(
            received_by=self.request.user,
            quantity_remaining=serializer.validated_data.get('quantity', 0)
        )

    @extend_schema(request=MaterialLotSplitSerializer, responses={201: MaterialLotSerializer})
    @action(detail=True, methods=['post'])
    def split(self, request, pk=None):
        """Split a lot into a child lot"""
        lot = self.get_object()
        serializer = MaterialLotSplitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            child_lot = lot.split(
                quantity=serializer.validated_data['quantity'],
                reason=serializer.validated_data.get('reason', '')
            )
            return Response(
                MaterialLotSerializer(child_lot, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ===== MATERIAL USAGE VIEWSETS =====

class MaterialUsageViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Material consumption records (read-only, created via lot consumption)"""
    queryset = MaterialUsage.objects.select_related('lot', 'part', 'work_order', 'step', 'consumed_by')
    serializer_class = MaterialUsageSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['lot', 'part', 'work_order', 'is_substitute']
    ordering_fields = ['consumed_at']
    ordering = ['-consumed_at']


# ===== TIME ENTRY VIEWSETS =====

class TimeEntryViewSet(TenantScopedMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """Labor time tracking with clock-in/out"""
    queryset = TimeEntry.objects.select_related(
        'user', 'part', 'work_order', 'step', 'equipment', 'work_center'
    )
    serializer_class = TimeEntrySerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['user', 'entry_type', 'work_order', 'approved']
    ordering_fields = ['start_time', 'end_time', 'entry_type']
    ordering = ['-start_time']

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(request=ClockInSerializer, responses={201: TimeEntrySerializer})
    @action(detail=False, methods=['post'])
    def clock_in(self, request):
        """Start a new time entry for the current user"""
        serializer = ClockInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Use the viewset's get_serializer to ensure proper tenant handling
        entry_serializer = self.get_serializer(data={
            'entry_type': serializer.validated_data['entry_type'],
            'start_time': timezone.now(),
            **{k: v.pk if hasattr(v, 'pk') else v for k, v in serializer.validated_data.items() if k != 'entry_type'}
        })
        entry_serializer.is_valid(raise_exception=True)
        entry_serializer.save(user=request.user)

        return Response(
            TimeEntrySerializer(entry_serializer.instance, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

    @extend_schema(
        request=inline_serializer(name="ClockOutInput", fields={"notes": serializers.CharField(required=False)}),
        responses={200: TimeEntrySerializer}
    )
    @action(detail=True, methods=['post'])
    def clock_out(self, request, pk=None):
        """End a time entry"""
        entry = self.get_object()
        if entry.end_time:
            return Response({'detail': 'Already clocked out'}, status=status.HTTP_400_BAD_REQUEST)

        entry.end_time = timezone.now()
        if 'notes' in request.data:
            entry.notes = request.data['notes']
        entry.save()
        return Response(TimeEntrySerializer(entry, context={'request': request}).data)

    @extend_schema(
        request=inline_serializer(name="ApproveTimeInput", fields={}),
        responses={200: TimeEntrySerializer}
    )
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a time entry"""
        entry = self.get_object()
        if entry.approved:
            return Response({'detail': 'Time entry already approved'}, status=status.HTTP_400_BAD_REQUEST)
        entry.approved = True
        entry.approved_by = request.user
        entry.approved_at = timezone.now()
        entry.save()
        return Response(TimeEntrySerializer(entry, context={'request': request}).data)


# ===== BOM VIEWSETS =====

class BOMViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Bill of Materials management"""
    queryset = BOM.objects.select_related('part_type', 'approved_by').prefetch_related('lines')
    serializer_class = BOMSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['part_type', 'bom_type', 'status']
    ordering_fields = ['part_type__name', 'revision', 'effective_date']
    ordering = ['part_type__name', '-revision']

    def get_serializer_class(self):
        if self.action == 'list':
            return BOMListSerializer
        return BOMSerializer

    @extend_schema(
        request=inline_serializer(name="ReleaseBOMInput", fields={}),
        responses={200: BOMSerializer}
    )
    @action(detail=True, methods=['post'])
    def release(self, request, pk=None):
        """Release a BOM for production use"""
        bom = self.get_object()
        if bom.status != 'draft':
            return Response({'detail': 'Only draft BOMs can be released'}, status=status.HTTP_400_BAD_REQUEST)

        bom.status = 'released'
        bom.effective_date = timezone.now().date()
        bom.approved_by = request.user
        bom.approved_at = timezone.now()
        bom.save()
        return Response(BOMSerializer(bom, context={'request': request}).data)

    @extend_schema(
        request=inline_serializer(name="ObsoleteBOMInput", fields={}),
        responses={200: BOMSerializer}
    )
    @action(detail=True, methods=['post'])
    def obsolete(self, request, pk=None):
        """Mark a BOM as obsolete"""
        bom = self.get_object()
        if bom.status == 'obsolete':
            return Response({'detail': 'BOM is already obsolete'}, status=status.HTTP_400_BAD_REQUEST)
        bom.status = 'obsolete'
        bom.obsolete_date = timezone.now().date()
        bom.save()
        return Response(BOMSerializer(bom, context={'request': request}).data)


class BOMLineViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """BOM line item management"""
    queryset = BOMLine.objects.select_related('bom', 'component_type')
    serializer_class = BOMLineSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['bom', 'component_type', 'is_optional']
    ordering_fields = ['line_number', 'component_type__name']
    ordering = ['bom', 'line_number']


# ===== ASSEMBLY USAGE VIEWSETS =====

class AssemblyUsageViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Assembly component tracking"""
    queryset = AssemblyUsage.objects.select_related(
        'assembly', 'component', 'bom_line', 'installed_by', 'removed_by', 'step'
    )
    serializer_class = AssemblyUsageSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['assembly', 'component', 'bom_line']
    ordering_fields = ['installed_at', 'removed_at']
    ordering = ['-installed_at']

    def perform_create(self, serializer):
        serializer.save(installed_by=self.request.user)

    @extend_schema(request=AssemblyRemoveSerializer, responses={200: AssemblyUsageSerializer})
    @action(detail=True, methods=['post'])
    def remove(self, request, pk=None):
        """Remove a component from an assembly"""
        usage = self.get_object()
        if usage.removed_at:
            return Response({'detail': 'Component already removed'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = AssemblyRemoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        usage.remove(user=request.user, reason=serializer.validated_data.get('reason', ''))
        return Response(AssemblyUsageSerializer(usage, context={'request': request}).data)
