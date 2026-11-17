"""
Bring preset-backed TenantGroups up to their preset, keeping admins' additions.

Adds missing preset perms, and revokes a perm only when its preset granted it once
and no longer does (presets.RETIRED_PRESET_PERMISSIONS) — so moving a permission out
of a role still takes effect. Anything else a tenant admin added stays; custom groups
(no matching preset name) are left untouched. Runs on every migrate anyway; this is
the manual run. Idempotent.

    python manage.py sync_tenant_permissions
    python manage.py sync_tenant_permissions --dry-run
"""

from django.core.management.base import BaseCommand

from Tracker.groups import GroupSeeder


class Command(BaseCommand):
    help = "Bring preset-backed tenant groups up to their preset (adds; revokes only retired preset perms)."

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
