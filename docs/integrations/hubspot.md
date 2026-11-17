# HubSpot Integration

Connect uqmes with HubSpot CRM so deals arrive as orders.

!!! info "An optional integration, not part of the core product"
    Nothing in uqmes depends on HubSpot. This is one adapter among others in
    the integrations framework — useful if you already run HubSpot, and safely
    ignored if you don't.

!!! note "Where to configure"
    Connect and configure HubSpot yourself at **Admin > Settings > Integrations**
    (`/settings/integrations`). Requires tenant administrator permissions.

## Overview

The HubSpot integration enables:
- Create orders from HubSpot deals
- Sync company information
- Track order status in HubSpot
- Unified customer data

## Integration Features

### Deal to Order
When deals close in HubSpot:
- Order created in uqmes
- Company linked/created
- Contact information synced
- Deal properties mapped

### Company Sync
Company data synchronized:
- Company name and details
- Contact information
- Custom properties

### Status Updates
Order status reflects in HubSpot:
- Order progress
- Completion status
- Shipping information

## Configuration

### Prerequisites
- A HubSpot account you can create a private app in
- Tenant administrator access to uqmes

### Setup Steps

1. **Create a HubSpot private app**
   - In HubSpot: **Settings** > **Integrations** > **Private Apps**
   - Create an app and grant it CRM scopes — contacts, companies, deals
   - Copy its **Private App Access Token**

2. **Connect it yourself**
   - In uqmes: **Admin** > **Settings** > **Integrations**
   - Open HubSpot and paste the access token

    !!! danger "Never send the token to anyone"
        The access token is a credential with access to your CRM. You paste it
        into the integration yourself — nobody needs it emailed, messaged or
        read out to them, and anyone asking you to do that is asking you to
        leak it.

3. **Test the connection**
   - Create a test deal in HubSpot, then run a sync from the integration's page
     (or wait for the hourly one)
   - Confirm an order appears in uqmes
   - Watch **Sync Activity** on the integration's page for failures

## Field Mapping

### Deal to Order

| HubSpot Field | uqmes Field |
|---------------|-------------|
| Deal name | Order **name** |
| Associated company | Company |
| Associated contacts | Customer portal users |
| Close date | Estimated completion |
| Deal stage | Order **milestone** |

!!! warning "Deal Amount is not imported, and there is nowhere to put it"
    An order has **no value, amount or price field**. uqmes records what a
    customer asked for, not what it is worth — pricing stays in the system that
    owns it. If an older mapping table showed *Amount → Order value*, that
    field does not exist.

### Company Mapping

| HubSpot Field | uqmes Field |
|---------------|-------------|
| Company name | Company name — also how an existing company is matched |
| Address | Address |

!!! note "A company record is deliberately minimal"
    There is no website or phone field on a company to map onto. People at a
    customer are held separately as external contacts. See
    [Companies](../admin/setup/companies.md).

## How orders arrive

Orders are created by the **sync**, not by anything in HubSpot's own screens.
Each sync creates an order for every deal that doesn't have one yet, links the
company (creating it if no company of that name exists), and keeps the link, so
later syncs update the same order. There is no "Create Order" button inside
HubSpot.

## How the sync runs

| | |
|---|---|
| **Frequency** | Every hour automatically, or triggered by hand |
| **Method** | Scheduled bulk sync. Optionally, a HubSpot webhook updates a linked order's stage as soon as the deal's stage changes |
| **First sync** | Creates orders from your existing HubSpot deals — expect a lot of them |

!!! note "The one webhook: deal stage changes, inbound"
    uqmes can receive one kind of HubSpot webhook: a **deal stage change**
    (`deal.propertyChange` on `dealstage`), which updates the stage of an order
    already linked to that deal. It doesn't create orders; the sync does. Point
    the private app's webhook subscription at the integration's webhook address,
    and set its webhook secret on the integration so each call is verified.
    uqmes sends no webhooks of its own (see [API](api.md#webhooks)).

**Direction.** Almost everything is inbound: deals, contacts, companies and
pipeline stages all flow HubSpot to uqmes. The one outbound flow is milestone
changes pushing back to the deal's stage.

## Known limitations

These are properties of the adapter, not faults to report:

- **Attachments and notes are not synced.**
- **Companies are matched by name**, so inconsistent naming produces duplicates.
- **Portal users are created with placeholder passwords.** Configure SSO if
  customers are to sign in — see [SSO](sso.md).

!!! note "Field mapping is fixed"
    There is no field-mapping editor. What maps to what is the adapter's, as
    tabled above.

## Viewing Integration Status

Open the integration from **Admin > Settings > Integrations** to see its status:

- **What syncs** — the record types this integration covers
- **Sync Activity** — sync run history, with a **Recent activity** feed
- **Pipeline Tracking**, **Active Stage Prefix**, and **Debug Mode** settings
- **Remove integration** to disconnect

## Troubleshooting

### "Connection failed"
- Verify API credentials
- Check API key permissions
- Confirm network access

### "Company not found"
Companies are matched by **name**. A difference in spelling, punctuation or
suffix (*Acme Inc* vs *Acme, Inc.*) creates a second company rather than
matching the first. Align the names in HubSpot, or merge afterwards.

### "Fields not mapping"
Mapping is fixed by the adapter, so there is nothing to misconfigure. If data
is missing, check the private app's **scopes** — a missing `read` scope on
contacts, companies or deals is the usual cause — and the **Sync Activity**
feed for the failure.

## Permissions

Integrations are **administrator-only**, and not through a model permission —
the endpoints require Django staff access, so there is no
`view_integrationconfig` or `change_integrationconfig` to grant. Viewing an
integration and configuring it are the same level of access: if you can open
the page, you can connect and disconnect it.

