# Change Control

Change control governs how a manufacturing process is altered once it has been
approved — who proposed it, who authorised it, what actually changed, and what
happened to the jobs already running under the old version.

**Quality** > **Change Control**

!!! important "Change Control is the register; you raise a change in the process editor"
    **Quality → Change Control** lists PCRs, PCOs and PCNs. You do not create one
    there.

    Open the process in the **process editor**, use the header menu →
    **Propose Change**, and the approved process forks into a Draft with a PCR
    opened against it. From then on each record has its own page and its own
    actions.

## Simplified or regulated

**Admin > Settings > Change control mode** decides how much a change needs
before it takes effect. New organisations start in **Simplified**.

| | Simplified | Regulated |
|---|---|---|
| Approving a PCR | **Approve** on the PCR page approves it at once. The signature request raised at submit is cancelled | The PCR's approval request must collect every required signature first. **Approve** only confirms what the signatures decided |
| The PCO | Created already approved, ready to implement | Created as a draft for its author, then sent for its own signed approval |
| Who approves | Anyone holding the authoring permissions, including whoever submitted the PCR | Whoever the PCR and PCO approval templates assign, under their self-approval rules |

!!! warning "In Simplified mode one person can carry a change through alone"
    Nothing in Simplified mode stops the person who raised a change from
    approving and implementing it, and no signature is collected. If your
    quality system needs an independent, signed authorisation of process
    changes, switch to **Regulated**.

!!! warning "A tenant needs its change-control approval templates"
    Submitting a PCR looks up the tenant's **`PCR_APPROVAL`** template, and
    approving the PCO needs **`PCO_APPROVAL`**. Without them the step refuses
    with *"PCR_APPROVAL approval template not found. Please configure approval
    templates."*

    New tenants get these from the defaults. An older tenant may only have
    the retired **`ECO`** template, which nothing looks up — see
    [Approval Templates](../../admin/setup/approval-templates.md).

!!! note "Planned Feature"
    A **`PCN_RELEASE`** template is seeded and appears in the template list, but
    no stage looks it up — releasing a PCN today checks only that the PCN is in
    Draft and that the person releasing it is not the one who approved the PCO.
    An approval workflow on PCN release is planned. Until then, treat the
    segregation-of-duties check as the whole of the gate, and do not expect the
    template's approvers to be consulted.

## The three artifacts

A process change moves through up to three records, in order:

| Artifact | Stands for | Answers |
|----------|-----------|---------|
| **PCR** | Process Change Request | *Should* we change this process? |
| **PCO** | Process Change Order | Authorisation to actually make the change |
| **PCN** | Process Change Notice | Telling people it happened, and verifying it worked |

Each is numbered per tenant, per type, per year.

## PCR — Process Change Request

A proposal to change a specific approved process.

| Status | Meaning |
|--------|---------|
| **Draft** | Being written |
| **Submitted** | Sent for review |
| **Under Review** | Being evaluated |
| **Approved** | Accepted — a PCO can now authorise the work |
| **Rejected** | Declined |
| **Cancelled** | Withdrawn |

!!! note "Several open changes against one process are allowed"
    Nothing stops a second PCR being raised against a process that already has
    one in flight, and proposing a change deliberately permits multiple drafts.
    Conflicts between them are detected at **PCR approval** time, not prevented
    at creation — so two people can draft competing changes, and the second one
    approved is where the clash surfaces.

Submitting a PCR snapshots the in-flight work orders it would affect and records
the baseline process version, so the impact is captured at proposal time rather
than reconstructed later.

!!! important "What a PCR points at is fixed when it is proposed"
    The **target process** and the **draft** it forked are set at proposal and
    cannot be edited afterwards — not in Draft, not at any later status. An
    attempt is refused: *"the target and draft process are set when the change
    is proposed, and the diff is computed at submit."*

    On top of that, the record **locks once it leaves Draft**. So an approved
    PCR cannot be quietly repointed at a different process or a different draft
    after somebody signed it, which is the property that makes the approval
    mean anything.

    If the change turns out to be against the wrong process, cancel it and
    propose a new one. That leaves the mistake visible, which is the intent.

## PCO — Process Change Order

Authorisation to implement an approved PCR.

| Status | Meaning |
|--------|---------|
| **Draft** | Being prepared |
| **Approved** | Authorised |
| **In Implementation** | Being carried out |
| **Implemented** | Done |
| **Cancelled** | Abandoned |

Authoring a PCO creates a **draft process version** copying the current state.
That draft is edited in the normal process editor, and flipped to approved when
the PCO is implemented. So the change is staged and reviewable before it becomes
the live process.

