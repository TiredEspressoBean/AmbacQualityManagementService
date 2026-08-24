"""
Scheduling models (OR-Tools CP-SAT foundation) — Phase 0.

New models the solver reads from and writes to. No solver code lives here; these
are pure data + small timing accessors. See
`Documents/SCHEDULING_IMPLEMENTATION_PLAN.md` (Phase 0) and
`Documents/OR_TOOLS_INTEGRATION.md`.

Design notes:
- All tenant-scoped models inherit `SecureModel` (tenant isolation + soft delete).
  None are versioned — these are operational/config records, not controlled docs.
- Timing is stored decomposed (setup / cycle / load-unload / external-setup) rather
  than a single `expected_duration`, so the solver can reason about transfer
  batches, SMED overlap, and multi-machine tending. `StepTiming` carries the
  accessors ported from the scheduling playground's `OperationTiming`.
- `ScheduledTask` is the single authoritative **Layer-1** (machine) solver schedule
  (see plan #3); operator dispatch (Layer 2) is a separate concern.
"""
from __future__ import annotations

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from .core import SecureModel


class AttentionType(models.TextChoices):
    FULL = 'full', 'Full attention (operator tied to the machine)'
    LOAD_UNLOAD = 'load_unload', 'Load/unload only (machine runs unattended between)'


class LaborModel(models.TextChoices):
    """How the Layer-1 solver constrains the operators a step needs (the dual-resource
    labor model, selectable per step — see PlanetTogether's Named/Shared/Pool split):
    - OFF: no crew constraint — the step runs machine-only, dispatch is advisory;
    - POOL: cap concurrent attended work at the qualified crew on shift (cheap,
      approximate — a multi-skilled operator counts in every pool);
    - NAMED: assign a SPECIFIC operator inside the solve (exact — use for a specialist
      bottleneck like one certified assembler; costs solve time, so reserve it)."""
    OFF = 'off', 'Off (no crew constraint)'
    POOL = 'pool', 'Pool (cap at qualified crew)'
    NAMED = 'named', 'Named (assign a specific operator)'


class StepTiming(SecureModel):
    """Decomposed time elements for a step, replacing a single `expected_duration`.

    All minute fields are per the OR-Tools timing model. `cycle_time_minutes` is a
    deterministic per-piece machine cycle (for CNC, from the program — not a
    historical average); the duration-fallback chain uses it before
    `StepExecution` history and `Steps.expected_duration`.
    """

    step = models.OneToOneField(
        'Tracker.Steps', on_delete=models.CASCADE, related_name='timing',
        help_text="The step these timings describe.",
    )
    setup_minutes = models.FloatField(
        default=0, validators=[MinValueValidator(0)],
        help_text="Internal (machine-stopped) setup / changeover minutes.",
    )
    cycle_time_minutes = models.FloatField(
        default=0, validators=[MinValueValidator(0)],
        help_text="Deterministic per-piece machine cycle time (minutes).",
    )
    load_unload_per_piece = models.FloatField(
        default=0, validators=[MinValueValidator(0)],
        help_text="Operator touch time to load/unload one piece (minutes).",
    )
    attention_type = models.CharField(
        max_length=12, choices=AttentionType.choices, default=AttentionType.FULL,
        help_text="Whether the operator is tied to the machine (full) or only "
                  "loads/unloads (enables multi-machine tending in Layer 2).",
    )
    external_setup_minutes = models.FloatField(
        default=0, validators=[MinValueValidator(0)],
        help_text="SMED external setup that can overlap the previous op's run time.",
    )

    class Meta:
        verbose_name = 'Step Timing'
        verbose_name_plural = 'Step Timings'

    def __str__(self):
        return f"Timing for {self.step} (cycle {self.cycle_time_minutes}m)"

    def machine_wall_time(self, quantity: int) -> float:
        """Minutes the machine is occupied for a batch: internal setup + run."""
        return self.setup_minutes + self.cycle_time_minutes * max(0, quantity)

    def first_piece_done(self) -> float:
        """Minutes until the first piece is complete (enables transfer batches —
        the next op can start before the full batch finishes)."""
        return self.setup_minutes + self.cycle_time_minutes + self.load_unload_per_piece

    def operator_attended_time(self, quantity: int) -> float:
        """Minutes of operator attention a batch needs. Full-attention ties the
        operator to the whole machine run; load/unload only needs setup plus a
        touch per piece (the rest runs unattended)."""
        quantity = max(0, quantity)
        if self.attention_type == AttentionType.FULL:
            return self.machine_wall_time(quantity)
        return self.setup_minutes + self.load_unload_per_piece * quantity


