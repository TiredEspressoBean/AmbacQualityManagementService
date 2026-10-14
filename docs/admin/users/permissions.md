# Assigning Permissions

Detailed guide to configuring user permissions in uqmes.

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
respond_to_approval  - Eligible to respond to approval requests
approve_disposition  - Can record (or co-sign) a disposition decision
close_capa           - Can close CAPAs
override_training_gate - Can authorize a start the training record doesn't cover
void_substepcompletion - Can void a recorded substep completion
```

!!! warning "Eligibility is not authorization"
    `respond_to_approval` makes you *eligible*. Whether a given request
    actually reaches you is decided by its approval template — see [Who can
    approve](../../workflows/approvals/overview.md#who-can-approve). Granting
    the permission to someone who was never assigned changes nothing.

## Assigning via Groups

**Start by assigning an existing group, not by building one.** All fifteen built-in
groups are seeded into every organisation already — QA Inspector, Operator, Planner
and the rest. They are not examples to copy; they are the groups people should be in.

1. Open the person in **User Management**
2. Put them in the group that matches their job
3. Only if no group fits, create a custom one — see
   [Roles and Groups](roles.md#creating-custom-groups)

!!! danger "Do not hand-build a group that already exists"
    Creating your own "QA Inspector" does not replace the built-in one — it adds a
    second group with the same job and whatever permissions you happened to pick.
    The real preset carries a few hundred permissions; a hand-assembled version will
    carry a handful, and the person will hit refusals you then have to debug one at
    a time.

    If someone cannot do something they should be able to, check **which group they
    are in** before adding permissions to fix it.

## When a permission looks granted but nothing changes

Permissions are only one of the ways access is decided, which is why granting one
sometimes appears to do nothing. Three different mechanisms are at work:

| Mechanism | What it controls | Symptom when it is the cause |
|-----------|------------------|------------------------------|
| **The permission itself** | Whether the action is allowed at all | A clear refusal, usually a 403 |
| **Row filtering** | *Which records* they can see — document classification, and export-control status | They can open the page but a record is missing from the list entirely |
| **Per-record eligibility** | Whether this particular record is theirs to action | The page loads, the record is visible, the button is absent or refuses |

So a person with `view_documents` may still not see a given document, because
classification filtering removes it from their queryset before permissions are
consulted. Adding more permissions will not fix that — their classification access
or export-control status is what needs looking at.

!!! note "Export control is not a permission"
    Access to export-controlled data is decided by flags on the **person**, not by
    any group. You cannot grant it here, and putting someone in a different group
    will not change it.

## Permission Categories

### Viewing Data

`view_*` permissions control visibility:

| Permission | Access |
|------------|--------|
| `view_orders` | See orders list and details |
| `view_parts` | See parts |
| `view_qualityreports` | See NCRs |
| `view_capa` | See CAPAs |
| `view_documents` | See documents |

### Creating Data

`add_*` permissions control creation:

| Permission | Allows |
|------------|--------|
| `add_orders` | Create new orders |
| `add_parts` | Add parts to orders |
| `add_qualityreports` | Create NCRs |
| `add_capa` | Initiate CAPAs |

### Editing Data

`change_*` permissions control modification:

| Permission | Allows |
|------------|--------|
| `change_orders` | Edit order details |
| `change_parts` | Modify parts |
| `change_qualityreports` | Update NCRs |
| `change_workorder` | Edit work orders |

### Deleting Data

`delete_*` permissions control removal:

| Permission | Allows |
|------------|--------|
| `delete_orders` | Remove orders |
| `delete_parts` | Delete parts |
| `delete_documents` | Remove documents |

!!! note "Soft Delete"
    Most deletions are soft deletes. Records are archived, not permanently removed.

## Special Permissions

### Approval Permissions

| Permission | Allows |
|------------|--------|
| `respond_to_approval` | Respond to any approval request routed to you — documents and processes included |
| `approve_disposition` | Approve disposition decisions |
| `approve_capa` | Approve CAPA closure |
| `approve_qualityreports` | Approve quality reports |

!!! note
    Document and process approvals have no dedicated `approve_*` permission.
    They are routed through approval templates: holding `respond_to_approval`
    makes you *eligible*, and the template decides which requests reach you.

### Confidential Access

| Permission | Allows |
|------------|--------|
| `view_confidential_documents` | See confidential docs |
| `view_restricted_documents` | See restricted docs |

### Export Permissions

| Permission | Allows |
|------------|--------|
| `export_data` | Export CSV/PDF reports |
| `export_auditlog` | Export audit trail |

### Admin Permissions

| Permission | Allows |
|------------|--------|
| `view_auditlog` | Access full audit trail |
| `change_tenant` | Modify organization settings |
| `add_user`, `change_user` | Create and edit users |

## Checking User Permissions

### View Effective Permissions

Users get permissions through their group memberships:

1. Navigate to **Admin** > **User Management**
2. Open user record and note their assigned **Groups**
3. Navigate to **Data Management > User Groups**
4. Open each group to view its **Permissions** tab
5. User has the combined permissions of all their groups

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

## Existing tenants and new permissions

Role presets are applied **when a tenant is created**. When an upgrade adds a
permission to a preset role, tenants that already exist do not pick it up on
their own — their groups keep the grants they were created with.

After an upgrade that changes role presets, reconcile them:

```
python manage.py sync_tenant_permissions
```

It reports what it changed, for example *1 group reconciled, 1 grant added,
0 revoked*. Until it is run, a role can be missing a permission the release
notes say it has — which presents as a user not seeing a control they should.

!!! tip "Check this first when a new feature's control is missing"
    If a release adds an action for a role and that role can't see it, confirm
    the sync has been run before investigating the feature itself. It is a far
    more common cause than a broken permission check.

## Next Steps

- [Roles & Groups](roles.md) - Group management
- [Adding Users](adding.md) - Create users
- [Deactivating Users](deactivating.md) - Remove access
