# Dispositions

Dispositions are decisions about what to do with non-conforming parts. This guide covers the disposition workflow.

!!! example "Demo Dispositions"
    In demo mode, three dispositions demonstrate the workflow:

    - **QD-2024-0001** (Rework): INJ-0042-017 failed flow test (142 mL/min vs 135 max), sent to nozzle rework step
    - **QD-2024-0002** (Use As Is): INJ-0042-019 minor cosmetic scratch, approved by QA Manager with customer concurrence
    - **QD-2024-0003** (Scrap): INJ-0042-023 cracked body detected at inspection, cannot be repaired

    QA Manager Maria Santos handles all disposition approvals. Production Manager Jennifer Walsh tracks rework progress.

## What is a Disposition?

A **disposition** is the formal decision about how to handle a part that doesn't meet specifications:

- Can it be used anyway?
- Can it be fixed?
- Must it be scrapped?
- Should it be returned to the vendor?

## Disposition Options

| Disposition | Code | When to Use |
|-------------|------|-------------|
| **Use As Is** | USE_AS_IS | Non-conformance doesn't affect function or safety |
| **Rework** | REWORK | Part can be corrected and re-inspected to full conformance |
| **Repair** | REPAIR | Part corrected but may deviate from spec (AS9100: requires approval) |
| **Scrap** | SCRAP | Part cannot be used or repaired |
| **Return to Supplier** | RETURN_TO_SUPPLIER | Supplier responsible, return for credit/replacement |

!!! info "Rework vs Repair (AS9100)"
    Rework restores full conformance. Repair may result in a part that deviates from original specs but is still acceptable for use (requires engineering approval).

## Disposition Workflow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Quality   │────▶│  Disposition│────▶│   Execute   │
│   Report    │     │   Decision  │     │  Decision   │
└─────────────┘     └─────────────┘     └─────────────┘
                          │
                          ▼
                    ┌─────────────┐
                    │   Approval  │
                    │ (if needed) │
                    └─────────────┘
```

### Step 1: Quality Report Created

A quality report documents the non-conformance and affected parts.

### Step 2: Investigation

Review the issue:

- What exactly is wrong?
- How many parts affected?
- What caused it?
- What are the options?

### Step 3: Disposition Decision

Select the disposition:

1. Open the quality report
2. Go to **Disposition** section
3. Select disposition type
4. Enter justification
5. Select parts (if partial disposition)
6. Submit

### Step 4: Approval (if required)

Some dispositions require approval:

| Disposition | Approval Required |
|-------------|-------------------|
| **Use As Is** | Yes (customer approval auto-required) |
| **Repair** | Yes (customer approval auto-required) |
| **Scrap** | Configurable by value threshold |
| **Return to Supplier** | Configurable |
| **Rework** | No (unless configured) |

### Step 5: Execution

After approval:

- **Use As Is**: Parts released, continue production
- **Rework**: Parts routed to rework step
- **Scrap**: Parts marked scrapped, removed from active
- **RTV**: Parts tagged for return, RMA created

## Making a Disposition

1. Open the quality report
2. Review affected parts
3. Click **Make Disposition**
4. Select disposition type
5. Fill in required fields:

| Field | Description |
|-------|-------------|
| **Disposition** | Use As Is, Rework, Repair, Scrap, or Return to Supplier |
| **Justification** | Why this decision |
| **Parts** | Which parts (all or select) |
| **Rework/Repair Instructions** | For rework/repair: what needs to be done |
| **Approval Required** | Auto-set based on rules |

6. Submit

## Partial Disposition

Different parts may get different dispositions:

1. Open quality report with multiple parts
2. Select subset of parts
3. Make disposition for selected
4. Repeat for remaining parts

Example:
- 5 parts: 3 rework, 2 scrap

!!! tip "Demo: Partial Disposition"
    Quality Report QR-2024-0187 for ORD-2024-0038 shows partial disposition in action: 3 parts sent to rework (nozzle adjustment), 2 parts scrapped (cracked bodies). This contributed to CAPA-2024-003 when the pattern indicated a systemic supplier issue.

## Disposition Approval

When approval is required:

1. Disposition is submitted
2. Request goes to approver(s)
3. Approver reviews and approves/rejects
4. If approved, disposition executes
5. If rejected, returns to requester

### Approval Levels

| Disposition | Typical Approver |
|-------------|------------------|
| Use As Is | Quality Manager + Customer |
| Repair | Quality Manager + Customer |
| Rework | Production Supervisor |
| Scrap | Quality Manager (based on value) |
| Return to Supplier | Quality Manager |

### Approval Records

All approvals are recorded:

- Who approved
- When approved
- Electronic signature (password verified)
- Comments

## Disposition Execution

### Use As Is

1. Parts are released from quarantine
2. Continue to next step
3. Record attached to part history

### Rework

1. Parts routed to rework step (specified in process)
2. Rework operation performed
3. Re-inspection required
4. Pass: Continue production
5. Fail: New disposition needed

### Scrap

1. Parts marked as scrapped
2. Removed from active production
3. Physical segregation
4. Disposal per procedures
5. Cost captured (if tracked)

### RTV

1. Parts tagged for return
2. RMA/credit request generated
3. Awaiting supplier pickup
4. Closed when returned

## Customer Approval

For dispositions requiring customer approval (Use As Is, Repair):

1. The system automatically flags these for customer approval
2. Enter justification and deviation details
3. Contact customer through your normal channels
4. Record customer response in the system
5. Execute if approved

## Disposition Metrics

Track disposition patterns:

- **Disposition by type**: What outcomes are most common
- **Scrap rate**: Cost of quality
- **Rework rate**: Efficiency impact
- **Time to disposition**: Cycle time

## Disposition History

View disposition history:

- On the part record
- On the quality report
- In disposition reports
- Audit trail

## Permissions

| Permission | Allows |
|------------|--------|
| `view_disposition` | View disposition records |
| `add_disposition` | Make disposition decisions |
| `approve_disposition` | Approve dispositions |

## Best Practices

1. **Decide promptly** - Quarantine ties up inventory
2. **Document thoroughly** - Justification matters for audits
3. **Consider cost** - Rework vs scrap economics
4. **Follow procedures** - Use defined criteria
5. **Escalate appropriately** - Get right approvals

## Next Steps

- [Quarantine](quarantine.md) - Managing held parts
- [Quality Reports](quality-reports.md) - Creating NCRs
- [CAPA Overview](../capa/overview.md) - Corrective actions
