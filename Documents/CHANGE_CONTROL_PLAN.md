# Change Control Plan

## Status: Approved for Phase 1 build

Design for change-control infrastructure that wraps controlled changes (process, document, eventually BOM) and routes them through a three-stage Request → Order → Notice pattern matching IATF 16949 and AS9100D expectations. Provides the manufacturing-side change governance layer; complements (does not replace) PLM systems that own engineering-side design management.

This document is written **before** the in-flight WO migration ("Path A") work to ensure the migration feature lands inside a coherent change-control story rather than as a one-off bolt-on. Path A becomes the implementation step inside the PCO (Process Change Order) phase.

## Explicitly Out of Scope: FDA / Medical Device Compliance

**This system is not designed for, validated against, or marketed to FDA-regulated medical device manufacturers.** This is a foundational scoping decision, not a phase-deferred feature.

Specifically, this design **does not satisfy and is not intended to satisfy**:

- **21 CFR Part 820** (Quality System Regulation for medical devices)
- **21 CFR Part 11** (Electronic records and electronic signatures with reverification per signing event, including password reverification, intent attestation, and meaning-of-signature recording)
- **ISO 13485** (Medical device QMS)
- **ISO 14971** (Medical device risk management with structured severity / probability / detection scoring)
- **EU MDR / IVDR** (European medical device regulations)
- **510(k) / PMA submission workflows**
- **Design History File (DHF) / Device Master Record (DMR) / Device History Record (DHR)** structured documentation requirements

Customers in FDA-regulated medical device manufacturing **must not rely on this system as their primary change-control tool of record**. They should continue using a validated eQMS (MasterControl, Sparta TrackWise, ETQ Reliance, Greenlight Guru, etc.) for compliance-critical change management.

**Why this is a hard scope boundary, not a roadmap item:**

- FDA Part 11 reverification at every signing event imposes UX requirements (password re-entry per signature, explicit intent attestation, audit-trail-tamper-evident storage) that conflict with the lighter `ApprovalRequest` infrastructure this design relies on.
- FDA-regulated medical device customers expect formal computer system validation (CSV) including IQ / OQ / PQ documentation, validation test scripts, and ongoing validation maintenance. We are not pursuing CSV.
- ISO 14971 structured risk management requires specific data structures (severity × probability × detection scoring, hazard analysis traceability) that are intentionally absent from this design.
- Defending FDA compliance claims requires regulatory expertise, audit experience, and ongoing investment well beyond Phase 5 expansion budget.
- Mis-positioning the system to medical device customers creates real liability exposure if a compliance failure traces back to our tooling.

This out-of-scope determination applies to **all phases** of the change-control plan including Phase 5 expansions. If FDA compliance ever becomes a target market, it requires a separate dedicated workstream — not an incremental extension of this design — likely including a separate validated build, separate certification, and separate sales motion.

The supported regulatory targets are explicitly:

- **ISO 9001 8.5.6** (general manufacturing — SIMPLIFIED mode)
- **IATF 16949 8.5.6.1** (automotive — REGULATED mode)
- **AS9100D 8.5.6** (aerospace and defense — REGULATED mode)

## Goals

- Three-stage change-control pattern matching industry conventions: Request (proposal) → Order (authorization) → Notice (communication).
- Concrete models per change type — `ProcessChangeRequest`, `ProcessChangeOrder`, `ProcessChangeNotice` for process changes; same triplet for document changes in Phase 2 — sharing scaffolding via abstract base classes.
- Customer-facing terminology: PCR / PCO / PCN, DCR / DCO / DCN. No abstract "change request" framing in user-facing surfaces.
- Per-stage approval routing through existing `ApprovalRequest` infrastructure — no new approval engine.
- PCO implementation step triggers existing `create_new_process_version` (Pattern C: DRAFT version created at PCO authoring, edited via existing process editor, approved as part of PCO approval, flipped to APPROVED at implementation).
- Disposition of in-flight production captured on the PCO (the artifact that authorizes the implementation).
- Effective date and customer-notification flags on PCO for PPAP / customer flow-down compliance.
- Effectiveness verification at PCN closure.
- Per-tenant **simplified mode** (auto-generates downstream artifacts) vs. **regulated mode** (explicit author-and-approve at each stage with separation-of-duties enforcement) — same data model, different UX gates.
- Auditable end-to-end via `auditlog` and existing approval signature trail.
- ISO 9001 8.5.6 / IATF 16949 8.5.6.1 / AS9100D 8.5.6 baseline compliance.

## Non-Goals

