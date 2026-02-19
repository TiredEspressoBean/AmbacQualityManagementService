# Deployment Models & Roadmap

**Last Updated:** February 11, 2026

This document outlines deployment options, compliance considerations, and the roadmap for each model.

Legend: [x] = Ready | [~] = Partial/In Progress | [ ] = Not Yet Implemented

---

## Deployment Strategy

| Customer Type | Deployment | Who Manages Infrastructure | Who Owns Compliance |
|---------------|------------|---------------------------|---------------------|
| **Commercial** | SaaS | Us | Us (SOC 2, etc.) |
| **Defense** | On-Premise | Customer | Customer (CMMC, ITAR) |

**Key Rule:** Defense customers (CMMC, ITAR, CUI) deploy on-premise only. This keeps compliance cleanly on their side.

---

## Compliance Responsibility Model (On-Premise for Defense)

When defense customers deploy on-premise, responsibilities are clear:

| Responsibility | Software Vendor (Us) | Customer (Defense Contractor) |
|----------------|---------------------|-------------------------------|
| CMMC Certification | ❌ Not applicable | ✅ Their certification |
| Software Security | ✅ Secure code, updates | ❌ Relies on us |
| Infrastructure | ❌ Not ours | ✅ Their hardware/network |
| Access Management | ⚠️ Provide controls | ✅ Configure & enforce |
| Data Classification | ❌ Not our data | ✅ Must classify their data |
| Incident Reporting | ⚠️ Notify of vulnerabilities | ✅ Report to DoD (72 hours) |
| Physical Security | ❌ Not applicable | ✅ Their facilities |
| Employee Vetting | ❌ No access to their data | ✅ Their employees |
| ITAR Compliance | ❌ Not applicable | ✅ Their responsibility |

**Why On-Premise Works:** Customer controls everything in their boundary. We provide software + updates via secure transfer. No FedRAMP needed, no cloud compliance complexity.

