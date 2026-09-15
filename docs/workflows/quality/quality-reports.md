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

1. Navigate to **Quality** > **Quality Reports**
2. Click **New Quality Reports**
3. Complete the form
4. Click **Submit**

A report can also be produced by an inspection substep in the step player — a
substep marked an **inspection point** writes a quality report from what the
operator captures. See [Authoring Work
Instructions](../dwi/authoring.md).

!!! note "No scan-to-report flow"
    There is no barcode-scan shortcut that opens a pre-filled report.

## Quality Report Form

| Field | Required | Description |
|-------|:--------:|-------------|
| **Status** | Yes | Where the report stands, e.g. Pending Review |
| **Part** | No | The affected part |
| **Process Step** | No | Where it was found |
| **Machine/Equipment** | No | Equipment involved |
| **Description** | No | Explanation of the issue |
| **Detected By** | No | Who found it |
| **Verified By** | No | Who verified it |
| **First Piece Inspection** | No | Links the report to an FPI record |
| **Archived** | No | Archive the report |

!!! note "Defects are added separately"
    **Error types are not fields on the report.** Each defect is its own entry
    with an error type, a **count**, a **location**, a **severity**, and notes.
    One report can carry several defects at different severities, which is why
    severity sits on the defect rather than the report.

!!! note "Not on the form"
    There is no quantity-affected, customer-reference, immediate-action, or
    root-cause field. Containment and root cause belong to the
    [CAPA](../capa/creating.md) raised from the report.

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
| **Visual/Cosmetic** | Scratches, dents, discoloration, nozzle tip erosion |
| **Material** | Wrong material, contamination, defective raw material |
| **Functional** | Doesn't work, fails test, spray pattern asymmetry, flow rate out of spec |
| **Documentation** | Missing paperwork, wrong revision, labeling error |
| **Process** | Wrong operation, missed step, wrong sequence |

Your administrator configures available error types.

!!! example "Diesel Injector Example"
    For a fuel injector failing Flow Testing: Error Type = **Functional**, Description = "Flow rate 142 mL/min (spec: 105-135 mL/min)", Severity = **Major**.

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
| **Pending** | Inspection not yet complete | Complete inspection |
| **Pass** | Part passed inspection | Continue production |
| **Fail** | Part failed inspection | Create disposition |

Note: Quality reports with FAIL status trigger the disposition workflow for handling non-conforming parts.

## Disposition

Quality reports with FAIL status trigger a separate disposition workflow. Disposition decisions are made through the Dispositions feature, not directly on the quality report.

Available dispositions:

| Disposition | Meaning |
|-------------|---------|
| **Use As Is** | Accept despite non-conformance (requires customer approval) |
| **Rework** | Correct and re-inspect to full conformance |
| **Repair** | Correct but may deviate from spec (requires approval) |
| **Scrap** | Dispose of parts |
| **Return to Supplier** | Send back to supplier |

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
| `view_qualityreports` | View reports |
| `add_qualityreports` | Create reports |
| `change_qualityreports` | Edit reports |
| `approve_qualityreports` | Approve quality reports |
| `approve_own_qualityreports` | Approve your own quality reports |

Note: Disposition decisions use separate permissions (`approve_disposition`, `close_disposition`).

## Next Steps

- [Dispositions](dispositions.md) - Making disposition decisions
- [Quarantine](quarantine.md) - Managing held parts
- [CAPA Overview](../capa/overview.md) - Corrective actions
- [Defect Analysis](../../analysis/defects.md) - Quality analytics