- **Full PLM.** No CAD management, no engineering BOM editing, no item-master ownership. We complement Windchill / Teamcenter / Arena / Agile.
- **FDA / medical device compliance** (21 CFR 820, ISO 13485, ISO 14971, 21 CFR Part 11 reverification). Not chasing this market in Phase 1+2. Existing `ApprovalRequest` signatures are sufficient for AS9100/IATF without Part 11 hardening.
- **Engineering Change Request (ECR / ECO / ECN) as an originating workflow.** Engineering changes originate in PLM. We support inbound ingestion only — Phase 4 if customers ask.
- **Supplier portals.** Out of scope.
- **Customer notification automation.** We flag PPAP-triggering changes and provide export-ready evidence; the actual customer submission is manual.
- **Training tracking integration.** Phase 5 territory.
- **FMEA / Control Plan editing tools.** Link out for now.
- **Distribution list management.** Existing `NotificationRule` infrastructure handles audience routing per event type; no per-PCN audience field in Phase 1.
- **Acknowledgment tracking.** Deferred to Phase 5 — acknowledgment is "best practice / strong evidence" but not strictly required by AS9100D 8.5.6 or IATF 16949 8.5.6.1 baseline.
- **Parallel PCRs against the same process.** Phase 1 is serial only (one open PCR per process). Phase 5 parallel upgrade is purely additive, no structural lock-in.
- **eQMS-grade additions** (tiered classification with conditional workflows, structured FMEA-lite risk fields with S × P × D, separate verification + validation phases with effectiveness metrics, competency-gated approvers, audit-package PDF export). Phase 5 Pro-tier expansion when customer demand surfaces.

## The Three-Stage Pattern

Every change-control artifact in regulated industries (IATF 16949, AS9100D) decomposes into three distinct documents with different purposes, audiences, and signatories:

| Stage | Internal name | Customer term (process) | Customer term (document) | Purpose |
|---|---|---|---|---|
| Request | `ProcessChangeRequest` | PCR | DCR | Proposal / case file: what's being proposed, why, initial impact, risk |
| Order | `ProcessChangeOrder` | PCO | DCO | Authorization: how to implement, responsibilities, effective date, in-flight disposition |
| Notice | `ProcessChangeNotice` | PCN | DCN | Communication: distributable notice, effectiveness verification |

Each stage:

- Has its own approval chain (often different signatories per stage).
- Produces its own auditable record.
- Has its own lifecycle state machine.
- Has its own typed fields appropriate to its purpose.
- Can be exported as its own document (PDF artifact via Typst report adapter).

In smaller / less-regulated organizations, these three stages collapse into a simpler workflow. The data model still records all three artifacts, but downstream stages auto-generate from approved upstream artifacts ("simplified mode"). Regulated tenants enable explicit author-and-approve gates at each stage ("regulated mode").

**Cardinality:** Phase 1 is constrained to 1:1:1 (one PCR → one PCO → one PCN). Multi-PCO / multi-PCN cardinality is deferred to Phase 5.

## Architectural Framing

The `change_control` app sits above `Tracker` and depends on it. It does NOT live inside `Tracker`. Reasons:

1. Different domain — change governance is orthogonal to manufacturing operations.
2. Different lifecycle — change requests are slow-moving governance artifacts, not real-time production data.
3. Different audience — quality engineers and document controllers, not operators.
4. May eventually wrap non-Tracker objects (supplier qualifications, equipment changes).

```
change_control/                          ← new app
  models/
    base.py                              ← abstract base classes
    process_change.py                    ← PCR / PCO / PCN
    document_change.py                   ← DCR / DCO / DCN  (Phase 2)
  services/
    process_change.py                    ← PCR → PCO → PCN lifecycle
    document_change.py                   ← Phase 2
    impact_analysis.py
    sequencing.py                        ← per-tenant per-year artifact_number generator
  viewsets/
    process_change.py                    ← three viewsets: PCR, PCO, PCN
    document_change.py                   ← Phase 2
  serializers/
    process_change.py
    document_change.py                   ← Phase 2
  templates/
  migrations/
```

## Domain Model

### Abstract Base Classes