### What happens to jobs already running

This is the part with real operational consequence. Implementing a PCO requires
deciding what to do with work orders already in flight under the old version:

| Disposition | Effect |
|-------------|--------|
| **Pending** | No decision made yet — the default |
| **Migrate All** | Every in-flight work order moves to the new version |
| **Migrate Selected** | Named work orders move; the rest stay |
| **Keep All** | All in-flight work finishes on the old version |

A [temporary change](#temporary-changes-deviations) offers no choice: it applies
only to the work orders it names.

The choice and its reason are recorded on the PCO, and each work order's move is
captured in the audit trail.

!!! tip "Migrating isn't automatically the right answer"
    Parts part-way through a routing may not be compatible with a changed
    process. **Keep All** is often correct for work already deep in production;
    **Migrate All** suits a change that fixes something wrong with the process
    itself.

## PCN — Process Change Notice

Distribution and effectiveness verification for an implemented PCO.

| Status | Meaning |
|--------|---------|
| **Draft** | Being prepared |
| **Released** | Distributed |
| **Closed** | Effectiveness verified |

Who gets told is handled by notification rules on the **PCN released** event
rather than an audience list on the notice itself — see
[Notification Rules](../../admin/setup/notification-rules.md).

## Temporary changes (deviations)

When the process has to depart from its approved form for a **bounded** piece of
work — a customer agrees to 27 Nm on two named jobs, say — raise it as a
**temporary change**. It goes through the same PCR, PCO and PCN, with three
differences:

- **It applies to the work orders it names, and nothing else.** Implementing it
  approves the revised version and moves those work orders onto it. The
  baseline stays current, so new work and every other job keep using the
  approved process. A temporary version is never offered for new work, and
  neither is a draft or superseded one.
- **It ends.** When you submit the PCR, switch on **Temporary change
  (deviation)** and give an **Ends on** date. The change is over when its work
  orders finish; the date is the backstop.
- **The customer's agreement is recorded on the PCR.** With **Customer
  notification required** on, a **Customer agreement** field records what was
  agreed.

Because the named work orders run a version whose spec *is* the agreed value, a
reading at that value passes. Nothing is quarantined, and no disposition opens
for work that was authorised in advance.

!!! warning "After the end date, the work stops"
    Once the date has passed, starting a step on one of its work orders is
    refused:

    > *PCR-… is a temporary change that ended on … Extend it through change
    > control, or move … back to the baseline, before more work is done.*

    This cannot be overridden by a supervisor. There are two ways on:

    - **Extend…** on the PCR page raises a new PCR, *"Extend PCR-… to
      <date>"*. It is submitted, approved and implemented like any other, and
      implementing it moves the end date. The new date must be later than the
      current one.
    - **Move back to baseline**, per work order, on the PCR's **Temporary
      change** card. Parts are re-pointed step by step, as in a migration. If a
      part is at a step the baseline does not have, the move is refused and the
      stranded parts are listed. The work order returns to the line's current
      approved version — the baseline, or its successor if a permanent change
      has since replaced it.

### How a temporary change shows

- **The register:** a **Temporary** badge with its end date and the number of
  work orders. It turns red once the date has passed. An extension reads
  *Extends PCR-…*.
- **The PCR page:** the badge, the end date, the customer agreement, and an
  amber **Temporary change** card listing its work orders — red, *Ended …*, once
  it has expired.
- **The process editor:** *"Temporary change PCR-… — in force until … for the
  work orders it names only. New work uses the current version."*
- **The PCN:** it says the change is temporary, gives the end date and lists
  the work orders, and states that the baseline remains current for all other
  work.

!!! note "Version numbers"
    A temporary version takes the next version number, as any revision does. A
    later permanent change from the same baseline takes that number too. The
    process's version history leaves temporary versions out, and the register
    and the editor label them temporary — so read a version by its PCR, not by
    its number alone.

!!! tip "Temporary change or concession?"
    A temporary change authorises a departure **before** the work. A
    [disposition](../quality/dispositions.md) — *Use As Is* or *Repair* —
    accepts nonconforming product **after** it was made. If you know in advance,
    raise the temporary change; the parts then never become nonconforming.

## Substeps ride the same process

Work instruction substeps version with their parent process, so changing them
follows this same path rather than a separate one. See
[Authoring Work Instructions](../dwi/authoring.md).

## Next Steps

- **[Digital Work Instructions](../dwi/overview.md)** - What substeps are
- **[Processes](../../admin/processes/overview.md)** - Defining processes
