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
- New suppliers
- Poor quality history

### AQL Sampling
Acceptance Quality Level sampling per ANSI/ASQ Z1.4:

- Based on lot size
- Defines sample size
- Accept/reject criteria

### Skip-Lot
Skip lots based on quality history:

- After N consecutive good lots, skip inspection
- Resume after skip period or on failure

### Reduced/Tightened
Adjust sampling based on history:

- **Reduced**: Good history → smaller samples
- **Tightened**: Issues found → larger samples

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
| **Rule Type** | AQL, Skip-lot, Fixed, etc. |
| **Applies To** | Part type, supplier, step |
| **Sample Size** | How many to inspect |
| **Accept Criteria** | Pass/fail threshold |
| **Effective Dates** | When rule applies |

### Rule Types

| Type | Description |
|------|-------------|
| **AQL** | Standard AQL tables (0.65, 1.0, 2.5, etc.) |
| **Fixed Quantity** | Always inspect N parts |
| **Fixed Percentage** | Always inspect N% of lot |
| **Skip-Lot** | Skip after consecutive passes |
| **Attribute** | Go/no-go attributes |

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

Based on AQL tables:

| Sample Size | Accept (Ac) | Reject (Re) |
|-------------|-------------|-------------|
| 8 | 0 | 1 |
| 13 | 1 | 2 |
| 20 | 2 | 3 |

- If defects ≤ Ac → Accept lot
- If defects ≥ Re → Reject lot
- Between → Additional sampling

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

## Skip-Lot Rules

After consistent good quality:

1. Track consecutive accepted lots
2. After N passes (e.g., 5), skip inspection
3. Lot N+1 (and some after) skipped
4. Resume inspection after skip period
5. Any failure resets counter

### Skip-Lot Configuration

| Parameter | Example |
|-----------|---------|
| Consecutive passes required | 5 lots |
| Lots to skip | 2 lots |
| Auto-reset on failure | Yes |

## Sampling History

Track sampling performance:

- Lots accepted/rejected
- Defect rates by supplier
- Sampling level changes
- Skip-lot status

## Switching Rules

Automatically adjust sampling:

| Condition | Action |
|-----------|--------|
| 5 consecutive accepts | Switch to reduced |
| 2 of 5 lots rejected | Switch to tightened |
| On tightened, 5 accepts | Return to normal |

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
