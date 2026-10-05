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


from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.db.models import Q, CheckConstraint, Index

from .core import SecureModel, SecureManager, SecureQuerySet, User, Companies


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

    _is_versioned = True  # MIL-STD-31000 — tooling/inspection equipment

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
            models.Q(_calibration_status='DUE_SOON') | models.Q(_calibration_status='OVERDUE')
        ).count() if self.requires_calibration else 0


class EquipmentStatus(models.TextChoices):
    """Status choices for equipment operational state."""
    IN_SERVICE = 'IN_SERVICE', 'In Service'
    OUT_OF_SERVICE = 'OUT_OF_SERVICE', 'Out of Service'
    IN_CALIBRATION = 'IN_CALIBRATION', 'In Calibration'
    IN_MAINTENANCE = 'IN_MAINTENANCE', 'In Maintenance'
    RETIRED = 'RETIRED', 'Retired'


class EquipmentQuerySet(SecureQuerySet):
    """Custom queryset for Equipment with calibration-aware filtering.

    Inherits tenant scoping, soft-delete, versioning, and export-control
    chaining from SecureQuerySet.
    """

    def requiring_calibration(self):
        """Equipment that requires calibration tracking."""
        return self.filter(
            models.Q(equipment_type__requires_calibration=True) |
            models.Q(_requires_calibration_override=True)
        ).exclude(_requires_calibration_override=False)

    def operational(self):
        """Equipment that is in service."""
        return self.filter(status=EquipmentStatus.IN_SERVICE)

    def calibration_overdue(self, tenant=None):
        """Equipment with overdue calibration.

        "Today" is the plant's day; `tenant` defaults to the current tenant
        (ContextVar) — pass it explicitly from code that spans tenants.
        """
        from Tracker.services.core.clock import tenant_today
        from django.db.models import OuterRef, Subquery
        from Tracker.models.qms import CalibrationRecord

        latest_due = CalibrationRecord.objects.filter(
            equipment=OuterRef('pk')
        ).order_by('-calibration_date').values('due_date')[:1]

        return self.requiring_calibration().annotate(
            _latest_due=Subquery(latest_due)
        ).filter(_latest_due__lt=tenant_today(tenant))

    def calibration_due_soon(self, within_days=30, tenant=None):
        """Equipment with calibration due within N days (plant's day; see above)."""
        from Tracker.services.core.clock import tenant_today
        from datetime import timedelta
        from django.db.models import OuterRef, Subquery
        from Tracker.models.qms import CalibrationRecord

        latest_due = CalibrationRecord.objects.filter(
            equipment=OuterRef('pk')
        ).order_by('-calibration_date').values('due_date')[:1]

        today = tenant_today(tenant)
        cutoff = today + timedelta(days=within_days)

        return self.requiring_calibration().annotate(
            _latest_due=Subquery(latest_due)
        ).filter(_latest_due__lte=cutoff, _latest_due__gte=today)


class EquipmentManager(SecureManager):
    """Manager using EquipmentQuerySet.

    Inherits .for_user(), .for_tenant(), .active(), etc. from SecureManager.
    """

    def get_queryset(self):
        return EquipmentQuerySet(self.model, using=self._db)

    def requiring_calibration(self):
        return self.get_queryset().requiring_calibration()

    def operational(self):
        return self.get_queryset().operational()

    def calibration_overdue(self, tenant=None):
        return self.get_queryset().calibration_overdue(tenant=tenant)

    def calibration_due_soon(self, within_days=30, tenant=None):
        return self.get_queryset().calibration_due_soon(within_days, tenant=tenant)


