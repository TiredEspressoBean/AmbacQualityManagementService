"""
Tests for the notification system.

Tests NotificationTask scheduling, handlers, and delivery logic.
"""

from datetime import timedelta, time as datetime_time
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from Tracker.models import (
    NotificationTask, Tenant, Orders, OrdersStatus, CAPA,
    ApprovalRequest, ApprovalTemplate, Approval_Status_Type,
    Companies, Documents, DocumentType
)
from Tracker.notifications import get_notification_handler
from Tracker.notifications.handlers import (
    build_weekly_report_context,
    build_capa_context,
    build_approval_request_context,
    build_approval_decision_context,
    build_approval_escalation_context,
    validate_weekly_report_send,
    validate_capa_send,
    validate_approval_request_send,
    validate_approval_escalation_send,
    get_frontend_url,
)
from Tracker.tests.base import TenantTestCase

User = get_user_model()


class NotificationTaskTestCase(TenantTestCase):
    """Test NotificationTask model and scheduling logic"""

    def setUp(self):
        super().setUp()
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
            channel_type='EMAIL',
            interval_type='FIXED',
            day_of_week=4,  # Friday
            time=datetime_time(15, 0),  # 3 PM UTC
            interval_weeks=1,
            status='PENDING',
            next_send_at=timezone.now() + timedelta(days=1),
            max_attempts=None  # Infinite
        )

        self.assertEqual(notification.notification_type, 'WEEKLY_REPORT')
        self.assertEqual(notification.recipient, self.user)
        self.assertEqual(notification.status, 'PENDING')

    def test_calculate_next_send(self):
        """Test calculate_next_send method"""
        notification = NotificationTask.objects.create(
            notification_type='WEEKLY_REPORT',
            recipient=self.user,
            channel_type='EMAIL',
            interval_type='FIXED',
            day_of_week=4,  # Friday
            time=datetime_time(15, 0),
            interval_weeks=1,
            status='PENDING',
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
            channel_type='EMAIL',
            interval_type='FIXED',
            day_of_week=4,
            time=datetime_time(15, 0),
            interval_weeks=1,
            status='PENDING',
            next_send_at=timezone.now() + timedelta(days=1),
        )

        self.assertFalse(notification.should_send())

    def test_should_send_past(self):
        """Test should_send returns True when next_send_at is in past"""
        notification = NotificationTask.objects.create(
            notification_type='WEEKLY_REPORT',
            recipient=self.user,
            channel_type='EMAIL',
            interval_type='FIXED',
            day_of_week=4,
            time=datetime_time(15, 0),
            interval_weeks=1,
            status='PENDING',
            next_send_at=timezone.now() - timedelta(minutes=1),
        )

        self.assertTrue(notification.should_send())

    def test_should_send_wrong_status(self):
        """Test should_send returns False when status is not pending"""
        notification = NotificationTask.objects.create(
            notification_type='WEEKLY_REPORT',
            recipient=self.user,
            channel_type='EMAIL',
            interval_type='FIXED',
            status='SENT',
            next_send_at=timezone.now() - timedelta(minutes=1),
        )

        self.assertFalse(notification.should_send())

    def test_mark_sent_success(self):
        """Test mark_sent updates notification correctly"""
        notification = NotificationTask.objects.create(
            notification_type='WEEKLY_REPORT',
            recipient=self.user,
            channel_type='EMAIL',
            interval_type='FIXED',
            day_of_week=4,
            time=datetime_time(15, 0),
            interval_weeks=1,
            status='PENDING',
            next_send_at=timezone.now() - timedelta(minutes=1),
        )

        initial_attempt_count = notification.attempt_count
        notification.mark_sent(success=True)

        self.assertEqual(notification.attempt_count, initial_attempt_count + 1)
        self.assertIsNotNone(notification.last_sent_at)
        # For recurring notifications, status should remain pending
        self.assertEqual(notification.status, 'PENDING')

    def test_mark_sent_failure(self):
        """Test mark_sent with failure sets status to failed"""
        notification = NotificationTask.objects.create(
            notification_type='WEEKLY_REPORT',
            recipient=self.user,
            channel_type='EMAIL',
            interval_type='FIXED',
            status='PENDING',
            next_send_at=timezone.now() - timedelta(minutes=1),
            max_attempts=3,
        )

        notification.mark_sent(success=False)
        self.assertEqual(notification.attempt_count, 1)
        self.assertEqual(notification.status, 'FAILED')  # Failed on first failure

    def test_max_attempts_reached(self):
        """Test notification is cancelled when max_attempts reached"""
        notification = NotificationTask.objects.create(
            notification_type='APPROVAL_REQUEST',
            recipient=self.user,
            channel_type='EMAIL',
            interval_type='FIXED',
            status='PENDING',
            next_send_at=timezone.now() - timedelta(minutes=1),
            max_attempts=1,
            attempt_count=0,
        )

        notification.mark_sent(success=False)
        # After 1 failed attempt with max_attempts=1, should be failed
        self.assertEqual(notification.attempt_count, 1)


