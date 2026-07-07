"""
Supplier qualification / ASL lifecycle + scope resolution.

A `SupplierQualification` says a supplier is approved for a scope (part type,
commodity, or special process) with a status and expiry. The ASL is the set of
active, in-date APPROVED/CONDITIONAL records — resolved here, not stored.

Lifecycle transitions live here (not in `save()`): open -> grant/submit ->
suspend / disqualify / expire. The grant can ride the approval engine
(`submit_for_approval`), or be applied directly by an authorized user (`grant`).
"""
from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from Tracker.models import SupplierQualification


@dataclass(frozen=True)
class QualificationStatus:
    """Resolved standing of a supplier for a scope."""
    qualified: bool
    status: str | None
    basis: str | None
    expiry_date: object | None          # datetime.date | None
    days_to_expiry: int | None
    record_id: str | None


# ---------------------------------------------------------------------------
# Resolution (the ASL query)
# ---------------------------------------------------------------------------

def _active_qs(supplier):
    today = timezone.now().date()
    return (
        SupplierQualification.objects
        .filter(supplier=supplier, status__in=SupplierQualification.ACTIVE_STATUSES)
        .filter(Q(effective_date__isnull=True) | Q(effective_date__lte=today))
        .filter(Q(expiry_date__isnull=True) | Q(expiry_date__gte=today))
        .order_by('-effective_date', '-created_at')
    )


def qualifying_record_for(*, supplier, part_type=None, commodity=None, special_process=None):
    """Return the active qualification covering the requested scope, or None.

    Match order: PART_TYPE scope by FK; COMMODITY / SPECIAL_PROCESS by
    case-insensitive scope_label. If no scope is given, any active record
    qualifies the supplier broadly.
    """
    if supplier is None:
        return None
    qs = _active_qs(supplier)

    if part_type is not None:
        return qs.filter(
            scope_type=SupplierQualification.SCOPE_PART_TYPE, part_type=part_type
        ).first()
    if commodity:
        return qs.filter(
            scope_type=SupplierQualification.SCOPE_COMMODITY, scope_label__iexact=commodity
        ).first()
    if special_process:
        return qs.filter(
            scope_type=SupplierQualification.SCOPE_SPECIAL_PROCESS, scope_label__iexact=special_process
        ).first()
    return qs.first()


def is_supplier_qualified(*, supplier, part_type=None, commodity=None, special_process=None) -> bool:
    return qualifying_record_for(
        supplier=supplier, part_type=part_type, commodity=commodity, special_process=special_process
    ) is not None


def resolve_status(*, supplier, part_type=None, commodity=None, special_process=None) -> QualificationStatus:
    record = qualifying_record_for(
        supplier=supplier, part_type=part_type, commodity=commodity, special_process=special_process
    )
    if record is None:
        return QualificationStatus(False, None, None, None, None, None)
    days = None
    if record.expiry_date:
        days = (record.expiry_date - timezone.now().date()).days
    return QualificationStatus(
        qualified=True, status=record.status, basis=record.basis or None,
        expiry_date=record.expiry_date, days_to_expiry=days, record_id=str(record.id),
    )


# ---------------------------------------------------------------------------
# Lifecycle transitions
# ---------------------------------------------------------------------------

def open_qualification(*, supplier, scope_type=SupplierQualification.SCOPE_PART_TYPE,
                       part_type=None, scope_label='', basis='', user=None, notes='') -> SupplierQualification:
    """Create a PENDING qualification record."""
    if scope_type == SupplierQualification.SCOPE_PART_TYPE and part_type is None:
        raise ValueError("PART_TYPE scope requires a part_type.")
    if scope_type != SupplierQualification.SCOPE_PART_TYPE and not scope_label:
        raise ValueError(f"{scope_type} scope requires a scope_label.")
    return SupplierQualification.objects.create(
        supplier=supplier, scope_type=scope_type, part_type=part_type,
        scope_label=scope_label, basis=basis, notes=notes,
        qualified_by=user if (user and getattr(user, 'is_authenticated', False)) else None,
    )


def grant(qualification, *, user=None, conditional=False, effective_date=None, expiry_date=None):
    """Directly grant a qualification (-> APPROVED, or CONDITIONAL). Used after an
    approval completes, or by an authorized user. Idempotent on the target status."""
    if qualification.status == 'DISQUALIFIED':
        raise ValueError("A disqualified supplier must be re-opened, not granted.")
    qualification.status = 'CONDITIONAL' if conditional else 'APPROVED'
    qualification.effective_date = effective_date or qualification.effective_date or timezone.now().date()
    if expiry_date is not None:
        qualification.expiry_date = expiry_date
    if user and getattr(user, 'is_authenticated', False):
        qualification.qualified_by = user
    qualification.save(update_fields=['status', 'effective_date', 'expiry_date', 'qualified_by', 'updated_at'])
    return qualification


