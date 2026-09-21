# Adding Users

Create and manage user accounts for your organization.

## User Types

| Type | Description | Access |
|------|-------------|--------|
| **Staff** | Internal employees | Full system based on permissions |
| **Customer** | External customer contacts | Portal access to their orders |
| **Auditor** | External auditors | Read-only access |

## Creating a User

### From User Management

1. Navigate to **Admin** > **User Management**
2. Click **Add user**
3. Fill in the details:

| Field | Description | Required |
|-------|-------------|----------|
| **Username** | Login identifier | Yes |
| **First Name** / **Last Name** | The person's name | No |
| **Email** | Contact email | No |
| **Company** | Company, for customer users | No |
| **Role** | Which role the user holds | No |

4. Click **Create User**

The **Role** picker offers: Auditor, Customer, Document Controller,
Engineering, Operator, Production Manager, Purchasing, QA Inspector,
QA Manager, Shift Lead, Tenant Admin.

!!! note "User Management is the surface to use"
    **Data Management > Users** reaches the same records through the generic
    editor, but User Management adds what you normally want — invite status
    filters (Active, Pending invite, Expired invite, Inactive), group
    filtering, and bulk actions.

### Invitation email

There is no "welcome email" on account creation. The email that gets someone
in is the **invitation**, and it is sent when you invite them — see
[Inviting Users](#inviting-users) below.

1. The invitation email carries a signup link with a token
2. The token is what places them in the right tenant when they sign up
3. They set a password, unless they sign in through SSO
4. They can log in

!!! note "Email verification is optional"
    Address verification is configured as *optional*, so a new user can sign
    in without having clicked a verification link. Do not treat a working
    login as proof the address is reachable.

!!! warning "Creating a user is not the same as inviting one"
    A record created without an invitation gets no email and no signup link.
    If someone says they never received anything, check whether they were
    invited or only created.

## Inviting Users

### Bulk invite

Invitations are issued from the bulk surface rather than a per-user invite
dialog:

1. In **User Management**, click **Bulk Actions**
2. Add a row per person with **Manual entry**, or **Upload workbook** for a
   batch
3. Set the group and status for each row
4. Click **Apply rows**

Invite state is then visible on the User Management list through the **Pending
invite** and **Expired invite** filters.

!!! note "No single-user invite dialog"
    There is no **Invite User** button. To invite one person, use Bulk Actions
    with a single row.

A workbook upload accepts the same columns as the manual rows:
```csv
email,first_name,last_name,role_type,groups
john@company.com,John,Smith,staff,"QA Inspector"
jane@company.com,Jane,Doe,staff,"Operator"
```
4. Upload CSV
5. Review and confirm
6. Invitations sent to all

## User Fields

### Basic Information

| Field | Description |
|-------|-------------|
| **Email** | Unique identifier, used for login |
| **First/Last Name** | Display name |
| **Phone** | Contact number (optional) |
| **Title** | Job title (optional) |

### Account Settings

| Field | Description |
|-------|-------------|
| **Role Type** | Admin, Staff, Customer, Auditor |
| **Active** | Whether account is enabled |
| **Groups** | Permission group membership |
| **Last Login** | Most recent login (read-only) |

### Compliance Fields (if required)

| Field | Description |
|-------|-------------|
| **Citizenship** | Country code for export control |
| **US Person** | ITAR qualification |
| **Export Control Verified** | Verification status |

## Assigning Groups

Groups determine permissions:

1. Edit the user
2. In **Groups** field, select groups
3. User gains permissions from all assigned groups
4. Save

Common group assignments:

| Role | Typical Groups |
|------|----------------|
| QA Inspector | QA Inspector |
| Production Operator | Operator |
| QA Manager | QA Manager |
| Document Controller | Document Controller |
| Administrator | Administrator |

See [Roles & Groups](roles.md) for details.

## SSO Users

If your organization uses Single Sign-On:

### Automatic Provisioning
- User logs in via SSO
- Account created automatically
- Assigned to default group

### Manual Pre-Creation
- Create user with matching email
- Assign groups
- User links when they SSO login

### SSO vs Password
- SSO users authenticate via identity provider
- Password managed by IdP (Microsoft Entra ID, Okta, etc.)
- MFA handled by IdP

## Customer Users

Create portal access for customers:

1. Create user with **Role Type: Customer**
2. Associate with Company record
3. User sees only their company's orders
4. Limited permissions (view orders, documents)

### Customer Permissions
- View own orders and parts
- View shared documents
- Cannot access internal data

## Auditor Users

Create temporary access for auditors:

1. Create user with **Role Type: Auditor**
2. Built-in read-only permissions
3. Set account expiration if needed
4. Access to compliance records only

## Password Policies

For non-SSO users:

- Minimum length (configured by admin)
- Complexity requirements
- Expiration period
- Lockout after failed attempts

SSO users follow IdP password policies.

## Permissions

| Permission | Allows |
|------------|--------|
| `view_user` | View user list |
| `add_user` | Create users |
| `change_user` | Edit users |
| `delete_user` | Deactivate users |

## Next Steps

- [Roles & Groups](roles.md) - Understanding permissions
- [Assigning Permissions](permissions.md) - Configure access
- [Deactivating Users](deactivating.md) - Offboarding
