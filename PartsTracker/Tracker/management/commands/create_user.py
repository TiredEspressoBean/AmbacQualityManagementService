"""
Management command to create a new user for a tenant.

Usage:
    # Create an operator
    python manage.py create_user --tenant ambac-international --email john@example.com --group Operator

    # Create a QA manager with specific name
    python manage.py create_user --tenant ambac-international --email jane@example.com \\
        --first-name Jane --last-name Smith --group QA_Manager

    # Create user with password (otherwise prompted)
    python manage.py create_user --tenant ambac-international --email user@example.com \\
        --password "SecurePass123" --group Production_Manager

Available groups:
    - Tenant Admin (full access within tenant)
    - QA Manager (quality management, approvals, CAPA)
    - QA Inspector (inspections, quality reports)
    - Production Manager (production operations, scheduling)
    - Operator (production floor work)
    - Document Controller (document management)
    - Engineering (design, engineering changes)
    - Auditor (read-only audit access)
    - Customer (external portal access)
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()

# Available groups (from presets.py)
AVAILABLE_GROUPS = [
    'Tenant Admin',
    'QA Manager',
    'QA Inspector',
    'Production Manager',
    'Operator',
    'Document Controller',
    'Engineering',
    'Auditor',
    'Customer',
]


class Command(BaseCommand):
    help = 'Create a new user for a tenant'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant',
            type=str,
            required=True,
            help='Tenant slug (e.g., "ambac-international")',
        )
        parser.add_argument(
            '--email',
            type=str,
            required=True,
            help='User email address (also used as username)',
        )
        parser.add_argument(
            '--password',
            type=str,
            help='User password (prompted if not provided)',
        )
        parser.add_argument(
            '--first-name',
            type=str,
            default='',
            help='User first name',
        )
        parser.add_argument(
            '--last-name',
            type=str,
            default='',
            help='User last name',
        )
        parser.add_argument(
            '--group',
            type=str,
            required=True,
            help=f'Group to assign user to. Available: {", ".join(AVAILABLE_GROUPS)}',
        )
        parser.add_argument(
            '--portal',
            action='store_true',
            help='Create as portal user (external customer)',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from Tracker.models import Tenant, TenantGroup, UserRole

        # Resolve tenant
        tenant_slug = options['tenant']
        try:
            tenant = Tenant.objects.get(slug=tenant_slug)
        except Tenant.DoesNotExist:
            raise CommandError(f'Tenant "{tenant_slug}" not found.')

        self.stdout.write(f'Tenant: {tenant.name} ({tenant.slug})')

        # Resolve group
        group_name = options['group']
        try:
            tenant_group = TenantGroup.objects.get(tenant=tenant, name=group_name)
        except TenantGroup.DoesNotExist:
            # List available groups for this tenant
            available = TenantGroup.objects.filter(tenant=tenant).values_list('name', flat=True)
            raise CommandError(
                f'Group "{group_name}" not found for tenant {tenant_slug}.\n'
                f'Available groups: {", ".join(available)}'
            )

        # Get or prompt for password
        password = options['password']
        if not password:
            import getpass
            password = getpass.getpass('Password: ')
            if not password:
                raise CommandError('Password is required')

        email = options['email']

        # Check if user exists
        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            if existing_user.tenant and existing_user.tenant != tenant:
                raise CommandError(
                    f'User "{email}" already exists in tenant "{existing_user.tenant.slug}". '
                    f'Users cannot belong to multiple tenants.'
                )
            self.stdout.write(
                self.style.WARNING(f'User "{email}" already exists, updating...')
            )
            user = existing_user
            user.tenant = tenant
            user.first_name = options['first_name'] or user.first_name
            user.last_name = options['last_name'] or user.last_name
            if options['portal']:
                user.user_type = User.UserType.PORTAL
            user.save()
            created = False
        else:
            # Create new user (is_staff=False - that's for UQMES platform staff only)
            user = User.objects.create_user(
                email=email,
                username=email,
                password=password,
                first_name=options['first_name'],
                last_name=options['last_name'],
                tenant=tenant,
                is_staff=False,
                user_type=User.UserType.PORTAL if options['portal'] else User.UserType.INTERNAL,
            )
            created = True
            self.stdout.write(self.style.SUCCESS(f'Created user: {email}'))

        # Assign to TenantGroup via UserRole
        user_role, role_created = UserRole.objects.get_or_create(
            user=user,
            group=tenant_group,
            defaults={}
        )
        if role_created:
            self.stdout.write(f'  Assigned to group: {group_name}')
        else:
            self.stdout.write(f'  Already in group: {group_name}')

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('User setup complete!'))
        self.stdout.write(f'  Email: {user.email}')
        self.stdout.write(f'  Name: {user.first_name} {user.last_name}'.strip())
        self.stdout.write(f'  Tenant: {tenant.name}')
        self.stdout.write(f'  Group: {group_name}')
        self.stdout.write(f'  Type: {user.user_type}')
