# Work Order Management: Feature Matrix

**Last Updated:** March 24, 2026
**Scope:** Work order management features for small-to-mid manufacturers (50-500 employees). Enterprise-only features (multi-site, IoT, advanced compliance) are tracked separately.
**Alignment:** Maps to five-tier structure (Lite/Standard/Pro/Premium/Enterprise) in MES_FEATURE_TIERS.md. See FEATURE_INVENTORY.csv for granular competitor benchmarking.

---

## How to Read This Document

**Status Key:**
- **DONE** = Fully implemented
- **API** = Backend complete, needs UI
- **PARTIAL** = Some pieces exist
- **PLANNED** = Not started

**Complexity:**
- **S (Small):** Days. One developer.
- **M (Medium):** Weeks. Multiple models, business logic, UI.
- **L (Large):** Months. Cross-cutting concerns, algorithm work.

Features are organized into **implementation buckets** — groups of features that ship together. Each bucket has a rough effort estimate.

---

## Bucket 1: Labels & Scanning (~1 week) — Standard

QR code generation, PDF labels, tablet camera scanning. Enables scan-and-go workflows.

### Design Decisions

- **QR content:** Serial string (e.g., `INJ-2025-0847`), NOT a URL. Environment-agnostic, survives domain changes.
- **Primary scan:** Tablet camera via `html5-qrcode` or `zxing-js`. Scan icon in nav → camera opens → serial captured → lookup resolves → navigates to detail page.
- **Label format:** QR code (primary, tablet camera) + Code 128 barcode (secondary, handheld scanners). Human-readable text alongside both.
- **Scanning is navigation, not a workflow trigger.** Operator scans → lands on existing detail page → decides what to do.
- **Printing:** Playwright renders React label components as PDF (same pipeline as documents). Labels are React components using `qrcode.react` + `JsBarcode`, laid out in a CSS grid on the print page. Shares Tailwind/shadcn styles with the rest of the app — one styling system for everything.
- **Label stock:** 2" × 1" Avery 5160/8160 (30/sheet) for part labels. 4" × 2" Avery 5163 for WO/bin labels.
- **Batch performance:** 30 labels ~0.5-1s, 500 labels ~3-4s. For large batches (500+), QR codes are pre-rendered server-side as base64 PNG data URIs to avoid client-side computation bottleneck.
- **Traveler package:** "Generate Traveler Package" on WO detail produces a single PDF combining the traveler document pages + part label sheets. One print action, everything comes out in order.
- **Thermal printers (ZPL):** Not in scope for initial implementation. Playwright + browser print handles laser/inkjet with label stock. ZPL support for Zebra printers can be added later when a customer requests it — same label data, different render target.

### Label Layout

```
┌─────────────────────────────┐
│ [QR CODE]  AMBAC MFG        │
│            PN: INJ-2500-A   │
│            SN: INJ-2025-0847│
│            WO: WO-2025-0123 │
│            Rev: C            │
│            Date: 2026-03-23  │
│ ████████████████████████████ │  ← Code 128 barcode of serial
└─────────────────────────────┘
```

### Features

| # | Feature | Description | Status |
|---|---------|-------------|--------|
| 8.4.1 | QR code generation | QR codes via `qrcode.react` (client-side) for small batches, Python `qrcode` → base64 PNG (server-side) for 500+ batches. | PLANNED |
| 8.4.2 | Code 128 barcode generation | Code 128 via `JsBarcode` (client-side React component). | PLANNED |
| 8.4.3 | PDF part label endpoint | React label print page rendered by Playwright. Batch via `?ids=1,2,3,...`. 30-up Avery grid layout. | PLANNED |
| 8.4.4 | Print Label buttons | Button on part detail and WO detail pages. Opens PDF in new tab. | PLANNED |
| 8.4.5 | Tablet camera QR scanner | In-browser camera component. Scan icon in nav bar → camera overlay → reads QR → navigates. | PLANNED |
| 8.4.6 | Universal serial lookup | `GET /api/lookup?q={serial}` — resolves part, WO, or lot number to frontend route. | PLANNED |
| 4.2.3a | Keyboard-wedge barcode scan | Scan serial via handheld scanner into any text field (HID input). | DONE |
| 8.4.7 | WO traveler QR/barcode | QR and Code 128 on printed traveler PDF header. | PLANNED |
| 8.4.8 | Material lot labels | Label PDF for material lots with lot number, supplier, expiration, QR + barcode. | PLANNED |

