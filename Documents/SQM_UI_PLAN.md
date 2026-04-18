# Supplier Quality Management - Plan

**Last Updated:** April 2026

For feature tier placement, see `MES_FEATURE_TIERS.md` Section 35.

---

## Backend

### Models

#### SupplierApproval (the ASL)

The Approved Supplier List is not a list of suppliers — it's a list of **supplier + part type** approval relationships.

```
SupplierApproval:
  supplier            FK → Companies
  part_type           FK → PartTypes (nullable — null = approved for commodity/category)
  commodity_category  CharField (optional, for non-part-specific approvals)
  approval_status     CharField (choices below)
  approval_date       DateField
  approved_by         FK → User
  expiration_date     DateField (nullable)
  requalification_due DateField (nullable)
  risk_classification CharField (CRITICAL / MAJOR / MINOR)
  qualification_basis CharField (AUDIT / SURVEY / CERTIFICATION / HISTORICAL / FIRST_ARTICLE)
  inspection_level    CharField (FULL / REDUCED / SKIP) — driven by scorecard rating
  status_change_reason TextField (blank — required on any status transition, stored in audit log)
  notes               TextField
  documents           GenericRelation → Documents
```

**Status choices:** `PENDING`, `CONDITIONALLY_APPROVED`, `APPROVED`, `ON_HOLD`, `PROBATION`, `DISQUALIFIED`

**Business rules for part_type:**
- One SupplierApproval per supplier + part_type combination (unique together)
- `part_type=null` with `commodity_category` set means "approved for this commodity" (e.g., "Fasteners")
- `part_type=null` with `commodity_category` blank means "approved for all part types" — use sparingly
- A supplier CAN have both specific part type approvals and a commodity approval simultaneously
- When checking if a supplier is approved for a given part type, check specific approvals first, fall back to commodity/all approvals

#### SupplierCertification

```
SupplierCertification:
  supplier            FK → Companies
  certification_type  CharField (ISO_9001 / AS9100 / IATF_16949 / NADCAP / ISO_13485 / OTHER)
  certificate_number  CharField
  issuing_body        CharField
  issue_date          DateField
  expiration_date     DateField
  scope_description   TextField
  document            FK → Documents (nullable)
  is_verified         BooleanField (default False)
```

#### IncomingInspection

```
IncomingInspection:
  inspection_number   CharField (auto-generated: INS-YYYY-NNNN)
  supplier            FK → Companies
  purchase_order_ref  CharField
  part_type           FK → PartTypes
  lot_number          CharField
  quantity_received   IntegerField
  quantity_sampled    IntegerField
  sampling_plan       CharField (e.g., "AQL 1.0, Level II, n=8")
  expected_delivery_date  DateField (nullable — promised date from PO, for OTD calculation)
  actual_delivery_date    DateField (nullable — actual receipt date, for OTD calculation)
  inspection_date     DateField
  inspector           FK → User
  result              CharField (ACCEPT / REJECT / CONDITIONAL_ACCEPT)
  material_cert_reviewed  BooleanField
  material_cert_acceptable BooleanField
  notes               TextField
  documents           GenericRelation → Documents
```

#### IncomingInspectionMeasurement

```
IncomingInspectionMeasurement:
  inspection          FK → IncomingInspection (related_name='measurements')
  measurement_def     FK → MeasurementDefinition  ← reuses existing
  nominal_value       DecimalField
  actual_value        DecimalField
  upper_tolerance     DecimalField
  lower_tolerance     DecimalField
  result              CharField (PASS / FAIL)
  notes               TextField
```

Nominal/tolerance values copy from MeasurementDefinition at creation time (snapshot — if specs change later, the inspection record preserves what was measured against).

#### SupplierNCR

```
SupplierNCR:
  ncr_number          CharField (auto-generated: SNCR-YYYY-NNNN)
  supplier            FK → Companies
  purchase_order_ref  CharField
  part_type           FK → PartTypes
  lot_number          CharField
  quantity_received   IntegerField
  quantity_rejected   IntegerField
  date_discovered     DateField
  discovered_by       FK → User
  discovery_point     CharField (INCOMING_INSPECTION / IN_PROCESS / FINAL_INSPECTION / FIELD)
  defect_description  TextField
  defect_category     FK → QualityErrorsList  ← reuses existing defect catalog
  severity            CharField (CRITICAL / MAJOR / MINOR / COSMETIC)
  disposition         CharField (RETURN_TO_SUPPLIER / USE_AS_IS / REWORK / SCRAP / MRB_REVIEW)
  disposition_approved_by  FK → User (nullable)
  disposition_date    DateField (nullable)
  status              CharField (choices below)
  linked_inspection   FK → IncomingInspection (nullable)
  linked_scar         FK → SCAR (nullable)
  documents           GenericRelation → Documents
```

**Status choices:** `OPEN`, `UNDER_REVIEW`, `DISPOSITIONED`, `CLOSED`

#### SCAR

```
SCAR:
  scar_number         CharField (auto-generated: SCAR-YYYY-NNNN)
  supplier            FK → Companies
  linked_ncrs         M2M → SupplierNCR  ← can consolidate multiple NCRs
  severity            CharField (CRITICAL / MAJOR / MINOR)
  issue_date          DateField
  response_due_date   DateField
  status              CharField (choices below)
  problem_description TextField
  supplier_root_cause         TextField (blank — filled when supplier responds)
  supplier_corrective_action  TextField (blank)
  supplier_preventive_action  TextField (blank)
  supplier_response_date      DateField (nullable)
  response_accepted_by        FK → User (nullable)
  verification_method         TextField (blank)
  verification_date           DateField (nullable)
  verified_by                 FK → User (nullable)
  effectiveness_check_date    DateField (nullable)
  effectiveness_result        CharField (EFFECTIVE / NOT_EFFECTIVE / PENDING)
  documents           GenericRelation → Documents
```

