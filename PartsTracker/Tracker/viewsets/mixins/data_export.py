"""
Data Export Mixin for ViewSets.

Provides export endpoints for filtered data in CSV and Excel formats.
Auto-configures from model introspection when no custom config is provided.
"""

import io
from typing import Dict, List, Optional

import pandas as pd
from django.db import models
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.decorators import action
from rest_framework.response import Response

# Fields to skip in auto-export
SKIP_EXPORT_FIELDS = {
    'tenant', 'created_by', 'modified_by', 'classification',
    'previous_version', 'is_current_version',
}


def get_exportable_fields(model) -> List[str]:
    """
    Get list of exportable fields from a model via introspection.

    Includes regular fields and common FK display fields (e.g., part_type__name).
    """
    fields = []

    for field in model._meta.get_fields():
        # Skip reverse relations
        if field.auto_created and not field.concrete:
            continue

        # Skip system fields
        if field.name in SKIP_EXPORT_FIELDS:
            continue

        # Handle ForeignKey - add both ID and name lookup
        if isinstance(field, models.ForeignKey):
            fields.append(field.name)
            # Add __name lookup if related model has name field
            related_model = field.related_model
            if hasattr(related_model, 'name'):
                fields.append(f'{field.name}__name')
            continue

        # Skip ManyToMany
        if isinstance(field, models.ManyToManyField):
            continue

        # Include regular fields
        if hasattr(field, 'name'):
            fields.append(field.name)

    return fields


def get_field_label(field_name: str) -> str:
    """Convert field name to human-readable label."""
    # Handle __ lookups
    if '__' in field_name:
        parts = field_name.split('__')
        return ' '.join(p.replace('_', ' ').title() for p in parts)

    return field_name.replace('_', ' ').title()


