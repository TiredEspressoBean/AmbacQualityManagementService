# Companies

Manage customer and supplier company records.

## Company Types

A company has **no type field**. What a company *is* follows from how it is
used:

| Acts as | Because it has |
|---------|----------------|
| **Customer** | Orders, returned cores, or portal users |
| **Supplier** | Supplied material lots or part types, supplier qualifications, outside-process shipments |
| **Both** | Any combination of the above |

So the same record serves both roles without being flagged as either.

## Creating a Company

1. Navigate to **Admin** > **Data Management** > **Companies**
2. Click **New Companies**
3. Fill in the details
4. Click **Create Company**

### Company Fields

The record is deliberately minimal:

| Field | Description | Required |
|-------|-------------|----------|
| **Company Name** | Company name | Yes |
| **Description** | What this company is to you | Yes |
| **Outside-process turnaround (days)** | Default turnaround when sending work to this vendor | No |

!!! note "No address, phone, or contact fields"
    A company record holds no postal address, phone number, website, or contact
    email. People are held separately as **external contacts**, and a company
    can have several.

## Customer-Specific Fields

For customer companies:

| Field | Description |
|-------|-------------|
| **Customer Portal Access** | Enable portal login |
| **Default Contact** | Primary contact user |
| **Billing Address** | Invoice address |
| **Shipping Address** | Delivery address |
| **Terms** | Payment terms |

## Supplier Information

None of this lives on the company record itself:

| What you want | Where it lives |
|---------------|----------------|
| Approved supplier list | [Supplier qualifications](../../workflows/supply/overview.md#approved-suppliers), per supplier and part type, with expiry |
| Quality rating | [Supplier Quality](../../workflows/supply/overview.md#supplier-quality) scorecards, computed from receiving inspection |
| Lead time | **Purchase lead time** on the [part type](part-types.md) |
| Outside-process turnaround | The turnaround field on the company |

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
| `view_companies` | View companies |
| `add_companies` | Create companies |
| `change_companies` | Edit companies |
| `delete_companies` | Remove companies |

