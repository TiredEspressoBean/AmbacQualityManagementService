"""
Reseed ONLY the demo tenant's training data (types, requirements, records).

A non-destructive alternative to a full `reset_demo` — repopulates the
deterministic demo training set via `DemoTrainingRecordsSeeder`
(idempotent `update_or_create`). Use this when the demo training data was
cleared (e.g. a partial reset) but the rest of the demo tenant is intact.

Usage:
    python manage.py seed_demo_training
    python manage.py seed_demo_training --slug demo
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from Tracker.utils.tenant_context import tenant_context


class Command(BaseCommand):
    help = "Reseed the demo tenant's training data (types, requirements, records)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--slug',
            type=str,
            help='Demo tenant slug (default: from DEMO_TENANT_SLUG setting, else "demo")',
        )

    def handle(self, *args, **options):
        from Tracker.models import Tenant, User
        from Tracker.management.commands.seed.demo.training_records import DemoTrainingRecordsSeeder

        slug = options['slug'] or getattr(settings, 'DEMO_TENANT_SLUG', 'demo')
        try:
            tenant = Tenant.objects.get(slug=slug)
        except Tenant.DoesNotExist:
            raise CommandError(
                f'Tenant "{slug}" not found. Pass --slug to target a different tenant.'
            )

        with tenant_context(str(tenant.id)):
            users_by_email = {
                u.email: u
                for u in User.objects.filter(tenant=tenant)
                if u.email
            }
            seeder = DemoTrainingRecordsSeeder(self.stdout, self.style, tenant)
            result = seeder.seed({'by_email': users_by_email})

        self.stdout.write(self.style.SUCCESS(
            f"Seeded demo training for '{slug}': "
            f"{len(result['training_types'])} types, "
            f"{len(result['training_requirements'])} requirements, "
            f"{len(result['training_records'])} records."
        ))
