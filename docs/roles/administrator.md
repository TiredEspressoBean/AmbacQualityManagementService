# Administrator Guide

This guide is for the person who configures uqmes for their facility, manages
users and maintains system settings.

!!! important "You are a Tenant Admin, not a System Admin"
    These are two different seats and only one of them is yours.

    | Group | Who holds it | Scope |
    |-------|--------------|-------|
    | **Tenant Admin** | Your facility's administrator — **this guide** | Everything inside your organisation |
    | **System Admin** | The platform operator | Every tenant on the platform |

    Tenant Admin is the widest role *in your organisation*: it is the union of
    every other role, plus user and group management, the secret document tier
    and the compliance permissions. It is not a platform seat, and it cannot see
    or touch another organisation's data.

    If something in this guide isn't available to you, check you are in **Tenant
    Admin** rather than a narrower group.

## Your Role

As an Administrator, you:

- Manage user accounts and permissions
- Configure processes and workflows
- Set up system master data
- Maintain integrations
- Monitor system health
- Support users with access issues

## Getting Started

### First-Time Setup

For a new uqmes instance:

1. [ ] Configure organization settings
2. [ ] Review the groups your organisation starts with, and adjust their
   permissions if your roles differ
3. [ ] Add initial users
4. [ ] Set up companies (customers/suppliers)
5. [ ] Define part types
6. [ ] Create manufacturing processes
7. [ ] Configure document types
8. [ ] Set up error types
9. [ ] Define sampling rules (if needed)
10. [ ] Configure approval templates

### Your Main Pages

| Page | Location | Purpose |
|------|----------|---------|
| **Settings** | Admin > Settings | Organization config |
| **Data Management** | Admin > Data Management | All editors |
| **Audit Log** | Admin > Audit Log | System activity |
| **Users** | Admin > User Management | User accounts, invites, bulk actions |
| **Groups** | Data Management > User Groups | Permission groups |

## User Management

### Adding Users

1. Navigate to **Admin** > **User Management**
2. Click **Add user**
3. Fill in:
   - Username — the login identifier
   - Email, first and last name
   - Groups, and job role
4. Save

Creating a user sends nothing. To let them in, use **Copy access link** on
their row and send it to them — or **Send invitation**, if this deployment
sends mail. See [Adding Users](../admin/users/adding.md).

### Managing Groups

1. Navigate to **Data Management** > **User Groups**
2. Create/edit groups
3. Assign permissions to groups
4. Assign users to groups

### Permission Strategy

- Create groups matching job roles
- Assign permissions to groups (not users)
- Users get permissions via group membership
- Use principle of least privilege

### Deactivating Users

When employees leave:
1. Go to **Admin** > **User Management**
2. Open their row menu and choose **Deactivate**

Their access to this organisation is suspended; the account and everything they
recorded is kept. See [Deactivating Users](../admin/users/deactivating.md).

## Process Configuration

### Creating Processes

1. Go to **Data Management** > **Processes** and click **New Process**
2. Build its steps and their connections in **Process Flow** — a routing is a
   graph, not a numbered list
3. Configure each step's requirements and measurements
4. **Submit for approval** — always required, and refused if the organisation
   has no `PROCESS_APPROVAL` template

### Step Configuration

For each step:
- Name and description
- Measurement requirements
- Document requirements
- Training requirements
- FPI settings
- Sampling rules

### Process Versioning

- Create new version for changes
- Approve before it can be used
- The previous version stops being current and drops out of the process lists
- In-flight work continues on the old version

## Master Data Setup

### Part Types

1. Navigate to **Data Management** > **Part Types**
2. Create part types for your products
3. Set attributes

A part type carries no process. The link runs the other way: each process names
the part type it is for, so you attach processes from **Processes**.

### Equipment

1. Navigate to **Data Management** > **Equipment**
2. Create equipment records
3. Set up equipment types
4. Configure calibration tracking

### Error Types

1. Navigate to **Data Management** > **Error Types**
2. Define defect categories — name, example, the part type it applies to, and
   whether it requires a 3D annotation

Error types are a flat list. There is no hierarchy, and severity is chosen on
each recorded defect rather than defaulted from the catalog.

### Document Types

1. Navigate to **Data Management** > **Document Types**
2. For each type set:
   - **Requires approval** — whether documents of this type must be released
     through an approval before they count as current
   - **Default review period** — how often they come up for periodic review.
     **A type with no review period never prompts one**, which is the usual
     reason a *Due for review* tile stays empty
   - **Default retention** — how long they must be kept
   - **Approval template** — optional. Leave it blank and the type uses
     **Document Release**; set it to route this type through a different
     approval instead

A full catalogue ships by default — 39 types covering
procedures, drawings, supplier certificates, quality records, calibration,
training and the IATF/AS9100 set (PPAP, PSW, FMEA, 8D, FAI). Prune or extend it
rather than starting from nothing.