class StepEquipmentAffinity(SecureModel):
    """Which machines can run a step, and how well. Drives eligibility + preference
    in the solver's machine-assignment decision."""

    class Affinity(models.TextChoices):
        ELIGIBLE = 'eligible', 'Eligible'
        PREFERRED = 'preferred', 'Preferred'
        DIALED_IN = 'dialed_in', 'Dialed in (proven best)'

    step = models.ForeignKey(
        'Tracker.Steps', on_delete=models.CASCADE, related_name='equipment_affinities',
    )
    equipment = models.ForeignKey(
        'Tracker.Equipments', on_delete=models.CASCADE, related_name='step_affinities',
    )
    affinity = models.CharField(
        max_length=10, choices=Affinity.choices, default=Affinity.ELIGIBLE,
    )
    cycle_time_override = models.FloatField(
        null=True, blank=True, validators=[MinValueValidator(0)],
        help_text="Per-piece cycle on THIS machine, overriding StepTiming (a faster "
                  "or slower machine for the same step).",
    )

    class Meta:
        verbose_name = 'Step-Equipment Affinity'
        verbose_name_plural = 'Step-Equipment Affinities'
        constraints = [
            models.UniqueConstraint(
                fields=['step', 'equipment'], name='step_equipment_affinity_uniq',
            ),
        ]
        indexes = [models.Index(fields=['equipment', 'affinity'])]

    def __str__(self):
        return f"{self.step} @ {self.equipment} ({self.affinity})"


class WorkCenterChangeover(SecureModel):
    """Sequence-dependent setup: minutes to reconfigure `equipment` when switching
    from running `from_step` to `to_step`. Feeds the solver's changeover matrix."""

    equipment = models.ForeignKey(
        'Tracker.Equipments', on_delete=models.CASCADE, related_name='changeovers',
    )
    from_step = models.ForeignKey(
        'Tracker.Steps', on_delete=models.CASCADE, related_name='changeovers_from',
    )
    to_step = models.ForeignKey(
        'Tracker.Steps', on_delete=models.CASCADE, related_name='changeovers_to',
    )
    changeover_minutes = models.FloatField(
        default=0, validators=[MinValueValidator(0)],
    )

    class Meta:
        verbose_name = 'Work-Center Changeover'
        verbose_name_plural = 'Work-Center Changeovers'
        constraints = [
            models.UniqueConstraint(
                fields=['equipment', 'from_step', 'to_step'],
                name='workcenter_changeover_uniq',
            ),
        ]

    def __str__(self):
        return f"{self.equipment}: {self.from_step} → {self.to_step} ({self.changeover_minutes}m)"


class Fixture(SecureModel):
    """A shared piece of tooling with limited quantity — a cumulative (capacity)
    resource: at most `quantity` steps using it can run at once."""

    name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(
        default=1, help_text="How many of this fixture exist (concurrency limit).",
    )
    steps = models.ManyToManyField(
        'Tracker.Steps', related_name='fixtures', blank=True,
        help_text="Steps that require this fixture.",
    )

    class Meta:
        verbose_name = 'Fixture'
        verbose_name_plural = 'Fixtures'

    def __str__(self):
        return f"{self.name} (x{self.quantity})"


