"""
RCA aggregate services.

Business operations for RcaRecord (including its FiveWhys / Fishbone
children). Phase 3b extraction — the model method, the viewset action,
and the serializer create/update paths all funnel through here so the
aggregate write logic lives in one place.

The string→list conversion for fishbone cause fields is a serializer
concern (input shape) and stays in `RcaRecordSerializer`. Services
receive already-normalized lists.
"""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.utils import timezone

from Tracker.models import (
    Fishbone,
    FiveWhys,
    RcaMethod,
    RcaRecord,
    RootCauseVerificationStatus,
)


def verify_root_cause(rca: RcaRecord, user, verification_notes: str | None = None) -> RcaRecord:
    """Mark an RCA's root cause as verified.

    Self-verification (user is the conductor) is only allowed when the
    parent CAPA has `allow_self_verification=True` and the caller supplies
    at least 10 characters of justification.

    Raises:
        ValidationError: self-verification rules violated.
    """
    is_self_verification = (user == rca.conducted_by)
    if is_self_verification:
        if not rca.capa.allow_self_verification:
            raise ValidationError(
                "Self-verification of RCA is not permitted for this CAPA"
            )
        if not verification_notes or len(verification_notes.strip()) < 10:
            raise ValidationError(
                "Justification required for RCA self-verification (minimum 10 characters)"
            )

    rca.root_cause_verification_status = RootCauseVerificationStatus.VERIFIED
    rca.root_cause_verified_by = user
    rca.root_cause_verified_at = timezone.now()
    rca.self_verified = is_self_verification
    rca.save()
    return rca


def approve_rca(rca: RcaRecord, user) -> RcaRecord:
    """Approve an RCA record (reviewer sign-off).

    Distinct from `verify_root_cause`: this is the reviewer workflow
    exposed at the `approve` viewset action; no self-verification rules
    apply here because the reviewer is explicitly a different persona.
    Viewset-level permission gating (`review_rca`) stays at the viewset.
    """
    rca.root_cause_verification_status = RootCauseVerificationStatus.VERIFIED
    rca.root_cause_verified_by = user
    rca.root_cause_verified_at = timezone.now()
    rca.save(update_fields=[
        'root_cause_verification_status',
        'root_cause_verified_by',
        'root_cause_verified_at',
    ])
    return rca


def create_rca_record(
    data: dict,
    five_whys_data: dict | None = None,
    fishbone_data: dict | None = None,
) -> RcaRecord:
    """Create an RcaRecord plus its method-specific child aggregate.

    `data` is the RcaRecord field dict as already validated by the
    serializer. `five_whys_data` and `fishbone_data` should be normalized
    (fishbone causes as lists) — the serializer handles that shape.
    Only the child aggregate matching the record's `rca_method` is
    created; the other is ignored if supplied.
    """
    rca_record = RcaRecord.objects.create(**data)

    if five_whys_data and rca_record.rca_method == 'FIVE_WHYS':
        FiveWhys.objects.create(rca_record=rca_record, **five_whys_data)

    if fishbone_data and rca_record.rca_method == 'FISHBONE':
        Fishbone.objects.create(rca_record=rca_record, **fishbone_data)

    return rca_record


def update_rca_record(
    instance: RcaRecord,
    data: dict,
    five_whys_data: dict | None = None,
    fishbone_data: dict | None = None,
) -> RcaRecord:
    """Update an RcaRecord plus its method-specific child aggregate.

    Child aggregate is get-or-create'd: existing children have their
    fields assigned and are saved; missing children are created.
    """
    for field, value in data.items():
        setattr(instance, field, value)
    instance.save()

    if five_whys_data and instance.rca_method == 'FIVE_WHYS':
        try:
            five_whys = instance.five_whys
            for key, value in five_whys_data.items():
                setattr(five_whys, key, value)
            five_whys.save()
        except FiveWhys.DoesNotExist:
            FiveWhys.objects.create(rca_record=instance, **five_whys_data)

    if fishbone_data and instance.rca_method == 'FISHBONE':
        try:
            fishbone = instance.fishbone
            for key, value in fishbone_data.items():
                setattr(fishbone, key, value)
            fishbone.save()
        except Fishbone.DoesNotExist:
            Fishbone.objects.create(rca_record=instance, **fishbone_data)

    return instance


def validate_rca_completeness(rca: RcaRecord) -> tuple[bool, list[str]]:
    """Check whether an RCA has enough content to be considered complete.

    Checks the parent record's required fields and the method-specific
    child aggregate (FiveWhys or Fishbone) for minimum coverage.

    Returns (is_complete, issues). `issues` is empty iff is_complete.
    """
    issues: list[str] = []

    if not rca.problem_description:
        issues.append("Problem description is required")
    if not rca.root_cause_summary:
        issues.append("Root cause summary is required")
    if not rca.conducted_by or not rca.conducted_date:
        issues.append("Conductor and date are required")

    if rca.rca_method == RcaMethod.FIVE_WHYS and hasattr(rca, 'five_whys'):
        whys_answered = sum([
            bool(rca.five_whys.why_1_answer),
            bool(rca.five_whys.why_2_answer),
            bool(rca.five_whys.why_3_answer),
        ])
        if whys_answered < 3:
            issues.append("At least 3 'why' levels must be answered")

    if rca.rca_method == RcaMethod.FISHBONE and hasattr(rca, 'fishbone'):
        categories_filled = sum([
            bool(rca.fishbone.man_causes),
            bool(rca.fishbone.machine_causes),
            bool(rca.fishbone.material_causes),
            bool(rca.fishbone.method_causes),
            bool(rca.fishbone.measurement_causes),
            bool(rca.fishbone.environment_causes),
        ])
        if categories_filled < 3:
            issues.append("At least 3 fishbone categories must have causes")

    return (len(issues) == 0, issues)
