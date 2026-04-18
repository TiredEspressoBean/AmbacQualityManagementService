from django.urls import path, include
from rest_framework.routers import DefaultRouter

from integrations.webhooks.views import integration_webhook
from integrations.viewsets import (
    IntegrationConfigViewSet,
    IntegrationSyncLogViewSet,
    HubSpotPipelineStageViewSet,
)

router = DefaultRouter()
router.register(r'integrations', IntegrationConfigViewSet, basename='integrations')
router.register(r'integration-sync-logs', IntegrationSyncLogViewSet, basename='integration-sync-logs')
router.register(r'hubspot-pipeline-stages', HubSpotPipelineStageViewSet, basename='hubspot-pipeline-stages')

urlpatterns = [
    # Webhook receiver: /webhooks/<provider>/<integration_id>/
    path(
        'webhooks/<str:provider>/<uuid:integration_id>/',
        integration_webhook,
        name='integration_webhook'
    ),

    # API endpoints
    path('api/', include(router.urls)),
]
