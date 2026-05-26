"""
NotificationRule + ExternalContact models for the Phase 3 rule-driven dispatcher.

A `NotificationRule` binds an event code (from `EVENT_REGISTRY`) to a recipient
spec, optionally narrowed by a CEL condition over the event's typed payload.
When `services.core.notifications.emit()` fires, the dispatcher resolves
matching rules across three scopes — tenant, customer, and personal — and
writes one `NotificationOutbox` row per `(recipient, channel)`.

Three structurally-incompatible row variants share this table:
  - scope_kind='tenant'   → scope_customer=NULL, owner_user=NULL
  - scope_kind='customer' → scope_customer FK,   owner_user=NULL
  - scope_kind='personal' → scope_customer=NULL, owner_user FK

The CHECK constraint enforces these shapes at the DB layer regardless of
write path. Polymorphism mitigations (custom manager methods, per-scope DRF
serializers, computed properties) are mandatory accompaniments — see the
design doc's Data Model section.
"""
from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from .core import SecureManager, SecureModel, TenantGroup


SCOPE_TENANT = "tenant"
SCOPE_CUSTOMER = "customer"
SCOPE_PERSONAL = "personal"

SCOPE_CHOICES = [
    (SCOPE_TENANT, "Tenant-wide"),
    (SCOPE_CUSTOMER, "Customer-scoped"),
    (SCOPE_PERSONAL, "Personal"),
]


# Recipient-resolution strategy: where the dispatcher pulls recipients from
# at fire time. `static` (default) uses only the rule's M2M lists — the
# admin authored them. `from_payload` reads `payload.recipient_user_ids`
# (and group/external variants), so domain code decides per-event who
# should be notified — needed for per-assignee / per-stage routing where
# the recipient is a runtime property of the source record. `union`
# combines both, so an admin can layer CC recipients onto domain-driven
# routing ("CC the QA Manager on critical approvals" alongside the
# pending approver).
RECIPIENT_STRATEGY_STATIC = "static"
RECIPIENT_STRATEGY_FROM_PAYLOAD = "from_payload"
RECIPIENT_STRATEGY_UNION = "union"

RECIPIENT_STRATEGY_CHOICES = [
    (RECIPIENT_STRATEGY_STATIC, "Static — recipients from this rule only"),
    (RECIPIENT_STRATEGY_FROM_PAYLOAD, "From event — recipients from the event payload"),
    (RECIPIENT_STRATEGY_UNION, "Union — combine event-payload recipients with this rule's"),
]


# =============================================================================
# Manager — named methods discourage raw `.filter(scope_kind=...)` in views.
# =============================================================================

class NotificationRuleManager(SecureManager):
    """Custom manager that exposes scope-aware queries.

    Views and viewsets call the named methods; raw `.filter(scope_kind=...)`
    in application code is a code-review smell — it bypasses the named
    surface that's meant to encode the polymorphism mitigations.

    All scope-aware methods exclude soft-deleted (`archived=True`) rows by
    default. Callers that need archived rules can use the lower-level
    `SecureManager.archived()` / `.all_versions()` helpers.
    """

    def tenant_rules(self):
        return self.filter(scope_kind=SCOPE_TENANT, archived=False)

    def customer_rules(self, customer):
        """Rules scoped to a specific Customer (Companies row)."""
        return self.filter(
            scope_kind=SCOPE_CUSTOMER, scope_customer=customer, archived=False,
        )

    def personal_rules_for(self, user):
        return self.filter(scope_kind=SCOPE_PERSONAL, owner_user=user, archived=False)

    def admin_visible(self):
        """Default for admin views — excludes personal rules."""
        return self.exclude(scope_kind=SCOPE_PERSONAL)

    def editable_by(self, user):
        """All rules the user is allowed to edit.

        Admins with `notification.edit_rules_and_branding` see all
        tenant + customer rules plus their own personal rules. Non-admins
        see only their own personal rules.
        """
        own_personal = self.filter(scope_kind=SCOPE_PERSONAL, owner_user=user)
        if user.has_perm("Tracker.edit_notification_rules"):
            return self.exclude(scope_kind=SCOPE_PERSONAL).union(own_personal)
        return own_personal


# =============================================================================
# NotificationRule
# =============================================================================

