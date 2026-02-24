"""
MES Standard Tier Models

Contains full traceability and compliance features:
- Equipment: EquipmentType, Equipments (tracking of manufacturing equipment)
- Sampling: SamplingRuleSet, SamplingRule, SamplingTriggerState, etc. (quality sampling engine)
- MeasurementDefinition: Measurement specifications with tolerances
- MaterialLot: Lot tracking with parent/child support for splits
- MaterialUsage: Junction table tracking materials/components used in parts
- TimeEntry: Labor time tracking (production, setup, rework, downtime)
- BOM/BOMLine: Bill of Materials (design-level assembly structure)
- AssemblyUsage: Instance-level part-to-assembly tracking
- WorkCenter: Equipment grouping
- Shift/ScheduleSlot: Scheduling infrastructure
- DowntimeEvent: Equipment downtime logging
"""

from decimal import Decimal

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models, transaction
from django.db.models import Q, CheckConstraint, Index

from .core import SecureModel, User, Companies


# =============================================================================
# EQUIPMENT MODELS (moved from mes_lite.py)
# =============================================================================

class EquipmentType(SecureModel):
    """
    Represents a category or classification of equipment used in the manufacturing process.

    Examples include 'Lathe', '3D Printer', or 'CMM Machine'.
    This model provides a way to group and differentiate equipment
    based on function or operational use cases.

    The requires_calibration flag drives calibration tracking behavior for
    equipment of this type. Measurement equipment (CMMs, calipers, gauges)
    should have this enabled; production equipment (CNC, cleaning tanks) should not.
    """

    name = models.CharField(max_length=50)
    """The unique name for this equipment type (e.g., 'Laser Welder')."""

    description = models.TextField(blank=True)
    """Optional description of this equipment type."""

    requires_calibration = models.BooleanField(default=False)
    """Whether equipment of this type requires calibration tracking."""

    default_calibration_interval_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Default calibration interval in days for new equipment of this type"
    )
    """Default interval used when creating new equipment of this type."""

    is_portable = models.BooleanField(default=False)
    """Whether equipment of this type is portable (calipers, torque wrenches) vs fixed (CMM, CNC)."""

    track_downtime = models.BooleanField(default=True)
    """Whether to track downtime/OEE for equipment of this type."""

    class Meta:
        verbose_name_plural = 'Equipment Types'
        verbose_name = 'Equipment Type'

    def __str__(self):
        """
        Returns the name of the equipment type for display purposes.
        """
        return self.name

    def get_equipment_count(self) -> int:
        """Returns count of equipment of this type."""
        return self.equipments_set.count()

    def get_calibration_due_count(self) -> int:
        """Returns count of equipment of this type with calibration due or overdue."""
        return self.equipments_set.filter(
            models.Q(_calibration_status='due_soon') | models.Q(_calibration_status='overdue')
        ).count() if self.requires_calibration else 0


class EquipmentStatus(models.TextChoices):
    """Status choices for equipment operational state."""
    IN_SERVICE = 'in_service', 'In Service'
    OUT_OF_SERVICE = 'out_of_service', 'Out of Service'
    IN_CALIBRATION = 'in_calibration', 'In Calibration'
    IN_MAINTENANCE = 'in_maintenance', 'In Maintenance'
    RETIRED = 'retired', 'Retired'


class EquipmentQuerySet(models.QuerySet):
    """Custom queryset for Equipment with calibration-aware filtering."""

    def requiring_calibration(self):
        """Equipment that requires calibration tracking."""
        return self.filter(
            models.Q(equipment_type__requires_calibration=True) |
            models.Q(_requires_calibration_override=True)
        ).exclude(_requires_calibration_override=False)

    def operational(self):
        """Equipment that is in service."""
        return self.filter(status=EquipmentStatus.IN_SERVICE)

    def calibration_overdue(self):
        """Equipment with overdue calibration."""
        from django.utils import timezone
        from django.db.models import OuterRef, Subquery
        from Tracker.models.qms import CalibrationRecord

        latest_due = CalibrationRecord.objects.filter(
            equipment=OuterRef('pk')
        ).order_by('-calibration_date').values('due_date')[:1]

        return self.requiring_calibration().annotate(
            _latest_due=Subquery(latest_due)
        ).filter(_latest_due__lt=timezone.now().date())

    def calibration_due_soon(self, within_days=30):
        """Equipment with calibration due within N days."""
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models import OuterRef, Subquery
        from Tracker.models.qms import CalibrationRecord

        latest_due = CalibrationRecord.objects.filter(
            equipment=OuterRef('pk')
        ).order_by('-calibration_date').values('due_date')[:1]

        cutoff = timezone.now().date() + timedelta(days=within_days)
        today = timezone.now().date()

        return self.requiring_calibration().annotate(
            _latest_due=Subquery(latest_due)
        ).filter(_latest_due__lte=cutoff, _latest_due__gte=today)


