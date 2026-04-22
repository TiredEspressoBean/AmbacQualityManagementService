# MES Feature Tiers

**Last Updated:** March 24, 2026

This document categorizes Manufacturing Execution System (MES) features by capability level. Each tier is **cumulative** - it includes all features from previous tiers plus new additions.

Legend: [x] = Implemented | [~] = API complete, needs UI | [ ] = Not yet implemented | ⛔ = Out of scope

---

## Tier Definitions

| Tier | Description | Target Customer | Market Comparables |
|------|-------------|-----------------|-------------------|
| **Lite** | Basic shop floor visibility - "where is my part?" | Small job shops without compliance requirements | Prodio, Steelhead |
| **Standard** | Production operations + core quality gates | Job shops needing production control, scheduling, and quality tracking | MachineMetrics, Amper, DELMIAworks Standard |
| **Pro** | Full compliance/QMS layer - document control, CAPA, SPC, traceability | **Aerospace (AS9100), Automotive (IATF 16949), Medical (ISO 13485)** - compliance-driven manufacturers | ProShop, TrakSYS Premier, QT9 |
| **Premium** | Advanced differentiators - 3D visualization, AI, advanced workflow controls | Manufacturers wanting cutting-edge capabilities beyond compliance | — (unique to UQMES) |
| **Enterprise** | Risk management, supplier quality, maintenance, advanced PPAP | Large facilities, multi-plant operations | Siemens Opcenter, Plex, DELMIA, Critical Manufacturing |
| **Out of Scope** | Belongs in ERP, PLM, or specialized systems | - | - |

> ⚠️ **Note for regulated industries:** AS9100 (aerospace), IATF 16949 (automotive), and ISO 13485 (medical) require **Pro** tier features: document control, CAPA, SPC, lot traceability, calibration tracking, training records. Lite and Standard tiers are for non-regulated shops only.

---

## 1. Work Order Management

### 🟢 Lite (18 features)
- [x] Create work order
- [x] Work order status (PENDING → IN_PROGRESS → COMPLETED, plus ON_HOLD, CANCELLED, WAITING_FOR_OPERATOR)
- [x] Link work orders to orders
- [x] Expected completion date
- [x] Expected duration
- [x] Actual completion tracking
- [x] Actual duration tracking
- [x] Work order notes/comments
- [x] Quantity tracking
- [x] WO from CAPA
- [x] CSV bulk import
- [x] API-triggered WO creation
- [x] Release authorization
- [x] Status change audit with e-sig
- [x] Auto-complete on quantity
- [x] Due date tracking with overdue alerts - *Hourly beat emits WORK_ORDER_OVERDUE; admin configures NotificationRule to route it*
- [x] Priority/sequencing - *priority field, lower number = higher priority*
- [~] Labor hours tracking - *TimeEntry model, needs UI*

### 🔵 Standard (+11 = 29 total)
*Includes all Lite, plus:*
- [ ] WO cloning
- [ ] Work order templates
- [ ] Waiting for material status
- [x] Hold escalation - *WorkOrderHold aggregate + hourly beat scanner emits WORK_ORDER_HELD_TOO_LONG; threshold hard-coded 48h, per-tenant config deferred*
- [ ] Partial completion / short close
- [ ] Closure checklist - *Configurable checklist before WO close*
- [x] WO splitting (simple quantity) - *split_work_order QUANTITY mode*
- [x] WO splitting at operation - *split_work_order OPERATION mode*
- [x] WO splitting for rework - *split_work_order REWORK mode with target_process_id; AS9100 (8.7), IATF 16949 (8.7.1.4)*
- [x] Parent-child WO hierarchy - *parent_workorder FK + split_reason/split_at/split_by; undo_split preserves audit trail*
- [ ] Yield tracking - *Good parts vs started quantity with yield loss categorization*

### 🟡 Pro (+1 = 30 total)
*Includes all Standard, plus:*
- [~] Scrap rate alerts - *Dashboard calculation exists, no reactive alerting yet*

### 🟠 Premium (+0 = 30 total)
*No additional WO features at Premium.*

### 🔴 Enterprise (+1 = 31 total)
*Includes all Pro, plus:*
- [ ] Work order costing

### ⛔ Out of Scope (ERP)
- Sales order management
- Customer invoicing
- Order costing/pricing
- Credit management

---