class NotificationRule(SecureModel):
    """Declarative routing rule.

    Resolution at emit time:
      - tenant + customer + personal rules matching the (event_code, scope)
        are loaded, CEL conditions are evaluated against the payload, and
        the union of (recipient, channel) pairs is written to the outbox.
      - Customer and personal rules ADD to tenant rules — they don't replace.
        The dispatcher dedupes (recipient, channel) across rules so a user
        in both a recipient group and a personal rule for the same event
        gets one notification, not two.
    """

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    event_code = models.CharField(
        max_length=64,
        default="",  # default for migration; clean() rejects empty
        db_index=True,
        help_text="Must exist in EVENT_REGISTRY (validated at save time).",
    )

    # ---- Scope discriminator + variant-specific FKs ----------------------
    scope_kind = models.CharField(
        max_length=16,
        choices=SCOPE_CHOICES,
        default=SCOPE_TENANT,
        db_index=True,
    )
    scope_customer = models.ForeignKey(
        "Tracker.Companies",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notification_rules",
        help_text="Required when scope_kind='customer'; null otherwise.",
    )
    owner_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="owned_notification_rules",
        help_text="Required when scope_kind='personal'; null otherwise.",
    )

    # ---- CEL condition ----------------------------------------------------
    # `conditions_source` is the human-edited expression; `conditions` is the
    # parsed AST cache populated by save-time validation.
    conditions_source = models.TextField(
        blank=True,
        help_text="CEL expression evaluated against the event's payload.",
    )
    conditions = models.JSONField(
        default=dict,
        blank=True,
        help_text="Parsed CEL AST cache; populated at save time.",
    )

    # ---- Recipients (additive across the three M2Ms) ---------------------
    recipient_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="notification_rules_as_recipient",
    )
    recipient_groups = models.ManyToManyField(
        TenantGroup,
        blank=True,
        related_name="notification_rules",
    )
    recipient_external = models.ManyToManyField(
        "Tracker.ExternalContact",
        blank=True,
        related_name="notification_rules",
        help_text="Only valid when scope_kind='customer'.",
    )

    # Determines whether recipients come from the rule's M2M lists (static,
    # default), the event payload's `recipient_user_ids` / `recipient_group_ids`
    # / `recipient_external_ids` (from_payload), or both unioned (union).
    # Ignored for personal-scope rules — those always resolve to owner_user.
    recipient_strategy = models.CharField(
        max_length=16,
        choices=RECIPIENT_STRATEGY_CHOICES,
        default=RECIPIENT_STRATEGY_STATIC,
        help_text=(
            "Where to pull recipients from at fire time. 'static' uses the rule's "
            "M2M lists only; 'from_payload' reads recipient IDs from the event's "
            "payload; 'union' combines both."
        ),
    )

    # ---- Delivery --------------------------------------------------------
    channels = models.JSONField(
        default=list,
        blank=True,
        help_text="List of channel codes, e.g. ['email', 'in_app'].",
    )
    priority = models.IntegerField(default=0)
    enabled = models.BooleanField(default=True, db_index=True)
    min_gap_seconds = models.PositiveIntegerField(
        default=3600,
        help_text=(
            "Per-(rule, recipient) cooldown. Recipients will not receive "
            "another notification from this rule until this many seconds "
            "have passed. 0 disables dedup."
        ),
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_notification_rules",
    )

    objects = NotificationRuleManager()

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "event_code", "enabled"]),
            models.Index(fields=["tenant", "scope_kind", "scope_customer"]),
            models.Index(
                fields=["owner_user", "event_code"],
                condition=Q(scope_kind=SCOPE_PERSONAL),
                name="nr_personal_owner_event",
            ),
        ]
        constraints = [
            # Database-level enforcement of the three valid row shapes.
            # Without this, malformed rules from raw SQL, fixtures, or buggy
            # bulk writes would slip past serializer-level validation.
            models.CheckConstraint(
                check=(
                    (Q(scope_kind=SCOPE_TENANT) & Q(scope_customer__isnull=True) & Q(owner_user__isnull=True))
                    | (Q(scope_kind=SCOPE_CUSTOMER) & Q(scope_customer__isnull=False) & Q(owner_user__isnull=True))
                    | (Q(scope_kind=SCOPE_PERSONAL) & Q(scope_customer__isnull=True) & Q(owner_user__isnull=False))
                ),
                name="notification_rule_scope_invariant",
            ),
        ]
        permissions = [
            ("edit_notification_rules", "Can author tenant and customer notification rules"),
        ]

    # ---- Polymorphism helpers --------------------------------------------

    @property
    def is_personal(self) -> bool:
        return self.scope_kind == SCOPE_PERSONAL

    @property
    def is_customer_scoped(self) -> bool:
        return self.scope_kind == SCOPE_CUSTOMER

    def is_editable_by(self, user) -> bool:
        """Centralized edit-permission check — viewsets and permission
        classes call this instead of branching on scope_kind."""
        if self.is_personal:
            return self.owner_user_id == user.id
        return user.has_perm("Tracker.edit_notification_rules")

    def effective_user_recipients(self, payload_dict=None):
        """Users who should receive a notification from this rule.

        Personal rules implicitly resolve to the owner — the recipient strategy
        is ignored, because a personal rule's premise is "fires to me." For
        tenant/customer rules, the resolution dispatches on `recipient_strategy`:

          - `static` (default): only the rule's `recipient_users` M2M plus
            users expanded from `recipient_groups`. Existing behavior pre-Phase 6.
          - `from_payload`: pulls user IDs from `payload_dict['recipient_user_ids']`
            and group IDs from `payload_dict['recipient_group_ids']`, expanding
            groups to their members. Use for per-instance routing (the approver
            of a specific ApprovalRequest, the assignee of a specific CAPA).
          - `union`: combines both sets. Lets admins CC additional recipients
            ("CC QA Manager on critical approvals") alongside domain-driven
            routing.

        `payload_dict` is required for from_payload and union strategies; the
        dispatcher always passes it. Callers that omit it on a from_payload rule
        will resolve to an empty set — useful for tests and admin queries that
        don't have a payload context.
        """
        if self.is_personal:
            return [self.owner_user] if self.owner_user_id else []

        use_static = self.recipient_strategy in (RECIPIENT_STRATEGY_STATIC, RECIPIENT_STRATEGY_UNION)
        use_payload = self.recipient_strategy in (RECIPIENT_STRATEGY_FROM_PAYLOAD, RECIPIENT_STRATEGY_UNION)

        users = set()

        if use_static:
            users.update(self.recipient_users.all())
            for group in self.recipient_groups.prefetch_related("role_assignments__user"):
                for role in group.role_assignments.all():
                    if role.user_id:
                        users.add(role.user)

        if use_payload and payload_dict:
            payload_user_ids = payload_dict.get("recipient_user_ids") or []
            payload_group_ids = payload_dict.get("recipient_group_ids") or []

            if payload_user_ids:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                # tenant-safe: payload IDs come from in-tenant emit; SecureManager filters to tenant.
                users.update(User.objects.filter(id__in=payload_user_ids))

            if payload_group_ids:
                # tenant-safe: TenantGroup IDs come from in-tenant emit; SecureManager filters to tenant.
                for group in TenantGroup.objects.filter(  # tenant-safe: IDs from in-tenant payload
                    id__in=payload_group_ids,
                ).prefetch_related("role_assignments__user"):
                    for role in group.role_assignments.all():
                        if role.user_id:
                            users.add(role.user)

        return list(users)

    def effective_external_recipients(self, payload_dict=None):
        """ExternalContacts who should receive a notification from this rule.

        Only customer-scoped rules can route to externals; everyone else
        gets an empty list regardless of strategy. Same strategy dispatch as
        `effective_user_recipients` for the customer-scoped case.
        """
        if not self.is_customer_scoped:
            return []

        use_static = self.recipient_strategy in (RECIPIENT_STRATEGY_STATIC, RECIPIENT_STRATEGY_UNION)
        use_payload = self.recipient_strategy in (RECIPIENT_STRATEGY_FROM_PAYLOAD, RECIPIENT_STRATEGY_UNION)

        contacts = set()

        if use_static:
            contacts.update(self.recipient_external.filter(enabled=True))

        if use_payload and payload_dict:
            payload_ids = payload_dict.get("recipient_external_ids") or []
            if payload_ids:
                from Tracker.models import ExternalContact
                contacts.update(
                    ExternalContact.objects.filter(  # tenant-safe: IDs from in-tenant payload
                        id__in=payload_ids,
                        enabled=True,
                    )
                )

        return list(contacts)

    # ---- Validation ------------------------------------------------------

    def clean(self):
        super().clean()
        # event_code must be registered. Imported locally to avoid a
        # model-import-time dependency on the services layer.
        from Tracker.services.core.notifications import EVENT_REGISTRY
        if self.event_code and self.event_code not in EVENT_REGISTRY:
            raise ValidationError(
                {"event_code": f"Unknown event code: {self.event_code!r}"}
            )

        # CEL validation — surfaces save-time errors as field-keyed
        # ValidationErrors with "did you mean" suggestions for typo'd
        # payload field references. Skipped when there's no condition
        # source (rule fires on every matching event).
        if self.event_code and self.conditions_source:
            from Tracker.services.core.notifications.cel import (
                CelValidationError,
                validate_against_event,
            )
            try:
                validate_against_event(self.conditions_source, self.event_code)
            except CelValidationError as exc:
                grouped: dict[str, list[str]] = {}
                for err in exc.errors:
                    field = err.get("field") or "conditions_source"
                    grouped.setdefault(field, []).append(err["message"])
                raise ValidationError(grouped) from exc

        # Per-scope shape checks. The CHECK constraint catches these at the
        # DB layer too, but surfacing them as ValidationError gives nicer
        # serializer-layer error messages.
        if self.scope_kind == SCOPE_TENANT:
            if self.scope_customer_id is not None:
                raise ValidationError({"scope_customer": "Must be null for tenant scope."})
            if self.owner_user_id is not None:
                raise ValidationError({"owner_user": "Must be null for tenant scope."})
        elif self.scope_kind == SCOPE_CUSTOMER:
            if self.scope_customer_id is None:
                raise ValidationError({"scope_customer": "Required for customer scope."})
            if self.owner_user_id is not None:
                raise ValidationError({"owner_user": "Must be null for customer scope."})
            # Cross-tenant guard: the customer must belong to this tenant.
            if (
                self.scope_customer
                and self.tenant_id
                and str(self.scope_customer.tenant_id) != str(self.tenant_id)
            ):
                raise ValidationError({"scope_customer": "Customer belongs to a different tenant."})
        elif self.scope_kind == SCOPE_PERSONAL:
            if self.scope_customer_id is not None:
                raise ValidationError({"scope_customer": "Must be null for personal scope."})
            if self.owner_user_id is None:
                raise ValidationError({"owner_user": "Required for personal scope."})

    def save(self, *args, **kwargs):
        # full_clean runs clean() so the scope-shape and event_code checks
        # always fire on save, even for code paths (admin actions, scripts,
        # data migrations) that skip serializer validation.
        # M2M fields can't be cleaned pre-save — those are validated at the
        # serializer layer via TenantScopedPrimaryKeyRelatedField.
        self.full_clean(exclude=["recipient_users", "recipient_groups", "recipient_external"])
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.name} [{self.event_code}/{self.scope_kind}]"


# =============================================================================
# ExternalContact — customer-side recipients for outbound notifications.
# =============================================================================

class ExternalContact(SecureModel):
    """A non-user recipient at a customer (e.g., Acme's procurement contact).

    Used for customer-scoped rules that need to notify someone outside the
    tenant's internal users — typically shipped ASN emails, NCR-to-customer
    notifications, late-risk alerts. Tenant-scoped via SecureModel; cross-
    tenant routing is blocked by the customer_id FK chain.

    `unsubscribe_token` is rotated whenever `enabled` flips on; expired or
    cross-tenant tokens are rejected by the unsubscribe endpoint (Phase 4).
    """

    customer = models.ForeignKey(
        "Tracker.Companies",
        on_delete=models.CASCADE,
        related_name="external_contacts",
    )
    name = models.CharField(max_length=128)
    email = models.EmailField()
    role = models.CharField(
        max_length=64,
        blank=True,
        help_text="Free-form label, e.g. 'primary', 'quality', 'procurement'.",
    )
    enabled = models.BooleanField(default=True)
    unsubscribe_token = models.CharField(max_length=128, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "email"],
                name="external_contact_unique_per_customer",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "customer", "enabled"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>"
