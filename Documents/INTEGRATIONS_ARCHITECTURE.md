# Integrations Architecture

**Last Updated:** February 4, 2026 (Questions Resolved)

---

## Purpose

A separate Django app for connecting to external systems (CRM, ERP, etc.) without polluting the core Tracker models.

---

## Goals

1. **Multi-tenant** - Each tenant configures their own integrations
2. **Zero cost for non-users** - No fields/tables for tenants who don't use integrations
3. **Extensible** - Adding Salesforce shouldn't touch Orders model
4. **Template** - HubSpot as reference implementation for future integrations

---

## Key Decisions

### Separate Django App
- `integrations/` lives alongside `Tracker/`
- One-way dependency: integrations imports from Tracker, never reverse
- Can be excluded from deployments that don't need it

### Separate Link Tables Per Integration
- `HubSpotOrderLink`, `SalesforceOrderLink`, etc.
- NOT GenericForeignKey (loses referential integrity, can't use select_related)
- Each integration has its own schema (HubSpot has deals, Salesforce has opportunities)

### Adapter Pattern
- Common interface (Protocol class) for all integrations
- Rest of system doesn't know which CRM is connected
- Easy to swap or add integrations

### Per-Tenant Configuration
- `IntegrationConfig` model stores credentials and settings per tenant
- Encrypted credentials at rest
- Enable/disable per tenant

### Audit Trail
- Link tables track current sync state (`last_synced_at`, `sync_status`, `last_error`)
- Celery `TaskResult` (via django-celery-results) provides task history and error details
- `ProcessedWebhook` for idempotency (don't process same event twice)
- Full `SyncLog` table can be added later if detailed per-entity history is needed (enterprise)

---

## File Structure

```
integrations/
├── models/
│   ├── config.py       # IntegrationConfig
│   ├── sync.py         # SyncLog, ProcessedWebhook
│   └── links/
│       ├── hubspot.py  # HubSpotOrderLink, HubSpotCompanyLink
│       └── ...         # Future integrations
├── adapters/
│   ├── base.py         # Protocol interface
│   ├── hubspot.py      # HubSpot implementation
│   └── ...
├── services/
│   ├── registry.py     # Get adapter by type
│   └── sync.py         # Orchestration
├── webhooks/
│   ├── views.py        # Receive + queue
│   └── handlers.py     # Process
├── tasks.py            # Celery tasks
└── urls.py             # Webhook endpoints
```

---

## Abstract Event Types

At the fundamental level, integrations handle only a few kinds of events:

### 1. Data Replication
*"Keep these two things in sync"*

- Your Order ↔ Their Deal
- Your Company ↔ Their Account
- Bidirectional or one-way
- Goal: Same data exists in both places

**Characteristics:**
- Has a "link" between entities
- Needs conflict resolution strategy
- Continuous (ongoing relationship)

### 2. Event Notification
*"Something happened"*

- Order shipped
- Inspection failed
- Document approved
- Training expired

**Characteristics:**
- One-way (fire and forget)
- No response expected
- Receiver decides what to do with it
- Past tense ("happened")

### 3. Command
*"Do this thing"*

- Create an invoice
- Send an email
- Generate a shipping label

**Characteristics:**
- Expects something to happen
- May expect confirmation/response
- Imperative ("do X")
- Failure matters

### 4. Query
*"Tell me something"*

- Get current deal stage
- Check if customer exists
- Fetch latest pricing

**Characteristics:**
- Request/response
- Read-only
- Synchronous (usually)
- Point-in-time

### How They Differ

| Type | Direction | Response? | Failure Handling |
|------|-----------|-----------|------------------|
| **Data Replication** | Bidirectional | State sync | Retry, reconcile |
| **Event Notification** | Outbound | No | Log, maybe retry |
| **Command** | Outbound | Yes (confirmation) | Retry, compensate |
| **Query** | Outbound→Inbound | Yes (data) | Retry, fallback |

### Integration Type Mapping

Most integrations are primarily one of these:

| Integration | Primary Type |
|-------------|--------------|
| HubSpot/Salesforce (CRM) | Data Replication |
| Slack/Teams | Event Notification |
| ERP (SAP, NetSuite) | Commands + Queries |
| LDAP/Active Directory | Query (auth lookup) |
| Shipping (FedEx, UPS) | Command |
| Email | Event Notification or Command |

---

## Core Models (Conceptual)

### IntegrationConfig
- tenant (FK)
- integration_type (hubspot, salesforce, etc.)
- enabled (bool)
- credentials (JSON, encrypted)
- settings (JSON)
- webhook_secret

### Link Tables (per integration)
- tenant (FK)
- order/company (OneToOne FK with related_name)
- external_id (the ID in the external system)
- sync metadata: `last_synced_at`, `sync_status`, `last_error`

### ProcessedWebhook
- tenant, integration_type, external_event_id
- Unique constraint prevents duplicate processing

---

## Adding a New Integration

1. Add link tables in `models/links/`
2. Create adapter implementing the Protocol
3. Register in `services/registry.py`
4. Add webhook endpoint
5. Write tests

---

## Migration from Current State

### Existing Code

There is an existing `Tracker/integrations/` module with:
- `base_service.py` — IntegrationService ABC
- `registry.py` — Service registry
- `hubspot_service.py` — HubSpot implementation

This code will be migrated to the new `integrations/` Django app structure. The existing patterns (registry, base service) are sound and will be preserved.

### Existing Data

Current `Orders` has hardcoded HubSpot fields:
- `hubspot_deal_id`
- `current_hubspot_gate`
- `hubspot_last_synced_at`
- etc.

### Migration Steps

1. Create new `integrations/` Django app
2. Move/refactor existing services into new structure
3. Create `HubSpotOrderLink` table
4. Copy existing HubSpot data from Orders to link table
5. Update HubSpot service to use link table
6. Remove old fields from Orders
7. Deprecate `Tracker/integrations/` module

---

## On-Premise / Air-Gapped Deployments

Some customers deploy on their own infrastructure with no external internet access. Integrations target systems on the same local network instead of cloud APIs.

### Examples

| Cloud Integration | On-Prem Equivalent |
|-------------------|-------------------|
| HubSpot CRM | On-prem CRM, local database |
| Salesforce | Microsoft Dynamics (self-hosted) |
| Okta SSO | LDAP / Active Directory |
| Cloud ERP | SAP on-prem, Oracle E-Business |
| Azure Blob | Local file server, NAS |

### Key Differences

| Concern | Cloud (SaaS) | On-Prem / Air-Gapped |
|---------|--------------|----------------------|
| Connection target | External API (internet) | Local network resource |
| Credentials | OAuth tokens, API keys | Service accounts, connection strings |
| Configuration | Per-tenant in database | Per-deployment in environment/settings |
| Discovery | Known endpoints | Customer provides connection details |
| Updates | Vendor pushes changes | Customer controls versions |

### Architecture Considerations

**1. Deployment-level vs Tenant-level Config**

Cloud integrations: Config stored in `IntegrationConfig` table (per-tenant)

On-prem integrations: May need environment variables or settings file (per-deployment)

```
# Cloud: stored in database
IntegrationConfig(tenant=acme, integration_type='hubspot', credentials={...})

# On-prem: might come from environment or settings
LDAP_SERVER = "ldap://192.168.1.50"
LDAP_BIND_DN = "cn=admin,dc=example,dc=com"
```

**2. Adapter Variants**

Same logical integration, different implementations:

- `SAPCloudAdapter` - calls SAP cloud APIs
- `SAPOnPremAdapter` - connects to local SAP instance
- `LDAPAdapter` - connects to customer's directory server

Registry selects based on deployment config, not just integration type.

**3. No Webhooks**

Air-gapped systems typically can't receive inbound webhooks. Options:
- Polling on schedule (Celery beat)
- Database triggers / change data capture
- Manual sync triggered by user

**4. Network Security**

On-prem integrations may require:
- VPN or private network access
- Firewall rules
- Client certificates
- Kerberos authentication

These are deployment concerns, not application concerns.

### Recommended Approach

**Keep the same adapter interface**, but allow:

1. **Connection details from environment** - Don't assume database config
2. **Polling instead of webhooks** - Scheduled sync tasks
3. **Adapter selection by deployment** - Not just integration type
4. **Optional modules** - LDAP adapter only included if needed

### Example: LDAP Authentication

For air-gapped customers who want to use their Active Directory:

- Not really an "integration" in the CRM/ERP sense
- More of an authentication backend
- Django has `django-auth-ldap` for this
- Configure via environment variables, not IntegrationConfig

This might live in `core/` auth backends rather than `integrations/`.

### What Belongs Where

| Integration Type | Where It Lives | Config Source |
|------------------|----------------|---------------|
| HubSpot, Salesforce (cloud CRM) | `integrations/` | Database (IntegrationConfig) |
| On-prem ERP (SAP, Oracle) | `integrations/` | Environment + Database |
| LDAP / Active Directory | `core/` auth backends | Environment |
| Local file storage | Django storage backend | Settings |
| On-prem email (Exchange) | Django email backend | Settings |

---

## Reliability Strategy

### Celery with Retries (Default)

For most sync operations, Celery with global retry settings is sufficient:

```python
# settings.py
CELERY_TASK_ANNOTATIONS = {
    '*': {
        'max_retries': 3,
        'default_retry_delay': 60,  # 60 seconds between retries
    }
}
```

**When this is enough:**
- CRM sync (HubSpot, Salesforce)
- Notification events (Slack, email)
- Most data replication

### When to Consider Outbox Pattern

Transactional outbox (django-outbox-pattern, django-jaiminho) is only needed for:
- Compliance-critical financial transactions
- When "exactly once" delivery is legally required
- Multi-system transactions that must be atomic

**For this application:** Celery with retries is sufficient. Don't add outbox complexity unless a specific compliance requirement demands it.

---

## Conflict Resolution

### Source-of-Truth Per Field

When both systems change the same data, resolve by field ownership:

| Field Category | Owner | Direction |
|----------------|-------|-----------|
| **Operational data** (part status, quality results, workflow state) | Your system | Push to CRM only |
| **Sales/customer data** (contact info, deal stage, notes) | CRM | Pull from CRM only |
| **Shared fields** (order name, dates) | Pick one | Configure per field |

### Rules

- Operational fields → `push` only (never let CRM overwrite quality data)
- Customer fields → `pull` only (CRM owns customer contact info)
- Avoid `bidirectional` unless necessary — requires timestamp comparison and conflict detection

---

## Field Mapping

Field mapping is needed because external systems have different field names (`Order.name` → `Deal.dealname`) and tenants may have custom CRM fields.

**Key decisions:**
- Base mappings defined by us (sensible defaults)
- Per-tenant overrides stored in database
- Support for `custom_fields` JSONField on core entities (for ERP integration data)
- Direction per field: `push`, `pull`, or `bidirectional` (ties into conflict resolution)

**Details TBD during implementation.**

---

## Adapter Selection (Cloud vs On-Prem)

### Single System, Multiple Adapters

The same integration type can have different adapters for different deployment scenarios:

```python
# adapters/sap/__init__.py
class SAPCloudAdapter(BaseAdapter):
    """Connects to SAP S/4HANA Cloud via REST API"""
    pass

class SAPOnPremAdapter(BaseAdapter):
    """Connects to on-prem SAP via RFC/BAPI"""
    pass
```

### Registry Selection

The adapter registry checks deployment configuration:

```python
# services/registry.py
def get_adapter(integration_type: str, tenant: Tenant) -> BaseAdapter:
    config = IntegrationConfig.objects.get(tenant=tenant, integration_type=integration_type)

    # Check for deployment-level override
    deployment_mode = getattr(settings, f'{integration_type.upper()}_MODE', 'cloud')

    adapters = {
        ('sap', 'cloud'): SAPCloudAdapter,
        ('sap', 'onprem'): SAPOnPremAdapter,
        ('hubspot', 'cloud'): HubSpotAdapter,
        # On-prem CRM would be a different integration type
    }

    adapter_class = adapters.get((integration_type, deployment_mode))
    return adapter_class(config)
```

### Configuration Sources

| Deployment | Config Source |
|------------|---------------|
| Cloud/SaaS | `IntegrationConfig` table (per-tenant) |
| On-prem | Environment variables + `IntegrationConfig` |
| Air-gapped | Environment variables only |

---

## Polling for Air-Gapped Environments

When webhooks aren't available (no inbound internet), use Celery beat for scheduled polling:

```python
# celery.py
app.conf.beat_schedule = {
    'sync-erp-orders-every-5-minutes': {
        'task': 'integrations.tasks.poll_erp_orders',
        'schedule': crontab(minute='*/5'),
    },
    'sync-erp-inventory-hourly': {
        'task': 'integrations.tasks.poll_erp_inventory',
        'schedule': crontab(minute=0),
    },
}
```

**Polling task pattern:**

```python
@shared_task
def poll_erp_orders():
    """Poll ERP for order changes since last sync."""
    for config in IntegrationConfig.objects.filter(
        integration_type='sap',
        enabled=True,
        settings__polling_enabled=True
    ):
        adapter = get_adapter('sap', config.tenant)
        last_sync = config.settings.get('last_poll_timestamp')

        changes = adapter.get_changes_since(last_sync)
        for change in changes:
            process_inbound_change.delay(config.id, change)

        config.settings['last_poll_timestamp'] = timezone.now().isoformat()
        config.save()
```

---

## Resolved Questions

| Question | Resolution |
|----------|------------|
| ~~django-outbox-pattern?~~ | No — Celery with retries is sufficient |
| ~~OAuth flow UI?~~ | Deferred — manual credential entry first |
| ~~Sync conflicts?~~ | Source-of-truth per field (see Conflict Resolution) |
| ~~Field mapping per tenant?~~ | Yes — base mappings + per-tenant overrides (details TBD) |
| ~~Cloud vs on-prem adapters?~~ | Single registry, deployment config selects adapter |
| ~~Polling for air-gapped?~~ | Celery beat schedule |

---

## Open Questions

*None currently — all initial questions resolved.*
