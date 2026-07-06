"""
Part-approval lifecycle + resolution.

A `PartApproval` says a `(part_type, supplier)` is approved for production via
PPAP (auto/IATF) or FAI / AS9102 (aero), with a status and expiry. The receiving
gate checks for an active, in-date APPROVED/CONDITIONAL record — resolved here,
not stored.

Lifecycle transitions live here (not in `save()`): open -> grant/submit ->
suspend / disqualify / expire. The grant can ride the approval engine
(`submit_for_approval`), or be applied directly by an authorized user (`grant`).

Simpler than supplier qualification: there is no scope-type union — the scope is
always the `(part_type, supplier)` pair.
"""
from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from Tracker.models import PartApproval


@dataclass(frozen=True)
class PartApprovalStatus:
    """Resolved standing of a (part_type, supplier) pair."""
    approved: bool
    status: str | None
    approval_type: str | None
    expiry_date: object | None          # datetime.date | None
    days_to_expiry: int | None
    record_id: str | None


# ---------------------------------------------------------------------------
# Resolution (the approval query)
# ---------------------------------------------------------------------------

def _active_qs(part_type, supplier):
    from django.db.models import Q
    today = timezone.now().date()
    return (
        PartApproval.objects
        .filter(part_type=part_type, supplier=supplier,
                status__in=PartApproval.ACTIVE_STATUSES)
        .filter(Q(effective_date__isnull=True) | Q(effective_date__lte=today))
        .filter(Q(expiry_date__isnull=True) | Q(expiry_date__gte=today))
        .order_by('-effective_date', '-created_at')
    )


def approving_record_for(*, part_type, supplier):
    """Return the active part approval covering (part_type, supplier), or None."""
    if part_type is None or supplier is None:
        return None
    return _active_qs(part_type, supplier).first()


def is_part_approved(*, part_type, supplier) -> bool:
    return approving_record_for(part_type=part_type, supplier=supplier) is not None


def resolve_status(*, part_type, supplier) -> PartApprovalStatus:
    record = approving_record_for(part_type=part_type, supplier=supplier)
    if record is None:
        return PartApprovalStatus(False, None, None, None, None, None)
    days = None
    if record.expiry_date:
        days = (record.expiry_date - timezone.now().date()).days
    return PartApprovalStatus(
        approved=True, status=record.status, approval_type=record.approval_type,
        expiry_date=record.expiry_date, days_to_expiry=days, record_id=str(record.id),
    )


# ---------------------------------------------------------------------------
# Lifecycle transitions
# ---------------------------------------------------------------------------

def open_approval(*, part_type, supplier, approval_type=PartApproval.APPROVAL_PPAP,
                  reference='', user=None, notes='') -> PartApproval:
    """Create a PENDING part-approval record."""
    if part_type is None:
        raise ValueError("A part approval requires a part_type.")
    if supplier is None:
        raise ValueError("A part approval requires a supplier.")
    return PartApproval.objects.create(
        part_type=part_type, supplier=supplier, approval_type=approval_type,
        reference=reference, notes=notes,
        approved_by=user if (user and getattr(user, 'is_authenticated', False)) else None,
    )


def grant(approval, *, user=None, conditional=False, effective_date=None, expiry_date=None):
    """Directly grant a part approval (-> APPROVED, or CONDITIONAL). Used after an
    approval completes, or by an authorized user. Idempotent on the target status."""
    if approval.status == 'DISQUALIFIED':
        raise ValueError("A disqualified part approval must be re-opened, not granted.")
    approval.status = 'CONDITIONAL' if conditional else 'APPROVED'
    approval.effective_date = effective_date or approval.effective_date or timezone.now().date()
    if expiry_date is not None:
        approval.expiry_date = expiry_date
    if user and getattr(user, 'is_authenticated', False):
        approval.approved_by = user
    approval.save(update_fields=['status', 'effective_date', 'expiry_date', 'approved_by', 'updated_at'])
    return approval


def submit_for_approval(approval, *, template, user):
    """Route the grant through the approval engine. Status stays PENDING until the
    approval completes (completion -> call `grant`)."""
    from Tracker.services.core.approval import create_approval_from_template

    with transaction.atomic():
        request = create_approval_from_template(
            content_object=approval, template=template, requested_by=user,
            reason=f"Approve {approval.part_type.name} from {approval.supplier.name}.",
        )
        approval.approval_request = request
        approval.save(update_fields=['approval_request', 'updated_at'])
    return request


def suspend(approval, *, user=None, reason=''):
    approval.status = 'SUSPENDED'
    if reason:
        approval.notes = (approval.notes + f"\n[SUSPENDED] {reason}").strip()
    approval.save(update_fields=['status', 'notes', 'updated_at'])
    return approval


def disqualify(approval, *, user=None, reason=''):
    approval.status = 'DISQUALIFIED'
    if reason:
        approval.notes = (approval.notes + f"\n[DISQUALIFIED] {reason}").strip()
    approval.save(update_fields=['status', 'notes', 'updated_at'])
    return approval


def expire(approval):
    approval.status = 'EXPIRED'
    approval.save(update_fields=['status', 'updated_at'])
    return approval
