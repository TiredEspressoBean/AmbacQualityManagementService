"""Importing sampling rulesets from a spreadsheet.

One sheet; each row is a RULE, and its ruleset is named on every row by part type,
step (`Process > Step`, see services.step_refs), supplier (blank = all suppliers) and
the ruleset's name. The file is the COMPLETE rule list for each ruleset it names
(replace, not merge), and an import never puts anything in force.

A SamplingRuleSet doesn't version through `create_new_version`: a successor is a new
row whose `supersedes` points at its predecessor, and what is in force is the `active`
flag (the sampling applier reads active, non-archived rulesets only). So here a DRAFT is
an INACTIVE ruleset, and per ruleset the file names:

- one is active and the file's rules are its rules    → nothing changes;
- one is active and it has an inactive successor      → that successor is the draft,
                                                        and its rules are replaced;
- one is active and it has no inactive successor      → a new inactive ruleset that
                                                        supersedes it (version + 1, its
                                                        plan and gate settings copied),
                                                        with the file's rules;
- none is active but an inactive one exists           → that one is the draft, edited;
- none at all                                          → a new inactive ruleset.

Putting a draft in force stays a human step: `activate_sampling_ruleset` (it also
deactivates the peers and re-evaluates the parts at the step). The model's own
`supersede_sampling_ruleset` isn't used for the draft because it creates the successor
ACTIVE — beside its predecessor, both in force — and drops the supplier, plan and gate.

A ruleset's rules land together or not at all: one bad rule fails that ruleset (every
one of its rows reports why), and the other rulesets in the file still import. Each rule
is validated by the API's own SamplingRuleSerializer.
"""
from __future__ import annotations

from collections import OrderedDict

from django.db import transaction
from rest_framework import serializers

from Tracker.services.csv_utils import ImportResult
from Tracker.services.mes.bom_import import _RowError, _blank, _part_type, _unique

# The columns, as an export writes them and an import reads them.
COLUMNS = OrderedDict([
    ('part_type', ('ruleset__part_type', 'ruleset_part_type')),
    ('step', ('ruleset__step', 'ruleset_step')),
    ('supplier', ('ruleset__supplier', 'ruleset_supplier')),
    ('ruleset', ('ruleset__name', 'ruleset_name', 'rule_set')),
    ('order', ('rule_order', 'position')),
    ('rule_type', ('type', 'rule')),
    ('value', ('rule_value',)),
])

_SUFFIXES = ('__name', '_name', '__ref', '_ref')

# Ruleset settings a draft carries over from the ruleset it supersedes. Not the
# `fallback_ruleset` link: it is one-to-one, so only one ruleset can hold it.
_CARRIED = ('aql', 'inspection_level', 'severity', 'strategy', 'variables_characteristic_id',
            'gate_metric', 'gate_threshold', 'gate_window', 'gate_window_n', 'gate_min_sample',
            'gate_actions', 'gate_capa_type', 'gate_capa_severity', 'gate_approval_template_id',
            'fallback_duration')


def _canonical(row: dict) -> dict:
    """Map a parsed row's columns to COLUMNS, ignoring case and export suffixes."""
    alias = {}
    for name, others in COLUMNS.items():
        for a in (name, *others):
            alias[a.lower()] = name
    out = {}
    for key, value in row.items():
        k = str(key).lower()
        if k not in alias:
            for sfx in _SUFFIXES:
                if k.endswith(sfx) and k[:-len(sfx)] in alias:
                    k = k[:-len(sfx)]
                    break
        name = alias.get(k)
        if name is not None and (out.get(name) in (None, '')):
            out[name] = value
    return out


def _int(value, what):
    try:
        return int(float(str(value).strip()))
    except ValueError:
        raise serializers.ValidationError({what: f"'{value}' isn't a whole number."})


