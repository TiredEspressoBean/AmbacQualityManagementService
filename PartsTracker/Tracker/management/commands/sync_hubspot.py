from django.core.management.base import BaseCommand
from Tracker.hubspot.sync import sync_all_deals
class Command(BaseCommand):
    help = 'Synchronizes hubspot data'

    def handle(self, *args, **options):
        self.stdout.write('Syncing hubspot data...')
        result = sync_all_deals()
        self.stdout.write(self.style.SUCCESS(f"Successfully synced hubspot data: {result}"))