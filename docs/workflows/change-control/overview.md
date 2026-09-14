# Change Control

Change control governs how a manufacturing process is altered once it has been
approved — who proposed it, who authorised it, what actually changed, and what
happened to the jobs already running under the old version.

**Quality** > **Change Control**

!!! warning "The UI is read-only today"
    The Change Control page **reads** existing records. Creating a PCR,
    approving it, implementing it, and releasing or closing a notice are all
    built in the backend but not yet exposed in the UI.

    In the meantime a change is opened from the **process editor**, and the
    remaining transitions are driven through the API or by an administrator.

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

!!! note "One open change per process"
    A process can have at most **one** open PCR at a time (Draft, Submitted,
    Under Review, or Approved). If you can't open a change, check whether one is
    already in flight against that process.

Submitting a PCR snapshots the in-flight work orders it would affect and records
the baseline process version, so the impact is captured at proposal time rather
than reconstructed later.

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

## Substeps ride the same process

Work instruction substeps version with their parent process, so changing them
follows this same path rather than a separate one. See
[Authoring Work Instructions](../dwi/authoring.md).

## Next Steps

- **[Digital Work Instructions](../dwi/overview.md)** - What substeps are
- **[Processes](../../admin/processes/overview.md)** - Defining processes
