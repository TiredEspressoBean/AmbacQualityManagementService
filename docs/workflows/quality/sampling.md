# Sampling Rules

Sampling allows inspecting a subset of parts rather than 100%, based on statistical rules. This guide covers sampling configuration and use.

!!! note "Rule sets follow the operation"
    A rule set is scoped by **step**. Its part type and process are recorded but
    not matched on, so in-process sets apply to every part running through the
    step. A receiving step's set can also name a supplier, so one supplier can be
    inspected tighter than the rest. See [Where a rule set
    applies](../../admin/setup/sampling-rules.md#where-a-rule-set-applies).

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
Random selection — deliberately not reproducible:

- Unbiased sample
- Nobody can work out in advance which unit will be picked
- **Cannot be reconstructed after the fact** — the choice is not derived from the
  part, so re-running it will not produce the same answer

!!! warning "Random cannot be reconstructed"
    The draw is a true random number wherever the rule is evaluated, step or
    substep. If you need a selection you can re-derive, use **Percentage**.

!!! note "If you need a sample an auditor can reproduce, use Percentage"
    **Percentage** is deterministic. On a step and on a substep alike it hashes
    the part's identity (SHA-256), so the same part always gets the same answer,
    whatever else is at the step, and the selection can be re-derived from the
    record. It comes to about the percentage overall, not an exact count per lot;
    0% selects none and 100% selects all. If every lot needs guaranteed coverage,
    use **Every Nth Part** or **First N Parts**.
    **Pure Random** does the opposite on purpose — it is the stronger choice against
    gaming, and the weaker one for reconstruction. Pick the property you need.

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

Sampling rules are authored by **QA** — see [Permissions](#permissions) below —
on the rule set's page, in the flow editor's step **Sampling** dialog, or on the
step form. See [Creating Sampling
Rules](../../admin/setup/sampling-rules.md#creating-sampling-rules).

### Rule Components

| Component | Description |
|-----------|-------------|
| **Rule Type** | How parts are selected — nine types, streaming or lot-acceptance |
| **Rule Set** | The set the rule belongs to; the set carries the scope (its step, and for receiving its supplier) |
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
| **Pure Random** | Unbiased random selection; deliberately not reproducible (use Percentage if you need to re-derive it) |
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
| **Percentage** | Scales coverage with lot size | Small lots get very few samples, possibly none — it is about the percentage overall, not per lot |
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
A **Random** rule decides each part independently, at the rule's percentage,
with a draw that cannot be reconstructed afterwards.

Selection is not a flag written onto the part. The system records a
**sampling decision** for the part and the rule that decided it; what you see on
the step is that decision, not a marker on the part itself.

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
└── Every 10th Part (ongoing monitoring)
```

### Rule Set Evaluation

Rules are evaluated in **order**, and the first rule to decide ends the
evaluation:

1. If a rule matches, the part is sampled and no later rule runs
2. If a **First N Parts** or **Last N Parts** rule does *not* match, the part is
   **not sampled** and no later rule runs
3. Any other rule that does not match simply falls through to the next one
4. Every decision, sampled or not, is written to the sampling audit log

!!! warning "A First-N or Last-N rule is a gate, not an alternative"
    Those two rule types short-circuit the whole set. In the example above, part
    7 is **not** sampled: the First-3 rule does not match it, so evaluation stops
    there and the Every-10th rule never runs. Put a First-N or Last-N rule in a
    set only when you mean "sample inside this window and nowhere else" — to
    combine a setup check with ongoing monitoring, order the ongoing rule
    first, or use separate rule sets.

See [Sampling Rules Configuration](../../admin/setup/sampling-rules.md) for setup.

## Sampling History

Track sampling performance:

- Lots accepted/rejected
- Defect rates by supplier
- Sampling level changes

## Sampling Analytics

There is no sampling-metrics screen or endpoint. A per-rule-set tally of parts
sampled and defects found is kept as quality reports are written, but nothing
shows it. Work rates out from the decisions below and the quality reports. The
step editor's coverage figure is an estimate from the rules, not a measured
rate.

## Sampling Audit Trail

Every step-level sampling decision is logged with:

- Part
- Rule and rule set applied (primary or fallback)
- Sampled or not
- When

A step's decisions show on the work order's control page: open a part's
history and read its **Sampling decisions** — the rule that selected or
excluded it, and when. A substep's decisions show in the operator's step
runtime, which marks each substep as skipped or waiting; decisions still
pending show on the control page's pending-decisions panel, with **Reconcile
now**. There is no list of a part's past substep decisions. The inspection
result is not in the log; it is on the part's quality report.

## Permissions

| Permission | Allows | Held by |
|------------|--------|---------|
| `view_samplingrule` | View sampling configuration | Every staff role |
| `add_samplingrule` / `change_samplingrule` | Author the rules | **QA Manager, QA Inspector, Tenant Admin** |
| `add_samplingruleset` / `change_samplingruleset` | Author the sets and their plan parameters | **QA Manager, QA Inspector, Tenant Admin** |
| `delete_samplingrule` / `delete_samplingruleset` | Remove one | **Tenant Admin, QA Manager** |

*Held by* is the groups that hold it when an organisation is created. Group permissions can be changed, so check your own in [Roles & Groups](../../admin/users/roles.md).

!!! note "This is a quality decision, not an administrative one"
    Sampling rules are **not** configured by whoever administers the system.
    How much gets inspected is a quality judgement, so authoring sits with QA —
    including the **QA Inspector**, which surprises people. It holds on every
    surface: the flow editor's step **Sampling** dialog needs
    `add_samplingruleset` and `change_samplingruleset`, and opens read-only
    without them.

    Production Manager, Shift Lead and Engineering do **not** hold it, even
    though Engineering authors the step the rule hangs off and owns SPC control
    limits. If a rule is inspecting the wrong amount, that is a conversation
    with QA.

Sampling decisions themselves are written by the engine, not by people —
recording one is part of running the step.

## Next Steps

- [Quality Reports](quality-reports.md) - When sampling fails
- [Sampling Configuration](../../admin/setup/sampling-rules.md) - Admin setup
- [Analytics](../../analysis/dashboard.md) - Quality metrics
