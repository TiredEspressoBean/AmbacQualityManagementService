# API Overview

REST API for integrating uqmes with other systems.

!!! example "Trying it out"
    ```bash
    # Orders, filtered by the auto-generated order number
    GET /api/Orders/?order_number=ORD-2024-0042

    # Parts currently quarantined
    GET /api/Parts/?status=QUARANTINED

    # A CAPA by id
    GET /api/CAPAs/{id}/

    # SPC measurement data
    GET /api/spc/data/
    ```

    The record ids in these examples come from the **demo data set**, which
    exists only if your deployment was seeded with it — see
    [Training Data Setup](../training/training-data-setup.md). On a system with
    your own data, the shapes hold but the identifiers will not.

    API tokens are issued by an administrator — there is no self-service
    **API Tokens** page on your Profile.

## API Basics

### Base URL
```
https://yourcompany.uqmes.com/api/
```

### Authentication
Token-based authentication:
```
Authorization: Token your-api-token
```

### Response Format
JSON responses:
```json
{
  "count": 100,
  "next": "https://api.example.com/endpoint/?page=2",
  "previous": null,
  "results": [...]
}
```

## Getting API Token

!!! note "Contact Administrator"
    API token management UI is planned. Contact your administrator to obtain an API token.

Once you have a token, use it in the Authorization header. Tokens inherit user's permissions.

## Core Endpoints

!!! warning "Path casing is inconsistent — never guess it"
    **Most** model collections are PascalCase, named exactly as the model is:
    `/api/Orders/`, `/api/QualityReports/`, `/api/Parts/`. A lowercase guess
    like `/api/orders/` is **not** the same URL and will not resolve.

    But there are three patterns in use, not one:

    | Pattern | Examples |
    |---------|----------|
    | **PascalCase** — most model collections | `/api/Orders/`, `/api/Parts/`, `/api/MaterialLots/` |
    | **lowercase**, mostly non-model | `/api/auditlog/`, `/api/spc/`, `/api/dashboard/`, `/api/reports/`, `/api/scope/`, `/api/content-types/`, `/api/ai/search/` |
    | **lowercase kebab, but a real model collection** | `/api/process-change-requests/`, `/api/process-change-orders/`, `/api/process-change-notices/`, `/api/spc-baselines/` |

    And two that match no rule at all:

    ```
    /api/Sampling-rule-sets/
    /api/Sampling-rules/
    ```

    Capital S, then kebab-case. `/api/SamplingRules/` returns **404**.

    **The schema is the authority, not this page.** Fetch `/api/schema/` and
    search it rather than inferring a casing from a model name — the inference
    is wrong often enough to cost you.

### Orders
```
GET    /api/Orders/           # List orders
POST   /api/Orders/           # Create order
GET    /api/Orders/{id}/      # Get order detail
PUT    /api/Orders/{id}/      # Update order
DELETE /api/Orders/{id}/      # Delete order
```

### Parts
```
GET    /api/Parts/            # List parts
POST   /api/Parts/            # Create part
GET    /api/Parts/{id}/       # Get part detail
PUT    /api/Parts/{id}/       # Update part
GET    /api/Parts/{id}/history/   # Part history
GET    /api/Parts/{id}/traveler/  # Traveler document
```

### Quality Reports
```
GET    /api/QualityReports/        # List NCRs
POST   /api/QualityReports/        # Create NCR
GET    /api/QualityReports/{id}/   # Get NCR detail
```

### Work Orders
```
GET    /api/WorkOrders/       # List work orders
POST   /api/WorkOrders/       # Create work order
GET    /api/WorkOrders/{id}/  # Get work order detail
```

### Material Lots
```
GET    /api/MaterialLots/           # List material lots
POST   /api/MaterialLots/           # Create lot
GET    /api/MaterialLots/{id}/      # Get lot detail
POST   /api/MaterialLots/{id}/split/ # Split a lot
```

