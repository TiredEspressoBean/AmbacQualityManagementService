"""One edit lock for everything the approval system decides or signs off.

The approval system — approval requests and the lifecycle actions (submit, decide,
grant, verify, close, …) — is the only source of truth for a decision. A client
edit (PATCH/PUT/DELETE through the API) must never be a second way to reach one.
Probed 2026-10-12: a PATCH could approve a process, a document or a CAPA, flip a
failed inspection to PASS, and rewrite a verified RCA or a closed CAPA.

Three rules, enforced once in the base viewset (`TenantScopedMixin`):

1. **Under approval, or approved — frozen.** A record with a PENDING or APPROVED
   ApprovalRequest is not edited or deleted. Approved content changes by a new
   revision; pending content by cancelling the request first.
2. **Signed off without an approval request — frozen once final.** `FINAL_WHEN`
   names the state at which each such record is a closed piece of evidence.
3. **Decision fields move only through their action.** `DECISION_FIELDS` may be
   sent unchanged (forms echo them back), never changed.

Services are not affected: they write models directly, and are the decision path.
"""
from __future__ import annotations

from django.contrib.contenttypes.models import ContentType

# model name -> (predicate on the instance, phrase for the refusal)
FINAL_WHEN = {
    'CAPA': (lambda o: o.status in ('CLOSED', 'CANCELLED'), "closed"),
    'CapaVerification': (lambda o: bool(o.effectiveness_result), "verified"),
    'RcaRecord': (lambda o: o.root_cause_verification_status == 'VERIFIED', "verified"),
    # The report is the inspector's FINDING — what was measured, by whom, when —
    # and is frozen once recorded. The QA Manager's JUDGEMENT about it (does this
    # need a CAPA?) is not: it's revised as evidence accumulates (Deferred ->
    # promoted when it recurs), so it moves through the `capa-decision` action and
    # capa_decision.py, which this lock deliberately doesn't cover.
    'QualityReports': (lambda o: o.status != 'PENDING', "recorded as a result"),
    'QuarantineDisposition': (lambda o: o.current_state == 'CLOSED', "closed"),
    'PartApproval': (lambda o: o.status != 'PENDING', "decided"),
    'Documents': (lambda o: o.status in ('APPROVED', 'RELEASED', 'OBSOLETE'), "approved"),
    'Processes': (lambda o: o.status not in ('DRAFT',), "out of draft"),
    'ProcessChangeRequest': (lambda o: o.status != 'DRAFT', "submitted for approval"),
    'TimeEntry': (lambda o: bool(o.approved), "approved"),
}

# model name -> ({fields}, where the decision is made)
DECISION_FIELDS = {
    'Documents': ({'status', 'approved_by', 'approved_at'}, "Submit for approval / Mark obsolete"),
    'Processes': ({'status', 'approved_by', 'approved_at'}, "Submit for approval, or a process change"),
    'CAPA': ({'approval_status', 'verified_by'}, "Request approval and the CAPA verification"),
    'PartApproval': ({'status'}, "Grant / Suspend / Disqualify"),
    'RcaRecord': ({'root_cause_verification_status', 'root_cause_verified_by', 'rca_review_status'},
                  "Submit for review / Approve"),
    'QuarantineDisposition': ({'disposition_type', 'current_state', 'decision_authorized_by'},
                              "Decide / Close"),
    'CapaVerification': ({'effectiveness_result', 'verified_by'}, "Verify"),
    'TimeEntry': ({'approved'}, "a supervisor's approval"),
}

_ACTIVE = ('PENDING', 'APPROVED')

# Where approval is a go-ahead rather than a sign-off of finished content: a
# Critical/Major CAPA is approved at creation so the work may start, then worked.
# Frozen while the approval is pending; editable once approved; frozen at close.
GO_AHEAD_APPROVALS = {'CAPA'}


def _label(instance) -> str:
    for attr in ('artifact_number', 'approval_number', 'capa_number', 'report_number',
                 'disposition_number', 'document_number', 'name', 'file_name'):
        v = getattr(instance, attr, None)
        if v:
            return str(v)
    return f"This {type(instance)._meta.verbose_name}"


def _active_approval(instance):
    from Tracker.models import ApprovalRequest
    if type(instance).__name__ in ('ApprovalRequest', 'ApprovalResponse', 'ApprovalTemplate'):
        return None
    # PENDING first: an open request outranks an older approved one.
    found = list(ApprovalRequest.objects  # tenant-safe: keyed to a tenant-scoped instance
                 .filter(content_type=ContentType.objects.get_for_model(type(instance)),
                         object_id=str(instance.pk), status__in=_ACTIVE)
                 .order_by('-requested_at'))
    return next((a for a in found if a.status == 'PENDING'), found[0] if found else None)


def _frozen_reason(instance) -> str | None:
    ar = _active_approval(instance)
    if ar is not None:
        if ar.status == 'PENDING':
            return (f"{_label(instance)} is awaiting approval ({ar.approval_number}); it can't be "
                    "changed while approvers are looking at it. Cancel the request to edit it.")
        if type(instance).__name__ not in GO_AHEAD_APPROVALS:
            return (f"{_label(instance)} is approved ({ar.approval_number}); approved content "
                    "changes only through a new revision.")
    final = FINAL_WHEN.get(type(instance).__name__)
    if final and final[0](instance):
        return f"{_label(instance)} is {final[1]}, so it can't be edited or deleted."
    return None


def _changed(instance, name, value) -> bool:
    try:
        field = type(instance)._meta.get_field(name)
    except Exception:
        return True
    current = getattr(instance, field.attname, None)
    if current is None or value is None:
        return (current is None) != (value in (None, ''))
    return str(current) != str(value)


def edit_refusal(instance, data) -> str | None:
    """Why a client may not apply ``data`` to ``instance``, or None when it may."""
    reason = _frozen_reason(instance)
    if reason:
        return reason
    decided = DECISION_FIELDS.get(type(instance).__name__)
    if decided:
        fields, route = decided
        moved = sorted(f for f in fields & set(data) if _changed(instance, f, data[f]))
        if moved:
            return (f"{', '.join(moved)} on {_label(instance)} is decided through {route}, "
                    "not by editing.")
    return None


def delete_refusal(instance) -> str | None:
    """Why a client may not delete ``instance``, or None when it may."""
    return _frozen_reason(instance)
