# Document Controller

The document controller's slice of [the shop day](../shop-day.md): bringing a
document under control, routing it for approval, putting it into force, replacing it
with a revision, and withdrawing it. Every exercise is on the training shop, and
every record it names is one the training seed creates.

**About 1½ hours**, in one sitting. **Before you start:** nothing.

!!! warning "On a training instance only"
    Every exercise writes real records: a document you release is the one people
    work to. See the [training program](../index.md).

## How a session runs

1. **Watch.** Your trainer works the modules on the training instance, saying what
   they look at and why.
2. **Regenerate.** Your trainer puts every exhibit back as it was (below).
3. **Do it with help.** You work the same modules on the same exhibits, with your
   trainer beside you.
4. **Try to break it.** Where a module has a refusal, something the system won't let
   you do, do it on purpose and read what it says. The refusal is part of the
   lesson, not an error.
5. **Alone.** After another regenerate, the [final task](#final-task-observed),
   with your trainer watching and not helping.

**Regenerating** (for the trainer): **Settings** > **Organization** > **Regenerate
demo data**, then type `REGENERATE` to confirm. It needs a Tenant Admin login, appears only
on the training tenant, and replaces **everyone's** work on the instance. It runs in
the background and takes a few minutes; the card stops waiting after five, so if it
hasn't finished by then, reload the page later rather than pressing it again.

## Who you are

| You log in as | When |
|---------------|------|
| **Lisa Park**, Document Controller, `lisa.docs@demo.ambac.com` | Every module except 3 |
| **Maria Santos**, QA Manager, `maria.qa@demo.ambac.com` | Module 3, to approve |
| **Jennifer Walsh**, Production Manager, `jennifer.mgr@demo.ambac.com` | Module 3, the approval in order |

Every password is `demo123`.

---

## 1. Your desk

**You will:** read the document controller's home page.

Log in as Lisa. **Approvals in flight** lists every approval under way in the shop,
with its type: most are *CAPA Major*, and one is a *Document Release*. Read the type
before you open one. In flight isn't the same as yours to decide.

**Documents** counts what *Needs my approval*, what's *Pending approval*, what's *Due
for review* and what's *Released*. **Training** counts records current, expiring and
expired. Each figure opens what it counts.

**Documents** in the sidebar is the library, with uploads, recent changes and counts
by classification.

---

## 2. Bring a document under control

**You will:** upload a new work instruction and route it for approval.

1. **Documents** > **Upload Document**. Choose the file. Its file name becomes the
   document's name, so name the file properly first (`WI-1004 Seat loupe check`).
   There's no separate title or number field.
2. **Document Type**: Work Instruction. **Classification Level**: Internal (module
   7). **Upload Document**: *Document created successfully!* It's *v1 · Draft*.
3. On its **Approval** tab, **Submit for Approval**. It's *Under Review*, and the
   **Assigned Approvers** are named by the document type's approval template: here,
   the QA manager. *You are not assigned as an approver for this document.*

You route documents; the people the template names approve them.

**Submitted it with a mistake in it?** Under review, it can't be edited: the edit page
says so and won't save. On the **Approval** tab (or **Approvals** > *My Submitted
Requests*), **Withdraw request** and say why. The approvers are no longer asked, the
document goes back to *Draft*, and you correct it and submit again. The withdrawn
request stays in its approval history as *Cancelled*.

---

## 3. Approve it (as the QA manager)

**You will:** see what an approver does.

Log in as Maria and open the document. **Approval** > **Submit Response**: choose
**Approve**, add a comment, draw your signature, tick the confirmation, enter your
password, and **Submit Approval**. The document is now *Approved*.

The signature and password make it an electronic signature: the record says who
approved it, when, and that it was really them.

Answered too soon? While the request is still open, the approver can use **Change my
response**, with a reason. Their answer is taken back and they're asked again. Once
the request is decided, its responses stand.

### An approval in order

Some documents are signed in stages. `DWG-1001` *Body bore detail* is a **Controlled
Drawing**, and that type routes through its own sequential template: the engineer
first, then any one QA Manager, then the production manager. The engineer has already
approved.

