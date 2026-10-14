# Deactivating Users

Properly offboard users when they leave the organization or no longer need access.

## Why Deactivate (Not Delete)

**Deactivation** is preferred over deletion because:

- **Audit trail preserved** - Historical records show who did what
- **Compliance** - Regulators require identity traceability
- **Data integrity** - Related records remain valid
- **Reversible** - Can reactivate if needed

!!! important "Deleting a user does this anyway"
    **Delete** on a user list does not destroy anything. It **removes their
    access to this organisation** by suspending their membership — the account
    survives, and so does everything they recorded: training, approvals,
    signatures.

    Reactivate them from **User Management**. The Data Management Users list
    shows them as **Access removed**.

    You cannot remove your own access.

    So the choice is not *delete or deactivate* — both lead to the same safe
    place, which is why the compliance argument above holds either way.

## Removing someone's access

1. Navigate to **Admin** > **User Management**
2. Find the user
3. Use **Delete** on the user list
4. Confirm

There is no *Deactivate* action and no **Active** checkbox. **Delete** is what
removes access, and despite the name it destroys nothing.

## What happens

| Effect | Description |
|--------|-------------|
| **Cannot log in** | Their membership of this organisation is suspended |
| **Assigned items remain** | Parts, NCRs and the rest keep their assignment |
| **History preserved** | The audit trail still shows their name |
| **Still listed** | They remain in the Data Management Users list, badged **Access removed** — they are not hidden |

## SSO Considerations

If using Single Sign-On:

### Deactivate in IdP First
1. Disable user in Microsoft Entra ID / Okta
2. User can't authenticate via SSO
3. Deactivate in uqmes

### Just uqmes
1. Deactivate in uqmes
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

### Reports
- Review any reports owned by this user
- Reassign ownership if needed

## Immediate Termination

For urgent access removal:

1. **Delete them on the user list** — this takes effect immediately
2. **Notify IT** — coordinate with other systems, and with your IdP if they
   sign in through SSO
3. **Review recent actions** — check the audit trail

!!! note "There is no force-logout or password-reset control"
    uqmes has no administrative "end sessions" or "change this user's password"
    action. Removing their access is the control you have; anything beyond it
    belongs to your identity provider.

## Bulk Deactivation

For multiple users:

1. Navigate to **Admin** > **User Management**
2. Click **Bulk Actions**
3. Add a row per user (**Manual entry**) or **Upload workbook** for a batch
4. Set their status, then click **Apply rows**

Use for:
- Contractor project end
- Department restructure
- Acquisition transitions

## Reactivating Users

If user needs access again:

1. Navigate to **Admin** > **User Management**
2. Find the user — they are still listed, badged **Access removed**
3. Reactivate them
4. Review and update their groups

They can log in immediately.

## Account vs Access

| Action | Effect | Use When |
|--------|--------|----------|
| **Delete** on the user list | Can't log in; history preserved; row stays, badged *Access removed* | Standard offboarding |
| **Remove from groups** | Still logged in, but nothing they can do | Temporary restriction |

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

!!! note "Planned Features"
    HR system integration and scheduled deactivation are planned for future releases. Currently, user deactivation is a manual process.

## Audit Trail

Deactivation is logged:
- Who deactivated the user
- When deactivated
- Previous active status

View in Admin > Audit Log.

## Permissions

| Permission | Allows |
|------------|--------|
| `change_user` | Deactivate and reactivate users |
| `view_user` | See inactive users |
| `delete_user` | Use **Delete** on the user list, which suspends their membership of this organisation. It does **not** destroy the account — see the note at the top of this page. |

!!! note "You cannot remove your own access"
    Removing yourself is refused: *"You can't remove your own access."* Worth
    knowing if you are the only administrator — you cannot lock yourself out this
    way, and you cannot hand over by removing yourself. Add the other person and
    give them what they need first.

## Checklist: User Offboarding

- [ ] Identify user to deactivate
- [ ] Reassign active work
- [ ] Reassign pending approvals
- [ ] Review user's reports and reassign if needed
- [ ] Deactivate in uqmes
- [ ] Deactivate in SSO (if applicable)
- [ ] Document the change
- [ ] Notify relevant parties

## Next Steps

- [Adding Users](adding.md) - Creating accounts
- [Roles & Groups](roles.md) - Permission management
- [Audit Trail](../../analysis/audit-trail.md) - Review history
