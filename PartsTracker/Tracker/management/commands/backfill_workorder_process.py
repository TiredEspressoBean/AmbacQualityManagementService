"""
Backfill WorkOrder.process field for existing records.

Sets process based on:
1. Parts attached to the WorkOrder → part_type → approved process
2. Or related_order's parts → part_type → approved process
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from Tracker.models import WorkOrder, Processes


class Command(BaseCommand):
    help = 'Backfill WorkOrder.process for existing records without a process assigned'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Find WorkOrders without a process
        workorders_to_update = WorkOrder.objects.filter(
            process__isnull=True,
            archived=False
        ).select_related('related_order').prefetch_related('parts__part_type')

        total = workorders_to_update.count()
        updated = 0
        skipped = 0

        self.stdout.write(f"Found {total} WorkOrders without process assigned")

        for wo in workorders_to_update:
            # Try to find part_type from WorkOrder's parts first
            part_type = None

            if wo.parts.exists():
                first_part = wo.parts.select_related('part_type').first()
                if first_part and first_part.part_type:
                    part_type = first_part.part_type

            # Fallback: try related_order's parts
            if not part_type and wo.related_order:
                order_part = wo.related_order.parts.select_related('part_type').first()
                if order_part and order_part.part_type:
                    part_type = order_part.part_type

            if not part_type:
                self.stdout.write(
                    self.style.WARNING(f"  WO {wo.id} ({wo.ERP_id}): No part_type found, skipping")
                )
                skipped += 1
                continue

            # Find approved process for this part_type
            process = Processes.objects.filter(
                part_type=part_type,
                status__in=['approved', 'deprecated'],
                archived=False
            ).first()

            if not process:
                self.stdout.write(
                    self.style.WARNING(
                        f"  WO {wo.id} ({wo.ERP_id}): No approved process for part_type '{part_type.name}', skipping"
                    )
                )
                skipped += 1
                continue

            if dry_run:
                self.stdout.write(
                    f"  WO {wo.id} ({wo.ERP_id}): Would set process to '{process.name}' (id={process.id})"
                )
            else:
                wo.process = process
                wo.save(update_fields=['process'])
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  WO {wo.id} ({wo.ERP_id}): Set process to '{process.name}'"
                    )
                )
            updated += 1

        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.NOTICE(f"DRY RUN: Would update {updated}, skip {skipped}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Updated {updated}, skipped {skipped}"))
