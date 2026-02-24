# Sampling Rules

Configure inspection sampling for quality control.

## What are Sampling Rules?

Sampling rules determine:

- **How many** parts to inspect (sample size)
- **When** to inspect (conditions)
- **What level** of inspection (normal or fallback)
- **Accept/reject criteria**

## Sampling Concepts

### Fallback Sampling
When quality issues occur, tighter sampling is automatically triggered:
- After N consecutive failures, fallback ruleset activates
- Fallback remains active until N consecutive passes
- Automatic deactivation rewards improved performance

### 100% Inspection
Inspect every part:
- For critical features
- New products/suppliers
- After quality issues

Note: Full AQL tables per ANSI/ASQ Z1.4 are not currently implemented. Use percentage or fixed sampling for similar coverage.

## Creating Sampling Rules

1. Navigate to **Data Management** > **Sampling Rules**
2. Click **+ New Sampling Rule**
3. Fill in details:

| Field | Description |
|-------|-------------|
| **Name** | Rule name |
| **Rule Type** | Every Nth, Percentage, First N, Last N, Exact, Random |
| **Applies To** | Part type, supplier, step |
| **Active** | Available for use |

4. Configure rule parameters
5. Save

## Rule Types

### Every Nth Part

| Parameter | Description |
|-----------|-------------|
| **Value (N)** | Inspect every Nth part (e.g., 5 = every 5th part) |

Use for consistent spread across the lot.

### Percentage of Parts

| Parameter | Description |
|-----------|-------------|
| **Value (%)** | Inspect N% of lot |

Scales with lot size.

### First N Parts

| Parameter | Description |
|-----------|-------------|
| **Value (N)** | Inspect first N parts in the lot |

Use for setup verification at production start.

### Last N Parts

| Parameter | Description |
|-----------|-------------|
| **Value (N)** | Inspect last N parts in the lot |

Use to verify end-of-run quality.

### Exact Count

| Parameter | Description |
|-----------|-------------|
| **Value (N)** | Always inspect exactly N parts |

Fixed sample size regardless of lot size.

### Pure Random

| Parameter | Description |
|-----------|-------------|
| **Value (N)** | Randomly select N parts |

SHA-256 hash-based random selection for audit compliance.

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

## Rule Sets

Group multiple rules with different triggers:

```
Rule Set: Production Inspection
├── Rule 1: First 3 parts (every new setup)
├── Rule 2: Every 10th part (ongoing production)
└── Rule 3: Last 2 parts (end-of-run verification)
```

Rules are evaluated in order based on their `order` field.

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
