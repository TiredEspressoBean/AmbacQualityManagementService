# Report Content Specifications

**Last Updated:** April 2026
**Status:** Per-report content requirements grounded in industry research
**Companion to:** [PDF_EXPORTS_REQUIREMENTS.md](./PDF_EXPORTS_REQUIREMENTS.md)
(catalog + architecture) and the shipped NCR adapter as the
reference implementation.

This document captures **what each report must actually contain** based
on industry standards (ISO 9001, IATF 16949, AIAG SPC, Ford G8D) and
real-world templates from large OEMs and QMS vendors. It complements
the catalog by going one level deeper: required fields, common
optional fields, structural constraints, and identified gaps in our
current data model.

The intent is to ground report development in real customer/auditor
expectations, not in our internal model assumptions. Several proposed
adapter designs have been adjusted based on this research.

---

## How to use this document

When starting a new report:

1. Read the per-report section below for required content + structural rules.
2. Read the **Schema gaps** subsection — these are blockers that should
   be resolved (or explicitly accepted as v1 limitations) before
   building.
3. Cross-reference [PDF_EXPORTS_REQUIREMENTS.md](./PDF_EXPORTS_REQUIREMENTS.md)
   for the architecture pattern (Pydantic context, DRF serializer,
   `build_context()`, Typst template).

When proposing scope changes, update this doc — it's the source of
truth for "what does this report actually need to contain?"

---

## Cross-cutting findings

These apply to multiple reports:

### Drawing number + revision is missing on PartTypes

Auditors check that any production record references the drawing
revision the part was made/inspected against. Affects: CofC, Part
Traveler, Inspection Report, FAI (when aero comes back).

**Recommended fields on `PartTypes`:** `drawing_number`,
`drawing_revision`.

### Material lot traceability is missing

IATF 16949 clause 8.5.2.1 requires material lot traceability through
every operation. We have a `MaterialLot` model but no FK from `Parts`
or `WorkOrder` to a specific lot.

**Recommended fields:** `Parts.material_lot` FK or
`WorkOrder.material_lot` FK + `material_spec` text.

### Customer PO number ≠ internal order number

Many reports (CofC, Inspection, Part Traveler) need the **customer's
PO number**, not just our internal `Orders.order_number`. The PO is
the document the customer references in their own systems.

**Recommended field:** `Orders.customer_po_number` (and possibly
`customer_po_revision`, `customer_po_line_number`).

### Operation number on ProcessStep

Travelers and inspection records use explicit operation numbers
("Op 10", "Op 20", "Op 30") — not just timestamp ordering. Verify
whether `ProcessStep.sequence` is exposed and used as the operation
number; if not, add `operation_number`.

### Document numbering is not the order number

Reports like CofC need their **own** document numbering sequence
(e.g., `COC-2026-00147`) for audit traceability. Don't reuse the
order number.

### Signature blocks: customer signs only when concession is required

The customer signs supplier documents only when granting a
**concession** — i.e., approving an NCR use-as-is disposition or
similar deviation request (per ISO 9001 8.7.1(b) and IATF 16949
8.7.1.6). Customers do **not** sign routine documents like the CofC
or a passing inspection report — they sign their own receiving paperwork.

Apply this rule consistently:

- **CofC** — no customer signature block. Internal signoff (originator
  + QA), max two.
- **NCR** — customer signature block belongs in the document **only
  when `requires_customer_approval` is true** (UAI / concession
  dispositions). When false, render a 2-column signature grid
  (Originator + Quality Manager). The shipped NCR template currently
  always shows the 3-column grid; this should be made conditional.
- **8D Report** — customer quality engineer acceptance is common
  (Ford, GM, MAHLE require it for supplier 8D responses). Include
  the slot.
- **Inspection / Traveler** — internal only; customer doesn't sign.

---

## Non-Conformance Report (NCR / NCMR)

**Status:** Shipped (backed by `QuarantineDisposition`). Needs
architectural rethink before adding the missing fields — see note
below.