**Status choices:** `ISSUED`, `AWAITING_RESPONSE`, `RESPONSE_RECEIVED`, `UNDER_REVIEW`, `ACCEPTED`, `REJECTED`, `VERIFIED`, `VERIFICATION_FAILED`, `CLOSED`

#### SupplierScorecard

```
SupplierScorecard:
  supplier            FK → Companies
  period_start        DateField
  period_end          DateField

  # Raw metrics (stored, not just computed)
  quality_ppm         DecimalField  ← (rejected / received) × 1,000,000
  on_time_delivery    DecimalField  ← % of POs received by promised date
  scar_response_rate  DecimalField  ← % of SCARs responded to on time
  lot_acceptance_rate DecimalField  ← % of inspected lots accepted
  ncr_count           IntegerField  ← raw count in period
  cert_currency       BooleanField  ← all required certs current?

  # Weighted composite
  composite_score     DecimalField  ← 0-100
  rating              CharField     ← A / B / C / D / F (derived from score)

  # Snapshot metadata
  created_at          DateTimeField (auto)
  created_by          FK → User (nullable — null if auto-generated)
```

All models inherit from `SecureModel` for multi-tenant RLS and audit fields.

### Relationships to Existing Models

```
Companies (existing)
  ├── SupplierApproval ──── PartTypes (existing)
  ├── SupplierCertification
  ├── SupplierScorecard
  ├── IncomingInspection ─── PartTypes (existing)
  │     └── IncomingInspectionMeasurement ─── MeasurementDefinition (existing)
  ├── SupplierNCR ─── PartTypes, QualityErrorsList (existing)
  └── SCAR ─── SupplierNCR (M2M)

Documents (existing GenericRelation) attaches to all new models.
ApprovalRequest (existing) used for disposition approvals and SCAR acceptance.
```

No changes to the Companies model — don't add a `is_supplier` flag or SupplierProfile. A company becomes a "supplier" by having SupplierApproval records. Companies can be both customers and suppliers.

### Status Workflows

#### SupplierApproval

```
PENDING → CONDITIONALLY_APPROVED → APPROVED
PENDING → APPROVED (direct, if qualification is clear)
PENDING → DISQUALIFIED (rejected during qualification)

APPROVED → ON_HOLD (critical quality escape — no new POs)
APPROVED → PROBATION (pattern of NCRs or poor scorecard)
CONDITIONALLY_APPROVED → APPROVED (follow-up completed)
CONDITIONALLY_APPROVED → DISQUALIFIED (follow-up failed)

ON_HOLD → APPROVED (SCAR resolved + verified)
PROBATION → APPROVED (improvement verified)
PROBATION → DISQUALIFIED (no improvement)
DISQUALIFIED → PENDING (re-qualification process)
```

Any status change creates an audit log entry with user, timestamp, and reason.

#### SupplierNCR

```
OPEN → UNDER_REVIEW → DISPOSITIONED → CLOSED
```

Simple linear flow. `UNDER_REVIEW` means someone is investigating. `DISPOSITIONED` means a decision has been made (return/scrap/rework/use-as-is). `CLOSED` after disposition is executed.

Use-As-Is and MRB Review dispositions trigger an ApprovalRequest before status can move to `DISPOSITIONED`.

#### SCAR

```
ISSUED → AWAITING_RESPONSE → RESPONSE_RECEIVED → UNDER_REVIEW
  → ACCEPTED → VERIFIED → CLOSED (if effectiveness_result = EFFECTIVE)
                        → VERIFICATION_FAILED (if NOT_EFFECTIVE)
  → REJECTED → AWAITING_RESPONSE (supplier must redo)
```

`VERIFIED` requires effectiveness_result = EFFECTIVE to proceed to CLOSED. If NOT_EFFECTIVE:
- Status moves to `VERIFICATION_FAILED` (new terminal-ish state)
- User must take action: either issue a new SCAR (links to the failed one) or downgrade supplier status
- No automatic retry loop — each SCAR is a single attempt. Persistent problems get new SCARs.

`REJECTED` → `AWAITING_RESPONSE` allows the supplier to resubmit. No max retry limit enforced in code — if a supplier keeps submitting bad responses, the quality manager should downgrade their status or issue a new SCAR with escalated severity rather than rejecting indefinitely.

### Scorecard Calculation

**Weights:**
- Quality (PPM): 40%
- On-Time Delivery: 30%
- Responsiveness (SCAR response rate): 20%
- Lot Acceptance: 10%

**Metric computation:**

```
quality_ppm = (rejected_parts / total_received_parts) × 1,000,000
  → Score = max(0, (10000 - ppm) / 10000 × 100)
  → Examples: PPM=0 → 100, PPM=1000 → 90, PPM=5000 → 50, PPM=10000+ → 0

on_time_delivery = (on_time_receipts / total_receipts) × 100
  → Score: direct percentage (95% OTD = 95 score)
  → Data source: IncomingInspection.purchase_order_ref links to expected date.
    For MVP, add expected_delivery_date and actual_delivery_date fields to
    IncomingInspection. Long term, this could link to a PurchaseOrder model
    or pull from ERP integration.

scar_response_rate = (SCARs responded on time / total SCARs) × 100
  → Score: direct percentage

lot_acceptance_rate = (lots_accepted / lots_inspected) × 100
  → Score: direct percentage

composite = (quality_score × 0.4) + (otd_score × 0.3) + (response_score × 0.2) + (lot_score × 0.1)
```

