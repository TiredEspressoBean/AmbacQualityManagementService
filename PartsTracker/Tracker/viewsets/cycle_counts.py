"""Cycle counts — count a location, see the differences, apply them. Logic lives in
services/mes/cycle_count.py."""
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from Tracker.models import CycleCount
from Tracker.serializers.cycle_counts import (
    CycleCountSerializer, RecordCountSerializer, StartCycleCountSerializer,
)
from Tracker.services.mes import cycle_count
from Tracker.viewsets.base import TenantScopedMixin

XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


class CycleCountViewSet(TenantScopedMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    """Counts of locations. POST starts one; `record`, `submit` and `apply` move it on.
    Never edited or deleted otherwise — a count is a record of what was found."""
    queryset = CycleCount.unscoped.select_related('location', 'started_by', 'submitted_by', 'applied_by')
    serializer_class = CycleCountSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter, filters.SearchFilter]
    search_fields = ['count_number', 'location__name']
    filterset_fields = ['status', 'location']
    ordering = ['-created_at']

    action_permissions = {
        'record': ['change_cyclecount'],
        'submit': ['change_cyclecount'],
        # Applying corrects stock — a lead's call, not the counter's.
        'apply': ['apply_cyclecount'],
    }
    crud_exempt_actions = {'record', 'submit', 'apply'}

    def _respond(self, count, code=status.HTTP_200_OK):
        return Response(CycleCountSerializer(count, context={'request': self.request}).data, status=code)

    @extend_schema(request=StartCycleCountSerializer, responses={201: CycleCountSerializer},
                   description="Start a count of a location: snapshots what UQMES expects there.")
    def create(self, request):
        req = StartCycleCountSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        try:
            count = cycle_count.start_count(request.tenant, req.validated_data['location'], request.user,
                                            blind=req.validated_data['blind'])
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return self._respond(count, status.HTTP_201_CREATED)

    @extend_schema(request=RecordCountSerializer, responses=CycleCountSerializer,
                   description="Save what was counted; an entry not on the list is something found here.")
    @action(detail=True, methods=['post'], url_path='record')
    def record(self, request, pk=None):
        count = self.get_object()
        req = RecordCountSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        entries = [{**e, 'id': str(e['id'])} for e in req.validated_data['entries']]
        try:
            count = cycle_count.record_count(count, entries)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return self._respond(count)

    @extend_schema(request=None, responses=CycleCountSerializer,
                   description="Finish counting; anything not counted is taken as not there.")
    @action(detail=True, methods=['post'], url_path='submit')
    def submit(self, request, pk=None):
        try:
            count = cycle_count.submit_count(self.get_object(), request.user)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return self._respond(count)

    @extend_schema(request=None, responses=CycleCountSerializer,
                   description="Correct UQMES from the count: quantity differences as recorded "
                               "adjustments, things found here moved here. Units not found are "
                               "reported, not changed.")
    @action(detail=True, methods=['post'], url_path='apply')
    def apply(self, request, pk=None):
        try:
            count = cycle_count.apply_count(self.get_object(), request.user)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return self._respond(count)

    @extend_schema(responses={(200, XLSX): OpenApiTypes.BINARY},
                   description="The count's differences as a spreadsheet, for keying into the ERP.")
    @action(detail=True, methods=['get'], url_path='differences-xlsx')
    def differences_xlsx(self, request, pk=None):
        count = self.get_object()
        resp = HttpResponse(cycle_count.discrepancy_workbook(count), content_type=XLSX)
        resp['Content-Disposition'] = f'attachment; filename="{count.count_number}_differences.xlsx"'
        return resp
