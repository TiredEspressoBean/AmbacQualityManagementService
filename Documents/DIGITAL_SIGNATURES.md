# Digital Signatures on Generated Reports

**Last Updated:** April 2026
**Status:** Note for future work — not started
**Context:** US-focused QMS. No FDA 21 CFR Part 11 customers in current
pipeline. If that changes, revisit the "Part 11 considerations" section
before starting implementation.

---

## Current state

Typst reports render with empty signature blocks (see `ncr_report.typ`'s
"Signatures" section as an example — originator, quality manager,
customer). The PDF pipeline ends at unsigned PDF generation. Signing
happens outside the system (printed + wet-ink, or via external
signing service used by the customer).

This note captures the design decisions if/when signing is brought
into the system itself.

---

## US legal framework (short version)

**ESIGN Act (2000)** and **UETA** (49 states) together make electronic
signatures legally equivalent to handwritten signatures for most
commercial transactions. Broad definition of an "electronic signature":
*any electronic sound, symbol, or process, attached to a record and
executed or adopted by a person with the intent to sign*.

No tiered system like the EU's eIDAS (SES / AES / QES). All electronic
signatures evaluated on the same standard: did the signer intend to
sign, and is there evidence of that intent.

Practical bar for US court admissibility:

1. **Intent to sign** — the signer meant to sign
2. **Consent to electronic signing** — they agreed to use electronic vs. wet-ink
3. **Attribution** — evidence linking the signature to the signer
4. **Record integrity** — evidence the document wasn't altered after signing
5. **Record retention** — ability to produce the signed record on demand

**Not strictly required:** a CA-issued certificate, "qualified trust
service provider" infrastructure, or any specific PDF signing standard.
A well-built audit trail satisfies most US use cases.

### Domain-specific exceptions

- **FDA 21 CFR Part 11** (medical device / pharma) — stricter
  requirements around per-user attribution, visible signature
  manifestation, and system validation. Not a current concern; would
  require re-architecting to per-user signing if added later.
- **IATF 16949** (automotive) — permissive; accepts electronic
  signatures that satisfy the general integrity requirement.
- **AS9100D** (aerospace) — references Part 11 for records retention
  in some contexts, but generally satisfied by ESIGN-compliant
  signatures with audit trails.
- **ITAR** — no specific digital-signature regulation, but documents
  may have additional handling rules (data residency, export controls)
  that affect which signing service can be used.

---

## Three conceptual flavors of "digital signature"

People mean different things by this phrase. Three are worth
distinguishing:

### 1. Signature image embedded in PDF

A scan or drawing of a signature, placed in the PDF. Legally it's a
picture — no cryptographic proof of origin or integrity. Adequate for
internal "looks signed" use. No infrastructure required.

### 2. Cryptographic signature (PAdES / PKCS#7)

Certificate-signed PDF. Adobe Reader shows a signature status
indicator. Anyone can verify the PDF hasn't been modified since
signing. Satisfies ESIGN/UETA when paired with an audit trail.

### 3. E-signature service workflow

Third-party service (DocuSign / Adobe Sign / etc.) handles the signing
ceremony in a browser, captures consent, returns a signed PDF plus a
tamper-evident audit trail. This is what most real businesses use.

**The recommended default for this codebase is #3.**

---

## The recommended architecture: "reserve space, sign downstream"

### Principle

The Typst pipeline produces **unsigned PDFs with reserved signature
areas**. Signing is a downstream service integration, not an in-system
feature. This keeps the PDF generation simple, lets signing services
do what they're best at (UX, consent capture, audit trails), and
allows multiple providers to coexist across tenants.

### Data flow

```
  Django + Typst          Signing Provider           Archived
  ──────────────          ─────────────────          ────────
  NCR/CoC/FAI      ─►     DocuSign/pyHanko      ─►  Signed PDF
  generated               Captures signatures        in DMS
  (unsigned)              + audit trail              linked back
```

### Template responsibility

Templates reserve visible signature space. Current NCR template
already does this:

```typst
= Signatures

#grid(
  columns: (1fr, 1fr, 1fr),
  [
    *Originator* \
    #v(24pt)
    #line(length: 100%, stroke: 0.5pt + ink) \
    #text(size: 9pt, fill: muted)[Name · Date]
  ],
  ...
)
```

The empty line + "Name · Date" label is exactly what third-party
signing services want: a visible space where they can overlay signing
widgets (or where wet-ink signing happens if the document is printed).

Templates should NOT embed cryptographic signatures directly; that's
the signing layer's job.

### Optional template enhancement: anchor tags

Adobe Sign and DocuSign both support invisible text anchors to
automate field placement:

```typst
*Originator* \
#v(24pt)
#line(length: 100%, stroke: 0.5pt + ink) \
#text(fill: white, size: 1pt)[{{sig:originator:signature}}]
#text(size: 9pt, fill: muted)[Name · Date]
```

The `{{sig:originator:signature}}` text is invisible (white, 1pt) but
the signing service recognizes it and places its signing widget there.

**Defer until needed.** Manual field placement in the signing UI works
fine for a first integration.

---

## Data model — what to add to `GeneratedReport`

