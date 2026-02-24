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

## CAPA Process (8D Methodology)

Ambac Tracker follows the 8D problem-solving methodology:

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
- Identify why it happened
- Use tools: 5 Why, Fishbone, etc.
- Verify root cause

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
| `close_capa` | Close CAPAs |
| `approve_capa` | Approve CAPAs |
| `verify_capa` | Verify CAPA effectiveness |

## Best Practices

1. **Start promptly** - Don't delay after trigger
2. **Contain first** - Protect customers
3. **Find true root cause** - Not symptoms
4. **Verify actions** - Confirm they worked
5. **Prevent recurrence** - Systemic changes
6. **Document thoroughly** - Audit evidence

## Next Steps

- [Creating a CAPA](creating.md) - Start a new CAPA
- [CAPA Tasks](tasks.md) - Managing action items
- [Verification & Closure](verification.md) - Completing CAPAs