def submit_for_approval(qualification, *, template, user):
    """Route the grant through the approval engine. Status stays PENDING until the
    approval completes (completion -> call `grant`)."""
    from Tracker.services.core.approval import create_approval_from_template

    with transaction.atomic():
        approval = create_approval_from_template(
            content_object=qualification, template=template, requested_by=user,
            reason=f"Qualify {qualification.supplier.name} for {qualification.scope_display}.",
        )
        qualification.approval_request = approval
        qualification.save(update_fields=['approval_request', 'updated_at'])
    return approval


def suspend(qualification, *, user=None, reason=''):
    qualification.status = 'SUSPENDED'
    if reason:
        qualification.notes = (qualification.notes + f"\n[SUSPENDED] {reason}").strip()
    qualification.save(update_fields=['status', 'notes', 'updated_at'])
    return qualification


def disqualify(qualification, *, user=None, reason=''):
    qualification.status = 'DISQUALIFIED'
    if reason:
        qualification.notes = (qualification.notes + f"\n[DISQUALIFIED] {reason}").strip()
    qualification.save(update_fields=['status', 'notes', 'updated_at'])
    return qualification


def expire(qualification):
    qualification.status = 'EXPIRED'
    qualification.save(update_fields=['status', 'updated_at'])
    _emit_qualification_expired(qualification)
    return qualification


# Reminder marks (days before expiry), tightest first — a qualification fires the
# 60-day reminder, then the 30-day reminder, each exactly once.
_EXPIRY_REMINDER_DAYS = (30, 60)


def notify_expiring_soon(qualification) -> bool:
    """Emit `supplier.qualification_expiring_soon` when the qualification is inside
    a reminder window (<= 30 or <= 60 days out). Idempotent per (qualification,
    window) so each threshold notifies once, not daily. Returns True if emitted."""
    if qualification.expiry_date is None:
        return False
    days = (qualification.expiry_date - timezone.now().date()).days
    window = next((d for d in _EXPIRY_REMINDER_DAYS if days <= d), None)
    if window is None:
        return False
    _emit_expiring_soon(qualification, days_to_expiry=days, window=window)
    return True


def _emit_expiring_soon(qualification, *, days_to_expiry: int, window: int) -> None:
    from Tracker.services.core.notifications import emit
    from Tracker.services.qms.events import SupplierQualificationExpiringSoonPayload

    supplier = qualification.supplier
    payload = SupplierQualificationExpiringSoonPayload(
        id=str(qualification.id),
        tenant_id=str(qualification.tenant_id) if qualification.tenant_id else "",
        qualification_id=str(qualification.id),
        qualification_number=qualification.qualification_number or "",
        supplier_id=str(supplier.id),
        supplier_name=supplier.name,
        scope=qualification.scope_display,
        expiry_date=qualification.expiry_date.isoformat(),
        days_to_expiry=days_to_expiry,
        reminder_window=window,
    )
    emit(
        "supplier.qualification_expiring_soon",
        tenant=qualification.tenant,
        payload=payload,
        correlation_id=f"supplier_qualification:{qualification.id}",
        # One reminder per window (60, then 30) — keyed by window so it doesn't repeat daily.
        idempotency_key=f"supplier.qualification_expiring_soon:{qualification.id}:{window}",
    )


def _emit_qualification_expired(qualification) -> None:
    """Notify (notification-rule eligible) that a qualification expired — the
    supplier is now off the ASL for this scope."""
    from Tracker.services.core.notifications import emit
    from Tracker.services.qms.events import SupplierQualificationExpiredPayload

    supplier = qualification.supplier
    payload = SupplierQualificationExpiredPayload(
        id=str(qualification.id),
        tenant_id=str(qualification.tenant_id) if qualification.tenant_id else "",
        qualification_id=str(qualification.id),
        qualification_number=qualification.qualification_number or "",
        supplier_id=str(supplier.id),
        supplier_name=supplier.name,
        scope=qualification.scope_display,
        expiry_date=qualification.expiry_date.isoformat() if qualification.expiry_date else "",
    )
    emit(
        "supplier.qualification_expired",
        tenant=qualification.tenant,
        payload=payload,
        correlation_id=f"supplier_qualification:{qualification.id}",
        # One notification per qualification expiry (status only flips to EXPIRED once).
        idempotency_key=f"supplier.qualification_expired:{qualification.id}",
    )
