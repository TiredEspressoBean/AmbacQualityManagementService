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
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from rest_framework import serializers, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response

from Tracker.services.csv_utils import parse_file, ImportResult, normalize_header
from Tracker.serializers.csv_import import (
    BaseCSVImportSerializer,
    ImportMode,
    get_or_create_import_serializer,
)

# Threshold for background processing
BACKGROUND_IMPORT_THRESHOLD = 100

# The most rows one file may carry. A file is parsed whole into memory and, above
# BACKGROUND_IMPORT_THRESHOLD, sent to Celery as one message — so an unbounded file is
# an unbounded message. Split larger loads into several files.
from Tracker.services.csv_utils import MAX_UPLOAD_BYTES, MAX_UPLOAD_ROWS
MAX_IMPORT_ROWS = MAX_UPLOAD_ROWS

# The largest file accepted, checked BEFORE parsing. An .xlsx is a zip: a small upload
# can decompress to gigabytes, and the whole file is read into memory either way.
MAX_IMPORT_BYTES = MAX_UPLOAD_BYTES


class CSVImportMixin:
    """
    Mixin to add CSV/Excel import functionality to ViewSets.

    Adds endpoints:
    - GET /import-template/csv/ - Download CSV import template
    - GET /import-template/xlsx/ - Download Excel import template
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

    def _importable_columns(self):
        """Column names (lowercased) an import may write — the API serializer's writable
        fields, as `BaseCSVImportSerializer._writable_columns` enforces. None when the
        serializer can't be introspected (then nothing is filtered)."""
        from Tracker.serializers.csv_import import BaseCSVImportSerializer
        try:
            api = self.get_serializer_class()(context=self.get_serializer_context())
            cols = {n for n, f in api.fields.items() if not f.read_only}
        except Exception:
            return None
        # Plus what this model's import consumes itself (e.g. a part's step).
        importer = self.get_csv_import_serializer()
        cols |= set(getattr(getattr(importer, 'Meta', None), 'import_only_fields', ()) or ())
        return {c.lower() for c in cols - BaseCSVImportSerializer.NEVER_IMPORTED}

    def _importable_generator(self):
        """The template generator, limited to columns an import will accept — so a
        template and a preview never invite a column the import then refuses."""
        import copy
        generator = self.get_csv_template_generator()
        allowed = self._importable_columns()
        if generator is not None and allowed is not None:
            # A copy: a viewset may set `csv_template_generator` at class level, and
            # filtering that instance in place would shrink it for every later request.
            generator = copy.copy(generator)
            generator.fields = [f for f in generator.fields if f.name.lower() in allowed]
        if generator is not None:
            # A column the importer reads its own way explains itself (`Meta.import_column_help`)
            # — the model's help text says what the field is, not how an import fills it.
            importer = self.get_csv_import_serializer()
            help_text = getattr(getattr(importer, 'Meta', None), 'import_column_help', {}) or {}
            if help_text:
                generator = copy.copy(generator)
                fields = []
                for f in generator.fields:
                    if f.name in help_text:
                        f = copy.copy(f)
                        f.description = help_text[f.name]
                    fields.append(f)
                generator.fields = fields
        return generator

    def _too_big(self, file):
        if getattr(file, 'size', 0) and file.size > MAX_IMPORT_BYTES:
            return Response(
                {"detail": f"The file is {file.size // (1024 * 1024)} MB; imports take up to "
                           f"{MAX_IMPORT_BYTES // (1024 * 1024)} MB. Split it into smaller files."},
                status=status.HTTP_400_BAD_REQUEST)
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
        too_big = self._too_big(file)
        if too_big:
            return too_big
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

        # Get model fields from template generator — importable columns only
        generator = self._importable_generator()
        model_fields = []
        field_names_set = set()

        if generator:
            for field in generator.fields:
                # TemplateField has no display_name / field_type — reading them made
                # every preview 500, so the dialog never reached its mapping step.
                model_fields.append({
                    'name': field.name,
                    'display': field.name.replace('_', ' '),
                    'required': field.required,
                    'type': 'reference' if field.fk_model else 'choice' if field.choices else 'value',
                })
                field_names_set.add(field.name.lower())
            # `id` is never written, but it is how a row names the record it updates —
            # an exported file carries it — so offer it as a column to match on.
            if 'id' not in field_names_set:
                model_fields.insert(0, {'name': 'id', 'display': 'ID (matches an existing record)',
                                        'required': False, 'type': 'string'})
                field_names_set.add('id')

        # Build column mapping suggestions
        columns = []
        viewset_mapping = getattr(self, 'csv_field_mapping', {})
        reference_fields = {f['name'].lower() for f in model_fields if f['type'] == 'reference'}

        for header in headers:
            header_lower = normalize_header(header)
            mapped_to = None
            confidence = 'none'
            # An exported FK by name (`part_type__name` / "Part Type Name") is the FK.
            fk_base = next((header_lower[:-len(sfx)] for sfx in ('__name', '_name', '__ref', '_ref', '__email', '_email')
                            if header_lower.endswith(sfx)
                            and header_lower[:-len(sfx)] in reference_fields), None)

            # An export's looked-up ID column is a formula with nothing stored: skip it.
            if header_lower.endswith('(auto)'):
                pass
            # Check viewset's custom mapping first
            elif header_lower in viewset_mapping:
                mapped_to = viewset_mapping[header_lower]
                confidence = 'high'
            # Check exact match
            elif header_lower in field_names_set:
                mapped_to = header_lower
                confidence = 'high'
            elif fk_base:
                mapped_to = fk_base
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
    @action(detail=False, methods=['get'], url_path=r'import-template/(?P<template_format>csv|xlsx)')
    def import_template(self, request, template_format: str):
        """
        Download an import template.

        URL path determines format:
        - /import-template/csv/ - CSV format
        - /import-template/xlsx/ - Excel format
        """
        generator = self._importable_generator()

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
            content = generator.generate_excel(tenant=tenant, user=request.user)
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            filename = f'{model_name.lower()}_import_template.xlsx'

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

        too_big = self._too_big(file)
        if too_big:
            return too_big

        # Get import mode
        mode = request.data.get('mode', ImportMode.UPSERT)
        if mode not in [ImportMode.CREATE, ImportMode.UPDATE, ImportMode.UPSERT]:
            return Response(
                {"detail": f"Invalid mode '{mode}'. Use 'create', 'update', or 'upsert'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update and upsert rewrite existing records, so they need the model's CHANGE
        # permission as well — the POST gate only checks ADD, which let anyone who could
        # create a model's rows overwrite any of them through a file.
        if mode != ImportMode.CREATE:
            model = self._get_model()
            if model is not None:
                perm = f"change_{model._meta.model_name}"
                if not request.user.has_tenant_perm(perm):
                    return Response(
                        {"detail": f"Mode '{mode}' updates existing records, which needs the "
                                   f"'{perm}' permission. Use mode 'create' to add new ones only."},
                        status=status.HTTP_403_FORBIDDEN,
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
        if len(rows) > MAX_IMPORT_ROWS:
            return Response(
                {"detail": f"{len(rows)} rows is more than one import takes "
                           f"({MAX_IMPORT_ROWS}). Split the file and import it in parts."},
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
        api_class = self.get_serializer_class()
        api_context = self.get_serializer_context()
        with transaction.atomic():
            for i, row in enumerate(rows, start=1):
                serializer = serializer_class(
                    data=row,
                    tenant=tenant,
                    user=user,
                    mode=mode,
                    api_serializer_class=api_class,
                    api_context=api_context,
                )
                # A savepoint per row. Without one, the first row that failed IN THE
                # DATABASE left the whole transaction aborted, and every row after it
                # failed too — reported as unrelated per-row errors.
                sid = transaction.savepoint()
                try:
                    instance, created, warnings = serializer.import_row(row)
                    transaction.savepoint_commit(sid)
                    if created:
                        result.add_created(i, instance.id, warnings or None)
                    else:
                        result.add_updated(i, instance.id, warnings or None)
                except Exception as e:
                    transaction.savepoint_rollback(sid)
                    if hasattr(e, 'detail'):
                        errors = e.detail
                    else:
                        errors = str(e)
                    result.add_error(i, errors)

        return Response(result.to_response(), status=status.HTTP_207_MULTI_STATUS)

    def _queue_background_import(self, rows, mode, serializer_class, tenant, user):
        """Queue large imports to Celery."""
        from uuid import uuid4
        from Tracker.tasks import process_import_task

        # Get serializer path for task
        serializer_path = f"{serializer_class.__module__}.{serializer_class.__name__}"
        # An importer built at runtime (`create_import_serializer_for_model`, or the
        # registry's fallback) lives at no module path, so its own path imports nothing
        # and every background import (100+ rows) failed "Invalid serializer". Point the
        # task at the viewset instead; it asks the viewset for its importer.
        import importlib
        try:
            found = getattr(importlib.import_module(serializer_class.__module__),
                            serializer_class.__name__, None)
        except ImportError:
            found = None
        if found is not serializer_class:
            serializer_path = f"viewset:{type(self).__module__}.{type(self).__name__}"

        model = self._get_model()
        model_name = model.__name__ if model else 'Unknown'

        # Pre-generate a task id so we can return it synchronously and still
        # dispatch after commit. apply_async accepts task_id as kwarg.
        task_id = str(uuid4())
        tenant_id = str(tenant.id) if tenant else None
        user_id = user.id
        api_class = self.get_serializer_class()
        api_serializer_path = f"{api_class.__module__}.{api_class.__qualname__}"
        # Who may read this task's status: the user who started it, in this tenant.
        from django.core.cache import cache
        cache.set(f"import-owner:{task_id}", f"{tenant_id}:{user_id}", 60 * 60 * 24)
        transaction.on_commit(lambda: process_import_task.apply_async(
            kwargs={
                'rows': rows,
                'model_name': model_name,
                'mode': mode,
                'tenant_id': tenant_id,
                'user_id': user_id,
                'serializer_path': serializer_path,
                'api_serializer_path': api_serializer_path,
            },
            task_id=task_id,
        ))

        return Response({
            'task_id': task_id,
            'status': 'queued',
            'total_rows': len(rows),
            'message': f'Import queued for background processing. Poll /import-status/{task_id}/ for progress.',
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
    @action(detail=False, methods=['get'], url_path=r'import-status/(?P<task_id>[^/.]+)')
    def import_status(self, request, task_id=None):
        """
        Check status of a background import task.

        Returns current state, progress, and results when complete.
        """
        # Only the import's own starter may read it. Without this any user could read
        # any Celery task's result — another tenant's import, or an unrelated task — by
        # id. Ids are random, but a result is not a capability to leave lying about.
        from django.core.cache import cache
        tenant = getattr(self, 'tenant', None) or getattr(request.user, 'tenant', None)
        owner = cache.get(f"import-owner:{task_id}")
        if owner != f"{getattr(tenant, 'id', None)}:{request.user.id}":
            return Response({"detail": "Import not found."}, status=status.HTTP_404_NOT_FOUND)

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
