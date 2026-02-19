# viewsets/reman.py - Remanufacturing ViewSets
"""
ViewSets for remanufacturing models:
- Core: Incoming used units with disassembly workflow
- HarvestedComponent: Disassembled components with scrap/accept actions
- DisassemblyBOMLine: Expected disassembly yields
"""
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from Tracker.models import Core, HarvestedComponent, DisassemblyBOMLine
from Tracker.serializers.reman import (
    CoreSerializer, CoreListSerializer, CoreScrapSerializer,
    HarvestedComponentSerializer, HarvestedComponentScrapSerializer, HarvestedComponentAcceptSerializer,
    DisassemblyBOMLineSerializer,
)
from .base import TenantScopedMixin
from .core import ExcelExportMixin


# ===== CORE VIEWSETS =====

class CoreViewSet(TenantScopedMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """
    Remanufacturing core management with disassembly workflow.

    Workflow:
    1. Create core (status: received)
    2. start_disassembly -> status: in_disassembly
    3. Create HarvestedComponents as components are extracted
    4. complete_disassembly -> status: disassembled

    Alternative: scrap -> status: scrapped (if core not suitable)
    """
    queryset = Core.objects.select_related('core_type', 'customer', 'received_by', 'disassembled_by', 'work_order')
    serializer_class = CoreSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    search_fields = ['core_number', 'serial_number', 'source_reference']
    filterset_fields = ['status', 'condition_grade', 'source_type', 'customer', 'core_type']
    ordering_fields = ['received_date', 'core_number', 'status']
    ordering = ['-received_date']

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
        if core.status == 'scrapped':
            return Response({'detail': 'Core is already scrapped'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = CoreScrapSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        core.scrap(reason=serializer.validated_data.get('reason', ''))
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


# ===== HARVESTED COMPONENT VIEWSETS =====

class HarvestedComponentViewSet(TenantScopedMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """
    Harvested component management.

    Components are created during core disassembly, then either:
    - accept_to_inventory -> Creates a Parts record for reuse
    - scrap -> Marks as scrapped
    """
    queryset = HarvestedComponent.objects.select_related(
        'core', 'component_type', 'component_part', 'disassembled_by', 'scrapped_by'
    )
    serializer_class = HarvestedComponentSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    search_fields = ['position', 'original_part_number']
    filterset_fields = ['core', 'component_type', 'condition_grade', 'is_scrapped']
    ordering_fields = ['disassembled_at', 'condition_grade']
    ordering = ['-disassembled_at']

    def perform_create(self, serializer):
        serializer.save(disassembled_by=self.request.user)

    @extend_schema(request=HarvestedComponentScrapSerializer, responses={200: HarvestedComponentSerializer})
    @action(detail=True, methods=['post'])
    def scrap(self, request, pk=None):
        """Scrap a harvested component"""
        component = self.get_object()
        if component.is_scrapped:
            return Response({'detail': 'Component already scrapped'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = HarvestedComponentScrapSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        component.scrap(user=request.user, reason=serializer.validated_data.get('reason', ''))
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

class DisassemblyBOMLineViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Disassembly BOM line management (expected yields from cores)"""
    queryset = DisassemblyBOMLine.objects.select_related('core_type', 'component_type')
    serializer_class = DisassemblyBOMLineSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['core_type', 'component_type']
    ordering_fields = ['line_number', 'expected_qty']
    ordering = ['core_type', 'line_number']