---

## Bucket 2: WO Lifecycle Gaps (~1 week) — Lite/Standard

Close remaining P0 gaps and basic P1 lifecycle features.

| # | Feature | Description | Standards | Status |
|---|---------|-------------|-----------|--------|
| 1.1.7 | WO cloning | Duplicate existing WO with option to modify quantity/dates | — | PLANNED |
| 1.2.4 | Waiting for material | Distinct status when WO cannot proceed due to material shortage | — | PLANNED |
| 1.2.7 | Hold escalation | Auto-escalate holds exceeding configurable duration (e.g., >48h → supervisor notification) | — | PLANNED |
| 1.5.2 | Partial completion / short close | Close WO with fewer parts than ordered (customer accepted partial) | — | PLANNED |
| 1.5.4 | Closure checklist | Configurable checklist before WO close (inspections done, NCRs dispositioned, materials reconciled) | AS9100, ISO 13485 | PLANNED |
| 1.1.6 | WO templates | Save and reuse WO configurations for repeat jobs | — | PLANNED |

### Already Done

| # | Feature | Status |
|---|---------|--------|
| 1.1.1 | Manual WO creation | DONE |
| 1.1.2 | WO from customer order | DONE |
| 1.1.3 | CSV bulk import | DONE |
| 1.1.5 | WO from CAPA | DONE |
| 1.1.8 | API-triggered WO creation | DONE |
| 1.2.1 | Core status set (DRAFT → RELEASED → IN_PROGRESS → COMPLETED → CLOSED) | DONE |
| 1.2.2 | Hold status with reason (6 categories) | DONE |
| 1.2.3 | Cancel with reason | DONE |
| 1.2.5 | Waiting for operator | DONE |
| 1.2.6 | Release authorization | DONE |
| 1.2.10 | Status change audit with e-sig | DONE |
| 1.5.1 | Auto-complete on quantity | DONE |
| 1.5.5 | Final inspection sign-off | PARTIAL |

---

## Bucket 3: WO Splitting & Rework (~2-3 weeks) — Standard

Split WOs for partial shipment, rework routing, and yield tracking.

| # | Feature | Description | Standards | Status |
|---|---------|-------------|-----------|--------|
| 1.3.1 | Simple split (quantity) | Split WO of 100 into 60 and 40, maintaining traceability link | — | PLANNED |
| 1.3.2 | Split at operation | Split mid-process: 30 parts at step 5 go to new WO, 70 continue | — | PLANNED |
| 1.3.3 | Split for rework | Separate failed parts into rework WO with different routing | AS9100 (8.7), IATF 16949 (8.7.1.4) | PLANNED |
| 1.3.5 | Parent-child WO hierarchy | Track original WO → all splits/rework WOs as a tree | AS9100 (traceability) | PLANNED |
| 1.4.3 | Rework loop tracking | Track rework count per part; enforce max rework attempts | IATF 16949 (8.7.1.4), ISO 13485 | PARTIAL |
| 1.4.5 | Scrap rate alerts | Notify supervisor when WO scrap rate exceeds threshold | IATF 16949 (10.2.3) | PLANNED |
| 1.4.8 | Yield tracking | Good parts vs started quantity with yield loss categorization | All | PLANNED |

### Already Done

| # | Feature | Status |
|---|---------|--------|
| 1.4.1 | Scrap disposition from WO with reason codes | DONE |
| 1.4.2 | Rework routing assignment | PARTIAL |
| 1.4.6 | MRB workflow (Use As-Is, Rework, Return, Scrap with approvals) | DONE |

---

## Bucket 4: Material Traceability UI (~2-3 weeks) — Standard/Pro

APIs exist for most of these — needs editor pages and UI. Lot tracking and genealogy are Standard; material reservation and incoming inspection are Pro (compliance-driven).

