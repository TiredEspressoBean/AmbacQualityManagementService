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

See [Processes Overview](../admin/processes/overview.md) and [Change
Control](../workflows/change-control/overview.md).

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
| **Approve a document** | [Document Controller](document-controller.md), QA Manager |
| **Classify a document / see the secret tier** | Document Controller |
| **Approve a disposition or a CAPA** | [QA Manager](qa-manager.md) |
| **Release work, solve the schedule** | [Planner](planner.md), Production Manager |
| **Delete a work centre** | Manager tier |

!!! note "Authoring a spec is not approving it"
    You can write a process, a routing and a measurement requirement. Whether the
    controlled document describing it is *released* runs through document
    control. Separating those is most of what an auditor is checking.

## Next Steps

- [Processes Overview](../admin/processes/overview.md)
- [DWI Overview](../workflows/dwi/overview.md) — work instructions
- [Change Control](../workflows/change-control/overview.md)
- [Scheduling Setup](../workflows/scheduling/setup.md) — what the solver believes
- [Document Controller](document-controller.md) — who releases what you write
