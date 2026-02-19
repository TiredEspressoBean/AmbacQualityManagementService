"""
Custom allauth adapters for tenant-aware user creation.

Handles multiple onboarding flows:
- Invitation: User invited to existing tenant
- Self-service: User creates new tenant (becomes admin)
- Subdomain: Tenant resolved from request by middleware
- SSO (Microsoft/Azure AD): User signs in via corporate identity provider
"""

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth.models import Group
import logging

logger = logging.getLogger(__name__)


class TenantAccountAdapter(DefaultAccountAdapter):
    """
    Adapter that assigns tenant to new users based on signup context.

    Priority order:
    1. Invitation token in session → inherit tenant from invitation
    2. Tenant in request (from middleware) → use that tenant
    3. Self-service signup → create new tenant, user becomes admin
    """

    def save_user(self, request, user, form, commit=True):
        """Assign tenant to user during signup."""
        user = super().save_user(request, user, form, commit=False)

        tenant = self._resolve_tenant(request, user, form)
        if tenant:
            user.tenant = tenant

        if commit:
            user.save()
            self._assign_default_groups(request, user, tenant)

        return user

    def _resolve_tenant(self, request, user, form):
        """
        Determine tenant for new user.

        Returns Tenant instance or None.
        """
        # 1. Check for invitation
        tenant = self._tenant_from_invitation(request)
        if tenant:
            return tenant

        # 2. Check request (set by TenantMiddleware from subdomain)
        tenant = getattr(request, 'tenant', None)
        if tenant:
            return tenant

        # 3. Self-service: create new tenant
        tenant = self._create_tenant_for_user(request, user, form)
        return tenant

    def _tenant_from_invitation(self, request):
        """Get tenant from invitation token in session."""
        from Tracker.models import UserInvitation

        token = request.session.get('invitation_token')
        if not token:
            return None

        try:
            invitation = UserInvitation.objects.select_related('user__tenant').get(
                token=token,
                accepted_at__isnull=True
            )
            if invitation.is_valid():
                return invitation.user.tenant
        except UserInvitation.DoesNotExist:
            pass

        return None

    def _create_tenant_for_user(self, request, user, form):
        """
        Create new tenant for self-service signup.

        User becomes the first admin of their new tenant.
        """
        from Tracker.models import Tenant
        from django.utils.text import slugify

        # Get organization name from form or generate from email
        org_name = getattr(form, 'cleaned_data', {}).get('organization_name')
        if not org_name:
            # Generate from email domain: john@acme.com -> "Acme"
            email_domain = user.email.split('@')[-1].split('.')[0]
            org_name = email_domain.title()

        # Generate unique slug
        base_slug = slugify(org_name)
        slug = base_slug
        counter = 1
        while Tenant.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        tenant = Tenant.objects.create(
            name=org_name,
            slug=slug,
        )

        # Mark this as self-service signup so we know to make them admin
        request._created_tenant = True

        return tenant

    def _assign_default_groups(self, request, user, tenant):
        """Assign default group memberships after user creation."""
        from Tracker.models import TenantGroupMembership

        if not tenant:
            return

        # If they created their own tenant, make them admin
        if getattr(request, '_created_tenant', False):
            try:
                admin_group = Group.objects.get(name='Admin')
                TenantGroupMembership.objects.create(
                    tenant=tenant,
                    user=user,
                    group=admin_group,
                )
            except Group.DoesNotExist:
                pass  # Admin group not set up yet

        # If from invitation, copy groups from invitation (future enhancement)
        # invitation = ...
        # for group in invitation.groups.all():
        #     TenantGroupMembership.objects.create(...)


class TenantSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Adapter for social account (SSO) logins with tenant awareness.

    Handles Microsoft/Azure AD SSO login flows:
    - Existing user: Link social account, preserve tenant
    - New user with matching email domain: Assign to tenant with that domain
    - New user (no matching tenant): Create new tenant (self-service)
    """

    def pre_social_login(self, request, sociallogin):
        """
        Called after successful SSO auth but before login/signup completes.

        This is the hook to link existing users by email.
        """
        # If user already exists with this email, connect the social account
        if sociallogin.is_existing:
            return

        email = sociallogin.account.extra_data.get('mail') or \
                sociallogin.account.extra_data.get('userPrincipalName', '')

        if not email:
            return

        from Tracker.models import User
        try:
            existing_user = User.objects.get(email__iexact=email)
            sociallogin.connect(request, existing_user)
            logger.info(f"Linked SSO account to existing user: {email}")
        except User.DoesNotExist:
            pass

    def save_user(self, request, sociallogin, form=None):
        """
        Create new user from social login with tenant assignment.
        """
        user = super().save_user(request, sociallogin, form)

        # Assign tenant if not already set
        if not user.tenant:
            tenant = self._resolve_tenant_for_sso(request, user, sociallogin)
            if tenant:
                user.tenant = tenant
                user.save(update_fields=['tenant'])
                self._assign_default_groups(request, user, tenant, sociallogin)

        return user

    def _resolve_tenant_for_sso(self, request, user, sociallogin):
        """
        Determine tenant for SSO user.

        Priority:
        1. Invitation in session
        2. Tenant from request (subdomain)
        3. Match by email domain (if tenant has allowed_domains configured)
        4. Create new tenant (self-service)
        """
        from Tracker.models import Tenant, UserInvitation
        from django.utils.text import slugify

        # 1. Check for invitation
        token = request.session.get('invitation_token')
        if token:
            try:
                invitation = UserInvitation.objects.select_related('user__tenant').get(
                    token=token,
                    accepted_at__isnull=True
                )
                if invitation.is_valid():
                    logger.info(f"SSO user {user.email} joining tenant from invitation")
                    return invitation.user.tenant
            except UserInvitation.DoesNotExist:
                pass

        # 2. Check request tenant (from subdomain middleware)
        if getattr(request, 'tenant', None):
            logger.info(f"SSO user {user.email} joining tenant from subdomain")
            return request.tenant

        # 3. Match by email domain (allowed_domains is a JSONField with list of domains)
        email_domain = user.email.split('@')[-1].lower()
        tenant = Tenant.objects.filter(
            allowed_domains__contains=[email_domain]
        ).first()
        if tenant:
            logger.info(f"SSO user {user.email} matched to tenant {tenant.slug} by domain")
            return tenant

        # 4. Create new tenant (self-service SSO signup)
        # Use organization info from Azure AD if available
        extra_data = sociallogin.account.extra_data
        org_name = extra_data.get('companyName') or \
                   extra_data.get('organization', {}).get('displayName') or \
                   email_domain.split('.')[0].title()

        base_slug = slugify(org_name)
        slug = base_slug
        counter = 1
        while Tenant.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        tenant = Tenant.objects.create(
            name=org_name,
            slug=slug,
        )

        # Mark that we created the tenant so user becomes admin
        request._created_tenant = True
        logger.info(f"Created new tenant {tenant.slug} for SSO user {user.email}")

        return tenant

    def _assign_default_groups(self, request, user, tenant, sociallogin):
        """Assign groups after SSO signup."""
        from Tracker.models import TenantGroupMembership

        if not tenant:
            return

        # If they created their own tenant via SSO, make them admin
        if getattr(request, '_created_tenant', False):
            try:
                admin_group = Group.objects.get(name='Admin')
                TenantGroupMembership.objects.get_or_create(
                    tenant=tenant,
                    user=user,
                    group=admin_group,
                )
                logger.info(f"Assigned Admin group to SSO user {user.email}")
            except Group.DoesNotExist:
                logger.warning("Admin group not found, skipping group assignment")

    def populate_user(self, request, sociallogin, data):
        """
        Populate user fields from social account data.

        Called during user creation to set initial field values.
        """
        user = super().populate_user(request, sociallogin, data)

        # Extract additional fields from Microsoft/Azure AD
        extra_data = sociallogin.account.extra_data

        # Microsoft Graph API returns these fields
        if not user.first_name:
            user.first_name = extra_data.get('givenName', '')
        if not user.last_name:
            user.last_name = extra_data.get('surname', '')
        if not user.email:
            user.email = extra_data.get('mail') or extra_data.get('userPrincipalName', '')

        # Optional: Store job title if your User model has this field
        # user.job_title = extra_data.get('jobTitle', '')

        return user