## 2. Order Management

### 🟢 Lite (8 features)
- [x] Create order
- [x] Order status workflow
- [x] Customer linkage
- [x] Customer notes/timeline
- [x] Order viewers (invite external viewers)
- [x] Estimated completion
- [x] Step distribution view
- [x] Bulk part operations

### 🟠 Premium (+1 = 9 total)
*Includes all Lite, plus:*
- [x] HubSpot integration - *Deal sync, gate tracking*

---

## 3. Parts & Part Types

### 🟢 Lite (11 features)
- [x] Create parts
- [x] Part status tracking (CREATED → IN_PROGRESS → COMPLETE)
- [x] Part type assignment
- [x] Step assignment
- [x] Order/WO linkage
- [x] ERP ID
- [x] Advance to next step
- [x] Part selection endpoint
- [x] Part type catalog
- [x] ID prefix configuration
- [x] ERP linkage for part types

### 🔵 Standard (+5 = 16 total)
*Includes all Lite, plus:*
- [x] Sampling assignment
- [x] Rework counter
- [x] Batch operations
- [~] Parent-child genealogy - *MaterialLot parent FK*
- [~] Lot merge/split - *Split exists, merge not implemented*

---

## 4. Process Definition & Routing

### 🟢 Lite (3 features)
- [x] Create process
- [x] Process steps with sequence
- [x] Process with steps hierarchical view

### 🔵 Standard (+5 = 8 total)
*Includes all Lite, plus:*
- [x] Batch process flag
- [x] Remanufacturing flag
- [x] Step branching/routing (conditional paths) - *StepEdge with edge_type, React Flow visual editor*
- [x] Decision points - *Visual decision point configuration*
- [~] Rework loops - *ALTERNATE/ESCALATION edge types + cycle control exist*

### 🟡 Pro (+0 = 8 total)
*No additional routing features at Pro.*

### 🟠 Premium (+0 = 8 total)
*No additional routing features at Premium.*

### 🔴 Enterprise (+0 = 8 total)
*No additional routing features at Enterprise.*

### ⛔ Out of Scope (PLM)
- Engineering change orders (ECO/ECR)
- Design revision control
- Engineering BOM management (effectivity dates, ECOs)

---

## 5. Steps & Workflow Control

### 🟢 Lite (4 features)
- [x] Create steps with ordering
- [x] Step ordering
- [x] Expected duration
- [x] Last step flag

### 🔵 Standard (+11 = 15 total)
*Includes all Lite, plus:*
- [x] Pass threshold
- [x] QA signoff requirement
- [x] Quarantine blocking
- [x] Sampling requirement
- [x] Measurement definitions per step
- [x] Next step routing - *Decision-based routing via StepEdge with conditions*
- [x] First Piece Inspection - *FPIRecord with 4 scopes: PER_WORK_ORDER, PER_SHIFT, PER_EQUIPMENT, PER_OPERATOR*
- [~] Step override workflow - *Override types: MISSING_QA, MEASUREMENT_FAIL, FPI_FAIL, TRAINING_EXPIRED*
- [~] Step execution measurements - *100% capture not tied to sampling*
- [~] Controlled rollback - *rollback_requires_approval on Steps*
- [~] Step requirements - *10 types: measurement, document, signoff, training, calibration, fpi, qa_approval, etc.*

---

## 6. Equipment & Work Centers

### 🟢 Lite (2 features)
- [x] Equipment types
- [x] Equipment instances

### 🔵 Standard (+10 = 12 total)
*Includes all Lite, plus:*
- [x] Equipment usage tracking
- [x] Equipment-error correlation
- [x] Equipment documents
- [x] Equipment availability status - *IN_SERVICE/OUT_OF_SERVICE/IN_CALIBRATION/IN_MAINTENANCE/RETIRED*
- [~] Work center definitions - *WorkCenter model with equipment M2M, capacity_units, default_efficiency*
- [~] Downtime logging (start/end) - *DowntimeEvent model*
- [~] Downtime reason codes - *DowntimeEvent.category + reason fields*
- [~] Planned vs unplanned downtime - *DowntimeEvent.category choices*
- [~] Setup/changeover tracking - *DowntimeEvent.category='changeover'*
- [ ] OEE calculation (Availability × Performance × Quality) - *Components exist, calculation endpoint needed*

