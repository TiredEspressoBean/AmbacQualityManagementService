"""
CSV Import Serializers for bulk data import.

Provides base class and model-specific serializers for importing
data from CSV/Excel files with foreign key resolution and validation.

Supports automatic model introspection for zero-config usage.
"""

from typing import Any, Dict, List, Optional, Tuple, Type
from uuid import UUID

from django.db import models, transaction
from django.db.models import Q
from rest_framework import serializers

from Tracker.services.csv_utils import (
    ImportResult,
    parse_date,
    parse_boolean,
    parse_integer,
    parse_decimal,
)

# Fields to skip during auto-introspection
SKIP_FIELDS = {
    'id', 'tenant', 'created_at', 'updated_at', 'archived',
    'created_by', 'modified_by', 'version', 'previous_version',
    'is_current_version', 'classification',
}


class ImportMode:
    """Import mode constants."""
    CREATE = 'create'
    UPDATE = 'update'
    UPSERT = 'upsert'

    CHOICES = [
        (CREATE, 'Create only (error if exists)'),
        (UPDATE, 'Update only (error if not found)'),
        (UPSERT, 'Create or update (default)'),
    ]


class BaseCSVImportSerializer(serializers.Serializer):
    """
    Base serializer for CSV imports with FK resolution and upsert support.

    Subclasses should define:
    - Meta.model: The Django model to import into
    - Meta.lookup_fields: Fields to use for finding existing records (in order)
    - Meta.field_mapping: Dict mapping CSV column names to model fields
    - Meta.fk_fields: Dict mapping field name to (Model, lookup_fields) for FK resolution

    Example:
        class PartsCSVImportSerializer(BaseCSVImportSerializer):
            class Meta:
                model = Parts
                lookup_fields = ['id', 'ERP_id']
                field_mapping = {
                    'part_id': 'ERP_id',
                    'type': 'part_type',
                }
                fk_fields = {
                    'part_type': (PartTypes, ['name', 'ERP_id']),
                    'order': (Orders, ['name', 'order_number', 'id']),
                }
    """

    class Meta:
        model = None
        lookup_fields = ['id']
        field_mapping = {}
        fk_fields = {}
        required_fields = []

    def __init__(self, *args, tenant=None, user=None, mode=ImportMode.UPSERT, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant
        self.user = user
        self.mode = mode
        self.warnings = []

    def resolve_fk(
        self,
        field_name: str,
        value: Any,
        model: Type[models.Model],
        lookup_fields: List[str],
    ) -> Optional[models.Model]:
        """
        Resolve a foreign key value to a model instance.

        Tries each lookup field in order until a match is found.
        Accepts name, ERP_id, id (UUID), or the actual instance.

        Args:
            field_name: Name of the FK field (for error messages)
            value: Value from CSV (name, id, ERP_id, etc.)
            model: Related model class
            lookup_fields: Fields to try for lookup (in order)

        Returns:
            Model instance or None if not found
        """
        if value is None or value == '':
            return None

        # Already a model instance
        if isinstance(value, model):
            return value

        # Build queryset with tenant filter if applicable
        qs = model.objects.all()
        if self.tenant and hasattr(model, 'tenant'):
            qs = qs.filter(tenant=self.tenant)

        # Try each lookup field
        for lookup_field in lookup_fields:
            try:
                # Handle UUID id field
                if lookup_field == 'id':
                    try:
                        uuid_val = UUID(str(value))
                        obj = qs.filter(id=uuid_val).first()
                        if obj:
                            return obj
                    except (ValueError, AttributeError):
                        continue

                # Handle integer id
                elif lookup_field == 'pk' or (lookup_field == 'id' and not hasattr(model._meta.pk, 'max_length')):
                    try:
                        int_val = int(value)
                        obj = qs.filter(pk=int_val).first()
                        if obj:
                            return obj
                    except (ValueError, TypeError):
                        continue

                # Try case-insensitive match for string fields
                else:
                    obj = qs.filter(**{f"{lookup_field}__iexact": str(value)}).first()
                    if obj:
                        return obj

            except Exception:
                continue

        return None

    def validate_required_fields(self, data: Dict[str, Any]) -> List[str]:
        """
        Validate that required fields are present.

        Returns list of missing field names.
        """
        meta = getattr(self, 'Meta', None)
        required = getattr(meta, 'required_fields', [])

        missing = []
        for field in required:
            value = data.get(field)
            if value is None or value == '':
                missing.append(field)

        return missing

    def find_existing(self, data: Dict[str, Any]) -> Optional[models.Model]:
        """
        Find an existing record that matches the import data.

        Uses lookup_fields in order: id, ERP_id, then model-specific fields.
        """
        meta = getattr(self, 'Meta', None)
        model = getattr(meta, 'model', None)
        lookup_fields = getattr(meta, 'lookup_fields', ['id'])

        if not model:
            return None

        qs = model.objects.all()
        if self.tenant and hasattr(model, 'tenant'):
            qs = qs.filter(tenant=self.tenant)

        for field in lookup_fields:
            value = data.get(field)
            if value is None or value == '':
                continue

            try:
                # Handle UUID
                if field == 'id':
                    try:
                        uuid_val = UUID(str(value))
                        obj = qs.filter(id=uuid_val).first()
                        if obj:
                            return obj
                    except (ValueError, AttributeError):
                        continue

                # Handle other fields
                obj = qs.filter(**{f"{field}__iexact": str(value)}).first()
                if obj:
                    return obj

            except Exception:
                continue

        return None

    def transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw CSV data for model creation/update.

        Handles:
        - FK resolution
        - Date parsing
        - Boolean conversion
        - Field name mapping

        Subclasses can override for model-specific transformations.
        """
        meta = getattr(self, 'Meta', None)
        fk_fields = getattr(meta, 'fk_fields', {})
        model = getattr(meta, 'model', None)

        result = {}

        for field_name, value in data.items():
            # Skip empty values (will use model defaults)
            if value is None or value == '':
                continue

            # FK resolution
            if field_name in fk_fields:
                fk_model, fk_lookups = fk_fields[field_name]
                resolved = self.resolve_fk(field_name, value, fk_model, fk_lookups)
                if resolved:
                    result[field_name] = resolved
                elif value:  # Had a value but couldn't resolve
                    self.warnings.append(f"Could not resolve {field_name}='{value}'")
                continue

            # Get model field for type conversion
            if model:
                try:
                    model_field = model._meta.get_field(field_name)

                    # Date fields
                    if isinstance(model_field, (models.DateField, models.DateTimeField)):
                        parsed = parse_date(value)
                        if parsed:
                            result[field_name] = parsed
                        continue

                    # Boolean fields
                    if isinstance(model_field, models.BooleanField):
                        parsed = parse_boolean(value)
                        if parsed is not None:
                            result[field_name] = parsed
                        continue

                    # Integer fields
                    if isinstance(model_field, models.IntegerField):
                        parsed = parse_integer(value)
                        if parsed is not None:
                            result[field_name] = parsed
                        continue

                    # Decimal/Float fields
                    if isinstance(model_field, (models.DecimalField, models.FloatField)):
                        parsed = parse_decimal(value)
                        if parsed is not None:
                            result[field_name] = parsed
                        continue

                except Exception:
                    pass

            # Default: use value as-is
            result[field_name] = value

        return result

    def create_instance(self, data: Dict[str, Any]) -> models.Model:
        """Create a new model instance."""
        meta = getattr(self, 'Meta', None)
        model = getattr(meta, 'model', None)

        if not model:
            raise ValueError("Meta.model not defined")

        # Add tenant if applicable
        if self.tenant and hasattr(model, 'tenant'):
            data['tenant'] = self.tenant

        # Add created_by if applicable
        if self.user and hasattr(model, 'created_by'):
            data['created_by'] = self.user

        return model.objects.create(**data)

    def update_instance(self, instance: models.Model, data: Dict[str, Any]) -> models.Model:
        """Update an existing model instance."""
        for field_name, value in data.items():
            setattr(instance, field_name, value)

        # Update modified_by if applicable
        if self.user and hasattr(instance, 'modified_by'):
            instance.modified_by = self.user

        instance.save()
        return instance

    def import_row(self, row_data: Dict[str, Any]) -> Tuple[Optional[models.Model], bool, List[str]]:
        """
        Import a single row of data.

        Returns:
            Tuple of (instance, created, warnings)
            - instance: Created or updated model instance (None on error)
            - created: True if created, False if updated
            - warnings: List of warning messages
        """
        self.warnings = []

        # Validate required fields
        missing = self.validate_required_fields(row_data)
        if missing:
            raise serializers.ValidationError({
                field: "This field is required" for field in missing
            })

        # Transform data (FK resolution, type conversion)
        transformed = self.transform_data(row_data)

        # Find existing record
        existing = self.find_existing(row_data)

        # Handle based on mode
        if self.mode == ImportMode.CREATE:
            if existing:
                raise serializers.ValidationError(
                    f"Record already exists (matched by lookup fields)"
                )
            instance = self.create_instance(transformed)
            return instance, True, self.warnings

        elif self.mode == ImportMode.UPDATE:
            if not existing:
                raise serializers.ValidationError(
                    f"Record not found (no match for lookup fields)"
                )
            instance = self.update_instance(existing, transformed)
            return instance, False, self.warnings

        else:  # UPSERT
            if existing:
                instance = self.update_instance(existing, transformed)
                return instance, False, self.warnings
            else:
                instance = self.create_instance(transformed)
                return instance, True, self.warnings


# ===== Model-specific CSV Import Serializers =====


class PartTypesCSVImportSerializer(BaseCSVImportSerializer):
    """CSV import serializer for PartTypes."""

    class Meta:
        from Tracker.models import PartTypes
        model = PartTypes
        lookup_fields = ['id', 'ERP_id', 'name']
        field_mapping = {}
        fk_fields = {}
        required_fields = ['name']


class PartsCSVImportSerializer(BaseCSVImportSerializer):
    """CSV import serializer for Parts."""

    class Meta:
        from Tracker.models import Parts, PartTypes, Orders, WorkOrder, Steps
        model = Parts
        lookup_fields = ['id', 'ERP_id']
        field_mapping = {
            'part_id': 'ERP_id',
            'type': 'part_type',
            'status': 'part_status',
        }
        fk_fields = {
            'part_type': (PartTypes, ['name', 'ERP_id', 'id']),
            'order': (Orders, ['name', 'order_number', 'id']),
            'work_order': (WorkOrder, ['ERP_id', 'id']),
            'step': (Steps, ['name', 'id']),
        }
        required_fields = ['part_type']

    def transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Additional transformations for Parts."""
        result = super().transform_data(data)

        # Handle part_status choices validation
        from Tracker.models import PartsStatus
        if 'part_status' in result:
            status_value = str(result['part_status']).upper()
            valid_statuses = [s.value for s in PartsStatus]
            if status_value in valid_statuses:
                result['part_status'] = status_value
            else:
                self.warnings.append(f"Invalid part_status '{result['part_status']}', using PENDING")
                result['part_status'] = PartsStatus.PENDING

        return result


class OrdersCSVImportSerializer(BaseCSVImportSerializer):
    """CSV import serializer for Orders."""

    class Meta:
        from Tracker.models import Orders, Companies, User
        model = Orders
        lookup_fields = ['id', 'order_number', 'name']
        field_mapping = {
            'status': 'order_status',
            'customer_name': 'customer',
        }
        fk_fields = {
            'company': (Companies, ['name', 'id']),
            'customer': (User, ['email', 'username', 'id']),
        }
        required_fields = ['name']

    def transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Additional transformations for Orders."""
        result = super().transform_data(data)

        # Handle order_status choices validation
        from Tracker.models import OrdersStatus
        if 'order_status' in result:
            status_value = str(result['order_status']).upper()
            valid_statuses = [s.value for s in OrdersStatus]
            if status_value in valid_statuses:
                result['order_status'] = status_value
            else:
                self.warnings.append(f"Invalid order_status '{result['order_status']}', using PENDING")
                result['order_status'] = OrdersStatus.PENDING

        return result


class WorkOrderCSVImportSerializer(BaseCSVImportSerializer):
    """CSV import serializer for WorkOrders."""

    class Meta:
        from Tracker.models import WorkOrder, Orders, PartTypes, Processes
        model = WorkOrder
        lookup_fields = ['id', 'ERP_id']
        field_mapping = {
            'wo_number': 'ERP_id',
            'item': 'part_type_erp_id',  # Special handling
            'due_date': 'expected_completion',
        }
        fk_fields = {
            'related_order': (Orders, ['name', 'order_number', 'id']),
            'process': (Processes, ['name', 'id']),
        }
        required_fields = ['ERP_id', 'quantity']

    def transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Additional transformations for WorkOrders."""
        result = super().transform_data(data)

        # Handle part_type_erp_id -> find process for part type
        part_type_ref = data.get('part_type_erp_id') or data.get('part_type')
        if part_type_ref and 'process' not in result:
            from Tracker.models import PartTypes, Processes, ProcessStatus
            pt = self.resolve_fk('part_type', part_type_ref, PartTypes, ['name', 'ERP_id', 'id'])
            if pt:
                # Find approved process for this part type
                process = Processes.objects.filter(
                    part_type=pt,
                    status__in=[ProcessStatus.APPROVED, ProcessStatus.DEPRECATED],
                    is_current_version=True
                ).first()
                if process:
                    result['process'] = process
                else:
                    self.warnings.append(f"No approved process found for part type '{pt.name}'")

        # Handle workorder_status choices validation
        from Tracker.models import WorkOrderStatus
        if 'workorder_status' in result:
            status_value = str(result['workorder_status']).upper()
            valid_statuses = [s.value for s in WorkOrderStatus]
            if status_value in valid_statuses:
                result['workorder_status'] = status_value
            else:
                self.warnings.append(f"Invalid workorder_status, using PENDING")
                result['workorder_status'] = WorkOrderStatus.PENDING

        return result

    def create_instance(self, data: Dict[str, Any]) -> 'WorkOrder':
        """Create work order with parts if quantity specified."""
        from Tracker.models import WorkOrder

        quantity = data.pop('quantity', 1)
        instance = super().create_instance(data)

        # Create parts if process is set
        if instance.process and quantity > 0:
            instance.create_parts(quantity, user=self.user)

        return instance


class EquipmentCSVImportSerializer(BaseCSVImportSerializer):
    """CSV import serializer for Equipment."""

    class Meta:
        from Tracker.models import Equipments, EquipmentType
        model = Equipments
        lookup_fields = ['id', 'serial_number', 'name']
        field_mapping = {
            'type': 'equipment_type',
        }
        fk_fields = {
            'equipment_type': (EquipmentType, ['name', 'id']),
        }
        required_fields = ['name', 'equipment_type']


class QualityReportsCSVImportSerializer(BaseCSVImportSerializer):
    """CSV import serializer for QualityReports."""

    class Meta:
        from Tracker.models import QualityReports, Parts, Steps, User
        model = QualityReports
        lookup_fields = ['id']
        field_mapping = {
            'inspector': 'recorded_by',
        }
        fk_fields = {
            'part': (Parts, ['ERP_id', 'id']),
            'step': (Steps, ['name', 'id']),
            'recorded_by': (User, ['email', 'username', 'id']),
        }
        required_fields = ['part']


# ===== Serializer Registry =====

CSV_IMPORT_SERIALIZERS = {
    'part-types': PartTypesCSVImportSerializer,
    'parttypes': PartTypesCSVImportSerializer,
    'parts': PartsCSVImportSerializer,
    'orders': OrdersCSVImportSerializer,
    'work-orders': WorkOrderCSVImportSerializer,
    'workorders': WorkOrderCSVImportSerializer,
    'equipment': EquipmentCSVImportSerializer,
    'equipments': EquipmentCSVImportSerializer,
    'quality-reports': QualityReportsCSVImportSerializer,
    'qualityreports': QualityReportsCSVImportSerializer,
}


def get_csv_import_serializer(model_name: str) -> Optional[Type[BaseCSVImportSerializer]]:
    """
    Get the CSV import serializer class for a model name.

    Args:
        model_name: Model name or URL path segment (e.g., 'parts', 'work-orders')

    Returns:
        Serializer class or None if not found
    """
    return CSV_IMPORT_SERIALIZERS.get(model_name.lower())


# ===== Automatic Serializer Generation =====

def introspect_model_for_import(model: Type[models.Model]) -> Dict[str, Any]:
    """
    Introspect a Django model to auto-generate import serializer configuration.

    Returns:
        Dict with lookup_fields, fk_fields, required_fields
    """
    lookup_fields = ['id']
    fk_fields = {}
    required_fields = []

    # Check for common lookup fields
    for field_name in ['ERP_id', 'name', 'serial_number', 'order_number', 'code']:
        if hasattr(model, field_name):
            lookup_fields.append(field_name)

    for model_field in model._meta.get_fields():
        # Skip reverse relations
        if model_field.auto_created and not model_field.concrete:
            continue

        # Skip system fields
        if model_field.name in SKIP_FIELDS:
            continue

        # Handle ForeignKey - auto-configure FK lookups
        if isinstance(model_field, models.ForeignKey):
            related_model = model_field.related_model

            # Determine best lookup fields for the related model
            fk_lookups = ['id']
            for fk_field in ['name', 'ERP_id', 'order_number', 'email', 'username', 'serial_number']:
                if hasattr(related_model, fk_field):
                    fk_lookups.insert(0, fk_field)

            fk_fields[model_field.name] = (related_model, fk_lookups)

            # FK required if not null/blank
            if not model_field.null and not model_field.blank:
                required_fields.append(model_field.name)
            continue

        # Skip ManyToMany
        if isinstance(model_field, models.ManyToManyField):
            continue

        # Track required fields (not null, not blank, no default)
        if hasattr(model_field, 'blank') and hasattr(model_field, 'null'):
            has_default = model_field.has_default()
            if not model_field.blank and not model_field.null and not has_default:
                required_fields.append(model_field.name)

    return {
        'lookup_fields': lookup_fields,
        'fk_fields': fk_fields,
        'required_fields': required_fields,
    }


def create_import_serializer_for_model(
    model: Type[models.Model],
    extra_fk_fields: Optional[Dict] = None,
    extra_required_fields: Optional[List[str]] = None,
    extra_lookup_fields: Optional[List[str]] = None,
) -> Type[BaseCSVImportSerializer]:
    """
    Dynamically create a CSV import serializer for any Django model.

    This function introspects the model and creates a serializer class
    with appropriate FK resolution, lookup fields, and required field validation.

    Args:
        model: Django model class
        extra_fk_fields: Additional FK field configurations to merge
        extra_required_fields: Additional required fields
        extra_lookup_fields: Additional lookup fields

    Returns:
        A new serializer class for the model

    Example:
        # Auto-create serializer for any model
        MyModelSerializer = create_import_serializer_for_model(MyModel)

        # Use in viewset
        serializer = MyModelSerializer(tenant=tenant, user=user)
        instance, created, warnings = serializer.import_row(row_data)
    """
    # Introspect model
    config = introspect_model_for_import(model)

    # Merge extra config
    if extra_fk_fields:
        config['fk_fields'].update(extra_fk_fields)
    if extra_required_fields:
        config['required_fields'].extend(extra_required_fields)
    if extra_lookup_fields:
        config['lookup_fields'].extend(extra_lookup_fields)

    # Create Meta class dynamically
    meta_attrs = {
        'model': model,
        'lookup_fields': config['lookup_fields'],
        'fk_fields': config['fk_fields'],
        'required_fields': config['required_fields'],
        'field_mapping': {},
    }
    Meta = type('Meta', (), meta_attrs)

    # Create serializer class dynamically
    serializer_class = type(
        f'{model.__name__}CSVImportSerializer',
        (BaseCSVImportSerializer,),
        {'Meta': Meta}
    )

    return serializer_class


def get_or_create_import_serializer(
    model: Type[models.Model]
) -> Type[BaseCSVImportSerializer]:
    """
    Get a registered import serializer or create one dynamically.

    First checks the registry for a custom serializer, then falls back
    to auto-generating one via model introspection.

    Args:
        model: Django model class

    Returns:
        Serializer class for the model
    """
    # Try registry first (for custom serializers)
    model_name = model.__name__.lower()
    registered = CSV_IMPORT_SERIALIZERS.get(model_name)
    if registered:
        return registered

    # Try with hyphens
    hyphenated = ''.join([
        f'-{c.lower()}' if c.isupper() else c
        for c in model.__name__
    ]).lstrip('-')
    registered = CSV_IMPORT_SERIALIZERS.get(hyphenated)
    if registered:
        return registered

    # Auto-create
    return create_import_serializer_for_model(model)