**Edge cases (zero data):**
- **No inspections in period:** quality_ppm and lot_acceptance_rate are null. Exclude those weights and redistribute proportionally across metrics that have data. If ALL metrics are null, do not generate a scorecard for that month.
- **No SCARs issued in period:** scar_response_rate = 100 (no problems = perfect score). This is intentional — a supplier shouldn't be penalized for having no issues.
- **No PO receipts in period:** on_time_delivery is null. Exclude and redistribute.
- **New supplier, first month:** Only metrics with data contribute. A supplier with only 1 inspection and no SCARs gets a scorecard based on quality_ppm + lot_acceptance (redistributed to 100% of weight). Rating letter still applies.
- **Supplier with zero activity all month:** No scorecard generated. Previous month's scorecard remains the "current" rating.

**Rating thresholds:**
- A: 90-100
- B: 70-89
- C: 50-69
- D: 1-49
- F: 0 or manually disqualified

**Snapshot frequency:** Monthly. A Celery beat task generates scorecards for all active suppliers on the 1st of each month, using the previous month's data. Quality managers can also trigger a manual recalculation.

Store both the raw metrics AND the composite score. Don't compute on-the-fly only — auditors need the historical record.

### API

#### ViewSets

All viewsets use `ModelViewSet` with standard CRUD, inheriting from your existing `SecureModelViewSet` pattern for RLS.

| ViewSet | Endpoint | Notable Filters | Custom Actions |
|---------|----------|----------------|----------------|
| `SupplierApprovalViewSet` | `/api/supplier-approvals/` | supplier, part_type, approval_status, risk_classification | `change_status` (POST) |
| `SupplierCertificationViewSet` | `/api/supplier-certifications/` | supplier, certification_type, is_verified | — |
| `IncomingInspectionViewSet` | `/api/incoming-inspections/` | supplier, part_type, result, inspector, date range | `create_ncr_from_rejection` (POST) |
| `SupplierNCRViewSet` | `/api/supplier-ncrs/` | supplier, part_type, severity, status, disposition | `issue_scar` (POST) |
| `SCARViewSet` | `/api/scars/` | supplier, severity, status, overdue (boolean) | `accept_response`, `reject_response`, `verify` (POST) |
| `SupplierScorecardViewSet` | `/api/supplier-scorecards/` | supplier, period, rating | `latest` (GET), `recalculate` (POST) |
| `SupplierDashboardView` | `/api/supplier-quality/dashboard/` | date range | Single endpoint returning KPIs |

**FilterSets:** Use `django-filters` (already in your stack). Each list endpoint supports search (supplier name), ordering, and the filters listed above.

**Serializer shape:**
- **List responses:** flat, minimal — IDs, names, status badges, dates. No nested objects. Keeps list queries fast.
- **Detail responses:** include nested data — supplier name (from Companies), part type name, linked NCR summaries on SCAR detail, measurement results on inspection detail.
- **Dashboard response:** single JSON blob, example schema:
```json
{
  "kpis": {
    "open_ncrs": { "value": 3, "trend": "up" },
    "open_scars": { "value": 1, "overdue": 0 },
    "inspections_this_month": { "value": 12 },
    "avg_supplier_rating": { "score": 84, "grade": "B" },
    "lot_acceptance_rate": { "value": 96.5 },
    "certs_expiring_soon": { "value": 2, "within_days": 30 }
  },
  "attention_items": [
    { "type": "probation", "supplier_id": 5, "supplier_name": "Acme Heat Treat", "message": "On probation since 2026-02-01" },
    { "type": "scar_overdue", "scar_id": 12, "supplier_name": "XYZ Plating", "message": "SCAR-2026-0012 response overdue by 5 days" },
    { "type": "cert_expiring", "cert_id": 8, "supplier_name": "ABC Fasteners", "message": "NADCAP expires 2026-05-01" }
  ]
}
```

### Signals & Triggers

| Trigger | Action |
|---------|--------|
| IncomingInspection saved with result=REJECT | Prompt option (not automatic) to create SupplierNCR. Implemented as a `create_ncr_from_rejection` action on the viewset, called by frontend dialog. |
| SupplierNCR disposition = USE_AS_IS or MRB_REVIEW | Auto-create ApprovalRequest using configured approval template. |
| SCAR response_due_date passes without response | Celery beat task checks daily. Creates notification for quality manager. Marks SCAR as overdue (queryable filter). |
| SupplierCertification expiration within 30/60/90 days | Celery beat task checks daily. Creates notification. Flags on dashboard attention list. |
| SupplierScorecard rating drops to D or F | Creates notification for quality manager. Suggests status change to PROBATION or DISQUALIFIED (user decides). |
| Monthly scorecard generation | Celery beat task on 1st of month. Calculates and stores SupplierScorecard for all suppliers with activity. |

No hard automations that change supplier status without user action. The system suggests, the quality manager decides.

### Permissions

| Action | Required Permission |
|--------|-------------------|
| View SQM pages | `view_supplier_quality` |
| Create/edit incoming inspections | `manage_inspections` |
| Create supplier NCRs | `manage_supplier_ncrs` |
| Disposition NCRs | `disposition_supplier_ncrs` (separate — not everyone who creates can disposition) |
| Issue SCARs | `manage_scars` |
| Accept/reject SCAR responses | `manage_scars` |
| Change supplier approval status | `manage_supplier_approvals` |
| Generate/recalculate scorecards | `manage_supplier_approvals` |

These map to your existing TenantGroup permission system. A "Quality Engineer" group would typically get all of these. A "Quality Inspector" group would get view + manage_inspections only.

---

## Frontend

---

## Sidebar Navigation

Add under **Quality** section in `app-sidebar.tsx`:

```
Quality
  Dashboard          (existing)
  CAPAs              (existing)
  Quality Reports    (existing)
  Training           (existing)
  Calibrations       (existing)
  Heat Map           (existing)
  ── Supplier Quality ──
  Supplier Dashboard
  Approved Suppliers
  Incoming Inspections
  Supplier NCRs
  SCARs
  Scorecards
```

