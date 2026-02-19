# Ambac Quality Management System (Pizza Tracker)

## Project Overview

A comprehensive Quality Management System for manufacturing diesel fuel injectors for military applications. Built to handle parts tracking, quality control, and compliance requirements (ISO 9001, AS9100D, ITAR) with an integrated **AI digital coworker** powered by LangGraph and local LLMs.

**Known As:** "Pizza Tracker" (inspired by Domino's Pizza order tracking, but for manufacturing parts)

---

## Core Technology Stack

### Backend
- **Django 5.1** - REST API, admin interface, business logic
- **Django REST Framework** - API endpoints with OpenAPI/Swagger docs
- **PostgreSQL** - Primary database with pgvector extension for AI embeddings
- **Celery + Redis** - Async task processing, scheduled jobs, notifications
- **Ollama** - Local LLM inference server (default: llama3.1:8b)

### Frontend
- **React 19** - UI framework
- **Vite** - Build tool and dev server
- **TanStack Router** - Type-safe routing
- **TanStack Query** - Server state management
- **Tailwind CSS** - Styling
- **assistant-ui** - LLM chat interface components
- **Three.js / React Three Fiber** - 3D visualization

### AI/ML Stack
- **LangGraph** - Agent orchestration (separate Python service)
- **LangChain** - LLM tooling and integrations
- **pgvector** - Vector similarity search (PostgreSQL extension)
- **nomic-embed-text** - Embedding model (via Ollama)

### Deployment
- **Local Development:** Docker Compose (full stack)
- **Production:** Azure App Services (3-tier: Django + Celery Worker + Celery Beat)
- **Shared Infrastructure:** PostgreSQL with pgvector, Redis, Azure Storage
- **Network:** `ambactracker-network` (Docker bridge for service communication)

---

## Architecture Overview

### System Architecture

```
┌─────────────────┐
│  React Frontend │ (Vite dev server / Azure Static Web App)
└────────┬────────┘
         │ HTTP/REST
         ├──────────────────────────────┐
         │                              │
┌────────▼────────┐            ┌────────▼────────┐
│  Django API     │◄───────────┤  LangGraph API  │
│  (Port 8000)    │  Tool Call │  (Agent Server) │
└────────┬────────┘            └────────┬────────┘
         │                              │
         │                              │
         ├──────────────┬───────────────┤
         │              │               │
┌────────▼────────┐ ┌──▼──────────────┐ ┌──────▼──────┐
│  PostgreSQL +   │ │  Redis          │ │   Ollama    │
│    pgvector     │ │ - Celery Broker │ │ (LLM/Embed) │
│ - App Data      │ │ - Cache         │ └─────────────┘
│ - Celery Results│ │ - Task Queue    │
└────────┬────────┘ └────────┬────────┘
         │                   │
         │                   │
         └──────────┬────────┘
                    │
           ┌────────▼────────┐
           │ Celery Workers  │
           │  - Worker       │ (async processing, reads from Redis queue)
           │  - Beat         │ (scheduled jobs)
           └─────────────────┘
                    │
                    └─────► Reads/Writes to PostgreSQL (results backend + task data)
```

### Request Flow Examples

**User asks AI: "What parts are quarantined?"**
```
User → React UI → LangGraph Agent → query_database() tool
→ Django API (/api/ai/query/execute_read_only/)
→ PostgreSQL → Response with quarantined parts
```

**User searches: "quality inspection procedure"**
```
User → React UI → LangGraph Agent → search_documents_semantic() tool
→ Django API (/api/ai/embedding/embed_query/ + /api/ai/search/vector_search/)
→ PostgreSQL pgvector similarity search → Relevant doc chunks
```

---

## Key Features

### 1. Manufacturing Operations & Traceability

#### Parts Tracking
- **Serial Number Tracking:** Every part has unique `ERP_id` tracked through all manufacturing steps
- **Status Management:** 11 distinct part statuses (Pending, In Progress, Awaiting QA, Quarantined, Completed, Scrapped, etc.)
- **Step Transitions:** Automatic logging of part movement through process steps with operator attribution
- **Version History:** Full audit trail of part status changes via django-auditlog

#### Work Order Management
- **Batch Production:** Work orders manage production runs with quantity tracking
- **ERP Integration:** External system identifiers for order synchronization
- **CSV Import:** Bulk work order creation from ERP exports
- **Progress Tracking:** Real-time completion status and actual vs. expected completion dates

#### Process & Workflow Management
- **Configurable Processes:** Multi-step manufacturing workflows per part type
- **Step Definitions:** Each step includes duration estimates, descriptions, operator instructions
- **Process Versioning:** Track changes to manufacturing processes over time
- **Linear Workflows:** Current implementation (planned: dynamic acyclic graphs for branching paths)

#### Part Types & Design Management
- **Product Versioning:** Track different revisions of product designs
- **ID Prefix System:** Auto-generated part serial numbers with configurable prefixes
- **Process Assignment:** Each part type linked to its manufacturing process
- **Document Attachments:** Specifications, drawings, work instructions via generic relations

---

### 2. Quality Control & Inspection

#### Quality Reporting
- **Per-Part Inspections:** Individual quality reports for each manufactured part
- **Measurement Tracking:**
  - Configurable measurement definitions per step (nominal, tolerance, units)
  - Actual measurement results with pass/fail validation
  - Support for numeric measurements and visual pass/fail checks
- **Operator & Equipment Logging:** Track who inspected with which equipment
- **Status Recording:** Pass, Fail, or Pending with detailed notes

#### Statistical Sampling System
One of the most sophisticated features - a flexible, rule-based sampling engine:

**Sampling Rules:**
- **Periodic Sampling:** Every Nth part (e.g., "inspect every 10th part")
- **Percentage Sampling:** Random sampling at X% rate
- **Threshold Sampling:** First N parts, then reduce frequency
- **Combined Rules:** Stack multiple rules (e.g., "first 5, then every 20th")

**Sampling Rule Sets:**
- Per part type, process, and step configuration
- Priority-based rule ordering
- Origin tracking (inherited, fallback, or direct)
- Active/inactive toggles for easy management

**Fallback Mechanisms:**
- Automatic escalation when defect thresholds exceeded
- Configurable fallback duration (inspect N consecutive parts)
- State tracking per work order and step
- Audit logging with deterministic hash-based sampling decisions

**Analytics & Compliance:**
- Sampling analytics tracking (compliance rate, defects found)
- Audit logs for regulatory compliance (why was this part sampled/skipped?)
- Real-time sampling decisions based on quality trends

#### Equipment Management
- **Equipment Registry:** Machines and tools tracked with type classification
- **Usage Logging:** Equipment usage per part and step
- **Equipment-Specific Errors:** Link quality issues to specific equipment
- **Maintenance Tracking:** (Planned: calibration scheduling and certificates)

#### Error Classification
- **Predefined Error Types:** Per part type error definitions
- **Examples & Descriptions:** Reference documentation for each error type
- **Quality Report Integration:** Link errors to inspection results

---

### 3. Non-Conformance Management (NCR)

#### Quarantine Dispositions
Lightweight NCR workflow for managing quality failures:

**Workflow States:**
- **Open:** Newly created, awaiting assignment
- **In Progress:** QA staff investigating/resolving
- **Closed:** Resolution complete

**Disposition Types:**
- **Rework:** Send back for correction
- **Scrap:** Reject and discard
- **Use As-Is:** Accept with deviation
- **Return to Supplier:** Incoming material rejection

**Features:**
- Auto-creation on failed quality reports (via Django signal)
- Assignment to QA staff with notifications
- Rework attempt tracking per step (1st rework, 2nd rework, etc.)
- Resolution notes and completion timestamps
- Document attachments for evidence/photos
- Links to multiple quality reports

**Limitations:**
- Not a full CAPA system (no formal root cause analysis, corrective action plans)
- No effectiveness verification workflow
- No preventive action tracking

---

### 4. 3D Visual Quality Management

**One of the system's unique differentiators** - interactive 3D defect visualization.

#### 3D Model Management
- **CAD File Support:** Upload GLB, GLTF, OBJ, or STEP files
- **Auto-Conversion:** STEP/STP files automatically convert to web-friendly GLB format (via cascadio library)
- **Part Type Linking:** Associate 3D models with specific product designs
- **Process Step Models:** Optional: store models showing intermediate manufacturing states
- **Unique Constraint:** One model per part_type + step combination

#### Interactive Defect Annotation Tool
- **Click-to-Annotate:** QA inspectors click directly on 3D model to mark defect locations
- **Defect Attributes:**
  - **3D Position:** X, Y, Z coordinates in model space
  - **Defect Type:** Crack, Burn, Porosity, Overspray, etc.
  - **Severity:** Low, Medium, High, Critical
  - **Measurement Value:** Optional numeric measurement
  - **Notes:** Text description
- **Two Modes:**
  - **Navigate Mode:** Orbit camera, inspect model
  - **Annotate Mode:** Click to place markers
- **Batch Saving:** Create multiple annotations, then save all at once

#### Heat Map Visualization
GPU-accelerated WebGL visualization showing defect density:

**Visual Features:**
- **Custom GLSL Shaders:** Real-time rendering on graphics card
- **Color Gradient:** Blue (low) → Cyan → Green → Yellow → Red (high)
- **Inverse Distance Falloff:** Heat spreads from annotation points
- **Adjustable Parameters:**
  - Radius (0.1-2.0): How far heat spreads
  - Intensity (0-2.0): Heat strength multiplier
  - Toggle on/off for comparison
- **Performance:** Supports up to 50 annotations per model without lag
- **Lighting:** Basic diffuse lighting for depth perception

**Use Cases:**
- **Pattern Recognition:** Identify recurring defect locations (e.g., cracks always near flange)
- **Process Issues:** Visual clustering indicates fixture, tooling, or process problems
- **Training:** Show new QA inspectors common defect locations
- **First Article Inspection:** Document specific measurement points on reference parts
- **Root Cause Analysis:** Correlate defect locations with manufacturing parameters

**Integration (In Progress):**
- Planned: Flag part types to require 3D annotation as a manufacturing step
- Planned: Timestamp-based or configuration-driven annotation requirements
- Planned: Auto-link annotations to quality reports
- Planned: Block part advancement until required annotations complete

---

### 5. Document Control & Management

#### Document Storage & Versioning
- **Version Control:** Full document versioning system (previous_version chain, is_current_version flag)
- **Generic Relations:** Attach documents to any entity (orders, parts, steps, quality reports, dispositions, etc.)
- **File Organization:** Structured upload paths with date-based organization
- **Content Types:** Support for PDFs, images, spreadsheets, CAD files
- **Metadata:** File names, upload dates, uploader tracking, custom descriptions

#### Document Classification
**Security Levels:**
- **Public:** Accessible to all users including customers
- **Internal:** Internal use only
- **Confidential:** Sensitive business information
- **Restricted:** Serious impact if disclosed
- **Secret:** Critical impact if disclosed

**Access Control:**
- Document-level permissions based on user roles and classification
- Customer users only see "public" documents
- Audit logging of document access (via django-auditlog)

#### AI-Readable Documents
- **AI Embedding Flag:** Mark documents for AI processing
- **Auto-Embedding Signal:** When `ai_readable=True`, automatically triggers async embedding
- **Document Chunking:** Text split into ~1200 character chunks (max 40 per doc)
- **Vector Storage:** Embeddings stored in pgvector for semantic search
- **Chunk Metadata:**
  - `preview_text`: Short snippet for search results
  - `full_text`: Complete chunk content
  - `span_meta`: Chunk index for ordering and context windows
  - `embedding`: Vector representation (pgvector field)

---

### 6. AI Digital Coworker (LangGraph Agent)

**The "Pizza Tracker" signature feature** - a local AI assistant that acts as a digital coworker for manufacturing personnel.

#### Architecture

**Separate LangGraph Service:**
- Independent Python service running LangGraph API server
- ReAct (Reasoning and Action) agent pattern
- Simple graph structure: Agent Node ↔ Tools Node
- Streaming responses to React frontend via assistant-ui

**LLM Configuration:**
- **Default:** Ollama llama3.1:8b (local inference, no cloud dependency)
- **Alternatives:** Claude (Anthropic), GPT (OpenAI), or Fireworks AI
- **Embeddings:** nomic-embed-text via Ollama
- **Deployment:** Shared Docker network with Django backend

#### AI Capabilities - 5 Tools

**1. Database Query Tool (`query_database`)**
- Safe, read-only ORM queries to operational data
- Whitelisted models: Orders, Parts, WorkOrder, QualityReports, User, Companies, Steps, Processes, etc.
- Whitelisted operations: exact, contains, icontains, gt, lte, in, range, date filters
- Relationship traversals: `order__customer__username`, `part__work_order__ERP_id`
- Aggregations: count, (planned: max, min, avg)
- Security: Field validation, operation validation, max 100 results per query
- **Example:** "Show me all quarantined parts from work order 12345"

**2. Semantic Document Search (`search_documents_semantic`)**
- Vector similarity search using pgvector and cosine distance
- Best for: Conceptually related content, procedures, specifications
- Configurable similarity threshold (default: 0.7)
- Returns: Document name, similarity score, text excerpt
- **Example:** "Find quality inspection procedures for diesel injectors"

**3. Keyword Document Search (`search_documents_keyword`)**
- PostgreSQL full-text search with ranking
- Best for: Exact terms, part numbers, specific phrases
- Returns: Document name, relevance rank, text excerpt
- **Example:** "Find documents mentioning part ABC-123"

**4. Hybrid Search (`hybrid_search`)**
- Combines vector similarity + keyword search
- Deduplicates results, shows both score types
- Best for: Complex queries needing both semantic and exact matching

**5. Context Window Tool (`get_context`)**
- Retrieves surrounding chunks for a specific document chunk
- Useful when search result needs more context
- Configurable window size (default: 2 chunks before/after)
- Maintains chunk ordering via `span_meta.i` index

#### System Prompt Design

**Role:** Manufacturing expert assistant for Ambac Tracker

**Expertise Areas:**
- Production planning and scheduling
- Quality assurance and sampling procedures
- Equipment operation and maintenance
- ERP systems and part tracking
- Regulatory compliance and documentation
- Continuous improvement processes

**Behavioral Guidelines:**
- **Plan before acting:** Think through which tools to use
- **Use tools strategically:** Don't guess, retrieve real data
- **Combine sources:** Blend documentation with operational data
- **Persist until complete:** Keep searching if initial results insufficient
- **Evidence-based:** Always cite sources (document names, data from queries)
- **Safety-conscious:** Highlight safety considerations and regulatory requirements

**Communication Style:**
- Direct and clear (shop floor needs concise info)
- Practical (focus on actionable next steps)
- Honest (say "I don't know" if searches fail)

**Critical Constraints:**
- DO NOT fabricate data, procedures, or specifications
- DO NOT proceed with incomplete safety-critical information
- DO NOT assume current status - query database for real-time data
- ALWAYS back up recommendations with specific sources

#### Example Workflows

**Scenario 1: "How many parts failed QA this week?"**
1. Agent calls `query_database(model="QualityReports", filters={"status": "FAIL", "created_at__gte": "2025-10-20"})`
2. Django API validates request, executes safe ORM query
3. Returns count and details
4. Agent formats response: "12 parts failed QA this week. Most common error: Porosity (7 instances)."

**Scenario 2: "What's the procedure for heat treating?"**
1. Agent calls `search_documents_semantic(query="heat treating procedure")`
2. Django embeds query via Ollama (nomic-embed-text)
3. pgvector searches for similar document chunks
4. Returns top 5 results with excerpts
5. Agent summarizes: "According to SOP-045 Heat Treatment, parts must be heated to 350°F for 2 hours..."

**Scenario 3: "Why is part ABC-123 quarantined?"**
1. Agent calls `query_database(model="Parts", filters={"ERP_id__icontains": "ABC-123"})`
2. Finds part is quarantined, linked to quality report #456
3. Agent calls `query_database(model="QuarantineDisposition", filters={"part__ERP_id": "ABC-123"})`
4. Retrieves disposition details
5. Agent responds: "Part ABC-123 is quarantined due to failed quality report. Disposition NCR-789 assigned to QA staff John Doe. Reason: Surface porosity detected. Current status: In Progress."

#### Security & Authentication
- **Current:** AllowAny permissions with debug logging (development mode)
- **Planned:** Token-based authentication per user
- **Token Flow:** Frontend passes user's Django auth token → LangGraph → Django APIs
- **Data Access:** Respects Django's SecureManager filtering (user group-based permissions)

#### Deployment Architecture
```
Docker Network: ambactracker-network
├── Django (port 8000)
├── LangGraph API (langgraph.json config)
├── Ollama (port 11434, via host.docker.internal)
├── PostgreSQL + pgvector
└── Redis
```

**Azure Production:**
- LangGraph runs as separate App Service
- Ollama hosted on dedicated VM or container instance
- Shared PostgreSQL Flexible Server with pgvector extension

---

### 7. Business Integration & CRM

#### HubSpot Integration
- **Company Sync:** Sync customer data from HubSpot CRM
- **Deal Pipeline:** Update deal stages based on order status
- **Contact Management:** Import HubSpot contacts as users
- **Sync Logging:** Track all HubSpot API calls for debugging
- **Bidirectional Sync:** (Planned: push order updates back to HubSpot)

#### Customer Management
- **Company Registry:** Customer organizations with HubSpot API IDs
- **User-Company Linking:** Associate users with parent companies
- **Customer Portal:** Customers can view their orders, parts, and documents
- **Customer Login:** Dedicated login interface for external customers
- **Customer Invitation System:** Invite customers to create accounts and access their order data
- **Read-Only Access:** Customers can view but not modify orders, parts, quality reports, and public documents
- **Data Isolation:** SecureManager ensures customers only see data linked to their parent company
- **Notification Preferences:** Full system for customer notification management
  - Backend: NotificationTask model with NotificationPreferenceViewSet (timezone handling, scheduling)
  - Frontend: Customer notification preference UI (completed)
  - Email infrastructure: Celery + Redis async delivery
  - Planned enhancements:
    - Automatic HubSpot gate progress notifications (deal stage changes)
    - Automatic production milestone notifications (order status changes)
    - Customizable frequency options (real-time, daily digest, weekly summary, disabled)

#### Order Management
- **Order Tracking:** Customer orders with status workflow
- **External Identifiers:** Link to ERP systems (e.g., SAP order numbers)
- **Estimated Completion:** Due date tracking and alerts
- **Customer Assignment:** Orders linked to customer users
- **Status Updates:** Trigger HubSpot deal stage changes

---

### 8. User Management & Authentication

#### User Onboarding
- **Invitation System:** Secure token-based user invitations via UserInvitation model
  - Admin generates invitation tokens with email and optional company assignment
  - Tokens have expiration dates for security
  - Single-use tokens prevent reuse
  - Track invitation status (pending, accepted, expired)
- **Self-Registration:** Public signup page for new users (SignupPage.tsx)
  - Email and password-based registration
  - Optional invitation token for company linking
  - Email verification (if configured)
- **Company Assignment:** Users automatically linked to parent company from invitation

#### Authentication & Password Management
- **Login System:** Token-based authentication (Django REST Framework)
  - Username/email + password login
  - Returns authentication token for API access
  - Token stored in browser for session persistence
- **Password Reset:** Self-service password reset workflow
  - Request reset via email (PasswordResetRequestForm)
  - Secure reset token sent to registered email
  - Confirm reset with new password (PasswordResetConfirmForm)
  - Time-limited reset tokens for security

#### User Profile Management
- **Profile Page:** Users can view and edit their profile (UserProfilePage.tsx)
  - Update personal information
  - Change password
  - View assigned company
  - View group membership (Admin, Manager, Operator, Employee, Customer)
- **User Administration:** Admin users can manage all users via UserViewSet
  - Create, update, deactivate users
  - Assign users to groups
  - Link users to companies
  - View user activity via audit logs

#### Session Management
- **Token Persistence:** Authentication tokens stored in browser local storage
- **Logout:** Clear authentication token and redirect to login
- **Session Security:** Tokens validated on every API request
- **Token Expiration:** Configurable token lifetime (default: no expiration, but can be configured)

---

### 9. Audit Trail & Compliance

#### Comprehensive Audit Logging
- **django-auditlog Integration:** Automatic logging on all SecureModel changes
- **Change Tracking:** Before/after values for every field modification
- **User Attribution:** Who made each change (via request context)
- **Timestamp Precision:** Exact datetime of every modification
- **Bulk Operation Logging:** Special handling for bulk deletes/restores
- **Read-Only Access:** Audit logs cannot be modified after creation

#### Soft Delete Pattern
- **Archive Instead of Delete:** All models use `archived` flag
- **Recovery Capability:** Restore soft-deleted records with full history
- **Archive Reasons:** Optional reason codes for deletions
- **Hard Delete Option:** Actual database deletion available when needed (e.g., GDPR compliance)

#### Version Control
Every SecureModel includes:
- `version` field (auto-incrementing)
- `previous_version` ForeignKey (chain to earlier versions)
- `is_current_version` boolean flag
- `create_new_version()` method for creating revisions
- `get_version_history()` to retrieve full version chain

#### Compliance Support
**Currently Implemented:**
- ✅ User authentication and authorization (Django auth)
- ✅ Role-based access control (Admin, Manager, Operator, QA, Customer groups)
- ✅ Document version control and classification
- ✅ Parts traceability (serial numbers, order relationships)
- ✅ Quality inspection workflows and sampling
- ✅ Audit logging for all changes
- ✅ FIPS compliance (via Azure infrastructure: Disk Encryption, TLS, PostgreSQL TDE)

**Standards Support:**
- **ISO 9001:2015** - Quality management system fundamentals
- **AS9100D** - Aerospace quality management (manufacturing focus)
- **ITAR** - Export control tracking (planned)
- **ISO 27001** - Information security (partial implementation)

**Gaps (Known):**
- ❌ Training tracking (no training records, certifications, competency tracking)
- ❌ Supplier management (no supplier qualification, approval, performance tracking)
- ❌ Full CAPA workflow (no formal root cause analysis, corrective action plans)
- ❌ FAI (First Article Inspection) dedicated workflow
- ❌ Calibration tracking (no calibration scheduling, due dates, certificates)
- ❌ Export control flagging (ITAR/ECCN classification fields)
- ❌ Multi-factor authentication (SAML configured but not enforced)

---

### 10. Access Control & Security

#### Role-Based Access Control (RBAC)

**User Groups:**
1. **Admin:** Full system access, all CRUD operations
2. **Manager:** Full data access, limited admin functions
3. **Operator:** All work data access, no customer filtering
4. **Employee:** Document access based on classification level (used for document permissions)
5. **Customer:** Limited to own orders, parts, and public documents

**Note:** Admin, Manager, and Operator have full access to manufacturing data. Customer users are restricted to their own company's data. Employee group is specifically used for document classification-based permissions.

**SecureManager Pattern:**
Unified manager for all models providing:
- Automatic user-based filtering via `for_user()` method
- Soft delete support (`active()`, `deleted()`)
- Version filtering (`current_versions()`, `all_versions()`)
- Combined filters (`active_current()`, `for_user_current()`)

**Data Isolation:**
- Superusers and Admins see everything
- Operators see all work data (no customer filtering)
- Customers only see data linked to their parent company:
  - Orders where `customer=user`
  - Parts via `order__customer=user`
  - Work orders via `related_order__customer=user`
  - Quality reports via `part__order__customer=user`
  - Documents marked "public" classification

#### Security Features
- **Token Authentication:** Django REST Framework token auth
- **HTTPS/TLS:** Encrypted transport (production)
- **Secure Cookies:** HTTP-only, secure flags enabled
- **CORS Configuration:** Whitelisted origins only
- **SQL Injection Protection:** ORM-based queries, parameterized SQL
- **XSS Protection:** React auto-escaping, CSP headers
- **Password Hashing:** PBKDF2 (FIPS-approved when using FIPS-validated OpenSSL)

---

### 11. Notifications & Alerts

#### Celery-Based Notification System
- **Email Notifications:** Primary channel (SMTP configuration)
- **Async Processing:** Non-blocking notification delivery
- **Retry Logic:** Automatic retry on transient failures
- **Template System:** HTML email templates

#### Notification Types (Planned)
- **Weekly Reports:** Recurring order summaries
- **CAPA Reminders:** Deadline-based escalation notifications
- **Quality Alerts:** Failed inspections, quarantine dispositions
- **Order Updates:** Status changes notify customers

#### NotificationTask Model
Supports:
- **Fixed Interval:** Weekly, daily, monthly recurring notifications
- **Deadline-Based:** Escalating reminders as deadline approaches
- **Multi-Channel:** Email, in-app, SMS (structure ready, email implemented)
- **Status Tracking:** Pending, sent, failed, cancelled

---

### 12. Excel Import/Export

#### Excel Export (All Major Entities)
- **ExcelExportMixin:** Applied to most ViewSets
- **One-Click Export:** Export filtered data to .xlsx
- **Formatted Output:** Headers, data types, column widths
- **Large Datasets:** Streaming export for performance

#### CSV Import
- **Work Order Import:** Bulk upload work orders from ERP exports
- **Validation:** Pre-import validation with error reporting
- **Error Handling:** Clear error messages for malformed data

---

## Data Models (Core Entities)

### Manufacturing
- **Orders** - Customer orders with status workflow
- **Parts** - Individual manufactured items (serial number tracking)
- **WorkOrder** - Production batches
- **PartTypes** - Product designs and revisions
- **Processes** - Manufacturing workflow definitions
- **Steps** - Individual process stages
- **StepTransitionLog** - Part movement history

### Quality
- **QualityReports** - Inspection results per part
- **MeasurementDefinition** - Measurement specs per step
- **MeasurementResult** - Actual measurements vs. specs
- **QualityErrorsList** - Error type definitions
- **QuarantineDisposition** - NCR workflow for failures
- **SamplingRule** - Sampling logic definitions
- **SamplingRuleSet** - Sampling configuration per part/process/step
- **SamplingTriggerState** - Active sampling state tracking
- **SamplingAnalytics** - Sampling effectiveness metrics
- **SamplingAuditLog** - Sampling decision audit trail
- **ThreeDModel** - 3D CAD files for visualization
- **HeatMapAnnotations** - Defect locations on 3D models

### Equipment
- **Equipments** - Machine and tool registry
- **EquipmentType** - Equipment classification
- **EquipmentUsage** - Equipment usage per part/step

### Business
- **Companies** - Customer organizations
- **User** - Extended Django user with company linking
- **UserInvitation** - Secure user onboarding tokens
- **Documents** - File storage with versioning and classification
- **DocChunk** - Document chunks with vector embeddings
- **ExternalAPIOrderIdentifier** - ERP system order IDs
- **HubSpotSyncLog** - CRM integration audit trail
- **NotificationTask** - Notification scheduling and tracking

### System
- **ArchiveReason** - Soft delete reason tracking
- **QaApproval** - QA staff approval records

---

## Deployment Environments

### Local Development (Docker Compose)

**Services:**
- Django backend (port 8000)
- PostgreSQL with pgvector
- Redis (Celery broker)
- Celery worker (background tasks)
- Celery beat (scheduled jobs)
- Ollama (LLM inference, port 11434)
- LangGraph API (agent server)
- React frontend (Vite dev server, port 5173)

**Configuration:**
- `.env` files for sensitive config
- `docker-compose.yml` orchestration
- Shared Docker network: `ambactracker-network`
- Volume mounts for development hot reload

### Azure Production

**App Services:**
1. **Django Backend** - Python 3.11, Gunicorn, REST API
2. **Celery Worker** - Background task processing
3. **Celery Beat** - Scheduled job coordinator
4. **(Planned) LangGraph API** - Agent server

**Data Services:**
- **Azure Database for PostgreSQL Flexible Server** - With pgvector extension
- **Azure Cache for Redis** - Celery broker and cache
- **Azure Storage Account** - Media files (documents, 3D models, uploads)

**Compute:**
- **(Planned) Azure Container Instance or VM** - Ollama LLM server

**Networking:**
- Virtual Network (VNet) for service isolation
- Private endpoints for database and Redis
- Application Gateway or Front Door for routing

**Security:**
- Azure Key Vault for secrets
- Managed identities for service authentication
- Azure Disk Encryption (FIPS 140-2 validated)
- TLS 1.2+ enforced

---

## Current Status

### ✅ Production Ready
- Core manufacturing operations (parts, work orders, processes)
- Quality inspection workflows
- Statistical sampling system
- Document management with AI embeddings
- LangGraph AI assistant (local LLM)
- Audit logging and soft deletes
- Role-based access control (5 user groups)
- User management (invitations, signup, password reset, profile)
- 3D defect visualization tool
- HubSpot CRM integration
- Excel import/export

### 🔶 In Progress
- 3D annotation as required manufacturing step (workflow integration)
- Compliance reporting and analytics
- Export control (ITAR) flagging
- Enhanced security features (MFA, advanced audit analytics)

---

## Development Roadmap

Features are organized into three priority tiers:
- **🔴 Needed:** Critical for compliance, operations, or customer requirements
- **🟡 Nice to Have:** Valuable improvements that enhance efficiency and capabilities
- **🟢 Yacht Problems:** Advanced features to implement when everything else is done

---

## 🔴 Tier 1: Needed (Critical)

### QMS Compliance Features

**CAPA (Corrective and Preventive Action)**
- ✅ **Completed:** Basic NCR workflow (QuarantineDisposition model)
- ❌ **Needed:** Full CAPA workflow:
  - Root cause analysis tools (5 Whys, Fishbone diagrams)
  - Corrective action plan tracking with assignments and due dates
  - Preventive action identification and implementation
  - Effectiveness verification and closure criteria
  - Recurrence tracking and trend analysis
  - Integration with audit findings and customer complaints

**Training & Competency Management**
- ❌ **Needed:** Training records and certifications
- ❌ **Needed:** Competency matrix per role and operation
- ❌ **Needed:** Training due date tracking and alerts
- ❌ **Needed:** Training effectiveness verification
- ❌ **Needed:** On-the-job training (OJT) documentation
- ❌ **Needed:** Integration with part/step restrictions (only trained users can perform operations)

**Calibration Tracking**
- ❌ **Needed:** Equipment calibration scheduling
- ❌ **Needed:** Calibration due date alerts
- ❌ **Needed:** Calibration certificate storage and version control
- ❌ **Needed:** Out-of-calibration equipment lockout (prevent use in quality reports)
- ❌ **Needed:** External calibration vendor tracking
- ❌ **Needed:** Measurement uncertainty tracking

**First Article Inspection (FAI)**
- ❌ **Needed:** AS9102 form generation (Form 1, 2, 3)
- ❌ **Needed:** FAI workflow with assignment and approval
- ❌ **Needed:** Measurement result tracking per characteristic
- ❌ **Needed:** Ballooned drawing integration
- ❌ **Needed:** FAI validity tracking (expiry on design changes)
- ❌ **Needed:** Customer FAI approval workflow

**Supplier Management**
- ❌ **Needed:** Supplier registry with contact information
- ❌ **Needed:** Supplier qualification and approval workflow
- ❌ **Needed:** Incoming inspection workflow
- ❌ **Needed:** Approved supplier lists per part type/material

**Compliance Reporting**
- ❌ **Needed:** Audit-ready exports (ISO 9001, AS9100D)
- ❌ **Needed:** Sampling compliance reports
- ❌ **Needed:** Training compliance by role

### Novel Features - Core Completion

**3D Visual Quality Management**
- ✅ **Completed:** 3D defect annotation tool with click-to-mark interface
- ✅ **Completed:** GPU-accelerated heat map visualization (WebGL shaders)
- ✅ **Completed:** STEP/STP to GLB auto-conversion via cascadio
- 🔶 **In Progress:** Workflow integration - flag part types to require 3D annotation as manufacturing step
- ❌ **Needed:** Auto-link annotations to quality reports and prevent part advancement until complete

**AI Digital Coworker**
- ✅ **Completed:** ReAct agent with 5 tools (database query, semantic/keyword/hybrid search, context window)
- ✅ **Completed:** Local LLM deployment (Ollama with llama3.1:8b)
- ✅ **Completed:** Streaming chat interface with assistant-ui
- 🔶 **In Progress:** Per-user authentication and data access control

---

## 🟡 Tier 2: Nice to Have (Enhancement)

### QMS Enhancements

**Setup & Changeover Tracking**
- ❌ **Nice to Have:** Setup documentation per equipment and part type
- ❌ **Nice to Have:** Setup approval workflow
- ❌ **Nice to Have:** Setup verification checklists
- ❌ **Nice to Have:** First piece inspection integration

**Supplier Management - Advanced**
- ❌ **Nice to Have:** Supplier performance metrics (on-time delivery, quality metrics)
- ❌ **Nice to Have:** Supplier corrective action requests (SCAR)
- ❌ **Nice to Have:** Supplier portal for order visibility and document exchange

**Dynamic Process Workflows (DAG)**
- ✅ **Completed:** Linear process workflows
- ❌ **Nice to Have:** Acyclic graph workflows for branching/conditional paths
- ❌ **Nice to Have:** Decision nodes (pass/fail routing, conditional steps)
- ❌ **Nice to Have:** Parallel step execution
- ❌ **Nice to Have:** Process flow visualization and editing UI

**Basic Analytics & Dashboards**
- ❌ **Nice to Have:** Shop floor real-time dashboards:
  - Parts status distribution (pie chart)
  - Work order progress (Gantt chart)
  - Equipment utilization (heatmap)
- ❌ **Nice to Have:** Quality analytics:
  - Statistical Process Control (SPC) charts (X-bar, R charts)
  - Pareto analysis for defect types
  - Defect trend analysis over time
- ❌ **Nice to Have:** Management KPIs:
  - First Pass Yield (FPY)
  - On-time delivery rate

### AI Enhancements - Practical

**Tool Expansion**
- ✅ **Completed:** 5 core tools (database query, semantic/keyword/hybrid search, context window)
- ❌ **Nice to Have:** Report generation tool (PDF exports, PPAP packages, audit reports)
- ❌ **Nice to Have:** Chart/graph generation tool (SPC charts, Pareto diagrams)
- ❌ **Nice to Have:** File analysis tool (parse uploaded documents, extract data)

**Natural Language Workflows**
- ❌ **Nice to Have:** Guided troubleshooting - interactive decision trees for common issues
- ❌ **Nice to Have:** Procedure walkthroughs - step-by-step guidance through SOPs

**Advanced Reasoning**
- ❌ **Nice to Have:** Root cause analysis assistance - guide users through structured RCA processes
- ❌ **Nice to Have:** Regulation interpretation - answer compliance questions with citations

**Performance & Deployment**
- ❌ **Nice to Have:** Model fine-tuning - train on company-specific data (local only)
- ❌ **Nice to Have:** Performance optimization - caching, response streaming, parallel tool execution

### Novel Features - Enhancement

**Advanced Statistical Sampling**
- ✅ **Completed:** Rule-based sampling engine (periodic, percentage, threshold, combined)
- ✅ **Completed:** Automatic fallback on defect thresholds
- ✅ **Completed:** Audit trail for sampling decisions
- ❌ **Nice to Have:** Risk-based sampling - higher inspection rates for critical characteristics
- ❌ **Nice to Have:** Supplier-driven sampling - adjust rules per supplier performance

**3D Quality - Pattern Recognition**
- ❌ **Nice to Have:** Pattern recognition AI - detect recurring defect locations and suggest root causes
- ❌ **Nice to Have:** Multi-part comparison - overlay heat maps from multiple parts to identify systemic issues

---

## 🟢 Tier 3: Yacht Problems (Advanced/Future)

### MES-Lite Features (Full Manufacturing Execution System)

**Shop Floor Execution**
- ❌ **Yacht:** Shop floor scheduling and dispatching
- ❌ **Yacht:** Real-time work center status and capacity tracking
- ❌ **Yacht:** Work-in-progress (WIP) tracking and visualization
- ❌ **Yacht:** Resource allocation and optimization
- ❌ **Yacht:** Cycle time tracking and analysis
- ❌ **Yacht:** Bottleneck identification and alerting
- ❌ **Yacht:** Production variance reporting (actual vs. planned)
- ❌ **Yacht:** Integration with process DAGs for dynamic routing

**Advanced Analytics & BI**
- ❌ **Yacht:** Changeover time tracking for OEE calculations
- ❌ **Yacht:** Overall Equipment Effectiveness (OEE) full implementation
- ❌ **Yacht:** Cost of quality tracking (scrap, rework, inspection costs)
- ❌ **Yacht:** Customer complaint rates and tracking
- ❌ **Yacht:** Operator activity timeline analysis

### AI Digital Coworker - Advanced Intelligence

**Proactive Intelligence**
- ❌ **Yacht:** Anomaly detection - flag unusual quality trends before they become problems
- ❌ **Yacht:** Scheduled insights - daily/weekly summary reports delivered proactively
- ❌ **Yacht:** Threshold monitoring - alert when KPIs exceed limits
- ❌ **Yacht:** Predictive maintenance - suggest equipment service based on usage patterns
- ❌ **Yacht:** Compliance monitoring - warn about approaching training/calibration due dates

**Multi-Modal Capabilities**
- ❌ **Yacht:** Image analysis - identify defects from photos, read part markings
- ❌ **Yacht:** CAD drawing interpretation - answer questions about technical drawings
- ❌ **Yacht:** Video analysis - extract information from training videos, procedure demonstrations
- ❌ **Yacht:** Audio transcription - convert voice memos to searchable text

**Advanced Features**
- ❌ **Yacht:** Voice interface - shop floor voice commands and responses
- ❌ **Yacht:** Natural language report generation - "Generate a PPAP package for part ABC-123"
- ❌ **Yacht:** Process optimization suggestions - identify bottlenecks and improvement opportunities
- ❌ **Yacht:** Historical context - "How does this compare to last quarter's data?"
- ❌ **Yacht:** A/B testing - compare model performance on common queries

**Knowledge Management - Advanced**
- ✅ **Completed:** Document embedding and semantic search
- ❌ **Yacht:** Knowledge graph - build relationships between procedures, parts, equipment
- ❌ **Yacht:** Best practice recommendations - learn from historical successes
- ❌ **Yacht:** Tribal knowledge capture - extract knowledge from operator conversations

### Statistical & Predictive Analytics

**Machine Learning Features**
- ❌ **Yacht:** Machine learning-optimized sampling - adjust rules based on historical defect patterns
- ❌ **Yacht:** Predictive quality analytics - ML models predict defect likelihood based on historical patterns

---

## Security & Data Sovereignty Policies

- 🔒 **Policy:** No cloud LLM services - data is too sensitive for external APIs
- 🔒 **Policy:** No AI data modification - all create/update/delete operations require human approval
- 🔒 **Policy:** Read-only AI access - LLM tools limited to queries and analysis only

---

## Known Limitations

### Feature Gaps
- No multi-tenancy (single company deployment)
- No real-time WebSocket updates (planned)
- Linear processes only (no branching workflows)
- Limited CAPA functionality (basic NCR only)
- No preventive maintenance scheduling
- No supplier portal
- No mobile app (web responsive only)

### Technical Debt
- New workflow for 3D render workflow management
- Rework LangGraph system for DocChunks to be treated as tightly as Docs
- LangGraph authentication needs tightening
- Limited error handling in some async tasks
- Frontend could benefit from more comprehensive E2E tests
- Some complex queries could be optimized with database indexes

### Code Bugs & Inconsistencies
- **Case sensitivity bug (models.py:1974):** Uses lowercase `'customer'` instead of `'Customer'` for group check
- **Missing "Employee" group:** Documents model references "Employee" group that is never created by management commands (create_basic_groups.py, populate_test_data.py only create: Admin, Manager, Operator, Customer)
- **Group inconsistency:** SecureManager uses 4 groups (Admin, Manager, Operator, Customer) but Documents model assumes 5 groups (adds Employee)

### Scalability Considerations
- Ollama LLM inference can be CPU-intensive (consider GPU acceleration)
- pgvector similarity search slows with millions of chunks (need index tuning)
- Celery task queue needs monitoring at high volume
- Document embedding is async but can create backlog with bulk uploads

---

## Why "Pizza Tracker"?

Inspired by Domino's Pizza order tracking, the name reflects the system's ability to track parts through manufacturing with real-time status updates - just like tracking a pizza from order to delivery. The AI assistant acts like a helpful coworker you can ask "where's my pizza?" (part) at any time.

---

## Project Statistics

- **Database Models:** 35+ core models
- **API Endpoints:** 100+ REST endpoints
- **React Components:** 200+ components
- **Supported File Types:**
  - Documents: PDF, DOCX, images
  - 3D Models: GLB, GLTF, OBJ, STEP/STP
- **Deployment Targets:** Docker Compose (local), Azure App Services (production)

---

## Quick Start

### Local Development
```bash
# Start all services
docker-compose up -d

# Apply migrations
docker-compose exec backend python manage.py migrate

# Create superuser
docker-compose exec backend python manage.py createsuperuser

# Access services
# Django Admin: http://localhost:8000/admin
# API Docs: http://localhost:8000/api/schema/swagger-ui/
# Frontend: http://localhost:5173
# LangGraph Studio: langgraph dev (in LangGraph directory)
```

### Azure Deployment
See `azure/README.md` for detailed deployment instructions including:
- Resource provisioning scripts
- Database setup with pgvector
- Environment variable configuration
- CI/CD pipeline setup

---

## Documentation Structure

- **PROJECT_OVERVIEW.md** (this file) - High-level architecture and features
- **PROJECT_CONTEXT.md** - Detailed technical implementation (data models, APIs, workflows)
- **COMPLIANCE_REQUIREMENTS.md** - Regulatory compliance mapping
- **azure/README.md** - Azure deployment guide
- **README.md** - Original project setup instructions

---

## Contact & Support

**Repository:** (Internal/Private)
**Deployment:** Local development + Azure production environment
**Last Updated:** October 2025
