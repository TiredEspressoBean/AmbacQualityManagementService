"""
Demo user seeder with preset, deterministic users.

Creates the exact users specified in DEMO_DATA_SYSTEM.md for sales demos
and user training. All users have known credentials (password: demo123).

Users:
    - admin@demo.ambac.com (Alex Demo) - Tenant Admin
    - sarah.qa@demo.ambac.com (Sarah Chen) - QA Inspector
    - mike.ops@demo.ambac.com (Mike Rodriguez) - Operator
    - jennifer.mgr@demo.ambac.com (Jennifer Walsh) - Production Manager
    - dave.wilson@demo.ambac.com (Dave Wilson) - Operator (expired training demo)
    - tom.bradley@midwestfleet.com (Tom Bradley) - Customer Portal
"""

from django.contrib.auth import get_user_model
from django.utils import timezone

from Tracker.models import TenantGroup, UserRole

from ..base import BaseSeeder

User = get_user_model()


# Preset demo users - covers ALL roles for comprehensive training
# Each training guide (docs/training/*.md) has a corresponding demo user
# NOTE: All enum values MUST be UPPERCASE to match model TextChoices
DEMO_USERS = [
    # === ADMIN ===
    {
        'email': 'admin@demo.ambac.com',
        'password': 'demo123',
        'first_name': 'Alex',
        'last_name': 'Demo',
        'role': 'Tenant Admin',
        'user_type': 'INTERNAL',  # UPPERCASE enum value
        'is_staff': True,
        'is_active': True,
        'is_superuser': False,
        'citizenship': 'USA',
        'us_person': True,
        'eu_authorized': False,
        'uk_authorized': False,
        'export_control_verified': True,
        'purpose': 'Admin training - full access, user management, configuration',
    },
    # === QA MANAGER ===
    {
        'email': 'maria.qa@demo.ambac.com',
        'password': 'demo123',
        'first_name': 'Maria',
        'last_name': 'Santos',
        'role': 'QA Manager',
        'user_type': 'INTERNAL',  # UPPERCASE enum value
        'is_staff': False,
        'is_active': True,
        'is_superuser': False,
        'citizenship': 'USA',
        'us_person': True,
        'eu_authorized': False,
        'uk_authorized': False,
        'export_control_verified': True,
        'purpose': 'QA Manager training - CAPA ownership, disposition approvals, SPC oversight',
    },
    # === QA INSPECTOR ===
    {
        'email': 'sarah.qa@demo.ambac.com',
        'password': 'demo123',
        'first_name': 'Sarah',
        'last_name': 'Chen',
        'role': 'QA Inspector',
        'user_type': 'INTERNAL',  # UPPERCASE enum value
        'is_staff': False,
        'is_active': True,
        'is_superuser': False,
        'citizenship': 'USA',
        'us_person': True,
        'eu_authorized': False,
        'uk_authorized': False,
        'export_control_verified': True,
        'purpose': 'QA Inspector training - inspections, quality reports, measurements',
    },
    # === PRODUCTION MANAGER ===
    {
        'email': 'jennifer.mgr@demo.ambac.com',
        'password': 'demo123',
        'first_name': 'Jennifer',
        'last_name': 'Walsh',
        'role': 'Production Manager',
        'user_type': 'INTERNAL',  # UPPERCASE enum value
        'is_staff': False,
        'is_active': True,
        'is_superuser': False,
        'citizenship': 'USA',
        'us_person': True,
        'eu_authorized': False,
        'uk_authorized': False,
        'export_control_verified': True,
        'purpose': 'Production Manager training - oversight, scheduling, approvals',
    },
    # === OPERATORS ===
    {
        'email': 'mike.ops@demo.ambac.com',
        'password': 'demo123',
        'first_name': 'Mike',
        'last_name': 'Rodriguez',
        'role': 'Operator',
        'user_type': 'INTERNAL',  # UPPERCASE enum value
        'is_staff': False,
        'is_active': True,
        'is_superuser': False,
        'citizenship': 'USA',
        'us_person': True,
        'eu_authorized': False,
        'uk_authorized': False,
        'export_control_verified': True,
        'purpose': 'Operator training - step completion, measurements, work queue',
    },
    {
        'email': 'dave.wilson@demo.ambac.com',
        'password': 'demo123',
        'first_name': 'Dave',
        'last_name': 'Wilson',
        'role': 'Operator',
        'user_type': 'INTERNAL',  # UPPERCASE enum value
        'is_staff': False,
        'is_active': True,
        'is_superuser': False,
        'citizenship': 'USA',
        'us_person': True,
        'eu_authorized': False,
        'uk_authorized': False,
        'export_control_verified': True,
        'purpose': 'Training compliance demo - EXPIRED certification blocks work',
    },
    # === DOCUMENT CONTROLLER ===
    {
        'email': 'lisa.docs@demo.ambac.com',
        'password': 'demo123',
        'first_name': 'Lisa',
        'last_name': 'Park',
        'role': 'Document Controller',
        'user_type': 'INTERNAL',  # UPPERCASE enum value
        'is_staff': False,
        'is_active': True,
        'is_superuser': False,
        'citizenship': 'USA',
        'us_person': True,
        'eu_authorized': False,
        'uk_authorized': False,
        'export_control_verified': True,
        'purpose': 'Document Controller training - document management, revisions, approvals',
    },
    # === CUSTOMER PORTAL ===
    {
        'email': 'tom.bradley@midwestfleet.com',
        'password': 'demo123',
        'first_name': 'Tom',
        'last_name': 'Bradley',
        'role': 'Customer',
        'user_type': 'PORTAL',  # UPPERCASE enum value
        'is_staff': False,
        'is_active': True,
        'is_superuser': False,
        'citizenship': 'USA',
        'us_person': True,
        'eu_authorized': False,
        'uk_authorized': False,
        'export_control_verified': False,  # External users not verified
        'purpose': 'Customer portal training - order tracking, self-service',
        'company_name': 'Midwest Fleet Services',
    },
]


