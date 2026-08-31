"""Expected yield / scrap planning.

Resolves the expected scrap rate for a step, then the cumulative yield of a process, so
`plan_work_order` can gross up the started quantity ("release 11 to ship 10").

The rate is resolved through a fallback chain deliberately shaped like the timing chain in
`services.scheduling.data.get_step_timings`:

    observed (future, statistical) → step.scrap_rate (authored) → process default → 0

`observed_scrap_rate` is a placeholder today (returns None), so the authored estimate is
used. When there's enough StepExecution history to infer the real scrap rate for a step
within a confidence threshold, implement it there and it will take precedence automatically
— no change needed at the call sites.
"""
from __future__ import annotations

import math

# Clamp so cumulative yield can never reach 0 (avoids divide-by-zero / an absurd gross-up
# if someone authors a rate of 1.0).
_MAX_RATE = 0.99


def observed_scrap_rate(step) -> float | None:
    """Statistically-observed scrap fraction for a step from execution history, or None when
    there isn't enough data to be confident. PLACEHOLDER for the future data-driven model —
    returns None today so the authored rate is used. When implemented, this takes precedence
    over the authored `Steps.scrap_rate`."""
    return None


def step_scrap_rate(step, process_default: float) -> float:
    """Effective expected scrap fraction for a step, clamped to [0, 0.99]:
    observed (future) → `Steps.scrap_rate` (authored) → process default → 0."""
    obs = observed_scrap_rate(step)
    if obs is not None:
        rate = obs
    elif step.scrap_rate is not None:
        rate = float(step.scrap_rate)
    else:
        rate = process_default
    return max(0.0, min(_MAX_RATE, rate))


def process_yield(process) -> float:
    """Cumulative expected yield of a process = Π(1 − scrap_i) over its steps. 1.0 when no
    scrap is configured anywhere on the route."""
    from Tracker.models import ProcessStep

    default = max(0.0, min(_MAX_RATE, float(process.default_scrap_rate or 0)))
    y = 1.0
    for ps in ProcessStep.objects.filter(process=process).select_related('step'):
        y *= (1.0 - step_scrap_rate(ps.step, default))
    return y if y > 0 else (1.0 - _MAX_RATE)


def start_quantity_for_good(process, good_quantity: int) -> int:
    """Parts to START so the process finishes `good_quantity` good ones given expected yield:
    ceil(good / yield). Equals `good_quantity` when no scrap is configured."""
    y = process_yield(process)
    if y >= 1.0:
        return good_quantity
    return int(math.ceil(good_quantity / y))