### 🟡 Pro (+0 = 12 total)
*No additional equipment features at Pro. Calibration tracked separately (Section 25).*

### 🔴 Enterprise (+2 = 14 total)
*Includes all Pro, plus:*
- [ ] Maintenance scheduling
- [ ] Maintenance work orders

### ⛔ Out of Scope (CMMS)
- Spare parts inventory
- Equipment repair history
- Calibration management (detailed lab management)

---

## 7. Labels & Scanning

### 🔵 Standard (8 features)
- [ ] QR code generation - *Serial string encoding, not URLs*
- [ ] Code 128 barcode generation
- [ ] PDF part label endpoint - *Batch mode for multi-label PDF*
- [ ] Print Label buttons - *On part detail and WO detail pages*
- [ ] Tablet camera QR scanner - *In-browser camera, scan icon in nav*
- [ ] Universal serial lookup - *Resolves part, WO, or lot number to route*
- [ ] WO traveler QR/barcode - *On printed traveler PDF header*
- [ ] Material lot labels - *Lot number, supplier, expiration, QR + barcode*

---

## 8. Operator Station

### 🟢 Lite (5 features)
- [x] QA work order view
- [x] Part selection
- [x] Progress overview
- [x] General step completion - *Non-QA steps complete normally via operator*
- [x] Barcode scanning - *Keyboard wedge (HID)*

### 🔵 Standard (+10 = 15 total)
*Includes all Lite, plus:*
- [x] QA form entry
- [x] Measurement entry
- [x] Documents at station
- [x] Batch processing
- [x] Operator login/badge - *Standard Django auth*
- [ ] Operator acknowledgment - *Confirm read/understood instructions before starting*
- [~] Skill/certification verification - *Service layer exists, not enforced in step advancement*
- [x] Multi-operator tracking - *Multiple TimeEntry records per WO/step + QualityReports operators M2M*
- [ ] Add step mid-process - *Insert additional operation into live WO*
- [~] Downtime logging UI - *DowntimeEvent model exists, needs editor page*

### 🟠 Premium (+1 = 16 total)
*Includes all Standard, plus:*
- [x] 3D model at station

---

## 8. Dashboard & Analytics

### 🟢 Lite (10 features)
- [x] KPI display
- [x] CAPA status widget
- [x] In-process actions
- [x] Failed inspections list
- [x] Open dispositions list
- [x] Big screen mode (shop floor display)
- [x] Quality rates (scrap/rework)
- [x] Filter options
- [x] Disposition breakdown
- [x] Needs attention alerts

### 🔵 Standard (+8 = 18 total)
*Includes all Lite, plus:*
- [x] FPY trend (30/60/90d toggle)
- [x] Defect Pareto charts
- [x] Defect trend chart
- [x] Defect records drill-down
- [x] Defects by process
- [x] NCR trend (created vs closed)
- [x] NCR aging buckets
- [ ] OEE calculation

---

## 9. Quality Records & Quarantine

### 🟢 Lite (5 features)
- [x] Create quality report
- [x] Pass/Fail status
- [x] Link errors/defects
- [x] Operator tracking
- [x] Error type catalog

### 🔵 Standard (+8 = 13 total)
*Includes all Lite, plus:*
- [x] Equipment tracking on quality records
- [x] File attachments
- [x] Auto-quarantine on fail
- [x] Sampling audit linkage
- [x] Error examples
- [x] Part type scoping for error types
- [x] Auto part status update on disposition
- [x] Rework tracking

### 🟠 Premium (+1 = 14 total)
*Includes all Standard, plus:*
- [x] 3D annotation requirement flag

---

## 10. Quarantine & Disposition

### 🟢 Lite (4 features)
- [x] Quarantine dispositions (REWORK/SCRAP/USE_AS_IS/RETURN)
- [x] Disposition types
- [x] Disposition workflow (OPEN → IN_PROGRESS → CLOSED)
- [x] Resolution tracking

---

## 11. Measurements

### 🔵 Standard (5 features)
- [x] Define measurement specs with tolerances
- [x] Numeric tolerances (nominal/upper/lower)
- [x] Pass/Fail measurements
- [x] Record measurement values
- [x] Auto spec compliance check

---

## 12. Traceability

### 🟢 Lite (3 features)
- [x] Step transition log
- [x] Operator attribution
- [x] Audit log (Django Auditlog)

