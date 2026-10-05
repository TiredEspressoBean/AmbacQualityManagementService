"""Importing a bill of materials from a spreadsheet.

One sheet; each row is a LINE, and the parent BOM is named on every row by its part type,
revision and BOM type. The file is the COMPLETE line list for each BOM it names
(replace, not merge), and an import only ever produces a DRAFT — releasing a BOM stays a
human approval. So, per BOM the file names:

- no BOM yet for that part type / type          → a new DRAFT with the file's lines;
- the current BOM is a DRAFT                    → its lines are replaced;
- the current BOM is RELEASED / OBSOLETE        → a new DRAFT revision (the same versioning
                                                  the Revise action uses), lines replaced;
                                                  unless the file's lines are exactly the
                                                  current lines, which changes nothing.

A BOM's lines land together or not at all: one bad line fails that BOM (every one of its
rows reports why), and the other BOMs in the file still import. Each line is validated by
the API's own BOMLineSerializer, so a file can't make a line the edit form wouldn't.
"""
from __future__ import annotations

from collections import OrderedDict
from decimal import Decimal, InvalidOperation

from django.db import transaction
from rest_framework import serializers

from Tracker.services.csv_utils import ImportResult, parse_boolean

# The columns, as an export writes them and an import reads them. Aliases on the right
# are what a person (or an export's related-name column) might call the same thing.
COLUMNS = OrderedDict([
    ('part_type', ('parent', 'parent_part_type', 'bom__part_type', 'bom_part_type')),
    ('revision', ('bom__revision', 'bom_revision', 'rev')),
    ('bom_type', ('bom__bom_type',)),
    ('line_number', ('line', 'line_no')),
    ('component_type', ('component', 'component_part_type')),
    ('material', ()),
    ('quantity', ('qty',)),
    ('unit_of_measure', ('uom', 'unit')),
    ('source', ('make_or_buy',)),
    ('consumed_at_step', ('step', 'consumed_at')),
    ('find_number', ()),
    ('reference_designator', ('ref_des',)),
    ('is_optional', ('optional',)),
    ('allow_harvested', ()),
    ('notes', ()),
])

_SUFFIXES = ('__name', '_name', '__ref', '_ref', '__part_number')


def _canonical(row: dict) -> dict:
    """Map a parsed row's columns to COLUMNS, ignoring case and export suffixes."""
    alias = {}
    for name, others in COLUMNS.items():
        for a in (name, *others):
            alias[a.lower()] = name
    out = {}
    for key, value in row.items():
        k = str(key).lower()
        for sfx in _SUFFIXES:
            if k.endswith(sfx) and k[:-len(sfx)] in alias:
                k = k[:-len(sfx)]
                break
        name = alias.get(k)
        if name is not None and (out.get(name) in (None, '')):
            out[name] = value
    return out


def _blank(v) -> bool:
    return v is None or str(v).strip() == ''


def _unique(qs, field, value, what):
    matches = list(qs.filter(**{f"{field}__iexact": str(value).strip()})[:2])
    if len(matches) > 1:
        raise serializers.ValidationError({what: f"'{value}' matches more than one — use its ID."})
    return matches[0] if matches else None


def _part_type(value, what):
    from uuid import UUID
    from Tracker.models import PartTypes
    qs = PartTypes.objects.filter(archived=False)  # tenant-safe: .objects auto-scopes to the request tenant
    current = qs.filter(is_current_version=True)
    try:
        found = qs.filter(id=UUID(str(value))).first()
        if found:
            return found
    except ValueError:
        pass
    for field in ('ERP_id', 'name'):
        found = _unique(current, field, value, what)
        if found:
            return found
    raise serializers.ValidationError({what: f"No part type matches '{value}'."})


def _material(value):
    from uuid import UUID
    from Tracker.models import Material
    qs = Material.objects.filter(archived=False)  # tenant-safe: .objects auto-scopes to the request tenant
    try:
        found = qs.filter(id=UUID(str(value))).first()
        if found:
            return found
    except ValueError:
        pass
    for field in ('part_number', 'name'):
        found = _unique(qs, field, value, 'material')
        if found:
            return found
    raise serializers.ValidationError({'material': f"No material matches '{value}'."})


def _line_values(row: dict) -> dict:
    """The BOMLine field values a row asks for (references resolved, types read)."""
    from Tracker.services.step_refs import resolve_step_ref
    vals: dict = {}
    if not _blank(row.get('component_type')):
        vals['component_type'] = _part_type(row['component_type'], 'component_type')
    if not _blank(row.get('material')):
        vals['material'] = _material(row['material'])
    if _blank(row.get('quantity')):
        raise serializers.ValidationError({'quantity': "Every line needs a quantity."})
    try:
        vals['quantity'] = Decimal(str(row['quantity']).strip())
    except InvalidOperation:
        raise serializers.ValidationError({'quantity': f"'{row['quantity']}' isn't a number."})
    for f in ('unit_of_measure', 'find_number', 'reference_designator', 'notes'):
        if not _blank(row.get(f)):
            vals[f] = str(row[f]).strip()
    if not _blank(row.get('source')):
        vals['source'] = str(row['source']).strip().upper()
    if not _blank(row.get('consumed_at_step')):
        vals['consumed_at_step'] = resolve_step_ref(row['consumed_at_step'], 'consumed_at_step')
    if not _blank(row.get('is_optional')):
        vals['is_optional'] = bool(parse_boolean(row['is_optional']))
    if not _blank(row.get('allow_harvested')):
        vals['allow_harvested'] = parse_boolean(row['allow_harvested'])
    if not _blank(row.get('line_number')):
        try:
            vals['line_number'] = int(float(str(row['line_number'])))
        except ValueError:
            raise serializers.ValidationError(
                {'line_number': f"'{row['line_number']}' isn't a line number."})
    return vals


