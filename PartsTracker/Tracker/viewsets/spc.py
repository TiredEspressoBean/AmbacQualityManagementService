"""
SPC (Statistical Process Control) ViewSets

Provides API endpoints for SPC data:
- Process/Step/Measurement hierarchy for navigation
- Measurement results for control charts
- Process capability calculations (Cpk/Ppk)
- SPC Baseline management (frozen control limits)
"""
import math
from datetime import timedelta

from django.db.models import F, Avg, StdDev, Count, Min, Max
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_field, OpenApiParameter, inline_serializer
from rest_framework import viewsets, serializers, status, filters
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from Tracker.models import (
    Processes,
    Steps,
    MeasurementDefinition,
    MeasurementResult,
    QualityReports,
    Parts,
    WorkOrder,
)
from Tracker.models.spc import SPCBaseline, BaselineStatus
from Tracker.serializers.spc import (
    SPCBaselineSerializer,
    SPCBaselineListSerializer,
    SPCBaselineFreezeSerializer,
)
from .core import ExcelExportMixin, ListMetadataMixin
from .base import TenantScopedMixin


# =============================================================================
# SERIALIZERS
# =============================================================================

class MeasurementDefinitionSPCSerializer(serializers.ModelSerializer):
    """Measurement definition for SPC dropdowns."""

    class Meta:
        model = MeasurementDefinition
        fields = ['id', 'label', 'type', 'unit', 'nominal', 'upper_tol', 'lower_tol']


class StepSPCSerializer(serializers.ModelSerializer):
    """Step with its measurement definitions for SPC."""
    measurements = MeasurementDefinitionSPCSerializer(
        source='measurement_definitions',
        many=True,
        read_only=True
    )

    class Meta:
        model = Steps
        fields = ['id', 'name', 'measurements']


class ProcessStepSPCSerializer(serializers.Serializer):
    """ProcessStep with nested step data for SPC hierarchy."""
    id = serializers.UUIDField(source='step.id')
    name = serializers.CharField(source='step.name')
    order = serializers.IntegerField()
    measurements = MeasurementDefinitionSPCSerializer(
        source='step.measurement_definitions',
        many=True,
        read_only=True
    )


class ProcessSPCSerializer(serializers.ModelSerializer):
    """Process with steps for SPC hierarchy."""
    steps = serializers.SerializerMethodField()
    part_type_name = serializers.CharField(source='part_type.name', read_only=True)

    class Meta:
        model = Processes
        fields = ['id', 'name', 'part_type_name', 'steps']

    @extend_schema_field(ProcessStepSPCSerializer(many=True))
    def get_steps(self, obj):
        """Get steps ordered by ProcessStep.order"""
        from Tracker.models import ProcessStep
        process_steps = ProcessStep.objects.filter(
            process=obj
        ).select_related('step').prefetch_related(
            'step__measurement_definitions'
        ).order_by('order')
        return ProcessStepSPCSerializer(process_steps, many=True).data


class MeasurementDataPointSerializer(serializers.Serializer):
    """Individual measurement data point for SPC charts."""
    id = serializers.UUIDField()
    value = serializers.FloatField()
    timestamp = serializers.DateTimeField()
    report_id = serializers.UUIDField()
    part_erp_id = serializers.CharField()
    operator_name = serializers.CharField(allow_null=True)
    is_within_spec = serializers.BooleanField()


class SPCDataResponseSerializer(serializers.Serializer):
    """Response format for SPC data endpoint."""
    definition = MeasurementDefinitionSPCSerializer()
    process_name = serializers.CharField()
    step_name = serializers.CharField()
    data_points = MeasurementDataPointSerializer(many=True)
    statistics = serializers.DictField()


# =============================================================================
# VIEWSETS
# =============================================================================

