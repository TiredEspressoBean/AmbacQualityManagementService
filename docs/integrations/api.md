# API Overview

REST API for integrating uqmes with other systems.

!!! example "Demo API Responses"
    In demo mode, try these API endpoints to see real data:

    ```bash
    # Get Midwest Fleet order
    GET /api/orders/?order_number=ORD-2024-0042

    # Get parts with flow test failures
    GET /api/parts/?status=QUARANTINED

    # Get CAPA with full workflow
    GET /api/capa/3/  # CAPA-2024-003

    # Get SPC data for Flow Testing
    GET /api/spc/measurements/?step=flow-testing
    ```

    Demo tokens can be generated from any demo account's Profile > API Tokens.

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

### Orders
```
GET    /api/orders/           # List orders
POST   /api/orders/           # Create order
GET    /api/orders/{id}/      # Get order detail
PUT    /api/orders/{id}/      # Update order
DELETE /api/orders/{id}/      # Delete order
```

### Parts
```
GET    /api/parts/            # List parts
POST   /api/parts/            # Create part
GET    /api/parts/{id}/       # Get part detail
PUT    /api/parts/{id}/       # Update part
GET    /api/parts/{id}/history/  # Part history
```

### Quality Reports
```
GET    /api/quality-reports/  # List NCRs
POST   /api/quality-reports/  # Create NCR
GET    /api/quality-reports/{id}/  # Get NCR detail
```

### Work Orders
```
GET    /api/work-orders/      # List work orders
POST   /api/work-orders/      # Create work order
GET    /api/work-orders/{id}/ # Get work order detail
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

!!! note "API-Only Endpoints"
    Material Lots and Schedule Slots are fully functional via API but do not have dedicated UI pages yet. Use these endpoints for programmatic access to lot tracking and scheduling features.

## Filtering

Use query parameters:
```
GET /api/orders/?status=in_progress
GET /api/parts/?order=123
GET /api/quality-reports/?severity=critical
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
GET /api/orders/?page=2
```

## Creating Records

POST with JSON body:
```bash
curl -X POST https://api.example.com/api/orders/ \
  -H "Authorization: Token your-token" \
  -H "Content-Type: application/json" \
  -d '{"order_number": "PO-001", "customer": 123}'
```

## Updating Records

PUT or PATCH:
```bash
curl -X PATCH https://api.example.com/api/orders/1/ \
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

- 1000 requests per hour per token
- 429 Too Many Requests when exceeded
- `X-RateLimit-Remaining` header shows remaining

## Webhooks

Configure webhooks for events:

| Event | Trigger |
|-------|---------|
| `order.created` | New order |
| `order.updated` | Order changed |
| `part.status_changed` | Part moved |
| `quality_report.created` | New NCR |

!!! note "Planned Feature"
    Webhook configuration UI is planned. Contact your administrator to configure webhooks via backend settings.

## OpenAPI Schema

Full API documentation:
```
GET /api/schema/
```

Returns OpenAPI 3.0 specification.

Interactive documentation:
```
GET /api/docs/
```

## Example: Create Order with Parts

```python
import requests

BASE_URL = "https://yourcompany.ambactracker.com/api"
TOKEN = "your-token"

headers = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "application/json"
}

# Create order
order_data = {
    "order_number": "PO-2026-001",
    "customer": 1,
    "due_date": "2026-04-01"
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

## Best Practices

1. **Secure tokens** - Never expose in client code
2. **Use HTTPS** - Always encrypted
3. **Handle errors** - Implement retry logic
4. **Respect rate limits** - Implement backoff
5. **Use pagination** - For large datasets
