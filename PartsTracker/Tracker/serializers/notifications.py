"""
Serializers for event-driven NotificationRule.

Recipient M2Ms use TenantScopedPrimaryKeyRelatedField so a request body
can only reference users/groups in the current tenant — cross-tenant PKs
fail validation with the standard "object does not exist" error.

GFK scope fields are exposed as a pair (scope_content_type + scope_object_id).
Null pair = tenant-wide rule; populated pair = rule scoped at a specific
object. Tenant-match validation for the GFK target runs in the model's
`clean()`.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from Tracker.models import NotificationRule, TenantGroup
from Tracker.serializers.fields import TenantScopedPrimaryKeyRelatedField
from Tracker.services.core.notification_resolvers import resolver_keys

User = get_user_model()


class NotificationRuleSerializer(serializers.ModelSerializer):
    """CRUD for NotificationRule."""

    # Recipient M2Ms — scoped to the current tenant. Plain-manager
    # queryset is required because the scoped field re-filters per-request.
    recipient_users = TenantScopedPrimaryKeyRelatedField(
        many=True, required=False,
        queryset=User.objects.all(),
    )
    recipient_groups = TenantScopedPrimaryKeyRelatedField(
        many=True, required=False,
        queryset=TenantGroup.objects.all(),
    )

    # GFK scope exposed as (content_type_id, object_id). ContentType is
    # global (not tenant-scoped); the tenant-match invariant on the
    # target object is enforced by the model's clean().
    scope_content_type = serializers.PrimaryKeyRelatedField(
        queryset=ContentType.objects.all(),
        allow_null=True, required=False,
    )
    scope_object_id = serializers.CharField(
        allow_null=True, required=False, allow_blank=True,
    )

    # Read-only metadata useful for admin UIs
    available_resolvers = serializers.SerializerMethodField()

    class Meta:
        model = NotificationRule
        fields = [
            'id',
            'name',
            'description',
            'event_type',
            'scope_content_type',
            'scope_object_id',
            'recipient_users',
            'recipient_groups',
            'recipient_resolver_key',
            'channel_type',
            'min_gap_seconds',
            'is_active',
            'created_at',
            'updated_at',
            'available_resolvers',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_available_resolvers(self, obj) -> list[str]:
        return resolver_keys()