class EquipmentManager(models.Manager):
    """Manager using EquipmentQuerySet."""

    def get_queryset(self):
        return EquipmentQuerySet(self.model, using=self._db)

    def requiring_calibration(self):
        return self.get_queryset().requiring_calibration()

    def operational(self):
        return self.get_queryset().operational()

    def calibration_overdue(self):
        return self.get_queryset().calibration_overdue()

    def calibration_due_soon(self, within_days=30):
        return self.get_queryset().calibration_due_soon(within_days)


class Equipments(SecureModel):
    """
    Individual piece of equipment used in manufacturing processes.

    Tracks equipment assets with optional type classification and associated documents
    for calibration certificates, maintenance logs, operator manuals, etc.

    Calibration tracking is driven by the equipment_type.requires_calibration flag,
    which can be overridden per-equipment via _requires_calibration_override.
    """

    documents = GenericRelation('Tracker.Documents')
    """Documents attached to this equipment (calibration certificates, maintenance logs, manuals, etc.)"""

    # === IDENTITY ===
    name = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=100, blank=True)
    """Physical serial number for identification and scanning."""

    equipment_type = models.ForeignKey(EquipmentType, on_delete=models.SET_NULL, null=True, blank=True)

    # === STATUS ===
    status = models.CharField(
        max_length=20,
        choices=EquipmentStatus.choices,
        default=EquipmentStatus.IN_SERVICE
    )
    """Current operational status of the equipment."""

    # === LOCATION ===
    location = models.CharField(max_length=100, blank=True)
    """Physical location (e.g., 'QA Lab', 'Machine Shop', 'Tool Crib')."""

    # === CALIBRATION ===
    calibration_interval_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Calibration interval in days. Overrides equipment type default if set."
    )
    """Calibration interval - overrides type default if set."""

    _requires_calibration_override = models.BooleanField(
        null=True,
        blank=True,
        db_column='requires_calibration_override',
        help_text="Override equipment type's requires_calibration setting. Null = inherit from type."
    )
    """Override for requires_calibration. Null inherits from equipment_type."""

    # === ASSET INFO ===
    manufacturer = models.CharField(max_length=100, blank=True)
    model_number = models.CharField(max_length=100, blank=True)

    notes = models.TextField(blank=True)

    objects = EquipmentManager()

    class Meta:
        verbose_name_plural = 'Equipments'
        verbose_name = 'Equipment'

    def __str__(self):
        return f"{self.name} ({self.equipment_type})" if self.equipment_type else self.name

    # === CALIBRATION PROPERTIES ===

    @property
    def requires_calibration(self) -> bool:
        """Whether this equipment requires calibration tracking.

        Returns override value if set, otherwise inherits from equipment_type.
        """
        if self._requires_calibration_override is not None:
            return self._requires_calibration_override
        return self.equipment_type.requires_calibration if self.equipment_type else False

    def get_latest_calibration(self):
        """Return the most recent CalibrationRecord for this equipment."""
        return self.calibration_records.first()  # Ordered by -calibration_date

    @property
    def calibration_status(self) -> str | None:
        """Returns calibration status: 'current', 'due_soon', 'overdue', 'failed', or None.

        Returns None if equipment doesn't require calibration.
        """
        if not self.requires_calibration:
            return None
        latest = self.get_latest_calibration()
        if not latest:
            return 'overdue'  # Never calibrated = overdue
        return latest.status

    @property
    def is_calibration_current(self) -> bool:
        """Whether calibration is current (not due, not overdue, not failed).

        Returns True for equipment that doesn't require calibration.
        """
        if not self.requires_calibration:
            return True
        latest = self.get_latest_calibration()
        return latest.is_current if latest else False

    @property
    def next_calibration_due(self):
        """Date of next calibration due, or None."""
        latest = self.get_latest_calibration()
        return latest.due_date if latest else None

    @property
    def days_until_calibration_due(self) -> int | None:
        """Days until calibration due. Negative if overdue. None if N/A."""
        if not self.requires_calibration:
            return None
        latest = self.get_latest_calibration()
        if not latest:
            return None
        return latest.days_until_due

    # === OPERATIONAL PROPERTIES ===

    @property
    def is_operational(self) -> bool:
        """Whether this equipment can be used right now.

        True if in_service AND calibration is current (or not required).
        """
        return self.status == EquipmentStatus.IN_SERVICE and self.is_calibration_current

    @property
    def is_portable(self) -> bool:
        """Whether this equipment is portable. Inherits from equipment_type."""
        return self.equipment_type.is_portable if self.equipment_type else False

    # === HISTORY METHODS ===

    def get_calibration_history(self):
        """Return all CalibrationRecords for this equipment, newest first."""
        return self.calibration_records.all()

    def get_downtime_history(self):
        """Return all DowntimeEvents for this equipment, newest first."""
        return self.downtime_events.order_by('-start_time')

    def get_affected_parts(self, start_date, end_date):
        """Return parts that used this equipment within the date range.

        Critical for impact assessment when equipment is found out of calibration.
        Query: "What parts did this equipment touch since last known good calibration?"
        """
        from Tracker.models import Parts
        from Tracker.models.qms import EquipmentUsage

        return Parts.objects.filter(
            id__in=EquipmentUsage.objects.filter(
                equipment=self,
                created_at__date__range=(start_date, end_date)
            ).values_list('part_id', flat=True)
        ).distinct()

    def get_effective_calibration_interval(self) -> int | None:
        """Return the effective calibration interval in days.

        Uses equipment-specific interval if set, otherwise falls back to type default.
        """
        if self.calibration_interval_days:
            return self.calibration_interval_days
        if self.equipment_type and self.equipment_type.default_calibration_interval_days:
            return self.equipment_type.default_calibration_interval_days
        return None


