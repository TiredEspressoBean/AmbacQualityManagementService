# Administrator Guide

This guide is for System Administrators who configure Ambac Tracker, manage users, and maintain system settings.

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

For a new Ambac Tracker instance:

1. [ ] Configure organization settings
2. [ ] Create user groups with permissions
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
| **Users** | Data Management > Users | User management |
| **Groups** | Data Management > Groups | Permission groups |

## User Management

### Adding Users

1. Navigate to **Data Management** > **Users**
2. Click **+ New User**
3. Fill in:
   - Email (login ID)
   - First/Last name
   - Role type (Staff, Customer, Auditor)
   - Groups
4. Save

User receives invitation email.

### Managing Groups

1. Navigate to **Data Management** > **Groups**
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
1. Open user record
2. Uncheck **Active**
3. Save

User cannot log in; history preserved.

## Process Configuration

### Creating Processes

1. Navigate to **Data Management** > **Processes**
2. Click **+ New Process**
3. Add steps in sequence
4. Configure requirements per step
5. Set up measurements
6. Submit for approval (if required)

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
- Approve before releasing
- Previous version becomes obsolete
- In-flight work continues on old version

## Master Data Setup

### Part Types

1. Navigate to **Data Management** > **Part Types**
2. Create part types for your products
3. Link to default process
4. Set attributes

### Equipment

1. Navigate to **Data Management** > **Equipment**
2. Create equipment records
3. Set up equipment types
4. Configure calibration tracking

### Error Types

1. Navigate to **Data Management** > **Error Types**
2. Define defect categories
3. Set up hierarchy if needed
4. Configure default severities

### Document Types

1. Navigate to **Data Management** > **Document Types**
2. Define categories
3. Set approval requirements
4. Configure retention

### Approval Templates

1. Navigate to **Data Management** > **Approval Templates**
2. Create templates for:
   - Document approval
   - Disposition approval
   - CAPA closure
3. Define approvers and flow

## System Settings

### Organization Settings

Navigate to **Settings**:
- Organization name
- Timezone
- Date/number formats
- Branding (logo, colors)

### Integration Settings

Configure:
- SSO/Azure AD
- HubSpot connection
- API access

### Notification Settings

Configure system notifications:
- Email templates
- Notification triggers
- Default preferences

## Monitoring & Maintenance

### Audit Log Review

Regularly review **Admin** > **Audit Log**:
- User activity
- Permission changes
- Unusual patterns
- Failed login attempts

### System Health

Monitor:
- User adoption
- Performance issues
- Error patterns
- Storage usage

### Periodic Tasks

**Weekly:**
- [ ] Review new user requests
- [ ] Check pending access issues
- [ ] Monitor system alerts

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
1. Account is active
2. Password not expired
3. SSO configured correctly
4. Account not locked

### Permission Issues

1. Check user's groups
2. Verify group has permission
3. Check role type restrictions
4. Confirm tenant assignment

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
| Password reset | Use reset function or SSO |
| Permission change | Modify group membership |
| New account | Create user, assign groups |
| Access issue | Check permissions, role type |

### Escalation

When you can't resolve:
- Platform issues: Contact Ambac support
- Integration issues: Coordinate with IT
- Compliance questions: Involve QA Manager

## Quick Reference

| Task | Location |
|------|----------|
| Add user | Data Management > Users > + New |
| Create group | Data Management > Groups > + New |
| Edit permissions | Groups > [Group] > Permissions |
| Configure process | Data Management > Processes |
| View audit log | Admin > Audit Log |
| System settings | Admin > Settings |

## Related Documentation

- [Adding Users](../admin/users/adding.md)
- [Roles & Groups](../admin/users/roles.md)
- [Process Configuration](../admin/processes/overview.md)
- [System Setup](../admin/index.md)
- [Audit Trails](../compliance/audit-trails.md)