### 🔵 Standard (+9 = 12 total)
*Includes all Lite, plus:*
- [x] Equipment usage log
- [x] QA approval log
- [ ] Full genealogy
- [~] Material lot tracking - *MaterialLot + MaterialUsage models exist*
- [x] BOM explosion per WO - *BOM report (Typst) renders WO BOM; BOM/BOMLine models power it*
- [ ] Material availability check - *Before WO release, verify materials available*
- [ ] Material reservation - *Reserve specific lots for WOs to prevent double-allocation*
- [ ] Incoming material inspection - *Inspect received lots before releasing to production*
- [~] Shelf life / expiration tracking - *Track expiration, prevent use of expired lots*

---

## 13. Task Management

### 🟢 Lite (4 features)
- [x] My tasks view
- [x] Inbox (pending approvals)
- [x] CAPA tasks assigned to me
- [x] Work queue - *my_workload endpoint*

---

## 14. Scheduling & Planning

### 🟢 Lite (1 feature)
- [~] Due date warnings (overdue, at risk) - *overdue_capas in dashboard; threshold logic needed*

### 🔵 Standard (+12 = 13 total)
*Includes all Lite, plus:*

**Resource Modeling:**
- [~] Work center definitions - *WorkCenter model exists*
- [~] Shift definitions - *Shift model with start/end times, days_of_week*
- [~] Shift assignment to schedule slots - *ScheduleSlot → Shift*
- [~] Work center assignment to schedule slots - *ScheduleSlot → WorkCenter*
- [ ] Visual schedule board (drag-drop) - *ScheduleSlot model complete; UI needed*
- [ ] Calendar/holiday management
- [ ] Schedule vs actual comparison

**Dispatch:**
- [x] Daily dispatch list per work center - *dispatch_list Typst report*
- [ ] Operator work queue ("what's assigned to me")
- [ ] Claim/unclaim work

**Resource Definitions:**
- [ ] Operator skill matrix
- [ ] Setup time definitions - *Per part type per machine*

### 🟡 Pro (+3 = 16 total)
*Includes all Standard, plus:*
- [ ] Resource allocation (equipment + labor)
- [ ] Shift handoff notes
- [ ] "What's next?" suggestion - *After completing current op, system suggests next*

### 🟠 Premium (+22 = 38 total)
*Includes all Pro, plus:*

**CP-SAT Solver Engine:**
- [ ] CP-SAT job shop model - *Operations × machines × time windows (OR-Tools)*
- [ ] Finite capacity scheduling - *Work center can only process N jobs simultaneously*
- [ ] Multi-resource constraints - *Operation requires machine AND operator AND tooling*
- [ ] Setup time optimization - *Family sequencing to minimize changeover*
- [ ] WO-to-WO dependencies - *Sub-assembly must complete before final assembly*
- [ ] Backward scheduling - *Calculate latest start from due date*
- [ ] Forward scheduling - *Calculate completion from release date*
- [ ] Objective function configuration - *Minimize lateness × priority + makespan + overtime*
- [ ] Solve timeout / fallback - *Best-known solution if solver doesn't converge*
- [ ] Re-solve on changes - *New WO, machine down, priority change triggers re-solve*

**Gantt Visualization:**
- [ ] Machine Gantt view - *Rows = machines, bars = scheduled operations*
- [ ] WO Gantt view - *Rows = work orders, bars = operations across machines*
- [ ] Gantt color coding by status/priority
- [ ] Gantt zoom (hour/day/week)
- [ ] Overdue/at-risk highlighting
- [ ] Conflict/overload highlighting
- [ ] Current time marker

**Interactive Editing:**
- [ ] Drag-and-drop reschedule
- [ ] Pin/lock operations - *Solver can't move pinned operations*
- [ ] Hot list / expedite queue - *Rush jobs pinned, solver schedules around them*
- [ ] Re-solve around locks
- [ ] Schedule undo/redo

### 🔴 Enterprise (+8 = 46 total)
*Includes all Premium, plus:*

**What-If Scenarios:**
- [ ] Clone schedule into scenario
- [ ] Add/remove WOs in scenario - *"What if we accept this rush order?"*
- [ ] Change machine availability in scenario - *"What if machine 3 goes down?"*
- [ ] Compare scenarios side-by-side - *Makespan, on-time %, utilization comparison*
- [ ] Promote scenario to live

