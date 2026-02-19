# Operator Guide

This guide is for production floor operators who move parts through manufacturing steps and record production data.

## Your Role

As an Operator, you:

- Move parts through production steps
- Record measurements and data
- Flag issues when problems occur
- Track work order progress
- Use equipment for operations

## Getting Started

### First-Time Setup

1. Log in with credentials from your admin
2. Review the [Navigation Tour](../getting-started/navigation.md)
3. Familiarize yourself with the Tracker

### Your Main Pages

| Page | Location | Purpose |
|------|----------|---------|
| **Tracker** | Portal > Tracker | View all orders and move parts |
| **Inbox** | Personal > Inbox | Your assigned tasks |
| **Work Orders** | Production > Work Orders | Detailed work order view |

## Daily Workflow

### 1. Check Your Inbox

Start your shift by checking your inbox:

1. Navigate to **Inbox**
2. Review assigned tasks
3. Note any urgent items
4. Plan your work

### 2. View Orders on Tracker

1. Navigate to **Tracker**
2. Find orders you're working on
3. Expand to see step distribution
4. Identify parts ready to work

### 3. Work on Parts

For each operation:

1. Complete the physical work
2. Move parts forward in the system
3. Record any required data
4. Continue to next part

## Moving Parts Forward

### Passing Parts (Order Level)

1. Navigate to **QA Work Orders**
2. Find the order
3. Click the **Pass** button
4. Select the step you completed in the "Pass Part by Step" dialog
5. Click **Submit**
6. All parts at that step move to the next step

### Quality Reports (Individual Parts)

For individual parts needing measurements:

1. Find the part in the parts table
2. Click **Quality Report**
3. Fill in operator, machine, measurements, status
4. Submit the form

### Quick Tips

- Pass parts promptly after completing work
- Use the Quality Report for detailed measurement recording
- Check for any required quality data first

## Recording Measurements

When your step requires measurements:

### Recording Values

1. Select the part
2. Click **Record Measurements**
3. Enter measured values for each field
4. System shows pass/fail automatically
5. Click **Save**

### Reading Pass/Fail

| Indicator | Meaning |
|-----------|---------|
| Green ✓ | Measurement passed |
| Red ✗ | Measurement failed |
| Yellow ! | Warning (near limit) |

### If Measurement Fails

1. Verify your measurement is correct
2. Re-measure if uncertain
3. If confirmed fail, flag the part
4. Follow your supervisor's guidance

## Flagging Issues

When you find a problem:

### Quick Flag

1. Select the part
2. Click **Flag** or **Quarantine**
3. Select error type (Dimensional, Visual, etc.)
4. Add brief description
5. Submit

Part goes to quarantine immediately.

### When to Flag

- Part doesn't meet visual standards
- Measurement out of tolerance
- Damage discovered
- Process deviation occurred
- Anything that seems wrong

!!! tip "When in Doubt, Flag It"
    It's better to flag a potential issue than let a bad part continue.

## Using Equipment

If equipment tracking is enabled:

### Selecting Equipment

1. When moving parts, you may be prompted
2. Select the equipment you used
3. System records utilization

### Checking Calibration

Before using measurement equipment:
- Look for calibration status indicator
- Green = current calibration
- Red = overdue, don't use

## Work Orders

### Viewing Work Order Details

1. Navigate to **Production** > **Work Orders**
2. Find your assigned work order
3. See parts by step
4. View work instructions

### Accessing Work Instructions

1. Open the work order
2. Go to **Documents** tab
3. Click linked work instruction
4. Follow procedures

## First Piece Inspection (FPI)

If FPI is required at your step:

### The Process

1. Complete first part
2. Record all measurements
3. Submit for FPI review
4. Wait for approval
5. Once passed, continue with batch

### While Waiting

- Other parts are held automatically
- Continue setup verification
- Don't proceed until FPI passes

## End of Shift

### Handoff

1. Update part status for in-progress work
2. Note any issues in work order
3. Inform next shift of status

### Don't Leave Hanging

- Move completed parts forward
- Record all measurements
- Flag any open issues

## Common Tasks Quick Reference

| Task | Steps |
|------|-------|
| Move part forward | Select part → Move Forward → Confirm |
| Record measurement | Select part → Record Measurements → Enter values → Save |
| Flag issue | Select part → Flag → Select error type → Submit |
| View instructions | Open work order → Documents → Click instruction |

## What You CAN'T Do

As an operator, you typically cannot:

- Create or edit orders
- Approve dispositions
- Close CAPAs
- Upload documents
- Manage users

Contact your supervisor for these actions.

## Troubleshooting

### "Cannot move forward"

Check for:
- Required measurements not recorded
- Pending approval
- FPI required but not passed
- Part in quarantine

### "Permission denied"

- You may not have access to this action
- Contact supervisor or admin

### Part not showing

- Check filters on Tracker
- Verify correct work order
- Part may be at different step

## Getting Help

- **Your Supervisor**: Process questions, permissions
- **Quality**: Measurement issues, defects
- **IT/Admin**: Login issues, system problems

## Related Documentation

- [Tracker Overview](../workflows/tracking/tracker-overview.md)
- [Moving Parts](../workflows/tracking/moving-parts.md)
- [Recording Measurements](../workflows/tracking/measurements.md)
- [Flagging Issues](../workflows/tracking/flagging-issues.md)
- [First Piece Inspection](../workflows/work-orders/fpi.md)
