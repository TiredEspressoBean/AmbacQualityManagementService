"""
Backfill starter notification rules onto existing tenants.

New tenants get their starter rules seeded via the Tenant post_save signal.
Existing tenants created before the seeder shipped — and any tenant whose
admin nuked the starter rules — get them via this command.

    python manage.py setup_notification_rules                 # all tenants
    python manage.py setup_notification_rules --tenant=<id>   # one tenant

Idempotent: re-running on a tenant that already has the starter rules
leaves them alone (matched by name).
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from Tracker.models import Tenant
from Tracker.services.core.notifications.system_rules import (
    seed_system_rules_for_tenant,
)
from Tracker.utils.tenant_context import tenant_context


class Command(BaseCommand):
    help = "Seed the starter NotificationRule set onto tenants."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant",
            dest="tenant_id",
            help="Limit to one tenant (UUID). Default: all tenants.",
        )

    def handle(self, *args, **options):
        tenant_id = options.get("tenant_id")
        qs = Tenant.objects.all()
        if tenant_id:
            qs = qs.filter(id=tenant_id)

        total_created = 0
        total_skipped = 0
        total_errors = 0
        tenants_touched = 0

        for tenant in qs:
            with tenant_context(tenant.id):
                counts = seed_system_rules_for_tenant(tenant)
            tenants_touched += 1
            total_created += counts["created"]
            total_skipped += counts["skipped"]
            total_errors += counts["errors"]
            self.stdout.write(
                f"  {tenant.slug or tenant.id}: created={counts['created']} "
                f"skipped={counts['skipped']} errors={counts['errors']}"
            )

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. {tenants_touched} tenant(s) processed. "
            f"Total: created={total_created} skipped={total_skipped} "
            f"errors={total_errors}"
        ))