Gated by permission (e.g., `can_view_supplier_quality`). Alternatively, if the section gets too long, break "Supplier Quality" into its own top-level sidebar group with its own icon (e.g., `Truck` or `ShieldCheck` from lucide-react).

---

## Page Inventory

| Page | Route | Pattern | Purpose |
|------|-------|---------|---------|
| Supplier Quality Dashboard | `/supplier-quality` | KpiGrid + attention list | Overview of supplier health |
| Approved Suppliers (ASL) | `/supplier-quality/approved` | ModelEditorPage | List/search/filter supplier approvals |
| Supplier Detail | `/supplier-quality/suppliers/:id` | Multi-tab detail (like CapaDetailPage) | Everything about one supplier |
| Incoming Inspections List | `/supplier-quality/inspections` | ModelEditorPage | List all incoming inspections |
| Incoming Inspection Form | `/supplier-quality/inspections/new` | Form page (like EditCompanyFormPage) | Create/edit an inspection record |
| Supplier NCR List | `/supplier-quality/ncrs` | ModelEditorPage | List supplier non-conformances |
| Supplier NCR Detail | `/supplier-quality/ncrs/:id` | Multi-tab detail | Full NCR with disposition |
| SCAR List | `/supplier-quality/scars` | ModelEditorPage | List supplier corrective actions |
| SCAR Detail | `/supplier-quality/scars/:id` | Multi-tab detail | Full SCAR lifecycle |
| Scorecards | `/supplier-quality/scorecards` | Card grid (like SettingsPage) | At-a-glance ratings for all suppliers |

---

## Page Designs

### 1. Supplier Quality Dashboard

**Pattern:** Same as existing `AnalysisPage` — KPI cards up top, attention list below, date range toggle.

**KPI Cards (KpiGrid, 6 cards):**
- Open Supplier NCRs (count, trend arrow)
- Open SCARs (count, with overdue highlighted)
- Inspections This Month (count)
- Average Supplier Rating (letter grade + score)
- Lot Acceptance Rate (% this period)
- Certs Expiring Soon (count, next 30/60/90 days)

**Attention List (below KPIs):**
Sorted by urgency, each item links to the relevant detail page.
- Suppliers on probation or conditional approval
- SCARs past response due date
- Certifications expiring within 30 days
- Suppliers with no inspection data (new, unverified)
- NCRs awaiting disposition

**Date Range Toggle:** 7d / 14d / 30d / 90d (same pattern as AnalysisPage)

---

### 2. Approved Suppliers (ASL)

**Pattern:** `ModelEditorPage`

**Columns:**
| Column | Priority | Content |
|--------|----------|---------|
| Supplier Name | 1 | Company name, links to supplier detail |
| Part Type | 1 | Which part type they're approved for. If part_type is null, display commodity_category (e.g., "Commodity: Fasteners") or "All Part Types" if both are empty. |
| Status | 1 | Badge: Approved (green), Conditional (yellow), On Hold (orange), Probation (red), Pending (gray), Disqualified (dark gray) |
| Risk | 2 | Badge: Critical / Major / Minor |
| Rating | 2 | Letter badge: A (green), B (blue), C (yellow), D (orange), F (red) |
| Expiration | 3 | Date, with overdue/expiring-soon highlighting |
| Last Inspection | 3 | Date of most recent incoming inspection |

**Filters:**
- Status dropdown (Approved / Conditional / Probation / Pending / Disqualified)
- Risk dropdown (Critical / Major / Minor)
- Rating dropdown (A / B / C / D / F)

**Actions:**
- "New Approval" button → opens form to create a SupplierApproval
- Row click → supplier detail page
- Details link column (blue ExternalLink button, standard pattern)

---

### 3. Supplier Detail Page

**Pattern:** Multi-tab detail page (like `CapaDetailPage` / `DocumentDetailPage`)

**Header:**
- Back button (← Approved Suppliers)
- Supplier name (h1)
- Status badge (Approved / Conditional / Probation / etc.)
- Risk classification badge
- Current rating (large letter grade with color)
- Action buttons: Edit, Change Status, Issue SCAR

**Tabs:**

#### Overview Tab
Two-column card layout:

**Left column:**
- **Contact Info Card** — company name, address, phone, email, website (from Companies model)
- **Current Rating Card** — large letter grade, composite score, bar chart breakdown of Quality / Delivery / Responsiveness / Cost weights
- **Quick Stats Card** — total NCRs, total SCARs, lot acceptance rate, on-time delivery %, all-time

**Right column:**
- **Approval Status Card** — current status, approval date, approved by, expiration date, requalification due, qualification basis
- **Risk Classification Card** — risk level, justification notes
- **Recent Activity Card** — last 5 events (NCR created, SCAR issued, inspection completed, cert uploaded, status change) as a simple timeline list

#### Approvals Tab
**Pattern:** Inline editable list (like `MilestonesEditorPage`)

List of SupplierApproval records for this supplier — one row per part type they're approved for.

| Part Type | Status | Approved Date | Expiration | Risk | Actions |
|-----------|--------|---------------|------------|------|---------|
| INJ-2500-A | Approved (green badge) | 2025-06-15 | 2026-06-15 | Major | Edit / Remove |
| INJ-3100-B | Conditional (yellow badge) | 2026-01-10 | 2026-07-10 | Critical | Edit / Remove |

"Add Part Type Approval" button at bottom.

#### Certifications Tab
**Pattern:** Simple table with upload.