| # | Feature | Description | Standards | Status |
|---|---------|-------------|-----------|--------|
| 3.1.1 | Production BOM definition | Define materials/components per finished part | AS9100 (8.5.2), IATF 16949, ISO 13485 | API |
| 3.1.2 | BOM explosion per WO | Calculate material requirements from WO quantity × BOM | — | PLANNED |
| 3.1.3 | Multi-level BOM | Sub-assemblies: Assembly A needs Sub-Assy B which needs parts C, D, E | — | API |
| 3.2.1 | Lot tracking editor | Track lots with lot number, supplier, CoC, expiration | AS9100, IATF 16949, ISO 13485 | API |
| 3.2.2 | Material consumption recording UI | Record which lot used on which WO/part | AS9100, IATF 16949, ISO 13485 | API |
| 3.2.4 | Genealogy viewer (forward/reverse) | Given lot X → which finished goods? Given serial Y → which lots? | AS9100, IATF 16949, ISO 13485 | API |
| 3.2.5 | Material availability check | Before WO release, verify materials available | — | PLANNED |
| 3.2.6 | Material reservation | Reserve specific lots for WOs to prevent double-allocation | — | PLANNED |
| 3.2.7 | Material substitution tracking UI | Record approved substitute usage with authorization | AS9100, IATF 16949 | API |
| 3.2.8 | Lot splitting/merging UI | Split lot into sub-lots for different WOs | — | API |
| 3.2.10 | Shelf life / expiration | Track expiration, prevent use of expired lots, alert before expiration | ISO 13485 | PARTIAL |
| 3.2.11 | Incoming material inspection | Inspect received lots before releasing to production | AS9100, IATF 16949 | PLANNED |

### Already Done

| # | Feature | Status |
|---|---------|--------|
| 3.1.4 | BOM versioning (via SecureModel) | DONE |
| 3.2.3 | Serial number tracking | DONE |
| 3.3.1 | Scrap reason codes | DONE |
| 3.3.2 | Scrap quantity per operation | PARTIAL |

---

## Bucket 5: Scheduling — Resource Modeling (~1 week) — Standard

Foundation for the CP-SAT solver. Models exist, need editor pages.

| # | Feature | Description | Status |
|---|---------|-------------|--------|
| 2.1.9 | Calendar/holiday management | Define non-working days | PLANNED |
| — | Operator skill matrix | Which operators can run which machines | PLANNED |
| — | Setup time definitions | Per part type per machine, for family sequencing | PLANNED |
| — | WorkCenter editor page | UI for existing WorkCenter model | API |
| — | Shift editor page | UI for existing Shift model | API |

### Already Done

| # | Feature | Status |
|---|---------|--------|
| 2.1.1 | Due date assignment | DONE |
| 2.1.2 | Priority assignment (Urgent/High/Normal/Low) | DONE |
| 2.1.4 | Shift assignment (ScheduleSlot ↔ Shift) | API |
| 2.1.5 | Work center assignment (ScheduleSlot ↔ WorkCenter) | API |

---

## Bucket 6: Scheduling — CP-SAT Solver Engine (~2-3 weeks) — Premium

OR-Tools CP-SAT constraint-based optimization. Enterprise-grade capability shipped at Premium as a differentiator. No competitor uses CP-SAT; most use heuristics. See OR_TOOLS_INTEGRATION.md for full design.

| # | Feature | Description | Status |
|---|---------|-------------|--------|
| 2.3.6 | CP-SAT job shop model | Operations × machines × time windows | PLANNED |
| 2.3.1 | Finite capacity scheduling | Work center can only process N jobs simultaneously | PLANNED |
| 2.3.2 | Multi-resource constraints | Operation requires machine AND operator AND tooling | PLANNED |
| 2.3.3 | Setup time optimization | Family sequencing to minimize changeover | PLANNED |
| 2.3.8 | WO-to-WO dependencies | Sub-assembly must complete before final assembly | PLANNED |
| 2.2.6 | Backward scheduling | Calculate latest start from due date (solver output) | PLANNED |
| 2.2.7 | Forward scheduling | Calculate completion from release date (solver output) | PLANNED |
| — | Objective function | Minimize lateness × priority + makespan + overtime penalties. Configurable weights. | PLANNED |
| — | Solve timeout / fallback | Best-known solution if solver doesn't converge in time limit | PLANNED |
| — | Re-solve on changes | New WO, machine down, priority change triggers re-solve | PLANNED |

