"""
Per-scope serializers for `NotificationSchedule`.

Three serializer classes — `TenantScheduleSerializer`,
`CustomerScheduleSerializer`, `PersonalScheduleSerializer` — each exposes
only the fields valid for its scope. Mirrors the per-scope rule serializer
pattern (`Tracker.serializers.notifications`) so the polymorphic shape is
enforced at the API boundary, not just the DB CHECK constraint.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

from Tracker.models import (
    Companies,
    ExternalContact,
    NotificationSchedule,
    SCOPE_CUSTOMER,
    SCOPE_PERSONAL,
    SCOPE_TENANT,
    TenantGroup,
)
from Tracker.serializers.fields import TenantScopedPrimaryKeyRelatedField

User = get_user_model()


# =============================================================================
# Shared base
# =============================================================================

class _BaseScheduleSerializer(serializers.ModelSerializer):
    """Fields common to every scope variant."""

    class Meta:
        model = NotificationSchedule
        fields = [
            "id",
            "name",
            "description",
            "enabled",
            "provider_kind",
            "provider_params",
            "cadence",
            "day_of_week",
            "day_of_month",
            "time_of_day",
            "timezone",
            "channels",
            "last_fired_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "last_fired_at", "created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["created_by"] = request.user
        return super().create(validated_data)


# =============================================================================
# Tenant-scoped
# =============================================================================

class TenantScheduleSerializer(_BaseScheduleSerializer):
    """Admin-authored, internal recipients only."""

    recipient_users = TenantScopedPrimaryKeyRelatedField(
        many=True,
        required=False,
        queryset=User.objects.all(),
    )
    recipient_groups = TenantScopedPrimaryKeyRelatedField(
        many=True,
        required=False,
        queryset=TenantGroup.objects.all(),  # tenant-safe: TenantScopedPrimaryKeyRelatedField filters to tenant
    )

    class Meta(_BaseScheduleSerializer.Meta):
        fields = _BaseScheduleSerializer.Meta.fields + [
            "recipient_users",
            "recipient_groups",
        ]

    def validate(self, attrs):
        attrs["scope_kind"] = SCOPE_TENANT
        return attrs


# =============================================================================
# Customer-scoped
# =============================================================================

class CustomerScheduleSerializer(_BaseScheduleSerializer):
    """Admin-authored, routes to one customer org's recipients (users,
    groups, or ExternalContacts at that customer)."""

    scope_customer = TenantScopedPrimaryKeyRelatedField(
        queryset=Companies.unscoped.all(),
        required=True,
    )
    recipient_users = TenantScopedPrimaryKeyRelatedField(
        many=True,
        required=False,
        queryset=User.objects.all(),
    )
    recipient_groups = TenantScopedPrimaryKeyRelatedField(
        many=True,
        required=False,
        queryset=TenantGroup.objects.all(),  # tenant-safe: TenantScopedPrimaryKeyRelatedField filters to tenant
    )
    recipient_external = TenantScopedPrimaryKeyRelatedField(
        many=True,
        required=False,
        queryset=ExternalContact.unscoped.all(),  # tenant-safe: TenantScopedPrimaryKeyRelatedField filters to tenant
    )

    class Meta(_BaseScheduleSerializer.Meta):
        fields = _BaseScheduleSerializer.Meta.fields + [
            "scope_customer",
            "recipient_users",
            "recipient_groups",
            "recipient_external",
        ]

    def validate(self, attrs):
        attrs["scope_kind"] = SCOPE_CUSTOMER
        # Belt-and-suspenders cross-tenant guard: external contacts must
        # belong to the same customer as scope_customer (mirrors the
        # customer rule serializer check).
        external = attrs.get("recipient_external") or []
        customer = attrs.get("scope_customer")
        if customer and external:
            mismatched = [c for c in external if c.customer_id != customer.id]
            if mismatched:
                raise serializers.ValidationError({
                    "recipient_external": (
                        "All external contacts must belong to the schedule's "
                        "scope_customer."
                    ),
                })
        return attrs


# =============================================================================
# Personal
# =============================================================================

class PersonalScheduleSerializer(_BaseScheduleSerializer):
    """User-authored. Owner is the implicit recipient — no recipient_*
    fields are exposed. `owner_user` is stamped from the request user at
    create time and read-only thereafter."""

    owner_user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta(_BaseScheduleSerializer.Meta):
        fields = _BaseScheduleSerializer.Meta.fields + ["owner_user"]

    def validate(self, attrs):
        attrs["scope_kind"] = SCOPE_PERSONAL
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError(
                "Personal schedules require an authenticated user."
            )
        validated_data["owner_user"] = request.user
        return super().create(validated_data)
