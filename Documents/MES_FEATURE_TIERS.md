# MES Feature Tiers

**Last Updated:** February 20, 2026

This document categorizes Manufacturing Execution System (MES) features by capability level. Each tier is **cumulative** - it includes all features from previous tiers plus new additions.

Legend: [x] = Implemented | [~] = API complete, needs UI | [ ] = Not yet implemented | ⛔ = Out of scope

---

## Tier Definitions

| Tier | Description | Target Customer |
|------|-------------|-----------------|
| **Lite** | Basic shop floor visibility - "where is my part?" | Small job shops without compliance requirements |
| **Standard** | Full production tracking + traceability | **Aerospace/Defense (AS9100), Automotive (IATF 16949), Medical (ISO 13485)** - compliance-driven manufacturers |
| **Enterprise** | Real-time integration + advanced analytics | Large facilities, multi-plant operations |
| **Out of Scope** | Belongs in ERP, PLM, or specialized systems | - |

> ⚠️ **Note for regulated industries:** AS9100 (aerospace), IATF 16949 (automotive), and ISO 13485 (medical) require Standard tier features: lot traceability, SPC, calibration tracking. Lite tier is for non-regulated shops only.

---

## 1. Work Order Management

### 🟢 Lite MES (8 features)
- [x] Work order creation from customer orders
- [x] Work order status (PENDING → IN_PROGRESS → COMPLETED, plus ON_HOLD, CANCELLED, WAITING_FOR_OPERATOR)
- [x] Link work orders to parts
- [x] Due dates (expected_completion and true_completion)
- [x] Customer association (indirect, via related order)
- [x] Work order listing and filtering
- [x] Work order notes/comments - *customer_note field with structured timeline*
- [x] Work order priority levels (Urgent, High, Normal, Low)

### 🟡 Standard MES (14 total)
*Includes all Lite, plus:*
- [ ] Work order scheduling (assign to date/shift)
- [ ] Capacity loading view (hours assigned per work center/day)
- [ ] Work order splitting (split large orders)
- [ ] Work order combining (batch similar jobs)
- [ ] Estimated vs actual hours tracking
- [ ] Work order templates

### 🔴 Enterprise MES (19 total)
*Includes all Standard, plus:*
- [ ] Finite capacity scheduling (constraint-based)
- [ ] Capacity planning with constraint modeling
- [ ] Automated scheduling optimization
- [ ] Multi-plant work order routing
- [ ] Real-time schedule adjustments

### ⛔ Out of Scope (ERP)
- Sales order management
- Customer invoicing
- Order costing/pricing
- Credit management

---

## 2. Process & Routing

### 🟢 Lite MES (6 features)
- [x] Process definitions (named workflows)
- [x] Process steps with sequence (linear)
- [x] Step instructions/documentation
- [x] Link processes to part types
- [x] Process flow visualization
- [x] Step estimated duration

### 🟡 Standard MES (17 total)
*Includes all Lite, plus:*
- [x] Step-level inspection requirements
- [x] Step dependencies (predecessor/successor) - *StepEdge model*
- [x] Routing versioning with effectivity dates - *Process versioning with previous_version FK*
- [ ] Step work center assignment
- [ ] Alternative routings per part type
- [ ] Setup time vs run time separation
- [ ] Parallel step support (concurrent operations)
- [x] Process approval workflow - *Processes.status (DRAFT/PENDING_APPROVAL/APPROVED/DEPRECATED), approve(), submit_for_approval() methods*
- [ ] Revision comparison (diff view)
- [x] Step override workflow - *StepOverride model with request/approve/reject/expire workflow for blocked parts*
- [x] Controlled rollback - *StepRollback model with undo_window_minutes and rollback_requires_approval on Steps*

### 🔴 Enterprise MES (20 total)
*Includes all Standard, plus:*
- [x] Dynamic routing (conditional paths) - *StepEdge with edge_type + decision_type on Steps*
- [ ] Routing optimization suggestions
- [ ] Cross-plant routing

### ⛔ Out of Scope (PLM)
- Engineering change orders (ECO/ECR)
- Design revision control
- Engineering BOM management (effectivity dates, ECOs)

> **Note:** Production BOM for traceability (Standard tier) is in scope. Engineering BOM management is not.

---

## 3. Shop Floor Data Collection

