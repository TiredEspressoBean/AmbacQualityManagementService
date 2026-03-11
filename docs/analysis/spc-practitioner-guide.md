# SPC Practitioner Guide

This guide provides decision-making workflows for acting on SPC data. It's intended for QA Managers, Quality Engineers, and Production Managers who need to investigate signals, trigger corrective actions, and manage process baselines.

!!! tip "Prerequisites"
    - Complete [SPC Fundamentals Training](../training/spc-fundamentals.md) first
    - Understand [SPC Charts](spc.md) technical reference

## Application Pages Reference

SPC data connects to several pages in uqmes:

| Page | Route | Purpose |
|------|-------|---------|
| **Analysis Dashboard** | `/analysis` | KPI overview: FPY trends, needs attention, defect pareto |
| **SPC Charts** | `/spc` | Control charts, capability indices, baseline management |
| **SPC Print View** | `/spc/print` | Print-optimized SPC reports |
| **Quality Dashboard** | `/quality` | Quality metrics, open NCRs, CAPA status |
| **Defect Analysis** | `/quality/defects` | Defect trends by type, supplier, part type |
| **CAPA List** | `/quality/capas` | Active CAPAs, some triggered by SPC |
| **Heat Map** | `/heatmap` | Visual defect location analysis |
| **Calibrations** | `/quality/calibrations` | Equipment calibration status (affects measurement validity) |

### Navigation Path

```
Tools (sidebar)
    ├── Documents (/documents)
    ├── Analytics (/analysis)
    │       └── Links to: SPC, Defects, Process Flow
    └── AI Chat (/ai-chat)

    From Analytics page:
        └── SPC (/spc)
                └── Process → Step → Measurement selection

Quality (sidebar)
    ├── Dashboard (/quality)
    ├── CAPAs (/quality/capas)
    ├── Quality Reports (/editor/qualityReports)
    ├── Training (/quality/training)
    ├── Calibrations (/quality/calibrations)
    └── Heat Map (/heatmap)
```

---

## 1. Signal Investigation Workflow

When an out-of-control signal appears, follow this systematic investigation.

### 1.1 Investigation Decision Tree

```
Signal Detected (red point on chart)
        │
        ▼
┌───────────────────┐
│ Is it Rule 1?     │──Yes──▶ STOP PRODUCTION if critical measurement
│ (beyond 3σ)       │         Investigate immediately
└───────────────────┘
        │ No
        ▼
┌───────────────────┐
│ Pattern signal?   │──Yes──▶ Continue production with monitoring
│ (Rules 2-6)       │         Investigate within same shift
└───────────────────┘
        │
        ▼
    Document and
    begin investigation
```

### 1.2 Investigation Checklist

When a signal appears, systematically check these factors:

| Factor | Questions to Ask | How to Check |
|--------|------------------|--------------|
| **Material** | New lot? Different supplier? | Check lot numbers in part history |
| **Machine** | Different equipment? Calibration due? | Check equipment assignment, calibration status |
| **Method** | Process change? New work instruction? | Check document versions, process revision |
| **Measurement** | Different gauge? Different operator measuring? | Check measurement records, equipment used |
| **Man** | New operator? Different shift? | Check StepTransitionLog for operator |
| **Environment** | Temperature change? Humidity? | Check environmental logs if available |

!!! example "Demo: Flow Rate Investigation"
    In demo mode, the Flow Rate Rule 2 violation can be traced to:

    1. Navigate to **Tools > Analytics**, then select **SPC** (or go directly to `/spc`)
    2. Select: Process = Common Rail Injector Remanufacturing, Step = Flow Testing, Measurement = Flow Rate @ 1000 bar
    3. Click on the red-flagged points to see timestamps
    4. Cross-reference with parts INJ-0042-017 and INJ-0042-019 (search in `/tracker`)
    5. Check part history for common factors (equipment, operator, material lot)

    The demo data shows these parts share a common material lot from Delphi Fuel Systems.

    **Connected pages:**

    - `/quality/defects` - Shows nozzle defects trending up
    - `/quality/capas` - Shows CAPA-2024-003 triggered by this pattern

### 1.3 Investigation Documentation

Record findings in a structured format:

```
SIGNAL: Rule 2 violation - Flow Rate @ 1000 bar
DATE DETECTED: 2024-01-15
PARTS AFFECTED: INJ-0042-017, INJ-0042-019

INVESTIGATION:
☑ Material: Lot DFS-2024-0088 (Delphi) - DIFFERENT from prior lots
☐ Machine: Flow Test Stand #1 - same as prior
☐ Method: WI-001-A Rev 3 - no changes
☐ Measurement: Same gauge, same calibration
☐ Man: Sarah Chen - experienced operator
☐ Environment: No noted changes

ROOT CAUSE: Suspect material lot variation from supplier

ACTION: Initiate CAPA, tighten incoming inspection for Delphi
```

