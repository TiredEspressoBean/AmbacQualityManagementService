"""
Management command to create a new tenant with admin user.

Usage:
    python manage.py setup_tenant --slug acme --name "ACME Corp" --admin-email admin@acme.com

    # For demo tenant:
    python manage.py setup_tenant --slug demo --name "Demo Company" --demo --admin-email demo@example.com --admin-password demo

    # For dedicated deployment (uses settings defaults):
    python manage.py setup_tenant --use-defaults --admin-email admin@example.com
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction


User = get_user_model()


class Command(BaseCommand):
    help = 'Create a new tenant with admin user'

    def add_arguments(self, parser):
        parser.add_argument(
            '--slug',
            type=str,
            help='URL-safe tenant identifier (e.g., "acme")',
        )
        parser.add_argument(
            '--name',
            type=str,
            help='Display name for the tenant',
        )
        parser.add_argument(
            '--tier',
            type=str,
            choices=['starter', 'pro', 'enterprise'],
            default='pro',
            help='Tenant tier (default: pro)',
        )
        parser.add_argument(
            '--admin-email',
            type=str,
            required=True,
            help='Email for the admin user',
        )
        parser.add_argument(
            '--admin-password',
            type=str,
            help='Password for admin user (prompted if not provided)',
        )
        parser.add_argument(
            '--admin-first-name',
            type=str,
            default='Admin',
            help='Admin user first name',
        )
        parser.add_argument(
            '--admin-last-name',
            type=str,
            default='User',
            help='Admin user last name',
        )
        parser.add_argument(
            '--demo',
            action='store_true',
            help='Mark this as a demo tenant',
        )
        parser.add_argument(
            '--use-defaults',
            action='store_true',
            help='Use DEFAULT_TENANT_SLUG and DEFAULT_TENANT_NAME from settings',
        )
        parser.add_argument(
            '--no-admin',
            action='store_true',
            help='Skip admin user creation',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from Tracker.models import Tenant

        # Determine slug and name
        if options['use_defaults']:
            slug = getattr(settings, 'DEFAULT_TENANT_SLUG', 'default')
            name = getattr(settings, 'DEFAULT_TENANT_NAME', 'My Company')
            is_demo = options['demo']
        else:
            slug = options['slug']
            name = options['name']
            is_demo = options['demo']

            if not slug:
                raise CommandError('--slug is required (or use --use-defaults)')
            if not name:
                name = slug.replace('-', ' ').replace('_', ' ').title()

        # Check if tenant already exists
        existing = Tenant.objects.filter(slug=slug).first()
        if existing:
            self.stdout.write(
                self.style.WARNING(f'Tenant "{slug}" already exists.')
            )
            tenant = existing
            tenant_created = False
        else:
            # Create tenant (signals auto-seed groups and reference data)
            tenant = Tenant.objects.create(
                slug=slug,
                name=name,
                tier=options['tier'],
                status=Tenant.Status.ACTIVE,
                is_active=True,
                is_demo=is_demo,
            )
            tenant_created = True
            self.stdout.write(
                self.style.SUCCESS(f'Created tenant: {tenant.name} ({tenant.slug})')
            )

            # Report on auto-seeded data
            from Tracker.models import TenantGroup, DocumentType, ApprovalTemplate
            groups_count = TenantGroup.objects.filter(tenant=tenant).count()
            doc_types_count = DocumentType.objects.filter(tenant=tenant).count()
            templates_count = ApprovalTemplate.objects.filter(tenant=tenant).count()
            self.stdout.write(f'  Seeded {groups_count} groups with permissions')
            self.stdout.write(f'  Seeded {doc_types_count} document types')
            self.stdout.write(f'  Seeded {templates_count} approval templates')

        # Create admin user unless --no-admin
        if not options['no_admin']:
            admin_email = options['admin_email']
            admin_password = options['admin_password']

            # Prompt for password if not provided
            if not admin_password:
                import getpass
                admin_password = getpass.getpass('Admin password: ')
                if not admin_password:
                    raise CommandError('Password is required')

            # Check if user exists
            existing_user = User.objects.filter(email=admin_email).first()
            if existing_user:
                self.stdout.write(
                    self.style.WARNING(f'User "{admin_email}" already exists, updating tenant.')
                )
                existing_user.tenant = tenant
                existing_user.save(update_fields=['tenant'])
                admin_user = existing_user
            else:
                # Create admin user
                admin_user = User.objects.create_user(
                    email=admin_email,
                    username=admin_email,
                    password=admin_password,
                    first_name=options['admin_first_name'],
                    last_name=options['admin_last_name'],
                    tenant=tenant,
                    is_staff=True,
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Created admin user: {admin_email}')
                )

            # Add to Admin group
            admin_group, _ = Group.objects.get_or_create(name='Admin')
            admin_user.groups.add(admin_group)
            self.stdout.write(f'  Added to Admin group')

        # Print summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Tenant setup complete!'))
        self.stdout.write(f'  Slug: {tenant.slug}')
        self.stdout.write(f'  Name: {tenant.name}')
        self.stdout.write(f'  Tier: {tenant.tier}')
        self.stdout.write(f'  Demo: {tenant.is_demo}')
        if not options['no_admin']:
            self.stdout.write(f'  Admin: {admin_email}')
