# NCRs

An **NCR** (non-conformance report) records one nonconformance: what's wrong,
how serious it is, where it was found and how it was contained. It covers the
parts the nonconformance affects, one or many, and each part gets its **own
decision** (its [disposition](dispositions.md)) under the NCR.

So an NCR answers *what is wrong*, and its dispositions answer *what we decided
for each part*. The failed [inspection records](quality-reports.md) behind it
are the evidence: one per part, or one for a failed batch cycle.

**Quality** > **NCRs** (`/quality/ncrs`).

## How an NCR opens

**Every failure belongs to an NCR.** You don't have to raise one for a failed
inspection: it opens on its own.

| What failed | The NCR |
|-------------|---------|
| An inspection record saved as **Fail**, an out-of-spec reading at a step that holds on it, a failed sample | One NCR for the part. Its severity starts at the worst defect recorded, or Major when none is |
| A batch cycle (wash, heat-treat, plating) | One NCR over the load: every part in it, each with its own decision |
| A first piece of several parts failed | One NCR over the failed pieces |
| A rejected outside-process return | One NCR, with a decision for each part it carried |
| A received lot rejected, or its remainder rejected | One NCR for the lot. Rejecting the remainder of an already-accepted lot always opens a new NCR |

**A part that fails again joins its open NCR**, as long as its own decision on
that NCR is still open. Once its decision there is done, a new failure opens a
new NCR.

Parts are only grouped where the event is one: a load, a first-piece run, or
parts you put together yourself. The system never guesses that two failures
belong together.

## Raising an NCR by hand

To put several parts on one NCR (the same burr on 8 of 50 bodies, say), raise
it yourself:

1. **Quality** > **NCRs** > **Raise NCR**, or select the parts on **WO Control**
   and press **Raise NCR** in the bulk toolbar (it opens with them filled in)
2. Choose the parts and say **What's wrong** (*e.g. Bores oversize from grinder
   setup 2 — 4.007 against 4.005 max*)
3. Under **Defects found**, **+ Add defect** for what was found: error type,
   severity, location, count, notes. The same defects go on every part's record
   (a finding on one part alone can be added on the NCR afterwards). They're what
   puts the NCR in defect analysis
4. **Severity**: *Critical - Safety/Regulatory Impact*, *Major - Functional
   Impact* or *Minor - Cosmetic Only*. It follows the worst defect you entered
   until you pick one yourself
5. **Raise NCR** (with several parts, **Raise NCR over N parts**). *NCR raised*

*"Each part gets a failed inspection record saying what's wrong and waits for its
own decision under this NCR. Parts still here are held; shipped/completed ones
are recorded."* A description is required: *"Say what is wrong — it's the NCR's
description."* The parts picker shows each part's status, work order, and any open
NCR it's already on (*INJ-0042-001 · Shipped · WO-2024-0042-A · on NCR-…*).
Raising needs `add_ncr`; without it the page says so.

**An escape** (a customer complaint, or a problem found after delivery) goes on an
NCR the same way. A shipped part isn't held, since it isn't here; its row reads
*Already shipped*, and its decision is kept as the record of what was decided.

