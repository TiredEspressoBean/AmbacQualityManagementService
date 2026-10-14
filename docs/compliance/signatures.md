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

## How Signatures Work

### Password Verification
When signing:
1. User enters password
2. System verifies against stored credentials
3. Verification logged
4. Signature recorded

### Signature Components
Each signature records:
- **Who**: User identity (unique ID, name, email)
- **What**: Record being signed
- **When**: Timestamp (server-generated)
- **Meaning**: What the signature means
- **Verification**: Password verified = true

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
| §11.200 — **two identification components**, and re-authentication at signing | Depends which signature. Signing **your own** work: the session established identity and the password re-confirms it — one identification component, re-entered. An inspection **verifier** supplies email **and** password, not being signed in at that terminal — two. In neither case does the drawing count: it is evidence of intent, not identification. Whether the own-signature case satisfies §11.200(a)(1) also depends on how your session is established — SSO with MFA is a different answer from a password login |
| §11.300 — controls over identification codes and passwords | Django's validators and the per-person signing throttle; password policy itself is your IdP's |

**What is not here, and is the larger half of Part 11:** computer-system validation
and its documentation, the SOPs and training that sit around the system, record
retention and the ability to produce accurate copies for inspection, and open-system
controls under §11.30. Those are programme questions, not features, and no vendor
answers them for you.

So the fair answer to "could you?" is: **the signing mechanism has the shape Part 11
describes, and the surrounding programme would be yours to build and validate.**

Wrong passwords are rate-limited, so a terminal left signed in can't be used to
guess a password. See [Authoring Work Instructions](../workflows/dwi/authoring.md#verified-sign-off)
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

### For Records

When signature is required:
1. Complete record entry
2. System prompts for signature
3. Enter password
4. Confirm signature meaning
5. Submit

## Signature Records

Each signature stores:

| Data | Description |
|------|-------------|
| **User ID** | Unique user identifier |
| **User Name** | Display name at time of signing |
| **Email** | User email |
| **Timestamp** | Server-generated UTC time |
| **Meaning** | Signature meaning text |
| **Password Verified** | Confirmation of verification |
| **Record Type** | What was signed |
| **Record ID** | Specific record |

## Signature Audit Trail

Signatures appear in audit trail:
- All signatures logged
- Cannot be modified
- Part of immutable record

### Viewing Signatures

On signed records:
1. View record detail
2. See **Signatures** or **Approvals** section
3. Each signature shows:
   - Who signed
   - When
   - Signature meaning
   - Comments

## Electronic vs Digital Signatures

| Type | Description | Use |
|------|-------------|-----|
| **Electronic** | Password verification + identity | uqmes standard |
| **Digital** | Cryptographic certificate (PKI) | Not currently implemented |

Electronic signatures with password verification meet most regulatory requirements.

## SSO and Signatures

When using Single Sign-On:
- User authenticates via IdP
- Signature still requires password re-entry
- Confirms user is present at time of signing
- Not just logged-in session

## Signature Image (Optional)

For visual signature capture:
1. User draws signature on screen
2. Image captured as base64
3. Stored with signature record
4. Displays on printed documents

Configuration determines if signature image is required.

## Failed Signature Attempts

Failed attempts are logged:
- Wrong password
- Account locked
- Timestamp of attempt
- IP address

Supports investigation of unauthorized access attempts.

## Signature Reports

Generate signature reports:
- All signatures in period
- By user
- By record type
- Failed attempts

For audit preparation.

## Permissions

| Permission | Allows |
|------------|--------|
| `view_approvalresponse` | View signature/approval records |
| `respond_to_approval` | Sign approvals when assigned |
| `approve_*` (e.g., `approve_capa`) | Approve specific record types |

## What a signature records

| Property | Implementation |
|----------|----------------|
| Unique to the individual | UUID user ID, never reused or reassigned |
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
