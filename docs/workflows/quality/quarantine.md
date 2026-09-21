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
| **Quality report** | NCR created for part |
| **Customer complaint** | Return or field issue |
| **Suspect material** | Material lot under investigation |
| **Process deviation** | Unauthorized change occurred |

## Putting Parts in Quarantine

### Automatic Quarantine

Some events automatically quarantine parts:

- Failed measurement (if configured)
- Quality report creation
- Incoming inspection failure

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

A quality report against a part also puts it into quarantine — see
[Quality Reports](quality-reports.md).

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
3. Filter by:
   - Error type
   - Date quarantined
   - Age in quarantine
   - Awaiting disposition

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

## Quarantine Time Tracking

The system tracks:

- **Date quarantined**
- **Time in quarantine** (aging)
- **Date released**
- **Total quarantine time**

### Quarantine Aging Reports

Identify parts sitting too long:

| Age | Status |
|-----|--------|
| 0-3 days | Normal |
| 4-7 days | Attention needed |
| 7+ days | Escalation required |

Long quarantine times indicate:

- Investigation delays
- Decision bottlenecks
- Resource constraints

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

## Quarantine Dashboard

The Quality Dashboard shows:

- **Current quarantine count**
- **Quarantine by error type** (Pareto)
- **Aging breakdown**
- **Trend over time**

## Bulk Quarantine Actions

For efficiency:

1. Select multiple quarantined parts
2. If same issue, bulk disposition
3. Apply same disposition to all
4. Single approval (if required)

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
