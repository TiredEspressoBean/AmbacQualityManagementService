# Inspection Records

An inspection record is the result of inspecting one part: pass or fail, the
defects found, who found it and where. It is the **evidence**. When the result
is a **Fail**, the part goes on an [NCR](ncrs.md), where the nonconformance is
described and the part's decision is made.

**Quality** > **Inspection Records**.

## Where inspection records come from

**Inspections are recorded in the work instructions.** A substep marked an
**inspection point** writes the inspection record from what the operator
captures as they work: the readings against their limits, the checks, the gauge
used and who signed. That's the normal path, and the strongest evidence, because
the record is tied to the step and its instruction. See [Authoring Work
Instructions](../dwi/authoring.md) and [Running Work
Instructions](../dwi/running.md).

The **Record Inspection** form is the fallback, for a finding outside the
instructions (damage noticed between steps, something seen during an audit) or a
result recorded after the fact. It captures less: no readings against the spec.
To put several parts on one NCR at once, [raise the NCR](ncrs.md#raising-an-ncr-by-hand)
instead.

### Recording one by hand

1. **Quality** > **Inspection Records**, then **Record Inspection**. The form
   reads: *"Record an inspection result. A Fail puts the
   part on an NCR — its open one, or a new one."*
2. Choose the part. **Process Step** fills in with the part's current step (the
   list offers only its process's steps), and **Detected By** with you. Change
   either if it's wrong, complete the form and save.
3. A **Fail** confirms *Inspection recorded · on NCR-…*, with **Open NCR** to go
   straight to it. A Pass confirms *Inspection recorded*.

An operator's Home offers the same form: beside the step they last finished,
**Flag** opens it with the **Part** and **Process Step** filled in and
**Detected By** set to them. A Fail saved there puts the part on an NCR. See
[Operator](../../roles/operator.md).

!!! note "No scan-to-report flow"
    Scanning a barcode does not open an inspection record. The pre-filled form
    comes only from **Flag** on the operator's Home.

## The form

| Field | Required | Description |
|-------|:--------:|-------------|
| **Status** | Yes | **Pending Review**, **Pass**, **Fail**, or **Needs repair (rebuild checks only)** — the last is refused except on a core in rebuild at a check with planned repairs. *"A Fail holds the part and puts it on an NCR, where its decision is made."* |
| **Part** | No | The affected part |
| **Process Step** | No | Where it was found |
| **Machine/Equipment** | No | Equipment involved |
| **Description** | No | Explanation of the issue, up to 300 characters |
| **Detected By** | No | Who found it |
| **Verified By** | No | Who verified it |
| **First Piece Inspection** | No | A flag marking *this* record as the first-piece inspection. It does not link to a separate FPI record. |
| **Archived** | No | Archive the record — only while it is still Pending |

!!! important "A result is final"
    An inspection record can be edited, archived or deleted only while it is
    **Pending Review**. Once it is saved as Pass, Fail or Needs repair it is the
    recorded result, and every edit or delete is refused:

    > &lt;record&gt; is recorded as a result, so it can't be edited or deleted.

    So moving a Pending record to **Fail** is one-way — there is no editing it
    back. A mistaken FAIL is closed as **Not a nonconformance**; see [When the
    finding was wrong](dispositions.md#when-the-finding-was-wrong-not-a-nonconformance)
    and [Putting a Mistake Right](../fixing-mistakes.md).

!!! note "Defects are added separately"
    **Error types are not fields on the record.** Each defect is its own entry
    with an error type, a **count**, a **location**, a **severity**, and notes.
    One record can carry several defects at different severities. The worst of
    them sets the severity of a new NCR.

!!! note "Not on the form"
    There is no quantity-affected, customer-reference, immediate-action, or
    root-cause field. What's wrong across several parts, and containment, live on
    the [NCR](ncrs.md); root cause on the [CAPA](../capa/creating.md).

### Attachments

Add supporting evidence:

- Photos of defect
- Measurement data
- CMM reports
- Customer communication

## Error Types

Error types are a list your administrator builds — each is a name and an
example, optionally limited to one part type. A typical list covers:

| Type | Examples |
|------|----------|
| **Dimensional** | Out of tolerance, wrong size, wrong location |
| **Visual/Cosmetic** | Scratches, dents, discoloration, nozzle tip erosion |
| **Material** | Wrong material, contamination, defective raw material |
| **Functional** | Doesn't work, fails test, spray pattern asymmetry, flow rate out of spec |
| **Documentation** | Missing paperwork, wrong revision, labeling error |
| **Process** | Wrong operation, missed step, wrong sequence |

Your administrator configures available error types.

!!! example "Diesel Injector Example"
    For a fuel injector failing its flow test, against an example spec of
    100–140 mL/min: Error Type = **Functional**, Description = "Flow rate 142 mL/min
    (spec 100–140 mL/min)", Severity = **Major**.

## Severity Levels

| Level | Definition | Examples |
|-------|------------|----------|
| **Minor** | Cosmetic, no functional impact | Light scratch, minor documentation |
| **Major** | Out of spec, may affect function | Dimensional error, material deviation |
| **Critical** | Safety risk or regulatory violation | Cracked safety component, wrong material in medical device |

A defect's severity sets the severity of the **NCR** the part goes on: the
worst defect recorded, or Major when none is. That's where severity binds: no
decision under a Critical or Major NCR closes until its containment is
recorded. See [NCRs](ncrs.md#containment).

## Status

| Status | Meaning | Next Action |
|--------|---------|-------------|
| **Pending** | Inspection not yet complete | Complete inspection |
| **Pass** | Part passed inspection | Continue production |
| **Fail** | Part failed inspection | It's on an NCR, where it's decided |
| **Needs repair** | At a rebuild check, the component needs planned repair work — inspected, not failed | Repair it; no NCR opens |

!!! info "What a Fail sets off"
    A record reaching **Fail** quarantines the part, alerts the step, updates
    sampling, and puts the part on an NCR: its open one, or a new one. It does
    this once, on the move into Fail, whether the record was created as Fail or
    edited to Fail from Pending. See [How an NCR opens](ncrs.md#how-an-ncr-opens).

## The NCR and the decision

A failed inspection record's page has an **NCR** card: *"This failure is on
NCR-… . The decision on the part, and whether a CAPA is needed, are made
there."* The part's decision is its [disposition](dispositions.md) under that
NCR, and whether the nonconformance needs a CAPA is the NCR's [CAPA
decision](ncrs.md#capa).

## Searching inspection records

Find existing records:

- By status — **Pending**, **Pass**, **Fail** or **Needs repair** (an inspection
  record doesn't close; its NCR does)
- By part
- By step
- By work order
- Search by description or part ERP ID

To find failed records by error type, period, process or part type, use the
**Defect Records** page (`/quality/defects`), opened from **Analytics** >
**Defect Patterns**. Its CSV includes each defect's NCR.

## Metrics

- **NCR Analysis** (`/quality/ncr-analysis`): NCRs opened and closed, **Avg
  Age**, **Closure Rate**, the ageing buckets and the disposition breakdown
- **Defect Analysis** (`/quality/defects`): defects by error type, process and
  part, with CSV export
- **Analytics**: first-pass yield, top defects, what needs attention

See [Dashboards](../../analysis/dashboard.md).

## Notifications

Notifications are **rule-driven and configurable**. See [Notification
Rules](../../admin/setup/notification-rules.md).

By default, **step failures** go to QA Manager and QA Inspector, and each **NCR
opened** goes to the QA Manager group, once per NCR, not once per part. See
[NCRs](ncrs.md#notifications).

## Permissions

| Permission | Allows |
|------------|--------|
| `view_qualityreports` | View inspection records |
| `add_qualityreports` | Record inspections |
| `change_qualityreports` | Edit records that are still Pending Review |

!!! note "An inspection record is not approved"
    There is no approval step on an inspection record, so there are no approve
    permissions either. The authorized act is the part's **decision** on its
    NCR, gated by `approve_disposition`. That is where the authority to accept
    a nonconformance sits.

!!! note "Where self-approval is controlled"
    Not here. Each approval **template** carries **Allow Self-Approval**, off by
    default; where a tenant turns it on, the approver must also write a
    justification. See
    [Approval Templates](../../admin/setup/approval-templates.md).

## Next Steps

- [NCRs](ncrs.md) - The nonconformance a failed record goes on
- [Dispositions](dispositions.md) - Making disposition decisions
- [Quarantine](quarantine.md) - Managing held parts
- [CAPA Overview](../capa/overview.md) - Corrective actions
- [Defect Analysis](../../analysis/defects.md) - Quality analytics
