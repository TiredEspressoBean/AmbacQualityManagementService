# Engineering Training Guide

**Duration:** 4-5 hours
**Prerequisites:** None, though Operator training helps you see how your routings get run
**Goal:** Learn to author part types, processes, routings, work instructions and
specifications — and to understand what each one does downstream

!!! note "Role Name"
    This training is for the **Engineering** role in the system.

!!! info "Demo Environment Login"
    **Email:** admin@demo.ambac.com
    **Password:** `demo123`

    The demo has no account whose only group is Engineering. Alex Demo is
    **Tenant Admin**, which holds every authoring permission plus more — so
    everything here works, and some screens show more than this guide describes.

!!! warning "Authoring is the distinguishing permission"
    Most roles *use* master data. Engineering **writes** it. Nearly everything in
    this guide is something nobody else on the floor can change — and a mistake
    propagates to every unit built afterwards.

---

## Module 1: What You Own

### Learning Objectives

1. Name the master data Engineering authors
2. Explain why authoring is separated from approving

### 1.1 The surfaces

| Master data | Where |
|-------------|-------|
| Part types and their specs | [Part Types](../admin/setup/part-types.md) |
| Processes, steps and the routing graph | [Creating Processes](../admin/processes/creating.md) |
| Measurement definitions and step requirements | [Measurements](../admin/processes/measurements.md) |
| Digital work instructions (substeps) | [DWI Authoring](../workflows/dwi/authoring.md) |
| Raw materials | [Supply](../workflows/supply/overview.md#materials) |
| Work centres | [Equipment](../admin/setup/equipment.md) |
| Life limits | [Life Tracking](../workflows/tracking/life-tracking.md) |
| SPC control limits | [SPC](../analysis/spc.md) |

### 1.2 Authoring is not approving

!!! note "You write the spec; document control releases it"
    You can write a process, a routing and a measurement requirement. Whether the
    controlled document describing it is *released* runs through
    [Document Controller](../roles/document-controller.md) and QA Manager.

    Separating those is most of what an auditor is checking.

You also do **not** hold: approving a disposition or CAPA, classifying documents,
releasing work, or deleting a work centre.

### Knowledge Check: Module 1

1. You've authored a new routing. Can you release the drawing that describes it?
2. Who approves a nonconformance against a part you specified?

---

## Module 2: Routings Are Versioned

### Learning Objectives

1. Create a new process version rather than editing in place
2. Explain why steps are shared across versions

### 2.1 Never edit a process in use

A process in use is not changed in place. New versions supersede old ones, and
the old version stays readable **because parts were built to it**. That is the
whole point: an as-built record must resolve against the routing that was in
force at the time.

### 2.2 Steps are shared across versions

!!! danger "This is deliberate structural sharing, not a bug"
    Steps belong to the process *family*, not to one version of it. It is what
    lets date snapshots resolve.

    Do not "fix" this by deep-copying steps per version or adding a foreign key
    to pin them. Doing so breaks historical resolution for every unit already
    built.

See [Processes Overview](../admin/processes/overview.md) and [Change
Control](../workflows/change-control/overview.md).

### Knowledge Check: Module 2

1. A customer reports a defect on a unit built six months ago. Which routing
   version do you read, and why can you still read it?
2. Why can't you deep-copy steps into each new version?

---

## Module 3: What the Solver Believes

### Learning Objectives

1. Explain how a blank cycle time corrupts planning
2. Set machine eligibility and changeovers correctly

### 3.1 Cycle times are a planning input, not documentation

!!! danger "An operation with no cycle time contributes no load"
    The capacity heatmap then shows free capacity that doesn't exist, and
    promised dates come out too optimistic.

    This is a planning failure whose **cause is a blank field on your routing
    step**. The planner cannot fix it from the planning view, and will not
    necessarily know to ask you.

Capacity Planning warns when orders contain operations with no cycle time. Treat
that warning as addressed to you.

### 3.2 The other two

| Symptom the planner sees | What you set |
|--------------------------|--------------|
| Work lands on the wrong machine | [Machine Eligibility](../workflows/scheduling/setup.md#machine-eligibility) |
| The solver interleaves similar jobs | [Changeovers](../workflows/scheduling/setup.md#changeovers) |
| Dates look too comfortable | [Step Timings](../workflows/scheduling/setup.md#step-timings) |

### 3.3 Work centres re-route work

!!! warning "A work centre's kind is a surface discriminator"
    Operator queue, QA inbox, receiving, outside processing. Changing a work
    centre's kind moves work to a different **screen** as surely as editing a
    routing does.

    It is authoring, not configuration. Treat it with the same care.

### Knowledge Check: Module 3

1. The planner says a promise looks too generous. What do you check on your
   routings?
2. You change a work centre's kind from operator queue to QA inbox. What happens
   to work currently at it?

---

## Module 4: Specifications and Measurements

### Learning Objectives

1. Define a measurement with a usable specification
2. Attach it as a step requirement

### 4.1 A definition and a requirement are different things

A **measurement definition** says what the characteristic is and what its limits
are. A **step measurement requirement** says that a particular step must capture
it.

Defining one without requiring it means nobody is ever asked for the number.

### 4.2 Writing a usable spec

- Give it a nominal and a tolerance, not just a nominal
- Use the unit the operator's instrument actually reads
- If it is pass/fail, say so — don't fake a tolerance around it

!!! tip "The operator sees exactly what you wrote"
    A characteristic named "Dim 3" tells the person at the bench nothing. Name it
    for the feature, not for its position on your drawing.

See [Measurements](../admin/processes/measurements.md).

### Knowledge Check: Module 4

1. You defined a torque characteristic but no one is recording it. What did you
   miss?
2. Why does the unit on the definition matter?

---

## Module 5: Life Limits

### Learning Objectives

1. Create a life limit definition
2. Explain why the link to a part type *is* the limit's application

### 5.1 The link is the limit

A life limit is a definition **plus its link to a part type**. The link is not
bookkeeping — it is the application:

- Unlinking stops a harvested component inheriting its core's accumulated life
- Unlinking drops a lot's per-type shelf life to the default

So the link travels with the definition rather than being incidental to it.

### 5.2 Removal is a soft delete

Removing a link from the part type page is a soft delete; linking the pair again
revives it. Nothing is destroyed.

See [Life Tracking](../workflows/tracking/life-tracking.md).

### Knowledge Check: Module 5

1. You unlink a life limit from a part type to "clean up". What breaks?
2. Is that reversible?

---

## Module 6: Digital Work Instructions

### Learning Objectives

1. Author substeps that an operator can actually follow
2. Know what belongs in a DWI versus a controlled document

### 6.1 Substeps are the operator's screen

DWIs are what the person at the bench reads while working. They support
resources (images, files) and translations.

!!! tip "Write for the bench, not for the file"
    A substep is read by someone with their hands busy. One action per substep,
    in the order it happens, with the measurement where it is taken.

### 6.2 DWI or document?

| Put it in a DWI | Put it in a controlled document |
|-----------------|---------------------------------|
| How to perform this step, right now | The specification the step implements |
| Torque sequence, fixture setup | The drawing, the customer spec |
| What "good" looks like at the bench | The quality plan |

See [DWI Overview](../workflows/dwi/overview.md).

### Knowledge Check: Module 6

1. Where does a customer drawing belong?
2. An operator says the instructions are ambiguous. Is that a DWI change or a
   document revision?

---

## Practical Assessment

### Task 1: Version a process
Take an existing process and create a new version. Explain what happened to the
old one and why units built to it still resolve.

### Task 2: Find a planning defect
Locate a routing operation with no cycle time. Explain what it does to the
capacity heatmap and fix it.

### Task 3: Define and require a measurement
Create a measurement definition with a nominal, tolerance and unit, then attach
it as a requirement to a step. Verify an operator would be asked for it.

### Task 4: Link a life limit
Create a life limit definition and link it to a part type. Then explain what
unlinking it would do to a harvested component.

### Task 5: Author a substep
Write a DWI substep for a step that currently has none. Have an assessor try to
follow it without asking you a question.

### Task 6: Find your boundary
Identify one thing in this system you cannot do, and name the role that can.

---

## Training Completion

### Sign-Off Requirements

- [ ] Completed all modules
- [ ] Passed knowledge checks
- [ ] Completed practical assessment
- [ ] Supervisor verification

### Trainee Acknowledgment

By completing this training, I confirm that I:

- Will version processes rather than editing them in place
- Will give every routing operation a real cycle time
- Will write specifications the person at the bench can act on
- Understand that authoring a spec is not approving the document that carries it

### Recording the qualification

Create a **Training Record** under **Quality** > **Training**, as in [Operator
training](operator.md#recording-the-qualification).

---

## Quick Reference Card

### Never
- Edit a process that is in use — version it
- Deep-copy or FK-pin steps per version
- Leave a cycle time blank
- Change a work centre's kind casually

### Always
- Nominal **and** tolerance **and** unit
- Require the measurement, not just define it
- Name characteristics for the feature

### Not yours
- Release a document → Document Controller
- Approve a disposition or CAPA → QA Manager
- Release work / solve the schedule → Planner, Production Manager
- Delete a work centre → manager tier

---

## Next Steps

- [Engineering role guide](../roles/engineering.md)
- [Processes Overview](../admin/processes/overview.md)
- [DWI Overview](../workflows/dwi/overview.md)
- [Change Control](../workflows/change-control/overview.md)
- [Scheduling Setup](../workflows/scheduling/setup.md) — what the solver believes
