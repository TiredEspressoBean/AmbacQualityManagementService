"""Writing database values into files someone will open in a spreadsheet.

A value that starts like a formula is run as one when the file is opened. Our exports
and import templates carry text anyone can type — a part note, a company name — so
without care, `=HYPERLINK("http://…","Open")` in a field becomes a live link, and worse
payloads have been used against spreadsheet users for years (CSV / formula injection).

Two formats, two rules:
- **xlsx** (openpyxl): only a leading `=` makes a formula, and openpyxl will store it as
  one. Forcing such cells to text is enough, and shows the value exactly as typed.
- **csv**: Excel evaluates a cell starting `=`, `+`, `-`, `@`, tab or carriage return.
  The standard guard is a leading apostrophe, which Excel reads as "this is text".
  A plain number (`-5`, `+3.2`) is left alone — it is a number, not a formula.
"""
from __future__ import annotations

import re
from uuid import UUID

_FORMULA_START = ('=', '+', '-', '@', '\t', '\r')
_PLAIN_NUMBER = re.compile(r'^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$')


def csv_safe(value):
    """`value` for a CSV cell, neutralised if it would start a formula."""
    if isinstance(value, str) and value.startswith(_FORMULA_START) \
            and not _PLAIN_NUMBER.match(value):
        return "'" + value
    return value


def write_cell(ws, row: int, column: int, value):
    """`ws.cell(row, column, value)` that never turns DATA into a formula.

    Only for values that came from the database or a user. A cell the export builds as
    a formula on purpose (a lookup it computes) must be written with `ws.cell` directly.
    """
    if isinstance(value, UUID):
        value = str(value)  # openpyxl refuses a UUID outright
    cell = ws.cell(row=row, column=column, value=value)
    if isinstance(value, str) and value.startswith('='):
        cell.data_type = 's'
    return cell
