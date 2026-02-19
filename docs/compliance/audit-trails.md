# Audit Trails

Comprehensive audit logging for regulatory compliance.

## Compliance Requirements

Audit trails are required by:

| Standard | Requirement |
|----------|-------------|
| **ISO 9001** | Records of monitoring and measurement |
| **ISO 13485** | Device history records |
| **21 CFR Part 11** | Audit trail, computer-generated timestamps |
| **AS9100D** | Configuration management, traceability |
| **IATF 16949** | Process control records |

## What is Logged

### All Record Changes
Every create, update, delete is logged:
- What changed (before/after values)
- Who made the change
- When (timestamp)
- System information

### Authentication Events
- Login attempts (success/failure)
- Logout events
- Session timeouts
- Password changes

### Electronic Signatures
- Who signed
- What was signed
- Timestamp
- Signature meaning

### Permission Changes
- Group assignments
- Permission grants/revocations
- User status changes

## Audit Trail Characteristics

### Immutability
Audit records cannot be:
- Modified
- Deleted
- Backdated

Protected at database level with triggers.

### Computer-Generated Timestamps
- Server-side timestamp (not client)
- UTC timezone
- Synchronized time source
- Cannot be altered by users

### User Attribution
- Unique user identification
- Cannot use shared accounts
- Session tracking

## Viewing Audit Data

### System Audit Log
Navigate to **Admin** > **Audit Log**

Full system audit trail with filtering:
- By user
- By record type
- By action type
- By date range

### Record History
On any record, view **History** tab:
- All changes to that record
- Chronological order
- Full change details

## Audit Reports

### Standard Reports
- User activity report
- Change summary report
- Access log report
- Signature report

### Custom Reports
Build reports for audits:
1. Filter to relevant data
2. Select columns
3. Export PDF or CSV

### Scheduled Reports
Automate regular audit reports:
- Daily activity summary
- Weekly change report
- Monthly compliance report

## Regulatory Mappings

### 21 CFR Part 11
| Requirement | Implementation |
|-------------|----------------|
| Secure, computer-generated timestamps | Server-side UTC timestamps |
| Audit trail for changes | All changes logged |
| Record of operator identity | User ID on all records |
| Previous values retained | Before/after values stored |

### ISO 13485
| Requirement | Implementation |
|-------------|----------------|
| Device history records | Part history with all events |
| Change records | Full change logging |
| Traceability | Part-to-lot-to-material tracking |

## Data Retention

Audit logs retained per policy:

| Industry | Typical Retention |
|----------|-------------------|
| Medical Devices | Life of device + 2 years |
| Aerospace | 10+ years |
| Automotive | 15+ years |
| General | 7 years minimum |

Audit logs are never auto-deleted.

## Export for Auditors

Prepare data for external audits:

1. Filter to audit scope
2. Export to PDF or CSV
3. Include all relevant records
4. Provide in auditor-requested format

## Permissions

| Permission | Allows |
|------------|--------|
| `view_auditlog` | View full audit trail |
| `export_auditlog` | Export audit data |

Standard users see history of records they can access.

## Best Practices

1. **Review regularly** - Spot anomalies early
2. **Prepare reports** - Have audit data ready
3. **Train users** - Understanding of requirements
4. **Test procedures** - Verify logging works
5. **Protect access** - Limit audit log access

## Next Steps

- [Electronic Signatures](signatures.md) - Signature compliance
- [Document Control](document-control.md) - Document management
- [Export Controls](export-controls.md) - ITAR/EAR compliance
