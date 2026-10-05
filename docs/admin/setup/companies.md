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
| **Address** | Printed on SCARs and return-to-vendor sheets | No |

!!! note "No phone or contact email on the company"
    Beyond the address, a company record holds no phone number, website or
    contact email. People are held separately as **external contacts**, and a
    company can have several.

## What a company is to you

Two switches decide where a company is offered, and a company can be **both**:

| Switch | Meaning |
|--------|---------|
| **Customer** | Buys from us — offered on orders |
| **Supplier** | Sells to us — offered on receipts and qualifications |

**Both are on by default**, so every existing company still appears everywhere
until someone narrows it.

Once narrowed, the pickers follow:

- **Suppliers only** — Expect, Expect from shortages, batch receive, the
  preferred supplier on a Material or Part Type, supplier qualifications, part
  approvals, outside-processing send-out, Supplier Quality
- **Customers only** — the order form

!!! tip "Narrowing is how you shorten the lists"
    The switches exist so a company that only ever sells to you stops appearing
    when someone picks a customer. On a shop with a long company list that is the
    difference between a usable picker and a scroll.

!!! note "Reman core pickers are not narrowed yet"
    They still offer every company.

## Outside contacts

A **user** record can be marked as someone at a supplier or customer rather than
a member of your staff — usually a contact who never logs in. The **Contact for**
field on the user form says what they are the contact *for*:

| Setting | Used for |
|---------|----------|
| **— not an outside contact** | Ordinary staff (the default) |
| **Quality (receives SCARs)** | The named recipient on a SCAR |
| **Deliveries / expediting** | Who to chase about a late delivery |
| **General** | Fallback for both |

Two places read it:

- **SCAR PDF** — *Issued To* shows **Attn: <quality contact> (<email>)** above the
  supplier's address, falling back to a General contact
- **Late deliveries** on Home — each row names the supplier's deliveries contact
  and email, falling back to General

!!! tip "This is what turns a report into an action"
    A SCAR addressed to a company goes to nobody in particular. The point of the
    field is that the paperwork and the Home card both tell you **which person**,
    without anyone looking it up.

    Set at least a General contact on suppliers you deal with regularly, even if
    you set nothing else.

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

