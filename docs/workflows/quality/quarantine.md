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

1. Select part(s) in Tracker or part list
2. Click **Quarantine** or **Hold**
3. Select reason/error type
4. Add notes
5. Submit

Parts immediately show quarantine status.

## Quarantine Status

Quarantined parts display:

- **Yellow status badge** on Tracker
- **Quarantine indicator** in part detail
- **Cannot pass** to next step
- **Appear in quarantine queue**

## Quarantine Queue

View all quarantined parts:

1. Navigate to **Production** > **Dispositions** (or Quarantine)
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

| Event | Recipients |
|-------|------------|
| Part quarantined | Quality team |
| Multiple parts quarantined (same issue) | QA Manager |
| Quarantine aging > threshold | Supervisor |
| Critical severity quarantine | Management |

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

## Best Practices

1. **Quarantine immediately** - Don't let suspect parts continue
2. **Segregate physically** - Prevent accidental use
3. **Document clearly** - What's wrong, where found
4. **Investigate promptly** - Reduce aging
5. **Decide and execute** - Clear the queue

## Next Steps

- [Dispositions](dispositions.md) - Making decisions
- [Quality Reports](quality-reports.md) - Documenting issues
- [CAPA Overview](../capa/overview.md) - Corrective actions
