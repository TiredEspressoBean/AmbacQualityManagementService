# QA Inspector Guide

This guide is for Quality Assurance Inspectors who perform inspections, record measurements, create quality reports, and manage sampling.

## Your Role

As a QA Inspector, you:

- Perform inspections at quality gates
- Record measurements and inspection data
- Create quality reports (NCRs) for non-conformances
- Apply sampling rules to lots
- Document defects with annotations
- Support disposition decisions

## Getting Started

### First-Time Setup

1. Log in and review [Navigation Tour](../getting-started/navigation.md)
2. Familiarize yourself with Quality section
3. Understand your inspection assignments

### Your Main Pages

| Page | Location | Purpose |
|------|----------|---------|
| **Tracker** | Portal > Tracker | View orders and parts |
| **Inbox** | Personal > Inbox | Your inspection tasks |
| **Quality Reports** | Quality > Quality Reports | NCRs you've created |
| **Work Orders** | Production > Work Orders | Assigned inspections |
| **Heat Map** | Quality > Heat Map | Visual defect analysis |

## Daily Workflow

### 1. Check Your Inbox

1. Navigate to **Inbox**
2. Review inspection assignments
3. Check pending approvals needing your input
4. Prioritize your work

### 2. Perform Inspections

For each inspection point:

1. Identify parts to inspect
2. Apply sampling (if applicable)
3. Perform measurements/checks
4. Record results
5. Disposition or pass parts

### 3. Document Issues

When problems are found:

1. Create quality report
2. Quarantine affected parts
3. Add annotations (if 3D model available)
4. Notify appropriate parties

## Performing Inspections

### At Inspection Steps

1. Open work order or find parts on Tracker
2. See parts waiting at inspection step
3. Determine sample size (per sampling rules)
4. Inspect selected parts
5. Record results

### Recording Measurements

1. Select part(s) to measure
2. Click **Record Measurements**
3. For each measurement:
   - Enter measured value
   - System calculates pass/fail
   - Note any observations
4. Save all measurements

### Measurement Best Practices

- Use calibrated equipment only
- Verify equipment is in calibration
- Record actual values (don't round inappropriately)
- Document measurement conditions if relevant

## Sampling Inspections

### When Sampling Applies

1. System shows required sample size
2. Select or identify sample parts
3. Inspect sample
4. Record results
5. System determines lot accept/reject

### AQL Sampling

Based on lot size and AQL level:
- System calculates sample size
- Accept number (Ac) and Reject number (Re) shown
- If defects ≤ Ac: Accept lot
- If defects ≥ Re: Reject lot

### After Lot Decision

**If Accepted:**
- Parts move forward
- Sample results recorded

**If Rejected:**
- Options: 100% inspect, scrap, RTV
- Create quality report
- Disposition required

## Creating Quality Reports (NCRs)

### When to Create

- Any non-conformance found
- Failed measurements
- Visual defects
- Material issues
- Customer complaints

### Creating the Report

1. Select affected part(s)
2. Click **Create Quality Report**
3. Fill in required fields:

| Field | What to Enter |
|-------|---------------|
| **Title** | Brief description of issue |
| **Error Type** | Category (Dimensional, Visual, etc.) |
| **Severity** | Minor, Major, Critical |
| **Description** | Detailed explanation |
| **Immediate Action** | What you did immediately |

4. Attach evidence (photos, data)
5. Submit

### Severity Guidelines

| Severity | Use When |
|----------|----------|
| **Minor** | Cosmetic, no functional impact |
| **Major** | Out of spec, affects function |
| **Critical** | Safety risk, regulatory violation |

## Annotating Defects

If 3D models are configured:

### Adding Annotations

1. Open Heat Map or Part Annotator
2. Select the part
3. Click location of defect on model
4. Fill in annotation details:
   - Error type
   - Severity
   - Description
5. Save

### Why Annotate

- Builds heat map data over time
- Visual communication of issues
- Pattern identification
- Training reference

## Managing Quarantine

### Parts You've Quarantined

1. Navigate to **Production** > **Dispositions**
2. See parts awaiting disposition
3. Provide additional information as needed
4. Await disposition decision

### Your Role in Disposition

- Provide inspection data
- Answer questions about findings
- Verify rework completion (if assigned)

## First Piece Inspection (FPI)

### Performing FPI

1. Receive first piece from operator
2. Perform all required measurements
3. Check against all specifications
4. Record results
5. Approve or reject

### FPI Decision

**If Pass:**
- Click **Approve FPI**
- Batch is released
- Production continues

**If Fail:**
- Click **Reject FPI**
- Enter rejection reason
- Operator must adjust and resubmit

## Incoming Inspection

For material from suppliers:

1. Identify lot to inspect
2. Apply incoming sampling rule
3. Perform inspection
4. Record results
5. Accept or reject lot

### Rejected Incoming Material

1. Create quality report
2. Mark lot status
3. Initiate RTV if appropriate
4. Notify purchasing/quality manager

## Supporting CAPA

You may be assigned CAPA tasks:

1. Check **Inbox** for CAPA tasks
2. Perform assigned investigation
3. Document findings
4. Complete task with evidence
5. Mark task complete

## End of Shift

### Handoff

1. Complete in-progress inspections
2. Document partial inspections
3. Note any pending items
4. Inform next shift

### Records

- Ensure all measurements saved
- Quality reports submitted
- Annotations complete

## Quick Reference

| Task | Steps |
|------|-------|
| Record measurement | Select part → Record Measurements → Enter values → Save |
| Create NCR | Select part → Create Quality Report → Fill form → Submit |
| Add annotation | Heat Map → Click location → Enter details → Save |
| Approve FPI | View FPI → Review data → Approve/Reject |
| Accept lot | Complete sampling → Record results → System calculates |

## What You CAN'T Do

Typically you cannot:

- Approve dispositions (QA Manager)
- Close CAPAs (QA Manager)
- Create orders
- Manage users

Escalate to QA Manager as needed.

## Troubleshooting

### Measurement equipment shows expired

- Don't use that equipment
- Select different calibrated equipment
- Report to calibration manager

### Can't find part to inspect

- Check filters
- Verify work order assignment
- Part may be at different step

### Quality report won't submit

- Check required fields
- Ensure parts are selected
- Verify you have permission

## Related Documentation

- [Quality Reports](../workflows/quality/quality-reports.md)
- [Recording Measurements](../workflows/tracking/measurements.md)
- [Sampling Rules](../workflows/quality/sampling.md)
- [Creating Annotations](../3d-models/annotations.md)
- [Heat Maps](../analysis/heatmaps.md)
