# serializers/dwi.py - Digital Work Instructions Serializers
"""
Serializers for the DWI subsystem.

Phase 1-3 models:
- Substep — the unit of work instruction within a Step
- SubstepCompletion — per-execution completion record
- SubstepResource — equipment / material / PPE references
- SubstepTranslation — localization rows
- SubstepGateCompletion — inline attestation / signature gate records
- SubstepResponse — per-node operator captures (text/choice/photo/etc.)

`body_blocks` is a TipTap document JSON blob — the editor produces it and
the server stores it verbatim. Per architectural decision #18, `node_id`
attributes inside the JSON are UUIDv7 minted client-side. The server
enforces that contract on write (`SubstepSerializer.validate_body_blocks`):
every `node_id` present must be a valid UUID and unique within the document.
That uniqueness is load-bearing — per-node operator captures
(`SubstepResponse` / `SubstepGateCompletion`) are keyed by
`(step_execution, substep, node_id)`, so two nodes sharing an id would
collide and silently drop a capture.
"""
import uuid

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from Tracker.models import (
    Substep,
    SubstepCompletion,
    SubstepResource,
    SubstepTranslation,
    SubstepGateCompletion,
    SubstepResponse,
)
from .core import SecureModelMixin


class SubstepSerializer(SecureModelMixin):
    """Substep — the unit of work instruction within a Step.

    The `body_blocks` field is a TipTap document JSON: `{type: 'doc',
    content: [...]}`. Frontend uses the type at
    `ambac-tracker-ui/src/types/dwi.ts` (DwiDocument).
    """

    step_name = serializers.CharField(source='step.name', read_only=True, allow_null=True)
    # Surfaced so the authoring UI can flip to read-only when the parent
    # Process(es) are no longer DRAFT. Backend writes are blocked separately
    # in the viewset; this is the UI hint.
    is_editable = serializers.BooleanField(read_only=True)

    class Meta:
        model = Substep
        fields = (
            'id',
            'step', 'step_name',
            'order',
            'title',
            'body_blocks',
            'is_optional',
            'is_critical',
            'allow_not_applicable',
            'requires_signature',
            'is_inspection_point',
            'expected_duration',
            'scope',
            'sampling_rule',
            'source_library_substep_id',
            'source_library_version',
            'is_editable',
            'created_at', 'updated_at', 'archived',
        )
        read_only_fields = ('created_at', 'updated_at', 'is_editable')

    def validate_body_blocks(self, value):
        """Enforce decision #18: every `node_id` in the TipTap doc is a valid
        UUID and unique within the document.

        Only capture nodes declare a `node_id` attr, so its presence marks a
        node whose id keys per-execution rows (`SubstepResponse` /
        `SubstepGateCompletion`, unique on `(step_execution, substep,
        node_id)`). A duplicate or malformed id would corrupt or drop a
        capture, so reject it at the authoring boundary.
        """
        seen = set()
        errors = []

        def walk(node):
            if not isinstance(node, dict):
                return
            attrs = node.get('attrs') or {}
            if 'node_id' in attrs:
                node_id = attrs['node_id']
                try:
                    uuid.UUID(str(node_id))
                except (ValueError, AttributeError, TypeError):
                    errors.append(
                        f"node '{node.get('type', '?')}' has an invalid "
                        f"node_id {node_id!r} (must be a UUID)."
                    )
                else:
                    if node_id in seen:
                        errors.append(f"duplicate node_id {node_id!r} in document.")
                    seen.add(node_id)
            for child in node.get('content') or []:
                walk(child)

        # body_blocks is a doc dict `{type:'doc', content:[...]}`; the model
        # default is `[]` (empty / not-yet-authored).
        if isinstance(value, dict):
            walk(value)
        elif isinstance(value, list):
            for node in value:
                walk(node)

        if errors:
            raise serializers.ValidationError(errors)
        return value

    def validate(self, attrs):
        """FPI ⊕ batch mutual exclusion (Decision #12): a first-piece-inspection
        step can't carry BATCH-scope substeps. FPI means "inspect the first piece,
        then run the rest"; a BATCH substep runs the whole lot at once — the two
        are incompatible. Guarded here at the authoring boundary.
        """
        scope = attrs.get('scope')
        if scope is None and self.instance is not None:
            scope = self.instance.scope
        step = attrs.get('step') or (self.instance.step if self.instance else None)
        if scope == 'batch' and step is not None and step.requires_first_piece_inspection:
            raise serializers.ValidationError({
                'scope': "Cannot set BATCH scope on a substep of a first-piece-inspection "
                         "step - FPI and batch are mutually exclusive.",
            })
        return attrs

    def update(self, instance, validated_data):
        """When editing from a PCR DRAFT process (`?process=<uuid>`),
        version the parent Step first so the substep change is isolated
        to that draft. Substeps from `create_new_step_version` carry
        their `identity_id` forward, so we look up the cloned substep
        on the new Step row by identity and apply the update there.

        Without `?process=`, falls back to in-place update for legacy
        substep editors that don't supply context. That path still
        leaks substep changes across all Process versions referencing
        the same parent Step — to fix, callers must supply process.
        """
        process = self._resolve_editing_process()
        if process is None:
            return super().update(instance, validated_data)

        # Check: is the parent Step the canonical version for this
        # process's ProcessStep junction? If not, abort — caller is
        # editing a stale Step row.
        from Tracker.models import ProcessStep
        # tenant-safe: SecureManager auto-scopes the lookup.
        ps = ProcessStep.objects.filter(process=process, step=instance.step).first()
        if ps is None:
            # The substep's parent Step isn't part of this process —
            # fall back to plain update. This shouldn't normally happen.
            return super().update(instance, validated_data)

        # Fork the parent Step into a per-process version. The Step
        # service copies substeps too — find the cloned substep with
        # the same identity_id on the new Step and apply the update to
        # that row.
        from Tracker.services.mes.steps import create_new_step_version
        new_step = create_new_step_version(
            instance.step,
            user=self.context['request'].user if 'request' in self.context else None,
            change_description=(
                f"Substep edit '{instance.title}' on {process.name} "
                f"v{process.version}"
            ),
            process=process,
        )
        # tenant-safe: filtered by identity_id, tenant-scoped via FK chain.
        cloned = Substep.objects.filter(
            step=new_step, identity_id=instance.identity_id,
        ).first()
        if cloned is None:
            # Substep wasn't on the new Step (newly added during the
            # fork itself, or copy gap). Fall back to plain update.
            return super().update(instance, validated_data)
        return super().update(cloned, validated_data)

    def _resolve_editing_process(self):
        """Read `?process=<uuid>` from the request, return the matching
        Process row in the caller's tenant. None when absent or invalid.
        """
        request = self.context.get('request')
        if request is None:
            return None
        process_id = request.query_params.get('process')
        if not process_id:
            return None
        from Tracker.models import Processes
        try:
            # tenant-safe: SecureManager auto-scopes via ContextVar.
            return Processes.objects.get(id=process_id)
        except Processes.DoesNotExist:
            return None


