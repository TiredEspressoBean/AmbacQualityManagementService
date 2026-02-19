# Glossary

Reference guide for terms and concepts used in Ambac Tracker.

## A

### Approval
A formal review and sign-off on a document, process, or action. Approvals require electronic signature (password verification) and are logged in the audit trail.

### Approval Template
A configured workflow defining who must approve something, in what order, and what type of approval is required.

### Audit Trail
A chronological record of all changes made in the system. Every create, update, and delete action is logged with the user, timestamp, and what changed.

## C

### Calibration
The process of verifying and adjusting equipment to ensure accurate measurements. Ambac Tracker tracks calibration due dates and records.

### CAPA (Corrective and Preventive Action)
A formal quality process for investigating problems, identifying root causes, implementing fixes, and preventing recurrence. Follows the 8D methodology.

### Control Plan
A document describing the quality controls for a manufacturing process, including measurements, frequencies, and reaction plans.

### Customer
An external company or organization that places orders. Customers can have portal access to view their order status.

## D

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

### Heat Map
A visual representation showing defect frequency overlaid on a 3D model or part diagram.

## I

### ITAR (International Traffic in Arms Regulations)
US export control regulations for defense articles. ITAR-controlled parts require special handling and US Person verification.

## L

### Legal Hold
A preservation order that prevents records from being deleted, typically for litigation or audit purposes.

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

### NCR (Non-Conformance Report)
See **Quality Report**. A document recording that a part or material doesn't meet specifications.

## O

### Order
A customer request to manufacture or process parts. Contains one or more parts and associated work orders.

### Operator
A user role for production floor workers who move parts through steps and record data.

## P

### Part
An individual item being tracked through production. Each part has a unique identifier, type, and status.

### Part Type
A template defining the attributes and default process for a category of parts.

### Process
A defined manufacturing workflow consisting of sequential steps. Processes can have versioning and require approval.

## Q

### QA (Quality Assurance)
The department or function responsible for ensuring products meet quality standards.

### QMS (Quality Management System)
The organizational structure, procedures, and resources for managing quality. Ambac Tracker is a QMS software.

### Quality Report
A record documenting a non-conformance or quality issue with a part. Requires disposition and may trigger CAPA.

### Quarantine
A status indicating a part is held for quality review and cannot proceed through production.

## R

### Retention
The period for which records must be kept for regulatory compliance before they can be deleted.

### Revision
A version of a document. When documents change, new revisions are created while old revisions are preserved.

### RCA (Root Cause Analysis)
A systematic process for identifying the underlying cause of a problem, often part of CAPA.

### RTV (Return to Vendor)
A disposition decision to return non-conforming material to the supplier.

## S

### Sampling
Inspecting a subset of parts rather than 100%, based on statistical rules (e.g., AQL sampling).

### Sampling Rule
A configuration defining when and how sampling applies, based on part type, history, or other criteria.

### Serial Number
A unique identifier for an individual part, used for full traceability.

### Skip-Lot
A sampling technique where lots are periodically skipped for inspection based on quality history.

### SPC (Statistical Process Control)
Using statistical methods to monitor and control a process. SPC charts show whether a process is stable and capable.

### Step
A single operation in a process (e.g., "Machining," "Inspection," "Assembly"). Parts move through steps sequentially.

### Step Transition
The event of a part moving from one step to the next. Transitions are logged with timestamps and user information.

## T

### Tenant
An organization using Ambac Tracker. Each tenant has isolated data and independent configuration.

### Training Record
A record that a user has completed training on a topic, including date, trainer, and verification.

## U

### US Person
Under ITAR, a US citizen, permanent resident, or protected individual who can access ITAR-controlled information.

## V

### Verification
Confirming that an action was effective. In CAPA, verification ensures corrective actions solved the problem.

## W

### Work Instruction
A document providing step-by-step directions for performing an operation.

### Work Order
A production order linking a customer order to a process. Tracks which step each part is at and overall progress.

---

## Acronyms Quick Reference

| Acronym | Meaning |
|---------|---------|
| AQL | Acceptable Quality Level |
| CAPA | Corrective and Preventive Action |
| ECCN | Export Control Classification Number |
| FAI | First Article Inspection |
| FPI | First Piece Inspection |
| FPY | First Pass Yield |
| ITAR | International Traffic in Arms Regulations |
| MES | Manufacturing Execution System |
| NCR | Non-Conformance Report |
| QA | Quality Assurance |
| QMS | Quality Management System |
| RCA | Root Cause Analysis |
| RTV | Return to Vendor |
| SPC | Statistical Process Control |
| SSO | Single Sign-On |
