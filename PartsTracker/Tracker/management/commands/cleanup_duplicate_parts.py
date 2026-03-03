"""
Cleanup duplicate parts created by running the seeder multiple times.

This command finds and removes duplicate parts based on ERP_id,
keeping only the oldest part (first created) for each ERP_id.

Usage:
    python manage.py cleanup_duplicate_parts --dry-run  # Preview changes
    python manage.py cleanup_duplicate_parts            # Execute cleanup
"""

from django.core.management.base import BaseCommand
from django.db.models import Count, Min

from Tracker.models import Parts, QualityReports, StepTransitionLog


class Command(BaseCommand):
    help = "Remove duplicate parts created by running the seeder multiple times"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without actually deleting anything',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))
        else:
            self.stdout.write(self.style.WARNING("LIVE RUN - Duplicate parts will be deleted"))

        # Find duplicate ERP_ids (using count only since UUIDs don't support Min)
        duplicates = (
            Parts.objects
            .values('ERP_id')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
        )

        total_duplicates = 0
        parts_to_delete = []

        for dup in duplicates:
            erp_id = dup['ERP_id']
            count = dup['count']

            # Get all parts with this ERP_id, ordered by created_at
            all_parts = list(Parts.objects.filter(ERP_id=erp_id).order_by('created_at'))

            # Keep the first (oldest) one, mark rest for deletion
            keep_part = all_parts[0]
            duplicate_parts = all_parts[1:]
            duplicate_count = len(duplicate_parts)
            total_duplicates += duplicate_count

            self.stdout.write(f"  {erp_id}: {count} copies (keeping id={keep_part.id}, deleting {duplicate_count})")

            parts_to_delete.extend([p.id for p in duplicate_parts])

        self.stdout.write(f"\nFound {len(duplicates)} duplicate ERP_ids")
        self.stdout.write(f"Total parts to delete: {total_duplicates}")

        if total_duplicates == 0:
            self.stdout.write(self.style.SUCCESS("No duplicates found - database is clean!"))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"\nRun without --dry-run to delete {total_duplicates} duplicate parts"
            ))
            return

        # Check for related records
        related_quality_reports = QualityReports.objects.filter(part_id__in=parts_to_delete).count()
        related_transition_logs = StepTransitionLog.objects.filter(part_id__in=parts_to_delete).count()

        if related_quality_reports > 0:
            self.stdout.write(self.style.WARNING(
                f"  {related_quality_reports} quality reports will be deleted"
            ))

        if related_transition_logs > 0:
            self.stdout.write(self.style.WARNING(
                f"  {related_transition_logs} step transition logs will be deleted"
            ))

        # Delete duplicates
        self.stdout.write("\nDeleting duplicates...")

        # Delete in chunks to avoid memory issues
        chunk_size = 100
        deleted_count = 0

        for i in range(0, len(parts_to_delete), chunk_size):
            chunk = parts_to_delete[i:i + chunk_size]
            deleted, _ = Parts.objects.filter(id__in=chunk).delete()
            deleted_count += deleted
            self.stdout.write(f"  Deleted {deleted_count}/{total_duplicates} parts...")

        self.stdout.write(self.style.SUCCESS(f"\nSuccessfully deleted {deleted_count} duplicate parts"))