---

## Bucket 7: Scheduling — Gantt Visualization (~2 weeks) — Premium

Interactive Gantt chart for planners and supervisors.

| # | Feature | Description | Status |
|---|---------|-------------|--------|
| 2.2.3 | Machine Gantt | Rows = machines, bars = scheduled operations | PLANNED |
| — | WO Gantt | Rows = work orders, bars = operations across machines | PLANNED |
| — | Color coding | By WO, part type, priority, status | PLANNED |
| — | Zoom | Hour/day/week views | PLANNED |
| — | Tooltips | WO details, operator, setup time, due date | PLANNED |
| 2.2.2 | Overdue/at-risk highlighting | Visual flags on late or at-risk WOs | PARTIAL |
| — | Conflict/overload highlighting | Visual when resources are double-booked | PLANNED |
| — | Current time marker | "We are here" line | PLANNED |

---

## Bucket 8: Scheduling — Interactive Editing (~1-2 weeks) — Premium

Manual overrides on top of solver output.

| # | Feature | Description | Status |
|---|---------|-------------|--------|
| 2.2.4 | Drag-and-drop reschedule | Move operation to different time/machine | PLANNED |
| — | Pin/lock operations | Solver can't move pinned operations | PLANNED |
| 2.1.8 | Hot list / expedite queue | Rush jobs pinned, solver schedules around them | PLANNED |
| — | Re-solve around locks | After manual changes, re-optimize unfrozen operations | PLANNED |
| — | Undo/redo | Revert manual changes | PLANNED |

---

## Bucket 9: Scheduling — Operator Dispatch (~1-2 weeks) — Standard/Pro

Schedule flows down to the shop floor. Dispatch lists and work queues are Standard; shift handoff and "what's next" are Pro.

| # | Feature | Description | Status |
|---|---------|-------------|--------|
| 2.1.7 | Daily dispatch list | Per work center, sorted by schedule. "What to run today." | PLANNED |
| 4.2.4 | Operator work queue UI | "What's assigned to me" (my_workload API exists) | API |
| 2.1.6 | Operator assignment | Skill-based assignment to scheduled operations | PLANNED |
| 4.2.5 | Claim/unclaim work | Operator self-assigns from available queue | PLANNED |
| — | "What's next?" | After completing current op, system suggests next | PLANNED |
| 4.2.6 | Shift handoff notes | Notes for next operator on same WO | PLANNED |

---

## Bucket 10: Scheduling — Capacity & Load Visibility (~1 week) — Standard/Enterprise

Capacity loading is Standard. Bottleneck identification, utilization %, and promise date calculation are Enterprise.

| # | Feature | Description | Status |
|---|---------|-------------|--------|
| 2.2.1 | Capacity loading | Hours scheduled vs available per work center per day/week | PLANNED |
| — | Bottleneck identification | Which work center is the constraint | PLANNED |
| — | Due date risk flags | WOs the solver can't fit before due date | PLANNED |
| — | Utilization % | By machine/work center | PLANNED |
| 2.2.8 | Promise date calculation | "If you order today, deliver by X" based on current load | PLANNED |

---

## Bucket 11: Scheduling — What-If Scenarios (~1-2 weeks) — Enterprise

Test changes before committing.

| # | Feature | Description | Status |
|---|---------|-------------|--------|
| 2.3.4 | Clone schedule into scenario | Copy live schedule for experimentation | PLANNED |
| — | Add/remove WOs in scenario | "What if we accept this rush order?" | PLANNED |
| — | Change machine availability | "What if machine 3 goes down?" | PLANNED |
| — | Compare scenarios side-by-side | Makespan, on-time %, utilization comparison | PLANNED |
| — | Promote scenario to live | Commit the winning scenario | PLANNED |

---

## Bucket 12: Shop Floor Execution Gaps (~1-2 weeks) — Standard/Pro

