"""
Per-scope serializers for `NotificationRule` plus an `ExternalContact`
serializer.

Three serializer classes — `TenantRuleSerializer`, `CustomerRuleSerializer`,
`PersonalRuleSerializer` — each exposes only the fields valid for its
scope, so endpoints can route to the appropriate class and reject
inappropriate fields at the boundary (e.g., a personal rule create
attempt with `recipient_groups` is a 400, not a silent ignore).

CEL save-time validation runs in the model's `clean()`; serializer
`validate()` re-runs explicit scope-shape checks for nicer error
surfacing at the API boundary.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from Tracker.models import (
    Companies,
    EscalationPolicy,
    EscalationStep,
    ExternalContact,
    MAX_ESCALATION_STEPS,
    NotificationRule,
    SCOPE_CUSTOMER,
    SCOPE_PERSONAL,
    SCOPE_TENANT,
    TenantGroup,
)
from Tracker.serializers.fields import TenantScopedPrimaryKeyRelatedField

User = get_user_model()


# =============================================================================
# Nested escalation serializer — used by all three rule scopes.
# =============================================================================
# Policy + steps come in as one nested object so a single PUT/PATCH on the
# rule applies the whole escalation chain. Read path mirrors the same shape.
# Omitting the field on update is a no-op; passing `null` deletes the policy.

class _EscalationStepSerializer(serializers.Serializer):
    """One step in a nested escalation chain."""

    order = serializers.IntegerField(
        min_value=0, max_value=MAX_ESCALATION_STEPS - 1,
    )
    delay_seconds = serializers.IntegerField(min_value=1)
    recipient_users = TenantScopedPrimaryKeyRelatedField(
        many=True, required=False, queryset=User.objects.all(),
    )
    recipient_groups = TenantScopedPrimaryKeyRelatedField(
        many=True, required=False, queryset=TenantGroup.objects.all(),
    )
    subject_override = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default="",
    )


class _EscalationSerializer(serializers.Serializer):
    """Nested policy + steps. Replace-all semantics on update: writing a
    step list overwrites the existing steps entirely. Passing `null` for
    the whole escalation deletes the policy (and its steps via CASCADE)."""

    enabled = serializers.BooleanField(default=True)
    steps = _EscalationStepSerializer(many=True)

    def validate_steps(self, value):
        if not value:
            raise serializers.ValidationError(
                "An escalation policy needs at least one step.",
            )
        if len(value) > MAX_ESCALATION_STEPS:
            raise serializers.ValidationError(
                f"Max {MAX_ESCALATION_STEPS} steps per chain.",
            )
        orders = [s["order"] for s in value]
        if len(set(orders)) != len(orders):
            raise serializers.ValidationError(
                "Step `order` values must be distinct.",
            )
        return value


def _serialize_escalation(rule) -> dict | None:
    """Read-side: dump the rule's escalation_policy (if any) as nested dict."""
    policy = getattr(rule, "escalation_policy", None)
    if policy is None:
        return None
    return {
        "enabled": policy.enabled,
        "steps": [
            {
                "order": step.order,
                "delay_seconds": step.delay_seconds,
                "recipient_users": list(
                    step.recipient_users.values_list("id", flat=True)
                ),
                "recipient_groups": list(
                    step.recipient_groups.values_list("id", flat=True)
                ),
                "subject_override": step.subject_override,
            }
            for step in policy.steps.all().order_by("order")
        ],
    }


def _persist_escalation(rule, escalation_data) -> None:
    """Write-side: apply nested escalation to the rule.

    Sentinel semantics:
      - `escalation_data is None` (explicit null) → delete the policy.
      - `escalation_data is _OMITTED` → no-op (caller didn't touch it).
      - otherwise → upsert policy + replace steps.
    """
    if escalation_data is _OMITTED:
        return

    existing = getattr(rule, "escalation_policy", None)

    if escalation_data is None:
        # Explicit null → wipe the policy. CASCADE clears steps + instances.
        if existing is not None:
            existing.delete()
        return

    if existing is None:
        policy = EscalationPolicy.objects.create(
            tenant=rule.tenant, rule=rule,
            enabled=escalation_data.get("enabled", True),
        )
    else:
        policy = existing
        policy.enabled = escalation_data.get("enabled", True)
        policy.save(update_fields=["enabled", "updated_at"])
        # Replace-all step semantics: simpler than diffing, and step
        # identity isn't durable (no client-facing step IDs in the API).
        policy.steps.all().delete()

    for step_data in escalation_data.get("steps", []):
        step = EscalationStep.objects.create(
            tenant=rule.tenant,
            policy=policy,
            order=step_data["order"],
            delay_seconds=step_data["delay_seconds"],
            subject_override=step_data.get("subject_override", ""),
        )
        users = step_data.get("recipient_users") or []
        groups = step_data.get("recipient_groups") or []
        if users:
            step.recipient_users.add(*users)
        if groups:
            step.recipient_groups.add(*groups)


# Sentinel: distinguishes "field omitted on PATCH" from "explicit null".
_OMITTED = object()


# =============================================================================
# Shared base — fields common to every rule scope.
# =============================================================================