class DemoUserSeeder(BaseSeeder):
    """
    Creates preset demo users with known credentials.

    All users get password 'demo123' and are assigned to appropriate
    TenantGroups based on their role.
    """

    def __init__(self, stdout, style, tenant, scale='small'):
        super().__init__(stdout, style, scale=scale)
        self.tenant = tenant

    def seed(self, companies=None):
        """
        Create all demo users and assign them to tenant groups.

        Args:
            companies: Optional dict of companies by name for linking customer users

        Returns:
            dict with created users organized by role
        """
        self.log("Creating demo users...")

        result = {
            'admin': None,
            'employees': [],
            'customers': [],
            'managers': [],
            'qa_staff': [],
            'by_email': {},
        }

        for user_data in DEMO_USERS:
            user = self._create_user(user_data, companies)
            result['by_email'][user.email] = user

            if user_data['role'] == 'Tenant Admin':
                result['admin'] = user
                result['employees'].append(user)
                result['managers'].append(user)
            elif user_data['role'] == 'Customer':
                result['customers'].append(user)
            else:
                result['employees'].append(user)

                if user_data['role'] in ('QA Manager', 'QA Inspector'):
                    result['qa_staff'].append(user)
                if user_data['role'] in ('QA Manager',):
                    result['qa_manager'] = user
                if user_data['role'] in ('Production Manager',):
                    result['managers'].append(user)
                if user_data['role'] in ('Document Controller',):
                    result['doc_controller'] = user

        self.log(f"  Created {len(DEMO_USERS)} demo users")
        return result

    def _create_user(self, user_data, companies=None):
        """Create a single demo user with all fields explicitly set."""
        # Resolve parent_company if company_name is provided
        parent_company = None
        if user_data.get('company_name') and companies:
            parent_company = companies.get(user_data['company_name'])

        # Build defaults dict with ALL fields explicitly set
        defaults = {
            'username': user_data['email'],
            'first_name': user_data['first_name'],
            'last_name': user_data['last_name'],
            'tenant': self.tenant,
            'user_type': user_data['user_type'],  # UPPERCASE enum value
            'is_staff': user_data['is_staff'],
            'is_active': user_data['is_active'],
            'is_superuser': user_data['is_superuser'],
            'parent_company': parent_company,
            # Export control fields - explicitly set
            'citizenship': user_data['citizenship'],
            'us_person': user_data['us_person'],
            'eu_authorized': user_data['eu_authorized'],
            'uk_authorized': user_data['uk_authorized'],
            'export_control_verified': user_data['export_control_verified'],
        }

        user, created = User.objects.update_or_create(
            email=user_data['email'],
            defaults=defaults
        )

        # Always set password on create, or update if password changed
        if created:
            user.set_password(user_data['password'])
            user.save(update_fields=['password'])

        # Assign to TenantGroup using update_or_create
        self._assign_to_group(user, user_data['role'])

        action = "Created" if created else "Updated"
        if self.verbose:
            self.log(f"    {action}: {user.first_name} {user.last_name} ({user.email}) - {user_data['role']}")

        return user

    def _assign_to_group(self, user, role_name):
        """Assign user to the appropriate TenantGroup using update_or_create."""
        # Map role names to TenantGroup names (from presets.py)
        role_to_group = {
            'Tenant Admin': 'Tenant Admin',
            'QA Manager': 'QA Manager',
            'QA Inspector': 'QA Inspector',
            'Production Manager': 'Production Manager',
            'Operator': 'Operator',
            'Document Controller': 'Document Controller',
            'Customer': 'Customer',
        }

        group_name = role_to_group.get(role_name)
        if not group_name:
            self.log(f"    Warning: Unknown role '{role_name}' - skipping group assignment")
            return

        try:
            tenant_group = TenantGroup.objects.get(tenant=self.tenant, name=group_name)

            # Use update_or_create to ensure fields are set correctly
            # Explicitly set all fields - do NOT rely on model defaults
            UserRole.objects.update_or_create(
                user=user,
                group=tenant_group,
                facility=None,  # Part of unique_together constraint
                company=None,   # Part of unique_together constraint
                defaults={
                    'granted_by': None,  # System-created
                    'granted_at': timezone.now(),  # Explicitly set timestamp
                }
            )
        except TenantGroup.DoesNotExist:
            self.log(f"    Warning: TenantGroup '{group_name}' not found for tenant")

    @property
    def verbose(self):
        """Check if verbose output is enabled."""
        return getattr(self, '_verbose', False)

    @verbose.setter
    def verbose(self, value):
        self._verbose = value
