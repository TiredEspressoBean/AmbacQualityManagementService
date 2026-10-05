"""
CSV/Excel file parsing utilities for data import.

Provides encoding detection, column mapping, and standardized parsing
for CSV and Excel files with support for various date formats.
"""

import csv
import io
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from charset_normalizer import from_bytes
import pandas as pd


# Common date formats to try when parsing dates
DATE_FORMATS = [
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%d/%m/%Y",
    "%m-%d-%Y",
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%m/%d/%y",
    "%d/%m/%y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%d %B %Y",
    "%d %b %Y",
]


def detect_encoding(file_bytes: bytes) -> str:
    """
    Detect the encoding of a byte string using charset_normalizer.

    Args:
        file_bytes: Raw bytes from file

    Returns:
        Detected encoding string (defaults to 'utf-8' if detection fails)
    """
    result = from_bytes(file_bytes).best()
    if result is None:
        return "utf-8"

    encoding = result.encoding

    # Handle common mis-detections
    if encoding.lower() in ("ascii", "iso-8859-1", "windows-1252"):
        # Try UTF-8 first for these
        try:
            file_bytes.decode("utf-8")
            return "utf-8"
        except UnicodeDecodeError:
            pass

    return encoding


def decode_file_content(file_bytes: bytes, encoding: Optional[str] = None) -> str:
    """
    Decode file bytes to string with fallback encodings.

    Args:
        file_bytes: Raw bytes from file
        encoding: Optional explicit encoding to use

    Returns:
        Decoded string content

    Raises:
        UnicodeDecodeError: If all decode attempts fail
    """
    if encoding:
        encodings_to_try = [encoding, "utf-8", "windows-1252", "latin-1"]
    else:
        detected = detect_encoding(file_bytes)
        encodings_to_try = [detected, "utf-8", "windows-1252", "latin-1"]

    for enc in encodings_to_try:
        try:
            return file_bytes.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue

    # Last resort: decode with errors='replace'
    return file_bytes.decode("utf-8", errors="replace")


def normalize_header(header: str) -> str:
    """
    Normalize a column header for matching.

    - Lowercase
    - Strip whitespace
    - Replace various quote characters with standard apostrophe
    - Replace spaces and dashes with underscores

    Args:
        header: Original header string

    Returns:
        Normalized header string
    """
    if not header:
        return ""

    # A byte-order mark (Excel's "CSV UTF-8", and our own CSV template) and the `*` our
    # templates put on required columns are not part of the name. With them, the first
    # column of such a file and every required column matched nothing.
    normalized = str(header).replace('\ufeff', '').strip().rstrip('*').strip().lower()

    # Normalize quote characters
    for quote in ["'", "'", "`", "´"]:
        normalized = normalized.replace(quote, "'")

    # Replace spaces and dashes with underscores
    for char in [" ", "-"]:
        normalized = normalized.replace(char, "_")

    return normalized


# What the import dialog sends for a column the user chose not to import.
SKIP_COLUMN = '_skip_'


def create_field_mapping(headers: List[str], field_map: Dict[str, str]) -> Dict[str, str]:
    """
    Create a mapping from CSV headers to model field names.

    Args:
        headers: List of header names from CSV/Excel
        field_map: Mapping of normalized headers to field names
                  e.g., {"wo_number": "ERP_id", "item": "part_type_erp_id"}

    Returns:
        Dictionary mapping original headers to field names
    """
    result = {}

    for header in headers:
        normalized = normalize_header(header)

        # The import dialog keys its choices by the header as the file spells it
        # ("Item"); viewset mappings key by the normalized header ("item"). Try both —
        # matching only the normalized form ignored every manual remap.
        if header in field_map:
            result[header] = field_map[header]
        elif normalized in field_map:
            result[header] = field_map[normalized]
        else:
            # Keep original if no mapping found
            result[header] = normalized

    return result


def remap_row(row: Dict[str, Any], field_mapping: Dict[str, str]) -> Dict[str, Any]:
    """
    Remap a row's keys using the field mapping.

    Args:
        row: Original row dictionary
        field_mapping: Mapping from original to target field names

    Returns:
        New dictionary with remapped keys and trimmed string values
    """
    result = {}

    for key, value in row.items():
        new_key = field_mapping.get(key, normalize_header(key))
        if new_key in (None, '', SKIP_COLUMN):
            continue

        # An empty xlsx cell reaches here as pandas' NaN / NaT, not ''. Left alone it
        # became the text "nan" — "not a valid UUID", "a valid integer is required" —
        # so any xlsx with an optional column left blank failed.
        try:
            if pd.isna(value):
                value = None
        except (TypeError, ValueError):
            pass  # a list-like value; not a blank cell

        # Trim string values
        if isinstance(value, str):
            value = value.strip()
            # Convert empty strings to None
            if not value:
                value = None

        result[new_key] = value

    return result


