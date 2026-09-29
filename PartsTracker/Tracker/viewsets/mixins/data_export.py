"""
Data Export Mixin for ViewSets.

Provides export endpoints for filtered data in CSV and Excel formats.
Auto-configures from model introspection when no custom config is provided.

Excel exports include:
- Main data sheet
- Reference sheets for foreign key lookups
- Data validation dropdowns for FK fields
- Conditional formatting for required fields
- Instructions sheet with field documentation
"""

import io
import re
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.decorators import action

# openpyxl imports for advanced Excel features
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.table import Table, TableStyleInfo

from Tracker.services.spreadsheet_safety import csv_safe, write_cell

# Fields to skip in auto-export
SKIP_EXPORT_FIELDS = {
    'tenant', 'created_by', 'modified_by', 'classification',
    'previous_version', 'is_current_version',
}

# Fields that are typically required
COMMON_REQUIRED_FIELDS = {'id', 'name', 'ERP_id'}

# The most rows one export returns. The whole filtered table is built in memory in a
# single request, so an unfiltered export of a large table could exhaust the worker.
# Past this the user is asked to filter the list first.
MAX_EXPORT_ROWS = 50_000


def _is_sensitive_segment(segment: str) -> bool:
    """Never exported, whatever a serializer or a `?fields=` request says.

    Belt and braces behind the serializer allow-list: a serializer that forgot to hide
    a credential must not turn an export into a way to read it.
    """
    s = segment.lower()
    return s == 'password' or 'secret' in s or 'token' in s or s == 'api_key'


def _is_sensitive_path(path: str) -> bool:
    """A path is refused if ANY segment is sensitive — `created_by__password` as well
    as `password`."""
    return any(_is_sensitive_segment(seg) for seg in path.split('__'))


def _model_path(model, dotted: str) -> Optional[str]:
    """`part.work_order.ERP_id` -> `part__work_order__ERP_id` when every segment is a
    concrete column or forward relation, else None.

    Only such paths can be exported: they are what `.values()` fetches in the ONE query
    the export makes. A property, a method field or a reverse relation is not.
    """
    if not dotted or dotted == '*':
        return None
    current = model
    parts = dotted.split('.')
    for i, part in enumerate(parts):
        try:
            field = current._meta.get_field(part)
        except Exception:
            return None
        if not getattr(field, 'concrete', False) or field.many_to_many:
            return None
        if i < len(parts) - 1:
            if not field.is_relation:
                return None
            current = field.related_model
    return '__'.join(parts)


def _has_name_column(model) -> bool:
    """Does `model` have a concrete `name` DB column?

    `hasattr(model, 'name')` is not the same question: ContentType.name is a
    *property* returning the verbose name, so hasattr says yes while
    `.values('content_type__name')` raises FieldError. Any model with a
    content_type FK -- Documents, ApprovalRequest, … -- failed to export
    because of that.
    """
    try:
        field = model._meta.get_field('name')
    except Exception:
        return False
    return getattr(field, 'concrete', False)


def _is_steps(model) -> bool:
    return model._meta.label == 'Tracker.Steps'


def _is_user(model) -> bool:
    from django.contrib.auth import get_user_model
    return model is get_user_model()


