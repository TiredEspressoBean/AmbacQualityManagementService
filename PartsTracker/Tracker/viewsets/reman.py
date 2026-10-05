# viewsets/reman.py - Remanufacturing ViewSets
"""
ViewSets for remanufacturing models:
- Core: Incoming used units with disassembly workflow
- HarvestedComponent: Disassembled components with scrap/accept actions
- DisassemblyBOMLine: Expected disassembly yields
"""
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from Tracker.models import (
    Companies, Core, HarvestedComponent, DisassemblyBOMLine, PartTypes, RepairCode,
    RebuildScopePreset, RebuildSlotOverride,
)
from Tracker.serializers.reman import (
    CoreSerializer, CoreListSerializer, CoreScrapSerializer,
    CoreLotSerializer, CoreLotReceiveSerializer, CoreAssignIdentitySerializer,
    HarvestedComponentSerializer, HarvestedComponentScrapSerializer, HarvestedComponentAcceptSerializer,
    HarvestedComponentFindingDismissSerializer,
    DisassemblyBOMLineSerializer, RebuildPlanSerializer,
    RepairCodeSerializer, RebuildScopePresetSerializer, RebuildSlotOverrideSerializer,
)
from Tracker.serializers.csv_import import BaseCSVImportSerializer, create_import_serializer_for_model
from .base import TenantScopedMixin
from .mixins import CSVImportMixin, DataExportMixin, VersionHistoryMixin
from .scheduling_setup import ReviveOnCreateMixin


# ===== CORE VIEWSETS =====

class _CoreImport(BaseCSVImportSerializer):
    """Cores already in the building, from a sheet (the migration workbook's Cores).

    Created through `create_core`, as every core is, so none exists without its part.
    A core loads as Received: one further along moves through teardown in UQMES, which
    is what keeps its part, harvest and authorisation consistent. The fulfilment mode
    follows the customer's standing arrangement when the row leaves it blank, as at the
    receiving desk — and who it came from must be a customer (a supplier, for a core
    bought from a broker), or that arrangement could send a customer's own unit into
    the harvest pool.
    """

    def create_instance(self, data):
        from Tracker.services.reman.core import resolve_fulfilment_mode
        from Tracker.services.reman.core_part import create_core
        if data.get('status') not in (None, '', 'RECEIVED'):
            raise serializers.ValidationError({'status': (
                "A core loads as Received; take it through teardown in UQMES from there.")})
        data.pop('status', None)
        company = data.get('customer')
        if company is not None:
            bought = data.get('source_type') == 'PURCHASED'
            if bought and not company.is_supplier:
                raise serializers.ValidationError({'customer': (
                    f"{company.name} isn't set up as a supplier, so a core can't be bought from it.")})
            if not bought and not company.is_customer:
                raise serializers.ValidationError({'customer': (
                    f"{company.name} isn't set up as a customer.")})
        if not data.get('fulfilment_mode'):
            data['fulfilment_mode'], _ = resolve_fulfilment_mode(company)
        return create_core(tenant=self.tenant, received_by=self.user, **data)


