"""Go-live history loads: import training records / material lots from another system,
and verify each load once. See Tracker.services.core.migration_import."""
from django.db import transaction
from django.http import HttpResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import parsers, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from Tracker.models import MigrationBatch, MigrationBatchKind
from Tracker.services.core import migration_import as svc
from Tracker.services.csv_utils import parse_file
from .base import TenantScopedMixin

# The columns each kind reads — what the template offers.
TEMPLATE_COLUMNS = {
    MigrationBatchKind.TRAINING_RECORDS: [
        'user', 'training_type', 'completed_date', 'level', 'expires_date', 'trainer',
        'source_reference', 'notes'],
    MigrationBatchKind.MATERIAL_LOTS: [
        'lot_number', 'material', 'material_type', 'supplier', 'supplier_lot_number',
        'quantity', 'quantity_remaining', 'unit_of_measure', 'received_date',
        'manufacture_date', 'expiration_date', 'storage_location', 'source_reference'],
}


class MigrationBatchSerializer(serializers.ModelSerializer):
    imported_by_email = serializers.CharField(source='imported_by.email', read_only=True)
    verified_by_email = serializers.CharField(source='verified_by.email', read_only=True,
                                              allow_null=True)
    is_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = MigrationBatch
        fields = ('id', 'kind', 'source_system', 'notes', 'row_count', 'imported_by',
                  'imported_by_email', 'created_at', 'verified_by', 'verified_by_email',
                  'verified_at', 'verification_notes', 'is_verified')
        read_only_fields = fields


class MigrationBatchViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Loads of go-live history. Each import makes one batch; each batch is verified once,
    by someone other than the person who loaded it."""
    queryset = MigrationBatch.unscoped.select_related('imported_by', 'verified_by')
    serializer_class = MigrationBatchSerializer
    action_permissions = {
        'import_history': ['add_migrationbatch'],
        'verify': ['change_migrationbatch'],
        'template': ['view_migrationbatch'],
    }

    @extend_schema(
        request={'multipart/form-data': inline_serializer('MigrationImportRequest', fields={
            'file': serializers.FileField(),
            'kind': serializers.ChoiceField(choices=MigrationBatchKind.choices),
            'source_system': serializers.CharField(),
            'notes': serializers.CharField(required=False),
        })},
        responses={207: inline_serializer('MigrationImportResponse', fields={
            'batch': MigrationBatchSerializer(),
            'summary': serializers.DictField(),
            'results': serializers.ListField(child=serializers.DictField()),
        })},
    )
    @action(detail=False, methods=['post'], url_path='import',
            parser_classes=[parsers.MultiPartParser, parsers.FormParser])
    def import_history(self, request):
        """Load one file of history as a new batch (create-only)."""
        kind = request.data.get('kind')
        if kind not in MigrationBatchKind.values:
            return Response({'detail': f"kind must be one of {', '.join(MigrationBatchKind.values)}."},
                            status=status.HTTP_400_BAD_REQUEST)
        upload = request.FILES.get('file')
        if upload is None:
            return Response({'detail': "Attach the file."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            rows, _ = parse_file(upload, upload.name)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            batch = svc.start_batch(tenant=self.tenant, user=request.user, kind=kind,
                                    source_system=request.data.get('source_system', ''),
                                    notes=request.data.get('notes', ''))
            run = (svc.import_training_records if kind == MigrationBatchKind.TRAINING_RECORDS
                   else svc.import_material_lots)
            body = run(rows, batch=batch, user=request.user)
        batch.refresh_from_db()
        body['batch'] = MigrationBatchSerializer(batch).data
        return Response(body, status=status.HTTP_207_MULTI_STATUS)

    @extend_schema(
        request=inline_serializer('MigrationVerifyRequest', fields={
            'notes': serializers.CharField(required=False)}),
        responses=MigrationBatchSerializer)
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Sign the batch off as checked against its source."""
        batch = svc.verify_batch(self.get_object(), user=request.user,
                                 notes=request.data.get('notes', ''))
        return Response(MigrationBatchSerializer(batch).data)

    @extend_schema(
        parameters=[OpenApiParameter('kind', str, OpenApiParameter.QUERY, required=True,
                                     enum=MigrationBatchKind.values)],
        responses={(200, 'text/csv'): bytes})
    @action(detail=False, methods=['get'])
    def template(self, request):
        """A CSV header for one kind of history."""
        kind = request.query_params.get('kind')
        if kind not in TEMPLATE_COLUMNS:
            return Response({'detail': "Pass ?kind=TRAINING_RECORDS or MATERIAL_LOTS."},
                            status=status.HTTP_400_BAD_REQUEST)
        response = HttpResponse((','.join(TEMPLATE_COLUMNS[kind]) + '\n').encode('utf-8-sig'),
                                content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{kind.lower()}_migration.csv"'
        return response
