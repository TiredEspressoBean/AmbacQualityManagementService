# Part Approvals

**PPAP / FAI approvals — a supplier approved to produce a specific part type.**

**Supply** > **Part Approvals**

## What it's for

A part approval records that a particular supplier is approved to produce a
particular part type, on the strength of a PPAP submission or First Article
Inspection.

The approval is per **(part type, supplier) pair**. A supplier approved for one
part type is not thereby approved for another.

## Why it matters at receiving

This is the part worth understanding:

!!! warning "Unapproved pairs are held at receiving"
    For part types that require approval, receiving **holds** lots from a
    (part type, supplier) pair that has no **active, in-date** approval. The
    material arrives and then stops — it won't flow into stock.

So a missing or expired part approval doesn't surface as a warning at the point
someone places the order. It surfaces later, as material sitting on hold. If
lots are being held unexpectedly, this page is the first place to look.

Active means **Approved** or **Conditional**, and not past its expiry date. The
date is checked directly, so an approval stops counting on the day it lapses —
it does not wait for its status to be changed to Expired.

## Statuses

| Status | Counts at receiving? | Means |
|--------|---------------------|-------|
| **Pending** | No | Recorded, not yet granted |
| **Approved** | **Yes** | Granted |
| **Conditional** | **Yes** | Granted with conditions |
| **Suspended** | No | Withdrawn for now |
| **Expired** | No | Past its expiry date — set automatically |
| **Disqualified** | No | Withdrawn for good |

## Creating and granting an approval

Creating an approval and approving it are **two steps, by two kinds of people**:

1. Click **New approval** and record the part type, the supplier and the
   approval type — **PPAP**, or **First Article (FAI / AS9102)**. It saves as
   **Pending**, which does not release anything at receiving
2. Someone holding `approve_partapproval` — by default **QA Manager** or
   **Tenant Admin** — uses **Grant…** on it, optionally marking it conditional and giving effective
   and expiry dates

!!! important "Saving is not approving"
    A new record is Pending whatever you fill in — the status cannot be set on
    the form or through the API. Only **Grant…** makes it count, and only
    holders of `approve_partapproval` can use it. A buyer can record that a PPAP has been
    submitted; they cannot approve their own supplier.

**Suspend…** and **Disqualify…** each take a reason, which is added to the
record's notes. A disqualified approval cannot be granted again — it has to be
re-opened as a new approval.

Filter the list by **status** or **type**, or search it by approval number,
part type or supplier.

!!! note "This records the approval, not the submission"
    The PPAP elements or the AS9102 forms themselves are not managed here. Keep
    them wherever you keep them, attach them as documents if you like, and
    record the outcome on this page.

## Related

Supplier-level qualification is separate from part-level approval. A supplier
can be qualified in general and still lack approval for a specific part type —
both are checked.

- **Approved Suppliers** — supplier-level qualification, with expiry
- **Supplier Quality** — how suppliers are actually performing

## Next Steps

- **[Supply Overview](overview.md)** - The rest of the inbound picture
