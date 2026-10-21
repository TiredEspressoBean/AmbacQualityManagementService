"""
Serializers for Change Control artifacts (PCR / PCO / PCN).

Phase 1 covers process-change artifacts. Document-change serializers
arrive in Phase 2 reusing the same shape.
"""
from __future__ import annotations

from drf_spectacular.utils import extend_schema_field
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

class TemporaryWorkOrderSerializer(serializers.Serializer):
    id = serializers.CharField()
    erp_id = serializers.CharField()
    status = serializers.CharField()
    # The version this WO runs underneath the deviation (where moving back returns it).
    base_version = serializers.IntegerField(allow_null=True)


class TemporaryChangeInfoSerializer(serializers.Serializer):
    version_id = serializers.CharField()
    version = serializers.IntegerField()
    until = serializers.DateField(allow_null=True)
    expired = serializers.BooleanField()
    work_orders = TemporaryWorkOrderSerializer(many=True)


class ProcessChangeRequestSerializer(SecureModelMixin):
    """Read/write serializer for PCRs.

    Most fields are read-only after creation; lifecycle transitions go
    through @action endpoints on the viewset rather than PATCH.
    """

    target_process_name = serializers.CharField(
        source='target_process.name',
        read_only=True,
    )
    # The *_by_username fields carry no `default=`: with one, DRF raises SkipField
    # on a partial (PATCH) serialisation and the key vanishes from the response,
    # which the generated client rejects as `undefined`. Without it, a null FK
    # serialises as None via `allow_null` on every write.
    created_by_username = serializers.CharField(
        source='created_by.username',
        read_only=True,
        allow_null=True,
    )
    submitted_by_username = serializers.CharField(
        source='submitted_by.username',
        read_only=True,
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
    extends_request_number = serializers.CharField(
        source='extends_request.artifact_number', read_only=True, allow_null=True)
    temporary_info = serializers.SerializerMethodField()

    @extend_schema_field(TemporaryChangeInfoSerializer(allow_null=True))
    def get_temporary_info(self, obj):
        """For an implemented temporary change: its version, end date, and the work
        orders on it. Null for anything else."""
        from Tracker.models import WorkOrder
        from Tracker.services.change_control.temporary import temporary_versions_of
        from Tracker.services.core.clock import tenant_today
        if not obj.is_temporary or obj.extends_request_id is not None:
            return None
        versions = temporary_versions_of(obj)
        if not versions:
            return None
        version = versions[0]
        # Every version it's in force on: each work order's base version says where it
        # goes back to.
        work_orders = (WorkOrder.objects.filter(process__in=versions)  # tenant-safe: .objects auto-scopes
                       .select_related('process__previous_version').order_by('ERP_id'))
        return {
            'version_id': str(version.id),
            'version': version.version,
            'until': version.temporary_until,
            'expired': bool(version.temporary_until
                            and version.temporary_until < tenant_today(obj.tenant_id)),
            'work_orders': [{'id': str(w.id), 'erp_id': w.ERP_id, 'status': w.workorder_status,
                             'base_version': (w.process.previous_version.version
                                              if w.process.previous_version_id else None)}
                            for w in work_orders],
        }

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
            'is_temporary',
            'temporary_until',
            'extends_request',
            'extends_request_number',
            'customer_agreement',
            'temporary_info',
        ]
        read_only_fields = [
            'extends_request',
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

class ProcessChangeOrderSerializer(SecureModelMixin):
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
    # A temporary change implements onto named work orders only; an extension moves a
    # temporary change's end date and migrates nothing. The implement dialog reads these.
    request_is_temporary = serializers.BooleanField(source='request.is_temporary', read_only=True)
    request_is_extension = serializers.SerializerMethodField()
    request_temporary_until = serializers.DateField(
        source='request.temporary_until', read_only=True, allow_null=True)

    @extend_schema_field(serializers.BooleanField())
    def get_request_is_extension(self, obj):
        return obj.request.extends_request_id is not None

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
        allow_null=True,
    )
    implemented_by_username = serializers.CharField(
        source='implemented_by.username',
        read_only=True,
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
            'request_is_temporary',
            'request_is_extension',
            'request_temporary_until',
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

class ProcessChangeNoticeSerializer(SecureModelMixin):
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
        allow_null=True,
    )
    closed_by_username = serializers.CharField(
        source='closed_by.username',
        read_only=True,
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
    # {str(part_id): {"action": "RELOCATE"|"HOLD"|"SCRAP", "target_step_id": <id>}}
    # for parts stranded at a step removed in the new version. See
    # services/change_control/part_remap.py.
    stranded_resolutions = serializers.JSONField(required=False, default=dict)


class PcoCancelPayloadSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default='')


class PcnClosePayloadSerializer(serializers.Serializer):
    closure_evidence = serializers.CharField()
