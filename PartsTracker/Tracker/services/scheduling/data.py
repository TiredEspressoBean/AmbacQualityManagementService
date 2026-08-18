"""
Scheduling data layer (Phase 1).

Pure Django ORM → solver-ready **frozen dataclasses**. No OR-Tools imports here;
the solver (Phase 2) consumes these DTOs. Every function takes `tenant` and uses
tenant-scoped `.objects`.

See `Documents/SCHEDULING_IMPLEMENTATION_PLAN.md` (Phase 1) and
`Documents/OR_TOOLS_INTEGRATION.md` (Data Layer).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F
from django.utils import timezone


# --- DTOs -------------------------------------------------------------------

@dataclass(frozen=True)
class TimingData:
    """Resolved time elements for a step. `cycle_time_minutes` comes from the
    fallback chain; `cycle_source` records which rung supplied it."""
    step_id: UUID
    cycle_time_minutes: float
    setup_minutes: float
    load_unload_per_piece: float
    external_setup_minutes: float
    attention_type: str
    cycle_source: str  # 'timing' | 'history' | 'expected' | 'none'


@dataclass(frozen=True)
class AffinityData:
    equipment_id: UUID
    affinity: str  # 'eligible' | 'preferred' | 'dialed_in'
    cycle_time_override: float | None


@dataclass(frozen=True)
class FixtureData:
    fixture_id: UUID
    quantity: int
    step_ids: frozenset


@dataclass(frozen=True)
class HorizonData:
    start: datetime
    end: datetime
    frozen_end: datetime
    slushy_end: datetime


# --- Timings (with the duration fallback chain) -----------------------------

def get_step_timings(tenant, min_samples: int = 20) -> dict[UUID, TimingData]:
    """Per current step: `StepTiming.cycle_time_minutes` → `StepExecution`
    historical average (≥ `min_samples` completed visits) → `Steps.expected_duration`.
    Setup / load-unload / external / attention come from `StepTiming` when present,
    else default to 0 / FULL."""
    from Tracker.models import StepExecution, Steps, StepTiming
    from Tracker.models.scheduling import AttentionType

    timings = {t.step_id: t for t in StepTiming.objects.filter(tenant=tenant)}

    dur = ExpressionWrapper(F('exited_at') - F('entered_at'), output_field=DurationField())
    hist = {
        row['step']: row
        for row in StepExecution.objects
        .filter(tenant=tenant, exited_at__isnull=False)
        .values('step').annotate(avg=Avg(dur), n=Count('id'))
    }

    def _historical(step_id):
        h = hist.get(step_id)
        if h and h['n'] >= min_samples and h['avg'] is not None:
            return h['avg'].total_seconds() / 60.0
        return None

    result: dict[UUID, TimingData] = {}
    for step in Steps.objects.filter(tenant=tenant, is_current_version=True):
        t = timings.get(step.id)
        if t and t.cycle_time_minutes:
            cycle, source = t.cycle_time_minutes, 'timing'
        else:
            hist_cycle = _historical(step.id)
            if hist_cycle is not None:
                cycle, source = hist_cycle, 'history'
            elif step.expected_duration:
                cycle, source = step.expected_duration.total_seconds() / 60.0, 'expected'
            else:
                cycle, source = 0.0, 'none'
        result[step.id] = TimingData(
            step_id=step.id,
            cycle_time_minutes=cycle,
            setup_minutes=t.setup_minutes if t else 0.0,
            load_unload_per_piece=t.load_unload_per_piece if t else 0.0,
            external_setup_minutes=t.external_setup_minutes if t else 0.0,
            attention_type=t.attention_type if t else AttentionType.FULL,
            cycle_source=source,
        )
    return result


# --- Machine eligibility / setup / fixtures ---------------------------------

def get_step_equipment_affinities(tenant) -> dict[UUID, list[AffinityData]]:
    """Which machines can run each step, and how well. `step_id → [AffinityData]`."""
    from Tracker.models import StepEquipmentAffinity

    result: dict[UUID, list[AffinityData]] = {}
    for a in StepEquipmentAffinity.objects.filter(tenant=tenant):
        result.setdefault(a.step_id, []).append(AffinityData(
            equipment_id=a.equipment_id,
            affinity=a.affinity,
            cycle_time_override=a.cycle_time_override,
        ))
    return result


def get_changeover_matrix(tenant) -> dict[tuple, float]:
    """Sequence-dependent setup: `(equipment_id, from_step_id, to_step_id) → minutes`."""
    from Tracker.models import WorkCenterChangeover

    return {
        (c.equipment_id, c.from_step_id, c.to_step_id): c.changeover_minutes
        for c in WorkCenterChangeover.objects.filter(tenant=tenant)
    }


def get_fixture_availability(tenant) -> dict[UUID, FixtureData]:
    """Shared tooling with limited quantity: `fixture_id → FixtureData`."""
    from Tracker.models import Fixture

    result: dict[UUID, FixtureData] = {}
    for f in Fixture.objects.filter(tenant=tenant).prefetch_related('steps'):
        result[f.id] = FixtureData(
            fixture_id=f.id,
            quantity=f.quantity,
            step_ids=frozenset(s.id for s in f.steps.all()),
        )
    return result


# --- Horizon ----------------------------------------------------------------

def get_schedule_horizon(tenant, horizon_days: int = 30) -> HorizonData:
    """The planning window and time-fence boundaries. Frozen/slushy widths come
    from `OptimizationConfig` (defaults 2 / 7 days); the slushy zone follows the
    frozen zone."""
    from Tracker.models import OptimizationConfig

    cfg = OptimizationConfig.objects.filter(tenant=tenant).first()
    frozen_days = cfg.frozen_zone_days if cfg else 2
    slushy_days = cfg.slushy_zone_days if cfg else 7

    start = timezone.now()
    return HorizonData(
        start=start,
        end=start + timedelta(days=horizon_days),
        frozen_end=start + timedelta(days=frozen_days),
        slushy_end=start + timedelta(days=frozen_days + slushy_days),
    )
