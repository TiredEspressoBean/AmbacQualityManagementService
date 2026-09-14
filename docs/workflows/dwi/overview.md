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
| **Photo** / **Video** | Media from the device camera |
| **Scan** | A barcode or QR code |
| **File** | An uploaded file |
| **Timer** | A countdown or stopwatch reading |
| **Computed** | A value derived by formula from other captures |
| **Attestation** | A confirmation or signature |
| **Quality status** | PASS / FAIL / PENDING |
| **Equipment / Personnel** | Which equipment and people were involved |
| **Inspection signatures** | Detected-by and verified-by signatures |
| **Defects** | Defect findings against error types |
| **Part annotation** | A marked point on the part's 3D model |
| **Harvested components** | Components recovered during teardown (reman) |

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
| **Sequential** | Substep *N* can only be completed once *N-1* is complete (or optional and marked N/A) |
| **Free order** | Any substep may be completed in any order; the step's signoff checks that all required substeps are done |

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

**Pending does not block.** The part advances tentatively and the decision is
re-evaluated when the cohort closes. If it then flips to *selected* on a part
that has already moved past the step, the system opens a non-blocking
nonconformance against that part rather than silently dropping the check.

## Optional, N/A, and safety-critical

Three authoring settings control whether a substep can be skipped:

| Setting | Effect |
|---------|--------|
| **Optional** | May be skipped without recording anything |
| **Allow N/A** | May be marked not-applicable, but the operator must pick a reason code and add a note |
| **Safety-critical** | Can *never* be marked N/A — the gate rejects any attempt |

Optional and N/A are deliberately different. Optional means nothing needs to be
recorded. N/A means the operator is making a recorded, reason-coded statement
that this substep did not apply to this part — which stays in the audit trail.

Safety-critical exists for things where "didn't apply" is never an acceptable
answer: torque on a safety-critical fastener, a witnessed signoff, final
dimensional verification.

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
