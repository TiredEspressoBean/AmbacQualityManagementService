# Notification System Design

## Status

| Phase | Scope | Status |
|---|---|---|
| 1 | Foundation — registry, `emit()`, outbox, ConsoleChannel, `ncr.opened` vertical slice | **Done** |
| 2 | Email + InAppChannel, TenantNotificationBranding, TenantNotificationDefault, UserNotificationPreference, NotificationTemplate, 4-layer resolver, tenant seeder | **Done** (34 tests green) |
| 3 | NotificationRule with three scopes (tenant/customer/personal), CEL conditions, dispatcher rewrite, API endpoints | Frontend demos done; backend not started |
| Escalation | EscalationPolicy + EscalationStep + EscalationInstance + beat task + `is_acknowledged` registry | Frontend demo done; backend not started |
| 4 | WatchedRecord, dry-run preview, activity log, unsubscribe links | Not started |
| 5 | Migrate legacy email sends, ship system templates, retire `services/core/notification.py` | Not started |
| In-app feed | Feed reader over `NotificationOutbox` — `/api/notifications/feed/`, bell, `/notifications` page | **Done** (2026-07-13, shipped out of phase order) |

**In-app feed (shipped 2026-07-13).** The reader side of `InAppChannel` landed ahead of its planned phase: `NotificationFeedViewSet` (`Tracker/viewsets/notifications.py`) exposes `/api/notifications/feed/` over the request user's own `NotificationOutbox` rows (self-scoped), with an `?unread=true` filter, an `unread-count` action, idempotent `mark-read`, and `mark-all-read`. Frontend: notification bell in the top chrome (`ambac-tracker-ui/src/components/notifications/NotificationBell.tsx`) and the `/notifications` feed page.

Frontend demos (running on a module-level `demoRuleStore`) live in `ambac-tracker-ui/src/pages/{settings,profile}/Notification*` and validate the UX before backend land. Replace the store with TanStack Query against `/api/notifications/*` once Phase 3 backend ships.

## Goals

- Single emit path for all notifications (`emit(event_code, tenant, payload)`).
- Curated, dev-owned event registry — events ship with code, not discovered from signals.
- Tenant-configurable routing rules with type-checked conditions (CEL).
- Three rule scopes — tenant, customer, personal — sharing one model and one evaluator.
- Per-user channel preferences (mute/unmute per event × channel).
- White-label tenant branding overlaid on every outbound email.
- System-authored templates with tenant branding overlay; no raw template editing by tenants.
- Outbox-backed delivery with retries, idempotency, and audit.
- Time-based escalation chains (notify additional people if not acknowledged in time).
- Compliance-supporting audit (ISO 9001 4.4, IATF 16949 8.7.1.4 proof of customer notification).

## Non-Goals

- Auto-generation of events from model signals.
- Tenant-authored raw templates.
- Generic Turing-complete rule engine. Conditions are CEL evaluated against typed payload schemas.
- Quiet hours, digest aggregation, real-time WebSocket push, multi-language templates — deferred to post-v1.
- Recipient-acknowledged audit beyond what's already tracked on source records.
- Replacement of `django-auditlog`. Model changes stay in auditlog; notification dispatch is logged in the outbox.

## Architecture

```
Event Registry  (code, dev-owned)
  ├── register_event(EventType(code, label, payload_schema, default_channels, ...))
  └── ~25 events at v1, growing as features ship
              │ emit(code, tenant, payload)
              ▼
Dispatcher  (Django signal receiver, transactional)
  ├── Validate payload against schema
  ├── Resolve matching NotificationRules (tenant + customer + personal scope)
  ├── Evaluate CEL conditions per rule
  ├── Apply per-user channel preferences (4-layer cascade)
  ├── Render template with tenant branding overlay
  ├── Write NotificationOutbox rows (idempotency_key per recipient × channel)
  └── Create EscalationInstance rows if the rule has an escalation policy
              │
              ▼
Outbox + Celery Workers
  ├── dispatch_outbox_row task → channel.send()
  ├── retry with exponential backoff on transport failure
  └── beat task `tick_escalations` advances pending escalation instances
              │
              ▼
Channel Adapters
  ├── EmailChannel (django.core.mail; SMTP at deploy level)
  ├── InAppChannel (writes outbox rows; frontend reads via inbox endpoint)
  └── Future: SMS / Teams / Slack / Push (settings-driven registration)
```

## Event Registry

Events are Python objects registered at app startup. Adding a new event is ~5 lines: register the event, define the payload dataclass, call `emit()` from the natural service-layer point. See `Tracker/services/{core,mes,qms,life_tracking,reman}/events.py` for the actual registrations.

### EventType shape

```python
@dataclass(frozen=True, eq=False)
class EventType:
    code: str                              # 'ncr.opened'
    label: str                             # 'Nonconformance Opened'
    domain: str                            # 'Quality'
    payload_schema: Type                   # frozen dataclass with .sample() classmethod
    default_channels: list[str]            # ['in_app', 'email']
    default_recipient_groups: list[str]    # Phase 2 fallback; Phase 3 uses rules
    default_on: bool                       # ships enabled in starter pack
    transactional: bool                    # exempt from unsubscribe (contractual)
    description: str
    external_routable: bool                # eligible for customer-scoped routing
    source_model: str                      # Phase 3: 'Tracker.QualityReport'
    is_acknowledged: Callable[[Any], bool] # Escalation: stops chain when True
```

Payload schemas are frozen dataclasses with a `sample()` classmethod. The dataclass shape doubles as the CEL type schema (Phase 3) and as the test factory baseline.

### v1 launch set

~25 events across Quality (NCR, CAPA, RCA, FPI, inspection, disposition), Orders & WorkOrders (received, ship-date-changed, late-risk, shipped, released, step-complete, held), Documents & Change Control (approval-required, released, approval-decided), Training, Sampling, Equipment (calibration due/overdue), and System (privileged-role-changed, account-locked).

Full catalog in `ambac-tracker-ui/src/lib/notifications/eventCatalog.ts` (frontend mirror) and the various `events.py` modules (backend source of truth).

**Registered 2026-07:** `fpi.requested` / `fpi.decided` (the first-piece andon loop) are live in `Tracker/services/qms/events.py`. **Named gap:** the starter rules in `Tracker/services/core/notifications/system_rules.py` do not yet cover `fpi.*` — new tenants get no default routing for these events until a starter rule is added.

## Data Model

All notification models inherit `SecureModel` for tenant auto-scoping.