**Capacity Analytics:**
- [ ] Bottleneck identification
- [ ] Utilization % by machine/work center
- [ ] Promise date calculation - *"If you order today, deliver by X"*

> **Note:** Premium scheduling features (CP-SAT solver, Gantt, interactive editing) are classified as Premium/Enterprise by market standards but are planned for earlier delivery as a key competitive differentiator. See WO_MANAGEMENT_FEATURE_MATRIX.md for implementation roadmap.

---

## 15. Reporting

### 🔵 Standard (+10 features)
- [x] PDF generation
- [x] Email reports
- [x] Report history
- [x] Report types config
- [ ] On-time delivery rate - *% WOs completed by due date, trending*
- [ ] Cycle time analysis - *Avg/min/max per step, per part type*
- [ ] Throughput trending - *Parts per hour/day/week by work center*
- [ ] Labor efficiency - *Actual hours vs standard hours per WO, per operator*
- [x] PDF WO traveler - *Traveler endpoint + PDF service via Playwright*
- [ ] Schedule vs actual - *Compare planned schedule to actual execution*

**PDF Report Library (Typst):** BOM, CAPA, NCR, Deviation Request, Pick List, Dispatch List, Checking Aids, Calibration Certificate, Calibration Due, Training Record — all rendering end-to-end.

---

## 16. Integration

### 🟢 Lite (2 features)
- [x] Excel export
- [x] API documentation (Swagger/OpenAPI)

### 🔵 Standard (+3 = 5 total)
*Includes all Lite, plus:*
- [~] ERP integration - *ERP_id fields exist, no real-time sync*
- [ ] Report completions to ERP - *Send WO completion with quantities back*
- [ ] Webhook on WO events - *Fire webhooks on status changes, completions, quality events*

### 🟠 Premium (+1 = 6 total)
*Includes all Standard, plus:*
- [x] HubSpot CRM sync

---

## 17. Customer Portal

### 🟢 Lite (2 features)
- [x] Order tracking (read-only)
- [x] Invite viewers

### 🔵 Standard (+1 = 3 total)
*Includes all Lite, plus:*
- [x] Document access (classification-filtered)

---

## 18. Audit Trail

### 🟢 Lite (1 feature)
- [x] Model change history

### 🟡 Pro (+1 = 2 total)
*Includes all Lite, plus:*
- [x] Permission change log

---

## 19. Document Control (Pro)

### 🟡 Pro (9 features)
- [x] Create/upload documents
- [x] Version history
- [x] Document approval workflow
- [x] Document revisions
- [x] Document types/classification
- [x] Security classification (5-level: PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED/SECRET)
- [x] Document audit trail
- [x] Document statistics
- [ ] ECR/ECN change control

---

## 20. CAPA (Pro)

### 🟡 Pro (18 features)
- [x] Create CAPA
- [x] CAPA types (Corrective/Preventive/etc)
- [x] Severity levels (CRITICAL/MAJOR/MINOR)
- [x] CAPA status workflow
- [x] Auto-numbering
- [x] CAPA tasks with multi-person assignment
- [x] Task signatures
- [x] Root Cause Analysis
- [x] 5 Whys method
- [x] Fishbone/Ishikawa (6M categories)
- [x] Root cause categorization
- [x] CAPA verification
- [x] Effectiveness confirmation
- [x] CAPA approval workflow
- [x] CAPA statistics
- [x] Link to quality reports
- [x] Link to dispositions
- [x] Multi-person task assignment

### 🟠 Premium (+3 = 21 total)
*Includes all Pro, plus:*
- [x] Self-verification controls
- [x] Blocking items tracking
- [x] Completion percentage

---

## 21. SPC (Pro)

### 🟡 Pro (11 features)
- [x] Control charts (X-bar/R)
- [x] Control charts (X-bar/S)
- [x] Control charts (I-MR)
- [x] Process capability (Cp/Cpk)
- [x] Freeze baselines
- [x] Baseline versioning
- [x] Baseline audit trail
- [x] SPC print/export
- [x] Hierarchy navigation
- [ ] SPC out-of-control alerts - *Notification on Western Electric rule violation*
- [ ] Last piece inspection - *Confirm process didn't drift during run*

---

## 22. Approval Workflows (Pro)

