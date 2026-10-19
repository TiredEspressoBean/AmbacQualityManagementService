# Adding Users

Create and manage user accounts for your organization.

## User types

There are exactly **two**, set by the **User type** field on the user:

| Type | Who it is for |
|------|---------------|
| **Internal** | Everyone who works here. What they can do comes from their groups. |
| **Portal** | External people — a customer contact reaching their own orders. |

!!! warning "There is no Admin / Staff / Customer / Auditor role type"
    *Auditor* and *Customer* are **groups**, not account types, and *Admin* is
    neither. If a procedure tells you to set a "Role Type", it is out of date —
    set the **User type** and then assign groups. See [Roles &
    Groups](roles.md).

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
| **User type** | Internal or Portal | No |
| **Company** | For portal users and outside contacts | No |
| **Groups** | What they are allowed to do — pick as many as apply | No |
| **Job role** | What they are *expected to be trained for* | No |
| **Default shift** | Which shift they normally work | No |
| **Contact for** | Marks them as an outside contact — see [Companies](../setup/companies.md#outside-contacts) | No |

4. Click **Create User**

!!! important "Groups and job role are different questions"
    **Groups** decide permissions — what the application lets them do.
    **Job role** drives the required-competency profile: which trainings the
    [training matrix](../../workflows/tracking/training-matrix.md) expects them
    to hold.

    Setting one does not set the other. A new operator with the Operator group
    and no job role can use the system and shows no training gaps — which is
    worse than showing gaps, because nothing looks wrong.

!!! note "The group list is whatever this tenant has"
    The picker reads the tenant's groups, so what you see is the groups that
    exist here rather than a fixed menu. The seeded set is listed in [Roles &
    Groups](roles.md).

!!! note "User Management is the surface to use"
    **Data Management > Users** reaches the same records through the generic
    editor, but User Management adds what you normally want — invite status
    filters (Active, Pending invite, Expired invite, Inactive), group
    filtering, and bulk actions.

### Getting someone in

There is no "welcome email" on account creation. What gets someone in is the
**invitation**, and what the invitation really is, is a **signup link carrying a
token** — see [Inviting Users](#inviting-users) below.

1. The invitation produces a signup link with a token
2. The token is what places them in the right tenant when they sign up
3. They set a password, unless they sign in through SSO
4. They can log in

!!! danger "Do not assume the link was emailed — check, or hand it over yourself"
    Whether an invitation is *delivered* depends on how this deployment is
    configured. The mail backend is set per environment, and one of its settings
    discards mail entirely — which is a normal choice where there is no mail path
    to use. Find out which you are on before you rely on it.

    **The link does not depend on email.** Every invited user's row carries their
    signup link with a **Copy** button — open it, copy the link, and send it to
    them however you normally reach them. That path always works.

    So if you are covering for someone and onboarding a person today: copy the link
    and hand it over. Telling them to watch their inbox is the failure that costs a
    day, because nothing errors — the invitation is created either way, and the only
    symptom is a person who never arrives.

!!! note "Email verification is optional"
    Address verification is configured as *optional*, so a new user can sign
    in without having clicked a verification link. Do not treat a working
    login as proof the address is reachable.

!!! warning "Creating a user is not the same as inviting one"
    A record created without an invitation gets no email and no signup link.
    If someone says they never received anything, check whether they were
    invited or only created.

## Inviting Users

### Inviting one person

Open the person's row menu in **User Management**:

| Action | When it appears | What it does |
|--------|-----------------|--------------|
| **Copy access link** | Always, for any user | Creates an invitation — or returns the live one — and shows the signup link with a **Copy** button |
| **Resend invitation** | Only while they are pending or expired | The same thing, named for the case you are usually in |

!!! tip "This is also how you get someone back in without email"
    Accepting a fresh invitation **re-sets the person's password**. So **Copy
    access link** on an *active* user is a password reset you can hand over
    directly — which is the answer when someone is locked out and the reset mail
    is not reaching them.

### Inviting everyone who was never invited

Where staff were loaded in bulk (a migration workbook, say) without invitations,
**User Management** offers a one-click action that invites everyone never invited
and never signed in. It is hidden when there is nobody in that state, so if you
cannot see it, there is nobody to invite.

### Bulk invite

To add and invite several people at once:

1. In **User Management**, click **Bulk Actions**
2. Add a row per person with **Manual entry**, or **Upload workbook** for a
   batch
3. Set the group and status for each row
4. Click **Apply rows**

Invite state is then visible on the User Management list through the **Pending
invite** and **Expired invite** filters.

Bulk Actions also offers **Copy all invite links** once rows are applied, which
gives you `email — url` lines for everyone created — the whole intake handed out
in one paste.

A workbook upload accepts the same columns as the manual rows:
```csv
username,email,first_name,last_name,groups
jsmith,john@company.com,John,Smith,"QA Inspector"
jdoe,jane@company.com,Jane,Doe,"Operator"
```

!!! warning "There is no role_type column"
    Account type and role are separate things here. The sheet carries
    **groups**; **User type** is not a column.

## Export control fields on a user

Three fields on the user record decide export-control access. They are
**not** permissions and no group grants them:

| Field | Description |
|-------|-------------|
| **Citizenship** | Country code |
| **US Person** | ITAR qualification |
| **Export Control Verified** | Verification status |

Whether a deployment uses this filtering at all is its own decision; where it is
used, these flags — not the user's role — are what decides access.

## Assigning Groups

Groups determine permissions:

1. Edit the user
2. In **Groups** field, select groups
3. User gains permissions from all assigned groups
4. Save

A person can hold several. Permissions are the **union** of every group they are
in, so adding a group only ever widens what they can do — there is no group that
takes something away.

That matters when someone covers two jobs: give the shift lead who also inspects
both groups rather than looking for a combined one.

!!! danger "Never add a staff group to a customer"
    A customer sees only their own orders because the **Customer** group is the
    one group that does *not* grant tenant-wide visibility. Every staff group
    does.

    So adding any staff group to a portal user — even Operator, even
    temporarily to let them "just see one thing" — hands them every order in the
    tenant, including other customers'. The data narrowing is the absence of a
    permission, and nothing you add can put it back.

    If a customer needs to see something outside their orders, share it with
    them on the order rather than changing their groups.

See [Roles & Groups](roles.md) for what each group holds.

## SSO Users

If your organization uses Single Sign-On:

Create the user and assign their groups as normal; they sign in through the
identity provider instead of setting a password. Password policy and MFA are the
IdP's (Microsoft Entra ID, Okta, and so on), not uqmes's.

Whether SSO is available depends on how your deployment is configured — see
[SSO](../../integrations/sso.md).

## Customer Users

Create portal access for customers:

1. Create the user with **User type: Portal**
2. Associate them with a Company record
3. Add them to the **Customer** group
4. They see only their own company's orders

### Customer Permissions
- View own orders and parts
- View shared documents
- Cannot access internal data

## Auditor Users

Create temporary access for auditors:

1. Create the user as **Internal**
2. Add them to the **Auditor** group, which is read-only
3. Assign nothing else — the group is the whole of their access

## Permissions

By default, managing accounts is **Tenant Admin**'s alone — no other starting group holds any of
it.

| Permission | Allows |
|------------|--------|
| `view_user` | View the user list |
| `add_user` | Create users |
| `change_user` | Edit users, and activate or deactivate them |
| `delete_user` | Remove someone's access to this organisation |

!!! note "Nothing here destroys an account"
    Both routes out suspend the person's **membership of this organisation**.
    The account survives, and so does every record carrying their name. See
    [Deactivating Users](deactivating.md).

## Next Steps

- [Roles & Groups](roles.md) - Understanding permissions
- [Assigning Permissions](permissions.md) - Configure access
- [Deactivating Users](deactivating.md) - Offboarding