class CoreViewSet(TenantScopedMixin, CSVImportMixin, DataExportMixin, viewsets.ModelViewSet):
    """
    Remanufacturing core management with disassembly workflow.

    Workflow:
    1. Create core (status: received)
    2. start_disassembly -> status: in_disassembly
    3. Create HarvestedComponents as components are extracted
    4. complete_disassembly -> status: disassembled

    Alternative: scrap -> status: scrapped (if core not suitable)
    """
    # The unit's position is its part's, so the work order and step are read through it.
    queryset = Core.unscoped.select_related('core_type', 'customer', 'received_by', 'disassembled_by',
                                            'part__work_order', 'part__step')
    serializer_class = CoreSerializer
    # A core is its number (blank: one is assigned). Customer by name, type by name or
    # part number.
    csv_import_serializer = create_import_serializer_for_model(
        Core, lookup_fields=['id', 'core_number'],
        extra_fk_fields={'customer': (Companies, ['name', 'id']),
                         'core_type': (PartTypes, ['name', 'ERP_id', 'id'])},
        # What a row must say; the part and receiver are create_core's to fill.
        meta={'required_fields': ['core_type', 'condition_grade']},
        base=_CoreImport)
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    search_fields = ['core_number', 'serial_number', 'source_reference']
    filterset_fields = ['status', 'condition_grade', 'source_type', 'customer', 'core_type']
    # `disassembly_completed_at` is what the rebuild queue ages on. An ordering field
    # that is not listed here is SILENTLY IGNORED by DRF and the queryset falls back to
    # `ordering` below — so the queue said "oldest first" and showed newest first.
    ordering_fields = [
        'received_date', 'core_number', 'status', 'disassembly_completed_at',
    ]
    ordering = ['-received_date']

    # Releasing is the terminal act of teardown, so it rides the perm that governs
    # completing one rather than adding a third codename for the same authority.
    action_permissions = {
        'release_to_rebuild': ['complete_disassembly'],
        'release_to_inventory': ['complete_disassembly'],
        # Gate and dispatch are core-lifecycle changes, gated on change_core rather
        # than inventing codenames for each transition.
        'request_authorisation_action': ['change_core'],
        'record_authorisation_action': ['change_core'],
        'return_to_customer': ['change_core'],
    }
    crud_exempt_actions = {
        'release_to_rebuild', 'release_to_inventory',
        'request_authorisation_action', 'record_authorisation_action',
        'return_to_customer',
    }

    def get_serializer_class(self):
        if self.action == 'list':
            return CoreListSerializer
        return CoreSerializer

    def perform_create(self, serializer):
        serializer.save(received_by=self.request.user)

    @extend_schema(
        request=inline_serializer(name="StartDisassemblyInput", fields={}),
        responses={200: CoreSerializer}
    )
    @action(detail=True, methods=['post'])
    def start_disassembly(self, request, pk=None):
        """Start disassembly of a core"""
        core = self.get_object()
        try:
            core.start_disassembly(user=request.user)
            return Response(CoreSerializer(core, context={'request': request}).data)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        request=inline_serializer(name="CompleteDisassemblyInput", fields={}),
        responses={200: CoreSerializer}
    )
    @action(detail=True, methods=['post'])
    def complete_disassembly(self, request, pk=None):
        """Complete disassembly of a core"""
        core = self.get_object()
        try:
            core.complete_disassembly(user=request.user)
            return Response(CoreSerializer(core, context={'request': request}).data)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(request=CoreScrapSerializer, responses={200: CoreSerializer})
    @action(detail=True, methods=['post'])
    def scrap(self, request, pk=None):
        """Scrap a core (not suitable for disassembly)"""
        core = self.get_object()
        serializer = CoreScrapSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            core.scrap(reason=serializer.validated_data.get('reason', ''))
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CoreSerializer(core, context={'request': request}).data)

    @extend_schema(
        request=inline_serializer(name="IssueCreditInput", fields={}),
        responses={200: CoreSerializer}
    )
    @action(detail=True, methods=['post'])
    def issue_credit(self, request, pk=None):
        """Issue core credit to customer"""
        core = self.get_object()
        try:
            core.issue_credit()
            return Response(CoreSerializer(core, context={'request': request}).data)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(responses={200: HarvestedComponentSerializer(many=True)})
    @action(detail=True, methods=['get'])
    def components(self, request, pk=None):
        """List all harvested components from this core"""
        core = self.get_object()
        components = core.harvested_components.all()
        return Response(HarvestedComponentSerializer(components, many=True, context={'request': request}).data)

    @extend_schema(
        request=None,
        responses={
            200: inline_serializer(name="CoreReleaseRebuild", fields={
                "core": CoreSerializer(),
                "first_step": serializers.CharField(allow_null=True),
                "operation_count": serializers.IntegerField(),
            }),
            400: inline_serializer(name="CoreReleaseRebuildError", fields={
                "detail": serializers.CharField(),
            }),
        },
        description="Release a repair-and-return core into rebuild on the same work "
                    "order the teardown ran on.",
    )
    @action(detail=True, methods=['post'], url_path='release_to_rebuild')
    def release_to_rebuild(self, request, pk=None):
        from django.core.exceptions import ValidationError as DjangoValidationError
        from Tracker.services.reman.release import release_core_to_rebuild

        core = self.get_object()
        try:
            core, plan = release_core_to_rebuild(core, request.user)
        except DjangoValidationError as e:
            return Response({'detail': '; '.join(e.messages)},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'core': CoreSerializer(core, context={'request': request}).data,
            'first_step': core.part.step.name if core.part.step_id else None,
            'operation_count': len(plan.operations),
        })

    @extend_schema(
        request=None,
        responses={
            200: inline_serializer(name="CoreReleaseInventory", fields={
                "core": CoreSerializer(),
                "accepted_count": serializers.IntegerField(),
                "accepted_part_ids": serializers.ListField(child=serializers.UUIDField()),
            }),
            400: inline_serializer(name="CoreReleaseInventoryError", fields={
                "detail": serializers.CharField(),
            }),
        },
        description="Accept this core's usable components into stock. The core is then "
                    "consumed — this is the exchange path, where the customer already "
                    "has a unit from stock.",
    )
    @action(detail=True, methods=['post'], url_path='release_to_inventory')
    def release_to_inventory(self, request, pk=None):
        from django.core.exceptions import ValidationError as DjangoValidationError
        from Tracker.services.reman.release import release_core_to_inventory

        core = self.get_object()
        try:
            core, accepted = release_core_to_inventory(core, request.user)
        except DjangoValidationError as e:
            return Response({'detail': '; '.join(e.messages)},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'core': CoreSerializer(core, context={'request': request}).data,
            'accepted_count': len(accepted),
            'accepted_part_ids': [p.id for p in accepted],
        })

    @extend_schema(
        request=inline_serializer(name="CoreAuthorisationInput", fields={
            "approved": serializers.BooleanField(),
            "note": serializers.CharField(required=False, allow_blank=True),
        }),
        responses={200: CoreSerializer, 400: inline_serializer(
            name="CoreAuthorisationError", fields={"detail": serializers.CharField()})},
        description="Record the customer's decision on over-and-above scope. The "
                    "conversation happens outside UQMES; this is the production record.",
    )
    @action(detail=True, methods=['post'], url_path='record_authorisation')
    def record_authorisation_action(self, request, pk=None):
        from django.core.exceptions import ValidationError as DjangoValidationError
        from Tracker.services.reman.release import record_authorisation

        core = self.get_object()
        try:
            core = record_authorisation(
                core, bool(request.data.get('approved')), request.user,
                note=request.data.get('note', ''))
        except DjangoValidationError as e:
            return Response({'detail': '; '.join(e.messages)},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(CoreSerializer(core, context={'request': request}).data)

    @extend_schema(
        request=None,
        responses={200: inline_serializer(name="CoreRequestAuthorisation", fields={
            "core": CoreSerializer(),
            "over_and_above": serializers.ListField(child=serializers.CharField()),
        }), 400: inline_serializer(
            name="CoreRequestAuthorisationError",
            fields={"detail": serializers.CharField()})},
        description="Pause a rebuild for customer authorisation of work beyond the "
                    "rebuild level that was sold.",
    )
    @action(detail=True, methods=['post'], url_path='request_authorisation')
    def request_authorisation_action(self, request, pk=None):
        from django.core.exceptions import ValidationError as DjangoValidationError
        from Tracker.services.reman.release import request_authorisation

        core = self.get_object()
        try:
            core, over = request_authorisation(core, request.user)
        except DjangoValidationError as e:
            return Response({'detail': '; '.join(e.messages)},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'core': CoreSerializer(core, context={'request': request}).data,
            'over_and_above': over,
        })

    @extend_schema(
        request=inline_serializer(name="CoreReturnInput", fields={
            "reference": serializers.CharField(required=False, allow_blank=True)}),
        responses={200: CoreSerializer, 400: inline_serializer(
            name="CoreReturnError", fields={"detail": serializers.CharField()})},
        description="Dispatch a unit back to its customer — repaired, or unrepaired "
                    "after a declined scope.",
    )
    @action(detail=True, methods=['post'], url_path='return_to_customer')
    def return_to_customer(self, request, pk=None):
        from django.core.exceptions import ValidationError as DjangoValidationError
        from Tracker.services.reman.release import return_core_to_customer

        core = self.get_object()
        try:
            core = return_core_to_customer(
                core, request.user, reference=request.data.get('reference', ''))
        except DjangoValidationError as e:
            return Response({'detail': '; '.join(e.messages)},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(CoreSerializer(core, context={'request': request}).data)

    @extend_schema(responses={200: RebuildPlanSerializer})
    @action(detail=True, methods=['get'], url_path='rebuild_plan')
    def rebuild_plan(self, request, pk=None):
        """Propose what goes back into this core, slot by slot.

        Read-only and side-effect free, so it can be asked of a core nobody has
        committed to rebuilding — which is also what lets the same call answer
        "what would this cost?" before teardown.
        """
        from dataclasses import asdict
        from Tracker.services.reman.rebuild import resolve_rebuild_plan

        core = self.get_object()
        plan = resolve_rebuild_plan(core)
        data = asdict(plan)
        # `needs_decision` is a property, so asdict() drops it — and it is the field
        # the screen collapses on.
        for slot, src in zip(data['slots'], plan.slots):
            slot['needs_decision'] = src.needs_decision
        return Response(RebuildPlanSerializer(data).data)

    @extend_schema(
        request=inline_serializer(name="CoreBulkCreateInput", fields={
            "cores": serializers.ListField(child=serializers.DictField(), allow_empty=False),
        }),
        responses={
            201: inline_serializer(name="CoreBulkCreateResponse", fields={
                "count": serializers.IntegerField(),
                "created_core_ids": serializers.ListField(child=serializers.UUIDField()),
            }),
            400: inline_serializer(name="CoreBulkCreateError", fields={
                "detail": serializers.CharField(required=False),
                "errors": serializers.ListField(child=serializers.DictField(), required=False),
            }),
        },
        description="Create N cores from a shipment. All-or-nothing - any row error rolls back the batch.",
    )
    @action(detail=False, methods=['post'], url_path='bulk_create')
    def bulk_create(self, request):
        """Bulk-create cores. Atomic: all rows validate and save together, or none do."""
        rows = request.data.get('cores')
        if not isinstance(rows, list) or len(rows) == 0:
            return Response(
                {"detail": "cores must be a non-empty list"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ctx = {'request': request}
        per_row_errors = []
        serializer_instances = []
        for idx, row in enumerate(rows):
            ser = CoreSerializer(data=row, context=ctx)
            if ser.is_valid():
                serializer_instances.append(ser)
            else:
                per_row_errors.append({'index': idx, 'errors': ser.errors})

        if per_row_errors:
            return Response(
                {"detail": "Validation failed", "errors": per_row_errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                created = [ser.save(received_by=request.user) for ser in serializer_instances]
        except Exception as exc:
            return Response(
                {"detail": "Bulk create failed", "errors": [{"index": -1, "errors": str(exc)}]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "count": len(created),
                "created_core_ids": [str(c.id) for c in created],
            },
            status=status.HTTP_201_CREATED,
        )

    # ----- bulk core lots (Documents/CORE_AS_PART_DESIGN.md §6) -----------------------

    @extend_schema(
        request=CoreLotReceiveSerializer,
        responses={201: CoreLotSerializer},
        description=(
            "Receive unidentified cores in bulk as one lot of the core type. Exchange "
            "only: a repair-and-return customer's units must be received individually."
        ),
    )
    @action(detail=False, methods=['post'], url_path='receive_lot')
    def receive_lot(self, request):
        from Tracker.services.reman.core_lot import receive_core_lot

        ser = CoreLotReceiveSerializer(data=request.data, context={'request': request})
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        try:
            lot = receive_core_lot(
                tenant=self.tenant, core_type=d['core_type'], quantity=d['quantity'],
                received_by=request.user, customer=d.get('customer'),
                received_date=d.get('received_date'), lot_number=d.get('lot_number', ''),
                storage_location=d.get('storage_location', ''),
                source_reference=d.get('source_reference', ''),
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CoreLotSerializer(lot).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=CoreAssignIdentitySerializer,
        responses={201: CoreSerializer},
        description=(
            "Take one unit off a bulk core lot and give it an identity: its core number, "
            "part and core role. From then on it is an ordinary (exchange) core."
        ),
    )
    @action(detail=False, methods=['post'], url_path='assign_identity')
    def assign_identity(self, request):
        from Tracker.models import MaterialLot
        from Tracker.services.reman.core_lot import assign_core_identity

        ser = CoreAssignIdentitySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        lot = MaterialLot.objects.filter(pk=d['lot']).first()  # tenant-safe: .objects auto-scopes to the request tenant
        if lot is None:
            return Response({'detail': 'Lot not found'}, status=status.HTTP_404_NOT_FOUND)
        try:
            core = assign_core_identity(
                lot, user=request.user, condition_grade=d['condition_grade'],
                serial_number=d.get('serial_number', ''),
                condition_notes=d.get('condition_notes', ''),
                source_type=d.get('source_type', 'CUSTOMER_RETURN'),
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CoreSerializer(core, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)

    @extend_schema(
        responses={200: CoreLotSerializer(many=True)},
        description="Bulk core lots with units still to be given an identity, oldest first.",
    )
    # A short, whole list — the lots still being identified — so neither paginated nor
    # filtered. Declared on the action, or the schema would promise the viewset's
    # pagination and Core filters and the generated client would reject the array.
    @action(detail=False, methods=['get'], url_path='lots',
            pagination_class=None, filter_backends=[])
    def lots(self, request):
        from Tracker.services.reman.core_lot import bank_lots

        return Response(CoreLotSerializer(bank_lots(self.tenant), many=True).data)

    @extend_schema(
        request=inline_serializer(name="CoreStartTeardownBatchInput", fields={
            "core_ids": serializers.ListField(child=serializers.UUIDField(), allow_empty=False),
            "process_id": serializers.UUIDField(required=False),
        }),
        responses={
            201: inline_serializer(name="CoreStartTeardownBatchResponse", fields={
                "work_order_id": serializers.UUIDField(),
                "work_order_erp_id": serializers.CharField(),
                "transitioned_core_ids": serializers.ListField(child=serializers.UUIDField()),
            }),
        },
        description=(
            "Create one teardown WorkOrder that links the given cores and "
            "transitions each from RECEIVED to IN_DISASSEMBLY. All-or-nothing."
        ),
    )
    @action(detail=False, methods=['post'], url_path='start_teardown_batch')
    def start_teardown_batch(self, request):
        from Tracker.models import Processes
        from Tracker.services.reman.teardown import start_teardown_batch as svc

        core_ids = request.data.get('core_ids') or []
        process_id = request.data.get('process_id')
        if not isinstance(core_ids, list) or not core_ids:
            return Response(
                {"detail": "core_ids must be a non-empty list"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cores = list(Core.objects.filter(id__in=core_ids).select_related('core_type', 'tenant'))
        if len(cores) != len(set(core_ids)):
            return Response(
                {"detail": "One or more core_ids not found in this tenant"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        process = None
        if process_id:
            process = Processes.objects.filter(id=process_id).first()
            if process is None:
                return Response(
                    {"detail": "process_id not found in this tenant"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            wo = svc(cores=cores, user=request.user, process=process)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "work_order_id": str(wo.id),
                "work_order_erp_id": wo.ERP_id,
                "transitioned_core_ids": [str(c.id) for c in cores],
            },
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=inline_serializer(name="CorePlanTeardownInput", fields={
            "core_ids": serializers.ListField(child=serializers.UUIDField(), allow_empty=False),
            # When the teardown should begin — the proposal's start-by date. Optional:
            # without one the work order is planned undated and the scheduler places it.
            "start_by": serializers.DateField(required=False, allow_null=True),
            "process_id": serializers.UUIDField(required=False),
        }),
        responses={
            201: inline_serializer(name="CorePlanTeardownResponse", fields={
                "work_order_id": serializers.UUIDField(),
                "work_order_erp_id": serializers.CharField(),
                "planned_core_ids": serializers.ListField(child=serializers.UUIDField()),
            }),
        },
        description=(
            "Accept a teardown proposal: create one PENDING teardown WorkOrder dated to "
            "`start_by` that links the given cores WITHOUT starting disassembly. The "
            "cores stay RECEIVED until an operator starts the first step. All-or-nothing; "
            "the same rules as start_teardown_batch."
        ),
    )
    @action(detail=False, methods=['post'], url_path='plan_teardown')
    def plan_teardown(self, request):
        from datetime import date as _date
        from Tracker.models import Processes
        from Tracker.services.reman.teardown import plan_teardown as svc

        core_ids = request.data.get('core_ids') or []
        if not isinstance(core_ids, list) or not core_ids:
            return Response(
                {"detail": "core_ids must be a non-empty list"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        start_by = request.data.get('start_by')
        if start_by:
            try:
                start_by = _date.fromisoformat(str(start_by))
            except ValueError:
                return Response({"detail": "start_by must be an ISO date (YYYY-MM-DD)"},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            start_by = None

        cores = list(Core.objects.filter(id__in=core_ids).select_related('core_type', 'tenant'))
        if len(cores) != len(set(core_ids)):
            return Response(
                {"detail": "One or more core_ids not found in this tenant"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        process = None
        process_id = request.data.get('process_id')
        if process_id:
            process = Processes.objects.filter(id=process_id).first()
            if process is None:
                return Response(
                    {"detail": "process_id not found in this tenant"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            wo = svc(cores, request.user, start_by=start_by, process=process)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "work_order_id": str(wo.id),
                "work_order_erp_id": wo.ERP_id,
                "planned_core_ids": [str(c.id) for c in cores],
            },
            status=status.HTTP_201_CREATED,
        )


# ===== HARVESTED COMPONENT VIEWSETS =====

class HarvestedComponentViewSet(TenantScopedMixin, DataExportMixin, viewsets.ModelViewSet):
    """
    Harvested component management.

    Components are created during core disassembly, then either:
    - accept_to_inventory -> Creates a Parts record for reuse
    - scrap -> Marks as scrapped
    """
    queryset = HarvestedComponent.unscoped.select_related(
        'core', 'component_type', 'component_part', 'disassembled_by', 'scrapped_by'
    )
    serializer_class = HarvestedComponentSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    search_fields = ['position', 'original_part_number']
    filterset_fields = ['core', 'component_type', 'condition_grade', 'is_scrapped']
    ordering_fields = ['disassembled_at', 'condition_grade']
    ordering = ['-disassembled_at']

    # `grade_component`, `accept_component` and `reject_component` were declared on the
    # model and enforced nowhere, so the CRUD default decided all three: anyone who
    # could add a harvested component could also put one into inventory. Declaring them
    # here is what turns them from labels into gates.
    #
    # Recording is separated from acting. Creating or editing a component carries its
    # condition grade, and the tech holding the part is the one who can see it —
    # `grade_component` ships with the general operational grant, so this changes who
    # *can* grade for nobody today; it makes the lever exist for a tenant that wants it.
    #
    # Accept and scrap are dispositions: one makes a used part available to be built
    # into customer product on the strength of that grade, the other destroys it. Both
    # are crud-exempt because neither is "adding a harvested component" — accept creates
    # a Parts record, scrap retires one — so the marker perm is the sole, sufficient
    # gate rather than an additive one on top of a CRUD perm that misdescribes the act.
    action_permissions = {
        'create': ['grade_component'],
        'update': ['grade_component'],
        'partial_update': ['grade_component'],
        'accept_to_inventory': ['accept_component'],
        'scrap': ['reject_component'],
        # Deciding a finding is ACTING on an observation, not making one: it decides
        # what goes back into the unit, and so the scope. That is a component
        # disposition (QA / lead tier — see COMPONENT_DISPOSITION_PERMISSIONS in
        # presets.py), not the operator's `grade_component`, which only records.
        'apply_finding': ['accept_component'],
        'dismiss_finding': ['accept_component'],
    }
    crud_exempt_actions = {'accept_to_inventory', 'scrap', 'apply_finding', 'dismiss_finding'}

    def perform_create(self, serializer):
        serializer.save(disassembled_by=self.request.user)

    @extend_schema(
        request=None,
        responses={200: HarvestedComponentSerializer},
        description="Apply the finding waiting on this component: it takes the proposed "
                    "grade, and the unit's rebuild plan re-resolves from it.",
    )
    @action(detail=True, methods=['post'])
    def apply_finding(self, request, pk=None):
        from Tracker.services.reman.findings import apply_finding
        component = apply_finding(self.get_object(), user=request.user)
        return Response(HarvestedComponentSerializer(component, context={'request': request}).data)

    @extend_schema(
        request=HarvestedComponentFindingDismissSerializer,
        responses={200: HarvestedComponentSerializer},
        description="Dismiss the finding waiting on this component; the grade stays. "
                    "The reason is kept on the component's notes.",
    )
    @action(detail=True, methods=['post'])
    def dismiss_finding(self, request, pk=None):
        from Tracker.services.reman.findings import dismiss_finding
        ser = HarvestedComponentFindingDismissSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        component = dismiss_finding(self.get_object(), user=request.user,
                                    reason=ser.validated_data['reason'])
        return Response(HarvestedComponentSerializer(component, context={'request': request}).data)

    @extend_schema(request=HarvestedComponentScrapSerializer, responses={200: HarvestedComponentSerializer})
    @action(detail=True, methods=['post'])
    def scrap(self, request, pk=None):
        """Scrap a harvested component"""
        component = self.get_object()

        serializer = HarvestedComponentScrapSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            component.scrap(user=request.user, reason=serializer.validated_data.get('reason', ''))
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(HarvestedComponentSerializer(component, context={'request': request}).data)

    @extend_schema(
        request=HarvestedComponentAcceptSerializer,
        responses={200: inline_serializer(
            name="AcceptToInventoryResponse",
            fields={
                'component': HarvestedComponentSerializer(),
                'part_id': serializers.UUIDField(),
                'part_erp_id': serializers.CharField(),
            }
        )}
    )
    @action(detail=True, methods=['post'])
    def accept_to_inventory(self, request, pk=None):
        """Accept a harvested component into inventory as a Part"""
        component = self.get_object()

        serializer = HarvestedComponentAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            part = component.accept_to_inventory(
                user=request.user,
                erp_id=serializer.validated_data.get('erp_id')
            )
            return Response({
                'component': HarvestedComponentSerializer(component, context={'request': request}).data,
                'part_id': part.id,
                'part_erp_id': part.ERP_id
            })
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ===== DISASSEMBLY BOM LINE VIEWSETS =====

class DisassemblyBOMLineViewSet(ReviveOnCreateMixin, TenantScopedMixin, viewsets.ModelViewSet):
    """Disassembly BOM line management (expected yields from cores)"""
    # A removed line keeps its (core, component) key, so adding it back revives it.
    revive_key = ('core_type', 'component_type')
    queryset = DisassemblyBOMLine.unscoped.select_related('core_type', 'component_type')
    serializer_class = DisassemblyBOMLineSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['core_type', 'component_type']
    ordering_fields = ['line_number', 'expected_qty']
    ordering = ['core_type', 'line_number']


class RepairCodeViewSet(VersionHistoryMixin, TenantScopedMixin, CSVImportMixin, DataExportMixin,
                        viewsets.ModelViewSet):
    """Repair codes — what operations a finding adds to a rebuild."""
    queryset = RepairCode.unscoped.select_related('component_type').prefetch_related('steps')
    serializer_class = RepairCodeSerializer
    # A code is matched on its code (unique among current versions); `component_type`
    # is found by part type name; `steps` is `Process > Step; Process > Step`. Edits
    # version the way the serializer's do (apply_versioned_update); a new version keeps
    # its steps.
    csv_import_serializer = create_import_serializer_for_model(
        RepairCode, lookup_fields=['id', 'code'])
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['component_type', 'trigger']
    search_fields = ['code', 'name']
    ordering_fields = ['code', 'trigger']
    ordering = ['code']


class RebuildScopePresetViewSet(VersionHistoryMixin, TenantScopedMixin, viewsets.ModelViewSet):
    """Named rebuild levels — the entry scope before any finding."""
    queryset = RebuildScopePreset.unscoped.select_related('core_type').prefetch_related('codes')
    serializer_class = RebuildScopePresetSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['core_type', 'is_default']
    search_fields = ['name']
    ordering_fields = ['name']
    ordering = ['core_type', 'name']


class RebuildSlotOverrideViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Planner decisions that differ from the proposed rebuild plan."""
    queryset = RebuildSlotOverride.unscoped.select_related(
        'core', 'bom_line', 'overridden_by')
    serializer_class = RebuildSlotOverrideSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['core', 'bom_line', 'resolution']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        # Attribution comes from the request, never the payload — an override is a
        # person's decision and a client should not be able to sign it as someone else.
        serializer.save(overridden_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(overridden_by=self.request.user)
