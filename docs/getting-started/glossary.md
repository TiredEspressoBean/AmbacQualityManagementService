# Glossary

Reference guide for terms and concepts used in uqmes.

## A

### Approval
A formal review and sign-off on a document, process, or action. Approvals require electronic signature (password verification) and are logged in the audit trail.

### Approval Template
A configured workflow defining who must approve something, in what order, and what type of approval is required.

### Audit Trail
A chronological record of all changes made in the system. Every create, update, and delete action is logged with the user, timestamp, and what changed.

## B

### Baseline (SPC)
A frozen set of control limits. While a baseline is active the chart is in
monitoring mode and new data is judged against the fixed limits instead of
recalculating them.

### Batch Execution
The record for a substep that runs once for a whole batch of parts rather than
per part — a heat-treat cycle, a plating bath, a wash tank.

## C

### Calibration
The process of verifying and adjusting equipment to ensure accurate measurements. uqmes tracks calibration due dates and records.

### CAPA (Corrective and Preventive Action)
A formal quality process for investigating problems, identifying root causes, implementing fixes, and preventing recurrence. Follows the 8D methodology.

### Capture
Something a substep asks the operator to record — a measurement, a photo, a
scan, a signature, a choice. The capture type determines what the operator sees
and where the result is stored.

### Change Control
The governed path for changing an approved process, via PCR, PCO, and PCN. See
[Change Control](../workflows/change-control/overview.md).

### Component Grading
The process of evaluating harvested components from disassembled cores. Grades determine routing: A (use as-is), B (rework needed), C (marginal), Scrap (dispose).

### Control Plan
A document describing the quality controls for a manufacturing process, including measurements, frequencies, and reaction plans.

### Core
In remanufacturing, a used unit received for rebuild (e.g., a used fuel injector). Cores are disassembled into components, graded, and tracked for core credit/exchange programs.

### Customer
An external company or organization that places orders. Customers can have portal access to view their order status.

## D

### Digital Work Instructions (DWI)
The substep layer beneath a step, providing rich work instructions and
structured data capture. See [Digital Work
Instructions](../workflows/dwi/overview.md).

### Dispatch
The scheduling pass that assigns an operator to each attended operation, taking
the machine schedule as given. Assigns per lot, not per piece, and only to
operators qualified for the step.

### Disposition
The decision made about a non-conforming part: Use As Is, Rework, Scrap, or Return to Vendor (RTV).

### Document
A controlled file (PDF, drawing, specification) with revision tracking and optional approval workflow.

### Document Type
A category for documents (e.g., Work Instruction, Specification, Certificate) that may have different retention and approval requirements.

## E

### ECCN (Export Control Classification Number)
A code identifying items subject to export controls under the Export Administration Regulations (EAR).

### Electronic Signature
A secure method of signing records that requires password verification and is linked to a unique user identity. Compliant with 21 CFR Part 11.

### Equipment
Physical machines or tools used in manufacturing. Equipment records track calibration status, usage, and maintenance.

### Error Type
A category of defect or non-conformance (e.g., Dimensional, Visual, Functional) used for classification and analysis.

## F

### First Piece Inspection (FPI)
A quality check performed on the first part of a production run to verify setup before proceeding with the full batch.

### FPY (First Pass Yield)
A quality metric: the percentage of parts that pass all steps without rework or rejection.

## G

### Group
A collection of users with shared permissions. Users are assigned to groups, and groups have permissions.

## H

### Harvested Component
A part recovered during disassembly of a core in remanufacturing. Components are graded (A/B/C/Scrap) and either accepted into inventory or scrapped. Example: a nozzle harvested from a used injector.

### Heat Map
A visual representation showing defect frequency overlaid on a 3D model or part diagram.

## I

### ITAR (International Traffic in Arms Regulations)
US export control regulations for defense articles. ITAR-controlled parts require special handling and US Person verification.

## L

### Legal Hold
A preservation order that prevents records from being deleted, typically for litigation or audit purposes.

### Lot Cohesion
The rule that parts which have not been split advance together — all parts at
the same work order and step move on, or none do.

### Lot Number
An identifier grouping parts manufactured together under the same conditions, used for traceability.

## M

### Measurement
A recorded value from an inspection, including the measured value, specification limits, and pass/fail status.

### Measurement Definition
The specification for a measurement: what to measure, target value, tolerances, and units.

### MES (Manufacturing Execution System)
Software that tracks and documents the transformation of raw materials into finished goods.

## N

### N/A Reason Code
The coded reason an operator gives when marking a substep not-applicable. Both
the code and a note are required, and both stay in the part's record.

### NCR (Non-Conformance Report)
See **Quality Report**. A document recording that a part or material doesn't meet specifications.

## O

### Operator
A user role for production floor workers who move parts through steps and record data.

### Order
A customer request to manufacture or process parts. Contains one or more parts and associated work orders.