# =============================================================================
# SAMPLING MODELS (moved from mes_lite.py)
# =============================================================================

class SamplingRuleType(models.TextChoices):
    EVERY_NTH_PART = "every_nth_part", "Every Nth Part"
    PERCENTAGE = "percentage", "Percentage of Parts"
    RANDOM = "random", "Pure Random"
    FIRST_N_PARTS = "first_n_parts", "First N Parts"
    LAST_N_PARTS = "last_n_parts", "Last N Parts"
    EXACT_COUNT = "exact_count", "Exact Count (No Variance)"


class SamplingRuleSet(SecureModel):
    """
    A versioned set of sampling rules applied to a step/part type combination.

    Supports fallback rulesets (triggered after consecutive failures) and
    rule versioning through the supersedes relationship.
    """
    part_type = models.ForeignKey('Tracker.PartTypes', on_delete=models.CASCADE)
    process = models.ForeignKey(
        'Tracker.Processes',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Optional process context. Steps can be in multiple processes."
    )
    step = models.ForeignKey(
        'Tracker.Steps',
        on_delete=models.CASCADE,
        related_name="sampling_ruleset"
    )

    name = models.CharField(max_length=100)
    origin = models.CharField(max_length=100, blank=True)
    active = models.BooleanField(default=True)

    supersedes = models.OneToOneField(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="superseded_by"
    )

    # CSP fallback support
    fallback_ruleset = models.OneToOneField(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="used_as_fallback_for"
    )
    fallback_threshold = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of consecutive failures before switching to fallback"
    )
    fallback_duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of good parts required before reverting to this ruleset"
    )

    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    modified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    is_fallback = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} (v{self.version})"

    def supersede_with(self, *, name, rules, created_by):
        return SamplingRuleSet.create_with_rules(
            part_type=self.part_type,
            process=self.process,
            step=self.step,
            name=name,
            rules=rules,
            supersedes=self,
            created_by=created_by,
        )

    @classmethod
    def create_with_rules(cls, *, part_type, process, step, name, rules=None, fallback_ruleset=None,
                          fallback_threshold=None, fallback_duration=None, created_by=None, origin="", active=True,
                          supersedes=None, is_fallback=False):
        ruleset = cls.objects.create(
            part_type=part_type,
            process=process,
            step=step,
            name=name,
            fallback_ruleset=fallback_ruleset,
            fallback_threshold=fallback_threshold,
            fallback_duration=fallback_duration,
            created_by=created_by,
            origin=origin,
            active=active,
            supersedes=supersedes,
            is_fallback=is_fallback,
        )

        SamplingRule.bulk_create_for_ruleset(
            ruleset=ruleset,
            rules=rules or [],
            created_by=created_by,
        )

        return ruleset

    def activate(self, user=None):
        """Activate this ruleset and deactivate others"""
        # Import here to avoid circular import
        from .mes_lite import Parts, PartsStatus
        from Tracker.sampling import SamplingFallbackApplier

        # Deactivate other rulesets for same step/part_type
        SamplingRuleSet.objects.filter(
            step=self.step,
            part_type=self.part_type,
            active=True,
            is_fallback=self.is_fallback
        ).exclude(pk=self.pk).update(active=False)

        # Activate this ruleset
        self.active = True
        self.modified_by = user
        self.save()

        # Re-evaluate sampling for affected active parts
        self._reevaluate_active_parts(user)

    def _reevaluate_active_parts(self, user=None):
        """Re-evaluate sampling for parts currently at this step"""
        from .mes_lite import Parts, PartsStatus
        from Tracker.sampling import SamplingFallbackApplier

        active_parts = Parts.objects.filter(
            step=self.step,
            part_type=self.part_type,
            part_status__in=[PartsStatus.PENDING, PartsStatus.IN_PROGRESS]
        )

        updates = []
        for part in active_parts:
            evaluator = SamplingFallbackApplier(part=part)
            result = evaluator.evaluate()

            part.requires_sampling = result.get("requires_sampling", False)
            part.sampling_rule = result.get("rule")
            part.sampling_ruleset = result.get("ruleset")
            part.sampling_context = result.get("context", {})
            updates.append(part)

        # Bulk update
        Parts.objects.bulk_update(
            updates,
            ["requires_sampling", "sampling_rule", "sampling_ruleset", "sampling_context"]
        )

    def create_fallback_trigger(self, triggering_part, quality_report):
        """Create fallback trigger and re-evaluate remaining parts"""
        if not self.fallback_ruleset:
            return None

        trigger_state = SamplingTriggerState.objects.create(
            ruleset=self.fallback_ruleset,
            work_order=triggering_part.work_order,
            step=self.step,
            triggered_by=quality_report
        )

        # Re-evaluate remaining parts with fallback rules
        self._apply_fallback_to_remaining_parts(triggering_part)

        return trigger_state

    def _apply_fallback_to_remaining_parts(self, triggering_part):
        """Apply fallback sampling to remaining parts in work order"""
        from .mes_lite import Parts, PartsStatus
        from Tracker.sampling import SamplingFallbackApplier

        remaining_parts = Parts.objects.filter(
            work_order=triggering_part.work_order,
            step=self.step,
            part_type=self.part_type,
            part_status__in=[PartsStatus.PENDING, PartsStatus.IN_PROGRESS],
            id__gt=triggering_part.id
        )

        updates = []
        for part in remaining_parts:
            evaluator = SamplingFallbackApplier(part=part)
            result = evaluator.evaluate()  # Will use fallback rules

            part.requires_sampling = result.get("requires_sampling", False)
            part.sampling_rule = result.get("rule")
            part.sampling_ruleset = result.get("ruleset")
            part.sampling_context = result.get("context", {})
            updates.append(part)

        Parts.objects.bulk_update(
            updates,
            ["requires_sampling", "sampling_rule", "sampling_ruleset", "sampling_context"]
        )


