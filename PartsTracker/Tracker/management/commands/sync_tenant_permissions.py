"""
Additively sync preset permissions onto existing TenantGroups.

Run after releases that introduce new permission codenames so existing
tenant groups pick up the new defaults without overriding admin
customisations. Idempotent.

    python manage.py sync_tenant_permissions
    python manage.py sync_tenant_permissions --dry-run
"""

from django.core.management.base import BaseCommand

from Tracker.groups import GroupSeeder


class Command(BaseCommand):
    help = 'Add new preset permissions to existing tenant groups (additive, non-destructive).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report what would change without writing.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        results = GroupSeeder.sync_permissions(dry_run=dry_run)

        prefix = '[DRY RUN] ' if dry_run else ''
        self.stdout.write(self.style.SUCCESS(
            f"{prefix}Inspected {results['groups_inspected']} groups, "
            f"updated {results['groups_updated']}, "
            f"added {results['permissions_added']} permission grants."
        ))
        if results['groups_skipped_custom']:
            self.stdout.write(self.style.NOTICE(
                f"Skipped {results['groups_skipped_custom']} custom groups "
                f"(no matching preset)."
            ))