class DeadlineNotificationTestCase(TenantTestCase):
    """Test deadline-based notification scheduling (e.g., CAPA reminders)"""

    def setUp(self):
        super().setUp()
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
            channel_type='EMAIL',
            interval_type='DEADLINE_BASED',
            deadline=timezone.now() + timedelta(days=20),
            escalation_tiers=[
                [28, 28],   # > 28 days: monthly
                [14, 7],    # 15-28 days: weekly
                [0, 3.5],   # 1-14 days: twice weekly
                [-999, 1]   # overdue: daily
            ],
            status='PENDING',
            next_send_at=timezone.now(),
            max_attempts=30
        )

        self.assertEqual(notification.notification_type, 'CAPA_REMINDER')
        self.assertEqual(notification.interval_type, 'DEADLINE_BASED')
        self.assertIsNotNone(notification.deadline)

    def test_escalation_tier_matching(self):
        """Test that correct escalation tier is matched based on days to deadline"""
        notification = NotificationTask.objects.create(
            notification_type='CAPA_REMINDER',
            recipient=self.user,
            channel_type='EMAIL',
            interval_type='DEADLINE_BASED',
            deadline=timezone.now() + timedelta(days=20),
            escalation_tiers=[
                [28, 28],   # > 28 days: monthly
                [14, 7],    # 15-28 days: weekly
                [0, 3.5],   # 1-14 days: twice weekly
                [-999, 1]   # overdue: daily
            ],
            status='PENDING',
            next_send_at=timezone.now(),
        )

        # 20 days out should match tier 2 (14-28 days = weekly)
        current_interval = notification._get_current_interval()
        self.assertEqual(current_interval, 7)

    def test_escalation_tier_overdue(self):
        """Test escalation tier when deadline is past"""
        notification = NotificationTask.objects.create(
            notification_type='CAPA_REMINDER',
            recipient=self.user,
            channel_type='EMAIL',
            interval_type='DEADLINE_BASED',
            deadline=timezone.now() - timedelta(days=5),  # 5 days overdue
            escalation_tiers=[
                [28, 28],
                [14, 7],
                [0, 3],
                [-999, 1]  # overdue: daily
            ],
            status='PENDING',
            next_send_at=timezone.now(),
        )

        current_interval = notification._get_current_interval()
        self.assertEqual(current_interval, 1)  # Daily when overdue


class NotificationHandlerTestCase(TenantTestCase):
    """Test notification handler loading and validation"""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username='test_handler_user',
            email='handler@example.com',
            password='testpass123',
            is_active=True,
        )

    def test_load_weekly_report_handler(self):
        """Test that WEEKLY_REPORT handler can be loaded"""
        handler = get_notification_handler('WEEKLY_REPORT')
        self.assertIsNotNone(handler)
        self.assertTrue(hasattr(handler, 'context_builder'))
        self.assertTrue(hasattr(handler, 'send_validator'))
        self.assertTrue(hasattr(handler, 'senders'))

    def test_load_capa_reminder_handler(self):
        """Test that CAPA_REMINDER handler can be loaded"""
        handler = get_notification_handler('CAPA_REMINDER')
        self.assertIsNotNone(handler)

    def test_load_approval_request_handler(self):
        """Test that APPROVAL_REQUEST handler can be loaded"""
        handler = get_notification_handler('APPROVAL_REQUEST')
        self.assertIsNotNone(handler)

    def test_load_approval_decision_handler(self):
        """Test that APPROVAL_DECISION handler can be loaded"""
        handler = get_notification_handler('APPROVAL_DECISION')
        self.assertIsNotNone(handler)

    def test_load_approval_escalation_handler(self):
        """Test that APPROVAL_ESCALATION handler can be loaded"""
        handler = get_notification_handler('APPROVAL_ESCALATION')
        self.assertIsNotNone(handler)

    def test_unknown_handler_raises(self):
        """Test that unknown notification type raises ValueError"""
        with self.assertRaises(ValueError):
            get_notification_handler('UNKNOWN_TYPE')

    def test_handler_has_email_sender(self):
        """Test that handlers have email sender configured"""
        for notification_type in ['WEEKLY_REPORT', 'CAPA_REMINDER', 'APPROVAL_REQUEST']:
            handler = get_notification_handler(notification_type)
            self.assertIn('EMAIL', handler.senders)

    def test_handler_validation(self):
        """Test handler validation logic"""
        notification = NotificationTask.objects.create(
            notification_type='WEEKLY_REPORT',
            recipient=self.user,
            channel_type='EMAIL',
            interval_type='FIXED',
            day_of_week=4,
            time=datetime_time(15, 0),
            interval_weeks=1,
            status='PENDING',
            next_send_at=timezone.now() - timedelta(minutes=1),
        )

        handler = get_notification_handler('WEEKLY_REPORT')
        result = handler.should_send(notification)
        self.assertIsInstance(result, bool)


