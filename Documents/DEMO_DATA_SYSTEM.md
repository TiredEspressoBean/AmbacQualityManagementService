# Demo Data System Design

## Overview

This document tracks the design and implementation of the demo/dev data system for AmbacTracker. The goal is to support two distinct data loading modes:

1. **Dev Data** - Generated test data for development and automated testing
2. **Demo Data** - Curated, pre-made data specifically designed for product demos and training

## Current State

### Existing Infrastructure
- `populate_test_data` management command - generates randomized test data
- `reset_demo` management command - clears tenant data and repopulates
- `is_demo` flag on Tenant model
- Seeder modules in `Tracker/management/commands/seed/`:
  - `base.py` - BaseSeeder class
  - `manufacturing.py` - Processes, steps, part types, equipment
  - `orders.py` - Orders, work orders, parts distribution
  - `quality.py` - Quality reports, measurements
  - `capa.py` - CAPAs, RCAs, tasks
  - `documents.py` - Document types, sample documents
  - `reman.py` - Cores, harvested components (life tracking)
  - `life_tracking.py` - SPC baselines

### What Works
- Generates realistic-ish data at small/medium/large scales
- Creates process flows, parts at various stages
- Handles FK relationships properly

### What's Missing for Demo
- Curated storylines (not random data)
- Named entities that make sense together
- Specific scenarios that showcase features
- Consistent user accounts with known passwords
- Pre-configured dashboards/views

---

## Design: Two Modes, Two Tenants

**Key Principles:**
- Dev and demo are separate tenants in the same database
- Resetting demo never affects dev (and vice versa)
- No persistence needed - reset wipes and rebuilds from scratch
- Superuser (created separately) can access both tenants

### Tenant Separation

| Tenant | Slug | `is_demo` | Purpose |
|--------|------|-----------|---------|
| Dev tenant | `dev` | `False` | Development, testing |
| Demo tenant | `demo` | `True` | Demos, training |

### User Model

| User Type | Created By | Scope | Purpose |
|-----------|------------|-------|---------|
| Superuser | `createsuperuser` / setup | Global | Dev/admin access to all tenants |
| Dev tenant users | `populate_test_data --mode dev` | Dev tenant only | Testing roles/permissions |
| Demo tenant users | `populate_test_data --mode demo` | Demo tenant only | Demo with known credentials |

### Mode 1: Dev Data (`--mode dev`, default)
**Purpose:** Development, automated testing, load testing

**Approach:** Randomly generated

**Characteristics:**
- Scalable (small/medium/large via `--scale`)
- Random names, IDs, distributions
- Focus on data variety and edge cases
- Good for testing code paths, not for storytelling
- Each run produces different data

**Implementation:** Current seeders (unchanged)

### Mode 2: Demo Data (`--mode demo`)
**Purpose:** Product demos, training, screenshots, documentation

**Approach:** Curated to support stories

**Characteristics:**
- Fixed scenario (no scale option)
- Meaningful names and relationships
- Data arranged to showcase features
- Supports narratives like "this order came in, these parts failed QA, which triggered this CAPA..."
- Demo users with known credentials for live demos
- Same result every time (idempotent)

**Implementation:** New demo seeders with hardcoded/scripted data

### Reset Behavior

```
reset_demo command:
1. Finds tenant by slug (default: DEMO_TENANT_SLUG setting)
2. Verifies tenant.is_demo == True (refuses otherwise)
3. Clears only that tenant's data
4. Repopulates with demo data (--mode demo)
```

Dev data is never touched by reset_demo.

---

## Demo Data Content Plan

### 1. Demo Users (tenant-scoped, recreated on reset)

| Email | Password | Role | Purpose |
|-------|----------|------|---------|
| admin@demo.ambac.com | demo123 | Admin | Full access demo |
| qa@demo.ambac.com | demo123 | QA Inspector | Quality workflow demo |
| operator@demo.ambac.com | demo123 | Operator | Production floor demo |
| manager@demo.ambac.com | demo123 | Manager | Reporting/oversight demo |

**Note:** Superuser (created separately via `createsuperuser`) can also access demo tenant for admin purposes.

## Demo Scenarios - Showcasing "Wow Moments"

Based on product analysis, the key differentiators to showcase are:
1. **3D Visual Quality + Heatmaps** - Spatial defect analysis
2. **AI Digital Coworker** - Natural language queries with RBAC
3. **Remanufacturing Workflows** - DAG-based conditional routing
4. **SPC with Audit Trails** - Frozen baselines, rule violations
5. **Sampling Engine** - Dynamic inspection escalation
6. **Customer Portal** - Self-service order tracking

---

### Story Interconnections

All stories share the same underlying data - they're different views into one coherent scenario:

```
┌─────────────────────────────────────────────────────────────────────┐
│                     MIDWEST FLEET ORDER                              │
│                     (Customer Portal View)                           │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   CORES RECEIVED                                     │
│              (Remanufacturing Journey)                               │
│   Core → Disassembly → Components graded → Route by condition        │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│               PRODUCTION & INSPECTION                                │
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │  Sampling    │───▶│   Quality    │───▶│  3D Heatmap  │          │
│  │  Decision    │    │   Reports    │    │  Defects     │          │
│  └──────────────┘    └──────┬───────┘    └──────┬───────┘          │
│                             │                   │                   │
│                             ▼                   │                   │
│                      ┌──────────────┐           │                   │
│                      │ Measurements │───────────┼──────────┐        │
│                      │   (SPC)      │           │          │        │
│                      └──────────────┘           │          │        │
└─────────────────────────────┬───────────────────┼──────────┼────────┘
                              │                   │          │
                              ▼                   ▼          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        CAPA                                          │
│   Triggered by: SPC drift + Defect pattern on nozzle tip            │
│   5-Whys → Supplier batch issue → Corrective actions                │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      AI COWORKER                                     │
│   Can query any of the above:                                        │
│   - "Show quarantined parts" → Parts from this order                │
│   - "FPY trend" → Data from this production run                     │
│   - "Find nozzle specs" → Documents attached to process             │
└─────────────────────────────────────────────────────────────────────┘
```

**Key Links:**
| From | To | Connection |
|------|-----|------------|
| Customer Portal | Reman Journey | Customer's order contains the cores |
| Reman Journey | Quality | Harvested components become parts that get inspected |
| Quality Reports | 3D Heatmap | Same defects shown spatially |
| Quality Reports | SPC | Measurements recorded during inspection |
| 3D Heatmap | CAPA | Defect pattern triggered investigation |
| SPC Drift | CAPA | Out-of-control signal triggered investigation |
| Sampling | Quality | Determines which parts get full inspection |
| AI Coworker | Everything | Queries all data with RBAC |

---

### Demo Story 1: "The Remanufacturing Journey" (Core → Component → Product)

**Purpose:** Show the complete reman workflow that competitors can't handle

**Setup:**
- 10 cores in various states (received, disassembly, disassembled, scrapped)
- Harvested components with grades (A/B/C/Scrap)
- Components routed based on grade (conditional routing)

**Story to tell:**
> "Here's a core that came in from Midwest Fleet. Watch how the system tracks disassembly - each component gets graded, and the system automatically routes Grade A parts to assembly, Grade B to rework, and scraps the rest. Click on any finished product and trace it back to the original core."

**Features showcased:**
- Core receiving and grading
- Disassembly tracking with genealogy
- Conditional routing (DAG-based decisions)
- Full traceability (core → component → assembly)

**Connects to:**
- → Story 2: These parts go through quality inspection where defects are marked on 3D model
- → Story 7: Customer (Midwest Fleet) can see this order's progress in their portal

---

### Demo Story 2: "Catching Quality Issues with 3D Visualization"

**Purpose:** Show the 3D defect heatmap - the visual "wow"

**Setup:**
- Part type with 3D model uploaded
- 50+ quality reports with defect annotations on the 3D model
- Visible clustering of defects on nozzle tip area

**Story to tell:**
> "Instead of reading through text reports, inspectors click directly on the 3D model to mark defects. Now look at this heatmap - see how defects cluster on the nozzle tip? That pattern would be invisible in a traditional QMS. This is what triggered our CAPA investigation."

**Features showcased:**
- 3D model viewer with defect annotation
- GPU-accelerated heatmap rendering
- Pattern recognition for systematic issues
- Link to CAPA from quality patterns

**Connects to:**
- ← Story 1: These are parts from the Midwest Fleet cores
- → Story 5: This nozzle defect pattern is what triggered CAPA-2024-003
- → Story 6: Sampling rules determined which of these parts got inspected

---

### Demo Story 3: "Ask the AI Anything"

**Purpose:** Show the AI Digital Coworker with natural language

**Setup:**
- Enough data to query meaningfully
- Documents indexed for semantic search

**Story to tell:**
> "Watch this - I'll just ask: 'Which parts are quarantined and why?' The AI queries our database and shows me exactly what I need. Now: 'What's our first-pass yield trend for injectors?' And here's the key - this AI runs completely on-premises. No data leaves your facility. ITAR compliant out of the box."

**Demo queries to pre-test:**
- "Which parts are quarantined?" → Returns parts from Story 2
- "Show me FPY trend for fuel injectors" → Uses data from Story 4
- "What triggered CAPA-2024-003?" → Links to Story 5
- "Find documents about nozzle inspection" → Finds work instructions

**Features showcased:**
- Natural language to SQL
- Per-user RBAC (AI respects permissions)
- Local LLM (Ollama) - no cloud dependency
- Semantic + keyword document search

**Connects to:**
- ↔ All stories: AI queries return data from the same scenario
- Standalone demo: Showcases AI as a distinct capability (local LLM, RBAC, ITAR compliance)

---

### Demo Story 4: "SPC Catching Drift Before Failures"

**Purpose:** Show proactive quality management with SPC

**Setup:**
- Measurement definition with SPC enabled
- 60+ measurement results over 30 days
- Frozen baseline with control limits
- Recent trend showing drift (Rule 2 violation flagged)
- One out-of-control point

**Story to tell:**
> "Here's our flow rate control chart. See this baseline? We froze these limits when the process was stable - full audit trail of who approved it and when. Now look at the last week - the system flagged a Rule 2 violation: two of three points beyond 2-sigma. That's a signal to investigate before we start producing scrap."

**Features showcased:**
- X̄-R / X̄-S / I-MR charts
- Frozen baselines with audit trail
- Western Electric rule violations
- Proactive vs reactive quality

**Connects to:**
- ← Story 1: Measurements taken on parts from Midwest Fleet order
- → Story 5: This SPC drift contributed to opening CAPA-2024-003
- ← Story 2: Same inspection step where defects were found

---

### Demo Story 5: "From Failure to Fix" (CAPA Workflow)

**Purpose:** Show complete investigation and corrective action cycle

**Setup:**
- CAPA in IN_PROGRESS status
- 5-Whys analysis completed
- Fishbone diagram with causes
- Tasks assigned to different users
- Linked to quality reports that triggered it

**Story to tell:**
> "When we saw that nozzle defect pattern, the system helped us open a CAPA. Here's our 5-Whys - we traced it to a supplier batch issue. See the tasks? Sarah contacted the supplier, Mike is updating the inspection procedure. Full traceability from defect to root cause to corrective action."

**Features showcased:**
- CAPA workflow (Open → RCA → Tasks → Verify → Close)
- 5-Whys analysis
- Fishbone diagrams
- Task assignment and tracking
- Link between quality data and investigations

**Connects to:**
- ← Story 2: CAPA triggered by defect pattern visible in 3D heatmap
- ← Story 4: SPC drift was additional evidence for investigation
- → Story 6: One corrective action is to tighten sampling rules

---

### Demo Story 6: "Smart Sampling Saves Money"

**Purpose:** Show dynamic sampling that adjusts to quality levels

**Setup:**
- Sampling ruleset with normal (10%) and tightened (100%) levels
- Audit log showing escalation event
- Parts with sampling decisions logged

**Story to tell:**
> "We don't inspect every part - that's expensive. But watch what happens when defect rate spikes: the system automatically escalates to 100% inspection. When quality stabilizes, it steps back down. Every decision is logged and auditable. This alone can cut inspection costs 30-40%."

**Features showcased:**
- Dynamic sampling rules
- Automatic escalation/de-escalation
- Deterministic, auditable decisions
- Sampling audit log

**Connects to:**
- ← Story 2: Sampling decides which parts from this batch get inspected
- ← Story 5: CAPA corrective action triggered tightened sampling
- → Story 4: More inspections = more SPC data points

---

### Demo Story 7: "Customer Self-Service Portal"

**Purpose:** Show customer portal reducing support burden

**Setup:**
- Customer user account with portal access
- Order visible in portal with status
- Notification preferences configured

**Story to tell:**
> "Your customers don't need to call asking 'where's my order?' They log into the portal and see real-time status. They configure their own notifications - daily summary, alerts on delays. This cuts support calls dramatically."

**Features showcased:**
- Customer portal with order tracking
- Configurable notifications
- RBAC (customer only sees their data)

**Connects to:**
- ← Story 1: This is Midwest Fleet's view of their order
- Demonstrates RBAC: Customer sees only their order, not other customers' data
- Can show: "16 of 24 injectors complete, 2 in QA hold" - reflects actual part states

---

## Data Model Descriptions

What each entity represents in the demo and how it supports the stories.

### Tenant
The organization running the MES/QMS. In demo, this is "Ambac Diesel Services" - a diesel fuel injector remanufacturer.

### Companies
External organizations that interact with the tenant. Two types:
- **Customers:** Send cores for remanufacturing, receive finished products (Midwest Fleet, Great Lakes Diesel, Northern Trucking)
- **Suppliers:** Provide parts/materials, may be involved in CAPA investigations (Delphi)

### Users
People who use the system. Each has a role that determines what they can see/do:
- **Admin:** Full system access, configuration
- **QA Inspector:** Quality reports, inspections, disposition decisions
- **Operator:** Production floor work, step completion
- **Production Manager:** Oversight, CAPA ownership, approvals
- **Customer Portal:** External customer viewing their orders

### Part Types
Categories of products being manufactured. In reman, these include:
- **Finished goods:** Common Rail Injector, HEUI Injector, Unit Injector
- **Components:** Nozzle, Plunger, Solenoid Valve, Spring Set, Injector Body

### Processes
Workflows that parts follow. A directed graph of steps with decision points for conditional routing (pass/fail, grade-based). Main process: "Common Rail Injector Remanufacturing"

### Steps
Individual operations within a process. Types:
- **Production:** Work being done (Disassembly, Cleaning, Assembly)
- **Inspection:** Quality checks with pass/fail outcomes (Nozzle Inspection, Flow Testing, Final Test)
- **Decision Points:** Routing based on results (Grade A → Assembly, Grade B → Rework, Grade C → Scrap)

### Orders
Customer requests for work. Contains:
- Customer reference (PO number)
- Quantity and due date
- Status progression: Received → In Progress → Completed → Shipped

### Work Orders
Internal grouping of work. Links orders to the shop floor. May contain multiple parts being processed together.

### Parts
Individual units being tracked through the workflow. Each part:
- Belongs to an order
- Has a current step in the process
- Has a status (in progress, completed, quarantined, scrapped)
- Has full history of step executions

### Cores (Reman)
Used units received for remanufacturing. Source of harvested components:
- Received from customer or purchased
- Graded on arrival (A/B/C/Scrap)
- Disassembled into components
- Tracked for core credit/exchange

### Harvested Components (Reman)
Parts recovered during disassembly:
- Linked to source core (traceability)
- Graded (A = use as-is, B = rework, C = scrap)
- Accepted components enter inventory or production

