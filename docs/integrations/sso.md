# SSO / Azure AD

Single Sign-On integration with Microsoft Azure AD and other identity providers.

## Overview

SSO allows users to:
- Log in with corporate credentials
- Use existing identity provider
- Leverage organization's MFA policies
- Centralize user management

## Supported Providers

| Provider | Protocol |
|----------|----------|
| **Microsoft Azure AD** | OAuth 2.0 / OIDC |
| **Microsoft 365** | OAuth 2.0 / OIDC |
| **Okta** | SAML / OIDC |
| **Google Workspace** | OAuth 2.0 |

## Azure AD Setup

### Prerequisites
- Azure AD tenant
- Admin access to register application
- Ambac Tracker admin access

### Configuration Steps

1. **Register Application in Azure AD**
   - Go to Azure Portal > Azure Active Directory
   - App registrations > New registration
   - Name: "Ambac Tracker"
   - Redirect URI: `https://yourapp.ambactracker.com/accounts/microsoft/login/callback/`

2. **Configure Application**
   - Note Application (client) ID
   - Create client secret
   - Configure API permissions:
     - Microsoft Graph: User.Read
     - Microsoft Graph: email
     - Microsoft Graph: profile

3. **Configure Ambac Tracker**
   - Contact Ambac support with:
     - Client ID
     - Client Secret
     - Tenant ID

4. **Test SSO**
   - Log out of Ambac Tracker
   - Click "Sign in with Microsoft"
   - Authenticate via Azure AD
   - Verify successful login

## User Provisioning

### Automatic (JIT)
- User logs in via SSO
- Account created automatically
- Assigned to default group

### Pre-Provisioning
- Create user account manually
- Set email to match Azure AD
- User links on first SSO login

### SCIM (if available)
- Automatic user sync
- Group sync
- Deprovisioning sync

## Group Mapping

Map Azure AD groups to Ambac Tracker groups:

| Azure AD Group | Ambac Tracker Group |
|----------------|---------------------|
| QA_Inspectors | QA Inspector |
| Production_Team | Operator |
| Quality_Managers | QA Manager |

Configure in Admin settings.

## MFA Enforcement

MFA is handled by the identity provider:
- Configure MFA policy in Azure AD
- Ambac Tracker inherits MFA
- No separate MFA configuration needed

## Session Management

### Session Duration
- Controlled by Azure AD policy
- Ambac Tracker session matches
- Configurable timeout

### Single Logout
- Logout from Ambac Tracker
- Optionally logout from Azure AD
- Clear all sessions

## Troubleshooting SSO

### "Invalid redirect URI"
- Verify redirect URI matches exactly
- Check for trailing slashes
- Confirm protocol (https)

### "User not found"
- User may not exist in Ambac Tracker
- Check auto-provisioning settings
- Verify email matches

### "Access denied"
- User may be deactivated
- Check Azure AD group membership
- Verify application assignment in Azure

## Security Considerations

- Use HTTPS only
- Rotate client secrets periodically
- Review access logs
- Monitor failed login attempts

## Permissions

| Permission | Allows |
|------------|--------|
| `change_sso_settings` | Configure SSO (admin) |

## Best Practices

1. **Test thoroughly** - Before production rollout
2. **Document configuration** - For disaster recovery
3. **Monitor logs** - Watch for issues
4. **Plan offboarding** - Deactivate in both systems
5. **Use groups** - Simplify permission management