class SubstepResourceSerializer(SecureModelMixin):
    """Equipment / material / PPE references attached to a substep."""

    equipment_type_name = serializers.CharField(
        source='equipment_type.name', read_only=True, allow_null=True,
    )

    class Meta:
        model = SubstepResource
        fields = (
            'id',
            'substep',
            'equipment_type', 'equipment_type_name',
            'quantity', 'notes', 'required',
            'created_at', 'updated_at', 'archived',
        )
        read_only_fields = ('created_at', 'updated_at')


class SubstepTranslationSerializer(SecureModelMixin):
    """Localized title + body for a substep."""

    class Meta:
        model = SubstepTranslation
        fields = (
            'id',
            'substep',
            'language', 'title', 'body_blocks',
            'created_at', 'updated_at', 'archived',
        )
        read_only_fields = ('created_at', 'updated_at')


class SubstepCompletionSerializer(SecureModelMixin):
    """Per-execution completion record."""

    substep_title = serializers.CharField(source='substep.title', read_only=True, allow_null=True)
    completed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = SubstepCompletion
        fields = (
            'id',
            'step_execution',
            'substep', 'substep_title',
            'completed_by', 'completed_by_name',
            'completed_at',
            'marked_not_applicable',
            'notes',
            'signature_data', 'signature_meaning',
            'verified_at', 'verification_method',
            'ip_address',
            'created_at', 'updated_at',
        )
        read_only_fields = ('completed_at', 'created_at', 'updated_at')

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_completed_by_name(self, obj) -> str | None:
        if obj.completed_by:
            return obj.completed_by.get_full_name() or obj.completed_by.username
        return None


class SubstepGateCompletionSerializer(SecureModelMixin):
    """Per-node attestation / signature gate records."""

    completed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = SubstepGateCompletion
        fields = (
            'id',
            'step_execution', 'substep', 'node_id',
            'completed_by', 'completed_by_name', 'completed_at',
            'signature_data', 'signature_meaning',
            'verified_at', 'verification_method', 'ip_address',
            'created_at', 'updated_at',
        )
        read_only_fields = ('completed_at', 'created_at', 'updated_at')

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_completed_by_name(self, obj) -> str | None:
        if obj.completed_by:
            return obj.completed_by.get_full_name() or obj.completed_by.username
        return None


class SubstepResponseSerializer(SecureModelMixin):
    """Per-node operator capture rows (text / choice / photo / file /
    timer / computed)."""

    responded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = SubstepResponse
        fields = (
            'id',
            'step_execution', 'substep', 'node_id', 'kind',
            'value_text', 'value_document', 'value_json',
            'responded_by', 'responded_by_name', 'responded_at',
            'created_at', 'updated_at',
        )
        read_only_fields = ('responded_at', 'created_at', 'updated_at')

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_responded_by_name(self, obj) -> str | None:
        if obj.responded_by:
            return obj.responded_by.get_full_name() or obj.responded_by.username
        return None


# =============================================================================
# SamplingDecision — read-only exposure for operator runtime
# =============================================================================

class SamplingDecisionSerializer(serializers.ModelSerializer):
    """Append-only sampling decision per (StepExecution, Substep). The
    operator runtime queries `?step_execution=<id>` to discover which
    substeps are SELECTED / DESELECTED / PENDING and grey out the
    sampled-out ones."""

    class Meta:
        from Tracker.models import SamplingDecision
        model = SamplingDecision
        fields = [
            'id', 'step_execution', 'substep', 'outcome',
            'ruleset_version', 'decided_at', 'superseded_by',
        ]
        read_only_fields = fields


# =============================================================================
# BatchExecution — read/list serializer for the seal lifecycle viewset
# =============================================================================

class BatchExecutionSerializer(SecureModelMixin):
    """Minimal BatchExecution shape for the lifecycle viewset.

    The viewset only exposes list/retrieve + the seal action in this
    iteration; write semantics live on the seal service, not on the
    serializer."""

    class Meta:
        from Tracker.models import BatchExecution
        model = BatchExecution
        fields = [
            'id', 'work_order', 'step', 'parts', 'started_by',
            'started_at', 'sealed_at', 'completed_at', 'notes',
        ]
        # started_by is stamped from request.user in the viewset, not sent by
        # the client; sealed/completed timestamps are lifecycle-service-owned.
        read_only_fields = ['id', 'started_by', 'started_at', 'sealed_at', 'completed_at']
