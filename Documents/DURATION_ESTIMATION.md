# Duration Estimation: Learning Scheduler

**Status:** Planned
**Estimated effort:** ~325 LOC, 2-3 weeks
**Depends on:** CP-SAT scheduler (Premium tier)

## Overview

Replace manually-entered step durations with statistically-computed estimates derived from actual production data. The system observes real execution times and builds factor-based models that feed the CP-SAT scheduler. Accuracy improves automatically over time.

## Data Sources (already collected)

- `StepExecution` — started_at, completed_at per step/part/operator/equipment
- `TimeEntry` — entry_type (PRODUCTION/SETUP/REWORK), duration per step/WO
- `StepTransitionLog` — timestamps of parts moving between steps
- `DowntimeEvent` — categorized downtime per machine

## Architecture

### Models (~60 LOC)

```
DurationEstimate     — base run/setup time per part_type + step + machine, with P50/P80/P95
MachineFactor        — speed multiplier per machine vs fleet average
OperatorFactor       — speed multiplier per operator vs team average
ChangeoverTime       — avg changeover between part types on a machine
TransportTime        — avg transit time between work centers
```

### Estimation Service (~150 LOC)

```
estimate_duration(step, machine, operator, part_type, quantity, confidence=0.5)

= base_time[part_type][step]
  × machine_factor[machine]
  × operator_factor[operator]
  × batch_factor(quantity)
  + setup_time[part_type][machine]
  + changeover_time[prev_part_type][curr_part_type][machine]
```

Confidence parameter selects percentile:
- P50 (0.5) for normal scheduling
- P80 (0.8) for customer promise dates
- P95 (0.95) for rush jobs / worst-case

### Factor Refresh (~60 LOC)

Celery beat task runs nightly:
- Recompute base times per part_type/step
- Recompute machine and operator factors
- Recompute changeover matrix
- Recompute transport times between work centers

### API Endpoint (~30 LOC)

```
GET /api/duration-estimate/?step=X&machine=Y&operator=Z&part_type=W&qty=100
```

Returns estimated duration with confidence interval and sample count.

### Scheduler Integration (~5 LOC)

Replace `step.expected_duration` with `DurationEstimate.get_estimate(...)` in the CP-SAT model builder.

## Levels of Sophistication

| Level | Approach | Effort | Accuracy |
|-------|----------|--------|----------|
| 1 | Simple averages | Days | Good for stable processes |
| 2 | Percentile-based (P50/P80/P95) + setup/run separation | 1 week | Good for quoting + scheduling |
| **3** | **Factor-based (machine × operator × batch × changeover)** | **2-3 weeks** | **Covers 95% of value** |
| 4 | Bayesian updating (handles cold start gracefully) | 3-4 weeks | Better for new machines/operators |
| 5 | ML-based prediction | 4-6 weeks | Marginal improvement over L3 for most shops |

Recommend implementing Level 3. Level 4 adds cold-start handling but Level 3 can fall back to manual estimates when sample count is low.

## Cold Start Strategy

- No history for a step/machine combo → use manual `expected_duration` from Step model
- < 5 samples → use fleet average for that step across all machines
- 5-20 samples → use machine-specific average
- 20+ samples → use full factor model

## Competitive Positioning

No MES or APS competitor learns durations from production data. ProShop, PlanetTogether, Siemens Opcenter, and TrakSYS all require manually-entered times. A self-improving scheduler that gets more accurate with use is a generation ahead.

Combined with the user-configurable solver and CP-SAT optimization, this creates a scheduling engine that:
1. Learns its own parameters from production data
2. Optimizes using mathematical programming (not heuristics)
3. Lets users define their own objectives and constraints