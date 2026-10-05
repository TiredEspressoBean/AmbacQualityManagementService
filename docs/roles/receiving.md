# Receiving

**The dock.** Taking material in, proving it is what was ordered, and putting it
somewhere findable.

!!! info "There is no Receiving group"
    Like [Planner](planner.md), this describes a **job**, not a group you can be
    put in. The work is usually held by **Purchasing**, whose description says so
    — *"supplier qualification, part approvals, expected receipts and incoming
    lots (purchase orders stay in the ERP)"* — and shared with **Operator**,
    **Shift Lead** and **Production Manager** depending on the shop.

    If something here isn't available to you, it is a permission question for
    whoever administers groups, not a sign you are on the wrong page.

## The day

| Question | Where |
|----------|-------|
| What is coming? | **Materials → On order**, and **Late** |
| What just arrived? | **Receive**, or **batch receive** for a lorry-load |
| What is stuck? | **Materials → Held**, and incoming inspection |
| What goes back? | **Materials → Rejected** |
| Where did I put it? | [Locations](../workflows/supply/locations.md) |

## Knowing what to expect

Expected deliveries are lots **on order** — created by **Import expected
deliveries** from your ERP's open PO lines, or added one at a time.

**Late** is anything overdue or due within three days. When a delivery slips,
**Chase…** records what the supplier said and any new promised date.

!!! important "Chasing never moves the goalposts"
    A new date changes what you are waiting for, but supplier on-time
    performance is still scored against the **first** promise. See [Chasing a
    late delivery](../workflows/supply/overview.md#chasing-a-late-delivery).

## Receiving a delivery

The receive dialog handles the things a dock actually meets:

- **Counting in by box or pound**, with the conversion shown as you type
- **Short deliveries** — you say whether more is coming or that's all. It is
  never assumed
- **Over-receipts** — the ordered figure is kept, and the lot reads *Ordered 100
  · 10 over*
- **Heat number** and **Source**
- **A photo of the CoC or packing slip**, taken at the dock

Putaway defaults to the **receiving dock** location; pick another if it is going
straight somewhere.

For a lorry-load, use the **paste grid** at `/production/material-lots/receive`.

## Dealing with holds

A lot can be held for **several reasons at once** — missing CoC, missing heat
number, unqualified supplier, expired shelf life. **Review hold** opens them.

**Supply what is missing and the hold clears itself.** Holds that are judgements
— an unqualified supplier, an unapproved part — need a quality manager to release
them with a reason.

The lot moves on **when the last hold goes**, so clearing one and seeing nothing
happen is normal.

Full detail: [Held at receiving](../workflows/supply/overview.md#held-at-receiving).

## Sending something back

Reject the bad pieces — or the whole lot, if you hold that permission — then
**Ship back** with the supplier's **RMA number**. Say whether replacements are
coming and an expected delivery is created and linked, so planning sees it.

Print the **RTV sheet** to travel with the goods.

## Putting it away, and proving it is still there

- **Print lot labels** at receipt, singly or for a whole batch
- **Move** lots by scanning, into locations that nest
- **Count** one location at a time, blind if you want an honest number

Submitting a count is the counter's job. **Applying** it needs `apply_cyclecount`
— a lead. The differences export as a spreadsheet for keying into the ERP.

See [Locations & Cycle Counts](../workflows/supply/locations.md).

## How the dock is doing

[Receiving Metrics](../workflows/supply/overview.md#receiving-metrics) — lots
received, what is waiting, median days to a decision, rejects and PPM, over 30,
60 or 90 days.

!!! tip "The number worth watching"
    *Median days to a decision* against *inspection itself*. If the first is days
    and the second is hours, material is waiting for someone to start — which is
    a scheduling problem, not an inspection one.

## Next Steps

- [Supply Overview](../workflows/supply/overview.md) — the full reference
- [Shipping](shipping.md) — the other direction
- [Locations & Cycle Counts](../workflows/supply/locations.md)
