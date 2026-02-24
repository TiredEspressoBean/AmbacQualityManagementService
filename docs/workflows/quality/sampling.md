# Sampling Rules

Sampling allows inspecting a subset of parts rather than 100%, based on statistical rules. This guide covers sampling configuration and use.

## What is Sampling?

**Sampling** inspects representative parts from a batch:

- Reduces inspection time and cost
- Statistically valid quality assessment
- Adjusts based on quality history

## Sampling Methods

### 100% Inspection
Every part inspected. Used for:

- Critical dimensions
- Safety-related features
- New suppliers/processes
- Poor quality history

### Every Nth Part
Inspect at regular intervals:

- Consistent coverage across lot
- Example: Every 5th part = 20% sampling

### First/Last N Parts
Setup and end-of-run verification:

- **First N**: Verify setup is correct
- **Last N**: Verify process stability at end

### Percentage Sampling
Sample based on lot size:

- Scales with production quantity
- Example: 10% of lot size

### Pure Random
Hash-based random selection:

- Unbiased sample
- Audit-compliant algorithm
- SHA-256 hash modulo arithmetic

## How Sampling Works

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│   Lot    │────▶│ Sampling │────▶│  Inspect │────▶│  Accept/ │
│  Arrives │     │   Rule   │     │  Sample  │     │  Reject  │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                      │
                      ▼
              ┌──────────────┐
              │ Sample Size  │
              │ Determined   │
              └──────────────┘
```

1. Parts arrive at inspection step
2. System checks applicable sampling rule
3. Calculates sample size
4. Inspector inspects sample
5. System determines accept/reject based on results

## Sampling Rules Configuration

Sampling rules are configured by administrators:

### Rule Components

| Component | Description |
|-----------|-------------|
| **Rule Type** | Every Nth, Percentage, Random, First N, Last N, Exact Count |
| **Ruleset** | Part type + Process + Step combination |
| **Value** | The N value (interval, percentage, count) |
| **Order** | Priority when multiple rules apply |
| **Fallback Ruleset** | Tighter sampling triggered after consecutive failures |

### Rule Types

| Type | Description |
|------|-------------|
| **Every Nth Part** | Inspect at regular intervals (e.g., every 5th part) |
| **Percentage** | Inspect a percentage of the lot |
| **Pure Random** | SHA-256 hash-based random selection for unbiased sampling |
| **First N Parts** | Inspect first N parts (setup verification) |
| **Last N Parts** | Inspect last N parts (end-of-run check) |
| **Exact Count** | Always inspect exactly N parts (no variance) |

## Viewing Sampling Requirements

When parts arrive at an inspection step:

1. System shows sampling requirements
2. Indicates sample size
3. Lists which parts to inspect
4. May randomly select sample parts

## Recording Sampling Results

1. Inspect the sampled parts
2. Record measurements/results for each
3. System calculates pass/fail
4. If sample passes → lot accepted
5. If sample fails → lot rejected (or tightened inspection)

## Sample Selection

### Random Selection
System randomly selects parts from the lot:

- Ensures unbiased sample
- Parts are flagged for inspection
- Remaining parts are not inspected

### Stratified Sampling
Sample from different production periods:

- First, middle, last of run
- Different cavities/machines
- Different operators

## Accept/Reject Decisions

Based on quality report results:

- **Pass**: Sampled parts pass quality check → lot continues
- **Fail**: Sampled part fails → quality report created, lot may be held

### Quality Report Integration

When a sampled part fails:
1. Quality report is created automatically
2. Part may be quarantined
3. Disposition workflow triggers
4. Remaining lot may need 100% inspection

## Lot Accept/Reject

### Accept
- Lot passes
- All parts in lot cleared
- Continue production

### Reject
Options:
- 100% inspection of lot
- Return entire lot
- Scrap entire lot
- Sort and disposition

## Sampling Rule Sets

Combine multiple rules for complex sampling strategies:

```
Rule Set: Production Inspection
├── First 3 Parts (setup verification)
├── Every 10th Part (ongoing monitoring)
└── Last 2 Parts (end-of-run check)
```

### Rule Set Evaluation

1. Rules are evaluated in order
2. Part is sampled if ANY rule matches
3. Sampling status recorded in audit log
4. Non-sampled parts may still require QA

See [Sampling Rules Configuration](../../admin/setup/sampling-rules.md) for setup.

## Sampling History

Track sampling performance:

- Lots accepted/rejected
- Defect rates by supplier
- Sampling level changes
- Skip-lot status

## Sampling Analytics

Track sampling performance:

| Metric | Description |
|--------|-------------|
| **Sample Rate** | % of parts sampled |
| **Pass Rate** | % of samples passing |
| **Rule Effectiveness** | Defect detection by rule |
| **Audit Compliance** | Algorithm verification logs |

View analytics in **Quality Dashboard** > **Sampling Analytics**.

## Sampling Audit Trail

All sampling decisions are logged:

- Sampling rule applied
- Sample size used
- Parts selected
- Results recorded
- Accept/reject decision

## Permissions

| Permission | Allows |
|------------|--------|
| `view_samplingrule` | View sampling configuration |
| `change_samplingrule` | Modify sampling rules |
| `record_sampling` | Record sampling results |

## Best Practices

1. **Match to risk** - Critical features need tighter sampling
2. **Review regularly** - Adjust based on performance
3. **Train inspectors** - Proper sampling technique
4. **Document decisions** - Audit trail matters
5. **Use history** - Leverage skip-lot for proven suppliers

## Next Steps

- [Quality Reports](quality-reports.md) - When sampling fails
- [Sampling Configuration](../../admin/setup/sampling-rules.md) - Admin setup
- [Analytics](../../analysis/dashboard.md) - Quality metrics
