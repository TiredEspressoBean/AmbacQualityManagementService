# Quarantine Management

Quarantine holds suspect or non-conforming parts for investigation and disposition. This guide covers quarantine workflow.

## What is Quarantine?

**Quarantine** is a part status (QUARANTINED) that:

- **Holds** parts from production flow
- **Segregates** them for investigation
- **Prevents** advancement at steps with `block_on_quarantine` enabled
- **Requires** disposition workflow to release

## Quarantine Triggers

Parts enter quarantine when:

| Trigger | Description |
|---------|-------------|
| **Failed inspection** | Measurement out of tolerance |
| **Visual defect** | Operator flags issue |
| **Quality report** | NCR **created** with result FAIL — see below; failing it later does not |
| **Customer complaint** | Return or field issue |
| **Suspect material** | Material lot under investigation |
| **Process deviation** | Unauthorized change occurred |

## Putting Parts in Quarantine

### Automatic Quarantine

A part is quarantined when a quality report is **created** with its result already
**FAIL**. A report created as PASS or PENDING leaves the part where it is.

!!! warning "Setting an existing report to FAIL does not quarantine the part"
    The quarantine runs once, as the report is created. Editing a PENDING report
    to FAIL afterwards does **not** move the part — but it *does* open a
    disposition, because that runs from a different trigger that fires on every
    save.

    So a report failed after the fact leaves you with a disposition against a
    part still sitting in progress. If you mean to quarantine, set the result
    when you create the report.

### Manual Quarantine

There are two manual routes, and they record different things.

**Holding specific parts** — from the work order's control page, tick the parts
in the list and click **Quarantine**. This sets their status and nothing more:
it holds the material but does not say what is wrong with it, so follow it with
a quality report or a disposition.

!!! warning "It acts on the whole selection"
    **Quarantine**, like **Rework** and **Scrap** beside it, applies to every
    ticked part rather than one row. Check the selection first.

**Raising it as an exception** — when the problem belongs to the work order
rather than to particular parts:

1. Open the work order in the **WO Control Center** or its control page
2. Click **Report…** to open the **Report exception** dialog
3. Choose type **Quarantine (quality hold)**

   The same dialog also raises **Downtime (equipment / resource)** and
   **CAPA (corrective action)** — the type routes the event to the right
   record.
4. Add the reason and notes
5. Submit

A **failed** quality report against a part also puts it into quarantine; a
passing or pending one does not — see [Quality Reports](quality-reports.md).

Parts immediately show quarantine status.

## Quarantine Status

Quarantined parts display:

- **Yellow status badge** on Tracker
- **Quarantine indicator** in part detail
- **Cannot pass** to next step
- **Appear in quarantine queue**

## Quarantine Queue

View all quarantined parts:

1. Navigate to **Quality** > **Dispositions** (or Quarantine)
2. See list of held parts
3. Filter by error type, or by whether a disposition is still awaited

Quarantine is a part **status** and nothing more — no timestamp is written when
a part enters or leaves it. There is therefore nothing to filter or sort by date
quarantined or age in quarantine.

## Investigating Quarantine

For each quarantined part:

1. **Review details** - What's the issue?
2. **Check history** - When did it occur?
3. **Examine part** - Physical inspection
4. **Gather data** - Measurements, photos
5. **Determine cause** - Root cause analysis
6. **Decide disposition** - What to do with it

## Releasing from Quarantine

Parts leave quarantine through disposition:

### Use As Is
Part is acceptable, release to continue production.

### Rework
Route to rework step, then re-inspect.

### Scrap
Part is scrapped, removed from active inventory.

### RTV
Part returns to vendor.

See [Dispositions](dispositions.md) for details.

## Quarantine Location

For physical segregation:

- Assign quarantine **bin location**
- Track physical movement
- Ensure separation from good parts

Best practice: Designated quarantine area with controlled access.

## Lot Quarantine

Quarantine entire material lots:

1. Identify suspect lot
2. Search for all parts from lot
3. Bulk quarantine
4. Investigate
5. Disposition by lot

This is common for:

- Incoming material issues
- Supplier quality escapes
- Recall situations

## Quarantine Notifications

Notifications are **rule-driven and configurable** — who gets told what is
decided by this tenant's notification rules, not by the event itself. Any rule
can be edited, disabled or deleted, so treat routing as something to check
rather than something to rely on. See [Notification
Rules](../../admin/setup/notification-rules.md).

No quarantine-specific routing is seeded by default. The related rule that
does ship sends **NCRs to the QA Manager**, so a quarantine raised through a
quality report is usually covered while one raised directly is not.

!!! warning "Do not rely on a notification to hand work over"
    Quarantined parts hold their lot. If a disposition needs deciding, check
    the work order's exceptions or the Dispositions list rather than assuming
    someone was paged.

## Where the quarantine count lives

The **Home** page carries an *In quarantine* count. The Quality Dashboard does
not — its tiles are Open CAPAs, Overdue, Pending Verification, Closed, Quick
Actions and My Tasks. There is no quarantine Pareto, aging breakdown or trend
chart anywhere.

## A whole load quarantined at once

There is no multi-select bulk disposition — you cannot tick several quarantined
parts and decide them together. Each disposition is decided on its own record.

What does happen in bulk is **containment**, and the system starts it, not you: if
a shared batch cycle fails — one ultrasonic wash, one heat-treat load — every part
that rode through it is quarantined together and a single disposition is opened
for the batch. That is one decision covering the load because they genuinely share
one event, not a convenience for grouping unrelated parts.

See [Running Work Instructions](../dwi/running.md#per-part-work-and-shared-cycles)
for how shared cycles differ from per-part work.

## Permissions

Quarantine is implemented as a part status (QUARANTINED), so standard part permissions apply:

| Permission | Allows |
|------------|--------|
| `view_parts` | View quarantined parts |
| `change_parts` | Change part status to/from quarantine |
| `approve_disposition` | Approve disposition decisions |
| `close_disposition` | Close dispositions and release parts |

## Next Steps

- [Dispositions](dispositions.md) - Making decisions
- [Quality Reports](quality-reports.md) - Documenting issues
- [CAPA Overview](../capa/overview.md) - Corrective actions