1. Log in as Jennifer and open `DWG-1001`'s **Approval** tab. **Assigned Approvers**
   lists Jordan Reyes *Approved*, the **QA Manager** group, and Jennifer *Pending*.
   **Submit Response** and try to approve. It's refused: *Not your turn — waiting on
   QA Manager.* It isn't in her pending approvals either; a request shows there only
   when it's your turn.
2. Log in as Maria and approve it: the QA Manager stage is done.
3. Log in as Jennifer again. Now she can approve, and the drawing is *Approved*.

**Exercise 3.1.** The Approval tab doesn't number the stages: the order is the
template's. Open **Data Management** > **Approval Templates** > *Drawing Release
(sequential)* and say who answers each stage, and which one the drawing is waiting
on.

---

## 4. Put it into force

**You will:** release an approved document.

Approved isn't in force. Releasing is the separate act that puts it in front of the
people who work to it, so an approved revision can wait for the training or tooling
it depends on.

1. Log in as Lisa and open `WI-1001 Injector Disassembly v3.2` (*Approved*).
2. **Release**: *It comes into force on the effective date, and its review and
   retention dates are set from its document type.* Leave the effective date blank
   for today, then **Release**.

It's *Released*. Its review date is a year out (the work instruction type's review
period), and the **Due for review** count will find it then.

---

## 5. Replace it with a revision

**You will:** revise a released document and put the revision into force.

1. Open `WI-1002 Nozzle Inspection v2.1` (*Released*). **Create Revision**: give the
   change justification (*Rev 2.2: add the 10x loupe seat check*). Attach the new
   file, or leave it empty to keep the current one. You get *v2 · Draft*.
2. Submit v2 for approval, approve it as Maria (module 3), and release it as Lisa
   (module 4).
3. **Versions** lists both. Releasing v2 superseded v1: v1 is *Obsolete*, and its
   page says what replaced it. Nobody can work to the old revision by mistake.

---

## 6. Withdraw a document

**You will:** mark a document obsolete.

Open a released document that's no longer needed. **Mark obsolete**: *It is withdrawn
from use from today and kept for its retention period. Marked obsolete by mistake, it
can be reinstated while no later revision has replaced it.* Confirm.

It stays in the library as *Obsolete*, readable for the record. Deleting is not how a
controlled document ends.

**Obsoleted the wrong one?** **Reinstate** puts it back in force: released again if it
had been released, with its obsolete date cleared. Say why. The reason shows under
*Corrections* on its **Audit Trail**. A revision that a later one replaced can't be
reinstated; revise the current revision instead.

---

## 7. Who can see it

**You will:** choose a classification.

| Tier | Who can see it |
|------|----------------|
| **Public** | Everyone, including a customer, if it's attached to their order |
| **Internal** | Staff, auditors included |
| **Confidential**, **Restricted** | Staff, except auditors |
| **Secret** | Tenant admin and document controller |

A customer sees only Public documents attached to their own order, its work orders
or parts: that's how a certificate reaches them. A document above someone's tier
isn't greyed out for them; it isn't there. When someone says a document vanished,
check its tier first.

`DWG-CRI-8800-N Nozzle seat geometry` is held at **Secret**. As Lisa it's in the
library. Log in as Jordan (Engineering) or Maria (QA manager) and it isn't: no row,
no greyed-out name. The QA manager can set a document's tier, including Secret,
and then not be able to open it.

---

## What isn't yours

| Not yours | Whose |
|-----------|-------|
| Approve a document | The approvers its template names (here, the QA manager) |
| Approve a CAPA in your approvals list | QA manager |
| Write the content | Its author, usually engineering or quality |

---

## Final task — observed

Your trainer regenerates the data, logs you in as Lisa, and says only: *"The seat
check needs to go into the nozzle inspection instruction, and it's in force from
Monday."* Then they watch without helping:

- revise `WI-1002`, with a justification
- route it for approval (your trainer approves it as Maria)
- release it effective Monday
- show that the old revision can no longer be worked to

Your trainer is watching for:

- [ ] The change went in as a revision, not a new document.
- [ ] You routed it and didn't try to approve it yourself.
- [ ] The release carried the effective date you were given.

## Recording your qualification

Passing the final task is the assessment. The record is a **training record**, which
your QA manager writes. See [Training Records](../../workflows/quality/training-records.md).
