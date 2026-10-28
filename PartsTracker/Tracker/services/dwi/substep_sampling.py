"""A sampling rule for one substep (user decision 2026-10-28, B7).

`Substep.sampling_rule` makes a substep apply only to the parts its rule selects (null =
every part). A `SamplingRule` must belong to a rule set, and a substep's rule is not
part of its step's sampling plan, so a step's substep rules live in one rule set of
their own: inactive (the step engine applies only active sets) and marked
`origin="substep"`. The editor creates a rule here, then saves the substep's
`sampling_rule` through its normal (draft-only, versioning) update.
"""
from __future__ import annotations

SUBSTEP_ORIGIN = "substep"
# The per-part rules the substep engine evaluates (services/dwi/sampling_decisions.py).
SUBSTEP_RULE_TYPES = ("PERCENTAGE", "RANDOM", "EVERY_NTH_PART", "FIRST_N_PARTS")
_PERCENT_TYPES = ("PERCENTAGE", "RANDOM")


def retire_if_unused(rule_id) -> bool:
    """Archive a substep's former rule once no substep (archived ones included, for
    history) refers to it — a changed or cleared choice otherwise leaves one rule row
    behind per save. Only rules in a substep set; a step plan's rules are never
    touched. Returns whether it archived."""
    from Tracker.models import SamplingRule, Substep
    if rule_id is None:
        return False
    rule = SamplingRule.objects.filter(  # tenant-safe: .objects auto-scopes
        id=rule_id, archived=False, ruleset__origin=SUBSTEP_ORIGIN).first()
    if rule is None or Substep.objects.filter(sampling_rule_id=rule_id).exists():  # tenant-safe: auto-scoped
        return False
    rule.archived = True
    rule.save(update_fields=['archived', 'updated_at'])
    return True


def create_substep_rule(step, rule_type: str, value, user=None):
    """A new rule for a substep of `step`. Raises ValueError for a rule type the
    substep engine doesn't evaluate, or a value out of range."""
    from Tracker.models import SamplingRule, SamplingRuleSet

    if rule_type not in SUBSTEP_RULE_TYPES:
        raise ValueError(f"A substep can sample by {', '.join(SUBSTEP_RULE_TYPES)}, not {rule_type}.")
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValueError("The rule needs a whole-number value.")
    if rule_type in _PERCENT_TYPES and not 1 <= value <= 100:
        raise ValueError("A percentage is between 1 and 100.")
    if rule_type not in _PERCENT_TYPES and value < 1:
        raise ValueError("N is at least 1.")

    ruleset = (SamplingRuleSet.objects.filter(  # tenant-safe: .objects auto-scopes
        step=step, origin=SUBSTEP_ORIGIN, archived=False).first())
    if ruleset is None:
        ruleset = SamplingRuleSet.objects.create(
            tenant=step.tenant, step=step, part_type=step.part_type,
            name=f"Substep sampling — {step.name}"[:100], origin=SUBSTEP_ORIGIN, active=False)
    order = ruleset.rules.count() + 1
    return SamplingRule.objects.create(
        tenant=step.tenant, ruleset=ruleset, rule_type=rule_type, value=value, order=order,
        created_by=user)