class _BaseRuleSerializer(serializers.ModelSerializer):
    """Common fields and write-time hooks shared by all three scope variants."""

    # Nested escalation policy. Optional + nullable so:
    #   - omit on PATCH = leave the existing policy alone (handled via
    #     the `_OMITTED` sentinel in `to_internal_value`)
    #   - explicit `null` = delete the policy
    #   - dict = upsert
    escalation = _EscalationSerializer(required=False, allow_null=True)

    class Meta:
        model = NotificationRule
        # Concrete subclasses override `fields` to expose only their scope's
        # valid columns.
        fields = [
            "id",
            "name",
            "description",
            "event_code",
            "conditions_source",
            "channels",
            "priority",
            "enabled",
            "min_gap_seconds",
            "recipient_strategy",
            "escalation",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    # ---- Read ----------------------------------------------------------
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["escalation"] = _serialize_escalation(instance)
        return data

    # ---- Write — preserve the omitted/null/dict distinction -----------
    def to_internal_value(self, data):
        # If the field is not present at all (e.g. PATCH that doesn't touch
        # it), DRF strips it from validated_data. We flag this with the
        # _OMITTED sentinel so create/update can skip rather than wipe.
        has_escalation_key = "escalation" in data
        validated = super().to_internal_value(data)
        if not has_escalation_key:
            validated["escalation"] = _OMITTED
        return validated

    @transaction.atomic
    def create(self, validated_data):
        """Stamp `created_by` from the request user; the rest matches the
        default `ModelSerializer.create()` behavior (which handles M2M
        post-create assignment via `set()` calls).

        Wrapped in `transaction.atomic` so the rule, its M2Ms, the
        EscalationPolicy, and the EscalationSteps land as one unit. A
        partial failure (e.g., the third step insert) used to leave a
        rule with a half-applied policy attached.
        """
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["created_by"] = request.user
        escalation_data = validated_data.pop("escalation", _OMITTED)
        instance = super().create(validated_data)
        _persist_escalation(instance, escalation_data)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        """Atomic update — see `create` docstring for the rationale on the
        transaction wrapper."""
        escalation_data = validated_data.pop("escalation", _OMITTED)
        instance = super().update(instance, validated_data)
        _persist_escalation(instance, escalation_data)
        return instance


# =============================================================================
# Tenant-scoped rules.
# =============================================================================

class TenantRuleSerializer(_BaseRuleSerializer):
    """Admin-authored, fires tenant-wide. Recipients are internal."""

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

    class Meta(_BaseRuleSerializer.Meta):
        fields = _BaseRuleSerializer.Meta.fields + [
            "recipient_users",
            "recipient_groups",
        ]

    def validate(self, attrs):
        # Stamp scope_kind so the model's clean() sees the correct shape.
        attrs["scope_kind"] = SCOPE_TENANT
        return attrs


# =============================================================================
# Customer-scoped rules.
# =============================================================================

class CustomerRuleSerializer(_BaseRuleSerializer):
    """Admin-authored, fires only for events referencing a specific customer.
    Can route to ExternalContacts at that customer in addition to internal
    users/groups."""

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

    class Meta(_BaseRuleSerializer.Meta):
        fields = _BaseRuleSerializer.Meta.fields + [
            "scope_customer",
            "recipient_users",
            "recipient_groups",
            "recipient_external",
        ]

    def validate(self, attrs):
        attrs["scope_kind"] = SCOPE_CUSTOMER
        # Belt-and-suspenders cross-tenant guard for external contacts:
        # each must belong to the same customer as scope_customer.
        external = attrs.get("recipient_external") or []
        customer = attrs.get("scope_customer")
        if customer and external:
            mismatched = [c for c in external if c.customer_id != customer.id]
            if mismatched:
                raise serializers.ValidationError({
                    "recipient_external": (
                        "All external contacts must belong to the rule's "
                        "scope_customer."
                    ),
                })
        return attrs


# =============================================================================
# Personal rules.
# =============================================================================

class PersonalRuleSerializer(_BaseRuleSerializer):
    """User-authored. Owner is the implicit recipient — no recipient_* fields
    are exposed.

    `owner_user` is write-once at create time; the viewset stamps it from the
    request user. The serializer exposes it read-only so clients can see who
    owns a rule but can't reassign it. Phase 4 may add an explicit "transfer
    ownership" endpoint if needed.
    """

    owner_user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta(_BaseRuleSerializer.Meta):
        fields = _BaseRuleSerializer.Meta.fields + ["owner_user"]

    def validate(self, attrs):
        attrs["scope_kind"] = SCOPE_PERSONAL
        return attrs

    def create(self, validated_data):
        # owner_user is request-user-stamped, not client-provided.
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["owner_user"] = request.user
        else:
            raise serializers.ValidationError(
                "Personal rules require an authenticated user."
            )
        return super().create(validated_data)


# =============================================================================
# External contacts (customer-side recipients).
# =============================================================================

class ExternalContactSerializer(serializers.ModelSerializer):
    """CRUD over `ExternalContact`. Tenant-scoped automatically by the
    viewset; the customer FK is validated to belong to the current tenant
    via TenantScopedPrimaryKeyRelatedField."""

    customer = TenantScopedPrimaryKeyRelatedField(queryset=Companies.unscoped.all())

    class Meta:
        model = ExternalContact
        fields = [
            "id",
            "customer",
            "name",
            "email",
            "role",
            "enabled",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


