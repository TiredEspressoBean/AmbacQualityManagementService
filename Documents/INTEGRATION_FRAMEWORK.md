# Integration Framework

## Overview

A separate Django app (`integrations/`) for connecting uqmes to external systems (CRM, ERP, accounting, etc.) without polluting the core Tracker models. HubSpot is the reference implementation. The existing HubSpot integration -- currently welded into Orders and Companies via inline fields and reading credentials from Django settings -- gets refactored into this framework.

This is not an integration platform or an embedded iPaaS. It is the minimum viable framework for tenant-scoped native integrations within uqmes.

---

## The Central Problem

> HubSpot is welded into the data model. Every tenant sees HubSpot fields. Only one HubSpot account can exist globally. Adding a second CRM would mean adding more inline fields to Orders.

The current architecture was built for one customer (Ambac) with one HubSpot account. Going multi-tenant means:

- Tenant A uses HubSpot. Tenant B uses Salesforce. Tenant C uses no CRM at all.
- Each tenant's credentials are isolated and encrypted.
- Each tenant's UI only shows integration features they've configured.
- Adding a new provider doesn't require a migration on the Orders table.

---

## Goals

1. **Multi-tenant** -- Each tenant configures their own integrations
2. **Zero cost for non-users** -- No fields/tables for tenants who don't use integrations
3. **Extensible** -- Adding Salesforce shouldn't touch the Orders model
4. **Template** -- HubSpot as reference implementation for future integrations
5. **Ambac continuity** -- Ambac's current gate/pipeline functionality must be preserved exactly as-is through the migration

---

## Key Decisions

### Separate Django App

- `integrations/` lives alongside `Tracker/`
- One-way dependency: integrations imports from Tracker, never reverse
- Can be excluded from deployments that don't need it

### Separate Link Tables Per Integration