### NotificationRule (Phase 3)

The existing `NotificationRule` model extended for three-scope routing.

| Field | Type | Notes |
|---|---|---|
| `tenant` | FK Tenant | via SecureModel |
| `event_code` | CharField(64), indexed | must exist in EVENT_REGISTRY |
| `scope_kind` | CharField | `'tenant'`, `'customer'`, or `'personal'` |
| `scope_id` | BigInteger, nullable | Customer FK id for customer scope; null otherwise |
| `owner_user` | FK User, nullable | required for personal scope; null otherwise |
| `conditions` | JSONField | parsed CEL AST (cached) |
| `conditions_source` | TextField | original CEL expression for editing |
| `recipient_groups` | M2M TenantGroup | tenant/customer scope only |
| `recipient_users` | M2M User | tenant/customer scope only |
| `recipient_external` | M2M ExternalContact | customer scope only |
| `channels` | ArrayField(CharField) | e.g. `['email', 'in_app']` |
| `priority` | Integer | resolution order |
| `enabled` | Boolean | |
| `created_by`, `created_at`, `updated_at` | | audit |

Indexes: `(tenant, event_code, enabled)`, `(tenant, scope_kind, scope_id)`, `(owner_user, event_code)` partial `WHERE scope_kind='personal'`.

**Database-level scope invariant** (CHECK constraint `notification_rule_scope_invariant`):

```python
CheckConstraint(check=(
    (Q(scope_kind='tenant')   & Q(scope_id__isnull=True)  & Q(owner_user__isnull=True))
    | (Q(scope_kind='customer') & Q(scope_id__isnull=False) & Q(owner_user__isnull=True))
    | (Q(scope_kind='personal') & Q(scope_id__isnull=True)  & Q(owner_user__isnull=False))
))
```

Three structurally incompatible row variants share one table. Three mitigations make that sustainable, all of which ship in the Phase 3 PR — they're not optional polish:

1. **Custom `NotificationRuleManager`** with `tenant_rules()`, `customer_rules(customer)`, `personal_rules_for(user)`, `editable_by(user)`. Views call the named methods; raw `.filter(scope_kind=...)` in views is a code-review smell.
2. **Per-scope DRF serializers** — `TenantRuleSerializer`, `CustomerRuleSerializer`, `PersonalRuleSerializer` — each exposing only the fields valid for its scope. Endpoints route to the right serializer.
3. **Computed properties on the model** (`is_personal`, `effective_recipients`, `is_editable_by(user)`) centralize scope-conditional logic so the resolver, viewsets, and permission classes don't branch on `scope_kind` directly.

**Resolution semantics.** Customer-scoped and personal rules **add** to tenant-scoped rules. The dispatcher dedupes (recipient, channel) pairs across all matched rules, so a user who is both in a recipient group and has a personal rule for the same event gets one notification, not two.

### NotificationOutbox (Phase 1)

Source of truth for delivery status, retries, and audit. Already shipped.

| Field | Type | Notes |
|---|---|---|
| `tenant` | FK | |
| `event_code` | CharField(64), indexed | |
| `rule` | FK NotificationRule, nullable | SET_NULL on rule delete |
| `user` | FK User, nullable | exactly one of `user` / `external_contact` set |
| `external_contact` | FK ExternalContact, nullable | Phase 3 |
| `channel` | CharField | `'email'`, `'in_app'`, ... |
| `template` | FK NotificationTemplate, nullable | row used at send time |
| `payload` | JSONField | original event payload |
| `correlation_id` | CharField, indexed | `'{event_code}:{source_id}'` for cross-row joins |
| `rendered_subject` / `_body_text` / `_body_html` / `_action_url` | text | populated at render time |
| `attachments` | JSONField | refs copied from payload (e.g. `[{"type":"generated_report","id":4521}]`) |
| `status` | CharField | `pending` / `sent` / `failed` / `retrying` / `suppressed` / `cancelled` |
| `sent_at`, `error`, `retry_count` | | delivery state |
| `read_at`, `archived_at` | DateTimeField, nullable | in-app channel UI state |
| `idempotency_key` | CharField, unique with `event_code` | prevents double-fire on Celery retry |
| `is_test` | Boolean | excluded from activity log; redirect-to-actor at send time |

Retention is bounded by source-record retention. Beat task purges outbox rows whose source record has been voided. No flat TTL window.

### NotificationTemplate (Phase 2)

System-authored, code-shipped, loaded via `loaddata` on deploy. Tenants do not author templates.

| Field | Type | Notes |
|---|---|---|
| `tenant` | FK, nullable | `null` = system default |
| `event_code`, `channel`, `language` | | `language='en'` in v1 |
| `subject` | CharField(255) | also used as in-app title |
| `body_text`, `body_html` | TextField | |
| `severity` | inlined choices | `info` / `warn` / `critical` |
| `action_url_template` | CharField | deep-link, e.g. `/orders/{{ order.id }}` |
| `icon` | CharField | for in-app |
| `version` | Integer | bumped on each `loaddata` |

Resolution: tenant template → system default (tenant=null) → English fallback (`tenant=null, language='en'`) → renderer's payload-dump fallback (so missing templates don't break the pipeline).

### TenantNotificationBranding (Phase 2)

Single row per tenant. Tenant-controlled HTML fields (`email_signature`, `footer_disclaimer`) are bleach-sanitized with a tight allow-list before render. Logo URL restricted to allow-listed schemes. From-address stays on the platform's DKIM-signed domain; tenants override `email_from_name` only.

### TenantNotificationDefault (Phase 2)

Per-tenant defaults for which channels are enabled per event. Two row variants distinguished by `role`:
- `role IS NULL` → tenant-wide default applying to every user.
- `role = <TenantGroup>` → role-scoped default overriding the tenant-wide value for users in that role.

Seeded on tenant creation by walking `EVENT_REGISTRY` (tenant-wide rows only; role rows are authored through the matrix UI). Unique constraint uses `nulls_distinct=False` so the tenant-wide row cannot duplicate.

### UserNotificationPreference (Phase 2)

Per-user override layer — the most specific layer in channel resolution. Stored as a JSONField (`{event_code: {channel: bool}}`) for fast read at dispatch time. Always-write semantics: any explicit toggle persists, even when matching the inherited state. Later changes to role/tenant defaults do not silently flip user-set values.

### ExternalContact (Phase 3)

Customer-side recipients for outbound notifications (ASN, NCR-to-customer, ship-date alerts).