```python
class BaseChangeArtifact(SecureModel, VoidableModel):
    """Common scaffolding for any change-control artifact."""
    artifact_number = CharField(max_length=32)
    # PCR-2026-0001, PCO-2026-0001, PCN-2026-0001, etc.
    # Per-tenant, per-artifact-type sequence with annual reset.
    status = CharField(choices=...)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    created_by = ForeignKey(User, on_delete=SET_NULL, null=True, related_name='+')
    data_origin = CharField(choices=[('NATIVE', 'Native'), ('IMPORTED', 'Imported')],
                             default='NATIVE')

    class Meta:
        abstract = True


class BaseChangeRequest(BaseChangeArtifact):
    """Shared fields for any *Request artifact (PCR / DCR)."""
    title = CharField(max_length=255)
    proposed_change = TextField()
    justification = TextField()
    risk_analysis = TextField()
    priority = CharField(choices=PRIORITY_CHOICES, default='NORMAL')
    submitted_at = DateTimeField(null=True, blank=True)
    submitted_by = ForeignKey(User, on_delete=SET_NULL, null=True, related_name='+')
    rejected_reason = TextField(blank=True, default='')
    customer_notification_required = BooleanField(default=False)
    superseded_by_request_ct = ForeignKey(ContentType, null=True, blank=True,
                                            on_delete=SET_NULL)
    superseded_by_request_id = UUIDField(null=True, blank=True)
    # GFK: when this PCR is rejected and a new PCR is filed as a retry,
    # this points forward to the new attempt. Optional.

    class Meta:
        abstract = True


class BaseChangeOrder(BaseChangeArtifact):
    """Shared fields for any *Order artifact (PCO / DCO)."""
    implementation_plan = TextField()
    effective_date = DateField(null=True, blank=True)
    approved_at = DateTimeField(null=True, blank=True)
    approved_by = ForeignKey(User, on_delete=SET_NULL, null=True, related_name='+')
    implemented_at = DateTimeField(null=True, blank=True)
    implemented_by = ForeignKey(User, on_delete=SET_NULL, null=True, related_name='+')

    class Meta:
        abstract = True


class BaseChangeNotice(BaseChangeArtifact):
    """Shared fields for any *Notice artifact (PCN / DCN)."""
    notice_content = TextField()
    released_at = DateTimeField(null=True, blank=True)
    released_by = ForeignKey(User, on_delete=SET_NULL, null=True, related_name='+')
    closure_evidence = TextField(blank=True, default='')
    closed_at = DateTimeField(null=True, blank=True)
    closed_by = ForeignKey(User, on_delete=SET_NULL, null=True, related_name='+')

    class Meta:
        abstract = True
```

### Concrete Models — Process Change (Phase 1)

```python
class ProcessChangeRequest(BaseChangeRequest):
    """PCR — proposal to change a manufacturing process."""
    target_process = ForeignKey('Tracker.Processes', on_delete=PROTECT,
                                 related_name='change_requests')
    baseline_version_id = UUIDField()
    # The Processes.id this PCR was proposed against. Captured at
    # submission time. Serial mode doesn't strictly need it (baseline
    # is always current), but recording it is a future-proofing move
    # for parallel mode (Phase 5) where rebasing requires the original
    # baseline.
    affected_workorders_snapshot = JSONField(default=list)
    # snapshot of {wo_id, erp_id, status, current_step_order, parts_count}
    # at submission time

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['target_process'],
                condition=Q(status__in=['DRAFT', 'SUBMITTED', 'UNDER_REVIEW',
                                          'APPROVED'])
                        & Q(is_voided=False),
                name='processchangerequest_one_open_per_process',
            ),
        ]


class ProcessChangeOrder(BaseChangeOrder):
    """PCO — authorization to implement an approved PCR."""
    request = OneToOneField(ProcessChangeRequest, on_delete=PROTECT,
                             related_name='order')
    draft_process_version = ForeignKey('Tracker.Processes', on_delete=PROTECT,
                                         null=True, blank=True,
                                         related_name='+')
    # The DRAFT version created during PCO authoring (Pattern C).
    # Edited through existing process editor. Flipped to APPROVED at
    # PCO implementation via existing approve_process service.

    # Migration disposition for in-flight WOs
    migration_disposition = CharField(choices=DISPOSITION_CHOICES,
                                       default='PENDING')
    # MIGRATE_ALL / MIGRATE_SELECTED / KEEP_ALL / PENDING
    migration_reason = TextField(blank=True, default='')
    migrated_workorder_ids = JSONField(default=list)
    # Path A migration events recorded in auditlog on WorkOrder.process changes


class ProcessChangeNotice(BaseChangeNotice):
    """PCN — distribution and effectiveness verification of an
    implemented PCO. Audience routing handled by existing NotificationRule
    on the PCN_RELEASED event."""
    order = OneToOneField(ProcessChangeOrder, on_delete=PROTECT,
                           related_name='notice')
```

### Concrete Models — Document Change (Phase 2)

Same pattern: `DocumentChangeRequest`, `DocumentChangeOrder`, `DocumentChangeNotice` extending the same abstract bases. Type-specific fields:

- `DocumentChangeRequest.target_document` (FK to `Documents`)
- `DocumentChangeOrder.draft_document_version` (FK to `Documents`, populated at PCO authoring)

## Lifecycle

Each concrete model has its own state machine.

### `ProcessChangeRequest` (PCR)

