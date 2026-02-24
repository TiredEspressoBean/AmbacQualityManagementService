# Document Control

Document management for regulated environments.

## Regulatory Requirements

| Standard | Key Requirements |
|----------|------------------|
| **ISO 9001** | Document control procedure, revision control |
| **ISO 13485** | Controlled documents, approval before release |
| **AS9100D** | Configuration management |
| **21 CFR Part 11** | Electronic records integrity |

## Document Control Features

### Revision Control
- All revisions retained
- Version history tracked
- Changes documented
- Previous versions accessible

### Approval Workflow
- Configurable approval templates
- Electronic signatures
- Approval records retained
- Rejection tracking

### Access Control
- Permission-based access
- Visibility levels (Public, Internal, Confidential)
- Role-based restrictions
- Customer access control

### Audit Trail
- All changes logged
- Who, what, when recorded
- Immutable records

## Document Lifecycle

```
Draft → Review → Approval → Released → Current
                    ↓
                 Rejected → Revision → (back to Review)

Released (previous) → Obsolete
```

### Status Definitions

| Status | Meaning |
|--------|---------|
| **Draft** | Work in progress |
| **Pending Approval** | Submitted for review |
| **Approved/Released** | Official, usable |
| **Obsolete** | Superseded, not for use |
| **Archived** | Retained for records |

## Creating Controlled Documents

1. Upload document
2. Set document type (determines controls)
3. Complete metadata
4. Save as draft
5. Submit for approval
6. Approval workflow proceeds
7. On approval: Released status

## Revision Process

1. Open existing document
2. Click **Create Revision**
3. Upload new file
4. Document change notes
5. Submit for approval
6. On approval:
   - New revision becomes current
   - Previous becomes obsolete

## Change Documentation

For each revision, document:

| Field | Description |
|-------|-------------|
| **Change Summary** | What changed |
| **Reason** | Why the change |
| **Impact** | Affected areas |
| **ECO Reference** | Engineering change order |

## Distribution Control

Track document distribution:

### For Internal Documents
- Available to permitted users
- Access logged
- View tracking (optional)

### For External Distribution
- Controlled copies
- Watermarking (optional)
- Distribution records

## Obsolete Document Handling

When documents become obsolete:
- Clearly marked as obsolete
- Removed from active views
- Retained for historical reference
- Accessible for audit purposes

## Training Integration

Link documents to training:
- Document release triggers training update
- Users notified of new versions
- Training records track acknowledgment

## Periodic Review

Configure document review cycles:

| Setting | Description |
|---------|-------------|
| **Review Interval** | Months between reviews |
| **Owner** | Who reviews |
| **Reminder** | Days before due |

System notifies owners when review due.

## Document Retention

Retention per document type:

| Type | Typical Retention |
|------|-------------------|
| Quality Records | Per regulatory requirements |
| Work Instructions | Life of product + years |
| Certificates | Per certification body |
| Contracts | Per legal requirements |

## Compliance Reports

### Document Status Report
- All documents by status
- Pending approvals
- Overdue reviews

### Revision History Report
- Changes over time
- By document type
- Approval tracking

### Access Report
- Who accessed what
- When accessed
- Download tracking

## Permissions

| Permission | Allows |
|------------|--------|
| `view_documents` | View documents |
| `add_documents` | Create documents |
| `change_documents` | Edit, submit for approval |
| `classify_documents` | Set document classification level |
| `view_confidential_documents` | Access CONFIDENTIAL docs |
| `view_restricted_documents` | Access RESTRICTED docs |
| `view_secret_documents` | Access SECRET docs |
| `respond_to_approval` | Approve documents when assigned |

## Best Practices

1. **Use templates** - Consistent formatting
2. **Clear naming** - Standard conventions
3. **Complete metadata** - Aid searchability
4. **Timely review** - Keep documents current
5. **Train users** - Document control procedures

## Next Steps

- [Document Approval](../workflows/documents/approval.md) - Approval process
- [Document Library](../workflows/documents/library.md) - Using documents
- [Audit Trails](audit-trails.md) - Compliance logging
