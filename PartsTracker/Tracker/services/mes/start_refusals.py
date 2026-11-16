"""The last refused start on a visit, kept for planning (scheduling review item 11).

A refused start leaves no trace in the plan: the plan-vs-actual board marked the op
"missed" with no cause, and late-cause didn't know gates exist. So the refusal — a
floor gate, or a supervisor gate nobody signed for (user ruling 2026-11-16) — is kept
on the part's open visit at the step (`last_refusal_*`) until it starts, which clears
it. A part with no open visit there (Add Parts places parts at their first step
without one) gets the PENDING visit its arrival would have made: it IS waiting there.

A refused request rolls its transaction back (ATOMIC_REQUESTS), so inside a request the
write waits for `StartRefusalMiddleware`, which makes it after the view's transaction
has ended, in its own. Outside a request (a service call, a test) it is written at once.
No worker is involved.
"""
from __future__ import annotations

import logging
from contextvars import ContextVar

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

# The refusals a request has met, written once its transaction is over. None outside
# a request (set by StartRefusalMiddleware).
_deferred: ContextVar[list | None] = ContextVar('start_refusals_deferred', default=None)


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


def record(exc, *, part, step) -> None:
    """Keep `exc` as the last refused start of `part` at `step`. Never raises: the
    refusal reaches the operator whatever happens here."""
    described = _describe(exc)
    if described is None or part is None or step is None:
        return
    code, message = described
    entry = {'tenant_id': str(part.tenant_id), 'part_id': str(part.pk), 'step_id': str(step.pk),
             'code': code, 'message': message[:2000], 'at': timezone.now()}
    pending = _deferred.get()
    if pending is not None:
        pending.append(entry)
        return
    try:
        with transaction.atomic():
            _write(entry)
    except Exception:  # noqa: BLE001 - recording must never mask the refusal
        logger.exception("start refusal: could not record for part %s", entry['part_id'])


def _write(entry: dict) -> None:
    """Put the refusal on the part's open visit at the step, making the PENDING visit
    its arrival would have made when it has none and the part is AT that step."""
    from Tracker.models import Parts, StepExecution
    # tenant-safe: explicit tenant filter (also runs after the request's context)
    visit = (StepExecution.unscoped
             .filter(tenant_id=entry['tenant_id'], part_id=entry['part_id'],
                     step_id=entry['step_id'], exited_at__isnull=True)
             .order_by('-visit_number').first())
    if visit is None:
        part = Parts.unscoped.filter(tenant_id=entry['tenant_id'], pk=entry['part_id']).first()  # tenant-safe: explicit tenant filter
        if part is None or str(part.step_id) != entry['step_id']:
            return
        from Tracker.services.mes.parts import arrival_visit
        visit = arrival_visit(part, part.step)
    if visit.status != 'PENDING':
        return   # started since (or held by someone): nothing to record against
    StepExecution.unscoped.filter(pk=visit.pk).update(  # tenant-safe: pk of a tenant-filtered row
        last_refusal_code=entry['code'], last_refusal_message=entry['message'],
        last_refused_at=entry['at'])


def clear_fields() -> dict:
    """The values that clear a visit's last refusal (set on a successful start)."""
    return {'last_refusal_code': '', 'last_refusal_message': '', 'last_refused_at': None}


class StartRefusalMiddleware:
    """Writes the start refusals a request met AFTER its (rolled-back) transaction, each
    in its own, under its tenant. Outside ATOMIC_REQUESTS' view wrapper by position."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = _deferred.set([])
        try:
            response = self.get_response(request)
        finally:
            pending = _deferred.get() or []
            _deferred.reset(token)
        if pending:
            from Tracker.utils.tenant_context import tenant_context
            for entry in pending:
                try:
                    with tenant_context(entry['tenant_id']), transaction.atomic():
                        _write(entry)
                except Exception:  # noqa: BLE001 - the response is already decided
                    logger.exception("start refusal: could not record for part %s",
                                     entry['part_id'])
        return response
