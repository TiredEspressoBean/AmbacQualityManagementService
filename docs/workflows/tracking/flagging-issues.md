# Flagging Issues

When problems are discovered during production, uqmes provides several ways to flag and track issues. This guide covers the options for reporting problems.

## When to Flag an Issue

Flag an issue when:

- A measurement fails inspection
- A visual defect is detected
- A part doesn't fit or function correctly
- Material doesn't meet specifications
- Process deviation occurs
- Customer reports a problem

## How to raise it

There is **no Flag button on a part**. Which route you take depends on what you
found and where you are standing when you find it.

| Situation | Route |
|-----------|-------|
| You're working the step and the substep asks for a result | Record it **in the step player** |
| The part is already past that step, or you're not the one running it | **Quarantine** it from the parts list |
| The problem is the process, the machine, or the whole lot | **Report…** an exception on the work order |

### In the step player (the in-process path)

If the step has an **inspection point** substep, that is where a bad result
belongs. Record the quality status, the defects against their error types, and
any signatures the substep asks for, then confirm.

You do not raise anything separately: an inspection point's captures write a
Quality Report as well as the substep record, so the nonconformance becomes a
queryable quality record on its own. This is the path that keeps the finding
attached to the work that produced it.

### Quarantining from the parts list

To hold parts that are already past the step, or that you are not running
yourself:

1. Open the work order's **control** page
2. **Tick the parts** in the parts list
3. Click **Quarantine** in the actions that appear

The same selection also offers **Rework**, **Scrap**, and **Split selection…**.
Quarantine holds the parts; it does not by itself say what is wrong with them,
so follow it with a quality report or a disposition.

!!! warning "Quarantine acts on the selection, not the row you clicked"
    These are bulk actions on every ticked part. Check the selection before
    clicking — quarantining a lot you did not mean to select stops all of it.

### Reporting an exception on the work order

When the problem is bigger than one part — a machine down, a bad batch, a
process out of control:

1. Open the work order in the **WO Control Center** or its control page
2. Click **Report…**
3. Choose the type — **Quarantine (quality hold)**, **Downtime (equipment /
   resource)**, or **CAPA (corrective action)**
4. Add the reason and notes, then submit

The type routes the event to the right record, and the exception is listed on
the work order until it is resolved. See [Quarantine](../quality/quarantine.md).

### Raising a report after the fact

For something found later — a customer complaint, an audit finding, a problem
noticed off the floor — create the report directly under **Quality** >
**Quality Reports**. See [Quality Reports](../quality/quality-reports.md).

## Error Types

Error types categorize defects for analysis:

| Category | Examples |
|----------|----------|
| **Dimensional** | Out of tolerance, wrong size |
| **Visual** | Scratches, dents, discoloration |
| **Material** | Wrong material, contamination |
| **Functional** | Doesn't work, fails test |
| **Documentation** | Missing paperwork, wrong revision |
| **Process** | Wrong operation, missed step |

Your administrator configures available error types.

## Severity Levels

| Level | Definition | Typical Response |
|-------|------------|------------------|
| **Minor** | Cosmetic or documentation issue | Disposition, no CAPA |
| **Major** | Functional impact or customer spec violation | Disposition + possible CAPA |
| **Critical** | Safety issue or regulatory violation | Immediate containment + CAPA |

## Annotating Defects (3D Models)

If 3D models are configured for the part type:

1. Click **Annotate Defect**
2. The 3D model viewer opens
3. Click on the location of the defect
4. Enter defect details
5. Save the annotation

Annotations appear on heat maps showing defect distribution.

## Containment Actions

For critical issues, take immediate action:

1. **Stop production** on affected parts
2. **Segregate** suspect inventory
3. **Notify** quality manager
4. **Document** containment actions

The quality report tracks containment activities.

## Linking Issues

Connect related issues:

### Link to Previous Reports
If this is a recurring issue:

1. Open the quality report
2. Click **Link Related**
3. Search for previous reports
4. Select related items

### Link to CAPA
If a CAPA is created:

1. The quality report links to the CAPA
2. Track investigation through CAPA
3. Closure requires CAPA completion

## Customer-Reported Issues

When a customer reports a problem:

1. Create a quality report
2. Select **Source: Customer**
3. Enter customer complaint reference
4. Link to affected shipped parts
5. Initiate RMA process if needed

## Operator Notifications

When an issue is flagged:

- Quality team receives notification
- Supervisor is alerted (for major/critical)
- Dashboard shows new issues
- Email sent based on preferences

## What Happens Next

After flagging:

```
Issue Flagged → Quarantine → Investigation → Disposition → Resolution
                    │
                    └── CAPA (if needed)
```

1. **Quarantine**: Part is held, cannot proceed
2. **Investigation**: Quality team reviews
3. **Disposition**: Decision made (Use As Is, Rework, Scrap, RTV)
4. **Resolution**: Part is processed per disposition
5. **CAPA**: Corrective action if systemic issue

See [Dispositions](../quality/dispositions.md) for disposition workflow.

## Permissions

| Permission | Allows |
|------------|--------|
| `add_qualityreports` | Create quality reports |
| `view_qualityreports` | View existing reports |
| `change_qualityreports` | Edit quality reports |

## Next Steps

- [Quality Reports](../quality/quality-reports.md) - Full NCR management
- [Quarantine](../quality/quarantine.md) - Managing held parts
- [Dispositions](../quality/dispositions.md) - Making decisions
- [CAPA Overview](../capa/overview.md) - Corrective actions