| # | Feature | Description | Standards | Status |
|---|---------|-------------|-----------|--------|
| 4.1.6 | Operator acknowledgment | Confirm read/understood instructions before starting | 21 CFR Part 11, AS9100 | PLANNED |
| 4.2.9 | Skill/certification verification | Verify operator trained for this operation before allowing start | AS9100, IATF 16949, ISO 13485 | PLANNED |
| 4.3.2 | Labor time recording UI | Clock in/out per operation (TimeEntry model exists) | — | API |
| 4.3.5 | Multi-operator tracking UI | Multiple operators on same WO (TimeEntry model exists) | — | API |
| 4.4.2 | Add step mid-process | Insert additional operation into live WO | — | PLANNED |
| 4.5.6 | Downtime logging UI | DowntimeEvent model exists, needs editor page | — | API |

### Already Done

| # | Feature | Status |
|---|---------|--------|
| 4.1.1 | Step-level work instructions | DONE |
| 4.1.2 | Document attachments per step | DONE |
| 4.1.4 | Revision-controlled instructions | DONE |
| 4.1.5 | Visual work instructions (image/video) | DONE |
| 4.2.1 | Start/stop per operation | DONE |
| 4.2.2 | Operator identification | DONE |
| 4.2.7 | Tablet/mobile optimized interface | DONE |
| 4.3.1 | Operation start/end timestamps | DONE |
| 4.3.3 | Setup vs run time separation (TimeEntry.entry_type) | DONE |
| 4.4.1 | Skip step with authorization | DONE |
| 4.4.4 | Step rollback | DONE |
| 4.4.7 | Quarantine from any step | DONE |
| 4.5.1 | Equipment assignment per operation | DONE |
| 4.5.2 | Calibration status check | DONE |
| 4.5.7 | OEE calculation | PARTIAL |
| 4.1.3 | Digital traveler | PARTIAL |
| 4.3.4 | Planned vs actual time comparison | PARTIAL |
| 4.4.6 | Emergency stop / line stop | PARTIAL |

---

## Bucket 13: Quality Gaps (~2 weeks) — Pro

| # | Feature | Description | Standards | Status |
|---|---------|-------------|-----------|--------|
| 5.1.5 | Last piece inspection | Confirm process didn't drift during run | IATF 16949 | PLANNED |
| 5.1.7 | SPC out-of-control alerts | Notification on Western Electric rule violation | IATF 16949 | PLANNED |
| 5.3.1 | Certificate of Conformance (CoC) | Generate from WO completion data | AS9100, IATF 16949 | PARTIAL |
| 5.3.2 | FAI report (AS9102) | Forms 1, 2, 3 from measurement data | AS9100/AS9102 | PARTIAL |
| 5.3.3 | Device History Record (DHR) | Complete production record for medical devices | ISO 13485, 21 CFR 820 | PLANNED |
| 5.3.5 | Lot traceability report | Forward/reverse traceability document | All traceability standards | API |

### Already Done

| # | Feature | Status |
|---|---------|--------|
| 5.1.1 | Inspection points in routing | DONE |
| 5.1.2 | In-process measurement recording | DONE |
| 5.1.3 | Auto-disposition on fail | DONE |
| 5.1.4 | First piece inspection (FPI) | DONE |
| 5.1.6 | SPC at the operation | DONE |
| 5.1.8 | Sampling plan enforcement | DONE |
| 5.2.1 | NCR auto-creation on inspection fail | DONE |
| 5.2.2 | NCR linkage to WO/step/part | DONE |
| 5.2.3 | Disposition from WO context | DONE |
| 5.2.4 | CAPA linkage from WO | DONE |
| 5.2.5 | Containment actions from WO | DONE |

---

## Bucket 14: Compliance (~1 week) — Pro

| # | Feature | Description | Standards | Status |
|---|---------|-------------|-----------|--------|
| 6.1.4 | Audit log export | Export audit trail for auditor review | All | PARTIAL |
| 6.3.1 | Record retention policy | Configurable retention periods (7yr auto, life+2yr medical) | IATF 16949, ISO 13485, 21 CFR 820 | PLANNED |
| 6.3.3 | Customer property identification | Track customer-supplied material/tooling separately | AS9100, ISO 9001 | PLANNED |

### Already Done

| # | Feature | Status |
|---|---------|--------|
| 6.1.1 | Change logging on all WO fields | DONE |
| 6.1.2 | Status transition history | DONE |
| 6.1.3 | Immutable audit log | DONE |
| 6.2.1 | E-signature with password re-auth and signature capture | DONE |
| 6.2.2 | Signature meaning | DONE |

