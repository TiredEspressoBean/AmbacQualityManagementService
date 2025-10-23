from celery import shared_task
import time
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


@shared_task
def test_celery_task(message="Hello from Celery!", delay=2):
    """
    A simple test task to verify Celery is working.
    Returns a message after a short delay.
    """
    time.sleep(delay)  # Simulate some work
    result = f"Task completed: {message}"
    return result


@shared_task
def add_numbers(x, y):
    """
    A simple addition task for testing.
    """
    result = x + y
    print(f"Adding {x} + {y} = {result}")
    return result


@shared_task(bind=True, max_retries=3)
def embed_document_async(self, document_id):
    """
    Asynchronously embed a document using AI/Ollama.

    Extracts text, chunks it, generates embeddings, and stores in DB.

    Args:
        document_id: The ID of the Document to embed

    Returns:
        dict with status and embedding info
    """
    import os
    from django.conf import settings
    from django.db import transaction
    from Tracker.models import Document, DocChunk
    from Tracker.ai_embed import embed_texts, chunk_text

    try:
        doc = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        logger.error(f"Document {document_id} not found")
        return {'status': 'error', 'message': 'Document not found'}

    if not settings.AI_EMBED_ENABLED:
        return {'status': 'skipped', 'message': 'AI embedding disabled'}

    if not doc.file or not os.path.exists(doc.file.path):
        return {'status': 'skipped', 'message': 'File not found'}

    file_size = os.path.getsize(doc.file.path)
    if file_size > settings.AI_EMBED_MAX_FILE_BYTES:
        return {'status': 'skipped', 'message': f'File too large: {file_size} bytes'}

    # Extract text
    text = doc._extract_text_from_file()
    if not text or not text.strip():
        return {'status': 'skipped', 'message': 'No text extracted'}

    # Chunk text
    chunks = chunk_text(
        text,
        max_chars=settings.AI_EMBED_CHUNK_CHARS,
        max_chunks=settings.AI_EMBED_MAX_CHUNKS
    )
    if not chunks:
        return {'status': 'skipped', 'message': 'No chunks created'}

    logger.info(f"Processing {len(chunks)} chunks for document {document_id}")

    # Generate embeddings with retry logic
    try:
        vecs = embed_texts(chunks)
    except Exception as e:
        logger.error(f"Error generating embeddings for document {document_id}: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        return {'status': 'error', 'message': str(e)}

    # Verify dimensions
    if vecs and len(vecs[0]) != settings.AI_EMBED_DIM:
        logger.error(f"Embedding dimension mismatch for document {document_id}")
        return {'status': 'error', 'message': 'Embedding dimension mismatch'}

    # Store in database
    rows = [
        DocChunk(
            doc=doc,
            preview_text=t[:300],
            full_text=t,
            span_meta={"i": i},
            embedding=v
        )
        for i, (t, v) in enumerate(zip(chunks, vecs))
    ]

    with transaction.atomic():
        DocChunk.objects.filter(doc=doc).delete()
        DocChunk.objects.bulk_create(rows, batch_size=settings.AI_EMBED_BATCH_SIZE)
        doc.ai_readable = True
        doc.save(update_fields=["ai_readable"])

    logger.info(f"Successfully embedded {len(chunks)} chunks for document {document_id}")
    return {
        'status': 'success',
        'document_id': document_id,
        'chunks_processed': len(chunks),
        'file_size': file_size
    }


@shared_task(bind=True, max_retries=3)
def send_weekly_order_update_task(self, customer_id: int, order_data: List[Dict[str, Any]]):
    """
    Celery task to send weekly order update email to a customer.

    Args:
        customer_id: Customer user ID
        order_data: List of order summary dicts with keys:
            - name, status, progress, current_stage, completion_date,
              total_parts, completed_parts, etc.

    Returns:
        dict with status and info
    """
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.utils import timezone
    from django.conf import settings
    from Tracker.models import User

    try:
        customer = User.objects.get(id=customer_id)
    except User.DoesNotExist:
        logger.error(f"Customer {customer_id} not found")
        return {'status': 'error', 'message': 'Customer not found'}

    # Prepare email context
    context = {
        'customer': customer,
        'orders': order_data,
        'week_ending': timezone.now().date(),
        'total_orders': len(order_data),
    }

    # Render email templates
    subject = f"Weekly Order Update - {timezone.now().strftime('%B %d, %Y')}"

    try:
        html_content = render_to_string('emails/weekly_customer_update.html', context)
        text_content = render_to_string('emails/weekly_customer_update.txt', context)
    except Exception as e:
        logger.error(f"Error rendering email templates for customer {customer_id}: {e}")
        return {'status': 'error', 'message': f'Template error: {str(e)}'}

    # Send email with retry logic
    try:
        send_mail(
            subject=subject,
            message=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[customer.email],
            html_message=html_content,
            fail_silently=False,
        )

        logger.info(f"Successfully sent weekly update to {customer.email}")
        return {
            'status': 'success',
            'customer_id': customer_id,
            'customer_email': customer.email,
            'orders_count': len(order_data)
        }

    except Exception as e:
        logger.error(f"Error sending email to {customer.email}: {e}")
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        return {'status': 'error', 'message': str(e)}


@shared_task
def send_weekly_emails_to_all_customers():
    """
    Celery Beat scheduled task to send weekly emails to all customers.

    This replaces the cron job. Runs once per week and queues individual
    email tasks for each customer with active orders.

    Returns:
        dict with summary of queued emails
    """
    from django.db.models import Q
    from Tracker.models import User, Orders, OrdersStatus
    from Tracker.email_notifications import send_weekly_order_update

    logger.info("Starting weekly email batch job")

    # Get customers with active orders
    active_statuses = [
        OrdersStatus.RFI,
        OrdersStatus.PENDING,
        OrdersStatus.IN_PROGRESS,
        OrdersStatus.ON_HOLD
    ]

    customers_with_orders = User.objects.filter(
        customer_orders__archived=False,
        customer_orders__order_status__in=active_statuses
    ).distinct()

    queued_count = 0
    skipped_count = 0

    for customer in customers_with_orders:
        # Get customer's active orders
        active_orders = Orders.objects.filter(
            customer=customer,
            archived=False,
            order_status__in=active_statuses
        ).select_related('company').prefetch_related('parts__step')

        if not active_orders.exists():
            skipped_count += 1
            continue

        # Prepare order data (same logic as management command)
        order_data = _prepare_order_data(active_orders)

        # Queue email task (async)
        send_weekly_order_update(customer.id, order_data, immediate=False)
        queued_count += 1
        logger.info(f"Queued weekly email for customer {customer.email}")

    logger.info(f"Weekly email batch complete: {queued_count} queued, {skipped_count} skipped")

    return {
        'status': 'success',
        'queued': queued_count,
        'skipped': skipped_count,
        'total_customers': customers_with_orders.count()
    }


def _prepare_order_data(orders):
    """
    Helper function to prepare order data for email.
    Extracted from management command logic.

    Filters orders to only include those with:
    - Active gate progress (is_in_progress=True), OR
    - Production parts in progress
    """
    from django.db.models import Avg, Max
    from Tracker.models import Steps

    order_summaries = []

    for order in orders:
        parts_qs = order.parts.filter(archived=False).select_related('step')
        total_parts = parts_qs.count()
        completed_parts = parts_qs.filter(part_status='COMPLETED').count()

        # Average current step index
        avg_step = parts_qs.aggregate(a=Avg('step__order'))['a'] or 0

        # All processes for the parts in this order
        process_ids = parts_qs.values_list('step__process_id', flat=True).distinct()

        # True max step across those processes
        max_step = (
            Steps.objects.filter(process_id__in=process_ids)
            .aggregate(m=Max('order'))['m']
        ) or 0

        progress = int(round(100 * (avg_step / max_step))) if max_step else 0

        # Get current stage
        current_stage = "Not Started"
        if order.parts.exists():
            first_part = order.parts.first()
            if first_part and first_part.step:
                current_stage = first_part.step.name

        gate_info = order.get_gate_info()

        # Filter: Only include orders with active gate progress OR production progress
        has_gate_progress = gate_info and gate_info.get('is_in_progress', False)
        has_production_progress = total_parts > 0 and current_stage != "Not Started"

        if not (has_gate_progress or has_production_progress):
            # Skip orders in terminal gate states with no production
            logger.debug(f"Skipping order {order.name} - no active progress (gate={has_gate_progress}, production={has_production_progress})")
            continue

        order_summaries.append({
            'name': order.name,
            'status': order.get_order_status_display(),
            'progress': round(progress),
            'current_stage': current_stage,
            'completion_date': order.estimated_completion,
            'original_completion': order.original_completion_date,
            'total_parts': total_parts,
            'completed_parts': completed_parts,
            'gate_info': gate_info,
        })

    return order_summaries


# ============================================================================
# NEW NOTIFICATION SYSTEM TASKS
# ============================================================================

@shared_task(bind=True, max_retries=3)
def send_notification_task(self, notification_id: int):
    """
    Celery task to send a single notification.

    This task:
    1. Loads the NotificationTask from the database
    2. Checks if it should send (status, timing, validation)
    3. Gets the appropriate handler and sends the notification
    4. Updates the NotificationTask state (mark_sent)

    Args:
        notification_id: ID of the NotificationTask to send

    Returns:
        dict with status and info
    """
    from django.utils import timezone
    from Tracker.models import NotificationTask
    from Tracker.notifications import get_notification_handler

    try:
        task = NotificationTask.objects.get(id=notification_id)
    except NotificationTask.DoesNotExist:
        logger.error(f"NotificationTask {notification_id} not found")
        return {'status': 'error', 'message': 'NotificationTask not found'}

    # Check if should send
    if not task.should_send():
        logger.info(f"NotificationTask {notification_id} should not send (status={task.status}, next_send_at={task.next_send_at})")
        return {'status': 'skipped', 'reason': f'status={task.status}'}

    # Get handler and validate
    try:
        handler = get_notification_handler(task.notification_type)
    except ValueError as e:
        logger.error(f"Unknown notification type for task {notification_id}: {task.notification_type}")
        return {'status': 'error', 'message': str(e)}

    # Additional validation (e.g., CAPA is not closed)
    if not handler.should_send(task):
        logger.info(f"NotificationTask {notification_id} failed validation, status updated to {task.status}")
        return {'status': 'cancelled', 'reason': 'validation_failed'}

    # Send the notification
    try:
        success = handler.send(task)
        task.mark_sent(success=success, sent_at=timezone.now())

        if success:
            logger.info(f"Successfully sent notification {notification_id} (attempt #{task.attempt_count})")
            return {
                'status': 'success',
                'notification_id': notification_id,
                'attempt_count': task.attempt_count,
                'next_send_at': task.next_send_at.isoformat() if task.status == 'pending' else None
            }
        else:
            logger.warning(f"Failed to send notification {notification_id}")
            return {'status': 'failed', 'notification_id': notification_id}

    except Exception as e:
        logger.error(f"Error sending notification {notification_id}: {e}")
        task.mark_sent(success=False)

        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

        return {'status': 'error', 'message': str(e)}


@shared_task(bind=True, max_retries=3)
def send_invitation_email_task(self, invitation_id: int):
    """
    Celery task to send invitation email to a user.

    Args:
        invitation_id: UserInvitation ID

    Returns:
        dict with status and info
    """
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.conf import settings
    from Tracker.models import UserInvitation

    try:
        invitation = UserInvitation.objects.select_related('user', 'invited_by').get(id=invitation_id)
    except UserInvitation.DoesNotExist:
        logger.error(f"UserInvitation {invitation_id} not found")
        return {'status': 'error', 'message': 'Invitation not found'}

    # Check if invitation is still valid
    if not invitation.is_valid():
        logger.warning(f"Invitation {invitation_id} is no longer valid (expired or accepted)")
        return {'status': 'skipped', 'message': 'Invitation no longer valid'}

    # Get frontend URL
    if settings.DEBUG:
        frontend_url = "http://localhost:5173"
    else:
        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://yourdomain.com')

    signup_url = f"{frontend_url}/signup?token={invitation.token}"

    # Prepare email context
    context = {
        'user': invitation.user,
        'invited_by': invitation.invited_by,
        'signup_url': signup_url,
        'expires_at': invitation.expires_at,
        'company_name': 'AMBAC',
    }

    # Render email templates
    subject = "You've been invited to join AMBAC Tracker"

    try:
        html_content = render_to_string('emails/user_invitation.html', context)
        text_content = render_to_string('emails/user_invitation.txt', context)
    except Exception as e:
        logger.error(f"Error rendering invitation email templates for invitation {invitation_id}: {e}")
        return {'status': 'error', 'message': f'Template error: {str(e)}'}

    # Send email with retry logic
    try:
        send_mail(
            subject=subject,
            message=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[invitation.user.email],
            html_message=html_content,
            fail_silently=False,
        )

        logger.info(f"Successfully sent invitation email to {invitation.user.email}")
        return {
            'status': 'success',
            'invitation_id': invitation_id,
            'user_email': invitation.user.email
        }

    except Exception as e:
        logger.error(f"Error sending invitation email to {invitation.user.email}: {e}")
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        return {'status': 'error', 'message': str(e)}


@shared_task
def dispatch_pending_notifications():
    """
    Celery Beat scheduled task to find and dispatch pending notifications.

    This task runs every 5 minutes (configured in celery_app.py) and:
    1. Finds all NotificationTask records that are ready to send
    2. Queues a send_notification_task for each one

    Returns:
        dict with summary of dispatched notifications
    """
    from django.utils import timezone
    from Tracker.models import NotificationTask

    logger.info("Dispatching pending notifications")

    # Find notifications ready to send
    now = timezone.now()
    ready_notifications = NotificationTask.objects.filter(
        status='pending',
        next_send_at__lte=now
    ).select_related('recipient')

    dispatched_count = 0
    for notification in ready_notifications:
        # Queue the send task
        send_notification_task.delay(notification.id)
        dispatched_count += 1
        logger.info(f"Dispatched notification {notification.id} ({notification.notification_type} to {notification.recipient.email})")

    logger.info(f"Dispatched {dispatched_count} notifications")

    return {
        'status': 'success',
        'dispatched': dispatched_count,
        'timestamp': now.isoformat()
    }


# ============================================================================
# HUBSPOT SYNC TASKS
# ============================================================================

@shared_task(bind=True, max_retries=2)
def sync_hubspot_deals_task(self):
    """
    Celery task to sync all HubSpot deals.

    Scheduled via Celery Beat for automatic periodic syncing.
    Can also be triggered manually via management command.

    Returns:
        dict with status and sync results
    """
    from Tracker.hubspot.sync import sync_all_deals

    logger.info("Starting HubSpot deals sync task")

    try:
        result = sync_all_deals()

        if result.get('status') == 'success':
            logger.info(f"HubSpot sync task completed: {result}")
            return result
        else:
            logger.error(f"HubSpot sync task failed: {result}")
            return result

    except Exception as e:
        logger.error(f"Error in HubSpot sync task: {e}", exc_info=True)

        # Retry with exponential backoff if HubSpot API fails
        if self.request.retries < self.max_retries:
            countdown = 300 * (2 ** self.request.retries)  # 5min, 10min
            logger.info(f"Retrying HubSpot sync in {countdown} seconds")
            raise self.retry(exc=e, countdown=countdown)

        return {'status': 'error', 'message': str(e)}


@shared_task(bind=True, max_retries=3)
def update_hubspot_deal_stage_task(self, deal_id, new_stage_id, order_id):
    """
    Update a deal stage in HubSpot asynchronously.

    Called when a user changes an order's HubSpot stage in the app.
    Pushes the change back to HubSpot.

    Args:
        deal_id: HubSpot deal ID
        new_stage_id: New stage ID (ExternalAPIOrderIdentifier ID)
        order_id: Local Order ID

    Returns:
        dict with status
    """
    from Tracker.hubspot.api import update_deal_stage
    from Tracker.models import Orders, ExternalAPIOrderIdentifier

    logger.info(f"Updating HubSpot deal {deal_id} to stage {new_stage_id}")

    try:
        order = Orders.objects.get(id=order_id)

        # Double-check this is a HubSpot order
        if not order.hubspot_deal_id:
            logger.warning(f"Order {order_id} is not a HubSpot order, skipping push")
            return {'status': 'skipped', 'reason': 'not_hubspot_order'}

        stage = ExternalAPIOrderIdentifier.objects.get(id=new_stage_id)
        result = update_deal_stage(deal_id, stage, order)

        if result:
            logger.info(f"Successfully updated HubSpot deal {deal_id}")
            return {
                'status': 'success',
                'deal_id': deal_id,
                'new_stage': stage.stage_name
            }
        else:
            raise Exception("Failed to update deal stage in HubSpot")

    except Exception as e:
        logger.error(f"Error updating HubSpot deal {deal_id}: {e}")

        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

        return {'status': 'error', 'message': str(e)}