def _supplier(value):
    from uuid import UUID
    from Tracker.models import Companies
    qs = Companies.objects.filter(archived=False)  # tenant-safe: .objects auto-scopes to the request tenant
    try:
        found = qs.filter(id=UUID(str(value))).first()
        if found:
            return found
    except ValueError:
        pass
    current = qs.filter(is_current_version=True)
    found = _unique(current, 'name', value, 'supplier') or _unique(qs, 'name', value, 'supplier')
    if found:
        return found
    raise serializers.ValidationError({'supplier': f"No company matches '{value}'."})


def _process_of(step_value):
    """The process a `Process > Step` reference names (None for a bare step or an ID)."""
    from Tracker.models import Processes
    from Tracker.services.step_refs import SEPARATOR
    raw = str(step_value).strip()
    if SEPARATOR not in raw:
        return None
    name = raw.split(SEPARATOR, 1)[0].strip()
    qs = Processes.objects.filter(name__iexact=name, archived=False)  # tenant-safe: .objects auto-scopes to the request tenant
    return qs.filter(is_current_version=True).first() or qs.order_by('-version').first()


def _rule_values(row: dict, position: int) -> dict:
    """The SamplingRule field values a row asks for."""
    if _blank(row.get('rule_type')):
        raise serializers.ValidationError({'rule_type': "Every rule needs a rule_type."})
    vals = {'rule_type': str(row['rule_type']).strip().upper(),
            'value': None if _blank(row.get('value')) else _int(row['value'], 'value'),
            'order': position if _blank(row.get('order')) else _int(row['order'], 'order')}
    return vals


def _signature(rules) -> list:
    """A ruleset's rules as comparable tuples (order-independent)."""
    out = []
    for r in rules:
        get = (lambda f: r.get(f)) if isinstance(r, dict) else (lambda f: getattr(r, f))
        out.append((str(get('rule_type')), '' if get('value') is None else str(get('value')),
                    str(get('order'))))
    return sorted(out)


def _live_rules(ruleset):
    return ruleset.rules.filter(archived=False)


def _new_draft(*, tenant, user, part_type, step, supplier, name, process, supersedes=None):
    """An inactive ruleset — from `supersedes`'s settings when there is one."""
    from Tracker.models import SamplingRuleSet
    source = supersedes
    draft = SamplingRuleSet.create_with_rules(
        part_type=part_type, step=step, supplier=supplier, name=name,
        process=source.process if source is not None else process,
        is_fallback=source.is_fallback if source is not None else False,
        origin="spreadsheet-import", active=False, rules=[], created_by=user,
        # `supersedes` is one-to-one: a predecessor whose (deleted) draft still holds
        # the link gets a successor that names it by version only.
        supersedes=source if source is not None and not SamplingRuleSet.objects.filter(  # tenant-safe: .objects auto-scopes to the request tenant
            supersedes=source).exists() else None,
    )
    if source is not None:
        for f in _CARRIED:
            setattr(draft, f, getattr(source, f))
        draft.version = source.version + 1
        draft.save(update_fields=[*[f.removesuffix('_id') for f in _CARRIED], 'version',
                                  'updated_at'])
    return draft


