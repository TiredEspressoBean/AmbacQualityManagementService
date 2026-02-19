"""
Management command to create standard user groups.

Usage:
    python manage.py setup_groups

This replaces the old 0002_seed_user_groups migration.
Groups are created idempotently - safe to run multiple times.
Permissions are assigned by the post_migrate signal in apps.py.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group


class Command(BaseCommand):
    help = 'Create standard user groups for RBAC'

    # Standard groups for the application
    GROUPS = [
        'Admin',
        'QA_Manager',
        'QA_Inspector',
        'Production_Manager',
        'Production_Operator',
        'Document_Controller',
        'Customer',
    ]

    def handle(self, *args, **options):
        self.stdout.write('Creating user groups...')

        created_count = 0
        for group_name in self.GROUPS:
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(f'  Created: {group_name}')
                created_count += 1
            else:
                self.stdout.write(f'  Exists:  {group_name}')

        self.stdout.write(
            self.style.SUCCESS(f'Done. Created {created_count} new groups.')
        )
        self.stdout.write(
            '  Note: Permissions are assigned by post_migrate signal.'
        )
