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
`/editor/processes/{processId}/steps/{stepId}/substeps`. Whether you can edit
there depends on the process, not on Edit Mode: substeps are editable on a draft,
and read-only on an approved or deprecated process, or while a draft still shares
the step with an approved version (open the step from the process flow with Edit
Mode on, and the draft takes its own copy).

## Adding a substep

1. Click **Add substep**
2. Give it a short, specific title — this is what the operator sees in the
   progress rail, so "Measure orifice diameter" beats "Measurement"
3. Build the body from the node library
4. Set its behaviour (below)
5. **Save draft**, at the top of the page. Nothing is stored until you press it;
   the page warns if you leave with unsaved changes.

The **Operator view** pane beside the editor shows the substep as the operator
will see it, whenever no node is selected (selecting a node shows its
**Properties** there instead).

## The node library

A substep's body is assembled from nodes. They fall into two groups.

### Instruction nodes

These tell the operator what to do. They capture nothing.

| Node | Use for |
|------|---------|
| **Callout** | A warning, caution, or note that must stand out |
| **Media** | An image or video demonstrating the work. For a 3D model, use **Callouts (3D)** — Media does not render one |
| **Document link** | A link to a controlled document |
| **Callouts (3D)** | Numbered guidance balloons on the part's 3D model |
| **Measurement spec** | Showing the specification an operator is working to |

### Capture nodes

These ask the operator for something and create the record.

| Node | Captures |
|------|----------|
| **Measurement** | A numeric value, checked against its spec |
| **Text input** | Free text |
| **Choice** | One option from a list you define |
| **Photo** | An image |
| **File** | An uploaded file of any kind — use it when the operator needs to attach a video |
| **Scan** | A barcode or QR code |
| **Timer** | A countdown or stopwatch |
| **Computed** | A value derived by formula from other captures |
| **Sign-off** | A confirmation or signature — see [Sign-off blocks](#sign-off-blocks) |
| **Quality status** | PASS / FAIL / PENDING |
| **Defect findings** | Defects, picked from error types |
| **Equipment + roles** / **Personnel + roles** | Who and what was involved |
| **Inspection signatures** | Detected-by and verified-by signatures |
| **Defect annotation (3D)** | Defects the operator marks on the part's 3D model. It makes the substep an inspection point: the switch is locked on |
| **Harvested components** | Components recovered during teardown, with their grades (reman) |
| **Components installed** | Which components went into the unit — its as-built record |
| **Rebuild finding** | A component found worse than its teardown grade, for a lead to apply or dismiss (reman) |

!!! tip "Measurements are more than a number field"
    Use **Measurement** rather than a text input for numeric values. Only
    measurement captures are evaluated against the specification and flow into
    SPC and measurement reporting.

## Substep settings

### Sequencing

Set on the step, governing all its substeps: the **Sequencing** select in the
process editor's step panel. It can be changed on a draft process with Edit Mode
on; otherwise it shows as a read-only badge.

- **Sequential** (the default) — *"Each substep needs the one before it done
  first."* Use when order matters for safety or correctness.
- **Free order** — *"Substeps can be done in any order."* Use when the work
  genuinely has no required sequence.

The server enforces Sequential: a substep is refused until the required
substeps before it are done.

### Per part or per batch

Set per substep, with the **Batch (once per lot)** switch:

- **Off** — runs once per part. The default.
- **On** — runs once for the whole batch. Use only for processes that act on
  the lot as a whole: heat-treat cycles, plating baths, wash tanks, oven cures.

A single step can mix both.

### Sampling

A per-part substep (**Batch (once per lot)** off) has a **Sampling** select:

| Option | Applies the substep to |
|--------|------------------------|
| **Every part** | Every part — a 100% check. The default |
| **Percentage** | A set percentage of parts, chosen by a stable per-part hash, so a given part gets the same answer however many others there are |
| **Random** | A percentage of parts, at random |
| **Every Nth part** | Every Nth part of the work order |
| **First N parts** | The first N parts of the work order |

Beside it, a number box takes the percentage (20 by default) or N (5 by
default). The choice is saved with **Save draft**, and only on a draft process.
On a substep you've just added, the switch and the select appear once it has
been saved.

A substep's sampling is its own: it is not part of the step's sampling plan.
See [Sampling Rules](../quality/sampling.md) for sampling a step.

### Optional and safety-critical

| Setting | Effect | Use when |
|---------|--------|----------|
| **Optional** | May be skipped; nothing is recorded | The substep genuinely may not be needed and you don't need to know |
| **Critical** | Shown to the operator as safety-critical | Torque on safety-critical fasteners, witnessed sign-offs, final dimensional verification |

There is no "not applicable" setting. If a substep only applies to some of the
parts that run the step, either the step is wrong for the others (give them their
own step), or the substep is optional, or what the operator finds is a choice to
capture ("Seal present: yes / no"), not a skip.

!!! warning "A required reman capture can't go on a step new builds also run"
    Recording harvested components, a rebuild finding or the components fitted
    needs a core, and a new build has none. A required substep carrying one of
    these is refused on any step a non-reman process uses: put it on a
    reman-only step. An optional one is allowed.

### Sign-off blocks

A **Sign-off** block is how a substep asks someone to put their name to something.
Each one picks its own assurance:

| How it's signed | The operator | Use it for |
|---|---|---|
| **Check off** | Ticks it. Recorded under their login. | Everyday confirmations — "new seals fitted" |
| **Signature + password** | Draws a signature and re-enters **their own** password | Acceptance and release — a final test release, an inspection acceptance |

The block's **label is what the record says was signed for**, so label it with the
act rather than the step: "Release sign-off" reads better in an audit than the
substep's title.

There is no separate substep setting. A substep needs a signature exactly when its
body contains a signature block, so the operator is never asked to sign the same
thing twice.

A signature block works the same way in a **batch** substep, except one signature
covers the whole load rather than each part in it.

### Inspection points

Turn on **Inspection point** when a substep's result should be a queryable
quality record, not just an entry in the substep audit trail. Its structured
captures then also write a Quality Report.

**Add inspection substep** adds a new substep with the switch on and the minimum
capture set a quality report needs already in its body. Turning **Inspection
point** on for an existing substep adds no captures; put them in yourself. A
substep containing a **Defect annotation (3D)** is always an inspection point.

## Changing published instructions

Substeps version with their parent process, so edits follow
[process change control](../change-control/overview.md). Work orders already in flight are migrated according to the change's
migration policy — all, selected, or none.

## Next Steps

- **[Running Work Instructions](running.md)** - What the operator sees
- **[Digital Work Instructions](overview.md)** - Concepts