### Quality Reports
Record of inspection results:
- Pass/Fail outcome
- Measurements taken
- Defects found (linked to 3D annotations)
- Inspector and equipment used

### Measurement Definitions
Specifications for quantitative inspections:
- Nominal value, tolerances (USL/LSL)
- SPC settings (enabled, control limits)
- Linked to specific steps

### Measurement Results
Actual values recorded during inspection:
- Linked to part, step, definition
- Used for SPC charting
- Triggers out-of-control alerts

### SPC Baselines
Frozen control limits for stable processes:
- Mean, standard deviation, UCL/LCL
- Frozen by whom/when (audit trail)
- Compared against current measurements

### CAPA
Corrective and Preventive Action records:
- Triggered by quality issues or patterns
- Contains investigation (5-Whys, Fishbone)
- Tasks assigned to team members
- Verification before closure

**Model Fields (for seeder implementation):**
```
CAPA:
  - capa_number: str (e.g., "CAPA-2024-003")
  - problem_statement: TextField (NOT "title")
  - status: enum (OPEN, RCA_PENDING, IN_PROGRESS, VERIFICATION, CLOSED)
  - capa_type: enum (CORRECTIVE, PREVENTIVE)
  - severity: enum (MINOR, MAJOR, CRITICAL) (NOT "priority")
  - initiated_by: FK(User) (NOT "opened_by")
  - initiated_date: DateField (auto_now_add) (NOT "opened_date")
  - assigned_to: FK(User)
  - due_date: DateField (nullable)
  - immediate_action: TextField (nullable) - containment action
  - approval_required: bool (auto-set for CRITICAL/MAJOR)
  - approval_status: enum (NOT_REQUIRED, PENDING, APPROVED, REJECTED)
  - quality_reports: M2M(QualityReports) - DIRECT LINK to triggering reports
  - part: FK(Parts, nullable) - representative part
  - step: FK(Steps, nullable) - step where issue occurred
  - work_order: FK(WorkOrder, nullable)

RcaRecord (child of CAPA - separate model for root cause analysis):
  - capa: FK(CAPA)
  - rca_method: enum (FIVE_WHYS, FISHBONE, PARETO, FAULT_TREE)
  - problem_description: TextField
  - root_cause_summary: TextField (nullable)
  - conducted_by: FK(User)
  - conducted_date: DateField
  - rca_review_status: enum (NOT_REQUIRED, PENDING, APPROVED, REJECTED)
  - root_cause_verification_status: enum (UNVERIFIED, VERIFIED, FAILED)
  - quality_reports: M2M(QualityReports) - reports analyzed

FiveWhys (child of RcaRecord, NOT CAPA directly):
  - rca_record: OneToOne(RcaRecord)
  - why_1_question: TextField (nullable)
  - why_1_answer: TextField (nullable)
  - why_2_question: TextField (nullable)
  - why_2_answer: TextField (nullable)
  - why_3_question: TextField (nullable)
  - why_3_answer: TextField (nullable)
  - why_4_question: TextField (nullable)
  - why_4_answer: TextField (nullable)
  - why_5_question: TextField (nullable)
  - why_5_answer: TextField (nullable)
  - identified_root_cause: TextField (nullable)

CapaTasks (child of CAPA):
  - capa: FK(CAPA)
  - title: str
  - assignee: FK(User) (primary owner, for backwards compatibility)
  - status: enum (PENDING, IN_PROGRESS, COMPLETE)
  - due_date: DateField
  - completion_mode: enum (SINGLE_OWNER, ANY_ASSIGNEE, ALL_ASSIGNEES)
    - SINGLE_OWNER: Only the primary assignee works on this task (default)
    - ANY_ASSIGNEE: Task completes when ANY one assignee finishes
    - ALL_ASSIGNEES: Task completes only when ALL assignees finish

CapaTaskAssignee (child of CapaTasks):
  - task: FK(CapaTasks)
  - user: FK(User)
  - status: enum (NOT_STARTED, IN_PROGRESS, COMPLETED)
  - completed_at: DateTimeField (nullable)
  - completion_notes: TextField (nullable)
```

**Relationships:**
- CAPA.quality_reports is a ManyToMany field - seeder must call `capa.quality_reports.add(qr1, qr2, ...)`
- FiveWhys is attached to RcaRecord, not CAPA: `CAPA → RcaRecord → FiveWhys`

### Quarantine Dispositions
Decisions about non-conforming parts:
- Part held pending decision
- Options: Use As-Is, Rework, Scrap, Return to Supplier
- Requires approval

**Model Fields (for seeder implementation):**
```
QuarantineDisposition:
  - disposition_number: str (auto-generated, e.g., "QD-2024-0001")
  - current_state: enum (OPEN, IN_PROGRESS, CLOSED) (NOT "status" for approval)
  - disposition_type: enum (REWORK, REPAIR, SCRAP, USE_AS_IS, RETURN_TO_SUPPLIER)
  - severity: enum (CRITICAL, MAJOR, MINOR)

  # Assignment
  - assigned_to: FK(User, nullable)
  - description: TextField
  - resolution_notes: TextField

  # Containment
  - containment_action: TextField - immediate action taken
  - containment_completed_at: DateTimeField (nullable)
  - containment_completed_by: FK(User, nullable)

  # Customer approval (simple tracking)
  - requires_customer_approval: bool (default False)
  - customer_approval_received: bool (default False)
  - customer_approval_reference: str
  - customer_approval_date: DateField (nullable)

  # Scrap verification
  - scrap_verified: bool (default False)
  - scrap_verification_method: str
  - scrap_verified_by: FK(User, nullable)

  # Note: For internal approval workflow, create separate ApprovalRequest
  # linked to this disposition via GenericForeignKey
```

**Approval Workflow Note:** QuarantineDisposition does NOT have a built-in approval status field. Internal approvals (e.g., MRB approval for USE_AS_IS) are handled by creating an ApprovalRequest with `content_object` pointing to the QuarantineDisposition. The disposition's `current_state` tracks workflow state (OPEN → IN_PROGRESS → CLOSED), not approval state.

### Sampling Rules
Logic for determining which parts get inspected:
- Normal/Tightened/Reduced states
- Automatic escalation on failures
- Audit log of state changes

### Equipment
Machines and tools used in production:
- Linked to equipment type
- Calibration tracking (due dates, records)
- Usage logged per step execution

### Calibration Records
History of equipment calibration:
- Performed by, date, result
- Next due date
- Supports compliance requirements

### Training Types & Records
Certifications required for operations:
- Which training is required for which steps
- Employee certification history
- Expiration tracking

### Documents
Files attached to various entities:
- Work instructions (attached to steps)
- Calibration certificates (attached to equipment)
- Customer POs (attached to orders)
- Investigation reports (attached to CAPAs)

### Approval Templates & Requests
Workflow for sign-offs:
- Who needs to approve what
- Pending/approved/rejected status
- Electronic signatures

---

## Demo Data Values

### Tenant

| Field | Value |
|-------|-------|
| Name | Ambac Diesel Services |
| Slug | demo |
| is_demo | True |

---

### Companies (Customers)

| Name | Type | Contact | Purpose |
|------|------|---------|---------|
| Midwest Fleet Services | Customer | orders@midwestfleet.com | Main demo order |
| Great Lakes Diesel Supply | Customer | purchasing@greatlakesdiesel.com | Completed order |
| Northern Trucking Co | Customer | fleet@northerntrucking.com | New order |
| Delphi Fuel Systems | Supplier | quality@delphi.com | Supplier for CAPA story |

---

### Users

**Internal Users (Ambac employees):**

| Email | Password | Name | Role | Purpose |
|-------|----------|------|------|---------|
| admin@demo.ambac.com | demo123 | Alex Demo | Tenant Admin | Full access, user management, configuration |
| maria.qa@demo.ambac.com | demo123 | Maria Santos | QA Manager | CAPA ownership, disposition approvals, SPC oversight |
| sarah.qa@demo.ambac.com | demo123 | Sarah Chen | QA Inspector | Inspections, quality reports, measurements |
| jennifer.mgr@demo.ambac.com | demo123 | Jennifer Walsh | Production Manager | Production oversight, scheduling, approvals |
| mike.ops@demo.ambac.com | demo123 | Mike Rodriguez | Operator | Step completion, measurements, work queue |
| dave.wilson@demo.ambac.com | demo123 | Dave Wilson | Operator | **Expired training demo** - blocked from Flow Testing |
| lisa.docs@demo.ambac.com | demo123 | Lisa Park | Document Controller | Document management, revisions, approvals |

**Customer Portal Users:**

| Email | Password | Name | Company | Purpose |
|-------|----------|------|---------|---------|
| tom.bradley@midwestfleet.com | demo123 | Tom Bradley | Midwest Fleet Services | Portal demo (Story 7) |

---

### User Persona Demo Experiences

Each user type should have a tailored demo experience with data "in their queue."

#### Mike Rodriguez (Operator)
**Role:** Production_Operator
**Primary View:** Work queue, step completion

| Demo Need | Data Required | Status |
|-----------|---------------|--------|
| Parts waiting at his steps | INJ-0042-020 at Assembly, INJ-0042-022 at Cleaning | ✓ Have |
| Equipment to select | Flow Test Stand #1 or #2, Torque Wrench | ✓ Have |
| Measurements to record | Torque values at Assembly | ✓ Have |
| Work instructions | WI-1001 Disassembly, WI-1003 Flow Test | ✓ Have |
| Blocked indicator | Show "Waiting for QA" on quarantined part | Need to verify |

**Demo script:** Log in as Mike → See work queue → Select a part → Complete step with measurement → Show next part auto-appears

#### Sarah Chen (QA Inspector)
**Role:** QA_Inspector
**Primary View:** Inspection queue, SPC, quality reports

| Demo Need | Data Required | Status |
|-----------|---------------|--------|
| Parts at inspection steps | INJ-0042-018 at Final Test, INJ-0042-021 at Flow Testing | ✓ Have |
| Quarantined parts | INJ-0042-017, INJ-0042-019 awaiting disposition | ✓ Have |
| SPC violation alert | Flow rate Rule 2 violation | ✓ Have |
| CAPA tasks assigned | "Update incoming inspection procedure" | ✓ Have |
| Pending approval | APR-2024-0015 (CAPA closure) | ✓ Have |
| Sampling decision | Tightened sampling active | ✓ Have |

**Demo script:** Log in as Sarah → See SPC alert → Review quarantined part → Approve disposition → Check CAPA task → Approve pending approval request

#### Maria Santos (QA Manager)
**Role:** QA_Manager
**Primary View:** Quality dashboard, CAPAs, disposition approvals, SPC oversight

| Demo Need | Data Required | Status |
|-----------|---------------|--------|
| CAPA ownership | CAPA-2024-003 (closed), CAPA-2024-004 (open) | ✓ Have |
| Pending disposition approvals | QD-2024-0003 awaiting MRB decision | ✓ Have |
| SPC oversight | Frozen baselines, out-of-control signals | ✓ Have |
| Sampling rule management | Active tightened sampling for nozzles | ✓ Have |
| Document approvals pending | WI-1002 Nozzle Inspection revision | ✓ Have |
| Quality metrics dashboard | FPY trends, defect Pareto | Need to verify |

**Demo script:** Log in as Maria → Review quality dashboard → Check CAPA status → Approve disposition → Review SPC violation → Approve document revision

#### Lisa Park (Document Controller)
**Role:** Document_Controller
**Primary View:** Document library, pending approvals, revision history

| Demo Need | Data Required | Status |
|-----------|---------------|--------|
| Documents to manage | WI-1001, WI-1002, WI-1003 work instructions | ✓ Have |
| Pending revision | WI-1002 updated per CAPA | ✓ Have |
| Approval workflow | Document release requiring sign-off | ✓ Have |
| Version history | WI-1002 showing Rev 2.0 → 2.1 | ✓ Have |
| Document types | SOP, WI, POL, FRM configured | ✓ Have |
| Controlled distribution | Track who has current revision | Need to verify |

**Demo script:** Log in as Lisa → View document library → Check pending approvals → Review revision history → Initiate approval workflow → Show controlled distribution

#### Jennifer Walsh (Production Manager)
**Role:** Production_Manager
**Primary View:** Dashboard, orders, CAPAs, approvals

| Demo Need | Data Required | Status |
|-----------|---------------|--------|
| Order overview | 3 orders in different states | ✓ Have |
| Work order status | WO-0042-A in progress, progress % | ✓ Have |
| CAPA she owns | CAPA-2024-003 | ✓ Have |
| Pending approval | APR-2024-0015 (needs her approval too) | ✓ Have |
| Equipment calibration | Torque Wrench overdue, Flow Stand #2 due soon | ✓ Have |
| Defect trends | Quality analytics dashboard data | Need to verify |
| Team workload | Parts per operator | Need to add |

**Demo script:** Log in as Jennifer → Dashboard overview → Check order progress → Review CAPA status → See calibration alert → Approve CAPA closure

#### Alex Demo (Admin)
**Role:** Admin / Tenant Admin
**Primary View:** Everything + configuration

| Demo Need | Data Required | Status |
|-----------|---------------|--------|
| Full system access | All features visible | ✓ Have |
| User management | 4 internal users + 1 portal user | ✓ Have |
| Process editor | Reman and New Mfg processes | ✓ Have |
| Tenant settings | Branding, notifications | ✓ Have |
| Permission demonstration | Show different role capabilities | Need TenantGroups |

**Demo script:** Log in as Admin → Show settings → Edit a process → Manage users → Demonstrate what other roles can/can't see

#### Tom Bradley (Customer Portal)
**Role:** Customer
**Primary View:** Their orders only

| Demo Need | Data Required | Status |
|-----------|---------------|--------|
| Their order visible | ORD-2024-0042 (Midwest Fleet) | ✓ Have |
| Other orders NOT visible | Great Lakes, Northern hidden | Need to verify RBAC |
| Order progress | 16 of 24 complete, 2 in QA hold | ✓ Have |
| Notification preferences | Configured for demo | ✓ Have |
| ETA impact | Quarantine affects due date? | Consider adding |