class SamplingRule(SecureModel):
    """
    Individual sampling rule within a ruleset.

    Defines how parts are selected for quality inspection (e.g., every Nth part,
    percentage-based, random, first N, etc.).
    """
    ruleset = models.ForeignKey(SamplingRuleSet, on_delete=models.CASCADE, related_name="rules")
    rule_type = models.CharField(max_length=32, choices=SamplingRuleType.choices)
    value = models.PositiveIntegerField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    modified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    # Compliance fields
    algorithm_description = models.TextField(
        default="SHA-256 hash modulo arithmetic",
        help_text="Description of sampling algorithm for audit purposes"
    )
    """Documentation of the sampling algorithm used for compliance."""

    last_validated = models.DateTimeField(null=True, blank=True)
    """Timestamp of last validation for regulatory compliance."""

    @classmethod
    def bulk_create_for_ruleset(cls, *, ruleset, rules, created_by=None):
        instances = [
            cls(
                ruleset=ruleset,
                rule_type=rule["rule_type"],
                value=rule.get("value"),
                order=rule.get("order", i),
                created_by=created_by,
            )
            for i, rule in enumerate(rules)
        ]
        cls.objects.bulk_create(instances)


class SamplingTriggerState(SecureModel):
    """
    Tracks active fallback sampling triggers for a work order/step.

    When quality failures exceed a threshold, fallback rules are activated.
    This model tracks the trigger state and progress toward auto-deactivation.
    """
    ruleset = models.ForeignKey(SamplingRuleSet, on_delete=models.CASCADE)
    work_order = models.ForeignKey('Tracker.WorkOrder', on_delete=models.CASCADE)
    step = models.ForeignKey('Tracker.Steps', on_delete=models.CASCADE)
    active = models.BooleanField(default=True)

    triggered_by = models.ForeignKey('Tracker.QualityReports', null=True, blank=True, on_delete=models.SET_NULL)
    triggered_at = models.DateTimeField(auto_now_add=True)

    success_count = models.PositiveIntegerField(default=0)
    fail_count = models.PositiveIntegerField(default=0)

    parts_inspected = models.ManyToManyField("Tracker.Parts", blank=True)

    # Email notification fields
    notification_sent = models.BooleanField(default=False)
    notification_sent_at = models.DateTimeField(null=True, blank=True)
    notified_users = models.ManyToManyField(User, blank=True, related_name='sampling_notifications')

    class Meta:
        verbose_name = 'Sampling Trigger State'
        verbose_name_plural = 'Sampling Trigger States'
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'ruleset', 'work_order', 'step'],
                name='samplingtriggerstate_tenant_uniq'
            ),
        ]

    def __str__(self):
        return f"Fallback {self.ruleset} active on WO-{self.work_order.ERP_id} @ {self.step}"


class SamplingTriggerManager:
    """
    Manager class for updating sampling trigger state based on inspection results.

    Not a Django model - this is a utility class for managing trigger state transitions.
    """
    def __init__(self, part, status: str):
        self.part = part
        self.status = status
        self.step = part.step
        self.work_order = part.work_order

    def update_state(self):
        active_state = SamplingTriggerState.objects.filter(
            step=self.step,
            work_order=self.work_order,
            active=True
        ).order_by("-triggered_at").first()

        if not active_state:
            return

        if self.status == "PASS":
            active_state.success_count += 1
        else:
            active_state.fail_count += 1

        active_state.parts_inspected.add(self.part)
        active_state.save()

        # Auto-deactivate?
        if active_state.ruleset.fallback_duration:
            if active_state.success_count >= active_state.ruleset.fallback_duration:
                active_state.active = False
                active_state.save()


