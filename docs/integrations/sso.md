# SSO / Azure AD

Single Sign-On integration with Microsoft Azure AD and other identity providers.

!!! note "Administrator Configuration"
    SSO is configured by system administrators via backend settings. Contact your administrator or uqmes support for SSO setup.

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
- uqmes admin access

### Configuration Steps

1. **Register Application in Azure AD**
   - Go to Azure Portal > Azure Active Directory
   - App registrations > New registration
   - Name: "uqmes"
   - Redirect URI: `https://yourapp.uqmes.com/accounts/microsoft/login/callback/`

2. **Configure Application**
   - Note Application (client) ID
   - Create client secret
   - Configure API permissions:
     - Microsoft Graph: User.Read
     - Microsoft Graph: email
     - Microsoft Graph: profile

3. **Configure uqmes**
   - Contact uqmes support with:
     - Client ID
     - Client Secret
     - Tenant ID

4. **Test SSO**
   - Log out of uqmes
   - Click "Sign in with Microsoft"
   - Authenticate via Azure AD
   - Verify successful login

## On-Premises / Firewalled Deployment

For a self-hosted instance behind a corporate firewall on an internal hostname
(e.g. `govtracker.ambac.local`) over TLS. Microsoft Entra SSO still works — the
sign-in is browser-mediated cloud auth — but a locked-down network needs a few
specific allowances.

!!! warning "Not for fully air-gapped sites"
    Cloud Entra SSO requires reaching Microsoft. A fully air-gapped deployment
    cannot use it — use on-prem **ADFS** or local accounts there instead. A
    controlled-egress firewall is fine.

### Backend configuration (environment variables)

SSO config is read from the environment; set these and redeploy (the Microsoft
provider only loads when `SSO_ENABLED=true`):

| Variable | Value |
|----------|-------|
| `SSO_ENABLED` | `true` |
| `AZURE_CLIENT_ID` | Application (client) ID from the app registration |
| `AZURE_CLIENT_SECRET` | Client secret value |
| `AZURE_TENANT_ID` | Your Directory (tenant) **GUID** — not `common`, for a single organization |
| `ALLOWED_HOSTS` | must include `govtracker.ambac.local` |
| `CSRF_TRUSTED_ORIGINS` | must include `https://govtracker.ambac.local` |

Also set the Django **Sites** entry (Site ID 1) domain to the internal host —
allauth builds the absolute callback URL from it.

### Redirect URI

Register it exactly (scheme, host, path, and trailing slash must all match):

```
https://govtracker.ambac.local/accounts/microsoft/login/callback/
```

Entra accepts internal, non-public hostnames for *web* redirect URIs and requires
`https`; internal TLS satisfies that.

### Firewall — outbound only (no inbound from the internet)

The OAuth code exchange and profile lookup run **server-side**, so the app server
needs outbound 443 to:

- `login.microsoftonline.com` — token and signing-key endpoints
- `graph.microsoft.com` — the `User.Read` profile call

Allowlist by **FQDN**, not IP — Microsoft rotates IPs across their CDN, so IP rules
break unpredictably. Client browsers also need to reach `login.microsoftonline.com`
for the interactive login (usually already permitted on a corporate network).

!!! danger "TLS inspection breaks SSO"
    If the firewall performs deep TLS / SSL interception, the app server sees the
    firewall's certificate instead of Microsoft's and **certificate verification
    fails — the token exchange dies with an SSL error.** Either exempt
    `login.microsoftonline.com` and `graph.microsoft.com` from inspection
    (Microsoft's recommendation for auth endpoints), **or** install the firewall's
    root CA into the app server's trust store.

### TLS terminated at a proxy, firewall, or switch

When TLS terminates upstream and plain traffic is forwarded to the app, the
terminator **must send `X-Forwarded-Proto: https`** (and the real
`Host: govtracker.ambac.local`). The backend trusts that header in production
(`SECURE_PROXY_SSL_HEADER`). Without it, Django treats the request as HTTP, allauth
builds an `http://…/callback`, and Entra rejects it as a redirect-URI mismatch —
the single most common on-prem SSO failure.

Client machines must also trust the internal CA certificate for the `.local` host
(typically distributed via GPO in a Microsoft environment).

## User Provisioning

### Automatic (JIT)
- User logs in via SSO
- Account created automatically
- Assigned to default group

### Pre-Provisioning
- Create the user account ahead of time (e.g. via an invitation) — it's created in
  the target tenant with its role already set.
- **Set the email to exactly match the user's Entra primary email / UPN.** On their
  first Microsoft sign-in, the SSO identity is auto-linked to that existing account
  by email (case-insensitive), preserving their tenant and role. No duplicate
  account, no new tenant.
- **If the emails don't match**, the sign-in is treated as a *new* user, and the
  tenant is resolved in this order: (1) an invitation token in the session, (2) the
  request's tenant (from the host/subdomain), (3) an email-**domain** match against
  a tenant's `allowed_domains`, and as a last resort (4) **a brand-new tenant is
  created with the user as its admin.**

!!! tip "Prevent stray tenant creation"
    For a single-organization deployment, set the tenant's `allowed_domains` to your
    domain (e.g. `ambac.net`). That makes step (3) above a safety net — anyone who
    isn't matched by exact email still lands in the correct tenant instead of
    spawning a new one.

### SCIM

!!! note "Planned Feature"
    SCIM provisioning is planned for a future release.

## Group Mapping

Azure AD groups can be mapped to uqmes permission groups. Contact your administrator for group mapping configuration.

## MFA Enforcement

MFA is handled by the identity provider:
- Configure MFA policy in Azure AD
- uqmes inherits MFA
- No separate MFA configuration needed

## Session Management

### Session Duration
- Controlled by Azure AD policy
- uqmes session matches
- Configurable timeout

### Single Logout
- Logout from uqmes
- Optionally logout from Azure AD
- Clear all sessions

## Troubleshooting SSO

### "Invalid redirect URI"
- Verify redirect URI matches exactly
- Check for trailing slashes
- Confirm protocol (https)

### "User not found"
- User may not exist in uqmes
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