def virtual_export_columns(model) -> Dict[str, tuple]:
    """Columns an export computes rather than reads with `.values()`.

    `{column: (kind, field_name)}` — kind is 'm2m' (a many-to-many set as `a; b`) or
    'step_ref' (a step FK as `Process > Step`). Both are written in the form an import
    reads back: see csv_import.M2M_SEPARATOR and Tracker.services.step_refs.
    """
    out = {}
    for field in model._meta.get_fields():
        if isinstance(field, models.ManyToManyField):
            out[field.name] = ('m2m', field.name)
        elif isinstance(field, models.ForeignKey) and _is_steps(field.related_model):
            out[f'{field.name}__ref'] = ('step_ref', field.name)
    return out


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

        # Skip GenericForeignKey. It is not a database column -- it is a
        # descriptor over (content_type, object_id) -- so naming it in
        # .values() raises FieldError: "Cannot resolve keyword 'content_object'
        # into field". Its two backing columns are concrete and get exported on
        # their own. Every model with a GFK (ApprovalRequest, Documents, …)
        # failed to export before this.
        if isinstance(field, GenericForeignKey):
            continue

        # Skip system fields
        if field.name in SKIP_EXPORT_FIELDS:
            continue

        # Handle ForeignKey - add both ID and a readable column that imports back
        if isinstance(field, models.ForeignKey):
            fields.append(field.name)
            related_model = field.related_model
            if _is_steps(related_model):
                fields.append(f'{field.name}__ref')  # "Process > Step"
            elif _is_user(related_model):
                fields.append(f'{field.name}__email')
            elif _has_name_column(related_model):
                fields.append(f'{field.name}__name')
            continue

        # ManyToMany: one column listing the related rows, `a; b`
        if isinstance(field, models.ManyToManyField):
            fields.append(field.name)
            continue

        # Include regular fields
        if hasattr(field, 'name'):
            fields.append(field.name)

    return fields


def get_fk_fields(model) -> Dict[str, models.ForeignKey]:
    """
    Get all ForeignKey fields from a model.

    Returns dict mapping field name to the field object.
    """
    fk_fields = {}

    for field in model._meta.get_fields():
        if isinstance(field, models.ForeignKey):
            if field.name not in SKIP_EXPORT_FIELDS:
                fk_fields[field.name] = field

    return fk_fields


def get_choice_fields(model) -> Dict[str, List[str]]:
    """
    Get all fields with choices (enums) from a model.

    Returns dict mapping field name to list of valid choice values.
    """
    choice_fields = {}

    for field in model._meta.get_fields():
        if field.auto_created and not field.concrete:
            continue
        if field.name in SKIP_EXPORT_FIELDS:
            continue

        # Check for choices
        if hasattr(field, 'choices') and field.choices:
            # Handle both tuples and enum-style choices
            choices = []
            for choice in field.choices:
                if isinstance(choice, (list, tuple)) and len(choice) >= 1:
                    choices.append(str(choice[0]))
                else:
                    choices.append(str(choice))
            if choices:
                choice_fields[field.name] = choices

    return choice_fields


def get_boolean_fields(model) -> List[str]:
    """
    Get all boolean fields from a model.

    Returns list of field names.
    """
    boolean_fields = []

    for field in model._meta.get_fields():
        if field.auto_created and not field.concrete:
            continue
        if field.name in SKIP_EXPORT_FIELDS:
            continue

        if isinstance(field, (models.BooleanField, models.NullBooleanField)):
            boolean_fields.append(field.name)

    return boolean_fields


def get_field_info(model) -> Dict[str, Dict[str, Any]]:
    """
    Get detailed field information for documentation.

    Returns dict with field metadata including type, required, choices, etc.
    """
    field_info = {}

    for field in model._meta.get_fields():
        if field.auto_created and not field.concrete:
            continue
        if field.name in SKIP_EXPORT_FIELDS:
            continue
        if isinstance(field, models.ManyToManyField):
            continue

        info = {
            'name': field.name,
            'type': type(field).__name__,
            'required': not getattr(field, 'blank', True) or not getattr(field, 'null', True),
            'description': getattr(field, 'help_text', '') or '',
            'choices': None,
            'related_model': None,
        }

        # Get choices if available
        if hasattr(field, 'choices') and field.choices:
            info['choices'] = [str(c[0]) for c in field.choices]

        # Get related model for FKs
        if isinstance(field, models.ForeignKey):
            info['related_model'] = field.related_model.__name__
            info['description'] = info['description'] or f"Reference to {field.related_model.__name__}"

        field_info[field.name] = info

    return field_info


def get_field_label(field_name: str) -> str:
    """Convert field name to human-readable label."""
    # Handle __ lookups
    if '__' in field_name:
        parts = field_name.split('__')
        return ' '.join(p.replace('_', ' ').title() for p in parts)

    return field_name.replace('_', ' ').title()


def sanitize_sheet_name(name: str) -> str:
    """Sanitize a string to be a valid Excel sheet name."""
    # Excel sheet names: max 31 chars, no []:*?/\
    name = re.sub(r'[\[\]:*?/\\]', '', name)
    return name[:31]


