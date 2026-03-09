"""
Life Tracking Models - Unified life-limited tracking for parts and materials.

Provides tenant-configurable tracking for:
- Part life limits (cycles, hours) - aerospace LLPs, rotables
- Material shelf life (calendar-based) - greases, adhesives, chemicals
- Equipment usage (hours, cycles) - machinery, tooling

Foundation models only. Extended features (audit trail, auto-increment rules,
life extensions) can be added later.
"""

from decimal import Decimal

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from .core import SecureModel, SecureManager, SecureQuerySet


class LifeLimitDefinition(SecureModel):
    """
    Tenant-defined life tracking rule.

    Examples:
    - "Flight Cycles" - hard_limit=20000 cycles
    - "Shelf Life" - is_calendar_based=True, hard_limit=365 days
    - "Shot Count" - soft_limit=400000, hard_limit=500000
    """

    name = models.CharField(
        max_length=100,
        help_text="Display name (e.g., 'Flight Cycles', 'Shelf Life')"
    )
    unit = models.CharField(
        max_length=50,
        help_text="Unit being tracked (e.g., 'cycles', 'hours', 'days')"
    )
    unit_label = models.CharField(
        max_length=50,
        help_text="Display label (e.g., 'Cycles', 'Flight Hours', 'Days')"
    )

    is_calendar_based = models.BooleanField(
        default=False,
        help_text="If true, value is calculated from reference_date. "
                  "Valid units for calendar-based: days, months, years"
    )

    soft_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Warning/overhaul threshold"
    )
    hard_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Absolute limit - block/retire when reached"
    )

    class Meta:
        verbose_name = 'Life Limit Definition'
        verbose_name_plural = 'Life Limit Definitions'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'name'],
                name='life_limit_def_tenant_name_uniq'
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.unit_label})"


class PartTypeLifeLimit(SecureModel):
    """
    Links a LifeLimitDefinition to a PartType.

    Defines which life limits apply to which part types, and whether tracking
    is required when creating parts of that type.
    """

    part_type = models.ForeignKey(
        'Tracker.PartTypes',
        on_delete=models.CASCADE,
        related_name='life_limits'
    )
    definition = models.ForeignKey(
        LifeLimitDefinition,
        on_delete=models.CASCADE,
        related_name='part_type_links'
    )
    is_required = models.BooleanField(
        default=True,
        help_text="If true, parts of this type must have this tracking"
    )

    class Meta:
        verbose_name = 'Part Type Life Limit'
        verbose_name_plural = 'Part Type Life Limits'
        constraints = [
            models.UniqueConstraint(
                fields=['part_type', 'definition'],
                name='part_type_life_limit_uniq'
            ),
        ]

    def __str__(self):
        req = " (required)" if self.is_required else ""
        return f"{self.part_type.name}: {self.definition.name}{req}"


class LifeTrackingQuerySet(SecureQuerySet):
    """Custom queryset with helper methods for life tracking."""

    def for_object(self, obj):
        """Filter to tracking records for a specific object."""
        ct = ContentType.objects.get_for_model(obj)
        return self.filter(content_type=ct, object_id=obj.pk)

    def expired(self):
        """Filter to expired tracking records."""
        return self.filter(cached_status='EXPIRED')

    def warning(self):
        """Filter to tracking records at warning level."""
        return self.filter(cached_status='WARNING')


class LifeTrackingManager(SecureManager):
    """Manager using LifeTrackingQuerySet."""

    def get_queryset(self):
        return LifeTrackingQuerySet(self.model, using=self._db)

    def for_object(self, obj):
        return self.get_queryset().for_object(obj)


