"""Machine overlaps a manual edit has created.

`ripple_forward` deliberately does not chase resource contention: a rippled task can
land on top of another job on the same machine, and CP-SAT owns no-overlap. That is the
right division — re-implementing it locally would duplicate the solver and drift from it
— but it obliges us to SHOW the overlap. A planner who pushed a job right and silently
double-booked a machine has made a mess they cannot see, and the schedule looks fine
until the next solve quietly moves something they thought they had decided.

Read-only and computed on demand: nothing is stored, because an overlap is a property of
the current positions and every solve rewrites those.
"""
from __future__ import annotations

from collections import defaultdict


def find_machine_overlaps(schedule) -> list[dict]:
    """Pairs of tasks booked on the same machine at the same time.

    A sweep per machine rather than a pairwise scan: sort by start, and a task overlaps
    only its immediate predecessors in that order, so this is O(n log n) in the number of
    tasks on a machine rather than O(n²) across the schedule.

    Tasks with no machine are skipped — an operation that needs no equipment cannot
    contend for it. So are unscheduled tasks (no start/end).
    """
    from Tracker.models.scheduling import ScheduledTask

    # tenant-safe: reverse FK from an in-tenant ScheduleResult.
    rows = list(
        schedule.tasks
        .filter(machine__isnull=False, start_time__isnull=False, end_time__isnull=False)
        .select_related('machine', 'step', 'part', 'core')
        .order_by('machine_id', 'start_time')
    )

    by_machine: dict = defaultdict(list)
    for t in rows:
        by_machine[t.machine_id].append(t)

    out: list[dict] = []
    for machine_id, tasks in by_machine.items():
        # `tasks` is already start-ordered by the queryset.
        for i, a in enumerate(tasks):
            for b in tasks[i + 1:]:
                if b.start_time >= a.end_time:
                    break        # sorted by start: nothing later can overlap `a` either
                out.append({
                    'machine': str(machine_id),
                    'machine_name': a.machine.name if a.machine else '',
                    'tasks': [str(a.id), str(b.id)],
                    'step_names': [a.step.name if a.step_id else '',
                                   b.step.name if b.step_id else ''],
                    'overlap_start': max(a.start_time, b.start_time),
                    'overlap_end': min(a.end_time, b.end_time),
                    # A pinned task in the pair is the one a planner put there, so it is
                    # the one they will want to reconsider — the other is the solver's
                    # and will move on its own at the next solve.
                    'pinned': [a.is_pinned, b.is_pinned],
                })
    return out


def overlapping_task_ids(schedule) -> set:
    """Just the ids, for marking bars on the board."""
    ids = set()
    for v in find_machine_overlaps(schedule):
        ids.update(v['tasks'])
    return ids
