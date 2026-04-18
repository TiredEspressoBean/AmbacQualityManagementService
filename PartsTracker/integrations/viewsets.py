"""
Integration app viewsets.

IntegrationConfigViewSet: CRUD + test_connection + trigger_sync + health
IntegrationSyncLogViewSet: Read-only sync history
HubSpotPipelineStageViewSet: Read-only pipeline stages
"""

from rest_framework import viewsets, status, serializers as drf_serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from drf_spectacular.utils import extend_schema, inline_serializer

from integrations.models import (
    IntegrationConfig, IntegrationSyncLog, HubSpotPipelineStage,
)
from integrations.serializers import (
    IntegrationConfigSerializer, IntegrationConfigListSerializer,
    IntegrationSyncLogSerializer, HubSpotPipelineStageSerializer,
)
from integrations.services.registry import get_adapter, get_all_adapters, discover_capabilities


class IntegrationConfigViewSet(viewsets.ModelViewSet):
    """
    CRUD for integration management.
    Scoped to the request user's tenant. Admin/staff only.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = IntegrationConfigSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return IntegrationConfig.objects.none()
        return IntegrationConfig.objects.filter(tenant=self.request.user.tenant)

    def get_serializer_class(self):
        if self.action == 'list':
            return IntegrationConfigListSerializer
        return IntegrationConfigSerializer

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)

    @extend_schema(
        responses=inline_serializer(
            name='IntegrationCatalogItem',
            fields={
                # Identity
                'provider': drf_serializers.CharField(),
                'name': drf_serializers.CharField(),
                'category': drf_serializers.CharField(),
                'description': drf_serializers.CharField(),
                'long_description': drf_serializers.CharField(),
                'icon': drf_serializers.CharField(),
                'capabilities': drf_serializers.ListField(child=drf_serializers.CharField()),
                # Auth
                'auth_type': drf_serializers.CharField(),
                'auth_label': drf_serializers.CharField(),
                'auth_instructions': drf_serializers.CharField(),
                'auth_docs_url': drf_serializers.CharField(),
                # Details
                'data_flows': drf_serializers.ListField(child=drf_serializers.DictField()),
                'sync_details': drf_serializers.DictField(),
                'requirements': drf_serializers.ListField(child=drf_serializers.CharField()),
                'creates': drf_serializers.ListField(child=drf_serializers.CharField()),
                'limitations': drf_serializers.ListField(child=drf_serializers.CharField()),
                # Status
                'status': drf_serializers.CharField(),
                'config_id': drf_serializers.CharField(allow_null=True),
                'is_enabled': drf_serializers.BooleanField(),
                'display_name': drf_serializers.CharField(),
                'sync_status': drf_serializers.CharField(allow_null=True),
                'last_synced_at': drf_serializers.CharField(allow_null=True),
                'last_sync_error': drf_serializers.CharField(allow_null=True),
                'last_sync_stats': drf_serializers.DictField(allow_null=True),
            },
            many=True,
        )
    )
    @action(detail=False, methods=['get'], pagination_class=None)
    def catalog(self, request):
        """
        Returns all available integrations merged with their configuration status
        for the current tenant.

        Each item includes:
        - Adapter manifest (name, description, icon, auth_type, capabilities)
        - Configuration status (not_configured, configured, connected, error)
        - IntegrationConfig data if configured (id, is_enabled, sync_status, last_synced_at, etc.)

        Adding a new adapter to INTEGRATION_ADAPTERS automatically makes it appear here.
        """
        tenant = request.user.tenant
        adapters = get_all_adapters()

        # Get all configs for this tenant, keyed by provider
        configs = {
            c.provider: c
            for c in IntegrationConfig.objects.filter(tenant=tenant)
        }

        catalog = []
        for adapter in adapters:
            manifest = adapter.manifest or {}
            provider = manifest.get('id', '')
            config = configs.get(provider)
            capabilities = sorted(discover_capabilities(adapter))

            # Determine status
            if not config:
                config_status = 'not_configured'
            elif not config.is_enabled:
                config_status = 'disabled'
            elif config.sync_status == IntegrationConfig.SyncStatus.ERROR:
                config_status = 'error'
            elif config.sync_status == IntegrationConfig.SyncStatus.SYNCING:
                config_status = 'syncing'
            else:
                config_status = 'connected'

            entry = {
                # From manifest — identity
                'provider': provider,
                'name': manifest.get('name', provider),
                'category': manifest.get('category', ''),
                'description': manifest.get('description', ''),
                'long_description': manifest.get('long_description', ''),
                'icon': manifest.get('icon', ''),
                'capabilities': capabilities,

                # From manifest — auth
                'auth_type': manifest.get('auth_type', 'api_key'),
                'auth_label': manifest.get('auth_label', 'API Key'),
                'auth_instructions': manifest.get('auth_instructions', ''),
                'auth_docs_url': manifest.get('auth_docs_url', ''),

                # From manifest — details
                'data_flows': manifest.get('data_flows', []),
                'sync_details': manifest.get('sync_details', {}),
                'requirements': manifest.get('requirements', []),
                'creates': manifest.get('creates', []),
                'limitations': manifest.get('limitations', []),

                # Configuration status
                'status': config_status,

                # Config data (if configured)
                'config_id': str(config.id) if config else None,
                'is_enabled': config.is_enabled if config else False,
                'display_name': config.display_name if config else '',
                'sync_status': config.sync_status if config else None,
                'last_synced_at': config.last_synced_at.isoformat() if config and config.last_synced_at else None,
                'last_sync_error': config.last_sync_error if config else None,
                'last_sync_stats': config.last_sync_stats if config else None,
            }
            catalog.append(entry)

        return Response(catalog)

    @extend_schema(
        responses=inline_serializer(
            name='TestConnectionResult',
            fields={
                'success': drf_serializers.BooleanField(),
                'message': drf_serializers.CharField(),
            },
        )
    )
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """Test that the integration's credentials work."""
        integration = self.get_object()
        try:
            adapter = get_adapter(integration.provider)
            success, message = adapter.test_connection(integration)
            return Response({
                'success': success,
                'message': message,
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e),
            })

    @extend_schema(
        responses=inline_serializer(
            name='TriggerSyncResult',
            fields={
                'status': drf_serializers.CharField(),
            },
        )
    )
    @action(detail=True, methods=['post'])
    def trigger_sync(self, request, pk=None):
        """Manually trigger a sync for this integration."""
        integration = self.get_object()
        if not integration.is_enabled:
            return Response(
                {'error': 'Integration is disabled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            adapter = get_adapter(integration.provider)
            adapter.dispatch_sync_task(integration)
            return Response({'status': 'sync_dispatched'})
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        responses=inline_serializer(
            name='IntegrationHealth',
            fields={
                'status': drf_serializers.CharField(),
                'is_enabled': drf_serializers.BooleanField(),
                'sync_status': drf_serializers.CharField(),
                'last_synced_at': drf_serializers.DateTimeField(allow_null=True),
                'last_sync_error': drf_serializers.CharField(allow_null=True),
                'last_sync_stats': drf_serializers.DictField(allow_null=True),
                'consecutive_failures': drf_serializers.IntegerField(),
            },
        )
    )
    @action(detail=True, methods=['get'])
    def health(self, request, pk=None):
        """Get health status for this integration."""
        integration = self.get_object()
        recent_logs = IntegrationSyncLog.objects.filter(
            integration=integration
        ).order_by('-started_at')[:5]

        consecutive_failures = 0
        for log in recent_logs:
            if log.status == IntegrationSyncLog.Status.FAILED:
                consecutive_failures += 1
            else:
                break

        health_status = 'healthy'
        if not integration.is_enabled:
            health_status = 'disabled'
        elif integration.sync_status == IntegrationConfig.SyncStatus.ERROR:
            health_status = 'error'
        elif consecutive_failures >= 3:
            health_status = 'degraded'

        return Response({
            'status': health_status,
            'is_enabled': integration.is_enabled,
            'sync_status': integration.sync_status,
            'last_synced_at': integration.last_synced_at,
            'last_sync_error': integration.last_sync_error,
            'last_sync_stats': integration.last_sync_stats,
            'consecutive_failures': consecutive_failures,
        })

    @extend_schema(
        responses=IntegrationSyncLogSerializer(many=True),
    )
    @action(detail=True, methods=['get'], pagination_class=None)
    def sync_logs(self, request, pk=None):
        """Get sync history for this integration."""
        integration = self.get_object()
        logs = IntegrationSyncLog.objects.filter(
            integration=integration
        ).order_by('-started_at')[:50]
        serializer = IntegrationSyncLogSerializer(logs, many=True)
        return Response(serializer.data)


class IntegrationSyncLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only sync log history. Admin/staff only."""
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = IntegrationSyncLogSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return IntegrationSyncLog.objects.none()
        return IntegrationSyncLog.objects.filter(
            integration__tenant=self.request.user.tenant
        ).select_related('integration')


class HubSpotPipelineStageViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only pipeline stages for HubSpot integrations. Admin/staff only."""
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = HubSpotPipelineStageSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return HubSpotPipelineStage.objects.none()
        return HubSpotPipelineStage.objects.filter(
            integration__tenant=self.request.user.tenant
        ).select_related('mapped_milestone')
