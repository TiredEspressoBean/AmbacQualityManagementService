# Administration Guide

This guide covers system administration for uqmes, including user management, process configuration, and system setup.

## Who is This For?

This guide is for:

- **Tenant Administrators**: Manage users, configure processes, set up system
- **Quality Managers**: Configure quality workflows, sampling rules
- **IT Administrators**: System integration and deployment
- **Implementation Teams**: Initial setup and configuration

## Administration Areas

### User Management

Manage who can access uqmes and what they can do.

- [Adding Users](users/adding.md) - Create and invite users
- [Roles & Groups](users/roles.md) - Understand permission structure
- [Assigning Permissions](users/permissions.md) - Configure access rights
- [Deactivating Users](users/deactivating.md) - Offboarding

### Process Configuration

Define manufacturing workflows and quality processes.

- [Process Overview](processes/overview.md) - Understanding processes
- [Creating Processes](processes/creating.md) - Build workflows
- [Step Configuration](processes/steps.md) - Configure process steps
- [Measurement Definitions](processes/measurements.md) - Define inspection requirements

### Data Management

Bulk data operations for import and export.

- [Import & Export](data/import-export.md) - Bulk data import/export with CSV and Excel
- [Data Management](data/data-management.md) - The Data Management page and what belongs on it

### System Setup

Configure master data and system settings.

- [Companies](setup/companies.md) - Customer and supplier records
- [Part Types](setup/part-types.md) - Product definitions
- [Equipment](setup/equipment.md) - Machines and tools
- [Error Types](setup/error-types.md) - Defect categories
- [Document Types](setup/document-types.md) - Document categories
- [Approval Templates](setup/approval-templates.md) - Approval workflows
- [Sampling Rules](setup/sampling-rules.md) - Inspection sampling
- [Notification Rules](setup/notification-rules.md) - Who gets told when something happens

### Deployment

How these help pages are built and served. How the application itself is
hosted depends on your deployment, and is documented by whoever runs it.

- [Documentation Site](deployment/documentation-site.md) - How these pages are built and served

## Accessing Administration

Navigate to **Admin** section in sidebar (visible to administrators only):

- **Settings**: Organization configuration
- **Data Management**: Access to all editors
- **Audit Log**: System activity trail

## Data Management

The **Data Management** page (`/Edit`) provides access to all data editors:

| Editor | Purpose |
|--------|---------|
| Orders | Customer order management |
| Parts | Individual part records |
| Part Types | Product type definitions |
| Processes | Manufacturing workflows |
| Steps | Process step definitions |
| Work Orders | Production work orders |
| Equipment | Machines and tools |
| Equipment Types | Equipment categories |
| Error Types | Defect classifications |
| Quality Reports | NCR management |
| Documents | Document library |
| Document Types | Document categories |
| Sampling Rules | Quality sampling configuration |
| 3D Models | Visual model management |
| Users | User account management |
| Groups | Permission groups |
| Approval Templates | Approval workflows |
| Companies | Customer and supplier records |

### Import & Export

Many data editors support bulk import and export — **but not all of them**.

- **Export**: Download filtered data as CSV or Excel
- **Import**: Upload CSV or Excel files to create/update records

!!! note "A missing Import button has two possible answers"
    The buttons appear only where the model actually supports them, and
    **Import** only for someone who holds the model's add permission. No
    **Import** means that model cannot be imported, or that you can't add its
    records — the [import table](data/import-export.md#what-can-be-imported-and-exported)
    says which.

Excel exports include reference sheets for lookups and dropdown validation; a
linked record exports as its ID beside its name, as plain values.

See [Import & Export Guide](data/import-export.md) for detailed instructions.

## Settings

### Integrations
Self-service integration management lives at **Admin > Settings > Integrations**
(`/settings/integrations`). The page lists a catalog of available providers;
connecting one opens a detail page where you configure it, watch **Sync
Activity**, and remove it.

!!! note "Planned Features"
    SSO configuration, API token management, and webhook configuration still
    have no self-service UI. API access is available now via tokens — contact
    your administrator (see [API documentation](../integrations/api.md)).

## Quick Start Checklist

For new implementations:

1. [ ] Configure organization settings
2. [ ] Create user groups and permissions
3. [ ] Add initial users
4. [ ] Set up companies (customers)
5. [ ] Define part types
6. [ ] Create manufacturing processes
7. [ ] Configure document types
8. [ ] Set up error types
9. [ ] Define sampling rules (if used)
10. [ ] Upload 3D models (if used)
11. [ ] Configure approval templates
12. [ ] Test with sample order

## Best Practices

### Principle of Least Privilege
- Grant minimum permissions needed
- Use groups for consistent access
- Review permissions periodically

### Standardization
- Use consistent naming conventions
- Document your configuration
- Train users on processes

### Change Management
- Plan configuration changes
- Test in development first
- Document changes made
- Communicate to users

## Getting Help

- Review specific guides in this section
- Check [FAQ](../troubleshooting/faq.md) for common questions
- Ask whoever else administers this deployment, or whatever support arrangement your organization has — see [Getting Help](../troubleshooting/help.md)

## Next Steps

Start with:
- [Adding Users](users/adding.md) - Set up your team
- [Process Overview](processes/overview.md) - Understand workflows
- [Part Types](setup/part-types.md) - Define products
