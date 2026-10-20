# Digital Work Instructions

Digital Work Instructions (DWI) break a manufacturing operation into **substeps**
— the individual things an operator does and records at a step.

## Why substeps exist

A **Step** (also called an Op) is one operation in a process: *Teardown*,
*Nozzle Inspection*, *Final Test*. A step tells you *what* operation to perform,
but not how to perform it or what evidence to capture.

Substeps live one level below the step. Each substep is a single unit of work
instruction — a photo to take, a torque value to record, a checklist item to
acknowledge, a signature to collect. Together they form the instructions an
operator follows, and the record of what actually happened.

```
Process (Routing)
└── Step (Op)              e.g. "Nozzle Inspection"
    ├── Substep 1          "Scan the part barcode"
    ├── Substep 2          "Measure orifice diameter"
    └── Substep 3          "Photograph the seat face"
```

## Captures

Most substeps ask the operator for something. That something is a **capture**,
and the kind of capture determines what the operator sees:

| Capture | Operator records |
|---------|------------------|
| **Measurement** | A numeric value, evaluated against its specification |
| **Text** | Free text |
| **Choice** | One option from a list |
| **Photo** | An image, from the device camera or a file |
| **Scan** | A barcode or QR code |
| **File** | An uploaded file of any kind — the way to attach a video |
| **Timer** | A countdown or stopwatch reading |
| **Computed** | A value derived by formula from other captures |
| **Attestation** | A confirmation or signature |
| **Quality status** | PASS / FAIL / PENDING |
| **Equipment / Personnel** | Which equipment and people were involved |
| **Inspection signatures** | Detected-by and verified-by signatures |
| **Defects** | Defect findings against error types |
| **Part annotation** | A marked point on the part's 3D model |
| **Harvested components** | Components recovered during teardown, with their grades (reman) |
| **Component install** | Which components went into the unit — its as-built record |
| **Rebuild finding** | A component found worse than its teardown grade, for a lead to decide (reman) |

Not every substep asks for something. Callouts, document links, embedded
media — an image, a video, a 3D model — and measurement specs are instruction
content the author places for the operator to read; they record nothing.

Numeric measurements are stored as measurement results, so they flow into SPC
and the usual measurement reporting. The other captures are stored as substep
responses against the completion record.

## How substeps gate advancement

Substeps are what make advancement *event-driven*. A part cannot leave a step
until that step's required substeps are satisfied for it. Completing the last
one is the event that lets the part move.

This is why there is no "move to next step" button — see
[Moving Parts Forward](../tracking/moving-parts.md).

### Sequencing

A step's substeps run in one of two modes:

| Mode | Behaviour |
|------|-----------|
| **Sequential** | Substep *N* can only be completed once every **required** substep before it is complete |
| **Free order** | Any substep may be completed in any order; the step's signoff checks that all required substeps are done |

!!! note "An optional substep never holds up the one after it"
    Sequencing looks only at the required substeps ahead of the one being
    completed. An **optional** earlier substep is skipped by the check, so a
    free-standing optional step cannot strand an operator.

### Per part or per batch

Each substep declares how it maps onto the parts at the step:

| Scope | Runs | Use for |
|-------|------|---------|
| **Per part (sampling)** | Once per part | Anything specific to an individual part — measurements, visual checks, scans |
| **Per batch** | Once for the whole batch | Processes that happen to the lot as a whole — heat-treat cycles, plating baths, wash tanks, oven cures |

The choice is made per substep, not per step, so one step can mix both. A
plating operation might scan each part in (per part), run the bath once (per
batch), then do a final visual on each part (per part).

!!! note "Why batch captures aren't a loophole"
    A batch cycle either succeeded for the lot or it didn't. Per-part failures
    are caught by the per-part substeps that run before and after it.

### Sampling

A per-part substep can carry a **sampling rule**. Without one it runs for every
part — a 100% sample. With one, the rule decides which parts it applies to, and
each part gets an outcome:

| Outcome | Meaning |
|---------|---------|
| **Selected** | This part is in the sample; the substep must be completed before the part advances |
| **Deselected** | This part is not in the sample; the substep is treated as satisfied |
| **Pending** | The rule needs more information — cohort size, end of shift, end of work order — and can't decide yet |

**Pending does not block at the step itself.** The part advances tentatively and
the decision is re-evaluated when the cohort closes — the rule that could not
decide at step entry can decide once it knows the full cohort. The pending row is
superseded by the resolved one, so the outcome is a record of both.

!!! warning "It does block at the terminal step"
    Nothing unresolved ships. At a terminal step the gate refuses any part whose
    work order still has live PENDING decisions — *"Terminal step: N PENDING
    sampling decision(s) require reconciliation before shipment."*

    Reconcile them and the gate clears. A decision that resolves to *selected* on
    a part with the substep still uncompleted simply becomes the next blocker the
    supervisor sees, which is the point: the check is deferred, never dropped.

## Optional and safety-critical

| Setting | Effect |
|---------|--------|
| **Optional** | May be skipped without recording anything |
| **Safety-critical** | Shown to the operator as critical: torque on a safety-critical fastener, a witnessed sign-off, final dimensional verification |

Everything else is required. There is no "not applicable": a substep that doesn't
apply to some parts belongs on a step only the others run, or is optional, or
records what the operator found as a choice. See
[Authoring](authoring.md#optional-and-safety-critical).

## Inspection points

A substep can be marked an **inspection point**. Its structured captures — quality
status, defects, signatures, equipment and personnel — then also write a Quality
Report, so the inspection is queryable as a quality record rather than living
only inside the substep's audit trail.

## Change control

Substeps version with their parent process. Changing them follows the same
change control path as any other process change — see
[Change Control](../change-control/overview.md). In-flight work orders are migrated
according to the change's migration policy.

## Next Steps

- **[Authoring Work Instructions](authoring.md)** - Building substeps on a step
- **[Running Work Instructions](running.md)** - The operator's step player
- **[Moving Parts Forward](../tracking/moving-parts.md)** - How advancement works
