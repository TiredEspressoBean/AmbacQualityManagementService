# viewsets/calibration.py - Calibration Management ViewSets
from datetime import timedelta

from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response

from Tracker.models import CalibrationRecord, Equipments
from Tracker.serializers.calibration import (
    CalibrationRecordSerializer,
    CalibrationStatsSerializer,
)
from .base import TenantScopedMixin
from .core import ExcelExportMixin, ListMetadataMixin


@extend_schema_view(
    list=extend_schema(
        description="List calibration records with filtering",
        parameters=[
            OpenApiParameter(name='equipment', description='Filter by equipment ID', required=False, type=str),
            OpenApiParameter(name='result', description='Filter by result (pass, fail, limited)', required=False, type=str),
            OpenApiParameter(name='calibration_type', description='Filter by calibration type', required=False, type=str),
            OpenApiParameter(name='status', description='Filter by status (current, due_soon, overdue, failed)', required=False, type=str),
        ]
    ),
    create=extend_schema(description="Create a new calibration record"),
    retrieve=extend_schema(description="Retrieve a specific calibration record"),
    update=extend_schema(description="Update a calibration record"),
    partial_update=extend_schema(description="Partially update a calibration record"),
    destroy=extend_schema(description="Soft delete a calibration record")
)
class CalibrationRecordViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing calibration records.

    Calibration records track calibration events for equipment, including:
    - Calibration date and due date
    - Result (pass, fail, limited)
    - Calibration type (scheduled, initial, after repair, etc.)
    - Traceability information (certificate number, standards used)
    - As-found/as-left status
    """
    queryset = CalibrationRecord.objects.all()
    serializer_class = CalibrationRecordSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['equipment', 'result', 'calibration_type']
    search_fields = [
        'equipment__name', 'certificate_number', 'performed_by',
        'external_lab', 'standards_used', 'notes'
    ]
    ordering_fields = ['calibration_date', 'due_date', 'created_at']
    ordering = ['-calibration_date']
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return CalibrationRecord.objects.none()

        qs = super().get_queryset()
        qs = qs.select_related('equipment', 'equipment__equipment_type')

        # Filter by computed status if provided
        status_filter = self.request.query_params.get('status')
        if status_filter:
            today = timezone.now().date()
            thirty_days = today + timedelta(days=30)

            if status_filter == 'current':
                # Current: not overdue and not failed
                qs = qs.filter(due_date__gte=today).exclude(result='fail')
            elif status_filter == 'due_soon':
                # Due soon: within 30 days but not overdue
                qs = qs.filter(
                    due_date__lte=thirty_days,
                    due_date__gte=today
                ).exclude(result='fail')
            elif status_filter == 'overdue':
                # Overdue: past due date
                qs = qs.filter(due_date__lt=today)
            elif status_filter == 'failed':
                # Failed result
                qs = qs.filter(result='fail')

        return qs

    @extend_schema(
        description="Get calibration records due within N days (default 30)",
        parameters=[
            OpenApiParameter(name='days', description='Days until due', required=False, type=int, default=30),
        ],
        responses={200: CalibrationRecordSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='due-soon')
    def due_soon(self, request):
        """Return calibration records due within N days."""
        days = int(request.query_params.get('days', 30))
        qs = CalibrationRecord.objects.due_soon(within_days=days)

        # Apply tenant scoping
        if hasattr(self, 'apply_tenant_scope'):
            qs = self.apply_tenant_scope(qs)

        qs = qs.select_related('equipment', 'equipment__equipment_type').order_by('due_date')
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @extend_schema(
        description="Get all overdue calibration records",
        responses={200: CalibrationRecordSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='overdue')
    def overdue(self, request):
        """Return all overdue calibration records."""
        qs = CalibrationRecord.objects.overdue()

        # Apply tenant scoping
        if hasattr(self, 'apply_tenant_scope'):
            qs = self.apply_tenant_scope(qs)

        qs = qs.select_related('equipment', 'equipment__equipment_type').order_by('due_date')
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @extend_schema(
        description="Get calibration statistics summary",
        responses={200: CalibrationStatsSerializer}
    )
    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """Return calibration statistics summary."""
        today = timezone.now().date()
        thirty_days = today + timedelta(days=30)

        # Get base queryset with tenant scoping
        qs = self.get_queryset()

        # Get latest calibration per equipment for accurate counts
        latest_per_equipment = qs.latest_per_equipment() if hasattr(qs, 'latest_per_equipment') else qs

        # Count equipment with calibration records
        total_equipment = Equipments.objects.filter(
            calibration_records__in=qs
        ).distinct().count()

        # Current calibrations (not overdue, not failed)
        current = latest_per_equipment.filter(
            due_date__gte=today
        ).exclude(result='fail').count()

        # Due soon (within 30 days)
        due_soon = latest_per_equipment.filter(
            due_date__lte=thirty_days,
            due_date__gte=today
        ).exclude(result='fail').count()

        # Overdue
        overdue = latest_per_equipment.filter(due_date__lt=today).count()

        # Compliance rate
        compliance_rate = 0.0
        if total_equipment > 0:
            compliance_rate = round((current / total_equipment) * 100, 1)

        return Response({
            'total_equipment': total_equipment,
            'current_calibrations': current,
            'due_soon': due_soon,
            'overdue': overdue,
            'compliance_rate': compliance_rate,
        })

    @extend_schema(
        description="Get calibration history for a specific piece of equipment",
        parameters=[
            OpenApiParameter(name='equipment_id', description='Equipment ID', required=True, type=str),
        ],
        responses={200: CalibrationRecordSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='for-equipment')
    def for_equipment(self, request):
        """Return all calibration records for a specific piece of equipment."""
        equipment_id = request.query_params.get('equipment_id')
        if not equipment_id:
            return Response({'error': 'equipment_id is required'}, status=400)

        qs = self.get_queryset().filter(equipment_id=equipment_id).order_by('-calibration_date')
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)