class Equipments(SecureModel):
    """
    Individual piece of equipment used in manufacturing processes.

    Tracks equipment assets with optional type classification and associated documents
    for calibration certificates, maintenance logs, operator manuals, etc.

    Calibration tracking is driven by the equipment_type.requires_calibration flag,
    which can be overridden per-equipment via _requires_calibration_override.
    """

    _is_versioned = True  # MIL-STD-31000, AIAG PPAP #16 — equipment asset records

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

    is_schedulable = models.BooleanField(
        default=False,
        help_text="Whether the scheduler treats this asset as a finite resource to "
                  "reserve (CNC, Keyence, CMM). Off for plentiful/handheld equipment "
                  "(calipers) — those are still tracked on step executions, just never "
                  "scheduled. Capacity for a type = the count of its schedulable units.",
    )
    """Scheduler reserves this asset only when True (plan #1). Off ≠ untracked."""

    class BatchMode(models.TextChoices):
        CONCURRENT = 'concurrent', 'Concurrent (parallel jobs)'
        CYCLE = 'cycle', 'Cycle (shared load, fixed cycle time)'

    batch_capacity = models.PositiveIntegerField(
        default=1,
        help_text="How many jobs/parts this resource handles at once. 1 (default) = a normal "
                  "one-at-a-time machine. >1 = a batch/process resource — see `batch_mode`.",
    )
    """Batch size. 1 = serial machine; >1 = batch/process resource (see batch_mode)."""

    batch_mode = models.CharField(
        max_length=12, choices=BatchMode.choices, default=BatchMode.CONCURRENT,
        help_text="How a batch resource (batch_capacity>1) behaves. CONCURRENT: up to "
                  "batch_capacity independent jobs run at once (a bank of wash tanks / parallel "
                  "stations). CYCLE: a furnace/oven — ONE load at a time of up to batch_capacity "
                  "parts, and the cycle time is fixed regardless of how full the load is (a job "
                  "of N parts takes ceil(N / batch_capacity) loads). Ignored when capacity = 1.",
    )
    """CONCURRENT = parallel jobs (cumulative); CYCLE = one shared load-fire-unload at a time."""

    runs_unattended = models.BooleanField(
        null=True, blank=True, default=None,
        help_text="Whether this machine runs lights-out (unattended) between staffed shifts. "
                  "NULL (default): inherit the facility default (OptimizationConfig."
                  "default_machine_unattended). True: the Layer-1 scheduler runs it 24/7, "
                  "gated only by downtime — a lot-operation can span nights/weekends. False: "
                  "its work is confined to the shift calendar (an operator must be present). "
                  "Operator presence for the attended portions is handled by Layer-2 dispatch "
                  "regardless of this flag.",
    )
    """Tri-state lights-out: True/False override, NULL inherits the tenant default."""

    operating_shifts = models.ManyToManyField(
        'Tracker.Shift', blank=True, related_name='equipment',
        help_text="Optional per-machine operating calendar: the shifts this machine runs. "
                  "Empty (default) inherits the tenant-wide shift calendar. Lets a "
                  "bottleneck run more shifts than the rest of the floor. Applies to "
                  "attended (runs_unattended=False) machines; lights-out machines run 24/7.",
    )
    """Per-machine operating calendar; empty inherits the tenant shift calendar."""

    # === LOCATION ===
    location = models.ForeignKey(
        'StorageLocation', null=True, blank=True, on_delete=models.PROTECT, related_name='equipment')
    """Where the machine is (e.g. 'QA Lab', 'Cell 3', 'Tool Crib') — a StorageLocation."""

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

    def create_new_version(self, *, user=None, change_description=None, **field_updates):
        """Thin wrapper — delegates to `services.mes.equipment.create_new_equipment_version`,
        which carries the `operating_shifts` M2M and repoints scheduling configuration
        (step affinities, changeovers, continuous profile, current work-centre
        membership) to the new current row. History (calibration, downtime) stays."""
        from Tracker.services.mes.equipment import create_new_equipment_version
        return create_new_equipment_version(
            self, user=user, change_description=change_description, **field_updates,
        )

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
        """Returns calibration status: 'CURRENT', 'DUE_SOON', 'OVERDUE', 'FAILED', or None.

        Returns None if equipment doesn't require calibration.
        """
        if not self.requires_calibration:
            return None
        latest = self.get_latest_calibration()
        if not latest:
            return 'OVERDUE'  # Never calibrated = overdue
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
        Unions step-execution touch (`StepExecutionEquipment`, any role) and quality-
        report touch (`QualityReportEquipment`) — see plan #1.
        """
        from Tracker.models import Parts
        from Tracker.models.qms import QualityReportEquipment, StepExecutionEquipment

        part_ids = set(
            StepExecutionEquipment.objects.filter(
                equipment=self, step_execution__part__isnull=False,
                step_execution__entered_at__date__range=(start_date, end_date),
            ).values_list('step_execution__part_id', flat=True)
        )
        part_ids.update(
            QualityReportEquipment.objects.filter(
                equipment=self, quality_report__part__isnull=False,
                quality_report__created_at__date__range=(start_date, end_date),
            ).values_list('quality_report__part_id', flat=True)
        )
        # tenant-safe: .objects auto-scopes; part_ids come from tenant-scoped queries
        return Parts.objects.filter(id__in=part_ids).distinct()

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
    EVERY_NTH_PART = "EVERY_NTH_PART", "Every Nth Part"
    PERCENTAGE = "PERCENTAGE", "Percentage of Parts"
    RANDOM = "RANDOM", "Pure Random"
    FIRST_N_PARTS = "FIRST_N_PARTS", "First N Parts"
    LAST_N_PARTS = "LAST_N_PARTS", "Last N Parts"
    EXACT_COUNT = "EXACT_COUNT", "Exact Count (No Variance)"
    # Lot-acceptance sampling (used by RECEIVING steps). Lot-terminal, not per-part
    # streaming — the plan params live on the ruleset (aql/level/severity/strategy)
    # and the evaluator is services.qms.acceptance_sampling.
    AQL = "AQL", "Acceptance Sampling (ANSI/ASQ Z1.4)"
    C_ZERO = "C_ZERO", "Zero-Acceptance (C=0 / Squeglia)"
    # Variables lot acceptance (ANSI/ASQ Z1.9): measures one characteristic on the
    # sample, accepts on x̄/s vs the acceptability constant k. Needs
    # `variables_characteristic` set on the ruleset.
    VARIABLES = "VARIABLES", "Variables Sampling (ANSI/ASQ Z1.9)"


class GateMetric(models.TextChoices):
    """Aggregate quality signal a step gate watches."""
    CONSECUTIVE_FAILS = "CONSECUTIVE_FAILS", "Consecutive failures"
    FAIL_RATE_PCT = "FAIL_RATE_PCT", "Failure rate (%)"
    DEFECTIVE_COUNT = "DEFECTIVE_COUNT", "Defective count"


class GateWindow(models.TextChoices):
    """Window over which a gate metric is computed."""
    WORK_ORDER = "WORK_ORDER", "Whole work order at this step"
    ROLLING_N = "ROLLING_N", "Rolling last N inspections"
    LOT = "LOT", "Receiving lot sample"


class GateAction(models.TextChoices):
    """Automatic actions a fired gate can take. Closed set — each maps to an
    existing service; no free-form scripting."""
    ROUTE_ALTERNATE = "ROUTE_ALTERNATE", "Route to alternate edge"
    TIGHTEN_SAMPLING = "TIGHTEN_SAMPLING", "Tighten sampling (switch ruleset)"
    HOLD_LOT = "HOLD_LOT", "Hold / quarantine"
    RAISE_CAPA_SCAR = "RAISE_CAPA_SCAR", "Raise CAPA / SCAR"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL", "Require approval"


class SamplingRuleSet(SecureModel):
    """
    A versioned set of sampling rules applied to a step/part type combination.

    Supports fallback rulesets (triggered after consecutive failures) and
    rule versioning through the supersedes relationship.
    """

    _is_versioned = True  # ISO 9001 4.4, AIAG PPAP #7

    # Null only for the sampling of a raw material's receiving plan, whose step carries
    # the material instead; `step` identifies the plan either way.
    part_type = models.ForeignKey('Tracker.PartTypes', on_delete=models.CASCADE,
                                  null=True, blank=True)
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
    # Supplier dimension — lets a RECEIVING step resolve a different acceptance-sampling
    # plan per supplier (e.g. tightened for a problem supplier). Null = applies to all
    # suppliers of the part type. Resolution: (step, supplier) > (step, supplier=NULL).
    supplier = models.ForeignKey(
        'Tracker.Companies', on_delete=models.CASCADE, null=True, blank=True,
        related_name="sampling_rulesets",
        help_text="Supplier scope for receiving acceptance sampling. Null = all suppliers.",
    )

    name = models.CharField(max_length=100)
    origin = models.CharField(max_length=100, blank=True)
    active = models.BooleanField(default=True)

    # Acceptance-sampling plan params — used when the ruleset carries an AQL/C_ZERO rule
    # (RECEIVING steps). Null for ordinary per-part streaming rulesets.
    aql = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True,
        help_text="Acceptable Quality Limit for AQL/C=0 lot acceptance.")
    inspection_level = models.CharField(max_length=3, blank=True,
        help_text="ANSI/ASQ Z1.4 inspection level (I/II/III) for AQL sampling.")
    severity = models.CharField(max_length=10, blank=True,
        help_text="AQL inspection severity (NORMAL/TIGHTENED/REDUCED).")
    strategy = models.CharField(max_length=4, blank=True,
        help_text="Acceptance-sampling strategy: C0 (default), Z14, or Z19 (variables).")
    # Z1.9 variables sampling measures ONE characteristic. Null for attribute plans.
    variables_characteristic = models.ForeignKey(
        'Tracker.MeasurementDefinition', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='variables_rulesets',
        help_text="The single numeric characteristic a Z1.9 variables plan measures.",
    )

    supersedes = models.OneToOneField(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="superseded_by"
    )

    # ---- Quality gate: aggregate-signal automatic decisions -------------
    # The gate is the single trigger definition for this step. When the
    # metric crosses the threshold over its window, the configured actions
    # fire (see services/qms/quality_gate.py). Blank gate_metric = no gate
    # (ordinary streaming ruleset). Consecutive-fails + TIGHTEN_SAMPLING is
    # the former CSP fallback, now expressed as one gate among others.
    gate_metric = models.CharField(
        max_length=20, choices=GateMetric.choices, blank=True,
        help_text="Aggregate signal this step watches. Blank = no gate.")
    gate_threshold = models.DecimalField(
        max_digits=7, decimal_places=3, null=True, blank=True,
        help_text="Threshold: percent for FAIL_RATE_PCT, count otherwise.")
    gate_window = models.CharField(
        max_length=12, choices=GateWindow.choices, blank=True,
        help_text="Window the metric is computed over.")
    gate_window_n = models.PositiveIntegerField(
        null=True, blank=True, help_text="N for ROLLING_N windows.")
    gate_min_sample = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Minimum inspections before a FAIL_RATE_PCT gate can fire.")
    gate_actions = models.JSONField(
        default=list, blank=True,
        help_text="List of GateAction codes to fire when the gate trips.")
    gate_capa_type = models.CharField(
        max_length=20, blank=True,
        help_text="CAPA type for a RAISE_CAPA_SCAR action (SUPPLIER => SCAR).")
    gate_capa_severity = models.CharField(
        max_length=10, blank=True,
        help_text="Severity for a RAISE_CAPA_SCAR action.")
    gate_approval_template = models.ForeignKey(
        'Tracker.ApprovalTemplate', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
        help_text="Template for a REQUIRE_APPROVAL action.")

    # TIGHTEN_SAMPLING action params (target ruleset + revert duration).
    fallback_ruleset = models.OneToOneField(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="used_as_fallback_for"
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

    def create_new_version(self, **_):
        raise NotImplementedError(
            "SamplingRuleSet versioning uses the supersede_with / active mechanism. "
            "Use services.mes.sampling_ruleset.supersede_sampling_ruleset instead."
        )

    def supersede_with(self, *, name, rules, created_by):
        from Tracker.services.mes.sampling_ruleset import supersede_sampling_ruleset
        return supersede_sampling_ruleset(self, name=name, rules=rules, user=created_by)

    def activate(self, user=None):
        """Activate this ruleset and deactivate others."""
        from Tracker.services.mes.sampling_ruleset import activate_sampling_ruleset
        activate_sampling_ruleset(self, user=user)

    def create_fallback_trigger(self, triggering_part, quality_report):
        """Create fallback trigger and re-evaluate remaining parts."""
        from Tracker.services.mes.sampling_ruleset import create_sampling_fallback_trigger
        return create_sampling_fallback_trigger(self, triggering_part, quality_report)

    @classmethod
    def create_with_rules(cls, *, part_type, process, step, name, rules=None, fallback_ruleset=None,
                          fallback_duration=None, created_by=None, origin="", active=True,
                          supersedes=None, is_fallback=False, supplier=None):
        ruleset = cls.objects.create(
            part_type=part_type,
            process=process,
            step=step,
            name=name,
            supplier=supplier,
            fallback_ruleset=fallback_ruleset,
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


class SamplingSeverityState(SecureModel):
    """Runtime Z1.4 inspection-severity state for a (receiving step, supplier).

    Severity switching (Normal ↔ Tightened ↔ Reduced) is driven by lot-acceptance
    history, so the *effective* severity is runtime state — not the versioned
    ``SamplingRuleSet.severity`` config field (which is only the *starting*
    severity). Scoped to (step, supplier): incoming inspection is supplier-scoped,
    cross-work-order. The switching engine (`services.qms.severity_switching`)
    owns transitions; the plan resolver reads ``severity`` here.
    """
    SEVERITY_CHOICES = [('NORMAL', 'Normal'), ('TIGHTENED', 'Tightened'), ('REDUCED', 'Reduced')]

    step = models.ForeignKey('Tracker.Steps', on_delete=models.CASCADE, related_name='severity_states')
    supplier = models.ForeignKey('Tracker.Companies', null=True, blank=True,
                                 on_delete=models.CASCADE, related_name='severity_states')
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='NORMAL')
    severity_since = models.DateTimeField(null=True, blank=True)  # when current severity was entered
    # Latched when tightened inspection persists N consecutive lots without earning
    # a return to normal: Z1.4 says stop accepting the supplier's product. Surfaced
    # as a recommendation (never an automatic ASL suspension).
    discontinued = models.BooleanField(default=False)

    # Incremental switching counters (updated per decided lot; reset on transition) —
    # deterministic, no reliance on timestamp ordering.
    recent_outcomes = models.JSONField(default=list, blank=True)   # last ≤5: 'A'|'R'|'G'
    consecutive_accepts = models.PositiveIntegerField(default=0)   # clean accepts in a row
    lots_in_regime = models.PositiveIntegerField(default=0)        # lots since the current severity began

    class Meta:
        verbose_name = 'Sampling Severity State'
        verbose_name_plural = 'Sampling Severity States'
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'step', 'supplier'],
                name='samplingseveritystate_tenant_uniq',
            ),
        ]
        indexes = [
            models.Index(fields=['step', 'supplier'], name='sevstate_step_sup_idx'),
        ]

    def __str__(self):
        who = self.supplier.name if self.supplier_id else "all suppliers"
        return f"{self.severity} @ {self.step} / {who}"


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
        """Thin wrapper — delegates to `services.mes.sampling.update_sampling_trigger_state`."""
        from Tracker.services.mes.sampling import update_sampling_trigger_state
        return update_sampling_trigger_state(self.part, self.status)


class StepGateFiring(SecureModel):
    """Record of a step quality gate firing — the idempotency marker (one fire
    per window) and the audit trail of an automatic quality decision: which
    metric crossed which threshold at what value, and which actions ran.

    Distinct from SamplingTriggerState: that is the runtime active-state for the
    TIGHTEN_SAMPLING action (which ruleset is in force, revert progress); this
    is the per-window firing ledger across all five actions.
    """
    ruleset = models.ForeignKey(SamplingRuleSet, on_delete=models.CASCADE, related_name='gate_firings')
    step = models.ForeignKey('Tracker.Steps', on_delete=models.CASCADE)
    work_order = models.ForeignKey('Tracker.WorkOrder', null=True, blank=True, on_delete=models.CASCADE)
    material_lot = models.ForeignKey('Tracker.MaterialLot', null=True, blank=True, on_delete=models.CASCADE)

    metric = models.CharField(max_length=20, choices=GateMetric.choices)
    metric_value = models.DecimalField(max_digits=10, decimal_places=3)
    threshold = models.DecimalField(max_digits=7, decimal_places=3, null=True, blank=True)
    actions_taken = models.JSONField(default=list, blank=True)

    triggered_by_report = models.ForeignKey(
        'Tracker.QualityReports', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    created_capa = models.ForeignKey(
        'Tracker.CAPA', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    approval_request = models.ForeignKey(
        'Tracker.ApprovalRequest', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    fired_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Step Gate Firing'
        verbose_name_plural = 'Step Gate Firings'
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'ruleset', 'work_order', 'step'],
                name='stepgatefiring_wo_uniq',
                condition=models.Q(work_order__isnull=False),
            ),
            models.UniqueConstraint(
                fields=['tenant', 'ruleset', 'material_lot', 'step'],
                name='stepgatefiring_lot_uniq',
                condition=models.Q(material_lot__isnull=False),
            ),
        ]

    def __str__(self):
        return f"Gate {self.ruleset.name} fired ({self.metric}={self.metric_value}) @ {self.step}"


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

class WorkCenterKind(models.TextChoices):
    """The surface a work-center serves. Primary discriminator between the
    operator queue, QA inbox, receiving inbox, and OSP dispatch. See
    Documents/WORK_CENTER_DESIGN.md."""
    PRODUCTION = "PRODUCTION", "Production"
    INSPECTION = "INSPECTION", "Inspection"
    RECEIVING = "RECEIVING", "Receiving"
    OSP = "OSP", "Outside Process"


class WorkCenter(SecureModel):
    """
    Grouping of equipment and/or workstations in a production area.

    Work centers are used for capacity planning, scheduling, and cost allocation.
    Additionally, `kind` is the primary discriminator that routes work to the
    right surface (operator / QA / receiving / OSP).
    """

    _is_versioned = True  # engineering judgment — routing master

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)  # Unique per tenant, not globally
    description = models.TextField(blank=True)
    # Surface discriminator — see Documents/WORK_CENTER_DESIGN.md.
    kind = models.CharField(
        max_length=20,
        choices=WorkCenterKind.choices,
        default=WorkCenterKind.PRODUCTION,
    )

    is_constraint = models.BooleanField(
        default=False,
        help_text="This work centre governs the plant's output — the bottleneck. Only "
                  "consulted when OptimizationConfig.release_policy is CONSTRAINT, "
                  "where order release is paced to these centres and the rest are "
                  "ignored. Declared by a planner rather than inferred: a resource "
                  "can look loaded for a month without being the real constraint, and "
                  "acting on a mis-identified one starves the shop.",
    )
    """Planner-declared bottleneck; paces order release under the CONSTRAINT policy."""

    is_critical = models.BooleanField(
        default=False,
        help_text="Watch this centre on the rough-cut capacity plan. RCCP is defined "
                  "as capacity planning over CRITICAL resources only — a plant with "
                  "forty work centres has maybe six whose load anyone can act on, and "
                  "showing all forty buries them. Presentation only: the flag filters "
                  "the heatmap, it never changes how load or capacity is computed, and "
                  "it is independent of `is_constraint`, which gates order release.",
    )
    """Planner-declared 'worth watching' — filters the RCCP heatmap, nothing else."""

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
                condition=models.Q(is_current_version=True),
                name='workcenter_tenant_code_uniq',
            ),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def create_new_version(self, *, user=None, change_description=None, **field_updates):
        """Thin wrapper — delegates to `services.mes.work_centers.
        create_new_work_center_version`, which carries the equipment M2M and
        repoints live references (steps, memberships, operational records) to
        the new current row."""
        from Tracker.services.mes.work_centers import create_new_work_center_version
        return create_new_work_center_version(
            self, user=user, change_description=change_description, **field_updates,
        )


class UserWorkCenterMembership(SecureModel):
    """Which work-centers a user is eligible to work at.

    ISA-95 PersonnelClass-style eligibility: a user CAN work at these
    stations; `is_primary` marks their preferred default. Session/kiosk
    presence layers on top later — this is membership, not presence.
    See Documents/WORK_CENTER_DESIGN.md.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='work_center_memberships',
    )
    work_center = models.ForeignKey(
        WorkCenter,
        on_delete=models.CASCADE,
        related_name='member_memberships',
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="The user's preferred default station (drives the operator home's initial scope).",
    )

    class Meta:
        verbose_name = 'Work Center Membership'
        verbose_name_plural = 'Work Center Memberships'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'work_center'],
                name='userworkcentermembership_user_wc_uniq',
            ),
        ]
        indexes = [
            models.Index(fields=['user', 'is_primary']),
            models.Index(fields=['work_center']),
        ]

    def __str__(self):
        return f"{self.user_id} @ {self.work_center_id}{' (primary)' if self.is_primary else ''}"


