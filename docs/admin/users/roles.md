# Roles & Groups

Understanding how permissions are organized and assigned in Ambac Tracker.

## Permission Model

Ambac Tracker uses a layered permission system:

```
User
  └── Groups (multiple)
        └── Permissions (many)
```

- **Users** belong to one or more **Groups**
- **Groups** have **Permissions**
- User's effective permissions = union of all group permissions

## Role Types

Role types control the broadest level of access:

| Role Type | Purpose | Data Access |
|-----------|---------|-------------|
| **Admin** | Full system access | All data |
| **Staff** | Internal operations | Per permissions |
| **Auditor** | Read-only compliance | All data (read) |
| **Customer** | External portal | Own orders only |

Role type is set per user and determines baseline behavior.

## Built-in Groups

### Administrator
Full system access:
- All permissions (400+)
- Can configure system
- Can manage users

### QA Manager
Quality management:
- Manage quality reports
- Approve dispositions
- Close CAPAs
- View production data

### Production Manager
Production operations:
- Manage orders and work orders
- View quality data
- Update parts
- Document access

### QA Inspector
Quality inspection:
- Create quality reports
- Record measurements
- View orders
- Limited edit rights

### Operator
Production floor:
- View orders
- Move parts through steps
- Record data
- Basic access

### Engineering
Technical access:
- Process configuration
- Document management
- Equipment setup
- ECO management

### Document Controller
Document management:
- Full document access
- Revision management
- Approval submission
- Confidential access

### Auditor
Read-only:
- View all records
- Cannot edit
- Compliance focused

### Customer
Portal access:
- View own orders
- View shared documents
- No internal access

## Creating Custom Groups

### From Groups Editor

1. Navigate to **Data Management** > **Groups**
2. Click **+ New Group**
3. Enter group name
4. Add description
5. Click **Save**
6. Add permissions (next step)

### Naming Conventions

Use clear, descriptive names:
- `QA Inspector - Medical`
- `Operator - Night Shift`
- `Customer - Premium`

## Assigning Permissions to Groups

### From Group Detail

1. Open the group
2. Go to **Permissions** tab
3. Search/browse available permissions
4. Check permissions to add
5. Save

### Permission Categories

Permissions are organized by model:

| Category | Examples |
|----------|----------|
| **Orders** | view_orders, add_orders, change_orders |
| **Parts** | view_parts, change_parts, delete_parts |
| **Quality** | add_qualityreport, approve_disposition |
| **Documents** | view_document, approve_document |
| **CAPA** | add_capa, close_capa |
| **Admin** | view_user, change_settings |

### Permission Naming Convention

`action_model`:
- `view_orders` - View order records
- `add_parts` - Create parts
- `change_qualityreport` - Edit quality reports
- `delete_document` - Remove documents
- `approve_capa` - Approve CAPA closure

## Viewing Effective Permissions

### For a User

1. Open user record
2. View **Permissions** tab
3. See all effective permissions (from all groups)
4. Identify source group for each

### For a Group

1. Open group record
2. View **Permissions** tab
3. See all permissions assigned to group

## Group Hierarchy

Groups can be nested:

```
Manager
  └── Supervisor
        └── Operator
```

Child groups inherit parent permissions.

## Multi-Tenant Groups

In multi-tenant deployments:

- Each tenant has own groups
- Groups are independent per tenant
- User can have different groups per tenant
- Switching tenants switches effective permissions

## Permission Best Practices

### Start Restrictive
- Begin with minimal permissions
- Add as needs are identified
- Easier than removing excess

### Use Groups
- Assign groups, not individual permissions
- Easier to audit
- Simpler to change

### Role-Based
- Create groups matching job roles
- Consistency across similar users
- Clear documentation

### Regular Review
- Quarterly permission audits
- Remove unnecessary access
- Update for role changes

## Common Permission Sets

### View Only
- `view_*` permissions only
- No create, edit, delete
- For read-only users

### Create and View
- `view_*` and `add_*`
- Cannot edit or delete
- For data entry roles

### Full Access
- All permissions for a model
- `view_`, `add_`, `change_`, `delete_`
- For model administrators

## Permissions Reference

Key permissions by function:

### Production
- `view_orders`, `add_orders`, `change_orders`
- `view_parts`, `change_parts`
- `view_workorder`, `change_workorder`
- `can_move_parts`

### Quality
- `add_qualityreport`, `change_qualityreport`
- `add_disposition`, `approve_disposition`
- `add_capa`, `change_capa`, `close_capa`
- `view_quarantine`

### Documents
- `view_document`, `add_document`
- `view_confidential_document`
- `approve_document`
- `change_document`

### Admin
- `view_user`, `add_user`, `change_user`
- `change_group`, `change_permissions`
- `view_auditlog`
- `change_settings`

## Next Steps

- [Assigning Permissions](permissions.md) - Detailed permission setup
- [Adding Users](adding.md) - Create users with groups
- [Deactivating Users](deactivating.md) - Remove access
