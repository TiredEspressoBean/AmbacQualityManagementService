# viewsets/mes_standard.py - MES Standard Tier ViewSets
"""
ViewSets for MES Standard tier models:
- Scheduling: WorkCenter, Shift, ScheduleSlot
- Downtime: DowntimeEvent
- Traceability: MaterialLot, MaterialUsage, BOM, BOMLine, AssemblyUsage
- Labor: TimeEntry
"""
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.db import transaction

from Tracker.models import (
    WorkCenter, Shift, ScheduleSlot, DowntimeEvent,
    MaterialLot, MaterialUsage, TimeEntry,
    BOM, BOMLine, AssemblyUsage,
)
from Tracker.serializers.mes_standard import (
    WorkCenterSerializer, WorkCenterSelectSerializer,
    ShiftSerializer,
    ScheduleSlotSerializer,
    DowntimeEventSerializer,
    MaterialLotSerializer, MaterialLotSplitSerializer,
    MaterialUsageSerializer,
    TimeEntrySerializer, ClockInSerializer,
    BOMSerializer, BOMListSerializer, BOMLineSerializer,
    AssemblyUsageSerializer, AssemblyRemoveSerializer,
)
from Tracker.serializers.qms import (
    QualityReportsSerializer,
    RecordInspectionRequestSerializer, RecordUnitsRequestSerializer, RecordBulkRequestSerializer,
    SamplePlanResponseSerializer, MaterialLotBulkCreateSerializer,
    IncomingInspectionRowSerializer, InspectionInboxRowSerializer,
)
from Tracker.services.qms import receiving_inspection
from Tracker.services.qms import incoming_inspection
from Tracker.services.qms import inspection_inbox
from .base import TenantScopedMixin
from .core import ExcelExportMixin


# ===== WORK CENTER VIEWSETS =====

class WorkCenterViewSet(TenantScopedMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """Work center management"""
    queryset = WorkCenter.unscoped.all()
    serializer_class = WorkCenterSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'code', 'created_at']
    ordering = ['code']


class WorkCenterSelectViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Lightweight work center endpoint for dropdowns"""
    queryset = WorkCenter.unscoped.all()
    serializer_class = WorkCenterSelectSerializer
    pagination_class = None


# ===== SHIFT VIEWSETS =====

class ShiftViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Shift definition management"""
    queryset = Shift.unscoped.all()
    serializer_class = ShiftSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['is_active']
    ordering_fields = ['start_time', 'name']
    ordering = ['start_time']


# ===== SCHEDULE SLOT VIEWSETS =====

class ScheduleSlotViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Production schedule management"""
    queryset = ScheduleSlot.unscoped.select_related('work_center', 'shift', 'work_order')
    serializer_class = ScheduleSlotSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['work_center', 'shift', 'work_order', 'status', 'scheduled_date']
    ordering_fields = ['scheduled_date', 'scheduled_start']
    ordering = ['scheduled_date', 'scheduled_start']

    @extend_schema(
        request=inline_serializer(name="StartSlotInput", fields={}),
        responses={200: ScheduleSlotSerializer}
    )
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Mark schedule slot as started"""
        slot = self.get_object()
        if slot.status != 'SCHEDULED':
            return Response(
                {'detail': f'Cannot start slot with status "{slot.status}"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        slot.status = 'IN_PROGRESS'
        slot.actual_start = timezone.now()
        slot.save()
        return Response(ScheduleSlotSerializer(slot, context={'request': request}).data)

    @extend_schema(
        request=inline_serializer(name="CompleteSlotInput", fields={}),
        responses={200: ScheduleSlotSerializer}
    )
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark schedule slot as completed"""
        slot = self.get_object()
        if slot.status != 'IN_PROGRESS':
            return Response(
                {'detail': f'Cannot complete slot with status "{slot.status}"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        slot.status = 'COMPLETED'
        slot.actual_end = timezone.now()
        slot.save()
        return Response(ScheduleSlotSerializer(slot, context={'request': request}).data)


# ===== DOWNTIME EVENT VIEWSETS =====

class DowntimeEventViewSet(TenantScopedMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """Equipment/work center downtime tracking"""
    queryset = DowntimeEvent.unscoped.select_related(
        'equipment', 'work_center', 'work_order', 'reported_by', 'resolved_by'
    )
    serializer_class = DowntimeEventSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['equipment', 'work_center', 'category', 'work_order']
    ordering_fields = ['start_time', 'end_time', 'category']
    ordering = ['-start_time']

    def perform_create(self, serializer):
        serializer.save(reported_by=self.request.user)

    @extend_schema(
        request=inline_serializer(name="ResolveDowntimeInput", fields={}),
        responses={200: DowntimeEventSerializer}
    )
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Mark downtime event as resolved"""
        event = self.get_object()
        if event.end_time:
            return Response(
                {'detail': 'Downtime event already resolved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        event.end_time = timezone.now()
        event.resolved_by = request.user
        event.save()
        return Response(DowntimeEventSerializer(event, context={'request': request}).data)


# ===== MATERIAL LOT VIEWSETS =====

class MaterialLotViewSet(TenantScopedMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """Material lot tracking with split capability"""
    queryset = MaterialLot.unscoped.select_related('material_type', 'supplier', 'parent_lot', 'received_by')
    serializer_class = MaterialLotSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    search_fields = ['lot_number', 'supplier_lot_number', 'material_description']
    filterset_fields = ['status', 'supplier', 'material_type']
    ordering_fields = ['received_date', 'lot_number', 'expiration_date']
    ordering = ['-received_date']

    def get_queryset(self):
        qs = super().get_queryset()
        # Receiving-inspection queue: lots still needing a disposition — RECEIVED,
        # AWAITING_INSPECTION, plus lots soft-held at receiving (QUARANTINE with a
        # hold_reason, e.g. an unqualified supplier) so they surface and get resolved.
        if self.request.query_params.get('inspection_pending') in ('true', '1'):
            from django.db.models import Q
            qs = qs.filter(
                Q(status__in=['RECEIVED', 'AWAITING_INSPECTION'])
                | (Q(status='QUARANTINE') & ~Q(hold_reason=''))
            )
        return qs

    def perform_create(self, serializer):
        # Auto-set received_by to current user, initialize quantity_remaining
        lot = serializer.save(
            received_by=self.request.user,
            quantity_remaining=serializer.validated_data.get('quantity', 0)
        )
        # Standards-compliant default: a received lot is auto-routed to inspection
        # (or dock-to-stock if no RECEIVING step) — never silently available.
        receiving_inspection.route_received_lot(lot, self.request.user)

    @extend_schema(request=MaterialLotSplitSerializer, responses={201: MaterialLotSerializer})
    @action(detail=True, methods=['post'])
    def split(self, request, pk=None):
        """Split a lot into a child lot"""
        lot = self.get_object()
        serializer = MaterialLotSplitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            child_lot = lot.split(
                quantity=serializer.validated_data['quantity'],
                reason=serializer.validated_data.get('reason', '')
            )
            return Response(
                MaterialLotSerializer(child_lot, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # ===== RECEIVING INSPECTION (purchased material, Flow A) =====

    action_permissions = {
        'accept': ['change_materiallot'],
        'reject': ['change_materiallot'],
    }

    def _qr_response(self, report):
        return Response(QualityReportsSerializer(report, context={'request': self.request}).data)

    @extend_schema(responses={200: SamplePlanResponseSerializer},
                   description="Derive the acceptance-sampling plan (n/Ac/Re) for this lot "
                               "from its part type's RECEIVING step + supplier sampling ruleset.")
    @action(detail=True, methods=['get'])
    def sample_plan(self, request, pk=None):
        lot = self.get_object()
        try:
            sp = receiving_inspection.sample_plan_for_lot(lot)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        step = receiving_inspection.resolve_receiving_step(lot.material_type)
        chars = [
            {'id': m.id, 'label': m.label, 'unit': m.unit or '', 'type': m.type,
             'nominal': float(m.nominal) if m.nominal is not None else None,
             'upper_tol': float(m.upper_tol) if m.upper_tol is not None else None,
             'lower_tol': float(m.lower_tol) if m.lower_tol is not None else None}
            for m in receiving_inspection.receiving_characteristics(step)
        ]
        ex = receiving_inspection.receiving_execution(lot)
        # variables_characteristic isn't on the SamplePlan DTO (lot-level); pull it
        # from the resolved ruleset so the UI knows which characteristic to capture.
        rs = receiving_inspection.resolve_sampling_ruleset(step, lot.supplier) if step else None
        return Response(SamplePlanResponseSerializer({
            **sp.__dict__,
            'variables_characteristic_id': rs.variables_characteristic_id if rs else None,
            'characteristics': chars,
            'step_id': step.id if step else None,
            'has_substeps': bool(step and step.substeps.filter(archived=False).exists()),
            'step_execution_id': ex.id if ex else None,
        }).data)

    @extend_schema(request=None, responses={201: QualityReportsSerializer})
    @action(detail=True, methods=['post'])
    def open_inspection(self, request, pk=None):
        lot = self.get_object()
        try:
            report = receiving_inspection.open_inspection(lot, request.user)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(QualityReportsSerializer(report, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)

    @extend_schema(request=RecordInspectionRequestSerializer, responses={200: QualityReportsSerializer})
    @action(detail=True, methods=['post'])
    def record_inspection(self, request, pk=None):
        lot = self.get_object()
        report = lot.quality_reports.order_by('-created_at').first()
        if report is None:
            return Response({'detail': 'No open inspection for this lot.'},
                            status=status.HTTP_400_BAD_REQUEST)
        ser = RecordInspectionRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            report = receiving_inspection.record_inspection(
                report, ser.validated_data['measurements'], request.user)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return self._qr_response(report)

    @extend_schema(request=RecordUnitsRequestSerializer, responses={200: QualityReportsSerializer})
    @action(detail=True, methods=['post'])
    def record_units(self, request, pk=None):
        lot = self.get_object()
        report = lot.quality_reports.order_by('-created_at').first()
        if report is None:
            return Response({'detail': 'No open inspection for this lot.'},
                            status=status.HTTP_400_BAD_REQUEST)
        ser = RecordUnitsRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            report = receiving_inspection.record_sample_units(
                report, ser.validated_data['units'], request.user)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return self._qr_response(report)

    @extend_schema(request=RecordBulkRequestSerializer, responses={200: QualityReportsSerializer})
    @action(detail=True, methods=['post'])
    def record_bulk(self, request, pk=None):
        lot = self.get_object()
        report = lot.quality_reports.order_by('-created_at').first()
        if report is None:
            return Response({'detail': 'No open inspection for this lot.'},
                            status=status.HTTP_400_BAD_REQUEST)
        ser = RecordBulkRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            report = receiving_inspection.record_bulk(
                report, ser.validated_data['defectives_found'], request.user)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return self._qr_response(report)

    @extend_schema(request=None, responses={200: QualityReportsSerializer})
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        lot = self.get_object()
        report = lot.quality_reports.order_by('-created_at').first()
        if report is None:
            return Response({'detail': 'No open inspection for this lot.'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            report = receiving_inspection.accept(report, request.user)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return self._qr_response(report)

    @extend_schema(
        request=None,
        responses={201: inline_serializer(name="RaiseScarResponse", fields={
            "capa_id": serializers.UUIDField(), "capa_number": serializers.CharField(),
        })},
        description="Raise a Supplier Corrective Action (SCAR) for this lot's supplier, "
                    "linking the lot's receiving inspection report.",
    )
    @action(detail=True, methods=['post'])
    def raise_scar(self, request, pk=None):
        from Tracker.services.qms.scar import open_scar_for_lot
        lot = self.get_object()
        try:
            capa = open_scar_for_lot(lot, user=request.user)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'capa_id': capa.id, 'capa_number': capa.capa_number},
                        status=status.HTTP_201_CREATED)

    @extend_schema(request=None, responses={200: QualityReportsSerializer})
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        lot = self.get_object()
        report = lot.quality_reports.order_by('-created_at').first()
        if report is None:
            return Response({'detail': 'No open inspection for this lot.'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            report = receiving_inspection.reject(report, request.user)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return self._qr_response(report)

    @extend_schema(
        request=None,
        responses={200: inline_serializer(name="ReceivingVerdict", fields={
            "status": serializers.CharField(),
            "is_variables": serializers.BooleanField(),
            "sample_size": serializers.IntegerField(allow_null=True),
            "accept_number": serializers.IntegerField(allow_null=True),
            "reject_number": serializers.IntegerField(allow_null=True),
            "k": serializers.FloatField(allow_null=True),
            "defectives": serializers.IntegerField(),
            "units_recorded": serializers.IntegerField(),
            "readings": serializers.IntegerField(),
        })},
        description="Run the lot-acceptance evaluation over the recorded inspection "
                    "results (attribute defective-unit count vs Ac/Re, or Z1.9 x̄/s vs k) "
                    "and return the current verdict. Server-authoritative — the DWI "
                    "unit-by-unit runtime reads this to show ACCEPT/REJECT before the "
                    "operator commits.",
    )
    @action(detail=True, methods=['get'])
    def evaluate_receiving(self, request, pk=None):
        from collections import defaultdict
        lot = self.get_object()
        report = lot.quality_reports.order_by('-created_at').first()
        if report is None:
            return Response({'detail': 'No open inspection for this lot.'},
                            status=status.HTTP_400_BAD_REQUEST)
        report = receiving_inspection.evaluate_lot_acceptance(report)
        results = list(report.measurements.all())
        by_unit = defaultdict(list)
        for r in results:
            by_unit[r.sample_number].append(r)
        defectives = sum(1 for rs in by_unit.values()
                         if any(x.is_within_spec is False for x in rs))
        return Response({
            'status': report.status,
            'is_variables': report.acceptability_constant_k is not None,
            'sample_size': report.sample_size,
            'accept_number': report.accept_number,
            'reject_number': report.reject_number,
            'k': report.acceptability_constant_k,
            'defectives': defectives,
            'units_recorded': len(by_unit),
            'readings': len(results),
        })

    @extend_schema(
        request=MaterialLotBulkCreateSerializer,
        responses={
            201: inline_serializer(name="MaterialLotBulkCreateResponse", fields={
                "count": serializers.IntegerField(),
                "created_lot_ids": serializers.ListField(child=serializers.UUIDField()),
            }),
            400: inline_serializer(name="MaterialLotBulkCreateError", fields={
                "detail": serializers.CharField(required=False),
                "errors": serializers.ListField(child=serializers.DictField(), required=False),
            }),
        },
        description="Receive N lots from a shipment (paste-grid). All-or-nothing — any row error rolls back.",
    )
    @action(detail=False, methods=['post'], url_path='bulk_create')
    def bulk_create(self, request):
        rows = request.data.get('lots')
        if not isinstance(rows, list) or len(rows) == 0:
            return Response({"detail": "lots must be a non-empty list"},
                            status=status.HTTP_400_BAD_REQUEST)
        ctx = {'request': request}
        per_row_errors = []
        valid_rows = []
        for idx, row in enumerate(rows):
            ser = MaterialLotSerializer(data=row, context=ctx)
            if ser.is_valid():
                valid_rows.append(ser)
            else:
                per_row_errors.append({'index': idx, 'errors': ser.errors})
        if per_row_errors:
            return Response({"detail": "Validation failed", "errors": per_row_errors},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            with transaction.atomic():
                created = []
                for ser in valid_rows:
                    lot = ser.save(received_by=request.user,
                                   quantity_remaining=ser.validated_data.get('quantity', 0))
                    receiving_inspection.route_received_lot(lot, request.user)
                    created.append(lot)
        except Exception as exc:
            return Response({"detail": "Bulk receive failed",
                             "errors": [{"index": -1, "errors": str(exc)}]},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({"count": len(created), "created_lot_ids": [str(c.id) for c in created]},
                        status=status.HTTP_201_CREATED)


class IncomingInspectionViewSet(viewsets.ViewSet):
    """Unified incoming-inspection worklist — purchased MaterialLots awaiting
    inspection + OutsideProcessShipments out/returned, in one list keyed by a
    `source` origin (SAP QM QA32-style). Read-only aggregation; rows carry enough
    to dispatch the Inspect action to the right runtime."""
    permission_classes = [IsAuthenticated]

    def get_view_name(self):
        return "Incoming Inspection"

    @extend_schema(
        responses=IncomingInspectionRowSerializer(many=True),
        description="Unified inbound-inspection queue: MaterialLots awaiting inspection "
                    "(PURCHASED_LOT) + OutsideProcessShipments out/returned (OUTSIDE_PROCESS), "
                    "normalized with a `source` discriminator and shared status vocabulary.",
    )
    def list(self, request):
        rows = incoming_inspection.build_incoming_rows()
        return Response(IncomingInspectionRowSerializer(rows, many=True).data)


class InspectionInboxViewSet(viewsets.ViewSet):
    """The QA inspector's task inbox — one flat list across every inspection
    source (FPI queue-jumpers, receiving lots w/ sampling answer + severity
    badge + resume progress, OSP returns, in-process operations). Read-only
    aggregation, standard list-of-rows contract (the IncomingInspection
    pattern); clients derive type counts / oldest-age chips from the rows.
    See services.qms.inspection_inbox for the row contract and tone rules."""
    permission_classes = [IsAuthenticated]

    def get_view_name(self):
        return "Inspection Inbox"

    @extend_schema(
        responses=InspectionInboxRowSerializer(many=True),
        description="The inspector's flat task inbox: FPI first, then by urgency "
                    "tone, then age. Derive type-count chips (with oldest-age — "
                    "counts alone hide rot) from the rows.",
    )
    def list(self, request):
        rows = inspection_inbox.build_inbox_rows()
        return Response(InspectionInboxRowSerializer(rows, many=True).data)


# ===== MATERIAL USAGE VIEWSETS =====

class MaterialUsageViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Material consumption records (read-only, created via lot consumption)"""
    queryset = MaterialUsage.unscoped.select_related('lot', 'part', 'work_order', 'step', 'consumed_by')
    serializer_class = MaterialUsageSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['lot', 'part', 'work_order', 'is_substitute']
    ordering_fields = ['consumed_at']
    ordering = ['-consumed_at']


# ===== TIME ENTRY VIEWSETS =====

class TimeEntryViewSet(TenantScopedMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """Labor time tracking with clock-in/out"""
    queryset = TimeEntry.unscoped.select_related(
        'user', 'part', 'work_order', 'step', 'equipment', 'work_center'
    )
    serializer_class = TimeEntrySerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    # end_time__isnull exposes "my open entry" as a clean server query (the clock
    # state read the operator home needs), without a client-side history scan.
    filterset_fields = {
        'user': ['exact'],
        'entry_type': ['exact'],
        'work_order': ['exact'],
        'approved': ['exact'],
        'end_time': ['isnull'],
    }
    ordering_fields = ['start_time', 'end_time', 'entry_type']
    ordering = ['-start_time']

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(request=ClockInSerializer, responses={201: TimeEntrySerializer})
    @action(detail=False, methods=['post'])
    def clock_in(self, request):
        """Start a new time entry for the current user"""
        serializer = ClockInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Use the viewset's get_serializer to ensure proper tenant handling
        entry_serializer = self.get_serializer(data={
            'entry_type': serializer.validated_data['entry_type'],
            'start_time': timezone.now(),
            **{k: v.pk if hasattr(v, 'pk') else v for k, v in serializer.validated_data.items() if k != 'entry_type'}
        })
        entry_serializer.is_valid(raise_exception=True)
        entry_serializer.save(user=request.user)

        return Response(
            TimeEntrySerializer(entry_serializer.instance, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

    @extend_schema(
        request=inline_serializer(name="ClockOutInput", fields={"notes": serializers.CharField(required=False)}),
        responses={200: TimeEntrySerializer}
    )
    @action(detail=True, methods=['post'])
    def clock_out(self, request, pk=None):
        """End a time entry"""
        entry = self.get_object()
        if entry.end_time:
            return Response({'detail': 'Already clocked out'}, status=status.HTTP_400_BAD_REQUEST)

        entry.end_time = timezone.now()
        if 'notes' in request.data:
            entry.notes = request.data['notes']
        entry.save()
        return Response(TimeEntrySerializer(entry, context={'request': request}).data)

    @extend_schema(
        request=inline_serializer(name="ApproveTimeInput", fields={}),
        responses={200: TimeEntrySerializer}
    )
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a time entry"""
        entry = self.get_object()
        if entry.approved:
            return Response({'detail': 'Time entry already approved'}, status=status.HTTP_400_BAD_REQUEST)
        entry.approved = True
        entry.approved_by = request.user
        entry.approved_at = timezone.now()
        entry.save()
        return Response(TimeEntrySerializer(entry, context={'request': request}).data)


# ===== BOM VIEWSETS =====

class BOMViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Bill of Materials management"""
    queryset = BOM.unscoped.select_related('part_type', 'approved_by').prefetch_related('lines')
    serializer_class = BOMSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['part_type', 'bom_type', 'status']
    ordering_fields = ['part_type__name', 'revision', 'effective_date']
    ordering = ['part_type__name', '-revision']

    def get_serializer_class(self):
        if self.action == 'list':
            return BOMListSerializer
        return BOMSerializer

    @extend_schema(
        request=inline_serializer(name="ReleaseBOMInput", fields={}),
        responses={200: BOMSerializer}
    )
    @action(detail=True, methods=['post'])
    def release(self, request, pk=None):
        """Release a BOM for production use"""
        bom = self.get_object()
        if bom.status != 'DRAFT':
            return Response({'detail': 'Only draft BOMs can be released'}, status=status.HTTP_400_BAD_REQUEST)

        bom.status = 'RELEASED'
        bom.effective_date = timezone.now().date()
        bom.approved_by = request.user
        bom.approved_at = timezone.now()
        bom.save()
        return Response(BOMSerializer(bom, context={'request': request}).data)

    @extend_schema(
        request=inline_serializer(name="ObsoleteBOMInput", fields={}),
        responses={200: BOMSerializer}
    )
    @action(detail=True, methods=['post'])
    def obsolete(self, request, pk=None):
        """Mark a BOM as obsolete"""
        bom = self.get_object()
        if bom.status == 'OBSOLETE':
            return Response({'detail': 'BOM is already obsolete'}, status=status.HTTP_400_BAD_REQUEST)
        bom.status = 'OBSOLETE'
        bom.obsolete_date = timezone.now().date()
        bom.save()
        return Response(BOMSerializer(bom, context={'request': request}).data)

    @extend_schema(
        request=inline_serializer(
            name="CreateBOMRevisionInput",
            fields={'change_description': serializers.CharField()},
        ),
        responses={201: BOMSerializer},
    )
    @action(detail=True, methods=['post'], url_path='revisions')
    def create_revision(self, request, pk=None):
        """POST a new revision of this BOM. Returns 201 with the new version."""
        from Tracker.services.mes.bom import create_new_bom_version
        bom = self.get_object()
        try:
            new_version = create_new_bom_version(
                bom,
                user=request.user,
                change_description=request.data.get('change_description', ''),
            )
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            BOMSerializer(new_version, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class BOMLineViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """BOM line item management"""
    queryset = BOMLine.unscoped.select_related('bom', 'component_type')
    serializer_class = BOMLineSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['bom', 'component_type', 'is_optional']
    ordering_fields = ['line_number', 'component_type__name']
    ordering = ['bom', 'line_number']


# ===== ASSEMBLY USAGE VIEWSETS =====

class AssemblyUsageViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Assembly component tracking"""
    queryset = AssemblyUsage.unscoped.select_related(
        'assembly', 'component', 'bom_line', 'installed_by', 'removed_by', 'step'
    )
    serializer_class = AssemblyUsageSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['assembly', 'component', 'bom_line']
    ordering_fields = ['installed_at', 'removed_at']
    ordering = ['-installed_at']

    def perform_create(self, serializer):
        serializer.save(installed_by=self.request.user)

    @extend_schema(request=AssemblyRemoveSerializer, responses={200: AssemblyUsageSerializer})
    @action(detail=True, methods=['post'])
    def remove(self, request, pk=None):
        """Remove a component from an assembly"""
        usage = self.get_object()
        if usage.removed_at:
            return Response({'detail': 'Component already removed'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = AssemblyRemoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        usage.remove(user=request.user, reason=serializer.validated_data.get('reason', ''))
        return Response(AssemblyUsageSerializer(usage, context={'request': request}).data)
