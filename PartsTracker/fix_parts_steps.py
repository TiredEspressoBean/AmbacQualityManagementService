"""Fix parts to use steps from their work order's process."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PartsTrackerApp.settings')
django.setup()

from Tracker.models import Parts, ProcessStep

updated = 0
skipped = 0

# Get all parts with a work order that has a process
parts = Parts.objects.select_related('step', 'work_order__process').filter(
    work_order__isnull=False,
    work_order__process__isnull=False
)

for part in parts:
    process = part.work_order.process
    current_step = part.step

    if not current_step:
        skipped += 1
        continue

    # Check if current step is in the process
    ps = ProcessStep.objects.filter(process=process, step=current_step).first()
    if ps:
        # Step is already correct
        skipped += 1
        continue

    # Find the equivalent step in the correct process by order position
    # Get the order of the current step in its original process
    original_ps = ProcessStep.objects.filter(step=current_step).first()
    if not original_ps:
        skipped += 1
        continue

    original_order = original_ps.order

    # Find step at same order position in the correct process
    correct_ps = ProcessStep.objects.filter(
        process=process,
        order=original_order
    ).select_related('step').first()

    if not correct_ps:
        # Fallback: use entry point (first step)
        correct_ps = ProcessStep.objects.filter(
            process=process,
            is_entry_point=True
        ).select_related('step').first()

        if not correct_ps:
            correct_ps = ProcessStep.objects.filter(
                process=process
            ).select_related('step').order_by('order').first()

    if correct_ps:
        old_step = current_step.name
        part.step = correct_ps.step
        part.save(update_fields=['step'])
        updated += 1
        if updated <= 20:  # Only print first 20
            print(f"Fixed {part.ERP_id}: {old_step} -> {correct_ps.step.name}")
    else:
        skipped += 1

print(f"\nDone. Updated: {updated}, Skipped: {skipped}")
