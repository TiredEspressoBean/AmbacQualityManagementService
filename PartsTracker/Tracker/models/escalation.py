"""
Escalation models — Phase 4 add-on to the rule-driven dispatcher.

Three models compose into a chain:

    NotificationRule  1───1  EscalationPolicy  1───n  EscalationStep
                                       │
                                       │ 1───n
                                       ▼
                              EscalationInstance
                              (one per source record, stateful)

When a rule with an enabled `EscalationPolicy` fires, the dispatcher creates
an `EscalationInstance` keyed on the source record (content_type + object_id).
The beat task `tick_escalations` advances instances on schedule, checks ack
status via the registry, fires the next step's outbox rows with the step's
extra recipients merged in, and marks the instance `exhausted` after the
last step or `acknowledged` / `cancelled` when the source record signals
resolution.

Runtime semantics: see `Documents/NOTIFICATION_SYSTEM_DESIGN.md` → Escalation.
"""
from __future__ import annotations

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from .core import SecureModel, TenantGroup


# Maximum number of steps in a single escalation chain. Aerospace-lean —
# pharma/medical can extend later. Enforced by DB CHECK constraint.
MAX_ESCALATION_STEPS = 3


class EscalationStatus(models.TextChoices):
    """Lifecycle of an EscalationInstance."""
    PENDING = 'pending', 'Pending'
    ACKNOWLEDGED = 'acknowledged', 'Acknowledged'
    EXHAUSTED = 'exhausted', 'Exhausted'
    CANCELLED = 'cancelled', 'Cancelled'


# =============================================================================
# EscalationPolicy — one per rule.
# =============================================================================

class EscalationPolicy(SecureModel):
    """A rule's escalation policy. Owns the ordered steps and the on/off
    toggle. 1:1 with NotificationRule.

    Personal rules use this same model under the "coverage" framing —
    casual users author a single-step chain ("if I don't ack in 4h, forward
    to Sarah"). The DB shape is identical; only the UI differs.
    """

    rule = models.OneToOneField(
        'Tracker.NotificationRule',
        on_delete=models.CASCADE,
        related_name='escalation_policy',
    )
    enabled = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=['tenant', 'enabled']),
        ]

    def __str__(self) -> str:
        return f"EscalationPolicy(rule={self.rule_id}, enabled={self.enabled})"

    def delete(self, using=None, keep_parents=False):
        """Hard delete — the policy is config attached to a rule. Soft-delete
        would leave an archived row blocking the OneToOne(rule) unique
        constraint on re-create. CASCADE will hard-delete owned steps and
        instances along with it."""
        return models.Model.delete(self, using=using, keep_parents=keep_parents)


# =============================================================================
# EscalationStep — ordered steps within a policy.
# =============================================================================

class EscalationStep(SecureModel):
    """One step in an escalation chain.

    `delay_seconds` is the wait from the previous step's fire time (or from
    the initial rule fire for step `order=0`). `recipient_users` and
    `recipient_groups` are MERGED with the rule's recipients when the step
    fires — they don't replace; they add. `subject_override` lets the step
    use a different email subject (e.g. "URGENT — unacknowledged for 4 hours").
    """

    policy = models.ForeignKey(
        EscalationPolicy,
        on_delete=models.CASCADE,
        related_name='steps',
    )
    order = models.PositiveSmallIntegerField(
        help_text="Step position in the chain, 0-indexed. Max 2 (three steps).",
    )
    delay_seconds = models.PositiveIntegerField(
        help_text=(
            "Wait from the previous step's fire (or from rule fire for order=0)."
        ),
    )
    recipient_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='escalation_steps_as_recipient',
    )
    recipient_groups = models.ManyToManyField(
        TenantGroup,
        blank=True,
        related_name='escalation_steps',
    )
    subject_override = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['policy', 'order'],
                name='escalation_step_unique_order',
            ),
            models.CheckConstraint(
                check=Q(order__lt=MAX_ESCALATION_STEPS),
                name='escalation_step_order_lt_max',
            ),
        ]
        indexes = [
            models.Index(fields=['policy', 'order']),
        ]
        ordering = ['order']

    def delete(self, using=None, keep_parents=False):
        """Hard delete — escalation steps are config, not entities needing
        an audit trail. The SecureModel soft-delete default would leave
        archived rows blocking the (policy, order) unique constraint when
        the serializer replaces a step list."""
        return models.Model.delete(self, using=using, keep_parents=keep_parents)

    def clean(self):
        super().clean()
        if self.order is not None and not (0 <= self.order < MAX_ESCALATION_STEPS):
            raise ValidationError({
                'order': f"Must be 0..{MAX_ESCALATION_STEPS - 1}."
            })
        if self.delay_seconds is not None and self.delay_seconds < 1:
            raise ValidationError({
                'delay_seconds': "Must be at least 1 second.",
            })

    def __str__(self) -> str:
        return f"EscalationStep(policy={self.policy_id}, order={self.order})"