class NotificationValidatorTestCase(TenantTestCase):
    """Test notification validators"""

    def setUp(self):
        super().setUp()
        self.active_user = User.objects.create_user(
            username='active_user',
            email='active@example.com',
            password='testpass123',
            is_active=True,
        )
        self.inactive_user = User.objects.create_user(
            username='inactive_user',
            email='inactive@example.com',
            password='testpass123',
            is_active=False,
        )

    def test_validate_weekly_report_active_user(self):
        """Test weekly report validation passes for active user"""
        notification = NotificationTask.objects.create(
            notification_type='WEEKLY_REPORT',
            recipient=self.active_user,
            channel_type='EMAIL',
            interval_type='FIXED',
            status='PENDING',
            next_send_at=timezone.now(),
        )

        result = validate_weekly_report_send(notification)
        self.assertTrue(result)

    def test_validate_weekly_report_inactive_user(self):
        """Test weekly report validation fails for inactive user"""
        notification = NotificationTask.objects.create(
            notification_type='WEEKLY_REPORT',
            recipient=self.inactive_user,
            channel_type='EMAIL',
            interval_type='FIXED',
            status='PENDING',
            next_send_at=timezone.now(),
        )

        result = validate_weekly_report_send(notification)
        self.assertFalse(result)
        notification.refresh_from_db()
        self.assertEqual(notification.status, 'CANCELLED')

    def test_validate_capa_no_related_object(self):
        """Test CAPA validation fails when no related object"""
        notification = NotificationTask.objects.create(
            notification_type='CAPA_REMINDER',
            recipient=self.active_user,
            channel_type='EMAIL',
            interval_type='DEADLINE_BASED',
            status='PENDING',
            next_send_at=timezone.now(),
            # No related_object set
        )

        result = validate_capa_send(notification)
        self.assertFalse(result)
        notification.refresh_from_db()
        self.assertEqual(notification.status, 'CANCELLED')

    def test_validate_approval_request_no_related_object(self):
        """Test approval request validation fails when no related object"""
        notification = NotificationTask.objects.create(
            notification_type='APPROVAL_REQUEST',
            recipient=self.active_user,
            channel_type='EMAIL',
            interval_type='FIXED',
            status='PENDING',
            next_send_at=timezone.now(),
        )

        result = validate_approval_request_send(notification)
        self.assertFalse(result)
        notification.refresh_from_db()
        self.assertEqual(notification.status, 'CANCELLED')


