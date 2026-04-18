from auditlog.registry import auditlog
from django.contrib import admin

from integrations.models import IntegrationConfig, IntegrationSyncLog

# Register IntegrationConfig with auditlog for credential/config change tracking
auditlog.register(IntegrationConfig, exclude_fields=['api_key', 'oauth_refresh_token', 'webhook_secret'])


@admin.register(IntegrationConfig)
class IntegrationConfigAdmin(admin.ModelAdmin):
    list_display = ['provider', 'tenant', 'display_name', 'is_enabled', 'sync_status', 'last_synced_at']
    list_filter = ['provider', 'is_enabled', 'sync_status']
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_synced_at', 'last_sync_error', 'last_sync_stats']

    def get_queryset(self, request):
        # Admin runs on an exempt path, so the tenant ContextVar is
        # unset. Use all_tenants to get cross-tenant visibility
        # (superuser admins see records across every tenant).
        return self.model.all_tenants.get_queryset()


@admin.register(IntegrationSyncLog)
class IntegrationSyncLogAdmin(admin.ModelAdmin):
    list_display = ['integration', 'sync_type', 'status', 'started_at', 'records_created', 'records_updated']
    list_filter = ['status', 'sync_type']
    readonly_fields = ['id']

    def get_queryset(self, request):
        return self.model.all_tenants.get_queryset()
