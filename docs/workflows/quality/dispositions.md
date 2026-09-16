# Dispositions

A **disposition** is the recorded decision about what happens to nonconforming
product. It is the controlled act at the centre of ISO 9001 **8.7** and AS9100 —
the record has to say what was decided, on what authority, and why.

**Quality** > **Dispositions**

Dispositions also surface where the nonconformance was found: the work order
**control** page lists open ones under *Exceptions on this WO*, each with an
**Open disposition** button.

## The five decisions

Choosing between these is the judgement the system asks you to make. They are
not interchangeable, and the standard treats them very differently.

| Decision | Use when | Part becomes |
|----------|----------|--------------|
| **Rework** | The part can be brought back to **full** conformance | `REWORK_NEEDED` |
| **Repair** | The part can be made acceptable but will **still deviate** from spec | `REWORK_NEEDED` |
| **Scrap** | The part cannot be used or economically corrected | `SCRAPPED` |
| **Use As Is** | The nonconformance is real but the part is acceptable **as it stands** | `READY_FOR_NEXT_STEP` |
| **Return to Supplier** | The supplier is responsible; return for credit or replacement | `CANCELLED` |

!!! info "Rework vs Repair is the distinction auditors check"
    **Rework** restores full conformance — afterwards the part meets the
    drawing, and nothing is given up. **Repair** leaves a known, accepted
    deviation. They look similar on the floor and are entirely different
    records: repair is a concession against the design, rework is not.

    Choosing *Repair* when you mean *Rework* creates a deviation record against
    a part that doesn't have one. Choosing *Rework* when you mean *Repair*
    hides one that does.

Rework and Repair both increment the part's **rework count**.

## Use As Is and Repair require recorded approval

These two accept known-nonconforming product, so they carry the highest
authority burden. The system **will not record the decision without an approval
reference**:

> *A 'Use As Is' decision accepts nonconforming product and requires recorded
> customer/design approval — provide an approval reference.*

This is a hard stop, not a warning. Obtain the concession or deviation through
your normal customer/engineering channel first, then enter its reference. The
reference, the date, and who authorized the decision are all stored on the
record.

Scrap, Rework, and Return to Supplier need no approval reference.

!!! warning "There is no scrap value threshold"
    Scrap does not trigger an approval step based on part value. If your
    procedure requires one, it is a procedural control, not a system-enforced
    one.

## Who can decide, and co-signing

Recording a decision requires **`approve_disposition`**.

If you don't hold it, you don't have to hand the record off: an authorized
approver can **co-sign inline**. Enter their email as the co-signer and the
decision is recorded against *them* as the authority, with you as the caller.
This keeps the QA Manager out of the loop for routine decisions without
misattributing authority.

Either way the record stores **who authorized it and when** — that pair is what
8.7 asks for.

## Severity

| Severity | Meaning |
|----------|---------|
| **Critical** | Safety or regulatory impact; needs special handling |
| **Major** | Affects function, correctable (the default) |
| **Minor** | Cosmetic, no functional impact |

## Containment comes first

Before the disposition decision, record the **containment action** — the
immediate step taken to stop nonconforming product escaping: parts pulled to
quarantine, a machine stopped, a lot put on hold.

Containment is time-stamped with who completed it. It is deliberately separate
from the decision, because containment is urgent and the decision often is not.
An auditor reading the record wants to see the gap between *found* and
*contained* be short, regardless of how long the disposition took.

### Attaching evidence

Containment usually has evidence behind it — a photo of the segregated bin, a
signed hold tag, the tooling report that prompted the stop. Documents can be
attached to the disposition, under **Containment Action** on its edit page.

Attach the evidence rather than describing it. "Parts moved to quarantine cage"
is an assertion; the same sentence with a photo and a timestamp is a record.

## States

```
OPEN  ──(decision recorded)──▶  IN_PROGRESS  ──(resolution completed)──▶  CLOSED
```

- **Open** — raised, not yet decided. A disposition can sit here untriaged with
  no type set at all.
- **In Progress** — a decision has been recorded and is being implemented.
  Setting the disposition type is what moves it here.
- **Closed** — the resolution is complete.

!!! warning "A closed disposition's decision cannot be changed"
    Attempting it is rejected: *"This disposition is closed; its decision can no
    longer be changed."* Raise a new record instead — the original stays as the
    history of what was decided at the time.

## What the decision does to the part

Recording the type cascades to the part's status using the table above — but
with two guards that are worth understanding, because they explain cases where
the part *doesn't* move.

**A disposition is a documented decision, not a routing action.**

**Rework and Repair only route a part that is still held** — quarantined, or
not yet started. If the operator has already routed the part onward (in
progress at a step, awaiting QA, already in rework), the disposition is recorded
as a **paper record** of what was authorized and the part's status is left
alone. It would otherwise drag a part that has moved on backwards.

**A less severe decision cannot undo a terminal one.** Scrap dominates
everything; a Rework, Repair, or Use As Is decision cannot revive a part that is
already scrapped or cancelled. Reversing a terminal status is a separate,
deliberate, permission-gated operation — never a side effect of another
disposition.

## Scrap verification

Scrapped parts carry their own verification fields: whether scrap was verified,
**by what method**, by whom, and when. Recording the method matters — "rendered
unusable and placed in the scrap bin" is a different assurance from "witnessed
into the crusher", and for critical parts the difference is the whole point of
the control.

This is what prevents scrapped product re-entering the supply chain, and it is
routinely sampled in audits.

## Closing a disposition

Completing the resolution closes the record — but only once nothing is
outstanding against it. If blockers remain (for example pending part
annotations), the close is rejected and names what is in the way. Clear those
first.

## Permissions

| Permission | Allows |
|------------|--------|
| `view_quarantinedisposition` | View disposition records |
| `add_quarantinedisposition` | Raise a disposition |
| `approve_disposition` | Record the decision, or co-sign someone else's |

Closing a resolution does not require `add_quarantinedisposition` — the person
who authorizes or closes a record needn't be the one who raised it.

## Next Steps

- [Quarantine](quarantine.md) - Managing held parts
- [Quality Reports](quality-reports.md) - Creating NCRs
- [CAPA Overview](../capa/overview.md) - When a pattern needs root-cause work
