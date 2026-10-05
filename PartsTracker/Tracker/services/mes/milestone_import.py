"""Importing milestone templates from a spreadsheet.

One sheet; each row is a MILESTONE, and its template is named on every row. The file is
the COMPLETE milestone list for each template it names (replace, not merge). Per
template the file names:

- no current template of that name        → a new template with the file's milestones;
- the current template has exactly the
  file's milestones                        → nothing changes;
- otherwise                                → a new VERSION of the template (the same
                                             `create_new_milestone_template_version` the
                                             Revise action and a PATCH use), whose
                                             milestones are then made the file's.

A MilestoneTemplate has no draft state: its revise path makes the new version current at
once, as an edit in the app does. Orders already under way keep the milestones of the
version they started on (see services.mes.milestone_template), so a new version reaches
new orders only.

Within the new version a milestone is its position (`display_order`, unique per
template): a copied milestone at a position the file names is updated to the file's
row, one at a position the file leaves out is soft-deleted, and a new position is added.

A template's milestones land together or not at all: one bad row fails that template
(every one of its rows reports why), and the other templates in the file still import.
Each milestone is validated by the API's own MilestoneSerializer.
"""
from __future__ import annotations

from collections import OrderedDict

from django.db import transaction
from rest_framework import serializers

from Tracker.services.csv_utils import ImportResult, parse_boolean
from Tracker.services.mes.bom_import import _RowError, _blank

COLUMNS = OrderedDict([
    ('template', ('template__name', 'template_name', 'milestone_template')),
    ('display_order', ('order', 'position', 'sequence')),
    ('name', ('milestone', 'milestone_name')),
    ('customer_display_name', ('customer_name', 'display_name')),
    ('description', ()),
    ('is_active', ('active',)),
])

_COMPARED = ('display_order', 'name', 'customer_display_name', 'description', 'is_active')


def _canonical(row: dict) -> dict:
    alias = {}
    for name, others in COLUMNS.items():
        for a in (name, *others):
            alias[a.lower()] = name
    out = {}
    for key, value in row.items():
        name = alias.get(str(key).lower())
        if name is not None and (out.get(name) in (None, '')):
            out[name] = value
    return out


def _milestone_values(row: dict, position: int) -> dict:
    if _blank(row.get('name')):
        raise serializers.ValidationError({'name': "Every milestone needs a name."})
    vals = {'name': str(row['name']).strip(),
            'customer_display_name': '' if _blank(row.get('customer_display_name'))
            else str(row['customer_display_name']).strip(),
            'description': '' if _blank(row.get('description')) else str(row['description']).strip(),
            'is_active': True if _blank(row.get('is_active')) else bool(parse_boolean(row['is_active'])),
            'display_order': position}
    if not _blank(row.get('display_order')):
        try:
            vals['display_order'] = int(float(str(row['display_order']).strip()))
        except ValueError:
            raise serializers.ValidationError(
                {'display_order': f"'{row['display_order']}' isn't a whole number."})
    return vals


def _signature(milestones) -> list:
    out = []
    for m in milestones:
        get = (lambda f: m.get(f)) if isinstance(m, dict) else (lambda f: getattr(m, f))
        out.append(tuple(str(get(f)) for f in _COMPARED))
    return sorted(out)


def import_milestone_rows(rows, *, tenant, user, context=None) -> dict:
    """Import milestones from parsed spreadsheet rows. Returns the import response shape
    the import dialog reads (summary + per-row results)."""
    from Tracker.models import Milestone, MilestoneTemplate
    from Tracker.serializers.mes_lite import MilestoneSerializer
    from Tracker.services.mes.milestone_template import create_new_milestone_template_version

    result = ImportResult()
    groups: "OrderedDict[str, list]" = OrderedDict()
    for i, raw in enumerate(rows, start=1):
        row = _canonical(raw)
        if all(_blank(v) for v in row.values()):
            continue
        if _blank(row.get('template')):
            result.add_error(i, {'template': "Every row names its milestone template."})
            continue
        groups.setdefault(str(row['template']).strip().lower(), []).append((i, row))

    for members in groups.values():
        row_numbers = [i for i, _ in members]
        name = str(members[0][1]['template']).strip()
        sid = transaction.savepoint()
        try:
            vals_list, seen = [], {}
            for n, (i, row) in enumerate(members, start=1):
                try:
                    vals = _milestone_values(row, n)
                except serializers.ValidationError as e:
                    raise _RowError(i, e.detail)
                if vals['display_order'] in seen:
                    raise _RowError(i, {'display_order': (
                        f"Rows {seen[vals['display_order']]} and {i} both have display "
                        f"order {vals['display_order']}.")})
                seen[vals['display_order']] = i
                vals_list.append((i, vals))
            wanted = _signature(v for _, v in vals_list)

            current = (MilestoneTemplate.objects.filter(  # tenant-safe: .objects auto-scopes to the request tenant
                name__iexact=name, is_current_version=True).first())
            if current is not None and current.archived:
                raise serializers.ValidationError({'template': (
                    f"'{current.name}' is archived. Restore it before importing into it.")})

            if current is not None:
                live = current.milestones.filter(archived=False)
                if _signature(live) == wanted:
                    transaction.savepoint_commit(sid)
                    for i in row_numbers:
                        result.add_unchanged(i, current.id, [
                            f"No change: the same milestones as '{current.name}' "
                            f"v{current.version}."])
                    continue
                target = create_new_milestone_template_version(
                    current, user=user, change_description="Imported from a spreadsheet")
                created = False
            else:
                target = MilestoneTemplate.objects.create(tenant=tenant, name=name)
                created = True

            # Replace, position by position (display_order is unique per template, deleted
            # rows included, so a position is reused rather than re-created).
            by_order = {m.display_order: m for m in target.milestones.all()}
            for i, vals in vals_list:
                existing = by_order.pop(vals['display_order'], None)
                ser = MilestoneSerializer(instance=existing, data={**vals, 'template': target.pk},
                                          context=context or {})
                if not ser.is_valid():
                    raise _RowError(i, ser.errors)
                if existing is None:
                    Milestone.objects.create(tenant=tenant, template=target, **vals)
                    continue
                for f, v in vals.items():
                    setattr(existing, f, v)
                existing.archived, existing.deleted_at = False, None
                existing.save()
            for leftover in by_order.values():
                leftover.delete()  # soft delete (SecureModel)
            transaction.savepoint_commit(sid)
            note = (f"'{target.name}' v{target.version} with {len(vals_list)} milestone(s)"
                    + ("" if created else " — orders already under way keep the version "
                                          "they started on."))
            for i in row_numbers:
                (result.add_created if created else result.add_updated)(i, target.id, [note])
        except _RowError as e:
            transaction.savepoint_rollback(sid)
            for i in row_numbers:
                result.add_error(i, e.detail if i == e.row else {
                    'template': f"Not imported: row {e.row} of this template has an error."})
        except (serializers.ValidationError, ValueError) as e:
            transaction.savepoint_rollback(sid)
            detail = getattr(e, 'detail', None) or str(e)
            for i in row_numbers:
                result.add_error(i, detail)
    return result.to_response()