# =============================================================================
# EscalationInstance — stateful in-flight chain, one per source record.
# =============================================================================

class EscalationInstance(SecureModel):
    """A live escalation chain anchored to one source record.

    Created by the dispatcher when a rule with `EscalationPolicy.enabled`
    fires. The unique constraint on `(policy, source_content_type, source_object_id)`
    means re-firing the same rule against the same source record can't
    create a second instance — the existing one wins.

    The beat task `tick_escalations` scans `status='pending'` rows where
    `next_fire_at <= now`, locks each row, checks ack via the registry,
    and either advances to the next step (writing outbox rows + updating
    `next_fire_at`) or marks the instance `acknowledged` / `exhausted`.

    Source-record void/close signals separately mark instances `cancelled`.
    """

    policy = models.ForeignKey(
        EscalationPolicy,
        on_delete=models.CASCADE,
        related_name='instances',
    )
    # GenericForeignKey to the source record (NCR, CAPA, ApprovalRequest, etc.)
    # — `(content_type, object_id)` is the natural key that ack callbacks
    # check against.
    source_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name='+',
    )
    source_object_id = models.CharField(max_length=64)
    source_record = GenericForeignKey('source_content_type', 'source_object_id')

    # Which step fires next. 0 = next tick fires step[0]. Incremented after
    # each step fires. When `current_step >= step_count`, mark exhausted.
    current_step = models.PositiveSmallIntegerField(
        default=0,
        help_text="0-indexed; the step that fires on the next tick.",
    )
    next_fire_at = models.DateTimeField(db_index=True)

    status = models.CharField(
        max_length=16,
        choices=EscalationStatus.choices,
        default=EscalationStatus.PENDING,
        db_index=True,
    )

    # Per-fire audit trail: append-only list of dicts capturing what happened.
    # Example entry: {"step": 0, "fired_at": "2026-05-20T16:00:00Z", "recipient_count": 3}
    audit = models.JSONField(default=list, blank=True)

    # Snapshot of the event payload that opened this chain. Stored verbatim
    # at dispatcher time so step firings render with the same context the
    # original notification had — the source row alone can't reconstruct
    # derived fields (e.g. `part_number`, `opened_by_name`) without
    # re-running domain emit logic.
    payload_snapshot = models.JSONField(default=dict, blank=True)

    # Correlation back to the original rule-fire outbox row(s). Lets the
    # admin "view this escalation's history" surface in the activity log.
    correlation_id = models.CharField(max_length=128, blank=True, default='')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['policy', 'source_content_type', 'source_object_id'],
                name='escalation_instance_unique_per_source',
            ),
        ]
        indexes = [
            models.Index(fields=['status', 'next_fire_at']),
            models.Index(fields=['tenant', 'status']),
            models.Index(
                fields=['source_content_type', 'source_object_id'],
                name='esc_inst_source_idx',
            ),
        ]

    @property
    def is_pending(self) -> bool:
        return self.status == EscalationStatus.PENDING

    @property
    def is_terminal(self) -> bool:
        """True iff the instance has reached a terminal state and won't fire again."""
        return self.status in (
            EscalationStatus.ACKNOWLEDGED,
            EscalationStatus.EXHAUSTED,
            EscalationStatus.CANCELLED,
        )

    def __str__(self) -> str:
        return (
            f"EscalationInstance(policy={self.policy_id}, "
            f"source={self.source_content_type_id}:{self.source_object_id}, "
            f"step={self.current_step}, status={self.status})"
        )