| Field | Type | Notes |
|---|---|---|
| `tenant` | FK | |
| `customer` | FK Customer | scoped to one customer |
| `name`, `email` | | required |
| `role` | CharField | `'primary'` / `'quality'` / `'procurement'` / etc. |
| `enabled` | Boolean | manual disable; opt-out via signed token sets this |
| `unsubscribe_token` | CharField | signed, expiring; rotated on enable |

### WatchedRecord (Phase 4)

User-followed records (orders, NCRs, CAPAs). Each `(user, source_content_type, source_object_id)` triggers a notification on every event fired against that record, regardless of rule matching.

### Escalation models (Phase 3 / additional table-stakes feature)

Three new models — designed but not yet built. See the **Escalation** section below for the runtime semantics.

```python
class EscalationPolicy(SecureModel):
    rule = OneToOneField(NotificationRule, on_delete=CASCADE)
    enabled = BooleanField(default=True)

class EscalationStep(SecureModel):
    policy = ForeignKey(EscalationPolicy, related_name='steps')
    order = PositiveSmallIntegerField()           # 0, 1, 2
    delay_seconds = PositiveIntegerField()        # from previous step (or rule fire for order=0)
    recipient_users = M2M(User, blank=True)
    recipient_groups = M2M(TenantGroup, blank=True)
    subject_override = CharField(max_length=255, blank=True)
    class Meta:
        unique_together = [('policy', 'order')]
        constraints = [CheckConstraint(check=Q(order__lt=3), name='escalation_step_order_lt_3')]

class EscalationInstance(SecureModel):
    policy = ForeignKey(EscalationPolicy)
    source_content_type = ForeignKey(ContentType)
    source_object_id = CharField(max_length=64)
    current_step = PositiveSmallIntegerField(default=0)
    next_fire_at = DateTimeField(db_index=True)
    status = CharField(choices=[('pending', ...), ('acknowledged', ...),
                                 ('exhausted', ...), ('cancelled', ...)])
    audit = JSONField(default=list)               # [{step, fired_at, recipient_count}]
    class Meta:
        unique_together = [('policy', 'source_content_type', 'source_object_id')]
        indexes = [Index(fields=['status', 'next_fire_at'])]
```

## CEL Conditions

CEL (Common Expression Language) is the rule condition language. `cel-python` provides the runtime. Each event registers its payload dataclass; the dispatcher generates a CEL type environment from that dataclass at load time and uses it to type-check expressions at save time.

**Examples** (against `ncr.opened` payload):

```
payload.severity == 'critical'
payload.severity in ['major', 'critical']
payload.opened_by_id == owner_user.id
payload.severity == 'critical' && payload.customer_id == 5
payload.opened_at > now() - duration("7d")
```

**Save-time validation** rejects unknown fields with "did you mean" suggestions:

```
Field 'severty' does not exist on NCROpenedPayload. Did you mean 'severity'?
```

**Supported operator subset** (the form builder covers the 95% case; the textarea is the escape hatch):

- Equality and comparison: `==`, `!=`, `>`, `>=`, `<`, `<=`
- Membership: `in [list]`
- String: `.contains(...)`
- Logical: `&&`, `||`, parens for grouping
- Special: `now()`, `duration("Nd")`, `owner_user.id`

**Fallback mode** — if `cel-python` integration becomes a tarpit, Phase 3 ships with runtime-only validation (try to eval, catch errors at dispatch) and adds save-time type-checking later as a non-breaking enhancement.

## Resolver and Dispatch

### Channel resolution (Phase 2, shipped)

`resolve_default_channels(user, event_code)` returns `{channel: enabled}` via a 4-layer cascade (most specific first):