Whenever signing is implemented, these fields support any provider:

```python
# Tracker/models/qms.py — add to GeneratedReport

signing_provider = models.CharField(
    max_length=30, blank=True,
    help_text="docusign, adobe_sign, pyhanko_local, manual, etc."
)
signing_envelope_id = models.CharField(
    max_length=200, blank=True,
    help_text="Provider's envelope/request ID for audit trail lookup."
)
signing_status = models.CharField(
    max_length=20, blank=True,
    choices=[
        ('', 'Not sent'),
        ('SENT', 'Sent for signature'),
        ('VIEWED', 'Viewed by signer(s)'),
        ('COMPLETED', 'All parties signed'),
        ('DECLINED', 'Declined by a signer'),
        ('VOIDED', 'Voided before completion'),
        ('EXPIRED', 'Envelope expired without completion'),
    ],
)
signing_sent_at = models.DateTimeField(null=True, blank=True)
signing_completed_at = models.DateTimeField(null=True, blank=True)
signed_document = models.ForeignKey(
    'Documents', null=True, blank=True,
    on_delete=models.SET_NULL,
    related_name='signed_reports',
    help_text="Post-signature PDF stored in the DMS."
)
```

The original unsigned PDF stays as `GeneratedReport.document`. The
signed version is `GeneratedReport.signed_document`. Both are
retained for audit purposes and cert-rotation re-signing.

**Preparatory step now (zero signing work):** these fields can be
added as nullable columns on `GeneratedReport` today, with a TODO
comment explaining they'll populate when signing lands. That reserves
the migration and makes the future change non-breaking.

---

## The SigningProvider abstraction

Critical for future flexibility. Every implementation satisfies the
same interface; tenants can be configured to use different providers;
switching is a config change, not a code rewrite.

```python
# Tracker/reports/services/signing/base.py

from typing import Protocol
from dataclasses import dataclass

@dataclass
class Signer:
    name: str
    email: str
    role: str  # "originator", "quality_manager", "customer", etc.
    routing_order: int = 1

@dataclass
class SigningStatusUpdate:
    envelope_id: str
    status: str            # matches GeneratedReport.signing_status choices
    completed_at: datetime | None
    signed_pdf_bytes: bytes | None


class SigningProvider(Protocol):
    name: str   # "docusign", "pyhanko_local", etc.

    def send_for_signature(
        self,
        generated_report: GeneratedReport,
        signers: list[Signer],
        subject: str = "",
        message: str = "",
    ) -> str:
        """Initiate signing. Return the provider's envelope ID."""
        ...

    def fetch_signed_document(self, envelope_id: str) -> bytes:
        """Download the signed PDF once completion is confirmed."""
        ...

    def handle_webhook(self, payload: dict) -> SigningStatusUpdate:
        """Process an async status update from the provider."""
        ...

    def void(self, envelope_id: str, reason: str) -> None:
        """Cancel an in-flight signing envelope."""
        ...
```

Directory layout:

```
Tracker/reports/services/signing/
  base.py                   # Protocol + shared dataclasses
  docusign.py               # DocuSign provider
  adobe_sign.py             # Adobe Sign provider (future)
  pyhanko_local.py          # In-backend cryptographic signing
  docuseal.py               # Self-hosted DocuSeal (future)
  manual_signature.py       # Browser-drawn signature capture (future)
  registry.py               # Map tenant → active provider
```

Per-tenant configuration selects the provider. On-prem-behind-firewall
tenants can use `pyhanko_local` (no outbound network required).
Cloud-hosted tenants can use DocuSign. Mixing is fine.

---

## Implementation paths (ordered by typical fit)

### Path A: DocuSign (or similar SaaS)

**The default.** When a customer asks "do you support digital
signatures?" the answer "yes, via DocuSign" ends the conversation.

- Integration effort: ~1-2 days for first tenant after abstraction exists
- Ongoing: $15-50/month/user for API tier
- Strengths: universally recognized, strongest audit trail, best UX,
  handles multi-party routing natively
- Weaknesses: requires outbound HTTPS (breaks on-prem firewall),
  per-envelope costs for high-volume tenants

Alternatives at this tier: Adobe Sign, Dropbox Sign, PandaDoc,
SignNow. Same integration shape, different tradeoffs on price and UX.

### Path B: pyHanko + company certificate

**For on-prem / air-gapped customers.** Django backend signs PDFs
directly using a tenant-owned certificate.

```python
from pyhanko.sign import signers
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter

def sign_pdf_with_tenant_cert(pdf_bytes: bytes, tenant) -> bytes:
    cert = load_tenant_cert(tenant)  # from secrets manager
    signer = signers.SimpleSigner.load(
        key_file=cert.key_path,
        cert_file=cert.cert_path,
        key_passphrase=cert.passphrase,
    )
    buf = BytesIO(pdf_bytes)
    writer = IncrementalPdfFileWriter(buf)
    signed = signers.PdfSigner(
        signers.PdfSignatureMetadata(
            field_name='CompanyApproval',
            reason='Approved for release',
            location=tenant.name,
        ),
        signer=signer,
    ).sign_pdf(writer)
    return signed.getvalue()
```

