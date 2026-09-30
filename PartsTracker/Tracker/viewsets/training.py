# viewsets/training.py - Training Management ViewSets
from datetime import timedelta

from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, inline_serializer
from rest_framework import viewsets, status, filters, serializers
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response

from Tracker.models import (
    EquipmentType, JobRole, Processes, TrainingRecord, TrainingRequirement, TrainingType,
)
from Tracker.serializers.csv_import import BaseCSVImportSerializer, create_import_serializer_for_model
from Tracker.serializers.training import (
    TrainingTypeSerializer,
    TrainingRecordSerializer,
    TrainingRequirementSerializer,
    TrainingMatrixSerializer,
    JobRoleSerializer,
)
from Tracker.services.training import build_training_matrix
from Tracker.services.core.clock import tenant_today
from .base import TenantScopedMixin
from .core import ListMetadataMixin
from .mixins import CSVImportMixin, DataExportMixin


# ===== TRAINING TYPE VIEWSET =====

@extend_schema_view(
    list=extend_schema(
        description="List all training types",
        parameters=[
            OpenApiParameter(name='search', description='Search by name or description', required=False, type=str),
        ]
    ),
    create=extend_schema(description="Create a new training type"),
    retrieve=extend_schema(description="Retrieve a specific training type"),
    update=extend_schema(description="Update a training type"),
    partial_update=extend_schema(description="Partially update a training type"),
    destroy=extend_schema(description="Soft delete a training type")
)
class TrainingTypeViewSet(TenantScopedMixin, ListMetadataMixin, CSVImportMixin, DataExportMixin,
                          viewsets.ModelViewSet):
    """
    ViewSet for managing training types.

    Training types define categories of training/qualifications that personnel can hold,
    such as 'Blueprint Reading', 'CMM Operation', or 'Soldering IPC-A-610'.
    """
    queryset = TrainingType.unscoped.all()
    serializer_class = TrainingTypeSerializer
    # Versioned: an import's edit versions the way the API's does
    # (TrainingTypeSerializer.update). A name matches the current one.
    csv_import_serializer = create_import_serializer_for_model(
        TrainingType, lookup_fields=['id', 'name'])
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['validity_period_days']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'validity_period_days', 'created_at']
    ordering = ['name']
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        """Current versions only when listing.

        TrainingType is versioned, so an edit leaves the superseded row behind and
        the list showed both. Scoped to `list` (as `WorkCenterViewSet` does) rather
        than the class queryset because `TrainingRecord.training_type` stays on the
        version a record was earned against — a by-id fetch of that version must
        keep working.
        """
        if getattr(self, 'swagger_fake_view', False):
            return TrainingType.objects.none()
        qs = super().get_queryset()
        if self.action == 'list':
            qs = qs.filter(is_current_version=True)
        return qs


# ===== TRAINING RECORD VIEWSET =====