def parse_csv_file(
    file,
    field_map: Optional[Dict[str, str]] = None,
    encoding: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parse a CSV file into a list of dictionaries.

    Args:
        file: File-like object or Django UploadedFile
        field_map: Optional mapping of normalized headers to field names
        encoding: Optional explicit encoding

    Returns:
        Tuple of (list of row dicts, list of headers)
    """
    # Read file content
    if hasattr(file, 'read'):
        raw = file.read()
        if hasattr(file, 'seek'):
            file.seek(0)  # Reset for potential re-read
    else:
        raw = file

    # Ensure bytes
    if isinstance(raw, str):
        raw = raw.encode('utf-8')

    # Decode content
    decoded = decode_file_content(raw, encoding)

    # Parse CSV
    reader = csv.DictReader(io.StringIO(decoded))
    headers = reader.fieldnames or []

    # Create field mapping
    field_mapping = create_field_mapping(headers, field_map or {})

    # Process rows
    rows = [remap_row(row, field_mapping) for row in reader]

    return rows, list(field_mapping.values())


def parse_excel_file(
    file,
    field_map: Optional[Dict[str, str]] = None,
    sheet_name: Union[str, int] = 0,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parse an Excel file into a list of dictionaries.

    Args:
        file: File-like object or path
        field_map: Optional mapping of normalized headers to field names
        sheet_name: Sheet name or index to read (default: first sheet)

    Returns:
        Tuple of (list of row dicts, list of headers)
    """
    # Our exports and templates put the rows on a sheet named "Data", and an export's
    # first sheet is its guide — reading sheet 0 imported the guide. Prefer "Data".
    if sheet_name == 0:
        try:
            names = pd.ExcelFile(file).sheet_names
            if 'Data' in names:
                sheet_name = 'Data'
        except Exception:
            pass
        if hasattr(file, 'seek'):
            file.seek(0)

    # Read Excel file — every cell as text, as a CSV arrives. pandas otherwise guesses
    # a type per column: a text "7" or "0045" became the number 7 / 45 (7.0 where the
    # column had blanks), so a part number or a characteristic lost its value. The
    # importer converts by FIELD type instead, which is what it does for CSV.
    df = pd.read_excel(file, sheet_name=sheet_name, dtype=str)

    # Get headers
    headers = list(df.columns)

    # Create field mapping
    field_mapping = create_field_mapping(headers, field_map or {})

    # Convert DataFrame to list of dicts
    rows = []
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        rows.append(remap_row(row_dict, field_mapping))

    return rows, list(field_mapping.values())


# Limits on any uploaded spreadsheet, enforced here so every caller (import, preview,
# user reconcile) gets them. An .xlsx is a zip, so a small upload can decompress to
# gigabytes; and every row is held in memory, and for large imports sent to Celery as
# one message. Split larger loads into several files.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_UPLOAD_ROWS = 10_000


def parse_file(
    file,
    filename: str,
    field_map: Optional[Dict[str, str]] = None,
    encoding: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parse a file (CSV or Excel) based on extension.

    Args:
        file: File-like object
        filename: Original filename (used to detect format)
        field_map: Optional mapping of normalized headers to field names
        encoding: Optional encoding for CSV files

    Returns:
        Tuple of (list of row dicts, list of headers)

    Raises:
        ValueError: If file type is not supported
    """
    size = getattr(file, 'size', None)
    if size and size > MAX_UPLOAD_BYTES:
        raise ValueError(
            f"The file is {size // (1024 * 1024)} MB; the limit is "
            f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MB. Split it into smaller files.")
    filename_lower = filename.lower()
    if filename_lower.endswith('.csv'):
        rows, headers = parse_csv_file(file, field_map, encoding)
    elif filename_lower.endswith('.xlsx'):
        rows, headers = parse_excel_file(file, field_map)
    elif filename_lower.endswith('.xls'):
        # The old binary format needs xlrd, which isn't installed, so .xls uploads only
        # ever failed as "Error reading file". Say what to do instead.
        raise ValueError("Old-format .xls files aren't supported. Save it as .xlsx or .csv "
                         "and upload that.")
    else:
        raise ValueError(f"Unsupported file type: {filename}. Use .csv or .xlsx")
    if len(rows) > MAX_UPLOAD_ROWS:
        raise ValueError(
            f"{len(rows)} rows is more than one upload takes ({MAX_UPLOAD_ROWS}). "
            "Split the file into smaller ones.")
    return rows, headers


def parse_date(value: Any) -> Optional[datetime]:
    """
    Parse a date value from various formats.

    Args:
        value: Date string or datetime object

    Returns:
        datetime object or None if parsing fails
    """
    if value is None or value == "":
        return None

    # Already a datetime
    if isinstance(value, datetime):
        return value

    # Handle pandas Timestamp
    if hasattr(value, 'to_pydatetime'):
        return value.to_pydatetime()

    # Handle date (not datetime)
    if hasattr(value, 'year') and hasattr(value, 'month') and hasattr(value, 'day'):
        return datetime(value.year, value.month, value.day)

    # String parsing
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None

        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue

        # A date with a time — what a CSV export writes for a date-time
        # (`2026-12-24 08:00:00`), and what people type (`12/24/2026 8:00 AM`). Only
        # dates were read, so every date-time in a CSV was "couldn't read".
        from django.utils.dateparse import parse_datetime as _iso
        try:
            parsed = _iso(value.replace('/', '-') if value[:4].isdigit() else value)
        except ValueError:
            parsed = None
        if parsed:
            return parsed
        for date_fmt in DATE_FORMATS:
            for time_fmt in DATETIME_TIME_FORMATS:
                try:
                    return datetime.strptime(value, f"{date_fmt} {time_fmt}")
                except ValueError:
                    continue

    return None


# Times accepted after a date, and on their own for a time-of-day field.
DATETIME_TIME_FORMATS = ["%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M:%S %p", "%I:%M%p"]


def parse_time(value: Any):
    """A time of day (`09:00`, `9:00 AM`, `09:00:00`, an Excel time cell), or None."""
    from datetime import time as _time
    if value is None or value == "":
        return None
    if isinstance(value, _time):
        return value
    if isinstance(value, datetime):
        return value.time()
    if hasattr(value, 'to_pydatetime'):
        return value.to_pydatetime().time()
    if isinstance(value, str):
        value = value.strip()
        for fmt in DATETIME_TIME_FORMATS:
            try:
                return datetime.strptime(value.upper(), fmt).time()
            except ValueError:
                continue
    return None


def ambiguous_day_month(value: Any) -> bool:
    """Whether a slash- or dash-separated date could be read either way round.

    `03/04/2026` is 4 March in the US and 3 April almost everywhere else; parse_date
    reads month first. True when both of the first two numbers are 12 or under and they
    differ — the only case the order changes the answer.
    """
    import re
    if not isinstance(value, str):
        return False
    m = re.match(r'^\s*(\d{1,2})[/-](\d{1,2})[/-]\d{2,4}\s*$', value)
    if not m:
        return False
    a, b = int(m.group(1)), int(m.group(2))
    return a <= 12 and b <= 12 and a != b


def parse_boolean(value: Any) -> Optional[bool]:
    """
    Parse a boolean value from various representations.

    Args:
        value: Boolean-like value (string, int, bool)

    Returns:
        Boolean or None
    """
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    if isinstance(value, str):
        value_lower = value.strip().lower()
        if value_lower in ('true', 'yes', 'y', '1', 'on'):
            return True
        if value_lower in ('false', 'no', 'n', '0', 'off', ''):
            return False

    return None


def parse_integer(value: Any) -> Optional[int]:
    """
    Parse an integer value.

    Args:
        value: Numeric value or string

    Returns:
        Integer or None
    """
    if value is None or value == "":
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return int(value)

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        try:
            # Handle floats represented as strings
            return int(float(value))
        except ValueError:
            return None

    return None


def parse_decimal(value: Any) -> Optional[float]:
    """
    Parse a decimal/float value.

    Args:
        value: Numeric value or string

    Returns:
        Float or None
    """
    if value is None or value == "":
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    return None


class ImportResult:
    """
    Container for import operation results.

    Tracks created, updated, and error counts along with per-row details.
    """

    def __init__(self):
        self.total = 0
        self.created = 0
        self.updated = 0
        self.unchanged = 0
        self.errors = 0
        self.results: List[Dict[str, Any]] = []

    def add_created(self, row_num: int, obj_id: Any, warnings: Optional[List[str]] = None):
        """Record a successful creation."""
        self.total += 1
        self.created += 1
        result = {"row": row_num, "status": "created", "id": str(obj_id)}
        if warnings:
            result["warnings"] = warnings
        self.results.append(result)

    def add_updated(self, row_num: int, obj_id: Any, warnings: Optional[List[str]] = None):
        """Record a successful update."""
        self.total += 1
        self.updated += 1
        result = {"row": row_num, "status": "updated", "id": str(obj_id)}
        if warnings:
            result["warnings"] = warnings
        self.results.append(result)

    def add_unchanged(self, row_num: int, obj_id: Any, warnings: Optional[List[str]] = None):
        """Record a row that matched an existing record and changed nothing."""
        self.total += 1
        self.unchanged += 1
        result = {"row": row_num, "status": "unchanged", "id": str(obj_id)}
        if warnings:
            result["warnings"] = warnings
        self.results.append(result)

    def add_error(self, row_num: int, errors: Union[str, Dict, List]):
        """Record an error."""
        self.total += 1
        self.errors += 1
        self.results.append({"row": row_num, "status": "error", "errors": errors})

    def to_response(self) -> Dict[str, Any]:
        """Convert to API response format."""
        return {
            "summary": {
                "total": self.total,
                "created": self.created,
                "updated": self.updated,
                "unchanged": self.unchanged,
                "errors": self.errors,
            },
            "results": self.results,
        }
