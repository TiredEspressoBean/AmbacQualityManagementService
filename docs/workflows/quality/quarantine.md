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

**Raising it as a disposition** — when the problem belongs to the work order
rather than to particular parts, open the **disposition form**. The work
order's **Report…** dialog offers **Quarantine (quality hold)** as a type, but
only as a link to that form; it does not hold anything by itself.

A **failed** quality report against a part also puts it into quarantine; a
passing or pending one does not — see [Quality Reports](quality-reports.md).

Parts immediately show quarantine status.

## Quarantine Status

Quarantined parts display:

- **Yellow status badge** on Tracker
- **Quarantine indicator** in part detail
- **Appear in quarantine queue**
- **Cannot ship** — always, from anywhere

!!! warning "Quarantine does not stop a part advancing unless the step says so"
    This is the one most people assume wrongly. Blocking is a **per-step
    opt-in**: a step only refuses to let a quarantined part past when its
    **Block on quarantine** flag is set, and that flag is **off by default**.

    On a routing where nobody armed it, a quarantined part keeps moving from
    step to step. What quarantine always does is hold the part out of
    **shipping** — it can never leave the building — and put it on the
    dispositions queue.

    If your procedure expects a quarantined part to stop dead at the next
    operation, check the flag on the steps that matter. It is authored on the
    step, so it is Engineering's to set.

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

Parts leave quarantine through a disposition. There are **five**, and the
decision needs `approve_disposition` — or a co-signature from someone who holds
it:

| Decision | What happens to the part |
|----------|--------------------------|
| **Rework** | Back for correction to **full** conformance, then re-inspected |
| **Repair** | Corrected, but with a **known accepted deviation** — needs a recorded approval reference |
| **Scrap** | Terminal. Scrap verification records the method, so the part cannot re-enter the supply chain |
| **Use As Is** | Accepted as it stands — needs a recorded approval reference. The part returns to **In progress** at the step it was already at, not to the next one |
| **Return to Supplier** | Goes back to the vendor. The **RTV sheet** travels with the goods |

!!! note "Rework and Repair only re-route a part that is still held"
    If the part has already moved on, the disposition is recorded as a paper
    record of what was authorised and the part's status is left alone — it does
    not get dragged backwards.

See [Dispositions](dispositions.md) for the full detail.

## Quarantine Location

For physical segregation:

- Assign quarantine **bin location**
- Track physical movement
- Ensure separation from good parts

Best practice: Designated quarantine area with controlled access.

## A suspect material lot

When the problem is the material rather than one part — an incoming issue, a
supplier escape, a recall — the question is *which units did this lot go into?*

1. Open the lot and read its **forward trace**: the parts each step drew it
   into, up through assemblies to the work order, order and customer
2. Quarantine those parts from the work order's control page, ticking them in
   the list
3. Investigate

!!! note "There is still no bulk disposition"
    You can quarantine many parts in one action. **Deciding** them is one record
    at a time — see [A whole load quarantined at once](#a-whole-load-quarantined-at-once)
    below for the single exception, which the system raises itself.

The lot itself also has its own hold and reject routes at receiving, which are
separate from part quarantine — see [Supply](../supply/overview.md).

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

Quarantine is a part **status**, not a record of its own, so putting a part into
it is an ordinary part write — by default **every staff role can do it**,
including an Operator. That is deliberate: anyone who sees a problem should be able to stop
the part.

The narrow permissions are the ones that decide what happens next:

| Permission | Allows | Held by |
|------------|--------|---------|
| `view_parts` | See quarantined parts | Every staff role |
| `add_parts` / `change_parts` | Put a part into or out of quarantine | Every staff role |
| `approve_disposition` | **Decide** what happens to it | QA Manager, Tenant Admin |
| `close_disposition` | **Close** the disposition once resolved | QA Inspector, Shift Lead, Production Manager, QA Manager, Tenant Admin |

*Held by* is the groups that hold it when an organisation is created. Group permissions can be changed, so check your own in [Roles & Groups](../../admin/users/roles.md).

!!! note "Holding is open; releasing is not"
    Anyone can quarantine. Getting a part *out* means a disposition, and
    deciding one is material review authority — so the part stays held until
    quality acts, whoever put it there.

## Next Steps

- [Dispositions](dispositions.md) - Making decisions
- [Quality Reports](quality-reports.md) - Documenting issues
- [CAPA Overview](../capa/overview.md) - Corrective actions
