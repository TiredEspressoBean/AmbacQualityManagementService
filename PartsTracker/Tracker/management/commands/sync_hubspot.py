from django.core.management.base import BaseCommand
from Tracker.tasks import sync_hubspot_deals_task


class Command(BaseCommand):
    help = 'Synchronizes HubSpot data (queues Celery task by default)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sync',
            action='store_true',
            help='Run sync synchronously (blocking) instead of queueing async task',
        )

    def handle(self, *args, **options):
        if options['sync']:
            # Run synchronously (blocking)
            self.stdout.write('Running HubSpot sync synchronously...')
            from Tracker.hubspot.sync import sync_all_deals
            result = sync_all_deals()

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
            task = sync_hubspot_deals_task.delay()
            self.stdout.write(self.style.SUCCESS(
                f"HubSpot sync task queued with ID: {task.id}\n"
                f"Check Celery logs or Django admin for results."
            ))