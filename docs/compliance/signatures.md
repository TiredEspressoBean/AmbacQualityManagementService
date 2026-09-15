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

## Best Practices

1. **Unique accounts** - No shared credentials
2. **Strong passwords** - Meet policy requirements
3. **MFA recommended** - Via SSO/IdP
4. **Clear meanings** - Unambiguous signature text
5. **Timely signing** - Sign when completing work

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