```
DRAFT → SUBMITTED → UNDER_REVIEW → APPROVED ──→ (PCO created)
                                  ↘ REJECTED  (terminal)
DRAFT / SUBMITTED → CANCELLED  (terminal)
```

- `DRAFT → SUBMITTED`: requires title, proposed_change, justification, risk_analysis, target_process. Snapshots `affected_workorders_snapshot` and captures `baseline_version_id` automatically.
- `SUBMITTED → UNDER_REVIEW`: reviewer claims request. Creates `ApprovalRequest` from tenant's `PCR_APPROVAL` template.
- `UNDER_REVIEW → APPROVED`: requires `ApprovalRequest` approval. Triggers PCO creation. In SIMPLIFIED mode, PCO auto-creates and auto-approves; in REGULATED mode, PCO created in DRAFT for explicit authoring.
- `UNDER_REVIEW → REJECTED`: any reviewer rejects with `rejected_reason`. Terminal. Retry requires a new PCR (optionally with `superseded_by_request` FK on the rejected one pointing forward).
- Cancellation by requestor or manager pre-approval.

### `ProcessChangeOrder` (PCO)

```
DRAFT → APPROVED → IN_IMPLEMENTATION → IMPLEMENTED ──→ (PCN created)
                                      ↘ CANCELLED  (terminal)
```

- `DRAFT`: auto-created from approved PCR. In SIMPLIFIED mode, auto-populates implementation_plan from PCR fields and auto-advances to APPROVED. In REGULATED mode, sits in DRAFT until an implementation owner authors and submits.
  - When PCO authoring begins (regulated) or auto-completes (simplified), the system creates a DRAFT process version copying current state and links it via `draft_process_version`. Author edits this DRAFT through the existing process editor (Pattern C).
- `DRAFT → APPROVED`: requires implementation_plan, effective_date, and a populated `draft_process_version`. Approval via `PCO_APPROVAL` template (different signatories than PCR — typically implementation owners). Separation of duties: PCO author cannot be the same user as the PCO approver.
- `APPROVED → IN_IMPLEMENTATION`: implementer triggers `approve_process` on the DRAFT version, flipping it to APPROVED.
- `IN_IMPLEMENTATION → IMPLEMENTED`: migration disposition decided (`MIGRATE_ALL` / `MIGRATE_SELECTED` / `KEEP_ALL`). Selected WOs migrated via Path A action (in-place update of `WorkOrder.process` to new version, audited via `auditlog`). Sets `implemented_at`, `implemented_by`. Triggers PCN creation.

### `ProcessChangeNotice` (PCN)

```
DRAFT → RELEASED → CLOSED  (terminal)
```

- `DRAFT`: auto-created from implemented PCO. In SIMPLIFIED mode, auto-populates `notice_content` from PCO + PCR + new version diff and auto-advances to RELEASED. In REGULATED mode, sits in DRAFT until communications/quality authors and releases.
- `DRAFT → RELEASED`: notice authored, formal release signature collected via `PCN_RELEASE` template. Triggers `PCN_RELEASED` notification event — audience routing handled by existing `NotificationRule` infrastructure. Separation of duties: PCN releaser cannot be the same user as the PCO approver.
- `RELEASED → CLOSED`: requires `closure_evidence` filled. Effectiveness verification. Explicit user action by quality manager.

## Simplified vs. Regulated Mode

A per-tenant configuration toggle: `change_control_mode` ∈ `{SIMPLIFIED, REGULATED}`. **Default for new tenants: SIMPLIFIED.**

| Behavior | Simplified | Regulated |
|---|---|---|
| Compliance equivalence | ISO 9001 8.5.6 baseline | AS9100D 8.5.6 + IATF 16949 8.5.6.1 baseline |
| PCR approval | ApprovalRequest (one signature) | ApprovalRequest (templated signatories) |
| PCO authoring | Auto-generated from approved PCR | Explicit author-and-submit |
| PCO approval | Auto-approved at creation | Explicit signature collection (different signatories) |
| Separation-of-duties enforcement | Off | On (PCO author ≠ approver, PCN releaser ≠ PCO approver) |
| PCN authoring | Auto-generated from implemented PCO | Explicit author-and-release |
| PCN release | Auto-released | Formal release signature |
| User experience | Two-stage (PCR → "implement" → PCN) | Three-stage (PCR → PCO → PCN) |
| Audit artifact | Three records, mostly auto-populated | Three records, fully authored |

Both modes produce the same audit trail. Regulated mode adds explicit gates and signatures at each stage. The data model is identical — auditors can pull all three artifacts regardless of mode, and SIMPLIFIED tenants can upgrade to REGULATED without data migration.

## Historical Data Import

Separate one-shot ingestion path for backfilling pre-existing change records from another system or paper records. Available in either mode.