### Outside Processing (OSP)
Sending parts to a subcontract vendor for an operation performed off-site, and
tracking them until they return. See [Outside
Processing](../workflows/supply/outside-processing.md).

## P

### Part
An individual item being tracked through production. Each part has a unique identifier, type, and status.

### Part Approval
A PPAP or FAI approval recording that a supplier is approved to produce a
specific part type. Receiving holds lots from unapproved (part type, supplier)
pairs.

### Part Type
A template defining the attributes and default process for a category of parts.

### PCR / PCO / PCN
Process Change Request, Order, and Notice — the three artifacts of
[change control](../workflows/change-control/overview.md). The request proposes
a change, the order authorises it, the notice announces it.

### Process
A defined manufacturing workflow consisting of sequential steps. Processes can have versioning and require approval.

## Q

### QA (Quality Assurance)
The department or function responsible for ensuring products meet quality standards.

### QMS (Quality Management System)
The organizational structure, procedures, and resources for managing quality. uqmes is a QMS software.

### Quality Report
A record documenting a non-conformance or quality issue with a part. Requires disposition and may trigger CAPA.

### Quarantine
A status indicating a part is held for quality review and cannot proceed through production.

## R

### RCA (Root Cause Analysis)
A systematic process for identifying the underlying cause of a problem, often part of CAPA.

### Remanufacturing (Reman)
The process of rebuilding used products to original specifications. Involves receiving cores, disassembly, component grading, rebuilding, and testing. Common in automotive/diesel industries (fuel injectors, turbochargers, etc.).

### Retention
The period for which records must be kept for regulatory compliance before they can be deleted.

### Revision
A version of a document. When documents change, new revisions are created while old revisions are preserved.

### RTV (Return to Vendor)
A disposition decision to return non-conforming material to the supplier.

## S

### Sampling
Inspecting a subset of parts rather than 100%, based on statistical rules (e.g., AQL sampling).

### Sampling Rule
A configuration defining when and how sampling applies, based on part type, history, or other criteria.

### Serial Number
A unique identifier for an individual part, used for full traceability.

### Shift Note
A handover note shown to the floor on the operator home screen, optionally
requiring acknowledgment. See [Shift Notes](../workflows/tracking/shift-notes.md).

### Skip-Lot
A sampling technique where lots are periodically skipped for inspection based on quality history.

### SPC (Statistical Process Control)
Using statistical methods to monitor and control a process. SPC charts show whether a process is stable and capable.

### Step
A single operation in a process (e.g., "Machining," "Inspection," "Assembly"),
also called an **Op**. Parts move through steps sequentially. A step's work
instructions are made up of substeps.

### Step Transition
The event of a part moving from one step to the next. Transitions are logged
with timestamps and user information. They happen automatically when a step's
requirements are satisfied — there is no manual "move to next step" action.

### Substep
The unit of work instruction within a step — one thing the operator does and
records. Substeps gate advancement: a part cannot leave a step until its
required substeps are satisfied.

## T

### Tenant
An organization using uqmes. Each tenant has isolated data and independent configuration.

### Training Matrix
A grid of operator competency against training types, showing role gaps and
which skills only one person can cover. Also drives scheduling, since dispatch
only assigns qualified operators. See [Training
Matrix](../workflows/tracking/training-matrix.md).

### Training Record
A record that a user has completed training on a topic, including date, trainer, and verification.

## U

### US Person
Under ITAR, a US citizen, permanent resident, or protected individual who can access ITAR-controlled information.

## V

### Verification
Confirming that an action was effective. In CAPA, verification ensures corrective actions solved the problem.

## W

### Work Center
A resource — a machine, bench, or cell — that work is scheduled onto.

### Work Instruction
The directions for performing an operation, built from **substeps** that the
operator works through one at a time. See [Digital Work
Instructions](../workflows/dwi/overview.md).

### Work Order
A production order linking a customer order to a process. Tracks which step each part is at and overall progress.

---

## Acronyms Quick Reference

| Acronym | Meaning |
|---------|---------|
| AQL | Acceptable Quality Level |
| CAPA | Corrective and Preventive Action |
| DWI | Digital Work Instructions |
| ECCN | Export Control Classification Number |
| FAI | First Article Inspection |
| FPI | First Piece Inspection |
| FPY | First Pass Yield |
| ITAR | International Traffic in Arms Regulations |
| MES | Manufacturing Execution System |
| NCR | Non-Conformance Report |
| Op | Operation (another name for a Step) |
| OSP | Outside Processing |
| PCN | Process Change Notice |
| PCO | Process Change Order |
| PCR | Process Change Request |
| PPAP | Production Part Approval Process |
| QA | Quality Assurance |
| QMS | Quality Management System |
| RCA | Root Cause Analysis |
| Reman | Remanufacturing |
| RTV | Return to Vendor |
| SPC | Statistical Process Control |
| SSO | Single Sign-On |