### 🟡 Pro (10 features)
- [x] Approval templates
- [x] Multi-level approval
- [x] Group-based approval
- [x] Parallel approval
- [x] Sequential approval
- [x] Approval responses
- [x] Delegation
- [x] Signature capture with meaning
- [x] Escalation (configurable days + escalation target)
- [x] My pending approvals

### 🟠 Premium (+2 = 12 total)
*Includes all Pro, plus:*
- [x] Threshold approval
- [x] Self-approval controls

---

## 23. Sampling (Pro)

### 🟡 Pro (7 features)
- [x] Sampling rule sets
- [x] Multiple rule types (6 types)
- [x] Primary/fallback rules
- [x] Automatic fallback trigger
- [x] Sampling audit log
- [x] Sampling analytics
- [x] Part sampling assignment

---

## 24. Training Records (Pro)

### 🟡 Pro (4 features)
- [x] Training types catalog with validity periods
- [x] Training records with expiration tracking
- [x] Training requirements (linked to Step/Process/EquipmentType)
- [x] Training status tracking (current/expiring_soon/expired)

---

## 25. Calibration (Pro)

### 🟡 Pro (3 features)
- [x] Calibration records (full CRUD with result/type/traceability)
- [x] Calibration due dates (overdue/due_soon/current status)
- [x] Calibration traceability (certificate number, standards used, as-found)

### 🟠 Premium (+1 = 4 total)
*Includes all Pro, plus:*
- [x] Affected parts lookup (parts inspected during calibration period)

---

## 26. Customer Complaints (Pro)

### 🟡 Pro (3 features)
- [~] Complaint intake - *Handled via CAPA with type=CUSTOMER_COMPLAINT, no separate form*
- [~] Complaint workflow - *Uses CAPA workflow, no complaint-specific SLAs*
- [~] Complaint resolution - *Via CAPA verification, no complaint trending*

---

## 27. Audit Management (Pro)

### 🟡 Pro (2 features)
- [ ] Audit scheduling
- [ ] Audit findings tracking

---

## 28. Compliance (Pro)

### 🟡 Pro (3 features)
- [~] Audit log export - *Export audit trail for auditor review*
- [ ] Record retention policy - *Configurable retention periods (7yr auto, life+2yr medical)*
- [ ] Customer property identification - *Track customer-supplied material/tooling separately*

---

## 29. Outside Processing (Pro)

### 🟡 Pro (4 features)
- [ ] Outside processing step type - *Mark routing step as "outside processing"*
- [ ] Subcontractor tracking - *Which supplier, expected/actual dates*
- [ ] Ship-out / receive-back workflow - *Track parts leaving and returning; receiving inspection on return*
- [ ] Supplier cert verification - *Verify NADCAP, AS9100 certs before allowing outside processing*

### Design Notes

Thin layer on existing models. Core implementation:
- `is_outside_processing` flag on Step model
- Supplier FK on the step (who performs the outside work)
- Two status transitions on parts at that step: **shipped out** / **received back** (with dates)
- Incoming inspection trigger on receive-back
- ASL check (SupplierApproval + SupplierCertification) to verify supplier certs are current before allowing the step to proceed

Depends on the Supplier Quality Management module (Section 35) — supplier approvals and certification tracking provide the cert verification. Common outside processes: heat treat, plating/coating, NDT, special welding.

---

## 30. Quality Reports & Certificates (Pro)

### 🟡 Pro (4 features)
- [~] Certificate of Conformance (CoC) - *Generate from WO completion data*
- [~] FAI report (AS9102) - *Forms 1, 2, 3 from measurement data*
- [ ] Device History Record (DHR) - *ISO 13485/21 CFR 820 only — deprioritized, aero/auto focus first*
- [~] Lot traceability report - *Forward/reverse traceability document*

---

## 31. PPAP (Pro/Enterprise)

### 🟡 Pro (14 features)
- [x] 1. Design Records - *Document storage*
- [~] 2. Engineering Change Documents - *No formal ECN workflow*
- [ ] 3. Customer Engineering Approval
- [x] 5. Process Flow Diagram - *Process/Steps model*
- [~] 7. Control Plan - *Document storage, no structured model*
- [x] 9. Dimensional Results - *Full SPC*
- [~] 10. Material/Performance Test Results - *No cert linking*
- [x] 11. Initial Process Studies (Cpk) - *Full SPC capability*
- [~] 12. Qualified Lab Documentation - *Document storage*
- [ ] 13. Appearance Approval Report
- [x] 16. Checking Aids - *Equipment model + checking_aids Typst report*
- [ ] 17. Customer-Specific Requirements
- [ ] 18. Part Submission Warrant (PSW)
- [ ] PPAP Submission Tracker

