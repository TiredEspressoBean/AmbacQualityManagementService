# Ambac Quality Management System - Full Development Roadmap

**Last Updated:** February 18, 2026

This document provides a complete view of all features: completed, in progress, needed, nice-to-have, and future aspirations.

---

## Development Context

**Timeline:** [TO BE FILLED]
**Team Size:** [TO BE FILLED]
**Starting Point:** [TO BE FILLED - What technologies were you familiar with vs. learned from scratch?]
**Architecture:** Django 5.1 + React 19 + PostgreSQL + pgvector + LangGraph + Ollama + Railway

**Technologies Learned During Development:**
[TO BE FILLED - List technologies you learned while building this project]

**Hardest Technical Challenges:**
[TO BE FILLED - What were the 3-5 hardest technical problems you solved? Examples: GPU shaders, token forwarding, sampling algorithms, etc.]

**Architecture Evolution:**
[TO BE FILLED - How did the architecture change over time? What major pivots or redesigns happened?]

---

## Legend

- ✅ **Completed** - Production ready and deployed
- 🔶 **In Progress** - Currently being developed
- 🔴 **Needed** - Critical for compliance, operations, or customer requirements
- 🟡 **Nice to Have** - Valuable improvements that enhance efficiency
- 🟢 **Yacht Problems** - Advanced features for when everything else is done

---

## Table of Contents