class Shift(SecureModel):
    """
    Defines a work shift (e.g., Day, Night, Weekend).

    Used for scheduling and labor tracking.
    """

    _is_versioned = True  # engineering judgment (DCAS labor audits)

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

    break_windows = models.JSONField(
        default=list, blank=True,
        help_text='Scheduled breaks/lunch within the shift, as a list of '
                  '{"start": "HH:MM", "end": "HH:MM"}. The scheduler keeps attended '
                  '(full-attention) work out of these windows; actual clock-out/in is '
                  'captured separately as TimeEntry BREAK/LUNCH entries.',
    )

    class Meta:
        verbose_name = 'Shift'
        verbose_name_plural = 'Shifts'
        ordering = ['start_time']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'code'],
                condition=models.Q(is_current_version=True),
                name='shift_tenant_code_uniq',
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.start_time} - {self.end_time})"

    def create_new_version(self, *, user=None, change_description=None, **field_updates):
        """Thin wrapper — delegates to `services.mes.shifts.create_new_shift_version`,
        which repoints live references (rostered users, overtime windows, machine
        operating_shifts) to the new current row."""
        from Tracker.services.mes.shifts import create_new_shift_version
        return create_new_shift_version(
            self, user=user, change_description=change_description, **field_updates,
        )


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
        ('SCHEDULED', 'Scheduled'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')

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
        ('PLANNED', 'Planned Maintenance'),
        ('UNPLANNED', 'Unplanned/Breakdown'),
        ('CHANGEOVER', 'Changeover/Setup'),
        ('CALIBRATION', 'Calibration'),
        ('NO_WORK', 'No Work Available'),
        ('NO_OPERATOR', 'No Operator Available'),
        ('MATERIAL', 'Waiting for Material'),
        ('QUALITY', 'Quality Issue'),
        ('OTHER', 'Other'),
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


class PlantCalendarException(SecureModel):
    """A tenant-wide non-working window — a holiday, plant shutdown, or inventory day.

    Unlike DowntimeEvent (which downs one machine), this closes the WHOLE plant for
    [start_time, end_time]: the scheduler blocks every machine and treats operators as
    absent. Recurring weekly hours live on Shift; this is for the one-off DATED closures
    the weekly day-of-week calendar can't express (so the solver stops booking work on
    Christmas / during the summer shutdown)."""
    KIND_CHOICES = [
        ('HOLIDAY', 'Holiday'),
        ('SHUTDOWN', 'Plant Shutdown'),
        ('INVENTORY', 'Inventory / Stock-take'),
        ('OTHER', 'Other'),
    ]
    RECURRENCE_CHOICES = [
        ('ONCE', 'One-off (dated)'),
        ('YEARLY', 'Repeats yearly'),
    ]
    name = models.CharField(max_length=100)
    kind = models.CharField(max_length=12, choices=KIND_CHOICES, default='HOLIDAY')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    recurrence = models.CharField(
        max_length=8, choices=RECURRENCE_CHOICES, default='ONCE',
        help_text="YEARLY repeats the closure's month/day span every year (fixed-date "
                  "holidays like Christmas); the stored year is just the first occurrence.")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Plant Calendar Exception'
        verbose_name_plural = 'Plant Calendar Exceptions'
        ordering = ['start_time']
        indexes = [models.Index(fields=['tenant', 'start_time'])]

    def __str__(self):
        return f"{self.name} ({self.kind}) {self.start_time:%Y-%m-%d}→{self.end_time:%Y-%m-%d}"


class LaborCalendarBlock(SecureModel):
    """Operator non-working time — PTO, sick, training, meetings, ad-hoc breaks —
    one-off or recurring weekly, for the whole company or one person.

    Unlike PlantCalendarException (which closes the WHOLE plant, blocking machines
    AND operators), this affects **operators only**: the scheduler drops the covered
    windows from the affected operators' on-shift time (see
    services.scheduling.data.get_operator_shift_windows), so Layer-1 pooled headcount
    and Layer-2 dispatch treat them as out — but a lights-out machine keeps running
    through, say, an all-hands. `user` null = the whole company; set = that person.

    `recurrence` picks which fields apply:
      - ONCE   → `start_time` / `end_time` (datetimes): a PTO day, a shutdown week.
      - WEEKLY → `days_of_week` + `window_start` / `window_end` (time-of-day): a
                 standing Monday all-hands, a daily stretch break.
    (Per-shift daily breaks/lunch already live on `Shift.break_windows`; this is for
    blocks that aren't tied to a single shift.)"""

    KIND_CHOICES = [
        ('PTO', 'PTO / vacation'),
        ('SICK', 'Sick'),
        ('TRAINING', 'Training'),
        ('MEETING', 'Meeting'),
        ('BREAK', 'Break'),
        ('OTHER', 'Other'),
    ]
    RECURRENCE_CHOICES = [
        ('ONCE', 'One-off (dated)'),
        ('WEEKLY', 'Weekly (recurring)'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='calendar_blocks',
        null=True, blank=True,
        help_text="The operator this block applies to. Null = the whole company "
                  "(every operator), e.g. an all-hands meeting.")
    kind = models.CharField(max_length=12, choices=KIND_CHOICES, default='OTHER')
    recurrence = models.CharField(max_length=8, choices=RECURRENCE_CHOICES, default='ONCE')

    # ONCE
    start_time = models.DateTimeField(
        null=True, blank=True, help_text="One-off start (recurrence=ONCE).")
    end_time = models.DateTimeField(
        null=True, blank=True, help_text="One-off end (recurrence=ONCE).")

    # WEEKLY
    days_of_week = models.CharField(
        max_length=20, blank=True, default='',
        help_text="Recurring days as comma-separated numbers (0=Monday..6=Sunday), "
                  "e.g. '0,2,4' (recurrence=WEEKLY).")
    window_start = models.TimeField(
        null=True, blank=True, help_text="Recurring start time-of-day (recurrence=WEEKLY).")
    window_end = models.TimeField(
        null=True, blank=True, help_text="Recurring end time-of-day (recurrence=WEEKLY).")

    reason = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Labor Calendar Block'
        verbose_name_plural = 'Labor Calendar Blocks'
        ordering = ['start_time']
        indexes = [
            models.Index(fields=['tenant', 'is_active']),
            models.Index(fields=['user', 'start_time']),
        ]

    def __str__(self):
        who = self.user_id or 'ALL'
        when = (f"{self.start_time:%Y-%m-%d}" if self.recurrence == 'ONCE' and self.start_time
                else f"weekly[{self.days_of_week}]")
        return f"{who} {self.kind} ({self.recurrence}) {when}"


class OvertimeWindow(SecureModel):
    """Additive shop-open time — an extra run of a SHIFT (overtime / weekend shift).

    The inverse of the other calendar entries: instead of removing availability, this
    GRANTS working time. It names a `shift`, so it inherits that shift's hours AND its
    crew: the scheduler adds the shift's window to the availability of operators
    rostered to that shift, and to every attended machine (the shop is running).
    Lights-out machines already run 24/7. Plant closures still win — overtime does not
    override a PlantCalendarException (don't mark a day a closure if you intend to run
    it). See services.scheduling.data.get_overtime_windows / get_overtime_machine_windows.

    `recurrence` picks which fields say WHEN to run the shift:
      - ONCE   → `start_date` / `end_date`: run it on each date in the range (this
                 Saturday, or a shutdown-recovery week).
      - WEEKLY → `days_of_week`: run it on those weekdays every week (a standing 2nd
                 shift on days the shift doesn't normally cover)."""

    RECURRENCE_CHOICES = [
        ('ONCE', 'One-off (dated)'),
        ('WEEKLY', 'Weekly (recurring)'),
    ]
    shift = models.ForeignKey(
        'Tracker.Shift', on_delete=models.CASCADE, related_name='overtime_windows',
        help_text="The shift being run as overtime — supplies the hours and the crew "
                  "(operators rostered to it).")
    recurrence = models.CharField(max_length=8, choices=RECURRENCE_CHOICES, default='ONCE')
    # ONCE — the extra day(s) to run the shift
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    # WEEKLY — extra weekdays to run the shift (0=Monday..6=Sunday)
    days_of_week = models.CharField(max_length=20, blank=True, default='')
    reason = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Overtime Window'
        verbose_name_plural = 'Overtime Windows'
        ordering = ['start_date']
        indexes = [models.Index(fields=['tenant', 'is_active'])]

    def __str__(self):
        when = (f"{self.start_date}" if self.recurrence == 'ONCE' and self.start_date
                else f"weekly[{self.days_of_week}]")
        return f"Overtime shift={self.shift_id} ({self.recurrence}) {when}"


# How a buyer buys an item, and so how a clerk counts it at the dock. STOCK = in the
# item's own stock unit (no conversion); BOX / LB convert to stock units through
# `units_per_purchase_unit` (pieces per box, pieces per pound).
PURCHASE_UNIT_CHOICES = [("STOCK", "Stock unit"), ("BOX", "Box"), ("LB", "Pound")]

# Where a lot came from — the first question of an AS9100 counterfeit-parts audit.
SOURCE_TYPE_CHOICES = [
    ("MANUFACTURER", "Manufacturer"),
    ("AUTHORIZED_DISTRIBUTOR", "Authorized distributor"),
    ("INDEPENDENT_DISTRIBUTOR", "Independent distributor"),
]


class Material(SecureModel):
    """A PURCHASED item — raw material or bought component (O-rings, seals, fasteners).

    Distinct from `PartTypes`, which is reserved for in-house SKUs / things produced
    in-house (holder bodies, etc.). BOM BUY lines reference a Material; received stock
    (`MaterialLot`) is stock of a Material. In-house MAKE components stay on PartTypes
    (they spawn child work orders). Purchase lead time lives here — it's a property of
    the bought item, not of a manufactured part type."""

    name = models.CharField(max_length=100)
    part_number = models.CharField(
        max_length=100, blank=True, help_text="Supplier or internal catalog number/SKU.")
    description = models.CharField(max_length=255, blank=True)
    unit_of_measure = models.CharField(max_length=20, default='EA')
    purchase_lead_time_days = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Days to source this item from a supplier — drives the order-by date in "
                  "the sourcing report (order-by = need-by − lead time).")
    preferred_supplier = models.ForeignKey(
        Companies, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='supplied_materials')
    safety_stock = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True,
        help_text="Buffer held back from planning. Coverage nets against on-hand MINUS "
                  "this, so the material lane warns while there is still stock to react "
                  "with instead of at the last unit. Does not block issuing — a picker "
                  "can always draw the physical stock.")
    is_active = models.BooleanField(default=True)
    # Supplier control for bulk stock. Part types qualify a supplier for that part; a
    # raw material qualifies by commodity ("elastomer seals", "4140 bar") — a
    # COMMODITY-scope SupplierQualification whose label matches.
    requires_supplier_qualification = models.BooleanField(
        default=False,
        help_text="Hold received lots from a supplier with no active qualification for "
                  "this material's commodity (or none at all, when no commodity is set).")
    commodity = models.CharField(
        max_length=100, blank=True,
        help_text="The commodity a supplier is qualified for when they supply this, e.g. "
                  "'Elastomer seals'. Matches a commodity-scope supplier qualification.")

    # Receiving controls — the same four on PartTypes.
    purchase_unit = models.CharField(
        max_length=10, choices=PURCHASE_UNIT_CHOICES, default="STOCK",
        help_text="How this item is bought and counted at receiving.")
    units_per_purchase_unit = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True,
        help_text="Stock units in one purchase unit — pieces per box, or pieces per pound. "
                  "Unused when the purchase unit is the stock unit.")
    requires_coc = models.BooleanField(
        default=False,
        help_text="Hold each received lot until its certificate of conformance is uploaded.")
    requires_heat_number = models.BooleanField(
        default=False,
        help_text="Hold each received lot until its heat / melt number is entered.")

    class Meta:
        verbose_name = 'Material'
        verbose_name_plural = 'Materials'
        ordering = ['name']
        indexes = [models.Index(fields=['tenant', 'is_active'])]

    def __str__(self):
        return self.name


