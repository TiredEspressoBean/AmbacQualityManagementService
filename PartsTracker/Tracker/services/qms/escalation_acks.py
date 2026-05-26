"""
QMS escalation ack registrations.

Each domain owns the ack predicates for its events. This module declares
the predicate(s) for QMS-domain events that support escalation chains.

Imported at app startup via `Tracker.apps.TrackerConfig.ready()` so the
registry is populated before any rule fires.

Currently registered:
- ``ncr.opened`` — acknowledged when a closed `QuarantineDisposition`
  exists for the QualityReport. Cancelled when the source QR is archived
  (covers `void()` via SecureModel).

Future registrations (when their events get emitted from domain code):
- ``capa.opened`` — acknowledged when any `CapaVerification` has a final
  `effectiveness_result` (i.e. ≠ INCONCLUSIVE).
- ``document.approval_required`` — acknowledged when an `ApprovalResponse`
  exists for the request.
"""
from __future__ import annotations

from Tracker.services.core.notifications.escalation import register_ack


def _ncr_is_acknowledged(quality_report) -> bool:
    """An NCR is acked when at least one QuarantineDisposition for it has
    reached `current_state='CLOSED'`. A merely-OPEN disposition isn't ack —
    QA staff is still working it; the chain should continue.
    """
    # Late import to avoid the model-layer dependency cycle at app load.
    from Tracker.models import QuarantineDisposition
    # tenant-safe: predicate is invoked from `fire_one` inside `tenant_context(...)`;
    # the implicit tenant ContextVar already scopes the QuerySet.
    return QuarantineDisposition.objects.filter(
        quality_reports=quality_report,
        current_state='CLOSED',
    ).exists()


def _resolve_source_model():
    """Late-bind the QualityReports model to avoid app-load ordering issues."""
    from Tracker.models import QualityReports
    return QualityReports


# Registered at module-import time. The source_model is resolved eagerly
# here — by `apps.ready()`, the model registry is fully loaded.
register_ack(
    event_code='ncr.opened',
    source_model=_resolve_source_model(),
    is_acknowledged=_ncr_is_acknowledged,
    # Default cancel predicate handles `quality_report.archived` (SecureModel).
)
