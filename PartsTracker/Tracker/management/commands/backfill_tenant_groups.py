"""
Management command to backfill default groups for existing tenants.

Run after migrating to ensure all tenants have default groups:
    python manage.py backfill_tenant_groups

This is idempotent - running multiple times is safe.
"""

from django.core.management.base import BaseCommand

from Tracker.groups import GroupSeeder


class Command(BaseCommand):
    help = 'Backfill default groups for all existing tenants'

    def handle(self, *args, **options):
        results = GroupSeeder.backfill_all_tenants()

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {results['tenants']} tenants, "
                f"created {results['groups_created']} new groups"
            )
        )

        if results['groups_created'] == 0:
            self.stdout.write(
                self.style.NOTICE(
                    "No new groups created - all tenants already have default groups."
                )
            )