class SamplingAuditLog(SecureModel):
    """
    Comprehensive audit trail for sampling decisions.
    Logs which rule was applied to which part and whether it triggered sampling.
    """
    part = models.ForeignKey('Tracker.Parts', on_delete=models.CASCADE)
    rule = models.ForeignKey(SamplingRule, on_delete=models.CASCADE)
    sampling_decision = models.BooleanField()
    timestamp = models.DateTimeField(auto_now_add=True)
    ruleset_type = models.CharField(
        max_length=20,
        choices=[('PRIMARY', 'Primary Ruleset'), ('FALLBACK', 'Fallback Ruleset')]
    )

    class Meta:
        indexes = [
            models.Index(fields=['part', 'timestamp']),
            models.Index(fields=['rule', 'sampling_decision']),
        ]
        verbose_name = 'Sampling Audit Log'
        verbose_name_plural = 'Sampling Audit Logs'

    def __str__(self):
        return f"Sampling decision for {self.part} at {self.timestamp}"


class SamplingAnalytics(SecureModel):
    """Track sampling effectiveness and compliance metrics"""
    ruleset = models.ForeignKey(SamplingRuleSet, on_delete=models.CASCADE)
    work_order = models.ForeignKey('Tracker.WorkOrder', on_delete=models.CASCADE)

    parts_sampled = models.PositiveIntegerField(default=0)
    parts_total = models.PositiveIntegerField(default=0)
    defects_found = models.PositiveIntegerField(default=0)

    actual_sampling_rate = models.FloatField()
    target_sampling_rate = models.FloatField()
    variance = models.FloatField()  # Difference between actual and target

    class Meta:
        verbose_name = 'Sampling Analytics'
        verbose_name_plural = 'Sampling Analytics'
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'ruleset', 'work_order'],
                name='samplinganalytics_tenant_uniq'
            ),
        ]

    @property
    def sampling_effectiveness(self):
        """Defects found per 100 sampled parts"""
        return (self.defects_found / self.parts_sampled * 100) if self.parts_sampled > 0 else 0

    @property
    def is_compliant(self):
        """Whether sampling rate is within acceptable variance"""
        return abs(self.variance) < 0.5  # Within 0.5%

    def __str__(self):
        return f"Analytics for {self.ruleset} - WO {self.work_order.ERP_id}"


# =============================================================================
# NEW STRUCTURAL MODELS (Standard Tier)
# =============================================================================

class WorkCenter(SecureModel):
    """
    Grouping of equipment and/or workstations in a production area.

    Work centers are used for capacity planning, scheduling, and cost allocation.
    """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)  # Unique per tenant, not globally
    description = models.TextField(blank=True)

    # Capacity info
    capacity_units = models.CharField(
        max_length=20,
        default='hours',
        help_text="Unit of measure for capacity (hours, pieces, etc.)"
    )
    default_efficiency = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100.00,
        help_text="Default efficiency percentage (100 = 100%)"
    )

    # Equipment assignment
    equipment = models.ManyToManyField(
        Equipments,
        blank=True,
        related_name='work_centers'
    )

    # Cost center (for accounting integration)
    cost_center = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = 'Work Center'
        verbose_name_plural = 'Work Centers'
        ordering = ['code']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'code'],
                name='workcenter_tenant_code_uniq'
            ),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Shift(SecureModel):
    """
    Defines a work shift (e.g., Day, Night, Weekend).

    Used for scheduling and labor tracking.
    """
    name = models.CharField(max_length=50)  # e.g., "Day Shift", "Night Shift"
    code = models.CharField(max_length=10)  # e.g., "DAY", "NGT" - unique per tenant

    start_time = models.TimeField()
    end_time = models.TimeField()

    # Days of week this shift applies (stored as comma-separated: "0,1,2,3,4" for Mon-Fri)
    days_of_week = models.CharField(
        max_length=20,
        default="0,1,2,3,4",
        help_text="Comma-separated day numbers (0=Monday, 6=Sunday)"
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Shift'
        verbose_name_plural = 'Shifts'
        ordering = ['start_time']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'code'],
                name='shift_tenant_code_uniq'
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.start_time} - {self.end_time})"


class ScheduleSlot(SecureModel):
    """
    A scheduled production slot at a work center.

    Used for production scheduling and capacity planning.
    """
    work_center = models.ForeignKey(
        WorkCenter,
        on_delete=models.CASCADE,
        related_name='schedule_slots'
    )
    shift = models.ForeignKey(
        Shift,
        on_delete=models.PROTECT,
        related_name='schedule_slots'
    )
    work_order = models.ForeignKey(
        'Tracker.WorkOrder',
        on_delete=models.CASCADE,
        related_name='schedule_slots'
    )

    scheduled_date = models.DateField()
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()

    # Actual timing (filled after production)
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)

    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')

    notes = models.TextField(blank=True)

    # Operator assignment
    assigned_operator = models.ForeignKey(
        'Tracker.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_slots',
        help_text="Operator assigned to this schedule slot"
    )
    """Operator assigned to work this slot."""

    needs_reassignment = models.BooleanField(
        default=False,
        help_text="Flag indicating operator reassignment is needed"
    )
    """Set when assigned operator is unavailable or a reassignment is requested."""

    class Meta:
        verbose_name = 'Schedule Slot'
        verbose_name_plural = 'Schedule Slots'
        ordering = ['scheduled_date', 'scheduled_start']
        indexes = [
            models.Index(fields=['work_center', 'scheduled_date']),
            models.Index(fields=['work_order', 'status']),
        ]

    def __str__(self):
        return f"{self.work_center.code} - {self.work_order.ERP_id} @ {self.scheduled_date}"


