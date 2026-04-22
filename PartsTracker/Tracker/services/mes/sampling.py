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

from Tracker.models import SamplingTriggerState


def update_sampling_trigger_state(part, status: str):
    """Record a PASS/FAIL result against the active sampling trigger
    for the part's step/work-order, and auto-deactivate the trigger
    if the success run has reached the configured fallback_duration.

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
        active_state.fail_count += 1

    active_state.parts_inspected.add(part)
    active_state.save()

    if active_state.ruleset.fallback_duration:
        if active_state.success_count >= active_state.ruleset.fallback_duration:
            active_state.active = False
            active_state.save()
