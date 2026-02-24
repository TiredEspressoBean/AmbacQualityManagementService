# Electronic Signatures

Compliant electronic signatures for approvals and records.

## Regulatory Requirements

Electronic signatures must comply with:

| Standard | Key Requirements |
|----------|------------------|
| **21 CFR Part 11** | Unique ID, password verification, signature meaning |
| **ISO 13485** | Authorized signatures, records |
| **EU MDR** | Electronic identification |

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

1. Review item requiring approval
2. Click **Approve** (or Reject)
3. Enter password
4. Add comments (optional)
5. Submit

Signature is recorded with all required data.

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
| **Electronic** | Password verification + identity | Ambac Tracker standard |
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

## Compliance Mapping

### 21 CFR Part 11 Requirements

| Requirement | Implementation |
|-------------|----------------|
| Unique to individual | UUID user ID |
| Not reused or reassigned | IDs never reused |
| Two distinct components | User ID + password |
| Signature meaning | Configurable meaning text |
| Date/time of signing | Server UTC timestamp |
| Manifest during signing | Meaning displayed before sign |

## Next Steps

- [Audit Trails](audit-trails.md) - Audit logging
- [Document Control](document-control.md) - Document approvals
- [Document Approval](../workflows/documents/approval.md) - Approval workflow