**Demo script:** Log in as Tom → See only Midwest Fleet order → View real-time progress → Check notification settings → Show RBAC (can't see other customers)

---

### TenantGroup Assignments

Map users to TenantGroups for RBAC demonstration:

| User | TenantGroups | Key Permissions |
|------|--------------|-----------------|
| Alex Demo | Tenant Admin | Full access, user management, configuration |
| Maria Santos | QA Manager | CAPA ownership, disposition approvals, SPC management |
| Sarah Chen | QA Inspector | Quality reports, inspections, measurements |
| Jennifer Walsh | Production Manager | Production oversight, scheduling, approvals |
| Mike Rodriguez | Operator | Step completion, measurements, work queue |
| Dave Wilson | Operator | Step completion (blocked by expired training) |
| Lisa Park | Document Controller | Document management, revisions, approvals |
| Tom Bradley | Customer | View own orders only, notification prefs |

---

### Notification Preferences

**Tom Bradley (Customer Portal):**

| Notification Type | Enabled | Frequency | Purpose in Demo |
|-------------------|---------|-----------|-----------------|
| Order Status Changes | Yes | Immediate | Shows real-time alerts |
| Daily Summary | Yes | Daily @ 8am | Shows digest option |
| Shipment Notifications | Yes | Immediate | Ready for pickup/shipped |
| Delay Alerts | Yes | Immediate | Part quarantined affects ETA |

**Sarah Chen (QA Inspector):**

| Notification Type | Enabled | Frequency | Purpose in Demo |
|-------------------|---------|-----------|-----------------|
| Parts Ready for Inspection | Yes | Immediate | Work queue |
| SPC Violations | Yes | Immediate | Rule 2 alert |
| CAPA Task Assigned | Yes | Immediate | Task notifications |
| Calibration Due Soon | Yes | Daily | Equipment alerts |

**Mike Rodriguez (Operator):**

| Notification Type | Enabled | Frequency | Purpose in Demo |
|-------------------|---------|-----------|-----------------|
| Parts in My Queue | Yes | Immediate | New work available |
| Step Blocked | Yes | Immediate | Part can't proceed (QA hold, FPI wait) |
| Work Order Priority Change | Yes | Immediate | Urgent work bumped up |
| Equipment Offline | Yes | Immediate | Equipment unavailable |

**Jennifer Walsh (Production Manager):**

| Notification Type | Enabled | Frequency | Purpose in Demo |
|-------------------|---------|-----------|-----------------|
| Daily Production Summary | Yes | Daily @ 6am | Overview before shift |
| Order Due Soon | Yes | Daily | Orders due within 3 days |
| Approval Required | Yes | Immediate | Pending her approval |
| CAPA Status Change | Yes | Immediate | CAPAs she owns |
| Calibration Overdue | Yes | Immediate | Equipment out of compliance |
| Throughput Alert | Yes | Immediate | Production below target |

---

### Process & Steps

**Process: Common Rail Injector Remanufacturing**

#### Step Definitions

| Order | Name | step_type | is_decision_point | decision_type | is_terminal | terminal_status | max_visits |
|-------|------|-----------|-------------------|---------------|-------------|-----------------|------------|
| 1 | Core Receiving | start | Yes | qa_result | No | - | - |
| 2 | Disassembly | task | No | - | No | - | - |
| 3 | Component Grading | decision | Yes | qa_result | No | - | - |
| 4 | Cleaning | task | No | - | No | - | - |
| 5 | Nozzle Inspection | decision | Yes | qa_result | No | - | 2 |
| 6 | Flow Testing | decision | Yes | measurement | No | - | 2 |
| 7 | Rework | rework | No | - | No | - | - |
| 8 | Assembly | task | No | - | No | - | - |
| 9 | Final Test | decision | Yes | qa_result | No | - | 2 |
| 10 | Packaging | task | No | - | No | - | - |
| 11 | Complete | terminal | No | - | Yes | shipped | - |
| 12 | Scrap | terminal | No | - | Yes | scrapped | - |

#### ProcessStep Records (entry/exit markers)

| Step | is_entry_point | is_exit_point | auto_advance |
|------|----------------|---------------|--------------|
| Core Receiving | **Yes** | No | No |
| Disassembly | No | No | Yes |
| Component Grading | No | No | No |
| Cleaning | No | No | Yes |
| Nozzle Inspection | No | No | No |
| Flow Testing | No | No | No |
| Rework | No | No | Yes |
| Assembly | No | No | Yes |
| Final Test | No | No | No |
| Packaging | No | No | Yes |
| Complete | No | **Yes** | - |
| Scrap | No | **Yes** | - |

#### StepEdge Records (DAG routing)

**Step Decision Type & Condition Evaluation:**

Steps have a `decision_type` field that determines how routing decisions are made:

| decision_type | How It Works | Example |
|---------------|--------------|---------|
| `qa_result` | Checks latest QualityReport.status for part at step. PASS → DEFAULT edge, else ALTERNATE | Nozzle Inspection, Final Test |
| `measurement` | Evaluates StepEdge.condition_measurement against condition_operator/value | Flow Testing: `flow_rate >= 105 AND flow_rate <= 135` |
| `manual` | Operator must explicitly select DEFAULT or ALTERNATE | Component Grading (grade selection) |

**StepEdge Model (for seeder implementation):**
```
StepEdge:
  - process: FK(Processes)
  - from_step: FK(Steps)
  - to_step: FK(Steps)
  - edge_type: enum (DEFAULT, ALTERNATE, ESCALATION)

  # Measurement-based routing (optional)
  - condition_measurement: FK(MeasurementDefinition, nullable)
  - condition_operator: enum ('gte', 'lte', 'eq')
  - condition_value: Decimal (nullable)
```

**Example: Flow Testing → Assembly edge (measurement-based):**
```python
StepEdge.objects.create(
    process=reman_process,
    from_step=flow_testing,
    to_step=assembly,
    edge_type='DEFAULT',
    condition_measurement=flow_rate_def,  # MeasurementDefinition for "Flow Rate @ 1000 bar"
    condition_operator='gte',
    condition_value=105.0  # Lower spec limit
)
# A second edge with condition_operator='lte', condition_value=135.0 handles upper limit
# OR the measurement definition itself has USL/LSL and is_within_spec is calculated
```

**Max Visits Enforcement:**
- `max_visits` is defined on ProcessStep (step within a process context)
- StepExecution.visit_number tracks current visit count
- When `visit_number >= max_visits` and decision would route to rework, ESCALATION edge is taken instead

```
                                    ┌─────────────┐
                                    │   SCRAP     │ (terminal)
                                    └─────────────┘
                                          ▲
                     escalation ──────────┼──────────────────────┐
                                          │                      │
┌──────────────┐    ┌──────────────┐    ┌─┴────────────┐    ┌────┴───────┐
│Core Receiving│───▶│ Disassembly  │───▶│Comp. Grading │    │  Rework    │
└──────────────┘    └──────────────┘    └──────────────┘    └────────────┘
       │                                       │                  ▲  │
       │ (scrap)                    (A/B/C)    │                  │  │
       ▼                                       ▼                  │  │
   [SCRAP]                              ┌──────────────┐          │  │
                                        │   Cleaning   │          │  │
                                        └──────────────┘          │  │
                                               │                  │  │
                                               ▼                  │  │
                                        ┌──────────────┐          │  │
                                        │Nozzle Inspec │──(fail)──┘  │
                                        └──────────────┘             │
                                               │ (pass)              │
                                               ▼                     │
                                        ┌──────────────┐             │
                                        │ Flow Testing │──(fail)─────┘
                                        └──────────────┘
                                               │ (pass)
                                               ▼
                                        ┌──────────────┐
                                        │   Assembly   │
                                        └──────────────┘
                                               │
                                               ▼
                                        ┌──────────────┐
                                        │  Final Test  │──(fail)──▶ [REWORK]
                                        └──────────────┘
                                               │ (pass)
                                               ▼
                                        ┌──────────────┐
                                        │  Packaging   │
                                        └──────────────┘
                                               │
                                               ▼
                                        ┌──────────────┐
                                        │   COMPLETE   │ (terminal)
                                        └──────────────┘
```

| from_step | to_step | edge_type | condition | Notes |
|-----------|---------|-----------|-----------|-------|
| Core Receiving | Disassembly | DEFAULT | Grade A/B/C | Pass - proceed |
| Core Receiving | Scrap | ALTERNATE | Grade = Scrap | Unrepairable core |
| Disassembly | Component Grading | DEFAULT | - | Always |
| Component Grading | Cleaning | DEFAULT | Grade A/B | Good/acceptable components |
| Component Grading | Cleaning | DEFAULT | Grade C | Marginal but usable (flagged for extra attention) |
| Component Grading | Scrap | ALTERNATE | Grade = Scrap | Damaged beyond repair |

**Note on Component Grades:** All usable components (A/B/C) proceed to Cleaning. Grade B/C components are flagged in inventory as "rework queue" meaning they may need extra cleaning or refinishing before use - this is handled within the Cleaning step, not as a separate routing branch. Only Scrap-grade components are discarded.
| Cleaning | Nozzle Inspection | DEFAULT | - | Always |
| Nozzle Inspection | Flow Testing | DEFAULT | Pass | QA pass |
| Nozzle Inspection | Rework | ALTERNATE | Fail | QA fail, rework possible |
| Nozzle Inspection | Scrap | ESCALATION | max_visits exceeded | 2nd failure → scrap |
| Flow Testing | Assembly | DEFAULT | measurement in spec | Flow rate 105-135 mL/min |
| Flow Testing | Rework | ALTERNATE | measurement OOS | Fail, rework possible |
| Flow Testing | Scrap | ESCALATION | max_visits exceeded | 2nd failure → scrap |
| Rework | Nozzle Inspection | DEFAULT | - | Return to inspection |
| Assembly | Final Test | DEFAULT | - | Always |
| Final Test | Packaging | DEFAULT | Pass | QA pass |
| Final Test | Rework | ALTERNATE | Fail | QA fail, rework possible |
| Final Test | Scrap | ESCALATION | max_visits exceeded | 2nd failure → scrap |
| Packaging | Complete | DEFAULT | - | Always |

**Rework Loop Behavior:**
- Parts failing Nozzle Inspection, Flow Testing, or Final Test route to Rework
- After Rework, parts return to Nozzle Inspection (re-enter QA sequence)
- `max_visits=2` on inspection steps means: 1st fail → rework, 2nd fail → scrap
- Escalation edges handle the max_visits exceeded case

---

### Process 2: New Injector Assembly

For new-build injectors (not remanufactured). Simpler flow - no core receiving or disassembly.

#### Step Definitions

| Order | Name | step_type | is_decision_point | decision_type | is_terminal | max_visits |
|-------|------|-----------|-------------------|---------------|-------------|------------|
| 1 | Incoming Inspection | start | Yes | qa_result | No | - |
| 2 | Sub-Assembly | task | No | - | No | - |
| 3 | Nozzle Inspection | decision | Yes | qa_result | No | 2 |
| 4 | Flow Testing | decision | Yes | measurement | No | 2 |
| 5 | Rework | rework | No | - | No | - |
| 6 | Final Assembly | task | No | - | No | - |
| 7 | Final Test | decision | Yes | qa_result | No | 2 |
| 8 | Packaging | task | No | - | No | - |
| 9 | Complete | terminal | No | - | Yes | - |
| 10 | Scrap | terminal | No | - | Yes | - |

#### StepEdge Records (DAG routing)

```
┌────────────────────┐
│Incoming Inspection │
└────────────────────┘
         │ (pass)              (reject) │
         ▼                              ▼
┌────────────────────┐           ┌──────────┐
│   Sub-Assembly     │           │  SCRAP   │
└────────────────────┘           └──────────┘
         │                              ▲
         ▼                              │ (escalation)
┌────────────────────┐                  │
│ Nozzle Inspection  │──(fail)──▶ REWORK ──┐
└────────────────────┘                  │   │
         │ (pass)                       │   │
         ▼                              │   │
┌────────────────────┐                  │   │
│   Flow Testing     │──(fail)──────────┼───┘
└────────────────────┘                  │
         │ (pass)                       │
         ▼                              │
┌────────────────────┐                  │
│  Final Assembly    │                  │
└────────────────────┘                  │
         │                              │
         ▼                              │
┌────────────────────┐                  │
│    Final Test      │──(fail)──────────┘
└────────────────────┘
         │ (pass)
         ▼
┌────────────────────┐
│     Packaging      │
└────────────────────┘
         │
         ▼
┌────────────────────┐
│     COMPLETE       │
└────────────────────┘
```

| from_step | to_step | edge_type | Notes |
|-----------|---------|-----------|-------|
| Incoming Inspection | Sub-Assembly | DEFAULT | Parts pass incoming QC |
| Incoming Inspection | Scrap | ALTERNATE | Reject defective incoming parts |
| Sub-Assembly | Nozzle Inspection | DEFAULT | Always |
| Nozzle Inspection | Flow Testing | DEFAULT | Pass |
| Nozzle Inspection | Rework | ALTERNATE | Fail |
| Nozzle Inspection | Scrap | ESCALATION | 2nd failure |
| Flow Testing | Final Assembly | DEFAULT | Pass |
| Flow Testing | Rework | ALTERNATE | Fail |
| Flow Testing | Scrap | ESCALATION | 2nd failure |
| Rework | Nozzle Inspection | DEFAULT | Return to inspection |
| Final Assembly | Final Test | DEFAULT | Always |
| Final Test | Packaging | DEFAULT | Pass |
| Final Test | Rework | ALTERNATE | Fail |
| Final Test | Scrap | ESCALATION | 2nd failure |
| Packaging | Complete | DEFAULT | Always |

**Key Differences from Reman:**
- No core receiving, disassembly, or component grading steps
- Starts with incoming inspection of new parts from suppliers
- Shares inspection steps (Nozzle Inspection, Flow Testing, Final Test) - same equipment
- Simpler linear flow with rework loop

---

### Equipment

| Name | Type | Serial | Calibration Due | Status | Used At Step |
|------|------|--------|-----------------|--------|--------------|
| Flow Test Stand #1 | Flow Tester | FTS-001 | +45 days | Current | Flow Testing |
| Flow Test Stand #2 | Flow Tester | FTS-002 | +12 days | Due Soon | Flow Testing |
| Nozzle Spray Analyzer | Spray Tester | NSA-100 | +90 days | Current | Nozzle Inspection |
| Bosch CMM Station | CMM | CMM-001 | +60 days | Current | Component Grading |
| Torque Wrench TW-25 | Torque Tool | TW-025 | -5 days | **Overdue** | Assembly |
| Pressure Gauge PG-100 | Gauge | PG-100 | +30 days | Current | Final Test |

**Calibration Status Behavior:**

| Status | System Behavior | Demo Story Purpose |
|--------|-----------------|-------------------|
| Current | Normal operation, no alerts | Baseline behavior |
| Due Soon (≤30 days) | Warning badge, scheduling reminder | Shows proactive compliance |
| **Overdue** | **Blocks step completion** - operator cannot submit step results until equipment is recalibrated or supervisor override | Compliance enforcement demo |

> **Implementation Note:** When equipment is overdue, the step execution form should:
> 1. Display a blocking error: "Equipment TW-025 calibration expired 5 days ago"
> 2. Offer "Request Supervisor Override" button (creates ApprovalRequest)
> 3. Once approved or equipment recalibrated, allow step completion
>
> For the demo scenario, Torque Wrench TW-025 being overdue at Assembly step creates a natural "compliance enforcement" demo moment where operators see blocking behavior.

**Equipment-Step Mapping (both processes):**

| Step | Process(es) | Required Equipment | Notes |
|------|-------------|-------------------|-------|
| Core Receiving | Reman | - | Visual inspection only |
| Incoming Inspection | New | Bosch CMM Station | Verify new parts meet spec |
| Disassembly | Reman | - | Hand tools (not tracked) |
| Component Grading | Reman | Bosch CMM Station | Dimensional verification |
| Sub-Assembly | New | - | Hand assembly |
| Cleaning | Reman | - | Ultrasonic cleaner (not calibrated) |
| Nozzle Inspection | Both | Nozzle Spray Analyzer | Spray pattern analysis |
| Flow Testing | Both | Flow Test Stand #1 or #2 | Either stand, same capability |
| Rework | Both | - | Varies by defect |
| Assembly | Reman | Torque Wrench TW-25 | Critical torque specs |
| Final Assembly | New | Torque Wrench TW-25 | Critical torque specs |
| Final Test | Both | Pressure Gauge PG-100 | Final pressure verification |
| Packaging | Both | - | No equipment required |

**Equipment-Step Linking Model:**
```
EquipmentUsage (logs ACTUAL usage, not requirements):
  - equipment: FK(Equipments)
  - step: FK(Steps)
  - part: FK(Parts)
  - operator: FK(User)
  - used_at: DateTimeField (auto_now_add)
  - error_report: FK(QualityReports, nullable)
  - notes: TextField
```

> **Implementation Note:** There is NO "required equipment" through model linking Steps to Equipments. The equipment-step mapping table above is reference data for operators, not enforced by the system. Equipment usage is tracked via `EquipmentUsage` records created when operators log which equipment they used.
>
> For the seeder, create EquipmentUsage records for completed StepExecutions where equipment was involved (e.g., Flow Testing → Flow Test Stand #1).
>
> **Multiple equipment options (e.g., "Flow Test Stand #1 or #2"):** Both stands are equivalent - operator chooses one and logs it. The seeder should randomly assign one of the valid options per step execution.

---

### Orders

**Order 1: ORD-2024-0042** (Main demo order)
| Field | Value |
|-------|-------|
| Customer | Midwest Fleet Services |
| PO Number | MFS-PO-2024-0312 |
| Received | 10 days ago |
| Due Date | +5 days |
| Quantity | 24 injectors |
| Status | In Progress |

**Order 2: ORD-2024-0038** (Completed)
| Field | Value |
|-------|-------|
| Customer | Great Lakes Diesel Supply |
| Received | 25 days ago |
| Completed | 5 days ago |
| Quantity | 12 injectors |
| Status | Shipped |

**Order 3: ORD-2024-0048** (New)
| Field | Value |
|-------|-------|
| Customer | Northern Trucking Co |
| Received | Yesterday |
| Quantity | 8 injectors |
| Status | Received |

---

### Work Orders

Work orders are the internal production jobs that link customer orders to the shop floor. Each work order:
- References a customer order (`related_order`)
- Specifies which process to follow (`process`)
- Has a priority for scheduling
- Tracks expected vs actual completion

**Work Order Definitions:**

| WO ID | ERP_id | Related Order | Process | Qty | Priority | Status | Created | Expected | Notes |
|-------|--------|---------------|---------|-----|----------|--------|---------|----------|-------|
| WO-0042-A | WO-2024-0042-A | ORD-2024-0042 | Reman | 24 | HIGH | IN_PROGRESS | -9 days | +4 days | Midwest Fleet main batch |
| WO-0038-A | WO-2024-0038-A | ORD-2024-0038 | Reman | 12 | NORMAL | COMPLETED | -24 days | -6 days | Great Lakes - shipped |
| WO-0048-A | WO-2024-0048-A | ORD-2024-0048 | Reman | 8 | NORMAL | PENDING | -1 day | +10 days | Northern Trucking - queued |

**Work Order Status Distribution:**

| Status | Count | Example | Purpose in Demo |
|--------|-------|---------|-----------------|
| PENDING | 1 | WO-0048-A | Show queued work |
| IN_PROGRESS | 1 | WO-0042-A | Active production |
| COMPLETED | 1 | WO-0038-A | Historical reference |

**Work Order → Parts Mapping:**

| Work Order | Parts | Current State |
|------------|-------|---------------|
| WO-0042-A | INJ-0042-001 through INJ-0042-024 | 16 complete, 2 quarantined, 1 scrapped, 5 in progress |
| WO-0038-A | INJ-0038-001 through INJ-0038-012 | All complete and shipped |
| WO-0048-A | (not yet created) | Parts created when WO starts |

**Work Order Timing:**

| WO | Created | Started | Expected Complete | Actual Complete | Duration |
|----|---------|---------|-------------------|-----------------|----------|
| WO-0042-A | -9 days | -9 days | +4 days | - | (ongoing) |
| WO-0038-A | -24 days | -23 days | -6 days | -5 days | 18 days |
| WO-0048-A | -1 day | - | +10 days | - | (not started) |

**Priority Demonstration:**
- WO-0042-A is HIGH priority because customer due date is approaching (+5 days)
- If a new urgent order came in, it could be marked URGENT (1) and jump the queue
- Scheduling views sort by priority, then by due date

---

### Parts

**Parts from ORD-2024-0042 (Midwest Fleet - main demo order):**

| Part ID | Work Order | Current Step | Status | Notes |
|---------|------------|--------------|--------|-------|
| INJ-0042-001 through 016 | WO-0042-A | Complete | Shipped | 16 completed |
| INJ-0042-017 | WO-0042-A | Flow Testing | **Quarantined** | Flow rate OOS, disposition pending (no approval created yet) |
| INJ-0042-018 | WO-0042-A | Final Test | In Progress | Almost done |
| INJ-0042-019 | WO-0042-A | **Rework** | In Progress | Spray pattern fail → rework approved (APR-2024-0014) → now in rework |
| INJ-0042-020 | WO-0042-A | Assembly | In Progress | - |
| INJ-0042-021 | WO-0042-A | Flow Testing | In Progress | - |
| INJ-0042-022 | WO-0042-A | Cleaning | In Progress | - |
| INJ-0042-023 | WO-0042-A | - | **Scrapped** | Core unrepairable |
| INJ-0042-024 | WO-0042-A | Component Grading | In Progress | - |
| INJ-0042-025 | WO-0042-A | Assembly | **FPI Failed** | FPI failure blocking production (see FPI section) |
| INJ-0042-026 | WO-0042-A | Cleaning | Waiting | Blocked - waiting for Assembly FPI to pass |

**Demo Note:** INJ-0042-017 shows a part awaiting disposition (demo can create the approval). INJ-0042-019 shows a part that was approved for rework and is now being reworked. INJ-0042-025 demonstrates FPI failure blocking subsequent parts.

**Parts from ORD-2024-0038 (Great Lakes - triggered CAPA):**

| Part ID | Work Order | Final Status | Rework? | Notes |
|---------|------------|--------------|---------|-------|
| INJ-0038-001 | WO-0038-A | Shipped | No | Clean pass |
| INJ-0038-002 | WO-0038-A | Shipped | No | Clean pass |
| INJ-0038-003 | WO-0038-A | Shipped | **Yes** | Failed nozzle inspection → rework → re-inspected → passed |
| INJ-0038-004 | WO-0038-A | Shipped | No | Clean pass |
| INJ-0038-005 | WO-0038-A | Shipped | No | Clean pass |
| INJ-0038-006 | WO-0038-A | Shipped | No | Clean pass |
| INJ-0038-007 | WO-0038-A | Shipped | **Yes** | Failed nozzle inspection → rework → re-inspected → passed |
| INJ-0038-008 | WO-0038-A | Shipped | **Yes** | Failed flow testing → rework → re-tested → passed |
| INJ-0038-009 | WO-0038-A | Shipped | No | Clean pass |
| INJ-0038-010 | WO-0038-A | Shipped | **Yes** | Failed nozzle inspection → rework → re-inspected → passed |
| INJ-0038-011 | WO-0038-A | Shipped | **Yes** | Failed flow testing → rework → re-tested → passed |
| INJ-0038-012 | WO-0038-A | Shipped | No | Clean pass |

**Summary:** 5 of 12 parts (42%) required rework → triggered CAPA investigation

**Step Execution History for Reworked Parts (INJ-0038-003 example):**

| Step | Result | Timestamp | Operator | Notes |
|------|--------|-----------|----------|-------|
| Core Receiving | Pass (Grade B) | -23 days | Mike Rodriguez | |
| Disassembly | Complete | -22 days | Mike Rodriguez | |
| Component Grading | Pass (Grade A) | -21 days | Sarah Chen | |
| Cleaning | Complete | -20 days | Mike Rodriguez | |
| Nozzle Inspection | **FAIL** | -18 days | Sarah Chen | Asymmetric spray pattern |
| Rework | Complete | -17 days | Mike Rodriguez | Nozzle replaced |
| Nozzle Inspection | Pass | -16 days | Sarah Chen | Re-inspection passed |
| Flow Testing | Pass | -15 days | Sarah Chen | 118 mL/min |
| Assembly | Complete | -14 days | Mike Rodriguez | |
| Final Test | Pass | -13 days | Sarah Chen | |
| Packaging | Complete | -12 days | Mike Rodriguez | |
| Complete | Shipped | -5 days | - | Shipped with order |

**Rework Routing Logic:** After rework, parts return to Nozzle Inspection (re-enter QA sequence). If Nozzle Inspection passes, they continue to Flow Testing → Assembly → Final Test → Packaging.

---

**INJ-0038-009: Complex Multi-Step Rework History**

This part demonstrates a complex rework scenario - failed at two different inspection points across multiple rework cycles. Shows that rework isn't always a single loop.

| Visit | Step | Status | Result | Timestamp | Notes |
|-------|------|--------|--------|-----------|-------|
| 1 | Receiving | completed | - | -24 days | Normal |
| 1 | Disassembly | completed | - | -23 days | Normal |
| 1 | Component Grading | completed | Grade B | -22 days | Normal |
| 1 | Cleaning | completed | - | -21 days | Normal |
| 1 | Nozzle Inspection | completed | **FAIL** | -20 days | Spray angle 148° (spec: 152 ±3) |
| 1 | Rework | completed | - | -19 days | Nozzle realigned |
| 2 | Nozzle Inspection | completed | Pass | -18 days | Spray angle 151° - within spec |
| 1 | Flow Testing | completed | **FAIL** | -17 days | Flow rate 142 mL/min (spec: 105-135) |
| 2 | Rework | completed | - | -16 days | Replaced plunger assembly |
| 2 | Nozzle Inspection | completed | Pass | -15 days | Re-verify after plunger change |
| 2 | Flow Testing | completed | Pass | -14 days | Flow rate 119 mL/min - within spec |
| 1 | Assembly | completed | - | -13 days | Normal |
| 1 | Final Test | completed | Pass | -12 days | All parameters nominal |
| 1 | Packaging | completed | - | -11 days | Normal |
| 1 | Complete | Shipped | - | -5 days | Shipped with order |

**Key Demo Points:**
- Part failed Nozzle Inspection first (visit_number=1), went to Rework, passed on second visit
- Then failed Flow Testing (visit_number=1 at that step), went to Rework again (visit_number=2 at Rework)
- After second rework, re-verified at Nozzle Inspection (visit_number=2) before Flow Testing retest
- Shows that `visit_number` is per-step, not global - this part has visit_number=2 at three different steps

> **Demo Value:** Demonstrates complex rework history with failures at different inspection points. Shows complete audit trail of all step visits. Useful for training on how to read part history and understand rework patterns.

---

**StepExecution Model (for seeder implementation):**
```
StepExecution:
  - part: FK(Parts)
  - step: FK(Steps)
  - visit_number: int (1st, 2nd, 3rd time at this step - for rework tracking)
  - status: enum (pending, claimed, in_progress, completed, skipped, cancelled, rolled_back)

  # Entry tracking
  - entered_at: DateTimeField (auto_now_add)
  - assigned_to: FK(User, nullable)

  # Exit tracking
  - exited_at: DateTimeField (nullable)
  - completed_by: FK(User, nullable)
  - next_step: FK(Steps, nullable) - audit trail of routing

  # Decision result (for branching steps)
  - decision_result: str (e.g., "pass", "fail", measurement value)

  # Work timing
  - started_at: DateTimeField (nullable) - when work actually began

  # FPI tracking
  - is_fpi: bool (default False)
  - fpi_status: enum (not_required, pending, passed, failed, waived)
```

**Seeder Note:** For each part, create StepExecution records for every step the part has visited. The `visit_number` field tracks rework cycles - if a part fails Nozzle Inspection and goes to Rework, then returns to Nozzle Inspection, the second visit has `visit_number=2`. This is how `max_visits` enforcement works.

**StepExecutionMeasurement Model (for recording measurements):**
```
StepExecutionMeasurement:
  - step_execution: FK(StepExecution)
  - measurement_definition: FK(MeasurementDefinition)
  - value: Decimal (nullable) - numeric measurement
  - string_value: str - for pass/fail or text measurements
  - is_within_spec: bool (nullable) - auto-calculated
  - recorded_by: FK(User)
  - recorded_at: DateTimeField (auto_now_add)
  - equipment: FK(Equipments, nullable) - which equipment was used
```

**Seeder Note:** Measurements are recorded during step execution, not on quality reports. When creating demo SPC data (60 flow rate measurements), create StepExecutionMeasurement records linked to StepExecution records for the Flow Testing step.

**Parts from ORD-2024-0048 (Northern Trucking):**
- Not yet created - work order is PENDING
- Parts will be created when WO-0048-A starts production

---

### Cores (for Reman Story)

**Core-to-Order Relationship:**
In remanufacturing, the relationship between customer cores and finished products is not 1:1:
- Customer sends cores with their order (or we source them separately)
- Cores are disassembled into components, which enter inventory by grade
- Finished products are built from pooled inventory components
- A finished injector may contain components from multiple cores
- The Parts (INJ-*) track finished goods; Cores (CORE-*) track incoming units

**For ORD-2024-0042 (Midwest Fleet, 24 injectors):**
- 6 cores received with the order (shown below)
- Additional components pulled from existing inventory (from prior orders/purchases)
- Some finished injectors use 100% Midwest Fleet components; others are mixed

| Core ID | Source | Condition | Status | Components |
|---------|--------|-----------|--------|------------|
| CORE-0042-001 | Midwest Fleet | Grade B | Disassembled | 5 harvested |
| CORE-0042-002 | Midwest Fleet | Grade A | Disassembled | 6 harvested |
| CORE-0042-003 | Midwest Fleet | Grade C | Disassembled | 4 harvested |
| CORE-0042-004 | Midwest Fleet | Grade B | In Disassembly | - |
| CORE-0042-005 | Midwest Fleet | Grade B | In Disassembly | - |
| CORE-0042-006 | Midwest Fleet | Scrap | **Scrapped** | Cracked body |
| CORE-0048-001 through 008 | Northern Trucking | Pending | Received | Not yet graded |

**Core Yield Summary (Midwest Fleet):**
- 6 cores received → 5 usable (1 scrapped outright)
- 15 usable components harvested (from 3 fully disassembled)
- 2 cores still in disassembly
- Combined with inventory: enough components to build 24 finished injectors

---

### Harvested Components (complete)

**CORE-0042-001** (Grade B) → 5 usable, 1 scrapped

| Component ID | Type | Grade | Disposition | Notes |
|--------------|------|-------|-------------|-------|
| HC-0042-001-NOZ | Nozzle Assembly | B | Rework queue | Minor wear |
| HC-0042-001-PLG | Plunger | A | Accepted to inventory | |
| HC-0042-001-VLV | Solenoid Valve | A | Accepted to inventory | |
| HC-0042-001-SPR | Spring Set | A | Accepted to inventory | |
| HC-0042-001-BDY | Injector Body | **SCRAP** | Scrapped | Micro-cracks |
| HC-0042-001-CTV | Control Valve | B | Rework queue | |

**CORE-0042-002** (Grade A) → 6 usable, 0 scrapped

| Component ID | Type | Grade | Disposition | Notes |
|--------------|------|-------|-------------|-------|
| HC-0042-002-NOZ | Nozzle Assembly | A | Accepted to inventory | |
| HC-0042-002-PLG | Plunger | A | Accepted to inventory | |
| HC-0042-002-VLV | Solenoid Valve | A | Accepted to inventory | |
| HC-0042-002-SPR | Spring Set | A | Accepted to inventory | |
| HC-0042-002-BDY | Injector Body | A | Accepted to inventory | |
| HC-0042-002-CTV | Control Valve | A | Accepted to inventory | |

**CORE-0042-003** (Grade C) → 4 usable, 2 scrapped

| Component ID | Type | Grade | Disposition | Notes |
|--------------|------|-------|-------------|-------|
| HC-0042-003-NOZ | Nozzle Assembly | **SCRAP** | Scrapped | Hole erosion |
| HC-0042-003-PLG | Plunger | C | Rework queue | Heavy scoring |
| HC-0042-003-VLV | Solenoid Valve | B | Rework queue | |
| HC-0042-003-SPR | Spring Set | A | Accepted to inventory | |
| HC-0042-003-BDY | Injector Body | **SCRAP** | Scrapped | Cracked bore |
| HC-0042-003-CTV | Control Valve | C | Rework queue | Worn seat |

**Summary:** 18 total components, 15 usable (9 Grade A, 4 Grade B, 2 Grade C), 3 scrapped

---

### Component → Finished Product Allocation (Traceability)

**How reman traceability works:**
```
Core (CORE-0042-001)
  └── HarvestedComponent (HC-0042-001-PLG)
        └── component_part: Parts (component inventory item, e.g., "PLG-INV-001")
              └── AssemblyUsage.component → Parts (PLG-INV-001)
                    └── AssemblyUsage.assembly → Parts (INJ-0042-001, finished injector)
```

**Model: HarvestedComponent**
```
HarvestedComponent:
  - core: FK(Core) - source core
  - component_type: FK(PartTypes) - what kind of component
  - component_part: OneToOne(Parts, nullable) - inventory Part created when accepted
  - condition_grade: enum (A, B, C, SCRAP)
  - disassembled_by: FK(User)
  - disassembled_at: DateTimeField
  - is_scrapped: bool
  - scrap_reason: str
```

**Model: AssemblyUsage** (tracks what components go into finished assemblies)
```
AssemblyUsage:
  - assembly: FK(Parts) - the finished product (e.g., INJ-0042-001)
  - component: FK(Parts) - the component installed (e.g., PLG-INV-001)
  - quantity: Decimal (default 1)
  - bom_line: FK(BOMLine, nullable) - link to design BOM
  - installed_by: FK(User)
  - installed_at: DateTimeField
  - step: FK(Steps, nullable) - step where installed
```

**Demo Allocation (INJ-0042-001 example):**

| Finished Injector | Component Part | Component Source | Core |
|-------------------|----------------|------------------|------|
| INJ-0042-001 | PLG-INV-001 | HC-0042-002-PLG | CORE-0042-002 |
| INJ-0042-001 | NOZ-INV-001 | HC-0042-002-NOZ | CORE-0042-002 |
| INJ-0042-001 | VLV-INV-001 | HC-0042-002-VLV | CORE-0042-002 |
| INJ-0042-001 | SPR-INV-001 | HC-0042-002-SPR | CORE-0042-002 |
| INJ-0042-001 | BDY-INV-001 | HC-0042-002-BDY | CORE-0042-002 |
| INJ-0042-001 | CTV-INV-001 | HC-0042-002-CTV | CORE-0042-002 |
| INJ-0042-002 | PLG-INV-002 | HC-0042-001-PLG | CORE-0042-001 |
| INJ-0042-002 | NOZ-INV-002 | *Prior inventory* | - |
| ... | ... | ... | ... |

> **Demo Note:** INJ-0042-001 uses all Grade A components from CORE-0042-002 (100% traceable to single core). INJ-0042-002 mixes components from CORE-0042-001 (Grade B body) with prior inventory (shows component pooling). This demonstrates both single-core and mixed-core traceability scenarios.

**Seeder Implementation:**
1. When HarvestedComponent is "Accepted to inventory", create a Parts record and link via `component_part`
2. When assembling finished injector at Assembly step, create AssemblyUsage records linking component Parts to assembly Part
3. Query example: `Part.objects.get(erp_id="INJ-0042-001").component_usages.all()` → all components in this injector

---

### Measurements & SPC Data

**Measurement: Flow Rate @ 1000 bar**
| Field | Value |
|-------|-------|
| Nominal | 120.0 mL/min |
| USL | 135.0 |
| LSL | 105.0 |
| Baseline Mean | 119.8 |
| Baseline StdDev | 3.2 |
| UCL | 129.4 |
| LCL | 110.2 |

**Recent trend (summary - see full 60 measurements in SPC Data section below):**
```
Days -30 to -13: Stable around 119-121 mL/min (in control)
Days -12 to -8:  Drifting up to 123-125 mL/min
Days -7 to -1:   Rule 2 violation - values 126-128 mL/min (> 2σ)
```

**Measurement: Return Leak Volume**
| Field | Value |
|-------|-------|
| Nominal | 45.0 mL/min |
| USL | 55.0 |
| LSL | 35.0 |
| Status | In control (stable) |

---

### Quality Reports

**ORD-2024-0038 (Great Lakes) - triggered CAPA:**

| Part | Step | Result | Inspector | Date | Notes |
|------|------|--------|-----------|------|-------|
| INJ-0038-003 | Nozzle Inspection | **FAIL** | Sarah Chen | -18 days | Asymmetric spray |
| INJ-0038-007 | Nozzle Inspection | **FAIL** | Sarah Chen | -16 days | Spray angle OOS |
| INJ-0038-008 | Flow Testing | **FAIL** | Sarah Chen | -15 days | Flow rate 136 mL/min |
| INJ-0038-010 | Nozzle Inspection | **FAIL** | Sarah Chen | -12 days | Hole erosion |
| INJ-0038-011 | Flow Testing | **FAIL** | Sarah Chen | -10 days | Flow rate 139 mL/min |
| INJ-0038-001 through 012 | Final Test | PASS | Sarah Chen | -6 days | After rework |

**INJ-0038-005: Scrapped via Max Visits Escalation**

This part demonstrates `max_visits` enforcement - failed the same step twice and was automatically routed to scrap.

| Field | Value |
|-------|-------|
| Part ID | INJ-0038-005 |
| Order | ORD-2024-0038 (Great Lakes) |
| Current Step | Scrapped (terminal) |
| Final Status | SCRAPPED |
| Scrap Reason | Max visits exceeded at Nozzle Inspection |

**StepExecution History (demonstrating escalation):**

| Visit | Step | Status | Result | Timestamp | Notes |
|-------|------|--------|--------|-----------|-------|
| 1 | Receiving | completed | - | -24 days | Normal |
| 1 | Disassembly | completed | - | -23 days | Normal |
| 1 | Cleaning | completed | - | -22 days | Normal |
| 1 | Nozzle Inspection | completed | FAIL | -21 days | Spray angle OOS |
| 1 | Rework | completed | - | -20 days | Cleaned and re-prepped |
| 2 | Nozzle Inspection | completed | FAIL | -19 days | **Still failing - max_visits=2 exceeded** |
| 1 | Scrap Review | completed | SCRAP | -18 days | Via ESCALATION edge |
| 1 | Scrapped | completed | - | -18 days | Terminal state |

> **Demo Value:** Shows the complete escalation path when a part fails the same inspection twice. The `visit_number` field on StepExecution tracks rework cycles. When `max_visits` is exceeded, the ESCALATION edge routes to Scrap Review instead of Rework.

---

**ORD-2024-0042 (Midwest Fleet) - current order:**

| Part | Step | Result | Inspector | Date | Notes |
|------|------|--------|-----------|------|-------|
| INJ-0042-017 | Flow Testing | **FAIL** | Sarah Chen | -3 days | Flow rate 138 mL/min (OOS) |
| INJ-0042-019 | Nozzle Inspection | **FAIL** | Sarah Chen | -2 days | Asymmetric spray pattern |
| INJ-0042-001 through 016 | Final Test | PASS | Sarah Chen | -4 to -1 days | Normal |
| INJ-0042-018 | Flow Testing | PASS | Sarah Chen | -1 day | 121 mL/min |

---

### Quarantine Dispositions (Demo Examples)

**QD-2024-0001: USE_AS_IS with Customer Concession**

This disposition demonstrates the `requires_customer_approval` workflow - a part accepted outside normal spec with customer agreement.

| Field | Value |
|-------|-------|
| disposition_number | QD-2024-0001 |
| part | INJ-0042-025 |
| current_state | CLOSED |
| disposition_type | **USE_AS_IS** |
| severity | MINOR |
| assigned_to | Sarah Chen |
| description | "Flow rate measured at 134 mL/min (spec: 105-135). Customer accepts +2% deviation for this batch." |
| resolution_notes | "Customer concession obtained via email. Part marked as-is with deviation noted on cert." |
| containment_action | "Part segregated pending customer response" |
| containment_completed_at | -2 days |
| containment_completed_by | Sarah Chen |
| **requires_customer_approval** | **True** |
| **customer_approval_received** | **True** |
| customer_approval_reference | "Email from Tom Bradley, 2024-03-01, Subject: RE: Deviation Request INJ-0042-025" |
| customer_approval_date | -1 day |

> **Demo Value:** Shows the MRB (Material Review Board) workflow where a part slightly outside spec is accepted with customer concession. Demonstrates `requires_customer_approval` field usage and customer approval tracking.

---

**QD-2024-0002: REWORK Disposition (Standard)**

| Field | Value |
|-------|-------|
| disposition_number | QD-2024-0002 |
| part | INJ-0042-019 |
| current_state | IN_PROGRESS |
| disposition_type | REWORK |
| severity | MAJOR |
| assigned_to | Mike Rodriguez |
| description | "Asymmetric spray pattern - nozzle requires rework" |
| resolution_notes | "Routed to Rework step via DAG" |
| requires_customer_approval | False |

---

**QD-2024-0003: Pending Disposition (Demo Starting Point)**

| Field | Value |
|-------|-------|
| disposition_number | QD-2024-0003 |
| part | INJ-0042-017 |
| current_state | OPEN |
| disposition_type | *(not yet decided)* |
| severity | MAJOR |
| assigned_to | Sarah Chen |
| description | "Flow rate 138 mL/min exceeds USL (135). Pending MRB decision." |
| requires_customer_approval | *(TBD based on decision)* |

> **Demo Value:** This is an OPEN disposition - user can demonstrate creating the disposition decision (REWORK, SCRAP, or USE_AS_IS) and initiating the appropriate approval workflow.

---

### CAPA

**CAPA-2024-003: Elevated Nozzle Rejection Rate**

| Field | Value | Model Field |
|-------|-------|-------------|
| capa_number | CAPA-2024-003 | `capa_number` |
| Problem Statement | Elevated Nozzle Rejection Rate - March 2024 | `problem_statement` |
| Status | IN_PROGRESS | `status` |
| Type | CORRECTIVE | `capa_type` |
| Severity | MAJOR | `severity` |
| Initiated By | Jennifer Walsh | `initiated_by` |
| Initiated Date | -7 days | `initiated_date` |
| Assigned To | Jennifer Walsh | `assigned_to` |
| Due Date | +14 days | `due_date` |
| Immediate Action | Quarantine remaining nozzle inventory from batch NZ-2024-0315 | `immediate_action` |
| Approval Required | True | `approval_required` |
| Approval Status | PENDING | `approval_status` |
| Quality Reports | QR for INJ-0038-003, -007, -008, -010, -011 | `quality_reports.add(...)` |
| Step | Nozzle Inspection | `step` |
| Work Order | WO-0038-A | `work_order` |

**RcaRecord (child of CAPA):**
| Field | Value | Model Field |
|-------|-------|-------------|
| CAPA | CAPA-2024-003 | `capa` |
| Method | FIVE_WHYS | `rca_method` |
| Problem Description | 5 nozzle failures in 12-unit order vs. expected 1-2 | `problem_description` |
| Root Cause Summary | Supplier process change not communicated; audit schedule lapsed | `root_cause_summary` |
| Conducted By | Jennifer Walsh | `conducted_by` |
| Conducted Date | -5 days | `conducted_date` |
| Review Status | APPROVED | `rca_review_status` |
| Verification Status | UNVERIFIED | `root_cause_verification_status` |

**FiveWhys (child of RcaRecord):**
| Why | Question | Answer |
|-----|----------|--------|
| 1 | Why did nozzle failures increase? | Nozzle spray pattern failures increased 3x during ORD-2024-0038 (Great Lakes) processing |
| 2 | Why are spray patterns failing? | Nozzle holes showing irregular wear patterns visible in 3D heatmap |
| 3 | Why do nozzles have irregular wear? | Incoming nozzles from supplier batch NZ-2024-0315 (received -30 days) have micro-cracks |
| 4 | Why does batch NZ-2024-0315 have micro-cracks? | Delphi changed heat treatment process without notification |
| 5 | Why wasn't Delphi's process change detected? | Supplier qualification audit overdue by 6 months; process change went undetected |

**Identified Root Cause:** Supplier process change not communicated; audit schedule lapsed

**Evidence linking to data:**
- Quality reports from ORD-2024-0038 show 5 nozzle failures (vs. typical 1-2)
- SPC chart shows flow rate drift starting -12 days (correlated with batch NZ-2024-0315)
- 3D heatmap defect clustering on nozzle tip area

**Explicit QualityReport → CAPA Linkage (for seeder):**

The following QualityReports should be linked to CAPA-2024-003 via `capa.quality_reports.add(...)`:

| QualityReport | Part | Step | Result | Defect | Link Reason |
|---------------|------|------|--------|--------|-------------|
| QR-0038-003-NI | INJ-0038-003 | Nozzle Inspection | FAIL | Asymmetric spray | Triggered investigation |
| QR-0038-007-NI | INJ-0038-007 | Nozzle Inspection | FAIL | Hole blockage | Pattern evidence |
| QR-0038-008-NI | INJ-0038-008 | Nozzle Inspection | FAIL | Spray angle drift | Pattern evidence |
| QR-0038-010-FT | INJ-0038-010 | Flow Testing | FAIL | Flow rate 138 mL/min | SPC violation |
| QR-0038-011-NI | INJ-0038-011 | Nozzle Inspection | FAIL | Nozzle erosion | Pattern evidence |

```python
# Seeder code:
capa = CAPA.objects.get(capa_number="CAPA-2024-003")
triggering_qrs = QualityReports.objects.filter(
    part__erp_id__startswith="INJ-0038",
    status="FAIL"
)
capa.quality_reports.add(*triggering_qrs)
```

**Tasks:**
| Task | Assignee | Completion Mode | Status | Due |
|------|----------|-----------------|--------|-----|
| Contact Delphi re: batch NZ-2024-0315 | Jennifer Walsh | SINGLE_OWNER | Complete | - |
| Quarantine remaining batch inventory | Mike Rodriguez | SINGLE_OWNER | Complete | - |
| Schedule supplier audit | Jennifer Walsh | SINGLE_OWNER | In Progress | +7 days |
| Update incoming inspection procedure | Sarah Chen, Maria Santos | ALL_ASSIGNEES | Pending | +10 days |
| Implement tightened sampling for nozzles | Sarah Chen | SINGLE_OWNER | Pending | +5 days |

**Multi-Person Task Example:** "Update incoming inspection procedure" uses ALL_ASSIGNEES mode, meaning both Sarah Chen and Maria Santos must complete their portion before the task is marked complete. See CapaTaskAssignee records for individual progress tracking.

---

### CAPA Lifecycle Examples

To demonstrate the full CAPA workflow, include CAPAs at different stages:

---

**CAPA-2024-001: Closed (Verified Complete)**

| Field | Value | Model Field |
|-------|-------|-------------|
| capa_number | CAPA-2024-001 | `capa_number` |
| Problem Statement | Torque wrench calibration drift causing loose fittings | `problem_statement` |
| Status | **CLOSED** | `status` |
| Type | CORRECTIVE | `capa_type` |
| Severity | MINOR | `severity` |
| Initiated By | Sarah Chen | `initiated_by` |
| Initiated Date | -45 days | `initiated_date` |
| Closed Date | -20 days | `closed_date` |
| Assigned To | Mike Rodriguez | `assigned_to` |
| Approval Required | False | `approval_required` |

**RcaRecord:**
| Field | Value |
|-------|-------|
| Method | FIVE_WHYS |
| Root Cause Summary | Calibration interval too long for usage rate |
| Verification Status | **VERIFIED** |

**CapaVerification (required for CLOSED status):**
| Field | Value |
|-------|-------|
| Verified By | Jennifer Walsh |
| Verification Date | -21 days |
| Effectiveness Result | CONFIRMED |
| Evidence | "30-day monitoring shows zero torque-related defects" |

> **Demo Value:** Shows a fully resolved CAPA with verification complete.

---

**CAPA-2024-005: Open (Just Initiated)**

| Field | Value | Model Field |
|-------|-------|-------------|
| capa_number | CAPA-2024-005 | `capa_number` |
| Problem Statement | Customer complaint - unit returned after 30 days with leak | `problem_statement` |
| Status | **OPEN** | `status` |
| Type | CORRECTIVE | `capa_type` |
| Severity | MAJOR | `severity` |
| Initiated By | Jennifer Walsh | `initiated_by` |
| Initiated Date | Today (-0 days) | `initiated_date` |
| Assigned To | Sarah Chen | `assigned_to` |
| Due Date | +14 days | `due_date` |
| Immediate Action | Quarantine returned unit for failure analysis | `immediate_action` |

**RcaRecord:** None yet (status = OPEN, RCA not started)

**Tasks:**
| Task | Assignee | Status | Due |
|------|----------|--------|-----|
| Receive and document returned unit | Mike Rodriguez | Pending | +2 days |
| Perform failure analysis | Sarah Chen | Pending | +5 days |

> **Demo Value:** Shows a newly opened CAPA before any RCA work begins. User can see the initiation state and pending tasks.

---

### Sampling Rules

**Ruleset: Nozzle Inspection Sampling**

| State | Sample Rate | Trigger |
|-------|-------------|---------|
| Normal | 10% (1 in 10) | Default |
| Tightened | 100% | 2 failures in 20 parts |
| Reduced | 5% (1 in 20) | 50 consecutive passes |

**Current State:** Tightened (triggered by recent failures)

**Sampling Model Fields (for seeder implementation):**

```
SamplingRuleSet:
  - part_type: FK(PartTypes)
  - process: FK(Processes, nullable)
  - step: FK(Steps)
  - name: str (e.g., "Nozzle Inspection - Normal")
  - active: bool
  - fallback_ruleset: FK(self, nullable) - tightened ruleset to switch to
  - fallback_threshold: int (nullable) - failures before escalation (e.g., 2)
  - fallback_duration: int (nullable) - passes before de-escalation (e.g., 50)
  - is_fallback: bool - True if this is a tightened/fallback ruleset

SamplingRule:
  - ruleset: FK(SamplingRuleSet)
  - rule_type: enum (every_nth_part, percentage, random, first_n_parts, exact_count)
  - value: int (e.g., 10 for "every 10th part" or "10%")
  - order: int

SamplingTriggerState:
  - ruleset: FK(SamplingRuleSet) - the fallback ruleset that's active
  - work_order: FK(WorkOrder)
  - step: FK(Steps)
  - active: bool
  - triggered_by: FK(QualityReports, nullable)
  - triggered_at: datetime
  - success_count: int - passes since activation
  - fail_count: int

SamplingAuditLog:
  - part: FK(Parts)
  - rule: FK(SamplingRule)
  - sampling_decision: bool - True if part was selected for inspection
  - timestamp: datetime
  - ruleset_type: enum (PRIMARY, FALLBACK)
```

**Seeder Implementation:**
```python
# Normal ruleset (10% sampling)
normal_ruleset = SamplingRuleSet.objects.create(
    part_type=injector_type,
    step=nozzle_inspection,
    name="Nozzle Inspection - Normal",
    fallback_threshold=2,  # 2 failures triggers escalation
    fallback_duration=50,  # 50 passes to de-escalate
)
SamplingRule.objects.create(ruleset=normal_ruleset, rule_type="percentage", value=10)

# Tightened ruleset (100% sampling)
tightened_ruleset = SamplingRuleSet.objects.create(
    part_type=injector_type,
    step=nozzle_inspection,
    name="Nozzle Inspection - Tightened",
    is_fallback=True,
)
SamplingRule.objects.create(ruleset=tightened_ruleset, rule_type="percentage", value=100)

# Link them
normal_ruleset.fallback_ruleset = tightened_ruleset
normal_ruleset.save()

# Current state: Tightened is active (8 passes, need 50 to de-escalate)
SamplingTriggerState.objects.create(
    ruleset=tightened_ruleset,
    work_order=wo_0042,
    step=nozzle_inspection,
    active=True,
    triggered_by=qr_0038_003,
    success_count=8,
)
```

---

### Documents

| Name | Type | Attached To | Version |
|------|------|-------------|---------|
| WI-1001 Injector Disassembly | Work Instruction | Disassembly step | 3.2 |
| WI-1002 Nozzle Inspection | Work Instruction | Nozzle Inspection step | 2.1 |
| WI-1003 Flow Test Procedure | Work Instruction | Flow Testing step | 4.0 |
| CAL-CERT-FTS001 | Calibration Certificate | Flow Test Stand #1 | - |
| PO-MFS-2024-0312 | Customer PO | ORD-2024-0042 | - |
| CAPA-003-Investigation | RCA Report | CAPA-2024-003 | 1.0 |
| Delphi-NZ-COC | Certificate of Conformance | Supplier record | - |

**Searchable Document Content (for AI Search Demo):**

The AI "Ask Anything" demo (Story 3) requires documents with searchable content. The seeder should create these documents with the following text content (stored in document body or indexed for semantic search):

**WI-1002 Nozzle Inspection (searchable content):**
```
WORK INSTRUCTION: Nozzle Inspection Procedure

1. SCOPE
This procedure covers the visual and dimensional inspection of diesel fuel injector nozzles during the remanufacturing process.

2. EQUIPMENT REQUIRED
- Optical comparator (calibrated)
- Spray pattern test fixture
- Nozzle hole gauge set (140-150 microns)
- Magnification lamp (10x minimum)

3. INSPECTION CRITERIA
3.1 Visual Inspection
- Check for cracks, erosion, or contamination at nozzle tip
- Verify all spray holes are clear and uniform
- Inspect seating surface for wear marks

3.2 Dimensional Inspection
- Measure hole diameter: 145 +/- 5 microns
- Verify spray angle: 152 +/- 3 degrees

3.3 Spray Pattern Test
- Mount nozzle in test fixture
- Apply 1000 bar test pressure
- Verify symmetric spray pattern
- Check for dripping or irregular atomization

4. ACCEPTANCE CRITERIA
PASS: All criteria met, spray pattern symmetric
FAIL: Any hole blocked, asymmetric pattern, or dimensions out of spec

5. REVISION HISTORY
Rev 2.1 - Updated spray angle tolerance per CAPA-2024-003
```

> **AI Demo Value:** When user asks "Find documents about nozzle inspection" or "What are the spray angle requirements?", the AI can retrieve and reference this content.

**WI-1001 Injector Disassembly (searchable content):**
```
WORK INSTRUCTION: Injector Disassembly Procedure

1. SCOPE
This procedure covers the safe disassembly of common rail diesel fuel injectors for remanufacturing.

2. SAFETY REQUIREMENTS
- Wear safety glasses and nitrile gloves
- Ensure injector is depressurized before disassembly
- Handle nozzle tips with care - precision ground surfaces

3. EQUIPMENT REQUIRED
- Injector holding fixture (IHF-100 or equivalent)
- Torque wrench set (5-50 Nm range)
- Component trays with ESD protection
- Cleaning solvent (approved diesel-compatible)

4. DISASSEMBLY SEQUENCE
4.1 Remove solenoid valve assembly
    - Disconnect electrical connector
    - Remove retaining bolts (torque spec: 8 Nm)
    - Lift valve assembly straight up

4.2 Remove nozzle assembly
    - Support injector body in fixture
    - Remove nozzle retaining nut (torque spec: 40 Nm)
    - Extract nozzle and spring as unit

4.3 Remove plunger assembly
    - Invert injector body
    - Extract plunger with guide tool
    - Inspect bore for scoring

5. COMPONENT HANDLING
- Place each component in labeled tray
- Keep components from same injector together until grading
- Record core serial number on tray label

6. REVISION HISTORY
Rev 3.2 - Added ESD protection requirement for solenoid handling
```

**WI-1003 Flow Test Procedure (searchable content):**
```
WORK INSTRUCTION: Flow Test Procedure

1. SCOPE
This procedure covers the flow rate testing of remanufactured diesel fuel injectors at the Flow Testing step.

2. EQUIPMENT REQUIRED
- Flow Test Stand (FTS-001 or FTS-002)
- Calibrated flow meter (accuracy: +/- 0.5%)
- Test fluid: ISO 4113 calibration fluid
- Pressure regulator (0-2000 bar range)

3. TEST PARAMETERS
| Parameter | Nominal | Tolerance | Unit |
|-----------|---------|-----------|------|
| Test Pressure | 1000 | +/- 10 | bar |
| Fluid Temperature | 40 | +/- 2 | °C |
| Flow Rate Target | 120 | +/- 15 | mL/min |
| Return Leak Max | 10 | - | mL/min |

4. TEST PROCEDURE
4.1 Pre-Test Setup
    - Verify equipment calibration is current
    - Warm up test stand for 15 minutes
    - Verify fluid temperature stable at 40°C

4.2 Flow Rate Test
    - Mount injector in test fixture
    - Apply 1000 bar test pressure
    - Measure flow rate over 30 second interval
    - Record value in mL/min

4.3 Return Leak Test
    - Maintain 1000 bar pressure
    - Measure return line flow
    - Must be less than 10 mL/min

5. ACCEPTANCE CRITERIA
PASS: Flow rate 105-135 mL/min AND return leak < 10 mL/min
FAIL: Any parameter outside limits

6. SPC REQUIREMENTS
Flow rate measurements are SPC-controlled. Record all measurements for control chart analysis. Alert QA if measurement exceeds UCL (135 mL/min) or LCL (105 mL/min).

7. REVISION HISTORY
Rev 4.0 - Tightened flow rate tolerance from +/- 20 to +/- 15 per CAPA-2024-003
```

> **AI Demo Value:** Users can ask "What equipment do I need for flow testing?", "What is the flow rate tolerance?", or "How do I disassemble an injector?" and get relevant answers.

---

### 3D Models & Annotations

**Model: Common Rail Injector**
- File: `common_rail_injector.glb`
- Annotations: 50+ defect marks clustered on nozzle tip area
- Heatmap shows hot spot at nozzle holes

---

### Timeline (relative to "today")

**Cause-effect narrative:** The CAPA was triggered by quality issues found in the *earlier* Great Lakes order (ORD-2024-0038). The current Midwest Fleet order is being processed under the corrective actions (tightened sampling), which is catching issues that would have slipped through before.

| When | Event | Details |
|------|-------|---------|
| -25 days | ORD-2024-0038 received | Great Lakes Diesel, 12 injectors |
| -20 days | First quality issues appear | Nozzle spray failures in Great Lakes parts |
| -15 days | Sampling escalated | Tightened to 100% due to 2 failures in 20 parts |
| -12 days | SPC drift begins | Flow rate measurements trending upward |
| -10 days | ORD-2024-0042 received | Midwest Fleet, 24 injectors (main demo order) |
| -8 days | Defect pattern visible | 3D heatmap shows clustering on nozzle tips |
| -7 days | **CAPA-2024-003 opened** | Triggered by Great Lakes defect pattern + SPC signal |
| -5 days | ORD-2024-0038 shipped | 12 units complete, 2 had rework |
| -3 days | INJ-0042-017 quarantined | Midwest Fleet part fails flow test (caught by tightened sampling) |
| -2 days | INJ-0042-019 quarantined | Another nozzle failure caught |
| -1 day | ORD-2024-0048 received | Northern Trucking, 8 injectors |
| **Today** | **Demo** | |
| +5 days | ORD-2024-0042 due | Midwest Fleet deadline |
| +12 days | Flow Test Stand #2 cal due | Upcoming maintenance |
| +14 days | CAPA-2024-003 due | Investigation deadline |

---

### Equipment Types

| Name | Category | Calibration Interval | Notes |
|------|----------|---------------------|-------|
| Flow Tester | Testing | 180 days | High precision flow measurement |
| Spray Analyzer | Testing | 180 days | Nozzle pattern analysis |
| CMM | Measurement | 365 days | Coordinate measuring machine |
| Torque Tool | Assembly | 90 days | Calibrated torque wrenches |
| Pressure Gauge | Measurement | 180 days | Pressure verification |

---

### Calibration Records

| Equipment | Last Cal Date | Next Due | Result | Technician |
|-----------|---------------|----------|--------|------------|
| Flow Test Stand #1 | -45 days | +135 days | Pass | External Lab |
| Flow Test Stand #2 | -168 days | +12 days | Pass | External Lab |
| Nozzle Spray Analyzer | -90 days | +90 days | Pass | External Lab |
| Bosch CMM Station | -305 days | +60 days | Pass | Bosch Service |
| Torque Wrench TW-25 | -95 days | **-5 days** | Pass | **OVERDUE** |
| Pressure Gauge PG-100 | -150 days | +30 days | Pass | Internal |

---

### Document Types

| Name | Code | Requires Approval | Retention |
|------|------|-------------------|-----------|
| Work Instruction | WI | Yes | 7 years |
| Calibration Certificate | CAL-CERT | No | Life of equipment |
| Customer PO | PO | No | 7 years |
| CAPA Investigation | CAPA-RPT | Yes | 10 years |
| Certificate of Conformance | COC | No | 7 years |
| Training Record | TR | Yes | Duration of employment |

---

### Training Types & Records

**Training Types:**

| Name | Code | Recertification | Required For |
|------|------|-----------------|--------------|
| Disassembly Certification | DISASM-CERT | 12 months | Disassembly step |
| Flow Test Operation | FLOW-CERT | 12 months | Flow Testing step |
| Nozzle Inspection | NOZ-CERT | 12 months | Nozzle Inspection step |
| Final Test Authorization | FINAL-CERT | 12 months | Final Test step |
| Quality Inspector | QA-CERT | 24 months | All inspection steps |

**Training Records:**

| User | Training Type | Certified Date | Expires | Status |
|------|---------------|----------------|---------|--------|
| Mike Rodriguez | DISASM-CERT | -60 days | +305 days | Current |
| Mike Rodriguez | FLOW-CERT | -200 days | +165 days | Current |
| Mike Rodriguez | NOZ-CERT | -358 days | **+7 days** | **EXPIRING SOON** |
| Sarah Chen | QA-CERT | -400 days | +330 days | Current |
| Sarah Chen | NOZ-CERT | -90 days | +275 days | Current |
| Sarah Chen | FLOW-CERT | -90 days | +275 days | Current |
| Sarah Chen | FINAL-CERT | -90 days | +275 days | Current |
| **Dave Wilson** | FLOW-CERT | -380 days | **-15 days** | **EXPIRED** |
| Dave Wilson | DISASM-CERT | -60 days | +305 days | Current |

**New User: Dave Wilson (Operator with Expired Certification)**

| Field | Value |
|-------|-------|
| Email | dave.wilson@demo.ambac.com |
| Password | demo123 |
| Name | Dave Wilson |
| Role | Production_Operator |
| Purpose | Demo expired training blocking |

**Training Demo Scenarios:**

| Scenario | User | Certification | Demo Value |
|----------|------|---------------|------------|
| Expiring warning | Mike Rodriguez | NOZ-CERT (+7 days) | Banner: "Certification expires in 7 days" |
| Blocked operator | Dave Wilson | FLOW-CERT (-15 days) | **Cannot execute Flow Testing step** |
| Dashboard alert | Jennifer Walsh | - | Shows 1 expired, 1 expiring certification |

> **Seeder Note:** Create TrainingRequirement linking FLOW-CERT to Flow Testing step. When Dave tries to execute Flow Testing, the system blocks based on expired certification.

---

### Disassembly BOM (Expected Components per Core)

**Part Type: Common Rail Injector**

| Component | Expected Qty | Typical Yield | Fallout Rate |
|-----------|--------------|---------------|--------------|
| Nozzle Assembly | 1 | 85% | 15% |
| Plunger | 1 | 90% | 10% |
| Solenoid Valve | 1 | 92% | 8% |
| Spring Set | 1 | 97% | 3% |
| Injector Body | 1 | 80% | 20% |
| Control Valve | 1 | 88% | 12% |

---

### Approval Templates

**Template Definitions:**

| Template Name | approval_type | flow_type | sequence | default_due_days | auto_assign_by_role |
|---------------|---------------|-----------|----------|------------------|---------------------|
| Document Release | DOCUMENT_RELEASE | ALL_REQUIRED | SEQUENTIAL | 5 | QA Manager |
| CAPA Major | CAPA_MAJOR | ALL_REQUIRED | PARALLEL | 7 | - |
| CAPA Critical | CAPA_CRITICAL | ALL_REQUIRED | SEQUENTIAL | 3 | - |
| Disposition Approval | PROCESS_APPROVAL | ANY | PARALLEL | 1 | QA Inspector |
| Training Certification | TRAINING_CERT | ALL_REQUIRED | PARALLEL | 14 | - |

**Template → Default Approvers:**

| Template | Default Approvers | Default Groups |
|----------|-------------------|----------------|
| Document Release | - | QA Manager |
| CAPA Major | Jennifer Walsh, Sarah Chen | - |
| CAPA Critical | Jennifer Walsh, Sarah Chen | Tenant Admin |
| Disposition Approval | - | QA Inspector |
| Training Certification | Jennifer Walsh | - |

---

### Approval Requests (Active)

**APR-2024-0015: CAPA Closure Approval**

| Field | Value |
|-------|-------|
| approval_number | APR-2024-0015 |
| content_object | CAPA-2024-003 |
| approval_type | CAPA_MAJOR |
| status | **PENDING** |
| requested_by | Jennifer Walsh |
| requested_at | -2 days |
| due_date | +5 days |
| flow_type | ALL_REQUIRED |
| reason | "Request to close CAPA after verification of corrective actions" |

**Approvers assigned:**

| Approver | is_required | sequence_order | Status |
|----------|-------------|----------------|--------|
| Sarah Chen | Yes | - | Awaiting |
| Jennifer Walsh | Yes | - | Awaiting (self - requires justification) |

**Demo story:** This approval is PENDING - user can demonstrate the approval workflow by having Sarah Chen approve, then Jennifer self-approve with justification.

---

**APR-2024-0012: Work Instruction Update**

| Field | Value |
|-------|-------|
| approval_number | APR-2024-0012 |
| content_object | WI-1002 Nozzle Inspection |
| approval_type | DOCUMENT_RELEASE |
| status | **APPROVED** |
| requested_by | Sarah Chen |
| requested_at | -8 days |
| completed_at | -6 days |
| flow_type | ALL_REQUIRED |
| reason | "Updated inspection criteria per CAPA-2024-003 corrective action" |

**Responses (completed):**

| Approver | decision | decision_date | comments |
|----------|----------|---------------|----------|
| Jennifer Walsh | APPROVED | -6 days | "Approved. Changes align with CAPA findings." |

---

**APR-2024-0014: Quarantine Disposition**

| Field | Value |
|-------|-------|
| approval_number | APR-2024-0014 |
| content_object | QuarantineDisposition for INJ-0042-019 |
| approval_type | PROCESS_APPROVAL |
| status | **APPROVED** |
| requested_by | Mike Rodriguez |
| requested_at | -1 day |
| completed_at | -1 day |
| flow_type | ANY |
| reason | "Rework approved for INJ-0042-019 - spray pattern failure is correctable" |

**Response:**

| Approver | decision | decision_date | comments |
|----------|----------|---------------|----------|
| Sarah Chen | APPROVED | -1 day | "Rework approved. Route back to cleaning step." |

---

**APR-2024-0010: Training Certification - REJECTED**

| Field | Value |
|-------|-------|
| approval_number | APR-2024-0010 |
| content_object | TrainingRecord for Mike Rodriguez (FINAL-CERT) |
| approval_type | TRAINING_CERT |
| status | **REJECTED** |
| requested_by | Mike Rodriguez |
| requested_at | -5 days |
| completed_at | -4 days |
| flow_type | ALL_REQUIRED |
| reason | "Request certification for Final Test operation" |

**Response (rejection):**

| Approver | decision | decision_date | comments |
|----------|----------|---------------|----------|
| Jennifer Walsh | **REJECTED** | -4 days | "Incomplete training hours. Need 8 more hours of supervised operation before certification. Please resubmit after completing additional training." |

> **Demo Value:** Shows rejection workflow with actionable feedback. User can see rejection reason and understand remediation path. Note: Mike's training records do NOT include FINAL-CERT - consistent with this rejection.

---

**APR-2024-0016: Equipment Override - Supervisor Approval**

| Field | Value |
|-------|-------|
| approval_number | APR-2024-0016 |
| content_object | Torque Wrench TW-025 (overdue calibration) |
| approval_type | EQUIPMENT_OVERRIDE |
| status | **PENDING** |
| requested_by | Mike Rodriguez |
| requested_at | -1 day |
| due_date | Today |
| flow_type | ALL_REQUIRED |
| reason | "Request supervisor override to use TW-025 for urgent order WO-0042-A. Calibration is 5 days overdue but equipment passed internal verification check. Replacement due tomorrow." |

**Approvers assigned:**

| Approver | is_required | sequence_order | Status |
|----------|-------------|----------------|--------|
| Jennifer Walsh | Yes | - | Awaiting |

**Demo story:** This approval is PENDING - demonstrates equipment calibration blocking and the override workflow. Jennifer can approve with documented justification, allowing work to proceed while acknowledging the deviation.

> **Demo Value:** Shows how supervisors can authorize equipment overrides with proper documentation. Demonstrates that the system enforces compliance but allows controlled exceptions for production continuity.

---

### Approval Workflow Demo Scenarios

| Scenario | Template | Demo Action |
|----------|----------|-------------|
| Approve pending CAPA | CAPA Major | Log in as Sarah Chen → Approve APR-2024-0015 |
| View completed approval | Document Release | Show APR-2024-0012 with signature and comments |
| Quick disposition | Disposition Approval | Show ANY flow - one approval was sufficient |
| View rejection | Training Certification | Show APR-2024-0010 with rejection reason |

---

### 3D Model & Defect Annotations

**Model:** 3DBenchy (`3DBenchy.glb`)

Using Benchy as a demo stand-in. Defects clustered on chimney to show heatmap pattern.

| Region | % of Defects | Count | Heatmap Color |
|--------|--------------|-------|---------------|
| Chimney (hot zone) | 70% | 35 | Red/Orange |
| Cabin roof | 15% | 8 | Yellow |
| Hull (scattered) | 15% | 7 | Blue/Green |
| **Total** | 100% | **50** | |

**Defect Types:**

| Code | Type | Severity |
|------|------|----------|
| WEAR | Wear | Medium |
| PORE | Porosity | High |
| SCRT | Scratch | Low |
| CONT | Contamination | Medium |
| CRCK | Crack | Critical |

**Coordinates:** TODO - manual capture in 3D viewer

---

### SPC Measurement Sequence (Flow Rate)

**Measurement Definition:**
- Name: Flow Rate @ 1000 bar
- Unit: mL/min
- Nominal: 120.0
- USL: 135.0, LSL: 105.0
- SPC Enabled: Yes
- Subgroup Size: 1 (I-MR chart)

**Frozen Baseline:**
| Field | Value |
|-------|-------|
| Mean | 119.8 |
| StdDev | 3.2 |
| UCL | 129.4 (mean + 3σ) |
| LCL | 110.2 (mean - 3σ) |
| 2σ Upper | 126.2 |
| 2σ Lower | 113.4 |
| Frozen By | Jennifer Walsh |
| Frozen Date | -45 days |
| Sample Size | 100 |

**Measurement Values (60 measurements over 30 days):**

```
Days -30 to -21 (stable, in control):
  119.2, 120.1, 118.5, 121.3, 119.8, 120.4, 118.9, 121.0, 119.5, 120.2
  118.8, 120.6, 119.1, 121.2, 119.9, 120.0, 118.7, 120.8, 119.4, 120.3

Days -20 to -13 (still stable):
  119.6, 120.5, 119.0, 120.9, 119.3, 120.7, 118.6, 121.1

Days -12 to -8 (starting to drift up - correlated with batch NZ-2024-0315):
  121.5, 122.3, 121.8, 123.1, 122.6, 123.4, 122.9, 124.2, 123.5, 124.8

Days -7 to -1 (Rule 2 violation: 2 of 3 points > 2σ):
  125.1, 126.8, 124.9, 127.5, 126.2, 128.1, 125.8, 127.9, 126.5, 128.4
        ^^^^         ^^^^         ^^^^         ^^^^         ^^^^
        (>126.2 = beyond 2σ, triggers Rule 2)
```

**Rule Violations to Flag:**
| Day | Value | Rule | Description |
|-----|-------|------|-------------|
| -6 | 126.8 | Rule 2 | First signal: 2 of 3 consecutive points beyond 2σ (same side) |
| -4 | 127.5 | Rule 2 | Continues pattern |
| -3 | **131.2** | **Rule 1** | **BEYOND UCL (129.4) - Out of Control!** Part INJ-0042-017 quarantined |
| -2 | 128.1 | Rule 2 | Pattern continues |
| -1 | 128.4 | Rule 2 | Latest point, still elevated |

> **Demo Value:** Measurement #61 (131.2 mL/min, Day -3) demonstrates **Rule 1 violation** - single point beyond 3σ. This is the measurement that caused INJ-0042-017 to be quarantined. SPC chart shows both drift pattern (Rule 2) AND the out-of-control point (Rule 1).

---

### Sampling Audit Log

**Ruleset: Nozzle Inspection Sampling**

| Timestamp | Event | From State | To State | Trigger | Parts Affected |
|-----------|-------|------------|----------|---------|----------------|
| -30 days | Created | - | Normal | Initial setup | - |
| -15 days | Escalation | Normal | Tightened | 2 failures in 20 parts | INJ-0038-003, INJ-0038-007 (Great Lakes) |
| -10 days | Maintained | Tightened | Tightened | Continued failures | INJ-0038-008, INJ-0038-010 |
| -3 days | Maintained | Tightened | Tightened | INJ-0042-017 failed | Now catching Midwest Fleet issues |

**Current State:** Tightened (100% inspection)

**Sampling Decisions Log (recent):**

| Part | Decision | Reason | Inspector | Date |
|------|----------|--------|-----------|------|
| INJ-0042-015 | Inspect | Tightened sampling | Sarah Chen | -5 days |
| INJ-0042-016 | Inspect | Tightened sampling | Sarah Chen | -4 days |
| INJ-0042-017 | Inspect | Tightened sampling | Sarah Chen | -3 days |
| INJ-0042-018 | Inspect | Tightened sampling | Sarah Chen | -1 day |
| INJ-0042-019 | Inspect | Tightened sampling | Sarah Chen | -2 days |

---

### First Piece Inspection (FPI) Examples

FPI is triggered for the first part of each work order at each step. StepExecution has `is_fpi` and `fpi_status` fields.

**StepExecution Model Fields (FPI-related):**
```
StepExecution:
  - is_fpi: bool - True if this is first piece inspection
  - fpi_status: enum (pending, passed, failed, waived) - nullable, only set if is_fpi=True
```

**FPI Status Distribution in Demo Data:**

| Part | Step | Work Order | is_fpi | fpi_status | Notes |
|------|------|------------|--------|------------|-------|
| INJ-0042-001 | Disassembly | WO-0042-A | True | **passed** | First part, FPI passed |
| INJ-0042-001 | Cleaning | WO-0042-A | True | **passed** | First at each step |
| INJ-0042-001 | Nozzle Inspection | WO-0042-A | True | **passed** | All FPI complete |
| INJ-0042-001 | Assembly | WO-0042-A | True | **passed** | Completed all FPI |
| INJ-0042-020 | Assembly | WO-0042-A | False | - | Not FPI (already done) |
| INJ-0048-001 | Receiving | WO-0048-A | True | **pending** | New order, awaiting FPI approval |
| INJ-0048-002 | Receiving | WO-0048-A | False | - | Not FPI (001 is first) |
| INJ-0042-025 | Assembly | WO-0042-A | True | **failed** | FPI failed - blocking production at Assembly |

**FPI Demo Scenarios:**

| Scenario | Part | Step | Demo Action |
|----------|------|------|-------------|
| View pending FPI | INJ-0048-001 | Receiving | See "FPI Required" badge, checklist items |
| Approve FPI | INJ-0048-001 | Receiving | Complete FPI checklist, mark passed |
| View completed FPI | INJ-0042-001 | Any step | See FPI approval history |
| **View failed FPI** | INJ-0042-025 | Assembly | See "FPI FAILED" blocking banner, requires re-inspection |

**Failed FPI Scenario (INJ-0042-025):**

| Field | Value |
|-------|-------|
| Part | INJ-0042-025 |
| Step | Assembly |
| is_fpi | True |
| fpi_status | **failed** |
| Failure Reason | "Torque settings out of spec on first assembly attempt" |
| Blocking | Yes - no other parts can proceed at Assembly until FPI re-passed |
| Required Action | Recalibrate torque wrench, re-inspect first piece |

> **Demo Value:** Shows FPI failure blocking production. Other parts (INJ-0042-026+) cannot proceed to Assembly until INJ-0042-025 passes FPI re-inspection. Demonstrates quality gate enforcement.

**Seeder Logic:**
```python
# First StepExecution for each (work_order, step) combination gets is_fpi=True
first_at_step = StepExecution.objects.filter(
    work_order=wo,
    step=step
).order_by('created_at').first()

if first_at_step:
    first_at_step.is_fpi = True
    first_at_step.fpi_status = 'passed'  # or 'pending' for in-progress demo
    first_at_step.save()
```

> **Demo Value:** Shows quality gate at start of each step for new work orders. Demonstrates that subsequent parts don't require FPI once first piece is approved.

---

### Life Limit Definitions (if showing life tracking)

| Component Type | Limit Type | Value | Unit |
|----------------|------------|-------|------|
| Nozzle Assembly | Cycles | 50,000 | injections |
| Nozzle Assembly | Calendar | 5 | years |
| Solenoid Valve | Cycles | 100,000 | actuations |
| Plunger | Cycles | 75,000 | strokes |

---

### External API Identifiers (HubSpot Pipeline)

| Stage Name | API ID | Display Order | Include in Progress |
|------------|--------|---------------|---------------------|
| New Lead | 12345001 | 1 | No |
| Qualification | 12345002 | 2 | Yes |
| Proposal Sent | 12345003 | 3 | Yes |
| Negotiation | 12345004 | 4 | Yes |
| Closed Won | 12345005 | 5 | No |
| Closed Lost | 12345006 | 6 | No |

---

## Implementation Approach

### Option A: Fixture Files (JSON/YAML)
```
fixtures/
  demo/
    users.json
    companies.json
    orders.json
    parts.json
    quality.json
    capa.json
```

**Pros:** Easy to edit, version controlled, standard Django pattern
**Cons:** Hard to maintain FK relationships, brittle to model changes

### Option B: Demo Seeder Script
```python
class DemoSeeder(BaseSeeder):
    """Loads curated demo data with specific scenarios."""

    def seed(self):
        self._create_demo_users()
        self._create_demo_company()
        self._create_demo_order()
        self._create_demo_quality_scenario()
        self._create_demo_capa()
        self._create_demo_spc_data()
```

**Pros:** Programmatic, handles relationships, can use model methods
**Cons:** More code to maintain

### Option C: Hybrid
- Use fixtures for static reference data (users, companies, document types)
- Use seeder scripts for interconnected transactional data

**Recommendation:** Option C (Hybrid)

---

## Command Interface

```bash
# Development data (current behavior)
python manage.py populate_test_data --mode dev --scale medium
python manage.py populate_test_data --mode dev --scale large --clear-existing

# Demo data (new)
python manage.py populate_test_data --mode demo
python manage.py populate_test_data --mode demo --clear-existing

# Reset demo tenant (existing, automatically uses --mode demo)
python manage.py reset_demo --slug demo
```

### Argument Changes to `populate_test_data`

| Argument | Current | New Behavior |
|----------|---------|--------------|
| `--mode` | N/A (new) | `dev` (default) or `demo` |
| `--scale` | Works | Only applies to `--mode dev`, ignored for demo |
| `--modules` | Works | Only applies to `--mode dev`, demo runs all |
| `--skip-historical` | Works | Only applies to `--mode dev` |
| `--clear-existing` | Works | Works for both modes |

### Mode Routing Logic

```python
def handle(self, *args, **options):
    mode = options.get('mode', 'dev')

    if mode == 'demo':
        self._run_demo_mode(options)
    else:
        self._run_dev_mode(options)  # Current behavior

def _run_demo_mode(self, options):
    """Load curated demo data."""
    # 1. Get or create demo tenant (is_demo=True)
    # 2. Optionally clear existing
    # 3. Run demo seeders in order
    # 4. Demo seeders use fixtures + scripted data

def _run_dev_mode(self, options):
    """Current behavior - random generated data."""
    # Existing implementation
```

### Tenant Selection by Mode

| Mode | Tenant Slug | `is_demo` |
|------|-------------|-----------|
| `dev` (default) | `dev` | `False` |
| `demo` | `demo` | `True` |

- Tenant slug is fixed based on mode (no separate `--tenant` flag needed)
- Tenant is created if it doesn't exist
- If tenant exists, `--clear-existing` wipes its data before repopulating

---

## File Structure

```
Tracker/management/commands/
  populate_test_data.py      # Main command, routes to mode
  seed/
    __init__.py
    base.py                  # BaseSeeder

    # Dev seeders (generated/random data)
    users.py
    manufacturing.py
    orders.py
    quality.py
    capa.py
    documents.py
    reman.py
    life_tracking.py
    training.py
    calibration.py
    three_d_models.py

    # Demo seeders (curated data)
    demo/
      __init__.py
      base.py                # DemoSeeder base class
      users.py               # Demo user accounts (known passwords)
      company.py             # Demo companies/customers
      manufacturing.py       # Demo processes, equipment (named)
      scenario.py            # Main orchestrator - the "story"
      production.py          # Demo order with parts at stages
      quality.py             # Demo quality issue scenario
      capa.py                # Demo CAPA investigation
      spc.py                 # Demo SPC with visible trend
      documents.py           # Sample work instructions, certs
```

### Dev Seeders vs Demo Seeders

| Aspect | Dev Seeders | Demo Seeders |
|--------|-------------|--------------|
| Data source | Random generation | Hardcoded/fixtures |
| Scale | Configurable (S/M/L) | Fixed (one scenario) |
| Names | Generated (Faker) | Meaningful names |
| IDs | Random | Predictable/sequential |
| Scenarios | Random distribution | Curated storyline |
| Users | Generated emails | Known credentials |
| Idempotent | No (random each time) | Yes (same result) |

### Demo Seeder Base Class

```python
class DemoSeeder(BaseSeeder):
    """Base class for demo seeders with curated data."""

    def __init__(self, stdout, style, tenant, **kwargs):
        # Demo seeders ignore scale - always same data
        super().__init__(stdout, style, tenant=tenant, scale='demo')

    def get_or_create(self, model, lookup, defaults):
        """Idempotent create - find existing or create new."""
        obj, created = model.objects.get_or_create(**lookup, defaults=defaults)
        if created:
            self.log(f"Created {model.__name__}: {obj}")
        return obj, created
```

---

## Tasks

### Phase 1: Command Infrastructure
- [ ] Add `--mode` argument to `populate_test_data` (dev/demo)
- [ ] Add tenant selection logic based on mode
- [ ] Create `seed/demo/` directory with `__init__.py`
- [ ] Create `DemoSeeder` base class
- [ ] Refactor command to route between dev/demo modes
- [ ] Update `reset_demo` to pass `--mode demo`

### Phase 2: Demo Foundation Seeders
- [ ] `demo/users.py` - Admin, QA, Operator, Manager accounts
- [ ] `demo/company.py` - Ambac + customer companies
- [ ] `demo/manufacturing.py` - Named processes, steps, equipment

### Phase 3: Demo Scenario Seeders
- [ ] `demo/production.py` - Orders with parts at various stages
- [ ] `demo/quality.py` - Quality reports, quarantined parts
- [ ] `demo/capa.py` - CAPA with RCA and tasks
- [ ] `demo/spc.py` - Measurement data with trends
- [ ] `demo/reman.py` - Cores and harvested components

### Phase 4: Demo Assets
- [ ] `demo/documents.py` - Work instructions, certs, POs
- [ ] Create/source sample PDF documents
- [ ] `demo/calibration.py` - Equipment with various cal states

### Phase 5: Integration & Testing
- [ ] `demo/scenario.py` - Orchestrator that runs all demo seeders
- [ ] Test full demo load from scratch
- [ ] Test demo reset (clear + reload)
- [ ] Verify all demo features showcase properly

### Phase 6: UI Integration
- [ ] Demo mode banner with reset button (partially done)
- [ ] Show demo credentials on login page
- [ ] Expose `last_reset_at` in tenant context
- [ ] Add reset timestamp to banner

---

## Notes

- Demo data should be designed to showcase the product's value
- Focus on "happy path" but include one quality issue to demonstrate QA workflow
- All demo data should be obviously fake (no real company names that could cause confusion)
- Consider: can the same demo data work for different industry verticals?

---

## Changelog

| Date | Change |
|------|--------|
| 2025-03-02 | Initial design document created |
| 2025-03-02 | Added detailed demo scenario specification |
| 2025-03-02 | Added command interface and mode routing design |
| 2025-03-02 | Added 7 interconnected demo stories based on product wow moments |
| 2025-03-02 | Added complete demo data values (entities, IDs, relationships) |
| 2025-03-02 | Added missing entities: equipment types, training, calibration, document types, BOM, approvals, 3D defect coordinates, SPC sequence, sampling audit log, life limits |
| 2025-03-02 | Expanded 3D models section with descriptions for all part type models (Common Rail Injector, Nozzle, Plunger, Solenoid Valve) and defect type definitions |
| 2026-03-02 | Fixed timeline cause-effect logic: CAPA triggered by Great Lakes order (ORD-0038), Midwest Fleet processed under corrective actions |
| 2026-03-02 | Completed harvested components table: 18 total components from 3 disassembled cores with grades and dispositions |
| 2026-03-02 | Updated 5-Whys to reference specific orders and evidence linking to data |
| 2026-03-02 | Added Great Lakes quality reports that triggered CAPA |
| 2026-03-02 | Aligned sampling audit log and SPC drift timeline with cause-effect narrative |
| 2026-03-02 | Fixed customer portal user collision: portal user is now tom.bradley@midwestfleet.com (separate from company contact) |
| 2026-03-02 | Added equipment-to-step mapping table |
| 2026-03-02 | Added notification preferences for Tom Bradley (customer) and Sarah Chen (QA) |
| 2026-03-02 | Clarified core-to-order relationship with explanation of component pooling in reman workflow |
| 2026-03-02 | Added complete DAG definitions for both processes: Reman (with core receiving, disassembly, component grading) and New Manufacturing (simpler linear flow) |
| 2026-03-02 | Updated equipment-step mapping to cover both processes with shared equipment |
| 2026-03-02 | Added Work Orders section: 3 work orders (PENDING, IN_PROGRESS, COMPLETED) linking orders to shop floor with timing and priority |
| 2026-03-02 | Expanded Parts section: added Great Lakes parts (triggered CAPA), linked all parts to work orders |
| 2026-03-02 | Expanded Approval Templates with full schema: 5 templates, default approvers/groups, flow types, SLAs |
| 2026-03-02 | Added 3 Approval Requests: CAPA closure (PENDING), Work Instruction (APPROVED), Disposition (APPROVED) |
| 2026-03-02 | Added Approval Workflow Demo Scenarios showing how to demo each flow type |
| 2026-03-02 | Added User Persona Demo Experiences: detailed demo needs and scripts for each role |
| 2026-03-02 | Added TenantGroup Assignments mapping users to groups for RBAC demonstration |
| 2026-03-02 | Expanded Notification Preferences for all internal users (Mike, Jennifer) |
| 2026-03-02 | Fixed INJ-0042-019 status: Changed from ambiguous "rework approved" to explicitly at Rework step after Nozzle Inspection failure |
| 2026-03-02 | Added Step Execution History section for reworked parts showing complete workflow path (INJ-0038-003 example) |
| 2026-03-02 | Added Component Grading Edge Clarification: All grades (A/B/C) proceed to Cleaning; "rework queue" is inventory status, not a DAG branch |
| 2026-03-02 | Added Model Field Specifications: CAPA, FiveWhys, QuarantineDisposition structures for seeder implementation |
| 2026-03-02 | Fixed SPC measurement count: Clarified as "summary of 60 total measurements" with reference to full data in SPC Data section |
| 2026-03-02 | Added Equipment Calibration Status Behavior: Defines blocking behavior for overdue equipment, supervisor override flow |
| 2026-03-02 | **CRITICAL FIX:** Updated CAPA model fields - `title`→`problem_statement`, `priority`→`severity`, `opened_by`→`initiated_by`, `opened_date`→`initiated_date` |
| 2026-03-02 | **CRITICAL FIX:** Added RcaRecord as separate model between CAPA and FiveWhys (CAPA → RcaRecord → FiveWhys) |
| 2026-03-02 | **CRITICAL FIX:** Updated FiveWhys to include both `why_X_question` AND `why_X_answer` fields, not just answers |
| 2026-03-02 | **CRITICAL FIX:** Added `CAPA.quality_reports` M2M field - direct link to triggering QualityReports, not just text reference |
| 2026-03-02 | **CRITICAL FIX:** Added StepExecution model documentation - records part movement through steps with visit_number for rework tracking |
| 2026-03-02 | **CRITICAL FIX:** Added StepExecutionMeasurement model - measurements recorded during step execution, linked to MeasurementDefinition |
| 2026-03-02 | **CRITICAL FIX:** Added HarvestedComponent → Part → AssemblyUsage traceability chain with allocation table example |
| 2026-03-02 | **CRITICAL FIX:** Updated QuarantineDisposition model - `current_state` not `status`, approval handled via separate ApprovalRequest |
| 2026-03-02 | Updated CAPA-2024-003 data table to use correct field names and added RcaRecord/FiveWhys with questions |
| 2026-03-02 | **HIGH FIX:** Added EquipmentUsage model documentation - equipment-step linking is via actual usage logging, not a requirements through model |
| 2026-03-02 | **HIGH FIX:** Added Step decision_type documentation (qa_result, measurement, manual) and StepEdge condition fields (condition_measurement, condition_operator, condition_value) |
| 2026-03-02 | **HIGH FIX:** Added max_visits enforcement explanation - visit_number on StepExecution, escalation edge when limit exceeded |
| 2026-03-02 | **HIGH FIX:** Added explicit QualityReport → CAPA linkage table with 5 specific QRs to link via `capa.quality_reports.add(...)` |
| 2026-03-02 | **CRITICAL FIX:** Added max_visits escalation scenario - INJ-0038-005 scrapped after failing Nozzle Inspection twice |
| 2026-03-02 | **CRITICAL FIX:** Added CAPA lifecycle coverage - CAPA-2024-001 (CLOSED with verification) and CAPA-2024-005 (OPEN, just initiated) |
| 2026-03-02 | **CRITICAL FIX:** Added rejected approval - APR-2024-0010 (Training Certification rejected with remediation feedback) |
| 2026-03-02 | **HIGH FIX:** Added Sampling model schema - SamplingRuleSet, SamplingRule, SamplingTriggerState, SamplingAuditLog fields |
| 2026-03-02 | **HIGH FIX:** Added SPC Rule 1 violation - Measurement #61 (131.2 mL/min) beyond UCL causing INJ-0042-017 quarantine |
| 2026-03-02 | **HIGH FIX:** Added training expiration scenarios - Mike's NOZ-CERT expiring in 7 days, Dave Wilson's FLOW-CERT expired 15 days ago (blocking) |
| 2026-03-02 | **HIGH FIX:** Added new user Dave Wilson (Operator) for expired training demo scenario |
| 2026-03-02 | **HIGH FIX:** Added First Piece Inspection (FPI) examples - is_fpi and fpi_status distribution across parts/steps |
| 2026-03-02 | **HIGH FIX:** Added FPI failure scenario - INJ-0042-025 with fpi_status=failed blocking Assembly step production |
| 2026-03-02 | **HIGH FIX:** Added supervisor equipment override approval - APR-2024-0016 for TW-025 calibration override |
| 2026-03-02 | **HIGH FIX:** Added QuarantineDisposition examples - QD-2024-0001 (USE_AS_IS with customer concession), QD-2024-0002 (REWORK), QD-2024-0003 (OPEN/pending) |
| 2026-03-02 | **MEDIUM FIX:** Added searchable document content for WI-1002 - enables AI "Ask Anything" demo queries about nozzle inspection |
| 2026-03-02 | **HIGH FIX:** Added searchable document content for WI-1001 (Disassembly) and WI-1003 (Flow Test) - complete AI search coverage |
| 2026-03-02 | **HIGH FIX:** Added INJ-0038-009 complex multi-step rework history - failed Nozzle Inspection then Flow Testing across multiple rework cycles |
| 2026-03-04 | Added CapaTaskAssignee model and completion_mode field - multi-person task assignments with ALL_ASSIGNEES/ANY_ASSIGNEE modes |
| 2026-03-04 | Added FPIRecord model seeding - separate table tracking FPI approvals with result, verifier, and notes |
