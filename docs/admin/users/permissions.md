# Assigning Permissions

Detailed guide to configuring user permissions in Ambac Tracker.

## Permission Structure

### Object-Level Permissions

Permissions control access to specific objects:

```
view_orders    - Can see order records
add_orders     - Can create new orders
change_orders  - Can edit existing orders
delete_orders  - Can remove orders
```

### Action Permissions

Special actions beyond CRUD:

```
approve_document   - Can approve documents
close_capa         - Can close CAPAs
disposition_part   - Can make disposition decisions
```

## Assigning via Groups

The recommended approach:

1. **Create a Group** matching the role
2. **Add Permissions** to the group
3. **Assign Users** to the group

### Example: QA Inspector Role

1. Create group "QA Inspector"
2. Add permissions:
   - `view_orders`, `view_parts`
   - `add_qualityreport`, `view_qualityreport`
   - `add_measurement`, `view_measurement`
   - `view_document`
3. Assign QA inspector users to this group

## Permission Categories

### Viewing Data

`view_*` permissions control visibility:

| Permission | Access |
|------------|--------|
| `view_orders` | See orders list and details |
| `view_parts` | See parts |
| `view_qualityreport` | See NCRs |
| `view_capa` | See CAPAs |
| `view_document` | See documents |

### Creating Data

`add_*` permissions control creation:

| Permission | Allows |
|------------|--------|
| `add_orders` | Create new orders |
| `add_parts` | Add parts to orders |
| `add_qualityreport` | Create NCRs |
| `add_capa` | Initiate CAPAs |

### Editing Data

`change_*` permissions control modification:

| Permission | Allows |
|------------|--------|
| `change_orders` | Edit order details |
| `change_parts` | Modify parts |
| `change_qualityreport` | Update NCRs |
| `change_workorder` | Edit work orders |

### Deleting Data

`delete_*` permissions control removal:

| Permission | Allows |
|------------|--------|
| `delete_orders` | Remove orders |
| `delete_parts` | Delete parts |
| `delete_document` | Remove documents |

!!! note "Soft Delete"
    Most deletions are soft deletes. Records are archived, not permanently removed.

## Special Permissions

### Approval Permissions

| Permission | Allows |
|------------|--------|
| `approve_document` | Approve document revisions |
| `approve_disposition` | Approve disposition decisions |
| `approve_capa` | Approve CAPA closure |
| `approve_process` | Approve process changes |

### Confidential Access

| Permission | Allows |
|------------|--------|
| `view_confidential_document` | See confidential docs |
| `view_restricted_document` | See restricted docs |

### Export Permissions

| Permission | Allows |
|------------|--------|
| `export_data` | Export CSV/PDF reports |
| `export_auditlog` | Export audit trail |

### Admin Permissions

| Permission | Allows |
|------------|--------|
| `view_auditlog` | Access full audit trail |
| `change_settings` | Modify system settings |
| `manage_users` | Full user management |

## Checking User Permissions

### View Effective Permissions

1. Navigate to **Users**
2. Open user record
3. View **Permissions** tab
4. See all effective permissions with source groups

### Test Permission

Before deploying:
1. Log in as test user
2. Verify access is as expected
3. Check both access and restrictions

## Permission Troubleshooting

### User Can't Access Something

1. Check what permission is needed
2. Check user's groups
3. Check group has the permission
4. Verify user assignment is saved

### User Has Too Much Access

1. Review all groups user belongs to
2. Permissions stack - check each group
3. Remove from unnecessary groups
4. Consider creating more specific groups

### Permission Not Working

1. User may need to log out/in
2. Clear browser cache
3. Check for conflicting group permissions
4. Verify permission name is correct

## Audit Trail for Permissions

Permission changes are logged:

- Who changed permissions
- When changed
- What was added/removed
- Which group affected

View in Admin > Audit Log, filter by permission changes.

## Role Type Restrictions

Role types impose hard limits:

### Customer Role Type
- Can only view own company's data
- Cannot see internal records
- Limited to portal features

### Auditor Role Type
- Read-only access
- Cannot create, edit, delete
- All view permissions granted

### Staff Role Type
- Permissions determine access
- Can have any permission set
- Default for internal users

### Admin Role Type
- Has all permissions
- Cannot be restricted
- Use sparingly

## Multi-Tenant Permissions

For users in multiple tenants:

- Permissions are per-tenant
- User may have different groups per tenant
- Switching tenants changes effective permissions

## Permission Templates

Create group templates for common roles:

### Read-Only Template
```
view_orders, view_parts, view_workorder
view_qualityreport, view_capa, view_document
view_measurement, view_equipment
```

### Data Entry Template
```
view_*, add_orders, add_parts, add_measurement
add_qualityreport, change_parts
```

### Quality Full Access
```
view_*, add_*, change_* for quality records
approve_disposition, approve_capa
```

## Best Practices

1. **Document group purposes** - Clear descriptions
2. **Audit regularly** - Quarterly reviews
3. **Least privilege** - Minimum necessary access
4. **Use groups consistently** - Same group for same role
5. **Test before deploy** - Verify with test users

## Next Steps

- [Roles & Groups](roles.md) - Group management
- [Adding Users](adding.md) - Create users
- [Deactivating Users](deactivating.md) - Remove access