---

## Bucket 15: Outside Processing (~1-2 weeks) — Pro

Every shop sends work out for plating, heat treat, NDT. Compliance-driven (AS9100 8.4 requires subcontractor controls).

| # | Feature | Description | Standards | Status |
|---|---------|-------------|-----------|--------|
| 9.1.1 | Outside processing step type | Mark routing step as "outside processing" — parts leave the building | AS9100 (8.4), IATF 16949 | PLANNED |
| 9.1.2 | Subcontractor tracking | Which supplier, expected/actual dates | AS9100 (8.4.2) | PLANNED |
| 9.1.3 | Ship-out / receive-back workflow | Track parts leaving and returning; receiving inspection on return | AS9100 (8.4.2) | PLANNED |
| 9.1.4 | Supplier cert verification | Verify NADCAP, AS9100 certs before allowing outside processing | AS9100 (8.4.1) | PLANNED |

---

## Bucket 16: Reporting & Analytics (~2 weeks) — Standard/Pro

| # | Feature | Description | Status |
|---|---------|-------------|--------|
| 7.1.3 | On-time delivery rate | % WOs completed by due date, trending | PLANNED |
| 7.2.1 | Cycle time analysis | Avg/min/max per step, per part type — bottleneck identification | PLANNED |
| 7.2.2 | Throughput trending | Parts per hour/day/week by work center | PLANNED |
| 7.2.4 | Labor efficiency | Actual hours vs standard hours per WO, per operator | PLANNED |
| 7.2.5 | OEE dashboard | Availability × Performance × Quality by machine/work center | PARTIAL |
| 7.4.2 | PDF WO traveler | Print-quality PDF of complete WO traveler | PLANNED |
| 2.3.7 | Schedule vs actual | Compare planned schedule to actual execution | PLANNED |

### Already Done

| # | Feature | Status |
|---|---------|--------|
| 7.1.1 | WO status summary | DONE |
| 7.1.4 | Past-due WO list | API |
| 7.1.5 | Daily production summary | API |
| 7.1.6 | Shop floor big screen display | DONE |
| 7.2.3 | Scrap/rework rate by WO | DONE |
| 7.3.1 | First pass yield by WO | DONE |
| 7.3.2 | Defect Pareto per WO | DONE |
| 7.3.3 | NCR aging from WO | DONE |
| 7.4.1 | Excel export | DONE |
| 7.4.4 | Customer portal WO status | DONE |

---

## Bucket 17: Integrations (~1 week) — Standard/Premium

| # | Feature | Description | Status |
|---|---------|-------------|--------|
| 8.1.2 | Report completions to ERP | Send WO completion with quantities back to ERP | PLANNED |
| 8.1.5 | Webhook on WO events | Fire webhooks on status changes, completions, quality events | PLANNED |

### Already Done

| # | Feature | Status |
|---|---------|--------|
| 8.1.1 | Receive WOs from ERP (CSV, REST API) | DONE |
| 8.2.1 | Order status sync to CRM (HubSpot) | DONE |
| 8.2.2 | Delivery date sync to CRM | DONE |
| 9.3.1 | Tenant isolation | DONE |

---

## UX by Role

### Production Manager

| # | Feature | Status |
|---|---------|--------|
| 10.1.1 | WO overview dashboard | DONE |
| 10.1.2 | Drill-down to WO detail | DONE |
| 10.1.3 | Bulk status changes | PLANNED |
| 10.1.4 | Exception alerts | PARTIAL |
| 10.1.5 | End-of-shift summary | PLANNED |
| 10.1.6 | Capacity vs demand view | PLANNED |

### Shop Floor Operator

| # | Feature | Status |
|---|---------|--------|
| 10.2.1 | Scan-and-go | PARTIAL |
| 10.2.2 | My work queue | PLANNED |
| 10.2.3 | Big button interface | PARTIAL |
| 10.2.4 | Quick quality entry | DONE |
| 10.2.5 | Raise hand / call for help | PLANNED |

### Quality Engineer

