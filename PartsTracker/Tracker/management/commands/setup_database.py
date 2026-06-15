"""
Management command to run all database setup after migrations.

Usage:
    python manage.py setup_database [--skip-extensions] [--skip-rls] [--skip-triggers]

This is the single command to run after migrations to set up:
1. PostgreSQL extensions (pgvector, pg_trgm)
2. User groups (for RBAC)
3. Row-Level Security policies (if ENABLE_RLS=true)
4. Audit immutability triggers (for compliance)

Typical deployment:
    python manage.py migrate
    python manage.py setup_database
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings


class Command(BaseCommand):
    help = 'Run all database setup commands after migrations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-extensions',
            action='store_true',
            help='Skip PostgreSQL extensions setup',
        )
        parser.add_argument(
            '--skip-rls',
            action='store_true',
            help='Skip RLS setup',
        )
        parser.add_argument(
            '--skip-triggers',
            action='store_true',
            help='Skip audit trigger setup',
        )
        parser.add_argument(
            '--skip-groups',
            action='store_true',
            help='Skip user group creation',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('Database Setup'))
        self.stdout.write('')

        # 1. PostgreSQL Extensions
        if not options['skip_extensions']:
            self.stdout.write(self.style.MIGRATE_HEADING('Step 1: PostgreSQL Extensions'))
            call_command('setup_extensions', stdout=self.stdout)
            self.stdout.write('')

        # 2. User Groups
        if not options['skip_groups']:
            self.stdout.write(self.style.MIGRATE_HEADING('Step 2: User Groups'))
            # Global app-level groups were retired in favor of per-tenant
            # TenantGroups (see migration 0072). The old `setup_groups` command
            # no longer exists; backfill each tenant's preset groups instead.
            # Idempotent (get_or_create). Permission reconcile for existing
            # groups is a separate step: `sync_tenant_permissions`.
            from Tracker.groups import GroupSeeder
            result = GroupSeeder.backfill_all_tenants()
            self.stdout.write(
                f"  Seeded groups for {result['tenants']} tenant(s); "
                f"created {result['groups_created']} new group(s)."
            )
            self.stdout.write('')

        # 3. Row-Level Security
        if not options['skip_rls']:
            self.stdout.write(self.style.MIGRATE_HEADING('Step 3: Row-Level Security'))
            if getattr(settings, 'ENABLE_RLS', False):
                call_command('setup_rls', stdout=self.stdout)
            else:
                self.stdout.write(
                    '  Skipped (ENABLE_RLS=False in settings)'
                )
            self.stdout.write('')

        # 4. Audit Triggers
        if not options['skip_triggers']:
            self.stdout.write(self.style.MIGRATE_HEADING('Step 4: Audit Triggers'))
            call_command('setup_audit_triggers', stdout=self.stdout)
            self.stdout.write('')

        self.stdout.write(self.style.SUCCESS('Database setup complete!'))
