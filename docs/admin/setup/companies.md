# Companies

Manage customer and supplier company records.

## Company Types

There is one company record, not separate customer and supplier records. Two
switches say which it is, and a company can be **both** — see [What a company is
to you](#what-a-company-is-to-you) below.

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
- **Customers only** — the order form, and the core lots list
- **Either, depending on the row** — core receiving, where a *purchased* core
  came from a supplier (a core broker) and every other source is a customer's
  own unit

!!! tip "Narrowing is how you shorten the lists"
    The switches exist so a company that only ever sells to you stops appearing
    when someone picks a customer. On a shop with a long company list that is the
    difference between a usable picker and a scroll.

!!! warning "Turning a switch off keeps existing links, but some actions then refuse"
    Orders, lots and qualifications already recorded against the company stay
    exactly as they are — narrowing does not undo a relationship. But a few
    actions check the switch when they run, not only when they offer the
    company:

    - **Shipping** to a company with **Customer** off is refused — *"&lt;company&gt;
      isn't set up as a customer."* — even for an order already recorded against
      it.
    - **Importing cores**: a customer's core from it is refused the same way, and
      a purchased core from a company with **Supplier** off is refused with
      *"&lt;company&gt; isn't set up as a supplier, so a core can't be bought from
      it."*
    - **Importing stock** owned by it is refused while **Customer** is off.
    - Saving it as a part type's **preferred supplier** in the sourcing dialog is
      refused while **Supplier** is off — *"&lt;company&gt; isn't set up as a
      supplier."*

    So turn **Customer** off only for a company you will not ship to again.

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

- **SCAR PDF** — *Issued To* shows **Attn: &lt;quality contact&gt; (&lt;email&gt;)** above the
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
| **Core fulfilment arrangement** | **Not recorded**, **Exchange**, or **Repair &amp; return** — the customer's standing arrangement for cores they send in. See the warning below. |
| **CoC with every shipment** | Print a Certificate of Conformance with the packing list each time you ship to this customer. |

!!! warning "Core fulfilment is a contract, not a per-unit decision"
    This decides whether a customer gets **their own unit back** (repair &amp; return)
    or **one from stock** (exchange). Receiving inherits it rather than asking
    whoever is on the dock to guess, so setting it wrong sends the wrong physical
    unit to a customer — and nothing about that looks like an error at the time.

    Leaving it **blank** is meaningful too: it records that nobody has established
    an arrangement, which is different from choosing one. Set it when the contract
    is agreed, not when the first core arrives.

!!! note "There is no billing, terms or payment information here"
    A company has one **address**, used on SCARs and return-to-vendor sheets. There
    are no billing or shipping addresses, no payment terms and no credit fields,
    because uqmes is not an accounting system — that information lives wherever you
    run finance. Portal access is granted per **person**, not per company: see
    [Portal Access](#portal-access) below. Contacts are their own records — see
    [Company Contacts](#company-contacts).

### When the company is also a supplier

| Field | Description |
|-------|-------------|
| **Outside-process turnaround (days)** | Calendar days the scheduler reserves for subcontract work when this company is a step's outside-process vendor and the step sets no lead time of its own. |

## Supplier Information

None of this lives on the company record itself:

| What you want | Where it lives |
|---------------|----------------|
| Approved supplier list | [Supplier qualifications](../../workflows/supply/overview.md#approved-suppliers), per supplier and part type, with expiry |
| Quality rating | [Supplier Quality](../../workflows/supply/overview.md#supplier-quality) scorecards, computed from receiving inspection |
| Lead time | **Purchase lead time** on the [part type](part-types.md) |
| Outside-process turnaround | The turnaround field on the company |

## Company Contacts

A company can have several **external contacts** — people at the customer who
receive notifications without being users here. They are their own records, and
they are **not edited from a tab on the company**: find them under
**Data Management** > **External Contacts**.

| Field | Description |
|-------|-------------|
| **Customer** | The company they belong to |
| **Name** | |
| **Email** | Unique per company |
| **Role** | A free-form label — `primary`, `quality`, `procurement` |
| **Enabled** | Whether they currently receive anything |

!!! note "No phone or title"
    These records exist to route notifications — shipped ASN emails, NCRs to
    the customer, late-risk alerts — so they carry an email and nothing else to
    reach someone by.

Separately, a **user** can be flagged as an outside contact with the
**Contact for** field — see [Outside contacts](#outside-contacts) above. That is
the one SCARs and delivery chasing read.

## Portal Access

Portal access is granted per **person**, not per company:

1. Create a user for the contact
2. Set their **User type** to **Portal**
3. Associate them with the company
4. Add them to the **Customer** group

They then see only their own company's orders.

!!! warning "There is no 'Role Type' field"
    The account type is **User type**, with two values — Internal and Portal — and *Customer* is a
    group. See [Adding Users](../users/adding.md).

## Company Documents

!!! note "There is no Documents tab on a company"
    To associate a document with a company — a contract, quality agreement,
    certification or NDA — upload it and use the document's own **Link To**
    field. See [Uploading Documents](../../workflows/documents/uploading.md).

    Documents linked to a company surface on the generic record view of each of
    its orders (`/details/Orders/<id>`), under *Company Documents*. They are
    not on the order page you reach from the Tracker, which lists only what is
    attached to the order itself.

## HubSpot Integration

Where a HubSpot integration is configured, the sync walks **deals**, and
companies arrive as a side effect of that:

- A deal becomes an **order**
- The deal's associated company is matched to a company here, or created if
  there is none, and the HubSpot id is stored on the record
- The deal's associated contact becomes the order's customer

!!! note "The HubSpot id is on the record, not on the screen"
    The company carries its HubSpot id and the API returns it, but nothing in
    the interface shows it or links out to HubSpot. To find a company's HubSpot
    counterpart, read the id through the API.

See [Integrations](../../integrations/api.md).

## Permissions

| Permission | Allows | Held by |
|------------|--------|---------|
| `view_companies` | View companies | Every staff role |
| `add_companies` | Create companies | Tenant Admin, QA Manager, Production Manager, Document Controller |
| `change_companies` | Edit companies | Tenant Admin, QA Manager, Production Manager, Document Controller |
| `delete_companies` | Remove companies | Tenant Admin, QA Manager, Production Manager, Document Controller |

*Held by* is the groups that hold it when an organisation is created. Group permissions can be changed, so check your own in [Roles & Groups](../users/roles.md).

!!! note "Customers and suppliers are shared master data"
    Adding or changing a company is manager-tier. Other roles — Purchasing and
    Engineering included — see companies and pick them, but ask one of those
    groups to add a new customer or supplier.