class DowntimeEvent(SecureModel):
    """
    Records equipment or work center downtime.

    Used for OEE (Overall Equipment Effectiveness) calculations and maintenance tracking.
    """
    DOWNTIME_CATEGORY_CHOICES = [
        ('planned', 'Planned Maintenance'),
        ('unplanned', 'Unplanned/Breakdown'),
        ('changeover', 'Changeover/Setup'),
        ('calibration', 'Calibration'),
        ('no_work', 'No Work Available'),
        ('no_operator', 'No Operator Available'),
        ('material', 'Waiting for Material'),
        ('quality', 'Quality Issue'),
        ('other', 'Other'),
    ]

    equipment = models.ForeignKey(
        Equipments,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='downtime_events'
    )
    work_center = models.ForeignKey(
        WorkCenter,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='downtime_events'
    )

    category = models.CharField(max_length=20, choices=DOWNTIME_CATEGORY_CHOICES)
    reason = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)

    # Link to work order if downtime occurred during production
    work_order = models.ForeignKey(
        'Tracker.WorkOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='downtime_events'
    )

    reported_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='reported_downtime'
    )
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_downtime'
    )

    class Meta:
        verbose_name = 'Downtime Event'
        verbose_name_plural = 'Downtime Events'
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['equipment', 'start_time']),
            models.Index(fields=['work_center', 'start_time']),
            models.Index(fields=['category', 'start_time']),
        ]

    def __str__(self):
        target = self.equipment or self.work_center
        return f"{target} - {self.category} @ {self.start_time}"

    @property
    def duration(self):
        """Duration of downtime, or None if still ongoing."""
        if self.end_time:
            return self.end_time - self.start_time
        return None