Sources: [CMMC Enforcement](https://erp.today/cmmc-2-0-enters-enforcement-what-contractors-and-vendors-must-know/), [Contractor Responsibility](https://thecgp.org/what-federal-contractors-need-to-know-about-cmmc/)

---

## CMMC 2.0 Overview (For Context)

CMMC (Cybersecurity Maturity Model Certification) applies to **defense contractors**, not software vendors. Since we only offer on-premise for defense, CMMC is entirely the customer's responsibility.

| Level | Data Type | Controls | Assessment | Deployment |
|-------|-----------|----------|------------|------------|
| **Level 1** | FCI only | 15 controls | Self-assessment | On-Premise |
| **Level 2** | CUI | 110 (NIST 800-171) | Self or C3PAO | On-Premise |
| **Level 3** | Critical CUI | 110 + 24 | Government-led | On-Premise (Airgapped likely) |

- **FCI** = Federal Contract Information (basic contract data, not sensitive)
- **CUI** = Controlled Unclassified Information (sensitive but unclassified defense data)

**Timeline:** Phase 1 (Nov 2025 - Nov 2026) requires self-assessments. Phase 2 (Nov 2026+) requires third-party assessments for Level 2.

**Our Role:** Provide secure, well-documented software. Customer handles everything else.

Sources: [CMMC Levels Explained](https://medium.com/@tyson.martin/cmmc-2-0-levels-1-2-and-3-what-changes-what-it-costs-and-how-to-choose-0f90ab7d8bf9), [CMMC 2026 Requirements](https://www.accorian.com/cmmc-2-0-in-2026-whats-new-and-what-organizations-must-know/)

---

## FedRAMP (Not Applicable)

FedRAMP is required for cloud service providers handling CUI. Since we offer **on-premise only** for defense customers, FedRAMP does not apply to us.

If we ever offered SaaS for defense (not planned), FedRAMP Moderate ($200-500K+, 12-18 months) would be required.

Sources: [FedRAMP and CMMC](https://www.deltek.com/en/blog/fedramp-impacts-cmmc)

---

## ITAR Requirements (Export Control)

ITAR (International Traffic in Arms Regulations) is **not a certification** - it's export control law administered by the State Department. Violations can result in criminal penalties.

### ITAR Technical Requirements

| Requirement | Description | Our Obligation |
|-------------|-------------|----------------|
| **US Person Access** | Only US citizens or permanent residents can access ITAR data | Restrict admin/support access |
| **US Data Location** | Data must reside in the United States | Use US-only data centers |
| **Access Logging** | Audit trail of all access to ITAR data | Comprehensive audit logs |
| **No Foreign Access** | Cannot be accessed from or by foreign nationals | Geo-blocking, access controls |

### Cloud Provider ITAR Support

| Provider | ITAR-Capable Region | Notes |
|----------|---------------------|-------|
| AWS | GovCloud (US) | FedRAMP High, US Persons only |
| Azure | Azure Government | FedRAMP High, US data centers |
| Google Cloud | Assured Workloads | ITAR control package |

**Key Point:** Standard commercial Azure/AWS regions are NOT ITAR-compliant. Must use government regions.

Sources: [AWS ITAR](https://aws.amazon.com/compliance/itar/), [Azure ITAR](https://learn.microsoft.com/en-us/compliance/regulatory/offering-itar), [Google Cloud ITAR](https://cloud.google.com/security/compliance/itar)

---

## Deployment Models

### Model 1: SaaS Multi-Tenant (Current - Railway)

**Status:** Production Ready ✅

**Target Customers:**
- Small job shops without defense contracts
- Commercial manufacturing
- Non-regulated industries

---

## SaaS Infrastructure Detail (Railway)

### Current Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Railway                               │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Backend   │  │   Celery    │  │   Celery    │         │
│  │  (Gunicorn) │  │   Worker    │  │    Beat     │         │
│  │   Django    │  │             │  │  (Scheduler)│         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│         └────────────────┼────────────────┘                 │
│                          │                                  │
│  ┌───────────────────────┼───────────────────────┐         │
│  │            PostgreSQL (pgvector)              │         │
│  │         - All tenant data (RLS)               │         │
│  │         - Celery results                      │         │
│  └───────────────────────────────────────────────┘         │
│                          │                                  │
│  ┌───────────────────────┼───────────────────────┐         │
│  │                    Redis                      │         │
│  │         - Celery broker (queue)               │         │
│  │         - Django cache                        │         │
│  └───────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
   Azure Blob         HubSpot API       Anthropic API
   (Documents)        (CRM Sync)        (AI Features)
```

### What's Already Working

| Component | Status | Configuration |
|-----------|--------|---------------|
| **Django Backend** | [x] | Gunicorn, 2 workers, 120s timeout |
| **Celery Worker** | [x] | Async tasks (emails, HubSpot sync, embeddings) |
| **Celery Beat** | [x] | Scheduled tasks (weekly emails, notifications) |
| **PostgreSQL** | [x] | pgvector for embeddings, RLS-ready |
| **Redis** | [x] | Broker (db 0) + Cache (db 1) |
| **Health Checks** | [x] | `/api/health/` endpoint |
| **Static Files** | [x] | WhiteNoise middleware |

### Multi-Tenancy Implementation

| Feature | Status | Notes |
|---------|--------|-------|
| **Tenant Model** | [x] | UUID PK, slug, tier (Starter/Pro/Enterprise), status |
| **SecureModel Base** | [x] | All business models inherit, auto-scoped to tenant |
| **TenantMiddleware** | [x] | Resolves tenant from header/subdomain/user |
| **TenantGroup** | [x] | Tenant-scoped permission groups |
| **TenantGroupMembership** | [x] | User can have different roles per tenant |
| **TenantPermissionBackend** | [x] | Permission checks scoped to current tenant |
| **Row-Level Security** | [~] | RLS policies defined, needs `ENABLE_RLS=True` |
| **Subdomain Routing** | [~] | Middleware supports it, DNS/Railway config needed |

### Railway-Specific Configuration

**railway.json:**
```json
{
  "build": { "builder": "NIXPACKS" },
  "deploy": {
    "startCommand": "gunicorn PartsTrackerApp.wsgi --bind 0.0.0.0:$PORT --workers 2 --timeout 120",
    "healthcheckPath": "/api/health/",
    "healthcheckTimeout": 30,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 5
  }
}
```

**Procfile (for multiple services):**
```
web: gunicorn PartsTrackerApp.wsgi --bind 0.0.0.0:$PORT --workers 2 --timeout 120
worker: celery -A PartsTrackerApp worker --loglevel=info --concurrency=2
beat: celery -A PartsTrackerApp beat --loglevel=info
release: python manage.py migrate && python manage.py setup_defaults
```

### Environment Variables Required

| Variable | Purpose | Example |
|----------|---------|---------|
| `DJANGO_SECRET_KEY` | Session encryption | (generate with `openssl rand -hex 32`) |
| `DJANGO_DEBUG` | Debug mode | `false` |
| `ALLOWED_HOSTS` | Valid hostnames | `app.example.com,*.railway.app` |
| `POSTGRES_*` | Database connection | Railway provides these |
| `REDIS_*` | Cache/broker | Railway provides these |
| `CORS_ALLOWED_ORIGINS` | Frontend URLs | `https://app.example.com` |
| `CSRF_TRUSTED_ORIGINS` | CSRF protection | `https://app.example.com` |
| `EMAIL_HOST_*` | SMTP settings | Your email provider |
| `HUBSPOT_API_KEY` | CRM integration | (optional) |
| `AI_EMBED_ENABLED` | AI features | `true` |
| `OLLAMA_URL` | Embeddings API | `http://ollama:11434` |

### What's Missing for Production SaaS

| Feature | Priority | Effort | Notes |
|---------|----------|--------|-------|
| **File Storage** | High | TBD | Currently local; cloud solution not decided |
| **Tenant Provisioning API** | High | Medium | Self-service signup flow |
| **Billing Integration** | High | Medium | Stripe for subscriptions |
| **Usage Metering** | Medium | Medium | Track API calls, storage, users |
| **Tenant Admin Portal** | Medium | Medium | Self-service settings, users, billing |
| **Backup Automation** | Medium | Low | Railway has built-in, but verify |
| **Monitoring/Alerting** | Medium | Low | Railway metrics + external (Sentry) |
| **Rate Limiting** | Medium | Low | DRF throttling or Redis-based |
| **SOC 2 Prep** | Low | High | Policies, procedures, audit |

### Subdomain Tenant Routing (Configuration Only)

The app already supports subdomain-based tenant resolution. Just needs configuration:

1. **DNS Provider** - Add wildcard record: `*.yourdomain.com → Railway IP/CNAME`
2. **Railway** - Configure custom domain with wildcard support
3. **Django Settings** - Set `TENANT_BASE_DOMAIN=yourdomain.com`

The `TenantMiddleware` already extracts subdomain from `Host` header and resolves tenant:
- `acme.yourdomain.com` → tenant slug "acme"
- `demo.yourdomain.com` → tenant slug "demo"

No code changes needed.

### Scaling Considerations

**Current (Single Instance):**
- 1 web dyno, 1 worker, 1 beat
- Good for ~50 concurrent users

**Horizontal Scaling:**
- Multiple web dynos (stateless, just add more)
- Multiple workers (Celery handles distribution)
- Single beat instance (only one scheduler)
- Redis: Railway's managed Redis scales
- PostgreSQL: Railway's managed Postgres scales

**Vertical Scaling:**
- Increase worker count per dyno
- Increase memory allocation
- Optimize queries (indexes, select_related)

### File Storage

**Current state:** Using Django's default FileSystemStorage (local filesystem).

**Packages available** (in requirements.txt but not configured):
- `django-storages==1.14.6`
- `azure-storage-blob==12.28.0`

**For Railway/SaaS:** TBD - need to decide on cloud storage solution. Local files don't persist on Railway.

**For On-Premise:** Local FileSystemStorage works out of the box. Just mount a persistent volume to `/app/media`.

### SaaS Features Summary

| Capability | Status | Notes |
|------------|--------|-------|
| Tenant isolation (app-level) | [x] | SecureModel, TenantMiddleware |
| Tenant isolation (DB-level RLS) | [~] | `setup_rls.py` exists for ~40 tables, needs `ENABLE_RLS=true` |
| Tenant-scoped permissions | [x] | TenantGroup, TenantPermissionBackend |
| Tenant tiers (Starter/Pro/Enterprise) | [x] | Model exists, feature gating TBD |
| Tenant status (Active/Trial/Suspended) | [x] | TenantStatusMiddleware |
| Demo tenant with reset | [x] | `is_demo` flag, `reset_demo` command |
| Deployment mode setting | [x] | `DEPLOYMENT_MODE=saas|dedicated` in settings |
| Subdomain routing | [x] | TenantMiddleware + `TENANT_BASE_DOMAIN` setting |
| Audit logging | [x] | django-auditlog on all models |
| HTTPS/TLS | [x] | Railway handles SSL |
| Health checks | [x] | `/api/health/` |
| Scheduled tasks | [x] | Celery Beat |
| Background jobs | [x] | Celery Worker |
| Email notifications | [x] | SMTP configured |
| AI embeddings | [x] | Ollama integration (`ai_embed.py`) |
| Document storage (local) | [x] | Django FileSystemStorage (default) |
| Document storage (cloud) | [ ] | TBD - packages exist, solution not decided |
| Billing/subscriptions | [ ] | Need Stripe integration |
| Usage metering | [ ] | Track for billing |
| Self-service signup | [ ] | Tenant provisioning API |
| Tenant admin portal | [ ] | Settings, users, billing UI |

---

### Model 2: SaaS Dedicated (Single-Tenant Cloud)

**Status:** Architecturally Ready, Needs Automation

**Compliance Suitability:**
- ✅ Non-regulated + regulated quality (ISO, AS9100)
- ⚠️ CMMC Level 1/2 - only if we achieve FedRAMP equivalency
- ⚠️ ITAR - only if deployed to Azure Government/AWS GovCloud
- ❌ CMMC Level 3 - unlikely without full FedRAMP High

**Target Customers:**
- Mid-market manufacturers wanting isolation
- Companies with data residency requirements
- Potential path to ITAR if we use government cloud

### Architecture
- Dedicated PostgreSQL instance
- Dedicated application container(s)
- Isolated storage container
- Dedicated Redis instance

### Features
| Capability | Status | Notes |
|------------|--------|-------|
| Isolated database | [x] | Separate instance |
| Isolated app instance | [x] | Separate deployment |
| Customer-managed keys | [ ] | Key Vault integration |
| Azure Government deployment | [ ] | For ITAR customers |
| Custom backup schedule | [ ] | Customer-defined RPO/RTO |
| Deployment automation | [ ] | Terraform scripts |

---

### Model 3: Private Cloud (Customer-Hosted Cloud)

**Status:** Needs Development

**Compliance Suitability:**
- ✅ All quality standards (ISO, AS9100)
- ⚠️ Not for defense/ITAR/CUI - use On-Premise instead

**Target Customers:**
- Enterprise manufacturers with existing AWS/Azure/GCP
- Companies wanting self-managed but cloud-hosted
- Organizations with cloud-first IT policies
- **NOT for defense contractors** - they should use On-Premise

### Our Deliverables
| Deliverable | Status | Notes |
|-------------|--------|-------|
| Docker images | [x] | Already containerized |
| Docker Compose | [x] | Works today |
| Helm charts | [ ] | Kubernetes deployment |
| Terraform modules | [ ] | Infrastructure as code |
| Installation guide | [ ] | Step-by-step documentation |
| Hardening guide | [ ] | Security configuration |

### Customer Responsibilities
- Provision infrastructure (compute, database, storage)
- Configure networking, firewalls, VPN
- Manage access control (LDAP/AD integration)
- Achieve their own CMMC certification
- Handle ITAR access restrictions
- Perform backups and disaster recovery

---

### Model 4: On-Premise (Defense)

**Status:** Partially Ready - Docker Compose works, needs packaging

**Compliance Suitability:**
- ✅ All compliance requirements - customer controls everything
- ✅ CMMC any level
- ✅ ITAR
- ✅ Classified (with appropriate controls)

**Target Customers:**
- Defense primes
- Companies with no-cloud policies
- Classified program support (NOFORN, etc.)

---

## On-Premise Deployment Detail

### What Already Works

The current `docker-compose.yml` is a working on-premise deployment:

```
┌─────────────────────────────────────────────────────────────┐
│                  Customer Data Center                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Backend   │  │   Celery    │  │   Celery    │         │
│  │  (Django)   │  │   Worker    │  │    Beat     │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│  ┌──────┴────────────────┴────────────────┴──────┐         │
│  │              Caddy (Reverse Proxy)            │         │
│  │           - TLS termination                   │         │
│  │           - Static file serving               │         │
│  └───────────────────────────────────────────────┘         │
│                          │                                  │
│  ┌───────────────────────┴───────────────────────┐         │
│  │          PostgreSQL (pgvector)                │         │
│  └───────────────────────────────────────────────┘         │
│                          │                                  │
│  ┌───────────────────────┴───────────────────────┐         │
│  │                    Redis                      │         │
│  └───────────────────────────────────────────────┘         │
│                          │                                  │
│  ┌───────────────────────┴───────────────────────┐         │
│  │         Local Storage (filesystem/NAS)        │         │
│  │              or MinIO (S3-compatible)         │         │
│  └───────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

### Current Docker Compose Services

| Service | Image | Status | Notes |
|---------|-------|--------|-------|
| `postgres` | ankane/pgvector:v0.5.1 | [x] | Vector search enabled |
| `redis` | redis:7-alpine | [x] | Broker + cache |
| `backend` | Custom Dockerfile | [x] | Django + Gunicorn |
| `celery-worker` | Same as backend | [x] | Async tasks |
| `celery-beat` | Same as backend | [x] | Scheduled tasks |
| `caddy` | caddy:2-alpine | [x] | Reverse proxy, TLS |
| `frontend-builder` | Node | [x] | Builds React app |

### What Needs Development for On-Premise

| Component | Current State | Needed | Effort |
|-----------|---------------|--------|--------|
| **File Storage** | Local filesystem (works!) | Mount persistent volume | Config only |
| **Authentication** | Django auth + allauth | LDAP/AD integration (optional) | Medium |
| **Installation** | Manual docker-compose | Installer script/wizard | Low |
| **Configuration** | .env file | Config wizard or web UI | Low |
| **Updates** | Git pull + rebuild | Versioned release packages | Medium |
| **Documentation** | Sparse | Full installation guide | Medium |
| **Hardening** | Basic | CIS benchmark guide | Medium |
| **RLS Enforcement** | Command exists, disabled | Enable `ENABLE_RLS=true` + run `setup_rls` | Config only |

### Local Storage Backend (Already Works)

Django's default FileSystemStorage is already configured:

```python
# Current settings.py
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
```

**For on-premise:** Mount a persistent volume to `/app/media` in docker-compose. No code changes needed.

### LDAP/AD Authentication

Add django-auth-ldap for enterprise SSO:

```python
# settings.py - LDAP authentication
if os.environ.get('LDAP_SERVER'):
    import ldap
    from django_auth_ldap.config import LDAPSearch, GroupOfNamesType

    AUTHENTICATION_BACKENDS = [
        'django_auth_ldap.backend.LDAPBackend',
        'django.contrib.auth.backends.ModelBackend',  # Fallback
    ]

    AUTH_LDAP_SERVER_URI = os.environ.get('LDAP_SERVER')
    AUTH_LDAP_BIND_DN = os.environ.get('LDAP_BIND_DN')
    AUTH_LDAP_BIND_PASSWORD = os.environ.get('LDAP_BIND_PASSWORD')
    AUTH_LDAP_USER_SEARCH = LDAPSearch(
        os.environ.get('LDAP_USER_BASE', 'ou=users,dc=example,dc=com'),
        ldap.SCOPE_SUBTREE,
        '(sAMAccountName=%(user)s)'  # AD style
    )
```

### On-Premise Installation Process

**Minimum Requirements:**
- Docker + Docker Compose
- 4 CPU cores, 8GB RAM, 100GB storage
- Network access to internal services only

**Installation Steps:**
1. Extract release package to server
2. Copy `.env.example` to `.env`, configure
3. Run `./install.sh` (creates network, pulls images, initializes DB)
4. Access web UI, complete setup wizard
5. Configure LDAP (optional), create admin user

**Release Package Contents:**
```
ambac-tracker-v1.2.3/
├── docker-compose.yml
├── docker-compose.override.yml  # Customer customizations
├── .env.example
├── install.sh
├── upgrade.sh
├── backup.sh
├── images/                       # Pre-built Docker images (tar)
│   ├── backend.tar
│   ├── frontend.tar
│   └── ...
├── conf/
│   ├── Caddyfile
│   └── ...
├── docs/
│   ├── INSTALLATION.md
│   ├── CONFIGURATION.md
│   ├── HARDENING.md
│   └── TROUBLESHOOTING.md
└── scripts/
    ├── backup-db.sh
    ├── restore-db.sh
    └── health-check.sh
```

### Update Mechanism (Connected On-Premise)

For on-premise with internet access:
```bash
# upgrade.sh
#!/bin/bash
docker-compose pull
docker-compose down
docker-compose up -d
docker-compose exec backend python manage.py migrate
```

### On-Premise Feature Checklist

| Feature | Status | Notes |
|---------|--------|-------|
| Docker Compose deployment | [x] | Works today |
| PostgreSQL + pgvector | [x] | Works today |
| Redis broker/cache | [x] | Works today |
| Caddy reverse proxy | [x] | Works today |
| TLS certificates | [x] | Caddy auto or manual certs |
| Health checks | [x] | `/api/health/` |
| Backup script | [~] | Basic, needs automation |
| Local file storage | [x] | Django FileSystemStorage works, mount volume |
| MinIO support | [ ] | Optional - for distributed storage |
| LDAP/AD auth | [ ] | Need django-auth-ldap |
| Installation script | [ ] | Need to create |
| Configuration wizard | [ ] | Nice to have |
| Upgrade script | [ ] | Need to create |
| Hardening guide | [ ] | Need to document |
| Offline image loading | [ ] | For airgapped, `docker load` |

---

### Model 5: Airgapped

**Status:** Needs Development (builds on On-Premise)

**Compliance Suitability:**
- ✅ CMMC Level 3
- ✅ ITAR with strict controls
- ✅ Classified environments
- ✅ NIST 800-171 / NIST 800-53

**Target Customers:**
- Classified programs
- Defense primes with strict security requirements
- Critical infrastructure

---

## Airgapped Deployment Detail

Airgapped = On-Premise + No Internet. Everything must work offline.

### Airgapped Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Airgapped Network (No Internet)                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Same as On-Premise                      │    │
│  │   Backend + Celery + PostgreSQL + Redis + Caddy     │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                   │
│  ┌───────────────────────┴───────────────────────┐          │
│  │              Ollama (Local LLM)               │          │
│  │         - Embeddings (nomic-embed-text)       │          │
│  │         - Chat (llama3, mistral, etc.)        │          │
│  └───────────────────────────────────────────────┘          │
│                          │                                   │
│  ┌───────────────────────┴───────────────────────┐          │
│  │           Internal Mail Relay (optional)      │          │
│  │              or notifications disabled        │          │
│  └───────────────────────────────────────────────┘          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
              │
              │ Secure Transfer (USB, DVD, Approved Media)
              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Update Staging Area                       │
│  - Signed release packages                                   │
│  - Verified checksums                                        │
│  - Security scan before import                               │
└─────────────────────────────────────────────────────────────┘
```

### What Changes for Airgapped

| Component | Connected | Airgapped | Status |
|-----------|-----------|-----------|--------|
| **AI Embeddings** | Ollama (can pull models) | Ollama (pre-loaded models) | [x] Ollama works, need model bundling |
| **AI Chat (LangGraph)** | LangGraph + any LLM | LangGraph + Ollama | [x] Agent exists, supports `ollama/` provider |
| **Email** | External SMTP | Internal relay or disabled | [x] Configurable |
| **HubSpot Sync** | API calls | Disabled | [x] Just don't configure |
| **Updates** | `docker pull` | Load from media | [ ] Need packaging |
| **License** | Online validation | Offline validation | [ ] Need to implement |
| **Documentation** | Link to web docs | Bundled offline docs | [ ] Need to bundle |
| **Time sync** | NTP to internet | Internal NTP or manual | Customer responsibility |

### Local AI with Ollama + LangGraph

**Already working:**
- Ollama integration for embeddings (`ai_embed.py`)
- LangGraph agent with RAG tools (separate repo at `PycharmProjects/LangGraph`)
- Agent supports `ollama/` provider for chat (default: `ollama/gpt-OSS:20b`)
- Frontend connects to LangGraph via `/lg/*` proxy (Caddy → port 8123)

**Current settings.py:**
```python
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
```

**LangGraph configuration.py:**
```python
model: str = "ollama/gpt-OSS:20b"  # Default uses Ollama
django_api_base_url: str = os.getenv("DJANGO_API_BASE_URL", "http://localhost:8000/api")
```

**What's needed for airgapped:**
1. Move LangGraph repo into main project (or submodule)
2. Add LangGraph + Ollama services to docker-compose
3. Bundle Ollama models in release package
4. Test full chat + RAG flow without internet

**Ollama docker-compose service:**
```yaml
ollama:
  image: ollama/ollama:latest
  volumes:
    - ollama_models:/root/.ollama
    - ./models:/models  # Pre-loaded models
  deploy:
    resources:
      reservations:
        devices:
          - capabilities: [gpu]  # Optional GPU support
```

**Pre-load models for airgapped:**
```bash
# On connected machine, pull models
ollama pull nomic-embed-text
ollama pull llama3:8b  # Or smaller model

# Export for airgapped transfer
# Models stored in ~/.ollama/models/
tar -czf ollama-models.tar.gz ~/.ollama/models/
```

### LangGraph Agent (AI Chat + RAG)

The LangGraph agent provides AI chat with RAG (retrieval-augmented generation) over documents and database queries.

**Current location:** Separate repo (needs to be moved/bundled)

**Architecture:**
```
Frontend  →  /lg/*  →  Caddy  →  LangGraph (port 8123)  →  Django API
                                      ↓
                                    Ollama (chat model)
```

**Agent Tools:**
- `get_schema` - Get database model info
- `query_database` - Read-only queries via Django API
- `search_documents_semantic` - Vector search (Ollama embeddings)
- `search_documents_keyword` - Full-text search
- `get_context` - Expand context around found chunks

**LangGraph docker-compose service (to add):**
```yaml
langgraph:
  build:
    context: ./langgraph  # After moving to main repo
    dockerfile: Dockerfile
  environment:
    - DJANGO_API_BASE_URL=http://backend:8000/api
    - OLLAMA_BASE_URL=http://ollama:11434
  ports:
    - "8123:8123"
  depends_on:
    - backend
    - ollama
```

### Airgapped Update Process

Updates delivered via approved media (USB, DVD, secure file transfer):

**Release Package (Airgapped):**
```
ambac-tracker-v1.2.3-airgapped/
├── MANIFEST.txt           # File list with SHA256 checksums
├── SIGNATURE.asc          # GPG signature of MANIFEST.txt
├── RELEASE_NOTES.md
├── images/
│   ├── backend-v1.2.3.tar
│   ├── frontend-v1.2.3.tar
│   ├── ollama-v0.1.30.tar
│   └── ...
├── models/
│   ├── nomic-embed-text.tar.gz
│   └── llama3-8b.tar.gz   # Optional chat model
├── migrations/
│   └── 0045_to_0048.sql   # DB migrations if needed
└── scripts/
    ├── verify.sh          # Verify signatures
    ├── upgrade.sh         # Run upgrade
    └── rollback.sh        # Rollback if needed
```

**Update Process:**
1. Transfer package to staging area
2. Security team scans package
3. Verify GPG signature: `./verify.sh`
4. Copy to production server
5. Run upgrade: `./upgrade.sh`
6. Verify health: `./health-check.sh`

### Airgapped License Validation

Options for offline license validation:

**Option 1: Time-Limited License File**
```python
# License file contains: customer_id, expiration_date, features, signature
# Signed with our private key, verified with embedded public key
LICENSE_FILE = '/etc/ambac-tracker/license.key'

def validate_license():
    with open(LICENSE_FILE) as f:
        license_data = json.load(f)
    # Verify signature with embedded public key
    # Check expiration date
    # Return enabled features
```

**Option 2: Hardware-Locked License**
```python
# License tied to machine fingerprint (CPU ID, MAC address, etc.)
# Customer provides fingerprint, we generate license for that machine
def get_machine_fingerprint():
    # Collect hardware identifiers
    # Hash them together
    return fingerprint

def validate_license():
    expected_fingerprint = license_data['fingerprint']
    actual_fingerprint = get_machine_fingerprint()
    return expected_fingerprint == actual_fingerprint
```

### Airgapped Feature Matrix

| Feature | Works Offline | Notes |
|---------|---------------|-------|
| Core MES (parts, work orders, steps) | ✅ | No external dependencies |
| Quality reports, inspections | ✅ | No external dependencies |
| SPC charts | ✅ | No external dependencies |
| CAPA workflow | ✅ | No external dependencies |
| Document storage | ✅ | Local filesystem/MinIO |
| Document search (embeddings) | ✅ | Ollama local embeddings |
| AI Document Q&A (LangGraph) | ✅ | Agent exists, uses Ollama - needs bundling |
| Email notifications | ⚠️ | Need internal mail relay |
| HubSpot CRM sync | ❌ | Disabled (no internet) |
| Automatic updates | ❌ | Manual via media |
| Error reporting (Sentry) | ❌ | Disabled (no internet) |

### Airgapped Checklist

| Requirement | Status | Notes |
|-------------|--------|-------|
| All On-Premise features | [ ] | Prerequisite |
| Ollama embeddings integration | [x] | `ai_embed.py` works with local Ollama |
| LangGraph agent (chat + RAG) | [x] | Agent exists in separate repo, supports Ollama |
| Move LangGraph to main repo | [ ] | Bundle or submodule |
| Add Ollama + LangGraph to docker-compose | [ ] | Service definitions |
| Pre-loaded embedding model | [ ] | Bundle nomic-embed-text (~300MB) |
| Pre-loaded chat model | [ ] | Bundle llama3:8b or similar (~4-8GB) |
| Offline documentation | [ ] | Bundle as static HTML |
| Signed release packages | [ ] | GPG signing process |
| Offline license validation | [ ] | Time-limited or hardware-locked |
| Air-gap update scripts | [ ] | verify.sh, upgrade.sh |
| Model loading scripts | [ ] | Load Ollama models from tar |
| Disable external services | [x] | HubSpot disabled if no API key, Sentry optional |

---

## Roadmap by Phase

### Phase 1: SaaS Hardening (Current - Q2 2026)
*Goal: Production-ready commercial SaaS*

- [x] Row-level security
- [x] Audit logging
- [x] HTTPS everywhere
- [ ] SOC 2 Type II preparation
- [ ] Penetration testing
- [ ] Tenant admin self-service
- [ ] Automated provisioning

**Decision Point:** Do we pursue FedRAMP for SaaS? Cost: $200-500K+, 12-18 months.

### Phase 2: On-Premise for Defense (Q3-Q4 2026)
*Goal: Deployable package for defense customers*

- [ ] Local storage backend (MinIO or filesystem)
- [ ] LDAP/AD authentication
- [ ] Offline installer package
- [ ] Installation documentation
- [ ] Hardening guide (CIS benchmarks)
- [ ] Air-gap update mechanism

**This unlocks the defense market** - they install it, they own compliance.

### Phase 3: Airgapped + Local AI (2027)
*Goal: Fully disconnected operation with AI features*

- [x] Local LLM integration (Ollama) - agent exists, supports `ollama/` provider
- [x] Local embeddings (Ollama nomic-embed-text) - `ai_embed.py` works
- [ ] Bundle LangGraph agent into main repo
- [ ] Add Ollama + LangGraph to docker-compose
- [ ] Bundle Ollama models in release package
- [ ] Offline license validation
- [ ] Bundled documentation

### Phase 4: Private Cloud (If Demand)
*Goal: Enterprise cloud-hosted option for non-defense*

Only if commercial enterprise customers want it:
- [ ] Helm charts for Kubernetes
- [ ] Terraform modules
- [ ] Cloud-agnostic deployment guide

---

## Defense Market Strategy

**Defense customers = On-Premise only.** No SaaS, no cloud. They host it in their facility, they own all compliance.

### Why On-Prem Only for Defense
- Defense contractors expect to self-host sensitive systems
- Eliminates FedRAMP requirement for us entirely
- Customer controls their CMMC boundary completely
- No dependency on our cloud security posture
- Simpler compliance story for both parties

### Customer Conversation
> "We provide MES software that you install in your own data center. You control everything - infrastructure, access, and compliance. We provide the software, documentation, updates, and support."

### What We Must Deliver
1. Offline installer package (all dependencies bundled)
2. Local storage backend (no Azure dependency) ✅ FileSystemStorage works
3. LDAP/AD authentication
4. Hardening guide (CIS benchmarks, STIG if needed)
5. Air-gap update mechanism
6. Local AI (Ollama + LangGraph) ✅ Code exists, needs bundling

### What We Don't Need
- FedRAMP authorization
- Azure Government / AWS GovCloud accounts
- CMMC certification (that's the customer's)
- Continuous cloud compliance monitoring

---

## Pricing Considerations

| Model | Pricing Approach | Notes |
|-------|------------------|-------|
| SaaS Multi-Tenant | Per-user/month | Lowest price, widest market |
| SaaS Dedicated | Base + per-user | Premium for isolation |
| Private Cloud | Annual license + support | Customer pays cloud costs |
| On-Premise | Perpetual license + annual maintenance | Or subscription |
| Airgapped | Perpetual + premium support | Highest price, specialized |

---

## Summary

| Customer Type | Deployment Model | Our Readiness |
|---------------|------------------|---------------|
| Commercial, no compliance | SaaS Multi-Tenant | ✅ Ready |
| Commercial, wants isolation | SaaS Dedicated | 🟡 Needs automation |
| Enterprise, cloud-first IT | Private Cloud | 🟡 Needs Helm/Terraform |
| Defense (CMMC, ITAR, CUI) | On-Premise | 🟡 Needs packaging |
| Classified programs | Airgapped On-Premise | 🟡 Needs bundling (AI ready) |

**Bottom Line:**
- **Commercial customers:** SaaS (we manage everything)
- **Defense customers:** On-Premise only (they manage everything, we provide software + support)
