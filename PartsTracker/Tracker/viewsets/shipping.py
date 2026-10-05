"""Customer shipments — the outbound dock. Logic lives in services/mes/shipping.py."""
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from Tracker.models import Companies, CustomerShipment, Orders, Parts
from Tracker.serializers.shipping import (
    CustomerShipmentSerializer,
    DeliveryPerformanceSerializer,
    OrderShippingSerializer,
    ReadyToShipOrderSerializer,
    ShipRequestSerializer,
    VoidShipmentRequestSerializer,
)
from Tracker.services.mes import shipping
from Tracker.viewsets.base import TenantScopedMixin
from Tracker.viewsets.mixins import DataExportMixin


class CustomerShipmentViewSet(TenantScopedMixin, DataExportMixin, mixins.ListModelMixin,
                              mixins.RetrieveModelMixin, mixins.UpdateModelMixin,
                              viewsets.GenericViewSet):
    """Shipments to customers. Created only by `ship`; corrected by PATCH (paperwork
    fields) or retracted by `void` — never deleted."""
    queryset = (CustomerShipment.unscoped.select_related('customer', 'shipped_by')
                .prefetch_related('parts__part_type', 'parts__work_order__related_order', 'parts__order'))
    serializer_class = CustomerShipmentSerializer
    http_method_names = ['get', 'post', 'patch', 'head', 'options']
    filter_backends = [DjangoFilterBackend, OrderingFilter, filters.SearchFilter]
    search_fields = ['shipment_number', 'reference', 'tracking_number', 'customer__name', 'parts__ERP_id']
    filterset_fields = ['customer', 'is_voided']
    ordering_fields = ['shipped_at', 'shipment_number']
    ordering = ['-shipped_at']

    action_permissions = {
        'ship': ['add_customershipment'],
        'void': ['change_customershipment'],
    }
    # void retracts an existing shipment → gated by change_ alone, not POST→add.
    crud_exempt_actions = {'void'}

    @extend_schema(responses=ReadyToShipOrderSerializer(many=True),
                   description="Parts that can ship now — at a Ship step or finished to stock — "
                               "grouped by order (one customer each).")
    @action(detail=False, methods=['get'], url_path='ready', pagination_class=None, filter_backends=[])
    def ready(self, request):
        return Response(ReadyToShipOrderSerializer(shipping.ready_to_ship(request.tenant), many=True).data)

    @extend_schema(request=ShipRequestSerializer, responses={201: CustomerShipmentSerializer},
                   description="Ship parts to one customer on one shipment. Parts at a Ship step "
                               "complete it (its sign-off gate runs); all or nothing.")
    @action(detail=False, methods=['post'], url_path='ship')
    def ship(self, request):
        req = ShipRequestSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        d = req.validated_data
        customer = None
        if d.get('customer'):
            customer = Companies.objects.filter(pk=d['customer']).first()  # tenant-safe: .objects auto-scopes (request context)
            if customer is None:
                return Response({'detail': 'Customer not found.'}, status=status.HTTP_400_BAD_REQUEST)
        parts = list(Parts.objects.filter(pk__in=d['part_ids']))  # tenant-safe: .objects auto-scopes (request context)
        try:
            shipment = shipping.ship_parts(
                tenant=request.tenant, parts=parts, user=request.user, customer=customer,
                carrier=d['carrier'], tracking_number=d['tracking_number'],
                reference=d['reference'], notes=d['notes'],
                expected_delivery=d.get('expected_delivery'))
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(shipment).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=VoidShipmentRequestSerializer, responses=CustomerShipmentSerializer,
                   description="A shipment recorded by mistake: its parts go back to the Ship "
                               "step or to stock, and anything it closed reopens.")
    @action(detail=True, methods=['post'], url_path='void')
    def void(self, request, pk=None):
        shipment = self.get_object()
        req = VoidShipmentRequestSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        try:
            shipping.void_shipment(shipment, user=request.user, reason=req.validated_data['reason'])
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        shipment.refresh_from_db()
        return Response(self.get_serializer(shipment).data)

    @extend_schema(parameters=[OpenApiParameter('order', str, required=True)],
                   responses=OrderShippingSerializer,
                   description="Per order line: ordered, shipped, and each shipment's date and "
                               "whether it met the line's due date.")
    @action(detail=False, methods=['get'], url_path='order-shipping', pagination_class=None, filter_backends=[])
    def order_shipping(self, request):
        order = Orders.objects.filter(pk=request.query_params.get('order')).first()  # tenant-safe: .objects auto-scopes (request context)
        if order is None:
            return Response({'detail': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(OrderShippingSerializer(shipping.order_shipping(order)).data)

    @extend_schema(parameters=[OpenApiParameter('days', int, required=False)],
                   responses=DeliveryPerformanceSerializer,
                   description="On-time delivery to customers over the last N days (default 90).")
    @action(detail=False, methods=['get'], url_path='delivery-performance',
            pagination_class=None, filter_backends=[])
    def delivery_performance(self, request):
        try:
            days = max(1, min(int(request.query_params.get('days', 90)), 730))
        except ValueError:
            days = 90
        return Response(DeliveryPerformanceSerializer(
            shipping.delivery_performance(request.tenant, days)).data)
