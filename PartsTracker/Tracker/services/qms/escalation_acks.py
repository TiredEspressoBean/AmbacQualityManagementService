"""
QMS escalation ack registrations.

Each domain owns the ack predicates for its events. This module declares
the predicate(s) for QMS-domain events that support escalation chains.

Imported at app startup via `Tracker.apps.TrackerConfig.ready()` so the
registry is populated before any rule fires.

Currently registered:
- ``ncr.opened`` — acknowledged when the NCR is closed (every decision under it
  closed). Cancelled when the NCR is archived.

Future registrations (when their events get emitted from domain code):
- ``capa.opened`` — acknowledged when any `CapaVerification` has a final
  `effectiveness_result` (i.e. ≠ INCONCLUSIVE).
- ``document.approval_required`` — acknowledged when an `ApprovalResponse`
  exists for the request.
"""
from __future__ import annotations

from Tracker.services.core.notifications.escalation import register_ack


def _ncr_is_acknowledged(ncr) -> bool:
    """An NCR is acked once it is closed — every decision under it made and carried
    out. While anything under it is open, QA is still working it; the chain continues.
    """
    ncr.refresh_from_db(fields=['state'])
    return ncr.state == 'CLOSED'


def _resolve_source_model():
    """Late-bind the NCR model to avoid app-load ordering issues."""
    from Tracker.models import NCR
    return NCR


# Registered at module-import time. The source_model is resolved eagerly
# here — by `apps.ready()`, the model registry is fully loaded.
register_ack(
    event_code='ncr.opened',
    source_model=_resolve_source_model(),
    is_acknowledged=_ncr_is_acknowledged,
    # Default cancel predicate handles `ncr.archived` (SecureModel).
)
