"""
SPCBaseline freeze service.

SPCBaseline uses a domain-specific supersession mechanism
(superseded_by / superseded_at / status) — NOT SecureModel's create_new_version.
The freeze operation creates a new ACTIVE baseline row; the model's save()
automatically marks any existing ACTIVE baseline for the same
measurement_definition as SUPERSEDED.

Public API
----------
freeze_spc_baseline(validated_data, *, user) -> SPCBaseline
"""
from __future__ import annotations

from Tracker.models.spc import SPCBaseline, BaselineStatus


def freeze_spc_baseline(validated_data: dict, *, user) -> SPCBaseline:
    """Create and persist a frozen SPC baseline from pre-validated data.

    *validated_data* is the dict produced by SPCBaselineFreezeSerializer after
    successful validation.  *user* is the request user who is freezing the
    baseline.

    The model's save() hook supersedes any existing ACTIVE baseline for the
    same measurement_definition in the same atomic write.

    Returns the newly created SPCBaseline instance.
    """
    from django.db import transaction
    reason = validated_data["freeze_reason"].strip()
    with transaction.atomic():
        replaced = list(SPCBaseline.objects.filter(  # tenant-safe: .objects auto-scopes
            measurement_definition_id=validated_data["measurement_definition_id"],
            status=BaselineStatus.ACTIVE).values_list('id', flat=True))
        baseline = _create_baseline(validated_data, user=user, reason=reason)
        # The baseline it replaced says why, and which one replaced it.
        SPCBaseline.objects.filter(id__in=replaced).update(  # tenant-safe: ids from the scoped query
            superseded_by=baseline, superseded_reason=f"Replaced by a new baseline: {reason}")
    return baseline


def supersede_spc_baseline(baseline: SPCBaseline, *, reason: str) -> SPCBaseline:
    """Unfreeze a baseline: the chart goes back to calculating its limits. The reason is
    required and kept on the baseline (user decision 2026-10-28).

    Raises:
        ValueError: no reason, or the baseline is already superseded.
    """
    from django.utils import timezone
    reason = (reason or '').strip()
    if not reason:
        raise ValueError("Say why the limits are being unfrozen.")
    if baseline.status == BaselineStatus.SUPERSEDED:
        raise ValueError("Baseline is already superseded")
    baseline.status = BaselineStatus.SUPERSEDED
    baseline.superseded_at = timezone.now()
    baseline.superseded_reason = reason
    baseline.save(update_fields=['status', 'superseded_at', 'superseded_reason', 'updated_at'])
    return baseline


def _create_baseline(validated_data: dict, *, user, reason: str) -> SPCBaseline:
    return SPCBaseline.objects.create(
        measurement_definition_id=validated_data["measurement_definition_id"],
        chart_type=validated_data["chart_type"],
        subgroup_size=validated_data["subgroup_size"],
        # X-bar limits
        xbar_ucl=validated_data.get("xbar_ucl"),
        xbar_cl=validated_data.get("xbar_cl"),
        xbar_lcl=validated_data.get("xbar_lcl"),
        range_ucl=validated_data.get("range_ucl"),
        range_cl=validated_data.get("range_cl"),
        range_lcl=validated_data.get("range_lcl"),
        # I-MR limits
        individual_ucl=validated_data.get("individual_ucl"),
        individual_cl=validated_data.get("individual_cl"),
        individual_lcl=validated_data.get("individual_lcl"),
        mr_ucl=validated_data.get("mr_ucl"),
        mr_cl=validated_data.get("mr_cl"),
        # Metadata
        sample_count=validated_data.get("sample_count", 0),
        notes=validated_data.get("notes", ""),
        # Tracking
        frozen_by=user,
        freeze_reason=reason,
        status=BaselineStatus.ACTIVE,
    )