- **`manage.py import_change_history`** management command (or admin-only API endpoint).
- Takes a CSV / JSON of historical change records.
- Creates PCR / PCO / PCN rows in CLOSED state with backdated timestamps.
- Records `data_origin = 'IMPORTED'` and historical approver names as text fields (no `ApprovalRequest` records — those approvals already happened in the source system).
- Skips the live workflow entirely (no notifications fire, no `create_new_process_version` call).
- Logs the import event itself in audit log for provenance.

This is **not** a tenant mode — it's a separate capability for one-shot data migration during onboarding. SIMPLIFIED is for ongoing ease-of-use; import is for backfill.

## Path A Migration Inside This Frame

Path A (in-flight WO migration) is **not** a standalone feature. It is the implementation step on a `ProcessChangeOrder`:

1. User creates a `ProcessChangeRequest` targeting an existing approved process.
2. Fills proposal, justification, risk analysis. `affected_workorders_snapshot` and `baseline_version_id` auto-populate.
3. Submits PCR. `ApprovalRequest` fires. Reviewers approve.
4. PCO is created (auto-populated in SIMPLIFIED, drafted by user in REGULATED). DRAFT process version created and linked via `draft_process_version`.
5. Implementation owner edits the DRAFT version through the existing process editor — adjusts steps, edges, tolerances, documents.
6. PCO approved (auto in SIMPLIFIED, separate signatory in REGULATED). Approver sees the actual version diff.
7. Implementer clicks "Implement." `approve_process` flips the DRAFT to APPROVED.
8. Implementer sees the affected WO list (from PCR snapshot, refreshed) and decides disposition: `MIGRATE_ALL` / `MIGRATE_SELECTED` / `KEEP_ALL` with reason.
9. Selected WOs are migrated (Path A action: `wo.process = new_version; wo.save()`). Each migration generates an audit row via `auditlog`. `migrated_workorder_ids` populated on PCO.
10. PCO transitions to IMPLEMENTED. PCN auto-created.
11. PCN released; notification fires via existing `NotificationRule` routing.
12. Effectiveness verified, PCN closed.

The migration UI from the earlier sketch (queue page, ticket detail) **goes away**. Migration is performed inside the PCO detail page's "Implementation" panel. Affected WOs surface as a checkbox list with bulk migrate / keep actions, audit rows generated per migration. No separate `ProcessMigrationTicket` model.

## Integration With Existing Systems

### Process Versioning (existing)

- `create_new_process_version()` and `approve_process()` are no longer called directly from the UI for tenants with change control enabled.
- New flow: PCR → approved PCR → PCO authoring (creates DRAFT version) → PCO approval → PCO implementation calls `approve_process()` internally.
- The `change_description` argument is sourced from PCR (`proposed_change` + `justification`).
- Backward compatibility: `create_new_process_version()` and `approve_process()` remain callable directly for management commands, migrations, and admin scripts. UI button "Create New Version" hidden when `change_control_enabled=True`.
- In-flight DRAFT versions at toggle time keep their existing path until approved or discarded. Only new versions created after toggling go through PCR.

### Document Versioning (existing) — Phase 2

- DCR → DCO → DCN wraps `Documents.create_new_version()` similarly.
- Phase 1 does not touch document versioning. Direct document version creation continues unchanged.

### Approval Workflow (existing)

- `ApprovalRequest` reused for signature collection at each stage.
- New `ApprovalTemplate` types: `PCR_APPROVAL`, `PCO_APPROVAL`, `PCN_RELEASE`.
- Per-tenant configuration: signatories per template (typically different roles per stage).

### Notifications (existing)

New event types in `NotificationEventType`:

- `PCR_SUBMITTED` (audience routing via existing NotificationRule)
- `PCR_APPROVED`
- `PCR_REJECTED`
- `PCO_AUTHORED` (regulated mode)
- `PCO_APPROVED`
- `PCO_IMPLEMENTED`
- `PCN_RELEASED`
- `PCN_CLOSED`

### Audit Log (existing)

- All three concrete models per type registered with `auditlog`.
- WO migration events visible via `WorkOrder.process` field change in auditlog.

### Permissions

New permissions in `change_control` app:

- `add_processchangerequest` — create PCRs (default: broad assignment to operator + engineer + supervisor groups; tenants narrow at their discretion via existing group permission infrastructure).
- `author_processchangeorder` — author PCO content in REGULATED mode (default: engineering + supervisor groups).
- `release_processchangenotice` — release PCNs in REGULATED mode (default: quality + document-control groups).
- View / list permissions broad by default.

### Tenant Configuration