- Integration effort: ~2-3 days
- Ongoing: $0 (self-signed cert) or ~$300-500/year (CA-issued cert)
- Strengths: zero network dependency, no per-envelope cost, fully
  under operator control
- Weaknesses: no multi-party workflow, no customer-facing signing UI,
  operator manages cert rotation and revocation

Good for: CofC, NCR closure, FAI final approval — single-signature
internal documents where the signer is always the tenant's own
organization.

### Path C: Manual signature capture

Browser canvas → base64 PNG → backend embeds into reserved template
space.

- Integration effort: ~2-3 days (frontend canvas + backend PDF
  embedding + audit trail)
- Ongoing: $0
- Strengths: no certificates, no external service, simple UX for
  internal users
- Weaknesses: not cryptographically signed (picture-of-signature
  only), legally equivalent to a scan of wet ink, your audit trail is
  the only evidence of integrity

Good for: informal internal approvals where "looks signed + we have
an audit log" is enough.

### Path D: Self-hosted signing platform

Deploy DocuSeal (or similar) as part of your infrastructure.

- Integration effort: ~3-5 days + ongoing hosting
- Ongoing: hosting costs + ops time + email deliverability setup
- Strengths: own the data, no per-envelope fees, customer-facing
  signing UI
- Weaknesses: self-hosted service to operate, feature gap vs.
  commercial services, legal defensibility of the audit trail is on
  you

Good for: customers with strict data-residency requirements,
high-volume signing where SaaS fees would dominate cost.

---

## Recommended rollout

**Preparatory (~15 min, do whenever):**
- Add nullable `signing_*` fields to `GeneratedReport`. No behavior
  change, just reserves the schema.

**When first customer asks for signing (~1-2 days):**
- Build the `SigningProvider` abstraction
- Implement the DocuSign provider
- Add "Send for signature" button on the report-history UI
- Wire DocuSign webhook handler to flip `signing_status` and store
  the signed PDF

**When an on-prem / air-gap customer needs signing (~2-3 days):**
- Add the `pyHanko` provider
- Per-tenant secrets management for cert storage
- Migrate tenant config to select provider

**When a customer needs self-hosted + customer-facing signing UX (~3-5 days):**
- Add the DocuSeal (or similar) provider
- Provision and operate the self-hosted instance

Each later path is additive. Existing tenants keep their provider;
new tenants get configured to whichever fits.

---

## What NOT to do

- **Don't build signing until a customer asks.** No current
  conversation is blocked on it. Building speculatively means guessing
  on decisions (which provider, single- vs. multi-sign, company vs.
  per-user cert) that real customer conversations will answer cleanly.
- **Don't skip the `SigningProvider` abstraction** even when only
  implementing one provider initially. The abstraction costs ~1 hour
  and saves days of refactoring later.
- **Don't try to build your own PKI infrastructure.** If cryptographic
  signing is needed, use pyHanko + a cert from a standard CA. PKI is
  a domain full of footguns.
- **Don't sign every PDF.** Signatures should mean something. Signing
  hello-world test PDFs devalues the signing concept.
- **Don't embed signatures directly in Typst templates.** Templates
  reserve visible space; the signing layer fills that space with
  either a cryptographic signature (PAdES) or a placed signature
  image (from DocuSign / manual capture). Keeping these concerns
  separate is what makes the SigningProvider abstraction work.
- **Don't delete unsigned PDFs after signing.** Keep both. The
  unsigned version is useful for re-signing after cert rotation,
  and for audit reproducibility.

---

## Part 11 considerations (if FDA customers arrive)

Not in scope today. Key differences if Part 11 support becomes
required:

- **Per-user signing required.** Single-company-cert approach does
  not satisfy Part 11's "unique identification" clause. Each authorized
  signer must have a unique credential.
- **Visible signature manifestation on the PDF** (printed name, date,
  meaning of signature — e.g., "Approved by Jane Alvarez · QA Manager
  · 2026-04-13 · Meaning: Approved for Release").
- **Two-component authentication at signing time** (username + password
  OR smart card + PIN OR biometric). Signing triggers a re-auth
  challenge, not just a click.
- **Comprehensive audit trail** including failed signing attempts.
  Part 11 wants evidence of attempted tampering, not just successful
  signatures.
- **System validation** (IQ/OQ/PQ) — process-level, not code-level,
  but the code needs to be designed to support validation.

Retrofitting Part 11 onto a system built for general US use is
painful — especially the per-user attribution change. If there's a
credible chance of FDA customers, consider the per-user data model
from day one even if the workflow starts with company-level signing.

---

## References

- ESIGN Act: 15 U.S.C. §§ 7001 et seq.
- UETA: https://www.uniformlaws.org/committees/community-home?CommunityKey=2c04b76c-2b7d-4399-977e-d5876ba7e034
- 21 CFR Part 11 (if it becomes relevant): https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-11
- pyHanko documentation: https://pyhanko.readthedocs.io/
- DocuSign Python SDK: https://github.com/docusign/docusign-esign-python-client
- DocuSeal (open-source alternative): https://github.com/docusealco/docuseal