| # | Feature | Status |
|---|---------|--------|
| 10.3.1 | Quality events feed from WOs | DONE |
| 10.3.2 | Inspection queue | PARTIAL |
| 10.3.3 | SPC monitoring view | DONE |
| 10.3.4 | Disposition dashboard | DONE |
| 10.3.5 | Traceability lookup | API |

### Planner / Scheduler

| # | Feature | Status |
|---|---------|--------|
| 10.4.1 | Scheduling board (Gantt) | PLANNED |
| 10.4.2 | What's late / what's at risk | PARTIAL |
| 10.4.3 | Load balancing view | PLANNED |

### Customer (Portal)

| # | Feature | Status |
|---|---------|--------|
| 10.5.1 | Order status visibility | DONE |
| 10.5.2 | Expected ship date | DONE |
| 10.5.3 | Quality summary | DONE |
| 10.5.4 | CoC download | PLANNED |
| 10.5.5 | Notification preferences | DONE |

---

## Summary

### By Bucket

| # | Bucket | Tier | Effort | Key Status |
|---|--------|------|--------|------------|
| 1 | Labels & Scanning | Standard | ~1 week | PLANNED |
| 2 | WO Lifecycle Gaps | Lite/Standard | ~1 week | PLANNED |
| 3 | WO Splitting & Rework | Standard | ~2-3 weeks | PLANNED |
| 4 | Material Traceability UI | Standard/Pro | ~2-3 weeks | API exists, needs UI |
| 5 | Scheduling — Resource Modeling | Standard | ~1 week | API exists, needs UI |
| 6 | Scheduling — CP-SAT Solver | Premium | ~2-3 weeks | PLANNED |
| 7 | Scheduling — Gantt | Premium | ~2 weeks | PLANNED |
| 8 | Scheduling — Interactive Editing | Premium | ~1-2 weeks | PLANNED |
| 9 | Scheduling — Operator Dispatch | Standard/Pro | ~1-2 weeks | API partial |
| 10 | Scheduling — Capacity Visibility | Standard/Enterprise | ~1 week | PLANNED |
| 11 | Scheduling — What-If | Enterprise | ~1-2 weeks | PLANNED |
| 12 | Shop Floor Execution Gaps | Standard/Pro | ~1-2 weeks | API exists for most |
| 13 | Quality Gaps | Pro | ~2 weeks | Skeletons exist for CoC/FAI |
| 14 | Compliance | Pro | ~1 week | PARTIAL |
| 15 | Outside Processing | Pro | ~1-2 weeks | PLANNED |
| 16 | Reporting & Analytics | Standard/Pro | ~2 weeks | Data exists, needs aggregation |
| 17 | Integrations | Standard/Premium | ~1 week | Foundations done |
| — | **Total** | — | **~28-35 weeks** | — |

### By Tier
- **Lite:** Bucket 2 (partial) = ~0.5 weeks
- **Standard:** Buckets 1, 2 (partial), 3, 4 (partial), 5, 9 (partial), 10 (partial), 12 (partial), 16 (partial), 17 (partial) = ~12-16 weeks
- **Pro:** Buckets 4 (partial), 9 (partial), 12 (partial), 13, 14, 15, 16 (partial) = ~8-10 weeks
- **Premium:** Buckets 6, 7, 8, 17 (partial) = ~6-8 weeks
- **Enterprise:** Buckets 10 (partial), 11 = ~2-3 weeks

---

## Competitive Positioning

See FEATURE_INVENTORY.csv for full 15-competitor feature parity analysis (300 features × 15 competitors).

### Features nobody else has (all DONE):
- 3D defect visualization with GPU heatmaps
- AI digital coworker with local LLM and per-user RBAC
- SPC baseline versioning with audit trail
- Advanced sampling engine with automatic fallback (6 rule types)
- Handwritten signature capture with password re-authentication
- Order viewer invitations (customer portal)
- Remanufacturing-native process flag

