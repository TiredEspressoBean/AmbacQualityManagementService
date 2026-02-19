# Sampling Rules

Configure inspection sampling for quality control.

## What are Sampling Rules?

Sampling rules determine:

- **How many** parts to inspect (sample size)
- **When** to inspect (conditions)
- **What level** of inspection (AQL, etc.)
- **Accept/reject criteria**

## Sampling Concepts

### AQL (Acceptable Quality Level)
Statistical sampling per ANSI/ASQ Z1.4:
- Based on lot size
- Defines acceptable defect rate
- Standard tables for sample size

### Skip-Lot
Skip inspection for proven quality:
- After N consecutive good lots
- Resume on failure
- Rewards good performance

### 100% Inspection
Inspect every part:
- For critical features
- New products/suppliers
- After quality issues

## Creating Sampling Rules

1. Navigate to **Data Management** > **Sampling Rules**
2. Click **+ New Sampling Rule**
3. Fill in details:

| Field | Description |
|-------|-------------|
| **Name** | Rule name |
| **Rule Type** | AQL, Skip-lot, Fixed, etc. |
| **Applies To** | Part type, supplier, step |
| **Active** | Available for use |

4. Configure rule parameters
5. Save

## Rule Types

### AQL Sampling

| Parameter | Description |
|-----------|-------------|
| **AQL Level** | 0.65, 1.0, 2.5, 4.0, etc. |
| **Inspection Level** | I, II, III (normal) |
| **Lot Size Ranges** | Auto per ANSI tables |

AQL tables determine sample size and accept/reject numbers.

### Fixed Quantity

| Parameter | Description |
|-----------|-------------|
| **Sample Size** | Always inspect N parts |
| **Accept Number** | Max defects to accept |

Use when lot sizes are consistent.

### Fixed Percentage

| Parameter | Description |
|-----------|-------------|
| **Percentage** | Inspect X% of lot |
| **Minimum** | At least N parts |
| **Maximum** | No more than M parts |

### Skip-Lot

| Parameter | Description |
|-----------|-------------|
| **Qualify Count** | Consecutive passes to qualify |
| **Skip Count** | Lots to skip after qualifying |
| **Requalify on Fail** | Reset counter on rejection |

## Applying Rules

### To Part Types
Default sampling for a product:
1. Edit part type
2. Set default sampling rule
3. Applies to all parts of type

### To Process Steps
Sampling at specific inspection:
1. Edit process step
2. Add sampling rule
3. Applies at that step

### To Suppliers
Incoming inspection sampling:
1. Edit supplier/company
2. Set sampling rule
3. Applies to material from supplier

## Switching Rules

Configure automatic level changes:

### Normal to Tightened
- After X rejects in Y lots
- Increases sample size
- Lower accept numbers

### Normal to Reduced
- After X consecutive accepts
- Decreases sample size
- Reward for quality

### Tightened to Normal
- After X accepts while tightened
- Return to standard sampling

## Sampling Rule Sets

Group rules for complex scenarios:

```
Rule Set: Incoming Inspection
├── New Supplier: 100% inspection
├── Qualified Supplier: AQL 1.0
└── Premium Supplier: Skip-lot
```

Rules applied based on conditions.

## Recording Sampling Results

When sampling applies:

1. System shows sample size
2. Select/mark sample parts
3. Inspect and record results
4. System calculates accept/reject
5. Lot disposition determined

## Sampling Audit Trail

All sampling decisions logged:
- Rule applied
- Sample size used
- Results recorded
- Accept/reject decision

For regulatory compliance.

## Permissions

| Permission | Allows |
|------------|--------|
| `view_samplingrule` | View rules |
| `add_samplingrule` | Create rules |
| `change_samplingrule` | Edit rules |
| `delete_samplingrule` | Remove rules |

## Best Practices

1. **Match risk** - Tighter sampling for critical parts
2. **Document rationale** - Why this AQL level
3. **Review performance** - Adjust based on results
4. **Train inspectors** - Proper technique
5. **Audit regularly** - Verify compliance

## Next Steps

- [Sampling Workflow](../../workflows/quality/sampling.md) - Using sampling
- [Quality Reports](../../workflows/quality/quality-reports.md) - When sampling fails
- [SPC Charts](../../analysis/spc.md) - Statistical monitoring
