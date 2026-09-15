# Authoring Work Instructions

This guide covers building substeps on a step. See
[Digital Work Instructions](overview.md) for the concepts.

!!! info "Who this is for"
    Process engineers and administrators who define how work is performed.
    Operators run these instructions but don't author them.

## Opening the substep editor

1. Open the process in the **Process Flow** editor
2. Turn on **Edit Mode**
3. Click the step (Op) you want to add instructions to
4. In its properties panel, use the **Substeps** control

The editor opens at
`/editor/processes/{processId}/steps/{stepId}/substeps`. With Edit Mode off the
same control opens the substeps read-only.

## Adding a substep

1. Click **Add substep**
2. Give it a short, specific title — this is what the operator sees in the
   progress rail, so "Measure orifice diameter" beats "Measurement"
3. Build the body from the node library
4. Set its behaviour (below)
5. **Save**

Use **Preview** to see the substep as the operator will.

## The node library

A substep's body is assembled from nodes. They fall into two groups.

### Instruction nodes

These tell the operator what to do. They capture nothing.

| Node | Use for |
|------|---------|
| **Callout** | A warning, caution, or note that must stand out |
| **Media** | An image or video demonstrating the work |
| **Document link** | A link to a controlled document |
| **Part callout** | Highlighting a feature on the part |
| **Measurement spec** | Showing the specification an operator is working to |

### Capture nodes

These ask the operator for something and create the record.

| Node | Captures |
|------|----------|
| **Measurement input** | A numeric value, checked against its spec |
| **Text input** | Free text |
| **Choice input** | One option from a list you define |
| **Photo capture** / **File capture** | Media or an uploaded file |
| **Scan input** | A barcode or QR code |
| **Timer** | A countdown or stopwatch |
| **Computed value** | A value derived by formula from other captures |
| **Attestation checkpoint** | A confirmation or signature |
| **Quality status field** | PASS / FAIL / PENDING |
| **Error types field** | Defect findings |
| **Equipment roles** / **Personnel roles** | Who and what was involved |
| **Inspection signatures** | Detected-by and verified-by signatures |
| **Part annotation** | A marked point on the part's 3D model |
| **Harvested component capture** | Components recovered during teardown (reman) |

!!! tip "Measurements are more than a number field"
    Use **Measurement input** rather than a text input for numeric values. Only
    measurement captures are evaluated against the specification and flow into
    SPC and measurement reporting.

## Substep settings

### Sequencing

Set on the step, governing all its substeps:

- **Sequential** — each substep unlocks the next. Use when order matters for
  safety or correctness.
- **Free order** — operators complete substeps in any order. Use when the work
  genuinely has no required sequence.

### Per part or per batch

Set per substep:

- **Per part (sampling)** — runs once per part. The default.
- **Per batch** — runs once for the whole batch. Use only for processes that
  act on the lot as a whole: heat-treat cycles, plating baths, wash tanks,
  oven cures.

A single step can mix both.

### Sampling

Leave a per-part substep's sampling rule empty for a 100% check. Attach a
sampling rule to check only the parts that rule selects. See
[Sampling Rules](../quality/sampling.md).

### Optional, N/A, and safety-critical

| Setting | Effect | Use when |
|---------|--------|----------|
| **Optional** | Skippable, nothing recorded | The substep genuinely may not be needed and you don't need to know |
| **Allow N/A** | Skippable with a reason code and a note | You need a recorded reason why it didn't apply |
| **Safety-critical** | Can never be marked N/A | "Didn't apply" is never acceptable |

Mark a substep **safety-critical** for torque on safety-critical fasteners,
witnessed signoffs, and final dimensional verification.

!!! warning "Safety-critical and N/A are mutually exclusive"
    A safety-critical substep cannot be marked N/A by anyone. The advancement
    gate rejects the attempt.

### Inspection points

Mark a substep an **inspection point** when its result should be a queryable
quality record, not just an entry in the substep audit trail. Its structured
captures then also write a Quality Report.

Adding an inspection point pre-seeds the minimum capture set a quality report
needs.

## Changing published instructions

Substeps version with their parent process, so edits follow
[process change control](../change-control/overview.md). Work orders already in flight are migrated according to the change's
migration policy — all, selected, or none.

## Next Steps

- **[Running Work Instructions](running.md)** - What the operator sees
- **[Digital Work Instructions](overview.md)** - Concepts