1. [Manufacturing Operations & Traceability](#1-manufacturing-operations--traceability)
2. [Quality Control & Inspection](#2-quality-control--inspection)
3. [3D Visual Quality Management](#3-3d-visual-quality-management)
4. [AI Digital Coworker (LangGraph)](#4-ai-digital-coworker-langgraph)
5. [Document Control & Management](#5-document-control--management)
6. [Business Integration & CRM](#6-business-integration--crm)
7. [User Management & Authentication](#7-user-management--authentication)
8. [Access Control & Security](#8-access-control--security)
9. [Audit Trail & Compliance](#9-audit-trail--compliance)
10. [Notifications & Alerts](#10-notifications--alerts)
11. [Data Import/Export](#11-data-importexport)
12. [QMS Compliance Features](#12-qms-compliance-features)
13. [MES-Lite Features](#13-mes-lite-features)
14. [Analytics & Dashboards](#14-analytics--dashboards)
15. [Bug Fixes & Technical Debt](#15-bug-fixes--technical-debt)
16. [Security Hardening (Production Readiness)](#16-security-hardening-production-readiness)

---

## 1. Manufacturing Operations & Traceability

### Parts Tracking

- ✅ **Completed:** Serial number tracking with unique ERP_id
- ✅ **Completed:** 11 distinct part statuses (Pending, In Progress, Awaiting QA, Quarantined, Completed, Scrapped, etc.)
- ✅ **Completed:** Automatic step transition logging with operator attribution
- ✅ **Completed:** Full version history via django-auditlog

### Work Order Management

- ✅ **Completed:** Batch production with quantity tracking
- ✅ **Completed:** ERP integration via external identifiers
- ✅ **Completed:** CSV import for bulk work order creation
- ✅ **Completed:** Real-time progress tracking (actual vs. expected completion)

### Process & Workflow Management

- ✅ **Completed:** Configurable multi-step manufacturing workflows per part type
- ✅ **Completed:** Step definitions with duration estimates, descriptions, operator instructions
- ✅ **Completed:** Process versioning
- ✅ **Completed:** Linear workflows
- ✅ **Completed:** Acyclic graph workflows for branching/conditional paths (StepEdge model)
- ✅ **Completed:** Decision nodes (pass/fail routing, conditional steps)
- 🟡 **Nice to Have:** Parallel step execution
- ✅ **Completed:** Process flow visualization and editing UI (ProcessFlowPage)

### Part Types & Design Management

- ✅ **Completed:** Product versioning for design revisions
- ✅ **Completed:** ID prefix system for auto-generated part serial numbers
- ✅ **Completed:** Process assignment per part type
- ✅ **Completed:** Document attachments via generic relations

---

## 2. Quality Control & Inspection

### Quality Reporting

- ✅ **Completed:** Per-part inspections with individual quality reports
- ✅ **Completed:** Configurable measurement definitions per step (nominal, tolerance, units)
- ✅ **Completed:** Actual measurement results with pass/fail validation
- ✅ **Completed:** Support for numeric measurements and visual pass/fail checks
- ✅ **Completed:** Operator & equipment logging
- ✅ **Completed:** Status recording (Pass, Fail, Pending) with detailed notes

### Statistical Sampling System

- ✅ **Completed:** Rule-based sampling engine:
    - Periodic sampling (every Nth part)
    - Percentage sampling (random X% rate)
    - Threshold sampling (first N parts, then reduce frequency)
    - Combined rules (stack multiple rules)
- ✅ **Completed:** Sampling rule sets per part type, process, and step
- ✅ **Completed:** Priority-based rule ordering
- ✅ **Completed:** Automatic fallback when defect thresholds exceeded
- ✅ **Completed:** Configurable fallback duration
- ✅ **Completed:** State tracking per work order and step
- ✅ **Completed:** Audit logging with deterministic hash-based sampling decisions
- ✅ **Completed:** Sampling analytics tracking (compliance rate, defects found)
- 🟡 **Nice to Have:** Risk-based sampling - higher inspection rates for critical characteristics
- 🟡 **Nice to Have:** Supplier-driven sampling - adjust rules per supplier performance
- 🟢 **Yacht:** Machine learning-optimized sampling - adjust rules based on historical defect patterns

### Equipment Management

**Note:** Many companies outsource calibration to ISO 17025 accredited labs. Focus on tracking due dates and storing certificates, not performing calibrations.

- ✅ **Completed:** Equipment registry with type classification
- ✅ **Completed:** Usage logging per part and step
- ✅ **Completed:** Equipment-specific error tracking
- ✅ **Completed:** CalibrationRecord model with calibration_date, next_due_date, result, certificate storage
- ✅ **Completed:** Calibration records editor page (CalibrationRecordsPage, CalibrationDashboardPage)
- 🔶 **Needs Logic:** Calibration due date alerting (Celery beat task)
- 🟡 **Nice to Have:** Out-of-calibration equipment lockout (prevent use in quality reports)
- 🟡 **Nice to Have:** External calibration vendor tracking
- 🟡 **Nice to Have:** Measurement uncertainty tracking

### Error Classification

- ✅ **Completed:** Predefined error types per part type
- ✅ **Completed:** Examples & descriptions for each error type
- ✅ **Completed:** Quality report integration

### Non-Conformance Management (NCR)

- ✅ **Completed:** QuarantineDisposition model with basic NCR workflow
- ✅ **Completed:** Workflow states (Open, In Progress, Closed)
- ✅ **Completed:** Disposition types (Rework, Scrap, Use As-Is, Return to Supplier)
- ✅ **Completed:** Auto-creation on failed quality reports (via Django signal)
- ✅ **Completed:** Assignment to QA staff with notifications
- ✅ **Completed:** Rework attempt tracking per step
- ✅ **Completed:** Resolution notes and completion timestamps
- ✅ **Completed:** Document attachments for evidence/photos
- ✅ **Completed:** Links to multiple quality reports
- ✅ **Completed:** Full CAPA workflow (see QMS Compliance Features section)

---

## 3. 3D Visual Quality Management

### 3D Model Management

- ✅ **Completed:** CAD file support (GLB, GLTF, OBJ, STEP)
- ✅ **Completed:** Auto-conversion: STEP/STP files automatically convert to GLB (via cascadio library)
- ✅ **Completed:** Part type linking
- ✅ **Completed:** Process step models (optional intermediate states)
- ✅ **Completed:** Unique constraint (one model per part_type + step combination)

### Interactive Defect Annotation Tool

- ✅ **Completed:** Click-to-annotate interface for marking defect locations
- ✅ **Completed:** 3D position tracking (X, Y, Z coordinates)
- ✅ **Completed:** Defect attributes (type, severity, measurement value, notes)
- ✅ **Completed:** Defect types: Crack, Burn, Porosity, Overspray, etc.
- ✅ **Completed:** Severity levels: Low, Medium, High, Critical
- ✅ **Completed:** Two modes: Navigate (orbit camera) and Annotate (click to place markers)
- ✅ **Completed:** Batch saving (create multiple annotations, save all at once)

### Heat Map Visualization

- ✅ **Completed:** GPU-accelerated WebGL visualization with custom GLSL shaders
- ✅ **Completed:** Real-time rendering on graphics card
- ✅ **Completed:** Color gradient: Blue (low) → Cyan → Green → Yellow → Red (high)
- ✅ **Completed:** Inverse distance falloff (heat spreads from annotation points)
- ✅ **Completed:** Adjustable parameters:
    - Radius (0.1-2.0): How far heat spreads
    - Intensity (0-2.0): Heat strength multiplier
    - Toggle on/off for comparison
- ✅ **Completed:** Performance: Supports up to 50 annotations per model without lag
- ✅ **Completed:** Basic diffuse lighting for depth perception

### Workflow Integration

- ✅ **Completed:** 3D annotation workflow integration
    - `requires_3d_annotation` flag on error types to indicate which need 3D annotation
    - AnnotatorPage filters quality reports to show only those needing annotation
    - Frontend-backend data flow for annotation creation/retrieval
    - Auto-link annotations to quality reports (user selects reports upfront, all annotations link automatically)
- 🔴 **Needed:** Block part advancement until required annotations complete (backend enforcement)
- 🔴 **Needed:** UI indicator for pending annotations (badge/alert on parts, work orders, quality reports needing annotation)
- 🟡 **Nice to Have:** Timestamp-based or configuration-driven annotation requirements
- 🟡 **Nice to Have:** Pattern recognition AI - detect recurring defect locations and suggest root causes
- 🟡 **Nice to Have:** Multi-part comparison - overlay heat maps from multiple parts to identify systemic issues

---

## 4. AI Digital Coworker (LangGraph)

### Core Agent

- ✅ **Completed:** ReAct (Reasoning and Action) agent pattern
- ✅ **Completed:** Simple graph structure: Agent Node ↔ Tools Node
- ✅ **Completed:** Streaming responses to React frontend via assistant-ui
- ✅ **Completed:** Local LLM deployment (Ollama llama3.1:8b)
- ✅ **Completed:** Alternative model support (Claude, GPT, Fireworks AI)
- ✅ **Completed:** Embeddings via nomic-embed-text (Ollama)
- ✅ **Completed:** Shared Docker network deployment

### Tools (5 Core Tools)

- ✅ **Completed:** Database Query Tool (query_database)
    - Safe, read-only ORM queries
    - Whitelisted models (20+ models)
    - Whitelisted operations (exact, contains, icontains, gt, lte, in, range, date filters)
    - Relationship traversals
    - Aggregations (count)
    - Field validation, operation validation, max 100 results per query
- ✅ **Completed:** Semantic Document Search (search_documents_semantic)
    - Vector similarity search using pgvector and cosine distance
    - Configurable similarity threshold (default: 0.7)
- ✅ **Completed:** Keyword Document Search (search_documents_keyword)
    - PostgreSQL full-text search with ranking
- ✅ **Completed:** Hybrid Search endpoint (Django API only - ai_viewsets.py:224)
    - Combines vector similarity + keyword search with deduplication
    - Available as REST endpoint but not wrapped as LangGraph tool
    - LangGraph agent calls semantic and keyword tools separately for granular reasoning
- ✅ **Completed:** Context Window Tool (get_context)
    - Retrieves surrounding chunks for specific document chunk
    - Configurable window size (default: 2 chunks before/after)

### System Prompt Design

- ✅ **Completed:** Manufacturing expert assistant role definition
- ✅ **Completed:** Expertise areas (production, quality, equipment, ERP, compliance, continuous improvement)
- ✅ **Completed:** Behavioral guidelines (plan before acting, use tools strategically, combine sources, persist,
  evidence-based)
- ✅ **Completed:** Communication style (direct, practical, honest)
- ✅ **Completed:** Critical constraints (no fabrication, don't assume, always cite sources)

### Security & Authentication

- ✅ **Completed:** Per-user authentication via token forwarding (tools.py:22)
- ✅ **Completed:** Token-based authentication flow (Frontend → LangGraph → Django APIs with service account fallback)

### File Upload & Analysis

- 🔴 **Needed:** Multi-file upload support for AI assistant
    - Accept documents (PDF, DOCX, TXT) directly in chat interface
    - Accept data files (CSV, XLSX) for analysis
    - Temporarily process uploaded files without permanent storage
    - Return analysis, summaries, or extracted data to user
- 🔴 **Needed:** Stateless Python code execution (Code Interpreter style)
    - Docker Compose isolated container for code execution
    - LLM generates Python scripts for data analysis on user-uploaded files
    - Execute code safely and return results (stdout, stderr, generated files)
    - Security: Network isolation, file system restrictions, resource limits
    - Estimated: ~200 LOC
- 🟡 **Nice to Have:** Stateful Jupyter notebook environment
    - Persistent kernel sessions per user/chat
    - LLM can execute cells sequentially, building on previous results
    - Maintain variables/dataframes across multiple interactions
    - Generate matplotlib charts and return as images
    - Interactive data exploration workflow
    - Estimated: ~800 LOC (security hardening is complex)

### Tool Expansion

- 🟡 **Nice to Have:** Report generation tool (PDF exports, PPAP packages, audit reports)
- 🟡 **Nice to Have:** Chart/graph generation tool (SPC charts, Pareto diagrams)

### Natural Language Workflows

- 🟡 **Nice to Have:** Guided troubleshooting - interactive decision trees for common issues
- 🟡 **Nice to Have:** Procedure walkthroughs - step-by-step guidance through SOPs

### Advanced Reasoning

- 🟡 **Nice to Have:** Root cause analysis assistance - guide users through structured RCA processes
- 🟡 **Nice to Have:** Regulation interpretation - answer compliance questions with citations

### Commercial Deployment Architecture

- 🔴 **Needed:** Commercial LLM endpoint configuration
    - Alternative LLM deployment for commercial/production customers
    - Options: Azure OpenAI, Databricks, LangGraph Cloud, or managed Ollama cluster
    - Separate from local development Ollama instance
    - Per-tenant API key management
    - Cost tracking and usage monitoring per customer
- 🔴 **Needed:** Public document replication to Azure
    - Sync Documents and DocChunks with classification='public' to Azure Flexible PostgreSQL
    - One-way replication: local → Azure for public documents only
    - Signal-based sync on document save (if classification='public')
    - Nightly reconciliation job comparing hash of all public docs (local vs Azure)
    - Commercial deployment LLM only accesses Azure public doc database
    - Keeps sensitive/internal documents isolated on local instance

### Performance & Deployment

- 🟡 **Nice to Have:** Model fine-tuning - train on company-specific data (local only)
- 🟡 **Nice to Have:** Performance optimization - caching, response streaming, parallel tool execution

### Proactive Intelligence (Yacht Problems)

- 🟢 **Yacht:** Anomaly detection - flag unusual quality trends before they become problems
- 🟢 **Yacht:** Scheduled insights - daily/weekly summary reports delivered proactively
- 🟢 **Yacht:** Threshold monitoring - alert when KPIs exceed limits
- 🟢 **Yacht:** Predictive maintenance - suggest equipment service based on usage patterns
- 🟢 **Yacht:** Compliance monitoring - warn about approaching training/calibration due dates

### Multi-Modal Capabilities (Yacht Problems)

- 🟢 **Yacht:** Image analysis - identify defects from photos, read part markings
- 🟢 **Yacht:** CAD drawing interpretation - answer questions about technical drawings
- 🟢 **Yacht:** Video analysis - extract information from training videos, procedure demonstrations
- 🟢 **Yacht:** Audio transcription - convert voice memos to searchable text

### Advanced Features (Yacht Problems)

- 🟢 **Yacht:** Voice interface - shop floor voice commands and responses
- 🟢 **Yacht:** Natural language report generation - "Generate a PPAP package for part ABC-123"
- 🟢 **Yacht:** Process optimization suggestions - identify bottlenecks and improvement opportunities
- 🟢 **Yacht:** Historical context - "How does this compare to last quarter's data?"
- 🟢 **Yacht:** A/B testing - compare model performance on common queries

### Knowledge Management

- ✅ **Completed:** Document embedding and semantic search
- 🟢 **Yacht:** Knowledge graph - build relationships between procedures, parts, equipment
- 🟢 **Yacht:** Best practice recommendations - learn from historical successes
- 🟢 **Yacht:** Tribal knowledge capture - extract knowledge from operator conversations

### Predictive Analytics (Yacht Problems)

- 🟢 **Yacht:** Predictive quality analytics - ML models predict defect likelihood based on historical patterns

### Data Sovereignty Policies (Locked)

- 🔒 **Policy:** No cloud LLM services - data is too sensitive for external APIs
- 🔒 **Policy:** No AI data modification - all create/update/delete operations require human approval
- 🔒 **Policy:** Read-only AI access - LLM tools limited to queries and analysis only

---

## 5. Document Control & Management

### Document Storage & Versioning

- ✅ **Completed:** Full document versioning system (previous_version chain, is_current_version flag)
- ✅ **Completed:** Generic relations - attach documents to any entity
- ✅ **Completed:** Structured upload paths with date-based organization
- ✅ **Completed:** Support for PDFs, images, spreadsheets, CAD files
- ✅ **Completed:** Metadata tracking (file names, upload dates, uploader, descriptions)

### Document Classification

- ✅ **Completed:** Security levels (Public, Internal, Confidential, Restricted, Secret)
- ✅ **Completed:** Document-level permissions based on user roles and classification
- ✅ **Completed:** Customer users only see "public" documents
- ✅ **Completed:** Audit logging of document access

### Document Management UI (DMS Module)

- ✅ **Completed:** Documents Dashboard (`/documents`) with stats cards, quick actions, pending approvals, recent docs
- ✅ **Completed:** Documents List Page (`/documents/list`) with search, sort, and filter
- ✅ **Completed:** "Needs My Approval" filter on documents list (backend + frontend toggle)
- ✅ **Completed:** Document Detail Page (`/documents/:id`) with tabbed layout:
    - Overview tab: File preview (images, PDFs), metadata, linked object info
    - Versions tab: Version history table with download capability
    - Approval tab: Submit for approval, status display, response modal, approval history
    - Audit Trail tab: Complete change history via django-auditlog
- ✅ **Completed:** Document approval workflow integration:
    - Submit for Approval action (DRAFT → UNDER_REVIEW)
    - Approval Request creation via ApprovalTemplate
    - Approval Response submission with signature capture
    - Auto-status transition on approval (UNDER_REVIEW → APPROVED)
- 🟡 **Nice to Have:** Document revision workflow (`/documents/:id/revise`) - create new version from existing
- 🟡 **Nice to Have:** Document Type configuration model - define approval templates per doc type
- 🟡 **Nice to Have:** Full version chain display - fetch and show all previous versions

### AI-Readable Documents

- ✅ **Completed:** AI embedding flag (ai_readable)
- ✅ **Completed:** Auto-embedding signal - triggers async embedding when ai_readable=True
- ✅ **Completed:** Document chunking (~1200 character chunks, max 40 per doc)
- ✅ **Completed:** Vector storage in pgvector
- ✅ **Completed:** Chunk metadata (preview_text, full_text, span_meta, embedding)

---

## 6. Business Integration & CRM

### HubSpot Integration

- ✅ **Completed:** Integration service architecture (`Tracker/integrations/`)
    - `IntegrationService` base class with test_connection, sync_orders, pull/push methods
    - `IntegrationRegistry` for auto-registration of integration services
    - `IntegrationConfig` dataclass for consistent configuration
    - `HubSpotService` implementation with full test coverage
- ✅ **Completed:** Company sync from HubSpot CRM
- ✅ **Completed:** Deal pipeline - update deal stages based on order status
- ✅ **Completed:** Contact management - import HubSpot contacts as users
- ✅ **Completed:** Sync logging - track all HubSpot API calls
- ✅ **Completed:** Webhook verification and handling
- 🟡 **Nice to Have:** Bidirectional sync - push order updates back to HubSpot

### Customer Management

**Portal & Access**

- ✅ **Completed:** Company registry with HubSpot API IDs
- ✅ **Completed:** User-company linking
- ✅ **Completed:** Customer portal (customers can view their orders, parts, documents)
- ✅ **Completed:** Customer login interface
- ✅ **Completed:** Customer invitation system (invite customers to create accounts)
- ✅ **Completed:** Read-only access (customers cannot modify data)
- ✅ **Completed:** Data isolation (customers only see their own orders/parts)

**Notification System**

- ✅ **Completed:** NotificationTask model with scheduling support
- ✅ **Completed:** NotificationPreferenceViewSet (backend API)
- ✅ **Completed:** Email notification infrastructure (Celery + SMTP)
- ✅ **Completed:** Customer notification preference UI (frontend)
- 🟡 **Nice to Have:** HubSpot gate progress notifications (automatic emails on deal stage changes)
- 🟡 **Nice to Have:** Production milestone notifications (automatic emails on order status changes)
- 🟡 **Nice to Have:** Customizable notification frequency (real-time, daily digest, weekly summary, disabled)

### Order Management

- ✅ **Completed:** Customer orders with status workflow
- ✅ **Completed:** External identifiers (link to ERP systems like SAP)
- ✅ **Completed:** Due date tracking and alerts
- ✅ **Completed:** Customer assignment
- ✅ **Completed:** Status updates trigger HubSpot deal stage changes

---

## 7. User Management & Authentication

### User Onboarding

- ✅ **Completed:** Invitation system - secure token-based user invitations (UserInvitation model)
- ✅ **Completed:** Admin generates invitation tokens with email and optional company assignment
- ✅ **Completed:** Token expiration dates for security
- ✅ **Completed:** Single-use tokens prevent reuse
- ✅ **Completed:** Track invitation status (pending, accepted, expired)
- ✅ **Completed:** Self-registration via signup page (SignupPage.tsx)
- ✅ **Completed:** Email and password-based registration
- ✅ **Completed:** Optional invitation token for company linking
- ✅ **Completed:** Company assignment from invitations

### Authentication & Password Management

- ✅ **Completed:** Token-based authentication (Django REST Framework)
- ✅ **Completed:** Username/email + password login
- ✅ **Completed:** Authentication token for API access
- ✅ **Completed:** Self-service password reset workflow
- ✅ **Completed:** Request reset via email (PasswordResetRequestForm)
- ✅ **Completed:** Secure reset token sent to registered email
- ✅ **Completed:** Confirm reset with new password (PasswordResetConfirmForm)
- ✅ **Completed:** Time-limited reset tokens

### User Profile Management

- ✅ **Completed:** User profile page (UserProfilePage.tsx)
- ✅ **Completed:** Update personal information
- ✅ **Completed:** Change password
- ✅ **Completed:** View assigned company
- ✅ **Completed:** View group membership
- ✅ **Completed:** User administration (admin can manage all users via UserViewSet)
- ✅ **Completed:** Create, update, deactivate users
- ✅ **Completed:** Assign users to groups
- ✅ **Completed:** Link users to companies
- ✅ **Completed:** View user activity via audit logs

### Group & Permission Management

- ✅ **Completed:** Declarative permission system (`Tracker/permissions.py`)
    - 7 groups: Admin, QA_Manager, QA_Inspector, Production_Manager, Production_Operator, Document_Controller, Customer
    - Module-aware permission structure (core, qms, mes, dms)
    - Wildcard support (`view_*`) and `__all__` for admin
    - PermissionService with idempotent apply/diff operations
    - PermissionChangeLog audit trail for QMS compliance
    - Management command: `python manage.py setup_permissions`
    - Post-migrate signal auto-applies permissions
- 🟡 **Nice to Have:** Admin panel for group management UI
    - Group creation and editing UI
    - Permission assignment subform per group
    - Bulk assign/remove users from groups

### Session Management

- ✅ **Completed:** Token persistence in browser local storage
- ✅ **Completed:** Logout functionality
- ✅ **Completed:** Session security (tokens validated on every API request)
- ✅ **Completed:** Configurable token lifetime

---

## 8. Access Control & Security

### Role-Based Access Control (RBAC)

- ✅ **Completed:** 7 user groups with Django permissions:
    1. Admin - All permissions (128 total)
    2. QA_Manager - View/change all, approve inspections/dispositions, manage documents (71 permissions)
    3. QA_Inspector - View all, perform inspections, view confidential docs (35 permissions)
    4. Production_Manager - View/change manufacturing data, view confidential docs (36 permissions)
    5. Production_Operator - View all, create/change parts (34 permissions)
    6. Document_Controller - Manage documents, all classification levels (39 permissions)
    7. Customer - View own orders/parts, public documents only (4 permissions)
- ✅ **Completed:** Custom permissions for approval workflows and document classification
- ✅ **Completed:** SecureManager pattern for unified security
- ✅ **Completed:** Automatic user-based filtering via for_user() method
- ✅ **Completed:** Document classification-based filtering (public, internal, confidential, restricted, secret)
- ✅ **Completed:** DocChunk security inheritance from parent Documents
- ✅ **Completed:** Permission-based document access (view_confidential_documents, view_restricted_documents, etc.)
- ✅ **Completed:** Soft delete support (active(), deleted())
- ✅ **Completed:** Version filtering (current_versions(), all_versions())
- ✅ **Completed:** Data isolation (customers only see own data)
- ✅ **Completed:** Scope API (`/api/scope/`) for secure graph traversal
    - Batched BFS traversal of model hierarchies
    - Respects `for_user()` permissions at every node
    - Enables cross-entity queries (e.g., "all documents under this order")
    - GenericForeignKey support via ContentType framework

### Security Features

- ✅ **Completed:** Token authentication (Django REST Framework)
- ✅ **Completed:** HTTPS/TLS encrypted transport (production)
- ✅ **Completed:** Secure cookies (HTTP-only, secure flags)
- ✅ **Completed:** CORS configuration (whitelisted origins)
- ✅ **Completed:** SQL injection protection (ORM-based queries)
- ✅ **Completed:** XSS protection (React auto-escaping, CSP headers)
- ✅ **Completed:** Password hashing (PBKDF2, FIPS-approved when using FIPS-validated OpenSSL)

---

## 9. Audit Trail & Compliance

### Audit Logging

- ✅ **Completed:** django-auditlog integration - automatic logging on all SecureModel changes
- ✅ **Completed:** Change tracking (before/after values for every field modification)
- ✅ **Completed:** User attribution (who made each change)
- ✅ **Completed:** Timestamp precision (exact datetime of every modification)
- ✅ **Completed:** Bulk operation logging (special handling for bulk deletes/restores)
- ✅ **Completed:** Read-only access (audit logs cannot be modified after creation)

### Soft Delete Pattern

- ✅ **Completed:** Archive instead of delete (all models use archived flag)
- ✅ **Completed:** Recovery capability (restore soft-deleted records with full history)
- ✅ **Completed:** Archive reasons (optional reason codes for deletions)
- ✅ **Completed:** Hard delete option (actual database deletion for GDPR compliance)

### Version Control

- ✅ **Completed:** Version field (auto-incrementing)
- ✅ **Completed:** previous_version ForeignKey (chain to earlier versions)
- ✅ **Completed:** is_current_version boolean flag
- ✅ **Completed:** create_new_version() method
- ✅ **Completed:** get_version_history() to retrieve full version chain

### Compliance Support

- ✅ **Completed:** User authentication and authorization (Django auth)
- ✅ **Completed:** Role-based access control (7 groups with declarative permission system)
- ✅ **Completed:** Document version control and classification
- ✅ **Completed:** Parts traceability (serial numbers, order relationships)
- ✅ **Completed:** Quality inspection workflows and sampling
- ✅ **Completed:** Audit logging for all changes
- ✅ **Completed:** FIPS compliance (via Azure infrastructure: Disk Encryption, TLS, PostgreSQL TDE)

### Compliance Reporting

- 🔴 **Needed:** Audit-ready exports (ISO 9001, AS9100D)
- 🔴 **Needed:** Sampling compliance reports
- 🔴 **Needed:** Training compliance by role

---

## 10. Notifications & Alerts

### Celery-Based Notification System

- ✅ **Completed:** Email notifications (SMTP configuration)
- ✅ **Completed:** Async processing (non-blocking notification delivery)
- ✅ **Completed:** Retry logic (automatic retry on transient failures)
- ✅ **Completed:** HTML email templates
- ✅ **Completed:** Retryable task base classes with exponential backoff
  ```python
  class RetryableEmailTask(celery.Task):
      autoretry_for = (SMTPException, ConnectionError, TimeoutError, OSError)
      retry_backoff = True
      retry_backoff_max = 600
      retry_jitter = True
      max_retries = 3

  class RetryableEmbeddingTask(celery.Task):
      autoretry_for = (ConnectionError, TimeoutError, OSError)
      retry_backoff = True
      retry_backoff_max = 300
      retry_jitter = True
      max_retries = 5

  class RetryableHubSpotTask(celery.Task):
      autoretry_for = (ConnectionError, TimeoutError, OSError)
      retry_backoff = True
      retry_backoff_max = 900
      retry_jitter = True
      max_retries = 4

  class RetryableFileTask(celery.Task):
      autoretry_for = (TimeoutError, MemoryError, OSError)
      retry_backoff = True
      retry_backoff_max = 120
      retry_jitter = True
      max_retries = 2
  ```

### NotificationTask Model

- ✅ **Completed:** Fixed interval support (weekly, daily, monthly recurring notifications)
- ✅ **Completed:** Deadline-based support (escalating reminders as deadline approaches)
- ✅ **Completed:** Multi-channel structure (email implemented, in-app/SMS ready)
- ✅ **Completed:** Status tracking (pending, sent, failed, cancelled)

### Notification Handler System

- ✅ **Completed:** `notifications.py` handler module with factory pattern
- ✅ **Completed:** Email notification handlers for all approval/CAPA types:
    - `APPROVAL_REQUEST` - Notify approvers of new approval request
    - `APPROVAL_DECISION` - Notify requester of approval/rejection outcome
    - `APPROVAL_ESCALATION` - Notify escalation recipients of overdue approvals
    - `CAPA_REMINDER` - Remind assignees of upcoming/overdue CAPA tasks
    - `WEEKLY_REPORT` - Weekly summary reports
- ✅ **Completed:** HTML email templates with actionable links

### Celery Beat Schedule

- ✅ **Completed:** Periodic task scheduling configured in `celery_app.py`:
    - `dispatch_pending_notifications` - Every 5 minutes
    - `check_overdue_approvals` - Hourly
    - `escalate_approvals` - Hourly (offset 30 min)
    - `check_overdue_capas` - Daily at 8 AM UTC

### Notification Types

- ✅ **Completed:** Approval request notifications
- ✅ **Completed:** Approval decision notifications
- ✅ **Completed:** Approval escalation notifications
- ✅ **Completed:** CAPA task reminders
- ✅ **Completed:** Weekly reports (basic placeholder)
- 🟡 **Nice to Have:** Quality alerts - failed inspections, quarantine dispositions
- 🟡 **Nice to Have:** Order updates - status changes notify customers

---

## 11. Data Import/Export

### Excel/CSV Export

- ✅ **Completed:** ExcelExportMixin applied to most ViewSets (backend)
- ✅ **Completed:** Formatted output (headers, data types, column widths)
- ✅ **Completed:** Streaming export for large datasets
- ✅ **Completed:** Frontend export buttons on ModelEditorPage
    - Auto-detects if backend has export_excel endpoint
    - Download button in toolbar triggers .xlsx download
    - Applies current search/filter state to export

### CSV Import

- ✅ **Completed:** Work order bulk upload from ERP exports (backend + frontend)
- ✅ **Completed:** Pre-import validation with error reporting
- ✅ **Completed:** Clear error messages for malformed data
- 🟡 **Nice to Have:** Modular CSV import system
    - Extensible import framework for any entity type
    - Configurable field mapping per entity
    - Reusable frontend import component with drag-and-drop
    - Preview and validation before commit
    - Import templates downloadable per entity
    - Support for Parts, Equipment, Users, Companies, Quality data, etc.

---

## 12. QMS Compliance Features

### CAPA (Corrective and Preventive Action)

- ✅ **Completed:** Basic NCR workflow (QuarantineDisposition model)
- ✅ **Completed:** Core CAPA workflow
    - CAPA model with auto-numbering (CAPA-CA-2025-001, CAPA-PA-2025-002, etc.)
    - Root cause analysis (5 Whys and Fishbone diagrams with dedicated models)
    - Task management with multi-assignee support (CapaTasks model)
    - Verification workflow with effectiveness confirmation (CapaVerification model)
    - State machine (OPEN → IN_PROGRESS → PENDING_VERIFICATION → CLOSED)
    - `transition_to()` method for validated state transitions with blocker checks
    - `get_blocking_items()` for closure validation
    - Links to QualityReports and QuarantineDispositions (M2M relationships)
    - Quality Dashboard with stats (open, overdue, pending verification, closed)
    - My Tasks view for assigned CAPA tasks
    - Full CRUD UI (list, detail, create pages with tabbed detail view)
    - RCA tab with 5 Whys and Fishbone entry
    - Tasks tab with inline task management
    - Verification tab with effectiveness confirmation
    - Documents and History tabs
    - Auto-approval trigger for Critical/Major severity CAPAs
    - CAPA rejection handling resets approval_required for re-request
- 🟡 **Nice to Have:** Intelligence layer (defer until after pilot feedback)
    - Auto-trigger rules (3 failures in 30 days → create CAPA)
    - Recurrence detection and pattern matching
    - Cost tracking (COPQ: scrap, rework, labor, downtime)
    - Task dependencies and sequencing
    - Statistical verification with significance testing
    - RCA quality scoring and peer review
    - Advanced analytics (Pareto charts, trend analysis)

### Training & Competency Management

**Note:** Many companies use external LMS (Cornerstone, SAP SuccessFactors) or third-party trainers. Focus on records tracking, not training delivery.

- ✅ **Completed:** TrainingType, TrainingRecord, TrainingRequirement models with full CRUD ViewSets
- ✅ **Completed:** Training records editor pages (TrainingRecordsPage, TrainingTypesPage, TrainingDashboardPage)
- 🔶 **Needs Logic:** Training/certification due date alerting (Celery beat task)
- 🟡 **Nice to Have:** Training effectiveness verification
- 🟡 **Nice to Have:** On-the-job training (OJT) documentation
- 🟡 **Nice to Have:** Integration with part/step restrictions (only trained users can perform operations)

### First Article Inspection (FAI)

- 🔴 **Needed:** AS9102 form generation (Form 1, 2, 3)
- 🔴 **Needed:** FAI workflow with assignment and approval
- 🔴 **Needed:** Measurement result tracking per characteristic
- 🔴 **Needed:** 3D model annotation for characteristic identification (reuse existing 3D annotation system)
- 🔴 **Needed:** FAI validity tracking (expiry on design changes)
- 🔴 **Needed:** Customer FAI approval workflow
- 🟡 **Nice to Have:** 2D PDF ballooned drawing support (for customers with contractual requirements)

**Implementation Notes:**
- AS9102 requires unique characteristic identification and traceability, NOT specifically ballooned drawings
- Existing 3D annotation system (HeatMapAnnotations) can be adapted for FAI characteristic marking
- 3D annotation provides superior visualization vs. traditional 2D balloons
- Reuses 90% of existing 3D annotation code
- 2D PDF support can be added later if customer contracts require it

### PPAP (Production Part Approval Process)

**PPAP consists of 18 elements. Current system support: ~50% (4 complete, 7 partial, 5 missing)**

#### ✅ Complete (4 elements)
| Element | Status | How |
|---------|--------|-----|
| 1. Design Records | ✅ Full | Documents model with versioning, approval workflow |
| 5. Process Flow Diagram | ✅ Full | Process/Steps model with API |
| 9. Dimensional Results | ✅ Full | MeasurementResult + SPC data |
| 11. Initial Process Studies (Cpk) | ✅ Full | SPC module (X-bar/R, X-bar/S, I-MR, Cpk/Ppk, Western Electric rules) |

#### 🔶 Partial (7 elements - document storage only, no structured workflow)
| Element | Status | Gap |
|---------|--------|-----|
| 2. Engineering Change Docs | 🔶 Partial | Document revisions exist, no formal ECN workflow |
| 4. Design FMEA | 🔶 Storage | Can upload FMEA docs, no RPN tracking |
| 6. Process FMEA | 🔶 Storage | Can upload FMEA docs, no RPN tracking |
| 7. Control Plan | 🔶 Storage | Can upload docs, no structured control plan model |
| 10. Material/Performance Test Results | 🔶 Partial | QualityReports exist, no material cert linking |
| 12. Qualified Lab Documentation | 🔶 Storage | Can upload docs |
| 16. Checking Aids | 🔶 Partial | Equipment model exists, no cal tracking |

#### ❌ Missing (5 elements)
| Element | Gap | Effort |
|---------|-----|--------|
| 3. Customer Engineering Approval | No customer approval tracking | Low |
| 8. MSA/Gage R&R | No study workflow or calculations | Medium |
| 13. Appearance Approval Report | No structured AAR form | Low |
| 17. Customer-Specific Requirements | No structured tracking (customer_note is portal comms) | Low |
| 18. Part Submission Warrant (PSW) | No PSW generation or submission tracker | Medium |

#### N/A (2 elements - physical, not software)
- 14. Sample Production Parts
- 15. Master Sample

#### Summary
- **Current state:** ~50% coverage. Core data exists (design records, SPC, process flow). Many elements can be stored as documents but lack structured workflows.
- **Minimum viable PPAP requires:** PSW generation, submission tracker, MSA/Gage R&R, customer approval workflow

### Supplier Management

- 🔴 **Needed:** Supplier registry with contact information
- 🔴 **Needed:** Supplier qualification and approval workflow
- 🔴 **Needed:** Incoming inspection workflow
- 🔴 **Needed:** Approved supplier lists per part type/material
- 🟡 **Nice to Have:** Supplier performance metrics (on-time delivery, quality metrics)
- 🟡 **Nice to Have:** Supplier corrective action requests (SCAR)
- 🟡 **Nice to Have:** Supplier portal for order visibility and document exchange

### Setup & Changeover Tracking

- 🟡 **Nice to Have:** Setup documentation per equipment and part type
- 🟡 **Nice to Have:** Setup approval workflow
- 🟡 **Nice to Have:** Setup verification checklists
- 🟡 **Nice to Have:** First piece inspection integration

### Material Lot Traceability

**Required for:** AS9100D §8.5.2, IATF 16949 §8.5.2.1, DFARS

- ✅ **Models Complete:** MaterialLot model with lot_number, supplier, material_type, received_date, quantity, status, expiration_date, CoC fields
- ✅ **Models Complete:** MaterialUsage model links lots to parts with qty_consumed, is_substitute, substitution_reason
- ✅ **API Complete:** MaterialLotViewSet with split action, MaterialUsageViewSet (read-only)
- 🔶 **Needs UI:** MaterialLot editor page, MaterialUsage viewer
- 🔶 **Needs UI:** Forward/backward trace visualization
- 🔶 **Needs Logic:** Material receipt with incoming inspection integration
- 🟡 **Nice to Have:** Recall simulation wizard (impact analysis, quarantine, notifications)
- 🟡 **Nice to Have:** Barcode scan for material issue to part

### PDF Package Generators

**Note:** Infrastructure exists in `Tracker/services/packages/`. Stubs created, implementation needed.

- 🔴 **Needed:** Certificate of Conformance (C of C) package - `coc.py`
- 🔴 **Needed:** 8D Report package - `eight_d.py`
- 🔴 **Needed:** FAI package (AS9102 Forms 1/2/3) - `fai.py`
- 🔴 **Needed:** PPAP package (PSW + 18 elements) - `ppap.py`
- 🟡 **Nice to Have:** Batch record / lot history package

### Change Management (ECO/ECR)

**Required for:** IATF 16949, AS9100D

- 🔴 **Needed:** Engineering Change Request (ECR) model and workflow
- 🔴 **Needed:** Engineering Change Order (ECO) model with approval workflow
- 🔴 **Needed:** Impact analysis (affected parts, orders, documents)
- 🔴 **Needed:** Effectivity tracking (by date, serial number, or lot)
- 🔴 **Needed:** Link changes to document revisions
- 🟡 **Nice to Have:** Customer notification for changes requiring approval

### Counterfeit Prevention (Aerospace)

**Required for:** AS6174, DFARS 252.246-7007

- 🟡 **Nice to Have:** Approved supplier list (ASL) with verification status
- 🟡 **Nice to Have:** Suspect/counterfeit part reporting workflow
- 🟡 **Nice to Have:** Source verification requirements per part type
- 🟡 **Nice to Have:** GIDEP alert integration (manual import)

### Special Process Controls (Aerospace)

**Required for:** AS9100D, Nadcap

- 🟡 **Nice to Have:** Special process identification per step (heat treat, NDT, welding, plating)
- 🟡 **Nice to Have:** Nadcap supplier certification tracking
- 🟡 **Nice to Have:** Process parameter logging (temperature, time, etc.)
- 🟡 **Nice to Have:** Operator qualification per special process

### Customer Source Inspection (Aerospace/Defense)

**Required for:** AS9100D, Defense contracts

- 🟡 **Nice to Have:** Source inspection hold points per step
- 🟡 **Nice to Have:** Customer/DCMA notification for witness points
- 🟡 **Nice to Have:** Inspection release tracking
- 🟡 **Nice to Have:** Government property identification (if applicable)

### Export Control (Defense)

**Required for:** ITAR, EAR, DFARS

- 🟡 **Nice to Have:** ECCN/USML classification per part type
- 🟡 **Nice to Have:** Export-controlled flag on documents
- 🟡 **Nice to Have:** Access restrictions based on citizenship/need-to-know
- 🟡 **Nice to Have:** Export license tracking

---

## 13. MES-Lite Features

**Note:** The system already has strong MES foundations. MES Standard backend is largely complete - main gap is UI.

### Already Built (MES Lite - Foundations)
- ✅ **Completed:** Work order management with quantity tracking
- ✅ **Completed:** Part status tracking (11 distinct states)
- ✅ **Completed:** Step-by-step workflow execution with operator attribution
- ✅ **Completed:** Step transition logs with timestamps (full audit trail)
- ✅ **Completed:** Equipment usage logging per part/step
- ✅ **Completed:** Process/step configuration per part type
- ✅ **Completed:** Real-time progress tracking (actual vs expected completion)

### MES Standard Backend (Complete, Needs UI)
- ✅ **API Complete:** WorkCenter, Shift, ScheduleSlot models with ViewSets (start/complete actions)
- ✅ **API Complete:** DowntimeEvent model with ViewSet (resolve action, category choices)
- ✅ **API Complete:** MaterialLot with split action, MaterialUsage for traceability
- ✅ **API Complete:** TimeEntry with clock_in/clock_out/approve actions
- ✅ **API Complete:** BOM, BOMLine, AssemblyUsage for assembly genealogy

**UI Work Needed for MES Standard:**
- 🔶 **Editor Pages (7):** WorkCenter, Shift, ScheduleSlot, DowntimeEvent, MaterialLot, TimeEntry, BOM
- 🔶 **Complex UI:** Visual schedule board with drag-drop (not just CRUD)
- 🔶 **Dashboard:** OEE calculation display (data exists, needs aggregation + UI)
- 🔶 **Reports (8):** Production summary, work order status, overdue WOs, operator productivity, OEE by equipment, labor efficiency, lot traceability, equipment utilization
- 🔶 **Enhancements:** WIP aging display, lead time tracking, due date "at risk" warnings, Big screen API wiring

### Missing Additive Fields (MES Standard)
- ✅ **Completed:** WorkOrder.priority (integer field with WorkOrderPriority choices)
- ✅ **Completed:** Equipments.status (EquipmentStatus choices: in_service, out_of_service, in_calibration, in_maintenance, retired)
- 🔴 **Needed:** Steps.work_center (FK to WorkCenter)
- 🔴 **Needed:** Steps.setup_duration (DurationField for setup vs run time)

### Needed for MES-Lite Offering
- ✅ **Completed:** Shop floor dashboard / Big screen display - BigScreenPage (`/big-screen`) with KPIs, quality trend, radar chart, highlights (needs API wiring)
- 🔴 **Needed:** WIP visualization (parts at each station/step)
- 🟡 **Nice to Have:** Barcode/QR scanning for part check-in/check-out
- 🟡 **Nice to Have:** Cycle time tracking and analysis
- 🟡 **Nice to Have:** Operator time tracking per operation - *TimeEntry model exists, needs UI*

### Advanced MES (Yacht Problems)
- 🟢 **Yacht:** Shop floor scheduling and dispatching - *ScheduleSlot model exists, needs advanced UI*
- 🟢 **Yacht:** Work center capacity tracking - *WorkCenter model exists, needs capacity view*
- 🟢 **Yacht:** Resource allocation and optimization
- 🟢 **Yacht:** Bottleneck identification and alerting
- 🟢 **Yacht:** Integration with process DAGs for dynamic routing

---

## 14. Analytics & Dashboards

### Executive Dashboard (`/analysis`) — COMPLETED ✅

- ✅ **Completed:** Quality KPIs with live API data:
    - First Pass Yield (FPY) with status coloring
    - Scrap Rate
    - Rework Rate
    - Open Issues (NCRs + Quarantine)
    - Active CAPAs
    - Overdue CAPAs
- ✅ **Completed:** FPY Trend Chart:
    - 30/60/90 day range selector
    - Dynamic Y-axis scaling
    - Average line reference
    - Target line (95%)
    - Summary stats (average, min, max, trend)
- ✅ **Completed:** Mini Pareto (Top 5 defects with quick link to detail)
- ✅ **Completed:** Needs Attention panel with severity-based alerts
- ✅ **Completed:** Quick links to drill-down pages

### Defect Analysis (`/quality/defects`) — COMPLETED ✅

- ✅ **Completed:** KPI cards (Total Defects, Defect Rate, Top Type, Trend)
- ✅ **Completed:** Defect trend chart over time with average line
- ✅ **Completed:** Breakdown filters (by defect type, process, part type)
- ✅ **Completed:** Clickable bars that filter records
- ✅ **Completed:** Records table with selection, Create CAPA, Export CSV

### NCR Analysis (`/quality/ncrs`) — COMPLETED ✅

- ✅ **Completed:** KPIs (Total NCRs, Open NCRs, Avg Age, Closure Rate)
- ✅ **Completed:** NCR Trend chart (created vs closed)
- ✅ **Completed:** Disposition breakdown donut chart
- ✅ **Completed:** NCR aging bucket chart
- ✅ **Completed:** Open Dispositions table

### Statistical Process Control (`/spc`) — COMPLETED ✅

- ✅ **Completed:** X-bar/R charts for subgroup data (subgroups 2-8)
- ✅ **Completed:** X-bar/S charts for larger subgroups (9-25)
- ✅ **Completed:** I-MR charts for individual measurements
- ✅ **Completed:** Process capability metrics (Cp, Cpk, Pp, Ppk)
- ✅ **Completed:** Western Electric rules for out-of-control detection (8 rules)
- ✅ **Completed:** Clickable data points linking to quality reports
- ✅ **Completed:** Hierarchical process/step/measurement navigation
- ✅ **Completed:** PDF export via Typst adapter pipeline (Email Report button)
- ✅ **Completed:** Baseline persistence with full audit trail
- ✅ **Completed:** Baseline vs Monitoring mode toggle
- ✅ **Completed:** Histogram with LSL/USL spec limits

### Shop Floor Dashboards

- 🟡 **Nice to Have:** Shop floor real-time dashboards:
    - Parts status distribution (pie chart)
    - Work order progress (Gantt chart)
    - Equipment utilization (heatmap)
- 🟡 **Nice to Have:** On-time delivery rate KPI

### Advanced Analytics & BI (Yacht Problems)

- 🟢 **Yacht:** Changeover time tracking for OEE calculations
- 🟢 **Yacht:** Overall Equipment Effectiveness (OEE) full implementation
- 🟢 **Yacht:** Cost of quality tracking (scrap, rework, inspection costs)
- 🟢 **Yacht:** Customer complaint rates and tracking
- 🟢 **Yacht:** Operator activity timeline analysis

---

## 15. Bug Fixes & Technical Debt

### Permission-Based RBAC System

**Completed:**
- ✅ Declarative permission system in `Tracker/permissions.py` (single source of truth)
- ✅ Module-aware structure supports future app splitting (core, qms, mes, dms)
- ✅ 7 user groups: Admin, QA_Manager, QA_Inspector, Production_Manager, Production_Operator, Document_Controller, Customer
- ✅ PermissionService with idempotent apply/diff/dry-run operations
- ✅ PermissionChangeLog model for QMS audit compliance
- ✅ Management command: `python manage.py setup_permissions [--dry-run|--diff|--status]`
- ✅ Post-migrate signal auto-applies permissions after each migration
- ✅ Custom permissions: Documents (4), QualityReports (2), QuarantineDisposition (2), CAPA (4)
- ✅ DocChunk security inheritance from parent Documents
- ✅ SecureManager classification-based filtering with permission checks
- ✅ All AI search endpoints secured with `.for_user()`
- ✅ SecureQuerySet handles models without `archived` field
- ✅ Customer portal tested - no breaking changes
- ✅ Unit tests for permission service (18 tests passing)

**Optional Enhancements (Nice to Have):**
- 🟡 Add `permission_classes = [DjangoModelPermissions]` to ViewSets for API-level CRUD protection
- 🟡 QualityReportsViewSet approval actions with separation of duties
- 🟡 QuarantineDispositionViewSet approval/close actions
- 🟡 DocumentsViewSet classification change protection
- 🟡 React group management interface
- 🟡 Permission audit view

---

### Other Technical Debt

- 🟡 **Nice to Have:** LangGraph authentication hardening
- 🟡 **Nice to Have:** Improve error handling in async tasks
- 🟡 **Nice to Have:** Add comprehensive E2E tests for frontend
- 🟡 **Nice to Have:** Optimize complex queries with database indexes

### Scalability Considerations

- 🟡 **Nice to Have:** GPU acceleration for Ollama LLM inference
- 🟡 **Nice to Have:** pgvector index tuning for millions of chunks
- 🟡 **Nice to Have:** Celery task queue monitoring at high volume
- 🟡 **Nice to Have:** Handle document embedding backlog with bulk uploads

---

## 16. Security Hardening (Production Readiness)

### Recently Fixed

- ✅ **Completed:** Fixed broken `is_user_assigned_approver()` → `can_approve()` in approval viewset
- ✅ **Completed:** Removed `console.log(values)` that logged passwords in Login.tsx
- ✅ **Completed:** Removed auth header print statements in ai_viewsets.py
- ✅ **Completed:** Moved hardcoded email credentials to environment variables

### Configuration Hardening

- ✅ **Completed:** DEBUG defaults to False - must explicitly set DJANGO_DEBUG=true
- ✅ **Completed:** SECRET_KEY required in production - fails fast if missing when DEBUG=False
- ✅ **Completed:** HUBSPOT_WEBHOOK_SECRET required in production - rejects webhooks if not configured

### Error Handling

- ✅ **Completed:** Replaced `str(e)` error returns with generic messages
    - api_views.py, health_views.py, hubspot_view.py, ai_viewsets.py, viewsets/core.py
- ✅ **Completed:** Health endpoints return minimal info (just "unhealthy" or "not ready")

### Input Validation

- 🔴 **Needed:** File upload MIME validation - currently only checks extension; add python-magic
- 🔴 **Needed:** File size limits in serializers - add explicit max file size validation
- 🔴 **Needed:** Webhook payload validation - add schema validation for HubSpot webhooks

### API Security

- 🟡 **Nice to Have:** Rate limiting on AI endpoints and auth endpoints (django-ratelimit)
- 🟡 **Nice to Have:** API versioning with `/api/v1/` prefix
- 🟡 **Nice to Have:** Token expiration and rotation

### Secrets Management

- 🟡 **Nice to Have:** Azure Key Vault integration for production secrets
- 🟡 **Nice to Have:** Pre-commit hooks for secret detection (git-secrets)

### Code Cleanup

- 🟡 **Nice to Have:** Remove remaining print() statements (signals.py, tasks.py, hubspot/api.py)
- 🟡 **Nice to Have:** Replace ast.literal_eval with JSON parsing in ai_viewsets.py

### Advanced Security (Yacht Problems)

- 🟢 **Yacht:** Circuit breakers for external services (Ollama, HubSpot)
- 🟢 **Yacht:** Request tracing with correlation IDs
- 🟢 **Yacht:** Structured JSON logging
- 🟢 **Yacht:** Penetration testing
- 🟢 **Yacht:** SOC 2 Type II preparation

---

## Important Note: QMS Software vs. QMS Certification

**This is QMS SOFTWARE for manufacturers to use - not a QMS system being certified.**

- **Your software** provides the tools and workflows manufacturers need
- **Your customers** (manufacturers) use your software to run their QMS
- **Your customers** get ISO 9001/AS9100D certified, not you
- **Success metric:** Can a customer achieve certification using only your software?

**What "Complete QMS" means:**
- ✅ Software has all modules needed for customer certification
- ✅ Generates all required records, audit trails, and reports
- ✅ Enforces required workflows and controls
- ❌ Does NOT mean you (the software vendor) need certification
- ❌ Does NOT mean you need production data or evidence of use

---

## Summary Statistics

### ✅ Completed Features: ~280 items

Major categories:

- Full manufacturing operations (parts, work orders, processes, steps)
- Quality inspection with advanced statistical sampling
- 3D visualization with heat maps and annotation
- **3D annotation workflow integration** (COMPLETED - ready for quality inspection and FAI)
- **Statistical Process Control (SPC)** - X-bar/R, I-MR charts, Cpk/Ppk, Western Electric rules
- **PDF generation infrastructure** - Typst adapter registry, Celery, email delivery, DMS integration
- AI digital coworker with 5 core tools
- Document management with AI embeddings and classification-based security
- Permission-based RBAC with 7 user groups
- DocChunk security inheritance from Documents
- Classification-based filtering (public, internal, confidential, restricted, secret)
- Audit trail and compliance foundation
- HubSpot CRM integration

### 🔶 Remaining Work for ISO 9001 (UI Complete, Needs Alerting)

1. **Training & Competency Management** (See Section 12)
   - ✅ Models complete: TrainingType, TrainingRecord, TrainingRequirement
   - ✅ UI complete: TrainingRecordsPage, TrainingTypesPage, TrainingDashboardPage
   - 🔶 Needs: Due date alerting (Celery beat task)

2. **Calibration Tracking** (See Section 2)
   - ✅ Model complete: CalibrationRecord
   - ✅ UI complete: CalibrationRecordsPage, CalibrationDashboardPage
   - 🔶 Needs: Due date alerting (Celery beat task)

### 🔶 In Progress

- Polish customer-facing UI screens (Portal, Quality Reports, Work Orders)

### Go-to-Market Bundle: QMS + MES-Lite

After completing Training & Calibration UI + alerting, the sellable package includes:

**QMS Core (Complete):**
- CAPA/8D workflow with RCA
- Document control with approvals
- NCR/Disposition management
- Quality inspections with sampling
- Training records & competency tracking - *UI complete, needs alerting*
- Calibration tracking & certificates - *UI complete, needs alerting*
- SPC (X-bar/R, I-MR, Cpk/Ppk)
- Quality dashboards (FPY, Pareto)
- PDF report generation
- Full audit trail

**MES-Lite (Fully Built):**
- Work order management
- Part tracking (11 states)
- Step-by-step workflow execution
- Operator attribution
- Equipment usage logging
- Progress tracking
- Shop floor big screen display (BigScreenPage - needs API wiring)
- *Needed:* WIP visualization (parts at each station)

**MES Standard (Backend Complete, Needs UI):**
- WorkCenter, Shift, ScheduleSlot - scheduling infrastructure
- DowntimeEvent - equipment/work center downtime tracking
- MaterialLot, MaterialUsage - lot traceability
- TimeEntry - labor time tracking with clock in/out
- BOM, BOMLine, AssemblyUsage - assembly genealogy

**Differentiators:**
- 3D defect annotation with heat maps
- AI assistant with semantic document search
- Customer portal with order visibility
- HubSpot CRM integration

**Target Price:** $50-70K/year depending on modules

**Nice-to-Have Modules (Customers Can Work Around):**
- Internal audit management - customers can use Word/checklists or outsource audits
- Management review process - customers can hold meetings and upload minutes as Documents
- Customer complaint tracking - can be handled via CAPA workflow initially
- Risk register - vague ISO 9001 requirement, often just meeting minutes

### 🟡 Nice to Have (Phase 3 - Segment B / Automotive):

- Supplier quality management (AVL, scorecards, incoming inspection)
- Change management (ECO/ECR workflow)
- 🔶 **PPAP** - See Section 12 for detailed 18-element breakdown. Currently ~50% coverage (4 complete, 7 partial, 5 missing). Gaps: PSW generation, MSA/Gage R&R, customer approval workflow.
- Assembly genealogy

### 🟢 Deferred (Phase 4 - Segment C / Aerospace):

- First Article Inspection (FAI) - can leverage existing 3D annotation
- Material lot tracking and C of C generation
- Full PPAP
- Supplier special process controls
- Export control flagging (ITAR/ECCN)

### 🚢 Yacht Problems: ~30+ items

- Full MES-lite capabilities
- Advanced AI features (multi-modal, voice, predictive)
- Advanced analytics (OEE, cost of quality)
- Knowledge graphs
- ML-optimized sampling

---

## Development Philosophy

**Security First:**

- All data stays on-premises (no cloud LLMs)
- AI is read-only (no data modification by AI)
- Human approval required for all critical operations

**Compliance Driven:**

- ISO 9001, AS9100D, ITAR support
- Comprehensive audit trails
- Traceability throughout manufacturing

**Practical Innovation:**

- Novel features (3D visualization, AI coworker, advanced sampling)
- Built on proven technologies (Django, React, PostgresSQL)
- Local LLM deployment for data sovereignty

---

## Implementation Roadmap

**Roadmap organized by customer segment and feature criticality**

This roadmap defines our go-to-market strategy and feature development priorities based on target customer segments.

---

## Target Customer Segments

### **Segment A: General Manufacturing (ISO 9001)**
- Industrial equipment, contract manufacturing, consumer products, electronics
- Need: ISO 9001 compliance, quality traceability, customer visibility
- Don't need: Industry-specific features (aerospace FAI, automotive PPAP)

### **Segment B: Automotive Tier 2-3 (IATF 16949 Foundation)**
- Automotive component suppliers, remanufacturers
- Need: ISO 9001 + IATF 16949 basics (CAPA, SPC, supplier management)
- Don't need: Full PPAP, AS9100D aerospace requirements

### **Segment C: Aerospace (AS9100D) - DEFERRED**
- Aerospace/defense manufacturers, primes and tier suppliers
- Need: ISO 9001 + AS9100D (FAI, material traceability, full PPAP)
- **Target for later** after automotive foundation is proven

---

## Phase 1: Demo-Ready ✅ MOSTLY COMPLETE

**Target Segments:** All segments (discovery and demos)

**Goal:** Polish existing system for compelling product demos

### Critical (Must Have)
- ✅ **Completed:** Wire Excel export to frontend UI (ModelEditorPage auto-detects export endpoint)
- ✅ **Completed:** Build quality metrics dashboard - AnalysisPage (`/analysis`) includes:
  - 6 KPI cards with live API data (FPY, Scrap Rate, Rework Rate, Open Issues, CAPAs, Overdue)
  - First Pass Yield trend chart (30/60/90 day ranges with target line, average line, dynamic Y-axis)
  - Mini Pareto (Top 5 defects with link to full analysis)
  - Needs Attention panel with severity-based alerts
  - Quick links to drill-down pages (/quality/defects, /quality/ncrs)
- ✅ **Completed:** Defect analysis drill-down (`/quality/defects`):
  - KPIs (Total Defects, Defect Rate, Top Type, Trend)
  - Defect trend chart over time
  - Breakdown filters (by type, process, part type)
  - Records table with Create CAPA and Export CSV actions

### High Value (Should Have)
- ✅ Polish customer-facing UI screens (Portal, Quality Reports, Work Orders)
- ✅ Demo data seed script - `python manage.py populate_test_data`

### Enables:/
- ✅ Discovery calls with all segments
- ✅ Product demos showing differentiators (3D viz, AI, portal, SPC)
- ✅ Pipeline building with ISO 9001 and automotive prospects
- ✅ Can pilot with customers willing to accept Training & Calibration gaps

---

## Phase 2: Pilot-Ready for Segment A (General Manufacturing) 🔶 6/7 COMPLETE

**Target Segments:** Segment A only (ISO 9001 manufacturers)

**Goal:** Minimum viable compliance for ISO 9001 manufacturers

### Critical (Must Have - Software Modules for Customer Certification)
- ✅ **Completed:** Complete CAPA workflow (root cause, corrective action, verification)
- ✅ **Completed:** Document approval workflow with handwritten signature capture
- ✅ **Completed:** DMS module with dashboard, detail pages, and approval integration
- ✅ **Completed:** Training records (TrainingRecordsPage, TrainingTypesPage, TrainingDashboardPage) - needs alerting logic
- ✅ **Completed:** Calibration tracking (CalibrationRecordsPage, CalibrationDashboardPage) - needs alerting logic
- ✅ **Completed:** Export UI (ModelEditorPage auto-shows export button)
- ✅ **Completed:** Quality dashboards with live API data:
    - Executive dashboard (`/analysis`) with KPIs, FPY trend, Pareto, needs attention
    - Defect analysis (`/quality/defects`) with trend, filters, records table
    - NCR analysis (`/quality/ncrs`) with trend, aging, disposition breakdown

**Status: All critical modules complete including UI. Training and Calibration need due date alerting (Celery beat tasks).**

### Nice-to-Have (Can Defer to Post-Pilot)
- Internal audit management - customers can use Word/checklists or outsource
- Management review module - customers can hold meetings and upload minutes as Documents
- Customer complaint tracking - can use CAPA workflow initially
- Supplier quality basics (AVL) - industry-specific, not all customers need it

### Enables:
- 🔶 **Customers can achieve ISO 9001 certification** - pending alerting tasks only
- 🔶 Deploy to Segment A - pending Celery beat alerting tasks
- ✅ All critical QMS modules complete with UI (CAPA, Docs, Quality, Traceability, NCR, Reporting, Training, Calibration)
- 🔶 Training & Calibration need: Celery beat alerting tasks only
- ✅ Pricing: $50-60K/year base tier
- ✅ Can support automotive SPC requirements (completed ahead of schedule)
- 🔶 Material lot traceability backend complete (MaterialLot, MaterialUsage) - needs UI

---

## Phase 3: Pilot-Ready for Segment B (Automotive Tier 2-3) 🔶 SPC COMPLETE

**Target Segments:** Segment A + Segment B (ISO 9001 + Automotive)

**Goal:** Add automotive-specific requirements for IATF 16949 foundation

### Critical (Must Have - Automotive Requirements)
- ✅ SPC with Cpk/Ppk and Western Electric rules (See Section 14)
- 🔴 Supplier quality management (See Section 12: Supplier Management)
- 🔴 Change management - ECO/ECR workflow (See Section 12: Change Management)

### High Value (Automotive Competitive Features)
- 🔶 **PPAP** - ~50% COVERAGE (4/18 complete, 7 partial, 5 missing). See Section 12 for full breakdown.
  - ✅ Have: Design records, process flow, dimensional results (SPC), Cpk/Ppk
  - 🔶 Partial: FMEA storage, control plan storage, ECN docs, test results, lab docs, checking aids
  - 🔴 Need: PSW generation, submission tracker, MSA/Gage R&R, customer approval, AAR, customer-specific requirements

### Medium Value (Nice to Have)
- Assembly genealogy (BOM tracking) - depends on product complexity
- Advanced reporting (compliance reports, audit packages)
- 🟡 Wire ProcessFlowPage to actual Process/Step data (currently hardcoded demo)

**Status: SPC module complete. PPAP ~50% coverage (4 complete, 7 partial, 5 missing). Supplier and Change Management remain for full automotive support.**

### Enables:
- 🔶 Deploy to Segment B - pending Supplier & Change Management modules
- 🔶 Support IATF 16949 certification foundation - SPC ready, needs supplier/change mgmt
- ✅ Pricing: $70-80K/year (base + automotive modules)
- 🔶 Scale to 5-10 customers - can start with SPC-focused customers
- ❌ Cannot yet support aerospace (needs FAI, material traceability, full PPAP)

---

## Phase 4: Aerospace Expansion (Segment C - DEFERRED)

**Target Segments:** Segment A + Segment B + Segment C (Add AS9100D)

**Goal:** Enter aerospace market after automotive foundation is proven

### Critical (Must Have - AS9100D Requirements)
- Material lot tracking and C of C generation (See Section 12: Material Lot Traceability)
- First Article Inspection (FAI) - leverage existing 3D annotation system (See Section 12: FAI)
- Full PPAP (Production Part Approval Process) (See Section 12: PPAP)
- Special process controls (See Section 12: Special Process Controls)

### High Value (Aerospace Competitive Features)
- Assembly genealogy and recall simulation
- Counterfeit prevention (See Section 12: Counterfeit Prevention)
- Customer source inspection (See Section 12: Customer Source Inspection)

### Medium Value (Defense-Specific)
- Export control flagging - ITAR/ECCN (See Section 12: Export Control)
- Customer/government property tracking

### Enables:
- ✅ Deploy to Segment C (aerospace primes, tier suppliers, defense)
- ✅ Support AS9100D certification audits
- ✅ Pricing: $90-120K/year (base + automotive + aerospace modules)
- ✅ Full market coverage (general, automotive, aerospace)

---

## Feature Sponsorship Opportunities

**Certain expensive features can be fast-tracked if customer sponsors development:**

### Sponsorable Features (Phase 3-4)
- **Supplier Management** ($30-35K sponsorship) - Then $12K/year module fee
- **Advanced SPC** ($25-30K sponsorship) - Then $10K/year module fee
- **First Article Inspection** ($30-35K sponsorship) - Then $15K/year module fee
- **Material Traceability + C of C** ($25-30K sponsorship) - Then $12K/year module fee
- **Assembly Genealogy** ($30-40K sponsorship) - Then $12K/year module fee

### How It Works:
1. First customer pays development fee + annual module fee
2. Customer gets feature priority, delivery timeline commitment, design input
3. Future customers pay only annual module fee (no development fee)
4. Sponsoring customer gets 6-12 month competitive advantage

---

## Strategic Decision Points

### After Phase 1 (Demo-Ready):
**Question:** Do we have 10-15 discovery calls showing interest from Segment A?
- **Yes** → Proceed to Phase 2 (build for ISO 9001)
- **No** → Revisit positioning, target different segment, or improve demos

### After Phase 2 (Segment A Pilots):
**Question:** Do we have 2-3 paying pilot customers (Segment A) using the system?
- **Yes** → Choose: Scale Segment A OR expand to Segment B (automotive)
- **No** → Fix product-market fit issues before expanding scope

### After Phase 3 (Segment B Ready):
**Question:** Do we have 5-10 customers across Segments A and B generating $400-600K ARR?
- **Yes** → Choose: Scale automotive OR expand to aerospace (Segment C)
- **No** → Focus on retention, referrals, and go-to-market before new segments

### **Hardest Implementation Challenges**

1. **Supplier Management** - Broad scope, requires external coordination, performance metrics, incoming inspection workflow
2. **Training Management** - Enforcement complexity, competency verification, step-level restrictions, integration with process workflows
3. **First Article Inspection** - AS9102 forms complexity, multi-stakeholder approval workflow (NOTE: 3D annotation integration is straightforward - reuses existing system)

### **Quickest Compliance Wins**

1. **Export Buttons** - operational improvement
2. **Group Admin UI** - completes RBAC implementation

**Last Updated:** February 18, 2026
