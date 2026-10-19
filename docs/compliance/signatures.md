# Electronic Signatures

Electronic signatures on approvals and records — who signed, what they were
attesting to, and how their identity was verified.

## Why signatures are captured

The standards uqmes targets require that approvals be **attributable** and
**recorded**:

| Standard | What it needs from a signature |
|----------|-------------------------------|
| **AS9100D** | Authorized approval of documents, processes, and dispositions |
| **IATF 16949** | Approval records for control plans and process changes |
| **ISO 9001** | Documented evidence of who authorized what, and when |

!!! note "Medical-device and FDA regulation is not a target"
    uqmes is not built for 21 CFR Part 11, ISO 13485, or EU MDR, and no claim
    of conformance with them is made. The signature mechanism described below
    is designed for aerospace and automotive quality requirements. If you need
    medical-device compliance, treat these controls as a starting point to be
    independently assessed, not as evidence.

## Signature Meanings

Common signature meanings:

| Context | Meaning Example |
|---------|-----------------|
| **Document Approval** | "I approve this document for release" |
| **Disposition** | "I authorize this disposition decision" |
| **CAPA Closure** | "I verify effectiveness and approve closure" |
| **Quality Report** | "I confirm this non-conformance record" |

Meanings are configured per approval template.

## How a signature in a work instruction is taken

A signature is a **block in the substep's body**, and whoever authors the
instruction chooses how strongly it is signed. There is no substep-wide setting:
a substep asks for a signature exactly when its body contains a block that does.

| Level | What the signer does | What is recorded |
|-------|----------------------|------------------|
| **Check off** | Ticks the block | The signed-in user, the server's time |
| **Signature + password** | Draws a signature and re-enters **their own** password | The signer, what the signature was for, the server's time, verification method *Password*, and the IP address |

An inspection block is different in one way that matters: its **verifier signs as
a second person**, with their own email and password, because a shop terminal
carries one login and the verifier is not the person signed in at it.

**What the server guarantees in every case:** who signed, when, how identity was
proven, the originating IP, and what the signature was for are all set by the
server. No endpoint accepts any of them from a client. A *Password* verification
can only be produced after a real password check — the signer's own, or a second
person's email and password. What a client supplies is the drawing itself and
which block it belongs to.

!!! note "What the signature was for"
    The recorded meaning is the **block's label** — so label it with the act
    ("Release sign-off") rather than leaving it blank. An unlabelled block falls
    back to the substep's title, which is usually less precise about what was
    accepted.

!!! warning "A drawing is not proof of verification"
    A check-off block also stores a drawing, recorded with verification method
    *None*. That is honest rather than forged — it says "signed under a session,
    not re-authenticated" — but it means the presence of a signature image is
    **not** evidence that anyone re-authenticated. Read the verification method,
    not the picture.

## Releasing a lot: QA sign-off at a step

A step can be gated so no part advances off it until QA releases the lot. That is a
different act from signing a substep — it covers the whole work order at that step,
and it is made by **someone other than whoever did the work**, which the server
enforces.

The author chooses how firmly it is signed, the same way they choose for a block:

| Level | What the signer does | What is recorded |
|-------|----------------------|------------------|
| **Check off** | Confirms the release | The signer, the server's time, the IP, meaning, method *None* |
| **Signature + password** | Re-enters **their own** password | The same, with method *Password* |

The meaning is server-derived — *"QA release of {step} for {work order}"* — and is
never supplied by a client.

!!! important "Independence and assurance are different controls"
    A QA release is always made by a second person: whoever signed the step's own
    substeps is refused. That is **segregation of duties**, and it is enforced
    whatever the assurance level — including *check off*.

    The password, where the author requires one, proves the signer is who they say.
    It does not make them independent, and independence does not re-authenticate
    them. The segregation check runs **first**, so a release cannot be bought by
    someone who was never entitled to make it.

    The password is the inspector's **own**, not a second person's, because the
    inspector is the one signed in at the terminal — unlike an inspection block's
    verifier, who is not.

!!! note "First-piece buy-off meets the same bar"
    A step can also be released through its first piece inspection. Both a **pass**
    and a **waive** release it, and both are held to the step's authored assurance —
    otherwise the gate could be walked around by releasing the other way. Where the
    buy-off is already co-signed with an email and password, it is not asked again:
    that is stronger than re-entering your own.

    Segregation of duties applies to all three outcomes — **pass, fail and
    waive** are each refused to whoever signed the first piece's own substeps.

!!! note "When an FPI carries a drawn signature"
    Only a **co-signed** buy-off asks for a drawing: the inspector signs at
    someone else's station with their email, password and signature. The drawing
    is kept on the FPI record, but only once the email and password verify, so a
    failed co-sign stores nothing.

    A buy-off from the inspector's own session asks for no drawing — at most
    their password, where the step's author requires it.

    Either way, what identifies the signer is the re-authentication,
    `inspected_by` and `inspected_at`. The drawing is the visible mark, not the
    identification.

!!! warning "Older releases read as what they were"
    A `QaApproval` made before this existed carries method *None* and no verified
    time. That is the honest record: it was made under the signer's session alone.
    Do not read an old release as a verified one.

**Which level a standard asks for:**

- **ISO 9001** asks that records identify who performed or authorized the work.
  An attestation does that.
