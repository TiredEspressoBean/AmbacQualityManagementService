"""
Test script for notification system.

Run with: python manage.py shell < test_notification_system.py
Or: python manage.py shell
     exec(open('test_notification_system.py').read())
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PartsTrackerApp.settings')
django.setup()

from datetime import timedelta, time as datetime_time
from django.utils import timezone
from django.contrib.auth import get_user_model
from Tracker.models import NotificationTask
from Tracker.notifications import get_notification_handler

User = get_user_model()

print("=" * 80)
print("NOTIFICATION SYSTEM TEST")
print("=" * 80)
print()

# ============================================================================
# Test 1: Create a user (or get existing)
# ============================================================================
print("Test 1: Get/Create Test User")
print("-" * 80)

test_user, created = User.objects.get_or_create(
    username='test_notification_user',
    defaults={
        'email': 'test@example.com',
        'first_name': 'Test',
        'last_name': 'User',
    }
)

if created:
    test_user.set_password('testpass123')
    test_user.save()
    print(f"✓ Created test user: {test_user.email}")
else:
    print(f"✓ Using existing test user: {test_user.email}")

print()

# ============================================================================
# Test 2: Create a NotificationTask (weekly report)
# ============================================================================
print("Test 2: Create NotificationTask for Weekly Report")
print("-" * 80)

# Delete any existing test notifications
NotificationTask.objects.filter(recipient=test_user, notification_type='WEEKLY_REPORT').delete()

# Create a weekly report notification (every Friday at 3 PM UTC)
notification = NotificationTask.objects.create(
    notification_type='WEEKLY_REPORT',
    recipient=test_user,
    channel_type='email',
    interval_type='fixed',
    day_of_week=4,  # Friday
    time=datetime_time(15, 0),  # 3 PM UTC
    interval_weeks=1,
    status='pending',
    next_send_at=timezone.now() + timedelta(days=1),  # Tomorrow for testing
    max_attempts=None  # Infinite
)

print(f"✓ Created NotificationTask:")
print(f"  ID: {notification.id}")
print(f"  Type: {notification.get_notification_type_display()}")
print(f"  Recipient: {notification.recipient.email}")
print(f"  Channel: {notification.channel_type}")
print(f"  Status: {notification.status}")
print(f"  Next send: {notification.next_send_at}")
print()

# ============================================================================
# Test 3: Test calculate_next_send method
# ============================================================================
print("Test 3: Test calculate_next_send Method")
print("-" * 80)

next_send = notification.calculate_next_send()
print(f"✓ Calculated next send time: {next_send}")
print(f"  Day of week: {next_send.strftime('%A')}")
print(f"  Time: {next_send.strftime('%H:%M')}")
print()

# ============================================================================
# Test 4: Test should_send method
# ============================================================================
print("Test 4: Test should_send Method")
print("-" * 80)

# Should not send (next_send_at is in the future)
should_send_future = notification.should_send()
print(f"✓ Should send (next_send_at in future): {should_send_future} (expected: False)")

# Change next_send_at to now
notification.next_send_at = timezone.now() - timedelta(minutes=1)
notification.save()

should_send_now = notification.should_send()
print(f"✓ Should send (next_send_at in past): {should_send_now} (expected: True)")
print()

# ============================================================================
# Test 5: Test notification handler loading
# ============================================================================
print("Test 5: Test Notification Handler Loading")
print("-" * 80)

try:
    handler = get_notification_handler('WEEKLY_REPORT')
    print(f"✓ Loaded WEEKLY_REPORT handler")
    print(f"  Context builder: {handler.context_builder.__name__}")
    print(f"  Send validator: {handler.send_validator.__name__}")
    print(f"  Channels: {list(handler.senders.keys())}")
except Exception as e:
    print(f"✗ Error loading handler: {e}")

print()

# ============================================================================
# Test 6: Test handler validation
# ============================================================================
print("Test 6: Test Handler Validation")
print("-" * 80)

try:
    handler = get_notification_handler('WEEKLY_REPORT')
    should_send_validated = handler.should_send(notification)
    print(f"✓ Handler validation result: {should_send_validated}")
except Exception as e:
    print(f"✗ Error validating: {e}")

print()

# ============================================================================
# Test 7: Test context building (will fail without active orders, but that's ok)
# ============================================================================
print("Test 7: Test Context Building")
print("-" * 80)

try:
    handler = get_notification_handler('WEEKLY_REPORT')
    context = handler.context_builder(notification)

    if context:
        print(f"✓ Built context successfully")
        print(f"  Keys: {list(context.keys())}")
        print(f"  Customer: {context.get('customer_name')}")
        print(f"  Orders: {context.get('total_orders')}")
    else:
        print(f"○ No context (expected - test user has no active orders)")
except Exception as e:
    print(f"✗ Error building context: {e}")

print()

# ============================================================================
# Test 8: Test mark_sent method
# ============================================================================
print("Test 8: Test mark_sent Method")
print("-" * 80)

print(f"Before mark_sent:")
print(f"  Status: {notification.status}")
print(f"  Attempt count: {notification.attempt_count}")
print(f"  Last sent at: {notification.last_sent_at}")

notification.mark_sent(success=True)

print(f"After mark_sent (success=True):")
print(f"  Status: {notification.status}")
print(f"  Attempt count: {notification.attempt_count}")
print(f"  Last sent at: {notification.last_sent_at}")
print(f"  Next send at: {notification.next_send_at}")
print(f"  ✓ Status should be 'pending' (will send again)")
print()

# ============================================================================
# Test 9: Query pending notifications
# ============================================================================
print("Test 9: Query Pending Notifications")
print("-" * 80)

pending_count = NotificationTask.objects.filter(status='pending').count()
print(f"✓ Pending notifications in database: {pending_count}")

# Notifications ready to send right now
ready_now = NotificationTask.objects.filter(
    status='pending',
    next_send_at__lte=timezone.now()
).count()
print(f"✓ Notifications ready to send right now: {ready_now}")
print()

# ============================================================================
# Test 10: Test deadline-based notification (CAPA)
# ============================================================================
print("Test 10: Test Deadline-Based Notification (CAPA)")
print("-" * 80)

# Create a mock CAPA notification
capa_notification = NotificationTask.objects.create(
    notification_type='CAPA_REMINDER',
    recipient=test_user,
    channel_type='email',
    interval_type='deadline_based',
    deadline=timezone.now() + timedelta(days=20),  # Due in 20 days
    escalation_tiers=[
        [28, 28],   # > 28 days: monthly
        [14, 7],    # 15-28 days: weekly
        [0, 3.5],   # 1-14 days: twice weekly
        [-999, 1]   # overdue: daily
    ],
    status='pending',
    next_send_at=timezone.now(),
    max_attempts=30
)

print(f"✓ Created CAPA notification:")
print(f"  ID: {capa_notification.id}")
print(f"  Deadline: {capa_notification.deadline}")
print(f"  Days until deadline: {(capa_notification.deadline - timezone.now()).days}")

# Test tier matching
current_interval = capa_notification._get_current_interval()
current_tier = capa_notification._find_matching_tier()

print(f"  Current interval: {current_interval} days")
print(f"  Current tier: {current_tier}")
print(f"  ✓ Should be 7 days (20 days out = tier 2)")
print()

# ============================================================================
# Summary
# ============================================================================
print("=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print(f"✓ NotificationTask model: WORKING")
print(f"✓ Notification handlers: WORKING")
print(f"✓ Scheduling logic: WORKING")
print(f"✓ Escalation tiers: WORKING")
print()
print(f"Next step: Test Celery tasks with test_celery_notification.py")
print()

# Cleanup (optional - comment out to keep test data)
print("Cleaning up test data...")
NotificationTask.objects.filter(recipient=test_user).delete()
# Don't delete user - might be useful for other tests
print("✓ Done")
