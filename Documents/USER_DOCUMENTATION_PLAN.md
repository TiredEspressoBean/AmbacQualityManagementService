# User Documentation Plan

> **Purpose:** Define the structure and content for Ambac Tracker user documentation (MkDocs)

## Audience Segments

| Role | Primary Tasks | Documentation Needs |
|------|---------------|---------------------|
| **Operator** | Move parts through steps, record measurements, flag issues | Quick workflows, mobile-friendly guides |
| **QA Inspector** | Review parts, approve/reject, create NCRs, sampling | Quality workflows, inspection procedures |
| **QA Manager** | CAPA management, approval workflows, reporting | Analysis features, compliance reporting |
| **Admin** | User management, process configuration, system setup | Configuration guides, permissions |
| **Customer (Portal)** | View order status, download documents | Portal-specific guide |

---

## Documentation Structure

### 1. Getting Started
*Goal: New user productive in 15 minutes*

- [ ] **Welcome & Overview** - What is Ambac Tracker, core concepts
- [ ] **First Login** - SSO vs password, profile setup
- [ ] **Navigation Tour** - Sidebar, pages, search
- [ ] **Your First Order** - End-to-end walkthrough creating an order, adding parts, tracking progress
- [ ] **Glossary** - Terms: Order, Work Order, Part, Step, Process, NCR, CAPA, Disposition

### 2. Core Workflows
*Goal: Day-to-day task documentation*

#### Orders & Parts
- [ ] **Creating Orders** - New order form, required fields, customer assignment
- [ ] **Adding Parts to Orders** - Manual entry, bulk add, part types
- [ ] **Viewing Order Status** - Progress tracking, step distribution chart
- [ ] **Order Documents** - Attaching files, document types

#### Parts Tracking (The Tracker)
- [ ] **Tracker Overview** - Understanding the card-based workflow
- [ ] **Moving Parts Forward** - Incrementing steps, batch operations
- [ ] **Recording Measurements** - Measurement definitions, entering data
- [ ] **Flagging Issues** - Error types, quarantine flow
- [ ] **Part History** - Viewing audit trail for a part

#### Work Orders
- [ ] **Work Order Basics** - Relationship to orders, processes, priority
- [ ] **Assigning Work Orders** - Equipment, operators
- [ ] **Work Order Progress** - Step completion, time tracking
- [ ] **First Piece Inspection** - FPI workflow when enabled

#### Quality Control
- [ ] **Quality Reports (NCRs)** - Creating, required fields, workflow
- [ ] **Dispositions** - Use As Is, Rework, Scrap, RTV decisions
- [ ] **Quarantine Management** - Quarantine queue, releasing parts
- [ ] **Sampling Rules** - How sampling works, rule types, skip-lot

#### CAPA
- [ ] **CAPA Overview** - When to create, 8D methodology
- [ ] **Creating a CAPA** - Linking to NCRs, root cause analysis
- [ ] **CAPA Tasks** - Assigning corrective actions, due dates
- [ ] **Verification & Closure** - Effectiveness verification, approval

#### Documents
- [ ] **Document Library** - Browsing, searching, filtering
- [ ] **Uploading Documents** - File types, metadata, revision control
- [ ] **Document Revisions** - Creating new revisions, approval workflow
- [ ] **Document Approval** - Submitting for approval, approval templates
- [ ] **Linking Documents** - Associating with orders, parts, processes

### 3. Analysis & Reporting
*Goal: Getting insights from data*

- [ ] **Dashboard Overview** - KPIs, charts, filtering
- [ ] **SPC Charts** - Control charts, Cpk, interpreting results
- [ ] **Defect Analysis** - Pareto charts, trend analysis
- [ ] **Heat Maps** - 3D annotation visualization
- [ ] **Exporting Data** - CSV export, report generation
- [ ] **Audit Trail** - Viewing system-wide audit logs

### 4. 3D Models & Annotations
*Goal: Visual quality tracking*

- [ ] **Uploading 3D Models** - Supported formats, model setup
- [ ] **Viewing Models** - Navigation, zoom, rotate
- [ ] **Creating Annotations** - Placing points, annotation types
- [ ] **Heat Map Visualization** - Error frequency overlay
- [ ] **Part Annotator** - Recording defects on specific parts

### 5. Administration Guide
*Goal: System configuration for admins*

#### User Management
- [ ] **Adding Users** - Invitations, manual creation
- [ ] **User Roles & Groups** - Permissions overview, built-in groups
- [ ] **Assigning Permissions** - Group membership, role-based access
- [ ] **Deactivating Users** - Offboarding, data retention

