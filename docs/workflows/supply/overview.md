# Supply

The **Supply** section covers everything inbound: material you buy, parts you
send out to subcontract vendors, and the suppliers behind both.

!!! info "Where to find it"
    **Supply** in the sidebar. It's collapsed by default — click the section
    header to expand it.

## The surfaces

| Page | Covers |
|------|--------|
| **Incoming Inspection** | The queue of everything awaiting inbound inspection |
| **[Outside Processing](outside-processing.md)** | Parts out at subcontract vendors |
| **Materials** | Material lots, by lifecycle status |
| **Receiving Inspection Plans** | What inspection to perform on receipt |
| **Supplier Quality** | Supplier scorecards |
| **Receiving Metrics** | How the dock itself is performing |
| **Approved Suppliers** | Supplier qualifications |
| **[Part Approvals](part-approvals.md)** | PPAP / FAI approvals per part type and supplier |

## Materials

The **Materials** page is the material lot hub, segmented by where each lot is
in its life:

| Segment | Meaning |
|---------|---------|
| **On order** | Expected, not yet arrived |
| **Late** | Expected receipts overdue, or due within 3 days |
| **Awaiting inspection** | Received, not yet inspected |
| **On hand** | Inspected and available |
| **Held** | Quarantined or otherwise not usable |
| **Rejected** | Rejected, awaiting return or already **Returned** |

An **All** tab shows everything regardless of state.

**Late** counts on the plant's own day, and its badge turns **red** when anything
is actually overdue. On the **On order** and **Late** tabs the Promised column
carries a red **Overdue** or amber **Due soon** badge, so you can see which is
which without reading dates.

| Reads | Means |
|-------|-------|
| **Overdue** | Past the promised date |
| **Due soon** | Within 3 days, today included |

Actions: **Add expected delivery** for one you know is coming, **Receive** one
that has arrived,
and **Inspect** one that's waiting. Lots import and export as CSV or Excel.

### Loading what is on order

Both tabs show a **PO** column — purchase-order number and line — and **Import
expected deliveries** on the toolbar loads them in bulk. The dialog of the same
name reads your ERP's **open PO lines**, taking a `.csv` or `.xlsx` with **PO
Number**, **PO Line**, **Item** (part number or name), **Open Quantity** (what is
still to come), **Promised Date**, and optionally **Supplier** and **Unit**. A
template downloads from the dialog.

