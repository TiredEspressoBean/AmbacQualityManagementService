"""
Tests for the notification system.

Tests NotificationTask scheduling, handlers, and delivery logic.
"""

from datetime import timedelta, time as datetime_time
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from Tracker.models import NotificationTask
from Tracker.notifications import get_notification_handler

User = get_user_model()


class NotificationTaskTestCase(TestCase):
    """Test NotificationTask model and scheduling logic"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='test_notification_user',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
        )

    def test_create_weekly_report_notification(self):
        """Test creating a weekly report notification"""
        notification = NotificationTask.objects.create(
            notification_type='WEEKLY_REPORT',
            recipient=self.user,
            channel_type='email',
            interval_type='fixed',
            day_of_week=4,  # Friday
            time=datetime_time(15, 0),  # 3 PM UTC
            interval_weeks=1,
            status='pending',
            next_send_at=timezone.now() + timedelta(days=1),
            max_attempts=None  # Infinite
        )

        self.assertEqual(notification.notification_type, 'WEEKLY_REPORT')
        self.assertEqual(notification.recipient, self.user)
        self.assertEqual(notification.status, 'pending')

    def test_calculate_next_send(self):
        """Test calculate_next_send method"""
        notification = NotificationTask.objects.create(
            notification_type='WEEKLY_REPORT',
            recipient=self.user,
            channel_type='email',
            interval_type='fixed',
            day_of_week=4,  # Friday
            time=datetime_time(15, 0),
            interval_weeks=1,
            status='pending',
            next_send_at=timezone.now(),
        )

        next_send = notification.calculate_next_send()
        self.assertIsNotNone(next_send)
        # Should be in the future
        self.assertGreater(next_send, timezone.now() - timedelta(minutes=1))

    def test_should_send_future(self):
        """Test should_send returns False when next_send_at is in future"""
        notification = NotificationTask.objects.create(
            notification_type='WEEKLY_REPORT',
            recipient=self.user,
            channel_type='email',
            interval_type='fixed',
            day_of_week=4,
            time=datetime_time(15, 0),
            interval_weeks=1,
            status='pending',
            next_send_at=timezone.now() + timedelta(days=1),
        )

        self.assertFalse(notification.should_send())

    def test_should_send_past(self):
        """Test should_send returns True when next_send_at is in past"""
        notification = NotificationTask.objects.create(
            notification_type='WEEKLY_REPORT',
            recipient=self.user,
            channel_type='email',
            interval_type='fixed',
            day_of_week=4,
            time=datetime_time(15, 0),
            interval_weeks=1,
            status='pending',
            next_send_at=timezone.now() - timedelta(minutes=1),
        )

        self.assertTrue(notification.should_send())

    def test_mark_sent_success(self):
        """Test mark_sent updates notification correctly"""
        notification = NotificationTask.objects.create(
            notification_type='WEEKLY_REPORT',
            recipient=self.user,
            channel_type='email',
            interval_type='fixed',
            day_of_week=4,
            time=datetime_time(15, 0),
            interval_weeks=1,
            status='pending',
            next_send_at=timezone.now() - timedelta(minutes=1),
        )

        initial_attempt_count = notification.attempt_count
        notification.mark_sent(success=True)

        self.assertEqual(notification.attempt_count, initial_attempt_count + 1)
        self.assertIsNotNone(notification.last_sent_at)
        # For recurring notifications, status should remain pending
        self.assertEqual(notification.status, 'pending')


class DeadlineNotificationTestCase(TestCase):
    """Test deadline-based notification scheduling (e.g., CAPA reminders)"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='test_capa_user',
            email='capa@example.com',
            password='testpass123',
        )

    def test_create_capa_reminder(self):
        """Test creating a CAPA reminder with escalation tiers"""
        notification = NotificationTask.objects.create(
            notification_type='CAPA_REMINDER',
            recipient=self.user,
            channel_type='email',
            interval_type='deadline_based',
            deadline=timezone.now() + timedelta(days=20),
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

        self.assertEqual(notification.notification_type, 'CAPA_REMINDER')
        self.assertEqual(notification.interval_type, 'deadline_based')
        self.assertIsNotNone(notification.deadline)

    def test_escalation_tier_matching(self):
        """Test that correct escalation tier is matched based on days to deadline"""
        notification = NotificationTask.objects.create(
            notification_type='CAPA_REMINDER',
            recipient=self.user,
            channel_type='email',
            interval_type='deadline_based',
            deadline=timezone.now() + timedelta(days=20),
            escalation_tiers=[
                [28, 28],   # > 28 days: monthly
                [14, 7],    # 15-28 days: weekly
                [0, 3.5],   # 1-14 days: twice weekly
                [-999, 1]   # overdue: daily
            ],
            status='pending',
            next_send_at=timezone.now(),
        )

        # 20 days out should match tier 2 (14-28 days = weekly)
        current_interval = notification._get_current_interval()
        self.assertEqual(current_interval, 7)


class NotificationHandlerTestCase(TestCase):
    """Test notification handler loading and validation"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='test_handler_user',
            email='handler@example.com',
            password='testpass123',
        )

    def test_load_weekly_report_handler(self):
        """Test that WEEKLY_REPORT handler can be loaded"""
        try:
            handler = get_notification_handler('WEEKLY_REPORT')
            self.assertIsNotNone(handler)
            self.assertTrue(hasattr(handler, 'context_builder'))
            self.assertTrue(hasattr(handler, 'send_validator'))
            self.assertTrue(hasattr(handler, 'senders'))
        except Exception as e:
            self.fail(f"Failed to load WEEKLY_REPORT handler: {e}")

    def test_handler_validation(self):
        """Test handler validation logic"""
        notification = NotificationTask.objects.create(
            notification_type='WEEKLY_REPORT',
            recipient=self.user,
            channel_type='email',
            interval_type='fixed',
            day_of_week=4,
            time=datetime_time(15, 0),
            interval_weeks=1,
            status='pending',
            next_send_at=timezone.now() - timedelta(minutes=1),
        )

        try:
            handler = get_notification_handler('WEEKLY_REPORT')
            # Handler validation should not raise
            result = handler.should_send(notification)
            self.assertIsInstance(result, bool)
        except Exception as e:
            self.fail(f"Handler validation failed: {e}")


class NotificationQueryTestCase(TestCase):
    """Test notification querying"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='test_query_user',
            email='query@example.com',
            password='testpass123',
        )

    def test_query_pending_notifications(self):
        """Test querying pending notifications"""
        # Create some test notifications
        NotificationTask.objects.create(
            notification_type='WEEKLY_REPORT',
            recipient=self.user,
            channel_type='email',
            interval_type='fixed',
            status='pending',
            next_send_at=timezone.now() - timedelta(minutes=5),
        )
        NotificationTask.objects.create(
            notification_type='WEEKLY_REPORT',
            recipient=self.user,
            channel_type='email',
            interval_type='fixed',
            status='pending',
            next_send_at=timezone.now() + timedelta(days=1),
        )

        pending = NotificationTask.objects.filter(status='pending')
        self.assertEqual(pending.count(), 2)

        ready_now = NotificationTask.objects.filter(
            status='pending',
            next_send_at__lte=timezone.now()
        )
        self.assertEqual(ready_now.count(), 1)
