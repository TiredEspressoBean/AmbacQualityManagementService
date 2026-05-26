"""
NotificationSchedule — scheduled snapshot-content delivery model.

Where `NotificationRule` (notifications.py) routes events emitted by the
domain to recipients, `NotificationSchedule` runs on a clock: it fires on
a configured cadence, asks a `ScheduledContentProvider` to render content,
and writes outbox rows for each (recipient, channel) pair.

Two structurally-incompatible row variants share this table:
  - scope_kind='tenant'    → scope_customer=NULL (tenant-wide subscription)
  - scope_kind='customer'  → scope_customer FK   (per-customer subscription)

No personal scope. Schedules are admin-configured; user-driven scheduled
content is rare enough that we defer it until a concrete need appears.

The CHECK constraints enforce scope-shape AND cadence-shape (weekly rules
must set day_of_week and clear day_of_month; monthly rules vice-versa) at
the DB layer so malformed rows from raw SQL, fixtures, or buggy bulk writes
can't slip past serializer validation.

Beat coordination uses `last_fired_at` as the lock anchor — see
`Tracker.services.core.notifications.schedule.fire_schedule()`.
"""
from __future__ import annotations

from datetime import time

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from .core import SecureManager, SecureModel, TenantGroup
from .notifications import SCOPE_CUSTOMER, SCOPE_PERSONAL, SCOPE_TENANT


# Cadence keys live here (not on Rule) — they're a scheduling concept, not
# a routing one. New cadences (daily, biweekly) plug in by adding to this
# tuple and extending `compute_next_fire` to handle them.
CADENCE_WEEKLY = "weekly"
CADENCE_MONTHLY = "monthly"

CADENCE_CHOICES = [
    (CADENCE_WEEKLY, "Weekly"),
    (CADENCE_MONTHLY, "Monthly"),
]

# Scope choices for schedules: tenant, customer, or personal.
# - tenant   = admin-authored, internal recipients (e.g. weekly CAPA digest to QA Manager)
# - customer = admin-authored, customer-org recipients (e.g. weekly orders to Acme's buyer)
# - personal = user-authored, self is the recipient (e.g. "send me a weekly summary")
#
# Personal schedules are managed by their owner via /profile/notifications;
# tenant + customer schedules are admin-managed via /settings/notification-schedules.
SCHEDULE_SCOPE_CHOICES = [
    (SCOPE_TENANT, "Tenant-wide"),
    (SCOPE_CUSTOMER, "Customer-scoped"),
    (SCOPE_PERSONAL, "Personal"),
]


# =============================================================================
# Manager
# =============================================================================

class NotificationScheduleManager(SecureManager):
    """Scope-aware queries for NotificationSchedule.

    Mirrors the NotificationRuleManager pattern: named methods discourage
    raw `.filter(scope_kind=...)` in views, and all methods exclude
    soft-deleted rows by default.
    """

    def tenant_schedules(self):
        return self.filter(scope_kind=SCOPE_TENANT, archived=False)

    def customer_schedules(self, customer):
        return self.filter(
            scope_kind=SCOPE_CUSTOMER, scope_customer=customer, archived=False,
        )

    def personal_schedules_for(self, user):
        """The current user's own scheduled subscriptions. Used by the
        `/profile/notifications` page; users can only see and edit their own."""
        return self.filter(
            scope_kind=SCOPE_PERSONAL, owner_user=user, archived=False,
        )

    def due_at(self, *, now):
        """Schedules where the next fire moment has passed, used by the
        beat tick task. Caller still re-checks under SELECT FOR UPDATE.
        """
        return self.filter(enabled=True, archived=False)


# =============================================================================
# NotificationSchedule
# =============================================================================