---

## 2. CAPA Triggering Criteria

Not every signal requires a CAPA. Use these decision rules.

### 2.1 When to Trigger CAPA

| Condition | CAPA Required? | Rationale |
|-----------|----------------|-----------|
| Single Rule 1 violation (beyond 3σ) | **Maybe** | Investigate first; CAPA if assignable cause found |
| 2+ Rule 1 violations in 30 days | **Yes** | Pattern indicates systemic issue |
| Any pattern signal (Rules 2-6) | **Yes** | Patterns always indicate assignable cause |
| Cpk drops below 1.0 | **Yes** | Process not capable of meeting spec |
| Cpk drops below 1.33 | **Maybe** | Monitor closely; CAPA if trend continues |
| Same signal on multiple measurements | **Yes** | Indicates broader process issue |

### 2.2 CAPA Decision Matrix

```
                        │ Single Occurrence │ Recurring (2+ in 30 days)
────────────────────────┼───────────────────┼─────────────────────────
Critical Measurement    │ Investigate +     │ CAPA Required
(safety, regulatory)    │ Likely CAPA       │ Escalate to Management
────────────────────────┼───────────────────┼─────────────────────────
Major Measurement       │ Investigate       │ CAPA Required
(functional impact)     │ Document findings │
────────────────────────┼───────────────────┼─────────────────────────
Minor Measurement       │ Document only     │ Investigate
(cosmetic, non-critical)│                   │ CAPA if pattern persists
```

### 2.3 Linking SPC Evidence to CAPA

When creating a CAPA from SPC data, include:

1. **Control chart screenshot** showing the violation
2. **Affected parts list** with serial numbers
3. **Timeline** of when signals first appeared
4. **Investigation findings** from 6M analysis
5. **Cpk trend** if capability is declining

!!! example "Demo: CAPA-2024-003 SPC Connection"
    CAPA-2024-003 (nozzle defect investigation) was triggered by:

    - Flow Rate showing Rule 2 violation (2 of 3 points beyond 2σ)
    - 5 of 12 parts (42%) from ORD-2024-0038 requiring rework
    - Cpk dropped from 1.45 to 1.28 over 2 weeks

    The 5-Whys traced root cause to supplier material lot variation.

    **View in app:**

    - CAPA detail: `/quality/capas` → click CAPA-2024-003
    - Related SPC data: `/spc` → Flow Testing → Flow Rate
    - Affected order: `/tracker` → search ORD-2024-0038

---

## 3. Baseline Management

SPC baselines define "normal" process behavior. Managing them correctly is critical.

### 3.1 When to Freeze a Baseline

Freeze control limits when ALL of these are true:

| Criterion | Requirement | How to Verify |
|-----------|-------------|---------------|
| **Stability** | No out-of-control signals for 25+ subgroups | Review chart for 25 consecutive green points |
| **Capability** | Cpk ≥ 1.33 | Check capability summary on SPC page |
| **Data volume** | Minimum 100 individual measurements | Check sample count |
| **Time span** | Data spans at least 20 production days | Check date range |
| **Representative** | Includes normal variation (shifts, operators, lots) | Verify data covers typical conditions |

### 3.2 Baseline Freeze Procedure

1. **Verify stability**: Confirm no signals in recent data
2. **Document current state**: Screenshot chart and capability indices
3. **Get approval**: QA Manager sign-off required
4. **Freeze in system**: Click **Freeze Limits** on SPC page
5. **Record justification**: System requires reason for freezing
6. **Communicate**: Notify production that baseline is locked

### 3.3 When to Update a Baseline

Update (unfreeze and refreeze) when:

| Situation | Action | Approval |
|-----------|--------|----------|
| Process improvement confirmed | Update to reflect new capability | QA Manager |
| Equipment replaced/upgraded | Update after requalification | QA Manager + Engineering |
| Baseline too tight (false alarms) | Investigate first; update if justified | QA Manager |
| Baseline too loose (missing issues) | Tighten; may need process improvement | QA Manager |

### 3.4 Baseline Update Procedure

