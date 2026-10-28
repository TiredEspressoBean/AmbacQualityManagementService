# First Login

This guide walks you through logging into uqmes for the first time and setting up your account.

## Accessing uqmes

Your organization's uqmes has its own web address, which depends on how it is
hosted. Your administrator will give it to you.

## Login Methods

uqmes supports two authentication methods:

### Single Sign-On (SSO)

If your organization uses Microsoft Entra ID or another identity provider:

1. Navigate to your uqmes URL
2. Click **Login with Microsoft**
3. Enter your corporate credentials
4. You'll be redirected back to uqmes, logged in

!!! tip "SSO Benefits"
    SSO uses your existing corporate credentials, so you don't need a separate password. Your IT team manages authentication policies like multi-factor authentication (MFA).

!!! note "The Microsoft button is always there"
    **Login with Microsoft** appears on every login page, whether or not your
    organization has set SSO up. If yours hasn't, it will not sign you in — use
    your email and password.

### Email and Password

If your organization uses direct login:

1. Navigate to your uqmes URL
2. Enter your **email address**
3. Enter your **password**
4. Click **Login**

### A notice on the login page

Your organization may show a notice above **Login** — typically a statement of
who may use the system and that use is monitored. If it asks you to, tick **I
acknowledge this notice**; **Login** and **Login with Microsoft** stay
unavailable until you do, and a sign-in without it is refused: *Acknowledge the
notice to sign in.*

The wording is your organization's. Administrators set it under **Settings** >
**Organization** — **Sign-in notice**, and **Require acknowledgement to sign
in**, which is available once there is a notice. Blank shows nothing; nothing
is shown by default.

Each acknowledged sign-in with email and password is recorded in the audit
log as an access entry — who, when, from which address, and a fingerprint of
the wording they saw. A sign-in with Microsoft needs the box ticked on the page
but is not recorded as an acknowledgement.

!!! note "The page has to know which organization it belongs to"
    The notice shows where the login page is your organization's own — a
    dedicated installation, or your organization's own address on a shared
    one. On a shared address that serves several organizations, no notice
    applies.

## First-Time Setup

### Invited Users

You are let in by an **invitation link**. It may reach you by email, or your
administrator may hand it to you directly — whether email is sent depends on how
your deployment is set up.

1. Open the link
2. Set your password (if not using SSO)
3. Complete your profile information
4. You'll be logged in automatically

If the link has expired, ask your administrator for a new one.

### Profile Setup

After your first login, you may want to update your profile:

1. Click your **name** at the **bottom of the sidebar**
2. Select **Profile**
3. Under **Personal Information**, click **Edit** to update:
   - **First Name** and **Last Name**
   - **Email** - Your contact email (may be locked if using SSO)

The Profile page also shows read-only **Account Information** and a **Change
Password** card.

!!! note "Notification preferences live elsewhere"
    Notification settings are not on the Profile page. Choose **My
    Notifications** from the same sidebar menu (`/profile/notifications`).

## Password Reset

If you forget your password:

1. Click **Forgot your password?** on the login page
2. Enter your email address
3. Click **Send reset email**
4. Check your email for the reset link
5. Click the link and set a new password

!!! note "SSO Users"
    If your organization uses SSO, password reset is handled by your IT department through your identity provider (Microsoft Entra ID, Okta, etc.).

!!! tip "If the reset email never arrives"
    The reset depends on this deployment sending mail, which not every one does.
    If nothing arrives, ask your administrator: an **access link** from User
    Management lets you set a new password without email.

## Multi-Tenant Access

If you belong to multiple organizations (tenants):

1. After logging in, you'll see your primary organization
2. Click the **organization name** at the **top of the sidebar**
3. Select a different organization from the menu
4. The page will reload with that organization's data

Your permissions may differ between organizations based on your assigned roles.

## Troubleshooting Login Issues

| Problem | Solution |
|---------|----------|
| *"Invalid email or password"* | Check the spelling, then reset your password if needed |
| *"Request was throttled"* | Too many attempts in a short time — by default ten logins a minute, or five password resets an hour, from one address. Wait for the time it names. There is no account lockout |
| **Login with Microsoft** does nothing useful | Your organization may not use SSO — sign in with email and password |
| SSO redirect fails | Clear browser cache, try a private window; if it persists, it is your identity provider's configuration |
| You can sign in but see nothing, or are refused | Your access to this organization may be deactivated — contact your administrator |
| MFA not working | MFA belongs to your identity provider — check your authenticator app, then contact IT |

## Next Steps

Now that you're logged in:

- **[Navigation Tour](navigation.md)** - Learn the interface
- **[Your First Order](first-order.md)** - Start tracking orders
