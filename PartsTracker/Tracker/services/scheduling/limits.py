"""How long CP-SAT may search. The planner's time limit and gap are the planner's
(Scheduling settings; user ruling "solver run length is the planner's"). The only
other cap is `settings.SOLVER_TIME_CAP_SECONDS`, which the test settings set so the
suite doesn't wait out the planner's limit; it's unset (no cap) everywhere else.
"""
from __future__ import annotations

from django.conf import settings


def solver_seconds(seconds):
    """`seconds`, capped by SOLVER_TIME_CAP_SECONDS when that's set."""
    cap = getattr(settings, 'SOLVER_TIME_CAP_SECONDS', None)
    return min(seconds, cap) if cap else seconds