To add parts to an open NCR, **Add parts** on its page, with **Why these parts**
(*e.g. Same grinder setup*), and any **Defects found** (the same go on every
added part's record). Each added part is held and gets its own failed
inspection record. A part already on it is refused (*"Already on
NCR-2026-000001: INJ-OPS-002."*), and so is a part on another open NCR, so it
isn't recorded twice: *"&lt;serial&gt; is on NCR-…: combine instead."* A closed NCR
takes no more: *"NCR-… is closed — raise a new NCR for these parts."*

## Combining NCRs

When several NCRs turn out to be the same nonconformance (eight failures logged
separately, then recognised as one grinder setup), combine them. On the NCR list,
tick the open NCRs (*Select at least two NCRs to combine.*) and **Combine into one
NCR**:

*"The others' decisions and inspection records move under the one you keep, and
each of them closes as combined into it. The one you keep keeps what's wrong; its
severity becomes the group's highest, and the others' containment is added to its
own."*

Choose which to **Keep** (the oldest is preselected) and **Combine into NCR-…**:
*NCRs combined*. Each other NCR closes, reading *Combined into NCR-…*; its parts
and its CAPA decision now belong to the one you kept, which reads *Combined from
NCR-…*. Their containment is added as *From NCR-… (&lt;name&gt;, &lt;date&gt;):
…*. Only open NCRs can be combined. Combining needs `change_ncr`.

## The NCR list

**Open** (the default), **Mine** (the NCRs you own), **Awaiting CAPA decision**
and **All**. Each row shows the NCR number, what it **Covers** (a serial, *N
parts*, or *Lot X*), what's wrong, severity, state, how many parts are
**Awaiting decision**, where it was found and when it opened. Filter by state,
severity or CAPA decision. A date filter (from Home's *NCRs open > 7 days*, say)
shows as a chip, *Opened before &lt;date&gt;*, with **✕** to clear it.

## Owning an NCR

Every NCR has an **owner**, the QA person who sees it through: its decisions,
its containment, its CAPA decision, and closing it. An NCR raised by hand by
someone from QA or a lead is theirs from the start. One a failure opened, or one
an operator raised, waits unowned in the queue: **NCRs to take** on Home and the QA home, one row per NCR
(*NCR-… · INJ-… / 3 parts / Lot … · WO-… · Major · what's wrong*).

**Take it** makes it yours: *"NCR-… is &lt;your name&gt;'s — with its decisions."* All its
decisions not yet closed go with it, and a part added to it later, or failing
into it, is yours too. On the NCR's **Owner** card, **Reassign** gives it to
someone else, or **Back to the queue** (*"NCR-… is back in the queue."*). Taking
or assigning needs `change_quarantinedisposition`.

**My NCRs** on Home lists what you own, each with what it still needs: *N to
decide*, *Containment needed*, *CAPA call needed*, *N to close*. Combining NCRs
keeps the kept NCR's owner (or one of the others' if it had none) and moves
everything to them.

## An NCR's page

### Parts and decisions

One row per part (or lot): its status, its disposition, the decision and its
state. A part still to be decided reads *Awaiting decision*. A part of a failed
load that had already moved past the step reads *Already past the step* under
its serial. It still gets a decision, kept as a record (its notes start
*"Already past the step when its load failed — decided for the record."*), so
the NCR can close.

**Decide all waiting (N)**, or tick rows and **Decide N chosen**: only the ones
you chose are decided. The decision (*Rework*, *Repair (AS9100)*, *Scrap*, *Use
As Is*, *Return to Supplier*, *Not a nonconformance (result voided)*) goes on each
part's own disposition, with you, or a co-signer, as who authorised it.
- *Use As Is* and *Repair* need a **Concession reference**; the button stays
  disabled until it's entered. **Concession date** is today if left blank.
- *Scrap* asks you to confirm first (*Scrap N parts?*), because the parts are
  scrapped as soon as it's saved.
- *Not a nonconformance* is for a finding withdrawn in error. It follows the
  same rules as on a [disposition](dispositions.md#when-the-finding-was-wrong-not-a-nonconformance):
  each result must have been voided and re-inspected as a pass.

Without `approve_disposition`, the button reads **Co-sign and record**: an
authorised colleague enters their email and password at your screen and confirms
*I authorize this disposition decision*. *Decision recorded*.

To change one part's decision afterwards, open its disposition: *"Everything on
NCR-… already has a decision; change a part's decision on its own
disposition."* Where each decision sends the part is on
[Dispositions](dispositions.md#what-the-decision-does-to-the-part).

### What's wrong

The description and severity, editable by a lead or QA (`change_ncr`).

**Severity** follows the worst defect recorded on the NCR's inspection records
as they come in, up or down, until anything on the NCR is decided. Until then a
lead or QA can also set it either way, since it's still being judged; once they
write the description or severity, it stops following the defects. After the
first decision it can only be **raised**: *"Decided at this severity: it can be
raised, not lowered."* A lowering is refused: *"NCR-… is Major; its severity may
only be raised."*

### Containment

*"The immediate action taken to prevent escape — once, for everything this NCR
covers."* Describe it, say who performed it under **Performed by (if not you)**,
and **Record containment**. Its page then reads *Recorded by &lt;name&gt; on
&lt;date&gt;*. Photos or segregation tags as evidence go in the
[Documents](#documents) card.

When missing containment is what stops decisions closing, the card is marked in
red: *"Record containment before these decisions can close."* A receiving lot
reject records containment by itself (*"Lot rejected and held at receiving: …"*),
stamped with who rejected it.

!!! important "Critical and Major NCRs need containment before a decision closes"
    No decision under a Critical or Major NCR can be closed until containment is
    recorded: *"Cannot complete disposition: Containment action required on
    NCR-… before closing a decision on a CRITICAL/MAJOR nonconformance"*.
    Marking containment complete needs its description first (*"Describe the
    containment action before marking it complete."*), and a closed NCR can't
    be edited.

#### Correcting containment

Recorded containment isn't edited: it's corrected, with a reason. While the NCR
is open, **Correct containment** (for leads and QA, who record it) opens
*Correct containment on NCR-…*: *"Recorded by &lt;name&gt;; that stays. The
correction is stamped with your name, the date and your reason, and the original
wording stays on the NCR."* Change the **Containment action** or **Performed by
(if not the recorder)**, say **Why it's corrected** (*e.g. Recorded the wrong
rack; the parts were moved to MRB*), and **Save correction**: *Containment
corrected*.

The card then shows the current wording with *Corrected by &lt;name&gt; on
&lt;date&gt;: &lt;reason&gt;*, and *Originally: …*. A later correction keeps the
first wording as the original; the audit log holds every step between. The
containment a lot reject records by itself is corrected the same way.

It's refused without a reason (*"Say why it's corrected — the reason is what an
auditor reads."*), with nothing changed, and on a closed NCR (*"NCR-… is closed,
so its containment stands as recorded."*). Every other way of changing recorded
containment is refused: *"Containment on NCR-… is recorded. Change it with
Correct containment, which keeps the original and says why."*

### Where it was found

The work order and step, set by the system and not editable; *Failed batch
load* for a load; who raised it, and when it opened and closed.

### CAPA

*"Whether this nonconformance needs corrective action — decided, not
assumed."* Each NCR carries a CAPA decision:

| Decision | Recorded by |
|----------|-------------|
| **CAPA raised** | Set when a CAPA links the NCR. **Raise CAPA** opens a new CAPA started from the NCR: problem statement, severity, part, work order, step and immediate action filled in from it (*"Raised for NCR-… — started from what it says; change anything that's wrong."*), and the NCR linked when you create it |
| **No CAPA needed** | A person, **with a reason** |
| **Deferred** | A person, **with a reason** |
| *Not decided yet* | Nobody has looked |

ISO 9001 §10.2.1(b) asks that the need for action be **evaluated**. The reason
is required, because it's what an auditor reads. NCRs nobody has decided on are
counted on Home (*Awaiting a CAPA decision*) and listed in the NCR list's view of
that name and on NCR Analysis. Recording the decision, or linking a CAPA to an
NCR or its records, needs `initiate_capa`.

### Inspection records

The failed inspection records behind the NCR: one per part, or, for a failed
batch load, the one record of the failed cycle. Each lists its defects
(*Tool marks (Minor) · Crack ×2 (Critical)*), or *No defects recorded.*

**Add a defect** records a finding made after the inspection, at MRB review
say, on that record: *"A finding made after the inspection. Until something on
NCR-… is decided, its severity follows the worst defect."* **Record defect(s)**:
*Defect recorded*. It's offered while the NCR is open and the record hasn't
been withdrawn, to QA and leads (`change_ncr`).

### Documents

*"Evidence for this NCR: containment photos, segregation tags, concessions."*
**View or attach documents** lists everything filed under the NCR, containment
evidence included, and attaches more (with `add_documents`; otherwise it's
read-only). A document can also be linked to an NCR from the document form's
**Link to** list. See [Uploading](../documents/uploading.md#linking-during-upload).

## When an NCR closes

**When every decision under it is closed.** *"This NCR is closed: every decision
under it has been carried out."*

Close the decisions from the NCR itself: **Close decided (N)** closes every
decided one in one go (with `close_disposition`). It's all or nothing: if any
can't close yet, none does, and the refusal lists what each still needs (*"None
closed — INJ-…: Cannot complete disposition: Containment action required on
NCR-… …"*). Clear those and press it again. A whole-lot reject still waiting for
confirmation isn't counted as decided.

Arriving on an NCR from one of its dispositions, the back button reads **Back to
DISP-…**.

An NCR where nothing was decided also closes once none of its inspection records
still fails: a receiving sample re-recorded within its accept number, for
example.

## Printing and tags

**NCR Report** prints the *Non-Conformance Report*: the header, the inspection
records, containment, a table of each part's decision, and closure. Printing
from a disposition prints its NCR. A part's **hold tag** carries the NCR number
and description.

## Notifications

One notification per NCR, when it opens, to the QA Manager group by default:
*[MAJOR] NCR-2026-000001 on &lt;part&gt;*, where the part is a serial, *N parts*
or *Lot X*. A rule can route on `payload.severity` (e.g. `== "CRITICAL"`), and
also offers the NCR number and part count. See [Notification
Rules](../../admin/setup/notification-rules.md).

## Permissions

| Action | Permission | Held by default |
|--------|------------|-----------------|
| See NCRs and print them | `view_ncr` | All staff |
| Raise an NCR, add parts to one | `add_ncr` | Everyone who can flag a problem, operators included |
| Edit what's wrong, record containment | `change_ncr` | QA Inspector, QA Manager, Shift Lead, Production Manager, Tenant Admin |
| Decide parts | `approve_disposition` | As for dispositions; co-signable |
| The CAPA decision | `initiate_capa` | As for CAPAs |

Where it was found isn't editable by anyone. Editing a disposition can't change
its NCR's header either: *"What's wrong on NCR-… — its description, severity and
containment — is edited by a lead or QA."*

## Next Steps

- [Dispositions](dispositions.md) - Each part's decision
- [Inspection Records](quality-reports.md) - The evidence behind an NCR
- [CAPA Overview](../capa/overview.md) - Corrective action
