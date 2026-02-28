# Flagging Issues

When problems are discovered during production, Ambac Tracker provides several ways to flag and track issues. This guide covers the options for reporting problems.

## When to Flag an Issue

Flag an issue when:

- A measurement fails inspection
- A visual defect is detected
- A part doesn't fit or function correctly
- Material doesn't meet specifications
- Process deviation occurs
- Customer reports a problem

## Reporting Issues via Quality Report

The primary way to flag a quality issue is through a Quality Report with FAIL status:

1. Find the part in **QA Parts** table
2. Click the **Quality Report** button
3. Fill in the form with status set to **FAIL**
4. Select the error type
5. Add a description of the issue
6. Submit

The part enters quarantine status and cannot proceed until disposition is determined.

## Quality Report Details

When creating a quality report:

1. Navigate to the part in **QA Parts** or from the order detail
2. Click **Quality Report**
3. Fill in the report form:

| Field | Description |
|-------|-------------|
| **Title** | Brief description of the issue |
| **Error Type** | Category of defect |
| **Severity** | Minor, Major, or Critical |
| **Description** | Detailed explanation |
| **Immediate Action** | What was done immediately |
| **Parts Affected** | Auto-populated with selection |

4. Set **Status** to FAIL for non-conforming parts
5. Add attachments (photos, measurements)
6. Submit the report

See [Quality Reports](../quality/quality-reports.md) for full details.

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

## Best Practices

1. **Flag immediately** - Don't wait, quarantine suspect parts
2. **Be specific** - Detailed descriptions help investigation
3. **Add photos** - Visual evidence is invaluable
4. **Include measurements** - Attach failed measurement data
5. **Note environment** - Conditions, equipment, operator info

## Permissions

| Permission | Allows |
|------------|--------|
| `add_qualityreport` | Create quality reports |
| `view_qualityreport` | View existing reports |
| `change_qualityreport` | Edit quality reports |

## Next Steps

- [Quality Reports](../quality/quality-reports.md) - Full NCR management
- [Quarantine](../quality/quarantine.md) - Managing held parts
- [Dispositions](../quality/dispositions.md) - Making decisions
- [CAPA Overview](../capa/overview.md) - Corrective actions