# What sort of place a StorageLocation is. Module-level so the API names one enum for it.
STORAGE_LOCATION_KINDS = [
    ('WAREHOUSE', 'Warehouse'), ('AREA', 'Area'), ('RACK', 'Rack'), ('SHELF', 'Shelf'),
    ('BIN', 'Bin'), ('CAGE', 'Cage'), ('YARD', 'Yard'), ('DOCK', 'Dock'),
    ('CELL', 'Work cell'), ('LINE_SIDE', 'Line-side'), ('OTHER', 'Other'),
]


class StorageLocation(SecureModel):
    """A place things are kept: a warehouse, an area, a rack, a bin, a cage, the yard,
    a work cell. Lots, serialised units and machines point at one
    (`MaterialLot.location`, `Parts.location`, `Equipments.location`), so a location is a
    record, not a spelling — renaming it renames it everywhere.

    Locations nest (`parent`): Main Stores / Rack 3 / Bin B. The name is unique per
    tenant; `path` is the full trail for display. A `code` is what the label's barcode
    carries when set (`LOC:<code>`), shorter to scan than a name.

    Controls: `held_only` — only held or rejected stock may be put here (an MRB cage);
    `receiving_dock` — where receiving puts things away by default. Where things are is
    MOM data; which bin to put something in (directed putaway, slotting) is not modelled.
    """

    KIND_CHOICES = STORAGE_LOCATION_KINDS

    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    parent = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.PROTECT, related_name='children',
        help_text="The location this one is inside (a bin's rack, a rack's area).")
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default='OTHER')
    code = models.CharField(max_length=40, blank=True,
                            help_text="Short code for the label barcode. Optional; the name is used without one.")
    held_only = models.BooleanField(
        default=False, help_text="Only held or rejected stock may be put here (an MRB or quarantine cage).")
    receiving_dock = models.BooleanField(
        default=False, help_text="Where receiving puts deliveries by default.")

    class Meta:
        verbose_name = 'Storage Location'
        verbose_name_plural = 'Storage Locations'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'name'], name='storage_location_unique_per_tenant'),
            models.UniqueConstraint(
                fields=['tenant', 'code'], condition=~models.Q(code=''),
                name='storage_location_code_unique_per_tenant'),
        ]

    def __str__(self):
        return self.name

    @property
    def path(self) -> str:
        """Main Stores / Rack 3 / Bin B — walked up the parents (bounded, so bad data
        can't loop)."""
        names, node, seen = [], self, set()
        while node is not None and node.pk not in seen and len(names) < 12:
            seen.add(node.pk)
            names.append(node.name)
            node = node.parent
        return " / ".join(reversed(names))