> **Data model mismatch.** The shipped adapter treats
> `QuarantineDisposition` as the NCR, but that model is a
> **per-part disposition workflow** ("rework part #47"). Similarly,
> `QualityReports` is a **per-part inspection event** ("I checked
> part #47, found 3 cracks"). A real-world NCR is a
> **batch/lot-level nonconformance document** that sits *above* both:
> "we found surface porosity on 12 of 50 parts from lot ABC-2026."
>
> The right fix is a dedicated **`NonConformanceReport`** model that:
>
> - Has its own numbering sequence (`NCR-YYYY-######`)
> - Links to **multiple** QualityReports (per-part inspection evidence)
> - Links to **multiple** QuarantineDispositions (per-part disposition
>   decisions)
> - Carries batch/lot-level fields: quantity affected / inspected /
>   defective, detection source, specification violated, severity,
>   containment, root cause summary, CAPA reference, cost, customer
>   notification, closure
>
> The individual QualityReports and QuarantineDispositions stay as-is —
> they're per-part records. The NCR is the umbrella document that
> groups them into a single reportable incident. The must-fix fields
> listed below belong on this new model, not on QuarantineDisposition.
>
> Until this model exists, the shipped adapter works as a
> single-part-disposition printout — functional but not auditor-grade
> for lot-level nonconformances.

### Purpose

The formal record produced when a nonconformance event requires
documentation and a disposition decision. Typically covers a
**batch or lot** of parts (not a single part), internally generated,
sometimes shared with customers when concession is required.

### Required content (per ISO 9001:2015 clause 8.7 + IATF 16949 clause 8.7.1)

ISO 8.7.2 mandates documented information describing:

- (a) the nonconformity itself
- (b) actions taken
- (c) any concessions obtained from the customer
- (d) the authority deciding the disposition

IATF 16949 adds:

- 8.7.1.6 — customer notification when nonconforming product has
  been shipped
- 8.7.1.7 — scrap rendered unusable prior to disposal, with
  verification

### Standard NCR sections (industry consensus)

**Header:**
- NCR number (own sequence), date opened, current state
- Severity (Critical / Major / Minor)
- Originator + department

**Identification:**
- Part number + revision, serial / lot / batch
- Work order, customer PO (if customer-impacting)
- Quantity affected, quantity inspected, quantity defective
- Detection source (Receiving / In-Process / Final / Customer Return)

**Non-conformance description:**
- What is wrong + the requirement / specification violated
- Reference defect codes if applicable

**Containment:**
- Immediate actions to bracket the issue
- Containment completed by + when

**Disposition:**
- Type (Rework / Repair / Scrap / Use-As-Is / Return-To-Supplier / Regrade)
- Disposition authority (MRB chair, QA manager — IATF requires
  authority be identified)
- Resolution narrative

**Customer concession (conditional, only when applicable):**
- Customer approval reference, date, signature

**Scrap verification (conditional, IATF 8.7.1.7):**
- Method, verified by, when

**Root cause + CAPA linkage:**
- Summary of root cause (full RCA happens in CAPA, but NCR carries a summary)
- Reference to CAPA / 8D number when one was opened

**Cost (IATF-aligned shops):**
- Estimated cost, cost category (scrap / rework / external / other)

**Closure:**
- Resolution completed by + when, signoff signatures

### Disposition types

The standard set used industry-wide:

- **Rework** — bring back into spec
- **Repair** — fix to acceptable condition (may not meet original spec)
- **Scrap** — destroy / dispose
- **Use-As-Is (UAI)** — accept with deviation (requires customer concession)
- **Return-To-Supplier (RTS)** — for supplier-caused defects
- **Regrade** — downgrade to alternate use (industry-standard, currently missing from our enum)

### Severity classification

**Critical / Major / Minor** is industry-standard (ISO auditing
practice, IATF, all major QMS vendors). Our implementation matches.

### NCR vs CAPA relationship

NCR and CAPA are **separate documents**:

- NCR = "what happened + immediate disposition" (per-incident)
- CAPA = "root cause + systemic fix" (cross-incident, addresses
  recurrence)

Not every NCR triggers a CAPA. Triggers include: repeat NCRs on the
same failure mode, critical severity, customer-impacting events. The
printed NCR **should** include a CAPA reference field when one
exists — auditors expect it.

### What's correct in the shipped model

- Severity tiers (Critical / Major / Minor) — standard
- Disposition types (Rework / Repair / Scrap / UAI / RTS) — core five correct
- Containment section — correctly modeled
- Scrap verification section — IATF 8.7.1.7 explicitly requires this
- Customer approval section already conditional on
  `requires_customer_approval`
- State machine (OPEN / IN_PROGRESS / CLOSED) — standard

### Schema gaps (must-fix for auditor-grade)

- **Quantity fields** (`quantity_affected`, `quantity_inspected`,
  `quantity_defective`) — universal on every real NCR form; required
  for bracketing and cost calculation
- **`root_cause_summary`** field — every real-world NCR form has at
  least a summary line, even when full RCA lives in a separate CAPA
- **`capa_reference`** (Optional[str]) — link to the CAPA / 8D number
  when one was opened
- **`detection_source`** enum (Receiving / In-Process / Final /
  Customer Return) — standard field
- **`specification_violated`** — text describing the requirement /
  drawing / spec not met (ISO 8.7.2(a))
- **Make customer signature line in template conditional** on
  `requires_customer_approval` — currently always renders 3-column
  grid; should fall back to 2-column (Originator + Quality Manager)
  when concession not required

### Schema gaps (should-fix)

- **`lot_or_batch_number`** (Optional[str]) — standard ID field
- **`disposition_authority`** field — IATF requires authority be
  identified; current `assigned_to` is ambiguous (reviewer vs
  rework operator)
- **`estimated_cost`** (Optional[Decimal]) + **`cost_type`** enum
  (Scrap / Rework / External / Other) — enables COPQ Pareto reporting
- **`VOIDED`** state — for NCRs opened in error
- **`REGRADE`** disposition type

### Schema gaps (nice-to-have)

- **`supplier_id`** — for receiving-inspection NCRs
- **`attachment_count`** or attachment list — audit trail reference
- **`related_ncr_numbers`** — for linked / repeat NCRs

### Don't include

- **`rework_attempt_at_step`** on the printed NCR — internal workflow
  state, not a printable field. Keep in the DB, hide from the rendered
  PDF.
- Embedded full RCA (5-Why tables, Fishbone diagrams) — that's a CAPA /
  8D concern. NCR carries a summary + reference.
- Full cost-of-quality breakdown — single estimated cost is enough on
  the NCR; detailed COPQ analytics live in dashboards.

### Sources

- [ISO 9001 Clause 8.7 — David Barker Consulting](https://davidbarker.consulting/iso9001/clause-8-7-control-of-nonconforming-outputs/)
- [IATF 16949 Clause 8.7.1.7 Nonconforming Product Disposition — Pretesh Biswas](https://preteshbiswas.com/2023/08/05/iatf-16949-clause-8-7-1-7-nonconforming-product-disposition/)
- [IATF 16949 Clause 8.7.1.6 Customer Notification — Pretesh Biswas](https://preteshbiswas.com/2023/08/03/iatf-169492016-clause-8-7-1-2-control-of-nonconforming-product-customer-specified-process-and-clause-8-7-1-6-customer-notification/)
- [Complete Guide to Nonconformance Management — 1factory](https://www.1factory.com/quality-academy/guide-nonconformance-management.html)
- [NCR — SimplerQMS](https://simplerqms.com/non-conformance-report/)
- [NCR/CAPA Integration — ComplianceQuest](https://www.compliancequest.com/cq-guide/integrate-non-conformance-reports-with-capa/)
- [Major vs Minor vs Critical Nonconformities — Qualityze](https://www.qualityze.com/blogs/major-minor-critical-non-conformities)
- [ISO 9001 Nonconforming Product Dispositions — Advisera](https://advisera.com/9001academy/blog/2014/11/18/understanding-dispositions-iso-9001-nonconforming-product/)

---

## Certificate of Conformance (CofC)

### Purpose

A statement from the supplier to the customer declaring that all
items in a shipment conform to the applicable specifications.
Per-shipment, not per-order.

### Required content (per ISO 9001 / IATF 16949 + automotive norm)

- **CofC document number** (own sequence, distinct from order/PO number)
- **Revision level** (for reissues)
- **Date of issue**
- **Supplier identification** (legal name, address, contact)
- **Customer identification** (name, address)
- **Customer PO number + line items + PO revision**
- **Product description** (part name/number, drawing number + revision)
- **Quantity shipped** (per line item)
- **Serial / lot / batch numbers** (or per-lot reference)
- **Applicable specifications/standards** (ISO, ASTM, customer drawing
  numbers, material specs)
- **Conformance declaration statement** (unambiguous; no hedging language
  like "substantially conforms")
- **Exceptions / deviations section** (when non-conformances exist with
  deviation approval references)
- **Authorized signature** (one QA-authority signature minimum, with
  printed name + title + date)

### Common optional content

- Material certification / Mill Test Report (MTR) reference numbers
- Test report references (by report number — not embedded)
- Manufacturing date / date code
- Shelf life / expiration date (perishables)
- Inspection method summary ("100% inspected" or "AQL per ANSI Z1.4")
- First-pass yield (some automotive customers request this)
- Country of origin (increasingly required, USMCA/tariff compliance)
- PPAP approval reference (automotive)
- IMDS submission reference (automotive material composition)
- RoHS / REACH declaration (sometimes embedded, often separate)

### Structural constraints

- **Per-shipment, not per-order.** One order with three partial
  shipments produces three CofCs.
- **CofC ≠ CofA.** A Certificate of Analysis embeds detailed test
  results; a Certificate of Conformance only **declares** conformance
  and **references** test reports by number. Don't conflate them.
- **No customer signature.** Drop the customer signature block.

### Schema gaps before this can ship credibly

- New `CertificateOfConformance` model with own numbering sequence,
  per-shipment, with `superseded_by` for reissues
- `Orders.customer_po_number` (+ optional revision/line)
- `PartTypes.drawing_number` + `drawing_revision`
- Conformance statement template per tenant (some customers mandate
  exact language)
- Deviations/exceptions field + linkage to approved deviations

### Don't include

- Per-part QualityReports embedded in the CofC body (that's a CofA)
- Customer signature block
- Three-signature block (originator + QA Manager + Customer) — drop
  customer; originator+QA is the maximum

### Sources

- [Certivo: Complete Guide for Manufacturers](https://www.certivo.com/blog-details/what-is-a-certificate-of-conformance-(coc)-complete-guide-for-manufacturers)
- [Certainty Software: Certificate of Conformity Ultimate Guide](https://www.certaintysoftware.com/certificate-of-conformity-guide/)
- [American Precision Products: CoC vs CoA](https://www.injection-moldings.com/groups/engineering-team/certificate-conformance-vs-certificate-analysis)
- [IATF Customer Specific Requirements](https://www.iatfglobaloversight.org/oem-requirements/customer-specific-requirements/)
- [Pantex CofC Template (PDF)](https://pantex.energy.gov/sites/default/files/PX-4893_Certificate_of_Conformance.pdf)

---

## Part Traveler / History Report

### Purpose

A traveler is **two documents in one**: a forward-looking **routing**
(the planned process steps) plus a backward-looking **history record**
(actuals — what happened at each step, by whom, when, with what
result). Some shops split them; many keep them combined.

When generating the PDF, both layers should appear: planned routing
alongside actual execution, with deviations highlighted.

### Required content (per ISO 9001 / IATF 16949)

ISO 9001 / IATF don't prescribe a template — they require **records
that prove**:

- Identification & traceability (clause 8.5.2 / IATF 8.5.2.1) — unique
  serial/lot through every operation, with operator and timestamp
- Drawing/process revision in effect at time of manufacture (8.5.6)
- Evidence of conformity at inspection gates (8.6)
- Rework/disposition records linked to specific serial + step (8.7)
- Measurement equipment ID + calibration traceability (7.1.5)

### Standard fields (industry consensus)

**Header:**
- Part number, drawing number + revision, serial / lot, work order
- Customer / order reference, quantity, material specification
- Date issued

**Per operation row:**
- Operation number (Op 10, Op 20, …) — explicit sequence
- Operation description / name
- Work center / machine
- Operator initials or badge ID
- Date/time in / out
- Inspector sign-off (separate from operator)
- Accept / reject
- Remarks (free-text per row)

**Footer:**
- Final inspection sign-off
- Total quantity accepted / rejected / scrapped
- Date completed
- QA release stamp ("released for shipment")

### Rework documentation

- The original failed step entry **stays on the traveler** — never
  replaced
- Rework appears as a **new entry** referencing the failure (visit_number)
- Cross-reference to the NCR/NCMR number
- Re-inspection after rework gets its own sign-off

(Our `StepExecution.visit_number` model already supports this.)

### Operator privacy (US context)

Operators are **routinely identified** by name, badge, or employee ID.
No GDPR equivalent for US manufacturing employee work records. IATF
effectively requires it for root-cause traceability.

### Schema gaps before this can ship credibly

- `PartTypes.drawing_number` + `drawing_revision` (cross-cutting)
- `Parts.material_lot` (or `WorkOrder.material_lot`) + `material_spec`
- `ProcessStep.operation_number` if not already exposed via `sequence`
- `StepExecution.inspected_by` FK to User (separate from
  `completed_by`)
- `StepExecution.notes` TextField for per-step remarks
- `Steps.work_instruction_ref` (CharField or FK to Documents) for the
  governing WI reference
- A final-release / `TravelerRelease` model or fields on Parts
  (released_by, released_at, disposition) — currently QualityReports
  are per-incident, not a final release gate

### Don't include

- Polymorphic content_type / subject_id internals (DB concern, not
  output concern)
- FPI status on every step (it's a batch-level event; show only on
  the first part's record)
- `needs_reassignment` flag (workflow concern)
- `spc_enabled` flag on MeasurementDefinition (configuration data)

### Sources

- [Tulip: Manufacturing Travelers](https://tulip.co/blog/manufacturing-travelers-steps-to-digitize-your-product-documentation/)
- [Qualityze: ISO 9001 Identification & Traceability](https://www.qualityze.com/blogs/iso-9001-clause-8-5-2-identification-traceability)
- [Pretesh Biswas: IATF 16949 8.5.2.1](https://preteshbiswas.com/2023/08/01/iatf-169492016-clause-8-5-2-1-identification-and-traceability/)
- [Codeware ShopFloor Travelers](https://www.codeware.com/products/shopfloor/shop-travelers/)

---

## 8D Report (Eight Disciplines)

### Purpose

Structured problem-solving response, originated by Ford (TOPS 1987,
revised G8D mid-90s). The de facto CAPA closure format across the
automotive supply chain. IATF 16949 doesn't mandate 8D by name but
requires a documented corrective action process.

### Standard structure (D0–D8)

| | Discipline | Required content |
|--|------------|------------------|
| D0 | Triage / ERA | Symptom checklist, emergency response actions, decision whether full 8D is needed |
| D1 | Team | Cross-functional team (4-10), Champion/Sponsor, Team Leader, members + roles + departments |
| D2 | Problem Description | Is/Is Not analysis, quantified problem statement (what/where/when/how big) |
| D3 | Interim Containment (ICA) | Actions to protect customer NOW, verification ICA is effective |
| D4 | Root Cause + Escape Point | **Two root causes:** occurrence cause + escape cause (why it wasn't detected). Verification root cause can be turned on/off |
| D5 | Permanent Corrective Action selection | Acceptance criteria, risk assessment, PCA selection rationale |
| D6 | Implement + Validate PCA | Implementation plan with owners/dates, remove ICA, validation data |
| D7 | Prevent Recurrence | Update FMEA, Control Plan, work instructions; horizontal deployment to similar processes; training updates |
| D8 | Closure + Recognition | Lessons learned, before/after metrics, archive, team recognition |

### RCA methods (D4)

Standard practice is to use Fishbone (Ishikawa) **AND** 5-Why
**together as complementary tools**, not pick one. Fishbone organizes
potential causes across 6M categories; 5-Why drills down to verify.

The most-cited gap in supplier 8Ds: failing to identify the **escape
point** — why the defect wasn't caught by existing controls. This is
just as important as the occurrence cause.

### Customer-facing format

When an OEM (Ford, GM, Stellantis, MAHLE) requires an 8D from a
supplier, they expect it in their specific template/format. The 8D
is the supplier's response document. Typical SLAs: 24h for D3, 14
days for full 8D. MAHLE formally scores supplier 8D reports against
a rubric.

### Approval/signoff

- Champion/Sponsor approves findings + authorizes changes
- Minimum signatures at closure: Team Leader + Champion/Sponsor
- Many OEMs require customer quality engineer acceptance
- 2-3 internal signatures is the norm

### Schema gaps before this can ship credibly

- **D1 Team:** missing entirely. Add M2M to User with role pivot
  (champion, leader, members) + departments
- **D4 model is wrong both ways:**
  - Polymorphic FiveWhys/Fishbone should be combined, not OR — drop
    the polymorphic classes
  - Replace with one `RcaRecord` with method enum + JSON analysis
    blob
  - **Add `escape_point` field** (currently missing — biggest D4 gap)
- **D6 verification too thin:** add `verification_method`,
  `acceptance_criteria`, `measurement_data` (file or JSON),
  `verification_date`
- **D7 Prevention missing entirely** — biggest real-world gap.
  Add `PreventionAction` model or fields:
  - `fmea_updated` (bool + ref)
  - `control_plan_updated` (bool + ref)
  - `work_instructions_updated` (bool + ref)
  - `horizontal_deployment_scope` (text)
  - `lessons_learned` (text)
- **D8 closure partial:** add `lessons_learned`,
  `before_after_summary`, `archive_reference`
- **CAPA type gate:** add `capa_type` enum (8D / mini-8D / simple)
  so D1-D8 fields aren't mandatory for minor CAPAs
- **D1-D8 phase tracking:** keep it (standard QMS software practice
  per Minitab, ComplianceQuest, SAP), enum status per discipline

### Don't include

- Polymorphic FiveWhys/Fishbone classes (combine; method enum + JSON)
- Forced 8D structure on every CAPA (gate by `capa_type`)
- Recognition as a structured table (text field is enough)

### Sources

- [Ford Global 8D Workbook (PDF)](https://cdn2.hubspot.net/hub/170850/file-18472412-pdf/docs/global_8d_workbook.pdf)
- [Quality-One: 8D Eight Disciplines](https://quality-one.com/8d/)
- [ASQ: Eight Disciplines Problem Solving](https://asq.org/quality-resources/eight-disciplines-8d)
- [MAHLE 8D Process Manual (PDF)](https://www.mahle.com/media/global/purchasing/supplier-portal/8d-e-learning/manual_8d-process_en-ex.pdf)
- [MAHLE 8D Assessment Manual (PDF)](https://www.mahle.com/media/global/purchasing/supplier-portal/8d-e-learning/manual_8d-assessment_en_ex.pdf)
- [PRIZ Guru: D4 Root Cause Analysis](https://www.priz.guru/8d-root-cause-analysis/)
- [AutomotiveQual: D7 Preventive Actions](https://www.automotivequal.com/what-preventive-actions-can-be-implemented-in-d7-methodology-8d/)

---

## Inspection Report (Generic)

### Purpose

Snapshot of a single inspection event. Generic enough to cover
incoming/receiving, in-process, final, and first-piece inspections
via an `inspection_type` enum.

### Inspection types

| Type | When | Focus |
|------|------|-------|
| Incoming / Receiving | Material arrival | Supplier conformance, CoC, dimensions, material grade |
| In-Process (IPQC) | During production | Machine settings, process params, intermediate measurements |
| Final | Before shipment | Full dimensional, functional, cosmetic, packaging |
| First-Piece (FPI) | First part off setup | Verifies setup before running batch |

(Layered Process Audit is a separate concern, not an inspection report.)

### Required content (per ISO 9001 / IATF 16949 + industry consensus)

ISO 9001 clause 8.6 requires documented evidence of conformity with
acceptance criteria, including identification of the person
authorizing release. Clause 7.1.5 requires calibration traceability.

**Header:**
- Report number, date, part number + revision, work order, lot/batch
- Customer / PO

**Personnel:**
- Inspector name, verified/approved by, date

**Sampling:**
- Method (100% / AQL), sample size, lot size, AQL parameters
  (inspection level, AQL value, accept/reject numbers)
- Reference standard (ISO 2859-1 / ANSI Z1.4)

**Measurements table:**
- Characteristic / dimension
- Nominal, upper / lower tolerance, actual value
- Pass / fail
- Instrument / gage ID used (per row)

**Defects section:**
- Defect type, quantity, severity (critical / major / minor), location

**Disposition (CRITICAL):**
- Accept / Reject / Rework / Use-As-Is / RTV (return to vendor)

**Attachments / notes:**
- Photos, sketches, remarks

**Signatures:**
- Inspector + quality authority sign-off + date

### AQL vs 100%

When AQL is used, the report **must** document: lot size, sample size,
inspection level (I/II/III), AQL value, accept/reject numbers, and
the standard referenced. A bare `sampling_method` string is
insufficient.

### Calibration tie-in

ISO 9001 7.1.5.2 requires calibration traceability and equipment cal
status identification. **The standard does NOT require cal status on
the inspection report itself** — it requires that out-of-cal equipment
be traceable. Best practice: record the **gage ID per measurement
row**; the cal database is the source of truth. A
`calibration_valid` boolean is a fine convenience flag.

### FPI vs PPAP vs FAI

| | First-Piece (FPI) | PPAP | FAI (AS9102) |
|---|---|---|---|
| Scope | 1 part per setup | 30-300 parts | 1-5 parts |
| Purpose | Verify setup | Prove process capability | Prove design-to-part conformity |
| Industry | General | Auto (IATF) | Aero (AS9100) — **deferred** |

For our generic Inspection Report, **FPI is the relevant variant**.
`is_first_piece` boolean handles it. PPAP is a multi-document
submission, not a single report.

### Schema gaps before this can ship credibly

- **Disposition field** (Accept/Reject/Rework/Use-As-Is/RTV) — critical
  omission; the most important output of an inspection report
- **AQL parameter group** — lot_size, sample_size, inspection_level,
  aql_value, accept_number, reject_number
- **Gage ID per measurement row** (currently equipment is at report
  level, not per row)
- **`inspection_type` enum** (INCOMING / IN_PROCESS / FINAL /
  FIRST_PIECE) — `is_first_piece` boolean only handles one variant
- **Drawing/spec revision reference** at the report level (cross-cutting)
- **Customer + PO reference** especially for incoming / final
- Approver signature with explicit timestamp + disposition authority

### Don't include (over-engineered for v1)

- **3D model heatmap annotations** — no real-world inspection report
  template surveyed includes these. CMM software (Polyworks, GOM
  Inspect) territory. Defer to v2+.
- **Live SPC baseline overlay per measurement row** — SPC charts are a
  separate deliverable in every QMS reviewed. Defer or simplify to an
  optional Cpk snapshot.
- **Full equipment calibration record snapshot** — overkill. Store
  gage ID; the cal database is the source of truth.

### Structural recommendation

Use **one generic model** with `inspection_type` enum. Don't split
into separate report types. Measurement table + defect table are
identical across all variants. Variation is small:

- Incoming adds supplier/PO fields (nullable on the base)
- Final adds a shipping release flag
- First-piece is just `inspection_type=FIRST_PIECE` with
  `sample_size=1`

### Sources

- [Falcony: Common Inspection Templates in Manufacturing](https://blog.falcony.io/en/8-common-inspection-templates-in-manufacturing)
- [GoAudits: Incoming Inspections](https://goaudits.com/blog/incoming-inspections/)
- [BPR Hub: ISO 9001 Inspection & Testing](https://www.bprhub.com/blogs/iso-9001-inspection-testing-procedure)
- [Core Business Solutions: ISO 9001 Clause 7.1.5](https://www.thecoresolution.com/clause-7-1-5-iso-9001-explained)
- [InTouch Quality: 100% vs AQL Sampling](https://www.intouch-quality.com/blog/when-to-perform-a-100-quality-control-inspection-vs.-aql-sampling)
- [Lexco Cable: FAI / PPAP / AS9102](https://www.lexcocable.com/resources/blog/understanding-fai-ppap-and-as9102-a-guide-for-modern-manufacturers/)

---

## SPC Control Charts

### Purpose

Time-series control charts (X-bar/R, X-bar/S, I-MR) with capability
indices (Cpk, Ppk) for ongoing process monitoring and PPAP submission.

### AIAG SPC reference

The current edition is **AIAG SPC-3 (2nd edition, July 2005)**, authored
with Chrysler/Ford/GM/Delphi/Bosch/Omnex. There is **no 4th edition** of
the SPC manual (4th edition refers to MSA, not SPC).

### Chart types — what matters

| Chart | When to use | Notes |
|-------|-------------|-------|
| X-bar/R | n=3-5 (commonly 5) — workhorse | Default for parts off a line in rational subgroups |
| I-MR | n=1 — destructive test, slow process, batch-level | Individual + Moving Range |
| X-bar/S | n>9 — rare on shop floor | Defer past v1 |
| p / np / c / u | Attribute data | Defer past v1 |

### Required chart elements

| Element | Required |
|---------|----------|
| UCL, CL, LCL lines | Yes, mandatory |
| Time-ordered data points | Yes |
| Subgroup ID / label on X-axis | Yes |
| Spec limits (USL/LSL) on chart | NO — spec limits go on capability/histogram, not on the control chart |
| Out-of-control point markers | Yes — minimum WE Rule 1 (point beyond 3-sigma) |
| Chart title (part name, characteristic, operation) | Yes |
| Sample size (n) noted | Yes |
| Date range | Yes |

### Capability indices

- **Cpk** is the primary index for ongoing production. PPAP Level 3
  requires Cpk ≥ 1.33 for initial studies, ≥ 1.67 preferred.
- **Ppk** for preliminary process studies before stability is
  demonstrated.
- **Cp / Pp** show potential — nice-to-have; Cpk/Ppk are what customers
  demand.
- Indices typically appear in a **summary table** alongside the chart,
  not overlaid on the control chart itself.
- **Compute at report time** from data + spec limits. Do not store.

### Out-of-control rules

Most shop floor SPC implements **Western Electric rules 1-4** by
default; Nelson rules 5-8 are configurable extensions. Full 8-rule
Nelson causes alert fatigue.

**v1 implementation:** WE Rule 1 (beyond control limits) + Rule 4
(8 points same side of CL). Catches spikes and shifts — the two
things operators actually care about. Defer rules 2-3 and Nelson
extensions.

### Subgroups vs individuals

Rational subgroups must be defined at **data collection time** based
on process knowledge ("5 consecutive parts from same setup"). They
**cannot** be derived from time-bucketing — production pace varies
and bucket boundaries cut subgroups in half.

### Histogram + normal curve

Standard companion to control charts in PPAP submissions and formal
capability studies. Separate panel/page, not on the control chart
itself. Minitab and JMP generate them as part of a "Capability
Sixpack" (X-bar + R + histogram + normal probability plot +
capability indices).

**v1:** include simple histogram with spec lines. Defer normal curve
overlay and probability plot.

### MSA / Gage R&R

MSA (Gage R&R) is a **prerequisite** for valid SPC per IATF 16949 and
PPAP — measurement system must have GRR ≤ 10% (ideal) or ≤ 30%
(acceptable). However, GRR results are **not shown on the SPC chart
itself** — separate document referenced in the control plan. Defer.

### Schema gaps before this can ship credibly

- **`StepExecutionMeasurement.subgroup_id`** — essential, cannot be
  derived from time-bucketing
- Decision: SPC adapter queries `StepExecutionMeasurement` (production
  data, time-ordered), not `MeasurementResult` (after-the-fact
  inspection). Filter by `measurement_definition__spc_enabled=True`.
- Optional: gage ID / MSA status reference field on
  `MeasurementDefinition` (v2)

### Don't include (defer past v1)

- Full 8-rule Nelson implementation (WE Rule 1 + 4 covers ~90% of
  real detections)
- X-bar/S charts (rare at n>9 on shop floor)
- Attribute charts (p, np, c, u)
- Normal probability plot (academic)
- Normal curve overlay on histogram (nice but not blocking)
- MSA/GRR on the SPC report (separate document)

### v1 ship scope

| Feature | v1 | v2 |
|---------|----|----|
| X-bar/R chart | Ship | — |
| I-MR chart | Ship | — |
| UCL/CL/LCL lines | Ship | — |
| OOC markers (Rule 1 + Rule 4) | Ship | Full Nelson |
| Cpk/Ppk summary box | Ship | Cp/Pp |
| Histogram with spec lines | Ship (simple) | Normal overlay |
| `subgroup_id` schema | Ship | — |
| X-bar/S | Defer | v2 |
| Attribute charts | Defer | v2+ |
| Normal probability plot | Defer | Maybe never |
| MSA/GRR reference | Defer | v2 |

This covers PPAP submission requirements and real shop floor needs.

### Sources

- [AIAG SPC-3 Manual](https://www.aiag.org/training-and-resources/manuals/details/SPC-3)
- [SPC Chart Types: X-bar R vs I-MR](https://eureka.patsnap.com/article/spc-chart-types-x-bar-r-vs-individual-moving-range-i-mr)
- [Nelson vs Western Electric Rules](https://www.parsec-corp.com/blog/nelson-vs-western-electric)
- [Process Capability Guide (1Factory)](https://www.1factory.com/quality-academy/guide-process-capability.html)
- [Cp/Cpk Formulas and Interpretation](https://www.superengineer.net/blog/spc-cp-cpk)
- [MSA Acceptance Criteria](https://www.spcforexcel.com/knowledge/measurement-systems-analysis-gage-rr/acceptance-criteria-for-msa/)
- [Minitab SPC Control Charts](https://support.minitab.com/en-us/minitab/help-and-how-to/quality-and-process-improvement/control-charts/supporting-topics/basics/understanding-control-charts/)

---

## Process Flow Diagram

Visual representation of the manufacturing process. PPAP Element #5.
Created first — its operation numbers cascade into the PFMEA and
Control Plan.

> **Versioning required for PPAP submission.** The PFD is a living
> document operationally but when submitted for PPAP it must be a
> point-in-time snapshot. Regenerating a PPAP's PFD later must
> reproduce the exact process DAG that was in effect at submission.
>
> **Good news:** `SecureModel` (the base class most models inherit
> from) already provides `version`, `previous_version`, and
> `is_current_version` fields. The versioning infrastructure is
> already in place — each edit can create a new version row with
> `previous_version` chain preserving history.
>
> What's still needed for PPAP lock:
> - Verify `Process`, `ProcessStep`, `StepEdge` properly create new
>   versions on edit (not just overwrite). The `SecureModel.new_version()`
>   method exists but may not be wired in to DAG editing flows.
> - PPAP submission records a specific `version` of the root `Process`
>   so regeneration reads from that version, not the current one
> - Adapter accepts an optional `version` param; defaults to current
>   (live view), specific version for PPAP

**Required elements:** Operation steps, inspection/verification
points, decision/test gates (pass/fail), storage symbols, transport/
material movement, rework/repair feedback loops, scrap disposition
paths, start/end terminators. Must show all processes including
special and outsourced.

**Per operation box:** Operation number (Op 10, 20, 30), description,
cross-reference to PFMEA/drawings, product and process
characteristics (flag special/key chars with symbols), equipment used.

**Symbols:** ISO 5807 or ASME — AIAG doesn't mandate one set.
Rectangle (process), diamond (decision), triangle (storage), oval
(terminator), arrow (flow).

**Key rules:**
- Must show rework/scrap paths, not just the happy path
- Scrap/rework material must move counter to workflow direction
- Operation numbers must be identical across PFD, PFMEA, and Control
  Plan — mismatches are a top audit finding

**Signatures:** QE + Process Engineer + APQP team leader. Customer
may require sign-off as part of PPAP.

**Format:** Landscape, typically 11x17 for complex flows. Left-to-right
or top-to-bottom. Header with part name/number, revision, date,
prepared by, page X of Y.

**Sources:**
- [Super Engineer - Process Flowchart](https://www.superengineer.net/blog/tools-process-flowchart)
- [AutomotiveQual - Visualize Production Process Flow](https://www.automotivequal.com/flowchart-how-to-visualize-production-operations/)

---

## Control Plan

Defines how each characteristic is controlled during production.
PPAP Element #7. Operationalizes the PFMEA — the PFMEA identifies
risks, the Control Plan specifies how to detect and react.

> **Versioning required for PPAP submission.** Same issue as Process
> Flow Diagram: the Control Plan is a living document but must be a
> point-in-time snapshot for PPAP. The underlying models (`Process`,
> `Steps`, `StepMeasurementRequirement`, `MeasurementDefinition`,
> `SamplingRule`, `Equipments`) all inherit from `SecureModel` which
> provides `version`, `previous_version`, and `is_current_version`.
>
> Same ship path as PFD: verify edit flows create new versions via
> `SecureModel.new_version()` rather than overwriting, then let the
> adapter accept an optional `version` param for PPAP-locked
> regeneration. Until then, buildable as a live operational view.

**Header:** Part number + change level, part name, organization/plant,
control plan number, phase (Prototype / Pre-Launch / Production /
Safe-Launch), core team, dates (orig/rev), customer engineering +
quality approval signatures.

**Body columns (per row, AIAG CP-1 2024 edition):**

1. Part/Process Number
2. Process Name / Operation Description
3. Machine, Device, Jig, Tools
4. Characteristic Number
5. Product Characteristic
6. Process Characteristic
7. Special Characteristic Classification (CC/SC)
8. Product/Process Specification / Tolerance
9. Evaluation / Measurement Technique
10. Sample Size
11. Sample Frequency
12. Control Method
13. Reaction Plan
14. RESP / Owner (new in 2024)

**Key rules:**
- One row per characteristic per operation — product and process
  characteristics must be **separate rows** (combining is a top audit
  finding)
- Operation numbers must match PFD and PFMEA exactly
- Reaction plan must be specific (containment + stop production +
  return-to-control), not generic
- Pass Through Characteristics get their own rows (2024 requirement)
- Must be reviewed/updated whenever PFMEA changes

**Phases:** Prototype → Pre-Launch → Production → Safe-Launch (new
2024, heightened controls during ramp).

**Format:** The AIAG form is guidance, not mandated. All IATF 16949
Annex A content must be present regardless of layout. Most OEM CSRs
effectively mandate the AIAG form as-is. Excel is the industry
standard format for the working document; PDF for the signed/filed
version.

**Signatures:** Customer Engineering Approval, Customer Quality
Approval, Supplier Quality Approval, Other (per CSR).

**Sources:**
- [Super Engineer - Control Plan Rules](https://www.superengineer.net/blog/apqp-control-plan)
- [Quality Magazine - The AIAG Control Plan Manual](https://www.qualitymag.com/articles/98156-the-aiag-control-plan-manual)

---

## Job Ticket / Routing Sheet

Forward-looking instruction document that travels with WIP. Companion
to the Part Traveler (which is the backward-looking history record).

**Required fields:** Work order number, part number + revision, qty,
operation sequence (Op 10/20/30) with work center per op, setup and
run time per op, drawing/spec references, tooling/fixture callouts.

**Signatures:** Typically unsigned — it's an instruction. Supervisor
may initial to authorize release to floor.

**Key rule:** Operations listed in sequence order; each op references
a single work center.

**Sources:**
- [Katana - Routing Manufacturing](https://katanamrp.com/blog/routing-manufacturing/)
- [Sage X3 - Routing Sheet](https://online-help.sagex3.com/erp/12/en-us/Content/OBJ/ARP_FICHSUI.htm)

---

## Production Summary / Daily Report

End-of-shift summary. Printed and signed.

**Required fields:** Date, shift, line/cell, supervisor. Planned vs
actual output (qty good, qty defective). Downtime events (duration +
reason code). Scrap/rework count. Labor hours.

**Signatures:** Shift supervisor signs; plant/production manager may
countersign.

**Key rule:** Planned-vs-actual comparison is the core structure —
every line shows target, actual, variance.

**Sources:**
- [Kladana - Daily Production Report Template](https://www.kladana.com/blog/mrp/production-report-template/)
- [SafetyCulture - End of Shift Report](https://safetyculture.com/checklists/end-of-shift-report/)

---

## Shift Handover Report

Outgoing shift to incoming shift. Printed and dual-signed.

**Required fields:** Outgoing/incoming shift ID + date/time. Equipment
status (running, down, in maintenance). Open issues / abnormalities.
Safety concerns. Pending tasks for incoming shift.

**Signatures:** Outgoing shift lead signs out; incoming shift lead
countersigns acknowledging receipt. Dual-signature is the defining
feature.

**Sources:**
- [Smartsheet - Shift Report Templates](https://www.smartsheet.com/content/shift-report-templates)
- [Documentero - Shift Handover Report](https://documentero.com/templates/manufacturing-quality/document/shift-handover-report/)

---

## Part ID Label / WIP Tag

Label printed and stuck on parts or bins during production. High
daily volume.

**Required fields:** Part number + revision, work order number, qty in
container, current operation / inspection status, barcode or QR
encoding the above.

**Signatures:** None — it's a label. QC may stamp/sticker for
inspection status.

**Key rule (ISO 9001 8.5.2):** Label must identify both the *product*
and its *inspection/test status* — two separate identification
requirements per the standard.

**Sources:**
- [The 9000 Store - Identification and Traceability](https://the9000store.com/iso-9001-2015-requirements/iso-9001-2015-operational-requirements/identification-traceability/)
- [Brady - Traceability in Manufacturing](https://www.bradyid.com/intelligent-manufacturing/traceability-in-manufacturing)

---

## BOM Report

Printed bill of materials for shop floor reference or customer
submittal.

**Required fields:** Parent assembly part number + revision. Per child
component: part number, description, qty per assembly, unit of
measure. BOM level for indented/multi-level BOMs.

**Signatures:** Typically unsigned for shop reference. Engineering
signs the master BOM during release in PLM/ERP.

**Key rule:** Indented (hierarchical) structure — each sub-assembly
level indented under its parent. Level 0 = finished good.

**Sources:**
- [NetSuite - Bill of Materials Guide](https://www.netsuite.com/portal/resource/articles/erp/bill-of-materials-bom.shtml)
- [Duro Labs - Bill of Materials Example](https://durolabs.co/blog/bill-of-materials-example/)

---

## Scrap & Rework Report

Periodic summary of scrap/rework events. Printed daily or weekly.

**Required fields:** Date, shift, department/line. Per event: part
number, work order, qty scrapped or reworked, reason/disposition code,
cost impact. Corrective action reference if any.

**Signatures:** Operator or inspector who dispositioned signs;
supervisor approves (especially for high-value scrap).

**Key rule:** Every event needs a reason code — this drives Pareto
analysis. Without coded reasons, the report has no analytical value.

**Sources:**
- [Documentero - Scrap Material Report](https://documentero.com/templates/manufacturing-quality/document/scrap-material-report/)
- [WilloWare - Scrap Reporting](https://willoware.com/online/mfg-powerpack-manual/scrap-reporting/)

---

## Remanufacturing / Core Teardown Report

Core receipt through disassembly with per-component condition grading
and yield summary.

**Required fields:** Core receipt info (tag/serial, source, date).
Disassembly BOM (components expected). Per component: condition grade
(Reuse / Repair / Scrap), defect observations. Yield summary (counts
by grade).

**Signatures:** Teardown technician signs per-component assessments;
QC inspector countersigns overall disposition.

**Key rule:** 100% inspection is mandatory — unlike new-part
manufacturing where sampling is acceptable, remanufacturing requires
every component individually inspected and graded.

**Sources:**
- [Springer - Inspection in Remanufacturing](https://link.springer.com/article/10.1186/2210-4690-3-7)
- [Western Computer - 365REMAN](https://www.westerncomputer.com/365reman/)

---

## Calibration Certificate

Single calibration event record for one instrument.

**Required fields:** Certificate number, issue date, calibration date.
Instrument ID (description, manufacturer, model, serial). Calibration
procedure reference, environmental conditions. Measurement results
with declared uncertainty per test point. Reference standards with
NIST traceability statement. As-found / as-left readings.

**Signatures:** Calibration technician; reviewing/approving authority.

**Key rule (ISO 17025 7.8.2):** Must include "end of certificate"
marker so the reader knows no pages are missing.

**Sources:**
- [Quality Magazine - How to Read ISO 17025 Calibration Certificates](https://www.qualitymag.com/articles/98235-how-to-read-and-interpret-iso-iec-17025-calibration-certificates)
- [LabCalibrate - Calibration Certificate Requirements](https://labcalibrate.com/calibration-certificate-requirements)

---

## Calibration Due Report

Equipment list sorted by due date. Published monthly.

**Required fields:** Equipment ID, description, location. Last cal
date, next due date, cal interval. Status flag (current / due /
overdue). Responsible person or department is common practice but not
required by ISO 9001 7.1.5 — the standard requires organizational
responsibility for the calibration program, not a per-equipment field.

**Signatures:** Quality Manager reviews/approves. No per-item
signatures.

**Key rule:** Sorted by due date ascending — overdue items first.

**Sources:**
- [ISO 9001 Checklist - Calibrated Equipment Procedure](https://www.iso-9001-checklist.co.uk/calibrated-equipment-procedure.htm)
- [PresentationEZE - Calibration Requirements](https://www.presentationeze.com/blog/calibration-requirements/)

---

## Training Record

Per-employee training history.

**Required fields:** Employee name, ID, job title, department.
Training topic/course, date completed, duration, trainer/provider.
Assessment result or competency evaluation (pass/fail or score).
Certification expiry date if applicable.

**Signatures:** Employee (acknowledging attendance), Trainer
(confirming delivery), Supervisor (confirming competency).

**Key rule (ISO 9001 7.2):** Must demonstrate *effectiveness* of
training, not just attendance — evidence of competence, not just a
sign-in sheet.

**Sources:**
- [ISO Certification US - Training Record](https://www.iso-certification.us/iso-9001-certification/documents-records/training-record.html)
- [Advisera - Training Record Template](https://advisera.com/9001academy/documentation/training-record/)

---

## CAPA Report

Full corrective/preventive action report. Not 8D-structured — a
general CAPA dump with tasks, RCA, and verification.

**Required fields:** CAPA number, date opened, source (audit, NCR,
complaint). Problem description (what, when, where, impact). Root
cause analysis (method + findings). Action items with owner, target
date, completion date. Effectiveness verification results + date.

**Signatures:** Initiator opens; Quality Manager approves RCA and
actions; Quality Manager or QRB closes after effectiveness
verification.

**Key rule:** Cannot be closed until effectiveness verification is
documented with evidence showing the problem has not recurred over a
defined monitoring period.

**Sources:**
- [The FDA Group - Definitive Guide to CAPA](https://www.thefdagroup.com/blog/definitive-guide-to-capa)
- [BPR Hub - CAPA Report Writing Guide](https://www.bprhub.com/blogs/capa-report-writing-guide)

---

## Deviation Request / Use-As-Is

Request to accept nonconforming product without rework.

**Required fields:** Deviation/NCR number, date, affected part
number(s) + qty. Specification requirement vs actual condition.
Reason/root cause. Disposition decision. Engineering justification
that the deviation does not affect form, fit, or function.

**Signatures:** MRB panel — at minimum **Engineering** (technical
acceptability) + **Quality** (QMS compliance). Customer approval if
contractually required.

**Key rule:** Use-as-is requires engineering sign-off — quality
cannot approve alone.

**Sources:**
- [Tulip - Material Review Board](https://tulip.co/blog/material-review-board/)
- [JELD-WEN Deviation Request Process (PDF)](https://www.corporate.jeld-wen.com/~/media/Files/J/Jeld-Wen-Corp/working-with-suppliers/op05-deviation-request-process-rev-b.pdf)

---

## Quarantine / Hold Tag

Label physically attached to quarantined material.

**Required fields:** Tag number (unique), date applied. Part number,
serial/lot/batch, qty. Description of defect or reason for hold.
NCR/NCMR reference number. Person who applied the tag.

**Signatures:** Applied by the person who identified the issue.
Released only by Quality after disposition is complete.

**Key rule:** Tag must remain physically attached until disposition is
complete and Quality authorizes removal — it's a physical blocker,
not just a record.

**Sources:**
- [SG Systems - Material Quarantine](https://sgsystemsglobal.com/glossary/material-quarantine/)
- [GMP Labeling - Quarantine Labels](https://gmplabeling.com/stock-labels/quality-control-labels/quarantine-labels/)

---

## ECN / ECO Report

Engineering change notice/order. Printed and distributed to shop
floor, filed as quality record.

> **Model dependency.** The ECO report is the *output* of a change
> management workflow, not just a standalone document. The system
> needs an `EngineeringChangeOrder` model (or similar) that:
>
> - Has its own numbering sequence (ECO-YYYY-######)
> - Links to affected `PartTypes` (part numbers / drawing numbers)
> - Links to affected `BOM` revisions, `Process` routings, `Documents`
> - Defines effectivity (date, serial, or lot cutover)
> - Specifies disposition of existing WIP / finished goods / field
>   inventory
> - Triggers downstream updates: BOM revision bump, process routing
>   change, `TrainingRequirement` creation for affected operators
> - Routes through `ApprovalRequest` (ECO type already exists) for
>   cross-functional sign-off
>
> The pieces exist (`ApprovalRequest` with ECO type, `Documents` with
> versioning, `BOM` with revision + status, `Process` + `ProcessStep`,
> `TrainingRequirement`), but the **change order entity that ties them
> together** does not. Until it exists, ECO is a DMS doc export with
> approval, not a system-generated report. This also applies to PCO
> (Process Change Order) and PCN (Process Change Notice) variants.

**Required fields:** ECN/ECO number, date, originator + department.
Affected part numbers, drawing numbers, document list. Description
of change + reason. Effectivity (date, serial number, or lot from
which change applies). Disposition of existing WIP, finished goods,
and field inventory.

**Signatures:** Originator (Engineering), then cross-functional:
Engineering Manager, Quality, Manufacturing, Purchasing.

**Key rule:** Must define effectivity clearly — the exact point
(date, serial, or lot) where old revision stops and new starts.
Ambiguous effectivity is a major audit finding.

**Sources:**
- [PTC - What Is an Engineering Change Notice](https://www.ptc.com/en/blogs/plm/what-is-an-engineering-change-notification)
- [Wikipedia - Engineering Change Order](https://en.wikipedia.org/wiki/Engineering_change_order)

---

## Schema-prep summary

Aggregated from the per-report sections, the high-priority schema work
that unblocks multiple reports:

### Cross-report schema additions

| Field / Model | Reports affected |
|---------------|------------------|
| `PartTypes.drawing_number` + `drawing_revision` | CofC, Traveler, Inspection, FAI |
| `Parts.material_lot` (or WO) + `material_spec` | Traveler, IATF compliance |
| `Orders.customer_po_number` (+ revision/line) | CofC, Inspection, Traveler |
| `ProcessStep.operation_number` (verify `sequence` exposure) | Traveler |
| `StepExecutionMeasurement.subgroup_id` | SPC (essential) |

### Per-report blockers

| Report | Schema work |
|--------|-------------|
| **NCR** (shipped, gaps) | Add `quantity_affected` / `quantity_inspected` / `quantity_defective`, `root_cause_summary`, `capa_reference`, `detection_source` enum, `specification_violated`, `lot_or_batch_number`, `disposition_authority`, `estimated_cost` + `cost_type`; add `VOIDED` state + `REGRADE` disposition; make customer signature line in template conditional on `requires_customer_approval` |
| **CofC** | New `CertificateOfConformance` model (per-shipment, own numbering, `superseded_by`); deviations field; remove customer signature block |
| **Traveler** | `StepExecution.inspected_by` FK, `StepExecution.notes` TextField, `Steps.work_instruction_ref`, `TravelerRelease` model or fields |
| **8D** | D1 team M2M with roles, drop polymorphic FiveWhys/Fishbone (combine), add `escape_point` to RCA, `PreventionAction` model for D7, enrich D6 verification, `capa_type` gate enum |
| **Inspection** | `disposition` enum, AQL parameter group, gage ID per measurement, `inspection_type` enum |
| **SPC** | `subgroup_id` on StepExecutionMeasurement |

### v1 scope cuts (over-engineered)

- Customer signature block on CofC (non-standard)
- Per-part QualityReports embed on CofC (that's a CofA)
- 3D heatmaps on Inspection Report
- Live SPC overlay per row on Inspection Report
- Polymorphic FiveWhys/Fishbone (combine, don't pick)
- Full 8-rule Nelson SPC implementation
- X-bar/S, attribute charts, normal probability plot