| Certification | Certificate # | Issuing Body | Issued | Expires | Status | Document |
|--------------|---------------|-------------|--------|---------|--------|----------|
| ISO 9001 | QMS-2024-1234 | BSI | 2024-03 | 2027-03 | Current (green) | View PDF |
| NADCAP Heat Treat | NT-2023-5678 | PRI | 2023-08 | 2025-08 | Expired (red) | View PDF |
| AS9100D | — | — | — | — | Missing (gray) | Upload |

Status badges:
- Current (green) — expires > 90 days
- Expiring Soon (yellow) — expires within 90 days
- Expired (red) — past expiration
- Missing (gray) — required but not uploaded

"Add Certification" button. Upload links to Documents (existing GenericRelation).

#### Performance Tab
**Pattern:** Charts (Recharts) + metric cards

- **Scorecard History Chart** — line chart of composite score over last 12 months
- **Quality PPM Chart** — bar chart by month
- **On-Time Delivery Chart** — line chart by month
- **Metric Breakdown Cards** — current values for each KPI with trend arrows:
  - Quality PPM
  - On-Time Delivery %
  - SCAR Response Rate %
  - Lot Acceptance Rate %
  - NCR Count (this period)

#### NCRs Tab
**Pattern:** Filtered `ModelEditorPage` (same columns as the NCR list page, pre-filtered to this supplier)

Shows all Supplier NCRs for this supplier. Click row → NCR detail page.

#### SCARs Tab
**Pattern:** Same as NCRs tab but for SCARs. Pre-filtered to this supplier.

#### Inspections Tab
**Pattern:** Filtered list of incoming inspections for this supplier.

| Inspection # | Part Type | Date | Qty Received | Qty Sampled | Result | Inspector |
|-------------|-----------|------|-------------|-------------|--------|-----------|
| INS-2026-0042 | INJ-2500-A | 2026-03-15 | 100 | 8 | Accept (green) | J. Smith |
| INS-2026-0038 | INJ-2500-A | 2026-02-28 | 50 | 5 | Reject (red) | M. Jones |

"New Inspection" button → inspection form with supplier pre-filled.

#### Documents Tab
**Pattern:** Standard documents list (existing GenericRelation pattern)

Quality agreements, audit reports, supplier questionnaires, etc. Uses existing Documents system.

---

### 4. Incoming Inspection List

**Pattern:** `ModelEditorPage`

**Columns:**
| Column | Priority | Content |
|--------|----------|---------|
| Inspection # | 1 | Auto-generated number |
| Supplier | 1 | Company name |
| Part Type | 1 | Part type name |
| Date | 2 | Inspection date |
| Result | 1 | Badge: Accept (green) / Reject (red) / Conditional (yellow) |
| Qty Received | 2 | Number |
| Qty Sampled | 3 | Number |
| Inspector | 3 | User name |

**Filters:**
- Result dropdown (Accept / Reject / Conditional)
- Supplier dropdown (searchable combobox)
- Date range

**Actions:**
- "New Inspection" button → inspection form
- Row click → inspection detail or form in edit mode

---

### 5. Incoming Inspection Form

**Pattern:** Form page (like `EditCompanyFormPage`)