class CycleCount(SecureModel):
    """One count of one location: what UQMES expected there, what the counter found,
    and — once applied — the corrections made (services/mes/cycle_count.py).

    Glovia is the stock register, so the discrepancy report goes there to be keyed; the
    count also brings UQMES's own lots back in line (recorded adjustments and moves), since
    nothing else re-aligns them. ``lines`` is the snapshot plus what was found — one row
    per lot or unit: ``{kind, id, label, item, unit, expected, counted, found_here,
    system_location, note}``. A JSON list rather than a table: a count is one document,
    read and written whole.
    """
    STATUS_CHOICES = [
        ('OPEN', 'Counting'),
        ('SUBMITTED', 'Submitted'),
        ('APPLIED', 'Applied'),
    ]

    count_number = models.CharField(max_length=40, blank=True)
    location = models.ForeignKey('StorageLocation', on_delete=models.PROTECT, related_name='cycle_counts')
    # The counter doesn't see expected quantities while counting — counts what's there
    # rather than confirming the number on the sheet.
    blind = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    lines = models.JSONField(default=list, blank=True)
    started_by = models.ForeignKey(
        'Tracker.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    submitted_by = models.ForeignKey(
        'Tracker.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    submitted_at = models.DateTimeField(null=True, blank=True)
    applied_by = models.ForeignKey(
        'Tracker.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Cycle Count'
        verbose_name_plural = 'Cycle Counts'
        ordering = ['-created_at']
        permissions = [
            ('apply_cyclecount', 'Can apply a submitted cycle count to stock'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'count_number'],
                condition=models.Q(count_number__isnull=False) & ~models.Q(count_number=''),
                name='cycle_count_tenant_number_uniq'),
        ]

    def save(self, *args, **kwargs):
        """Auto-fill count_number (CC-YYYY-####) on creation."""
        if not self.count_number:
            from django.utils import timezone
            from Tracker.utils.sequences import generate_next_sequence
            self.count_number = generate_next_sequence(
                queryset=type(self).objects, number_field='count_number',
                prefix=f"CC-{timezone.now().year}-", padding=4, tenant=self.tenant)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.count_number or 'CC'} · {self.location.name if self.location_id else ''}"


# A short delivery's outcome, from the packing slip (see MaterialLot.short_receipt).
# CLOSED is "nothing more expected" in UQMES's copy — it doesn't close the ERP's PO line.
SHORT_RECEIPT_CHOICES = [("BACKORDERED", "More coming"), ("CLOSED", "That's all")]