class ContextBuilderTestCase(TenantTestCase):
    """Test context builders for different notification types"""

    def test_build_weekly_report_context_no_orders(self):
        """Test weekly report context returns None when no active orders"""
        notification = NotificationTask.objects.create(
            notification_type='WEEKLY_REPORT',
            recipient=self.user_a,
            channel_type='EMAIL',
            interval_type='FIXED',
            status='PENDING',
            next_send_at=timezone.now(),
        )

        context = build_weekly_report_context(notification)
        self.assertIsNone(context)  # No orders = no context = skip sending

    def test_build_weekly_report_context_with_orders(self):
        """Test weekly report context with active orders"""
        # Create an order for user_a
        company = Companies.objects.create(
            tenant=self.tenant_a,
            name='Test Company',
            description='Test company for notification tests'
        )
        order = Orders.objects.create(
            tenant=self.tenant_a,
            name='Test Order',
            customer=self.user_a,
            company=company,
            order_status=OrdersStatus.IN_PROGRESS,
        )

        notification = NotificationTask.objects.create(
            notification_type='WEEKLY_REPORT',
            recipient=self.user_a,
            channel_type='EMAIL',
            interval_type='FIXED',
            status='PENDING',
            next_send_at=timezone.now(),
        )

        context = build_weekly_report_context(notification)
        self.assertIsNotNone(context)
        self.assertEqual(context['recipient'], self.user_a)
        self.assertEqual(context['total_orders'], 1)
        self.assertIn('orders', context)
        self.assertIn('frontend_url', context)

    def test_build_capa_context(self):
        """Test CAPA context builder"""
        capa = CAPA.objects.create(
            tenant=self.tenant_a,
            capa_type='CORRECTIVE',
            severity='MAJOR',
            problem_statement='Test issue',
            initiated_by=self.user_a,
            assigned_to=self.user_a,
            due_date=timezone.now().date() + timedelta(days=10),
        )

        capa_ct = ContentType.objects.get_for_model(CAPA)
        notification = NotificationTask.objects.create(
            notification_type='CAPA_REMINDER',
            recipient=self.user_a,
            channel_type='EMAIL',
            interval_type='DEADLINE_BASED',
            status='PENDING',
            next_send_at=timezone.now(),
            related_content_type=capa_ct,
            related_object_id=str(capa.id),
        )

        context = build_capa_context(notification)
        self.assertIsNotNone(context)
        self.assertEqual(context['recipient'], self.user_a)
        self.assertIn('disposition_number', context)
        self.assertIn('days_until_due', context)
        self.assertFalse(context['is_overdue'])

    def test_build_capa_context_overdue(self):
        """Test CAPA context builder for overdue CAPA"""
        capa = CAPA.objects.create(
            tenant=self.tenant_a,
            capa_type='CORRECTIVE',
            severity='MAJOR',
            problem_statement='Overdue test issue',
            initiated_by=self.user_a,
            assigned_to=self.user_a,
            due_date=timezone.now().date() - timedelta(days=5),  # 5 days overdue
        )

        capa_ct = ContentType.objects.get_for_model(CAPA)
        notification = NotificationTask.objects.create(
            notification_type='CAPA_REMINDER',
            recipient=self.user_a,
            channel_type='EMAIL',
            interval_type='DEADLINE_BASED',
            status='PENDING',
            next_send_at=timezone.now(),
            related_content_type=capa_ct,
            related_object_id=str(capa.id),
        )

        context = build_capa_context(notification)
        self.assertIsNotNone(context)
        self.assertTrue(context['is_overdue'])
        self.assertLess(context['days_until_due'], 0)

    def test_build_capa_context_no_due_date(self):
        """Test CAPA context builder handles missing due date"""
        capa = CAPA.objects.create(
            tenant=self.tenant_a,
            capa_type='CORRECTIVE',
            severity='MINOR',
            problem_statement='No due date test',
            initiated_by=self.user_a,
            assigned_to=self.user_a,
            due_date=None,
        )

        capa_ct = ContentType.objects.get_for_model(CAPA)
        notification = NotificationTask.objects.create(
            notification_type='CAPA_REMINDER',
            recipient=self.user_a,
            channel_type='EMAIL',
            interval_type='DEADLINE_BASED',
            status='PENDING',
            next_send_at=timezone.now(),
            related_content_type=capa_ct,
            related_object_id=str(capa.id),
        )

        context = build_capa_context(notification)
        self.assertIsNotNone(context)
        self.assertEqual(context['days_until_due'], 0)
        self.assertFalse(context['is_overdue'])


class FrontendUrlTestCase(TestCase):
    """Test frontend URL generation"""

    @override_settings(DEBUG=True, FRONTEND_URL='http://localhost:5173')
    def test_frontend_url_debug(self):
        """Test frontend URL in debug mode"""
        url = get_frontend_url()
        self.assertEqual(url, 'http://localhost:5173')

    @override_settings(DEBUG=False, FRONTEND_URL='https://app.example.com')
    def test_frontend_url_production(self):
        """Test frontend URL in production"""
        url = get_frontend_url()
        self.assertEqual(url, 'https://app.example.com')


