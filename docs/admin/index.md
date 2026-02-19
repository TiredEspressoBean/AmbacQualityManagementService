# Administration Guide

This guide covers system administration for Ambac Tracker, including user management, process configuration, and system setup.

## Who is This For?

This guide is for:

- **Tenant Administrators**: Manage users, configure processes, set up system
- **Quality Managers**: Configure quality workflows, sampling rules
- **IT Administrators**: System integration, SSO configuration
- **Implementation Teams**: Initial setup and configuration

## Administration Areas

### User Management

Manage who can access Ambac Tracker and what they can do.

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

### System Setup

Configure master data and system settings.

- [Companies](setup/companies.md) - Customer and supplier records
- [Part Types](setup/part-types.md) - Product definitions
- [Equipment](setup/equipment.md) - Machines and tools
- [Error Types](setup/error-types.md) - Defect categories
- [Document Types](setup/document-types.md) - Document categories
- [Approval Templates](setup/approval-templates.md) - Approval workflows
- [Sampling Rules](setup/sampling-rules.md) - Inspection sampling

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

## Settings

Organization settings include:

### General
- Organization name and details
- Default timezone
- Date/number formats
- Logo and branding

### Quality
- Default severity levels
- NCR workflows
- CAPA settings
- Sampling defaults

### Documents
- Document numbering
- Retention policies
- Approval requirements

### Integration
- SSO configuration
- API settings
- Webhook configuration

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
- Contact support for implementation assistance

## Next Steps

Start with:
- [Adding Users](users/adding.md) - Set up your team
- [Process Overview](processes/overview.md) - Understand workflows
- [Part Types](setup/part-types.md) - Define products