- **AS9100** requires control of *acceptance authority media* — inspection stamps
  and their electronic equivalents. A signature that accepts an inspection or
  releases product is one, so it should be unique to the person and impossible to
  use on their behalf. Author those blocks as **signature + password**.

**If someone from an FDA-regulated space asks "could you do Part 11?"** — this is
what to tell them. It is not a conformance claim and uqmes is not built for Part 11,
as the note above says. It is an honest account of what the mechanism does, so the
question can be answered instead of dodged.

| What Part 11 asks | What verified sign-off actually does |
|-------------------|--------------------------------------|
| §11.50 — a signature shows the signer, the date and time, and its **meaning** | All three: the signer from the session (or the verified second person), the server's time, and the meaning stored from the block's label, falling back to the substep title when a block is unlabelled |
| §11.70 — the signature is **linked to its record** so it can't be moved or copied | Each signature is its own row keyed to the substep, the block within it, and the execution or batch it was taken against — not a free-standing artifact that could be re-pointed |
| §11.100 — **unique to one individual**, never reused | The signer is a user id from the account itself; accounts are suspended rather than deleted, so an id is never reassigned to a different person |
| §11.200 — **two identification components**, and re-authentication at signing | Three situations, two answers. Signing **your own** work, and a **QA release** of a lot: the signer is the person at the terminal, so the session established identity and the password re-confirms it — one identification component, re-entered. An inspection **verifier** is not signed in, so they supply email **and** password — two. Note that a QA release being made by a *different person* is segregation of duties, not a second identification component; it answers a different question. The drawing never counts in any case — it is evidence of intent, not identification. Whether the one-component cases satisfy §11.200(a)(1) also depends on how your session is established — SSO with MFA is a different answer from a password login |
| §11.300 — controls over identification codes and passwords | Django's validators and the per-person signing throttle; password policy itself is your IdP's |

**What is not here, and is the larger half of Part 11:** computer-system validation
and its documentation, the SOPs and training that sit around the system, record
retention and the ability to produce accurate copies for inspection, and open-system
controls under §11.30. Those are programme questions, not features, and no vendor
answers them for you.

So the fair answer to "could you?" is: **the signing mechanism has the shape Part 11
describes, and the surrounding programme would be yours to build and validate.**

Wrong passwords are rate-limited, so a terminal left signed in can't be used to
guess a password. See [Authoring Work Instructions](../workflows/dwi/authoring.md#sign-off-blocks)
for turning it on.

## Signing Process

### For Approvals

1. Review the item requiring approval
2. Click **Submit Response**
3. Choose a **Decision** — Approved, Rejected, or Delegated
4. Add comments (optional)
5. Sign, if the approval template requires verification
6. Submit

The response is recorded with your identity, the decision, a timestamp, the
verification method used, and the originating IP address.

### Viewing signatures

On a signed record, open its **Signatures** or **Approvals** section. Each entry
shows who signed, when, what the signature meant, and any comments. Signatures
are part of the audit trail and cannot be modified.

!!! note "Signature reporting is not built"
    There is no signature report — no "all signatures in a period", "by user" or
    "by record type" view. For an audit, read the signatures on the records
    themselves. See [Audit Trails](audit-trails.md), which lists signature
    reporting among the planned exports.

## Digital (PKI) signatures

Cryptographic certificate signing is **not implemented**. uqmes signatures are
electronic: an identity established by the session or a password check, bound to
the record by the server.

## Permissions

| Permission | Allows |
|------------|--------|
| `view_approvalresponse` | View signature/approval records |
| `respond_to_approval` | Sign approvals when assigned |
| `approve_disposition`, `verify_capa`, `approve_stepoverride`, … | Gate a specific authorized act |

!!! warning "Approval routing does not come from a permission"
    For documents, processes, CAPAs and the other approval types, **who may
    approve is set by the approval template's approver bindings**, not by an
    `approve_*` permission. Holding `respond_to_approval` lets you answer a
    request that was routed to you; it does not decide routing.

    Before relying on any permission as a control, confirm what enforces it —
    three `approve_*` permissions existed for years and were checked by
    nothing.

## What a signature records

| Property | Implementation |
|----------|----------------|
| Unique to the individual | The signer's user id, taken from the account itself. Accounts are suspended rather than deleted, so an id is never reassigned to a different person. |
| Identity verification | `verification_method` — `PASSWORD`, `SSO`, or `NONE` |
| Signature meaning | `signature_meaning`, e.g. "I approve as QA Manager" |
| Signature image | `signature_data`, a base64 PNG, when one is captured |
| Date and time | Server UTC timestamp |
| Origin | `ip_address` of the signing request |

!!! warning "`NONE` is a valid verification method"
    Signing can be configured to require no identity verification at all. A
    signature recorded with `verification_method = NONE` attributes the action
    to a user account but does **not** evidence that the account holder
    personally authorized it.

    If you are relying on signatures as controls, confirm your approval
    templates require `PASSWORD` or `SSO` — the model does not enforce this
    for you.

## Next Steps

- [Audit Trails](audit-trails.md) - Audit logging
- [Document Control](document-control.md) - Document approvals
- [Document Approval](../workflows/documents/approval.md) - Approval workflow