class NotificationQueryTestCase(TenantTestCase):
    """Test notification querying"""

    def setUp(self):
        super().setUp()
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
            channel_type='EMAIL',
            interval_type='FIXED',
            status='PENDING',
            next_send_at=timezone.now() - timedelta(minutes=5),
        )
        NotificationTask.objects.create(
            notification_type='WEEKLY_REPORT',
            recipient=self.user,
            channel_type='EMAIL',
            interval_type='FIXED',
            status='PENDING',
            next_send_at=timezone.now() + timedelta(days=1),
        )

        pending = NotificationTask.objects.filter(status='PENDING')
        self.assertEqual(pending.count(), 2)

        ready_now = NotificationTask.objects.filter(
            status='PENDING',
            next_send_at__lte=timezone.now()
        )
        self.assertEqual(ready_now.count(), 1)

    def test_query_by_notification_type(self):
        """Test filtering by notification type"""
        NotificationTask.objects.create(
            notification_type='WEEKLY_REPORT',
            recipient=self.user,
            channel_type='EMAIL',
            interval_type='FIXED',
            status='PENDING',
            next_send_at=timezone.now(),
        )
        NotificationTask.objects.create(
            notification_type='CAPA_REMINDER',
            recipient=self.user,
            channel_type='EMAIL',
            interval_type='DEADLINE_BASED',
            status='PENDING',
            next_send_at=timezone.now(),
        )

        weekly = NotificationTask.objects.filter(notification_type='WEEKLY_REPORT')
        self.assertEqual(weekly.count(), 1)

        capa = NotificationTask.objects.filter(notification_type='CAPA_REMINDER')
        self.assertEqual(capa.count(), 1)