class MaterialLot(SecureModel):
    """
    Tracks a lot of material received from a supplier.

    Supports lot splitting via parent_lot relationship, enabling full material
    traceability from receipt through consumption.
    """

    # Physical inventory, NOT a controlled document — the cert of conformance is a
    # separate versioned Document and metadata corrections are captured by
    # auditlog. Versioning the lot forked its live balance across versions (the #1
    # bug in Documents/SCHEDULING_IMPLEMENTATION_PLAN.md), so it is deliberately
    # not versioned.
    _is_versioned = False

    # CoC, mill/material certs, packing slips, supplier docs attached at receipt.
    documents = GenericRelation('Tracker.Documents')
    # Calendar shelf-life record(s). Attached at receipt by
    # services.life_tracking.shelf_life.attach_shelf_life; the runtime authority
    # for expiry gating/status (the expiration_date scalar is just the input).
    life_tracking = GenericRelation('Tracker.LifeTracking')

    LOT_STATUS_CHOICES = [
        # Ordered but not yet delivered — an expected receipt, not physical stock.
        # Planning counts it as incoming supply (both the sourcing report and the RCCP
        # material lane derive "incoming" by excluding the on-hand and terminal statuses,
        # so this joins them with no change there). Consumption and staging use an
        # allowlist of ACCEPTED/IN_USE, so ON_ORDER stock can never be picked or issued.
        ('ON_ORDER', 'On Order'),
        ('RECEIVED', 'Received'),
        ('AWAITING_INSPECTION', 'Awaiting Inspection'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
        ('IN_USE', 'In Use'),
        ('CONSUMED', 'Consumed'),
        ('SCRAPPED', 'Scrapped'),
        ('QUARANTINE', 'Quarantine'),
        # Shipped back to the supplier on a return-to-supplier disposition. Not
        # scrapped — the goods exist, at the vendor — and not stock.
        ('RETURNED', 'Returned to supplier'),
        # An expected receipt that won't come: the ERP cancelled the line, or a sheet
        # typed before the ERP caught up expected a line already received. Never was
        # stock; no longer supply. (`cancel_expected_receipt`, reason on record.)
        ('CANCELLED', 'Cancelled'),
        # Sent to a customer on a CustomerShipment — their own property going back, or
        # our material sold or kitted. Gone; not stock, not supply.
        ('SHIPPED', 'Shipped to customer'),
    ]

    lot_number = models.CharField(max_length=100)  # Unique per tenant, not globally
    parent_lot = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='child_lots'
    )

    # What this lot is stock of. A received lot is either a buyable *part*
    # (`material_type` → PartTypes; make/buy is a sourcing attribute of the part) or a
    # raw *material* / consumable (`material` → Material). Exactly-one is enforced by a
    # check constraint; both may be null only for an ad-hoc lot described by
    # `material_description`. See item()/item_name() for the subject-agnostic accessors.
    material_type = models.ForeignKey(
        'Tracker.PartTypes',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='material_lots'
    )
    material = models.ForeignKey(
        'Tracker.Material',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='lots',
        help_text="The raw material / consumable this lot is stock of (mutually exclusive "
                  "with material_type, which is for buyable parts).",
    )
    material_description = models.CharField(
        max_length=200,
        blank=True,
        help_text="Free-text description for ad-hoc raw materials not in the Material list"
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
    # Hybrid-ERP reference: purchasing lives in the ERP; UQMES only references the PO.
    erp_po_number = models.CharField(
        max_length=100, blank=True,
        help_text="ERP purchase-order reference (UQMES does not own purchasing)."
    )
    # With the PO number, the key an expected-receipts import matches on — a PO with
    # several lines would otherwise re-import as duplicates.
    erp_po_line = models.CharField(
        max_length=20, blank=True,
        help_text="Line on the ERP purchase order."
    )
    promised_date = models.DateField(
        null=True, blank=True,
        help_text="Supplier's promised delivery date (from the PO); drives on-time-delivery scoring."
    )
    # The first promise. A re-promise moves `promised_date` (planning wants the latest
    # word); on-time delivery is judged against this, or a supplier who slipped twice
    # would still score "on time".
    original_promised_date = models.DateField(null=True, blank=True)
    # The buyer's last chase of a late delivery: what they were told, and when.
    chase_note = models.TextField(blank=True)
    chased_at = models.DateTimeField(null=True, blank=True)
    # A delivery short of what was on order: what had been ordered, and the clerk's call
    # from the packing slip. The ERP can't tell us, so closing short is never inferred.
    ordered_quantity = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True,
        help_text="What was on order, when the delivery was short of it.")
    short_receipt = models.CharField(
        max_length=12, blank=True, default="",
        choices=SHORT_RECEIPT_CHOICES,
        help_text="For a short delivery: the remainder stays on order (BACKORDERED) or the "
                  "order closed at what arrived (CLOSED).")

    # Null while the lot is ON_ORDER: nobody has received it, so there is no receipt date
    # and no receiver. Both are stamped by `receive_expected_lot` when it actually lands.
    received_date = models.DateField(null=True, blank=True)
    received_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='received_lots'
    )

    # Quantity tracking
    quantity = models.DecimalField(max_digits=12, decimal_places=4)
    quantity_remaining = models.DecimalField(max_digits=12, decimal_places=4)
    unit_of_measure = models.CharField(max_length=20)  # "EA", "KG", "M", etc.

    status = models.CharField(max_length=20, choices=LOT_STATUS_CHOICES, default='RECEIVED')
    hold_reason = models.CharField(
        max_length=40, blank=True,
        help_text="Why a lot is held/quarantined (e.g. SUPPLIER_UNQUALIFIED). "
                  "Lets the receiving queue explain a hold.")
    # Every hold on the lot at once — a lot can lack its CoC AND its heat number, and
    # come from an unqualified supplier. `hold_reason` is the first of these, kept for
    # every filter and badge that reads one. Written only by services/qms/lot_holds.py.
    hold_reasons = models.JSONField(default=list, blank=True)

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
    # Where the lot is — a StorageLocation, changed by a recorded move.
    location = models.ForeignKey(
        'StorageLocation', null=True, blank=True, on_delete=models.PROTECT, related_name='lots')

    # Traceability at receipt. The heat (melt) number ties a lot to the batch of metal it
    # was made from — how a recall finds everything poured from one bad melt.
    heat_number = models.CharField(
        max_length=64, blank=True, help_text="Heat / melt number from the mill certificate.")
    source_type = models.CharField(
        max_length=30, blank=True, choices=SOURCE_TYPE_CHOICES,
        help_text="Bought from the manufacturer, an authorized distributor, or an "
                  "independent one.")
    # Customer property (ISO 9001 §8.5.3): material a customer sent in for their own
    # job — a free-issue kit. It isn't ours: it skips the supplier gates and scorecards,
    # and only that customer's work may draw it or plan against it.
    owner = models.ForeignKey(
        Companies, on_delete=models.PROTECT, null=True, blank=True, related_name='owned_lots',
        help_text="The customer this stock belongs to, when it is theirs, not ours.")
    # The shipment this lot left on (services/mes/shipping.py). Null until it ships.
    customer_shipment = models.ForeignKey(
        'Tracker.CustomerShipment', on_delete=models.PROTECT, null=True, blank=True,
        related_name='material_lots')
    # A return to the supplier: their RMA / return authorisation, and — when they are
    # sending replacement goods — the expected lot that replaces this one points back here.
    rma_number = models.CharField(max_length=100, blank=True)
    replaces = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replacements',
        help_text="The returned lot this delivery replaces.")
    # What the clerk counted, in the unit they counted it in ("3 boxes"), beside the
    # stock quantity it converted to ("6,000"). Null when entered in the stock unit.
    received_as_quantity = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True)
    received_as_unit = models.CharField(max_length=10, blank=True, choices=PURCHASE_UNIT_CHOICES)

    # Set by `services.reman.core_lot.receive_core_lot` only: this lot is cores received
    # in bulk, units waiting to be given an identity — not stock of the part. The part
    # type alone cannot say so: a reman shop's core type is usually the very part number
    # it sells, so a bought lot of that part and a pallet of returned cores look alike.
    holds_cores = models.BooleanField(
        default=False,
        help_text="Cores received in bulk (units to be identified), not stock of the part.",
    )

    # Posted to the ERP: a person keyed this delivery's goods receipt into the ERP from
    # the receipts sheet (services.mes.receipt_export). UQMES exports the receipt and
    # records that it was posted; the posting itself is the ERP's. The snapshot is what
    # was posted (received / accepted / rejected), so a later change — a reject after
    # posting, a recount — shows as "changed since posted".
    erp_posted_at = models.DateTimeField(null=True, blank=True)
    erp_posted_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    erp_posted_snapshot = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = 'Material Lot'
        verbose_name_plural = 'Material Lots'
        ordering = ['-received_date']
        permissions = [
            # Rejecting a whole lot back to the vendor (a VDMR) rather than only the
            # pieces found bad. Granted to QA managers by default; a tenant may grant
            # it to inspectors. Without it, a whole-lot reject is held as a request.
            ('reject_whole_lot', 'Can reject a whole lot back to the vendor'),
        ]
        indexes = [
            models.Index(fields=['lot_number']),
            models.Index(fields=['supplier', 'received_date']),
            models.Index(fields=['status', 'expiration_date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'lot_number'],
                condition=models.Q(is_current_version=True),
                name='materiallot_tenant_lotnumber_uniq',
            ),
            # A lot is stock of a buyable part XOR a raw material (or neither, for an
            # ad-hoc lot named only by material_description) — never both.
            models.CheckConstraint(
                condition=~models.Q(material_type__isnull=False, material__isnull=False),
                name='materiallot_part_xor_material',
            ),
        ]

    @property
    def item(self):
        """The thing this lot is stock of — a buyable PartType or a raw Material
        (or None for an ad-hoc lot described only by material_description)."""
        return self.material_type or self.material

    @property
    def item_name(self):
        it = self.item
        return it.name if it is not None else (self.material_description or "")

    @property
    def storage_location(self) -> str:
        """The location's name ('' for none) — what lists and reports print."""
        return self.location.name if self.location_id else ""

    def __str__(self):
        return f"Lot {self.lot_number} - {self.item_name}"

    def split(self, quantity, reason=""):
        """Thin wrapper — delegates to `services.mes.material_lot.split_material_lot`."""
        from Tracker.services.mes.material_lot import split_material_lot
        return split_material_lot(self, quantity, reason=reason)


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
        # Update lot remaining quantity — on insert only. Use
        # `_state.adding`, NOT `not self.pk`. SecureModel assigns pk at
        # instantiation via uuid7, so `not self.pk` is always False.
        if self.lot and self._state.adding:
            # Shelf-life gate (backstop). No consumption endpoint exists yet, so
            # this chokepoint is the load-bearing guard; a future consume service
            # should call assert_lot_usable itself. Validation logic lives in the
            # service, not here.
            from Tracker.services.life_tracking.shelf_life import assert_lot_usable
            assert_lot_usable(self.lot)
            self.lot.quantity_remaining -= self.qty_consumed
            if self.lot.quantity_remaining <= 0:
                self.lot.status = 'CONSUMED'
            else:
                self.lot.status = 'IN_USE'
            self.lot.save()
        super().save(*args, **kwargs)


class MaterialStaging(SecureModel):
    """Whether a job's material has been put at its bench, per (work order, step).

    Deliberately NOT a flag on ScheduledTask: the solver replaces every task row on
    each solve, so staging state recorded there would vanish the next time a planner
    re-solved — losing exactly the work a handler had already done on the floor.
    (work_order, step) is the durable identity of "this job at this operation", and
    nothing else in the schema carries it, so it earns its own small table.

    `staged_at` null means not staged: the row is a toggle rather than an event log,
    so un-staging can't collide with the uniqueness constraint on re-staging.
    """

    work_order = models.ForeignKey(
        'Tracker.WorkOrder', on_delete=models.CASCADE, related_name='material_stagings')
    step = models.ForeignKey(
        'Tracker.Steps', on_delete=models.CASCADE, related_name='material_stagings')

    staged_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When the material was put at the bench. Null = not staged.")
    staged_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='material_stagings',
        help_text="Who staged it — the shift-handover question is 'who has this'.")
    note = models.TextField(
        blank=True, default='',
        help_text="Anything the next person needs: part-picked, substituted lot, "
                  "left on the blue cart.")

    class Meta:
        verbose_name = 'Material Staging'
        verbose_name_plural = 'Material Stagings'
        ordering = ['-staged_at']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'work_order', 'step'],
                name='unique_material_staging_per_job_step',
            )
        ]
        indexes = [models.Index(fields=['tenant', 'staged_at'])]

    def __str__(self):
        state = "staged" if self.staged_at else "not staged"
        return f"{self.work_order} @ {self.step} ({state})"


