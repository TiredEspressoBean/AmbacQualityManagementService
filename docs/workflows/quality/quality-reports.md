# Quality Reports (NCRs)

Quality Reports document non-conformances found during production or inspection. Also known as Non-Conformance Reports (NCRs).

## What is a Quality Report?

A Quality Report is a formal record of:

- **What** went wrong (defect description)
- **Where** it was found (step, location)
- **How many** parts are affected
- **What caused it** (error type, root cause)
- **What to do** (disposition, corrective action)

## Creating a Quality Report

### From Part Tracking

1. Select the affected part(s)
2. Click **Create Quality Report**
3. Complete the form
4. Submit

### From Quality Menu

1. Navigate to **Quality** > **Quality Reports**
2. Click **+ New Quality Report**
3. Search for and select affected parts
4. Complete the form
5. Submit

### From Mobile/Shop Floor

1. Scan part barcode or enter serial
2. Tap **Report Issue**
3. Quick-fill form
4. Submit

## Quality Report Form

### Required Fields

| Field | Description |
|-------|-------------|
| **Title** | Brief summary of the issue |
| **Error Type** | Category (Dimensional, Visual, etc.) |
| **Severity** | Minor, Major, or Critical |
| **Description** | Detailed explanation |
| **Parts** | Affected parts (auto-populated if started from part) |

### Optional Fields

| Field | Description |
|-------|-------------|
| **Detected At** | Process step where found |
| **Detected By** | Who found the issue |
| **Quantity Affected** | Number of parts |
| **Customer Ref** | Customer complaint number |
| **Immediate Action** | Containment steps taken |
| **Root Cause** | Initial assessment |

### Attachments

Add supporting evidence:

- Photos of defect
- Measurement data
- CMM reports
- Customer communication

## Error Types

Standard error type categories:

| Type | Examples |
|------|----------|
| **Dimensional** | Out of tolerance, wrong size, wrong location |
| **Visual/Cosmetic** | Scratches, dents, discoloration, finish defects |
| **Material** | Wrong material, contamination, defective raw material |
| **Functional** | Doesn't work, fails test, wrong operation |
| **Documentation** | Missing paperwork, wrong revision, labeling error |
| **Process** | Wrong operation, missed step, wrong sequence |

Your administrator configures available error types.

## Severity Levels

| Level | Definition | Examples |
|-------|------------|----------|
| **Minor** | Cosmetic, no functional impact | Light scratch, minor documentation |
| **Major** | Out of spec, may affect function | Dimensional error, material deviation |
| **Critical** | Safety risk or regulatory violation | Cracked safety component, wrong material in medical device |

Severity affects:

- Notification urgency
- Required approvals
- CAPA trigger threshold
- Containment requirements

## Quality Report Status

| Status | Meaning | Next Action |
|--------|---------|-------------|
| **Draft** | Not yet submitted | Complete and submit |
| **Open** | Submitted, awaiting disposition | Assign disposition |
| **Under Review** | Being investigated | Continue investigation |
| **Pending Disposition** | Awaiting disposition decision | Make disposition |
| **Closed** | Disposition complete | No action |

## Disposition

Each quality report requires a disposition decision:

| Disposition | Meaning |
|-------------|---------|
| **Use As Is** | Accept despite non-conformance |
| **Rework** | Repair/correct and re-inspect |
| **Scrap** | Dispose of parts |
| **Return to Vendor (RTV)** | Send back to supplier |
| **Deviate** | Customer-approved deviation |

See [Dispositions](dispositions.md) for detailed workflow.

## Linking to CAPA

Major or recurring issues may require CAPA:

1. Open the quality report
2. Click **Create CAPA** or **Link CAPA**
3. CAPA tracks root cause analysis and corrective actions
4. Quality report links to CAPA record

See [CAPA Overview](../capa/overview.md) for details.

## Searching Quality Reports

Find existing reports:

- By status (Open, Closed)
- By error type
- By severity
- By date range
- By affected part
- By created by

## Quality Report Metrics

Track quality performance:

- **NCRs per period**: Trend over time
- **By error type**: Pareto analysis
- **By severity**: Distribution
- **By process step**: Where defects occur
- **Time to close**: Disposition cycle time

View on **Quality Dashboard** or **Analytics**.

## Notifications

Quality reports trigger notifications:

| Event | Recipients |
|-------|------------|
| New Quality Report | Quality team |
| Critical severity | QA Manager, Supervisor |
| Assigned to you | Assigned user |
| Awaiting your disposition | Approver |
| Report closed | Creator, stakeholders |

## Permissions

| Permission | Allows |
|------------|--------|
| `view_qualityreport` | View reports |
| `add_qualityreport` | Create reports |
| `change_qualityreport` | Edit reports |
| `close_qualityreport` | Close reports |
| `disposition_qualityreport` | Make disposition decisions |

## Best Practices

1. **Report immediately** - Don't wait, document while fresh
2. **Be specific** - Exact measurements, locations, quantities
3. **Add photos** - Visual evidence is invaluable
4. **Include context** - Equipment, operator, conditions
5. **Link related items** - Previous similar issues, parts, orders

## Next Steps

- [Dispositions](dispositions.md) - Making disposition decisions
- [Quarantine](quarantine.md) - Managing held parts
- [CAPA Overview](../capa/overview.md) - Corrective actions
- [Defect Analysis](../../analysis/defects.md) - Quality analytics
