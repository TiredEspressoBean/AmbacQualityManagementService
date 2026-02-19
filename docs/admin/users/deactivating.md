# Deactivating Users

Properly offboard users when they leave the organization or no longer need access.

## Why Deactivate (Not Delete)

**Deactivation** is preferred over deletion because:

- **Audit trail preserved** - Historical records show who did what
- **Compliance** - Regulators require identity traceability
- **Data integrity** - Related records remain valid
- **Reversible** - Can reactivate if needed

## Deactivating a User

### Quick Deactivation

1. Navigate to **Data Management** > **Users**
2. Find the user
3. Click the action menu (...)
4. Select **Deactivate**
5. Confirm

### From User Detail

1. Open the user record
2. Uncheck **Active** checkbox
3. Save

## What Happens on Deactivation

When a user is deactivated:

| Effect | Description |
|--------|-------------|
| **Cannot log in** | Immediate access removal |
| **Sessions ended** | Active sessions terminated |
| **Assigned items remain** | Parts, NCRs, etc. keep assignment |
| **History preserved** | Audit trail shows user's name |
| **Hidden from lists** | Doesn't appear in user selection |

## SSO Considerations

If using Single Sign-On:

### Deactivate in IdP First
1. Disable user in Azure AD / Okta
2. User can't authenticate via SSO
3. Deactivate in Ambac Tracker

### Just Ambac Tracker
1. Deactivate in Ambac Tracker
2. User authenticates via SSO but access denied
3. Sees "account deactivated" message

Best practice: Deactivate in both systems.

## Handling Assigned Work

Before deactivating, consider reassigning:

### Active Work Orders
- Reassign to another user
- Or leave assigned (history preserved)

### Open CAPAs
- Reassign CAPA ownership
- Reassign open tasks

### Pending Approvals
- Items awaiting user's approval need reassignment
- Or use backup approver

### Scheduled Reports
- Disable or reassign scheduled reports
- Update email recipients

## Immediate Termination

For urgent access removal:

1. **Deactivate immediately** - No waiting
2. **Change password** (if not SSO) - Prevent stored credentials
3. **End sessions** - Force logout
4. **Notify IT** - Coordinate with other systems
5. **Review recent actions** - Check audit trail

## Bulk Deactivation

For multiple users:

1. Navigate to **Users**
2. Select users (checkboxes)
3. Click **Bulk Actions** > **Deactivate**
4. Confirm

Use for:
- Contractor project end
- Department restructure
- Acquisition transitions

## Reactivating Users

If user needs access again:

1. Navigate to **Users**
2. Show inactive users (filter toggle)
3. Find the user
4. Open user record
5. Check **Active** checkbox
6. Review/update groups
7. Save

User can log in immediately.

## Account vs Access

| Action | Effect | Use When |
|--------|--------|----------|
| **Deactivate** | Can't log in, history preserved | Standard offboarding |
| **Remove from groups** | Logged in but no access | Temporary restriction |
| **Change role type** | Different access level | Role change |

## Compliance Considerations

### Regulated Industries
- Document offboarding process
- Maintain records of when access removed
- Include in audit documentation

### Access Reviews
- Periodic review of active users
- Verify all active users should have access
- Deactivate stale accounts

## Automation

### Integration with HR
- Connect to HR system
- Automatic deactivation on termination
- Sync employment status

### Scheduled Deactivation
- Set future deactivation date
- For contract end dates
- For project-based access

## Audit Trail

Deactivation is logged:
- Who deactivated the user
- When deactivated
- Previous active status

View in Admin > Audit Log.

## Permissions

| Permission | Allows |
|------------|--------|
| `change_user` | Deactivate/reactivate users |
| `view_user` | See inactive users |
| `delete_user` | Permanent deletion (rarely used) |

## Best Practices

1. **Process, not ad-hoc** - Document offboarding steps
2. **Timely** - Remove access promptly
3. **Complete** - All systems, not just Ambac Tracker
4. **Documented** - Record in change log
5. **Reviewed** - Periodic access audits

## Checklist: User Offboarding

- [ ] Identify user to deactivate
- [ ] Reassign active work
- [ ] Reassign pending approvals
- [ ] Update scheduled reports
- [ ] Deactivate in Ambac Tracker
- [ ] Deactivate in SSO (if applicable)
- [ ] Document the change
- [ ] Notify relevant parties

## Next Steps

- [Adding Users](adding.md) - Creating accounts
- [Roles & Groups](roles.md) - Permission management
- [Audit Trail](../../analysis/audit-trail.md) - Review history