class MaterialStagingLine(SecureModel):
    """One material on a staging record: how much is needed, how much was pulled, and
    WHICH LOTS actually went in the tote.

    Together with `MaterialStaging` this is the materials requisition the shop
    documentation calls for — the header says which job and operation, the lines say
    what and how much. (The header keeps its historical name; renaming the pair is a
    separate pass.)

    Two problems it exists to solve, both of which show up as wrong numbers elsewhere:

    1. **Nothing reserved stock.** `plan_draw` is computed fresh every time it's asked,
       so two pick sheets printed the same morning name the same lot, and a shortage
       count treats material already sitting on a cart as still available. A line with
       `qty_picked` and no `issued_at` IS the reservation — stock that physically left
       the shelf but hasn't been consumed yet.

    2. **Planned lot ≠ actual lot.** The sheets print the lots FEFO *will* draw, and the
       picker regularly takes a different one — the named lot is empty, short, or
       someone got there first. `picked_lots` records what was really taken, and
       consumption then reads it instead of re-deriving FEFO. Without that, the
       traceability record asserts what the plan intended rather than what happened,
       which is precisely the claim an AS9100 audit tests.
    """

    staging = models.ForeignKey(
        MaterialStaging, on_delete=models.CASCADE, related_name='lines')

    # What is being kitted. Mirrors `MaterialLot`: a line is for a raw *material* /
    # consumable (`material`) or a buyable *part* (`material_type`), never both.
    #
    # It was Material-only, which meant a BUY line pointing at a purchased part could
    # be procured, received and held as stock — `MaterialLot.material_type` has always
    # supported that — but never kitted to a bench. The Material Requisition printed
    # "purchased part — not kitted here" on those rows, which was the system stating
    # its own gap on a shop-floor document. `services.mes.bom.buy_line_item` already
    # normalises both kinds behind one key; this is the row that could not hold them.
    material = models.ForeignKey(
        'Tracker.Material', null=True, blank=True,
        on_delete=models.PROTECT, related_name='staging_lines',
        help_text="Raw material / consumable being kitted (mutually exclusive with "
                  "material_type, which is for buyable parts).")
    material_type = models.ForeignKey(
        'Tracker.PartTypes', null=True, blank=True,
        on_delete=models.PROTECT, related_name='staging_lines',
        help_text="Buyable part being kitted (mutually exclusive with material).")

    qty_required = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    qty_picked = models.DecimalField(
        max_digits=12, decimal_places=4, default=0,
        help_text="What was physically pulled. Reserves stock until issued.")

    # [{lot_id, lot_number, qty}] — what was ACTUALLY taken, in the picker's own words.
    # A list because one line can legitimately draw from several lots. JSON rather than
    # a child table: `MaterialUsage` remains the authoritative consumption record with
    # real FKs, and this is the pick-time note that feeds it.
    picked_lots = models.JSONField(default=list, blank=True)

    issued_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When consumption drew this line down. Null = picked but not yet "
                  "consumed, i.e. still reserved against on-hand.")
    picked_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='staging_lines_picked')

    class Meta:
        verbose_name = 'Material Staging Line'
        verbose_name_plural = 'Material Staging Lines'
        # Materials first, then parts; each alphabetical. A single `material__name`
        # ordering put every part row in one undifferentiated NULL block.
        ordering = ['material__name', 'material_type__name']
        constraints = [
            # Two PARTIAL constraints rather than one over both columns. Postgres treats
            # NULLs as distinct, so the original `(tenant, staging, material)` constraint
            # stopped preventing anything the moment `material` became nullable — every
            # part row has material=NULL and would collide with nothing, including
            # itself. Each kind now gets a constraint scoped to the rows it applies to.
            models.UniqueConstraint(
                fields=['tenant', 'staging', 'material'],
                condition=models.Q(material__isnull=False),
                name='unique_staging_line_per_material',
            ),
            models.UniqueConstraint(
                fields=['tenant', 'staging', 'material_type'],
                condition=models.Q(material_type__isnull=False),
                name='unique_staging_line_per_part',
            ),
            # A line kits a raw material XOR a buyable part. Unlike MaterialLot there is
            # no ad-hoc third case: a staging line exists because a BOM line asked for
            # something, so it always has a subject.
            models.CheckConstraint(
                condition=(
                    models.Q(material__isnull=False, material_type__isnull=True)
                    | models.Q(material__isnull=True, material_type__isnull=False)
                ),
                name='stagingline_material_xor_part',
            ),
        ]
        indexes = [models.Index(fields=['tenant', 'issued_at'])]

    def __str__(self):
        return f"{self.item_name} x{self.qty_picked or self.qty_required}"

    @property
    def item(self):
        """The Material or PartTypes this line kits — whichever it holds."""
        return self.material or self.material_type

    @property
    def item_name(self) -> str:
        item = self.item
        return getattr(item, 'name', '') or str(item or '')

    @property
    def item_key(self) -> tuple:
        """`('MATERIAL'|'PART_TYPE', id)` — the same key `services.mes.bom.BuyItem`
        uses, so a staging line and the BOM line that produced it identify the same
        subject. A Material and a PartTypes can share a uuid space, so the kind is
        part of the identity, not decoration."""
        if self.material_id is not None:
            return ('MATERIAL', self.material_id)
        return ('PART_TYPE', self.material_type_id)

    @property
    def is_reserved(self) -> bool:
        """Pulled from the shelf, not yet consumed — invisible to on-hand without this."""
        return self.issued_at is None and (self.qty_picked or 0) > 0


