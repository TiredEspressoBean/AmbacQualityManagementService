"""Whether a nonconformance needed a CAPA — the decision, recorded on its NCR.

ISO 9001 10.2.1(b) asks a nonconformity's need for action to be *evaluated*, not only
acted on. Most NCRs don't become CAPAs ("the disposition handles this part", "one-off,
no systemic cause"), and before this an NCR nobody promoted looked exactly like one
nobody had looked at. So the decision is a recorded human judgement:

- ``record_decision`` — a person says No CAPA needed or Deferred, with the reason.
- ``stamp_promoted`` — when a CAPA links the NCR, the NCR says CAPA raised.
  That is the one case that can be inferred safely; nothing else is ever defaulted.

Null means undecided, and the NCR list shows NCRs still in that state.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

DECIDABLE = ("NOT_REQUIRED", "DEFERRED")


def record_decision(ncr, *, decision: str, note: str, user):
    """Record that ``ncr`` needs no CAPA (NOT_REQUIRED) or that the call is put off
    (DEFERRED). The reason is required — it is what an auditor reads. A decision can be
    changed; the audit log keeps the earlier one. CAPA raised isn't recorded here: it
    follows from raising the CAPA."""
    from Tracker.models import NCR
    note = (note or "").strip()
    if decision == "PROMOTED":
        raise ValueError("Raise the CAPA from this NCR — it's marked CAPA raised when the CAPA links it.")
    if decision not in DECIDABLE:
        raise ValueError("Choose No CAPA needed or Deferred.")
    if not note:
        raise ValueError("Say why — the reason is what an auditor reads.")
    with transaction.atomic():
        locked = NCR.objects.select_for_update(of=("self",)).get(pk=ncr.pk)  # tenant-safe: pk of a scoped NCR
        if locked.capa_decision == "PROMOTED" and locked.capas.exists():
            raise ValueError("A CAPA already covers this NCR.")
        locked.capa_decision = decision
        locked.capa_decision_note = note
        locked.capa_decided_by = user if getattr(user, "is_authenticated", False) else None
        locked.capa_decided_at = timezone.now()
        locked.save(update_fields=["capa_decision", "capa_decision_note", "capa_decided_by",
                                   "capa_decided_at", "updated_at"])
    return locked


def stamp_promoted(capa, user) -> int:
    """Link the NCRs behind ``capa``'s reports and dispositions, and mark every NCR it
    links as CAPA raised (unless it already says so). Overrides an earlier No CAPA needed
    / Deferred: the CAPA is the newer, stronger decision. Returns how many NCRs changed."""
    from Tracker.services.qms.ncr import link_capa_ncrs
    link_capa_ncrs(capa)
    note = f"CAPA {capa.capa_number}" if capa.capa_number else "CAPA raised"
    by = user if getattr(user, "is_authenticated", False) else None
    changed = 0
    for ncr in capa.ncrs.exclude(capa_decision="PROMOTED"):  # tenant-safe: M2M of a scoped CAPA
        ncr.capa_decision = "PROMOTED"
        ncr.capa_decision_note = note
        ncr.capa_decided_by = by
        ncr.capa_decided_at = timezone.now()
        ncr.save(update_fields=["capa_decision", "capa_decision_note", "capa_decided_by",
                                "capa_decided_at", "updated_at"])
        changed += 1
    return changed