!!! important "This records what is coming; it does not manage purchase orders"
    UQMES does not own purchasing, and importing here creates no purchase order.
    What it creates is **expected receipts** — the same objects **Add expected
    delivery** makes one at a time — each carrying its PO number and line as a
    *reference back* to the system that does own the order.

    The consequences follow from that, and they are the ones to remember:

    - **Nothing is ever closed by being left off the sheet.** A line you omit
      stays as it was. Closing short is a decision made [at
      receiving](#a-short-delivery-is-a-decision-not-an-assumption), by whoever
      is holding the packing slip.
    - **A line you already received, that the sheet still shows open, is
      expected again.** It comes back marked *Expected again* with a note,
      rather than being refused. The PO line belongs to the ERP and uqmes
      mirrors it — if your purchasing system still has quantity open on that
      line, that is the answer uqmes takes.

Rows are matched on **PO number + line**, so re-uploading the same sheet updates
quantity and promised date rather than duplicating. That makes a daily or weekly
export from the purchasing system safe to re-import as it changes.

Bad rows are listed with the reason and the rest still import.

!!! tip "Adding one by hand takes a line too"
    The PO reference there is two boxes — **PO number** and **Line** — so a
    manually expected receipt keys the same way an imported one does.

### Material or part

A lot can be either. The picker on batch receiving
(`/production/material-lots/receive`) and in **Add an expected delivery** is grouped
**Materials / Part types**, and searches both — so a **bought part** is expected
and received exactly like raw material. Pasted names match either kind, and
choosing one fills in its preferred supplier.

### A short delivery is a decision, not an assumption

When fewer arrive than were on order, **Receive expected lot** asks:

> N fewer than the M on order. What does the packing slip say?

You must answer one of two:

| Answer | What happens |
|--------|--------------|
| **More coming** | The remainder stays on order as a **new expected lot**, keeping the supplier, PO number and promised date |
| **That's all** | Nothing more is expected on this line |

The receipt is refused until you pick — *"say whether more is coming
(back-ordered) or that's all (closed)"*.

!!! important "Why you are asked rather than told"
    Closing an order short is never inferred. UQMES doesn't own purchasing, so it
    has no way to know whether a supplier is still sending the rest — but the
    clerk holding the packing slip does.

    *That's all* records that nothing further is expected **here**. It does not
    close the PO line — the dialog says so, and that is done in the ERP.

    This matters beyond tidiness: **More coming** keeps the remainder visible to
    planning as incoming supply. Answer *That's all* on a delivery that is
    actually part-shipped and the material lane stops expecting stock the
    supplier still intends to send.

!!! tip "Safety stock lives on the material"
    The **Material** form carries a **Safety stock** field. It is the buffer
    deducted from on-hand when the planning views work out free stock — see
    [How the numbers are made](../scheduling/how-the-numbers-are-made.md), which
    explains why the material lane can go red while there is stock on the shelf.

### Chasing a late delivery

**Chase…** appears on the Home *Late deliveries* card and on on-order rows. It
records **what the supplier said**, optionally a **new promised date**, and opens
a **pre-filled email** to that supplier's expediting contact — see [Outside
contacts](../../admin/setup/companies.md#outside-contacts).

!!! important "The first promise is the one you are judged against"
    A new date updates what you are waiting for, but **supplier on-time
    performance is measured against the original promise**, and rows show *first
    promised …*.

    Otherwise a supplier could be perpetually on time by moving the date, and the
    scorecard would measure their diary rather than their delivery.

### Cancelling something you are no longer expecting

An expected receipt that is never going to arrive can be cancelled. On **On
order** and **Late** rows, the **⋯** menu offers **Cancel expected receipt…**,
which asks for a **reason**. The import results also put a **Cancel** button on
*Expected again* rows, so you can deal with one as you meet it.

A cancelled lot reads **Cancelled**: it stops counting as incoming supply and
drops out of Late deliveries.

!!! note "Cancelling a back-ordered remainder settles the original delivery"
    If the remainder came from a short delivery you answered *More coming*,
    cancelling it makes that delivery read **That's all** — the two are the same
    decision arrived at later.

!!! important "The ERP still gets the last word"
    If your purchasing system continues to show the line open, the **next import
    expects it again** — and says *"was cancelled on <date> by <name>"* so you
    know why it came back rather than thinking the cancel failed.

    Cancelling here is a statement about *your* expectation. Closing the line is
    done in the ERP.

### Handing receipts to the ERP

**Receipts for ERP** on the Materials page opens a dialog: pick a **date range**,
optionally **only deliveries received against a PO**, and download an `.xlsx`
with one row per delivery.

Each row carries **PO / line**, received date, item, supplier, **our lot and
theirs**, ordered, received, accepted, rejected, awaiting decision, whether it
was a short delivery, the decision, and an **ERP Status** — explained on the
sheet's own About tab.

### Keeping track of what you have posted

The dialog counts the range before you download: **N ready to post**, **N
awaiting a decision**, **N changed since posted**. **Leave out what's already
posted** is on by default.

After **Download**, a **Mark N as posted** button appears — only deliveries with a
**final decision** can be marked, since a delivery still under inspection has no
settled quantity to post.

!!! important "A posted delivery can come back"
    If its numbers move afterwards — a later reject, a recount — it reappears as
    **Changed since posted**. That is the point: the ERP holds a figure that is
    now wrong, and nothing else would tell you.

    So *Mark as posted* is a record of what you handed over, not a promise it
    stays true.

!!! important "No prices — this is a goods receipt, not an invoice"
    The export exists so goods receipts can be posted in the ERP (Glovia here)
    without re-keying them off paperwork. It says **what arrived and what you
    decided about it**; what that is worth is the ERP's business.

    It is the mirror of [Import expected
    deliveries](#loading-what-is-on-order): the ERP tells uqmes what is coming,
    uqmes tells the ERP what landed.

!!! tip "Deep links to a tab"
    The Materials page opens on a tab from the URL, which is what the **All** link
    on the Home *Late deliveries* card uses:

    `?tab=` **onorder** · **late** · **awaiting** · **onhand** · **held** ·
    **rejected** · **all**

    The values are not all guessable from the tab labels — *onorder* and *onhand*
    have no hyphen, and *awaiting* is short for Awaiting inspection. An
    unrecognised value is ignored rather than erroring, so a wrong guess looks
    like the link silently not working.

### Working a row

Each row carries **one primary button** for whatever that lot is waiting on —
**Receive** on order, **Inspect** awaiting inspection, **Resolve** when held —
with everything else under **⋯**:

| Action | |
|--------|---|
| **Print label** | One 4"×2" thermal label |
| **Print label (Letter sheet)** | A sheet of ten (Avery 5163 / 8163) |
| **Adjust quantity…** | Correct what is actually on the shelf |
| **Extend shelf life…** | When shelf life applies |

Status badges read as words — *Awaiting inspection*, *Held* — and the **Qty**
column shows *left of total* once stock has been drawn or adjusted.

Search finds a lot by **item, part number, supplier, PO or heat number**, not
just by lot number.

!!! note "An over-receipt keeps what was ordered"
    Receive more than the line said and the lot records both: the page reads
    *Ordered 100 · 10 over*. The ordered figure is evidence about the order, so
    it is not overwritten by what turned up.

### What cannot be edited directly

**Status** is not an editable field, and **quantity** changes only through
**Adjust quantity**. Both follow from what happens to the lot — a receipt, an
inspection decision, a draw, a correction — so setting either by hand would make
the record disagree with its own history.

Counting a lot down to **0** makes it **Consumed**.

### Adjusting a quantity

**Adjust quantity** asks for **On hand now** and a **required reason**, then sets
what is left on the lot and records both.

!!! warning "Adjust the system that owns stock too"
    A correction here fixes what UQMES believes is on the shelf. It does not
    reach your ERP, and the dialog says so — an adjustment made in one place and
    not the other is how the two drift apart.

### Lot labels

Labels print from the row menu, or from the **Print labels** action on the toast
after a batch receipt, which covers every lot just created.

A label carries the item and part number, **LOT number with a barcode**, a **QR
code to the lot**, supplier and supplier lot, quantity (as *3 boxes* when counted
that way), heat number, received date, use-by date, company name and print date.

!!! note "A label never shows status"
    Deliberately. Status changes — received, inspected, held, drawn down — and a
    printed label cannot. Anything that would go stale on a shelf is left off, so
    a label is never contradicted by the record it points at. Scan the QR for the
    live picture.

See [Material Lot Tracking](../tracking/lot-tracking.md) for the underlying
concepts.

## Customer property

Material a customer sends in for their own job — a free-issue kit, their castings
to machine — is **customer property** (ISO 9001 §8.5.3). It is in your building
and it is not yours.

Batch receive carries a **Customer's own** column: *— ours*, or the customer it
belongs to.

### What changes when a lot has an owner

**It is not a purchase, so the supplier gates do not apply.** It skips the
supplier-qualification and part-approval holds, and it stays out of the supplier
scorecard — judging a supplier on material you were given would be meaningless.

**The quality gates still do.** Inspection, shelf life and paperwork holds apply
exactly as they would to your own stock. You still have to know it is fit to use.

**It is ringfenced to its owner:**

| | |
|---|---|
| **Consumption** | Only that customer's work orders may draw it — and it is used **before** your own stock |
| **Planning** | In Requirements it covers only that customer's demand. Another customer's stock never reduces a shortage |

!!! important "One customer's material never covers another's shortage"
    This is the rule that makes the feature safe. If free-issue stock counted as
    general supply, planning would quietly promise one customer's material to
    another customer's order, and the shortage you were relying on seeing would
    disappear.

    So a shortage that looks wrong on a part you plainly have stock of is worth
    checking against ownership before anything else.

### It is labelled as theirs

- The lot label prints **CUSTOMER PROPERTY — <customer>**
- Materials shows a **<customer>'s** badge
- The lot page says *"Customer property — X. Only their work may use it."*

!!! note "Why it is on the label and not just the screen"
    The obligation under §8.5.3 is to identify, protect and safeguard it. A
    printed label travels with the material to the shelf and the bench, where the
    decision to pick it up actually gets made.

## What an item requires on arrival

**Material** and **Part Type** forms carry a **Receiving** section — on a part
type only when **Purchased** is ticked. Everything in it is **off by default**,
and with nothing set receiving simply books lots in.

| Setting | Effect |
|---------|--------|
| **Bought and counted by** | The stock unit, or **Box** / **Pound (weighed)**, with *EA per box* or *EA per pound* when it converts |
| **Requires a certificate of conformance** | Every lot is **held** until the CoC is uploaded |
| **Requires a heat number** | Every lot is **held** until one is entered |

!!! tip "Set these once, on the item, not per delivery"
    This is where a paperwork rule belongs: it applies to every lot of that item
    from then on, rather than relying on a clerk remembering which parts need a
    cert.

### Counting in what you buy by the box

When an item is bought by the box or pound and has a conversion, receiving offers
a toggle: enter the **stock unit**, or **Boxes** / **Weigh**. Type the number of
boxes or the scale reading, and the dialog shows the arithmetic — *= N EA at X
per box* — so you can check it before committing.

Batch receiving has the same thing as a **Count in** column (Units / Boxes /
Pounds), and **Qty** then means whatever you chose.

### Lot numbers are issued here

uqmes numbers each receipt itself — **LOT-<year>-00001**. The supplier's own
number goes in **Supplier lot number**, which is **optional**: you record it when
they give you one, and nothing waits on them.

In the batch grid, **Lot #** can be left blank and one is assigned. Type a number
that clashes with an existing lot and the receipt is refused with a message.

!!! note "Two lot numbers, and they answer different questions"
    **Ours** identifies the receipt in this system, and always exists.
    **Theirs** is how the supplier refers to the same material — needed for a
    SCAR, a return or a traceability enquiry back to them.

    Both print on the label and appear on the RTV sheet and inspection record.

### Heat number and where it came from

**Receive expected lot** and batch receiving both take:

- **Heat number**, marked *(required)* when the item demands one. Leaving it
  blank holds the lot rather than refusing the receipt — the material is on the
  dock either way.
- **A photo or PDF of the CoC**, taken at receipt. Attaching it **clears an
  Awaiting-CoC hold automatically**, so the certificate and the material arrive
  together.
- **Source (from the paperwork, if shown)** — Manufacturer, Authorized
  distributor, or Independent distributor.

Heat # is the 9th column in the batch paste order.

## Incoming Inspection

**Everything awaiting inbound inspection — purchased material and parts back
from a subcontract vendor — in one queue.**

This is deliberately one queue rather than two. Purchased material and returning
subcontract work both need the same thing on arrival, so **Inspect** opens the
same runtime for both. Filter by source or status to narrow it.

!!! tip "QA Inspectors get this on their Home page"
    If you're a QA Inspector, incoming work already appears on your Home queue,
    segmented into Receiving, OSP returns, and In-process. See the
    [QA Inspector Guide](../../roles/qa-inspector.md).

### Rejecting

The reject dialog asks two things.

**What happens to it?** — **Return to supplier** or **Scrap**. Those are the only
two, deliberately: *use as is* is a concession somebody approves on the
disposition afterwards, not a choice at the bench, and rework is not something
you do to bought stock.

**Which pieces?**

| Choice | What happens |
|--------|--------------|
| **Some of them** (default) | You enter how many are bad. Those pieces **split into their own rejected lot** — numbered `-01`, `-02` … and carrying the heat number, source, PO and CoC — with a disposition for that quantity in pieces. **The rest of the lot is accepted.** |
| **Reject whole lot** | The entire lot goes back. Needs permission — see below |

The reject and its disposition are created **together**, in one step.

!!! note "Rejecting part of a delivery is the normal case"
    The default assumes a delivery is mostly good, because it usually is. The
    split lot keeps the bad pieces identifiable and traceable without holding up
    the ones you can use.

#### Who can reject a whole lot

Sending an entire delivery back is a bigger call than quarantining some of it, so
it sits behind **Can reject a whole lot back to the vendor**
(`reject_whole_lot`). **QA Manager** and **Tenant Admin** hold it by default, and
a company can grant it to its inspectors' group.

Without it the button reads **Request whole-lot reject**, and the dialog says so.
The lot is then held as *Whole-lot reject requested*, waiting on QA — the request
is recorded, not refused.

Someone holding the permission then either:

- **Confirm: reject whole lot** — on the hold panel; or
- **Decline request…** — *"Why is the whole-lot reject being declined?"*, then
  **Decline — back to inspection**. The pending disposition closes and the lot
  returns to inspection, where a partial reject can be done instead.

!!! note "This panel says Decline, not Release"
    Every other hold offers *Release hold…*, which waives a check and lets the
    lot through. This one turns a request down, so it is labelled for what it
    does.

A permission holder can also escalate later: **Reject remaining stock…** at the bottom of the
Materials row menu, in red, rejects the **unconsumed remainder** of an accepted lot, with
a reason and a destination. Anything already used is not reversed.

### Sending it back

A rejected lot waiting to go back shows **Ship back**. The dialog offers **Print
RTV sheet**, carrier and tracking, the **supplier's RMA number** (printed on the
RTV sheet), and **Mark shipped back**.

It also asks whether **the supplier is sending replacements**, with a date. Say
yes and an **expected delivery is created, linked to the returned lot** — so the
replacement is visible to planning as incoming supply instead of being something
someone has to remember.

The lot page then shows **Replacement for / Replaced by / Supplier RMA /
Shipped**, which is the whole round trip on one record.

The lot then becomes **Returned**.

!!! important "Returned is not Scrapped"
    The goods exist — they are at the vendor. A returned lot has no stock left
    and counts as neither stock nor incoming supply for planning, but it is not
    destroyed, and its record stays live for the credit conversation.

    Scrapped means gone. Returned means somewhere else.

The **Rejected** tab on Materials holds lots in this state, and the **⋯** menu
carries **RTV sheet (PDF)** for lots waiting to go back or already returned.

### What a disposition does to the lot

| Disposition | The lot becomes |
|-------------|-----------------|
| **Scrap** | **Scrapped** — nothing left in stock |
| **Use as is** (with its approval reference) | **Accepted** |
| **Return to supplier** | Waits for **Ship back**, then **Returned** |

!!! note "Rework and repair are not offered on a material lot"
    You cannot rework bought stock into conformance — it either serves, goes
    back, or is scrapped. Completing a return-to-supplier disposition ships the
    lot back.

### The inspection record

Every inspected lot can produce a **Receiving Inspection Record** PDF — the
evidence that it was released, with the sampling, the measurements, the checklist
answers and who decided. **Record** in the inspection page header, or **Inspection
record (PDF)** in the Materials row menu.

See [Compliance Reports](../../compliance/reports.md#receiving-inspection-record).

### Held at receiving

A held lot shows an amber **Held at receiving** panel on its inspection page.

!!! important "A lot can be held for several reasons at once"
    Awaiting CoC *and* Awaiting heat number *and* Unqualified supplier is a
    normal state, not a confused one. Each hold gets **its own card and its own
    release**, clears independently, and **the lot moves on when the last one
    goes**.

    So clearing one and seeing the lot stay put is the system working. Look for
    the next card.

| Hold | How it clears |
|------|---------------|
| **Awaiting CoC** | Upload the certificate — including the photo or PDF taken at receipt |
| **Awaiting heat number** | Enter it in the inline box and Save |
| **Shelf life expired** | Extend the shelf life, or reject the lot |
| **Unqualified supplier** | A quality manager releases it |
| **Unapproved part** | A quality manager releases it |
| **Held by a quality gate** | A quality rule stopped the lot rather than a missing document |
| **Whole-lot reject requested** | Someone confirms or declines — see [Who can reject a whole lot](#who-can-reject-a-whole-lot) |

**The first three clear themselves.** You are not asking permission, you are
supplying what was needed.

**The next two are judgements.** They offer **Release hold…**, with a **required
reason**, to someone holding the disposition-approval permission. The lot then
continues with **that one check waived** — any other hold still applies. Anyone
without the permission sees: *"A quality manager can release this hold, or the
lot can be rejected."*

!!! note "Holds used to be a dead end"
    A held lot could once only be **rejected**; nothing released it. A delivery
    missing its cert had to be sent back rather than held until the paperwork
    caught up.

    The split is the point: **paperwork clears itself, judgements need
    authority.** Waiting on a document is not the same as deciding a supplier is
    acceptable.

## Receiving Inspection Plans

A receiving inspection plan defines what to check when a lot arrives. Plans are
built from substeps, the same way work instructions are — see
[Authoring Work Instructions](../dwi/authoring.md).

Create with **New Plan**, then **Configure** to build the plan's substeps. The
dialog's one **Material or part** picker covers both: *a bought part, or a raw
material such as bar stock or seals*. The list's **Inspects** column names
whichever it is, with a small **material** tag on raw stock.

!!! important "No plan means no inspection"
    A lot is inspected **only when its item has a plan**. Without one it goes
    straight to stock — dock-to-stock — exactly as before.

    That is the control: you decide what gets inspected by deciding what gets a
    plan. Open an inspection for an item with none and the page tells you so,
    rather than presenting an empty checklist.

### Lot-level checks: "Once per lot"

When a plan samples **unit by unit** — measured values, Z1.9 — every substep
normally repeats for each sampled unit. A substep switched to **Once per lot** is
asked on the **first unit only**.

Use it for anything that is true of the delivery rather than of a part: *is the
CoC present and correct?*, *does the paperwork match the label?*

!!! note "It only changes anything on sampling plans"
    Attribute plans (counting defectives) and one-unit checklist plans walk the
    substeps once anyway, so the switch makes no difference there. It is also
    shown on receiving plans only, never on process steps.

### The proportionate check

For most commodity items you do not need measurements. A plan with **sample size
1** and a single checklist substep — *"Is this information correct for this lot
according to the paperwork?"* — is the ISO 9001 **proportionate** verification,
and it is the right default for bought stock you are not measuring.

It still produces a release record, which is the point: *verified* is a decision
somebody made, not an absence of evidence.

## Receiving Metrics

**Supply** > **Receiving Metrics** (`/production/receiving-metrics`), over the
last **30, 60 or 90 days**.

This page is about **your dock**, not your suppliers — *"Supplier performance is
on Supplier Quality."* The question it answers is whether material is moving
through receiving, and where it is stuck.

| Card | |
|------|---|
| **Lots received** | Deliveries in the window |
| **Waiting for a decision** | With *Oldest waiting N days* — amber past **5 days**, and it links straight to Incoming Inspection |
| **Median days to a decision** | Receipt to accepted or rejected |
| **Rejected** | Pieces, lots, and **PPM** |

Below them: **Lots received per day** (one bar per day, empty days included),
**Held now, by reason**, and **Holds released** in the window, by what they were.

### The two clocks, and the gap between them

The median card shows both:

- **Median days to a decision** — from **receipt** to accepted or rejected
- **Inspection itself: N h median** — from the inspection being **opened** to
  decided

!!! tip "The difference between them is queue, not work"
    If the decision takes four days and the inspection takes two hours, inspection
    is not the bottleneck — material is sitting on the dock waiting for someone to
    start. That is a scheduling problem, not an inspection one, and no amount of
    speeding up the check will fix it.

    It is the same distinction the planning pages draw between run time and queue
    time. See [How the numbers are
    made](../scheduling/how-the-numbers-are-made.md#measured-flow-time).

### Two exclusions worth knowing

**Split lots are not deliveries.** A lot split off by a partial reject doesn't
count in *Lots received* — otherwise rejecting material would inflate the number
of deliveries you appear to have taken.

**PPM counts your own, each-counted pieces only.** PPM is pieces rejected per
million received, and it exists to describe **bought** quality — so material a
customer sent you is out, and so is anything not counted in pieces. Parts per
million of a quantity measured in kilograms or metres is not a number.

Those exclusions keep the figure comparable between periods instead of moving
with your mix of free-issue work and bulk stock.

## Supplier Quality

**Receiving-inspection scorecards** per supplier:

| Metric | Shows |
|--------|-------|
| **Lots received** | Volume |
| **Accepted** / **Rejected** | Counts |
| **Reject rate** | Quality performance |
| **CoC compliance** | Whether certificates of conformance arrived |
| **On-time delivery** | Delivery performance |
| **Open SCARs** | Outstanding corrective actions |

Suppliers also show their qualification state — an unqualified supplier is
flagged here as **Not qualified**.

### Qualifying for bulk stock

Parts and raw materials are gated differently, because they are different kinds
of thing:

| | Gate |
|---|---|
| **Bought parts** | Part approval — PPAP or FAI, per part type and supplier |
| **Raw material** | Supplier qualification, by **commodity** |

A part approval approves a *design*. Bulk stock has no design to approve, so
there is nothing for PPAP to attach to — what you are approving is the supplier's
ability to supply that class of material.

Two fields on the **Material** form drive it:

- **Requires a qualified supplier** — holds a lot from a supplier with no active
  qualification covering it.
- **Commodity**, e.g. *Elastomer seals* — matched against commodity-scope
  qualifications, ignoring case.

!!! note "No commodity set means any active qualification will do"
    Leave **Commodity** blank and the check only asks whether the supplier is
    qualified at all. Set it, and the qualification has to name that commodity.

    So you can start with a blanket approved-supplier list and tighten to
    commodities later, on the materials that warrant it.

### Qualifying on a certificate

A qualification can have basis **Certification**, which asks which certificate:
**ISO 9001**, **IATF 16949**, **AS9100**, **Nadcap** or **Other**. One record per
certificate.

!!! tip "Set the expiry to the certificate's own"
    Reminders go out before it lapses, so the expiry date is what turns a
    certificate on the wall into something that chases itself.

## Approved Suppliers

Supplier qualifications, with expiry. The Home page surfaces qualifications that
are expiring or expired, since an expired qualification affects what you're
allowed to receive.

## Next Steps

- **[Outside Processing](outside-processing.md)** - Sending work to vendors
- **[Part Approvals](part-approvals.md)** - PPAP / FAI
