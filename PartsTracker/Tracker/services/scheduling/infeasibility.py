"""Why did the solve place nothing?

CP-SAT answers INFEASIBLE with no explanation and no partial plan, and the board then
shows a planner an empty week with no hint of what to do about it. That is the worst
outcome the scheduler can produce: not a bad plan, but no plan and no reason.

The dominant cause is arithmetic rather than anything subtle. Every lot-op's start and
end are bounded by the horizon (`NewIntVar(0, H)`), so ALL work admitted to the window
must finish inside it. Ask for more hours than the window holds and there is no
assignment at all — the model has no way to say "this much fits and the rest waits".
Fixing that properly is deferral (optional intervals); until then, at least say so.

So this module compares the work the solver was actually given against the capacity of
the window it had to fit into, and names the resources that overflowed. It is a
heuristic explanation, not a proof of the infeasibility — CP-SAT's certificate would be
an IIS, which OR-Tools doesn't expose and a planner couldn't act on anyway. Capacity
arithmetic they can act on.
"""
from __future__ import annotations

# Below this, an "overload" is noise rather than a cause — a rounding artifact or a
# single short op — and blaming capacity would send the planner down the wrong path.
_MATERIAL_OVERLOAD_HOURS = 1.0


def diagnose_infeasible(tenant, horizon) -> dict:
    """Explain an INFEASIBLE solve over `horizon`.

    Returns `{'cause', 'summary', 'resources': [...]}`. `cause` is `'overload'` when a
    resource is demonstrably short, else `'unknown'` — better to say so than to invent
    a reason, since the planner would act on it.
    """
    from Tracker.services.planning.rccp import load_and_capacity, window_bucket

    bucket = window_bucket(tenant, horizon.start, horizon.end, label="horizon")
    figures = load_and_capacity(tenant, bucket)

    resources = [figures['labor'], *figures['work_centers']]
    over = sorted(
        (r for r in resources if r['overload_hours'] >= _MATERIAL_OVERLOAD_HOURS),
        key=lambda r: -r['overload_hours'],
    )
    window_days = round((horizon.end - horizon.start).total_seconds() / 86400)

    if not over:
        return {
            'cause': 'unknown',
            'summary': (
                f"The solver couldn't produce any plan for the {window_days}-day "
                f"window, and no resource is obviously over capacity. Look for a "
                f"conflict the capacity figures can't show — a pinned task on a "
                f"machine that is now down, an impossible max-time-between-ops "
                f"window, or a release date that leaves no room before the due date."
            ),
            'resources': resources,
            'window_days': window_days,
        }

    worst = over[0]
    others = (f" (+{len(over) - 1} more resource(s) short)" if len(over) > 1 else "")
    return {
        'cause': 'overload',
        'summary': (
            f"More work than the {window_days}-day window can hold. "
            f"{worst['name']} needs {worst['required_hours']:g}h but has "
            f"{worst['available_hours']:g}h available — short "
            f"{worst['overload_hours']:g}h{others}. Every scheduled operation must "
            f"finish inside the horizon, so nothing could be placed at all. Widen the "
            f"horizon, add capacity (overtime or a shift), or push work out by "
            f"changing due dates or holding orders."
        ),
        'resources': over,
        'window_days': window_days,
    }
