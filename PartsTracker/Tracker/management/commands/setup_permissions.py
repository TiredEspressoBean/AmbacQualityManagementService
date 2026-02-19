"""
Management command to set up group permissions.

Usage:
    python manage.py setup_permissions              # Apply permissions
    python manage.py setup_permissions --dry-run   # Preview changes
    python manage.py setup_permissions --diff      # Show differences
    python manage.py setup_permissions --status    # Show current status
"""

from django.core.management.base import BaseCommand

from Tracker.services.permission_service import PermissionService, get_permission_diff
from Tracker.permissions import get_group_names


class Command(BaseCommand):
    help = 'Set up group permissions from the declarative permission structure'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without applying them',
        )
        parser.add_argument(
            '--diff',
            action='store_true',
            help='Show differences between declared and actual permissions',
        )
        parser.add_argument(
            '--status',
            action='store_true',
            help='Show current permission status for all groups',
        )
        parser.add_argument(
            '--group',
            type=str,
            help='Only process a specific group',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force permission application even if no changes detected',
        )

    def handle(self, *args, **options):
        service = PermissionService(source='management_command')

        if options['diff']:
            self._show_diff(service, options.get('group'))
            return

        if options['status']:
            self._show_status(service, options.get('group'))
            return

        # Apply permissions
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be applied\n'))

        # Ensure groups exist
        created_groups = service.ensure_groups_exist()
        if created_groups:
            self.stdout.write(
                self.style.SUCCESS(f"Created groups: {', '.join(created_groups)}")
            )

        # Apply permissions
        results = service.apply_permissions(dry_run=dry_run)

        # Report results
        self._report_results(results, dry_run)

    def _show_diff(self, service: PermissionService, group_name: str = None):
        """Show permission differences."""
        diffs = service.diff(group_name)

        if not diffs:
            self.stdout.write(self.style.SUCCESS('All permissions are in sync'))
            return

        for name, diff in diffs.items():
            self.stdout.write(f"\n{self.style.WARNING(name)}:")
            self.stdout.write(f"  Declared: {diff['declared_count']}, Actual: {diff['actual_count']}")

            if diff['to_add']:
                self.stdout.write(self.style.SUCCESS('  To add:'))
                for perm in diff['to_add']:
                    self.stdout.write(f"    + {perm}")

            if diff['to_remove']:
                self.stdout.write(self.style.ERROR('  To remove:'))
                for perm in diff['to_remove']:
                    self.stdout.write(f"    - {perm}")

    def _show_status(self, service: PermissionService, group_name: str = None):
        """Show current permission status."""
        groups = [group_name] if group_name else get_group_names()

        for name in groups:
            status = service.get_group_status(name)

            if 'error' in status:
                self.stdout.write(self.style.ERROR(f"{name}: {status['error']}"))
                continue

            sync_status = self.style.SUCCESS('IN SYNC') if status['in_sync'] else self.style.WARNING('OUT OF SYNC')

            self.stdout.write(f"\n{self.style.HTTP_INFO(name)} [{sync_status}]")
            self.stdout.write(f"  Description: {status['description']}")
            self.stdout.write(f"  Declared: {len(status['declared_permissions'])} permissions")
            self.stdout.write(f"  Actual: {len(status['actual_permissions'])} permissions")

            if status['missing']:
                self.stdout.write(self.style.WARNING(f"  Missing: {len(status['missing'])}"))

            if status['extra']:
                self.stdout.write(self.style.WARNING(f"  Extra: {len(status['extra'])}"))

    def _report_results(self, results: dict, dry_run: bool):
        """Report the results of permission application."""
        action_word = 'would be' if dry_run else 'were'

        self.stdout.write('')
        self.stdout.write(f"Groups processed: {results['groups_processed']}")
        self.stdout.write(f"Permissions {action_word} added: {results['permissions_added']}")
        self.stdout.write(f"Permissions {action_word} removed: {results['permissions_removed']}")

        if results['errors']:
            self.stdout.write(self.style.ERROR(f"\nErrors ({len(results['errors'])}):"))
            for error in results['errors']:
                self.stdout.write(f"  - {error}")

        if results['changes']:
            self.stdout.write(f"\nChanges ({len(results['changes'])}):")
            for change in results['changes'][:20]:  # Limit output
                action = change['action']
                if 'add' in action:
                    style = self.style.SUCCESS
                    symbol = '+'
                else:
                    style = self.style.ERROR
                    symbol = '-'
                self.stdout.write(style(f"  {symbol} {change['group']}: {change['permission']}"))

            if len(results['changes']) > 20:
                self.stdout.write(f"  ... and {len(results['changes']) - 20} more")

        if not dry_run and not results['errors']:
            self.stdout.write(self.style.SUCCESS('\nPermissions applied successfully'))
        elif dry_run:
            self.stdout.write(self.style.WARNING('\nRun without --dry-run to apply changes'))
