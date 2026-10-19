# Deactivating Users

Properly offboard users when they leave the organization or no longer need access.

## Why Deactivate (Not Delete)

**Deactivation** is preferred over deletion because:

- **Audit trail preserved** - Historical records show who did what
- **Compliance** - Regulators require identity traceability
- **Data integrity** - Related records remain valid
- **Reversible** - Can reactivate if needed

!!! important "There is no route that destroys an account"
    This is not a policy you have to remember — it is what the system does.
    Both ways out suspend the person's **membership of this organisation**: the
    account survives, and so does everything they recorded. Training, approvals
    and signatures all keep their name.

    **Delete** on the Data Management users list does the same thing as
    **Deactivate** in User Management. Despite the name it destroys nothing, and
    it is reversible from User Management either way.

    You cannot do it to yourself.

## Removing someone's access

1. Navigate to **Admin** > **User Management**
2. Find the user
3. Open their row menu and choose **Deactivate**

To put them back, the same menu offers **Activate**. Several at once: tick them
and use the bulk bar.

!!! note "This is per organisation, not the whole account"
    Deactivating suspends their membership *here*. It does not disable the
    underlying account, and someone who belongs to another organisation keeps
    their access there.

## What happens

| Effect | Description |
|--------|-------------|
| **Cannot log in** | Their membership of this organisation is suspended |
| **Assigned items remain** | Parts, NCRs and the rest keep their assignment |
| **History preserved** | The audit trail still shows their name |
| **Still listed** | They are not hidden. User Management badges them **Inactive**; the Data Management users list says **Access removed** |

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

1. **Deactivate them in User Management** — this takes effect immediately
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
2. Tick the people in the list
3. Use **Deactivate** on the bulk bar that appears

For a long list from somewhere else — a leavers report, a contract ending —
**Bulk Actions** takes a workbook instead, with a status per row, and reconciles
existing people to match it.

Use for:
- Contractor project end
- Department restructure
- Acquisition transitions

## Reactivating Users

If user needs access again:

1. Navigate to **Admin** > **User Management**
2. Find the user — they are still listed, badged **Inactive**. The **Inactive**
   filter narrows the list to them
3. Open their row menu and choose **Activate**
4. Review and update their groups

They can log in immediately.

## Account vs Access

| Action | Effect | Use When |
|--------|--------|----------|
| **Deactivate** | No access to this organisation; history preserved; the row stays, badged *Inactive* | Standard offboarding |
| **Delete** on the Data Management list | The same thing under a different name | Never deliberately — prefer Deactivate, so the next person reading the audit log is not misled |
| **Remove from groups** | Can still log in, but has nothing to do | Temporary restriction, or a change of job |

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

The membership record itself carries **when** it was suspended and **by whom**,
and the change is in the audit log like any other.

!!! warning "Reactivating clears those two fields"
    Putting someone back wipes the suspended-at and suspended-by values from
    their membership — the record describes the present, not the past. So a
    person who was offboarded and later returned shows no sign of it there.

    The [audit log](../../analysis/audit-trail.md) is where that history
    survives. If you need to answer *when did they lose access and who removed
    it?* about someone currently active, that is the only place with the answer.

## Permissions

| Permission | Allows |
|------------|--------|
| `change_user` | Deactivate and reactivate users |
| `view_user` | See inactive users |
| `delete_user` | **Delete** on the Data Management list — which suspends membership, exactly as Deactivate does |

By default only **Tenant Admin** holds these.

!!! note "You cannot remove your own access"
    Both routes refuse it — Delete answers *"You can't remove your own access,"*
    and a bulk deactivation silently skips you, so the count it reports may be
    one lower than the number you ticked.

    Worth knowing if you are the only administrator: you cannot lock yourself
    out this way, and you cannot hand over by removing yourself. Add the other
    person and give them what they need first.

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
