"""
CSV Import Mixin for ViewSets.

Provides import and import-template endpoints for bulk data import.
Auto-configures from model introspection when no custom config is provided.

Background Processing:
- Small imports (< 100 rows): Processed inline, immediate response
- Large imports (>= 100 rows): Queued to Celery, returns task ID
- Use GET /import-status/{task_id}/ to poll progress
"""

from typing import Dict, Optional, Type

from celery.result import AsyncResult
from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from rest_framework import serializers, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response

from Tracker.services.csv_utils import parse_file, ImportResult
from Tracker.serializers.csv_import import (
    BaseCSVImportSerializer,
    ImportMode,
    get_or_create_import_serializer,
)

# Threshold for background processing
BACKGROUND_IMPORT_THRESHOLD = 100


class CSVImportMixin:
    """
    Mixin to add CSV/Excel import functionality to ViewSets.

    Adds two endpoints:
    - GET /import-template/ - Download import template (CSV or Excel)
    - POST /import/ - Import data from uploaded file

    Works automatically with any model through introspection.
    Override attributes for customization:

    - csv_import_serializer: Custom serializer class (auto-detected if not set)
    - csv_template_generator: Custom template generator (auto-created if not set)
    - csv_field_mapping: Dict mapping CSV columns to model fields

    Example:
        # Basic - just add the mixin, everything auto-configured
        class PartsViewSet(CSVImportMixin, viewsets.ModelViewSet):
            queryset = Parts.objects.all()

        # Custom - override serializer or mapping
        class PartsViewSet(CSVImportMixin, viewsets.ModelViewSet):
            csv_import_serializer = CustomPartsCSVSerializer
            csv_field_mapping = {'Part ID': 'ERP_id'}
    """

    csv_import_serializer: Optional[Type[BaseCSVImportSerializer]] = None
    csv_template_generator = None
    csv_field_mapping: Dict[str, str] = {}

    def _get_model(self):
        """Get the model class from queryset."""
        if hasattr(self, 'queryset') and self.queryset is not None:
            return self.queryset.model
        return None

    def get_csv_import_serializer(self) -> Optional[Type[BaseCSVImportSerializer]]:
        """
        Get the CSV import serializer class for this viewset.

        Priority:
        1. Explicit csv_import_serializer attribute
        2. Auto-generated from model introspection
        """
        if self.csv_import_serializer:
            return self.csv_import_serializer

        model = self._get_model()
        if model:
            return get_or_create_import_serializer(model)

        return None

    def get_csv_template_generator(self):
        """
        Get the template generator for this viewset.

        Priority:
        1. Explicit csv_template_generator attribute
        2. Auto-generated from model introspection
        """
        if self.csv_template_generator:
            return self.csv_template_generator

        model = self._get_model()
        if model:
            from Tracker.services.template_generator import template_from_model
            return template_from_model(model)

        return None

    @extend_schema(
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'file': {
                        'type': 'string',
                        'format': 'binary',
                        'description': 'CSV or Excel file to preview'
                    },
                },
                'required': ['file']
            }
        },
        responses={
            200: inline_serializer(
                name='ImportPreviewResponse',
                fields={
                    'total_rows': serializers.IntegerField(),
                    'columns': serializers.ListField(child=serializers.DictField()),
                    'sample_data': serializers.ListField(child=serializers.DictField()),
                    'model_fields': serializers.ListField(child=serializers.DictField()),
                }
            ),
            400: {'description': 'Bad request (invalid file)'},
        },
        description='Preview a file before importing. Returns columns, suggested mappings, and sample data.',
        tags=['Import/Export'],
    )
    @action(
        detail=False,
        methods=['post'],
        url_path='import-preview',
        parser_classes=[parsers.MultiPartParser]
    )
    def import_preview(self, request):
        """
        Preview a file before importing.

        Returns:
        - total_rows: Number of data rows
        - columns: List of {name, mapped_to, confidence} for each column
        - sample_data: First 5 rows of data
        - model_fields: Available model fields for manual mapping
        """
        file = request.FILES.get('file')
        if not file:
            return Response(
                {"detail": "No file provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Parse file
        try:
            rows, headers = parse_file(
                file,
                file.name,
                field_map={},  # Don't apply mapping yet
            )
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"detail": f"Error reading file: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get model fields from template generator
        generator = self.get_csv_template_generator()
        model_fields = []
        field_names_set = set()

        if generator:
            for field in generator.fields:
                model_fields.append({
                    'name': field.name,
                    'display': field.display_name,
                    'required': field.required,
                    'type': field.field_type,
                })
                field_names_set.add(field.name.lower())

        # Build column mapping suggestions
        columns = []
        viewset_mapping = getattr(self, 'csv_field_mapping', {})

        for header in headers:
            header_lower = header.lower().replace(' ', '_').replace('-', '_')
            mapped_to = None
            confidence = 'none'

            # Check viewset's custom mapping first
            if header_lower in viewset_mapping:
                mapped_to = viewset_mapping[header_lower]
                confidence = 'high'
            # Check exact match
            elif header_lower in field_names_set:
                mapped_to = header_lower
                confidence = 'high'
            # Check if header matches a field display name
            else:
                for field in model_fields:
                    if header.lower() == field['display'].lower():
                        mapped_to = field['name']
                        confidence = 'medium'
                        break

            columns.append({
                'original': header,
                'mapped_to': mapped_to,
                'confidence': confidence,
            })

        # Get sample data (first 5 rows)
        sample_data = rows[:5] if rows else []

        return Response({
            'total_rows': len(rows),
            'columns': columns,
            'sample_data': sample_data,
            'model_fields': model_fields,
        })

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='format',
                description='Template format (csv or xlsx)',
                required=False,
                type=str,
                enum=['csv', 'xlsx'],
                default='xlsx',
            ),
        ],
        responses={
            200: {
                'type': 'string',
                'format': 'binary',
                'description': 'Template file download'
            }
        },
        description='Download an import template with headers, hints, and FK lookups (Excel only).',
        tags=['Import/Export'],
    )
    @action(detail=False, methods=['get'], url_path='import-template')
    def import_template(self, request):
        """
        Download an import template.

        Query params:
        - format: 'csv' or 'xlsx' (default: xlsx)
        """
        template_format = request.query_params.get('format', 'xlsx').lower()
        generator = self.get_csv_template_generator()

        if not generator:
            return Response(
                {"detail": "Import template not available for this model"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get tenant for FK lookups
        tenant = getattr(self, 'tenant', None) or getattr(request.user, 'tenant', None)

        model = self._get_model()
        model_name = model.__name__ if model else 'data'

        if template_format == 'csv':
            content = generator.generate_csv()
            content_type = 'text/csv'
            filename = f'{model_name.lower()}_import_template.csv'
        else:
            content = generator.generate_excel(tenant=tenant)
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            filename = f'{model_name.lower()}_import_template.xlsx'

        from django.http import HttpResponse
        response = HttpResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @extend_schema(
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'file': {
                        'type': 'string',
                        'format': 'binary',
                        'description': 'CSV or Excel file to import'
                    },
                    'mode': {
                        'type': 'string',
                        'enum': ['create', 'update', 'upsert'],
                        'description': 'Import mode: create, update, or upsert (default)'
                    },
                },
                'required': ['file']
            }
        },
        responses={
            207: inline_serializer(
                name='ImportResponse',
                fields={
                    'summary': inline_serializer(
                        name='ImportSummary',
                        fields={
                            'total': serializers.IntegerField(),
                            'created': serializers.IntegerField(),
                            'updated': serializers.IntegerField(),
                            'errors': serializers.IntegerField(),
                        }
                    ),
                    'results': serializers.ListField(
                        child=serializers.DictField()
                    ),
                }
            ),
            202: inline_serializer(
                name='ImportQueued',
                fields={
                    'task_id': serializers.CharField(),
                    'status': serializers.CharField(),
                    'total_rows': serializers.IntegerField(),
                    'message': serializers.CharField(),
                }
            ),
            400: {'description': 'Bad request (invalid file or data)'},
        },
        description='Import data from CSV or Excel file. Small imports return immediate results (207). Large imports are queued and return task_id (202).',
        tags=['Import/Export'],
    )
    @action(
        detail=False,
        methods=['post'],
        url_path='import',
        parser_classes=[parsers.MultiPartParser]
    )
    def import_data(self, request):
        """
        Import data from CSV or Excel file.

        Form data:
        - file: The CSV or Excel file to import
        - mode: Import mode ('create', 'update', or 'upsert', default: upsert)
        - column_mapping: Optional JSON string of {original_column: target_field} mappings

        Small imports (< 100 rows): Returns 207 Multi-Status with immediate results.
        Large imports (>= 100 rows): Returns 202 Accepted with task_id for polling.
        """
        file = request.FILES.get('file')
        if not file:
            return Response(
                {"detail": "No file provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get import mode
        mode = request.data.get('mode', ImportMode.UPSERT)
        if mode not in [ImportMode.CREATE, ImportMode.UPDATE, ImportMode.UPSERT]:
            return Response(
                {"detail": f"Invalid mode '{mode}'. Use 'create', 'update', or 'upsert'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get custom column mapping from request (overrides viewset defaults)
        import json
        custom_mapping = {}
        column_mapping_str = request.data.get('column_mapping')
        if column_mapping_str:
            try:
                custom_mapping = json.loads(column_mapping_str)
            except json.JSONDecodeError:
                return Response(
                    {"detail": "Invalid column_mapping JSON"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Merge with viewset's default mapping (custom takes precedence)
        field_map = {**self.csv_field_mapping, **custom_mapping}

        # Get serializer
        serializer_class = self.get_csv_import_serializer()
        if not serializer_class:
            return Response(
                {"detail": "Import not available for this model"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Parse file
        try:
            rows, headers = parse_file(
                file,
                file.name,
                field_map=field_map,
            )
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"detail": f"Error reading file: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not rows:
            return Response(
                {"detail": "No data rows found in file"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get tenant and user
        tenant = getattr(self, 'tenant', None) or getattr(request.user, 'tenant', None)
        user = request.user

        # Large import -> queue to Celery
        if len(rows) >= BACKGROUND_IMPORT_THRESHOLD:
            return self._queue_background_import(rows, mode, serializer_class, tenant, user)

        # Small import -> process inline
        return self._process_import_inline(rows, mode, serializer_class, tenant, user)

    def _process_import_inline(self, rows, mode, serializer_class, tenant, user):
        """Process small imports synchronously."""
        result = ImportResult()

        with transaction.atomic():
            for i, row in enumerate(rows, start=1):
                serializer = serializer_class(
                    data=row,
                    tenant=tenant,
                    user=user,
                    mode=mode,
                )

                try:
                    instance, created, warnings = serializer.import_row(row)
                    if created:
                        result.add_created(i, instance.id, warnings or None)
                    else:
                        result.add_updated(i, instance.id, warnings or None)

                except Exception as e:
                    if hasattr(e, 'detail'):
                        errors = e.detail
                    else:
                        errors = str(e)
                    result.add_error(i, errors)

        return Response(result.to_response(), status=status.HTTP_207_MULTI_STATUS)

    def _queue_background_import(self, rows, mode, serializer_class, tenant, user):
        """Queue large imports to Celery."""
        from Tracker.tasks import process_import_task

        # Get serializer path for task
        serializer_path = f"{serializer_class.__module__}.{serializer_class.__name__}"

        model = self._get_model()
        model_name = model.__name__ if model else 'Unknown'

        # Queue task
        task = process_import_task.delay(
            rows=rows,
            model_name=model_name,
            mode=mode,
            tenant_id=str(tenant.id) if tenant else None,
            user_id=user.id,
            serializer_path=serializer_path,
        )

        return Response({
            'task_id': task.id,
            'status': 'queued',
            'total_rows': len(rows),
            'message': f'Import queued for background processing. Poll /import-status/{task.id}/ for progress.',
        }, status=status.HTTP_202_ACCEPTED)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='task_id',
                description='Celery task ID from import response',
                required=True,
                type=str,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={
            200: inline_serializer(
                name='ImportStatusResponse',
                fields={
                    'task_id': serializers.CharField(),
                    'status': serializers.CharField(),
                    'progress': serializers.DictField(),
                    'result': serializers.DictField(required=False),
                }
            ),
        },
        description='Check status of a background import task.',
        tags=['Import/Export'],
    )
    @action(detail=False, methods=['get'], url_path='import-status/(?P<task_id>[^/.]+)')
    def import_status(self, request, task_id=None):
        """
        Check status of a background import task.

        Returns current state, progress, and results when complete.
        """
        result = AsyncResult(task_id)

        response = {
            'task_id': task_id,
            'status': result.status,
        }

        if result.status == 'PROGRESS':
            # Task is running, include progress info
            response['progress'] = result.info or {}
        elif result.status == 'SUCCESS':
            # Task completed
            response['progress'] = {
                'current': result.result.get('summary', {}).get('total', 0),
                'total': result.result.get('summary', {}).get('total', 0),
                'percent': 100,
            }
            response['result'] = result.result
        elif result.status == 'FAILURE':
            # Task failed
            response['error'] = str(result.result) if result.result else 'Unknown error'
        elif result.status == 'PENDING':
            # Task hasn't started yet
            response['progress'] = {'current': 0, 'total': 0, 'percent': 0}

        return Response(response)
