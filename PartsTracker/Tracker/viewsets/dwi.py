# viewsets/dwi.py - Digital Work Instructions ViewSets
"""
ViewSets for the DWI subsystem.

CRUD endpoints for the Phase 1-3 models. Operator-side capture actions
(complete_substep, record_gate_completion, etc.) live in
`services/mes/substeps.py` and are exposed via dedicated viewset actions
when Phase 4 frontend wires them.
"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from Tracker.models import (
    Substep,
    SubstepCompletion,
    SubstepResource,
    SubstepTranslation,
    SubstepGateCompletion,
    SubstepResponse,
)
from Tracker.serializers.dwi import (
    SubstepSerializer,
    SubstepResourceSerializer,
    SubstepTranslationSerializer,
    SubstepCompletionSerializer,
    SubstepGateCompletionSerializer,
    SubstepResponseSerializer,
)
from .base import TenantScopedMixin


class SubstepViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD for Substep rows.

    Filter by `?step=<step_id>` to fetch all substeps belonging to a Step
    (the typical substep-editor query). Default ordering matches the
    operator's working order within the parent Op.
    """

    queryset = Substep.unscoped.select_related('step', 'sampling_rule')
    serializer_class = SubstepSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = ['step', 'is_optional', 'requires_signature', 'is_inspection_point']
    search_fields = ['title']
    ordering_fields = ['order', 'created_at', 'updated_at']
    ordering = ['step', 'order']


class SubstepResourceViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD for SubstepResource rows.

    Filter by `?substep=<substep_id>` to fetch the resource list for a
    substep (the typical authoring-popover query).
    """

    queryset = SubstepResource.unscoped.select_related('substep', 'equipment_type')
    serializer_class = SubstepResourceSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['substep', 'equipment_type', 'required']
    ordering_fields = ['created_at']
    ordering = ['substep', 'pk']


class SubstepTranslationViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD for SubstepTranslation rows."""

    queryset = SubstepTranslation.unscoped.select_related('substep')
    serializer_class = SubstepTranslationSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['substep', 'language']
    ordering_fields = ['created_at']
    ordering = ['substep', 'language']


class SubstepCompletionViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Per-execution substep completions.

    Filter by `?step_execution=<id>` or `?substep=<id>` to scope queries.
    """

    queryset = SubstepCompletion.unscoped.select_related(
        'step_execution', 'substep', 'completed_by',
    )
    serializer_class = SubstepCompletionSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['step_execution', 'substep', 'completed_by', 'marked_not_applicable']
    ordering_fields = ['completed_at']
    ordering = ['-completed_at']


class SubstepGateCompletionViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Per-node attestation / signature gate completions."""

    queryset = SubstepGateCompletion.unscoped.select_related(
        'step_execution', 'substep', 'completed_by',
    )
    serializer_class = SubstepGateCompletionSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['step_execution', 'substep', 'node_id', 'completed_by']
    ordering_fields = ['completed_at']
    ordering = ['-completed_at']


class SubstepResponseViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Per-node operator capture rows."""

    queryset = SubstepResponse.unscoped.select_related(
        'step_execution', 'substep', 'responded_by', 'value_document',
    )
    serializer_class = SubstepResponseSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['step_execution', 'substep', 'node_id', 'kind', 'responded_by']
    ordering_fields = ['responded_at']
    ordering = ['-responded_at']