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
    (part type, supplier) pair that has no approval. The material arrives and
    then stops — it won't flow into stock.

So a missing or expired part approval doesn't surface as a warning at the point
someone places the order. It surfaces later, as material sitting on hold. If
lots are being held unexpectedly, this page is the first place to look.

## Creating an approval

1. Click **New approval**
2. Record the part type, the supplier, and the approval type
3. Save

Filter the list by **status** or **type**, or search it.

## Related

Supplier-level qualification is separate from part-level approval. A supplier
can be qualified in general and still lack approval for a specific part type —
both are checked.

- **Approved Suppliers** — supplier-level qualification, with expiry
- **Supplier Quality** — how suppliers are actually performing

## Next Steps

- **[Supply Overview](overview.md)** - The rest of the inbound picture