class MaterialLot(SecureModel):
    """
    Tracks a lot of material received from a supplier.

    Supports lot splitting via parent_lot relationship, enabling full material
    traceability from receipt through consumption.
    """
    LOT_STATUS_CHOICES = [
        ('received', 'Received'),
        ('in_use', 'In Use'),
        ('consumed', 'Consumed'),
        ('scrapped', 'Scrapped'),
        ('quarantine', 'Quarantine'),
    ]

    lot_number = models.CharField(max_length=100)  # Unique per tenant, not globally
    parent_lot = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='child_lots'
    )

    # Material type - can be a PartType for components, or generic for raw materials
    material_type = models.ForeignKey(
        'Tracker.PartTypes',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='material_lots'
    )
    material_description = models.CharField(
        max_length=200,
        blank=True,
        help_text="Description for raw materials not tracked as PartTypes"
    )

    supplier = models.ForeignKey(
        Companies,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='supplied_lots'
    )
    supplier_lot_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Supplier's lot/batch number"
    )

    received_date = models.DateField()
    received_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='received_lots'
    )

    # Quantity tracking
    quantity = models.DecimalField(max_digits=12, decimal_places=4)
    quantity_remaining = models.DecimalField(max_digits=12, decimal_places=4)
    unit_of_measure = models.CharField(max_length=20)  # "EA", "KG", "M", etc.

    status = models.CharField(max_length=20, choices=LOT_STATUS_CHOICES, default='received')

    # Shelf life tracking
    manufacture_date = models.DateField(null=True, blank=True)
    expiration_date = models.DateField(null=True, blank=True)

    # Certificate/documentation
    certificate_of_conformance = models.FileField(
        upload_to='lot_certificates/',
        null=True,
        blank=True
    )

    # Location
    storage_location = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = 'Material Lot'
        verbose_name_plural = 'Material Lots'
        ordering = ['-received_date']
        indexes = [
            models.Index(fields=['lot_number']),
            models.Index(fields=['supplier', 'received_date']),
            models.Index(fields=['status', 'expiration_date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'lot_number'],
                name='materiallot_tenant_lotnumber_uniq'
            ),
        ]

    def __str__(self):
        desc = self.material_type.name if self.material_type else self.material_description
        return f"Lot {self.lot_number} - {desc}"

    @transaction.atomic
    def split(self, quantity, reason=""):
        """
        Create a child lot by splitting off a quantity from this lot.

        Uses row-level locking to prevent race conditions when multiple
        splits happen concurrently.

        Args:
            quantity: Amount to split off (must be positive and <= quantity_remaining)
            reason: Optional reason for the split (for audit purposes)

        Returns:
            The new child MaterialLot

        Raises:
            ValueError: If quantity is invalid or lot cannot be split
        """
        # Re-fetch with row lock to prevent race conditions
        locked_self = MaterialLot.objects.select_for_update().get(pk=self.pk)

        # Validate positive quantity
        if quantity <= Decimal('0'):
            raise ValueError("Quantity must be greater than zero")

        if quantity > locked_self.quantity_remaining:
            raise ValueError(f"Cannot split {quantity}, only {locked_self.quantity_remaining} remaining")

        # Validate lot status - can only split received or in_use lots
        if locked_self.status not in ('received', 'in_use'):
            raise ValueError(f"Cannot split a {locked_self.status} lot")

        # Generate child lot number atomically
        child_count = locked_self.child_lots.count()
        child_lot_number = f"{locked_self.lot_number}-{child_count + 1:02d}"

        child = MaterialLot.objects.create(
            tenant=locked_self.tenant,
            lot_number=child_lot_number,
            parent_lot=locked_self,
            material_type=locked_self.material_type,
            material_description=locked_self.material_description,
            supplier=locked_self.supplier,
            supplier_lot_number=locked_self.supplier_lot_number,
            received_date=locked_self.received_date,
            received_by=locked_self.received_by,
            quantity=quantity,
            quantity_remaining=quantity,
            unit_of_measure=locked_self.unit_of_measure,
            status='received',
            manufacture_date=locked_self.manufacture_date,
            expiration_date=locked_self.expiration_date,
            storage_location=locked_self.storage_location,
        )

        # Update parent remaining
        locked_self.quantity_remaining -= quantity
        if locked_self.quantity_remaining <= 0:
            locked_self.status = 'consumed'
        locked_self.save()

        # Refresh self to reflect changes
        self.refresh_from_db()

        return child


class MaterialUsage(SecureModel):
    """
    Junction table tracking what materials/components went into a part.

    This is CRITICAL for full material traceability - enables answering:
    - "What lots went into this part?"
    - "What parts were made from this lot?"
    - "If lot X is recalled, which parts are affected?"

    Exactly one of (lot, harvested_component) must be set.
    """
    # Source - exactly one must be set
    lot = models.ForeignKey(
        MaterialLot,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='usages'
    )
    harvested_component = models.ForeignKey(
        'Tracker.HarvestedComponent',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='usages'
    )

    # Target
    part = models.ForeignKey(
        'Tracker.Parts',
        on_delete=models.PROTECT,
        related_name='material_usages'
    )
    work_order = models.ForeignKey(
        'Tracker.WorkOrder',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='material_usages'
    )

    # Tracking
    qty_consumed = models.DecimalField(max_digits=12, decimal_places=4)
    consumed_at = models.DateTimeField(auto_now_add=True)
    consumed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='material_consumptions'
    )
    step = models.ForeignKey(
        'Tracker.Steps',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='material_usages'
    )

    is_substitute = models.BooleanField(
        default=False,
        help_text="True if this material was a substitute for the BOM-specified material"
    )
    substitution_reason = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = 'Material Usage'
        verbose_name_plural = 'Material Usages'
        ordering = ['-consumed_at']
        constraints = [
            CheckConstraint(
                check=(Q(lot__isnull=False) & Q(harvested_component__isnull=True)) |
                      (Q(lot__isnull=True) & Q(harvested_component__isnull=False)),
                name='material_usage_source_xor'
            )
        ]
        indexes = [
            models.Index(fields=['part']),
            models.Index(fields=['lot']),
            models.Index(fields=['harvested_component']),
        ]

    def __str__(self):
        source = self.lot or self.harvested_component
        return f"{source} -> {self.part}"

    def save(self, *args, **kwargs):
        # Update lot remaining quantity
        if self.lot and not self.pk:  # Only on create
            self.lot.quantity_remaining -= self.qty_consumed
            if self.lot.quantity_remaining <= 0:
                self.lot.status = 'consumed'
            else:
                self.lot.status = 'in_use'
            self.lot.save()
        super().save(*args, **kwargs)


class TimeEntry(SecureModel):
    """
    Labor time tracking - single flexible table with entry_type.

    Supports production time, setup/changeover, rework, downtime, and indirect labor.
    """
    ENTRY_TYPE_CHOICES = [
        ('production', 'Production'),
        ('setup', 'Setup/Changeover'),
        ('rework', 'Rework'),
        ('downtime', 'Downtime'),
        ('indirect', 'Indirect Labor'),
    ]

    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPE_CHOICES)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='time_entries'
    )

    # Context (nullable based on entry_type)
    part = models.ForeignKey(
        'Tracker.Parts',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='time_entries'
    )
    work_order = models.ForeignKey(
        'Tracker.WorkOrder',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='time_entries'
    )
    step = models.ForeignKey(
        'Tracker.Steps',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='time_entries'
    )
    equipment = models.ForeignKey(
        Equipments,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='time_entries'
    )
    work_center = models.ForeignKey(
        WorkCenter,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='time_entries'
    )

    # Details
    notes = models.TextField(blank=True)
    downtime_reason = models.CharField(max_length=100, blank=True)

    # Approval (for labor costing)
    approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='approved_time_entries'
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Time Entry'
        verbose_name_plural = 'Time Entries'
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['user', 'start_time']),
            models.Index(fields=['work_order', 'entry_type']),
            models.Index(fields=['entry_type', 'start_time']),
        ]

    def __str__(self):
        return f"{self.user} - {self.entry_type} @ {self.start_time}"

    @property
    def duration(self):
        """Time spent, or None if still in progress."""
        if self.end_time:
            return self.end_time - self.start_time
        return None

    @property
    def duration_hours(self):
        """Duration in decimal hours for costing."""
        if self.duration:
            return self.duration.total_seconds() / 3600
        return None


