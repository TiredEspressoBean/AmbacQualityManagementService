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
        status=BaselineStatus.ACTIVE,
    )
