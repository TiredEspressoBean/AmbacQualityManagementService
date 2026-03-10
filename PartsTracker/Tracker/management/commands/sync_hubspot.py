from django.core.management.base import BaseCommand, CommandError
from Tracker.tasks import sync_hubspot_deals_task


class Command(BaseCommand):
    help = 'Synchronizes HubSpot data for Ambac tenant'

    # Hardcoded for Ambac - this sync will be replaced by n8n in the future
    DEFAULT_TENANT_SLUG = 'ambac-international'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sync',
            action='store_true',
            help='Run sync synchronously (blocking) instead of queueing async task',
        )
        parser.add_argument(
            '--tenant',
            type=str,
            default=self.DEFAULT_TENANT_SLUG,
            help=f'Tenant slug (default: {self.DEFAULT_TENANT_SLUG})',
        )

    def handle(self, *args, **options):
        from Tracker.models import Tenant

        # Resolve tenant
        tenant_slug = options['tenant']
        try:
            tenant = Tenant.objects.get(slug=tenant_slug)
        except Tenant.DoesNotExist:
            raise CommandError(f'Tenant "{tenant_slug}" not found. Create it first with: python manage.py setup_tenant --slug {tenant_slug} --name "Ambac International" --admin-email admin@example.com')

        self.stdout.write(f'Using tenant: {tenant.name} ({tenant.slug})')

        if options['sync']:
            # Run synchronously (blocking)
            self.stdout.write('Running HubSpot sync synchronously...')
            from Tracker.hubspot.sync import sync_all_deals
            result = sync_all_deals(tenant=tenant)

            if result.get('status') == 'success':
                self.stdout.write(self.style.SUCCESS(
                    f"Successfully synced HubSpot data: "
                    f"{result.get('created', 0)} created, "
                    f"{result.get('updated', 0)} updated"
                ))
            else:
                self.stdout.write(self.style.ERROR(f"Sync failed: {result.get('message')}"))
        else:
            # Queue async task (default)
            self.stdout.write('Queuing HubSpot sync task...')
            task = sync_hubspot_deals_task.delay(tenant_id=str(tenant.id))
            self.stdout.write(self.style.SUCCESS(
                f"HubSpot sync task queued with ID: {task.id}\n"
                f"Check Celery logs or Django admin for results."
            ))