class NotificationSchedule(SecureModel):
    """A scheduled, content-producer-driven delivery.

    The fire flow at a high level:

      tick_notification_schedules (every 5 min)
        for each enabled schedule:
          if compute_next_fire(schedule, after=last_fired_at) <= now:
            fire_one_schedule.delay(schedule.id)

      fire_one_schedule(id):
        SELECT FOR UPDATE SKIP LOCKED on the schedule row
        if still due:
          mark last_fired_at = now (atomic)
          render content via ScheduledContentProvider
          write outbox rows with idempotency keyed on (schedule, fire_window_start)

    Crash semantics: `last_fired_at` is set BEFORE rendering. A crash mid-
    render therefore drops that cycle's delivery rather than double-firing
    on the next tick. For weekly digests this is the right trade — at-most-
    once is preferred to at-least-once when retries would duplicate user-
    facing email.
    """

    # ---- Identity --------------------------------------------------------
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    enabled = models.BooleanField(default=True, db_index=True)

    # ---- Scope (tenant / customer / personal) ----------------------------
    scope_kind = models.CharField(
        max_length=16,
        choices=SCHEDULE_SCOPE_CHOICES,
        default=SCOPE_TENANT,
        db_index=True,
    )
    scope_customer = models.ForeignKey(
        "Tracker.Companies",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notification_schedules",
        help_text="Required when scope_kind='customer'; null otherwise.",
    )
    owner_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="owned_notification_schedules",
        help_text=(
            "Required when scope_kind='personal'; null otherwise. "
            "Personal-scoped schedules are also delivered to this user "
            "(the owner is the implicit recipient)."
        ),
    )

    # ---- Content --------------------------------------------------------
    # `provider_kind` is a registry key resolved by
    # `Tracker.notifications.scheduled_content.registry.get_provider(name)`.
    # Validated at save() against the live registry.
    provider_kind = models.CharField(
        max_length=64,
        help_text="ScheduledContentProvider registry key.",
    )
    provider_params = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Params passed to the provider. For customer-scoped schedules, "
            "the dispatcher merges in {'customer_id': scope_customer.id} "
            "before invoking the provider."
        ),
    )

    # ---- Cadence --------------------------------------------------------
    cadence = models.CharField(
        max_length=16,
        choices=CADENCE_CHOICES,
        default=CADENCE_WEEKLY,
    )
    day_of_week = models.IntegerField(
        null=True,
        blank=True,
        help_text="0=Monday ... 6=Sunday. Required when cadence='weekly'.",
    )
    day_of_month = models.IntegerField(
        null=True,
        blank=True,
        help_text=(
            "1-28 (capped to avoid Feb/short-month gotchas). Required when "
            "cadence='monthly'."
        ),
    )
    time_of_day = models.TimeField(
        default=time(8, 0),
        help_text="Local clock time in the schedule's timezone.",
    )
    timezone = models.CharField(
        max_length=64,
        default="UTC",
        help_text=(
            "IANA timezone name (e.g. 'America/New_York'). Defaults to UTC; "
            "the fire task falls back to tenant.default_timezone if 'UTC' "
            "is set and the tenant configured a non-UTC default."
        ),
    )

    # ---- Recipients (mirror NotificationRule shape) ---------------------
    recipient_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="notification_schedules_as_recipient",
    )
    recipient_groups = models.ManyToManyField(
        TenantGroup,
        blank=True,
        related_name="notification_schedules",
    )
    recipient_external = models.ManyToManyField(
        "Tracker.ExternalContact",
        blank=True,
        related_name="notification_schedules",
        help_text="Only valid when scope_kind='customer'.",
    )

    # ---- Delivery -------------------------------------------------------
    channels = models.JSONField(
        default=list,
        blank=True,
        help_text="List of channel codes, e.g. ['email']. Email-only at launch.",
    )

    # ---- Beat coordination ---------------------------------------------
    last_fired_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Set to now() inside the fire transaction, before rendering.",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_notification_schedules",
    )

    objects = NotificationScheduleManager()

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "enabled", "cadence"]),
            models.Index(fields=["tenant", "scope_kind", "scope_customer"]),
        ]
        constraints = [
            # Scope-shape: tenant has neither extra FK; customer has scope_customer;
            # personal has owner_user.
            models.CheckConstraint(
                check=(
                    (Q(scope_kind=SCOPE_TENANT) & Q(scope_customer__isnull=True) & Q(owner_user__isnull=True))
                    | (Q(scope_kind=SCOPE_CUSTOMER) & Q(scope_customer__isnull=False) & Q(owner_user__isnull=True))
                    | (Q(scope_kind=SCOPE_PERSONAL) & Q(scope_customer__isnull=True) & Q(owner_user__isnull=False))
                ),
                name="notification_schedule_scope_shape",
            ),
            # Cadence-shape: weekly rows have day_of_week and null day_of_month;
            # monthly rows have day_of_month and null day_of_week.
            models.CheckConstraint(
                check=(
                    (Q(cadence=CADENCE_WEEKLY) & Q(day_of_week__isnull=False) & Q(day_of_month__isnull=True))
                    | (Q(cadence=CADENCE_MONTHLY) & Q(day_of_week__isnull=True) & Q(day_of_month__isnull=False))
                ),
                name="notification_schedule_cadence_shape",
            ),
        ]
        permissions = [
            (
                "edit_notification_schedules",
                "Can author tenant and customer scheduled notifications",
            ),
        ]

    # ---- Convenience properties -----------------------------------------

    @property
    def is_customer_scoped(self) -> bool:
        return self.scope_kind == SCOPE_CUSTOMER

    @property
    def is_personal(self) -> bool:
        return self.scope_kind == SCOPE_PERSONAL

    def is_editable_by(self, user) -> bool:
        """Centralized edit-permission check. Personal schedules are
        owner-only; tenant/customer schedules require the
        `edit_notification_rules` permission (reused — schedules and rules
        share the same admin role)."""
        if self.is_personal:
            return self.owner_user_id == user.id
        return user.has_perm("Tracker.edit_notification_rules")

    @property
    def is_weekly(self) -> bool:
        return self.cadence == CADENCE_WEEKLY

    @property
    def is_monthly(self) -> bool:
        return self.cadence == CADENCE_MONTHLY

    def resolved_timezone(self) -> str:
        """The effective IANA timezone for fire-time math.

        Defaults to the schedule's `timezone` field. If that's left at the
        default 'UTC' and the tenant has a non-UTC `default_timezone`, falls
        back to the tenant's setting. This lets admins set a tenant-wide
        local timezone once instead of stamping every schedule.
        """
        if self.timezone and self.timezone != "UTC":
            return self.timezone
        if self.tenant_id and getattr(self.tenant, "default_timezone", None):
            return self.tenant.default_timezone
        return "UTC"

    # ---- Validation -----------------------------------------------------

    def clean(self):
        super().clean()

        # Validate provider_kind against the live registry. Imported lazily
        # so the model package doesn't depend on the services layer at
        # import time.
        if self.provider_kind:
            from Tracker.services.core.notifications.scheduled_content import (
                UnknownProviderError,
                get_provider,
            )
            try:
                get_provider(self.provider_kind)
            except UnknownProviderError:
                raise ValidationError(
                    {"provider_kind": f"Unknown content provider: {self.provider_kind!r}"}
                )

        # Channels must be a non-empty list of strings.
        if not isinstance(self.channels, list) or not self.channels:
            raise ValidationError(
                {"channels": "At least one channel is required (e.g. ['email'])."}
            )
        for c in self.channels:
            if not isinstance(c, str):
                raise ValidationError({"channels": "Channels must be strings."})

        # Scope-shape (mirrors NotificationRule.clean()).
        if self.scope_kind == SCOPE_TENANT:
            if self.scope_customer_id is not None:
                raise ValidationError(
                    {"scope_customer": "Must be null for tenant scope."}
                )
            if self.owner_user_id is not None:
                raise ValidationError(
                    {"owner_user": "Must be null for tenant scope."}
                )
        elif self.scope_kind == SCOPE_CUSTOMER:
            if self.scope_customer_id is None:
                raise ValidationError(
                    {"scope_customer": "Required for customer scope."}
                )
            if self.owner_user_id is not None:
                raise ValidationError(
                    {"owner_user": "Must be null for customer scope."}
                )
            # Cross-tenant guard.
            if (
                self.scope_customer
                and self.tenant_id
                and str(self.scope_customer.tenant_id) != str(self.tenant_id)
            ):
                raise ValidationError(
                    {"scope_customer": "Customer belongs to a different tenant."}
                )
        elif self.scope_kind == SCOPE_PERSONAL:
            if self.scope_customer_id is not None:
                raise ValidationError(
                    {"scope_customer": "Must be null for personal scope."}
                )
            if self.owner_user_id is None:
                raise ValidationError(
                    {"owner_user": "Required for personal scope."}
                )

        # Cadence-shape.
        if self.cadence == CADENCE_WEEKLY:
            if self.day_of_week is None:
                raise ValidationError(
                    {"day_of_week": "Required when cadence='weekly'."}
                )
            if self.day_of_month is not None:
                raise ValidationError(
                    {"day_of_month": "Must be null for weekly cadence."}
                )
            if not (0 <= self.day_of_week <= 6):
                raise ValidationError(
                    {"day_of_week": "Must be 0 (Monday) through 6 (Sunday)."}
                )
        elif self.cadence == CADENCE_MONTHLY:
            if self.day_of_month is None:
                raise ValidationError(
                    {"day_of_month": "Required when cadence='monthly'."}
                )
            if self.day_of_week is not None:
                raise ValidationError(
                    {"day_of_week": "Must be null for monthly cadence."}
                )
            if not (1 <= self.day_of_month <= 28):
                raise ValidationError(
                    {"day_of_month": "Must be 1-28 (avoids month-length gotchas)."}
                )

    def save(self, *args, **kwargs):
        # Same pattern as NotificationRule: full_clean before save so
        # admin/script/fixture write paths all hit the validators.
        self.full_clean(
            exclude=["recipient_users", "recipient_groups", "recipient_external"]
        )
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.name} [{self.provider_kind}/{self.cadence}]"