class OptimizationConfig(SecureModel):
    """Per-tenant solver knobs: cost rates, lateness penalties, time-fence zone
    widths, PFD allowance, and the CP-SAT gap limit. One row per tenant."""

    shop_rate_per_hour = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('75.00'),
        help_text="Labor + overhead cost per shop hour (objective input).",
    )
    overtime_multiplier = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal('1.50'),
    )
    late_penalty_urgent = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1000.00'))
    late_penalty_high = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('500.00'))
    late_penalty_normal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('100.00'))
    late_penalty_low = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('25.00'))
    frozen_zone_days = models.PositiveIntegerField(
        default=2, help_text="Days from now within which tasks are pinned (frozen).",
    )
    slushy_zone_days = models.PositiveIntegerField(
        default=7, help_text="Days after the frozen zone where moves are discouraged.",
    )
    pfd_allowance_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('15.00'),
        help_text="Personal/fatigue/delay allowance added to attended time (%).",
    )
    relative_gap_limit = models.FloatField(
        default=0.02, validators=[MinValueValidator(0)],
        help_text="CP-SAT relative optimality gap to stop at (e.g. 0.02 = 2%).",
    )
    staging_buffer_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Minutes between a component WO finishing and its parent assembly "
                  "WO being allowed to start (move/stage time). Assembly-convergence "
                  "peg — plan #9.",
    )
    job_change_minutes = models.PositiveIntegerField(
        default=10,
        help_text="Setup minutes charged when a resource switches to a different work "
                  "order on the SAME operation — keeps a job's parts batched together. "
                  "Kept below operation-change setups by design: staying on the same "
                  "operation matters more than staying on the same work order.",
    )
    default_labor_model = models.CharField(
        max_length=10, choices=LaborModel.choices, default=LaborModel.POOL,
        help_text="The labor model applied to steps that don't set their own "
                  "(`Steps.labor_model`): POOL caps attended work at the qualified crew "
                  "on shift; OFF drops the crew constraint; NAMED assigns a specific "
                  "operator in the solve (reserve for specialist bottlenecks).",
    )
    match_operators = models.BooleanField(
        default=False,
        help_text="Two-phase solve: first schedule machines (fast, pooled labor), then "
                  "re-solve assigning a SPECIFIC operator to every attended op, warm-"
                  "started from the machine plan. Guarantees a real operator↔operation "
                  "matching (scarce skills push work late, never silently uncovered) at "
                  "the cost of a longer solve. Off = single fast machine solve.",
    )
    default_lockstep_batch = models.BooleanField(
        default=True,
        help_text="Default lot-cohesion intent for work orders that don't set their own "
                  "(`WorkOrder.lockstep_batch`). NOTE: currently informational only — the "
                  "solver always schedules co-located cohort parts as one cohesive lot and "
                  "carves a rework straggler into its own lot so the cohort keeps "
                  "progressing (it does NOT hold the WO); ON and OFF behave identically "
                  "today. The OFF meaning (allow a large lot to break into transfer batches "
                  "to pipeline) is reserved for the future transfer-batching work.",
    )

    class Meta:
        verbose_name = 'Optimization Config'
        verbose_name_plural = 'Optimization Configs'
        constraints = [
            models.UniqueConstraint(fields=['tenant'], name='optimization_config_one_per_tenant'),
        ]

    def __str__(self):
        return f"Optimization config (${self.shop_rate_per_hour}/hr)"


class SolverStatus(models.TextChoices):
    OPTIMAL = 'OPTIMAL', 'Optimal'
    FEASIBLE = 'FEASIBLE', 'Feasible'
    INFEASIBLE = 'INFEASIBLE', 'Infeasible'
    MODEL_INVALID = 'MODEL_INVALID', 'Model invalid'
    UNKNOWN = 'UNKNOWN', 'Unknown'


class ScheduleResult(SecureModel):
    """One run of the solver over a horizon. Holds the solve metadata; the tasks
    hang off it. `is_active` marks the schedule currently in force; `is_stale`
    marks one superseded by new demand/actuals."""

    horizon_start = models.DateTimeField()
    horizon_end = models.DateTimeField()
    solver_status = models.CharField(
        max_length=15, choices=SolverStatus.choices, default=SolverStatus.UNKNOWN,
    )
    solve_time_ms = models.PositiveIntegerField(default=0)
    objective_value_cents = models.BigIntegerField(
        default=0,
        help_text="Raw CP-SAT objective (lateness + makespan + pin-stickiness "
                  "penalties). NOT money despite the legacy 'cents' name — the pin "
                  "weights dominate it. Kept for solve-to-solve comparison; surface "
                  "weighted_lateness to planners instead.",
    )
    weighted_lateness = models.BigIntegerField(
        default=0,
        help_text="Priority-weighted lateness only (Σ part late-minutes × the WO's "
                  "priority penalty) — the objective's lateness term, isolated from "
                  "makespan and pin penalties. The 'how late, weighted by priority' "
                  "signal shown in the UI.",
    )
    relaxed_pin_count = models.PositiveIntegerField(
        default=0,
        help_text="Frozen/planner-pinned tasks the solver had to move because the "
                  "world changed under them (machine down, shift edited). >0 means the "
                  "freeze couldn't be fully honored — surface for the planner.",
    )
    is_stale = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=False, db_index=True)
    is_draft = models.BooleanField(
        default=False, db_index=True,
        help_text="A proposed 'what-if' schedule the planner reviews against the live "
                  "one and then commits or discards. A draft never supersedes the active "
                  "schedule until committed; committing promotes it to is_active.",
    )

    class Meta:
        verbose_name = 'Schedule Result'
        verbose_name_plural = 'Schedule Results'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', 'is_stale']),
            models.Index(fields=['is_draft']),
        ]

    def __str__(self):
        return f"Schedule {self.created_at:%Y-%m-%d %H:%M} ({self.solver_status})"