### 🟢 Lite MES (5 features)
- [x] Step start/complete timestamps (StepTransitionLog)
- [x] Operator attribution (who worked on part)
- [x] Big screen mode (shop floor dashboard) - *UI implemented, needs API wiring for live data*
- [x] Barcode scanning for part identification - *Works via keyboard wedge (HID) - any text input accepts scanner*
- [x] Simple start/stop buttons per operation - *DowntimeEvent start/end, TimeEntry clock in/out, StepExecution entry/exit*

### 🟡 Standard MES (13 total)
*Includes all Lite, plus:*
- [x] Inspection data entry
- [x] Quality report creation
- [x] Measurement recording
- [~] Labor time tracking (clock in/out per operation) - *TimeEntry model with entry_type choices*
- [x] Scrap disposition workflow with reason codes - *QuarantineDisposition model*
- [ ] Rework quantity tracking
- [ ] Setup time tracking
- [~] Downtime logging at workstation - *DowntimeEvent model*

### 🔴 Enterprise MES (17 total)
*Includes all Standard, plus:*
- [ ] Machine integration (OPC-UA, MTConnect)
- [ ] Automatic cycle time capture
- [ ] Real-time production counts from PLCs
- [ ] IoT sensor data collection

### ⛔ Out of Scope (Time & Attendance)
- Employee clock in/out (shift start/end)
- Payroll hours
- Overtime tracking
- PTO/absence management

---

## 4. Production Tracking & WIP

