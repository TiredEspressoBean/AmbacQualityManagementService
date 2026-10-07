"""Whether a failed quality report needed a CAPA — the decision, recorded.

ISO 9001 10.2.1(b) asks a nonconformity's need for action to be *evaluated*, not only
acted on. Most failed reports don't become CAPAs ("the disposition handles this part",
"one-off, no systemic cause"), and before this an NCR nobody promoted looked exactly
like one nobody had looked at. So the decision is a recorded human judgement:

- ``record_decision`` — a person says No CAPA needed or Deferred, with the reason.
- ``stamp_promoted`` — when a CAPA links the report, the report says CAPA raised.
  That is the one case that can be inferred safely; nothing else is ever defaulted.

Null means undecided, and the NCR page lists failed reports still in that state.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

DECIDABLE = ("NOT_REQUIRED", "DEFERRED")


def record_decision(report, *, decision: str, note: str, user):
    """Record that ``report`` needs no CAPA (NOT_REQUIRED) or that the call is put off
    (DEFERRED). The reason is required — it is what an auditor reads. A decision can be
    changed; the audit log keeps the earlier one. CAPA raised isn't recorded here: it
    follows from raising the CAPA."""
    from Tracker.models import QualityReports
    note = (note or "").strip()
    if decision == "PROMOTED":
        raise ValueError("Raise the CAPA from this report — it's marked CAPA raised when the CAPA links it.")
    if decision not in DECIDABLE:
        raise ValueError("Choose No CAPA needed or Deferred.")
    if not note:
        raise ValueError("Say why — the reason is what an auditor reads.")
    with transaction.atomic():
        locked = QualityReports.objects.select_for_update(of=("self",)).get(pk=report.pk)  # tenant-safe: pk of a scoped report
        if locked.status != "FAIL":
            raise ValueError("Only a failed report needs a CAPA decision.")
        if locked.capa_decision == "PROMOTED" and locked.capas.exists():
            raise ValueError("A CAPA already covers this report.")
        locked.capa_decision = decision
        locked.capa_decision_note = note
        locked.capa_decided_by = user if getattr(user, "is_authenticated", False) else None
        locked.capa_decided_at = timezone.now()
        locked.save(update_fields=["capa_decision", "capa_decision_note", "capa_decided_by",
                                   "capa_decided_at", "updated_at"])
    return locked


def stamp_promoted(capa, user) -> int:
    """Mark every report ``capa`` links as CAPA raised (unless it already says so).
    Overrides an earlier No CAPA needed / Deferred: the CAPA is the newer, stronger
    decision. Returns how many reports changed."""
    note = f"CAPA {capa.capa_number}" if capa.capa_number else "CAPA raised"
    by = user if getattr(user, "is_authenticated", False) else None
    changed = 0
    for report in capa.quality_reports.exclude(capa_decision="PROMOTED"):  # tenant-safe: M2M of a scoped CAPA
        report.capa_decision = "PROMOTED"
        report.capa_decision_note = note
        report.capa_decided_by = by
        report.capa_decided_at = timezone.now()
        report.save(update_fields=["capa_decision", "capa_decision_note", "capa_decided_by",
                                   "capa_decided_at", "updated_at"])
        changed += 1
    return changed