class DataExportMixin:
    """
    Mixin to add CSV/Excel export functionality to ViewSets.

    Adds endpoint:
    - GET /export/ - Download filtered data as CSV or Excel

    Works automatically with any model through introspection.
    Override attributes for customization:

    - export_fields: List of fields to export (auto-detected if not set)
    - export_filename: Base filename for exports (model name if not set)
    - export_field_labels: Dict mapping field names to display labels

    Example:
        # Basic - just add the mixin, everything auto-configured
        class PartsViewSet(DataExportMixin, viewsets.ModelViewSet):
            queryset = Parts.objects.all()

        # Custom - specify fields and labels
        class PartsViewSet(DataExportMixin, viewsets.ModelViewSet):
            export_fields = ['ERP_id', 'part_type__name', 'part_status']
            export_field_labels = {'ERP_id': 'Part ID', 'part_type__name': 'Part Type'}
    """

    export_fields: Optional[List[str]] = None
    export_filename: Optional[str] = None
    export_field_labels: Dict[str, str] = {}

    def _get_model(self):
        """Get the model class from queryset."""
        if hasattr(self, 'queryset') and self.queryset is not None:
            return self.queryset.model
        return None

    def get_export_fields(self) -> List[str]:
        """
        Get the list of fields to export.

        Priority:
        1. Query param ?fields=id,name,status (user override)
        2. self.export_fields (class attribute)
        3. Auto-detected from model (all non-system fields)
        """
        # Check query params first
        if hasattr(self, 'request'):
            fields_param = self.request.query_params.get('fields')
            if fields_param:
                return [f.strip() for f in fields_param.split(',')]

        # Use class attribute if specified
        if self.export_fields:
            return self.export_fields

        # Auto-detect from model
        model = self._get_model()
        if model:
            return get_exportable_fields(model)

        return ['id']

    def get_export_filename(self, format: str) -> str:
        """
        Get the filename for the export.

        Priority:
        1. Query param ?filename=custom
        2. self.export_filename (class attribute)
        3. Model name
        """
        if hasattr(self, 'request'):
            filename_param = self.request.query_params.get('filename')
            if filename_param:
                base_name = filename_param.rsplit('.', 1)[0]
                return f"{base_name}.{format}"

        if self.export_filename:
            return f"{self.export_filename}.{format}"

        model = self._get_model()
        if model:
            return f"{model.__name__.lower()}_export.{format}"

        return f"export.{format}"

    def get_export_field_labels(self) -> Dict[str, str]:
        """
        Get field label mapping.

        Merges auto-generated labels with custom labels.
        """
        labels = {}

        # Auto-generate labels for all fields
        for field in self.get_export_fields():
            labels[field] = get_field_label(field)

        # Override with custom labels
        labels.update(self.export_field_labels)

        return labels

    def get_export_queryset(self):
        """
        Get the queryset for export.

        Uses the same filtering as the list view.
        """
        return self.filter_queryset(self.get_queryset())

    def prepare_export_data(self, queryset, fields: List[str]) -> pd.DataFrame:
        """
        Prepare data for export as a DataFrame.

        Handles related field lookups (field__subfield) and applies labels.
        """
        # Separate simple fields from related fields
        simple_fields = []
        related_lookups = {}

        for field in fields:
            if '__' in field:
                # Related field lookup
                parts = field.split('__')
                related_lookups[field] = parts
            else:
                simple_fields.append(field)

        # Get data using values()
        if simple_fields:
            data = list(queryset.values(*simple_fields))
        else:
            data = list(queryset.values('id'))

        # Add related field values
        if related_lookups:
            # Re-fetch with related objects for lookups
            for i, obj in enumerate(queryset):
                for field_key, parts in related_lookups.items():
                    value = obj
                    for part in parts:
                        value = getattr(value, part, None)
                        if value is None:
                            break
                    if i < len(data):
                        data[i][field_key] = value

        # Create DataFrame
        df = pd.DataFrame(data)

        # Reorder columns to match requested fields order
        existing_cols = [f for f in fields if f in df.columns]
        if existing_cols:
            df = df[existing_cols]

        # Apply field labels for column names
        labels = self.get_export_field_labels()
        rename_map = {f: labels.get(f, f) for f in df.columns if f in labels}
        if rename_map:
            df.rename(columns=rename_map, inplace=True)

        return df

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='format',
                description='Export format (csv or xlsx)',
                required=False,
                type=str,
                enum=['csv', 'xlsx'],
                default='xlsx',
            ),
            OpenApiParameter(
                name='fields',
                description='Comma-separated list of fields to export',
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name='filename',
                description='Custom filename for the download',
                required=False,
                type=str,
            ),
        ],
        responses={
            200: {
                'type': 'string',
                'format': 'binary',
                'description': 'File download'
            }
        },
        description='Export filtered data to CSV or Excel format.',
        tags=['Import/Export'],
    )
    @action(detail=False, methods=['get'], url_path='export')
    def export_data(self, request):
        """
        Export filtered data to CSV or Excel.

        Query params:
        - format: 'csv' or 'xlsx' (default: xlsx)
        - fields: Comma-separated field names
        - filename: Custom filename

        Respects all filters, search, and ordering applied to the list view.
        """
        export_format = request.query_params.get('format', 'xlsx').lower()
        if export_format not in ['csv', 'xlsx']:
            export_format = 'xlsx'

        # Get filtered queryset
        queryset = self.get_export_queryset()

        # Get fields to export
        fields = self.get_export_fields()

        # Prepare DataFrame
        df = self.prepare_export_data(queryset, fields)

        # Generate filename
        filename = self.get_export_filename(export_format)

        # Create response
        if export_format == 'csv':
            output = io.StringIO()
            df.to_csv(output, index=False)
            content = output.getvalue().encode('utf-8-sig')
            content_type = 'text/csv'
        else:
            output = io.BytesIO()
            df.to_excel(output, index=False, engine='openpyxl')
            output.seek(0)
            content = output.getvalue()
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

        response = HttpResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