1. **Justify the change**: Document why update is needed
2. **Collect new data**: Minimum 25 subgroups under new conditions
3. **Verify improvement**: New Cpk should be better (or justify why acceptable)
4. **Approve change**: QA Manager + Engineering sign-off
5. **Update in system**: Click **Update Baseline**, enter justification
6. **Retain history**: Old baseline is archived automatically

```
BASELINE UPDATE JUSTIFICATION TEMPLATE:

Measurement: Flow Rate @ 1000 bar
Previous Baseline: μ=120.5, σ=4.2, Cpk=1.32
New Baseline: μ=120.2, σ=3.1, Cpk=1.58

Reason for Update:
- CAPA-2024-003 implemented new incoming inspection procedure
- Supplier quality improved after corrective action
- 45 days of stable data collected post-improvement
- New capability exceeds 1.33 threshold

Approved by: Maria Santos (QA Manager)
Date: 2024-03-01
```

---

## 4. Measurement Prioritization

You can't monitor everything with equal intensity. Prioritize based on risk.

### 4.1 Risk-Based Priority Matrix

| Priority | Criteria | Monitoring Frequency | Example |
|----------|----------|---------------------|---------|
| **Critical** | Safety-related, regulatory requirement, or customer-specified CTQ | Daily review | Flow Rate (affects engine performance) |
| **High** | Functional impact, high scrap cost if out of spec | Weekly review | Spray Angle, Response Time |
| **Medium** | Quality impact but recoverable (rework possible) | Bi-weekly review | Torque values, dimensional checks |
| **Low** | Cosmetic or non-critical | Monthly review | Surface finish scores |

### 4.2 Prioritization Checklist

Score each measurement (1-5 scale):

| Factor | Weight | Score | Weighted |
|--------|--------|-------|----------|
| Safety impact | 5 | ___ | ___ |
| Regulatory requirement | 4 | ___ | ___ |
| Customer complaint history | 4 | ___ | ___ |
| Scrap/rework cost | 3 | ___ | ___ |
| Detection difficulty downstream | 3 | ___ | ___ |
| Historical instability | 2 | ___ | ___ |
| **Total** | | | ___ |

**Priority assignment:**
- Score > 50: Critical
- Score 35-50: High
- Score 20-35: Medium
- Score < 20: Low

### 4.3 Demo: Prioritized Measurements

In the demo Common Rail Injector process:

| Measurement | Step | Priority | Rationale |
|-------------|------|----------|-----------|
| Flow Rate @ 1000 bar | Flow Testing | **Critical** | Affects engine performance, customer CTQ |
| Spray Angle | Flow Testing | **High** | Functional impact on combustion |
| Return Flow Rate | Flow Testing | **High** | Indicates internal leakage |
| Body Torque | Assembly | **Medium** | Reworkable if out of spec |
| Cleaning Time | Cleaning | **Low** | Process parameter, not product spec |

---

## 5. SPC and Disposition Integration

When SPC signals occur, consider the impact on in-process and completed parts.

### 5.1 Disposition Decision Flow

```
Out-of-Control Signal Detected
            │
            ▼
┌─────────────────────────────┐
│ Identify affected time      │
│ period (when did it start?) │
└─────────────────────────────┘
            │
            ▼
┌─────────────────────────────┐
│ Query parts produced during │
│ out-of-control period       │
└─────────────────────────────┘
            │
            ▼
    ┌───────┴───────┐
    │               │
    ▼               ▼
Parts still    Parts already
in process     shipped/completed
    │               │
    ▼               ▼
Quarantine     Risk assessment
and review     (notify customer?)
```

### 5.2 Parts Affected by SPC Signals

When a signal indicates process shift:

| Part Status | Action | Responsibility |
|-------------|--------|----------------|
| **In process (before final inspection)** | Hold and re-inspect | QA Inspector |
| **In process (past inspection)** | Quarantine, review data | QA Manager |
| **Completed, not shipped** | Review measurements, disposition | QA Manager |
| **Shipped** | Risk assessment, customer notification if warranted | QA Manager + Sales |

### 5.3 Querying Affected Parts

To find parts produced during an out-of-control period:

1. Note the **timestamp range** of suspect measurements from SPC chart (`/spc`)
2. Navigate to `/tracker` or **Portal > Tracker**
3. Use filters:
   - Step = the affected step
   - Date range within suspect period
   - Equipment (if equipment-specific issue)
4. Alternatively, use `/quality/defects` to see defect patterns by time period
5. Export list for review

**API approach:**
```
GET /api/parts/?step={step_id}&created_at__gte={start}&created_at__lte={end}
```

### 5.4 Disposition Considerations

