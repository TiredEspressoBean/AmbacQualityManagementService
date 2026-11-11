"""The andon: a refused start calls whoever clears it (user decision 2026-11-11).

A start refused by a gate nobody on the floor can clear — a held work order, a machine
down, a life limit… — emits `start.refused`, routed per gate to the groups that clear it
(starter rules in services/core/notifications/system_rules.py). The operator's screen
shows "Waiting on: …" from the refusal itself (`Blocker.to_dict`).

Not called for:
- a first piece: it already calls QA (`fpi.requested`);
- a supervisor-override refusal (training, repeat visit, reassignment): answered on the
  spot — "Ask a supervisor" — and not a StartRefused at all.

A refused request rolls its transaction back, so the call goes out through a task
dispatched straight away (not on commit), which writes in its own transaction.
De-duplicated per part (or step) and gate per hour, so retries don't spam.
"""
from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

# Gates whose refusal calls nobody (see the module docstring).
NOT_CALLED = {'first_piece_pending'}


def _payload(blocker, tenant_id) -> dict:
    part, step, wo = blocker.part, blocker.step, blocker.work_order
    anchor = part.id if part is not None else (step.id if step is not None else 'start')
    return {
        'id': f"{anchor}:{blocker.code}",
        'tenant_id': str(tenant_id),
        'gate': str(blocker.code),
        'waiting_on': blocker.spec.waiting_on,
        'message': blocker.message,
        'part_id': str(part.id) if part is not None else None,
        'part_number': part.ERP_id if part is not None else '',
        'step_id': str(step.id) if step is not None else None,
        'step_name': step.name if step is not None else '',
        'work_order_id': str(wo.id) if wo is not None else None,
        'work_order_number': wo.ERP_id if wo is not None else '',
    }


def call_for(blockers, tenant_id) -> None:
    """A start was refused for `blockers`: call whoever clears each. Never raises —
    the refusal reaches the operator whatever happens here."""
    if not tenant_id:
        return
    # Supervisor gates listed as pending behind the floor (P5) are answered on the spot.
    calls = [_payload(b, tenant_id) for b in blockers
             if str(b.code) not in NOT_CALLED and not getattr(b, 'pending', False)]
    if not calls:
        return
    # The de-duplication hour is the refusal's, not whenever a worker gets to it.
    hour = timezone.now().strftime('%Y%m%d%H')
    try:
        notify_start_refused.apply_async(args=[str(tenant_id), calls, hour])
    except Exception:  # noqa: BLE001 - the call must never mask the refusal
        logger.exception("andon: could not dispatch start.refused for tenant %s", tenant_id)


@shared_task
def notify_start_refused(tenant_id: str, calls: list[dict], hour: str | None = None) -> None:
    """Emit `start.refused` for each call, in its own transaction. `hour`: when the
    start was refused (YYYYMMDDHH), the de-duplication window."""
    from Tracker.models import Tenant
    from Tracker.services.core.notifications import emit
    from Tracker.services.mes.events import StartRefusedPayload
    from Tracker.utils.tenant_context import tenant_context

    tenant = Tenant.objects.filter(pk=tenant_id).first()
    if tenant is None:
        return
    hour = hour or timezone.now().strftime('%Y%m%d%H')
    with tenant_context(tenant_id):
        for call in calls:
            emit('start.refused', tenant=tenant, payload=StartRefusedPayload(**call),
                 correlation_id=f"start:{call['id']}",
                 idempotency_key=f"start.refused:{call['id']}:{hour}")
