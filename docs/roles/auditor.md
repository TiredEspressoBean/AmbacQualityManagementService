# Auditor

**Read everything, change nothing.** A seat for internal and external audits,
built so that audit independence is a property of the system rather than a
promise.

!!! info "The whole permission set is 'view'"
    Auditor holds the staff **view** permissions and full-tenant visibility. It
    holds no write permission of any kind — not a comment, not a status, not a
    note. There is nothing an auditor can touch that would later need explaining.

## What you can see

Everything in the tenant, subject to one exclusion below: orders, work orders,
parts and their histories, quality records, dispositions, CAPAs, documents,
training records, calibration records, audit trails and the analytics on top of
them.

!!! warning "Sensitive data is not masked"
    The role is read-only, not anonymised. You see real customer names, real
    people's names on records, and real quantities. Treat the access as you would
    any other access to a shop's live records.

## What you are not given

**The classified document tiers.** An auditor is not granted
`view_secret_documents` or the export-control tier, because an external auditor
may not be an authorised person for export-controlled technical data.

!!! note "This can look like a gap, and isn't"
    If a document is invisible to you, that is the export-control and
    classification machinery working, not a permissions mistake. Ask your host
    for a reader with the right clearance rather than asking to be given the
    tier. See [Export Controls](../compliance/export-controls.md).

## Where the evidence lives

| Question | Where |
|----------|-------|
| Who did what, when, to which record | [Audit Trails](../compliance/audit-trails.md) |
| Was the person qualified | [Training Matrix](../workflows/tracking/training-matrix.md) |
| Was the equipment in calibration | Calibrations |
| What happened to this nonconformance | [Dispositions](../workflows/quality/dispositions.md) |
| Was the corrective action effective | [CAPA Verification](../workflows/capa/verification.md) |
| What was this unit actually built to | [Part History](../workflows/tracking/part-history.md) |
| Which revision was in force then | [Document Revisions](../workflows/documents/revisions.md) |
| Who signed, and was it really them | [Signatures](../compliance/signatures.md) |

## Things worth knowing before you start

!!! tip "Records are voided, not deleted"
    uqmes soft-deletes. A voided record stays readable with its reason and its
    author. An empty list rarely means something was destroyed — check whether
    you are filtering voided rows out.

!!! tip "A version is the same entity, updated"
    A new version of a process, document or supplier record is not a new thing.
    History stays attached and forward links follow. Don't read a version bump as
    a replacement.

!!! note "Overrides are recorded where they happened"
    A supervisor authorising unqualified work leaves a reason on the step
    execution itself, not in a separate log. Same for release overrides on a work
    order. The exception is stored next to the thing it excepted.

## Standards

uqmes is built against **ISO 9001** today, with IATF 16949 as a later target.

- [ISO 9001](../compliance/iso9001.md)
- [Compliance Overview](../compliance/overview.md)
- [Compliance Reports](../compliance/reports.md)

## Next Steps

- [Audit Trails](../compliance/audit-trails.md)
- [Signatures](../compliance/signatures.md)
- [Export Controls](../compliance/export-controls.md)
- [Exporting](../analysis/exporting.md) — taking evidence away with you
