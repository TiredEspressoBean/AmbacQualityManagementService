# Auditor Orientation

**Duration:** 1 hour
**Prerequisites:** None
**Goal:** Find the evidence you need without needing anyone to fetch it for you

!!! note "Role Name"
    This is for the **Auditor** role in the system.

!!! info "Demo Environment Login"
    **Email:** admin@demo.ambac.com
    **Password:** `demo123`

    The demo has no read-only auditor account. Alex Demo is **Tenant Admin** and
    can change things — so in the demo, look but don't touch.

!!! tip "This is orientation, not training"
    An auditor holds **no write permission of any kind**. There is nothing to
    practise and nothing you can break. This page exists to show you where the
    evidence lives.

---

## Module 1: What You Hold

### 1.1 The whole permission set is "view"

You get the staff view permissions and full-tenant visibility. Not a comment, not
a status, not a note. There is nothing you can touch that would later need
explaining — which is the point: **audit independence is a property of the
system here, not a promise.**

### 1.2 Sensitive data is not masked

!!! warning "Read-only is not anonymised"
    You see real customer names, real people's names on records, real quantities.
    Treat this as you would any access to a shop's live records.

### 1.3 One thing you are not given

**The classified document tiers.** An auditor is not granted
`view_secret_documents` or the export-control tier, because an external auditor
may not be an authorised person for export-controlled technical data.

!!! note "An invisible document is the control working"
    Ask your host for a reader with the right clearance rather than asking to be
    given the tier. See [Export Controls](../compliance/export-controls.md).

---

## Module 2: Where the Evidence Is

| Question | Where |
|----------|-------|
| Who did what, when, to which record | [Audit Trails](../compliance/audit-trails.md) |
| Was the person qualified | [Training Matrix](../workflows/tracking/training-matrix.md) |
| Was the equipment in calibration | Quality → Calibrations |
| What happened to this nonconformance | [Dispositions](../workflows/quality/dispositions.md) |
| Was the corrective action effective | [CAPA Verification](../workflows/capa/verification.md) |
| What was this unit actually built to | [Part History](../workflows/tracking/part-history.md) |
| Which revision was in force then | [Document Revisions](../workflows/documents/revisions.md) |
| Who signed, and was it really them | [Signatures](../compliance/signatures.md) |

---

## Module 3: Four Things That Will Mislead You

These are properties of the system that look like findings if you don't know
them.

!!! tip "1. Records are voided, not deleted"
    uqmes soft-deletes. A voided record stays readable with its reason and its
    author. **An empty list rarely means something was destroyed** — check
    whether you are filtering voided rows out.

!!! tip "2. A version is the same entity, updated"
    A new version of a process, document or supplier record is not a new thing.
    History stays attached and forward links follow. Don't read a version bump as
    a replacement.

!!! tip "3. Overrides are recorded where they happened"
    A supervisor authorising past the training gate signs in separately, and the
    reason lands on the **step execution itself**, not in a separate log. Same
    for release overrides on a work order. The exception is stored next to the
    thing it excepted — so look at the record, not for a register.

    Read these as *the record hadn't caught up*, not as *unqualified work* — the
    gate can only see what is recorded, and the authorisation already carries a
    second person's name. What is worth sampling is an authorisation with **no
    training record following it**.

!!! tip "4. Steps are shared across process versions"
    This is deliberate structural sharing so date snapshots resolve. A step
    appearing under two process versions is correct, not a data integrity fault.

---

## Module 4: Separation of Duties

The pattern worth checking, because it is what the design is built around:

**Many roles can raise; few can approve.**

- Any staff role may initiate a CAPA or raise a supplier qualification — only
  **QA Manager** approves one
- The dock can reject pieces — only QA rejects a whole lot or approves a
  disposition
- A Shift Lead can override a training gate — and **cannot** void the quality
  record of work someone else signed
- Engineering authors a specification — **Document Controller** releases the
  document that carries it

See [Role Comparison](../roles/index.md#what-tells-the-roles-apart) for the full
matrix, generated from the permission presets.

---

## Module 5: Standards

uqmes is built against **ISO 9001** today, with IATF 16949 as a later target once
PPAP support is complete.

- [ISO 9001](../compliance/iso9001.md)
- [Compliance Overview](../compliance/overview.md)
- [Compliance Reports](../compliance/reports.md)
- [Audit Trails](../compliance/audit-trails.md)

---

## Orientation Checklist

- [ ] Logged in and confirmed you cannot edit anything
- [ ] Found an audit trail entry naming a person and a record
- [ ] Found a training record and the matrix it feeds
- [ ] Traced one unit's as-built history
- [ ] Found a disposition and the CAPA it led to
- [ ] Found a document's revision history
- [ ] Exported something to take away

---

## Next Steps

- [Auditor role guide](../roles/auditor.md)
- [Audit Trails](../compliance/audit-trails.md)
- [Signatures](../compliance/signatures.md)
- [Exporting](../analysis/exporting.md) — taking evidence with you