### Schedule Slots
```
GET    /api/ScheduleSlots/          # List schedule slots
POST   /api/ScheduleSlots/          # Create slot
GET    /api/ScheduleSlots/{id}/     # Get slot detail
```

!!! note "These have UI too"
    Material Lots and Schedule Slots are **not** API-only. Material lots have a
    full Materials page (see [Supply overview](../workflows/supply/overview.md))
    and scheduling has the Gantt board (see
    [Scheduling](../workflows/scheduling/overview.md)). Use the API for
    programmatic access, not because there is nowhere else to go.

## Filtering

Use query parameters:
```
GET /api/Orders/?status=in_progress
GET /api/Parts/?order=123
GET /api/QualityReports/?severity=critical
```

### Common Filters
- `status` - Filter by status
- `created_at__gte` - Created after date
- `created_at__lte` - Created before date
- `ordering` - Sort results

## Pagination

Default page size: 25

```json
{
  "count": 100,
  "next": "https://api.example.com/orders/?page=2",
  "previous": null,
  "results": [...]
}
```

Use `page` parameter:
```
GET /api/Orders/?page=2
```

## Creating Records

POST with JSON body:
```bash
curl -X POST https://api.example.com/api/Orders/ \
  -H "Authorization: Token your-token" \
  -H "Content-Type: application/json" \
  -d '{"name": "PO-001"}'
```

## Updating Records

PUT or PATCH:
```bash
curl -X PATCH https://api.example.com/api/Orders/{id}/ \
  -H "Authorization: Token your-token" \
  -H "Content-Type: application/json" \
  -d '{"status": "complete"}'
```

## Error Responses

### 400 Bad Request
Invalid data:
```json
{
  "order_number": ["This field is required."]
}
```

### 401 Unauthorized
Invalid or missing token.

### 403 Forbidden
Insufficient permissions.

### 404 Not Found
Record doesn't exist.

## Rate Limiting

**There is no global API rate limit**, and no `X-RateLimit-*` headers. Normal
authenticated API traffic is not throttled, so do not design a retry loop around
a 429 you will not receive.

Throttling is applied only to specific unauthenticated, abuse-prone endpoints —
login, signup, registration and password reset. Those limits are tunable per
deployment, so the exact numbers are your administrator's to confirm.

## Webhooks

!!! warning "Webhooks are not implemented"
    There is no webhook model, no outbound delivery and no retry — not in the
    UI and not in backend settings either. The event names an earlier version of
    this page listed (`order.created`, `part.status_changed` and the rest) do
    not exist.

    What *does* exist is **notification rules**: events raised inside the
    product, routed to people by rule. If you need to react to something
    happening, that is the mechanism — see
    [Notification Rules](../admin/setup/notification-rules.md). For pulling
    changes from outside, poll the relevant collection with a filter.

## OpenAPI Schema

Full API documentation:
```
GET /api/schema/
```

Returns OpenAPI 3.0 specification.

!!! note "No interactive docs endpoint"
    There is no `/api/docs/` browser. Fetch `/api/schema/` and read it with your
    own OpenAPI viewer.

## Example: Create Order with Parts

```python
import requests

BASE_URL = "https://yourcompany.uqmes.com/api"
TOKEN = "your-token"

headers = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "application/json"
}

# Create order
order_data = {
    "name": "PO-2026-001",
    # order_number is read-only — the server generates ORD-YYYY-NNNN
    "customer": "<customer-uuid>",
    "estimated_completion": "2026-04-01"
}
response = requests.post(f"{BASE_URL}/orders/",
                         json=order_data,
                         headers=headers)
order = response.json()

# Add parts
parts_data = {
    "order": order["id"],
    "part_type": 1,
    "quantity": 10,
    "serial_prefix": "WA-"
}
response = requests.post(f"{BASE_URL}/parts/bulk-create/",
                         json=parts_data,
                         headers=headers)
```

## Permissions

API access requires:
- Valid API token
- User must have permission for action
- Tenant context determined by token