- `change_control_enabled: bool` — feature flag. Default False. When false, existing direct version creation continues.
- `change_control_mode: 'SIMPLIFIED' | 'REGULATED'` — controls auto-generation vs. explicit author-and-approve gates. Default SIMPLIFIED for new tenants.
- Mode upgrade is a one-click admin action; no data migration. Downgrade also supported but unusual.

## Cross-Type Reporting

Cross-type queries (e.g., "show me all change activity in Q4") require unioning across concrete models. Phase 1 ships the Approach A pattern:

```python
def list_all_changes(*, tenant_id, since, until, status=None) -> list[dict]:
    """Union of PCR + DCR (+ future types) for tenant dashboard / audit reports."""
    pcrs = ProcessChangeRequest.objects.filter(...).values('id', 'artifact_number', ...)
    dcrs = DocumentChangeRequest.objects.filter(...).values('id', 'artifact_number', ...)
    return sorted(chain(pcrs, dcrs), key=lambda r: r['created_at'], reverse=True)
```

Used for:

- Quality dashboard: "open change activity by type"
- Audit export: "all changes in Q4 2026"
- Notification digest: "weekly change activity summary"

If cross-type queries become hot enough to matter, a denormalized `ChangeLogEntry` table can be added in Phase 3+. Defer until proven necessary.

## Implementation Phases

### Phase 1 — PCR / PCO / PCN process change control (this push)

- Abstract base classes (`BaseChangeArtifact`, `BaseChangeRequest`, `BaseChangeOrder`, `BaseChangeNotice`)
- Concrete models: `ProcessChangeRequest`, `ProcessChangeOrder`, `ProcessChangeNotice`
- Migration + auditlog registration
- Per-tenant per-type per-year `artifact_number` sequencing service
- Services for PCR, PCO, PCN lifecycle transitions (with separation-of-duties enforcement in REGULATED mode)
- Impact analysis service (process changes — affected WO snapshot)
- Integration with `create_new_process_version` / `approve_process` and `ApprovalRequest`
- Historical import management command (`import_change_history`)
- Viewsets, serializers, bulk endpoints (one set per concrete model)
- Frontend:
  - PCR queue page + detail page
  - PCO detail page with implementation panel (embedded migration UX, embedded process editor link for DRAFT version)
  - PCN detail page with closure surface
  - "Propose Change" entry-point on Process detail pages (replaces "Create New Version" when change control enabled)
  - PCRs surface on Process detail page (open + recent)
- New notification event types
- Tenant feature flag + simplified/regulated mode toggle

**Effort estimate: 11-13 working days. Roughly 3 weeks.**

### Phase 2 — DCR / DCO / DCN document change control

- Concrete models reusing abstract bases (`DocumentChangeRequest`, `DocumentChangeOrder`, `DocumentChangeNotice`)
- Document-specific impact analysis (downstream document chain)
- Integration with `Documents.create_new_version()`
- Frontend pattern replicated
- Cross-type dashboard surfaces

**Effort estimate: 5-7 working days incremental.**

### Phase 3 — Customer notification + cross-type reporting expansion

- PPAP-triggering change detection (heuristics on change_type + affected products + customer flow-downs for automotive OEMs)
- FAI re-trigger detection for AS9100 customer flow-downs (aerospace primes)
- Export-ready evidence package (PDF report adapter for full PCR + PCO + PCN bundle)
- Dashboard with cross-type KPIs (cycle time, approval time, effectiveness rates)

### Phase 4 — Inbound engineering change tracking

- `EngineeringChangeRecord` (single model — inbound, no internal three-stage lifecycle since approval already happened in PLM)
- Integration framework hook for PLM-originated ECNs
- Trigger downstream PCRs / DCRs from inbound ECN

### Phase 5 — eQMS-grade Pro-tier expansions (deferred until customer demand)

- Tiered change classifications with conditional workflows
- Structured FMEA-lite risk analysis (S × P × D = RPN)
- Verification + Validation as separate phases with effectiveness metrics
- Auto-computed effectiveness from QualityReport / WorkOrder data
- Typed change intents (modify, rollback, emergency, standardize)
- Competency-gated approvers (linked to training infrastructure)
- Multi-PCO / multi-PCN cardinality (1:N support)
- **Parallel PCRs against the same process** (drop unique constraint, add merge/rebase logic, conflict detection on shared fields, signature recollection workflow on rebase)
- Acknowledgment tracking (`Acknowledgment` model, ack-driven dashboards, signed acknowledgment artifacts)

## Future-Proofing Notes (For Phase 1 Implementation)

These small moves take negligible effort during Phase 1 and keep upgrade paths additive rather than retrofitting. Be on the lookout for similar small moves throughout implementation — the cost of a few minutes of forethought is consistently lower than the cost of refactoring later.

### Phase 5 parallel-PCRs upgrade — four moves baked into Phase 1

