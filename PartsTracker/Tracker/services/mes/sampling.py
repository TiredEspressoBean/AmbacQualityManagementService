"""
Sampling trigger services.

`update_sampling_trigger_state` handles the "a measurement was just
recorded — update the active sampling trigger's counters and maybe
deactivate it" flow. The `SamplingTriggerManager` class in
`models/mes_standard.py` is a thin utility wrapper around this
function, preserved for backward compat; new callers should use this
service directly.

SamplingRuleSet lifecycle methods (`supersede_with`, `activate`,
`create_fallback_trigger`) are extracted to
`Tracker/services/mes/sampling_ruleset.py`.
"""
from __future__ import annotations

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from Tracker.models import SamplingTriggerState


def update_sampling_trigger_state(part, status: str):
    """Record a PASS/FAIL result against the active sampling trigger
    for the part's step/work-order, and auto-revert to the primary ruleset
    once the consecutive-good run reaches the configured fallback_duration.

    No-op when no active trigger state exists.
    """
    active_state = SamplingTriggerState.objects.filter(
        step=part.step,
        work_order=part.work_order,
        active=True,
    ).order_by('-triggered_at').first()

    if not active_state:
        return

    if status == 'PASS':
        active_state.success_count += 1
    else:
        # A failure during recovery resets progress — revert requires a
        # *consecutive* run of good parts.
        active_state.fail_count += 1
        active_state.success_count = 0

    active_state.parts_inspected.add(part)
    active_state.save(update_fields=['success_count', 'fail_count'])

    # The revert duration ("good parts required before reverting to this
    # ruleset") is configured on the PRIMARY ruleset, reachable from the
    # active fallback via its reverse one-to-one. Fall back to the value on
    # the fallback ruleset itself for legacy data that set it there.
    primary = _primary_ruleset_for(active_state)
    revert_after = getattr(primary, 'fallback_duration', None) if primary else None
    if revert_after is None:
        revert_after = active_state.ruleset.fallback_duration

    if revert_after and active_state.success_count >= revert_after:
        _deactivate_and_restore(active_state, primary)


def _primary_ruleset_for(active_state):
    """The primary ruleset that *active_state*'s fallback ruleset stands in
    for, or None when the relation isn't configured."""
    try:
        return active_state.ruleset.used_as_fallback_for
    except ObjectDoesNotExist:
        return None


def _deactivate_and_restore(active_state, primary):
    """Deactivate the fallback trigger and re-evaluate in-flight parts back
    to the primary ruleset.

    Deactivation alone isn't enough: parts already flagged for fallback keep
    their flag until re-evaluated. With the trigger inactive,
    SamplingFallbackApplier resolves them to the primary ruleset again.
    Atomic so the deactivation and the part restore commit together.
    """
    from Tracker.services.mes.sampling_ruleset import _reevaluate_active_parts_for_ruleset

    with transaction.atomic():
        active_state.active = False
        active_state.save(update_fields=['active'])
        if primary:
            _reevaluate_active_parts_for_ruleset(primary)