#### Process Configuration
- [ ] **Processes Overview** - What is a process, versioning
- [ ] **Creating Processes** - Steps, sequence, branching
- [ ] **Step Configuration** - Step types, requirements, measurements
- [ ] **Measurement Definitions** - Nominal, tolerances, units
- [ ] **Process Approval** - Review workflow for process changes

#### System Setup
- [ ] **Companies & Customers** - Multi-customer setup
- [ ] **Part Types** - Creating, attributes, defaults
- [ ] **Equipment** - Adding equipment, calibration tracking
- [ ] **Equipment Types** - Categories, calibration intervals
- [ ] **Error Types** - Defect categories for reporting
- [ ] **Document Types** - Categories, retention settings
- [ ] **Approval Templates** - Configuring approval workflows

#### Sampling Configuration
- [ ] **Sampling Rules** - Creating rules, criteria
- [ ] **Rule Types** - AQL, skip-lot, 100% inspection
- [ ] **Sampling Rule Sets** - Grouping rules, priority

### 6. Compliance Features
*Goal: Audit-readiness documentation*

- [ ] **Audit Trails** - What's logged, how to access
- [ ] **Electronic Signatures** - How signatures work, password verification
- [ ] **Document Control** - Revision history, approval records
- [ ] **Export Controls** - ITAR fields, US Person verification (admin)
- [ ] **Data Export for Audits** - Generating compliance reports

### 7. Integrations
*Goal: Connecting to other systems*

- [ ] **SSO / Azure AD** - Setup, user provisioning
- [ ] **HubSpot Integration** - Deal sync, order creation from deals
- [ ] **API Overview** - REST API basics, authentication
- [ ] **Webhooks** - Event notifications (if applicable)

### 8. Troubleshooting & FAQ
*Goal: Self-service problem solving*

- [ ] **Common Issues** - Login problems, permission errors, sync issues
- [ ] **FAQ** - Frequently asked questions by role
- [ ] **Error Messages** - What they mean, how to resolve
- [ ] **Getting Help** - Support contact, feedback

---

## Content Guidelines

### Writing Style
- Active voice, present tense
- Task-oriented headings ("Creating an Order" not "Order Creation")
- Step-by-step numbered lists for procedures
- Screenshots with annotations for complex UI
- Callouts for warnings, tips, notes

### Standard Page Structure
```markdown
# Page Title

Brief description of what this page covers and when you'd need it.

## Prerequisites
- What you need before starting (permissions, prior setup)

## Steps

1. First step with clear action
2. Second step
   - Sub-detail if needed
3. Third step

## Example
Concrete example with screenshot

## Related
- Links to related documentation
```

### Screenshot Guidelines
- Capture at consistent resolution (1280px width)
- Highlight relevant UI elements with boxes/arrows
- Blur/redact sensitive data in examples
- Update screenshots when UI changes (track in changelog)

---

## Priority Order

### Phase 1: MVP Documentation (Launch-Critical)
1. Getting Started (all)
2. Core Workflows: Orders & Parts
3. Core Workflows: Parts Tracking
4. Core Workflows: Quality Control (NCR, Disposition)
5. Glossary

### Phase 2: Complete Coverage
6. Work Orders
7. CAPA
8. Documents
9. Administration Guide (Users, Processes)

### Phase 3: Advanced Features
10. 3D Models & Annotations
11. SPC & Analysis
12. Sampling Configuration
13. Compliance Features
14. Integrations

### Phase 4: Polish
15. Troubleshooting & FAQ (build from support tickets)
16. Video tutorials for complex workflows
17. Role-specific quick reference cards (PDF)

---

## Technical Setup

### MkDocs Configuration
- Theme: Material for MkDocs
- Search: Built-in search enabled
- Navigation: Expandable sections
- Plugins:
  - `search`
  - `awesome-pages` (auto-nav from folder structure)
  - `glightbox` (image lightbox)

### Hosting
- **Option A:** GitHub Pages (free, `mkdocs gh-deploy`)
- **Option B:** Subdomain docs.ambactracker.com behind Caddy
- **Option C:** ReadTheDocs (free tier, auto-build from repo)

### Maintenance
- Documentation repo separate or in monorepo `/docs` folder
- Screenshots stored in `docs/assets/images/`
- Review documentation quarterly for accuracy
- Track UI changes that require doc updates in changelog

---

## Metrics (Post-Launch)

- Most viewed pages (identify gaps)
- Search queries with no results (missing content)
- Time on page (engagement)
- Support ticket reduction (success metric)

---

## Notes

- Consider in-app contextual help tooltips that link to docs
- API reference can be auto-generated from OpenAPI schema
- Customer-specific documentation (if needed) via separate MkDocs instance or gated section