1. **Capture `baseline_version_id` on PCR at submission.** Records which `Tracker.Processes.id` this PCR was proposed against. Serial doesn't strictly need it (the baseline is always "current"), but recording it is required for parallel-mode rebasing. Already in the model definition above. Cost: ~5 minutes.

2. **Don't hard-code "current version" in DRAFT creation.** When PCO authoring spawns the DRAFT (Pattern C), base it on `pcr.baseline_version_id` rather than `process.current_version`. Same result for serial mode; correct behavior for parallel mode. Cost: 1 line of difference.

3. **Make the unique constraint a one-line migration.** Use Django's `UniqueConstraint(condition=Q(...))` partial unique constraint pattern as shown above. Drop in a single migration when parallel ships. Already the natural pattern. Cost: zero (this is the right approach anyway).

4. **Don't assume single-DRAFT semantics in queries.** When listing DRAFT process versions for a process, write `Processes.objects.filter(previous_version=parent, status=DRAFT)` not `.get(...)`. Cheap defensive coding. Cost: query style discipline.

### General principle

When making a Phase 1 design choice, ask: *"What would change if we relaxed this constraint later?"* If the answer is "trivial / additive code only," the choice is fine. If the answer is "data migration / refactor across services," look for a 5-minute move that prevents the lock-in. Examples that may surface during build:

- **Status / priority enum values.** Add new values via Django choices migrations later — but if any code does `status == 'APPROVED'` literal-string comparisons rather than using the choices constant, those locations need refactoring. Always use the choices constant.
- **Cardinality assumptions.** `OneToOneField` is harder to relax than `ForeignKey` later. Use OneToOne only when the 1:1 invariant is genuinely permanent (PCR ↔ PCO is permanent for Phase 1 but loosens in Phase 5; using ForeignKey with a unique=True flag instead of OneToOneField makes the loosening trivial).
- **Tenant-vs-global scope.** Sequence numbers, defaults, configurations all should be per-tenant from day one even if Phase 1 has a single multi-tenant deployment.
- **Hard-coded role names.** "OPERATORS" / "QUALITY" / "ENGINEERS" should be drawn from a configurable source (group permissions, role tags) rather than string literals in service code.
- **Auto-numbering format hard-coding.** The `PCR-2026-0001` format should come from a sequencing service, not f-strings scattered across the code. Customers may want suffixes, prefixes, or different patterns; centralization makes this a config change.

Maintain a running "future-proofing log" as Phase 1 implementation progresses — when a small move is taken to preserve optionality, document it briefly so the rationale survives to whoever maintains the code later.

## Risks / Corners to Avoid

1. **Building a parallel approval engine.** `ApprovalRequest` already exists and works. Reuse it. Do not invent a new approval flow inside `change_control`.

2. **Building a parallel notification system.** Emit events through existing `notify()` calls. New event types in the existing catalog; not a separate notification stack. Audience routing via `NotificationRule`, not a new mechanism.

3. **Path A as a separate feature.** It's not. It's the implementation panel of PCO detail. Building it standalone first means duplicate UI surface and an awkward migration to the unified model later.

4. **Over-modeling the artifacts.** Resist adding fields for "rollback plan," "validation tests," "S/P/D scoring," etc. before customers ask. Free text covers most documentation needs; structure can be added per-customer later. eQMS-grade fields belong in Phase 5.

5. **Forcing all tenants onto the new flow.** The feature flag is non-negotiable. Existing tenants depending on direct version creation must continue to work without configuration.

6. **Auto-closing PCNs.** Closure should always be an explicit user decision with effectiveness verification. Auto-closure on time-out invites compliance failures.

7. **Cross-type abstraction creep.** It's tempting to add a polymorphic "all changes" model to make cross-type queries easier. Don't. Use union querysets in the reporting service. The benefit of typed concrete models is lost the moment we add a polymorphic abstraction over them.

8. **Multi-PCO / multi-PCN cardinality early.** Phase 1 constrains to 1:1:1. Customers asking for staged implementation or multi-audience distribution come in Phase 5. Adding the cardinality flexibility now bloats the data model and UI for no current value.

9. **Auto-numbering uniqueness across tenants.** Use a per-tenant sequence — not a global sequence. Two tenants both seeing `PCR-2026-0001` is correct; cross-tenant uniqueness is wrong.

10. **Treating SIMPLIFIED as historical import.** Distinct concerns: SIMPLIFIED is ongoing-operations-with-fewer-gates; import is one-shot historical-data-ingestion. Don't conflate.

## Compliance Mapping

