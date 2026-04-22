"""
ViewSet for event-driven NotificationRule.

Uses TenantScopedMixin for auto-scoping + TenantModelPermissions; admins
with the notificationrule permissions get full CRUD within their tenant.
"""
from __future__ import annotations

from rest_framework import filters, serializers, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, inline_serializer

from Tracker.models import NotificationRule
from Tracker.serializers.notifications import NotificationRuleSerializer
from Tracker.services.core.notification_resolvers import resolver_keys
from Tracker.viewsets.base import TenantScopedMixin


# Catalog of event types the rule engine understands. Adding a new event:
#   1. Append to NotificationEventType.choices in models/notifications.py
#   2. Append here with the scope model the UI should use for narrowing
#   3. Register a handler in Tracker.notifications.handlers
#   4. Add a trigger call to `notify(...)` at the event site
_EVENT_CATALOG: list[dict] = [
    {
        'key': 'STEP_FAILURE',
        'label': 'Part failed at step',
        'description': 'A part has been quarantined because a quality report failed at its current step.',
        'scope_model': 'Tracker.Steps',
        'scope_label': 'Step',
    },
    {
        'key': 'WORK_ORDER_HELD_TOO_LONG',
        'label': 'Work order held too long',
        'description': 'A work order has been on hold past the configured threshold.',
        'scope_model': 'Tracker.WorkOrder',
        'scope_label': 'Work Order',
    },
    {
        'key': 'WORK_ORDER_STALLED',
        'label': 'Work order stalled',
        'description': 'A work order has had no step activity for an extended period.',
        'scope_model': 'Tracker.WorkOrder',
        'scope_label': 'Work Order',
    },
    {
        'key': 'WORK_ORDER_OVERDUE',
        'label': 'Work order overdue',
        'description': 'A work order is past its expected completion date and has not completed.',
        'scope_model': 'Tracker.WorkOrder',
        'scope_label': 'Work Order',
    },
]


class NotificationRuleViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD for event-driven notification rules."""

    # Class-level queryset evaluates at import time with no tenant
    # context; use all_tenants to avoid the SecureManager raise. The
    # tenant filter is re-applied per-request by TenantScopedMixin.
    queryset = NotificationRule.all_tenants.all()
    serializer_class = NotificationRuleSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['event_type', 'is_active', 'channel_type']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'name']
    ordering = ['-created_at']


class NotificationEventTypeCatalogView(APIView):
    """Static catalog of event types the rule engine can fire on.

    Consumed by the admin UI to build the event-type dropdown and to
    render the right scope picker per event (scope_model tells the UI
    which model list to fetch when the admin picks "scope at a specific
    object").
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: inline_serializer(
            name='NotificationEventTypeCatalog',
            many=True,
            fields={
                'key': serializers.CharField(),
                'label': serializers.CharField(),
                'description': serializers.CharField(),
                'scope_model': serializers.CharField(allow_null=True),
                'scope_label': serializers.CharField(allow_null=True),
                'resolver_keys': serializers.ListField(child=serializers.CharField()),
            },
        )}
    )
    def get(self, request):
        resolvers = resolver_keys()
        entries = [
            {**entry, 'resolver_keys': resolvers}
            for entry in _EVENT_CATALOG
        ]
        return Response(entries, status=status.HTTP_200_OK)