### vs. ProShop (~$500+/month, ~$15M revenue, ~117 employees):
- **Quality:** We're ahead — SPC baselines, 3D viz, AI, smart sampling. ProShop has no SPC.
- **Shop floor:** Comparable — both have paperless work instructions, operator tracking, digital traveler.
- **Scheduling:** ProShop has finite capacity + drag-drop + dispatch (all working). We have models but no solver or Gantt UI yet. Once CP-SAT ships, a generation ahead (constraint optimization vs heuristic scheduling). Currently behind on scheduling.
- **ProShop has:** WO costing, purchasing, quoting, tool crib management, maintenance/CMMS — all ERP territory we don't build. They integrate with QuickBooks for actual accounting.
- **ProShop lacks:** SPC, 3D defect visualization, AI assistant, advanced sampling, CP-SAT scheduling (planned).

### vs. Plex ($500-600K implementation for 75-person shop):
- Same or better quality and shop floor execution at Pro tier
- CP-SAT scheduling (Premium) competitive with Plex's finite scheduling
- Implementation: $20-30K vs $500K+. Live in 6-8 weeks vs 12-18 months.
- Plex has: Full ERP (financials, purchasing, inventory), machine integration (OPC-UA/MTConnect), multi-site — Enterprise territory we don't target

### vs. PlanetTogether APS ($50-150K/year):
- CP-SAT solver is directly competitive — and uses true mathematical optimization vs their heuristic/constraint/GA hybrid
- Plus we have quality, shop floor execution, traceability — they're scheduling-only
- They're an add-on to an existing MES/ERP. We're the whole MES/QMS.
- No competitor in the MES space uses CP-SAT; this is a genuine algorithmic differentiator

### vs. TrakSYS ($2K-$16K/month by tier):
- At their Growth tier ($5K/mo): comparable SPC, we have deeper CAPA and sampling
- At their Premier tier ($11K/mo): they gate traceability and audit trail here; we include at Standard/Pro
- At their Ultimate tier ($16K/mo): they add algorithmic scheduling; our CP-SAT (Premium) would compete
- We're significantly cheaper for equivalent capability

---

## Edge Cases & Gotchas

1. **Quantity changes after release** — Customer changes order quantity mid-production. Handle increase (add parts) and decrease (parts already in progress).
2. **Engineering change mid-WO** — Drawing revs while parts are on the floor. Split WO? Continue with old rev?
3. **Daylight saving time** — Shift scheduling across DST boundary. 8-hour night shift becomes 7 or 9 hours.
4. **Partial shipments** — Customer wants 50 of 100 shipped now. WO stays open. Track shipped vs in-production.
5. **Rush order insertion** — Hot job arrives. Solver re-optimizes. Cascade effect on all other WO due dates.
6. **Multiple units of measure** — WO quantity is "pieces" but material consumed in "feet" or "kg". BOM needs conversion.
7. **Batch vs. individual tracking** — CNC machines parts individually, heat treat processes batches. Same routing handles both.
8. **Concurrent operations** — Steps 3 and 4 in parallel. StepEdge DAG supports this.
9. **Lot-controlled operations** — Heat treat must process entire lot together. Scheduling waits for all parts to reach that step.
10. **Yield-dependent downstream** — 95% expected yield means start 105 parts to get 100 good ones.

---

## Sources

- [IoT Analytics - MES Market 2025-2031](https://iot-analytics.com/mes-vendors-replace-pen-paper-spreadsheets/)
- [Tulip - Core Features of MES](https://tulip.co/blog/core-features-of-mes-manufacturing-execution-systems/)
- [ProShop ERP - MES Module](https://proshoperp.com/product/mes/)
- [Microsoft Dynamics 365 - Work Order Lifecycle States](https://learn.microsoft.com/en-us/dynamics365/supply-chain/asset-management/setup-for-work-orders/work-order-lifecycle-states)
- [Connected Manufacturing - Finite Capacity Scheduling](https://connectedmanufacturing.com/knowledge-topics/finite-capacity-scheduling-explained)
- [PlanetTogether - APS Software](https://www.planettogether.com/products/advanced-planning-scheduling-software)
- [PyJobShop - CP Scheduling in Python](https://arxiv.org/abs/2502.13483)
- [ASQ - Statistical Process Control](https://asq.org/quality-resources/statistical-process-control)
- [AS9100 Store - AS9102 FAI](https://as9100store.com/aerospace-standards-explained/what-is-as9102-first-article-inspection/)
- [MasterControl - 21 CFR Part 11](https://www.mastercontrol.com/glossary-page/21-cfr-part-11/)
