# Sampling Rules

Configure inspection sampling for quality control.

!!! example "Demo Sampling Configuration"
    In demo mode, these sampling rules are configured:

    - **Normal Inspection**: Every 5th part (20% sampling) for Flow Testing step
    - **Tightened Inspection**: Every 3rd part (33% sampling) - activates after 2 consecutive failures
    - **First Piece**: First 3 parts always inspected at setup (First N rule)
    - **Incoming Inspection**: 10% random sampling for supplier materials

    Delphi Fuel Systems supplier is currently in **tightened** state after 2 consecutive lot rejections. Next 5 consecutive passing lots will return to normal.

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

!!! tip "State Transitions in Demo"
    The demo shows Delphi Fuel Systems in **tightened** state:

    1. **Normal → Tightened**: After 2 consecutive lot failures (triggered)
    2. **Tightened → Normal**: After 5 consecutive lot passes (pending)

    This mirrors ANSI/ASQ Z1.4 switching rules where tightened inspection provides higher defect detection until quality improves.

### 100% Inspection
Inspect every part:
- For critical features
- New products/suppliers
- After quality issues

!!! tip "For incoming lots, prefer a lot-acceptance plan"
    100% inspection is the blunt instrument. ANSI/ASQ Z1.4 (with Normal,
    Tightened and Reduced severities), C=0, and Z1.9 variables sampling are all
    implemented and give defensible protection from a fraction of the
    inspection. See [Choosing a
    rule](../../workflows/quality/sampling.md#choosing-a-rule).

## Creating Sampling Rules

1. Navigate to **Data Management** > **Sampling Rules**
2. Click **New Sampling Rules**
3. Fill in details:

| Field | Description |
|-------|-------------|
| **Rule Set** *(required)* | The rule set this rule belongs to |
| **Rule Type** *(required)* | How parts are selected (below) |
| **Sampling Rule Value** *(required)* | The rule's number — N, a percentage, or a count |
| **Order** | Position when a set holds several rules |

Submit with **Create Sampling Rule**.

!!! important "Rules live inside a rule set"
    A sampling rule is not standalone and carries no name or scope of its own.
    It belongs to a **Sampling Rule Set**, and the set is what decides *where*
    the sampling applies — its part type, process, step, or supplier — along
    with AQL, inspection level, severity, strategy, and fallback behaviour.

    Create the rule set first, then add rules to it.

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

## Lot-Acceptance Rule Types

The types above stream per part. These three judge a **whole lot** from a
sample, and are what receiving inspection uses. Their plan parameters —
**AQL**, **inspection level**, **severity**, and **strategy** — live on the
rule set, not the rule.

| Type | Standard | Accepts on |
|------|----------|-----------|
| **Acceptance Sampling** | ANSI/ASQ Z1.4 | Defects found in the sample against the AQL plan |
| **Zero-Acceptance** | C=0 (Squeglia) | Any defect in the sample rejects the lot |
| **Variables Sampling** | ANSI/ASQ Z1.9 | A measured characteristic — sample mean and spread against an acceptability constant |

!!! note "Variables sampling needs a characteristic"
    A Variables rule measures one characteristic, so the rule set must name
    which one. Without it the rule cannot be evaluated.

## Gates: reacting to bad results

A rule set can carry a **gate** — a rule that watches results and fires actions
when quality degrades. This is what escalates a problem instead of letting it
repeat.

**What it watches:**

| Metric | Trips on |
|--------|----------|
| **Consecutive failures** | A run of failures in a row |
| **Failure rate (%)** | Failure percentage over the window |
| **Defective count** | Number of defectives in the window |

**Over what window:**

| Window | Meaning |
|--------|---------|
| **Whole work order at this step** | Everything at that step on the job |
| **Rolling last N inspections** | The most recent N |
| **Receiving lot sample** | The lot's sample |

**What it does when it trips** — one or more of:

| Action | Effect |
|--------|--------|
| **Route to alternate edge** | Send parts down a different path |
| **Tighten sampling** | Switch to a stricter rule set |
| **Hold / quarantine** | Stop the material |
| **Raise CAPA / SCAR** | Open a CAPA, or a SCAR when the type is Supplier |
| **Require approval** | Demand an approval before continuing |

A gate also sets a **minimum sample** before it can trip, so it does not fire
on one bad reading.

!!! tip "Tighten sampling is the ANSI/ASQ switching rule"
    Pairing **Tighten sampling** with a stricter rule set implements normal →
    tightened inspection switching: quality drops, sampling intensifies, and
    it relaxes again when the process settles.

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

## Next Steps

- [Sampling Workflow](../../workflows/quality/sampling.md) - Using sampling
- [Quality Reports](../../workflows/quality/quality-reports.md) - When sampling fails
- [SPC Charts](../../analysis/spc.md) - Statistical monitoring
