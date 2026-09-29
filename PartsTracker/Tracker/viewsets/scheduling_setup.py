"""CRUD + spreadsheet import/export for the scheduler's setup data.

- StepTimingViewSet — a step's standard times (one row per step).
- StepEquipmentAffinityViewSet — which machines can run a step, and how well.
- WorkCenterChangeoverViewSet — the changeover matrix, one row per
  (machine, from step, to step): the long form, which is what a spreadsheet can
  round-trip.

These tables were only ever written by the seed commands; the solver reads them. Steps
are named `Process > Step` in a file (step names repeat across processes), machines by
serial number or name. Edits are in place — the models are not versioned, and a step's
timing edited through the Steps API is written in place too.

DELETE soft-archives (SecureModel.delete), and the solver skips archived rows. Each
table has a unique key (the step; the step + machine; the machine + both steps), and an
archived row still holds its key — so adding the same thing again REVIVES the archived
row (`ReviveOnCreateMixin`, Tracker.services.core.soft_delete), over the API and through
an import alike.
"""
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from Tracker.models.scheduling import (
    StepEquipmentAffinity, StepTiming, WorkCenterChangeover,
)
from Tracker.serializers.csv_import import create_import_serializer_for_model
from Tracker.serializers.scheduling_setup import (
    StepEquipmentAffinitySerializer, StepTimingRecordSerializer,
    WorkCenterChangeoverSerializer,
)
from .base import TenantScopedMixin
from .core import ListMetadataMixin
from .mixins import CSVImportMixin, DataExportMixin


class ReviveOnCreateMixin:
    """A create whose unique key an archived row holds revives that row.

    Without this, a deleted eligibility or changeover could never be added back: the
    archived row keeps its key, and the create is refused as a duplicate.
    `revive_key` names the unique key's fields as the request sends them.
    """
    revive_key: tuple = ()

    def create(self, request, *args, **kwargs):
        from Tracker.services.core.soft_delete import find_archived, revive
        key = {f: request.data.get(f) for f in self.revive_key}
        archived = None
        if self.revive_key and all(v not in (None, '') for v in key.values()):
            archived = find_archived(self.queryset.model, self.tenant,
                                     {f"{f}_id": v for f, v in key.items()})
        if archived is None:
            return super().create(request, *args, **kwargs)
        with transaction.atomic():  # an invalid body leaves the row archived
            revive(archived)
            serializer = self.get_serializer(archived, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class StepTimingViewSet(ReviveOnCreateMixin, TenantScopedMixin, ListMetadataMixin,
                        CSVImportMixin, DataExportMixin, viewsets.ModelViewSet):
    """CRUD for step standard times — what the solver and RCCP size every operation
    from. One row per step (the step is the key)."""
    queryset = StepTiming.unscoped.all().select_related('step')
    serializer_class = StepTimingRecordSerializer
    # The step is a one-to-one, so it is the natural key: a row names its step as
    # `Process > Step` (or by ID) and updates that step's timing. A one-part tuple, so
    # the step is resolved as a reference — a bare 'step' would be matched as text.
    csv_import_serializer = create_import_serializer_for_model(
        StepTiming, lookup_fields=['id', ('step',)], meta={'revive_key': ('step',)})
    revive_key = ('step',)
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = ['step', 'attention_type']
    search_fields = ['step__name']
    ordering_fields = ['step__name', 'cycle_time_minutes', 'setup_minutes']
    ordering = ['step__name']


class StepEquipmentAffinityViewSet(ReviveOnCreateMixin, TenantScopedMixin, ListMetadataMixin,
                                   CSVImportMixin, DataExportMixin, viewsets.ModelViewSet):
    """CRUD for step-to-machine eligibility: a machine that can run a step, how well
    (eligible / preferred / dialed in), and optionally its own cycle time for it."""
    queryset = StepEquipmentAffinity.unscoped.all().select_related('step', 'equipment')
    serializer_class = StepEquipmentAffinitySerializer
    # Unique on (step, equipment): a row is found by that pair.
    csv_import_serializer = create_import_serializer_for_model(
        StepEquipmentAffinity, lookup_fields=['id', ('step', 'equipment')],
        meta={'revive_key': ('step', 'equipment')})
    revive_key = ('step', 'equipment')
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = ['step', 'equipment', 'affinity']
    search_fields = ['step__name', 'equipment__name']
    ordering_fields = ['step__name', 'equipment__name', 'affinity']
    ordering = ['equipment__name', 'step__name']


class WorkCenterChangeoverViewSet(ReviveOnCreateMixin, TenantScopedMixin, ListMetadataMixin,
                                  CSVImportMixin, DataExportMixin, viewsets.ModelViewSet):
    """CRUD for sequence-dependent setup: minutes to reconfigure a machine when it
    switches from running one step to another. One row per matrix cell."""
    queryset = WorkCenterChangeover.unscoped.all().select_related(
        'equipment', 'from_step', 'to_step')
    serializer_class = WorkCenterChangeoverSerializer
    # Unique on (equipment, from_step, to_step): a row is found by all three.
    csv_import_serializer = create_import_serializer_for_model(
        WorkCenterChangeover, lookup_fields=['id', ('equipment', 'from_step', 'to_step')],
        meta={'revive_key': ('equipment', 'from_step', 'to_step')})
    revive_key = ('equipment', 'from_step', 'to_step')
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = ['equipment', 'from_step', 'to_step']
    search_fields = ['equipment__name', 'from_step__name', 'to_step__name']
    ordering_fields = ['equipment__name', 'from_step__name', 'to_step__name',
                       'changeover_minutes']
    ordering = ['equipment__name', 'from_step__name', 'to_step__name']