### 🟢 Lite MES (6 features)
- [x] Part status tracking (CREATED → IN_PROGRESS → COMPLETE)
- [x] Current step visibility
- [x] Work order progress percentage
- [x] Part location (implicit via current step)
- [x] Serial number tracking
- [x] Queue visibility (what's waiting at each step) - *wip_at_step endpoint*

### 🟡 Standard MES (14 total)
*Includes all Lite, plus:*
- [x] WIP count by process step - *wip_summary endpoint*
- [~] Simple WIP aging (time at current step) - *entered_at exposed, client calculates*
- [~] Lead time tracking (order to completion) - *WorkOrder duration fields*
- [ ] WIP count by work center
- [ ] WIP value tracking (cost at each stage)
- [ ] Bottleneck identification
- [ ] Cycle time analysis
- [ ] Throughput metrics

### 🔴 Enterprise MES (18 total)
*Includes all Standard, plus:*
- [ ] Real-time WIP dashboards with drill-down
- [ ] Predictive completion dates
- [ ] Constraint-based WIP limits
- [ ] Theory of Constraints (TOC) metrics

### ⛔ Out of Scope (ERP)
- Inventory valuation
- Standard costing
- Variance analysis
- Work order costing

---

## 5. Equipment & Work Centers

### 🟢 Lite MES (3 features)
- [x] Equipment master records
- [x] Equipment types
- [x] Equipment assignment to steps

### 🟡 Standard MES (12 total)
*Includes all Lite, plus:*
- [x] Equipment usage logging
- [~] Work center definitions (grouping of equipment) - *WorkCenter model with equipment M2M*
- [x] Equipment availability status - *EquipmentStatus: IN_SERVICE, OUT_OF_SERVICE, IN_CALIBRATION, IN_MAINTENANCE, RETIRED + is_operational property*
- [~] Simple downtime logging (start/end) - *DowntimeEvent model*
- [~] Downtime reason codes - *DowntimeEvent.category + reason fields*
- [~] Planned vs unplanned downtime - *DowntimeEvent.category choices*
- [~] Setup/changeover tracking - *DowntimeEvent.category='changeover'*
- [x] Equipment calibration status with due date tracking - *CalibrationRecord model + CalibrationRecordsPage UI*
- [~] OEE calculation (Availability × Performance × Quality) - *All components present (DowntimeEvent, TimeEntry, QualityReports); calculation endpoint needed*

### 🔴 Enterprise MES (16 total)
*Includes all Standard, plus:*
- [ ] Real-time machine monitoring
- [ ] Predictive maintenance alerts
- [ ] Energy consumption tracking
- [ ] Equipment utilization optimization

### ⛔ Out of Scope (CMMS)
- Preventive maintenance scheduling
- Spare parts inventory
- Maintenance work orders
- Equipment repair history
- Calibration management (detailed)

---

## 6. Quality Integration

### 🟢 Lite MES (5 features)
- [x] In-process inspection triggers
- [x] Pass/fail determination
- [x] NCR creation on failure - *Auto-creates QuarantineDisposition on QualityReport fail*
- [x] Quality holds on parts - *Auto-quarantine on fail; block_on_quarantine prevents advancement*
- [x] First piece inspection (FPI) - *FPIRecord model with scope options (PER_WORK_ORDER, PER_SHIFT, PER_EQUIPMENT, PER_OPERATOR); FpiStatusBanner UI; designate/waive/verify actions*

### 🟡 Standard MES (17 total)
*Includes all Lite, plus:*
- [x] Measurement definitions with tolerances - *StepMeasurementRequirement with is_mandatory flag*
- [x] CAPA workflow
- [x] SPC charts (X-bar/R, I-MR, Cpk/Ppk)
- [x] Sampling rules engine
- [x] 3D defect annotation
- [x] Automatic sampling triggers based on production count - *SamplingFallbackApplier evaluates on part creation*
- [ ] Last piece inspection workflow
- [ ] SPC alerts to operators (out-of-control notification)
- [x] Quality gates (cannot proceed without inspection) - *block_on_quarantine, requires_qa_signoff, pass_threshold enforced in can_advance_step(); auto-quarantine + auto-disposition on fail*
- [~] Defect Pareto by work center - *defect_pareto endpoint exists; work center breakdown needs enhancement*
- [ ] First Article Inspection (FAI) status tracking - *Track FAI approval per part number*
- [ ] Balloon numbering for characteristics - *Link measurements to drawing callouts*

### 🔴 Enterprise MES (23 total)
*Includes all Standard, plus:*
- [ ] Real-time quality dashboards per line
- [ ] Predictive quality (ML-based)
- [ ] Automated inspection integration (CMM, vision)
- [ ] Closed-loop process adjustments
- [ ] AS9102 FAI form generation - *Auto-generate Forms 1, 2, 3 from measurement data*
- [ ] Material cert linking for FAI - *Trace raw materials to Form 2*
- [ ] Special process cert tracking - *NADCAP certs for Form 2*
- [ ] PPAP support - *Automotive Production Part Approval Process*

### ⛔ Out of Scope (Metrology)
- CMM programming
- GD&T analysis
- Measurement uncertainty studies
- Gage R&R studies (measurement system analysis)

---

## 7. Material & Inventory

### 🟢 Lite MES (3 features)
- [x] Part serial number tracking (ERP_id with auto-generation)
- [x] Part-to-order linkage
- [x] Batch grouping via work orders (not explicit lot tracking)

### 🟡 Standard MES (13 total)
*Includes all Lite, plus:*
- [~] Material lot tracking (MaterialLot model) - *Full lot model with status, expiration, CoC*
- [~] Material usage tracking (which lot used on which part) - *MaterialUsage junction table*
- [ ] Material issue to work order
- [ ] Material shortage alerts
- [~] Full lot genealogy (lot → parts → assemblies) - *MaterialUsage + AssemblyUsage*
- [~] Assembly structure tracking (BOM for traceability, not PLM) - *BOM + BOMLine + AssemblyUsage models*
- [~] Material consumption tracking - *MaterialUsage.qty_consumed*
- [ ] Backflush material on completion
- [~] Material substitution tracking - *MaterialUsage.is_substitute + substitution_reason*
- [~] Lot splitting/merging - *MaterialLot.parent_lot FK for splits*

### 🔴 Enterprise MES (16 total)
*Includes all Standard, plus:*
- [ ] Real-time inventory sync with ERP
- [ ] Automated material requests
- [ ] Kanban replenishment signals

### ⛔ Out of Scope (ERP/PLM)
- Inventory management (stock levels, reorder points)
- Purchase orders
- Receiving
- Warehouse management
- Material costing
- Supplier management
- Full BOM revision control (ECOs, effectivity dates) → PLM

> **Note:** Standard MES includes *lightweight assembly tracking* for traceability (what parts went into this assembly). This is NOT full PLM BOM management - it's production genealogy.

---

## 8. Scheduling & Planning

### 🟢 Lite MES (3 features)
- [x] Due dates on orders and work orders
- [x] Manual prioritization (implicit via order)
- [~] Due date warnings (overdue, at risk) - *overdue_capas in dashboard; expected_completion fields exist; "at risk" threshold logic needed*

### 🟡 Standard MES (12 total)
*Includes all Lite, plus:*
- [~] Visual schedule board (drag-drop) - *ScheduleSlot model complete; UI needs implementation*
- [ ] Work order sequencing
- [ ] Capacity loading view
- [~] Shift-based scheduling - *ScheduleSlot model links WorkOrder to Shift*
- [ ] Resource allocation (equipment + labor)
- [ ] Schedule vs actual comparison
- [ ] Gantt chart visualization
- [~] Shift definitions - *Shift model with start/end times, days_of_week*
- [ ] Calendar/holiday management

### 🔴 Enterprise MES (17 total)
*Includes all Standard, plus:*
- [ ] Advanced Planning & Scheduling (APS)
- [ ] Constraint-based optimization
- [ ] What-if scenario modeling
- [ ] Multi-resource scheduling
- [ ] Integration with ERP MRP

### ⛔ Out of Scope (ERP/APS)
- Material Requirements Planning (MRP)
- Demand forecasting
- Sales & Operations Planning (S&OP)
- Long-term capacity planning

---

## 9. Reporting & Analytics

### 🟢 Lite MES (5 features)
- [x] Excel export
- [~] Production summary report (parts completed per day/week) - *get_step_distribution API; needs PDF template*
- [~] Work order status report - *dashboard KPIs, get_process_stages API; needs PDF template*
- [x] Basic quality summary (pass/fail counts) - *quality_rates endpoint, kpis endpoint*
- [~] Overdue work order report - *overdue calculations exist; needs report format*

### 🟡 Standard MES (18 total)
*Includes all Lite, plus:*
- [x] Quality metrics dashboard
- [x] FPY, scrap rate, rework rate
- [x] Defect Pareto charts
- [x] NCR trends and aging
- [x] SPC reports with PDF export
- [~] Operator productivity report - *TimeEntry model tracks labor by user; needs report aggregation*
- [~] OEE reports by equipment - *Components exist; needs report format*
- [ ] Cycle time analysis reports
- [ ] Schedule adherence reports
- [~] Labor efficiency reports - *TimeEntry duration_hours; needs report aggregation*
- [ ] WIP aging reports
- [~] Lot traceability reports - *MaterialLot, MaterialUsage, AssemblyUsage models complete; needs report template*
- [~] Equipment utilization reports - *DowntimeEvent, EquipmentStatus data available; needs aggregation*

### 🔴 Enterprise MES (23 total)
*Includes all Standard, plus:*
- [ ] Real-time production dashboards
- [ ] Custom report builder
- [ ] Scheduled report delivery
- [ ] Multi-site rollup reports
- [ ] Executive KPI dashboards

### ⛔ Out of Scope (BI Tools)
- Ad-hoc reporting (Power BI, Tableau)
- Data warehousing
- Cross-system analytics
- Financial reporting

---

## Platform Capabilities (Not Tier-Tracked)

Integration and connectivity features are platform concerns, not MES functionality. They depend on customer-specific requirements (which ERP? which protocols?) and are tracked separately.

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

### Feature Counts by Tier

| Category | Lite | Standard | Enterprise |
|----------|------|----------|------------|
| Work Orders | 8 | 14 | 19 |
| Process/Routing | 6 | 17 | 20 |
| Data Collection | 5 | 13 | 17 |
| Production Tracking | 6 | 14 | 18 |
| Equipment | 3 | 12 | 16 |
| Quality | 5 | 17 | 25 |
| Material | 3 | 13 | 16 |
| Scheduling | 3 | 12 | 17 |
| Reporting | 5 | 18 | 23 |
| **TOTAL** | **44** | **130** | **171** |

### Lite MES Progress (44 features)

| Category | Done | API Ready | Remaining | Progress |
|----------|------|-----------|-----------|----------|
| Work Orders | 8 | 0 | 0 | 100% |
| Process/Routing | 6 | 0 | 0 | 100% |
| Data Collection | 5 | 0 | 0 | 100% |
| Production Tracking | 6 | 0 | 0 | 100% |
| Equipment | 3 | 0 | 0 | 100% |
| Quality | 5 | 0 | 0 | 100% |
| Material | 3 | 0 | 0 | 100% |
| Scheduling | 2 | 1 | 0 | 100% |
| Reporting | 2 | 3 | 0 | 100% |
| **TOTAL** | **40** | **4** | **0** | **100%** |

### Lite MES Complete! 🎉

All 44 Lite MES features are now implemented.

**API Ready (need UI polish):**
1. Due date warnings (overdue, at risk)
2. Production summary report
3. Work order status report
4. Overdue work order report

### Standard MES Progress (86 features beyond Lite)

| Category            | Done   | API Ready | Remaining | Progress |
|---------------------|--------|-----------|-----------|----------|
| Work Orders         | 0      | 0         | 6         | 0%       |
| Process/Routing     | 6      | 0         | 5         | 55%      |
| Data Collection     | 4      | 2         | 2         | 75%      |
| Production Tracking | 1      | 2         | 5         | 38%      |
| Equipment           | 3      | 6         | 0         | 100%     |
| Quality             | 7      | 1         | 4         | 67%      |
| Material            | 0      | 7         | 3         | 70%      |
| Scheduling          | 0      | 3         | 6         | 33%      |
| Reporting           | 5      | 5         | 3         | 77%      |
| **TOTAL**           | **26** | **26**    | **34**    | **60%**  |

> **Note:** "API Ready" means models + serializers + viewsets complete, pending UI implementation.

### To Reach Standard MES (+82 features on top of Lite)

Major structural models (API complete ✅, UI needed):
1. **MaterialLot + MaterialUsage** - Lot traceability ✅
2. **BOM + BOMLine + AssemblyUsage** - Assembly genealogy ✅
3. **TimeEntry** - Labor time tracking ✅
4. **WorkCenter** - Work center definitions ✅
5. **DowntimeEvent** - Equipment downtime ✅
6. **Shift + ScheduleSlot** - Scheduling ✅

Standard unlocks (once UI complete):
- Full quality suite (SPC, CAPA, sampling, measurements) - *mostly done*
- Equipment tracking + OEE - *API ready*
- Scheduling + capacity planning - *API ready*
- Compliance reporting

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
| Advanced scheduling (APS)  | APS (Opcenter, PlanetTogether) |
| BI / ad-hoc reporting      | BI (Power BI, Tableau)         |
| ECO/ECR workflow           | PLM (Arena, Windchill)         |
| Full BOM revision control  | PLM/ERP                        |
| Gage R&R studies           | Metrology software             |

> **Clarification:** We track *production BOM* (what parts went into this assembly) for traceability. We do NOT manage *engineering BOM* (revision control, effectivity dates, ECOs).

---

## Positioning

**Today:**
- Lite MES: 100% complete (40 done + 4 API-ready of 44 features) ✅
- Standard MES: 60% complete (24 done + 26 API-ready of 84 features beyond Lite)
- MES Standard Backend: All major models complete (WorkCenter, Shift, ScheduleSlot, DowntimeEvent, MaterialLot, TimeEntry, BOM) - needs 7 editor pages
- Reman Add-on: API complete, needs UI
- Platform: 5 integrations complete (REST API, Email, Azure Blob, CSV, HubSpot)

**Reality check:** Lite tier is for shops without compliance requirements. Regulated manufacturers (aerospace, automotive, medical) need **Standard** for:
- AS9100/IATF 16949 lot traceability
- NADCAP SPC requirements
- Equipment calibration tracking
- Full genealogy for recalls

Reman is an **add-on** to either tier - Lite for non-regulated, Standard for regulated.

**Sweet spot:** Standard MES for compliance-driven manufacturers who:
- Need quality traceability (ISO 9001, IATF 16949, AS9100)
- Don't have or want a full ERP
- Want shop floor visibility without enterprise complexity
- Value the quality/3D/AI differentiators

**Lite tier use case:** Non-regulated job shops who just want basic "where's my part?" visibility. Can upgrade to Standard when they win aerospace contracts.

**Not competing with:** SAP ME, Siemens Opcenter, Plex, Rockwell FTPC

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
| Non-regulated reman (automotive aftermarket) | **Lite + Reman** | Core/component traceability only. New materials tracked as "used new O-rings" without lot numbers. |
| Regulated reman (AS9100, IATF 16949) | **Standard + Reman** | Full genealogy required: lot traceability for new materials + core traceability for harvested. Auditors will ask "what lot did the new spring come from?" |

> **Note:** Aerospace/defense remanufacturers almost always need Standard due to AS9100 lot traceability requirements, not because of reman itself.
