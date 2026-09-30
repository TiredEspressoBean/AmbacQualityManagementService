# viewsets/life_tracking.py - Life Tracking ViewSets
"""
ViewSets for life tracking models:
- LifeLimitDefinition: Tenant-defined tracking rules (admin)
- PartTypeLifeLimit: Links definitions to part types (admin)
- LifeTracking: Actual tracking records with increment/reset/override actions
"""
from django.contrib.contenttypes.models import ContentType
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from Tracker.models import LifeLimitDefinition, PartTypeLifeLimit, LifeTracking
from Tracker.serializers.life_tracking import (
    LifeLimitDefinitionSerializer, LifeLimitDefinitionSelectSerializer,
    PartTypeLifeLimitSerializer,
    LifeTrackingSerializer, LifeTrackingListSerializer,
    LifeTrackingIncrementSerializer, LifeTrackingResetSerializer, LifeTrackingOverrideSerializer,
)
from Tracker.serializers.csv_import import (
    BaseCSVImportSerializer, create_import_serializer_for_model,
)
from .base import TenantScopedMixin
from .scheduling_setup import ReviveOnCreateMixin
from .core import ListMetadataMixin
from .mixins import CSVImportMixin, DataExportMixin, VersionHistoryMixin


class LifeLimitDefinitionViewSet(VersionHistoryMixin, TenantScopedMixin, ListMetadataMixin, CSVImportMixin, DataExportMixin,
                                 viewsets.ModelViewSet):
    """
    Life limit definition management.

    Tenants define their own life tracking rules here:
    - Flight Cycles (hard_limit=20000)
    - Shelf Life (is_calendar_based=True, hard_limit=365 days)
    - Shot Count (soft_limit=400000, hard_limit=500000)

    Import/export is one row per definition; its part-type links import on the
    PartTypeLifeLimits endpoint. A content edit from a file makes a new version, as
    the API's does (the importer follows LifeLimitDefinitionSerializer.update).
    """
    # Versioned: each revision is a row, so the list is the current ones.
    queryset = LifeLimitDefinition.unscoped.filter(is_current_version=True)
    serializer_class = LifeLimitDefinitionSerializer
    # A definition is its name (unique among current versions); a name finds the
    # current version.
    csv_import_serializer = create_import_serializer_for_model(
        LifeLimitDefinition, lookup_fields=['id', 'name'])
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    search_fields = ['name', 'unit', 'unit_label']
    filterset_fields = ['is_calendar_based']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    @action(detail=False, methods=['get'])
    def select_options(self, request):
        """Lightweight list for dropdowns"""
        definitions = self.get_queryset()
        return Response(LifeLimitDefinitionSelectSerializer(definitions, many=True).data)

    @extend_schema(
        description=(
            "Create a new revision of a LifeLimitDefinition. "
            "Returns the new version with incremented version number. "
            "PartTypeLifeLimit children are copied to the new version."
        ),
        request={
            "application/json": {
                "type": "object",
                "required": ["change_description"],
                "properties": {
                    "change_description": {
                        "type": "string",
                        "description": "Human narrative of what changed and why (AS9100D §8.3)."
                    },
                },
            }
        },
        responses={201: LifeLimitDefinitionSerializer},
    )
    @action(detail=True, methods=['post'], url_path='revisions')
    def create_revision(self, request, pk=None):
        """Create a new version of this life limit definition.

        PATCH routes content edits through create_new_version via the
        serializer's update() method. This endpoint is the explicit
        "create a new revision" path when callers want full control.
        Returns 201 with the new version.
        """
        from Tracker.services.life_tracking.life_limit_definition import (
            create_new_life_limit_definition_version,
        )

        definition = self.get_object()
        change_description = request.data.get('change_description', '')

        try:
            new_version = create_new_life_limit_definition_version(
                definition,
                user=request.user,
                change_description=change_description,
            )
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            LifeLimitDefinitionSerializer(new_version, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class _PartTypeLifeLimitImport(BaseCSVImportSerializer):
    """Keeps a link on the version it is pinned to when the file names that version.

    Revising a definition copies its links onto the new version and leaves the old ones
    on the old version (historical pinning — create_new_life_limit_definition_version),
    so an export lists both. An .xlsx export's ID columns are lookups the import skips,
    so the old link's `definition` arrives as a name, which finds the CURRENT version:
    re-pointing the old link there collides with the copy already on it. A name that is
    the linked row's own name names that row, so it is kept.
    """

    def resolve_with_existing(self, row, transformed, existing):
        if existing is None:
            return
        for field in ('part_type', 'definition'):
            new, old = transformed.get(field), getattr(existing, field, None)
            if new is None or old is None or new.pk == old.pk:
                continue
            if str(row.get(field, '')).strip().lower() == (old.name or '').strip().lower():
                transformed[field] = old


class PartTypeLifeLimitViewSet(ReviveOnCreateMixin, TenantScopedMixin, CSVImportMixin,
                               DataExportMixin, viewsets.ModelViewSet):
    """
    Links life limit definitions to part types.

    Defines which life limits apply to which part types,
    and whether tracking is required when creating parts.
    """
    queryset = PartTypeLifeLimit.unscoped.select_related('part_type', 'definition')
    serializer_class = PartTypeLifeLimitSerializer
    # A link is its (part type, definition) pair — the model's unique constraint. Both
    # are found by name, and a versioned definition's name finds its current version.
    # A link pinned to an older version imports back onto that version (see the base).
    csv_import_serializer = create_import_serializer_for_model(
        PartTypeLifeLimit, lookup_fields=['id', ('part_type', 'definition')],
        base=_PartTypeLifeLimitImport, meta={'revive_key': ('part_type', 'definition')})
    # A removed link still holds its (part type, definition) key; linking the pair again
    # revives it rather than failing as a duplicate.
    revive_key = ('part_type', 'definition')
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['part_type', 'definition', 'is_required']
    ordering_fields = ['part_type__name', 'definition__name']
    ordering = ['part_type__name']


class LifeTrackingViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """
    Life tracking record management.

    Tracks accumulated life for parts, cores, equipment, etc.
    Supports increment, reset (overhaul), and per-instance limit overrides.
    """
    queryset = LifeTracking.unscoped.select_related('definition', 'content_type', 'override_approved_by')
    serializer_class = LifeTrackingSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['definition', 'cached_status', 'source', 'content_type', 'object_id']
    ordering_fields = ['accumulated', 'created_at', 'cached_status']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return LifeTrackingListSerializer
        return LifeTrackingSerializer

    @extend_schema(request=LifeTrackingIncrementSerializer, responses={200: LifeTrackingSerializer})
    @action(detail=True, methods=['post'])
    def increment(self, request, pk=None):
        """Increment accumulated value (after operation/cycle)"""
        tracking = self.get_object()
        serializer = LifeTrackingIncrementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tracking.increment(serializer.validated_data['value'])
        return Response(LifeTrackingSerializer(tracking, context={'request': request}).data)

    @extend_schema(request=LifeTrackingResetSerializer, responses={200: LifeTrackingSerializer})
    @action(detail=True, methods=['post'])
    def reset(self, request, pk=None):
        """Reset accumulated value to zero (after rebuild/overhaul)"""
        tracking = self.get_object()
        serializer = LifeTrackingResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tracking.reset(
            user=request.user,
            reason=serializer.validated_data.get('reason', '')
        )
        return Response(LifeTrackingSerializer(tracking, context={'request': request}).data)

    @extend_schema(request=LifeTrackingOverrideSerializer, responses={200: LifeTrackingSerializer})
    @action(detail=True, methods=['post'])
    def apply_override(self, request, pk=None):
        """Apply per-instance limit override (engineering approval)"""
        tracking = self.get_object()
        serializer = LifeTrackingOverrideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tracking.apply_override(
            hard_limit=serializer.validated_data.get('hard_limit'),
            soft_limit=serializer.validated_data.get('soft_limit'),
            reason=serializer.validated_data['reason'],
            approved_by=request.user
        )
        return Response(LifeTrackingSerializer(tracking, context={'request': request}).data)

    @action(detail=False, methods=['get'])
    def for_object(self, request):
        """
        Get all life tracking records for a specific object.

        Query params:
        - content_type: e.g., "tracker.parts" or content_type ID
        - object_id: UUID of the object
        """
        content_type_param = request.query_params.get('content_type')
        object_id = request.query_params.get('object_id')

        if not content_type_param or not object_id:
            return Response(
                {'detail': 'content_type and object_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Handle both "app.model" format and ID
        if '.' in content_type_param:
            app_label, model = content_type_param.split('.')
            try:
                ct = ContentType.objects.get(app_label=app_label, model=model)
            except ContentType.DoesNotExist:
                return Response({'detail': 'Invalid content_type'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            try:
                ct = ContentType.objects.get(pk=content_type_param)
            except ContentType.DoesNotExist:
                return Response({'detail': 'Invalid content_type'}, status=status.HTTP_400_BAD_REQUEST)

        tracking_records = self.get_queryset().filter(content_type=ct, object_id=object_id)
        return Response(LifeTrackingSerializer(tracking_records, many=True, context={'request': request}).data)

    @action(detail=False, methods=['get'])
    def warnings(self, request):
        """Get all tracking records at warning level"""
        records = self.get_queryset().filter(cached_status='WARNING')
        return Response(LifeTrackingListSerializer(records, many=True).data)

    @action(detail=False, methods=['get'])
    def expired(self, request):
        """Get all tracking records that have exceeded limits"""
        records = self.get_queryset().filter(cached_status='EXPIRED')
        return Response(LifeTrackingListSerializer(records, many=True).data)
