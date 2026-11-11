"""
A step's gates: which of the registry's gates (services/mes/gates.py) apply to a step,
composed by the engineer as typed `StepRequirement` rows (user decisions 2026-11-11).

Every gate is composable. The floor — the gates every step had before a person
chose otherwise — is the default set on a new step; an engineer may remove any of
them. A gate's stage (start or release) and escape tier come from the registry, never
from the row.

The data migration that moved the old Steps flags into rows
(migrations/0302_step_gates_from_flags.py) carries its own copy of the mapping.
"""
from __future__ import annotations

# The gate kinds a step can carry, in the order the editor lists them. Values are
# `gates.GateCode` values. Sampling is configured per substep through rulesets and
# isn't one of them; nor is reassignment (only the visit's holder works it — not a
# property of a step).
START_GATES = (
    'work_order_not_workable',
    'deviation_expired',
    'part_quarantined',
    'core_awaiting_authorisation',
    'training_not_authorized',
    'revisit_rule',
)
RELEASE_GATES = (
    'substeps_incomplete',
    'qualified_operator',
    'life_limit',
    'quarantine_hold',
    'qa_signoff',
    'first_piece',
    'measurement_out_of_spec',
)
COMPOSABLE_GATES = START_GATES + RELEASE_GATES

# On by default on a new step, and given to every step that existed before rows did:
# these applied to every step whatever its flags said.
FLOOR_GATES = (
    'work_order_not_workable',
    'deviation_expired',
    'part_quarantined',
    'core_awaiting_authorisation',
    'training_not_authorized',
    'substeps_incomplete',
    'qualified_operator',
    'life_limit',
)

FPI_SCOPES = ('PER_WORKORDER', 'PER_SHIFT', 'PER_EQUIPMENT')
QA_ASSURANCES = ('NONE', 'PASSWORD')
REVISIT_RULES = ('SAME', 'DIFFERENT', 'ROLE')


def ordered(rows: list[dict]) -> list[dict]:
    """`rows` in the editor's order, numbered."""
    rank = {g: i for i, g in enumerate(COMPOSABLE_GATES)}
    rows = sorted(rows, key=lambda r: rank.get(r['gate'], len(rank)))
    for i, r in enumerate(rows):
        r['order'] = i
    return rows


def floor_rows() -> list[dict]:
    """The rows a new step starts with."""
    return ordered([{'gate': g} for g in FLOOR_GATES])


def gate_row(step, gate: str):
    """The step's live row for `gate`, or None when the gate doesn't apply to it.
    Reads `step.requirements.all()`, so a `prefetch_related('requirements')` serves it."""
    for r in step.requirements.all():
        if r.gate == gate and not r.archived:
            return r
    return None


def rows_of(step) -> list[dict]:
    """The step's live gates as the editor's dicts — for writing them onto another step
    with `set_step_gates`."""
    return [{'gate': r.gate, 'order': r.order, 'fpi_scope': r.fpi_scope,
             'qa_assurance': r.qa_assurance, 'revisit_assignment': r.revisit_assignment,
             'revisit_role_id': r.revisit_role_id}
            for r in step.requirements.filter(archived=False).order_by('order')]


def gate_signature(rows) -> frozenset:
    """A comparable form of a gate list — dicts as the editor sends them, or
    StepRequirement rows — so two lists that configure the same gates compare equal."""
    out = set()
    for r in rows:
        d = r if isinstance(r, dict) else {
            'gate': r.gate, 'fpi_scope': r.fpi_scope, 'qa_assurance': r.qa_assurance,
            'revisit_assignment': r.revisit_assignment, 'revisit_role_id': r.revisit_role_id}
        c = clean_gate_row(d)
        out.add(tuple((k, str(v) if v is not None else '') for k, v in sorted(c.items())))
    return frozenset(out)


def clean_gate_row(row: dict) -> dict:
    """One row's fields, validated: only its own kind's settings kept."""
    from django.core.exceptions import ValidationError
    gate = row.get('gate')
    if gate not in COMPOSABLE_GATES:
        raise ValidationError(f"'{gate}' isn't a gate a step can carry.")
    out = {'gate': gate, 'fpi_scope': '', 'qa_assurance': '', 'revisit_assignment': '',
           'revisit_role_id': None}
    if gate == 'first_piece':
        scope = row.get('fpi_scope') or 'PER_WORKORDER'
        if scope not in FPI_SCOPES:
            raise ValidationError(f"'{scope}' isn't a first-piece scope.")
        out['fpi_scope'] = scope
        # How the inspector signs the buy-off: the buy-off is a QA release in its own
        # right, so the author sets it here as on the QA sign-off gate.
        assurance = row.get('qa_assurance') or 'NONE'
        if assurance not in QA_ASSURANCES:
            raise ValidationError(f"'{assurance}' isn't a sign-off assurance.")
        out['qa_assurance'] = assurance
    elif gate == 'qa_signoff':
        assurance = row.get('qa_assurance') or 'NONE'
        if assurance not in QA_ASSURANCES:
            raise ValidationError(f"'{assurance}' isn't a sign-off assurance.")
        out['qa_assurance'] = assurance
    elif gate == 'revisit_rule':
        rule = (row.get('revisit_assignment') or '').upper()
        if rule not in REVISIT_RULES:
            raise ValidationError("A repeat-visit gate needs its rule: SAME, DIFFERENT or ROLE.")
        out['revisit_assignment'] = rule
        if rule == 'ROLE':
            role = row.get('revisit_role_id', row.get('revisit_role'))
            out['revisit_role_id'] = getattr(role, 'pk', role) or None
    return out