- `HubSpotOrderLink`, `SalesforceOrderLink`, etc.
- NOT GenericForeignKey (loses referential integrity, can't use `select_related`)
- NOT a single generic `ExternalOrderLink` with a provider FK
- Each integration has its own schema (HubSpot has deals with pipeline stages, Salesforce has opportunities with forecast categories, QuickBooks has invoices with line items). Separate tables give real columns, real constraints, real queryability per provider.

### Adapter Pattern

- Common interface (BaseAdapter base class) for all integrations
- Rest of system doesn't know which CRM is connected
- Adapter registry selects implementation by integration type and deployment mode
- Easy to swap or add integrations

### Per-Tenant Configuration

- `IntegrationConfig` model stores credentials and settings per tenant
- Encrypted credentials at rest (using existing `django-encrypted-model-fields` pattern from `TenantLLMProvider`)
- Enable/disable per tenant

### Audit Trail

- Link tables track current sync state (`last_synced_at`, `sync_status`, `last_error`)
- Celery `TaskResult` (via django-celery-results) provides task history and error details
- `ProcessedWebhook` for idempotency (don't process same event twice)
- Full `SyncLog` table can be added later if detailed per-entity history is needed (enterprise)

---

## Abstract Event Types

At the fundamental level, integrations handle only a few kinds of events:

### 1. Data Replication
*"Keep these two things in sync"*

- Your Order <-> Their Deal
- Your Company <-> Their Account
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
| **Query** | Outbound->Inbound | Yes (data) | Retry, fallback |

### Integration Type Mapping

| Integration | Primary Type |
|-------------|--------------|
| HubSpot/Salesforce (CRM) | Data Replication |
| QuickBooks/Xero (Accounting) | Commands + Queries |
| Slack/Teams | Event Notification |
| ERP (SAP, NetSuite) | Commands + Queries |
| LDAP/Active Directory | Query (auth lookup) |
| Shipping (FedEx, UPS) | Command |

---

## File Structure

```
integrations/
├── models/
│   ├── config.py               # IntegrationConfig, IntegrationSyncLog, ProcessedWebhook
│   └── links/
│       ├── hubspot.py          # HubSpotOrderLink, HubSpotCompanyLink, HubSpotPipelineStage
│       └── ...                 # Future: salesforce.py, quickbooks.py
├── adapters/
│   ├── base.py                 # BaseAdapter, BaseFetcher, ADAPTER_API_VERSION
│   ├── hubspot/
│   │   ├── manifest.py         # MANIFEST dict (metadata, auth type, link models)
│   │   ├── adapter.py          # HubSpotAdapter (wires SDK to serializers)
│   │   ├── serializers.py      # HubSpotConfigSerializer, HubSpotDealInboundSerializer, etc.
│   │   └── sync.py             # sync_all_deals() orchestration (SDK -> serializer)
│   └── ...                     # Future adapters follow same structure
├── services/
│   ├── registry.py             # get_adapter(), discover_capabilities(), settings-based
│   └── gate_info.py            # get_gate_info_for_stage() utility
├── webhooks/
│   ├── views.py                # integration_webhook() — routing, auth, idempotency
│   └── handlers/
│       └── hubspot.py          # HubSpot-specific webhook processing
├── signals.py                  # post_save on HubSpotOrderLink -> push task
├── tasks.py                    # sync_all_integrations_task, provider-specific sync/push tasks
├── serializers.py              # IntegrationConfigSerializer, link serializers for API
├── viewsets.py                 # IntegrationConfig CRUD, set_pipeline_stage action
├── filters.py                  # FilterSets for sync logs, integration listing
└── urls.py                     # Webhook endpoints + API routes
```

---

## What Exists Today (Current State)

### Inline Fields on Core Models

**Orders** (`Tracker/models/mes_lite.py` lines 1660-1672):
```python
# HubSpot Integration Fields
current_hubspot_gate = models.ForeignKey("ExternalAPIOrderIdentifier", ...)
hubspot_deal_id = models.CharField(max_length=60, null=True, blank=True, db_index=True)
last_synced_hubspot_stage = models.CharField(max_length=100, null=True, blank=True)
hubspot_last_synced_at = models.DateTimeField(null=True, blank=True)
```

Plus `save()` logic (lines 1694-1718) that detects `current_hubspot_gate` changes and fires `update_hubspot_deal_stage_task.delay()`. Plus `push_to_hubspot()`, `_should_push_to_hubspot()`, and `get_gate_info()` methods. Plus a unique constraint: `orders_tenant_hubspot_deal_uniq` on `(tenant, hubspot_deal_id)`.

**Companies** (`Tracker/models/core.py` line 1242):
```python
hubspot_api_id = models.CharField(max_length=50, null=True, blank=True)
```

**ExternalAPIOrderIdentifier** (`Tracker/models/core.py` lines 1254-1316):
```python
class ExternalAPIOrderIdentifier(SecureModel):
    stage_name = models.CharField(max_length=100)
    API_id = models.CharField(max_length=50)
    pipeline_id = models.CharField(max_length=50, null=True, blank=True)
    display_order = models.IntegerField(default=0)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    include_in_progress = models.BooleanField(default=False)
```

Nominally generic but entirely HubSpot-specific. Has `get_customer_display_name()` that strips "Gate One" / "Gate Two" prefixes -- an Ambac convention. Inherits from `SecureModel`, which provides `tenant` FK, `created_at`, `updated_at`, and the `.for_user()` queryset method used for multi-tenant scoping.

**HubSpotSyncLog** (`Tracker/models/integrations/hubspot.py`):
```python
class HubSpotSyncLog(models.Model):
    sync_type = models.CharField(max_length=20, choices=SYNC_TYPE_CHOICES)  # FULL, INCREMENTAL, SINGLE
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)        # RUNNING, SUCCESS, FAILED
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    deals_processed = models.IntegerField(default=0)
    deals_created = models.IntegerField(default=0)
    deals_updated = models.IntegerField(default=0)
    error_message = models.TextField(null=True, blank=True)
```
Note: No `tenant` FK on this model -- all logs are global. The data migration assigns them to the first `IntegrationConfig` found.

### Credentials in Settings

```python
# settings.py
HUBSPOT_API_KEY = os.environ.get("HUBSPOT_API_KEY")
HUBSPOT_DEBUG = os.getenv("HUBSPOT_DEBUG", "false").lower() in {"1", "true", "yes"}
```

One API key, globally.

### Integration Service Layer (Built but Unused)

- `IntegrationService` ABC in `Tracker/integrations/base_service.py`
- `IntegrationRegistry` in `Tracker/integrations/registry.py`
- `HubSpotService` in `Tracker/integrations/hubspot_service.py`
- `IntegrationConfig` dataclass
- `ExternalSyncMixin` and `ExternalPipelineMixin` in `Tracker/integrations/base.py` (deprecated, never used)

Nothing in the running application calls through `HubSpotService`. The Celery tasks, the `save()` method, and the webhook view all call `Tracker/hubspot/api.py` and `Tracker/hubspot/sync.py` directly.

### Working HubSpot Code

- `Tracker/hubspot/api.py` -- raw HTTP calls to HubSpot REST API
- `Tracker/hubspot/sync.py` -- `sync_all_deals(tenant)` bulk sync, creates/updates Orders + Users + Companies
- `Tracker/hubspot_view.py` -- webhook endpoint at `/webhooks/hubspot/`
- `Tracker/tasks.py` -- `RetryableHubSpotTask` base, `sync_hubspot_deals_task`, `update_hubspot_deal_stage_task`
- `Tracker/management/commands/sync_hubspot.py` -- CLI
- Celery Beat: hourly schedule

### Existing Encryption Pattern

`TenantLLMProvider` (`Tracker/models/core.py` lines 196-204):
```python
from encrypted_model_fields.fields import EncryptedCharField
api_key = EncryptedCharField(max_length=500, blank=True, default='')
```
Uses `django-encrypted-model-fields==0.6.5` (already in requirements.txt).

### Existing Bug

In `Orders.save()`, the `_should_push_to_hubspot()` method does **not** check for `_skip_hubspot_push`. The flag is set by `sync.py` and `hubspot_service.py` but never read. Every sync-triggered save currently tries to push back to HubSpot. It doesn't cause an infinite loop only because the stage hasn't changed from HubSpot's perspective -- but it's wasted API calls and a latent bug.

### Frontend Touchpoints (8 files)

| File | What it shows |
|---|---|
| `OrderFormPage.tsx` | "Current HubSpot Gate" dropdown via `useListHubspotGates` hook |
| `TrackerCard.tsx` | Gate progress bar (collapsed: name + position + %; expanded: full stage list) |
| `TrackerPage.tsx` | Filters orders by `gate_info !== null` for visibility |
| `fieldsConfigMap.tsx` | HubSpot fields on order detail ("Integration & System" section) and company detail ("Integration" section) |
| `CompaniesEditorPage.tsx` | "HubSpot API ID" column in company list |
| `EditCompanyFormPage.tsx` | "HubSpot API ID" text input in company form |
| `useListHubspotGates.ts` | React Query hook wrapping `api.api_HubspotGates_list()` |
| `generated.ts` | API client with HubspotGates endpoints and schema types |

---

## Ambac Gate Functionality: What Must Be Preserved

Ambac's HubSpot integration provides a specific user-facing feature: **pipeline gate tracking**. This must continue working identically after migration.

### What users see today

- **Order form**: a "Current HubSpot Gate" dropdown populated from `ExternalAPIOrderIdentifier` records. Users can manually set which pipeline stage an order is in.
- **Tracker page**: each order card shows a progress bar with the current gate name (e.g., "Quotation"), position (e.g., "Stage 3/7"), and progress percentage. Only orders with `gate_info` or production stages are shown.
- **Tracker card expanded view**: lists all pipeline stages with completed/current/pending status icons.
- **Order detail page**: shows "Current HubSpot Gate" and "Last Synced HubSpot Stage" in an "Integration & System" section.
- **Company detail/edit**: shows "HubSpot API ID" field.
- **Active pipeline filter**: `?active_pipeline=true` shows only orders that are local (no deal ID) or whose current gate starts with "Gate" (Ambac's convention for active pipeline stages vs closed/lost).

### What happens behind the scenes

- Hourly Celery Beat sync pulls all HubSpot deals, creates/updates Orders with `hubspot_deal_id`, syncs pipeline stages to `ExternalAPIOrderIdentifier`, creates Users and Companies from contacts.
- When a user changes the gate dropdown and saves, `Orders.save()` detects the change and queues a Celery task to push the stage update back to HubSpot.
- HubSpot webhooks update the local order's gate when someone changes the deal stage in HubSpot.
- `_skip_hubspot_push` flag prevents sync-triggered saves from pushing back (though currently bugged -- flag is set but never checked).
- The "Ghost Pepper" debug mode (`HUBSPOT_DEBUG=True`) limits sync to a single named deal for testing.

### What must survive the migration

All of this. The gate dropdown, the progress bar, the sync, the push-back, the webhook, the filter. The data moves from inline fields to link tables, the credentials move from settings to database, the push logic moves from `Orders.save()` to a signal on the link model -- but from Ambac's users' perspective, nothing changes.

The `get_gate_info()` method's output shape must remain identical so `TrackerCard.tsx` and `TrackerPage.tsx` need zero changes. The `gate_info` computed field on the serializer continues to work, it just reads from the link model instead of inline fields.

### Pipeline tracking is opt-in via integration config

Pipeline visualization (progress bars, gate dropdown, active pipeline filter) is controlled by a `pipeline_tracking_enabled` flag in `IntegrationConfig.config`. Ambac's migrated config has this set to `true`. New tenants default to `false` -- they get basic HubSpot sync (deals become orders, contacts become users) without the pipeline UI.

The `active_stage_prefix` config value (default: `"Gate"`) controls which stages count as "active" for the pipeline filter. This replaces the hardcoded `startswith('Gate')` check. Ambac keeps `"Gate"`, another tenant could set `"Stage"` or leave it blank to include all stages.

This means:
- The backend always syncs pipeline stages to `HubSpotPipelineStage` if they exist in HubSpot
- The `gate_info` serializer field only populates when `pipeline_tracking_enabled` is `true`
- The frontend gate dropdown only renders when the integration config says to show it
- The `filter_active_pipeline` uses the configured prefix instead of hardcoded `"Gate"`

---

## Native Order Milestones (Tracker App)

### Why milestones belong in the core app, not the integration app

Manufacturers track where orders are in their business process — from inquiry to delivery. This is a universal need across every manufacturing vertical (automotive APQP gates, aerospace design reviews, medical device design controls, job shop status tracking). It's not a CRM feature — it's a core QMS/MES capability that the customer portal depends on.

Currently, Ambac tracks this via HubSpot pipeline stages. But:
- Job shops without a CRM need milestones too (they're the biggest addressable market)
- The customer portal's progress bar should work for every tenant, not just those with CRM integrations
- 74% of B2B buyers prefer suppliers with digital order tracking — the portal with milestone visibility is a core selling point
- Competitors (ProShop, JobBOSS2, QT9, Plex) all have order status visibility in their portals — it's table stakes

### What already exists

- `OrdersStatus` enum: RFI, Pending, In Progress, Completed, On Hold, Cancelled — these are **states** (current condition, can go backwards)
- `APQPStage` enum: the 5 standard APQP phases — **defined but unused** (never added as a field on Orders)
- `current_hubspot_gate` FK on Orders — what actually tracks the business milestone today, but tied to HubSpot
- `process_stages` on the tracker serializer — shop floor step progression (MES data, different layer)
- `gate_info` computed field — the progress bar data for the customer portal

### What milestones are NOT

- **Not production steps** — you have the step/process DAG for shop floor operations. Milestones are above that.
- **Not order status** — "On Hold" is a state, "Engineering" is a milestone. An order can be at milestone "Production" and status "On Hold" simultaneously.
- **Not a workflow engine** — no automatic transitions, no required approvals (those can be added later). Just tracking.

### New models (in Tracker app, not integrations app)

```python
class MilestoneTemplate(SecureModel):
    """
    Tenant-defined ordered sequence of business milestones.

    Each tenant can have multiple templates for different order types.
    Examples:
      - "Standard Order Process": Quote → PO → Engineering → Production → Ship
      - "APQP Process": Planning → Design → Process Dev → Validation → Production
      - "Repair Process": Receive → Evaluate → Quote → Repair → Ship
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False,
        help_text="Default template for new orders")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'name'],
                name='milestone_template_tenant_name_uniq'
            ),
        ]
        ordering = ['-is_default', 'name']


class Milestone(SecureModel):
    """
    A single milestone within a template.
    Ordered sequence — display_order determines the progression.
    """
    template = models.ForeignKey(MilestoneTemplate, on_delete=models.CASCADE,
        related_name='milestones')
    name = models.CharField(max_length=100)
    display_order = models.IntegerField(default=0)
    description = models.TextField(blank=True)
    customer_display_name = models.CharField(max_length=100, blank=True,
        help_text="Optional customer-facing name (e.g., 'Design Review' instead of 'Gate Two - Design Review')")

    class Meta:
        ordering = ['template', 'display_order']
        constraints = [
            models.UniqueConstraint(
                fields=['template', 'display_order'],
                name='milestone_template_order_uniq'
            ),
        ]

    def get_display_name(self):
        """Return customer_display_name if set, otherwise name."""
        return self.customer_display_name or self.name
```

And on Orders:

```python
# Add to Orders model:
current_milestone = models.ForeignKey('Milestone', null=True, blank=True,
    on_delete=models.SET_NULL, related_name='orders')
"""Current business milestone for this order. Set manually or synced from CRM/ERP."""
```

### How `gate_info` changes

The `gate_info` computed field on the serializer reads from `current_milestone` instead of `current_hubspot_gate` or `HubSpotOrderLink.current_stage`:

```python
def get_gate_info(self, obj):
    if not obj.current_milestone:
        return None

    milestone = obj.current_milestone
    all_milestones = list(milestone.template.milestones.all().order_by('display_order'))

    current_index = next(
        (i for i, m in enumerate(all_milestones) if m.id == milestone.id), None
    )
    if current_index is None:
        return None

    return {
        'current_gate_name': milestone.get_display_name(),
        'current_gate_full_name': milestone.name,
        'is_in_progress': True,
        'current_position': current_index + 1,
        'total_gates': len(all_milestones),
        'progress_percent': round(((current_index + 1) / len(all_milestones)) * 100),
        'gates': [
            {
                'name': m.get_display_name(),
                'full_name': m.name,
                'is_current': m.id == milestone.id,
                'is_completed': i < current_index,
            }
            for i, m in enumerate(all_milestones)
        ],
    }
```

The output shape is **identical** to the current `gate_info`. TrackerCard.tsx and TrackerPage.tsx need zero changes.

### How integrations sync to milestones

The HubSpot integration maps its pipeline stages to native milestones:

- `HubSpotPipelineStage` gets a FK to `Milestone`: `mapped_milestone = models.ForeignKey('Tracker.Milestone', null=True, blank=True, ...)`
- During sync, when the integration resolves a deal's stage, it sets `order.current_milestone` to the mapped milestone
- The mapping is set up during integration configuration (admin maps each HubSpot stage to a milestone, or auto-maps by name)
- Push direction: when `current_milestone` changes on an order that has a `HubSpotOrderLink`, the integration looks up the reverse mapping and pushes the corresponding stage to HubSpot

This means:
- Tenants without integrations: set milestones manually via the order form
- Tenants with HubSpot: milestones sync from/to HubSpot pipeline stages
- Tenants with Salesforce (future): milestones sync from/to opportunity stages
- The UI always reads from the native `current_milestone` — never from integration-specific data

### Preset templates

Seed common templates during tenant setup:

```python
PRESET_TEMPLATES = {
    'standard': {
        'name': 'Standard Order Process',
        'milestones': ['Quoting', 'PO Received', 'Engineering', 'Production', 'Shipping', 'Complete'],
    },
    'apqp': {
        'name': 'APQP Process',
        'milestones': ['Planning', 'Product Design & Development', 'Process Design & Development',
                       'Product & Process Validation', 'Production'],
    },
    'repair': {
        'name': 'Repair Process',
        'milestones': ['Receive', 'Evaluate', 'Quote', 'Approve', 'Repair', 'QC', 'Ship'],
    },
}
```

The existing `APQPStage` enum can be removed — its values become a preset template.

### Data migration

For Ambac's existing data:
1. Create a `MilestoneTemplate` from their HubSpot pipeline stages (the 9 stages we synced)
2. Create `Milestone` records from each `HubSpotPipelineStage`
3. Set `HubSpotPipelineStage.mapped_milestone` FK for each stage
4. For each `HubSpotOrderLink` with a `current_stage`, set `order.current_milestone` to the mapped milestone
5. The `current_hubspot_gate` inline field (old) and `HubSpotOrderLink.current_stage` (new integration) both feed into `current_milestone` (native)

### Filter changes

`filter_active_pipeline` reads from the native milestone model:

```python
def filter_active_pipeline(self, queryset, name, value):
    if value:
        return queryset.filter(
            Q(current_milestone__isnull=True) |
            Q(current_milestone__name__startswith=self._get_active_prefix(self.request))
        )
    return queryset
```

Or better: add an `is_active` boolean on `Milestone` that the tenant configures (which milestones count as "active in progress" vs "closed/completed"). Eliminates the prefix string matching entirely.

---

## Core Models

### IntegrationConfig

Per-tenant integration credentials and config. Follows the existing `TenantLLMProvider` pattern.

```python
class IntegrationConfig(models.Model):
    """
    One row per integration per tenant. Stores credentials (encrypted),
    provider-specific config, and sync status.
    """

    class Provider(models.TextChoices):
        HUBSPOT = 'hubspot', 'HubSpot CRM'
        SALESFORCE = 'salesforce', 'Salesforce CRM'
        QUICKBOOKS = 'quickbooks', 'QuickBooks Online'
        XERO = 'xero', 'Xero'

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    tenant = models.ForeignKey('Tracker.Tenant', on_delete=models.CASCADE, related_name='integrations')
    provider = models.CharField(max_length=30, choices=Provider.choices)
    display_name = models.CharField(max_length=100, blank=True)

    is_enabled = models.BooleanField(default=False)  # disabled until credentials are entered and verified

    class SyncStatus(models.TextChoices):
        IDLE = 'IDLE', 'Idle'
        SYNCING = 'SYNCING', 'Syncing'
        ERROR = 'ERROR', 'Error'

    sync_status = models.CharField(max_length=10, choices=SyncStatus.choices, default=SyncStatus.IDLE)

    # Credentials (encrypted at rest)
    # API key auth (HubSpot, etc.)
    api_key = EncryptedCharField(max_length=500, blank=True, default='')
    # OAuth2 auth (QuickBooks, Salesforce, etc.)
    oauth_refresh_token = EncryptedCharField(max_length=500, blank=True, default='')
    oauth_token_expires_at = models.DateTimeField(null=True, blank=True)
    # Webhook
    webhook_secret = EncryptedCharField(max_length=500, blank=True, default='')
    # Optional API URL override (e.g. sandbox)
    api_url = models.URLField(blank=True, default='')

    # Provider-specific configuration
    # HubSpot: {"pipeline_id": "...", "debug_mode": false, "debug_deal_name": "Ghost Pepper",
    #           "pipeline_tracking_enabled": true, "active_stage_prefix": "Gate"}
    # QuickBooks: {"company_id": "...", "sandbox": true}
    config = models.JSONField(default=dict, blank=True)

    # Sync tracking
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_sync_error = models.TextField(null=True, blank=True)
    last_sync_stats = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'integrations_config'
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'provider'],
                name='integrations_config_tenant_provider_uniq'
            ),
        ]
```

### ProcessedWebhook

```python
class ProcessedWebhook(models.Model):
    """Idempotency guard -- don't process the same event twice."""
    tenant = models.ForeignKey('Tracker.Tenant', on_delete=models.CASCADE)
    integration = models.ForeignKey('IntegrationConfig', on_delete=models.CASCADE)
    external_event_id = models.CharField(max_length=200)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'integrations_processed_webhook'
        constraints = [
            models.UniqueConstraint(
                fields=['integration', 'external_event_id'],
                name='integrations_webhook_idempotency'
            ),
        ]
```

### IntegrationSyncLog

History of sync operations per integration. Used for troubleshooting ("it was working until Tuesday"), compliance auditing ("show me every data exchange for the last 6 months"), and the admin UI sync status dashboard.

`IntegrationConfig.last_sync_stats` is a denormalized convenience field for the common "is this integration healthy right now" check. The log table is the real history.

```python
class IntegrationSyncLog(models.Model):
    """
    Records each sync operation for an integration.
    Replaces: HubSpotSyncLog (which was HubSpot-specific).
    """

    class SyncType(models.TextChoices):
        FULL = 'FULL', 'Full Sync'
        INCREMENTAL = 'INCREMENTAL', 'Incremental Sync'
        SINGLE = 'SINGLE', 'Single Record Sync'
        PUSH = 'PUSH', 'Outbound Push'

    class Status(models.TextChoices):
        RUNNING = 'RUNNING', 'Running'
        SUCCESS = 'SUCCESS', 'Success'
        FAILED = 'FAILED', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    integration = models.ForeignKey('IntegrationConfig', on_delete=models.CASCADE,
        related_name='sync_logs')
    sync_type = models.CharField(max_length=20, choices=SyncType.choices, default=SyncType.FULL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RUNNING)
    started_at = models.DateTimeField(default=timezone.now)  # not auto_now_add -- allows explicit set during migration
    completed_at = models.DateTimeField(null=True, blank=True)
    records_processed = models.IntegerField(default=0)
    records_created = models.IntegerField(default=0)
    records_updated = models.IntegerField(default=0)
    error_message = models.TextField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True,
        help_text="Provider-specific details (e.g. pipeline stages synced, contacts created)")

    class Meta:
        db_table = 'integrations_sync_log'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['-started_at']),
            models.Index(fields=['integration', 'status']),
        ]

    @property
    def duration(self):
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
```

---

### HubSpot Link Tables (per-integration, not generic)

```python
class HubSpotPipelineStage(models.Model):
    """
    Maps HubSpot pipeline stage IDs to human-readable names.

    Replaces ExternalAPIOrderIdentifier. Provider-specific because
    pipeline stages are a HubSpot concept -- Salesforce has "opportunity stages"
    with different properties.
    """
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    integration = models.ForeignKey('IntegrationConfig', on_delete=models.CASCADE,
        related_name='hubspot_pipeline_stages')
    stage_name = models.CharField(max_length=100)
    api_id = models.CharField(max_length=50)
    pipeline_id = models.CharField(max_length=50, null=True, blank=True)
    display_order = models.IntegerField(default=0)
    include_in_progress = models.BooleanField(default=False)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    # Maps this HubSpot stage to a native Milestone in the Tracker app.
    # Set during integration configuration. Used by sync to set order.current_milestone.
    mapped_milestone = models.ForeignKey('Tracker.Milestone', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='hubspot_stages')

    class Meta:
        db_table = 'integrations_hubspot_pipeline_stage'
        ordering = ['pipeline_id', 'display_order']
        constraints = [
            models.UniqueConstraint(
                fields=['integration', 'api_id'],
                name='hubspot_stage_integration_apiid_uniq'
            ),
        ]

    def get_customer_display_name(self):
        """Remove 'Gate [Word] ' prefix for customer-facing display."""
        import re
        cleaned = re.sub(r'^Gate\s+\w+\s+', '', self.stage_name)
        return cleaned if cleaned != self.stage_name else self.stage_name


class HubSpotOrderLink(models.Model):
    """
    Links a local Order to a HubSpot Deal.

    Replaces: Orders.hubspot_deal_id, current_hubspot_gate,
              last_synced_hubspot_stage, hubspot_last_synced_at
    """
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    order = models.OneToOneField('Tracker.Orders', on_delete=models.CASCADE,
        related_name='hubspot_link')
    integration = models.ForeignKey('IntegrationConfig', on_delete=models.PROTECT,
        related_name='hubspot_order_links')

    deal_id = models.CharField(max_length=60)
    current_stage = models.ForeignKey('HubSpotPipelineStage',
        on_delete=models.SET_NULL, null=True, blank=True)
    last_synced_stage_name = models.CharField(max_length=100, null=True, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_sync_error = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'integrations_hubspot_order_link'
        constraints = [
            models.UniqueConstraint(
                fields=['integration', 'deal_id'],
                name='hubspot_order_link_integration_dealid_uniq'
            ),
        ]


class HubSpotCompanyLink(models.Model):
    """
    Links a local Company to a HubSpot Company.
    FK (not OneToOne) because a company could also be linked via QuickBooks etc.

    Replaces: Companies.hubspot_api_id
    """
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    company = models.ForeignKey('Tracker.Companies', on_delete=models.CASCADE,
        related_name='hubspot_links')
    integration = models.ForeignKey('IntegrationConfig', on_delete=models.PROTECT,
        related_name='hubspot_company_links')
    hubspot_company_id = models.CharField(max_length=50)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'integrations_hubspot_company_link'
        constraints = [
            models.UniqueConstraint(
                fields=['integration', 'hubspot_company_id'],
                name='hubspot_company_link_integration_companyid_uniq'
            ),
        ]
```

Note how HubSpot link tables use HubSpot-specific field names (`deal_id`, not `external_id`; `company_id`, not `external_id`). This is intentional -- each integration speaks its own language. When Salesforce is added, `SalesforceOrderLink` will have `opportunity_id`.

---

## Conflict Resolution

### Source-of-Truth Per Field

When both systems change the same data, resolve by field ownership:

| Field Category | Owner | Direction |
|----------------|-------|-----------|
| **Operational data** (part status, quality results, workflow state) | uqmes | Push to CRM only |
| **Sales/customer data** (contact info, deal stage, notes) | CRM | Pull from CRM only |
| **Shared fields** (order name, dates) | Pick one | Configure per field |

### Rules

- Operational fields -> `push` only (never let CRM overwrite quality data)
- Customer fields -> `pull` only (CRM owns customer contact info)
- Avoid `bidirectional` unless necessary -- requires timestamp comparison and conflict detection

---

## Field Mapping

Field mapping is needed because external systems have different field names (`Order.name` -> `Deal.dealname`) and tenants may have custom CRM fields.

**Key decisions:**
- Base mappings defined by us (sensible defaults)
- Per-tenant overrides stored in `IntegrationConfig.config` JSONField
- Direction per field: `push`, `pull`, or `bidirectional` (ties into conflict resolution)

**Details TBD during implementation.**

---

## Moving Push Logic Out of Orders.save()

Currently, `Orders.save()` (line 1694-1718) detects `current_hubspot_gate` changes and fires the Celery push task. This couples the Orders model to HubSpot.

The fix: move push logic to a `post_save` signal on `HubSpotOrderLink`.

**Change detection:** Use `django-model-utils` `FieldTracker` on `HubSpotOrderLink` to detect when `current_stage` changes. Add `stage_tracker = FieldTracker(fields=['current_stage'])` to the model. The signal checks `instance.stage_tracker.has_changed('current_stage')`.

```python
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=HubSpotOrderLink)
def push_stage_change_to_hubspot(sender, instance, **kwargs):
    """When a HubSpotOrderLink's stage changes, push to HubSpot."""
    if not instance.integration.is_enabled:
        return
    if getattr(instance, '_skip_external_push', False):
        return
    if not instance.stage_tracker.has_changed('current_stage'):
        return

    from integrations.tasks import push_hubspot_deal_stage_task
    push_hubspot_deal_stage_task.delay(
        integration_id=str(instance.integration_id),
        deal_id=instance.deal_id,
        stage_id=str(instance.current_stage_id),
        order_id=str(instance.order_id),
    )
```

**Push path clarification:** The outbound push flow is: user changes stage in UI → `set_pipeline_stage` action on viewset → `link.save()` → `post_save` signal fires → signal dispatches `push_hubspot_deal_stage_task` via Celery → task loads the integration, calls `adapter.push_order_status(integration, link, stage)` → adapter calls `update_deal_stage()` with the integration's API key. The signal handles async dispatch, the adapter method handles the actual API call.

**Frontend gate dropdown write path:** The `HubSpotOrderLink` serializer is read-only when nested in the `OrderSerializer`. To update the stage, expose a separate endpoint or a custom action on the Order viewset:

```python
# On OrderViewSet:
@action(detail=True, methods=['patch'])
def set_pipeline_stage(self, request, pk=None):
    """PATCH /api/orders/{id}/set_pipeline_stage/ {"stage_id": "..."}"""
    order = self.get_object()
    link = getattr(order, 'hubspot_link', None)
    if not link:
        return Response({"error": "No integration link"}, status=400)
    stage = HubSpotPipelineStage.objects.get(
        id=request.data['stage_id'],
        integration=link.integration,  # ensure stage belongs to same integration
    )
    link.current_stage = stage
    link.save()  # triggers signal -> push to HubSpot
    return Response(HubSpotOrderLinkSerializer(link).data)
```

The frontend gate dropdown calls this action endpoint instead of PATCHing `current_hubspot_gate` directly on the order.

**`get_gate_info` utility:** Moves to `integrations/services/gate_info.py` as a standalone function:

```python
def get_gate_info_for_stage(stage):
    """
    Build gate_info dict from a HubSpotPipelineStage.
    Returns the same shape as the current Orders.get_gate_info() output.
    """
    if not stage:
        return None

    active_stages = HubSpotPipelineStage.objects.filter(
        integration=stage.integration,
        pipeline_id=stage.pipeline_id,
        include_in_progress=True
    ).order_by('display_order')

    # ... same logic as current get_gate_info(), building:
    # {current_gate_name, current_gate_full_name, is_in_progress,
    #  current_position, total_gates, progress_percent, gates: [...]}
```

`Orders.save()` becomes clean manufacturing logic. All HubSpot methods (`push_to_hubspot()`, `_should_push_to_hubspot()`, `get_gate_info()`) are removed from the Orders model.

This also fixes the `_skip_hubspot_push` bug.

---

## Rewiring hubspot/ to the New Pattern

The current `Tracker/hubspot/api.py` and `Tracker/hubspot/sync.py` are replaced by the ETL composition described in the Adapter Pattern section:

- `api.py` raw HTTP calls → **`HubSpotDealFetcher`**, **`HubSpotCompanyFetcher`** (fetchers handle auth, pagination, retry via `BaseFetcher`)
- `sync.py` `_prepare_order_from_deal()` → **`HubSpotDealInboundSerializer`** (DRF serializer handles field mapping, validation, create/update with `transaction.atomic()`)
- `sync.py` `sync_all_deals()` → **`sync_all_deals(integration)`** that wires SDK calls to DRF serializers (see Adapter Pattern section for full example)
- `get_hubspot_api_key()` from settings → **`integration.api_key`** from database, passed to `HubSpot(access_token=...)`

The batch association fetching (contacts from deals, companies from deals) uses the SDK's batch APIs (`client.crm.companies.batch_api.read()`, etc.).

---

## Tasks

```python
# Celery Beat dispatches this hourly:
@shared_task
def sync_all_integrations_task():
    """Dispatch sync tasks for all enabled integrations."""
    for config in IntegrationConfig.objects.filter(is_enabled=True):
        adapter = get_adapter(config.provider)
        adapter.dispatch_sync_task(config)

# HubSpot-specific sync task:
@shared_task(bind=True, base=RetryableIntegrationTask)
def sync_hubspot_deals_task(self, integration_id):
    integration = IntegrationConfig.objects.get(id=integration_id)
    from integrations.adapters.hubspot.sync import sync_all_deals
    return sync_all_deals(integration)

# Push stage change (called from post_save signal on HubSpotOrderLink):
@shared_task(bind=True, base=RetryableIntegrationTask)
def push_hubspot_deal_stage_task(self, integration_id, deal_id, stage_id, order_id):
    integration = IntegrationConfig.objects.get(id=integration_id)
    link = HubSpotOrderLink.objects.get(integration=integration, deal_id=deal_id)
    stage = HubSpotPipelineStage.objects.get(id=stage_id)
    adapter = get_adapter(integration.provider)
    adapter.push_order_status(integration, link=link, status=stage)
```

Note: `RetryableHubSpotTask` generalizes to `RetryableIntegrationTask` — same retry/backoff behavior, not provider-specific.

---

## Webhook Changes

URL-based routing (each integration gets a unique webhook URL):

```python
# urls.py
path("webhooks/<str:provider>/<uuid:integration_id>/", integration_webhook)
```

When a tenant configures HubSpot, they register `https://app.uqmes.com/webhooks/hubspot/{integration_id}/` in HubSpot's webhook settings.

```python
@csrf_exempt
def integration_webhook(request, provider, integration_id):
    integration = get_object_or_404(IntegrationConfig, id=integration_id, provider=provider, is_enabled=True)

    # Signature check FIRST -- before any DB reads or processing
    if not verify_webhook_signature(request, integration):
        return HttpResponseForbidden("Invalid signature")

    # Idempotency check -- prevent duplicate processing of same event
    event_id = extract_event_id(request, provider)
    if ProcessedWebhook.objects.filter(integration=integration, external_event_id=event_id).exists():
        return JsonResponse({"status": "already_processed"})

    # Dispatch to provider-specific handler
    adapter = registry.get_adapter(provider)
    result = adapter.handle_webhook(request, integration)

    ProcessedWebhook.objects.create(integration=integration, external_event_id=event_id, tenant=integration.tenant)
    return JsonResponse(result)
```

---

## Adapter Pattern

### Design Principles

Three principles from studying platforms at scale (Airbyte 300+ connectors, Zapier 8000+ integrations, Home Assistant 2000+ integrations):

1. **The code is the declaration.** Capabilities are discovered by introspecting which methods the adapter overrides, not declared separately. This is what Airbyte, Workato, Zapier, Tray.io, and Saleor all converge on. No enum, no manifest capabilities section — if you implemented the method, you support it.

2. **ETL composition with DRF.** All integrations do some subset of three operations: pull records in, push status out, receive events. The per-entity behavior is composed from reusable pieces: a Fetcher (extract, provider-specific), a DRF Serializer (transform + validate + load, mostly reusable), and signals (push). This prevents n^4 complexity (N providers × N entities × N capabilities × N implementations).

3. **Standard Django patterns.** Base class with `NotImplementedError` (same as django-allauth, Saleor, Celery, Django storage/auth). Settings-based registry with `import_string()`. DRF serializers for transform/validate/load. No new abstractions when existing ones suffice.

### Versioning

The adapter interface is versioned from day one.

```python
# integrations/adapters/base.py
ADAPTER_API_VERSION = 1
```

Every adapter's manifest declares which version it targets. The registry checks compatibility.

### Adapter Manifest

Each adapter has a Python dict declaring metadata — identity, auth requirements, link models. Capabilities are NOT in the manifest — they're discovered from the code. Config schema is NOT in the manifest — it's defined by a DRF serializer that drf-spectacular exposes via OpenAPI.

```python
# integrations/adapters/hubspot/manifest.py
from integrations.adapters.base import ADAPTER_API_VERSION

MANIFEST = {
    'id': 'hubspot',
    'name': 'HubSpot CRM',
    'description': 'Sync deals, contacts, and companies from HubSpot CRM',
    'version': '1.0.0',
    'adapter_api_version': ADAPTER_API_VERSION,
    'author': 'uqmes',
    'icon': 'hubspot.svg',
    'auth_type': 'api_key',  # or 'oauth2', 'basic', etc.
    'link_models': {
        'order': 'integrations.models.links.hubspot.HubSpotOrderLink',
        'company': 'integrations.models.links.hubspot.HubSpotCompanyLink',
        'pipeline_stage': 'integrations.models.links.hubspot.HubSpotPipelineStage',
    },
    'config_serializer': 'integrations.adapters.hubspot.serializers.HubSpotConfigSerializer',
}
```

A future QuickBooks manifest:

```python
MANIFEST = {
    'id': 'quickbooks',
    'name': 'QuickBooks Online',
    'version': '1.0.0',
    'adapter_api_version': ADAPTER_API_VERSION,
    'auth_type': 'oauth2',
    'link_models': {
        'company': 'integrations.models.links.quickbooks.QuickBooksCompanyLink',
        'invoice': 'integrations.models.links.quickbooks.QuickBooksInvoiceLink',
    },
    'config_serializer': 'integrations.adapters.quickbooks.serializers.QuickBooksConfigSerializer',
}
```

### Per-Provider Config Serializers

Instead of a `config_schema` dict on the manifest, each provider defines a DRF serializer for its config fields. drf-spectacular generates the OpenAPI schema. The frontend renders the settings form from the schema. Validation is handled by the serializer.

```python
# integrations/adapters/hubspot/serializers.py
from rest_framework import serializers

class HubSpotConfigSerializer(serializers.Serializer):
    """Validates and describes the provider-specific config for HubSpot."""
    pipeline_id = serializers.CharField(required=False, allow_blank=True, help_text="HubSpot pipeline ID")
    pipeline_tracking_enabled = serializers.BooleanField(default=False, help_text="Show pipeline progress UI")
    active_stage_prefix = serializers.CharField(required=False, default='', help_text="Stage prefix for active filter (e.g. 'Gate')")
    debug_mode = serializers.BooleanField(default=False)
    debug_deal_name = serializers.CharField(required=False, default='Ghost Pepper')

# integrations/adapters/quickbooks/serializers.py
class QuickBooksConfigSerializer(serializers.Serializer):
    company_id = serializers.CharField(required=True, help_text="QuickBooks Company ID")
    sandbox = serializers.BooleanField(default=False, help_text="Use sandbox environment")
```

### Capability Discovery via Method Introspection

No enum, no manifest declaration. The registry discovers what an adapter supports by checking which base class methods were overridden. This is the pattern used by Airbyte, Workato, Saleor, and every platform at scale.

```python
# integrations/services/registry.py

# Map of capability names to the base class method they correspond to
CAPABILITY_METHOD_MAP = {
    'order_sync': 'sync_orders',
    'company_sync': 'sync_companies',
    'contact_sync': 'sync_contacts',
    'push_order_status': 'push_order_status',
    'webhooks': 'handle_webhook',
    'pipeline_stages': 'has_pipeline_stages',  # property, not a sync method
}

def discover_capabilities(adapter):
    """
    Discover which capabilities an adapter supports by checking
    which BaseAdapter methods it overrides.
    """
    caps = set()
    for cap_name, method_name in CAPABILITY_METHOD_MAP.items():
        adapter_method = getattr(type(adapter), method_name, None)
        base_method = getattr(BaseAdapter, method_name, None)
        if adapter_method is not None and adapter_method is not base_method:
            caps.add(cap_name)
    return caps
```

The orchestration layer checks capabilities before calling:

```python
caps = discover_capabilities(adapter)
if 'order_sync' in caps:
    adapter.sync_orders(integration)
if 'company_sync' in caps:
    adapter.sync_companies(integration)
```

The frontend receives capabilities via the serializer:

```python
class IntegrationConfigSerializer(serializers.ModelSerializer):
    capabilities = serializers.SerializerMethodField()

    def get_capabilities(self, obj):
        adapter = get_adapter(obj.provider)
        return sorted(discover_capabilities(adapter))
    # Returns: ["company_sync", "order_sync", "pipeline_stages", "push_order_status", "webhooks"]
```

### ETL Composition: Fetcher + Serializer

All integration sync follows the ETL pattern. The Fetcher handles extraction (provider-specific API calls). DRF serializers handle transformation, validation, and loading. This prevents each adapter from being a monolithic block of code.

#### BaseFetcher (the only new abstraction)

```python
# integrations/adapters/base.py
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

class BaseFetcher:
    """
    Handles paginated extraction from external APIs.
    Uses requests.Session with urllib3 retry for HTTP-level resilience.
    Subclasses override get_page() for provider-specific pagination.
    """

    max_retries = 3
    backoff_factor = 1
    retry_status_codes = [429, 500, 502, 503, 504]

    def get_session(self, integration):
        """Build a requests.Session with retry/backoff and auth headers."""
        session = requests.Session()
        retry = Retry(
            total=self.max_retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=self.retry_status_codes,
        )
        session.mount('https://', HTTPAdapter(max_retries=retry))
        session.headers.update(self.get_auth_headers(integration))
        return session

    def get_auth_headers(self, integration):
        """Return auth headers. Override for OAuth2, etc."""
        return {
            'Authorization': f'Bearer {integration.api_key}',
            'Content-Type': 'application/json',
        }

    def fetch_all(self, integration, since=None):
        """Yield all records, handling pagination automatically."""
        session = self.get_session(integration)
        next_cursor = None
        while True:
            records, next_cursor = self.get_page(session, integration, cursor=next_cursor, since=since)
            yield from records
            if not next_cursor:
                break

    def get_page(self, session, integration, cursor=None, since=None):
        """
        Fetch one page of results. Override in subclass.
        Returns: (list[dict], next_cursor or None)
        """
        raise NotImplementedError
```

#### HubSpot: Uses Official SDK (no BaseFetcher)

HubSpot uses `hubspot-api-client` (official SDK) which handles pagination, rate limits, and auth natively. No `BaseFetcher` subclass needed:

```python
# integrations/adapters/hubspot/sync.py
from hubspot import HubSpot

def get_hubspot_client(integration):
    return HubSpot(access_token=integration.api_key)

def fetch_all_deals(integration):
    client = get_hubspot_client(integration)
    return client.crm.deals.get_all()  # SDK handles pagination + rate limits

def fetch_companies_by_ids(integration, company_ids):
    client = get_hubspot_client(integration)
    return client.crm.companies.batch_api.read(
        batch_read_input_simple_public_object_id={
            'properties': ['name', 'description'],
            'inputs': [{'id': cid} for cid in company_ids],
        }
    )
```

#### BaseFetcher Example (for providers without an SDK)

`BaseFetcher` is used when a provider has no official Python SDK and you're calling a REST API directly. Example for a hypothetical custom CRM:

```python
class CustomCRMOrderFetcher(BaseFetcher):
    """Fetches orders from a custom CRM with cursor-based pagination."""

    def get_page(self, session, integration, cursor=None, since=None):
        params = {'limit': 100}
        if cursor:
            params['after'] = cursor
        if since:
            params['updated_since'] = since.isoformat()

        response = session.get(f'{integration.api_url}/api/orders', params=params)
        response.raise_for_status()
        data = response.json()

        return data.get('results', []), data.get('next_cursor')
```

#### Inbound Serializers (Transform + Validate + Load)

DRF serializers replace the custom `_prepare_order_from_deal()` function. They handle field mapping, validation, and create/update in the standard DRF way.

```python
# integrations/adapters/hubspot/serializers.py
from rest_framework import serializers
from Tracker.models import Orders, Companies

class HubSpotDealInboundSerializer(serializers.ModelSerializer):
    """Deserializes a HubSpot deal dict into an Order."""

    class Meta:
        model = Orders
        fields = ['name', 'estimated_completion', 'customer', 'company', 'archived']

    def to_internal_value(self, data):
        """Map HubSpot deal properties to Order fields."""
        props = data.get('properties', {})
        return {
            'name': props.get('dealname', f"Deal {data['id']}"),
            'estimated_completion': props.get('closedate'),
            'archived': data.get('archived', False),
            # company and customer resolved in create() from associated data
        }

    def create(self, validated_data):
        """Create Order + HubSpotOrderLink in a single transaction."""
        from django.db import transaction
        from integrations.models.links.hubspot import HubSpotOrderLink

        integration = self.context['integration']
        deal_id = self.context['deal_id']
        current_stage = self.context.get('current_stage')
        tenant = integration.tenant

        with transaction.atomic():
            order = Orders.objects.create(tenant=tenant, **validated_data)
            link = HubSpotOrderLink.objects.create(
                order=order,
                integration=integration,
                deal_id=deal_id,
                current_stage=current_stage,
                last_synced_at=timezone.now(),
            )
            link._skip_external_push = True
            link.save()

        return order

    def update(self, instance, validated_data):
        """Update existing Order + link in a single transaction."""
        from django.db import transaction

        integration = self.context['integration']
        current_stage = self.context.get('current_stage')

        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            link = instance.hubspot_link
            link.current_stage = current_stage
            link.last_synced_at = timezone.now()
            link._skip_external_push = True
            link.save()

        return instance
```

This replaces the `_prepare_order_from_deal()` helper and the `Orders.objects.update_or_create()` call in the current `sync.py`. The serializer handles validation, the `create()`/`update()` methods handle writes with `transaction.atomic()` (fixing the existing data integrity gap where an order could be created without its link).

#### How the sync wires SDK + serializer (HubSpot)

```python
# integrations/adapters/hubspot/sync.py
from hubspot import HubSpot
from .serializers import HubSpotDealInboundSerializer
from integrations.models.links.hubspot import HubSpotOrderLink

def sync_all_deals(integration):
    """Sync all HubSpot deals for an integration. Uses official SDK for extraction."""
    client = HubSpot(access_token=integration.api_key)
    results = {'created': 0, 'updated': 0, 'errors': []}

    # SDK handles pagination and rate limits
    deals = client.crm.deals.get_all()

    for deal in deals:
        # Check debug mode
        if integration.config.get('debug_mode') and deal.properties.get('dealname') != integration.config.get('debug_deal_name', 'Ghost Pepper'):
            continue

        # Resolve stage, company, contacts (existing batch logic via SDK)
        context = {
            'integration': integration,
            'deal_id': deal.id,
            'current_stage': resolve_stage(deal, integration),
        }

        # Find existing order by link
        existing_link = HubSpotOrderLink.objects.filter(
            integration=integration, deal_id=deal.id
        ).select_related('order').first()

        serializer = HubSpotDealInboundSerializer(
            instance=existing_link.order if existing_link else None,
            data=deal.properties,
            context=context,
        )

        if serializer.is_valid():
            serializer.save()
            results['created' if not existing_link else 'updated'] += 1
        else:
            results['errors'].append({'deal_id': deal.id, 'errors': serializer.errors})

    return results
```

### Base Adapter Class

The three universal operations. Capabilities are discovered by introspection, not declared.

```python
# integrations/adapters/base.py

ADAPTER_API_VERSION = 1

class BaseAdapter:
    """
    Base class for all integration adapters.

    Follows the standard Django ecosystem pattern (django-allauth, Saleor, Celery).
    Required methods raise NotImplementedError. Optional methods return safe defaults.
    Capabilities are discovered by introspection -- if you override a method, you support it.

    To add a new integration:
    1. Create manifest.py with MANIFEST dict (metadata, auth type, link models)
    2. Create fetchers.py with BaseFetcher subclasses (one per entity type)
    3. Create serializers.py with inbound serializers (one per entity type) + config serializer
    4. Subclass BaseAdapter, wire fetchers to serializers
    5. Register in settings.INTEGRATION_ADAPTERS
    """

    manifest = None  # Subclass sets this

    # --- Required ---

    def test_connection(self, integration):
        """Test credentials and config. Returns (success: bool, message: str)."""
        raise NotImplementedError

    def dispatch_sync_task(self, integration):
        """Queue the provider-specific Celery sync task."""
        raise NotImplementedError

    # --- Optional: Inbound sync ---

    def sync_orders(self, integration):
        """Pull orders/deals, create/update local Orders + link records."""
        return {'status': 'not_supported'}

    def sync_companies(self, integration):
        """Pull companies/accounts, create/update local Companies + link records."""
        return {'status': 'not_supported'}

    def sync_contacts(self, integration):
        """Pull contacts/users. Some providers handle this as part of sync_orders."""
        return {'status': 'not_supported'}

    # --- Optional: Outbound push ---

    def push_order_status(self, integration, link, status):
        """Push an order status/stage change to the external system."""
        return False

    # --- Optional: Webhooks ---

    def handle_webhook(self, request, integration):
        """Process an incoming webhook."""
        return {'status': 'not_supported'}

    # --- Optional: Pipeline stages ---

    @property
    def has_pipeline_stages(self):
        """Override to return True if this adapter syncs pipeline/stage data."""
        return False

    # --- Optional: Single-record fetch ---

    def pull_order(self, integration, external_id):
        """Fetch a single order/deal."""
        return None

    def pull_company(self, integration, external_id):
        """Fetch a single company/account."""
        return None
```

### HubSpot Adapter (reference implementation)

```python
# integrations/adapters/hubspot/adapter.py
from integrations.adapters.base import BaseAdapter
from .manifest import MANIFEST

class HubSpotAdapter(BaseAdapter):
    manifest = MANIFEST

    def test_connection(self, integration):
        from hubspot import HubSpot
        try:
            client = HubSpot(access_token=integration.api_key)
            client.crm.deals.basic_api.get_page(limit=1)
            return True, 'Connected to HubSpot API'
        except Exception as e:
            return False, f'Connection failed: {e}'

    def dispatch_sync_task(self, integration):
        from integrations.tasks import sync_hubspot_deals_task
        sync_hubspot_deals_task.delay(integration_id=str(integration.id))

    def sync_orders(self, integration):
        from .sync import sync_all_deals
        return sync_all_deals(integration)

    # NOTE: sync_companies is NOT overridden. Companies sync as part of sync_orders
    # (contacts carry company associations). Capability discovery will correctly
    # NOT report 'company_sync' since the base class method is unchanged.

    def push_order_status(self, integration, link, status):
        from hubspot import HubSpot
        client = HubSpot(access_token=integration.api_key)
        client.crm.deals.basic_api.update(
            deal_id=link.deal_id,
            simple_public_object_input={'properties': {'dealstage': status.api_id}}
        )
        return True

    def handle_webhook(self, request, integration):
        from integrations.webhooks.handlers.hubspot import handle_hubspot_webhook
        return handle_hubspot_webhook(request, integration)

    @property
    def has_pipeline_stages(self):
        return True
```

### Registry

Settings-based registration with `import_string()`. Settings ARE the registry.

```python
# settings.py
INTEGRATION_ADAPTERS = {
    ('hubspot', 'cloud'): 'integrations.adapters.hubspot.adapter.HubSpotAdapter',
}

# integrations/services/registry.py
from django.conf import settings
from django.utils.module_loading import import_string

_adapter_cache = {}

def get_adapter(provider: str) -> BaseAdapter:
    """Get the adapter instance for a provider, considering deployment mode."""
    deployment_mode = getattr(settings, f'{provider.upper()}_MODE', 'cloud')
    cache_key = (provider, deployment_mode)

    if cache_key not in _adapter_cache:
        adapter_path = settings.INTEGRATION_ADAPTERS.get(cache_key)
        if not adapter_path:
            raise ValueError(f"No adapter registered for ({provider}, {deployment_mode})")
        adapter_class = import_string(adapter_path)
        _adapter_cache[cache_key] = adapter_class()

    return _adapter_cache[cache_key]

def get_all_adapters() -> list:
    """Get all registered adapter instances."""
    seen = set()
    adapters = []
    for (provider, mode), path in settings.INTEGRATION_ADAPTERS.items():
        if provider not in seen:
            adapters.append(get_adapter(provider))
            seen.add(provider)
    return adapters

def clear_cache():
    """Clear cached adapter instances. For testing."""
    _adapter_cache.clear()
```

### How the frontend uses capabilities

```python
class IntegrationConfigSerializer(serializers.ModelSerializer):
    capabilities = serializers.SerializerMethodField()

    def get_capabilities(self, obj):
        from integrations.services.registry import get_adapter, discover_capabilities
        adapter = get_adapter(obj.provider)
        return sorted(discover_capabilities(adapter))
    # Returns: ["company_sync", "order_sync", "pipeline_stages", "push_order_status", "webhooks"]
```

Frontend checks: `capabilities.includes('pipeline_stages')` before showing gate UI.

### Recommended packages

New dependencies to add for the integration framework:

| Package | Purpose | Why |
|---|---|---|
| **`hubspot-api-client`** (v12, official) | HubSpot API client | Replaces hand-rolled `requests.get()` in `hubspot/api.py`. Handles pagination, rate limits, auth natively. The SDK IS the fetcher for HubSpot — no need to write `HubSpotDealFetcher` from scratch. |
| **`authlib`** | OAuth2 token management (outbound) | For integrations that use OAuth2 (QuickBooks, Salesforce). Handles token refresh automatically via `OAuth2Session` with a callback that saves refreshed tokens to your `IntegrationConfig`. Build a `TenantOAuthToken` model or store tokens in the encrypted config. |
| **`pyrate-limiter`** | Outbound API rate limiting | Per-tenant, per-API rate limit tracking with Redis backend (already have Redis). Prevents hitting rate limits proactively, unlike `urllib3.Retry` which only retries after a 429. |
| **`django-pydantic-field`** | Typed JSONField validation | Use Pydantic models as the type for `IntegrationConfig.config`. Gives validated, typed config instead of raw dict. Auto-generates OpenAPI schema through DRF for the dynamic settings form. |
| **`python-quickbooks`** (v0.9.12) | QuickBooks API client | Community-maintained, built for Django originally. For the second adapter. |
| **`simple-salesforce`** | Salesforce API client | Low-level REST/APEX client, well-maintained. For future Salesforce adapter. |

Already in requirements.txt and leveraged:

| Package | How it's used |
|---|---|
| **`django-encrypted-model-fields`** | Encrypted API keys and secrets on `IntegrationConfig` |
| **`django-auditlog`** | Register `IntegrationConfig` — free credential/config change logging |
| **`django-celery-beat`** | Per-integration dynamic sync schedules via `PeriodicTask` |
| **`django-celery-results`** | Task execution history (supplements `IntegrationSyncLog`) |
| **`django-filter`** | FilterSets for sync logs, integration listing |
| **`django-redis`** | Cache integration config lookups, rate limit state (via pyrate-limiter) |
| **`drf-spectacular`** | OpenAPI schema from config serializers — frontend renders settings forms |
| **`openpyxl`** | Sync log / integration status Excel export via existing `ExcelExportMixin` |

### How the pieces map to ETL

| Concern | Tool | Notes |
|---|---|---|
| **Extract** | Provider SDK (`hubspot-api-client`, `python-quickbooks`) or `BaseFetcher` | Use official SDK when available. `BaseFetcher` is the fallback for APIs without SDKs. |
| **Rate limiting** | `pyrate-limiter` + Redis | Proactive, per-tenant. Wraps API client calls. |
| **OAuth2 token refresh** | `authlib` `OAuth2Session` | Auto-refresh with callback to persist new tokens. |
| **Transform** | DRF serializer `to_internal_value()` | Maps external fields to local model fields. |
| **Validate** | DRF serializer field validation | Type checking, required/optional, FK existence. |
| **Load** | DRF serializer `create()` / `update()` | Writes to local model + link model inside `transaction.atomic()`. |
| **Config schema** | Per-provider DRF serializer + `django-pydantic-field` + drf-spectacular | Typed, validated, auto-documented. |
| **Sync scheduling** | `django-celery-beat` `PeriodicTask` | Per-integration dynamic schedules. |
| **Execution history** | `django-celery-results` + `IntegrationSyncLog` | Task results + structured sync record counts. |
| **Audit trail** | `django-auditlog` | Config change tracking. |
| **Data integrity** | `transaction.atomic()` | Order + link atomically. Fixes existing gap. |
| **Batch performance** | `bulk_create` / `bulk_update` | For large syncs. Optimize after initial implementation. |
| **Caching** | `django-redis` | Integration config lookups. |

### What this means for `BaseFetcher`

`BaseFetcher` becomes less central than originally described. For providers with official SDKs (HubSpot, QuickBooks, Salesforce), the SDK replaces the fetcher — it already handles pagination, auth, and rate limits. `BaseFetcher` is the escape hatch for providers without SDKs, where you're making raw HTTP calls against a REST API.

The adapter uses whatever client makes sense for that provider:

```python
# HubSpot: uses official SDK
class HubSpotAdapter(BaseAdapter):
    def sync_orders(self, integration):
        from hubspot import HubSpot
        client = HubSpot(access_token=integration.api_key)
        deals = client.crm.deals.get_all()  # SDK handles pagination + rate limits
        # ... pass to serializer

# Custom API without SDK: uses BaseFetcher
class CustomCRMAdapter(BaseAdapter):
    def sync_orders(self, integration):
        fetcher = CustomCRMFetcher()
        for record in fetcher.fetch_all(integration):
            # ... pass to serializer
```

### Scaling trajectory

| Stage | What | When |
|---|---|---|
| **Now** | Base class + manifest + fetcher + serializer + HubSpot adapter | Phase 1-2 |
| **Second adapter** | QuickBooks — validates the pattern works for a different type | After HubSpot stable |
| **Before third adapter** | Conformance test suite + scaffolding CLI | Must come before adapter #3 |
| **Then** | Salesforce, Xero, Datanomix, ShipStation, etc. | As market demands |

---

## Operational Concerns

### Concurrent sync protection

If the hourly Celery Beat fires while a previous sync is still running (slow API, large tenant), two syncs could create duplicate links. Before starting a sync, check `IntegrationConfig.sync_status`:

```python
def sync_all_deals(integration):
    if integration.sync_status == IntegrationConfig.SyncStatus.SYNCING:
        return {'status': 'skipped', 'reason': 'sync_already_running'}

    integration.sync_status = IntegrationConfig.SyncStatus.SYNCING
    integration.save(update_fields=['sync_status'])

    try:
        # ... sync logic ...
        integration.sync_status = IntegrationConfig.SyncStatus.IDLE
    except Exception:
        integration.sync_status = IntegrationConfig.SyncStatus.ERROR
        raise
    finally:
        integration.save(update_fields=['sync_status', 'last_synced_at', 'last_sync_error'])
```

For extra safety, use a Redis lock with a TTL as a secondary guard against race conditions.

### Webhook out-of-order delivery

HubSpot can deliver webhooks out of order. If a deal stage changes A→B→C and webhooks arrive as C, A, B, applying all three leaves the final state as B (wrong). The webhook handler should compare the event timestamp against `HubSpotOrderLink.last_synced_at` and skip events older than the current state:

```python
# In handle_hubspot_webhook:
if event_timestamp < link.last_synced_at:
    return  # stale event, skip
```

### Credential rotation

When an API key is rotated on a live integration:
- The admin updates the key in the integration settings UI
- `is_enabled` stays true (no need to disable/re-enable for a key rotation)
- If a sync task is in flight when the key changes, it will fail on the next API call and retry with the new key (Celery retry loads fresh credentials from the database)
- `django-auditlog` records the change for audit trail

### Auto-disable on persistent failure

If an integration fails N consecutive syncs (e.g., 401 Unauthorized because someone revoked the key), it should auto-disable rather than retrying forever:

```python
MAX_CONSECUTIVE_FAILURES = 5

# After sync failure:
consecutive_failures = IntegrationSyncLog.objects.filter(
    integration=integration, status='FAILED'
).order_by('-started_at')[:MAX_CONSECUTIVE_FAILURES].count()

if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
    integration.is_enabled = False
    integration.sync_status = IntegrationConfig.SyncStatus.ERROR
    integration.last_sync_error = f'Auto-disabled after {MAX_CONSECUTIVE_FAILURES} consecutive failures'
    integration.save()
    # TODO: notify admin
```

### ProcessedWebhook cleanup

The `ProcessedWebhook` table grows indefinitely. Add a periodic Celery task to prune old records:

```python
@shared_task
def cleanup_processed_webhooks():
    """Delete processed webhook records older than 30 days."""
    cutoff = timezone.now() - timedelta(days=30)
    ProcessedWebhook.objects.filter(processed_at__lt=cutoff).delete()
```

Add to Celery Beat schedule (daily).

### `get_gate_info_for_stage` N+1 prevention

The `get_gate_info_for_stage()` utility queries `HubSpotPipelineStage.objects.filter(...)` to get all stages in the pipeline. On a list view with 50 orders, that's 50 additional queries. Solutions:

- **Prefetch**: load all stages for the tenant's integration once, pass as context to the serializer
- **Cache**: cache the stage list per integration (invalidate on sync)
- **Denormalize**: store `total_gates` and `current_position` directly on `HubSpotOrderLink` and update during sync

The simplest approach for Phase 3 is prefetching in the viewset's `get_queryset()`.

### Health check endpoint

Expose `GET /api/integrations/{id}/health/` returning:

```json
{
    "status": "healthy",
    "last_synced_at": "2026-03-17T10:00:00Z",
    "sync_status": "IDLE",
    "consecutive_failures": 0,
    "records_synced_last": {"created": 5, "updated": 12},
    "next_sync_at": "2026-03-17T11:00:00Z"
}
```

Trivial to build from `IntegrationConfig` + `IntegrationSyncLog`. Gives the admin UI something meaningful to display.

---

## On-Premise / Air-Gapped Deployments

### Key Differences

| Concern | Cloud (SaaS) | On-Prem / Air-Gapped |
|---------|--------------|----------------------|
| Connection target | External API (internet) | Local network resource |
| Credentials | OAuth tokens, API keys | Service accounts, connection strings |
| Configuration | Per-tenant in database | Per-deployment in environment/settings |
| Webhooks | Available | Not available -- use polling |

### Architecture

**Keep the same adapter interface**, but allow:
1. **Connection details from environment** -- don't assume database config for all cases
2. **Polling instead of webhooks** -- scheduled Celery beat tasks
3. **Adapter selection by deployment** -- not just integration type
4. **n8n available for dedicated deployments** -- ships alongside for custom automation beyond native integrations

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

For most sync operations, Celery with retry settings is sufficient. The existing `RetryableHubSpotTask` base class (auto-retry on `ConnectionError`/`TimeoutError`/`OSError`, exponential backoff up to 15min, jitter) migrates into the `integrations/` app.

### When to Consider Outbox Pattern

Only for compliance-critical financial transactions or when "exactly once" delivery is legally required. Not needed for CRM sync.

---

## Data Migration Strategy

### Approach

Use `makemigrations` to generate schema migrations from the model definitions — don't hand-write migrations. Review the generated migrations and adjust as needed (e.g., adding `RunPython` data migration operations to the auto-generated file, or creating a separate data-only migration). Let Django do the schema work.

### Migration 1: Schema

Run `python manage.py makemigrations integrations` after defining the new models. This should auto-generate the table creation for: `IntegrationConfig`, `IntegrationSyncLog`, `ProcessedWebhook`, `HubSpotPipelineStage`, `HubSpotOrderLink`, `HubSpotCompanyLink`. Review the output and adjust if needed.

### Migration 2: Data (RunPython, preserves Ambac data)

Create a separate data migration (`python manage.py makemigrations integrations --empty --name migrate_hubspot_data`) and add the following `RunPython` operation:

```python
def forward(apps, schema_editor):
    Tenant = apps.get_model('Tracker', 'Tenant')
    IntegrationConfig = apps.get_model('integrations', 'IntegrationConfig')
    HubSpotOrderLink = apps.get_model('integrations', 'HubSpotOrderLink')
    HubSpotCompanyLink = apps.get_model('integrations', 'HubSpotCompanyLink')
    HubSpotPipelineStage = apps.get_model('integrations', 'HubSpotPipelineStage')
    Orders = apps.get_model('Tracker', 'Orders')
    Companies = apps.get_model('Tracker', 'Companies')
    ExternalAPIOrderIdentifier = apps.get_model('Tracker', 'ExternalAPIOrderIdentifier')

    # Find tenants with HubSpot data (check both Orders and Companies)
    tenant_ids_from_orders = set(
        Orders.objects.filter(hubspot_deal_id__isnull=False)
        .exclude(hubspot_deal_id='').values_list('tenant_id', flat=True).distinct()
    )
    tenant_ids_from_companies = set(
        Companies.objects.filter(hubspot_api_id__isnull=False)
        .exclude(hubspot_api_id='').values_list('tenant_id', flat=True).distinct()
    )
    tenants_with_hubspot = Tenant.objects.filter(
        id__in=tenant_ids_from_orders | tenant_ids_from_companies
    )

    for tenant in tenants_with_hubspot:
        # Create IntegrationConfig with is_enabled=False -- enable after api_key is set
        config = IntegrationConfig.objects.create(
            tenant=tenant,
            provider='hubspot',
            display_name='HubSpot CRM',
            is_enabled=False,  # disabled until api_key is manually entered
            config={
                'migrated_from_settings': True,
                'pipeline_tracking_enabled': True,
                'active_stage_prefix': 'Gate',
            },
        )

        # Migrate pipeline stages
        stage_id_map = {}  # old ExternalAPIOrderIdentifier.id -> new HubSpotPipelineStage.id
        for old_stage in ExternalAPIOrderIdentifier.objects.filter(tenant=tenant):
            new_stage = HubSpotPipelineStage.objects.create(
                integration=config,
                stage_name=old_stage.stage_name,
                api_id=old_stage.API_id,
                pipeline_id=old_stage.pipeline_id,
                display_order=old_stage.display_order,
                include_in_progress=old_stage.include_in_progress,
                last_synced_at=old_stage.last_synced_at,
            )
            stage_id_map[old_stage.id] = new_stage.id

        # Migrate Orders -> HubSpotOrderLink
        for order in Orders.objects.filter(
            tenant=tenant, hubspot_deal_id__isnull=False
        ).exclude(hubspot_deal_id=''):
            new_stage_id = stage_id_map.get(order.current_hubspot_gate_id)
            HubSpotOrderLink.objects.create(
                order=order,
                integration=config,
                deal_id=order.hubspot_deal_id,
                current_stage_id=new_stage_id,
                last_synced_stage_name=order.last_synced_hubspot_stage,
                last_synced_at=order.hubspot_last_synced_at,
            )

        # Migrate Companies -> HubSpotCompanyLink
        for company in Companies.objects.filter(
            tenant=tenant, hubspot_api_id__isnull=False
        ).exclude(hubspot_api_id=''):
            HubSpotCompanyLink.objects.create(
                company=company,
                integration=config,
                hubspot_company_id=company.hubspot_api_id,
            )

    # Migrate HubSpotSyncLog -> IntegrationSyncLog (outside tenant loop -- logs aren't tenant-scoped)
    # HubSpotSyncLog has no tenant FK, so assign all logs to the first (likely only) integration.
    # If multiple tenants exist, logs are best-effort assigned to the first config found.
    HubSpotSyncLog = apps.get_model('Tracker', 'HubSpotSyncLog')
    IntegrationSyncLog = apps.get_model('integrations', 'IntegrationSyncLog')
    first_config = IntegrationConfig.objects.first()
    if first_config:
        for log in HubSpotSyncLog.objects.all():
            IntegrationSyncLog.objects.create(
                integration=first_config,
                sync_type=log.sync_type,
                status=log.status,
                started_at=log.started_at,
                completed_at=log.completed_at,
                records_processed=log.deals_processed,
                records_created=log.deals_created,
                records_updated=log.deals_updated,
                error_message=log.error_message,
            )
```

**Post-migration manual steps:**
1. Set `IntegrationConfig.api_key` for Ambac via Django shell (key was previously in environment variables)
2. Set `IntegrationConfig.is_enabled=True` after confirming the api_key works

### Migration 3: Cleanup (separate PR, after bake period)

- Remove `hubspot_deal_id`, `current_hubspot_gate`, `last_synced_hubspot_stage`, `hubspot_last_synced_at` from Orders
- Remove `orders_tenant_hubspot_deal_uniq` constraint from Orders
- Remove `hubspot_api_id` from Companies
- Remove `ExternalAPIOrderIdentifier` model from Tracker
- Remove `HubSpotSyncLog` from Tracker (replaced by `IntegrationSyncLog` in the integrations app)
- Remove `Tracker/hubspot/` package
- Remove `Tracker/hubspot_view.py`
- Remove `Tracker/integrations/` module (base_service, registry, hubspot_service)
- Remove `HUBSPOT_*` settings from settings.py
- Remove HubSpot-specific Celery tasks from `Tracker/tasks.py`

---

## Serializer Changes

### Query optimization

Order list views that include `hubspot_link` and `gate_info` must use `select_related` to avoid N+1 queries:

```python
# In OrderViewSet.get_queryset():
queryset = queryset.select_related('hubspot_link__current_stage', 'hubspot_link__integration')
```

This replaces the zero-cost inline field access with a JOIN, so it's important to get right.

### OrderSerializer

```python
class HubSpotOrderLinkSerializer(serializers.ModelSerializer):
    current_stage_name = serializers.CharField(source='current_stage.stage_name', read_only=True, allow_null=True)

    class Meta:
        model = HubSpotOrderLink
        fields = ['deal_id', 'current_stage', 'current_stage_name', 'last_synced_at']
        read_only_fields = ['deal_id', 'current_stage_name', 'last_synced_at']

class OrderSerializer(SecureModelMixin, serializers.ModelSerializer):
    hubspot_link = HubSpotOrderLinkSerializer(read_only=True, allow_null=True)
    gate_info = serializers.SerializerMethodField()

    def get_gate_info(self, obj):
        link = getattr(obj, 'hubspot_link', None)
        if link and link.current_stage:
            return get_gate_info_for_stage(link.current_stage)
        return None
```

The `gate_info` output shape stays identical -- `TrackerCard.tsx` and `TrackerPage.tsx` need zero changes.

### CompanySerializer

```python
class CompanySerializer(SecureModelMixin, serializers.ModelSerializer):
    hubspot_links = HubSpotCompanyLinkSerializer(many=True, read_only=True)

    class Meta:
        model = Companies
        fields = ('id', 'name', 'description', 'hubspot_links', ...)
        # hubspot_api_id removed
```

---

## Filter Changes

```python
# Before:
def filter_active_pipeline(self, queryset, name, value):
    if value:
        return queryset.filter(
            Q(hubspot_deal_id__isnull=True) | Q(hubspot_deal_id='') |
            Q(current_hubspot_gate__stage_name__startswith='Gate')
        )

# After:
def filter_active_pipeline(self, queryset, name, value):
    if value:
        # Orders with no external link are always included (local orders)
        local_orders = Q(hubspot_link__isnull=True)

        # For linked orders, look up the active_stage_prefix from the
        # integration config. Can't do a JSONField lookup on the RHS of
        # startswith in the ORM, so resolve the prefix in Python first.
        # This is a per-request lookup, not per-row -- the user belongs
        # to one tenant with one HubSpot config.
        prefix = self._get_active_stage_prefix(self.request)
        if prefix:
            active_orders = Q(hubspot_link__current_stage__stage_name__startswith=prefix)
        else:
            # No prefix configured -- all linked orders are considered active
            active_orders = Q(hubspot_link__isnull=False)

        return queryset.filter(local_orders | active_orders)
    return queryset

def _get_active_stage_prefix(self, request):
    """Look up the active_stage_prefix from the tenant's HubSpot integration config."""
    from integrations.models.config import IntegrationConfig
    try:
        config = IntegrationConfig.objects.get(
            tenant=request.user.tenant,
            provider='hubspot',
            is_enabled=True,
        )
        return config.config.get('active_stage_prefix', '')
    except IntegrationConfig.DoesNotExist:
        return ''
```

The `active_stage_prefix` in `IntegrationConfig.config` replaces the hardcoded `"Gate"` check. Ambac's config has `"Gate"`. A tenant with no prefix configured includes all linked orders as active.

---

## Frontend Changes (High Level)

| File | Change |
|---|---|
| `OrderFormPage.tsx` | Gate dropdown conditional on tenant having HubSpot integration. Field targets `hubspot_link.current_stage`. |
| `TrackerCard.tsx` | **No change** -- `gate_info` API shape is identical. |
| `TrackerPage.tsx` | **No change** -- still filters by `gate_info` presence. |
| `fieldsConfigMap.tsx` | Replace hardcoded "HubSpot" labels. Show integration section only when link exists. |
| `CompaniesEditorPage.tsx` | Remove hardcoded "HubSpot API ID" column. Show external links if present. |
| `EditCompanyFormPage.tsx` | Remove `hubspot_api_id` field. External links managed by sync, not manual entry. |
| `useListHubspotGates.ts` | Rename to `useListPipelineStages`. Fetch from new HubSpotPipelineStage endpoint. |
| New: Integration settings page | Admin page for adding/configuring integrations. |

---

## Adding a New Integration

1. Add link tables in `integrations/models/links/` (e.g., `salesforce.py`)
2. Create adapter in `integrations/adapters/` subclassing `BaseAdapter`
3. Register in `integrations/services/registry.py`
4. Add webhook handler in `integrations/webhooks/handlers/`
5. Write tests
6. Add frontend conditional rendering for the new provider

---

## Implementation Phases

### Phase 1: Foundation
Create `integrations/` Django app with models (`IntegrationConfig`, `IntegrationSyncLog`, `ProcessedWebhook`, HubSpot link tables), `BaseAdapter`, `BaseFetcher`, registry, and `IntegrationConfig` CRUD viewset/serializer. Schema + data migrations. Register `IntegrationConfig` with django-auditlog.

### Phase 2: HubSpot Adapter (ETL Composition)
Build `HubSpotAdapter` using the new pattern: `HubSpotDealFetcher` + `HubSpotDealInboundSerializer` + `sync_all_deals()` orchestration. Per-provider config serializer (`HubSpotConfigSerializer`). Move push logic from `Orders.save()` to `post_save` signal on `HubSpotOrderLink`. Move webhook to integrations app. `RetryableIntegrationTask` replaces `RetryableHubSpotTask`. Fix `_skip_hubspot_push` bug. All sync writes use `transaction.atomic()`.

### Phase 3: Serializer, Filter, and API Updates
`OrderSerializer` uses `hubspot_link` with `select_related`. `CompanySerializer` uses `hubspot_links` with `prefetch_related`. `filter_active_pipeline` reads prefix from integration config. `gate_info` reads from `get_gate_info_for_stage()` utility. `set_pipeline_stage` action on `OrderViewSet`. Pipeline stage viewset points to `HubSpotPipelineStage`. Capability discovery exposed via `IntegrationConfigSerializer`.

### Phase 4: Frontend
Conditional UI based on capabilities from API. Integration settings page (form rendered from OpenAPI schema via spectacular). Gate dropdown uses `set_pipeline_stage` action. Rename `useListHubspotGates` to `useListPipelineStages`.

### Phase 5: Cleanup (after bake period)
Drop deprecated inline fields from Orders and Companies. Remove `ExternalAPIOrderIdentifier`. Remove `HubSpotSyncLog`. Remove `Tracker/integrations/` and `Tracker/hubspot/`. Remove `HUBSPOT_*` settings. Remove HubSpot tasks from `Tracker/tasks.py`.

---

## Verification

1. Run migrations on dev database with existing Ambac HubSpot data
2. Verify `IntegrationConfig` record created for Ambac with `provider='hubspot'`
3. Verify `HubSpotOrderLink` records match existing `hubspot_deal_id` data (count identical)
4. Verify `HubSpotCompanyLink` records match existing `hubspot_api_id` data
5. Verify `HubSpotPipelineStage` records match existing `ExternalAPIOrderIdentifier` data
6. Set `api_key` on IntegrationConfig, trigger sync, confirm orders sync correctly
7. Send test webhook, confirm it resolves integration and updates `HubSpotOrderLink.current_stage`
8. Update an order's stage in the UI, confirm push to HubSpot fires via signal
9. Verify `_skip_external_push` prevents loop during sync
10. Verify `gate_info` output shape is identical (TrackerCard renders correctly)
11. Verify frontend shows gate info for Ambac, hides it for tenants without HubSpot
12. Create a test tenant with no integrations, verify clean order form
13. Verify `filter_active_pipeline` works correctly with new link model
14. Run existing test suite

---

## Resolved Questions

| Question | Resolution |
|----------|------------|
| ~~django-outbox-pattern?~~ | No -- Celery with retries is sufficient |
| ~~OAuth flow UI?~~ | Deferred -- manual credential entry first |
| ~~Sync conflicts?~~ | Source-of-truth per field |
| ~~Field mapping per tenant?~~ | Yes -- base mappings + per-tenant overrides in config JSONField |
| ~~Cloud vs on-prem adapters?~~ | Single registry, deployment config selects adapter |
| ~~Polling for air-gapped?~~ | Celery beat schedule |
| ~~Generic vs per-provider link tables?~~ | Per-provider (HubSpotOrderLink, not ExternalOrderLink) |
| ~~Keep IntegrationService ABC?~~ | Replace with BaseAdapter base class in new integrations app |
| ~~n8n for multi-tenant SaaS?~~ | No -- native integrations in application code. n8n for dedicated deployments only. |