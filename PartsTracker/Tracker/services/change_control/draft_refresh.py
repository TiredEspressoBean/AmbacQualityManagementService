"""A submitted change's draft stays editable — and nothing unreviewed is ever approved
(user ruling 2026-11-16).

Any edit to the draft of a SUBMITTED / UNDER_REVIEW process change (step content, gates,
machines, tooling, routing) refreshes the change's proposed-changes diff. When the diff
actually changed, the approvals already given are withdrawn — each a RecordEdit naming
the edit — the change's history records the refresh, and the approvers are notified
again. An approval can then only be given on the diff as it now stands. No withdraw /
resubmit loop.

Edits reach here through signals (Tracker/signals.py) on the rows a draft is made of; a
save that touches many rows refreshes once, after its transaction commits.
"""
from __future__ import annotations

import logging

from django.db import transaction

logger = logging.getLogger(__name__)

_REVIEW_STATUSES = ('SUBMITTED', 'UNDER_REVIEW')


def drafts_under_review_for_step(step_id) -> set:
    """The DRAFT processes using this step row whose change is under review."""
    from Tracker.models import ProcessChangeRequest, ProcessStep
    drafts = set(ProcessStep.objects.filter(  # tenant-safe: .objects auto-scopes
        step_id=step_id, process__status='DRAFT').values_list('process_id', flat=True))
    if not drafts:
        return set()
    return set(ProcessChangeRequest.objects.filter(  # tenant-safe: .objects auto-scopes
        draft_process_version_id__in=drafts, status__in=_REVIEW_STATUSES)
        .values_list('draft_process_version_id', flat=True))


def schedule_refresh(process_ids, user=None) -> None:
    """Refresh each draft's change once the current transaction commits — in the
    tenant of the edit, which may no longer be current by then."""
    from Tracker.utils.tenant_context import get_current_tenant_id, tenant_context
    tenant_id = get_current_tenant_id()

    def run(pid):
        with tenant_context(tenant_id):
            refresh_submitted_change(pid, user=user)

    for pid in set(process_ids or ()):
        transaction.on_commit(lambda pid=pid: run(pid))


def refresh_submitted_change(process_id, user=None) -> int:
    """Recompute the diff of the change under review whose draft is `process_id`. When
    it differs from what reviewers saw: withdraw the approvals given, record the
    refresh, notify the approvers. Returns the approvals withdrawn."""
    from django.contrib.contenttypes.models import ContentType
    from Tracker.models import (
        ApprovalDecision, ApprovalRequest, ProcessChangeRequest, RecordEdit,
    )
    from Tracker.services.change_control.diff import compute_process_diff

    withdrawn = 0
    for pcr in (ProcessChangeRequest.objects  # tenant-safe: .objects auto-scopes
                .filter(draft_process_version_id=process_id, status__in=_REVIEW_STATUSES)
                .select_related('target_process', 'draft_process_version')):
        new = compute_process_diff(pcr.target_process, pcr.draft_process_version)
        if new == (pcr.proposed_change_diff or {}):
            continue
        # Outside a request (a script, a task) the edit has no user: the change's
        # submitter stands in, the history saying so.
        actor = user or pcr.submitted_by
        who = ((user.get_full_name() or user.get_username()) if user is not None
               else "A script or task outside the app")
        with transaction.atomic():
            pcr.proposed_change_diff = new
            pcr.save(update_fields=['proposed_change_diff', 'updated_at'])
            withdrawn_here = 0
            requests = ApprovalRequest.objects.filter(  # tenant-safe: .objects auto-scopes
                content_type=ContentType.objects.get_for_model(ProcessChangeRequest),
                object_id=str(pcr.id), status='PENDING', archived=False)
            for request in requests:
                for response in request.responses.filter(decision=ApprovalDecision.APPROVED):
                    RecordEdit.objects.create(
                        tenant=response.tenant,
                        content_type=ContentType.objects.get_for_model(type(response)),
                        object_id=response.id, field_name='decision',
                        old_value=ApprovalDecision.APPROVED, new_value=ApprovalDecision.WITHDRAWN,
                        edited_by=actor,
                        reason=f"{pcr.artifact_number}'s draft was edited by {who} after this "
                               f"approval; it must be approved again on the changes as they stand.")
                    response.decision = ApprovalDecision.WITHDRAWN
                    response.save(update_fields=['decision'])
                    withdrawn_here += 1
                try:
                    request.notify_approvers()
                except Exception:  # noqa: BLE001 - the refresh stands whatever the notice does
                    logger.exception("draft refresh: could not notify approvers of %s",
                                     request.approval_number)
            # The change's history (shown on its page): who edited, and what it undid.
            RecordEdit.objects.create(
                tenant=pcr.tenant, content_type=ContentType.objects.get_for_model(ProcessChangeRequest),
                object_id=pcr.id, field_name='proposed_change_diff', old_value='(as reviewed)',
                new_value='(refreshed)', edited_by=actor,
                reason=(f"{who} edited the draft; "
                        + (f"{withdrawn_here} approval{'s' if withdrawn_here != 1 else ''} withdrawn."
                           if withdrawn_here else "no approvals had been given.")))
            withdrawn += withdrawn_here
    return withdrawn
