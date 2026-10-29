# Auditor

An orientation for an auditor: where the evidence for a question lives, and how to
read it without anyone fetching it for you. Every exercise is on the training shop,
and every record it names is one the training seed creates.

**About an hour.** It assumes you know what you're auditing against (see
[ISO 9001](../../compliance/iso9001.md)), not how this shop works.

!!! tip "This is orientation, not training"
    An auditor changes nothing. There's nothing to practise and nothing you can
    break, so there's no final task: this page shows you where the evidence is.

## Who you are

| You log in as | When |
|---------------|------|
| **Alex Morgan**, Auditor, `alex.audit@demo.ambac.com` | Every module |

The password is `demo123`.

Alex holds view permissions across the whole shop, plus the audit log and report
downloads, and nothing that changes a record: the pages show what's recorded,
without the buttons for changing it.

---

## 1. Your desk

**You will:** find where each kind of evidence starts.

Log in as Alex. The home page is a list of where to look:

- **Audit log**: every change, who made it, and when.
- **CAPAs**, **Calibration records**, **Training records**, **Documents**.
- **Approvals**: signed decisions.

Below them are the CAPAs by state and how old the open nonconformances are.

---

## 2. One unit, start to finish

**You will:** read everything recorded about one serial.

`INJ-QA-INSPECT-013` failed flow calibration and is waiting to be reworked.

1. Open work order `WO-QA-INSPECT-02`, then **Parts**, then the part's **View Part
   Details**. The part page lists its quality reports, its disposition
   (`DISP-2026-000014`, Rework) and why it can't move on yet.
2. **Traveler** > **Download PDF** prints this serial's record. Each operation shows
   who did it and when, every reading against its specification (*Flow Rate 98
   mL/min ✗ OUT OF SPEC*), the material lots fitted at assembly, and the
   nonconformance with who authorised its disposition (*authorised Maria S.*).

The traveler says *Uncontrolled when printed*: the system is the record, and the PDF
is a copy of it on the day you printed it.

---

## 3. Was the person qualified, and was the gauge good?

**You will:** check the two things a reading depends on.

1. **Quality** > **Training** > **Training Matrix**. Hover a cell for the skill,
   the level and its expiry (*Dimensional Inspection Certification: Trainee —
   expires …*, a week after the shop was set up); the person is the row.
2. **Calibration records**. The micrometer `MIC-2` failed its check this morning.
   Open that record's exposure: **What Micrometer MIC-2 measured** lists every
   report it was used for since it last passed, `INJ-QA-INSPECT-013`'s bore among
   them. The page lists them; deciding what to do about them is the QA manager's.

Where someone worked a step without the training on record, the authorisation sits
on the step itself: who allowed it and why. Read it as *the record hadn't caught
up*, not as unqualified work. What's worth sampling is an authorisation with no
training record after it.

---

## 4. A problem and its corrective action

**You will:** follow a CAPA from the problem to its approval.

Open **CAPAs** > `CAPA-2024-003`, *Elevated Nozzle Rejection Rate*.

- **Overview**: the problem and the containment.
- **Root Cause**: the analysis, its method and who did it.
- **Approval**: a Major CAPA needs management approval before work starts. Maria
  Santos approved it, with her comment and the time.

Many roles can raise a CAPA; only a QA manager or production manager approves one,
and not their own when someone else can.

---

## 5. Which revision was in force

**You will:** find a document's revisions, and see what's withheld from you.

**Documents** lists the controlled documents you may read. Open
`WI-1002 Nozzle Inspection` and its **Versions**: each revision with who uploaded
it, when, its status and why it changed (*Rev 2.1: Updated spray angle tolerance per
CAPA-2024-003*). When a revision is released, the one before it is marked
superseded and stays readable here.

Drawings marked confidential, restricted or secret don't appear at all. An auditor
isn't given the classified tiers. That's the control working: ask your host for a
reader with the clearance rather than to be given it.

---

## 6. Who changed what

**You will:** find a change, who made it, and what it was before.

Before this module your trainer, logged in as one of the shop's people, changes
something: records a calibration, say, or a training record.

**Audit log**: newest first, each row with the time, the person, what they did,
the record, and the fields before → after. Your own looking is recorded too: the
traveler you printed in module 2 is there as *Accessed*.

A record's own **History** tab shows the same trail for that record. On the training
shop, records that were loaded when it was set up show *No audit history*: nobody
worked them here. Records your trainer changes show every change.

---

## Things that look like findings and aren't

!!! tip "Voided isn't deleted"
    A record put right is voided, with who, when and why, and stays readable. A
    corrected inspection result is kept as recorded and marked superseded, with the
    new result beside it. An empty list rarely means something was destroyed.

!!! tip "A new version is the same thing, updated"
    A new version of a process, document or supplier record isn't a replacement.
    Its history stays attached.

!!! tip "Steps are shared across process versions"
    A step appearing under two versions of a process is deliberate, so older work
    still reads against the step it ran.

---

## Orientation checklist

- [ ] Read one serial's record and printed its traveler
- [ ] Checked a person's qualification and a gauge's calibration behind a reading
- [ ] Followed a CAPA to its approval
- [ ] Found a document's revisions
- [ ] Found a change in the audit log, with who and what it was before