### 🔴 Enterprise (+6 = 20 total)
*Includes all Pro, plus:*
- [~] 4. Design FMEA - *Document storage, no RPN tracking*
- [~] 6. Process FMEA - *Document storage, no RPN tracking*
- [ ] 8. MSA / Gage R&R
- [ ] 14-15. Sample Parts / Master Sample - *Physical items*
- [ ] Drawing extraction/ballooning - *1Factory strength*
- [ ] Auto-PFMEA population - *1Factory strength*

---

## 32. 3D Visualization (Premium)

### 🟠 Premium (5 features)
- [x] Upload 3D models
- [x] View 3D models
- [x] Defect annotations
- [x] Heatmap visualization
- [x] Link to quality reports

---

## 33. AI Assistant (Premium)

### 🟠 Premium (3 features)
- [x] Document search (vector + hybrid)
- [x] Document query (keyword)
- [x] Document embeddings (automatic on upload)

---

## 34. Risk Management (Enterprise)

### 🔴 Enterprise (2 features)
- [ ] FMEA
- [ ] Risk register

---

## 35. Supplier Quality (Enterprise)

### 🔴 Enterprise (2 features)
- [ ] Supplier scorecards
- [ ] Supplier audits

---

## Platform Capabilities (Not Tier-Tracked)

Integration and connectivity features are platform concerns, not MES functionality.

### Current Platform Features
- [x] REST API (full CRUD)
- [x] Email notifications (SMTP)
- [x] Azure Blob Storage (documents)
- [x] CSV import/export for bulk operations
- [x] HubSpot CRM sync

### Planned Platform Features
- [ ] Basic label printing
- [ ] Barcode/QR code generation
- [ ] Webhook support for events
- [ ] Document revision notifications
- [ ] Quality alert notifications
- [ ] ERP integration (customer-specific)

### Enterprise Platform Features (Future)
- [ ] OPC-UA server/client
- [ ] MTConnect adapter
- [ ] Real-time event streaming
- [ ] Enterprise service bus integration

### ⛔ Out of Scope
- ETL pipelines
- Master data management
- Enterprise integration platform
- EDI (850, 856) - use REST APIs instead

---

## Summary

### Feature Counts by Tier (cumulative)

| Tier | Cumulative | New at Tier |
|------|-----------|-------------|
| **Lite** | 83 | 83 |
| **Standard** | 199 | 116 |
| **Pro** | 296 | 97 |
| **Premium** | 336 | 40 |
| **Enterprise** | 372 | 36 |

### Progress by Tier (features new at each tier)

| Tier | Done | API Ready | Missing | Total | Progress |
|------|------|-----------|---------|-------|----------|
| **Lite** | 80 | 3 | 0 | 83 | 96% |
| **Standard** | 50 | 24 | 42 | 116 | 43% |
| **Pro** | 64 | 13 | 20 | 97 | 66% |
| **Premium** | 18 | 0 | 22 | 40 | 45% |
| **Enterprise** | 5 | 2 | 29 | 36 | 14% |

> Progress = Complete [x] features only. Standard is 43% because expanded scheduling (46 features), labels/scanning (8), WO lifecycle gaps (10), material traceability (5), shop floor execution (3), and reporting (5) are mostly unbuilt. Pro includes outside processing (4), compliance (3), quality reports/certs (4), and audit management (2) as gaps.

### What We'll Never Build

These belong in specialized systems:

| Feature                    | Belongs In                     |
|----------------------------|--------------------------------|
| MRP / demand planning      | ERP (SAP, Oracle, NetSuite)    |
| Inventory management       | ERP                            |
| Purchase orders            | ERP                            |
| Preventive maintenance     | CMMS (Fiix, UpKeep)            |
| Full calibration mgmt      | CMMS (track due dates only)    |
| Employee time & attendance | HRIS (ADP, Workday)            |
| BI / ad-hoc reporting      | BI (Power BI, Tableau)         |
| ECO/ECR workflow           | PLM (Arena, Windchill)         |
| Full BOM revision control  | PLM/ERP                        |
| Gage R&R studies           | Metrology software             |