| SPC Finding | Disposition Guidance |
|-------------|---------------------|
| Single point beyond limits | Re-inspect affected part; if passes, USE AS IS |
| Pattern signal (trend, run) | Quarantine batch, 100% inspection of suspect period |
| Cpk dropped below 1.0 | All parts need re-inspection; likely REWORK or SCRAP |
| Equipment-related signal | Inspect all parts from that equipment during period |

!!! warning "Document the Connection"
    When dispositioning parts due to SPC signals, link the disposition to the SPC investigation. This creates traceability for audits.

---

## 6. Reporting and Communication

### 6.1 SPC Review Meeting Agenda

Weekly SPC review (recommended for QA Manager):

1. **Dashboard review** (5 min)
   - Any new out-of-control signals?
   - Cpk trends across critical measurements

2. **Open investigations** (10 min)
   - Status of active signal investigations
   - Root causes identified

3. **CAPA connections** (5 min)
   - CAPAs triggered by SPC data
   - Effectiveness verification using SPC

4. **Baseline management** (5 min)
   - Any baselines needing update?
   - Process improvements ready to capture?

5. **Action items** (5 min)
   - Assign investigation owners
   - Set follow-up dates

### 6.2 Management Reporting

Monthly SPC summary for leadership:

| Metric | This Month | Last Month | Trend |
|--------|------------|------------|-------|
| Measurements monitored | 12 | 12 | — |
| Measurements with Cpk ≥ 1.33 | 10 (83%) | 9 (75%) | ↑ |
| Out-of-control signals | 3 | 7 | ↓ |
| CAPAs triggered by SPC | 1 | 2 | ↓ |
| Baselines updated | 2 | 0 | — |

### 6.3 Escalation Matrix

| Situation | Escalate To | Timeframe |
|-----------|-------------|-----------|
| Critical measurement out of control | Production Manager + QA Manager | Immediately |
| Cpk drops below 1.0 | QA Manager + Engineering | Same day |
| Pattern signal on any measurement | QA Manager | Same shift |
| Recurring signals (3+ in 30 days) | QA Manager + initiate CAPA | Within 24 hours |
| Customer-reported field issue matches SPC trend | Management + Sales | Immediately |

---

## 7. Quick Reference

### Signal Response Summary

| Signal Type | Severity | Production | Investigation | CAPA? |
|-------------|----------|------------|---------------|-------|
| Rule 1 (beyond 3σ) | High | Stop if critical | Immediate | If cause found |
| Rule 2 (2 of 3 beyond 2σ) | Medium | Monitor | Same shift | If recurring |
| Rule 3 (4 of 5 beyond 1σ) | Medium | Monitor | Same shift | If recurring |
| Rule 4 (8 same side) | Medium | Continue | Within 24h | Yes |
| Rule 5 (6 trending) | Medium | Continue | Within 24h | Yes |
| Rule 6 (14 alternating) | Low | Continue | Within week | If persists |

### Cpk Action Thresholds

| Cpk Range | Status | Action Required |
|-----------|--------|-----------------|
| ≥ 1.67 | Excellent | Maintain; consider reducing inspection |
| 1.33 - 1.67 | Capable | Monitor; standard inspection |
| 1.0 - 1.33 | Marginal | Improvement plan within 30 days |
| < 1.0 | Not capable | Immediate action; 100% inspection |

### Baseline Rules of Thumb

- **Freeze after**: 25+ stable subgroups, Cpk ≥ 1.33, 100+ measurements
- **Update when**: Confirmed improvement, equipment change, or justified recalculation
- **Never**: Update baseline to hide a problem or reduce false alarms without investigation

---

## Related Documentation

| Document | App Page | Route |
|----------|----------|-------|
| [SPC Charts](spc.md) | SPC Charts | `/spc` |
| [SPC Fundamentals Training](../training/spc-fundamentals.md) | — | — |
| [Dashboard Overview](dashboard.md) | Analysis Dashboard | `/analysis` |
| [Defect Analysis](defects.md) | Defect Analysis | `/quality/defects` |
| [CAPA Overview](../workflows/capa/overview.md) | CAPA List | `/quality/capas` |
| [Dispositions](../workflows/quality/dispositions.md) | Dispositions | `/dispositions` |
| [Quality Reports](../workflows/quality/quality-reports.md) | Quality Reports | `/qualityReports` |
| [Heat Maps](../3d-models/heatmap-viz.md) | Heat Map Viewer | `/heatmap` |
| [Calibrations](../admin/setup/equipment.md) | Calibration Dashboard | `/quality/calibrations` |