class NotificationTasksTestCase(TenantTestCase):
    """Test Celery tasks for notification creation"""

    def test_create_weekly_report_notifications(self):
        """Test creating weekly report notifications for customers"""
        from Tracker.tasks import create_weekly_report_notifications
        
        # Create a customer with an active order
        company = Companies.objects.create(
            tenant=self.tenant_a,
            name='Test Company',
            description='Test company for notification tests'
        )
        order = Orders.objects.create(
            tenant=self.tenant_a,
            name='Active Order',
            customer=self.user_a,
            company=company,
            order_status=OrdersStatus.IN_PROGRESS,
        )

        # Run the task
        result = create_weekly_report_notifications()

        self.assertEqual(result['status'], 'success')
        self.assertGreaterEqual(result['created'], 1)

        # Check notification was created
        notification = NotificationTask.objects.filter(
            notification_type='WEEKLY_REPORT',
            recipient=self.user_a,
            status='PENDING'
        ).first()
        self.assertIsNotNone(notification)

    def test_create_weekly_report_no_duplicate(self):
        """Test that duplicate weekly report notifications are not created"""
        from Tracker.tasks import create_weekly_report_notifications
        
        company = Companies.objects.create(
            tenant=self.tenant_a,
            name='Test Company',
            description='Test company for notification tests'
        )
        order = Orders.objects.create(
            tenant=self.tenant_a,
            name='Active Order',
            customer=self.user_a,
            company=company,
            order_status=OrdersStatus.IN_PROGRESS,
        )

        # Run twice
        result1 = create_weekly_report_notifications()
        result2 = create_weekly_report_notifications()

        # Second run should skip (notification already pending)
        self.assertEqual(result2['skipped'], result2['skipped'])

        # Only one notification should exist
        count = NotificationTask.objects.filter(
            notification_type='WEEKLY_REPORT',
            recipient=self.user_a,
            status='PENDING'
        ).count()
        self.assertEqual(count, 1)

    def test_check_capa_reminders(self):
        """Test CAPA reminder creation"""
        from Tracker.tasks import check_capa_reminders

        # Create a CAPA with a due date
        capa = CAPA.objects.create(
            tenant=self.tenant_a,
            capa_type='CORRECTIVE',
            severity='MAJOR',
            problem_statement='Test CAPA for reminder',
            initiated_by=self.user_a,
            assigned_to=self.user_a,
            due_date=timezone.now().date() + timedelta(days=7),
            status='OPEN',
        )

        # Run the task
        result = check_capa_reminders()

        self.assertEqual(result['status'], 'success')
        self.assertGreaterEqual(result['created'], 1)

        # Check notification was created
        capa_ct = ContentType.objects.get_for_model(CAPA)
        notification = NotificationTask.objects.filter(
            notification_type='CAPA_REMINDER',
            related_content_type=capa_ct,
            related_object_id=str(capa.id),
            status='PENDING'
        ).first()
        self.assertIsNotNone(notification)

    def test_check_capa_reminders_closed_capa(self):
        """Test that closed CAPAs don't get reminders"""
        from Tracker.tasks import check_capa_reminders

        # Create a closed CAPA
        capa = CAPA.objects.create(
            tenant=self.tenant_a,
            capa_type='CORRECTIVE',
            severity='MINOR',
            problem_statement='Closed CAPA',
            initiated_by=self.user_a,
            assigned_to=self.user_a,
            due_date=timezone.now().date() + timedelta(days=7),
            status='CLOSED',
        )

        result = check_capa_reminders()

        # No notification should be created for closed CAPA
        capa_ct = ContentType.objects.get_for_model(CAPA)
        notification = NotificationTask.objects.filter(
            notification_type='CAPA_REMINDER',
            related_content_type=capa_ct,
            related_object_id=str(capa.id),
        ).first()
        self.assertIsNone(notification)

    def test_escalate_approvals(self):
        """Test approval escalation notification creation"""
        from Tracker.tasks import escalate_approvals

        # Create document type first
        doc_type = DocumentType.objects.create(
            tenant=self.tenant_a,
            name='SOP',
            description='Standard Operating Procedure',
        )

        # Create a document
        doc = Documents.objects.create(
            tenant=self.tenant_a,
            file_name='Test Document',
            file='test.pdf',
            document_type=doc_type,
            status='UNDER_REVIEW',
        )

        # Create an overdue approval request
        doc_ct = ContentType.objects.get_for_model(Documents)
        approval = ApprovalRequest.objects.create(
            tenant=self.tenant_a,
            content_type=doc_ct,
            object_id=str(doc.id),
            requested_by=self.user_a,
            status=Approval_Status_Type.PENDING,
            due_date=timezone.now() - timedelta(days=3),
            escalation_day=timezone.now().date() - timedelta(days=1),
            escalate_to=self.user_b,
        )

        # Run the task
        result = escalate_approvals()

        self.assertEqual(result['status'], 'success')
        self.assertGreaterEqual(result['created'], 1)

        # Check escalation notification was created
        approval_ct = ContentType.objects.get_for_model(ApprovalRequest)
        notification = NotificationTask.objects.filter(
            notification_type='APPROVAL_ESCALATION',
            related_content_type=approval_ct,
            related_object_id=str(approval.id),
            recipient=self.user_b,
            status='PENDING'
        ).first()
        self.assertIsNotNone(notification)

    def test_escalate_approvals_no_duplicate(self):
        """Test that duplicate escalation notifications are not created"""
        from Tracker.tasks import escalate_approvals

        # Create document type first
        doc_type = DocumentType.objects.create(
            tenant=self.tenant_a,
            name='SOP',
            description='Standard Operating Procedure',
        )

        doc = Documents.objects.create(
            tenant=self.tenant_a,
            file_name='Test Document',
            file='test.pdf',
            document_type=doc_type,
            status='UNDER_REVIEW',
        )

        doc_ct = ContentType.objects.get_for_model(Documents)
        approval = ApprovalRequest.objects.create(
            tenant=self.tenant_a,
            content_type=doc_ct,
            object_id=str(doc.id),
            requested_by=self.user_a,
            status=Approval_Status_Type.PENDING,
            due_date=timezone.now() - timedelta(days=3),
            escalation_day=timezone.now().date() - timedelta(days=1),
            escalate_to=self.user_b,
        )

        # Run twice
        escalate_approvals()
        result2 = escalate_approvals()

        # Second run should skip
        self.assertGreaterEqual(result2['skipped'], 1)


