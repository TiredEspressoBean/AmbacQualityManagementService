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
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view, inline_serializer
from rest_framework import viewsets, status, serializers, parsers
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.db import transaction

from Tracker.models import (
    WorkCenter, Shift, ScheduleSlot, DowntimeEvent,
    Material, MaterialLot, MaterialUsage, StorageLocation, TimeEntry,
    BOM, BOMLine, AssemblyUsage,
    UserWorkCenterMembership,
)
from Tracker.serializers.mes_standard import (
    WorkCenterSerializer, WorkCenterSelectSerializer,
    UserWorkCenterMembershipSerializer,
    ShiftSerializer,
    ScheduleSlotSerializer,
    DowntimeEventSerializer,
    MaterialSerializer,
    MaterialLotSerializer, MaterialLotSplitSerializer,
    ExtendShelfLifeSerializer, ExpectedReceiptSerializer, ReceiveExpectedLotSerializer,
    BulkExpectedReceiptSerializer, ExpectedReceiptImportResultSerializer, LateDeliverySerializer,
    ReleaseHoldSerializer, AdjustQuantitySerializer, StorageLocationSerializer,
    RejectLotSerializer, RejectLotResponseSerializer, LotDecisionSerializer, ShipBackSerializer,
    LotTraceSerializer, DockMetricsSerializer,
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
from Tracker.services.core.clock import tenant_today
from .base import TenantScopedMixin
from Tracker.serializers.csv_import import BaseCSVImportSerializer, create_import_serializer_for_model
from .core import ListMetadataMixin
from .mixins import CSVImportMixin, DataExportMixin, VersionHistoryMixin


# ===== WORK CENTER VIEWSETS =====

class _WorkCenterImport(BaseCSVImportSerializer):
    """A work-centre import edits a row the way the API does: `WorkCenterSerializer.update`
    versions a content edit (name, code, kind, capacity, cost centre) and saves a
    placement/planning edit (equipment, is_constraint, is_critical) in place."""

    def transform_data(self, data):
        from decimal import Decimal
        result = super().transform_data(data)
        # The base reads a number as a float, and a float is not equal to the Decimal
        # on the row (92.3 != Decimal('92.30')) — so an unchanged efficiency looked
        # edited and forked a version.
        if isinstance(result.get('default_efficiency'), float):
            result['default_efficiency'] = Decimal(str(result['default_efficiency']))
        return result

    def update_instance(self, instance, data):
        from Tracker.services.core.versioning import apply_versioned_update
        return apply_versioned_update(
            instance, data,
            non_versioning_fields=WorkCenterSerializer._NON_VERSIONING_FIELDS,
            default_update=super().update_instance,
            version_kwargs={'user': self.user,
                            'change_description': "Imported from a spreadsheet"},
        )


class WorkCenterViewSet(VersionHistoryMixin, TenantScopedMixin, CSVImportMixin, DataExportMixin, viewsets.ModelViewSet):
    """Work center management"""
    queryset = WorkCenter.unscoped.all()
    serializer_class = WorkCenterSerializer
    # A row is matched on its code (unique per tenant among current versions);
    # `equipment` is a `; `-separated list of equipment names.
    csv_import_serializer = create_import_serializer_for_model(
        WorkCenter, lookup_fields=['id', 'code'], base=_WorkCenterImport)
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'code', 'created_at']
    ordering = ['code']

    # Recording a pick writes a staging line, not a work centre — without this the
    # inherited CRUD rule would gate it on `add_workcenter`, which has nothing to do
    # with the act. (`mark_staged` above still inherits that; left alone rather than
    # changing its gate as a side effect of this work.)
    action_permissions = {'record_pick': ['add_materialstagingline']}
    crud_exempt_actions = {'record_pick'}

    def get_queryset(self):
        """Current versions only when listing.

        `WorkCenter` is versioned, so an edit leaves the superseded row behind — and the
        list was returning both, so one station appeared twice with a stale step and
        people count on the older row. Every internal consumer (RCCP, the workload-
        control policy) already filters `is_current_version`; the list was the outlier.

        Scoped to `list` rather than filtered on the class queryset (as `ShiftViewSet`
        does) because `Steps.work_center` holds whichever version was current when the
        step was authored. Filtering every action would 404 a by-id fetch of a work
        centre an older routing still legitimately points at.
        """
        qs = super().get_queryset()
        if self.action == 'list':
            qs = qs.filter(is_current_version=True)
        return qs

    @extend_schema(
        request=inline_serializer(name="MarkStagedInput", fields={
            "work_order": serializers.UUIDField(),
            "step": serializers.UUIDField(),
            "staged": serializers.BooleanField(),
            "note": serializers.CharField(required=False, allow_blank=True),
        }),
        responses={200: OpenApiTypes.OBJECT},
    )
    @action(detail=False, methods=['post'], url_path='mark-staged')
    def mark_staged(self, request):
        """Record that a job's material is at the bench (or take it back).

        Survives a re-solve: staging is kept per (work order, step), not on the
        scheduled tasks the solver replaces each run."""
        from Tracker.services.mes.staging import set_staged
        wo, step = request.data.get('work_order'), request.data.get('step')
        if not wo or not step:
            return Response({"detail": "work_order and step are required."},
                            status=status.HTTP_400_BAD_REQUEST)
        row = set_staged(self.tenant, wo, step, bool(request.data.get('staged', True)),
                         request.user, request.data.get('note', '') or '')
        return Response({'work_order': str(row.work_order_id), 'step': str(row.step_id),
                         'staged_at': row.staged_at, 'note': row.note})

    @extend_schema(
        request=inline_serializer(name="RecordPickInput", fields={
            "work_order": serializers.UUIDField(),
            "step": serializers.UUIDField(),
            "material": serializers.UUIDField(),
            # Which subject `material` names. Defaults to MATERIAL so existing callers
            # are unchanged; PART_TYPE kits a purchased part.
            "kind": serializers.ChoiceField(
                choices=['MATERIAL', 'PART_TYPE'], required=False),
            "qty": serializers.FloatField(),
            "qty_required": serializers.FloatField(required=False),
            "lots": inline_serializer(name="PickedLot", many=True, required=False, fields={
                "lot_id": serializers.UUIDField(),
                "lot_number": serializers.CharField(required=False, allow_blank=True),
                "qty": serializers.FloatField(),
            }),
        }),
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    @action(detail=False, methods=['post'], url_path='record-pick')
    def record_pick(self, request):
        """Record what was ACTUALLY pulled for one material on one job-operation.

        Does two jobs at once, both of which the system got wrong without it.

        It reserves: until consumption draws the line down, the picked quantity is
        netted out of on-hand everywhere, so a second sheet can't promise the same
        units. `MaterialLot.quantity_remaining` doesn't move until consumption, so a
        loaded cart otherwise still reads as available stock.

        And it corrects traceability: consumption reads these lots instead of
        re-deriving FEFO. The sheet names the lots the plan WOULD draw; the picker
        regularly takes another because the named one is empty, short, or already gone.
        Recording it is the difference between the record saying what happened and
        saying what was intended.
        """
        from Tracker.services.mes.staging import record_pick as svc

        data = request.data
        required = ('work_order', 'step', 'material')
        if not all(data.get(k) for k in required):
            return Response({"detail": "work_order, step and material are required."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            qty = float(data.get('qty', 0))
        except (TypeError, ValueError):
            qty = -1
        if qty < 0:
            return Response({"detail": "`qty` must be a number >= 0."},
                            status=status.HTTP_400_BAD_REQUEST)

        kind = (data.get('kind') or 'MATERIAL').upper()
        if kind not in ('MATERIAL', 'PART_TYPE'):
            return Response({"detail": "`kind` must be MATERIAL or PART_TYPE."},
                            status=status.HTTP_400_BAD_REQUEST)

        line = svc(
            self.tenant, data['work_order'], data['step'], data['material'],
            qty, data.get('lots') or [], request.user,
            qty_required=data.get('qty_required'), kind=kind,
        )
        return Response({
            # Echo the subject back the way it was addressed. A Material and a PartTypes
            # can share a uuid, so the id alone does not identify what was picked.
            'kind': kind,
            'material': str(line.material_id if line.material_id is not None
                            else line.material_type_id),
            'qty_picked': float(line.qty_picked),
            'qty_required': float(line.qty_required),
            'picked_lots': line.picked_lots,
            'reserved': line.is_reserved,
        })

    @extend_schema(
        parameters=[
            OpenApiParameter(name='work_center', type=OpenApiTypes.UUID, required=False,
                             description="Narrow to one station."),
            OpenApiParameter(name='hours', type=OpenApiTypes.INT, required=False,
                             description="How far ahead to stage (1-72, default 8)."),
        ],
        responses={200: OpenApiTypes.OBJECT},
    )
    @action(detail=False, methods=['get'], url_path='staging-list')
    def staging_list(self, request):
        """What to put at each bench before the operator arrives: the next few hours
        of scheduled work per station, with the material each job consumes there,
        whether it's on hand, and the fixtures needed."""
        from Tracker.services.mes.staging import staging_list as svc
        try:
            hours = max(1, min(72, int(request.query_params.get('hours', 8))))
        except (TypeError, ValueError):
            hours = 8
        return Response(svc(self.tenant, request.query_params.get('work_center'), hours))


class WorkCenterSelectViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Lightweight work center endpoint for dropdowns.

    Current, live versions only: WorkCenter is versioned, so `.all()` listed every
    superseded revision beside the current one and a pick could bind a record to an
    old version. Archived ones are excluded outright, not left to `?include_archived`
    — a dropdown offers what can be chosen now."""
    # Tenant-scoped per request by TenantScopedMixin.get_queryset.
    queryset = WorkCenter.unscoped.filter(is_current_version=True, archived=False)
    serializer_class = WorkCenterSelectSerializer
    pagination_class = None


# ===== USER WORK CENTER MEMBERSHIP VIEWSET =====

class UserWorkCenterMembershipViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Which stations a user is eligible at — CRUD for the through-table.
    See Documents/WORK_CENTER_DESIGN.md.

    Perms: add/change/delete_userworkcentermembership (TEAM_ACCESS_ADMIN_
    PERMISSIONS — admin + manager tier). view is broad (STAFF_VIEW_PERMISSIONS).
    """
    queryset = UserWorkCenterMembership.unscoped.select_related('user', 'work_center')
    serializer_class = UserWorkCenterMembershipSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['user', 'work_center', 'is_primary']
    ordering_fields = ['created_at', 'is_primary']
    ordering = ['-is_primary', 'work_center__code']

    def perform_create(self, serializer):
        serializer.save(tenant=self.tenant)

    @extend_schema(
        request=inline_serializer(name="SetPrimaryInput", fields={}),
        responses={200: UserWorkCenterMembershipSerializer},
        description=(
            "Set this membership as the user's primary station in this tenant. "
            "Atomically unsets is_primary on any other memberships this user has."
        ),
    )
    @action(detail=True, methods=['post'], url_path='set-primary')
    def set_primary(self, request, pk=None):
        from django.db import transaction
        target = self.get_object()
        with transaction.atomic():
            # The scoping is what makes this action's documented contract
            # ("primary station in this tenant") true — a user with
            # memberships in several tenants keeps a primary in each.
            # tenant-safe: .objects auto-scopes via the request tenant ContextVar
            UserWorkCenterMembership.objects.filter(user=target.user).exclude(pk=target.pk).update(is_primary=False)
            target.is_primary = True
            target.save(update_fields=['is_primary'])
        return Response(self.get_serializer(target).data)


# ===== SHIFT VIEWSETS =====

# A shift's breaks in a spreadsheet cell: `12:00-12:30; 15:00-15:15`. The export writes
# this and the import reads it (JSON — `[{"start": "12:00", "end": "12:30"}]` — is read
# too). A blank cell leaves the breaks as they are.
_BREAK_SEPARATOR = '; '


def _format_break_windows(value):
    if not isinstance(value, list):
        return value
    return _BREAK_SEPARATOR.join(
        f"{b.get('start')}-{b.get('end')}" if isinstance(b, dict) else str(b) for b in value)


def _parse_break_windows(value):
    import json
    if isinstance(value, list):
        return value
    text = str(value).strip()
    if text.startswith('['):
        try:
            return json.loads(text)
        except ValueError:
            raise serializers.ValidationError({'break_windows': (
                f"Couldn't read {text!r} as JSON.")})
    out = []
    for item in (p.strip() for p in text.split(_BREAK_SEPARATOR.strip())):
        if not item:
            continue
        start, sep, end = item.partition('-')
        if not sep:
            raise serializers.ValidationError({'break_windows': (
                f"Couldn't read {item!r} — write breaks as 12:00-12:30; 15:00-15:15.")})
        out.append({'start': start.strip(), 'end': end.strip()})
    return out


def _parse_time(value):
    """A cell's time as a `datetime.time` — the export writes `06:00:00`, Excel may hand
    back a time. Anything unreadable is passed through for the API to refuse."""
    import datetime as _dt
    if isinstance(value, _dt.datetime):
        return value.time()
    if isinstance(value, _dt.time):
        return value
    for fmt in ('%H:%M:%S', '%H:%M'):
        try:
            return _dt.datetime.strptime(str(value).strip(), fmt).time()
        except ValueError:
            continue
    return value


class _ShiftImport(BaseCSVImportSerializer):
    """Shift's times and breaks, read the way the export writes them.

    The base passes a time column through as text, and '06:00:00' != time(6, 0) — so
    every row of an unchanged export looked edited and forked a new version."""

    def transform_data(self, data):
        result = super().transform_data(data)
        for f in ('start_time', 'end_time'):
            if f in result:
                result[f] = _parse_time(result[f])
        if 'break_windows' in result:
            result['break_windows'] = _parse_break_windows(result['break_windows'])
        return result


class ShiftViewSet(VersionHistoryMixin, TenantScopedMixin, ListMetadataMixin, CSVImportMixin, DataExportMixin, viewsets.ModelViewSet):
    """Shift definition management.

    `Shift` is a versioned model (`_is_versioned=True`, for DCAS labor audits), so
    edits mutate via `create_new_version` — never a raw save — and the list is scoped
    to current versions. Delete is the SecureModel soft-delete (archive).
    """
    queryset = Shift.unscoped.filter(is_current_version=True)
    serializer_class = ShiftSerializer
    # Matched on its code. An edit is routed as `perform_update` routes it: the
    # importer's automatic path (a versioned model whose serializer declares
    # `_NON_VERSIONING_FIELDS`) versions a content edit and saves an
    # is_active/archived flip in place.
    # `days_of_week` is the model's own text (`0,1,2,3,4`, 0 = Monday).
    csv_import_serializer = create_import_serializer_for_model(
        Shift, lookup_fields=['id', 'code'], base=_ShiftImport,
        meta={'import_column_help': {
            'break_windows': "Breaks as start-end, e.g. 12:00-12:30; 15:00-15:15. "
                             "Blank leaves them unchanged.",
            'days_of_week': "Day numbers, comma-separated: 0 = Monday … 6 = Sunday.",
        }})
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['is_active']
    ordering_fields = ['start_time', 'name']
    ordering = ['start_time']

    def _convert_df_for_excel(self, df):
        # Before the base turns the list into its Python repr, which nothing reads back.
        if 'break_windows' in df.columns:
            df['break_windows'] = df['break_windows'].apply(_format_break_windows)
        return super()._convert_df_for_excel(df)

    def perform_update(self, serializer):
        """Version a content edit so labor-hour changes keep an audit trail; save a
        flip of only the serializer's `_NON_VERSIONING_FIELDS` (is_active, archived)
        in place. The routing is `apply_versioned_update`'s, keyed on the fields that
        actually changed — the same rule the spreadsheet import applies. On a
        version, the validated changes become field overrides on the new current
        version and the response reflects it."""
        from Tracker.services.core.versioning import apply_versioned_update

        instance = serializer.instance
        updates = {k: v for k, v in serializer.validated_data.items() if k != 'tenant'}
        if not updates:
            return  # nothing submitted — don't spin a no-op version
        serializer.instance = apply_versioned_update(
            instance, updates,
            non_versioning_fields=ShiftSerializer._NON_VERSIONING_FIELDS,
            # The plain in-place save — ShiftSerializer.update would route a second time.
            default_update=super(ShiftSerializer, serializer).update,
            version_kwargs={'user': self.request.user,
                            'change_description': "Edited via scheduling settings"},
        )


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

class DowntimeEventViewSet(TenantScopedMixin, DataExportMixin, viewsets.ModelViewSet):
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

class MaterialViewSet(TenantScopedMixin, CSVImportMixin, DataExportMixin, ListMetadataMixin,
                      viewsets.ModelViewSet):
    """Purchased items — raw materials / bought components (O-rings, seals, fasteners).
    The buy-side item list, distinct from in-house PartTypes; holds purchase lead time."""
    queryset = Material.unscoped.select_related('preferred_supplier').all()
    serializer_class = MaterialSerializer
    # A row is matched on its part number, then its name; `preferred_supplier` is found
    # by company name. Everything else is read from the model.
    csv_import_serializer = create_import_serializer_for_model(
        Material, lookup_fields=['id', 'part_number', 'name'])
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    search_fields = ['name', 'part_number', 'description']
    filterset_fields = ['is_active', 'preferred_supplier']
    ordering_fields = ['name', 'part_number']
    ordering = ['name']


class StorageLocationViewSet(TenantScopedMixin, ListMetadataMixin, CSVImportMixin, DataExportMixin,
                             viewsets.ModelViewSet):
    """The tenant's managed list of storage locations. Optional: with none set up,
    receiving takes free text and suggests what has been typed before."""
    queryset = StorageLocation.unscoped.all()
    serializer_class = StorageLocationSerializer
    # A location is its name (unique per tenant).
    csv_import_serializer = create_import_serializer_for_model(
        StorageLocation, lookup_fields=['id', 'name'])
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    search_fields = ['name', 'description']
    filterset_fields = ['is_active']
    ordering_fields = ['name']
    ordering = ['name']


# `inspection_pending` is read straight off query_params in get_queryset rather
# than declared in filterset_fields, so drf-spectacular cannot see it and the
# generated client didn't know the param existed. Callers had to cast the
# mismatch away, which is indistinguishable from the case where the filter is
# genuinely undeclared and silently dropped. Declaring it keeps the two apart.
@extend_schema_view(
    list=extend_schema(parameters=[
        OpenApiParameter(
            name='inspection_pending', type=OpenApiTypes.STR, required=False,
            description=(
                "'true'/'1' narrows to lots still needing a receiving disposition: "
                "RECEIVED, AWAITING_INSPECTION, plus lots soft-held at receiving "
                "(QUARANTINE with a hold_reason)."
            ),
        ),
        OpenApiParameter(
            name='delivery', type=OpenApiTypes.STR, required=False,
            enum=['overdue', 'due_soon', 'late'],
            description=(
                "ON_ORDER lots by promised date on the plant's day: 'overdue' (passed), "
                "'due_soon' (today through DUE_SOON_DAYS ahead), 'late' (both)."
            ),
        ),
    ]),
)
class MaterialLotViewSet(TenantScopedMixin, DataExportMixin, viewsets.ModelViewSet):
    """Material lot tracking with split capability"""
    queryset = MaterialLot.unscoped.select_related(
        'material_type', 'material', 'supplier', 'owner', 'parent_lot', 'received_by'
    ).prefetch_related('life_tracking__definition')
    serializer_class = MaterialLotSerializer
    # Explicit, with MultiPart first, so the schema advertises multipart ahead
    # of JSON and the generated client gets requestFormat "form-data" on
    # PATCH. `certificate_of_conformance` is a FileField, and the request
    # schema already types it as a File — but under the DRF defaults JSON was
    # listed first, the client serialised as JSON, and a CoC upload had to
    # bypass the client with a hand-rolled multipart fetch. DocumentViewSet
    # already declares its parsers this way for the same reason.
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    search_fields = ['lot_number', 'supplier_lot_number', 'material_description']
    filterset_fields = ['status', 'supplier', 'material_type']
    # promised_date is the useful axis for ON_ORDER lots — they have no received_date yet.
    ordering_fields = ['received_date', 'lot_number', 'expiration_date', 'promised_date']
    ordering = ['-received_date']
    # Releasing a receiving hold is a quality decision — accepting stock from an
    # unqualified supplier, say — so it takes the disposition-approval perm, not just
    # edit rights on the lot.
    action_permissions = {
        'release_hold': ['approve_disposition'],
        'adjust_quantity': ['change_materiallot'],
        # The whole-lot decisions. Rejecting a lot under inspection is open to
        # inspectors (the service holds a whole-lot reject as a request without it).
        'confirm_whole_lot_reject': ['reject_whole_lot'],
        'reject_remainder': ['reject_whole_lot'],
        'ship_back': ['change_materiallot'],
    }

    def get_queryset(self):
        from django.db.models import Exists, OuterRef
        from Tracker.models import QuarantineDisposition
        qs = super().get_queryset().annotate(_awaiting_return=Exists(
            QuarantineDisposition.objects.filter(  # tenant-safe: correlated to the scoped outer lot
                material_lot=OuterRef('pk'), disposition_type='RETURN_TO_SUPPLIER',
            ).exclude(current_state='CLOSED')))
        # Receiving-inspection queue: lots still needing a disposition — RECEIVED,
        # AWAITING_INSPECTION, plus lots soft-held at receiving (QUARANTINE with a
        # hold_reason, e.g. an unqualified supplier) so they surface and get resolved.
        if self.request.query_params.get('inspection_pending') in ('true', '1'):
            from django.db.models import Q
            qs = qs.filter(
                Q(status__in=['RECEIVED', 'AWAITING_INSPECTION'])
                | (Q(status='QUARANTINE') & ~Q(hold_reason=''))
            )
        # Late deliveries: ON_ORDER lots past (overdue), or within DUE_SOON_DAYS of
        # (due_soon), their promised date; `late` is both. The plant's day, not UTC's.
        delivery = self.request.query_params.get('delivery')
        if delivery in ('overdue', 'due_soon', 'late'):
            from datetime import timedelta
            from Tracker.services.mes.material_lot import DUE_SOON_DAYS
            today = tenant_today(getattr(self.request, 'tenant', None))
            qs = qs.filter(status='ON_ORDER', promised_date__isnull=False)
            if delivery == 'overdue':
                qs = qs.filter(promised_date__lt=today)
            elif delivery == 'due_soon':
                qs = qs.filter(promised_date__gte=today,
                               promised_date__lte=today + timedelta(days=DUE_SOON_DAYS))
            else:
                qs = qs.filter(promised_date__lte=today + timedelta(days=DUE_SOON_DAYS))
        return qs

    def create(self, request, *args, **kwargs):
        # A receipt with no lot number is numbered by us (next_lot_number) — the
        # supplier's number goes in supplier_lot_number.
        if not str(request.data.get('lot_number') or '').strip():
            from Tracker.services.mes.material_lot import next_lot_number
            data = request.data.copy()
            data['lot_number'] = next_lot_number(request.tenant)
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED,
                            headers=self.get_success_headers(serializer.data))
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        # Auto-set received_by to current user, initialize quantity_remaining
        lot = serializer.save(
            received_by=self.request.user,
            quantity_remaining=serializer.validated_data.get('quantity', 0),
        )
        # Standards-compliant default: a received lot is auto-routed to inspection
        # (or dock-to-stock if no RECEIVING step) — never silently available.
        receiving_inspection.route_received_lot(lot, self.request.user)

    def perform_update(self, serializer):
        lot = serializer.save()
        # Uploading the CoC or entering the heat number is what clears the hold waiting
        # on it; the lot then routes on as if it had just arrived.
        receiving_inspection.reevaluate_hold(lot, self.request.user)

    @extend_schema(request=ReleaseHoldSerializer, responses={200: MaterialLotSerializer})
    @action(detail=True, methods=['post'], url_path='release-hold')
    def release_hold(self, request, pk=None):
        """Lift a receiving hold with a reason on record; the lot is then routed on with
        that one gate waived (inspection or dock-to-stock as usual)."""
        lot = self.get_object()
        ser = ReleaseHoldSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            lot = receiving_inspection.release_hold(lot, request.user, ser.validated_data['reason'])
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(MaterialLotSerializer(lot, context={'request': request}).data)

    @extend_schema(request=AdjustQuantitySerializer, responses={200: MaterialLotSerializer})
    @action(detail=True, methods=['post'], url_path='adjust-quantity')
    def adjust_quantity(self, request, pk=None):
        """Correct what's left of a lot to what is physically there, with a reason."""
        lot = self.get_object()
        ser = AdjustQuantitySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        from Tracker.services.mes.material_lot import adjust_quantity
        try:
            lot = adjust_quantity(lot, new_quantity=ser.validated_data['quantity'],
                                  reason=ser.validated_data['reason'], user=request.user)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(MaterialLotSerializer(lot, context={'request': request}).data)

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

    @extend_schema(request=ExpectedReceiptSerializer, responses={201: MaterialLotSerializer})
    @action(detail=False, methods=['post'], url_path='expected-receipt')
    def expected_receipt(self, request):
        """Record stock ordered but not yet delivered, so netting can see it.

        Not a plain create: `perform_create` routes every new lot to receiving inspection,
        which is wrong for something that has not arrived. This goes through the service
        so the lot lands ON_ORDER with a generated placeholder lot number.
        """
        ser = ExpectedReceiptSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        from Tracker.services.mes.material_lot import record_expected_receipt
        try:
            lot = record_expected_receipt(
                tenant=request.tenant,
                material=ser.validated_data.get('material'),
                material_type=ser.validated_data.get('material_type'),
                quantity=ser.validated_data['quantity'],
                promised_date=ser.validated_data['promised_date'],
                unit_of_measure=ser.validated_data.get('unit_of_measure', ''),
                supplier=ser.validated_data.get('supplier'),
                erp_po_number=ser.validated_data.get('erp_po_number', ''),
                erp_po_line=ser.validated_data.get('erp_po_line', ''),
                lot_number=ser.validated_data.get('lot_number', ''),
            )
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(MaterialLotSerializer(lot, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)

    @extend_schema(request=BulkExpectedReceiptSerializer,
                   responses={201: MaterialLotSerializer(many=True)})
    # pagination_class=None: a many=True response on a paginated viewset would be
    # documented as a paginated envelope; this returns the bare list it created.
    @action(detail=False, methods=['post'], url_path='bulk-expected-receipt',
            pagination_class=None)
    def bulk_expected_receipt(self, request):
        """Several expected receipts at once, all or nothing — a buyer recording what
        they just ordered against a list of shortages."""
        ser = BulkExpectedReceiptSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        from Tracker.services.mes.material_lot import record_expected_receipts
        keys = ('material', 'material_type', 'quantity', 'promised_date', 'unit_of_measure',
                'supplier', 'erp_po_number', 'erp_po_line', 'lot_number')
        rows = [{k: r[k] for k in keys if k in r} for r in ser.validated_data['receipts']]
        try:
            lots = record_expected_receipts(tenant=request.tenant, rows=rows)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(MaterialLotSerializer(lots, many=True, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)

    @extend_schema(
        request={'multipart/form-data': inline_serializer(
            name='ExpectedReceiptImportRequest', fields={'file': serializers.FileField()})},
        responses={200: ExpectedReceiptImportResultSerializer},
        description=(
            "Import open purchase-order lines (.csv or .xlsx) as expected receipts, matched "
            "on PO number + line. Only adds and updates — a line missing from the file is "
            "left alone, and a line already received is never put back on order."),
    )
    @action(detail=False, methods=['post'], url_path='import-expected',
            parser_classes=[parsers.MultiPartParser])
    def import_expected(self, request):
        upload = request.FILES.get('file')
        if upload is None:
            return Response({'detail': 'Attach the file as "file".'},
                            status=status.HTTP_400_BAD_REQUEST)
        from Tracker.services.mes.expected_receipt_import import import_expected_receipts
        try:
            result = import_expected_receipts(tenant=request.tenant, file=upload,
                                              filename=upload.name)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ExpectedReceiptImportResultSerializer(result).data)

    @extend_schema(responses={(200, 'text/csv'): OpenApiTypes.STR},
                   description="A blank expected-receipts import sheet with one example row.")
    @action(detail=False, methods=['get'], url_path='import-expected-template')
    def import_expected_template(self, request):
        from django.http import HttpResponse
        from Tracker.services.mes.expected_receipt_import import template_csv
        resp = HttpResponse(template_csv(), content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = 'attachment; filename="expected_receipts_template.csv"'
        return resp

    @extend_schema(
        parameters=[
            OpenApiParameter('start', OpenApiTypes.DATE, required=True,
                             description="First receipt date (inclusive)."),
            OpenApiParameter('end', OpenApiTypes.DATE, required=True,
                             description="Last receipt date (inclusive)."),
            OpenApiParameter('po_only', OpenApiTypes.BOOL, required=False,
                             description="Only deliveries received against a PO."),
        ],
        responses={(200, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'):
                   OpenApiTypes.BINARY},
        description=("What the dock received in a date range, one row per delivery by PO "
                     "line — received, accepted, rejected, awaiting decision — as a sheet "
                     "to post the goods receipts in the ERP. No prices."),
    )
    @action(detail=False, methods=['get'], url_path='receipts-export',
            pagination_class=None, filter_backends=[])
    def receipts_export(self, request):
        from django.http import HttpResponse
        from django.utils.dateparse import parse_date
        from Tracker.services.mes.receipt_export import receipts_workbook
        start = parse_date(request.query_params.get('start') or '')
        end = parse_date(request.query_params.get('end') or '')
        if start is None or end is None or start > end:
            return Response({'detail': 'Give a start and end date (YYYY-MM-DD), start first.'},
                            status=status.HTTP_400_BAD_REQUEST)
        po_only = str(request.query_params.get('po_only', '')).lower() in ('1', 'true', 'yes')
        resp = HttpResponse(
            receipts_workbook(request.tenant, start, end, with_po_only=po_only),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        resp['Content-Disposition'] = f'attachment; filename="receipts_{start}_{end}.xlsx"'
        return resp

    # pagination_class / filter_backends off: the viewset paginates and filters, so
    # this bare list would otherwise be documented as a filtered, paginated envelope.
    @extend_schema(responses={200: LateDeliverySerializer(many=True)})
    @action(detail=False, methods=['get'], url_path='late-deliveries',
            pagination_class=None, filter_backends=[])
    def late_deliveries(self, request):
        """Expected receipts overdue or due soon, most overdue first, each with the open
        work orders whose BOM calls for the item."""
        from Tracker.services.mes.late_deliveries import late_deliveries
        return Response(LateDeliverySerializer(late_deliveries(request.tenant), many=True).data)

    @extend_schema(
        description=(
            "Storage locations for a picker to suggest. When the tenant keeps a managed "
            "list (StorageLocations), its active entries; otherwise every location "
            "already typed on material lots and equipment."
        ),
        responses={200: {"type": "array", "items": {"type": "string"}}},
    )
    @action(detail=False, methods=['get'], pagination_class=None)
    def locations(self, request):
        from Tracker.models import Equipments, StorageLocation
        # tenant-safe: SecureManager scopes StorageLocation to the request's tenant.
        managed = list(StorageLocation.objects.filter(is_active=True, archived=False)
                       .values_list('name', flat=True))
        if managed:
            return Response(sorted(managed, key=str.casefold))
        lots = (self.get_queryset().exclude(storage_location='')
                .values_list('storage_location', flat=True))
        # tenant-safe: SecureManager scopes Equipments to the request's tenant.
        machines = Equipments.objects.exclude(location='').values_list('location', flat=True)
        seen = {}
        for raw in [*lots, *machines]:
            name = (raw or '').strip()
            if name:
                seen.setdefault(name.casefold(), name)  # one spelling per case-insensitive name
        return Response(sorted(seen.values(), key=str.casefold))

    @extend_schema(request=ReceiveExpectedLotSerializer, responses={200: MaterialLotSerializer})
    @action(detail=True, methods=['post'], url_path='receive')
    def receive(self, request, pk=None):
        """Book in an ON_ORDER lot that has physically arrived (→ RECEIVED, then routed
        to incoming inspection like any other receipt)."""
        lot = self.get_object()
        ser = ReceiveExpectedLotSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        from Tracker.services.mes.material_lot import receive_expected_lot
        try:
            lot = receive_expected_lot(
                lot,
                lot_number=ser.validated_data.get('lot_number', ''),
                supplier_lot_number=ser.validated_data.get('supplier_lot_number'),
                received_by=request.user,
                received_date=ser.validated_data.get('received_date'),
                quantity=ser.validated_data.get('quantity'),
                storage_location=ser.validated_data.get('storage_location'),
                remainder=ser.validated_data.get('remainder'),
                received_as_quantity=ser.validated_data.get('received_as_quantity'),
                received_as_unit=ser.validated_data.get('received_as_unit') or '',
                heat_number=ser.validated_data.get('heat_number'),
                source_type=ser.validated_data.get('source_type'),
            )
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        # Same disposition path a walk-in receipt takes — inspection or dock-to-stock.
        receiving_inspection.route_received_lot(lot, request.user)
        lot.refresh_from_db()
        return Response(MaterialLotSerializer(lot, context={'request': request}).data)

    @extend_schema(request=ExtendShelfLifeSerializer, responses={200: MaterialLotSerializer})
    @action(detail=True, methods=['post'])
    def extend_shelf_life(self, request, pk=None):
        """Governed shelf-life extension (re-tested material gets a new use-by)."""
        lot = self.get_object()
        ser = ExtendShelfLifeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        from Tracker.services.life_tracking.shelf_life import extend_shelf_life
        try:
            extend_shelf_life(
                lot,
                new_expiration_date=ser.validated_data['new_expiration_date'],
                reason=ser.validated_data['reason'],
                approved_by=request.user,
            )
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        lot.refresh_from_db()
        return Response(MaterialLotSerializer(lot, context={'request': request}).data)

    # ===== RECEIVING INSPECTION (purchased material, Flow A) =====

    action_permissions = {
        'accept': ['change_materiallot'],
        'reject': ['change_materiallot'],
        'extend_shelf_life': ['change_materiallot'],
        # raise_scar creates a real CAPA row (SUPPLIER type) via
        # open_scar_for_lot. Without this it would fall through to the CRUD
        # gate (POST -> add_materiallot) and become a side door around the
        # initiate_capa gate on CAPAViewSet.create.
        'raise_scar': ['initiate_capa'],
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
        step = receiving_inspection.resolve_receiving_step_for_lot(lot)
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

    @extend_schema(request=RejectLotSerializer, responses={200: RejectLotResponseSerializer})
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject at receiving inspection, opening the disposition with it. A partial
        reject splits the bad pieces off and accepts the rest; a whole-lot reject needs
        reject_whole_lot, and without it holds the lot as a request."""
        from Tracker.services.qms.lot_reject import reject_lot
        lot = self.get_object()
        report = lot.quality_reports.order_by('-created_at').first()
        if report is None:
            return Response({'detail': 'No open inspection for this lot.'},
                            status=status.HTTP_400_BAD_REQUEST)
        ser = RejectLotSerializer(data=request.data or {})
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        try:
            rejected, disposition, outcome = reject_lot(
                report, request.user, disposition_type=v['disposition_type'],
                rejected_quantity=v.get('rejected_quantity'), whole_lot=v['whole_lot'],
                description=v.get('description', ''), severity=v['severity'])
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        rejected.refresh_from_db()
        return Response(RejectLotResponseSerializer({
            'outcome': outcome,
            'lot': rejected,
            'disposition_id': str(disposition.id),
            'disposition_number': disposition.disposition_number,
        }, context={'request': request}).data)

    @extend_schema(
        parameters=[OpenApiParameter(name='days', type=OpenApiTypes.INT, required=False,
                                     description="Window in days (default 30, at most 365).")],
        responses={200: DockMetricsSerializer})
    @action(detail=False, methods=['get'], url_path='dock-metrics',
            pagination_class=None, filter_backends=[])
    def dock_metrics(self, request):
        """Receiving's own numbers: receipts per day, lots waiting and for how long, time
        to a decision, holds by reason, and rejects in pieces."""
        from Tracker.services.mes.dock_metrics import dock_metrics
        try:
            days = max(1, min(365, int(request.query_params.get('days', 30))))
        except ValueError:
            days = 30
        return Response(DockMetricsSerializer(dock_metrics(request.tenant, days=days)).data)

    @extend_schema(responses={200: LotTraceSerializer})
    @action(detail=True, methods=['get'])
    def trace(self, request, pk=None):
        """Two-way traceability: where the lot came from, and every part, assembly,
        work order, order and customer it reached."""
        from Tracker.services.mes.lot_trace import trace_lot
        return Response(LotTraceSerializer(trace_lot(self.get_object())).data)

    @extend_schema(request=None, responses={200: MaterialLotSerializer})
    @action(detail=True, methods=['post'], url_path='confirm-whole-lot-reject')
    def confirm_whole_lot_reject(self, request, pk=None):
        """Confirm an inspector's request to reject the whole lot."""
        from Tracker.services.qms.lot_reject import confirm_whole_lot_reject
        try:
            lot, _ = confirm_whole_lot_reject(self.get_object(), request.user)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(MaterialLotSerializer(lot, context={'request': request}).data)

    @extend_schema(request=LotDecisionSerializer, responses={200: MaterialLotSerializer})
    @action(detail=True, methods=['post'], url_path='reject-remainder')
    def reject_remainder(self, request, pk=None):
        """Escalate to the whole lot: reject what's left of an accepted lot."""
        from Tracker.services.qms.lot_reject import reject_remainder
        ser = LotDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            lot, _ = reject_remainder(self.get_object(), request.user,
                                      disposition_type=ser.validated_data['disposition_type'],
                                      description=ser.validated_data['description'])
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(MaterialLotSerializer(lot, context={'request': request}).data)

    @extend_schema(request=ShipBackSerializer, responses={200: MaterialLotSerializer})
    @action(detail=True, methods=['post'], url_path='ship-back')
    def ship_back(self, request, pk=None):
        """The dock ships a return-to-supplier lot back (→ Returned)."""
        from Tracker.services.qms.lot_reject import ship_back
        ser = ShipBackSerializer(data=request.data or {})
        ser.is_valid(raise_exception=True)
        try:
            lot, _ = ship_back(self.get_object(), request.user, note=ser.validated_data.get('note', ''))
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(MaterialLotSerializer(lot, context={'request': request}).data)

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
                    "and return the current verdict. Server-authoritative - the DWI "
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
        description="Receive N lots from a shipment (paste-grid). All-or-nothing - any row error rolls back.",
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
        # Rows with no lot number are numbered by us, consecutively, before validation.
        from Tracker.services.mes.material_lot import next_lot_numbers
        blank = [i for i, r in enumerate(rows)
                 if isinstance(r, dict) and not str(r.get('lot_number') or '').strip()]
        for i, number in zip(blank, next_lot_numbers(request.tenant, len(blank))):
            rows[i] = {**rows[i], 'lot_number': number}
        typed = [str(r.get('lot_number')).strip().lower() for r in rows if isinstance(r, dict)]
        dupes = {n for n in typed if typed.count(n) > 1}
        for idx, row in enumerate(rows):
            if isinstance(row, dict) and str(row.get('lot_number')).strip().lower() in dupes:
                per_row_errors.append({'index': idx, 'errors': {'lot_number': [
                    "This lot number is on more than one row."]}})
                continue
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
                    "tone, then age. Derive type-count chips (with oldest-age - "
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

class TimeEntryViewSet(TenantScopedMixin, DataExportMixin, viewsets.ModelViewSet):
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
        bom.effective_date = tenant_today(self.tenant)
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
        bom.obsolete_date = tenant_today(self.tenant)
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


# The one sheet a BOM imports from and exports to: each row a line, its BOM named by
# part type + revision + type (see services.mes.bom_import). Export labels ARE the
# import column names, so an exported file imports back.
_BOM_SHEET = [
    ('bom__part_type__name', 'part_type'), ('bom__revision', 'revision'),
    ('bom__bom_type', 'bom_type'), ('line_number', 'line_number'),
    ('component_type__name', 'component_type'), ('material__name', 'material'),
    ('quantity', 'quantity'), ('unit_of_measure', 'unit_of_measure'),
    ('source', 'source'), ('consumed_at_step__ref', 'consumed_at_step'),
    ('find_number', 'find_number'), ('reference_designator', 'reference_designator'),
    ('is_optional', 'is_optional'), ('allow_harvested', 'allow_harvested'),
    ('notes', 'notes'),
]


def _bom_template():
    from Tracker.services.template_generator import TemplateField, TemplateGenerator
    help_text = {
        'part_type': "The part this BOM builds (name or ERP id) — on every row of its BOM",
        'revision': "The BOM revision (a new draft revision if the released one differs)",
        'bom_type': "ASSEMBLY (default) or another BOM type",
        'component_type': "A part (name or ERP id) — or leave blank and name a material",
        'material': "A raw material (part number or name) — or name a component_type",
        'source': "MAKE or BUY",
        'consumed_at_step': "The step that consumes it: Process > Step",
    }
    required = {'part_type', 'quantity'}
    return TemplateGenerator(
        model_name="BOMLines",
        description=("One row per BOM line. The file is the COMPLETE line list for each BOM "
                     "it names; an import creates a draft, never releases it."),
        fields=[TemplateField(col, required=col in required, description=help_text.get(col, ''))
                for _, col in _BOM_SHEET])


class BOMLineViewSet(TenantScopedMixin, CSVImportMixin, DataExportMixin, viewsets.ModelViewSet):
    """BOM line item management — and BOM import/export, one sheet of lines."""
    queryset = BOMLine.unscoped.select_related('bom', 'component_type')
    serializer_class = BOMLineSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    # `bom__part_type`: the BOM export from a part type's page is that part type's
    # BOMs — without it, a part with no BOM yet exported every current BOM.
    filterset_fields = ['bom', 'bom__part_type', 'component_type', 'is_optional']
    ordering_fields = ['line_number', 'component_type__name']
    ordering = ['bom', 'line_number']

    export_fields = [path for path, _ in _BOM_SHEET]
    export_field_labels = {path: col for path, col in _BOM_SHEET}
    # The parent BOM's part type / revision / type name the sheet's BOM on every row.
    export_extra_paths = frozenset({'bom__part_type__name', 'bom__revision', 'bom__bom_type'})
    export_filename = 'bom_lines'
    csv_template_generator = _bom_template()
    # The import runs through services.mes.bom_import; this importer only tells the
    # template and preview which columns it reads beyond the line's own fields.
    csv_import_serializer = create_import_serializer_for_model(
        BOMLine, meta={'import_only_fields': ['part_type', 'revision', 'bom_type']})

    def get_export_queryset(self):
        """The lines of each part's current BOM only — older revisions would put two
        versions of one BOM in the file."""
        return (super().get_export_queryset()
                .filter(archived=False, bom__archived=False, bom__is_current_version=True)
                .order_by('bom__part_type__name', 'bom__revision', 'line_number'))

    def _process_import_inline(self, rows, mode, serializer_class, tenant, user):
        """A BOM's lines import together (services.mes.bom_import), not row by row."""
        from Tracker.services.mes.bom_import import import_bom_rows
        with transaction.atomic():
            body = import_bom_rows(rows, tenant=tenant, user=user,
                                   context=self.get_serializer_context())
        return Response(body, status=status.HTTP_207_MULTI_STATUS)

    def _queue_background_import(self, rows, mode, serializer_class, tenant, user):
        # A BOM file is lines of a handful of BOMs; each BOM must land whole, so it's
        # imported inline however many rows it has (the upload cap still applies).
        return self._process_import_inline(rows, mode, serializer_class, tenant, user)


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
