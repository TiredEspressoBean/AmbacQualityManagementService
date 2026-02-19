"""
Tracker services module.

Contains business logic services for the Tracker app.
"""

from .permission_service import PermissionService
from .csv_utils import (
    detect_encoding,
    decode_file_content,
    normalize_header,
    parse_file,
    parse_csv_file,
    parse_excel_file,
    parse_date,
    parse_boolean,
    parse_integer,
    parse_decimal,
    ImportResult,
)
from .template_generator import (
    TemplateField,
    TemplateGenerator,
    template_from_model,
    introspect_model,
    get_part_types_template,
    get_parts_template,
    get_orders_template,
    get_work_orders_template,
    get_equipment_template,
)

__all__ = [
    # Permission Service
    'PermissionService',

    # CSV Utils
    'detect_encoding',
    'decode_file_content',
    'normalize_header',
    'parse_file',
    'parse_csv_file',
    'parse_excel_file',
    'parse_date',
    'parse_boolean',
    'parse_integer',
    'parse_decimal',
    'ImportResult',

    # Template Generator
    'TemplateField',
    'TemplateGenerator',
    'template_from_model',
    'introspect_model',
    'get_part_types_template',
    'get_parts_template',
    'get_orders_template',
    'get_work_orders_template',
    'get_equipment_template',
]
