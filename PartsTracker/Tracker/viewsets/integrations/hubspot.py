# viewsets/integrations/hubspot.py - HubSpot Integration ViewSets
from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework import viewsets

from Tracker.models.core import ExternalAPIOrderIdentifier
from Tracker.serializers.integrations.hubspot import ExternalAPIOrderIdentifierSerializer
from ..core import ExcelExportMixin


@extend_schema_view(
    list=extend_schema(summary="List HubSpot gates/milestones"),
    retrieve=extend_schema(summary="Get HubSpot gate details"),
    create=extend_schema(summary="Create HubSpot gate"),
    update=extend_schema(summary="Update HubSpot gate"),
    partial_update=extend_schema(summary="Partially update HubSpot gate"),
    destroy=extend_schema(summary="Delete HubSpot gate"),
)
class HubspotGatesViewSet(ExcelExportMixin, viewsets.ModelViewSet):
    """ViewSet for managing HubSpot gate/milestone data"""
    serializer_class = ExternalAPIOrderIdentifierSerializer
    pagination_class = None

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ExternalAPIOrderIdentifier.objects.none()

        return ExternalAPIOrderIdentifier.objects.for_user(self.request.user)