**Fields:**
- Supplier (combobox, searchable) — required
- Purchase Order Reference (text) — required
- Part Type (combobox, filtered by supplier's approved part types) — required
- Lot Number (text)
- Quantity Received (number) — required
- Quantity Sampled (number)
- Sampling Plan (text, e.g., "AQL 1.0, Level II, n=8")
- Material Cert Reviewed (checkbox)
- Material Cert Acceptable (checkbox, shown when cert reviewed is checked)

**Measurements Section:**
Repeating rows (one per MeasurementDefinition for this part type):
| Characteristic | Nominal | Tol+ | Tol- | Actual | Result |
|---------------|---------|------|------|--------|--------|
| OD | 1.500 | +0.002 | -0.002 | [input] | Auto (green/red) |
| Length | 3.000 | +0.005 | -0.005 | [input] | Auto (green/red) |

Auto-populated from MeasurementDefinitions linked to the part type's process steps. Inspector enters actual values, pass/fail auto-calculated.

**Result Section:**
- Overall Result (select: Accept / Reject / Conditional Accept) — required
- Notes (textarea)
- Documents (file upload, optional — photos, cert scans)

**On Reject:**
Dialog prompt: "Create Supplier NCR for this rejection?" → Yes pre-fills a new Supplier NCR with supplier, part type, lot number, quantities from this inspection.

---

### 6. Supplier NCR List

**Pattern:** `ModelEditorPage`

**Columns:**
| Column | Priority | Content |
|--------|----------|---------|
| NCR # | 1 | Auto-generated (SNCR-2026-0001) |
| Supplier | 1 | Company name |
| Part Type | 1 | Part type name |
| Severity | 1 | Badge: Critical (red) / Major (orange) / Minor (yellow) / Cosmetic (gray) |
| Disposition | 2 | Badge: Return / Use As-Is / Rework / Scrap / MRB Review |
| Status | 1 | Badge: Open (yellow) / Under Review (blue) / Dispositioned (green) / Closed (gray) |
| Date | 2 | Date discovered |

**Filters:** Status, Severity, Supplier

---

### 7. Supplier NCR Detail

**Pattern:** Multi-tab detail (mirrors internal quality report / CAPA detail patterns)

**Header:**
- NCR number, supplier name, status badge, severity badge
- Action buttons: Edit, Disposition, Issue SCAR, Close

**Tabs:**

#### Overview Tab
- **Defect Info Card** — description, defect category (from QualityErrorsList), severity, discovery point (incoming inspection / in-process / final / field)
- **Quantities Card** — received, rejected, accepted
- **Source Card** — supplier, PO reference, lot number, linked incoming inspection
- **Photos/Documents** — attached images and files

#### Disposition Tab
- Disposition decision (select: Return to Supplier / Use As-Is / Rework / Scrap / MRB Review)
- Disposition approved by (user, via approval workflow)
- Disposition date
- Disposition notes
- If disposition requires approval → shows ApprovalRequest status (reuse existing approval components)

#### SCAR Tab
- If SCAR issued: link to SCAR detail page with current status
- If no SCAR: "Issue SCAR" button → creates SCAR pre-filled from this NCR

#### History Tab
- Timeline of status changes, edits, approvals (audit trail)

---

### 8. SCAR List

**Pattern:** `ModelEditorPage`

**Columns:**
| Column | Priority | Content |
|--------|----------|---------|
| SCAR # | 1 | Auto-generated (SCAR-2026-0001) |
| Supplier | 1 | Company name |
| Severity | 1 | Badge: Critical / Major / Minor |
| Status | 1 | Badge with colors (see below) |
| Issue Date | 2 | Date |
| Response Due | 2 | Date, with overdue highlighting (red if past due) |

**Status badges:**
- Issued (gray)
- Awaiting Response (yellow)
- Response Received (blue)
- Under Review (blue)
- Accepted (green)
- Rejected (red)
- Verified (green, darker)
- Verification Failed (red, darker)
- Closed (gray, darker)

**Filters:** Status, Severity, Supplier

---

### 9. SCAR Detail

**Pattern:** Multi-tab detail (closely mirrors `CapaDetailPage` — SCAR is the outward-facing equivalent of CAPA)

**Header:**
- SCAR number, supplier name, status badge, severity badge
- Response due date (with overdue warning if applicable)
- Action buttons: Edit, Accept Response, Reject Response, Verify, Close

**Tabs:**

#### Overview Tab
- **Problem Description Card** — what went wrong, linked NCRs (click through to NCR detail)
- **Supplier Info Card** — supplier name, contact, linked from Companies
- **Timeline Card** — issue date, response due, response received, verification date, closed date — with status dots (like TrackerCard pipeline stages)

#### Supplier Response Tab
This is the core workflow tab. Shows fields that get filled in as the SCAR progresses:

- **Root Cause** (textarea) — filled by supplier or entered on their behalf
- **Corrective Action** (textarea) — what the supplier will do to fix it
- **Preventive Action** (textarea) — what the supplier will do to prevent recurrence
- **Response Date** — when the supplier responded
- **Supporting Documents** — uploaded evidence from supplier

Each field shows as empty/placeholder when pending, filled when supplier has responded. Status badge on the tab header shows whether response is received.

#### Verification Tab
- Verification method (textarea) — how you'll verify the corrective action worked
- Verification date
- Verified by (user)
- Effectiveness check date (future date for follow-up)
- Effectiveness result (select: Effective / Not Effective / Pending)
- Notes

If "Not Effective" → prompt to issue a new SCAR or escalate supplier status.

#### Approval Tab
- Reuse existing ApprovalRequest/ApprovalResponse components
- Shows approval status for SCAR acceptance

#### History Tab
- Full audit trail of status changes, edits, approvals

---

### 10. Scorecards Page

**Pattern:** Card grid (like `SettingsPage` settings cards, but richer)

**Layout:** Responsive grid, 1 column mobile, 2 columns md, 3 columns lg.

**Each Supplier Card:**
```
┌─────────────────────────────────────┐
│  [Company Logo/Icon]                │
│  Acme Heat Treating         A      │  ← Large letter grade with color
│  ████████████████████░░  87/100    │  ← Progress bar + score
│                                     │
│  Quality PPM:    450  ↓            │  ← Green arrow = improving
│  On-Time:        96%  ↑            │
│  Lot Accept:     98%  →            │  ← Gray arrow = flat
│  Open NCRs:      1                 │
│  Open SCARs:     0                 │
│                                     │
│  Status: Approved    Risk: Major   │  ← Small badges
│  Last Inspection: 2026-03-15       │
└─────────────────────────────────────┘
```

**Rating colors:**
- A (90-100): green background accent
- B (70-89): blue
- C (50-69): yellow
- D (below 50): orange
- F (disqualified): red

**Sort options:** Rating (high→low), Rating (low→high), Name, Last Inspection Date, Open NCR Count

**Click card →** Supplier Detail Page, Performance tab.

---

## Key UI Flows

### Flow 1: Qualify a New Supplier

```
Settings → Companies → Create or find company
                ↓
Supplier Quality → Approved Suppliers → "New Approval"
                ↓
Fill form: company, part type, risk classification, qualification basis
                ↓
Status = Pending → triggers approval workflow (if configured)
                ↓
Approval granted → Status = Approved (or Conditional)
                ↓
Upload certifications on Supplier Detail → Certifications tab
```

### Flow 2: Receive and Inspect Parts

```
Supplier Quality → Incoming Inspections → "New Inspection"
                ↓
Select supplier, PO, part type → measurements auto-populate
                ↓
Enter actuals, system auto-calculates pass/fail
                ↓
Set overall result: Accept / Reject / Conditional
                ↓
If Accept → done, parts go to inventory
If Reject → dialog: "Create Supplier NCR?" → pre-fills NCR form
```

### Flow 3: NCR → SCAR → Resolution

```
Supplier NCR created (from inspection or manually)
                ↓
Quality engineer reviews, sets severity, adds defect details
                ↓
Disposition decision (Return / Rework / Scrap / Use As-Is)
  → may trigger approval workflow for Use As-Is or MRB
                ↓
If pattern of NCRs → "Issue SCAR" button on NCR detail
                ↓
SCAR created, linked to NCR(s), response due date set
                ↓
Supplier provides root cause + corrective action + preventive action
  (entered by quality engineer on supplier's behalf, or via portal later)
                ↓
Quality engineer reviews response → Accept or Reject
                ↓
If Accepted → schedule verification date
                ↓
Verification performed → Effective / Not Effective
                ↓
If Effective → SCAR closed
If Not Effective → new SCAR or supplier status downgrade
```

### Flow 4: Scorecard Review

```
Scorecards page shows all rated suppliers in card grid
                ↓
Scorecard auto-calculates from transactional data:
  - Quality PPM from inspection results
  - OTD from PO expected vs actual dates
  - SCAR response rate from SCAR records
  - Lot acceptance rate from inspections
                ↓
Monthly snapshot stored (SupplierScorecard record)
                ↓
Rating drives supplier status suggestions:
  A (90+) → eligible for reduced inspection
  B (70-89) → normal inspection
  C (50-69) → enhanced inspection, improvement plan
  D (<50) → probation, new business hold
  F → disqualified
                ↓
Quality manager reviews, manually adjusts status if needed
```

---

## Component Reuse Map

| SQM Page | Existing Pattern | Component/Page to Reference |
|----------|------------------|-----------------------------|
| Dashboard | KPI cards + attention list | `AnalysisPage.tsx` |
| ASL list | Searchable table with filters | `ModelEditorPage.tsx` |
| Supplier detail | Multi-tab with header | `CapaDetailPage.tsx` |
| Part type approvals (inline) | Inline editable list | `MilestonesEditorPage.tsx` |
| Inspection form | Form with validation | `EditCompanyFormPage.tsx` |
| Measurement entry | Repeating measurement rows | QA form entry (existing) |
| NCR detail | Multi-tab with disposition | `CapaDetailPage.tsx` |
| SCAR detail | Multi-tab with approval | `CapaDetailPage.tsx` |
| Scorecard cards | Card grid with metrics | `SettingsPage.tsx` card layout |
| Status badges | Color-coded badges | Existing badge patterns throughout app |
| Approval workflow | Approval status display | `ApprovalWorkflow` components |
| Document attachments | GenericRelation docs | `DocumentDetailPage.tsx` pattern |
| Timeline/history | Audit trail list | CAPA history tab |

**New components needed:**
- `<SupplierScorecard>` — the card component for the scorecards grid page
- `<InspectionMeasurementRow>` — repeating measurement entry row for inspection form (may be able to reuse existing QA measurement entry)
- `<ScarResponseForm>` — the root cause / corrective action / preventive action form section

Everything else is assembly of existing patterns.

---

## Hooks Needed

| Hook | Purpose | API Endpoint |
|------|---------|-------------|
| `useListSupplierApprovals` | ASL list with filters | `GET /api/supplier-approvals/` |
| `useRetrieveSupplierApproval` | Single approval detail | `GET /api/supplier-approvals/:id/` |
| `useCreateSupplierApproval` | New approval | `POST /api/supplier-approvals/` |
| `useUpdateSupplierApproval` | Edit approval | `PATCH /api/supplier-approvals/:id/` |
| `useListSupplierCertifications` | Certs for a supplier | `GET /api/supplier-certifications/?supplier=:id` |
| `useCreateSupplierCertification` | Add cert | `POST /api/supplier-certifications/` |
| `useListIncomingInspections` | Inspection list | `GET /api/incoming-inspections/` |
| `useCreateIncomingInspection` | New inspection | `POST /api/incoming-inspections/` |
| `useListSupplierNCRs` | NCR list | `GET /api/supplier-ncrs/` |
| `useRetrieveSupplierNCR` | NCR detail | `GET /api/supplier-ncrs/:id/` |
| `useCreateSupplierNCR` | New NCR | `POST /api/supplier-ncrs/` |
| `useListSCARs` | SCAR list | `GET /api/scars/` |
| `useRetrieveSCAR` | SCAR detail | `GET /api/scars/:id/` |
| `useCreateSCAR` | Issue SCAR | `POST /api/scars/` |
| `useUpdateSCAR` | Update SCAR (response, verification) | `PATCH /api/scars/:id/` |
| `useSupplierScorecard` | Scorecard for one supplier | `GET /api/supplier-scorecards/?supplier=:id` |
| `useListSupplierScorecards` | All current scorecards | `GET /api/supplier-scorecards/latest/` |
| `useSupplierDashboard` | Dashboard KPIs | `GET /api/supplier-quality/dashboard/` |

---

## Implementation Order

Build in this order — each phase is usable on its own:

1. **ASL + Certifications** (~1-2 weeks)
   - SupplierApproval model + API + list page + form
   - SupplierCertification model + API
   - Supplier detail page (Overview + Approvals + Certifications tabs only)
   - Highest audit value, smallest scope

2. **Incoming Inspection** (~1-2 weeks)
   - IncomingInspection + IncomingInspectionMeasurement models + API
   - Inspection list page + form (with auto-populated measurements)
   - Supplier detail Inspections tab
   - Reuses existing MeasurementDefinition infrastructure

3. **Supplier NCR + SCAR** (~2-3 weeks)
   - SupplierNCR model + API + list page + detail page
   - SCAR model + API + list page + detail page
   - Link NCR → SCAR creation flow
   - Supplier detail NCRs + SCARs tabs
   - Follows existing CAPA patterns closely

4. **Scorecards + Dashboard** (~1-2 weeks)
   - SupplierScorecard model + calculation logic + API
   - Scorecards grid page
   - Supplier detail Performance tab (charts)
   - Dashboard page with KPIs and attention list
   - Depends on inspection + NCR data existing to calculate from

**Total: ~5-9 weeks frontend, assuming backend models/API are built in parallel.**

---

## Implementation Hints (Existing Patterns to Follow)

These SQM features have direct precedents in the existing codebase. Don't reinvent — follow the established pattern.

### Auto-Generated Numbers (SNCR-YYYY-NNNN, etc.)
- **Pattern:** `CAPA.generate_capa_number()` at `Tracker/models/qms.py` ~line 890
- Uses `generate_next_sequence()` utility with SELECT FOR UPDATE for race condition protection
- Called from `CAPA.save()` at ~line 879
- Format: `{PREFIX}-{TYPE_CODE}-{YEAR}-{SEQUENCE}`
- Do the same for SupplierNCR, SCAR, IncomingInspection

### Measurement Snapshots (copy specs at creation)
- **Pattern:** `MeasurementResult` at `Tracker/models/qms.py` ~line 355
- Links to `MeasurementDefinition` via FK, specs live on the definition at `Tracker/models/mes_lite.py` ~line 468 (nominal, upper_tol, lower_tol fields at ~lines 485-487)
- `evaluate_spec()` method at ~line 374 auto-calculates `is_within_spec` from the linked definition's tolerances
- For IncomingInspectionMeasurement: copy nominal/tolerance values from MeasurementDefinition onto the measurement record at creation time (snapshot), then evaluate against those copied values

### NCR Disposition → ApprovalRequest
- **Pattern:** Critical CAPA → ApprovalRequest via signal at `Tracker/signals.py` ~line 214
- Uses `ApprovalRequest.create_from_template()` at `Tracker/models/core.py` ~line 2621
- GenericFK on ApprovalRequest (content_type + object_id) at ~line 2454 allows linking to any model
- For SupplierNCR: when disposition is set to USE_AS_IS or MRB_REVIEW, call `ApprovalRequest.create_from_template(content_object=ncr, template=..., requested_by=..., reason=...)`
- NCR stays at UNDER_REVIEW until approval is granted, then moves to DISPOSITIONED

### "Issue SCAR" from NCR (pre-fill new record)
- **Approach:** Custom viewset action on SupplierNCRViewSet
- Opens a dialog pre-filled with NCR data (supplier, part type, problem description from defect_description)
- User sets severity and response_due_date, then creates
- Link the new SCAR back to the NCR via SCAR.linked_ncrs M2M

### Status Transitions with Audit
- **Pattern:** `CAPA.transition_to()` at `Tracker/models/qms.py` ~line 1092
- Validates allowed transitions, updates status field
- `QuarantineDisposition.save()` at ~line 575 shows auto-transition pattern (OPEN → IN_PROGRESS when disposition_type is set)
- django-auditlog (via SecureModel) automatically logs all field changes
- For SupplierApproval: store `status_change_reason` and let auditlog capture the rest

### GenericRelation for Documents
- **Example:** `QualityErrorsList` at `Tracker/models/qms.py` ~line 36: `documents = GenericRelation('Tracker.Documents')`
- Also used on `QuarantineDisposition` at ~line 550
- `Documents` model at `Tracker/models/core.py` ~line 3132
- Add `documents = GenericRelation('Tracker.Documents')` to all new SQM models

### ApprovalRequest with GenericFK
- **Class:** `ApprovalRequest` at `Tracker/models/core.py` ~line 2442
- GenericFK fields at ~line 2454: `content_type`, `object_id`, `content_object`
- Creation via `create_from_template()` at ~line 2621 — pass `content_object=your_model_instance`
- `ApprovalTemplate` at ~line 3035, `ApprovalResponse` at ~line 2907

### SecureModel Base Class
- **Class:** `SecureModel` at `Tracker/models/core.py` ~line 998
- Provides: `id` (UUIDv7), `tenant` (FK), `external_id`, `archived`, `deleted_at`, `created_at`, `updated_at`, `version`, `previous_version`, `is_current_version`
- `SecureManager` handles soft delete, tenant scoping, and audit logging automatically
- All new SQM models must inherit from SecureModel

### FilterSet with Tenant Scoping
- **Example:** `PartFilter` at `Tracker/filters.py` ~line 36
- Custom filter methods (e.g., `filter_needs_qa()` at ~line 59)
- ModelChoiceFilter with tenant-scoped queryset at ~lines 45-48
- `__init__` method scopes querysets to tenant at ~lines 83-89
- Use this pattern for all SQM filtersets

### Frontend: Hook Pattern
- **Example:** `useCreateIntegration` at `ambac-tracker-ui/src/hooks/useCreateIntegration.ts`
- Pattern: `useMutation` with typed input/response, `mutationFn` calls API with CSRF, `onSuccess` invalidates query keys
- Follow same pattern for all SQM hooks (useCreateSupplierApproval, useCreateSCAR, etc.)

### Frontend: ModelEditorPage (List Pages)
- **Example:** `CompaniesEditorPage` at `ambac-tracker-ui/src/pages/editors/CompaniesEditorPage.tsx` ~line 50
- Props: `title`, `modelName`, `useList` (hook), `columns` (with `renderCell` and `priority`), `renderActions`, `onCreate`
- Use for ASL list, inspection list, NCR list, SCAR list

### Frontend: Multi-Tab Detail Page
- **Example:** `CapaDetailPage` at `ambac-tracker-ui/src/pages/quality/CapaDetailPage.tsx`
- Tab structure at ~line 387: Radix UI Tabs with grid layout
- 7 tabs: Overview, Root Cause, Tasks (with count badge), Verification, Approval (with pending indicator), Documents, History
- Status badges with severity and status icons at ~line 326
- Use this structure for Supplier Detail, NCR Detail, SCAR Detail

### Frontend: Inline Editable List
- **Example:** `MilestonesEditorPage` at `ambac-tracker-ui/src/pages/editors/MilestonesEditorPage.tsx`
- Reorderable rows with inline inputs, add/delete buttons
- Use for Supplier Detail → Approvals Tab (one row per part type approval)
