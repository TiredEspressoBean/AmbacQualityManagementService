# First Login

This guide walks you through logging into Ambac Tracker for the first time and setting up your account.

## Accessing Ambac Tracker

Your organization's Ambac Tracker instance is available at a URL like:

```
https://yourcompany.ambactracker.com
```

Your administrator will provide the exact URL for your organization.

## Login Methods

Ambac Tracker supports two authentication methods:

### Single Sign-On (SSO)

If your organization uses Microsoft Azure AD or another identity provider:

1. Navigate to your Ambac Tracker URL
2. Click **Sign in with Microsoft** (or your organization's SSO provider)
3. Enter your corporate credentials
4. You'll be redirected back to Ambac Tracker, logged in

!!! tip "SSO Benefits"
    SSO uses your existing corporate credentials, so you don't need a separate password. Your IT team manages authentication policies like multi-factor authentication (MFA).

### Email and Password

If your organization uses direct login:

1. Navigate to your Ambac Tracker URL
2. Enter your **email address**
3. Enter your **password**
4. Click **Log In**

## First-Time Setup

### Invited Users

If you received an invitation email:

1. Click the link in the invitation email
2. Set your password (if not using SSO)
3. Complete your profile information
4. You'll be logged in automatically

### Profile Setup

After your first login, you may want to update your profile:

1. Click your **avatar** or **name** in the sidebar header
2. Select **Profile**
3. Update your information:
   - **Display Name** - How your name appears to others
   - **Email** - Your contact email (may be locked if using SSO)
   - **Phone** - Optional contact number
   - **Notification Preferences** - How you receive alerts

## Password Reset

If you forget your password:

1. Click **Forgot Password?** on the login page
2. Enter your email address
3. Click **Send Reset Link**
4. Check your email for the reset link
5. Click the link and set a new password

!!! note "SSO Users"
    If your organization uses SSO, password reset is handled by your IT department through your identity provider (Azure AD, Okta, etc.).

## Multi-Tenant Access

If you belong to multiple organizations (tenants):

1. After logging in, you'll see your primary organization
2. Click the **organization name** in the sidebar header
3. Select a different organization from the dropdown
4. The page will reload with that organization's data

Your permissions may differ between organizations based on your assigned roles.

## Troubleshooting Login Issues

| Problem | Solution |
|---------|----------|
| "Invalid credentials" | Check email spelling, reset password if needed |
| "Account locked" | Contact your administrator |
| SSO redirect fails | Clear browser cache, try incognito mode |
| "Access denied" | Your account may not be activated—contact admin |
| MFA not working | Check your authenticator app, contact IT |

## Next Steps

Now that you're logged in:

- **[Navigation Tour](navigation.md)** - Learn the interface
- **[Your First Order](first-order.md)** - Start tracking orders
