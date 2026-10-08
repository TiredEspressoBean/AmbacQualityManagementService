# Roles & Groups

Understanding how permissions are organized and assigned in uqmes.

## Permission Model

uqmes uses a layered permission system:

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

There are **15** built-in group presets. Each one's name below is exactly what
appears in the Groups editor.

| Group | Perms | What it is for |
|-------|------:|----------------|
| **System Admin** | 3 | Platform administrator — manages all tenants and system settings |
| **Tenant Admin** | 506 | Full access within one organization |
| **QA Manager** | 463 | Quality management, approvals, CAPA control |
| **QA Inspector** | 290 | Perform inspections, create quality reports, initiate CAPAs |
| **Production Manager** | 466 | Production operations, work orders, scheduling |
| **Operator** | 270 | Production floor work, inspections, data entry |
| **Shift Lead** | 287 | Floor supervisor: operator work plus team visibility and quality oversight |
| **Planner** | 293 | Releasing work, promising dates, running the schedule and its calendars |
| **Engineering** | 363 | Engineering changes, drawing control, design work |
| **Purchasing** | 275 | Supplier qualification, part approvals, expected receipts |
| **Receiving** | 272 | The inbound dock: receipt, incoming inspection, holds, put-away |
| **Shipping** | 270 | The outbound dock: shipments, packing lists and CoCs, subcontract send-out |
| **Document Controller** | 412 | Controlled documents, revisions and approvals |
| **Auditor** | 138 | Read-only for audits: sees everything, changes nothing |
| **Customer** | 17 | External portal — their own orders only |

!!! warning "Group names have no underscores"
    Older documentation used underscored names — "Production_Operator",
    "QA_Manager", "Document_Controller" and similar. **Those names do not
    exist.** The real names are as written above: plain words with spaces, and
    the floor role is **Operator**, not "Production Operator".

    There is also no "Supplier_Quality" group. That work is split: the buyer
    side is [Purchasing](../../roles/purchasing.md), and approving a supplier
    qualification is [QA Manager](../../roles/qa-manager.md).

!!! note "The permission counts are a size, not a ranking"
    A bigger number is not more senior. **Auditor** holds 138 and can change
    nothing; **Operator** holds 270 because the shared staff base is broad. What
    separates the roles is a short list of specific authorities — see [Role
    Comparison](../../roles/index.md#what-tells-the-roles-apart).

For what each group can actually *do*, see the [Role Guides](../../roles/index.md).

## Creating Custom Groups

### From Groups Editor

1. Navigate to **Data Management** > **User Groups**
2. Click **New User Groups**
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
| **Documents** | view_document, respond_to_approval |
| **CAPA** | add_capa, close_capa |
| **Admin** | view_user, change_settings |

### Permission Naming Convention

`action_model`:
- `view_orders` - View order records
- `add_parts` - Create parts
- `change_qualityreports` - Edit quality reports
- `delete_documents` - Remove documents
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
- `add_qualityreports`, `change_qualityreports`
- `add_quarantinedisposition`, `approve_disposition`
- `add_capa`, `change_capa`, `close_capa`
- `view_quarantinedisposition`

### Documents
- `view_documents`, `add_documents`
- `view_confidential_documents`
- `respond_to_approval`
- `change_documents`

### Admin
- `view_user`, `add_user`, `change_user`
- `change_group`, `change_permission`
- `view_auditlog`
- `change_tenant`
## Next Steps

- [Assigning Permissions](permissions.md) - Detailed permission setup
- [Adding Users](adding.md) - Create users with groups
- [Deactivating Users](deactivating.md) - Remove access
