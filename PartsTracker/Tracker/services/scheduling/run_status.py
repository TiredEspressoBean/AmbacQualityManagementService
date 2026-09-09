"""Tenant-wide status for the background solve / dispatch.

The task id used to live only in the requesting browser tab, so a running solve was
invisible to everyone else — a second planner saw a board that wasn't changing and no
reason why. Recording it against the tenant lets every client poll the same answer.

Two things make the estimate honest rather than decorative:

* **CP-SAT runs to a wall-clock cap.** `solver_time_limit_seconds` bounds the solve, so
  the finish time is known, not guessed. It can end early by proving optimality, which
  is why the UI should say "at most", never "exactly".

* **A run can die.** If the worker is down the task sits in the queue indefinitely — that
  happened in development: a solve was queued, the worker was killed, and the task only
  executed hours later when a worker came back. A naive in-flight flag would have shown
  every client "solving…" for those hours, and a permanently-spinning indicator is worse
  than none because people stop believing it. Hence `_is_stale`.
"""
from __future__ import annotations

from datetime import timedelta

# Queue wait, worker startup, and the solve overrunning its own cap slightly (a 120s
# limit measured 122.3s in practice — CP-SAT checks the clock between search nodes).
_GRACE_SECONDS = 120


def _limit_seconds(config) -> int:
    return int(getattr(config, 'solver_time_limit_seconds', 180) or 180)


def _is_stale(config, now) -> bool:
    """Past its cap plus grace with nothing recorded — the worker almost certainly died."""
    started = getattr(config, 'active_run_started_at', None)
    if started is None:
        return True
    return now > started + timedelta(seconds=_limit_seconds(config) + _GRACE_SECONDS)


def mark_started(config, task_id: str, kind: str) -> None:
    """Record a queued run so every client can see it, not just the requester."""
    from django.utils import timezone

    config.active_run_task_id = task_id or ''
    config.active_run_kind = kind
    config.active_run_started_at = timezone.now()
    config.save(update_fields=['active_run_task_id', 'active_run_kind',
                               'active_run_started_at'])


def mark_finished(config) -> None:
    """Clear the in-flight marker. Safe to call when nothing is recorded."""
    if not config.active_run_task_id and config.active_run_started_at is None:
        return
    config.active_run_task_id = ''
    config.active_run_kind = ''
    config.active_run_started_at = None
    config.save(update_fields=['active_run_task_id', 'active_run_kind',
                               'active_run_started_at'])


def current_run(config) -> dict:
    """What this tenant has in flight, for any client that asks.

    Returns `{running, kind, task_id, state, seconds_elapsed, seconds_remaining,
    limit_seconds, stale}`. `state` distinguishes QUEUED from STARTED where the result
    backend knows — "queued four minutes ago and never started" is the signature of a
    worker that isn't running, and is worth saying out loud rather than showing a
    spinner that never resolves.
    """
    from celery.result import AsyncResult
    from django.utils import timezone

    task_id = getattr(config, 'active_run_task_id', '') or ''
    if not task_id:
        return {'running': False}

    now = timezone.now()
    started = config.active_run_started_at
    limit = _limit_seconds(config)
    elapsed = int((now - started).total_seconds()) if started else 0

    res = AsyncResult(task_id)
    if res.ready():
        # Finished while nobody was polling — clear it so the next reader sees the truth.
        mark_finished(config)
        return {'running': False, 'last_state': res.state}

    if _is_stale(config, now):
        # Don't clear it: the task may still be sitting in the queue and could yet run.
        # Say it's stale and let a human decide, rather than silently forgetting a job
        # that might still fire.
        return {
            'running': False, 'stale': True, 'kind': config.active_run_kind,
            'task_id': task_id, 'seconds_elapsed': elapsed, 'limit_seconds': limit,
            'state': res.state,
        }

    return {
        'running': True,
        'stale': False,
        'kind': config.active_run_kind,
        'task_id': task_id,
        'state': res.state,          # PENDING = queued, STARTED = a worker has it
        'seconds_elapsed': elapsed,
        # "At most": the cap is a ceiling, and proving optimality ends it sooner.
        'seconds_remaining': max(0, limit - elapsed),
        'limit_seconds': limit,
    }
