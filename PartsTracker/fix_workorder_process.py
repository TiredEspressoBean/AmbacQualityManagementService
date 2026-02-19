"""Backfill process field on existing WorkOrders."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PartsTrackerApp.settings')
django.setup()

from Tracker.models import WorkOrder, Processes

updated = 0
skipped = 0

for wo in WorkOrder.objects.filter(process__isnull=True):
    # Get part type from the work order's parts
    first_part = wo.parts.select_related('part_type').first()
    if not first_part or not first_part.part_type:
        skipped += 1
        continue

    part_type = first_part.part_type

    # Find an appropriate process for this part type (prefer approved, current version)
    process = Processes.objects.filter(
        part_type=part_type,
        archived=False
    ).order_by('-status', '-created_at').first()  # APPROVED > DRAFT, newest first

    if process:
        wo.process = process
        wo.save(update_fields=['process'])
        updated += 1
        print(f"Updated {wo.ERP_id} -> {process.name}")
    else:
        skipped += 1
        print(f"Skipped {wo.ERP_id} - no process found for {part_type.name}")

print(f"\nDone. Updated: {updated}, Skipped: {skipped}")
