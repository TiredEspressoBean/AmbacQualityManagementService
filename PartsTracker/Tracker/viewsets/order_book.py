"""Production › Orders — the staff order book and order page (read-only). The rows
come from services/mes/order_book; planning stays on the existing order-line actions."""
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from Tracker.models import Orders
from Tracker.serializers.order_book import OrderBookSerializer, OrderDetailSerializer
from Tracker.viewsets.base import TenantScopedMixin


class OrderBookViewSet(TenantScopedMixin, viewsets.GenericViewSet):
    """Open customer demand, its progress, and whether it will make its promise.

    Permissioned on `view_orders` (TenantModelPermissions derives it from the
    queryset's model). Every figure is scoped to what the viewer may see (`for_user`)."""
    queryset = Orders.unscoped.none()
    serializer_class = OrderBookSerializer
    pagination_class = None

    # An action, not `list`: the book is one object (rows + on-time delivery), and the
    # schema generator types any `list` as an array.
    @extend_schema(responses=OrderBookSerializer)
    @action(detail=False, methods=['get'], url_path='book', pagination_class=None)
    def book(self, request, *args, **kwargs):
        from Tracker.services.mes.order_book import order_book
        return Response(OrderBookSerializer(order_book(request.user, self.tenant)).data)

    @extend_schema(responses=OrderDetailSerializer)
    def retrieve(self, request, pk=None, *args, **kwargs):
        from Tracker.services.mes.order_book import order_detail
        order = (Orders.objects.for_user(request.user)  # scoped to what the user may see
                 .filter(pk=pk, archived=False).select_related('company').first())
        if order is None:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(OrderDetailSerializer(order_detail(order, request.user)).data)
