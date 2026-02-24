# Export Controls

ITAR and EAR compliance features for defense and controlled articles.

## Regulatory Overview

| Regulation | Scope |
|------------|-------|
| **ITAR** | Defense articles, technical data |
| **EAR** | Dual-use items, commercial with military application |
| **UK Export Control** | UK defense and dual-use |

## ITAR Features

### Part-Level Controls

| Field | Description |
|-------|-------------|
| **ITAR Controlled** | Flag indicating defense article |
| **ECCN** | Export Control Classification Number |
| **Export License Required** | License needed for export |
| **Country of Origin** | Manufacturing location |

### User-Level Controls

| Field | Description |
|-------|-------------|
| **Citizenship** | User's citizenship (ISO country code) |
| **US Person** | ITAR "US Person" status |
| **UK Person** | UK Export Control authorization |
| **Export Control Verified** | Verification status |
| **Verified By** | Who verified |
| **Verified Date** | When verified |

## US Person Definition

Under ITAR, a "US Person" is:
- US citizen
- US permanent resident (green card)
- Protected individual under asylum
- Organization incorporated in US

Non-US Persons require licenses for ITAR access.

## Access Control

### Automatic Restrictions

For ITAR-controlled parts:
- Only US Persons can access
- Non-US Persons see access denied
- Access attempts logged

### Manual Verification

Before granting ITAR access:
1. Verify user's citizenship status
2. Confirm US Person qualification
3. Mark user as verified
4. Record verifier and date

## Part Classification

### Marking Parts as ITAR

1. Edit part type or part
2. Set **ITAR Controlled** = Yes
3. Enter ECCN if applicable
4. Save

### ECCN Assignment

Export Control Classification Numbers:
- 0A001 (example: weapons)
- 9A515 (example: spacecraft)
- EAR99 (no specific control)

Consult export control counsel for proper classification.

## Audit Trail

All ITAR-related events logged:
- Access to controlled parts
- User verification changes
- Classification changes
- Denied access attempts

## Compliance Workflow

### Onboarding Users

1. Collect citizenship documentation
2. Verify US Person status
3. Update user record
4. Mark as export control verified
5. Record verification

### Accessing ITAR Parts

1. User attempts access
2. System checks user's export control status
3. If US Person verified: access granted
4. If not: access denied, event logged

## Document Control

For ITAR-controlled documents:
- Visibility limited to US Persons
- Download tracking
- Watermarking (if configured)
- Distribution records

## Reporting

### ITAR Compliance Report
- Users with ITAR access
- Verification status
- Parts under ITAR control
- Access log

### Access Audit
- Who accessed ITAR parts
- When
- What was accessed

## Country Restrictions

Configure country-based restrictions:
- Denied parties screening
- Embargoed countries
- License requirements by destination

## Permissions

| Permission | Allows |
|------------|--------|
| `verify_export_control` | Verify user export status (mark as US Person) |
| `change_export_classification` | Modify ITAR/ECCN classification on documents |

Note: Access to ITAR-controlled items is determined by the user's `us_person` attribute, not a permission. The `ExportControlService` automatically filters querysets based on user export control status.

## Best Practices

1. **Train staff** - ITAR awareness training
2. **Verify promptly** - Don't delay verification
3. **Document everything** - Audit trail matters
4. **Regular review** - Periodic access review
5. **Consult experts** - Export counsel for questions

## Compliance Notes

!!! warning "Legal Requirements"
    Export control violations carry serious penalties. This system supports compliance but does not replace proper export control procedures and legal counsel.

## Next Steps

- [User Management](../admin/users/adding.md) - User export verification
- [Audit Trails](audit-trails.md) - Access logging
- [Part Types](../admin/setup/part-types.md) - ITAR classification