class TimeEntry(SecureModel):
    """
    Labor time tracking - single flexible table with entry_type.

    Supports production time, setup/changeover, rework, downtime, and indirect labor.
    """
    ENTRY_TYPE_CHOICES = [
        ('PRODUCTION', 'Production'),
        ('SETUP', 'Setup/Changeover'),
        ('REWORK', 'Rework'),
        ('DOWNTIME', 'Downtime'),
        ('INDIRECT', 'Indirect Labor'),
        ('SHIFT', 'On Shift'),
        ('BREAK', 'Break'),
        ('LUNCH', 'Lunch'),
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

    _is_versioned = True  # ISO 9001 4.4, MIL-STD-31000

    BOM_TYPE_CHOICES = [
        ('ASSEMBLY', 'Assembly'),
        ('DISASSEMBLY', 'Disassembly'),
    ]

    BOM_STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('RELEASED', 'Released'),
        ('OBSOLETE', 'Obsolete'),
    ]

    part_type = models.ForeignKey(
        'Tracker.PartTypes',
        on_delete=models.PROTECT,
        related_name='boms'
    )
    revision = models.CharField(max_length=10)
    bom_type = models.CharField(max_length=20, choices=BOM_TYPE_CHOICES, default='ASSEMBLY')
    status = models.CharField(max_length=20, choices=BOM_STATUS_CHOICES, default='DRAFT')

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
            # Partial: only enforced for current versions so historical
            # versions can coexist with the same natural key. (Migration 0024
            # introduced this; 0028 inadvertently reverted to unconditional;
            # this restores it.)
            models.UniqueConstraint(
                fields=['tenant', 'part_type', 'revision', 'bom_type'],
                condition=models.Q(is_current_version=True),
                name='bom_tenant_parttype_rev_type_uniq',
            ),
        ]

    def __str__(self):
        return f"BOM {self.part_type.name} Rev {self.revision}"

    def create_new_version(self, *, user=None, change_description=None, **field_updates):
        """Thin wrapper — delegates to `services.mes.bom.create_new_bom_version`."""
        from Tracker.services.mes.bom import create_new_bom_version
        return create_new_bom_version(self, user=user, change_description=change_description, **field_updates)


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
    # Exactly one of component_type / material is set (see the Meta constraint), and
    # `source` says what we do about it — the two are independent:
    #
    #   component_type + MAKE  → build it here; spawns a pegged child work order.
    #   component_type + BUY   → buy the part (requires PartTypes.can_buy). Procured,
    #                            never spawns a WO — but it IS a PartType, so it carries
    #                            the receiving-inspection plan, supplier qualification,
    #                            part approval and life limits that Material has none of.
    #   material      + BUY    → buy the raw material / consumable.
    #   material      + MAKE   → meaningless; a Material is never produced here.
    #
    # `services.mes.bom.buy_line_item` is the one place that resolves what a BUY line
    # points at; go through it rather than testing `material_id` directly, or bought
    # parts silently drop out of sourcing and the material gate.
    component_type = models.ForeignKey(
        'Tracker.PartTypes',
        null=True, blank=True,
        on_delete=models.PROTECT,
        related_name='used_in_boms',
        help_text="A part (not a raw material). With source=MAKE it spawns a child work "
                  "order; with source=BUY it is purchased instead, which requires the "
                  "part type's can_buy flag. Mutually exclusive with `material`.",
    )
    material = models.ForeignKey(
        'Tracker.Material',
        null=True, blank=True,
        on_delete=models.PROTECT,
        related_name='used_in_boms',
        help_text="Purchased raw material / consumable (source=BUY) — something never "
                  "produced in-house. Mutually exclusive with `component_type`.",
    )

    quantity = models.DecimalField(max_digits=10, decimal_places=4)
    unit_of_measure = models.CharField(max_length=20, default='EA')

    source = models.CharField(
        max_length=4,
        choices=[('MAKE', 'Made in-house'), ('BUY', 'Purchased')],
        default='BUY',
        help_text="Make-vs-buy: MAKE spawns an in-house child WO the parent assembly "
                  "pegs to (WorkOrder.pegged_to_bom_line); BUY is procured. Plan #9.",
    )

    consumed_at_step = models.ForeignKey(
        'Tracker.Steps',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='bom_lines_consumed_here',
        help_text="The parent-process step that consumes this component (the assembly "
                  "step). When set, the scheduler gates only that step on the component "
                  "WO's completion; when null, the whole parent waits. Plan #9.",
    )

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
        null=True, blank=True,
        help_text="Per-use OVERRIDE of the component type's `can_recover`. Leave blank "
                  "to follow the item master, which is the right answer almost always. "
                  "Set False for the exception: a safety-critical position or a customer "
                  "contract that forbids reuse even of a normally recoverable item.",
    )

    # Substitutes (comma-separated PartType IDs or linked via separate model)
    notes = models.TextField(blank=True)

    # Line ordering
    line_number = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'BOM Line'
        verbose_name_plural = 'BOM Lines'
        ordering = ['bom', 'line_number']
        constraints = [
            models.CheckConstraint(
                name='bomline_exactly_one_component',
                check=(
                    models.Q(component_type__isnull=False, material__isnull=True)
                    | models.Q(component_type__isnull=True, material__isnull=False)
                ),
            ),
        ]

    @property
    def component_label(self) -> str:
        """Human name of the component, whichever kind it is (Material or PartType)."""
        if self.material_id:
            return self.material.name
        if self.component_type_id:
            return self.component_type.name
        return "component"

    def __str__(self):
        return f"{self.bom} Line {self.line_number}: {self.component_label} x{self.quantity}"

    def save(self, *args, **kwargs):
        # Auto-fill a gap-numbered line_number (10, 20, 30…) for new lines that don't
        # specify one, so the BOM keeps a stable, insertable ordering. Explicit values
        # (seeds, version copies) are preserved. Sequence-number auto-fill only — no
        # business logic here.
        if self._state.adding and not self.line_number and self.bom_id:
            last = (
                # tenant-safe: scoped to a single BOM, which belongs to one tenant.
                BOMLine.unscoped.filter(bom_id=self.bom_id)
                .order_by('-line_number')
                .values_list('line_number', flat=True).first()
            )
            self.line_number = (last or 0) + 10
        super().save(*args, **kwargs)


class AssemblyUsage(SecureModel):
    """
    Tracks actual parts assembled into a parent assembly - instance-level tracking.

    While BOM defines what SHOULD go into an assembly (design),
    AssemblyUsage tracks what ACTUALLY went into a specific assembly instance.

    Also supports removal tracking for remanufacturing/repair scenarios.
    """
    # One parent, two possible children. The parent is always a part — a reman core is a
    # part too (Documents/CORE_AS_PART_DESIGN.md; this reverses the earlier
    # "mirror-not-abstract" decision, which kept a separate `assembly_core` parent).
    # The child is a stock part, or a HarvestedComponent that never became stock — a
    # repair-and-return unit's own parts going back in, which are the customer's.
    assembly = models.ForeignKey(
        'Tracker.Parts',
        null=True, blank=True,
        on_delete=models.PROTECT,
        related_name='component_usages',
        help_text="The parent this component was installed into — for a core rebuild, the "
                  "core's part."
    )
    component = models.ForeignKey(
        'Tracker.Parts',
        null=True, blank=True,
        on_delete=models.PROTECT,
        related_name='installed_in',
        help_text="The component part installed. Null when the thing installed is a "
                  "harvested component that never became stock."
    )
    component_harvested = models.ForeignKey(
        'Tracker.HarvestedComponent',
        null=True, blank=True,
        on_delete=models.PROTECT,
        related_name='installed_in',
        help_text="The harvested component installed — the customer's own part going "
                  "back into their own unit, which never became a Parts row."
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
        constraints = [
            # A parent always, and exactly one child: a stock part, or a harvested
            # component going back into the unit it came from.
            models.CheckConstraint(
                condition=models.Q(assembly__isnull=False),
                name='assemblyusage_has_parent',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(component__isnull=False, component_harvested__isnull=True)
                    | models.Q(component__isnull=True, component_harvested__isnull=False)
                ),
                name='assemblyusage_one_component',
            ),
        ]
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
        """Thin wrapper — delegates to `services.mes.assembly_usage.remove_assembly_usage`."""
        from Tracker.services.mes.assembly_usage import remove_assembly_usage
        return remove_assembly_usage(self, user, reason=reason)