| Standard | Clause | Requirement | How this design satisfies |
|---|---|---|---|
| ISO 9001 | 8.5.6 | Documented review of changes, authorizing person, necessary actions retained | PCR proposal + ApprovalRequest signatures + PCO authorization + PCN release |
| IATF 16949 | 8.5.6.1 | Documented process for change control, risk analysis, customer notification per CSR, verification of changes | Three-stage lifecycle is the documented process; `risk_analysis` field on PCR; `customer_notification_required` flag on PCR; PCO `implementation_plan` review + approval signature |
| AS9100D | 8.5.6 | Procedures for controlling and re-validating changes; configuration management with per-serial traceability; communication to affected parties | Three-stage lifecycle; per-WO process version pinning + `auditlog` on `WorkOrder.process` changes; PCN with `closure_evidence` captures re-validation evidence |

**Equivalences:**

- SIMPLIFIED mode ≈ ISO 9001 8.5.6 baseline (general manufacturing).
- REGULATED mode ≈ AS9100D 8.5.6 + IATF 16949 8.5.6.1 baseline (automotive, aerospace, defense).
- FDA / medical device compliance (21 CFR 820, ISO 13485, ISO 14971, 21 CFR Part 11) is out of scope.

## Decisions Made

All ten Phase 1 decisions are settled.

1. **Artifact numbering:** Per-tenant, annual reset, separate sequences per artifact type. Format `PCR-2026-0001`, `PCO-2026-0001`, `PCN-2026-0001`.

2. **Default mode:** `SIMPLIFIED` for new tenants. Tenant admin flips to `REGULATED` via one-click action when ready. Mode upgrade requires no data migration. Historical import is a separate one-shot capability available in either mode.

3. **PCR creation:** Open by default to anyone with `change_control.add_processchangerequest` permission. Default group assignments grant the permission broadly; tenants narrow at their discretion via existing group permission infrastructure.

4. **PCO authoring (regulated mode):** Pattern A — implementation owner authors via `change_control.author_processchangeorder` permission. Separate approver signs via `PCO_APPROVAL` ApprovalTemplate. System enforces separation of duties (author ≠ approver). Auto-skipped in SIMPLIFIED.

5. **PCN release (regulated mode):** Quality manager releases via `change_control.release_processchangenotice` permission and `PCN_RELEASE` ApprovalTemplate. Separation-of-duties: PCN releaser ≠ PCO approver. Auto-skipped in SIMPLIFIED.

6. **Distribution audiences and acknowledgments:** Not on the model in Phase 1. Audience routing via existing `NotificationRule` on `PCN_RELEASED` event. Acknowledgment tracking deferred to Phase 5 when real customer business requirements surface.

7. **Process version creation timing:** Pattern C. PCR carries text proposal only. PCO authoring auto-creates a DRAFT process version copying current state, edited through existing process editor. PCO approval signs off on the actual DRAFT diff. PCO implementation flips DRAFT to APPROVED via existing `approve_process` service.

8. **Linkage from process detail pages:**
   - `change_control_enabled=False`: existing direct flow unchanged.
   - `change_control_enabled=True`: "Create New Version" button hidden from UI (still callable via management commands). Replaced with "Propose Change" button (creates draft PCR). Process detail page surfaces open and recent PCRs targeting the process.
   - In-flight DRAFTs at toggle time keep their existing path; only new versions require PCR.

9. **PCR rejection and retry:** Rejected PCRs are terminal. Retry creates a new PCR with optional `superseded_by_request` FK on the rejected record pointing forward to the new attempt.

10. **Concurrent PCRs against same target_process:** Serial only in Phase 1. Partial unique constraint enforcing one open PCR per target_process (status not in CLOSED/REJECTED/CANCELLED, not voided). Four future-proofing moves baked into Phase 1 to keep the parallel upgrade purely additive in Phase 5.

## Open Architectural Questions

These can be deferred until Phase 1 implementation begins; flag them for early decision.

- Should `Documents` GFK attachments be allowed on PCRs / PCOs / PCNs (proposal documents, supporting evidence, supplier acknowledgments)? Recommendation: yes, via existing `Documents` GenericRelation. No new attachment infrastructure.

- Outbound webhooks on lifecycle transitions for ERP / PLM sync — wire via existing `integrations/` framework when customers ask. Phase 3+.

- Phase 1 constrains to one open PCR per target_process via partial unique constraint. Rejected PCRs are CLOSED-equivalent for the constraint — new PCR can be filed against same process. Cancelled and rejected PCRs do not block.

- `superseded_by_request` is currently a GFK (ContentType + UUIDField) to allow polymorphic reference if a rejected PCR is superseded by a different change_type's request. May simplify to typed FK if cross-type supersession is never needed.

- Should the abstract base classes register with `auditlog` at the abstract level, or do concrete models register individually? Django's auditlog registration happens on concrete classes. Each concrete model registers explicitly; not inherited.