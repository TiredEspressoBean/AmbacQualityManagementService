# Sampling Rules

Sampling allows inspecting a subset of parts rather than 100%, based on statistical rules. This guide covers sampling configuration and use.

!!! example "Demo: Flow Testing Sampling"
    In demo mode, Flow Testing uses **Every 5th Part** sampling (20%):

    - Order ORD-2024-0042 with 24 parts: 5 parts sampled for inspection
    - QA Inspector Sarah Chen sees which parts require inspection
    - Parts INJ-0042-018 and INJ-0042-021 are currently awaiting sample inspection

    **Delphi Fuel Systems** is in **tightened** state (Every 3rd Part = 33% sampling) after 2 consecutive lot failures. This demonstrates automatic switching rules.

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
| **Rule Type** | How parts are selected — nine types, streaming or lot-acceptance |
| **Rule Set** | The set the rule belongs to; the set carries the scope (part type, process, step, supplier) |
| **Value** | The N value (interval, percentage, count) |
| **Order** | Position when a set holds several rules |
| **Fallback Rule Set** | Tighter sampling switched to when quality degrades |

!!! tip "Gates decide when sampling tightens"
    Switching to the fallback set is one of the actions a **gate** can fire —
    alongside holding the lot, routing to an alternate path, raising a
    CAPA/SCAR, or requiring approval. The gate watches consecutive failures,
    failure rate, or defective count over a window. See [Sampling
    Rules](../../admin/setup/sampling-rules.md#gates-reacting-to-bad-results).

### Rule Types

| Type | Description |
|------|-------------|
| **Every Nth Part** | Inspect at regular intervals (e.g., every 5th part) |
| **Percentage** | Inspect a percentage of the lot |
| **Pure Random** | SHA-256 hash-based random selection for unbiased sampling |
| **First N Parts** | Inspect first N parts (setup verification) |
| **Last N Parts** | Inspect last N parts (end-of-run check) |
| **Exact Count** | Always inspect exactly N parts (no variance) |

Three further types judge a **whole lot** from a sample rather than streaming
per part, and are what receiving inspection uses:

| Type | Standard |
|------|----------|
| **Acceptance Sampling** | ANSI/ASQ Z1.4 — defects in the sample against an AQL plan |
| **Zero-Acceptance** | C=0 (Squeglia) — any defect rejects the lot |
| **Variables Sampling** | ANSI/ASQ Z1.9 — a measured characteristic against an acceptability constant |

Their plan parameters (AQL, inspection level, severity, strategy) are set on
the **rule set**. See [Sampling
Rules](../../admin/setup/sampling-rules.md).

## Choosing a rule

The rule types are not interchangeable. Each is blind to something, and the
choice is really about *which failure you are trying to catch*.

### In-process (streaming) rules

| Rule | Catches | Blind to |
|------|---------|----------|
| **First N Parts** | Setup and first-off errors | Anything that develops during the run |
| **Last N Parts** | Tool wear, drift, thermal growth | Setup errors — the lot is already made |
| **Every Nth Part** | Steady-state process shift | Periodic faults that sync with your interval |
| **Percentage** | Scales coverage with lot size | Small lots get very few samples |
| **Pure Random** | Anything — it has no pattern to defeat | Nothing systematic, but the workload is unpredictable |
| **Exact Count** | Gives a fixed, plannable workload | Detection power falls as lots get bigger |

!!! tip "First N and Last N are complements, not alternatives"
    Setup errors and drift are different failure modes with different causes.
    A rule set containing both brackets the run at each end, and is a far more
    common configuration than either alone.

!!! warning "Every Nth has a blind spot by construction"
    If a fault recurs on a cycle that shares a factor with your interval — a
    4-cavity mould sampled every 4th part, one bad spindle in a 6-spindle
    machine sampled every 6th — you can inspect forever and always miss it.
    Where the process has a natural cycle, **Pure Random** removes the problem.

### Lot-acceptance rules (receiving)

These decide **accept or reject for the whole lot**, so the question is how
much risk you will carry and how much inspection you will pay for.

| Rule | Choose when | Cost |
|------|-------------|------|
| **Zero-Acceptance (C=0)** | You cannot knowingly accept *any* defective unit | Smallest attribute sample for equivalent protection |
| **Acceptance Sampling (Z1.4)** | You have an established AQL agreement with the supplier or customer | Larger samples; accept numbers above zero |
| **Variables (Z1.9)** | The characteristic is *measured*, and reasonably normal | Much smaller samples — but one characteristic per plan |

**The practical difference between C=0 and Z1.4** is what happens when the
inspector finds one defect. Under a Z1.4 plan with an accept number above zero,
the lot is still accepted. Under C=0 it is rejected. If your customer would be
astonished to learn you accepted a lot after finding a defect in the sample,
you want C=0 — which is why it has largely displaced Z1.4 in aerospace work.

**Variables sampling buys smaller samples with stronger assumptions.** Z1.9
judges the lot from the sample's mean and spread against an acceptability
constant, which is dramatically more efficient than counting defectives — but
it needs a genuinely measured characteristic, an approximately normal
distribution, and a separate plan per characteristic. It cannot judge
attributes, and it is the wrong tool for a mixed pass/fail inspection.

!!! warning "AQL is not a quality target"
    An AQL is the worst average quality that will still be *accepted* routinely
    — a limit on what you tolerate, not a goal to aim at. Treating "AQL 1.0" as
    "1% defects is fine" inverts its meaning. It is the boundary of
    acceptability, and a process sitting at it is performing as badly as the
    plan permits.

### Sample size is not the same as protection

A bigger sample from a bigger lot does not automatically mean better detection.
With **Exact Count**, inspecting 5 parts gives real coverage of a 20-part lot
and almost none of a 2,000-part lot — the rule is unchanged but the protection
has collapsed. If lot sizes vary a lot, prefer **Percentage** or a proper
lot-acceptance plan, which size the sample from the lot.

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

!!! note "Planned Feature"
    Sampling analytics are recorded by the system but have no screen yet. The
    metrics above are available via the API; a **Sampling Analytics** view is
    planned for a future release.

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
| `add_samplingdecision` | Record a sampling decision |

## Next Steps

- [Quality Reports](quality-reports.md) - When sampling fails
- [Sampling Configuration](../../admin/setup/sampling-rules.md) - Admin setup
- [Analytics](../../analysis/dashboard.md) - Quality metrics