class FenceZone(models.TextChoices):
    FROZEN = 'frozen', 'Frozen'
    SLUSHY = 'slushy', 'Slushy'
    LIQUID = 'liquid', 'Liquid'


class ScheduledTask(SecureModel):
    """A single solver-assigned operation: one part+step on one machine in a time
    window. The authoritative Layer-1 (machine) schedule (plan #3)."""

    schedule = models.ForeignKey(
        ScheduleResult, on_delete=models.CASCADE, related_name='tasks',
    )
    part = models.ForeignKey(
        'Tracker.Parts', null=True, blank=True, on_delete=models.CASCADE,
        related_name='scheduled_tasks',
    )
    core = models.ForeignKey(
        'Tracker.Core', null=True, blank=True, on_delete=models.CASCADE,
        related_name='scheduled_tasks',
        help_text="Reman core being torn down (mutually exclusive with `part`).",
    )
    step = models.ForeignKey(
        'Tracker.Steps', on_delete=models.PROTECT, related_name='scheduled_tasks',
    )
    machine = models.ForeignKey(
        'Tracker.Equipments', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='scheduled_tasks',
        help_text="Assigned machine (null if the step needs none).",
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_pinned = models.BooleanField(
        default=False, help_text="Planner-pinned: the solver must keep this fixed.",
    )
    fence_zone = models.CharField(
        max_length=6, choices=FenceZone.choices, default=FenceZone.LIQUID,
    )
    # Layer 2 (operator dispatch): filled by `dispatch_operators`, not Layer 1.
    requires_operator = models.BooleanField(
        default=True,
        help_text="Whether this task needs an operator (false for unattended runs).",
    )
    assigned_operator = models.ForeignKey(
        'Tracker.User', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='dispatched_tasks',
        help_text="Layer-2 operator assignment; null on an attended task means "
                  "the dispatcher could not cover it (no qualified operator free).",
    )

    class Meta:
        verbose_name = 'Scheduled Task'
        verbose_name_plural = 'Scheduled Tasks'
        ordering = ['start_time']
        indexes = [
            models.Index(fields=['schedule', 'start_time']),
            models.Index(fields=['machine', 'start_time']),
            models.Index(fields=['part', 'step']),
            models.Index(fields=['core', 'step']),
            models.Index(fields=['assigned_operator', 'start_time']),
        ]
        constraints = [
            models.CheckConstraint(
                name='scheduledtask_part_xor_core',
                check=(models.Q(part__isnull=False, core__isnull=True)
                       | models.Q(part__isnull=True, core__isnull=False)),
            ),
        ]

    def __str__(self):
        unit = self.part or self.core
        return f"{unit} · {self.step} @ {self.machine} [{self.start_time:%m-%d %H:%M}]"


class ContinuousMachine(SecureModel):
    """A continuous-feed machine (e.g. bar-fed screw machine, extruder) modeled by
    throughput rather than per-piece cycle, with periodic bar-change interruptions."""

    equipment = models.OneToOneField(
        'Tracker.Equipments', on_delete=models.CASCADE, related_name='continuous_profile',
    )
    parts_per_hour = models.FloatField(
        default=0, validators=[MinValueValidator(0)],
    )
    bar_change_interval_hours = models.FloatField(
        null=True, blank=True, validators=[MinValueValidator(0)],
        help_text="Hours of run between bar changes (null = no bar changes).",
    )
    bar_change_duration_minutes = models.FloatField(
        default=0, validators=[MinValueValidator(0)],
    )

    class Meta:
        verbose_name = 'Continuous Machine'
        verbose_name_plural = 'Continuous Machines'

    def __str__(self):
        return f"{self.equipment} ({self.parts_per_hour}/hr)"
