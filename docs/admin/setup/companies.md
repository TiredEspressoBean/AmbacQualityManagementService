# Companies

Manage customer and supplier company records.

## Company Types

| Type | Purpose |
|------|---------|
| **Customer** | Companies that place orders |
| **Supplier** | Companies that provide materials |
| **Both** | Companies that are both customer and supplier |

## Creating a Company

1. Navigate to **Data Management** > **Companies**
2. Click **+ New Company**
3. Fill in company details
4. Save

### Company Fields

| Field | Description | Required |
|-------|-------------|----------|
| **Name** | Company name | Yes |
| **Type** | Customer, Supplier, Both | Yes |
| **Code** | Short identifier | No |
| **Contact Email** | Primary contact | No |
| **Phone** | Contact number | No |
| **Address** | Business address | No |
| **Website** | Company website | No |
| **Notes** | Internal notes | No |

## Customer-Specific Fields

For customer companies:

| Field | Description |
|-------|-------------|
| **Customer Portal Access** | Enable portal login |
| **Default Contact** | Primary contact user |
| **Billing Address** | Invoice address |
| **Shipping Address** | Delivery address |
| **Terms** | Payment terms |

## Supplier-Specific Fields

For supplier companies:

| Field | Description |
|-------|-------------|
| **Vendor Code** | Your internal code |
| **Quality Rating** | Supplier quality score |
| **Approved** | Approved supplier list |
| **Lead Time** | Default lead time |
| **Certifications** | ISO, AS, etc. |

## Company Contacts

Add multiple contacts per company:

1. Open company record
2. Go to **Contacts** tab
3. Click **Add Contact**
4. Enter contact details:
   - Name
   - Email
   - Phone
   - Title
   - Role
5. Save

## Portal Access

Give customers access to view their orders:

1. Create user for contact
2. Set user **Role Type** to Customer
3. Associate user with company
4. User sees only their company's orders

See [Adding Users](../users/adding.md).

## Company Documents

Attach company-related documents:

- Contracts
- Quality agreements
- Certifications
- NDAs

1. Go to **Documents** tab
2. Upload or link documents
3. Set document visibility

## HubSpot Integration

If HubSpot integration is enabled:

- Companies sync from HubSpot
- Deals create orders
- Contact information shared

Company records show HubSpot link.

## Permissions

| Permission | Allows |
|------------|--------|
| `view_company` | View companies |
| `add_company` | Create companies |
| `change_company` | Edit companies |
| `delete_company` | Remove companies |

## Best Practices

1. **Unique codes** - Use consistent identifiers
2. **Complete information** - Fill in key fields
3. **Track contacts** - Maintain contact list
4. **Regular review** - Update stale information
5. **Link documents** - Keep contracts attached
