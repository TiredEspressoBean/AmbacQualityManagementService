"""
Serializers for Change Control artifacts (PCR / PCO / PCN).

Phase 1 covers process-change artifacts. Document-change serializers
arrive in Phase 2 reusing the same shape.
"""
from __future__ import annotations

from rest_framework import serializers

from Tracker.models import (
    ProcessChangeNotice,
    ProcessChangeOrder,
    ProcessChangeRequest,
)
from Tracker.serializers.core import SecureModelMixin


# ---------------------------------------------------------------------------
# Process Change Request
# ---------------------------------------------------------------------------

class ProcessChangeRequestSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Read/write serializer for PCRs.

    Most fields are read-only after creation; lifecycle transitions go
    through @action endpoints on the viewset rather than PATCH.
    """

    target_process_name = serializers.CharField(
        source='target_process.name',
        read_only=True,
    )
    created_by_username = serializers.CharField(
        source='created_by.username',
        read_only=True,
        default=None,
        allow_null=True,
    )
    submitted_by_username = serializers.CharField(
        source='submitted_by.username',
        read_only=True,
        default=None,
        allow_null=True,
    )
    is_open = serializers.BooleanField(read_only=True)
    affected_workorders_count = serializers.SerializerMethodField()

    # Order shortcut: surface the FK to the downstream PCO if it exists
    order_id = serializers.PrimaryKeyRelatedField(
        source='order',
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = ProcessChangeRequest
        fields = [
            'id',
            'tenant',
            'artifact_number',
            'status',
            'priority',
            'title',
            'proposed_change',
            'justification',
            'risk_analysis',
            'target_process',
            'target_process_name',
            'baseline_version_id',
            'affected_workorders_snapshot',
            'affected_workorders_count',
            'customer_notification_required',
            'rejected_reason',
            'submitted_at',
            'submitted_by',
            'submitted_by_username',
            'created_at',
            'created_by',
            'created_by_username',
            'updated_at',
            'is_open',
            'order_id',
            'data_origin',
            'draft_process_version',
            'proposed_change_diff',
        ]
        read_only_fields = [
            'id',
            'tenant',
            'artifact_number',
            'status',
            'baseline_version_id',
            'affected_workorders_snapshot',
            'rejected_reason',
            'submitted_at',
            'submitted_by',
            'created_at',
            'created_by',
            'updated_at',
            'data_origin',
        ]

    def get_affected_workorders_count(self, obj) -> int:
        return len(obj.affected_workorders_snapshot or [])


# ---------------------------------------------------------------------------
# Process Change Order
# ---------------------------------------------------------------------------

class ProcessChangeOrderSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Read/write serializer for PCOs.

    Implementation actions (author, approve, implement, cancel) flow
    through @action endpoints. PATCH is limited to authoring fields
    while in DRAFT status.
    """

    request_artifact_number = serializers.CharField(
        source='request.artifact_number',
        read_only=True,
    )
    request_title = serializers.CharField(
        source='request.title',
        read_only=True,
    )
    target_process_name = serializers.CharField(
        source='request.target_process.name',
        read_only=True,
    )
    draft_process_version_id = serializers.PrimaryKeyRelatedField(
        source='draft_process_version',
        read_only=True,
    )
    approved_by_username = serializers.CharField(
        source='approved_by.username',
        read_only=True,
        default=None,
        allow_null=True,
    )
    implemented_by_username = serializers.CharField(
        source='implemented_by.username',
        read_only=True,
        default=None,
        allow_null=True,
    )
    is_open = serializers.BooleanField(read_only=True)
    notice_id = serializers.PrimaryKeyRelatedField(
        source='notice',
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = ProcessChangeOrder
        fields = [
            'id',
            'tenant',
            'artifact_number',
            'status',
            'request',
            'request_artifact_number',
            'request_title',
            'target_process_name',
            'draft_process_version_id',
            'implementation_plan',
            'effective_date',
            'migration_disposition',
            'migration_reason',
            'migrated_workorder_ids',
            'approved_at',
            'approved_by',
            'approved_by_username',
            'implemented_at',
            'implemented_by',
            'implemented_by_username',
            'created_at',
            'created_by',
            'updated_at',
            'is_open',
            'notice_id',
            'data_origin',
        ]
        read_only_fields = [
            'id',
            'tenant',
            'artifact_number',
            'status',
            'request',
            'migrated_workorder_ids',
            'approved_at',
            'approved_by',
            'implemented_at',
            'implemented_by',
            'created_at',
            'created_by',
            'updated_at',
            'data_origin',
        ]


# ---------------------------------------------------------------------------
# Process Change Notice
# ---------------------------------------------------------------------------

class ProcessChangeNoticeSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Read/write serializer for PCNs."""

    order_artifact_number = serializers.CharField(
        source='order.artifact_number',
        read_only=True,
    )
    pcr_artifact_number = serializers.CharField(
        source='order.request.artifact_number',
        read_only=True,
    )
    target_process_name = serializers.CharField(
        source='order.request.target_process.name',
        read_only=True,
    )
    released_by_username = serializers.CharField(
        source='released_by.username',
        read_only=True,
        default=None,
        allow_null=True,
    )
    closed_by_username = serializers.CharField(
        source='closed_by.username',
        read_only=True,
        default=None,
        allow_null=True,
    )
    is_open = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProcessChangeNotice
        fields = [
            'id',
            'tenant',
            'artifact_number',
            'status',
            'order',
            'order_artifact_number',
            'pcr_artifact_number',
            'target_process_name',
            'notice_content',
            'released_at',
            'released_by',
            'released_by_username',
            'closure_evidence',
            'closed_at',
            'closed_by',
            'closed_by_username',
            'created_at',
            'created_by',
            'updated_at',
            'is_open',
            'data_origin',
        ]
        read_only_fields = [
            'id',
            'tenant',
            'artifact_number',
            'status',
            'order',
            'released_at',
            'released_by',
            'closed_at',
            'closed_by',
            'created_at',
            'created_by',
            'updated_at',
            'data_origin',
        ]


# ---------------------------------------------------------------------------
# Action payloads — used by viewset @action endpoints
# ---------------------------------------------------------------------------

class PcrRejectPayloadSerializer(serializers.Serializer):
    reason = serializers.CharField()


class PcrCancelPayloadSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default='')


class PcoAuthorPayloadSerializer(serializers.Serializer):
    implementation_plan = serializers.CharField(required=False, allow_blank=True)
    effective_date = serializers.DateField(required=False, allow_null=True)


class PcoImplementPayloadSerializer(serializers.Serializer):
    migration_disposition = serializers.ChoiceField(
        choices=['MIGRATE_ALL', 'MIGRATE_SELECTED', 'KEEP_ALL'],
    )
    migration_reason = serializers.CharField(required=False, allow_blank=True, default='')
    selected_workorder_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
    )


class PcoCancelPayloadSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default='')


class PcnClosePayloadSerializer(serializers.Serializer):
    closure_evidence = serializers.CharField()
