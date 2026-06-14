"""
Reconcile preset-backed TenantGroups to exactly match their preset.

Run after releases that add, remove, or relocate permission codenames so
existing tenant groups converge on the current presets. Adds missing preset
perms AND revokes perms no longer in the preset — required to enforce changes
that move a permission out of a role (e.g. scoping ITAR/export-control or
notification-rule editing). Preset-backed groups are authoritative; custom
groups (no matching preset) are left untouched. Idempotent.

    python manage.py sync_tenant_permissions
    python manage.py sync_tenant_permissions --dry-run
"""

from django.core.management.base import BaseCommand

from Tracker.groups import GroupSeeder


class Command(BaseCommand):
    help = 'Reconcile preset-backed tenant groups to exactly match their preset (adds + revokes).'

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
            f"reconciled {results['groups_updated']}, "
            f"added {results['permissions_added']}, "
            f"revoked {results['permissions_removed']} permission grants."
        ))
        if results['groups_skipped_custom']:
            self.stdout.write(self.style.NOTICE(
                f"Skipped {results['groups_skipped_custom']} custom groups "
                f"(no matching preset)."
            ))