def set_step_gates(step, rows: list[dict]) -> None:
    """Replace `step`'s gates with `rows` (the editor's whole list). A gate left out no
    longer applies to the step; one listed twice is refused."""
    from django.core.exceptions import ValidationError
    from Tracker.models import StepRequirement
    cleaned = [clean_gate_row(r) for r in rows]
    seen = [r['gate'] for r in cleaned]
    dupes = sorted({g for g in seen if seen.count(g) > 1})
    if dupes:
        raise ValidationError(f"A step carries each gate once: {', '.join(dupes)}.")
    # Without its role a Specific Role rule let anyone through: refused when written.
    # (Checked here, not in clean_gate_row, so comparing a step's existing gates —
    # one whose role was since deleted — never fails.)
    if any(r['revisit_assignment'] == 'ROLE' and not r['revisit_role_id'] for r in cleaned):
        raise ValidationError("A repeat-visit rule of Specific Role needs its role.")
    roles = {r['revisit_role_id'] for r in cleaned if r['revisit_role_id']}
    if roles:
        from Tracker.models import TenantGroup
        found = TenantGroup.objects.filter(  # tenant-safe: explicit tenant filter
            tenant_id=step.tenant_id, pk__in=roles).count()
        if found != len(roles):
            raise ValidationError("The repeat-visit role isn't one of this company's roles.")
    StepRequirement.objects.filter(step=step, archived=False).delete()  # tenant-safe: keyed to a scoped step
    for r in ordered(cleaned):
        StepRequirement.objects.create(tenant=step.tenant, step=step, **r)
    if hasattr(step, '_prefetched_objects_cache'):
        step._prefetched_objects_cache.pop('requirements', None)


def give_floor(step) -> None:
    """A new step's default gates: the floor."""
    set_step_gates(step, floor_rows())


# The old Steps flag names, for authoring code (seeds, fixtures) that describes a
# step the way the flags did.
FLAG_NAMES = ('requires_qa_signoff', 'qa_signoff_assurance', 'requires_first_piece_inspection',
              'fpi_scope', 'block_on_quarantine', 'block_on_measurement_failure',
              'revisit_assignment', 'revisit_role')


def set_gates_from_flags(step, *, requires_qa_signoff=False, qa_signoff_assurance='NONE',
                         requires_first_piece_inspection=False, fpi_scope='PER_WORKORDER',
                         block_on_quarantine=False, block_on_measurement_failure=False,
                         revisit_assignment='ANY', revisit_role=None) -> None:
    """Give `step` the floor plus the gate a flag named: the step a set of old flags
    described."""
    rows = floor_rows()
    rule = (revisit_assignment or 'ANY').upper()
    if rule in REVISIT_RULES:
        rows.append({'gate': 'revisit_rule', 'revisit_assignment': rule,
                     'revisit_role_id': getattr(revisit_role, 'pk', revisit_role)})
    if block_on_quarantine:
        rows.append({'gate': 'quarantine_hold'})
    if requires_qa_signoff:
        rows.append({'gate': 'qa_signoff', 'qa_assurance': qa_signoff_assurance or 'NONE'})
    if requires_first_piece_inspection:
        # The old step-level assurance applied to the buy-off too.
        rows.append({'gate': 'first_piece', 'fpi_scope': fpi_scope or 'PER_WORKORDER',
                     'qa_assurance': qa_signoff_assurance or 'NONE'})
    if block_on_measurement_failure:
        rows.append({'gate': 'measurement_out_of_spec'})
    set_step_gates(step, rows)


def split_flags(fields: dict) -> tuple[dict, dict]:
    """(step fields, gate flags) out of a dict that may carry the old flag names."""
    flags = {k: fields[k] for k in FLAG_NAMES if k in fields}
    return {k: v for k, v in fields.items() if k not in FLAG_NAMES}, flags