_COMPARED = ('component_type_id', 'material_id', 'quantity', 'unit_of_measure', 'source',
             'consumed_at_step_id', 'find_number', 'reference_designator', 'is_optional',
             'allow_harvested', 'notes', 'line_number')


def _signature(lines) -> list:
    """A BOM's lines as comparable tuples (order-independent)."""
    out = []
    for ln in lines:
        get = (lambda f: ln.get(f)) if isinstance(ln, dict) else (lambda f: getattr(ln, f))
        out.append(tuple(str(get(f)) if get(f) is not None else '' for f in _COMPARED))
    return sorted(out)


def _as_compared(vals: dict, line_number: int) -> dict:
    """A row's values in the shape `_signature` compares (model defaults filled in)."""
    return {
        'component_type_id': getattr(vals.get('component_type'), 'id', None),
        'material_id': getattr(vals.get('material'), 'id', None),
        'quantity': vals['quantity'].quantize(Decimal('0.0001')),
        'unit_of_measure': vals.get('unit_of_measure', 'EA'),
        'source': vals.get('source', 'BUY'),
        'consumed_at_step_id': getattr(vals.get('consumed_at_step'), 'id', None),
        'find_number': vals.get('find_number', ''),
        'reference_designator': vals.get('reference_designator', ''),
        'is_optional': vals.get('is_optional', False),
        'allow_harvested': vals.get('allow_harvested'),
        'notes': vals.get('notes', ''),
        'line_number': line_number,
    }


def import_bom_rows(rows, *, tenant, user, context=None) -> dict:
    """Import BOM lines from parsed spreadsheet rows. Returns the import response shape
    the import dialog reads (summary + per-row results)."""
    from Tracker.models import BOM, BOMLine
    from Tracker.serializers.mes_standard import BOMLineSerializer
    from Tracker.services.mes.bom import create_new_bom_version

    result = ImportResult()
    groups: "OrderedDict[tuple, list]" = OrderedDict()
    for i, raw in enumerate(rows, start=1):
        row = _canonical(raw)
        if all(_blank(v) for v in row.values()):
            continue
        if _blank(row.get('part_type')):
            result.add_error(i, {'part_type': "Every row names its BOM's part type."})
            continue
        key = (str(row['part_type']).strip().lower(),
               str(row.get('revision') or '').strip(),
               str(row.get('bom_type') or 'ASSEMBLY').strip().upper())
        groups.setdefault(key, []).append((i, row))

    for (_, revision, bom_type), members in groups.items():
        row_numbers = [i for i, _ in members]
        sid = transaction.savepoint()
        try:
            parent = _part_type(members[0][1]['part_type'], 'part_type')
            line_vals = []
            for n, (i, row) in enumerate(members, start=1):
                try:
                    vals = _line_values(row)
                except serializers.ValidationError as e:
                    raise _RowError(i, e.detail)
                vals.setdefault('line_number', n)
                line_vals.append((i, vals))

            current = (BOM.objects.filter(  # tenant-safe: .objects auto-scopes to the request tenant
                part_type=parent, bom_type=bom_type, archived=False, is_current_version=True)
                .order_by('-version').first())
            wanted = _signature(_as_compared(v, v['line_number']) for _, v in line_vals)
            if current is not None and current.status != 'DRAFT':
                have = _signature(current.lines.filter(archived=False))
                if have == wanted and (not revision or revision == current.revision):
                    transaction.savepoint_commit(sid)
                    for i in row_numbers:
                        result.add_unchanged(i, current.id, [
                            f"No change: the same lines as {parent.name} rev "
                            f"{current.revision} ({current.status.lower()})."])
                    continue
                updates = {'revision': revision} if revision else {}
                draft = create_new_bom_version(
                    current, user=user, change_description="Imported from a spreadsheet",
                    **updates)
                created_bom = False
            elif current is not None:
                draft = current
                if revision and revision != draft.revision:
                    draft.revision = revision
                    draft.save(update_fields=['revision', 'updated_at'])
                created_bom = False
            else:
                draft = BOM.objects.create(tenant=tenant, part_type=parent, bom_type=bom_type,
                                           revision=revision or 'A', status='DRAFT')
                created_bom = True

            # Replace: the file is the complete line list for this BOM.
            draft.lines.filter(archived=False).delete()  # soft delete (SecureModel)
            for i, vals in line_vals:
                data = {k: (v.pk if hasattr(v, 'pk') else v) for k, v in vals.items()}
                data['bom'] = draft.pk
                ser = BOMLineSerializer(data=data, context=context or {})
                if not ser.is_valid():
                    raise _RowError(i, ser.errors)
                BOMLine.objects.create(tenant=tenant, bom=draft, **vals)
            transaction.savepoint_commit(sid)
            for i in row_numbers:
                (result.add_created if created_bom else result.add_updated)(
                    i, draft.id, [f"{parent.name} rev {draft.revision}: draft with "
                                  f"{len(line_vals)} line(s) — release it to put it in force."])
        except _RowError as e:
            transaction.savepoint_rollback(sid)
            for i in row_numbers:
                result.add_error(i, e.detail if i == e.row else {
                    'bom': f"Not imported: row {e.row} of this BOM has an error."})
        except (serializers.ValidationError, ValueError) as e:
            transaction.savepoint_rollback(sid)
            detail = getattr(e, 'detail', None) or str(e)
            for i in row_numbers:
                result.add_error(i, detail)
    return result.to_response()


class _RowError(Exception):
    def __init__(self, row, detail):
        super().__init__(str(detail))
        self.row, self.detail = row, detail
