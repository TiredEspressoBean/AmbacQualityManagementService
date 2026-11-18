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
| You just finished the step and then saw the problem | **Flag** beside your last finished step on Home — it opens *Record Inspection* ([inspection record](../quality/quality-reports.md#recording-an-inspection)) with the part, step and you filled in |
| The part is already past that step, or you're not the one running it | **Quarantine** it from the parts list, or **Raise NCR** from the same toolbar to hold it and say what's wrong |
| Several parts share one problem | Tick them on the work order's control page and **Raise NCR**: one [NCR](../quality/ncrs.md#raising-an-ncr-by-hand) over all of them |
| A machine or resource is down | **Report…** downtime on the work order |
| The problem is the process or the whole lot | Raise a **disposition** or a **CAPA** — **Report…** links to both |
| **You can't run the job at all** | Tell your lead |

### In the step player (the in-process path)

If the step has an **inspection point** substep, that is where a bad result
belongs. Record the quality status, the defects against their error types, and
any signatures the substep asks for, then confirm.

You do not raise anything separately: an inspection point's captures write an
inspection record as well as the substep record, and a Fail puts the part on an
[NCR](../quality/ncrs.md) by itself. This is the path that keeps the finding
attached to the work that produced it.

### Quarantining from the parts list

To hold parts that are already past the step, or that you are not running
yourself:

1. Open the work order's **control** page
2. **Tick the parts** in the parts list
3. Click **Quarantine** in the actions that appear

The same selection also offers **Rework**, **Scrap**, **Split selection…** and
**Raise NCR**. Quarantine holds the parts; it does not by itself say what is
wrong with them. **Raise NCR** holds them *and* says what's wrong, with a
decision for each part: see [Raising an NCR by
hand](../quality/ncrs.md#raising-an-ncr-by-hand).

!!! warning "Quarantine acts on the selection, not the row you clicked"
    These are bulk actions on every ticked part. Check the selection before
    clicking — quarantining a lot you did not mean to select stops all of it.

### Reporting downtime on the work order

When a machine or resource is down:

1. Open the work order in the **WO Control Center** or its control page
2. Click **Report…** and choose **Downtime (equipment / resource)**
3. Pick the **equipment**, a **category**, and a **reason** (required, up to 200
   characters); add a description if it helps
4. In the Control Center, optionally pick the **work order** it affects — from a
   work order's own page it is recorded against that work order
5. **Record downtime**

The event starts now and stays open in the Exceptions list until someone
resolves it there.

!!! note "Quarantine and CAPA open their own forms"
    **Report…** also lists **Quarantine** and **CAPA**, but it does not raise
    either itself — each shows a link to the form that does: the disposition
    form, or the CAPA form. To hold specific parts, quarantine them from the
    parts list as above.

    Equipment whose type has **Track downtime** turned off is not offered.

### Raising it after the fact

For something found later — a customer complaint, an audit finding, a problem
noticed off the floor — record the inspection under **Quality** > **Inspection
Records**, or raise the NCR directly under **Quality** > **NCRs** > **Raise
NCR**. See [Inspection Records](../quality/quality-reports.md) and
[NCRs](../quality/ncrs.md).

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

Containment is recorded on the NCR, once for every part it covers. A Critical
or Major NCR's decisions can't close until it is. See
[NCRs: Containment](../quality/ncrs.md#containment).

## Linking Issues

Connect related issues:

### Link to CAPA

Whether a CAPA is needed is decided on the NCR's **CAPA** card: **Raise CAPA**
there opens one with the NCR's inspection records linked, and the
investigation is tracked on the CAPA. See [NCRs: CAPA](../quality/ncrs.md#capa).

!!! note "The two close independently"
    A linked CAPA does **not** hold the disposition open, and the disposition
    does not hold the CAPA open. You can close out the part — rework it,
    re-inspect it, close its disposition — while the CAPA investigating *why* it
    happened runs on for weeks. That is normal: one is about this part, the
    other is about the cause.

## Who gets told

Notifications are **rule-driven**, and only two quality rules ship by default:

| Event | Goes to | Channels |
|-------|---------|----------|
| An NCR is opened | **QA Manager** group | In-app and email |
| A step fails | **QA Manager** and **QA Inspector** groups | In-app and email |

!!! warning "Severity does not change who is told"
    There is **no severity-based routing**. A Critical nonconformance notifies
    exactly the same people as a Minor one, and no supervisor is alerted on the
    strength of severity alone. Nor is there a per-user notification preference
    deciding this — the rules are tenant-level and your administrator owns them.

    If your procedure expects a Critical to escalate differently, that is a
    [notification rule](../../admin/setup/notification-rules.md) somebody has to
    write. Until then, severity is a label a reader acts on, not a trigger.

**Do not rely on a notification to hand work over.** Check the work order's
exceptions, the Dispositions list or your inbox rather than assuming someone was
paged.

## What Happens Next

After flagging:

```
Issue Flagged → Quarantine → Investigation → Disposition → Resolution
                    │
                    └── CAPA (if needed)
```

1. **Quarantine**: the part is held. It can never ship, and work can't start
   on it at its next step. If its current step was already under way, it stays
   at that step until its disposition is decided
2. **Investigation**: Quality reviews the part's [NCR](../quality/ncrs.md)
3. **Disposition**: the decision — Use As Is, Rework, Repair, Scrap or Return to
   Supplier — one per part, made from the NCR or on the part's own disposition
4. **Resolution**: the part is processed per the decision, then the disposition
   is closed
5. **CAPA**: corrective action, *if* the pattern warrants it — most
   nonconformances do not become CAPAs, and declining is itself a recorded
   decision with a reason

See [Dispositions](../quality/dispositions.md) for disposition workflow.

## Permissions

| Permission | Allows |
|------------|--------|
| `add_qualityreports` | Record inspections |
| `view_qualityreports` | View inspection records |
| `change_qualityreports` | Edit inspection records that are still Pending Review |
| `add_ncr` | Raise an NCR, add parts to one. Held by everyone who can flag a problem, operators included |

## Next Steps

- [Inspection Records](../quality/quality-reports.md) - Recording inspection results
- [NCRs](../quality/ncrs.md) - The nonconformance and its parts
- [Quarantine](../quality/quarantine.md) - Managing held parts
- [Dispositions](../quality/dispositions.md) - Making decisions
- [CAPA Overview](../capa/overview.md) - Corrective actions
