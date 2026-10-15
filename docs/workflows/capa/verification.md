# Verification & Closure

The final phases of CAPA: verifying corrective actions worked and formally closing the investigation.

## Verification Phase (D7)

After implementing corrective actions, verify they were effective.

### What to Verify

| Question | Method |
|----------|--------|
| **Was action implemented?** | Review evidence, inspect |
| **Did it fix the problem?** | Check data, no recurrence |
| **Are there side effects?** | Monitor for new issues |
| **Is it sustainable?** | Procedures updated, training complete |

### Verification Activities

Common verification tasks:

1. **Audit**: Check implementation
2. **Data Review**: Compare before/after metrics
3. **Sample Inspection**: Verify parts produced correctly
4. **Process Confirmation**: Walk the process
5. **Document Review**: Procedures updated

### Recording Verification

1. Open the CAPA
2. Go to the **Verification** tab
3. Record:

| Field | Description |
|-------|-------------|
| **Verification method** | How effectiveness was checked |
| **Verification criteria** | What would count as effective |
| **Verification date** | When it was checked |
| **Verified by** | Who checked |
| **Verification notes** | What was found |

4. Decide the effectiveness result

!!! warning "Self-verification is refused unless the CAPA allows it"
    If the person verifying is the CAPA's own initiator or assignee, the system
    **refuses** — *"Self-verification is not permitted for this CAPA"*. Independence
    is the default, not a preference.

    It can be allowed per CAPA, and only deliberately: the CAPA must carry
    `allow_self_verification`, which is **off** unless someone turns it on, and the
    verification then also requires a written justification of at least ten
    characters. The record is flagged **self-verified** so an auditor can see which
    CAPAs were closed on their owner's own word.

    The same flag exists on the root cause analysis, for a conductor who
    verifies their own RCA.

### Verification Outcome

| Outcome | Meaning | Next step |
|---------|---------|-----------|
| **Confirmed Effective** | The action worked | The CAPA closes, there and then |
| **Not Effective** | It did not work | Revisit the root cause and raise further action |
| **Inconclusive** | Not yet decidable — the default | Keep monitoring and gather more data |

Inconclusive is the starting state, so a verification that was opened but never
concluded reads as inconclusive rather than as a pass.

## Effectiveness Criteria

The verification record stores the criteria you judged against, in
**Verification criteria**. Write them so someone else can tell whether they were
met — there is no scheduled follow-up review and no review date to set, so the
criteria you record here are the whole of the evidence an auditor will see.

Define measurable criteria:

- Zero recurrence for X months
- Defect rate below Y%
- No related customer complaints
- Process capability maintained

## Prevent Recurrence (D7)

Beyond fixing the immediate issue:

### Horizontal Deployment

Apply learnings to similar:

- Processes
- Products
- Suppliers
- Locations

### Systemic Changes

- Update procedures
- Modify training
- Change specifications
- Implement poka-yoke

### Knowledge Capture

Document lessons learned:

- What happened
- Why it happened
- How it was fixed
- How to prevent in future

## Closing the CAPA

There is no separate closure step and no closure approval. **Recording a
*Confirmed Effective* verification closes the CAPA**, in the same action:

1. Status changes to **Closed**
2. The completion date is set to today
3. A status transition is written with your verification notes

Closing is therefore the verification decision, and it is gated by
`verify_capa`. If you do not hold that permission the system does not refuse
outright — a colleague who does hold it can co-sign in place, by supplying their
email and password on the verification. The verification, and the closure, are
then attributed to **them**, not to you.

!!! note "The Approval tab is not the closure gate"
    A CAPA of **Critical** or **Major** severity does raise a `CAPA_APPROVAL`
    request — but at **creation**, not at closure, and only when your tenant has a
    CAPA_APPROVAL template configured. That is the request you see on the Approval
    tab. Approving it does not close the CAPA, and a CAPA can close whether or not
    it was ever approved.

## Closure Summary

The closure record includes:

| Section | Content |
|---------|---------|
| **Problem Statement** | Original issue |
| **Root Cause** | Verified cause |
| **Corrective Actions** | What was done |
| **Verification** | Proof of effectiveness |
| **Preventive Actions** | Systemic changes |
| **Verification** | Who verified, when, and whether it was self-verified |

## Closed is the end of the line

**A closed CAPA cannot be reopened.** `Closed` is a terminal status — there is no
Reopen action and no transition out of it. If the problem recurs, raise a new
CAPA and reference the old one.

The one route back is *before* closure: a **Not Effective** verification returns
the CAPA from Pending Verification to **In Progress**, marks the root cause
analysis for review, and raises a follow-up corrective task due in 30 days. That
is the only reopening the system does, and it happens because the CAPA never
closed.

## Post-Closure Monitoring

After closure:

1. **Metrics Monitoring**: Watch for recurrence
2. **Audit Inclusion**: Include in quality audits

## CAPA Metrics

Closure-related metrics:

| Metric | Description |
|--------|-------------|
| **On-time closure** | % closed by due date |
| **Average days to close** | Cycle time |
| **First-time effectiveness** | % confirmed on the first verification |
| **Verification compliance** | % with proper verification |

## Regulatory Considerations

For regulated industries:

- **AS9100D**: Clause 10.2 corrective action
- **IATF 16949**: Clause 10.2 problem solving
- **AS9100**: Clause 10.2
- **IATF 16949**: Clause 10.2.3

Ensure documentation meets requirements.

## Permissions

| Permission | Allows |
|------------|--------|
| `verify_capa` | Record the effectiveness outcome — which is what closes the CAPA. Co-signable by a holder when the caller lacks it. |

There is no submit-for-closure action, no closure approval and no reopen, so
`verify_capa` is the only permission in play.

!!! note "`close_capa` and `approve_capa` were removed"
    Both existed as permissions and neither was ever checked. If you meet them
    in an old group export or a procedure document, they granted nothing — the
    control is `verify_capa`.

## Next Steps

- [CAPA Overview](overview.md) - Process reference
- [Quality Reports](../quality/quality-reports.md) - Where CAPAs start
- [Compliance](../../compliance/audit-trails.md) - Audit trail
