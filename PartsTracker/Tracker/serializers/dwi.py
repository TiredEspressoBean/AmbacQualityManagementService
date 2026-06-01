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
attributes inside the JSON are UUIDv7 minted client-side. Server-side
validation (UUID format + intra-document uniqueness) is a TODO when a real
authoring flow surfaces a bad-input case; for v1 the editor is the single
producer and the schema is trusted.
"""
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


class SubstepSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Substep — the unit of work instruction within a Step.

    The `body_blocks` field is a TipTap document JSON: `{type: 'doc',
    content: [...]}`. Frontend uses the type at
    `ambac-tracker-ui/src/types/dwi.ts` (DwiDocument).
    """

    step_name = serializers.CharField(source='step.name', read_only=True, allow_null=True)

    class Meta:
        model = Substep
        fields = (
            'id',
            'step', 'step_name',
            'order',
            'title',
            'body_blocks',
            'is_optional',
            'requires_signature',
            'is_inspection_point',
            'expected_duration',
            'sampling_rule',
            'source_library_substep_id',
            'source_library_version',
            'created_at', 'updated_at', 'archived',
        )
        read_only_fields = ('created_at', 'updated_at')


class SubstepResourceSerializer(serializers.ModelSerializer, SecureModelMixin):
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


class SubstepTranslationSerializer(serializers.ModelSerializer, SecureModelMixin):
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


class SubstepCompletionSerializer(serializers.ModelSerializer, SecureModelMixin):
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

    def get_completed_by_name(self, obj):
        if obj.completed_by:
            return obj.completed_by.get_full_name() or obj.completed_by.username
        return None


class SubstepGateCompletionSerializer(serializers.ModelSerializer, SecureModelMixin):
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

    def get_completed_by_name(self, obj):
        if obj.completed_by:
            return obj.completed_by.get_full_name() or obj.completed_by.username
        return None


class SubstepResponseSerializer(serializers.ModelSerializer, SecureModelMixin):
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

    def get_responded_by_name(self, obj):
        if obj.responded_by:
            return obj.responded_by.get_full_name() or obj.responded_by.username
        return None
