# Quarantine Management

Quarantine holds suspect or non-conforming parts for investigation and disposition. This guide covers quarantine workflow.

## What is Quarantine?

**Quarantine** is a part status (QUARANTINED) that:

- **Holds** parts from production flow
- **Segregates** them for investigation
- **Refuses** any start except a re-capture of a voided result: work on the part comes through its disposition
- **Requires** disposition workflow to release

## Quarantine Triggers

Parts enter quarantine when:

| Trigger | Description |
|---------|-------------|
| **Failed inspection** | Measurement out of tolerance |
| **Visual defect** | Operator flags issue |
| **Inspection record** | A record reaching FAIL, whether created as FAIL or edited to it |
| **Customer complaint** | Return or field issue |
| **Suspect material** | Material lot under investigation |
| **Process deviation** | Unauthorized change occurred |

## Putting Parts in Quarantine

### Automatic Quarantine

A part is quarantined when an inspection record against it reaches **FAIL**:
created as FAIL, edited to FAIL, a reading out of spec, an inspector's FAIL on an
inspection, or a failed first piece. A record at PASS or PENDING leaves the part
where it is. The part's history records the status change and who made it.

The failure also puts the part on an [NCR](ncrs.md), with a disposition for the
part, **unassigned**. It waits on the QA home page under *Unassigned
dispositions* until someone takes it with **Take it**. See [Dispositions](dispositions.md#where-a-disposition-comes-from).

### Manual Quarantine

There are two manual routes, and they record different things.

**Holding specific parts** — from the work order's control page, tick the parts
in the list and click **Quarantine**. This sets their status and nothing more:
it holds the material but does not say what is wrong with it. To hold the parts
*and* say what's wrong in one go, use **Raise NCR** from the same toolbar
instead: it opens [an NCR](ncrs.md#raising-an-ncr-by-hand) with the ticked parts
filled in.

!!! warning "It acts on the whole selection"
    **Quarantine**, like **Rework** and **Scrap** beside it, applies to every
    ticked part rather than one row. Check the selection first.

**Raising it as a disposition** — when the problem belongs to the work order
rather than to particular parts, open the **disposition form**. The work
order's **Report…** dialog offers **Quarantine (quality hold)** as a type, but
only as a link to that form; it does not hold anything by itself.

A **failed** inspection record against a part also puts it into quarantine; a
passing or pending one does not — see [Inspection Records](quality-reports.md).

Parts immediately show quarantine status.

## Quarantine Status

Quarantined parts display:

- **Quarantined** status on the part's page and in the work order's parts
  (the Tracker shows orders, not parts, so it doesn't show this)
- **Held — DISP-… open** on the operator's Home, for a part they started
- **Appear in quarantine queue**
- **Cannot ship** — always, from anywhere

!!! warning "A quarantined part can't be started"
    Starting work on it is refused, naming its disposition: *"… is quarantined —
    DISP-… decides what happens to it; work it from there."* Rework reaches the
    part through the disposition, not through a fresh start. The one exception
    is re-capturing a result that was voided.

    A part quarantined **while its step was already under way** can't move on
    from that step either: completing it is refused with *Part held — DISP-…
    decides it*, QA Manager and QA Inspector are called (*Held at &lt;step&gt;:
    &lt;part&gt; — waiting on the part's disposition*), and where the lot moves
    together, it holds the lot there. Deciding the disposition releases it:
    rework or repair splits it off down the step's Fail branch (or to the
    Rework step), and use-as-is lets it carry on along the pass path (the
    operator's Home reads *Cleared by QA — complete it*, and they complete the
    step). That's the step's **Quarantine hold** gate, on
    every step unless Engineering removed it. See
    [Gates](../../admin/processes/steps.md#gates).

## Quarantine Queue

View all quarantined parts:

1. Navigate to **Quality** > **Quarantined Parts**
2. See every part with the **Quarantined** status (parts awaiting QA or rework
   have their own queues). Home's *Parts in quarantine* and *Quarantined parts*
   counts are the same number
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

Parts leave quarantine through a disposition. While a part has an open
disposition, its status can't be changed by editing the part or by the bulk
status action: *"&lt;part&gt; has an open disposition (&lt;DISP-…&gt;); its
status changes through that disposition."* The disposition's decision moves it.

There are **five** decisions, and the decision needs `approve_disposition` — or
a co-signature from someone who holds it:

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

### Tagging it

A part's ID label carries no status — it stays with the part for life, and a
status on it would go stale. What marks a held part on the floor is a **Hold
tag**: a printed page to attach to the part or its container.

**Hold tag** is on each held row of **Quarantined Parts** (a quarantined part, or
one needing rework), and beside **NCR Report** on a disposition while its part is
held. Its heading says what state the item is in:

| Heading | When | Under it | Box at the foot |
|---------|------|----------|-----------------|
| **QUARANTINE** | Awaiting its disposition | *DO NOT USE UNTIL RELEASED* | **Release** — *Released by*: name, date, disposition or reason released |
| **HOLD** | On hold, or needing rework | *DO NOT USE UNTIL RELEASED* | **Release**, as above |
| **REJECTED** | Dispositioned scrap | *DO NOT USE — TO BE RETURNED OR SCRAPPED* | **Closure** — *Returned / scrapped by*: name, date, RTV or scrap reference |

A rejected item is never released — it ends when it leaves — so its tag closes
with who sent it back or scrapped it. Every tag also carries:

- **Item** — part type, serial, quantity, location, work order and step
- **Why it is held** — the NCR number and its description, the inspection
  records and the finding
- **Placed by** and **Placed** — from the record's history

A part that isn't held has no tag to print: *&lt;serial&gt; isn't held
(&lt;status&gt;) — nothing to tag.* Like every report it needs `export_data`.

## A suspect material lot

When the problem is the material rather than one part — an incoming issue, a
supplier escape, a recall — the question is *which units did this lot go into?*

1. Open the lot and read its **forward trace**: the parts each step drew it
   into, up through assemblies to the work order, order and customer
2. Quarantine those parts from the work order's control page, ticking them in
   the list
3. Investigate

!!! tip "Decide them together on one NCR"
    To decide the suspect parts together, put them on one NCR: tick them on the
    work order's control page and **Raise NCR**, or **Add parts** to an open
    NCR. On the NCR, **Decide all waiting** (or **Decide N chosen**) records
    each part's decision in one go. See [NCRs](ncrs.md#parts-and-decisions).

The lot itself also has its own hold and reject routes at receiving, which are
separate from part quarantine — see [Supply](../supply/overview.md).

## Quarantine Notifications

Notifications are **rule-driven and configurable** — who gets told what is
decided by this tenant's notification rules, not by the event itself. Any rule
can be edited, disabled or deleted, so treat routing as something to check
rather than something to rely on. See [Notification
Rules](../../admin/setup/notification-rules.md).

No quarantine-specific routing is seeded by default. The related rule that
does ship sends each **NCR opened to the QA Manager**, so a quarantine that came
with an NCR is usually covered, while a part quarantined directly from the
control page, without an NCR, is not.

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

When a shared batch cycle fails (one ultrasonic wash, one heat-treat load), the
system raises one [NCR](ncrs.md) over the load, marked *Failed batch load*. The
parts from that load **still in production** (in progress, awaiting QA, ready for
their next step, or at an outside process) are quarantined together, each with
its own disposition under the NCR.

Parts from the load that had already moved on (completed, shipped, scrapped)
aren't held. On the NCR they read *Already past the step*, and each gets a
decision kept as a record, so the NCR can close.

Decide the load from the NCR's page like any NCR: **Decide all waiting**, or
tick parts and **Decide N chosen**. Each part's decision goes on its own
disposition, and from there it behaves like any part's decision: Scrap scraps
it, Rework sends it down the step's Fail branch or to the Rework step, Use As Is
needs its approval reference. Parts not chosen stay held until they're decided.
Once every part has a decision: *"Everything on NCR-… already has a decision;
change a part's decision on its own disposition."* The NCR closes when every
decision under it is closed.

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
| `add_parts` / `change_parts` | Put a part into quarantine; change its status while it has no open disposition | Every staff role |
| `approve_disposition` | **Decide** what happens to it | QA Manager, Tenant Admin |
| `close_disposition` | **Close** the disposition once resolved | QA Inspector, Shift Lead, Production Manager, QA Manager, Tenant Admin |

*Held by* is the groups that hold it when an organisation is created. Group permissions can be changed, so check your own in [Roles & Groups](../../admin/users/roles.md).

!!! note "Holding is open; releasing is not"
    Anyone can quarantine. Getting a part *out* means a disposition, and
    deciding one is material review authority — so the part stays held until
    quality acts, whoever put it there.

## Next Steps

- [NCRs](ncrs.md) - What's wrong, and deciding many parts together
- [Dispositions](dispositions.md) - Making decisions
- [Inspection Records](quality-reports.md) - Documenting inspection results
- [CAPA Overview](../capa/overview.md) - Corrective actions