### Approval Templates

1. Navigate to **Data Management** > **Approval Templates**
2. Configure the approval **types** the product raises:
   - **Document Release**
   - **Critical CAPA**, **Major CAPA** and the general **CAPA Approval** — the
     authorisation a CAPA needs *before* work begins, chosen by its severity
   - **PCR**, **PCO** and **PCN** — the process-change chain
3. For each: who is assigned, whether self-approval is allowed, how long it has
   and when it escalates

!!! warning "Two things people expect here and won't find"
    **Disposition approval** and **CAPA closure** have no templates. A
    disposition is recorded and co-signed in place by someone holding
    `approve_disposition`; closure follows from verifying a CAPA's
    effectiveness. Neither is routed as an approval request, so neither can be
    configured here.

!!! danger "Group names must match exactly"
    A template assigns approvers by **group name**, matched exactly. A name that
    matches nothing assigns the approval to **nobody** — silently, because a
    filter that finds nothing is not an error.

    Group names carry no underscores: *QA Manager*, *Document Controller*,
    *Tenant Admin*. After editing a template, check it actually resolves to
    people before relying on it.

## System Settings

### Organization Settings

Navigate to **Admin > Settings**:
- Organization name
- Contact email, phone, website and address
- Shop floor timezone
- Change control mode
- Over-receipt tolerance
- Logo

### Integration Settings

Configure:
- SSO / Microsoft Entra ID
- HubSpot connection
- API access

### Notification Settings

Under **Settings**:
- **Notifications** — what event tells whom, through which channel
- **Notification Defaults** — what a new user receives until they change it

See [Notification Rules](../admin/setup/notification-rules.md).

## Monitoring & Maintenance

### Audit Log Review

Regularly review **Admin** > **Audit Log**:
- User activity
- Permission changes
- Unusual patterns

!!! note "Failed logins are not recorded"
    A rejected sign-in leaves no trace in the audit log. If you need to
    investigate repeated failures, that evidence has to come from your identity
    provider or the web server, not from uqmes.

### System Health

uqmes has no system-health page: no adoption, performance, error or storage
figures. Those come from wherever this deployment is hosted.

### Periodic Tasks

**Weekly:**
- [ ] Review new user requests
- [ ] Check pending access issues

**Monthly:**
- [ ] Permission audit
- [ ] Deactivate stale accounts
- [ ] Review group configurations
- [ ] Check integration health

**Quarterly:**
- [ ] Full permission review
- [ ] Process configuration audit
- [ ] User training needs

## Troubleshooting

### User Can't Log In

Check:
1. Their access to this organisation is active, not deactivated
2. They are using the right username or email
3. If they use SSO, that your identity provider is set up for them
4. They have not hit the rate limit — by default ten login attempts a minute
   from one address; it clears by itself. There is no password expiry and no
   account lockout

### Permission Issues

1. Check user's groups
2. Verify the group has the permission
3. For approvals, check the **approval template** assigns them — permission
   alone does not make someone an approver
4. A permission newly added to the product reaches an existing organisation only
   after `sync_tenant_permissions` — see [Permissions](../admin/users/permissions.md)

### Integration Issues

1. Check connection status
2. Verify credentials
3. Review error logs
4. Test connectivity

## Security

### Best Practices

- Regular permission reviews
- Prompt user deactivation
- Strong password policies
- SSO with MFA when possible
- Audit log monitoring

### Compliance

- Maintain audit trails
- Document configuration changes
- Regular access reviews
- Incident response procedures

## Supporting Users

### Common Requests

| Request | Action |
|---------|--------|
| Password reset | The reset link on the login page — or, if mail does not arrive, **Copy access link** on their row, which lets them set a new one |
| Permission change | Modify group membership |
| New account | Create user, assign groups |
| Access issue | Check permissions and group membership |

### Escalation

When you can't resolve:
- Platform issues: whoever hosts this deployment, under whatever support
  arrangement your organisation has
- Integration issues: Coordinate with IT
- Compliance questions: Involve QA Manager

## Quick Reference

| Task | Location |
|------|----------|
| Add user | Admin > User Management > **Add user** |
| Create group | Data Management > User Groups > **New User Groups** |
| Edit permissions | Groups > [Group] > Permissions |
| Configure process | Data Management > Processes, then Process Flow |
| View audit log | Admin > Audit Log |
| System settings | Admin > Settings |
| Put back someone suspended by mistake | User Management → tick their row → **Activate** in the bar above the list |

## Related Documentation

- [Adding Users](../admin/users/adding.md)
- [Roles & Groups](../admin/users/roles.md)
- [Process Configuration](../admin/processes/overview.md)
- [System Setup](../admin/index.md)
- [Audit Trails](../compliance/audit-trails.md)