> **Clarification:** We track *production BOM* (what parts went into this assembly) for traceability. We do NOT manage *engineering BOM* (revision control, effectivity dates, ECOs).

---

## Positioning

**Today (372 features across 35 sections):**
- Lite MES: 96% complete (83 features, 80 done) — effectively shippable
- Standard MES: 43% complete (116 new features; quality/equipment ops mostly done, scheduling/labels/WO lifecycle/material gaps)
- Pro MES: 66% complete (97 new features; CAPA/SPC/sampling/approvals done, PPAP/audit/outside processing/compliance gaps)
- Premium: 45% complete (40 new features; 3D viz/AI/advanced workflows done, CP-SAT scheduling unbuilt)
- Enterprise: 14% (36 features, not target market)
- Reman Add-on: API complete, needs UI
- Platform: 5 integrations complete (REST API, Email, Azure Blob, CSV, HubSpot)

**Key gaps:**
1. **Scheduling** — biggest unbuilt area: 46 features across Standard/Pro/Premium/Enterprise, only 1 partially implemented
2. **Labels & Scanning** — 8 Standard features, all unbuilt
3. **WO Lifecycle** — 11 Standard features (splitting, rework, yield tracking), all unbuilt
4. **Outside Processing** — 4 Pro features, all unbuilt (AS9100 requirement)
5. **Quality Reports/Certs** — CoC, FAI, DHR partially built

**Target buyer:** Pro tier for compliance-driven manufacturers who:
- Need quality traceability (ISO 9001, IATF 16949, AS9100)
- Don't have or want a full ERP
- Want shop floor visibility without enterprise complexity
- Value the quality/3D/AI differentiators

**Tier use cases:**
- **Lite:** Non-regulated job shops who just want basic "where's my part?" visibility. Can upgrade when they win aerospace contracts.
- **Standard:** Shops that need production control, scheduling, and quality gates but aren't in regulated industries.
- **Pro:** Regulated manufacturers — AS9100, IATF 16949, ISO 13485. The compliance layer.
- **Premium:** Manufacturers wanting advanced capabilities — 3D defect visualization, AI assistant, advanced workflow controls.
- **Enterprise:** Large facilities needing multi-site, IoT, risk management, supplier quality. Not our current target.

**Not competing with:** SAP ME, Siemens Opcenter, Plex, Rockwell FTPC (Enterprise tier)
**Competing with:** ProShop, TrakSYS, 1Factory, QT9 (Pro tier)
**Competing with:** MachineMetrics, Amper, Redzone (Standard tier)
**Replacing:** Prodio, Steelhead, spreadsheets (Lite tier)

---

## Remanufacturing Add-on

Not included in tier counts above. Available as add-on to any tier.

**Status:** API complete ✅, UI needed

| Feature | Model | Status |
|---------|-------|--------|
| Core receiving & tracking | Core | [~] API ready |
| Core grading (A/B/C/Scrap) | Core.condition_grade | [~] API ready |
| Disassembly workflow | Core.start_disassembly/complete_disassembly | [~] API ready |
| Harvested component tracking | HarvestedComponent | [~] API ready |
| Component grading | HarvestedComponent.condition_grade | [~] API ready |
| Accept component to inventory | HarvestedComponent.accept_to_inventory | [~] API ready |
| Core → Assembly genealogy | MaterialUsage.harvested_component | [~] API ready |
| Core credit/exchange tracking | Core.core_credit_* + issue_credit action | [~] API ready |
| Disassembly BOM (expected yields) | DisassemblyBOMLine | [~] API ready |
| Life-limited part tracking | Part.total_cycles, Part.cycles_remaining | [ ] Not started |
| Back-to-birth traceability | HarvestedComponent → Core → historical | [~] API ready |

### Reman Tier Requirements

| Customer Type | Tier Needed | Why |
|---------------|-------------|-----|
| Non-regulated reman (automotive aftermarket) | **Lite + Reman** | Core/component traceability only. |
| Regulated reman (AS9100, IATF 16949) | **Pro + Reman** | Full genealogy required: lot traceability for new materials + core traceability for harvested. |

> **Note:** Aerospace/defense remanufacturers almost always need Pro due to AS9100 lot traceability requirements.
