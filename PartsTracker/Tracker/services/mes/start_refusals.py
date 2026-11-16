"""The last refused start on a visit, kept for planning (scheduling review item 11).

A refused start leaves no trace in the plan: the plan-vs-actual board marked the op
"missed" with no cause, and late-cause didn't know gates exist. So the refusal — a
floor gate, or a supervisor gate nobody signed for (user ruling 2026-11-16) — is kept
on the visit (`last_refusal_*`) until the visit starts, which clears it.

A refused request rolls its transaction back (ATOMIC_REQUESTS), so, like the andon
(services/mes/andon.py), the write goes through a task dispatched straight away and
done in its own transaction.
"""
from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


def _describe(exc) -> tuple[str, str] | None:
    """(code, message) for a start refusal, or None for an error that isn't one."""
    from Tracker.services.mes.gates import StartRefused
    from Tracker.services.mes import lifecycle
    if isinstance(exc, StartRefused):
        live = [b for b in exc.blockers if not getattr(b, 'pending', False)] or exc.blockers
        return str(live[0].code), ' '.join(b.message for b in live)
    codes = {lifecycle.NotQualified: 'training',
             lifecycle.NeedsReassignment: 'assigned_to_other',
             lifecycle.RevisitRefused: 'revisit_rule'}
    for cls, code in codes.items():
        if isinstance(exc, cls):
            return code, str(exc)
    return None


def record(execution, exc) -> None:
    """Keep `exc` as the visit's last refused start. Never raises: the refusal reaches
    the operator whatever happens here."""
    described = _describe(exc)
    if described is None or execution is None or not execution.pk:
        return
    code, message = described
    try:
        record_start_refusal.apply_async(args=[str(execution.pk), str(execution.tenant_id),
                                               code, message[:2000],
                                               timezone.now().isoformat()])
    except Exception:  # noqa: BLE001 - recording must never mask the refusal
        logger.exception("start refusal: could not record for visit %s", execution.pk)


def clear_fields() -> dict:
    """The values that clear a visit's last refusal (set on a successful start)."""
    return {'last_refusal_code': '', 'last_refusal_message': '', 'last_refused_at': None}


@shared_task
def record_start_refusal(execution_id: str, tenant_id: str, code: str, message: str,
                         refused_at: str) -> None:
    """Write the refusal onto the visit, unless it has started since."""
    from datetime import datetime
    from Tracker.models import StepExecution
    # tenant-safe: explicit tenant filter (runs outside a request)
    StepExecution.unscoped.filter(tenant_id=tenant_id, pk=execution_id,
                                  status='PENDING').update(
        last_refusal_code=code, last_refusal_message=message,
        last_refused_at=datetime.fromisoformat(refused_at))
