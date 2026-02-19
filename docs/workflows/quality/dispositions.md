# Dispositions

Dispositions are decisions about what to do with non-conforming parts. This guide covers the disposition workflow.

## What is a Disposition?

A **disposition** is the formal decision about how to handle a part that doesn't meet specifications:

- Can it be used anyway?
- Can it be fixed?
- Must it be scrapped?
- Should it be returned to the vendor?

## Disposition Options

| Disposition | Code | When to Use |
|-------------|------|-------------|
| **Use As Is** | UAI | Non-conformance doesn't affect function or safety |
| **Rework** | RWK | Part can be corrected and re-inspected |
| **Scrap** | SCR | Part cannot be used or repaired |
| **Return to Vendor** | RTV | Supplier responsible, return for credit/replacement |
| **Deviate** | DEV | Customer approves deviation from spec |

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
| Scrap (high value) | Yes |
| Use As Is | Yes (engineering/quality) |
| Deviate | Yes (customer + internal) |
| RTV | Sometimes |

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
| **Disposition** | UAI, Rework, Scrap, RTV, Deviate |
| **Justification** | Why this decision |
| **Parts** | Which parts (all or select) |
| **Rework Instructions** | For rework: what to do |
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
| Use As Is | Quality Engineer |
| Rework | Production Supervisor |
| Scrap (low value) | Quality Inspector |
| Scrap (high value) | Quality Manager |
| Deviate | Customer + Quality Manager |

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

## Customer Deviations

For deviations requiring customer approval:

1. Select **Deviate** disposition
2. Enter deviation request details
3. System generates deviation request
4. Send to customer for approval
5. Customer approves/rejects
6. Record customer response
7. Execute if approved

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