@extend_schema_view(
    list=extend_schema(
        description="List training records with filtering",
        parameters=[
            OpenApiParameter(name='user', description='Filter by user ID', required=False, type=int),
            OpenApiParameter(name='training_type', description='Filter by training type ID', required=False, type=str),
            OpenApiParameter(name='trainer', description='Filter by trainer user ID', required=False, type=int),
            OpenApiParameter(name='status', description='Filter by status (current, expiring_soon, expired)', required=False, type=str),
        ]
    ),
    create=extend_schema(description="Create a new training record"),
    retrieve=extend_schema(description="Retrieve a specific training record"),
    update=extend_schema(description="Update a training record"),
    partial_update=extend_schema(description="Partially update a training record"),
    destroy=extend_schema(description="Soft delete a training record")
)
class TrainingRecordViewSet(TenantScopedMixin, ListMetadataMixin, DataExportMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing training records.

    Training records track when a user has completed a specific training,
    including completion date, expiration, and trainer information.
    """
    queryset = TrainingRecord.unscoped.all()
    serializer_class = TrainingRecordSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['user', 'training_type', 'trainer', 'level']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'training_type__name', 'notes']
    ordering_fields = ['completed_date', 'expires_date', 'level', 'created_at']
    ordering = ['-completed_date']
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return TrainingRecord.objects.none()

        qs = super().get_queryset()
        qs = qs.select_related('user', 'training_type', 'trainer')

        # Filter by computed status if provided
        status_filter = self.request.query_params.get('status')
        if status_filter:
            today = tenant_today(self.tenant)
            thirty_days = today + timedelta(days=30)

            if status_filter == 'current':
                # Current: no expiration or expires_date >= today and not within 30 days
                qs = qs.filter(
                    Q(expires_date__isnull=True) |
                    Q(expires_date__gt=thirty_days)
                )
            elif status_filter == 'expiring_soon':
                # Expiring soon: expires within 30 days but not yet expired
                qs = qs.filter(
                    expires_date__lte=thirty_days,
                    expires_date__gte=today
                )
            elif status_filter == 'expired':
                # Expired: expires_date < today
                qs = qs.filter(expires_date__lt=today)

        return qs

    @extend_schema(
        description="Get training records for the current authenticated user",
        responses={200: TrainingRecordSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='my-training')
    def my_training(self, request):
        """Return all training records for the current user.

        Routed through the viewset's pagination class so the response
        shape matches the schema-generated `PaginatedTrainingRecordList`.
        Without this the bare-list response trips Zodios's response
        validation on the frontend.
        """
        qs = self.get_queryset().filter(user=request.user)
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(qs, many=True).data)

    @extend_schema(
        description="Get training records expiring within N days (default 30)",
        parameters=[
            OpenApiParameter(name='days', description='Days until expiration', required=False, type=int, default=30),
        ],
        responses={200: TrainingRecordSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='expiring-soon')
    def expiring_soon(self, request):
        """Return training records expiring within N days."""
        days = int(request.query_params.get('days', 30))
        today = tenant_today(self.tenant)
        cutoff = today + timedelta(days=days)

        qs = self.get_queryset().filter(
            expires_date__lte=cutoff,
            expires_date__gte=today
        ).order_by('expires_date')

        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(qs, many=True).data)

    @extend_schema(
        description="Get all expired training records",
        responses={200: TrainingRecordSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='expired')
    def expired(self, request):
        """Return all expired training records."""
        today = tenant_today(self.tenant)
        qs = self.get_queryset().filter(expires_date__lt=today).order_by('-expires_date')
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(qs, many=True).data)

    @extend_schema(
        description="Get training statistics summary",
        responses={200: inline_serializer(
            name='TrainingStats',
            fields={
                'total_records': serializers.IntegerField(),
                'current': serializers.IntegerField(),
                'expiring_soon': serializers.IntegerField(),
                'expired': serializers.IntegerField(),
            }
        )}
    )
    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """Return training statistics summary."""
        today = tenant_today(self.tenant)
        thirty_days = today + timedelta(days=30)

        qs = self.get_queryset()
        total = qs.count()

        # Current: no expiration or expires_date > 30 days from now
        current = qs.filter(
            Q(expires_date__isnull=True) | Q(expires_date__gt=thirty_days)
        ).count()

        # Expiring soon: within 30 days but not expired
        expiring_soon = qs.filter(
            expires_date__lte=thirty_days,
            expires_date__gte=today
        ).count()

        # Expired
        expired = qs.filter(expires_date__lt=today).count()

        return Response({
            'total_records': total,
            'current': current,
            'expiring_soon': expiring_soon,
            'expired': expired,
        })


# ===== TRAINING REQUIREMENT VIEWSET =====

class _TrainingRequirementImportBase(BaseCSVImportSerializer):
    """A spreadsheet row writes a requirement through the same validating service as
    the API (exactly one target, no duplicate) — the import writes the model
    directly, bypassing `TrainingRequirementSerializer.create/update`."""

    def create_instance(self, data):
        from Tracker.services.training import create_training_requirement
        # Same stamping as BaseCSVImportSerializer.create_instance.
        if self.tenant:
            data['tenant'] = self.tenant
        if self.user and hasattr(TrainingRequirement, 'created_by'):
            data['created_by'] = self.user
        return create_training_requirement(**data)

    def _save_in_place(self, instance, changes):
        from Tracker.services.training import update_training_requirement
        if self.user and hasattr(instance, 'modified_by'):
            instance.modified_by = self.user
        return update_training_requirement(instance, **changes)


@extend_schema_view(
    list=extend_schema(
        description="List training requirements with filtering",
        parameters=[
            OpenApiParameter(name='training_type', description='Filter by training type ID', required=False, type=str),
            OpenApiParameter(name='step', description='Filter by step ID', required=False, type=str),
            OpenApiParameter(name='process', description='Filter by process ID', required=False, type=str),
            OpenApiParameter(name='equipment_type', description='Filter by equipment type ID', required=False, type=str),
        ]
    ),
    create=extend_schema(description="Create a new training requirement"),
    retrieve=extend_schema(description="Retrieve a specific training requirement"),
    update=extend_schema(description="Update a training requirement"),
    partial_update=extend_schema(description="Partially update a training requirement"),
    destroy=extend_schema(description="Soft delete a training requirement")
)
class TrainingRequirementViewSet(TenantScopedMixin, ListMetadataMixin, CSVImportMixin, DataExportMixin,
                                 viewsets.ModelViewSet):
    """
    ViewSet for managing training requirements.

    Training requirements link a TrainingType to work activities
    (Step, Process, or EquipmentType).
    """
    queryset = TrainingRequirement.unscoped.all()
    serializer_class = TrainingRequirementSerializer
    # A requirement is one training type on one target, so it is found by that pair
    # (the model's four unique constraints). Steps are `Process > Step`; a process by
    # name is its current version.
    csv_import_serializer = create_import_serializer_for_model(
        TrainingRequirement,
        lookup_fields=['id', ('training_type', 'step'), ('training_type', 'process'),
                       ('training_type', 'equipment_type'), ('training_type', 'job_role')],
        extra_fk_fields={
            'training_type': (TrainingType, ['name', 'id']),
            'process': (Processes, ['name', 'id']),
            'equipment_type': (EquipmentType, ['name', 'id']),
            'job_role': (JobRole, ['name', 'id']),
        },
        base=_TrainingRequirementImportBase)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['training_type', 'step', 'process', 'equipment_type', 'job_role', 'min_level']
    search_fields = ['training_type__name', 'step__name', 'process__name', 'equipment_type__name', 'job_role__name', 'notes']
    ordering_fields = ['training_type__name', 'min_level', 'created_at']
    ordering = ['training_type__name']
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return TrainingRequirement.objects.none()

        qs = super().get_queryset()
        return qs.select_related('training_type', 'step', 'process', 'equipment_type', 'job_role')

    @extend_schema(
        description="Get all training requirements for a specific step",
        parameters=[
            OpenApiParameter(name='step_id', description='Step ID', required=True, type=str),
        ],
        responses={200: TrainingRequirementSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='for-step')
    def for_step(self, request):
        """Return all training requirements for a specific step."""
        step_id = request.query_params.get('step_id')
        if not step_id:
            return Response({'detail': 'step_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        qs = self.get_queryset().filter(step_id=step_id)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @extend_schema(
        description="Get all training requirements for a specific process",
        parameters=[
            OpenApiParameter(name='process_id', description='Process ID', required=True, type=str),
        ],
        responses={200: TrainingRequirementSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='for-process')
    def for_process(self, request):
        """Return all training requirements for a specific process."""
        process_id = request.query_params.get('process_id')
        if not process_id:
            return Response({'detail': 'process_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        qs = self.get_queryset().filter(process_id=process_id)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


# ===== JOB ROLE VIEWSET =====

@extend_schema_view(
    list=extend_schema(
        description="List job roles",
        parameters=[
            OpenApiParameter(name='search', description='Search by name or description', required=False, type=str),
            OpenApiParameter(name='active', description='Filter by active flag', required=False, type=bool),
        ],
    ),
    create=extend_schema(description="Create a new job role"),
    retrieve=extend_schema(description="Retrieve a specific job role"),
    update=extend_schema(description="Update a job role"),
    partial_update=extend_schema(description="Partially update a job role"),
    destroy=extend_schema(description="Soft delete a job role"),
)
class JobRoleViewSet(TenantScopedMixin, ListMetadataMixin, CSVImportMixin, DataExportMixin,
                     viewsets.ModelViewSet):
    """
    ViewSet for managing job roles (HR/organizational positions).

    Job roles carry required-competency profiles via TrainingRequirement rows
    scoped to the role, and users are assigned a primary role via User.job_role.
    """
    queryset = JobRole.unscoped.all()
    serializer_class = JobRoleSerializer
    csv_import_serializer = create_import_serializer_for_model(
        JobRole, lookup_fields=['id', 'name'])
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return JobRole.objects.none()
        return super().get_queryset()


# ===== COMPETENCE MATRIX =====

class CompetenceMatrixView(APIView):
    """
    Read-only competency matrix aggregate: operators (rows) x training types
    (columns), each cell carrying the operator's current level, plus per-skill
    coverage (how many are qualified / expiring).

    A single JSON object (not a collection), so it's an APIView rather than a
    router ViewSet — a `list` action would make spectacular type the response as
    an array and break the generated client at runtime.

    Supervisor/HR surface — gated on the dedicated `view_training_matrix`
    permission (distinct from view_trainingrecord) so line operators don't see
    the org-wide grid.
    """

    @extend_schema(
        description="Operators x training-types competency matrix with per-skill "
                    "coverage counts. HR / quality view - requires view_training_matrix.",
        responses={200: TrainingMatrixSerializer},
    )
    def get(self, request):
        if not request.user.has_perm('Tracker.view_training_matrix'):
            return Response(
                {'detail': 'You do not have permission to view the training matrix.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        # `.objects` is tenant-scoped for the duration of the request, so the
        # aggregate is automatically limited to the caller's tenant.
        data = build_training_matrix()
        return Response(TrainingMatrixSerializer(data).data)
