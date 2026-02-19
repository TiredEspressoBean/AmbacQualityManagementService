# Adding Users

Create and manage user accounts for your organization.

## User Types

| Type | Description | Access |
|------|-------------|--------|
| **Staff** | Internal employees | Full system based on permissions |
| **Customer** | External customer contacts | Portal access to their orders |
| **Auditor** | External auditors | Read-only access |

## Creating a User

### From User Editor

1. Navigate to **Data Management** > **Users**
2. Click **+ New User**
3. Fill in user details:

| Field | Description | Required |
|-------|-------------|----------|
| **Email** | User's email (login ID) | Yes |
| **First Name** | User's first name | Yes |
| **Last Name** | User's last name | Yes |
| **Role Type** | Staff, Customer, Auditor | Yes |
| **Groups** | Permission groups | Recommended |
| **Active** | Account enabled | Yes |

4. Click **Save**

### Invitation Email

After creating the user:

1. User receives welcome email
2. Email contains setup link
3. User sets password (if not SSO)
4. User can log in

## Inviting Users

### Quick Invite

1. Click **Invite User** button
2. Enter email address
3. Select role/groups
4. Click **Send Invitation**

### Bulk Invite

Import multiple users:

1. Click **Import Users**
2. Download CSV template
3. Fill in user data:
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
- Password managed by IdP (Azure AD, Okta, etc.)
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

## Best Practices

1. **Use SSO when available** - Centralized management
2. **Assign groups, not individual permissions** - Easier to manage
3. **Verify email addresses** - Ensure delivery
4. **Document user roles** - Who should have what
5. **Regular access review** - Periodic audit of users

## Next Steps

- [Roles & Groups](roles.md) - Understanding permissions
- [Assigning Permissions](permissions.md) - Configure access
- [Deactivating Users](deactivating.md) - Offboarding
