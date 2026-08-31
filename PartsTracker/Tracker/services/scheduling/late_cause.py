"""Late-cause attribution (E7) — a post-solve heuristic.

For every task that finishes after its work order's due date, tag the single binding
constraint that best explains it, so a planner can see *why* an order is late and act on
it. This is a heuristic (not a formal critical-path proof): it picks the highest-priority
reason among material, labor, machine contention, release date, and lead time.

Runs after the schedule is written (`solve_schedule`), reading the persisted tasks + their
work orders. On-time tasks get an empty `late_cause`.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

# How close a preceding op on the same machine must end to this op's start for the delay to
# read as machine contention (covers back-to-back runs + changeover). Beyond this the
# machine sat idle, so the cause is elsewhere (release / lead time).
_CONTENTION_GAP = timedelta(minutes=60)


def attribute_late_causes(schedule) -> int:
    """Set `late_cause` on the schedule's late tasks (clear it on on-time ones). Returns the
    number of rows updated. tenant-safe: .objects auto-scopes to the request tenant, and
    every task belongs to `schedule` (already tenant-scoped)."""
    from Tracker.models import ScheduledTask

    tasks = list(
        # tenant-safe: `schedule` is a tenant-scoped row; its tasks belong to the same tenant.
        ScheduledTask.objects.filter(schedule=schedule).select_related(
            'part__work_order', 'core__work_order', 'step', 'machine')
    )
    if not tasks:
        return 0

    horizon_start_date = schedule.horizon_start.date()

    # Immediately-preceding op end per task on the same machine (for contention detection).
    by_machine: dict = defaultdict(list)
    for t in tasks:
        if t.machine_id:
            by_machine[t.machine_id].append(t)
    prev_end: dict = {}
    for mt in by_machine.values():
        mt.sort(key=lambda x: x.start_time)
        for i in range(1, len(mt)):
            prev_end[mt[i].id] = mt[i - 1].end_time

    def _wo(t):
        return (t.part.work_order if t.part_id
                else t.core.work_order if t.core_id else None)

    updated = []
    for t in tasks:
        wo = _wo(t)
        due = wo.expected_completion if wo else None
        late = bool(due and t.end_time and t.end_time.date() > due)

        cause = ""
        if late:
            if t.material_shortage:
                cause = "Material short — no incoming receipt"
            elif t.requires_operator and t.assigned_operator_id is None:
                cause = "Uncovered — no operator assigned"
            elif (t.machine_id and t.id in prev_end
                  and (t.start_time - prev_end[t.id]) <= _CONTENTION_GAP):
                cause = (f"Machine contention — {t.machine.name} busy"
                         if t.machine else "Machine contention")
            elif wo and wo.expected_start and wo.expected_start > horizon_start_date:
                cause = f"Late release — WO released {wo.expected_start:%b %d}"
            else:
                cause = "Tight lead time vs due date"

        if t.late_cause != cause:
            t.late_cause = cause
            updated.append(t)

    if updated:
        ScheduledTask.objects.bulk_update(updated, ['late_cause'])
    return len(updated)
