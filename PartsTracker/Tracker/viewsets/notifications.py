"""
Per-scope viewsets for `NotificationRule` and `NotificationSchedule`,
plus the `ExternalContact` viewset and read-only catalog endpoints.

URL layout (registered in `PartsTrackerApp/urls.py`):
    /api/notifications/rules/tenant/             TenantRuleViewSet
    /api/notifications/rules/customer/           CustomerRuleViewSet
    /api/notifications/rules/personal/           PersonalRuleViewSet
    /api/notifications/schedules/tenant/         TenantScheduleViewSet
    /api/notifications/schedules/customer/       CustomerScheduleViewSet
    /api/notifications/schedules/personal/       PersonalScheduleViewSet
    /api/notifications/schedules/providers/      ScheduledContentProviderCatalogView
    /api/notifications/external-contacts/        ExternalContactViewSet
    /api/notifications/events/                   NotificationEventTypeCatalogView

Permission model (matches across rules and schedules — `edit_notification_rules`
is reused for both since they're managed by the same admin role):
  - Tenant + customer scopes: `Tracker.edit_notification_rules` required.
  - Personal scope: viewset filters to the request user's own rows; any
    authenticated user can manage their own without the permission.
"""
from __future__ import annotations

from django.utils import timezone
from rest_framework import filters, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, inline_serializer

from Tracker.permissions import TenantAccessPermission
from Tracker.models import (
    ExternalContact,
    NotificationOutbox,
    NotificationRule,
    NotificationSchedule,
)
from Tracker.serializers.notifications import (
    CustomerRuleSerializer,
    ExternalContactSerializer,
    NotificationFeedItemSerializer,
    PersonalRuleSerializer,
    TenantRuleSerializer,
)
from Tracker.serializers.notification_schedule import (
    CustomerScheduleSerializer,
    PersonalScheduleSerializer,
    TenantScheduleSerializer,
)
from Tracker.viewsets.base import TenantScopedMixin


# =============================================================================
# Rule viewsets (one per scope).
# =============================================================================

class TenantRuleViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD over tenant-scoped rules. Filtered to the current tenant via
    `TenantScopedMixin`; further filtered to `scope_kind='tenant'` via the
    manager method so customer/personal rules don't leak through."""

    # Class-level queryset for drf-spectacular schema introspection (runs
    # without a tenant context). Real filtering happens in get_queryset.
    queryset = NotificationRule.all_tenants.none()
    serializer_class = TenantRuleSerializer
    permission_classes = [IsAuthenticated, TenantAccessPermission]
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    search_fields = ["name", "description", "event_code"]
    ordering_fields = ["created_at", "updated_at", "name", "priority"]
    ordering = ["priority", "-created_at"]

    def get_queryset(self):
        return NotificationRule.objects.tenant_rules()


class CustomerRuleViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD over customer-scoped rules.

    Supports a `?customer=<uuid>` query param to filter to one customer's
    rules; without it, all customer-scoped rules in the tenant are returned.
    """

    queryset = NotificationRule.all_tenants.none()
    serializer_class = CustomerRuleSerializer
    permission_classes = [IsAuthenticated, TenantAccessPermission]
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    search_fields = ["name", "description", "event_code"]
    ordering_fields = ["created_at", "updated_at", "name", "priority"]
    ordering = ["priority", "-created_at"]

    def get_queryset(self):
        # tenant-safe: viewset request runs under TenantMiddleware ContextVar; SecureManager auto-scopes.
        qs = NotificationRule.objects.filter(scope_kind="customer", archived=False)
        customer_id = self.request.query_params.get("customer")
        if customer_id:
            qs = qs.filter(scope_customer_id=customer_id)
        return qs


class PersonalRuleViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD over the request user's own personal rules. Filtered to
    `owner_user=request.user` — users can't see or modify each other's
    personal rules."""

    queryset = NotificationRule.all_tenants.none()
    serializer_class = PersonalRuleSerializer
    permission_classes = [IsAuthenticated, TenantAccessPermission]
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    search_fields = ["name", "description", "event_code"]
    ordering_fields = ["created_at", "updated_at", "name"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return NotificationRule.objects.personal_rules_for(self.request.user)


# =============================================================================
# External contacts.
# =============================================================================

class ExternalContactViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD over `ExternalContact` rows. Tenant-scoped via the mixin;
    customer FK validation handled at the serializer layer."""

    queryset = ExternalContact.all_tenants.none()
    serializer_class = ExternalContactSerializer
    permission_classes = [IsAuthenticated, TenantAccessPermission]
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    search_fields = ["name", "email", "role"]
    ordering_fields = ["created_at", "updated_at", "name"]
    ordering = ["name"]

    def get_queryset(self):
        # tenant-safe: viewset request runs under TenantMiddleware ContextVar; SecureManager auto-scopes.
        qs = ExternalContact.objects.filter(archived=False)
        customer_id = self.request.query_params.get("customer")
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        return qs


# =============================================================================
# Event catalog (slice 1 stub kept; route stays the same).
# =============================================================================

class NotificationEventTypeCatalogView(APIView):
    """Returns the EVENT_REGISTRY catalog (event_code, label, description,
    domain, default_channels, default_on, supports_escalation).

    `supports_escalation` is derived from the ack registry — events without
    an ack predicate registration can't have escalation chains attached,
    so the rule editor disables that toggle for them.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: inline_serializer(
            name="NotificationEventTypeCatalog",
            many=True,
            fields={
                "code": serializers.CharField(),
                "label": serializers.CharField(),
                "domain": serializers.CharField(),
                "description": serializers.CharField(),
                "default_channels": serializers.ListField(child=serializers.CharField()),
                "default_on": serializers.BooleanField(),
                "supports_escalation": serializers.BooleanField(),
            },
        )}
    )
    def get(self, request):
        from Tracker.services.core.notifications import EVENT_REGISTRY
        from Tracker.services.core.notifications.escalation import (
            list_acknowledged_events,
        )

        ack_events = set(list_acknowledged_events())

        entries = [
            {
                "code": event.code,
                "label": event.label,
                "domain": event.domain,
                "description": event.description,
                "default_channels": list(event.default_channels),
                "default_on": event.default_on,
                "supports_escalation": event.code in ack_events,
            }
            for event in EVENT_REGISTRY.values()
        ]
        return Response(entries, status=status.HTTP_200_OK)


# =============================================================================
# Schedule viewsets (one per scope).
# =============================================================================

class TenantScheduleViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD over tenant-scoped scheduled notifications."""

    queryset = NotificationSchedule.all_tenants.none()
    serializer_class = TenantScheduleSerializer
    permission_classes = [IsAuthenticated, TenantAccessPermission]
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    search_fields = ["name", "description", "provider_kind"]
    ordering_fields = ["created_at", "updated_at", "name", "cadence"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return NotificationSchedule.objects.tenant_schedules()


class CustomerScheduleViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD over customer-scoped scheduled notifications.

    Supports `?customer=<uuid>` to filter to one customer's schedules.
    """

    queryset = NotificationSchedule.all_tenants.none()
    serializer_class = CustomerScheduleSerializer
    permission_classes = [IsAuthenticated, TenantAccessPermission]
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    search_fields = ["name", "description", "provider_kind"]
    ordering_fields = ["created_at", "updated_at", "name", "cadence"]
    ordering = ["-created_at"]

    def get_queryset(self):
        # tenant-safe: viewset request runs under TenantMiddleware ContextVar; SecureManager auto-scopes.
        qs = NotificationSchedule.objects.filter(
            scope_kind="customer", archived=False,
        )
        customer_id = self.request.query_params.get("customer")
        if customer_id:
            qs = qs.filter(scope_customer_id=customer_id)
        return qs


class PersonalScheduleViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD over the request user's own personal schedules.

    Filtered to `owner_user=request.user` — users can't see or modify each
    other's scheduled subscriptions. Used by `/profile/notifications` to
    let customers self-manage their digest cadence.
    """

    queryset = NotificationSchedule.all_tenants.none()
    serializer_class = PersonalScheduleSerializer
    permission_classes = [IsAuthenticated, TenantAccessPermission]
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    search_fields = ["name", "description", "provider_kind"]
    ordering_fields = ["created_at", "updated_at", "name"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return NotificationSchedule.objects.personal_schedules_for(self.request.user)


# =============================================================================
# Scheduled content provider catalog
# =============================================================================

class ScheduledContentProviderCatalogView(APIView):
    """Returns the registered ScheduledContentProvider catalog.

    Used by the schedule editor UI to populate the provider dropdown and
    render dynamic param fields (via the provider's `param_serializer_class`
    field metadata).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: inline_serializer(
            name="ScheduledContentProviderCatalog",
            many=True,
            fields={
                "name": serializers.CharField(),
                "title": serializers.CharField(),
                "description": serializers.CharField(),
                "params_schema": serializers.JSONField(),
            },
        )}
    )
    def get(self, request):
        from Tracker.services.core.notifications.scheduled_content import (
            get_all_providers,
        )

        entries = []
        for provider in get_all_providers().values():
            param_serializer = provider.param_serializer_class()
            params_schema = {
                field_name: {
                    "type": field.__class__.__name__,
                    "required": field.required,
                    "help_text": getattr(field, "help_text", "") or "",
                }
                for field_name, field in param_serializer.fields.items()
            }
            entries.append({
                "name": provider.name,
                "title": provider.title,
                "description": provider.description,
                "params_schema": params_schema,
            })
        return Response(entries, status=status.HTTP_200_OK)




# =============================================================================
# In-app notification feed — the reader for what InAppChannel writes.
# =============================================================================

class NotificationFeedViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """The request user's in-app notification feed.

    InAppChannel does no wire delivery — the outbox row IS the notification,
    and this endpoint is the reader it was written toward. Self-scoped like
    PersonalRuleViewSet: any authenticated user reads their own rows; the
    admin-only NotificationOutbox CRUD perms deliberately don't apply (this
    is a /me-style surface, not outbox administration).

    The AWARENESS surface (ephemeral, mark-read), distinct from /inbox's
    COMMITMENTS (owned, due-dated work items). Kept separate by design.
    """

    queryset = NotificationOutbox.all_tenants.none()
    serializer_class = NotificationFeedItemSerializer
    permission_classes = [IsAuthenticated, TenantAccessPermission]
    filter_backends = [filters.OrderingFilter]
    ordering = ["-created_at"]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return NotificationOutbox.objects.none()
        # tenant-safe: request runs under TenantMiddleware ContextVar; SecureManager auto-scopes.
        qs = NotificationOutbox.objects.filter(
            user=self.request.user,
            channel='in_app',
            archived_at__isnull=True,
            is_test=False,
        ).exclude(status__in=['failed', 'cancelled', 'suppressed'])
        if self.request.query_params.get('unread', '').lower() == 'true':
            qs = qs.filter(read_at__isnull=True)
        return qs

    @extend_schema(
        description="Number of unread in-app notifications for the current user.",
        responses={200: inline_serializer(
            name='NotificationUnreadCount',
            fields={'unread': serializers.IntegerField()},
        )},
    )
    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        return Response({'unread': self.get_queryset().filter(read_at__isnull=True).count()})

    @extend_schema(
        description="Mark one notification as read (idempotent).",
        request=None,
        responses={200: NotificationFeedItemSerializer},
    )
    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        row = self.get_object()
        if row.read_at is None:
            row.read_at = timezone.now()
            row.save(update_fields=['read_at', 'updated_at'])
        return Response(self.get_serializer(row).data)

    @extend_schema(
        description="Mark every unread in-app notification as read.",
        request=None,
        responses={200: inline_serializer(
            name='NotificationMarkAllRead',
            fields={'marked': serializers.IntegerField()},
        )},
    )
    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        marked = self.get_queryset().filter(read_at__isnull=True).update(
            read_at=timezone.now(),
        )
        return Response({'marked': marked})