def import_sampling_rows(rows, *, tenant, user, context=None) -> dict:
    """Import sampling rules from parsed spreadsheet rows. Returns the import response
    shape the import dialog reads (summary + per-row results)."""
    from Tracker.models import SamplingRule, SamplingRuleSet
    from Tracker.serializers.qms import SamplingRuleSerializer
    from Tracker.services.step_refs import resolve_step_ref

    result = ImportResult()
    groups: "OrderedDict[tuple, list]" = OrderedDict()
    for i, raw in enumerate(rows, start=1):
        row = _canonical(raw)
        if all(_blank(v) for v in row.values()):
            continue
        missing = [c for c in ('part_type', 'step', 'ruleset') if _blank(row.get(c))]
        if missing:
            result.add_error(i, {c: "Every row names its ruleset's part type, step and name."
                                 for c in missing})
            continue
        key = tuple(str(row.get(c) or '').strip().lower()
                    for c in ('part_type', 'step', 'supplier', 'ruleset'))
        groups.setdefault(key, []).append((i, row))

    for members in groups.values():
        row_numbers = [i for i, _ in members]
        first = members[0][1]
        sid = transaction.savepoint()
        try:
            part_type = _part_type(first['part_type'], 'part_type')
            step = resolve_step_ref(first['step'], 'step')
            supplier = None if _blank(first.get('supplier')) else _supplier(first['supplier'])
            name = str(first['ruleset']).strip()

            rule_vals, seen = [], {}
            for n, (i, row) in enumerate(members):
                try:
                    vals = _rule_values(row, n)
                except serializers.ValidationError as e:
                    raise _RowError(i, e.detail)
                if vals['order'] in seen:
                    raise _RowError(i, {'order': (f"Rows {seen[vals['order']]} and {i} both "
                                                  f"have order {vals['order']}.")})
                seen[vals['order']] = i
                rule_vals.append((i, vals))
            wanted = _signature(v for _, v in rule_vals)

            base = SamplingRuleSet.objects.filter(  # tenant-safe: .objects auto-scopes to the request tenant
                archived=False, part_type=part_type, step=step, supplier=supplier,
                name__iexact=name)
            in_force = base.filter(active=True).order_by('-version').first()
            if in_force is not None:
                draft = (SamplingRuleSet.objects.filter(  # tenant-safe: .objects auto-scopes to the request tenant
                    supersedes=in_force, active=False, archived=False).first())
                unchanged = in_force if _signature(_live_rules(in_force)) == wanted else None
            else:
                draft = (base.filter(active=False, superseded_by__isnull=True)
                         .order_by('-version', '-created_at').first())
                unchanged = None
            if unchanged is None and draft is not None \
                    and _signature(_live_rules(draft)) == wanted:
                unchanged = draft
            if unchanged is not None:
                transaction.savepoint_commit(sid)
                state = "in force" if unchanged.active else "draft, not active"
                for i in row_numbers:
                    result.add_unchanged(i, unchanged.id, [
                        f"No change: the same rules as '{unchanged.name}' "
                        f"v{unchanged.version} ({state})."])
                continue

            # "Created" is a ruleset the tenant didn't have; a draft of one in force is an
            # update of that ruleset (as a BOM's new draft revision is).
            created = draft is None and in_force is None
            new_draft = draft is None
            if new_draft:
                draft = _new_draft(tenant=tenant, user=user, part_type=part_type, step=step,
                                   supplier=supplier, name=name,
                                   process=_process_of(first['step']), supersedes=in_force)
            else:
                draft.modified_by = user
                draft.save(update_fields=['modified_by', 'updated_at'])

            # Replace: the file is the complete rule list for this ruleset.
            _live_rules(draft).delete()  # soft delete (SecureModel)
            for i, vals in rule_vals:
                ser = SamplingRuleSerializer(data={**vals, 'ruleset': draft.pk},
                                             context=context or {})
                if not ser.is_valid():
                    raise _RowError(i, ser.errors)
                SamplingRule.objects.create(tenant=tenant, ruleset=draft, created_by=user,
                                            **vals)
            transaction.savepoint_commit(sid)
            notes = [f"'{draft.name}' v{draft.version}: draft (inactive) with "
                     f"{len(rule_vals)} rule(s) — activate it to put it in force."]
            if in_force is not None and in_force.fallback_ruleset_id and new_draft:
                notes.append("The ruleset in force has a fallback ruleset; the draft doesn't "
                             "carry that link — set it before activating.")
            for i in row_numbers:
                (result.add_created if created else result.add_updated)(i, draft.id, notes)
        except _RowError as e:
            transaction.savepoint_rollback(sid)
            for i in row_numbers:
                result.add_error(i, e.detail if i == e.row else {
                    'ruleset': f"Not imported: row {e.row} of this ruleset has an error."})
        except (serializers.ValidationError, ValueError) as e:
            transaction.savepoint_rollback(sid)
            detail = getattr(e, 'detail', None) or str(e)
            for i in row_numbers:
                result.add_error(i, detail)
    return result.to_response()
