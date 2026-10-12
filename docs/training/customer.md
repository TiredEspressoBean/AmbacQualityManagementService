# Customer Portal Orientation

**Duration:** 30 minutes
**Prerequisites:** None
**Goal:** Track your orders, find your documents, invite a colleague, and
respond when you are asked to approve something

!!! note "Role Name"
    This is for the **Customer** role in the system.

!!! info "Demo Environment Login"
    **Email:** tom.bradley@midwestfleet.com
    **Password:** `demo123`

    Tom Bradley is a Midwest Fleet Services contact and sees only Midwest Fleet's
    orders — which is the point of this orientation.

!!! important "Start on Tracker, not Home"
    **Tracker** in the sidebar is your portal. Home is deliberately bare for a
    customer — *"Use the sidebar to navigate to your workflow."*

    Verified 2026-10-12: Tom sees **11 orders, all Midwest Fleet Services**, out
    of 16 in the tenant. Other customers' orders are filtered out entirely.

!!! tip "This is orientation for an external user"
    Hand this to your customer. It assumes no knowledge of manufacturing systems
    and nothing about how the shop works internally.

!!! note "Two rough edges to warn them about"
    The sidebar is not yet filtered by role, so a customer sees internal menu
    items — Processes, Scheduling, CAPAs — that refuse them when clicked. Home
    may also show a brief *"Failed to load data"* message for the same reason.
    Neither affects their orders.

---

## Module 1: What You Can See

### 1.1 Your orders, and only your orders

The Customer role is the only one in the system **without** tenant-wide
visibility. Everything you see is filtered to orders you are the customer on, or
have been invited to view.

You cannot see other customers' orders, the shop's internal work, costs, or
anyone else's documents. That isn't a setting your supplier chose — it is how the
role is built.

### 1.2 What you get

| You can | You cannot |
|---------|------------|
| View your orders and their progress | See any other customer's anything |
| View the parts on them | Change an order |
| See documents linked to your orders | Upload documents |
| See quality information for your orders | See internal quality data |
| Invite colleagues to view your orders | Invite anyone to someone else's |
| Respond to approval requests | Approve your supplier's internal work |
| Use AI chat on your own data | Query anything outside your orders |

---

## Module 2: Tracking an Order

### 2.1 Progress

Each order shows where it is: which stage, how many stages, and the delivery
date. A part-level view shows each unit's status.

### 2.2 What the statuses mean

Ask your supplier to walk you through their stage names once — they come from
that shop's own process, so "Nozzle Inspection" means what it means there.

See [Order Status](../workflows/orders/order-status.md).

### 2.3 What shipped

An order shows what has shipped, when, and by which carrier — including partial
shipments, so nine of ten units going out early appears as exactly that.

---

## Module 3: Documents

Documents linked to your orders appear in the portal — certificates, packing
lists, CoCs and whatever else your supplier shares against the order.

!!! note "You see what was shared against your order"
    Not the supplier's library. If you expect a document and don't see it, it
    hasn't been linked to your order yet — ask.

---

## Module 4: Inviting a Colleague

You can see who has access to your orders and **invite viewers** to them.

!!! warning "You can only invite to orders you can already reach"
    The invite applies to your own orders. There is no way to grant someone
    access to anything you cannot see yourself.

---

## Module 5: Responding to an Approval

Sometimes your supplier needs an answer from you — a use-as-is on a
nonconformance, an authorisation to proceed.

You will see the request, and you respond in the portal. Your answer is recorded
against the order with your name and the date.

!!! important "The decision is recorded, not negotiated here"
    The conversation about price or commercial terms happens wherever you
    normally have it. The portal records **what you decided**, so it is attached
    to the job rather than living in an email thread.

See [Approvals Overview](../workflows/approvals/overview.md).

---

## Orientation Checklist

- [ ] Logged in and found your order list
- [ ] Opened one order and read its progress
- [ ] Found what has shipped against it
- [ ] Opened a document linked to the order
- [ ] Found who else has access
- [ ] Located an approval request (if one exists)

---

## Next Steps

- [Customer Portal guide](../roles/customer.md) — the full reference
- [Order Status](../workflows/orders/order-status.md)
- [Approvals Overview](../workflows/approvals/overview.md)
