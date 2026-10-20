# CAPA Overview

CAPA (Corrective and Preventive Action) is a systematic approach to investigating quality issues, identifying root causes, and implementing actions to prevent recurrence.

## What is CAPA?

CAPA addresses quality problems through:

- **Corrective Action**: Fix the immediate problem and prevent recurrence
- **Preventive Action**: Identify potential problems and prevent occurrence

## When to Use CAPA

Create a CAPA for:

| Trigger | Examples |
|---------|----------|
| **Recurring defects** | Same error type multiple times |
| **Major/Critical NCRs** | Significant quality escapes |
| **Customer complaints** | Field failures, returns |
| **Audit findings** | Internal or external audit issues |
| **Near misses** | Potential safety issues |
| **Trend analysis** | Data shows concerning patterns |

## CAPA Process

!!! note "8D is a method you run, not a structure uqmes tracks"
    The eight disciplines below are a widely used framework and map cleanly onto
    the work — but **the CAPA record has no phase field**. The system tracks
    *status* (Open → In Progress → Pending Verification → Closed), an RCA
    record, tasks and a verification. It does not know which D you are on. One
    step of the sequence is enforced: the root cause must be **verified** (D4)
    before effectiveness can be checked. Containment and tasks are never held
    back waiting for it.

    Use 8D if your facility works that way, and attach the **8D Report**
    document type to the CAPA. IATF 16949 expects a defined problem-solving
    method; it does not require this one.

The disciplines, and where each lands in uqmes:

```
D1: Team         D2: Problem      D3: Containment
    ↓                ↓                 ↓
D4: Root Cause   D5: Corrective   D6: Implement
    ↓                ↓                 ↓
D7: Preventive   D8: Close &
                     Recognize
```

### D1: Establish Team
- Assign team members
- Define roles and responsibilities
- Set timeline

### D2: Define Problem
- Clear problem statement
- Affected products/processes
- Scope and impact

### D3: Containment Actions
- Immediate actions to limit impact
- Quarantine suspect material
- Stop shipment if needed

### D4: Root Cause Analysis
Recorded as an **RCA record** linked to the CAPA, with one of four methods:

| Method | Structured capture |
|--------|--------------------|
| **5 Whys** | **Yes** — the whys are captured as their own fields |
| **Fishbone Diagram** | **Yes** — causes captured per category (man, machine, material, method, measurement, environment) |
| **Fault Tree** | **No** — the method is recorded, the tree is not |
| **Pareto Analysis** | **No** — the method is recorded, the ranking is not |

Each RCA carries a problem description, the identified root causes, a root
cause summary, and who conducted it.

!!! warning "Two of the four methods have no structured form behind them"
    Choosing **Fault Tree** or **Pareto** records *that* you used it. There is
    no tree to build and no chart to fill in — the analysis itself lives in the
    problem description, the root causes and the summary, or in a document you
    attach.

    That is workable, but it means the evidence for those two is prose. If you
    want the analysis itself held as data, use 5 Whys or Fishbone.

The root cause then has its own **verification status** — **Unverified**,
**Verified**, or **Disputed**. *Disputed* matters: a root cause can be
challenged rather than silently accepted, and the CAPA shows that it is
contested.

### Approving the root cause

On the CAPA's **RCA** tab, a holder of `review_rca` — by default QA Manager and
Tenant Admin — presses **Approve** on an unverified or disputed RCA. Approving
verifies the root cause, records who did it and when, and adds any
**Verification notes**.

**Whoever conducted the RCA cannot approve it**, unless the CAPA allows
self-verification. If it does, the notes become required, at least ten
characters, and the RCA is flagged self-verified. If it does not, the dialog
says so and offers no Approve.

Until the root cause is verified, the CAPA cannot move to Pending Verification
and no effectiveness check can be recorded: *"The root cause must be verified
before effectiveness can be checked"*. The CAPA lists *Root cause not verified*
among what is blocking it.

### D5: Develop Corrective Actions
- Define permanent fixes
- Address root cause
- Plan implementation

### D6: Implement Actions
- Execute corrective actions
- Track completion
- Verify implementation

### D7: Prevent Recurrence
- Systemic changes
- Update procedures/training
- Extend to similar processes

### D8: Close and Recognize
- Verify effectiveness
- Close CAPA
- Recognize team

## CAPA Status

| Status | Meaning |
|--------|---------|
| **Open** | CAPA created, initial phase |
| **In Progress** | Active work (tasks or RCA started) |
| **Pending Verification** | All tasks complete, awaiting effectiveness verification |
| **Closed** | CAPA complete with verified effectiveness |
| **Cancelled** | CAPA cancelled |

Note: Status transitions automatically based on task completion and RCA progress. The system calculates suggested status from current state.

## CAPA Severity

| Severity | When to Use |
|----------|-------------|
| **Critical** | Safety issues, regulatory concerns, immediate containment required |
| **Major** | Significant quality escapes, customer complaints, functional defects |
| **Minor** | Cosmetic issues, improvement opportunities, recurring minor issues |

## CAPA Types

| Type | Description |
|------|-------------|
| **Corrective Action** | Fix existing problem and prevent recurrence |
| **Preventive Action** | Address potential problem before it occurs |
| **Customer Complaint** | Response to field failure or customer report |
| **Internal Audit** | Finding from internal quality audit |
| **Supplier Issue** | Problem with supplier materials or processes |

## Linked Records

CAPAs connect to:

- **Quality Reports**: The triggering NCR(s)
- **Parts**: Affected parts
- **Orders**: Affected orders
- **Documents**: Related procedures, evidence
- **Tasks**: Action items

## CAPA Dashboard

The Quality Dashboard shows:

- Open CAPAs by status
- CAPAs by priority
- Overdue actions
- Aging analysis
- Effectiveness metrics

## CAPA Metrics

Track CAPA performance:

| Metric | Description |
|--------|-------------|
| **Open CAPAs** | Current workload |
| **Average age** | Time to closure |
| **On-time closure** | % closed by due date |
| **Effectiveness** | % verified effective |
| **Recurrence rate** | Issues that return |

## Permissions

| Permission | Allows |
|------------|--------|
| `view_capa` | View CAPAs |
| `add_capa` | Create CAPAs |
| `change_capa` | Edit CAPAs |
| `initiate_capa` | Initiate new CAPAs |
| `verify_capa` | Record the effectiveness outcome — **this is what closes the CAPA** |

!!! note "There is no close or approve permission"
    Closure is the verification decision, so `verify_capa` is the whole of it.
    A Critical or Major CAPA also raises a **CAPA_APPROVAL** request at
    creation; who may answer that is set by the approval **template's**
    approver bindings, the same as every other approval type.

## Next Steps

- [Creating a CAPA](creating.md) - Start a new CAPA
- [CAPA Tasks](tasks.md) - Managing action items
- [Verification & Closure](verification.md) - Completing CAPAs
