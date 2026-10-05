"""Receipts for the ERP: the deliveries in a date range with their ERP status, and
marking them posted once a person has keyed them in (services.mes.receipt_export). The
.xlsx download is MaterialLots/receipts-export/."""
from django.utils.dateparse import parse_date
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from Tracker.permissions import TenantAccessPermission
from Tracker.serializers.receipts import (
    MarkReceiptsPostedResultSerializer,
    MarkReceiptsPostedSerializer,
    ReceiptRowSerializer,
)

_KEYS = {
    "lot_id": "lot_id", "our_lot": "Our Lot", "po_number": "PO Number", "po_line": "PO Line",
    "received": "Received", "item": "Item", "item_name": "Item Name", "supplier": "Supplier",
    "unit": "Unit", "received_qty": "Received Qty", "accepted": "Accepted",
    "rejected": "Rejected", "awaiting_decision": "Awaiting Decision", "decision": "Decision",
    "erp_status": "erp_status",
}


class ReceiptsViewSet(viewsets.ViewSet):
    # Lot permissions, checked per action: seeing receipts is viewing lots; recording
    # that they were posted is changing them.
    permission_classes = [IsAuthenticated, TenantAccessPermission]

    @extend_schema(
        parameters=[
            OpenApiParameter('start', OpenApiTypes.DATE, required=True),
            OpenApiParameter('end', OpenApiTypes.DATE, required=True),
            OpenApiParameter('po_only', OpenApiTypes.BOOL, required=False),
            OpenApiParameter('unposted_only', OpenApiTypes.BOOL, required=False,
                             description="Leave out deliveries already posted, unchanged."),
        ],
        responses={200: ReceiptRowSerializer(many=True)},
        description="Deliveries received in a date range, each with its ERP status.",
    )
    def list(self, request):
        from Tracker.services.mes.receipt_export import receipt_rows
        if not request.user.has_tenant_perm("view_materiallot"):
            return Response({'detail': "Viewing receipts needs view_materiallot."},
                            status=status.HTTP_403_FORBIDDEN)
        start = parse_date(request.query_params.get('start') or '')
        end = parse_date(request.query_params.get('end') or '')
        if start is None or end is None or start > end:
            return Response({'detail': 'Give a start and end date (YYYY-MM-DD), start first.'},
                            status=status.HTTP_400_BAD_REQUEST)
        flag = lambda k: str(request.query_params.get(k, '')).lower() in ('1', 'true', 'yes')
        rows = receipt_rows(request.tenant, start, end, with_po_only=flag('po_only'),
                            unposted_only=flag('unposted_only'))
        data = [{k: r[src] for k, src in _KEYS.items()} for r in rows]
        return Response(ReceiptRowSerializer(data, many=True).data)

    @extend_schema(request=MarkReceiptsPostedSerializer,
                   responses={200: MarkReceiptsPostedResultSerializer},
                   description=("Record that these deliveries were keyed into the ERP, with the "
                                "numbers posted. Ones still awaiting a decision are skipped."))
    @action(detail=False, methods=['post'], url_path='mark-posted')
    def mark_posted(self, request):
        from Tracker.services.mes.receipt_export import mark_posted
        if not request.user.has_tenant_perm("change_materiallot"):
            return Response({'detail': "Marking receipts posted needs change_materiallot."},
                            status=status.HTTP_403_FORBIDDEN)
        ser = MarkReceiptsPostedSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        marked = mark_posted(request.tenant, [str(i) for i in ser.validated_data['lot_ids']],
                             user=request.user)
        return Response(MarkReceiptsPostedResultSerializer({'marked': marked}).data)