def make_excel_safe_name(name: str) -> str:
    """Convert a string to a valid Excel named range identifier."""
    # Must start with letter or underscore, only alphanumeric and underscore
    safe = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    if safe and safe[0].isdigit():
        safe = '_' + safe
    return safe


class DataExportMixin:
    """
    Mixin to add CSV/Excel export functionality to ViewSets.

    Adds endpoints:
    - GET /export/csv/ - Download filtered data as CSV
    - GET /export/xlsx/ - Download filtered data as Excel (with reference sheets)

    Excel exports include:
    - Main data sheet with your filtered data
    - Reference sheets for each foreign key relationship
    - Data validation dropdowns for FK columns
    - Conditional formatting highlighting required fields
    - Instructions sheet documenting all fields

    Works automatically with any model through introspection.
    Override attributes for customization:

    - export_fields: List of fields to export (auto-detected if not set)
    - export_filename: Base filename for exports (model name if not set)
    - export_field_labels: Dict mapping field names to display labels
    - export_include_references: Whether to include FK reference sheets (default True)

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
    export_include_references: bool = True
    # Paths exported beyond what the serializer shows — a deliberate, per-viewset choice
    # (see get_export_allowed_paths). E.g. {'user__email'} so a row about a person
    # exports them in a form an import reads back.
    export_extra_paths: frozenset = frozenset()

    def _get_model(self):
        """Get the model class from queryset."""
        if hasattr(self, 'queryset') and self.queryset is not None:
            return self.queryset.model
        return None

    def get_export_allowed_paths(self) -> Optional[set]:
        """Model paths this viewset's serializer already shows its reader.

        An export can never show more than the API does. It reads the model directly,
        so without this every column a serializer deliberately hides — a password hash,
        a field masked for this user — was exportable, and `?fields=` reached any of
        them through any relation. The serializer is instantiated with the request
        context, so a field it drops for this user is dropped here too.

        A foreign key the serializer shows also allows `<fk>__name`: the related row's
        name is what the dropdown sheets are built from.

        None when the serializer cannot be introspected; callers then fall back to the
        model's own fields minus sensitive ones, never to "anything".
        """
        model = self._get_model()
        if model is None:
            return None
        try:
            serializer = self.get_serializer_class()(context=self.get_serializer_context())
            fields = serializer.fields
        except Exception:
            return None
        allowed = {'id'}
        m2m_names = {f.name for f in model._meta.many_to_many}
        for name, field in fields.items():
            if getattr(field, 'write_only', False):
                continue
            source = getattr(field, 'source', None) or name
            if source in m2m_names:
                allowed.add(source)  # listed as `a; b`
                continue
            path = _model_path(model, source)
            if path is None:
                continue
            allowed.add(path)
            if '__' not in path:
                mf = model._meta.get_field(path)
                if isinstance(mf, models.ForeignKey):
                    if _is_steps(mf.related_model):
                        allowed.add(f'{path}__ref')
                    elif _has_name_column(mf.related_model):
                        allowed.add(f'{path}__name')
        # A person's email is NOT allowed just because the serializer shows their ID:
        # it is data the API may deliberately hide. A viewset whose rows are about a
        # person (a labor block) opts in: `export_extra_paths = {'user__email'}`.
        allowed |= set(self.export_extra_paths or ())
        return {p for p in allowed if not _is_sensitive_path(p)}

    def get_export_fields(self) -> List[str]:
        """
        Get the list of fields to export.

        Priority:
        1. Query param ?fields=id,name,status (user override)
        2. self.export_fields (class attribute)
        3. Auto-detected from model (all non-system fields)

        Whichever it is, only paths the serializer shows (`get_export_allowed_paths`),
        and no sensitive path, survive. A requested field outside that is refused with
        a 400 naming it rather than dropped silently.
        """
        from rest_framework.exceptions import ValidationError

        allowed = self.get_export_allowed_paths()

        def permitted(path: str) -> bool:
            if _is_sensitive_path(path):
                return False
            return allowed is None or path in allowed

        if hasattr(self, 'request'):
            fields_param = self.request.query_params.get('fields')
            if fields_param:
                requested = [f.strip() for f in fields_param.split(',') if f.strip()]
                refused = [f for f in requested if not permitted(f)]
                if refused:
                    raise ValidationError({'fields': (
                        f"Not exportable: {', '.join(refused)}. Only fields this list "
                        "already shows can be exported.")})
                return requested

        if self.export_fields:
            return [f for f in self.export_fields if permitted(f)] or ['id']

        model = self._get_model()
        if model:
            return [f for f in get_exportable_fields(model) if permitted(f)] or ['id']

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

        Uses the same filtering as the list view — and, for a versioned model, only
        the current versions. Several of those viewsets list every version (or limit to
        current only for the `list` action), so an export carried superseded rows too:
        the same code twice, and an edit to an old row's line would land on the old row.
        """
        qs = self.filter_queryset(self.get_queryset())
        model = qs.model
        if getattr(model, '_is_versioned', False) and any(
                f.name == 'is_current_version' for f in model._meta.concrete_fields):
            qs = qs.filter(is_current_version=True)
        return qs

    def _export_timezone(self):
        """The tenant's shop-floor clock (`Tenant.default_timezone`), else UTC."""
        import zoneinfo
        tenant = getattr(self, 'tenant', None) or getattr(
            getattr(getattr(self, 'request', None), 'user', None), 'tenant', None)
        name = getattr(tenant, 'default_timezone', None) or 'UTC'
        try:
            return zoneinfo.ZoneInfo(name)
        except Exception:
            return zoneinfo.ZoneInfo('UTC')

    def _convert_df_for_excel(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert DataFrame types for Excel compatibility."""
        for col in df.columns:
            # Timezone-aware datetimes (openpyxl doesn't support them) are written on
            # the tenant's clock, and an import reads them on the same clock. Stripping
            # the zone without converting wrote UTC, which is what people then typed.
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                try:
                    if df[col].dt.tz is not None:
                        df[col] = df[col].dt.tz_convert(self._export_timezone()).dt.tz_localize(None)
                except (AttributeError, TypeError):
                    pass
            # Convert object columns (UUIDs, complex objects, etc.). A list or dict is
            # written as JSON — its Python repr (`[{'start': ...}]`) couldn't be read back.
            elif df[col].dtype == 'object':
                import json as _json
                df[col] = df[col].apply(
                    lambda x: _json.dumps(x, default=str) if isinstance(x, (list, dict))
                    else str(x) if x is not None and not isinstance(x, (str, int, float, bool)) else x
                )
        return df

    def prepare_export_data(self, queryset, fields: List[str], apply_labels: bool = True) -> pd.DataFrame:
        """
        Prepare data for export as a DataFrame.

        Handles related field lookups (field__subfield) and applies labels.
        """
        # One query for every column, related ones included. Related columns used to
        # be filled by a second pass over the queryset and matched to the first by
        # POSITION: two queries whose row order agreed only when the ordering had no
        # ties, so a row could carry another row's related values — and the second
        # pass cost a query per relation per row. `.values()` follows `fk__name` itself.
        virtual = virtual_export_columns(queryset.model)
        wanted_virtual = [f for f in fields if f in virtual]
        db_fields = [f for f in fields if f not in virtual]
        need_id = bool(wanted_virtual) and 'id' not in db_fields
        data = list(queryset.values(*((db_fields + (['id'] if need_id else [])) or ['id'])))
        if wanted_virtual:
            self._fill_virtual_columns(queryset.model, data, wanted_virtual, virtual)
            if need_id:
                for row in data:
                    row.pop('id', None)

        # Create DataFrame
        df = pd.DataFrame(data, columns=[f for f in fields] if not data else None)

        # Convert types for Excel compatibility
        df = self._convert_df_for_excel(df)

        # Reorder columns to match requested fields order
        existing_cols = [f for f in fields if f in df.columns]
        if existing_cols:
            df = df[existing_cols]

        # Apply field labels for column names
        if apply_labels:
            labels = self.get_export_field_labels()
            rename_map = {f: labels.get(f, f) for f in df.columns if f in labels}
            if rename_map:
                df.rename(columns=rename_map, inplace=True)

        return df

    def _fill_virtual_columns(self, model, data, columns, virtual) -> None:
        """Fill each computed column (see `virtual_export_columns`) into `data`, in a
        couple of queries per column however many rows there are."""
        from Tracker.services.step_refs import step_refs
        from Tracker.serializers.csv_import import M2M_SEPARATOR

        ids = [row['id'] for row in data]
        for column in columns:
            kind, field_name = virtual[column]
            if kind == 'step_ref':
                pairs = list(model.objects.filter(pk__in=ids).values_list('pk', field_name))  # tenant-safe: .objects auto-scopes
                refs = step_refs(r for _, r in pairs)
                by_row = {pk: refs.get(r) for pk, r in pairs}
                for row in data:
                    row[column] = by_row.get(row['id'])
                continue
            # m2m
            rel_model = model._meta.get_field(field_name).related_model
            pairs = [(pk, r) for pk, r in model.objects.filter(pk__in=ids)  # tenant-safe: .objects auto-scopes
                     .values_list('pk', field_name) if r is not None]
            rel_ids = {r for _, r in pairs}
            if _is_steps(rel_model):
                labels = step_refs(rel_ids)
            elif _has_name_column(rel_model):
                labels = dict(rel_model.objects.filter(pk__in=rel_ids).values_list('pk', 'name'))  # tenant-safe: .objects auto-scopes
            else:
                labels = {o.pk: str(o) for o in rel_model.objects.filter(pk__in=rel_ids)}  # tenant-safe: .objects auto-scopes
            grouped: Dict[Any, List[str]] = {}
            for pk, r in pairs:
                if r in labels:
                    grouped.setdefault(pk, []).append(str(labels[r]))
            for row in data:
                row[column] = M2M_SEPARATOR.join(sorted(grouped.get(row['id'], [])))

    def _get_reference_data(self, fk_field: models.ForeignKey, limit: int = 1000) -> pd.DataFrame:
        """
        Get reference data for a foreign key field.

        Returns DataFrame with id and display columns for the related model.
        """
        related_model = fk_field.related_model

        # Determine display field (prefer name, then fall back to str)
        if _has_name_column(related_model):
            display_field = 'name'
        else:
            display_field = None

        # Only rows this user may see. `.objects` scopes by tenant but not by the
        # user's own permission, so a reference sheet listed every related row in the
        # tenant — every user by name, say — to someone who can't view that model.
        manager = related_model.objects
        user = getattr(getattr(self, 'request', None), 'user', None)
        qs = manager.for_user(user) if (user is not None and hasattr(manager, 'for_user')) \
            else manager.all()

        # Limit results — one extra row fetched, to know whether the list was cut short.
        qs = list(qs[:limit + 1])
        truncated = len(qs) > limit
        qs = qs[:limit]

        # Get data
        if display_field:
            data = [{'id': obj.pk, 'name': getattr(obj, display_field)} for obj in qs]
        else:
            data = [{'id': str(obj.pk), 'name': str(obj)} for obj in qs]
        df = pd.DataFrame(data)

        # Convert types
        df = self._convert_df_for_excel(df)

        df.attrs['truncated'] = truncated
        return df

    def _create_instructions_sheet(self, ws, model, field_info: Dict[str, Dict], fk_fields: Dict[str, models.ForeignKey]):
        """Create the instructions sheet with field documentation."""
        # Styles
        header_font = Font(bold=True, size=12)
        header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
        header_font_white = Font(bold=True, color='FFFFFF')
        required_fill = PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid')

        # Title
        ws['A1'] = f'{model.__name__} Import/Export Guide'
        ws['A1'].font = Font(bold=True, size=16)
        ws.merge_cells('A1:E1')

        # Headers
        headers = ['Field Name', 'Required', 'Type', 'Description', 'Valid Values / Reference']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=3, column=col, value=header)
            cell.font = header_font_white
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')

        # Field rows
        row = 4
        for field_name, info in field_info.items():
            ws.cell(row=row, column=1, value=field_name)

            required_cell = ws.cell(row=row, column=2, value='Yes' if info['required'] else 'No')
            if info['required']:
                required_cell.fill = required_fill

            ws.cell(row=row, column=3, value=info['type'])
            ws.cell(row=row, column=4, value=info['description'])

            # Valid values
            if info['choices']:
                ws.cell(row=row, column=5, value=', '.join(info['choices']))
            elif info['related_model']:
                ws.cell(row=row, column=5, value=f"See '{info['related_model']}' sheet")

            row += 1

        # Adjust column widths
        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 10
        ws.column_dimensions['C'].width = 15
        ws.column_dimensions['D'].width = 40
        ws.column_dimensions['E'].width = 30

    def _create_reference_sheet(self, wb: Workbook, fk_name: str, fk_field: models.ForeignKey) -> Optional[Dict[str, Any]]:
        """
        Create a reference sheet for a foreign key.

        Returns dict with sheet info if successful:
        - range_name: Named range for dropdown
        - sheet_name: The worksheet name
        - max_row: Last row of data
        """
        ref_df = self._get_reference_data(fk_field)

        if ref_df.empty:
            return None

        # Create sheet
        related_name = fk_field.related_model.__name__
        sheet_name = sanitize_sheet_name(related_name)

        # Handle duplicate sheet names
        existing_names = [ws.title for ws in wb.worksheets]
        if sheet_name in existing_names:
            sheet_name = sanitize_sheet_name(f"{fk_name}_{related_name}")[:31]

        ws = wb.create_sheet(title=sheet_name)

        # Style settings
        header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF')

        # Write headers
        ws.cell(row=1, column=1, value='ID').font = header_font
        ws.cell(row=1, column=1).fill = header_fill
        ws.cell(row=1, column=2, value='Name').font = header_font
        ws.cell(row=1, column=2).fill = header_fill

        # Write data
        for row_idx, row_data in enumerate(ref_df.values, 2):
            for col_idx, value in enumerate(row_data, 1):
                write_cell(ws, row_idx, col_idx, value)

        # Adjust column widths
        ws.column_dimensions['A'].width = 40  # UUID width
        ws.column_dimensions['B'].width = 30

        # Create named range for the name column (for dropdowns)
        range_name = make_excel_safe_name(f"ref_{fk_name}")
        max_row = len(ref_df) + 1

        # Named range for the name column (column B, rows 2 to end)
        from openpyxl.workbook.defined_name import DefinedName
        ref = f"'{sheet_name}'!$B$2:$B${max_row}"
        defn = DefinedName(range_name, attr_text=ref)
        wb.defined_names[range_name] = defn

        truncated = bool(ref_df.attrs.get('truncated'))
        if truncated:
            # Say so on the sheet: this list is the first rows only.
            write_cell(ws, 1, 4, f"First {len(ref_df)} only — a value not listed can still "
                                 "be typed into the Data sheet.")
        return {
            'range_name': range_name,
            'sheet_name': sheet_name,
            'max_row': max_row,
            'truncated': truncated,
        }

    def _add_data_validation(self, ws, col_idx: int, range_name: str, max_row: int,
                             strict: bool = True):
        """Add dropdown data validation to a column."""
        col_letter = get_column_letter(col_idx)

        # Create data validation with reference to named range
        dv = DataValidation(
            type='list',
            formula1=f'={range_name}',
            allow_blank=True,
            showDropDown=False,  # False means show dropdown (confusing API)
            showErrorMessage=True,
            errorTitle='Invalid Value',
            error='Please select a value from the dropdown list.',
        )
        # A truncated list can't be strict: Excel's default "stop" style would refuse a
        # valid value that is simply past the reference sheet's cap, and flag every
        # existing row holding one. Warn instead.
        if not strict:
            dv.errorStyle = 'warning'
            dv.error = ('Not in the list shown — the list is incomplete, so this may '
                        'still be valid.')

        # Apply to column (rows 2 to max_row, skipping header)
        dv.add(f'{col_letter}2:{col_letter}{max_row}')
        ws.add_data_validation(dv)

    def _add_inline_data_validation(self, ws, col_idx: int, values: List[str], max_row: int):
        """Add dropdown data validation with inline values (for small lists like enums)."""
        col_letter = get_column_letter(col_idx)

        # Excel inline list format: "value1,value2,value3"
        # Max length is ~255 chars, so this works for small choice lists
        values_str = ','.join(str(v) for v in values)

        dv = DataValidation(
            type='list',
            formula1=f'"{values_str}"',
            allow_blank=True,
            showDropDown=False,
            showErrorMessage=True,
            errorTitle='Invalid Value',
            error='Please select a value from the dropdown list.',
        )

        dv.add(f'{col_letter}2:{col_letter}{max_row}')
        ws.add_data_validation(dv)

    def _create_excel_export(self, queryset, fields: List[str], include_references: bool = True) -> bytes:
        """
        Create a full-featured Excel export with reference sheets.

        Returns the Excel file as bytes.
        """
        model = self._get_model()
        # Reference sheets only for the foreign keys actually being exported — every FK
        # on the model got one before, whether or not its column was in the file.
        exported = {f.split('__')[0] for f in fields}
        fk_fields = {k: v for k, v in (get_fk_fields(model) if model else {}).items()
                     if k in exported}
        choice_fields = get_choice_fields(model) if model else {}
        boolean_fields = get_boolean_fields(model) if model else []
        field_info = get_field_info(model) if model else {}

        # Create workbook
        wb = Workbook()

        # Remove default sheet
        default_sheet = wb.active

        # Create Instructions sheet first
        instructions_ws = wb.create_sheet(title='Instructions', index=0)
        if model:
            self._create_instructions_sheet(instructions_ws, model, field_info, fk_fields)

        # Create reference sheets and track info for formulas
        ref_sheet_info = {}  # fk_field_name -> {range_name, sheet_name, max_row}
        if include_references:
            for fk_name, fk_field in fk_fields.items():
                info = self._create_reference_sheet(wb, fk_name, fk_field)
                if info:
                    ref_sheet_info[fk_name] = info

        # Create main data sheet
        data_ws = wb.create_sheet(title='Data', index=1)

        # Prepare data (without labels for now, we'll add custom headers)
        df = self.prepare_export_data(queryset, fields, apply_labels=False)

        # Style settings
        header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF')
        required_fill = PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid')

        # Track columns for data validation
        fk_name_columns = {}  # col_idx -> fk_name (for name columns with dropdowns)
        choice_columns = {}   # col_idx -> list of choices (for enum dropdowns)
        boolean_columns = []  # col_idx (for True/False dropdowns)

        # Write headers with formatting
        labels = self.get_export_field_labels()
        for col_idx, field_name in enumerate(df.columns, 1):
            label = labels.get(field_name, get_field_label(field_name))

            # Mark required fields
            is_required = field_info.get(field_name, {}).get('required', False)
            if is_required:
                label = f'{label}*'

            # An FK's own column carries the row's ID, as a value; its name is in the
            # column beside it. It used to be a lookup formula, which has no stored
            # value, so an import fell back to the name — and a name always finds the
            # CURRENT version, re-pointing every link to an older one.
            cell = data_ws.cell(row=1, column=col_idx, value=label)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')

            # Track FK columns
            base_field = field_name.split('__')[0]
            if base_field in fk_fields and field_name.endswith('__name'):
                fk_name_columns[col_idx] = base_field

            # Track choice/enum columns
            if field_name in choice_fields:
                choice_columns[col_idx] = choice_fields[field_name]

            # Track boolean columns
            if field_name in boolean_fields:
                boolean_columns.append(col_idx)

        # Write data rows
        for row_idx, row_data in enumerate(df.values, 2):
            for col_idx, value in enumerate(row_data, 1):
                field_name = df.columns[col_idx - 1]

                # Data, never a formula.
                cell = write_cell(data_ws, row_idx, col_idx, value)

                # Highlight required field cells that are empty
                is_required = field_info.get(field_name, {}).get('required', False)
                if is_required and (value is None or value == ''):
                    cell.fill = required_fill

        # Add data validation for FK name columns
        max_row = max(len(df) + 1, 100)  # At least 100 rows for new entries
        for col_idx, fk_name in fk_name_columns.items():
            if fk_name in ref_sheet_info:
                info = ref_sheet_info[fk_name]
                self._add_data_validation(data_ws, col_idx, info['range_name'], max_row,
                                          strict=not info.get('truncated'))

        # Add data validation for choice/enum columns
        for col_idx, choices in choice_columns.items():
            self._add_inline_data_validation(data_ws, col_idx, choices, max_row)

        # Add data validation for boolean columns
        for col_idx in boolean_columns:
            self._add_inline_data_validation(data_ws, col_idx, ['True', 'False'], max_row)

        # Auto-adjust column widths
        for col_idx, field_name in enumerate(df.columns, 1):
            max_length = len(labels.get(field_name, field_name)) + 2
            # Sample first 100 rows for width
            for row_idx in range(2, min(len(df) + 2, 102)):
                cell_value = data_ws.cell(row=row_idx, column=col_idx).value
                if cell_value:
                    max_length = max(max_length, min(len(str(cell_value)), 50))
            data_ws.column_dimensions[get_column_letter(col_idx)].width = max_length + 2

        # Freeze header row
        data_ws.freeze_panes = 'A2'

        # Remove the default empty sheet if it still exists
        if default_sheet.title == 'Sheet' and default_sheet in wb.worksheets:
            wb.remove(default_sheet)

        # Save to bytes
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()

    @extend_schema(
        parameters=[
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
            OpenApiParameter(
                name='include_references',
                description='Include FK reference sheets in Excel export (default: true)',
                required=False,
                type=bool,
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
    @action(detail=False, methods=['get'], url_path=r'export/(?P<export_format>csv|xlsx)')
    def export_data(self, request, export_format: str):
        """
        Export filtered data to CSV or Excel.

        URL path determines format:
        - /export/csv/ - CSV format (simple, just data)
        - /export/xlsx/ - Excel format (includes reference sheets, validation, formatting)

        Query params:
        - fields: Comma-separated field names
        - filename: Custom filename
        - include_references: Include FK reference sheets (xlsx only, default true)

        Respects all filters, search, and ordering applied to the list view.
        """
        # Get filtered queryset
        queryset = self.get_export_queryset()
        row_count = queryset.count()
        if row_count > MAX_EXPORT_ROWS:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'detail': (
                f"{row_count:,} rows is more than one export returns ({MAX_EXPORT_ROWS:,}). "
                "Filter the list first, then export.")})

        # Get fields to export
        fields = self.get_export_fields()

        # Generate filename
        filename = self.get_export_filename(export_format)

        # Create response
        if export_format == 'csv':
            # Simple CSV export
            df = self.prepare_export_data(queryset, fields).map(csv_safe)
            output = io.StringIO()
            df.to_csv(output, index=False)
            content = output.getvalue().encode('utf-8-sig')
            content_type = 'text/csv'
        else:
            # Full-featured Excel export
            include_refs = request.query_params.get('include_references', 'true').lower() != 'false'
            content = self._create_excel_export(queryset, fields, include_references=include_refs)
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

        response = HttpResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        # Bulk egress is the access event that matters most, and it was the one
        # not recorded: opening a single document was logged while pulling the
        # whole filtered table to Excel was not. Record the shape of what left
        # -- model, format, row count, and the filters in force, since
        # "exported 4,000 parts" and "exported 4,000 parts for one supplier"
        # are different events to anyone reviewing this later.
        from Tracker.services.core.access_log import record_access
        from Tracker.throttling import get_client_ip

        model = queryset.model
        # `row_count` was taken up front, where it also enforces MAX_EXPORT_ROWS.
        record_access(
            obj=model,
            user=request.user,
            action_type='bulk_export',
            object_repr=f'Export {export_format}: {model.__name__} ({row_count} rows)',
            remote_addr=get_client_ip(request),
            payload={
                'model': model.__name__,
                'export_format': export_format,
                'row_count': row_count,
                'filename': filename,
                'fields': fields,
                # Query params rather than the compiled SQL: this is the record
                # of what the user asked for, which is what a review reads.
                'filters': {
                    k: v for k, v in request.query_params.items()
                    if k not in ('fields', 'filename', 'include_references')
                },
            },
        )

        return response