1. `UserNotificationPreference` — explicit per-user override.
2. `TenantNotificationDefault` role-scoped (union across user's roles — any-enabled wins).
3. `TenantNotificationDefault` tenant-wide.
4. `EVENT_REGISTRY[event_code].default_channels`.

A short-lived cache (5 min TTL) shaves the per-emit DB cost. Invalidation is via `post_save` signals on the preference models (currently no-op pending Redis pattern-delete or version-key scheme; the TTL is the correctness backstop).

### Rule resolution (Phase 3, not yet built)

```python
def resolve_recipients(event, payload, tenant):
    candidates = NotificationRule.objects.filter(
        tenant=tenant, event_code=event.code, enabled=True
    ).filter(
        Q(scope_kind='tenant')
        | Q(scope_kind='customer', scope_id=getattr(payload, 'customer_id', None))
        | Q(scope_kind='personal')   # owner_user.id evaluated per-rule via CEL
    )

    for rule in candidates:
        if evaluate_cel(rule.conditions, payload, owner_user=rule.owner_user):
            for recipient in rule.effective_recipients(payload):
                yield (recipient, rule)
```

Dedupe on `(recipient, channel)` across matched rules, then intersect with the channel resolver, then write outbox rows.

## Channels

Single channel interface:

```python
class NotificationChannel(Protocol):
    code: str
    def send(self, outbox_row: NotificationOutbox) -> None: ...
    def supports_attachments(self) -> bool: ...
    def max_body_length(self) -> int | None: ...
```

**ConsoleChannel** (Phase 1, dev only) — logs to stdout. Useful in local development.

**InAppChannel** (Phase 2) — `send()` is a no-op marker. The outbox row IS the in-app notification; the frontend inbox queries `NotificationOutbox` rows directly via the API filtered by `channel='in_app'`.

**EmailChannel** (Phase 2) — `EmailMultiAlternatives` via `django.core.mail`. From-address: `DEFAULT_FROM_EMAIL` with display name from `TenantNotificationBranding.email_from_name`. HTML body attached as an alternative. Attachments resolved per `AttachmentRef` on the row (v1 only handles `type='generated_report'`; new artifact types extend the adapter as their events ship).

Future channels (SMS, Teams, Slack, push) plug in by implementing the protocol and registering with `register_channel(MyChannel())`. The dispatcher is channel-agnostic.

## Escalation

Aerospace-grade lean version (post-Phase 3 add). Pharma/medical can extend later without redesign.

### Behavior

A critical NCR opens. The matching `NotificationRule` has an attached `EscalationPolicy` with 2 steps: *+4h to QA Director*, *+24h to Plant Manager*. The system fires the normal rule notification AND creates an `EscalationInstance` tied to that specific NCR with `next_fire_at = now + 4h`.

A beat task (every 60s) iterates pending instances:
- If the source NCR is voided/closed → `cancelled`.
- If a `QualityReportDisposition` row exists → `acknowledged`, stop.
- If `next_fire_at <= now()` → fire the next step (emit synthetic event with the step's extra recipients merged in), advance to next step, set `next_fire_at = now + step.delay_seconds`.

After the last step, the instance is `exhausted` and quiet.

### Acknowledgement registry

Each event type that supports escalation registers an `is_acknowledged(source_record) -> bool` callable alongside its payload schema. v1 supports three events:

- `ncr.opened` → ack = `QualityReportDisposition` row exists.
- `capa.opened` → ack = `CapaAction` row exists.
- `document.approval_required` → ack = `ApprovalDecision` row exists.

Events without an `is_acknowledged` callable cannot host an escalation chain — the editor UI disables the escalation toggle with explainer copy. New ack definitions land alongside their respective domain features.

### Personal-scope coverage

Personal rules also support the same model under the framing of "forwarding when away." A casual user authors a one-step chain ("if I don't ack in 4 hours, forward to Sarah"). The full 3-step chain is reserved for the V2 editor (admin tier); the casual subscribe form exposes a single-step forwarding UI only.

### Deliberately not in v1

- Business-hours math ("4 working hours") — elapsed time only. Add per-tenant calendar later if customers ask.
- Per-recipient ack — source-level only.
- Dynamic recipients ("assignee's supervisor") — static picks only.
- Branching / conditional steps — linear chain.
- Custom email templates per step — subject override only.
- Multiple parallel escalation policies per rule — 1:1.

## UI Surfaces

Surfaces map to user tiers. Each tier sees only what it needs; all three are backed by the same data model.

### Tier-1: channel preferences (`/profile/notifications`)

`MyNotificationsPage` — matrix of events × channels with toggles. Reads `UserNotificationPreference`; falls back to `TenantNotificationDefault`. Saves only on explicit "Save changes." Shows "Showing 9 of 25 events" with a "Show all events" toggle to expose less-common events.

Also hosts the **My subscriptions** section (personal rules) and the placeholder **Watched records** section (Phase 4).

### Tier-2: casual personal subscribe (`SubscribeToEventSheet`)

Slide-out sheet opened from "My subscriptions." Single-step authoring:
- Event picker.
- Optional smart-token chips ("Opened by me", "Severity is critical", "In the last 7 days") — typed against the event's payload schema, no CEL exposed.
- Channel toggles (in-app, email).
- Optional "Forward when away" — single-step coverage forwarding with a delay + user/group picker.

Generates a `NotificationRule` with `scope_kind='personal'`. The user never sees CEL, scope pickers, recipient pickers, or AND/OR groups.

### Tier-3: admin rule editor (`NotificationRulesV2EditPage`)

Full-width route with sticky header (back link + action buttons + plain-English readback). Card stack below the header:

1. **Basics** — name.
2. **Scope** — tenant / customer / personal radio cards.
3. **Trigger** — event picker + Simple/Advanced toggle.
   - *Simple* mode: form-builder with nested AND/OR groups, smart-token chips, and a real-time English readback. Output compiles to CEL.
   - *Advanced* mode: monospace CEL textarea with inline "Insert field" / "Insert pattern" popovers and "did you mean" hints for unknown payload fields.
4. **Recipients** — groups + users + (customer scope only) external contacts. Multi-picker with chips.
5. **Delivery** — channels + active toggle.
6. **Escalation** (or **Coverage** for personal scope) — up to 3 steps, each with delay + recipients + optional subject override.

**Test rule** button in the header opens a side sheet with an editable sample payload and a live "Would fire?" badge. Phase 3 backend replaces the in-browser stub evaluator with a backtest against the last N days of real events.

### Tenant defaults (`/settings/notifications`)

`NotificationDefaultsPage` — admin-facing matrix that authors `TenantNotificationDefault` rows. Same component as the user matrix with a "Defaults for" role selector (tenant-wide vs. specific TenantGroup).

### Branding (`/settings/branding`)

Form for the six `TenantNotificationBranding` fields. Sanitization happens server-side at save; the form preview shows the rendered (sanitized) output.

### Rule list (`/settings/notification-rules-v2`)

Scope-tabbed list of rules with name, event, condition source, recipients summary, channels, active toggle, and a small "↗ N steps" / "↗ coverage" badge when escalation is configured. Click a row to open the editor.

### Component reuse

- `DelayInput` — number + unit picker, shared across editor and subscribe sheet.
- `SmartTokenRow` + `SmartTokenIcon` — chip rendering with inline parameter editing, shared.
- `LiveSamplePayload` — editable sample with enum chip toggles, shared.
- `NotificationChannelMatrix` — matrix grid used by both `MyNotificationsPage` and `NotificationDefaultsPage`.
- The two recipient pickers (`MultiPicker` in the editor, the flat chip grid in the subscribe sheet) are intentionally *not* shared — different UX tiers.

## Phase Plan

Sized at planning time, not in this doc.

### Phase 1 — Foundation *(done)*
Event registry, `EventType`, `register_event()`, payload schemas, `emit()` + Django signal, `NotificationOutbox` model, `ConsoleChannel`, `ncr.opened` vertical slice, factories module, debug command.

### Phase 2 — Email + In-app + Branding *(done)*
`EmailChannel` + `InAppChannel`, `TenantNotificationBranding` + branding form, `TenantNotificationDefault` with nullable `role` FK + post-save seeder, 4-layer `resolve_default_channels()`, `UserNotificationPreference` with always-write semantics + cache invalidation, matrix UI with "Defaults for" role selector and fallback hint subtitles, `NotificationTemplate` model + renderer with `bleach` sanitization. 34 tests green.

### Phase 3 — Rules + CEL + Three scopes *(frontend demos done, backend not started)*
`NotificationRule` with `scope_kind`/`scope_id`/`owner_user` + CHECK constraint + custom manager methods + per-scope DRF serializers, `cel-python` integration with type-schema generation from payload dataclasses, dispatcher rewrite (`_resolve_recipients` becomes rule-driven), API endpoints, `ExternalContact` model.

**Done when:** all three scopes save and dispatch correctly; CHECK constraint rejects malformed rows; CEL save-time validation produces field-level "did you mean" errors for typo'd payload paths; per-scope serializers reject inappropriate fields; tenant admin authors tenant + customer-scoped rules through the UI; users author personal rules; tenant-isolation lint passes; CEL fallback mode reachable via settings flag if integration slips.

### Phase 4 — Escalation + Watch + Dry-run + Activity log + Test-send
**Escalation engine** *(in progress)* — three new models (`EscalationPolicy`, `EscalationStep`, `EscalationInstance`), `tick_escalations` beat task, ack registry for the v1 events. Wires the existing `EscalationCard` UI placeholder to a real save path. See the **Escalation** section for runtime semantics.

`WatchedRecord` + watch button; rule dry-run/preview endpoint (replaces the in-browser stub evaluator with backend CEL + real events); activity log over `NotificationOutbox`; send-test endpoint with channel-level redirect-to-actor guard; `auditlog` registration on rule / preference / branding models with per-scope field exclusions.

**Escalation done when:** A `NotificationRule` with an `EscalationPolicy` writes both an initial outbox row and a pending `EscalationInstance` on emit; the beat task advances pending instances on schedule; logging a disposition on the source NCR cancels the instance; voiding the source cancels the instance; reaching the last step marks `exhausted`. EscalationCard saves through the rule serializer with no "preview" badge.

### Phase 5 — Migration + Polish

Original scope: replace scattered `send_mail` call sites with `emit()`, migrate any existing `NotificationRule` rows to `scope_kind='tenant'`, delete legacy `services/core/notification.py` + `email_handler.py` + `email_notifications.py`, copywrite system templates for the v1 launch event set, staging smoke run.

**Actual scope after reconnaissance** (May 2026):

- Most event cutovers in the original inventory turned out to need per-instance recipient routing (`recipient_strategy='from_payload'`) and got deferred to Phase 6 alongside the engine extension. See "Phase 6 event-set additions" below.

- Some entries in the original "Path B" inventory turned out to be **transactional response flows**, not notification events — they belong outside the rule engine entirely:
  - **`report.generated`** — user clicks "Email me" on the SPC page; backend generates PDF and emails it to that user. Not a notification (no platform-side decision about who gets it; the user explicitly requested it). Stays as a direct `EmailMessage` send in `Tracker/reports/tasks.py`.
  - **`user.invited`** — admin invites a specific user; transactional response flow same as above. Stays as a direct send.

- Some entries turned out to be **dead code** rather than cutovers:
  - **`sampling.triggered` email path** — `email_handler.py` was scaffolded in Aug 2025 but never had a caller in any commit. Deleted as part of Phase 5 cleanup. The actual feature (alerting per-step reviewers when fallback sampling fires) is a legitimate notification and gets built fresh in Phase 6 (see event-set additions below).
  - **STEP_FAILURE Path A handler** — Phase 3 cutover landed but the handler entry was never deleted. Removed in Phase 5; new system template added for `quality.step_failure`.

**The remaining "CAPA reminder cutover" also needs Phase 6 infrastructure.**

Closer reading of `check_capa_reminders` in `tasks.py` shows the recipient is `capa.assigned_to` (per-CAPA dynamic, not static QA group). That's the same `recipient_strategy='from_payload'` shape as everything else. It moves to Phase 6 alongside the other dynamic-routing cutovers — and the proper version of it isn't just a template port but a reframe onto `EscalationPolicy` (the hand-rolled `28d / 7d / 3d / 1d` tier-table in the beat task is reinventing what the escalation engine does natively).

**Phase 5 status (May 2026): functionally complete.**

What actually landed:
- ✅ `STEP_FAILURE` Path A handler removed; new `quality.step_failure` system template registered.
- ✅ Dead `email_handler.py` + `sampling_trigger_notification.txt` deleted.
- ✅ `NotificationOutbox` source GFK added (admin-tooling infrastructure that was incidentally explored during the dropped PII redaction slice; kept because it's independently useful for "show all notifications about this source" admin views).
- ✅ Design doc updated to reflect actual scope.

What waits on Phase 6 (cannot finish standalone):
- Final delete of `Tracker/notifications/__init__.py` + `handlers.py` — blocked on the CAPA reminder cutover, which is blocked on `recipient_strategy='from_payload'`. The handler registry stays alive in the meantime; it's mostly inert (orphan entries with no callers) but the file structure stays.
- The `FIXED` branch of `calculate_next_send` in `services/core/notification.py` — goes with the approval cutover (Phase 6).

**Conclusion:** Phase 5 turned out to be a "what does the inventory actually look like at the deadline" exercise more than a "do the migration" exercise. Most originally-listed cutovers belong to Phase 6 because they need per-instance routing, two belong outside the notification engine entirely (transactional flows), one was dead code. The substantive next slice is the Phase 6 engine extension, which unblocks the full backlog of approval / CAPA / sampling cutovers in one move.

### Phase 6 (planned) — Per-instance recipient routing + quorum-aware reminders

Phase 5 ports the legacy emit sites onto the rule engine as-is. The engine handles three notification shapes natively today: **broadcast** (NCR opened to QA Managers), **role-fanout** (anyone in a group), and **personal subscription**. Two real production shapes don't fit, and we punt them to Phase 6 rather than expand Phase 5's scope:

1. **Per-instance / per-assignee routing** — e.g. sequential MRB stages where each stage's approver is determined by the domain at request time, or "CAPA assigned to Tina" where the recipient is a runtime property of the source record, not an admin-authored rule recipient. Until this lands, these events route via the cheap workaround in the cutover — the producer signal calls `emit()` once per resolved recipient — which gives the right notifications but loses the rule engine's CC / observability / escalation hooks for these events specifically.

2. **Quorum-aware reminders** — e.g. CAPA Review Board where 2 of 5 must approve before a Process Change Request can spawn. The board membership routes fine via a static `TenantGroup`, the quorum-met / quorum-failed predicates fit the existing ack registry, but reminder steps at +24h / +48h fire to *everyone* including users who've already approved.

**Two engine extensions cover both.** Both are small (~150 LOC combined plus tests) and additive — no breaking changes to rules authored under Phase 5:

- **`recipient_strategy='from_payload'` on `NotificationRule`** — dispatcher resolves recipients from `payload.recipient_user_ids` (and/or group/external) instead of, or in addition to, the rule's static M2M lists. Solves shape (1). Pairs with a "Recipients come from the event" empty state in the rule editor that hides the multipicker.

- **`skip_recipient` predicate on the ack registry** — runner consults `skip_recipient(source, user)` per candidate at step-fire time and drops outbox rows for users who've already responded. Solves shape (2) and any future "track who responded" event (RFP responses, training acks, audit-finding sign-offs).

Independent of the notification engine, **CAPA → PCR auto-creation is a separate product decision** — today the CAPA and PCR aggregates are linked only by user action. If the product calls for auto-spawning a PCR from a quorum-approved CAPA, that's a signal handler in `services/change_control/`, not a notification feature. Notification: emit `capa.approved` when `ApprovalRequest.status` flips. Product: decide whether a downstream service listens to that event and creates a PCR. Phase 6 only commits to emitting the event.

**Phase 6 done when:** A rule authored with `recipient_strategy='from_payload'` fires to the payload-resolved users plus any static CCs, with cooldown + escalation working unchanged; a step fire on an ack-registered event with `skip_recipient` set excludes already-responded users from that step's outbox rows; CAPA Review Board demo runs end-to-end (5 reviewers, 2 must approve, reminders at +24h skip the 2 who already approved, quorum-fail cancels the chain, quorum-met fires `capa.approved`).

**Phase 6 event-set additions** — events that turned out to need `recipient_strategy='from_payload'` and so deferred from Phase 5. All build on the same engine pieces; difference is the source domain code that fills `payload.recipient_user_ids` at emit time:

- **`approval.requested`** / **`approval.decided`** — payload includes `recipient_user_ids` from `ApprovalRequest.get_pending_approvers()` (request side) or `[requested_by_id]` (decision side). Cuts over the `notify_approvers` / `notify_status_change` path. Existing templates at `emails/approval_request` and `emails/approval_decision` port into `system_templates`. Escalation policy on the rule replaces the legacy `escalate_approvals` beat task. The orphan Path B tasks `send_approval_request_notification` / `send_approval_decision_notification` in `tasks.py` get deleted (already zero callers).

- **`capa.assigned`** / **`capa.task_assigned`** — payload includes `recipient_user_ids=[capa.assigned_to.id]` (or task assignee). Replaces the direct `send_capa_assignment_notification` Celery task. Existing inline templates become a proper system template.

- **`capa.ready_for_verification`** / **`capa.verified_effective`** — same shape, single-recipient routing.

- **`sampling.triggered`** — payload includes `recipient_user_ids` from `step.notification_users` (per-Step M2M already in schema). Fires from `create_sampling_fallback_trigger()` in `services/mes/sampling_ruleset.py`. The `SamplingTriggerState.notification_sent` / `notified_users` columns already exist in schema (Aug 2025 scaffold) — never had a writer because the right pipeline (rule engine) wasn't built yet. Escalation worth attaching: a sampling-fallback firing without acknowledgement in ~4h is a quality-floor signal worth pushing up. The dead `email_handler.py` was deleted during Phase 5 cleanup; Phase 6 builds this fresh through `emit()`.

- **`capa.due_soon`** / **`capa.overdue`** — these CAN stay in Phase 5 because the recipients are typically a static "QA Manager" group, not per-CAPA dynamic. Phase 6 picks up the leftover if they turn out to also need per-CAPA routing in practice.

### Future (post-v1, demand-driven)

- **Digest aggregation** — windowed batched notifications. High user demand once event volume grows.
- **Rate limit / circuit breaker** — per-rule counter with TTL; safety prerequisite before opening rule authoring to non-admins.
- **Backtest against historical events** — replaces the in-browser "Would fire?" stub with real matched events from the last 7 days.
- **SMS / Teams / Slack / push** channels.
- **Quiet hours** (paired with SMS).
- **Real-time push** — Django Channels for instant in-app updates.
- **Multi-language templates** — schema reserves `language` field.
- **Pattern detection / CEP** — "3 NCRs on same part type in 24h" type rules.
- **Business hours math** — "4 working hours" semantics for escalation, per-tenant calendar.
- **Shift-aware / location-hierarchy / skill-certification recipient resolution** — require supporting domain models.

## Testing

Conventions and test files live under `Tracker/tests/notifications/`. Established patterns:

- Django `TestCase` / `TransactionTestCase` (no pytest).
- `TenantContextMixin` from `Tracker/tests/base.py` for ContextVar tenant scoping in `setUp` / `setUpTestData`.
- `time-machine` for time-dependent tests (escalation, SLAs).
- Django `locmem` email backend for channel tests.
- Tests must pass the existing `test_tenant_scoping_lint.py` audit.
- API-shape testing lives at the serializer level only — `drf-spectacular` + `openapi-zod-client` carry runtime validation through to the frontend.

Current test files: `test_emit_vertical_slice` (deleted in Phase 2; replaced by per-component), `test_resolver`, `test_seeder`, `test_render`, `test_channels`, `test_dispatcher_phase2`. Factories in `Tracker/tests/notifications/factories.py` cover the common patterns (`make_event_payload`, `capture_channel_sends`, `make_tenant_group`, `make_user_in_groups`, `set_user_preference`, `set_tenant_default`).

Coverage targets: service modules >90%, channel adapters >85%, models with managers/properties >80%, subsystem total >85%.

## Compliance

The notification system supports compliance; it is not itself a compliance subsystem. Audit-relevant artifacts (NCR dispositions, CAPA closures, e-signatures) live on the underlying business records.

- **Proof of dispatch for customer-required notifications (IATF 16949 8.7.1.4)** — outbox row + SMTP send confirmation.
- **Audit trail of system configuration (ISO 9001 4.4)** — `django-auditlog` registered on `NotificationRule`, `TenantNotificationDefault`, `TenantNotificationBranding`. Tenant admin edits produce auditlog entries with actor + timestamp.
- **PII retention discipline** — *Deferred indefinitely for the v1 deployment context.* See "Per-contact pseudonymization (Phase 6+)" below for the shape this work takes when it does land. Earlier versions of this section proposed a source-record-void redaction signal; that's the wrong trigger and wrong shape — left this note so the next reader sees why.

### Per-contact pseudonymization (Phase 6+)

**Not part of v1.** Captured here so the right shape exists when a tenant needs it.

Trigger: a tenant's customer-portal end-customer is EU-based (e.g., the tenant's MRO contract is with Volvo), and a specific person at that customer formally requests erasure of their personal data under GDPR Article 17. *Not* a source-record void; *not* a system-wide signal. Just a per-contact admin action.

Shape: an admin (the tenant's compliance officer) reviews the request, decides which fields fall under the aviation legal-obligation exception (FAA/EASA + customer-mandated retention typically refuse most of the request lawfully), and clicks "Anonymize this contact" for the remainder. The action:

- Pseudonymizes the `ExternalContact` row: `name`, `email`, `phone` → blank or stable token; `customer` FK + `id` preserved so operational links survive.
- Pseudonymizes references in surviving `NotificationOutbox` rows for this contact: `rendered_subject` / `rendered_body_text` / `rendered_body_html` replace the contact's name with the token; `external_contact_id` + `sent_at` + `event_code` + `status` preserved.
- Pseudonymizes audit log entries that reference the contact by name (django-auditlog supports this).
- Writes an audit log entry recording who triggered the anonymization, when, and the citation for the refusal-of-other-fields decision.

Why this isn't v1:
- US-only deployment doesn't engage GDPR at all.
- Even for an EU-facing tenant, the legal-obligation exception covers most operational records — actual anonymization is the exception, not the routine.
- Engaging this feature requires a signed DPA + SCCs between the platform and the tenant; that's a customer-success step, not engineering.

When this becomes v1: when the first tenant signs an aerospace contract with an EU end customer and that customer requests erasure for a real individual. The `NotificationOutbox` source GFK added in Phase 4 cleanup is the only piece of supporting infrastructure already in place; everything else builds at that time.

CAN-SPAM does not apply to transactional B2B notifications; unsubscribe links are gated by `EventType.transactional`.

## Open Questions

To resolve during Phase 3 implementation:

1. **In-app polling cadence.** Background poll on unread-count (60s default) + refetch-on-focus via React Query. Tune from real load; SSE upgrade is a separate roadmap item.
2. **WatchedRecord cap.** Soft warning at >50 likely sufficient for v1.
3. **In-app inbox query window.** Default "last 30 days, paginate further on demand." Confirm against tenant traffic.
4. **CEL fallback boundary.** When does the runtime-only validation cutover become a permanent ship-state rather than a temporary fallback? Tied to `cel-python` ergonomics.

## References

- `Documents/PERMISSION_SYSTEM_REFACTOR.md` — `TenantGroup` / `UserRole` used in recipient resolution.
- `Documents/SECURE_MODEL_TENANT_AUTO_SCOPING.md` — tenant scoping inherited by every notification model.
- `Documents/COMPLIANCE_REQUIREMENTS.md` — ISO 9001 / IATF 16649 / AIAG PPAP audit-trail constraints.
- `Tracker/services/core/notification.py` — existing partial implementation, replaced in Phase 5.
- [CEL spec](https://github.com/google/cel-spec) · [cel-python](https://github.com/cloud-custodian/cel-python) · [Django email docs](https://docs.djangoproject.com/en/stable/topics/email/)

## Appendix: Phase 5 Migration Inventory

The codebase has **three** parallel email-sending implementations running side-by-side. Phase 5 consolidates all three into the `emit()` path. Inventory below was produced via codebase audit (May 2026); line numbers will drift before Phase 5 starts — re-grep at the time.

### Already removed during the NotificationSchedule cutover *(May 2026)*

The legacy `WEEKLY_REPORT` slice of Path A was removed when `NotificationSchedule` shipped. The following items in the original inventory are **already gone** and need not be re-removed in Phase 5:

- `Tracker/services/core/notification.py:enqueue_weekly_report` — deleted
- `Tracker/email_notifications.py:send_weekly_order_update` — deleted (file kept; `send_invitation_email` still lives there)
- `Tracker/email_handler.py:send_weekly_order_report` — deleted (file kept; sampling-trigger helpers still live there)
- `Tracker/tasks.py:send_weekly_order_update_task` + `send_weekly_emails_to_all_customers` + `create_weekly_report_notifications` — deleted
- `Tracker/notifications/handlers.py` — `WEEKLY_REPORT` handler entry + `build_weekly_report_context` + `validate_weekly_report_send` deleted
- `Tracker/management/commands/send_weekly_emails.py` — entire file deleted
- `Tracker/management/commands/send_reports.py` — entire file deleted
- `PartsTrackerApp/celery_app.py` — `create-weekly-customer-notifications` beat entry deleted
- `Tracker/viewsets/qms.py:NotificationPreferenceViewSet` — entire viewset deleted (the legacy `/api/NotificationPreferences/` endpoint)
- `Tracker/serializers/qms.py` — legacy `NotificationScheduleSerializer` + `NotificationPreferenceSerializer` deleted
- `PartsTracker/PartsTrackerApp/urls.py` — `/api/NotificationPreferences/` route deleted
- `ambac-tracker-ui/src/hooks/useRetrieveNotificationPreferences.ts` + `useCreate/Update/DeleteNotificationPreference.ts` — four files deleted
- Customer-activation hook in `viewsets/core.py` rewired: `opt_in_notifications=True` now creates a personal `NotificationSchedule` instead of `enqueue_weekly_report`
- Data migration `Tracker/migrations/0046_migrate_weekly_reports.py` archived all legacy `WEEKLY_REPORT` `NotificationTask` rows

Net Phase 5 inventory adjustments:
- `order.weekly_report_ready` row in the events table (line ~554) is **resolved**, not Phase 5 work.
- The deletion list (`email_handler.py`, `email_notifications.py`, the two management commands) is shorter — the files stay, just the weekly functions inside them are gone.
- The `WEEKLY_REPORT` enum value on `NotificationTask.notification_type` choices is intentionally kept for compat with the archived legacy rows. Drop only when the table is dropped (Phase 5).

### Additional items discovered post-Phase 3 *(add as found)*

- **The `FIXED` branch of `calculate_next_send`** in `services/core/notification.py:38-49` is dead code once the approval cutover completes — only `interval_type='FIXED'` callers were WEEKLY_REPORT (gone) and the approval enqueue helpers (which never set `day_of_week`/`time`/`interval_weeks` and would crash if the branch ran). Remove with the approval cutover, not standalone.
- **The legacy `escalate_approvals` celery task** in `Tracker/tasks.py` parallels the new generic escalation engine (Phase 4). After Phase 4's escalation engine handles approval escalation generically via `EscalationPolicy`, this dedicated task can be deleted.
- **`Tracker/notifications/__init__.py:get_notification_handler`** and the `NOTIFICATION_HANDLERS` registry will be empty once Path A is fully migrated (CAPA_REMINDER + APPROVAL_* are the remaining entries). Delete the whole package in the same PR as the last Path A handler.



### The three paths

| Path | Mechanism | Templates | Currently sends |
|---|---|---|---|
| **A** — legacy rule engine | `notify()` → `NotificationRule` match → `NotificationTask` row → `dispatch_pending_notifications` (5-min beat) → `NotificationHandler.send()` → `send_mail` | Real Django templates (`emails/capa_reminder`, `emails/approval_request`, ...) | STEP_FAILURE, CAPA_REMINDER, WEEKLY_REPORT, APPROVAL_REQUEST/DECISION/ESCALATION |
| **B** — direct `send_mail` | Per-event Celery tasks in `tasks.py` with hardcoded message bodies | None (inline f-strings) | CAPA assignment + task assignment + ready-for-verification + verification-complete + overdue, approval overdue + escalation, user invitations |
| **C** — template direct | `send_mail()` with `render_to_string()` outside the rule engine | Real Django templates | Sampling trigger, generated-report-ready, legacy weekly reports |

### Double-send risk: approvals

Three events fire via **both Path A and Path B** today, producing duplicate emails:

| Event | Path A trigger | Path B trigger |
|---|---|---|
| `APPROVAL_REQUEST` | `notify_approvers()` signal → `enqueue_approval_notification()` → NotificationTask | `send_approval_request_notification` task (around `tasks.py:807`) |
| `APPROVAL_DECISION` | `notify_requester_on_decision` signal → `enqueue_decision_notification()` → NotificationTask | `send_approval_decision_notification` task (around `tasks.py:851`) |
| `APPROVAL_ESCALATION` | `escalate_approvals` beat task → NotificationTask | `check_overdue_approvals` task sends direct `send_mail` (around `tasks.py:911`) |

**Sequencing trap.** If Phase 3 swaps the dispatcher without disabling one path, double-emails get worse, not better. Order: disable Path A handler OR Path B task, never both at once, with staging verification between steps. The approval cutover deserves its own PR with explicit verification.

### Cutover protocol

For each event: (1) switch the upstream signal/beat-task to `emit()`, (2) disable the redundant direct-send Celery task, (3) confirm the new path produces the same email. Steps 1+2 without 3 = no email sent. Steps 1+3 without 2 = double-send. Verify in staging before deleting old paths.

### Events to register (~15 total)

| Event code | Today | Notes |
|---|---|---|
| `capa.assigned` | Path B `send_capa_assignment_notification` | New template needed |
| `capa.task_assigned` | Path B `send_capa_task_assignment_notification` | New template needed |
| `capa.ready_for_verification` | Path B `send_capa_ready_for_verification_notification` | New template needed |
| `capa.verified_effective` | Path B `send_capa_verification_complete_notification` | New template needed |
| `capa.overdue` / `capa.task_overdue` | Path B `check_overdue_capas` | New templates needed |
| `capa.due_soon` | Path A `CAPA_REMINDER` handler | Existing template migrates as `emails/capa_reminder` |
| `approval.requested` | **Path A + B duplicate** — pick A, disable B | Existing template `emails/approval_request` |
| `approval.decided` | **Path A + B duplicate** — pick A, disable B | Existing template `emails/approval_decision` |
| `approval.escalated` | **Path A + B duplicate** — pick A, disable B | Existing template `emails/approval_escalation` |
| `approval.overdue` | Path B `check_overdue_approvals` | New event + template |
| `sampling.triggered` | Path C `send_sampling_trigger_email` | Existing template `emails/sampling_trigger_notification.txt` migrates |
| `report.generated` | Path C `generate_and_email_report` | New event + template; attachment ref via `AttachmentRef` |
| `order.weekly_report_ready` | Path C + A — multiple paths exist | Existing template `emails/weekly_customer_update` migrates |
| `user.invited` | Path B `send_invitation_email_task` | New event + template |
| `quality.step_failure` | Path A via `notify()` from `quality_report.py:88` | **Phase 3 scope, not Phase 5** — clean migration |
| `workorder.held` / `workorder.overdue` | Path A via `notify()` from `tasks.py:scan_work_order_holds_and_overdue` | **Phase 3 scope, not Phase 5** — clean migration |

The three `quality.*` / `workorder.*` events at the bottom are the only `notify()` callers and fold into Phase 3 because they share the rule-subsystem cutover. Everything else is Phase 5.

### Signals to rewrite (6)

All in `Tracker/signals.py`:

- Sequential-approval next-approver notify (post_save on ApprovalResponse).
- Requester-on-decision notify (post_save on ApprovalRequest).
- CAPA assignment notify (post_save on CAPA).
- CapaTasks assignment notify (post_save on CapaTasks).
- CAPA ready-for-verification notify (post_save on CapaTasks completion).
- CAPA verification-complete notify (post_save on CapaVerification).

Each becomes `emit('<event_code>', tenant=..., payload=...)` after the migration.

### Files to delete

- `Tracker/email_handler.py` — content moves into `sampling.triggered` and `order.weekly_report_ready` event templates.
- `Tracker/email_notifications.py` — thin wrapper layer; callers target `emit()` directly.
- `Tracker/management/commands/send_reports.py` — unused, references deleted handler.
- `Tracker/management/commands/send_weekly_emails.py` — preview branches can move to a debug command if useful; real-send is dead.
- Direct-send blocks in `Tracker/tasks.py` covering CAPA (~lines 1009–1306), approval (~lines 772–925), invitation (~lines 461–528).

### Files staying as-is

- `Tracker/adapters.py` — allauth social/account adapters. Allauth handles confirmation/verification email.
- `Tracker/serializers/core.py:340` — allauth password-reset path.
- `PartsTrackerApp/settings.py:464–470` — SMTP backend / DKIM config.

### Sizing

- ~15 event codes to register.
- ~25 `send_mail` / template-render call sites to replace.
- 6 signal handlers to rewrite.
- 4 files to delete entirely, several blocks within `tasks.py`.
- 2 cutover decisions requiring staging verification (CAPA overdue paths, approval overdue + decision + request paths).
- Email channel adapter gains a small attachment-handling extension (~20 LOC) for `report.generated`.

Line numbers stale by definition — re-grep at Phase 5 time. Treat as a structured punch list, not a literal map.

## Working notes

- **Phase boundaries are checkpoints.** Don't ship phase N+1 work in a phase N PR. Surface the boundary, summarize what's complete against the phase's "Done when" line, get explicit approval before starting the next phase.
- **Polymorphism mitigations are mandatory, not optional polish.** CHECK constraint, custom manager methods, per-scope DRF serializers all ship in the Phase 3 PR that introduces the three-scope model.
- **Tenant scoping is non-negotiable.** Every notification model inherits `SecureModel`. Every cache key includes `tenant_id`. Every `.unscoped` query is annotated with `# tenant-safe:` rationale.
- **Sub-decisions made during build get logged** in a companion `Documents/NOTIFICATION_SYSTEM_DECISIONS.md` (URL strings, polling cadence, default copy, etc.) so future sessions stay consistent.