class LifeTracking(SecureModel):
    """
    Tracks accumulated life for a specific entity.

    Attaches to any model (Parts, MaterialLot, Equipment) via GenericForeignKey.
    Each entity can have multiple tracking records (one per definition).

    Usage:
        # Create tracking for a part
        tracking, created = LifeTracking.for_object(part, cycles_def, accumulated=5000)

        # Query tracking for an object
        LifeTracking.objects.for_object(part)

        # Increment after operation
        tracking.increment(100)

        # Check status
        tracking.status        # 'OK', 'WARNING', 'EXPIRED'
        tracking.remaining     # cycles/hours/days until hard limit
        tracking.percent_used  # 0-100+
    """

    class Source(models.TextChoices):
        OEM = 'OEM', 'OEM Records'
        CUSTOMER = 'CUSTOMER', 'Customer Provided'
        LOGBOOK = 'LOGBOOK', 'Logbook Entry'
        CALCULATED = 'CALCULATED', 'Calculated'
        ESTIMATED = 'ESTIMATED', 'Estimated'
        TRANSFERRED = 'TRANSFERRED', 'Transferred from Core'
        RESET = 'RESET', 'Reset After Rebuild'

    objects = LifeTrackingManager()

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
    )
    object_id = models.UUIDField()
    tracked_object = GenericForeignKey('content_type', 'object_id')

    definition = models.ForeignKey(
        LifeLimitDefinition,
        on_delete=models.PROTECT,
        related_name='tracking_records'
    )

    accumulated = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Current accumulated value"
    )

    reference_date = models.DateField(
        null=True,
        blank=True,
        help_text="For calendar-based: manufacture/install/overhaul date"
    )

    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.ESTIMATED,
        help_text="Where did this life data come from?"
    )

    # Cached for efficient queryset filtering
    cached_status = models.CharField(
        max_length=10,
        default='OK',
        db_index=True,
        help_text="Cached status, updated on save"
    )

    # Per-instance limit overrides (instead of separate LifeExtension model)
    hard_limit_override = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Override hard limit for this specific instance"
    )
    soft_limit_override = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Override soft limit for this specific instance"
    )
    override_reason = models.CharField(
        max_length=200,
        blank=True,
        help_text="Reason for limit override"
    )
    override_approved_by = models.ForeignKey(
        'Tracker.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='approved_life_overrides'
    )

    # Reset history (instead of separate LifeOverhaul model)
    # Format: [{"at": "2024-01-15T...", "from_value": 50000, "reason": "Rebuild", "user_id": "..."}]
    reset_history = models.JSONField(
        default=list,
        blank=True,
        help_text="History of resets/overhauls"
    )

    class Meta:
        verbose_name = 'Life Tracking'
        verbose_name_plural = 'Life Tracking Records'
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['content_type', 'object_id', 'definition'],
                name='life_tracking_entity_definition_uniq'
            ),
        ]

    @classmethod
    def for_object(cls, obj, definition, **defaults):
        """
        Get or create life tracking for an object.

        Args:
            obj: The object to track (Part, MaterialLot, etc.)
            definition: LifeLimitDefinition instance
            **defaults: Fields to set on create (accumulated, reference_date, etc.)

        Returns:
            (LifeTracking, created) tuple
        """
        ct = ContentType.objects.get_for_model(obj)
        defaults.setdefault('tenant', obj.tenant)
        return cls.objects.get_or_create(
            content_type=ct,
            object_id=obj.pk,
            definition=definition,
            defaults=defaults
        )

    def increment(self, value):
        """
        Add to accumulated value and save.

        Args:
            value: Amount to add (can be negative for corrections)

        Returns:
            self for chaining
        """
        self.accumulated += Decimal(str(value))
        self.save(update_fields=['accumulated', 'updated_at', 'cached_status'])
        return self

    def reset(self, user=None, reason=""):
        """
        Reset accumulated value to zero (after rebuild/overhaul).

        Records the reset in history for audit purposes.
        django-auditlog also captures the change automatically.

        Args:
            user: User performing the reset
            reason: Reason for reset (e.g., "Complete rebuild")

        Returns:
            self for chaining
        """
        history_entry = {
            "at": timezone.now().isoformat(),
            "from_value": float(self.accumulated),
            "reason": reason,
            "user_id": str(user.pk) if user else None,
        }
        self.reset_history = self.reset_history + [history_entry]  # Append immutably
        self.accumulated = Decimal('0')
        self.source = self.Source.RESET
        self.save()
        return self

    def apply_override(self, hard_limit=None, soft_limit=None, reason="", approved_by=None):
        """
        Apply per-instance limit override.

        Use when engineering approves extended service for a specific part.

        Args:
            hard_limit: New hard limit (None to clear)
            soft_limit: New soft limit (None to clear)
            reason: Justification for override
            approved_by: User who approved

        Returns:
            self for chaining
        """
        self.hard_limit_override = hard_limit
        self.soft_limit_override = soft_limit
        self.override_reason = reason
        self.override_approved_by = approved_by
        self.save()
        return self

    def __str__(self):
        return f"{self.definition.name}: {self.current_value}"

    @property
    def current_value(self):
        """Current value - calculated for calendar, accumulated for others."""
        if self.definition.is_calendar_based and self.reference_date:
            days = (timezone.now().date() - self.reference_date).days
            unit = self.definition.unit.lower()
            if unit in ('months', 'month'):
                return Decimal(days) / Decimal('30.44')
            elif unit in ('years', 'year'):
                return Decimal(days) / Decimal('365.25')
            return Decimal(days)
        return self.accumulated

    @property
    def effective_hard_limit(self):
        """Hard limit with per-instance override applied."""
        return self.hard_limit_override if self.hard_limit_override is not None else self.definition.hard_limit

    @property
    def effective_soft_limit(self):
        """Soft limit with per-instance override applied."""
        return self.soft_limit_override if self.soft_limit_override is not None else self.definition.soft_limit

    @property
    def remaining(self):
        """Remaining until hard limit (None if no limit)."""
        limit = self.effective_hard_limit
        if limit is None:
            return None
        return max(Decimal('0'), limit - self.current_value)

    @property
    def remaining_to_soft_limit(self):
        """Remaining until soft limit / overhaul interval (None if no limit)."""
        limit = self.effective_soft_limit
        if limit is None:
            return None
        return max(Decimal('0'), limit - self.current_value)

    @property
    def percent_used(self):
        """Percentage of hard limit consumed (0-100+). None if no hard limit."""
        limit = self.effective_hard_limit
        if not limit:
            return None
        return float(self.current_value / limit * 100)

    @property
    def status(self):
        """Returns 'OK', 'WARNING', or 'EXPIRED'."""
        current = self.current_value
        hard = self.effective_hard_limit
        soft = self.effective_soft_limit

        if hard is not None and current >= hard:
            return 'EXPIRED'
        if soft is not None and current >= soft:
            return 'WARNING'
        return 'OK'

    @property
    def is_blocked(self):
        """Should this entity be blocked from advancement?"""
        return self.status == 'EXPIRED'

    def save(self, *args, **kwargs):
        # Update cached status for efficient filtering
        self.cached_status = self.status
        super().save(*args, **kwargs)