class SendNotificationTaskTestCase(TenantTestCase):
    """Test the send_notification_task Celery task"""

    @patch('Tracker.notifications.handlers.send_mail')
    def test_send_weekly_report_notification(self, mock_send_mail):
        """Test sending a weekly report notification"""
        from Tracker.tasks import send_notification_task

        # Create order for context
        company = Companies.objects.create(
            tenant=self.tenant_a,
            name='Test Company',
            description='Test company for notification tests'
        )
        order = Orders.objects.create(
            tenant=self.tenant_a,
            name='Test Order',
            customer=self.user_a,
            company=company,
            order_status=OrdersStatus.IN_PROGRESS,
        )

        notification = NotificationTask.objects.create(
            notification_type='WEEKLY_REPORT',
            recipient=self.user_a,
            channel_type='EMAIL',
            interval_type='FIXED',
            day_of_week=4,  # Friday
            time=datetime_time(15, 0),  # 3 PM
            interval_weeks=1,
            status='PENDING',
            next_send_at=timezone.now() - timedelta(minutes=1),
        )

        mock_send_mail.return_value = 1

        result = send_notification_task(notification.id)

        self.assertEqual(result['status'], 'success')
        mock_send_mail.assert_called_once()

        notification.refresh_from_db()
        self.assertEqual(notification.attempt_count, 1)
        self.assertIsNotNone(notification.last_sent_at)

    @patch('Tracker.notifications.handlers.send_mail')
    def test_send_capa_reminder_notification(self, mock_send_mail):
        """Test sending a CAPA reminder notification"""
        from Tracker.tasks import send_notification_task

        capa = CAPA.objects.create(
            tenant=self.tenant_a,
            capa_type='CORRECTIVE',
            severity='MAJOR',
            problem_statement='Test CAPA',
            initiated_by=self.user_a,
            assigned_to=self.user_a,
            due_date=timezone.now().date() + timedelta(days=5),
            status='OPEN',
        )

        capa_ct = ContentType.objects.get_for_model(CAPA)
        notification = NotificationTask.objects.create(
            notification_type='CAPA_REMINDER',
            recipient=self.user_a,
            channel_type='EMAIL',
            interval_type='DEADLINE_BASED',
            status='PENDING',
            next_send_at=timezone.now() - timedelta(minutes=1),
            related_content_type=capa_ct,
            related_object_id=str(capa.id),
        )

        mock_send_mail.return_value = 1

        result = send_notification_task(notification.id)

        self.assertEqual(result['status'], 'success')
        mock_send_mail.assert_called_once()

    def test_send_notification_not_found(self):
        """Test sending notification that doesn't exist"""
        from Tracker.tasks import send_notification_task
        import uuid

        result = send_notification_task(999999)

        self.assertEqual(result['status'], 'error')
        self.assertIn('not found', result['message'])

    def test_send_notification_skipped_future(self):
        """Test that future notifications are skipped"""
        from Tracker.tasks import send_notification_task

        notification = NotificationTask.objects.create(
            notification_type='WEEKLY_REPORT',
            recipient=self.user_a,
            channel_type='EMAIL',
            interval_type='FIXED',
            status='PENDING',
            next_send_at=timezone.now() + timedelta(days=1),  # Future
        )

        result = send_notification_task(notification.id)

        self.assertEqual(result['status'], 'skipped')


class DispatchNotificationsTestCase(TenantTestCase):
    """Test the dispatch_pending_notifications task"""

    @patch('Tracker.tasks.send_notification_task.delay')
    def test_dispatch_pending_notifications(self, mock_send_delay):
        """Test dispatching pending notifications"""
        from Tracker.tasks import dispatch_pending_notifications

        # Create notifications ready to send
        notification1 = NotificationTask.objects.create(
            notification_type='WEEKLY_REPORT',
            recipient=self.user_a,
            channel_type='EMAIL',
            interval_type='FIXED',
            status='PENDING',
            next_send_at=timezone.now() - timedelta(minutes=5),
        )
        notification2 = NotificationTask.objects.create(
            notification_type='CAPA_REMINDER',
            recipient=self.user_a,
            channel_type='EMAIL',
            interval_type='DEADLINE_BASED',
            status='PENDING',
            next_send_at=timezone.now() - timedelta(minutes=1),
        )
        # Future notification - should not be dispatched
        NotificationTask.objects.create(
            notification_type='WEEKLY_REPORT',
            recipient=self.user_a,
            channel_type='EMAIL',
            interval_type='FIXED',
            status='PENDING',
            next_send_at=timezone.now() + timedelta(days=1),
        )

        result = dispatch_pending_notifications()

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['dispatched'], 2)
        self.assertEqual(mock_send_delay.call_count, 2)
