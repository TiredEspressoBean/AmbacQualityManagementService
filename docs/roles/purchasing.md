# Purchasing

**The buyer's seat.** You own supplier relationships, what the shop is waiting
on, and the sourcing facts the requirements report nets against.

!!! warning "Purchase orders stay in your ERP"
    uqmes is not a purchasing system. It does not hold POs, prices, quotes or
    approvals to spend. What it holds is **what you are expecting, from whom, and
    when** — and what is waiting on it.

    Where a decision needs a price, uqmes produces the **scope** — what work,
    what parts, and the finding behind each — and records the answer. The money
    happens where the money lives.

## What you own

| Thing | Where |
|-------|-------|
| **Expected deliveries** — what's on order, from whom, when | [Supply](../workflows/supply/overview.md#loading-what-is-on-order) |
| **Supplier qualification** — raising it | [Supplier Quality](../workflows/supply/overview.md#supplier-quality) |
| **Approved suppliers** | [Approved Suppliers](../workflows/supply/overview.md#approved-suppliers) |
| **Part approvals** | [Part Approvals](../workflows/supply/part-approvals.md) |
| **Sourcing facts** — lead time, preferred supplier, safety stock | The material or part type record |
| **Supplier companies and contacts** | [Companies](../admin/setup/companies.md) |

## Sourcing facts are planning inputs

Lead time, preferred supplier and safety stock aren't filing — they are what the
requirements report nets against. A wrong lead time produces a buy
recommendation at the wrong moment, every time, quietly.

!!! note "You own a bought part's sourcing, not its definition"
    You can change where a part comes from and how long it takes. The part's
    **definition** — what it is, its drawing, its specs — stays with
    [Engineering](engineering.md). Two different questions about the same record.

## Chasing what's late

The **Late deliveries** card on Home names the item, quantity, supplier and
PO/line, with a lateness badge — and, more usefully, **which work orders it is
holding up**. Each row carries the supplier's deliveries contact and their email,
so chasing it doesn't start with looking someone up.

!!! note "\"Holding up\" is read from the production BOM"
    It means *this work needs that item*, not *this lot was earmarked for it*.
    Read it as "who is waiting on this", not as an allocation.

**The card is absent when nothing is late.** Empty space is good news.

You also get **Supplier qualifications expiring** — the other thing that bites
quietly.

See [Chasing a late delivery](../workflows/supply/overview.md#chasing-a-late-delivery)
and [Cancelling something you are no longer
expecting](../workflows/supply/overview.md#cancelling-something-you-are-no-longer-expecting).

## When a supplier sends you something wrong

A **SCAR is a CAPA against a supplier**, and you can raise one from the rejected
lot. That is the formal route — it creates a record the supplier is answerable
to, rather than a phone call nobody can find later.

See [Rejecting](../workflows/supply/overview.md#rejecting) and [Sending it
back](../workflows/supply/overview.md#sending-it-back).

!!! warning "You raise supplier quality problems; QA settles them"
    **Approving** a supplier qualification is QA's, not yours — separation of
    duties. So is rejecting a whole lot and approving a disposition. You can see
    all of it and start all of it.

## Purchasing or Receiving?

They are different jobs and uqmes separates them, though one person often holds
both.

| | Purchasing | [Receiving](receiving.md) |
|---|-----------|---------------------------|
| **Owns** | The supplier relationship and the order | The physical delivery |
| **Does** | Places it, chases it, qualifies the supplier | Takes it in, inspects it, puts it away |

## What you don't hold

**No authoring** — processes, BOMs and specs aren't yours. **No deletes** —
retention is manager tier. **No shop-floor supervisor grants** — FPI sign-off,
training overrides and shift notes belong to [Shift Lead](shift-lead.md).

## If you got something wrong

An expected delivery keyed with the wrong quantity or date is cancelled with
**Cancel expected receipt…** (a reason is required) and added again. Don't use
**Chase…** to correct it: a chase records what the supplier said. A wrong lead time
or preferred supplier is simply edited again. See [Putting a Mistake
Right](../workflows/fixing-mistakes.md#receiving-and-stock).

## Next Steps

- [Supply](../workflows/supply/overview.md) — the full reference
- [Receiving](receiving.md) — the dock
- [Part Approvals](../workflows/supply/part-approvals.md)
- [Companies](../admin/setup/companies.md) — suppliers and their contacts
- [CAPA Overview](../workflows/capa/overview.md) — what a SCAR becomes