class SPCViewSet(TenantScopedMixin, viewsets.GenericViewSet):
    """
    ViewSet for Statistical Process Control data.

    Endpoints:
        GET /api/spc/hierarchy/ - Get process/step/measurement tree for navigation
        GET /api/spc/data/ - Get measurement data for control charts
        GET /api/spc/capability/ - Get process capability metrics (Cpk/Ppk)
    """
    permission_classes = [IsAuthenticated]
    queryset = MeasurementResult.objects.none()  # For drf-spectacular schema generation
    pagination_class = None  # Disable pagination - these endpoints return custom responses

    @extend_schema(responses={200: ProcessSPCSerializer(many=True)})
    @action(detail=False, methods=['get'], url_path='hierarchy')
    def hierarchy(self, request):
        """
        Get the full process → step → measurement hierarchy.

        Used to populate the SPC page dropdowns.
        Only returns processes that have steps with numeric measurement definitions.

        Response:
        [
            {
                "id": "019c4a2b-...",
                "name": "CNC Machining",
                "part_type_name": "Valve Body",
                "steps": [
                    {
                        "id": "019c4a3f-...",
                        "name": "Rough Turning",
                        "order": 1,
                        "measurements": [
                            {
                                "id": "019c4a5d-...",
                                "label": "Outer Diameter",
                                "type": "NUMERIC",
                                "unit": "mm",
                                "nominal": 25.0,
                                "upper_tol": 0.1,
                                "lower_tol": 0.1
                            }
                        ]
                    }
                ]
            }
        ]
        """
        # Get processes that have steps with numeric measurements
        # Uses qs_for_user() for tenant-scoped queries
        # Note: Steps are linked via ProcessStep through model
        processes = self.qs_for_user(Processes).filter(
            archived=False,
            process_steps__step__measurement_definitions__type='NUMERIC',
            process_steps__step__archived=False,
        ).distinct().prefetch_related(
            'part_type',
            'process_steps__step',
            'process_steps__step__measurement_definitions',
        ).order_by('name')

        # Filter to only include steps with numeric measurements
        result = []
        for process in processes:
            process_data = ProcessSPCSerializer(process).data
            # Filter steps to only those with numeric measurements
            process_data['steps'] = [
                step for step in process_data['steps']
                if any(m['type'] == 'NUMERIC' for m in step['measurements'])
            ]
            # Filter measurements to only numeric ones
            for step in process_data['steps']:
                step['measurements'] = [
                    m for m in step['measurements']
                    if m['type'] == 'NUMERIC'
                ]
            if process_data['steps']:
                result.append(process_data)

        return Response(result)

    @extend_schema(
        parameters=[
            OpenApiParameter(name='measurement_id', type=str, required=True, description='UUID of the MeasurementDefinition'),
            OpenApiParameter(name='days', type=int, required=False, default=90, description='Number of days of data to return'),
            OpenApiParameter(name='limit', type=int, required=False, default=500, description='Max number of data points'),
        ],
        responses={200: SPCDataResponseSerializer}
    )
    @action(detail=False, methods=['get'], url_path='data')
    def data(self, request):
        """
        Get measurement data for SPC control charts.

        Query params:
            measurement_id (required): ID of the MeasurementDefinition
            days (optional): Number of days of data to return (default: 90)
            limit (optional): Max number of data points (default: 500)

        Response:
        {
            "definition": { ... measurement definition ... },
            "process_name": "CNC Machining",
            "step_name": "Rough Turning",
            "data_points": [
                {
                    "id": "019c4a7e-...",
                    "value": 25.02,
                    "timestamp": "2025-01-15T10:30:00Z",
                    "report_id": "019c4a8f-...",
                    "part_erp_id": "PART-001",
                    "operator_name": "John Smith",
                    "is_within_spec": true
                }
            ],
            "statistics": {
                "count": 150,
                "mean": 25.01,
                "std_dev": 0.03,
                "min": 24.95,
                "max": 25.08,
                "within_spec_count": 148,
                "out_of_spec_count": 2
            }
        }
        """
        measurement_id = request.query_params.get('measurement_id')
        if not measurement_id:
            return Response(
                {"error": "measurement_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Filter by tenant for multi-tenancy security using qs_for_user()
        try:
            definition = self.qs_for_user(MeasurementDefinition).select_related(
                'step', 'step__part_type'
            ).get(id=measurement_id)
        except MeasurementDefinition.DoesNotExist:
            return Response(
                {"error": "Measurement definition not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get query params
        days = int(request.query_params.get('days', 90))
        limit = int(request.query_params.get('limit', 500))

        # Calculate date range
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        # Query measurement results - filter by tenant using qs_for_user()
        results = self.qs_for_user(MeasurementResult).filter(
            definition_id=measurement_id,
            value_numeric__isnull=False,
            report__created_at__gte=start_date,
            report__created_at__lte=end_date,
            archived=False,
        ).select_related(
            'report',
            'report__part',
            'created_by',
        ).order_by('report__created_at')[:limit]

        # Build data points
        data_points = []
        for result in results:
            data_points.append({
                'id': result.id,
                'value': result.value_numeric,
                'timestamp': result.report.created_at,
                'report_id': result.report_id,
                'part_erp_id': result.report.part.ERP_id if result.report.part else 'N/A',
                'operator_name': result.created_by.get_full_name() if result.created_by else None,
                'is_within_spec': result.is_within_spec,
            })

        # Calculate statistics
        if data_points:
            values = [dp['value'] for dp in data_points]
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1) if len(values) > 1 else 0
            std_dev = math.sqrt(variance)
            within_spec = sum(1 for dp in data_points if dp['is_within_spec'])

            statistics = {
                'count': len(values),
                'mean': round(mean, 6),
                'std_dev': round(std_dev, 6),
                'min': round(min(values), 6),
                'max': round(max(values), 6),
                'within_spec_count': within_spec,
                'out_of_spec_count': len(values) - within_spec,
            }
        else:
            statistics = {
                'count': 0,
                'mean': None,
                'std_dev': None,
                'min': None,
                'max': None,
                'within_spec_count': 0,
                'out_of_spec_count': 0,
            }

        # Get process name from ProcessStep (step can be in multiple processes)
        process_name = None
        if definition.step:
            from Tracker.models import ProcessStep
            ps = self.qs_for_user(ProcessStep).filter(step=definition.step).first()
            if ps and ps.process:
                process_name = ps.process.name

        return Response({
            'definition': MeasurementDefinitionSPCSerializer(definition).data,
            'process_name': process_name,
            'step_name': definition.step.name,
            'data_points': data_points,
            'statistics': statistics,
        })

    @extend_schema(
        parameters=[
            OpenApiParameter(name='measurement_id', type=str, required=True, description='UUID of the MeasurementDefinition'),
            OpenApiParameter(name='days', type=int, required=False, default=90, description='Number of days of data'),
            OpenApiParameter(name='subgroup_size', type=int, required=False, default=5, description='Size for subgroup calculations'),
        ],
        responses={200: inline_serializer(
            name='SPCCapabilityResponse',
            fields={
                'definition': MeasurementDefinitionSPCSerializer(),
                'sample_size': serializers.IntegerField(),
                'subgroup_size': serializers.IntegerField(),
                'num_subgroups': serializers.IntegerField(),
                'usl': serializers.FloatField(),
                'lsl': serializers.FloatField(),
                'mean': serializers.FloatField(),
                'std_dev_within': serializers.FloatField(),
                'std_dev_overall': serializers.FloatField(),
                'cp': serializers.FloatField(allow_null=True),
                'cpk': serializers.FloatField(allow_null=True),
                'pp': serializers.FloatField(allow_null=True),
                'ppk': serializers.FloatField(allow_null=True),
                'interpretation': serializers.CharField(),
            }
        )}
    )
    @action(detail=False, methods=['get'], url_path='capability')
    def capability(self, request):
        """
        Calculate process capability metrics (Cp, Cpk, Pp, Ppk).

        Query params:
            measurement_id (required): ID of the MeasurementDefinition
            days (optional): Number of days of data (default: 90)
            subgroup_size (optional): Size for subgroup calculations (default: 5)

        Response:
        {
            "definition": { ... },
            "sample_size": 150,
            "usl": 25.1,
            "lsl": 24.9,
            "mean": 25.01,
            "std_dev_within": 0.025,
            "std_dev_overall": 0.030,
            "cp": 1.33,
            "cpk": 1.20,
            "pp": 1.11,
            "ppk": 1.00,
            "interpretation": "Process is capable but not centered"
        }
        """
        measurement_id = request.query_params.get('measurement_id')
        if not measurement_id:
            return Response(
                {"error": "measurement_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Filter by tenant using qs_for_user()
        try:
            definition = self.qs_for_user(MeasurementDefinition).get(id=measurement_id)
        except MeasurementDefinition.DoesNotExist:
            return Response(
                {"error": "Measurement definition not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get query params
        days = int(request.query_params.get('days', 90))
        subgroup_size = int(request.query_params.get('subgroup_size', 5))

        # Calculate date range
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        # Get all values - filter by tenant using qs_for_user()
        values = list(self.qs_for_user(MeasurementResult).filter(
            definition_id=measurement_id,
            value_numeric__isnull=False,
            report__created_at__gte=start_date,
            report__created_at__lte=end_date,
            archived=False,
        ).values_list('value_numeric', flat=True).order_by('report__created_at'))

        if len(values) < 2:
            return Response({
                'definition': MeasurementDefinitionSPCSerializer(definition).data,
                'sample_size': len(values),
                'error': 'Insufficient data for capability analysis (need at least 2 measurements)',
            })

        # Calculate spec limits
        nominal = float(definition.nominal) if definition.nominal else None
        upper_tol = float(definition.upper_tol) if definition.upper_tol else None
        lower_tol = float(definition.lower_tol) if definition.lower_tol else None

        if nominal is None or upper_tol is None or lower_tol is None:
            return Response({
                'definition': MeasurementDefinitionSPCSerializer(definition).data,
                'sample_size': len(values),
                'error': 'Measurement definition missing nominal or tolerance values',
            })

        usl = nominal + upper_tol
        lsl = nominal - lower_tol

        # Calculate statistics
        n = len(values)
        mean = sum(values) / n

        # Overall standard deviation (for Pp/Ppk)
        variance_overall = sum((v - mean) ** 2 for v in values) / (n - 1)
        std_dev_overall = math.sqrt(variance_overall)

        # Within-subgroup standard deviation (for Cp/Cpk)
        # Using average range method with d2 factor
        d2_factors = {2: 1.128, 3: 1.693, 4: 2.059, 5: 2.326, 6: 2.534, 7: 2.704, 8: 2.847, 9: 2.970, 10: 3.078}
        d2 = d2_factors.get(subgroup_size, 2.326)  # Default to n=5

        # Calculate ranges for subgroups
        ranges = []
        for i in range(0, n - subgroup_size + 1, subgroup_size):
            subgroup = values[i:i + subgroup_size]
            if len(subgroup) == subgroup_size:
                ranges.append(max(subgroup) - min(subgroup))

        if ranges:
            r_bar = sum(ranges) / len(ranges)
            std_dev_within = r_bar / d2
        else:
            std_dev_within = std_dev_overall  # Fallback

        # Calculate capability indices
        # Cp = (USL - LSL) / (6 * sigma_within)
        # Cpk = min((USL - mean) / (3 * sigma_within), (mean - LSL) / (3 * sigma_within))
        # Pp = (USL - LSL) / (6 * sigma_overall)
        # Ppk = min((USL - mean) / (3 * sigma_overall), (mean - LSL) / (3 * sigma_overall))

        if std_dev_within > 0:
            cp = (usl - lsl) / (6 * std_dev_within)
            cpu = (usl - mean) / (3 * std_dev_within)
            cpl = (mean - lsl) / (3 * std_dev_within)
            cpk = min(cpu, cpl)
        else:
            cp = cpk = float('inf')

        if std_dev_overall > 0:
            pp = (usl - lsl) / (6 * std_dev_overall)
            ppu = (usl - mean) / (3 * std_dev_overall)
            ppl = (mean - lsl) / (3 * std_dev_overall)
            ppk = min(ppu, ppl)
        else:
            pp = ppk = float('inf')

        # Interpretation
        if cpk >= 1.33:
            interpretation = "Process is capable and well-centered"
        elif cpk >= 1.0:
            interpretation = "Process is marginally capable - monitor closely"
        elif cpk >= 0.67:
            interpretation = "Process needs improvement - high defect risk"
        else:
            interpretation = "Process is not capable - immediate action required"

        if cp > cpk + 0.2:
            interpretation += ". Process is not centered (Cp > Cpk)."

        return Response({
            'definition': MeasurementDefinitionSPCSerializer(definition).data,
            'sample_size': n,
            'subgroup_size': subgroup_size,
            'num_subgroups': len(ranges),
            'usl': round(usl, 6),
            'lsl': round(lsl, 6),
            'mean': round(mean, 6),
            'std_dev_within': round(std_dev_within, 6),
            'std_dev_overall': round(std_dev_overall, 6),
            'cp': round(cp, 3) if cp != float('inf') else None,
            'cpk': round(cpk, 3) if cpk != float('inf') else None,
            'pp': round(pp, 3) if pp != float('inf') else None,
            'ppk': round(ppk, 3) if ppk != float('inf') else None,
            'interpretation': interpretation,
        })

    @extend_schema(
        parameters=[
            OpenApiParameter(name='part_id', type=str, required=False, description='UUID of a specific Part'),
            OpenApiParameter(name='work_order_id', type=str, required=False, description='UUID of a WorkOrder (returns all parts results)'),
        ],
        responses={200: inline_serializer(
            name='DimensionalResultsResponse',
            fields={
                'part': serializers.DictField(allow_null=True),
                'work_order': serializers.DictField(allow_null=True),
                'results': serializers.ListField(child=serializers.DictField()),
                'summary': serializers.DictField(),
            }
        )}
    )
    @action(detail=False, methods=['get'], url_path='dimensional-results')
    def dimensional_results(self, request):
        """
        Get all dimensional measurement results for a part or work order.

        Useful for PPAP dimensional reports (Element 9).

        Query params:
            part_id (optional): ID of a specific Part
            work_order_id (optional): ID of a WorkOrder (returns all parts' results)
            At least one must be provided.

        Response:
        {
            "part": { "id": 1, "erp_id": "PART-001", ... } or null,
            "work_order": { "id": 1, "identifier": "WO-001", ... } or null,
            "results": [
                {
                    "part_erp_id": "PART-001",
                    "step_name": "Finish Turning",
                    "measurement_label": "Outer Diameter",
                    "nominal": 25.0,
                    "upper_tol": 0.1,
                    "lower_tol": 0.1,
                    "usl": 25.1,
                    "lsl": 24.9,
                    "actual": 25.02,
                    "deviation": 0.02,
                    "unit": "mm",
                    "is_within_spec": true,
                    "timestamp": "2025-01-15T10:30:00Z",
                    "operator": "John Smith"
                }
            ],
            "summary": {
                "total_measurements": 50,
                "within_spec": 48,
                "out_of_spec": 2,
                "pass_rate": 96.0
            }
        }
        """
        part_id = request.query_params.get('part_id')
        work_order_id = request.query_params.get('work_order_id')

        if not part_id and not work_order_id:
            return Response(
                {"error": "Either part_id or work_order_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Build queryset filter
        filters = {
            'definition__type': 'NUMERIC',
            'value_numeric__isnull': False,
            'archived': False,
        }

        part_info = None
        work_order_info = None

        if part_id:
            try:
                part = self.qs_for_user(Parts).get(id=part_id)
                part_info = {
                    'id': part.id,
                    'erp_id': part.ERP_id,
                    'part_type': part.part_type.name if part.part_type else None,
                }
                filters['report__part_id'] = part_id
            except Parts.DoesNotExist:
                return Response(
                    {"error": "Part not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

        if work_order_id:
            try:
                work_order = self.qs_for_user(WorkOrder).get(id=work_order_id)
                work_order_info = {
                    'id': work_order.id,
                    'identifier': work_order.identifier,
                    'order_id': work_order.order_id,
                }
                filters['report__part__work_order_id'] = work_order_id
            except WorkOrder.DoesNotExist:
                return Response(
                    {"error": "Work order not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

        # Query measurement results with tenant scoping
        results_qs = self.qs_for_user(MeasurementResult).filter(
            **filters
        ).select_related(
            'definition',
            'definition__step',
            'report',
            'report__part',
            'created_by',
        ).order_by(
            'report__part__ERP_id',
            'definition__step__name',
            'definition__label',
            'report__created_at',
        )

        # Build results
        results = []
        for r in results_qs:
            defn = r.definition
            nominal = float(defn.nominal) if defn.nominal else 0
            upper_tol = float(defn.upper_tol) if defn.upper_tol else 0
            lower_tol = float(defn.lower_tol) if defn.lower_tol else 0
            actual = r.value_numeric

            results.append({
                'part_erp_id': r.report.part.ERP_id if r.report.part else 'N/A',
                'step_name': defn.step.name,
                'measurement_label': defn.label,
                'nominal': nominal,
                'upper_tol': upper_tol,
                'lower_tol': lower_tol,
                'usl': round(nominal + upper_tol, 6),
                'lsl': round(nominal - lower_tol, 6),
                'actual': round(actual, 6),
                'deviation': round(actual - nominal, 6),
                'unit': defn.unit,
                'is_within_spec': r.is_within_spec,
                'timestamp': r.report.created_at,
                'operator': r.created_by.get_full_name() if r.created_by else None,
                'report_id': r.report_id,
            })

        # Summary
        total = len(results)
        within_spec = sum(1 for r in results if r['is_within_spec'])
        out_of_spec = total - within_spec

        return Response({
            'part': part_info,
            'work_order': work_order_info,
            'results': results,
            'summary': {
                'total_measurements': total,
                'within_spec': within_spec,
                'out_of_spec': out_of_spec,
                'pass_rate': round((within_spec / total * 100), 1) if total > 0 else 0,
            }
        })


class SPCBaselineViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """
    ViewSet for SPC Baselines (frozen control limits).

    Standard CRUD plus custom actions:
        POST /api/spc-baselines/freeze/ - Freeze current limits as new baseline
        POST /api/spc-baselines/{id}/supersede/ - Supersede/unfreeze a baseline
        GET /api/spc-baselines/active/?measurement_id=X - Get active baseline
    """
    queryset = SPCBaseline.objects.all()
    serializer_class = SPCBaselineSerializer
    pagination_class = LimitOffsetPagination
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['measurement_definition', 'chart_type', 'status', 'frozen_by']
    search_fields = ['notes', 'measurement_definition__label']
    ordering_fields = ['frozen_at', 'status', 'measurement_definition__label']
    ordering = ['-frozen_at']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return SPCBaseline.objects.none()

        # Apply tenant scoping first, then user filtering
        qs = super().get_queryset()
        return qs.select_related(
            'measurement_definition',
            'measurement_definition__step',
            'measurement_definition__step__part_type',
            'frozen_by',
            'superseded_by',
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return SPCBaselineListSerializer
        if self.action == 'freeze':
            return SPCBaselineFreezeSerializer
        return SPCBaselineSerializer

    @extend_schema(
        request=SPCBaselineFreezeSerializer,
        responses={201: SPCBaselineSerializer},
        description="Freeze control limits as new baseline. Auto-supersedes existing active baseline."
    )
    @action(detail=False, methods=['post'], url_path='freeze')
    def freeze(self, request):
        """
        Freeze current control limits as a new baseline.

        Request body:
        {
            "measurement_definition_id": 123,
            "chart_type": "XBAR_R",
            "subgroup_size": 5,
            "xbar_ucl": 25.10,
            "xbar_cl": 25.00,
            "xbar_lcl": 24.90,
            "range_ucl": 0.15,
            "range_cl": 0.07,
            "range_lcl": 0,
            "sample_count": 150,
            "notes": "Initial baseline after process stabilization"
        }
        """
        serializer = SPCBaselineFreezeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        baseline = serializer.save()
        return Response(SPCBaselineSerializer(baseline).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=inline_serializer(
            name='SupersedeRequest',
            fields={'reason': serializers.CharField(required=False, allow_blank=True)}
        ),
        responses={200: SPCBaselineSerializer},
        description="Supersede (unfreeze) a baseline."
    )
    @action(detail=True, methods=['post'], url_path='supersede')
    def supersede(self, request, pk=None):
        """Supersede/unfreeze a baseline with optional reason."""
        baseline = self.get_object()

        if baseline.status == BaselineStatus.SUPERSEDED:
            return Response(
                {"error": "Baseline is already superseded"},
                status=status.HTTP_400_BAD_REQUEST
            )

        baseline.status = BaselineStatus.SUPERSEDED
        baseline.superseded_at = timezone.now()
        baseline.superseded_reason = request.data.get('reason', '')
        baseline.save()

        return Response(SPCBaselineSerializer(baseline).data)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                'measurement_id',
                type=str,
                required=True,
                description='UUID of the MeasurementDefinition'
            )
        ],
        responses={200: SPCBaselineSerializer},
        description="Get active baseline for a measurement."
    )
    @action(detail=False, methods=['get'], url_path='active')
    def active(self, request):
        """Get the active baseline for a measurement definition."""
        measurement_id = request.query_params.get('measurement_id')
        if not measurement_id:
            return Response(
                {"error": "measurement_id required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        baseline = SPCBaseline.get_active(measurement_id)
        if baseline:
            return Response(SPCBaselineSerializer(baseline).data)
        return Response(None)
