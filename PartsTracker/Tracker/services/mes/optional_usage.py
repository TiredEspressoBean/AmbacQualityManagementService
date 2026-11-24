"""Optional BOM lines on the floor: how much of one a unit draws (user ruling 2026-11-24).

An optional line (an O-ring kit fitted when the old one is cracked) was never drawn:
nobody recorded whether it went in, so its stock never moved. Two ways to say, per
optional line at its consuming step, in this order:

1. **A "used?" question** (`optionalPartUsed` node) on the step's work instructions —
   the operator answers used / not used and how many, per unit. Required: the unit
   can't leave the step unanswered on any gated path. The draw is made from the answer
   when the unit leaves the step, through the normal consume path (`consume_for_step`).
2. **Else the line's usage %** — drawn automatically at that rate as units pass. A
   running total over the work order keeps the count exact in whole units: after n
   units, round_half_up(n x qty x %) have been drawn, never more than n x qty; each unit
   draws the difference from what's already drawn, so a short shelf catches up later.
   Round half up rather than floor: the drawn count is never more than half a unit
   off the true rate either way, where floor runs a whole unit behind and draws nothing
   at all for small rates. Cycle counts square what's left.
3. **Else** nothing is drawn, as before.

Planning reads the usage % too (`bom.planned_share`); the question only decides draws.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

NODE_TYPE = 'optionalPartUsed'


def _walk(node, out):
    if isinstance(node, dict):
        if node.get('type') == NODE_TYPE:
            attrs = node.get('attrs') or {}
            if attrs.get('node_id') and attrs.get('bom_line_id'):
                out.append(attrs)
        for value in node.values():
            _walk(value, out)
    elif isinstance(node, list):
        for value in node:
            _walk(value, out)


def _node_attrs(doc) -> list:
    out: list = []
    _walk(doc, out)
    return out


def questions_for_step(step) -> dict:
    """`{bom_line_id: (substep, node_id)}`: the optional lines the step's work
    instructions ask "used?" about."""
    out: dict = {}
    for substep in step.substeps.filter(archived=False):
        for attrs in _node_attrs(substep.body_blocks):
            out.setdefault(str(attrs['bom_line_id']), (substep, attrs['node_id']))
    return out


def _execution_at(part, step):
    """The unit's latest visit to `step` — the one its answers belong to."""
    from Tracker.models import StepExecution
    return (StepExecution.objects.filter(part=part, step=step)  # tenant-safe: by the part FK
            .order_by('-entered_at').first())


def answer_for(part, step, node_id):
    """This unit's stored answer to a "used?" node on its latest visit, or None."""
    from Tracker.models import SubstepResponse
    execution = _execution_at(part, step)
    if execution is None:
        return None
    sr = (SubstepResponse.objects  # tenant-safe: by the execution FK
          .filter(step_execution=execution, node_id=node_id).order_by('-updated_at').first())
    return (sr.value_json or {}) if sr is not None else None


def unanswered(part, step) -> list[str]:
    """The optional parts the step asks about that this unit hasn't answered — what
    refuses the unit leaving the step (services/mes/parts.advance_part_step)."""
    from Tracker.models import BOMLine
    questions = questions_for_step(step)
    if not questions:
        return []
    missing = []
    for line_id, (_substep, node_id) in questions.items():
        if answer_for(part, step, node_id) is None:
            line = BOMLine.objects.filter(pk=line_id).select_related(  # tenant-safe: id from the tenant's own node
                'material', 'component_type').first()
            missing.append(_line_name(line))
    return missing


def _line_name(line) -> str:
    if line is None:
        return "an optional part"
    item = line.material or line.component_type
    return getattr(item, 'name', None) or "an optional part"


def answer_problem(attrs, cap) -> str | None:
    """Why a submitted answer doesn't satisfy the node, or None (the required check)."""
    if not cap or not isinstance(cap.get('used'), bool):
        return "Say whether it was used"
    if cap['used']:
        try:
            qty = Decimal(str(cap.get('quantity')))
        except Exception:  # noqa: BLE001 - any unreadable quantity is the same answer
            return "Say how many were used"
        if qty <= 0:
            return "Say how many were used"
    return None


def validate_answer(substep, node_id, cap, step_execution) -> dict:
    """The answer as stored: the node's line, used or not, and how many (0..the line's
    quantity; an omitted quantity is the line's). A unit's answer is given once — a
    different answer for the same visit is refused, as other per-unit captures are.
    Raises ValueError."""
    from Tracker.models import BOMLine, SubstepResponse
    attrs = next((a for a in _node_attrs(substep.body_blocks) if a['node_id'] == node_id), None)
    if attrs is None:
        raise ValueError("This question isn't on the substep.")
    line = BOMLine.objects.filter(pk=attrs['bom_line_id'], archived=False).first()  # tenant-safe: .objects auto-scopes
    if line is None or not line.is_optional:
        raise ValueError("This question's BOM line is gone or no longer optional.")
    used = cap.get('used')
    if not isinstance(used, bool):
        raise ValueError(f"Say whether {_line_name(line)} was used.")
    quantity = Decimal('0')
    if used:
        raw = cap.get('quantity')
        quantity = Decimal(str(line.quantity)) if raw in (None, '') else Decimal(str(raw))
        if quantity <= 0 or quantity > Decimal(str(line.quantity)):
            raise ValueError(f"{_line_name(line)}: used is 1 to {line.quantity}; "
                             f"answer 'Not used' for none.")
    lots = [{'lot_id': str(l.get('lot_id')), 'qty': str(l.get('qty') or '')}
            for l in (cap.get('lots') or []) if l.get('lot_id')] if used else []
    answer = {'node_id': node_id, 'kind': cap.get('kind'), 'bom_line_id': str(line.id),
              'used': used, 'quantity': str(quantity), 'lots': lots}
    prior = (SubstepResponse.objects  # tenant-safe: by the execution FK
             .filter(step_execution=step_execution, substep=substep, node_id=node_id).first())
    if prior is not None and prior.value_json:
        same = (prior.value_json.get('used') == used
                and Decimal(str(prior.value_json.get('quantity') or 0)) == quantity)
        if not same:
            raise ValueError(f"{_line_name(line)} was already answered for this unit at "
                             f"this step.")
    return answer


def rate_quantity(part, step, line, item_key) -> Decimal:
    """What this unit draws of an optional line at its usage %: the running target
    for the work order after this unit, less what's already been drawn there."""
    from django.db.models import Sum
    from Tracker.models import MaterialUsage, StepExecution
    from Tracker.services.mes.consumption import item_filter
    wo_id = part.work_order_id
    if wo_id is None or line.usage_percent is None:
        return Decimal('0')
    # Units of the order that have left this step, this one included (consumption runs
    # after the visit closes); a rework re-entry is another pass, as for required lines.
    n = StepExecution.objects.filter(  # tenant-safe: by the work order FK
        part__work_order_id=wo_id, step=step, exited_at__isnull=False).count()
    per_unit = Decimal(str(line.quantity))
    target = (Decimal(n) * per_unit * Decimal(str(line.usage_percent)) / Decimal(100)
              ).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    target = min(target, Decimal(n) * per_unit)
    drawn = (MaterialUsage.objects  # tenant-safe: by the work order FK
             .filter(work_order_id=wo_id, step=step, lot__isnull=False,
                     **item_filter(item_key, prefix='lot__'))
             .aggregate(q=Sum('qty_consumed'))['q'] or Decimal('0'))
    return max(Decimal('0'), target - drawn)
