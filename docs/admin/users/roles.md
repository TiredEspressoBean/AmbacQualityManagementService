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

Three separate things decide what a person can do, and they are often confused:

| What | Where it lives | What it decides |
|------|----------------|-----------------|
| **User type** | On the user — `INTERNAL` or `PORTAL`, and only those two | Whether they are one of your people or a customer using the portal |
| **Groups** | Membership in one or more of the built-in groups below, or a custom group | Everything they can actually *do* |
| **Superuser** | A Django flag, off for nearly everyone | Bypasses permission checks entirely |

**There is no "role type" field offering Admin / Staff / Auditor / Customer.**
*Auditor* and *Customer* are **groups** in the list below; *Admin* is not a group at
all — the two real ones are **System Admin** and **Tenant Admin**, and they are very
different. If you are looking for a single dropdown that sets someone's access, there
isn't one: set the user type when you create them, then put them in groups.

## Built-in Groups

There are **15** built-in group presets. **14** of them are created in every
organisation and appear in the Groups editor, named exactly as below — **with the
spaces**, which matters (see the warning at the end of this section). The
fifteenth, **System Admin**, is for the platform team and is not created in an
organisation.

!!! note "Permission counts are not listed here on purpose"
    A group's permission count changes whenever anyone adds a permission anywhere in
    the product, so a number written on this page is wrong within weeks and nobody
    notices. To see what a group holds **today**, open it in the **Groups editor**,
    or run `python manage.py check_permissions`.

| Group | What it is for |
|-------|----------------|
| **System Admin** | Platform administrator — manages all tenants and system settings. Not created in an organisation |
| **Tenant Admin** | Full access within one organization |
| **QA Manager** | Quality management, approvals, CAPA control |
| **QA Inspector** | Perform inspections, create quality reports, initiate CAPAs |
| **Production Manager** | Production operations, work orders, scheduling |
| **Operator** | Production floor work, inspections, data entry |
| **Shift Lead** | Floor supervisor: operator work plus team visibility and quality oversight |
| **Planner** | Releasing work, promising dates, running the schedule and its calendars |
| **Engineering** | Engineering changes, drawing control, design work |
| **Purchasing** | Supplier qualification, part approvals, expected receipts |
| **Receiving** | The inbound dock: receipt, incoming inspection, holds, put-away |
| **Shipping** | The outbound dock: shipments, packing lists and CoCs, subcontract send-out |
| **Document Controller** | Controlled documents, revisions and approvals |
| **Auditor** | Read-only for audits: sees everything, changes nothing |
| **Customer** | External portal — their own orders only |

!!! warning "Group names have no underscores"
    Names such as "Production_Operator", "QA_Manager" or "Document_Controller"
    **do not exist.** The real names are as written above: plain words with
    spaces, and the floor role is **Operator**, not "Production Operator".

    There is also no "Supplier_Quality" group. That work is split: the buyer
    side is [Purchasing](../../roles/purchasing.md), and approving a supplier
    qualification is [QA Manager](../../roles/qa-manager.md).

!!! note "A permission count is a size, not a ranking"
    If you compare counts in the Groups editor, read them carefully: a bigger
    number is not a more senior role. **Auditor** holds a large set and can
    change **nothing** — they are `view_` permissions, plus `view_auditlog`
    (browse the audit trail), `export_data` (export lists and reports) and
    `full_tenant_access` (see every record, not only those linked to them).
    **Operator** holds more still, because the shared staff base is broad.

    What separates the roles is a short list of specific authorities, not
    volume — see [Role Comparison](../../roles/index.md#what-tells-the-roles-apart).

For what each group can actually *do*, see the [Role Guides](../../roles/index.md).

!!! danger "Group names are matched exactly, spaces and all"
    Anywhere a group is referred to **by name** rather than by reference, the
    match is exact. The real names have spaces — `QA Manager`, `Production
    Manager`, `Document Controller`. An underscored form (`QA_Manager`) **does
    not match anything**.

    This matters most on **approval templates**. A template's **Auto-assign to
    Group** keeps the group's name, and a name that matches nothing assigns
    **nobody** — without an error, because a filter returning no rows is not a
    failure. The approval simply sits there with no one to action it. Renaming
    a group does this to every template that auto-assigns it; pick the group
    again on those templates. See [Approval
    Templates](../setup/approval-templates.md).

## Creating Custom Groups

### From Groups Editor

1. Navigate to **Data Management** > **User Groups**
2. Click **New group**
3. Enter its **Name**
4. Pick **Start from**: *Blank — no permissions*, or *&lt;Preset&gt; preset* to
   start with a built-in group's permissions. A blank group also takes a
   **Description**
5. Click **Create**. The new group opens
6. Add or remove permissions (next step)

To start from an existing group instead, use **Copy** on its row. The dialog,
*Copy &lt;group&gt;*, reads *"A new custom group with the same permissions.
Members aren't copied."* Give it a name and click **Copy**; the copy opens.

**New group** and **Copy** are shown only to someone holding
`change_tenantgroup`.

### Deleting a group

The Groups editor has no delete button; a group is deleted through the
[API](../../integrations/api.md), by someone holding `change_tenantgroup`. A
group that still has members is refused — *"Cannot delete group with members.
Remove all members first."* — so empty it on its **Members** tab first. The
delete is permanent: a group is not archived, and cannot be restored.

### Naming Conventions

Use clear, descriptive names:
- `QA Inspector - Medical`
- `Operator - Night Shift`
- `Customer - Premium`

## Assigning Permissions to Groups

### From Group Detail

1. Open the group (**View** on its row)
2. Go to the **Permissions** tab
3. Search the permissions
4. Click a permission under **Available** to grant it, or one under
   **Granted** to revoke it

Each click takes effect at once — there is no Save. The tab says so: *"Click a
permission to grant or revoke it"*.

### Permission Categories

Permissions are organized by model:

| Category | Examples |
|----------|----------|
| **Orders** | view_orders, add_orders, change_orders |
| **Parts** | view_parts, change_parts, delete_parts |
| **Quality** | add_qualityreports, approve_disposition |
| **Documents** | view_documents, respond_to_approval |
| **CAPA** | add_capa, initiate_capa, verify_capa |
| **Admin** | view_user, change_tenantgroup |

### Permission Naming Convention

`action_model`:
- `view_orders` - View order records
- `add_parts` - Create parts; `add_<model>` also shows a list's **Import**
  button and allows a create-only import
- `change_qualityreports` - Edit quality reports still **Pending Review**;
  `change_<model>` is also needed for an update or create-or-update import
- `delete_documents` - Remove documents
- `verify_capa` - Record a CAPA effectiveness check

## Seeing what a user can actually do

There is **no aggregate "effective permissions" view** on a user, and nothing
tells you which group a given permission came from. Work it out group by group:

1. Open the user record and note their assigned **Groups**
2. Go to **Data Management** > **User Groups**
3. Open each group and read its **Permissions** tab
4. The user holds the union of all of them

!!! note "Groups do not nest"
    There is no parent group and no inheritance. A user's permissions are the
    union of the groups they are in, full stop — so putting someone in
    **Production Manager** does not confer what **Shift Lead** or **Operator**
    hold.

## Next Steps

- [Assigning Permissions](permissions.md) - Detailed permission setup
- [Adding Users](adding.md) - Create users with groups
- [Deactivating Users](deactivating.md) - Remove access
