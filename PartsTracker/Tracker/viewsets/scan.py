"""Scan lookup — one endpoint every scan field asks (services/core/scan.py)."""
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from Tracker.permissions import TenantAccessPermission
from Tracker.serializers.locations import ScanResultSerializer
from Tracker.services.core.scan import resolve_scan


class ScanViewSet(viewsets.ViewSet):
    """Turns a scanned (or typed) code into what it names. Only tenant membership is
    asked: the answer is an id and a path, and the page it leads to checks its own
    permission."""
    permission_classes = [IsAuthenticated, TenantAccessPermission]

    @extend_schema(parameters=[OpenApiParameter('code', str, required=True)],
                   responses={200: ScanResultSerializer, 404: None},
                   description="Resolve a scanned code: a label QR URL, LOC:<location>, "
                               "a lot number, a serial, a work-order number or a location name.")
    def list(self, request):
        found = resolve_scan(request.tenant, request.query_params.get('code', ''))
        if found is None:
            return Response({'detail': 'Nothing matches that code.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(ScanResultSerializer(found).data)