class BOM(SecureModel):
    """
    Bill of Materials - design-level assembly structure.

    Defines what components/materials are needed to build a part type.
    Supports both assembly BOMs (building) and disassembly BOMs (for reman).
    """
    BOM_TYPE_CHOICES = [
        ('assembly', 'Assembly'),
        ('disassembly', 'Disassembly'),
    ]

    BOM_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('released', 'Released'),
        ('obsolete', 'Obsolete'),
    ]

    part_type = models.ForeignKey(
        'Tracker.PartTypes',
        on_delete=models.PROTECT,
        related_name='boms'
    )
    revision = models.CharField(max_length=10)
    bom_type = models.CharField(max_length=20, choices=BOM_TYPE_CHOICES, default='assembly')
    status = models.CharField(max_length=20, choices=BOM_STATUS_CHOICES, default='draft')

    description = models.TextField(blank=True)
    effective_date = models.DateField(null=True, blank=True)
    obsolete_date = models.DateField(null=True, blank=True)

    # Approval tracking
    approved_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='approved_boms'
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Bill of Materials'
        verbose_name_plural = 'Bills of Materials'
        ordering = ['part_type', '-revision']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'part_type', 'revision', 'bom_type'],
                name='bom_tenant_parttype_rev_type_uniq'
            ),
        ]

    def __str__(self):
        return f"BOM {self.part_type.name} Rev {self.revision}"


class BOMLine(SecureModel):
    """
    One component line in a Bill of Materials.

    Defines a single component/material requirement for building the parent part.
    """
    bom = models.ForeignKey(
        BOM,
        on_delete=models.CASCADE,
        related_name='lines'
    )
    component_type = models.ForeignKey(
        'Tracker.PartTypes',
        on_delete=models.PROTECT,
        related_name='used_in_boms'
    )

    quantity = models.DecimalField(max_digits=10, decimal_places=4)
    unit_of_measure = models.CharField(max_length=20, default='EA')

    # Drawing references
    find_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="Drawing callout number"
    )
    reference_designator = models.CharField(
        max_length=100,
        blank=True,
        help_text="Reference designator(s) - e.g., 'R1, R2, R3' for electronics"
    )

    # Options
    is_optional = models.BooleanField(default=False)
    allow_harvested = models.BooleanField(
        default=True,
        help_text="For reman: whether harvested components can satisfy this line"
    )

    # Substitutes (comma-separated PartType IDs or linked via separate model)
    notes = models.TextField(blank=True)

    # Line ordering
    line_number = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'BOM Line'
        verbose_name_plural = 'BOM Lines'
        ordering = ['bom', 'line_number']

    def __str__(self):
        return f"{self.bom} Line {self.line_number}: {self.component_type.name} x{self.quantity}"


class AssemblyUsage(SecureModel):
    """
    Tracks actual parts assembled into a parent assembly - instance-level tracking.

    While BOM defines what SHOULD go into an assembly (design),
    AssemblyUsage tracks what ACTUALLY went into a specific assembly instance.

    Also supports removal tracking for remanufacturing/repair scenarios.
    """
    assembly = models.ForeignKey(
        'Tracker.Parts',
        on_delete=models.PROTECT,
        related_name='component_usages',
        help_text="The parent assembly this component was installed into"
    )
    component = models.ForeignKey(
        'Tracker.Parts',
        on_delete=models.PROTECT,
        related_name='installed_in',
        help_text="The component part installed"
    )

    quantity = models.DecimalField(max_digits=10, decimal_places=4, default=1)

    # Link to BOM for design reference
    bom_line = models.ForeignKey(
        BOMLine,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='actual_usages'
    )

    # Installation tracking
    installed_at = models.DateTimeField(auto_now_add=True)
    installed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='installed_assemblies'
    )
    step = models.ForeignKey(
        'Tracker.Steps',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assembly_installations'
    )

    # Removal tracking (for reman/repair)
    removed_at = models.DateTimeField(null=True, blank=True)
    removed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='removed_assemblies'
    )
    removal_reason = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = 'Assembly Usage'
        verbose_name_plural = 'Assembly Usages'
        ordering = ['-installed_at']
        indexes = [
            models.Index(fields=['assembly']),
            models.Index(fields=['component']),
            models.Index(fields=['removed_at']),
        ]

    def __str__(self):
        status = " (removed)" if self.removed_at else ""
        return f"{self.component} in {self.assembly}{status}"

    @property
    def is_installed(self):
        """Whether the component is currently installed (not removed)."""
        return self.removed_at is None

    def remove(self, user, reason=""):
        """Mark this component as removed from the assembly."""
        from django.utils import timezone
        self.removed_at = timezone.now()
        self.removed_by = user
        self.removal_reason = reason
        self.save()
