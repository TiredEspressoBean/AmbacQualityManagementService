"""Advance parts through their workflows to create realistic progression."""
import os
import random
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PartsTrackerApp.settings')
django.setup()

from Tracker.models import (
    Orders, WorkOrder, Parts, ProcessStep, PartsStatus,
    OrdersStatus, WorkOrderStatus
)

def get_target_step_index(steps_count, order_status):
    """Get target step index based on order status."""
    if order_status == OrdersStatus.COMPLETED:
        return steps_count - 1
    elif order_status == OrdersStatus.IN_PROGRESS:
        return random.randint(steps_count // 3, steps_count - 2)
    elif order_status == OrdersStatus.PENDING:
        return random.randint(0, max(0, steps_count // 3))
    elif order_status == OrdersStatus.RFI:
        return random.randint(1, steps_count // 2)
    elif order_status == OrdersStatus.ON_HOLD:
        return random.randint(steps_count // 4, steps_count * 3 // 4)
    else:
        return 0

advanced_count = 0
orders_processed = 0

for order in Orders.objects.all():
    wo = order.related_orders.filter(process__isnull=False).first()
    if not wo or not wo.process:
        continue

    process = wo.process
    process_steps = list(
        ProcessStep.objects.filter(process=process)
        .select_related('step')
        .order_by('order')
    )

    if not process_steps:
        continue

    steps = [ps.step for ps in process_steps]
    target_idx = get_target_step_index(len(steps), order.order_status)

    # Get parts for this order that are at step 1
    parts = Parts.objects.filter(
        order=order,
        step=steps[0],
        part_status__in=[PartsStatus.PENDING, PartsStatus.IN_PROGRESS, PartsStatus.READY_FOR_NEXT_STEP]
    )

    if not parts.exists():
        continue

    orders_processed += 1

    # Move a portion of parts to different steps to create variety
    parts_list = list(parts)
    random.shuffle(parts_list)

    # Distribute parts across steps up to target
    for i, part in enumerate(parts_list):
        # Vary the step each part is at
        part_target = min(target_idx + random.randint(-1, 1), len(steps) - 1)
        part_target = max(0, part_target)

        if part_target > 0:
            new_step = steps[part_target]
            part.step = new_step

            # Set appropriate status
            if part_target == len(steps) - 1:
                part.part_status = PartsStatus.COMPLETED
            else:
                part.part_status = PartsStatus.IN_PROGRESS

            part.save(update_fields=['step', 'part_status'])
            advanced_count += 1

print(f"Processed {orders_processed} orders, advanced {advanced_count} parts")
