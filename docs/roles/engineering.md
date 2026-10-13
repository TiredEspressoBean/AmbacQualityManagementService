# Engineering

**You define what the shop builds and how.** Part types, processes, routings,
work instructions, specifications and the limits parts live under.

!!! info "Authoring is the distinguishing permission"
    Most roles *use* master data. Engineering **writes** it. Nearly everything on
    this page is a thing nobody else on the floor can change.

## What you author

| Master data | Where |
|-------------|-------|
| **Part types and their specs** | [Part Types](../admin/setup/part-types.md) |
| **Processes, steps and the routing graph** | [Creating Processes](../admin/processes/creating.md), [Steps](../admin/processes/steps.md) |
| **Measurement definitions and step requirements** | [Measurements](../admin/processes/measurements.md) |
| **Digital work instructions (substeps)** | [DWI Authoring](../workflows/dwi/authoring.md) |
| **Raw materials** | [Supply](../workflows/supply/overview.md#materials) |
| **Work centres** | [Equipment](../admin/setup/equipment.md) |
| **Life limits** | [Life Tracking](../workflows/tracking/life-tracking.md) |
| **SPC control limits** | [SPC](../analysis/spc.md) |

!!! warning "Editing a work centre re-routes work"
    A work centre's **kind** is the surface discriminator — operator queue, QA
    inbox, receiving, outside processing. Changing it moves work to a different
    screen as surely as editing a routing does. It is authoring, not
    configuration.

## Routings are versioned, not edited

A process in use is not changed in place. New versions supersede old ones, and
the old version stays readable because parts were built to it.

!!! danger "Steps are shared across process versions on purpose"
    This is deliberate structural sharing, not a bug to normalise away. It is
    what lets date snapshots resolve. Treat a step as belonging to the process
    family, not to one version of it.

!!! important "Duplicate is how you revise"
    An approved process is **locked** — the flow editor says so: *"This process
    is locked. Duplicate to make changes."* You duplicate it, work in the Draft,
    and approve that. A Draft sitting beside the Approved version it will replace
    is the normal working state.

See [Processes Overview](../admin/processes/overview.md).

!!! important "A formal change starts in the process editor, not on the Change Control page"
    **Quality → Change Control** is the *register* — it lists PCRs, PCOs and PCNs.
    You **raise** one from the process editor: **Propose Change** forks a DRAFT
    process and opens a PCR against it.

    From there each record has its own page with its own actions — a PCR can be
    approved, rejected or cancelled; a PCO authored, approved, linked to affected
    work orders and implemented; a PCN released and closed with evidence.

!!! note "The page carries a stale banner"
    It still says creating and approving *"are all backend-built but not yet
    exposed in the UI"*. That text dates from June 2026 and was not updated when
    the actions shipped. The register looks empty in the demo because the tenant
    has **0 PCRs, 0 POs and 0 PCNs** — not because the feature is missing.

    See [Change Control](../workflows/change-control/overview.md).

## Cycle times are a planning input, not documentation

An operation with **no cycle time contributes no load**. The capacity heatmap
then shows free capacity that doesn't exist, and promised dates come out too
optimistic — a planning failure whose cause is a blank field on your routing
step.

!!! tip "Fix it on the routing step"
    Capacity Planning warns when orders contain operations with no cycle time.
    The fix belongs on the step, never in the planning view. See [Step
    Timings](../workflows/scheduling/setup.md#step-timings).

The same goes for **machine eligibility** (work on the wrong machine) and
**changeovers** (the solver interleaving jobs that shouldn't interleave).

## Life limits

A life limit is a definition plus its **link to a part type** — and the link *is*
the application. Unlinking stops a harvested component inheriting its core's
accumulated life, and drops a lot's shelf life to the default. So the link
travels with the definition rather than being incidental to it.

Removing a link from the part type page is a soft delete; linking the pair again
revives it.

## What you don't hold

| Not yours | Whose |
|-----------|-------|
| **Classify a document** | Document Controller, [QA Manager](qa-manager.md), Tenant Admin |
| **See the secret tier** | Document Controller, Tenant Admin |
| **Approve a disposition or a CAPA** | [QA Manager](qa-manager.md) |
| **Solve the schedule** | [Planner](planner.md), Production Manager |
| **Delete a work centre** | Manager tier |

!!! note "You can approve documents — if a template names you"
    There is no separate document-approval permission. You hold the general
    *respond to approval* right, and whether you are asked is decided by the
    approval template: if it names Engineering, by group or by name, you are an
    assigned approver and the **Submit Response** action is yours. If it doesn't,
    nobody can grant it with a permission. See [Document
    Approval](../workflows/documents/approval.md).

!!! note "Releasing work *is* yours"
    Release, unrelease and bulk release run on the same write right as the rest
    of your work-order editing, so you can release work orders. What you cannot
    do is **solve the schedule** — that is the Planner's.

## Next Steps

- [Processes Overview](../admin/processes/overview.md)
- [DWI Overview](../workflows/dwi/overview.md) — work instructions
- [Change Control](../workflows/change-control/overview.md)
- [Scheduling Setup](../workflows/scheduling/setup.md) — what the solver believes
- [Document Controller](document-controller.md) — who releases what you write
