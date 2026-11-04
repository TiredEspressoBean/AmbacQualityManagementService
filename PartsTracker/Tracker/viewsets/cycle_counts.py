"""Cycle counts — count a location or an item, see the differences, apply them, chase
what wasn't found, and key the differences into the ERP. Logic lives in
services/mes/cycle_count.py (and the cadence in services/mes/count_cadence.py)."""
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from Tracker.models import CycleCount
from Tracker.serializers.cycle_counts import (
    AccuracyMonthSerializer, ApplyCountSerializer, CountAccuracySerializer, CycleCountSerializer, DueForCountSerializer,
    ItemCountStatusSerializer, MarkKeyedSerializer, MissingUnitSerializer, RecordCountSerializer, ResolveMissingSerializer,
    SendBackCountSerializer, StartCycleCountSerializer,
)
from Tracker.services.mes import cycle_count
from Tracker.viewsets.base import TenantScopedMixin

XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


class CycleCountViewSet(TenantScopedMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    """Counts of a location or an item. POST starts one; `record`, `submit` and `apply`
    move it on. Never edited or deleted otherwise — a count is a record of what was found."""
    queryset = CycleCount.unscoped.select_related('location', 'material', 'part_type', 'started_by',
                                                  'submitted_by', 'applied_by', 'erp_keyed_by')
    serializer_class = CycleCountSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter, filters.SearchFilter]
    search_fields = ['count_number', 'location__name', 'material__name', 'part_type__name']
    filterset_fields = ['status', 'location', 'material', 'part_type']
    ordering = ['-created_at']

    action_permissions = {
        'record': ['change_cyclecount'],
        'submit': ['change_cyclecount'],
        # Applying corrects stock — a lead's call, not the counter's.
        'apply': ['apply_cyclecount'],
        # Sending it back is the same lead's call, made instead of applying.
        'send_back': ['apply_cyclecount'],
        # Closing out a unit not found, and the ERP keying, follow from applying.
        'resolve_missing': ['apply_cyclecount'],
        'mark_keyed': ['apply_cyclecount'],
    }
    crud_exempt_actions = {'record', 'submit', 'apply', 'send_back', 'resolve_missing', 'mark_keyed'}

    def _respond(self, count, code=status.HTTP_200_OK):
        return Response(CycleCountSerializer(count, context={'request': self.request}).data, status=code)

    @extend_schema(request=StartCycleCountSerializer, responses={201: CycleCountSerializer},
                   description="Start a count of a location, or of a material or part type wherever "
                               "it's kept: snapshots what UQMES expects.")
    def create(self, request):
        req = StartCycleCountSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        d = req.validated_data
        try:
            count = cycle_count.start_count(request.tenant, request.user,
                                            location=d.get('location') or None,
                                            material=d.get('material'), part_type=d.get('part_type'),
                                            blind=d['blind'])
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

    @extend_schema(request=SendBackCountSerializer, responses=CycleCountSerializer,
                   description="Send a submitted count back for a recount, with a reason. It "
                               "reopens with what was entered. An applied count is final.")
    @action(detail=True, methods=['post'], url_path='send-back')
    def send_back(self, request, pk=None):
        req = SendBackCountSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        try:
            count = cycle_count.send_back(self.get_object(), request.user, req.validated_data['reason'])
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return self._respond(count)

    @extend_schema(request=None, responses=CycleCountSerializer,
                   description="Finish counting. A line left blank stays uncounted: it is left "
                               "out of the differences and never applied.")
    @action(detail=True, methods=['post'], url_path='submit')
    def submit(self, request, pk=None):
        try:
            count = cycle_count.submit_count(self.get_object(), request.user)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return self._respond(count)

    @extend_schema(request=ApplyCountSerializer, responses=CycleCountSerializer,
                   description="Correct UQMES from the count: quantity differences as recorded "
                               "adjustments, things found here moved here. Units not found are "
                               "reported, not changed. Lines outside their class's tolerance "
                               "need a note saying why the difference is real.")
    @action(detail=True, methods=['post'], url_path='apply')
    def apply(self, request, pk=None):
        try:
            count = cycle_count.apply_count(self.get_object(), request.user,
                                            note=request.data.get('note', ''),
                                            reasons=request.data.get('reasons') or {})
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return self._respond(count)

    @extend_schema(responses=MissingUnitSerializer(many=True),
                   description="Units a count didn't find, still unresolved: not seen since, not "
                               "left for good, and nobody has said what became of them.")
    @action(detail=False, methods=['get'], url_path='missing', pagination_class=None)
    def missing(self, request):
        return Response(MissingUnitSerializer(cycle_count.missing_units(request.tenant), many=True).data)

    @extend_schema(request=ResolveMissingSerializer, responses=CycleCountSerializer,
                   description="Say what became of a unit this count didn't find, taking it off "
                               "the missing list.")
    @action(detail=True, methods=['post'], url_path='resolve-missing')
    def resolve_missing(self, request, pk=None):
        req = ResolveMissingSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        try:
            count = cycle_count.resolve_missing(self.get_object(), req.validated_data['part'],
                                                request.user, req.validated_data['note'])
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return self._respond(count)

    @extend_schema(responses=CycleCountSerializer(many=True),
                   description="Applied counts whose differences haven't been keyed into the ERP yet.")
    @action(detail=False, methods=['get'], url_path='to-key', pagination_class=None)
    def to_key(self, request):
        return Response(CycleCountSerializer(cycle_count.to_key(request.tenant), many=True,
                                             context={'request': request}).data)

    @extend_schema(responses={(200, XLSX): OpenApiTypes.BINARY},
                   description="Every difference not yet keyed into the ERP, across counts, as one sheet.")
    @action(detail=False, methods=['get'], url_path='to-key-xlsx')
    def to_key_xlsx(self, request):
        resp = HttpResponse(cycle_count.discrepancy_workbook(cycle_count.to_key(request.tenant)),
                            content_type=XLSX)
        resp['Content-Disposition'] = 'attachment; filename="count_differences_to_key.xlsx"'
        return resp

    @extend_schema(request=MarkKeyedSerializer, responses={200: OpenApiTypes.OBJECT},
                   description="Mark counts' differences as keyed into the ERP.")
    @action(detail=False, methods=['post'], url_path='mark-keyed')
    def mark_keyed(self, request):
        req = MarkKeyedSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        counts = list(self.get_queryset().filter(pk__in=req.validated_data['counts']))
        return Response({'marked': cycle_count.mark_keyed(counts, request.user)})

    @extend_schema(responses=DueForCountSerializer(many=True),
                   description="Items due for counting under their ABC class: stock in a "
                               "location not counted within the class's interval (never "
                               "counted first, then most overdue), with the locations to count.")
    @action(detail=False, methods=['get'], url_path='due', pagination_class=None)
    def due(self, request):
        from dataclasses import asdict
        from Tracker.services.mes.count_cadence import due_for_count
        return Response(DueForCountSerializer([asdict(r) for r in due_for_count(request.tenant)],
                                              many=True).data)

    @extend_schema(parameters=[OpenApiParameter('material', OpenApiTypes.UUID, required=False),
                               OpenApiParameter('part_type', OpenApiTypes.UUID, required=False)],
                   responses=ItemCountStatusSerializer,
                   description="When one material or part type (exactly one) was last counted and "
                               "is next due, on the same terms as the due list — for its form.")
    @action(detail=False, methods=['get'], url_path='item-status', pagination_class=None)
    def item_status(self, request):
        from dataclasses import asdict
        from django.core.exceptions import ValidationError as DjangoValidationError
        from Tracker.models import Material, PartTypes
        from Tracker.services.mes.count_cadence import count_status
        material, part_type = request.query_params.get('material'), request.query_params.get('part_type')
        if bool(material) == bool(part_type):
            return Response({'detail': "Give a material or a part type."}, status=status.HTTP_400_BAD_REQUEST)
        model, kind, pk = (Material, 'MATERIAL', material) if material else (PartTypes, 'PART_TYPE', part_type)
        try:
            item = model.objects.filter(pk=pk).first()
        except DjangoValidationError:
            item = None
        if item is None:
            return Response({'detail': "Not found."}, status=status.HTTP_404_NOT_FOUND)
        st = count_status(request.tenant, kind, item.pk, abc_class=item.abc_class)
        return Response(ItemCountStatusSerializer(asdict(st)).data)

    @extend_schema(parameters=[OpenApiParameter('days', OpenApiTypes.INT, required=False,
                                                description="Window in days (default 90).")],
                   responses=CountAccuracySerializer,
                   description="Inventory record accuracy per ABC class: counted lines within "
                               "their class's tolerance, over counts applied in the window.")
    @action(detail=False, methods=['get'], url_path='accuracy', pagination_class=None)
    def accuracy(self, request):
        from Tracker.services.mes.count_cadence import accuracy
        try:
            days = max(1, min(int(request.query_params.get('days') or 90), 3650))
        except ValueError:
            days = 90
        return Response(CountAccuracySerializer({'days': days, **accuracy(request.tenant, days=days)}).data)

    @extend_schema(parameters=[OpenApiParameter('months', OpenApiTypes.INT, required=False,
                                                description="How many months back (default 12).")],
                   responses=AccuracyMonthSerializer(many=True),
                   description="Inventory record accuracy per ABC class for each recent month, "
                               "oldest first; a month with nothing counted has null percentages.")
    @action(detail=False, methods=['get'], url_path='accuracy-trend', pagination_class=None)
    def accuracy_trend(self, request):
        from Tracker.services.mes.count_cadence import accuracy_trend
        try:
            months = max(1, min(int(request.query_params.get('months') or 12), 60))
        except ValueError:
            months = 12
        return Response(AccuracyMonthSerializer(accuracy_trend(request.tenant, months=months), many=True).data)

    @extend_schema(responses={(200, XLSX): OpenApiTypes.BINARY},
                   description="The count's differences as a spreadsheet, for keying into the ERP.")
    @action(detail=True, methods=['get'], url_path='differences-xlsx')
    def differences_xlsx(self, request, pk=None):
        count = self.get_object()
        resp = HttpResponse(cycle_count.discrepancy_workbook(count), content_type=XLSX)
        resp['Content-Disposition'] = f'attachment; filename="{count.count_number}_differences.xlsx"'
        return resp
