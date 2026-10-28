# Sampling Rules

Configure inspection sampling for quality control.

## What are Sampling Rules?

Sampling rules determine:

- **How many** parts to inspect (sample size)
- **When** to inspect (conditions)
- **What level** of inspection (normal or fallback)
- **Accept/reject criteria**

## Sampling Concepts

### Tightening, and getting back

There are **two** tightening mechanisms, and they are not the same thing. Which
one you get depends on whether you are inspecting your own production or an
incoming lot.

#### On production: the fallback ruleset

A rule set can name a **fallback ruleset** — a stricter set that takes over when
a [gate](#gates-reacting-to-bad-results) fires. Getting back to the primary set
is automatic, and governed by **Number of good parts required before reverting**
on the primary:

- Each passing part counts towards the run
- **A failure resets the count to zero** — the run has to be *consecutive*
- On reaching the figure, the fallback deactivates and parts still in flight are
  re-evaluated against the primary set

!!! warning "Fallback state is per work order, per step"
    It does not follow the part type or the process. A job that tightened and
    never recovered leaves the **next** work order starting at normal, because
    the state belongs to the job that earned it.

    If you want tightening that persists across jobs, that is a supplier
    question, and it is the mechanism below.

#### On receiving: Z1.4 severity switching

Where the rule set's strategy is **Z1.4**, incoming inspection carries a
**severity** per supplier per receiving step, and it switches itself on lot
history. This one is **cross-work-order** — it is a standing judgement about
that supplier:

| Transition | When |
|------------|------|
| Normal → **Tightened** | 2 of the last 5 lots rejected |
| Tightened → **Normal** | 5 consecutive lots accepted |
| Normal → **Reduced** | 10 consecutive lots accepted |
| Reduced → **Normal** | One lot rejected, or one landing in the reduced accept/reject gap |

!!! note "The severity on the rule set is only the starting point"
    Once a supplier has lot history at a step, the live severity is runtime
    state and the configured field no longer decides anything. Editing it does
    not pull a tightened supplier back to normal — five accepted lots do.

!!! danger "Discontinue is a recommendation, never automatic"
    Z1.4 says that where tightened inspection persists for 5 consecutive lots
    without earning a return to normal, you stop accepting that supplier's
    product. The system raises that as a **recommendation**. It does not suspend
    the supplier's approval, and it never will — removing a source is a
    commercial decision with a person's name on it.

    C=0 and Z1.9 do not switch severity. C=0 escalates through the gate's
    100%-inspection and fallback path instead.

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
| **Value** | A **percentage**, 1–100 — each part has that chance of being selected |

!!! warning "The value is a percentage, not a count of parts"
    Setting it to `5` does **not** sample five parts. It gives every part a 5%
    chance, so a lot of 20 may yield one part and a lot of 1000 about fifty. If you
    want a fixed number of parts, use **Exact Count**; for a fixed proportion with
    predictable behaviour, use **Percentage of Parts**.

!!! danger "Do not choose Pure Random for auditability"
    It is the one rule type deliberately built so a selection **cannot** be
    reconstructed afterwards. The draw is unseeded wherever it is evaluated — the
    intent is a genuinely unpredictable spot check, not a repeatable one.

    **If you need a selection an auditor can reproduce, use Percentage of Parts.**
    That is what it is for: it walks the parts in order and takes the first slice,
    so the same lot always yields the same sample.

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

## Where a rule set applies

Scope lives on the **rule set**, not on the things it covers. You do not go to a
part type, a step or a supplier and attach sampling to it — there is no such
field on any of them. You create the rule set and tell it what it covers:

| Scope field | Effect |
|-------------|--------|
| **Part type** | The product this set governs |
| **Process** | Optional context, because a step can appear in several processes |
| **Step** | The inspection point it applies at |
| **Supplier** | For receiving acceptance sampling. Blank = all suppliers. |

Leave a field blank to widen the scope rather than narrow it.

!!! note "What a step itself carries"
    A step has only **Sampling required** and a **minimum sampling rate** — a
    floor, not a rule. Which parts get selected is the rule set's business.

## Rule sets

A rule set groups rules that fire on different triggers:

```
Rule Set: Production Inspection
├── Rule 1: First 3 parts (every new setup)
├── Rule 2: Every 10th part (ongoing production)
└── Rule 3: Last 2 parts (end-of-run verification)
```

Rules are evaluated in order, by their `order` field.

!!! warning "Supplier tiers are separate rule sets, not rules in one"
    To sample a new supplier at 100% and a qualified one by AQL, build **two
    rule sets**, each scoped to its supplier. A single set does not switch
    between its own rules by condition.

## Using the rules

Nobody picks a sample by hand. The rules decide which parts are flagged for
inspection as work moves, and which lots are judged at receiving — see
[Sampling](../../workflows/quality/sampling.md) for what that looks like at the
inspection point.

### Why this part and not that one

Every selection is logged: the part, the rule that decided it, whether it was
selected or skipped, which ruleset type was in force, and when.

!!! tip "The skips are the point"
    Logging only the parts you inspected proves nothing — an auditor's question
    is *why was that one not inspected?* Because the log records the decision
    rather than the outcome, that question has an answer: this rule, this
    position in the lot, this moment.

    A part skipped because a rule ruled it out — outside a *first N* or
    *last N* window — is logged against that rule. A part that **no** rule
    selected is logged against the rule set, with no rule named: every rule was
    weighed and none chose it. **Pure Random** is unreconstructable by design,
    as above.

### Reading a part's decisions

On the work order's control page, open a part's history: the **Sampling
decisions** block lists every decision for it, newest first, with the time.
Selected lines are bold, and a decision made under the fallback rule set says
so.

- *Selected by every 5th part* — or *5% of parts*, *a random 10% of parts*,
  *the first 15 parts*, *exactly 3 parts*
- *Excluded by the first 15 parts* — outside a first-N or last-N window
- *Not selected — no rule in &lt;rule set&gt; chose it*

A plain *Not selected* comes from a decision recorded before skips were
attributed. Read it as "this rule set did not select it". There is no list of
decisions across parts or by rule set.

## Permissions

Authoring sampling is **quality planning**, so it sits with the quality roles
rather than with every staff role — the same tier as SPC baselines.

| Permission | Allows | Held by |
|------------|--------|---------|
| `view_samplingrule` / `view_samplingruleset` | See the rules and sets | Every staff role |
| `add_samplingrule` / `change_samplingrule` | Author the rules | QA Inspector, QA Manager, Tenant Admin |
| `add_samplingruleset` / `change_samplingruleset` | Author the sets, where the scope and plan live | QA Inspector, QA Manager, Tenant Admin |
| `delete_samplingrule` / `delete_samplingruleset` | Remove them | QA Manager, Tenant Admin |

*Held by* is the groups that hold it when an organisation is created. Group permissions can be changed, so check your own in [Roles & Groups](../users/roles.md).

!!! note "Engineering does not author sampling by default"
    A step's **Sampling required** flag is Engineering's, because it is part of
    the routing. *How much* to sample is a quality judgement, and the rule sets
    belong to QA.

## Next Steps

- [Sampling Workflow](../../workflows/quality/sampling.md) - Using sampling
- [Quality Reports](../../workflows/quality/quality-reports.md) - When sampling fails
- [SPC Charts](../../analysis/spc.md) - Statistical monitoring
