from celery import shared_task, Task
from smtplib import SMTPException
import time
import logging
from typing import List, Dict, Any

from Tracker.utils.tenant_context import (
    tenant_context,
    get_tenant_for_object,
    with_tenant_from_model,
)

logger = logging.getLogger(__name__)


# ============================================================================
# RETRYABLE TASK BASE CLASSES
# ============================================================================

class RetryableEmailTask(Task):
    """Base task for email operations with automatic retry on transient failures."""
    autoretry_for = (SMTPException, ConnectionError, TimeoutError, OSError)
    retry_backoff = True
    retry_backoff_max = 600  # Max 10 minutes between retries
    retry_jitter = True
    max_retries = 3
    soft_time_limit = 120  # 2 minutes soft limit
    time_limit = 180  # 3 minutes hard limit


class RetryableEmbeddingTask(Task):
    """Base task for AI embedding operations with automatic retry."""
    autoretry_for = (ConnectionError, TimeoutError, OSError)
    retry_backoff = True
    retry_backoff_max = 300  # Max 5 minutes between retries
    retry_jitter = True
    max_retries = 5
    soft_time_limit = 300  # 5 minutes soft limit (embeddings can be slow)
    time_limit = 600  # 10 minutes hard limit


class RetryableHubSpotTask(Task):
    """Base task for HubSpot API operations with automatic retry on rate limits."""
    autoretry_for = (ConnectionError, TimeoutError, OSError)
    retry_backoff = True
    retry_backoff_max = 900  # Max 15 minutes between retries (for rate limits)
    retry_jitter = True
    max_retries = 4
    soft_time_limit = 60  # 1 minute soft limit
    time_limit = 120  # 2 minutes hard limit


class RetryableFileTask(Task):
    """Base task for file conversion operations with automatic retry."""
    autoretry_for = (TimeoutError, MemoryError, OSError)
    retry_backoff = True
    retry_backoff_max = 120  # Max 2 minutes between retries
    retry_jitter = True
    max_retries = 2
    soft_time_limit = 300  # 5 minutes soft limit (file conversion can be slow)
    time_limit = 600  # 10 minutes hard limit


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


@shared_task(bind=True, base=RetryableEmbeddingTask)
def embed_document_async(self, document_id):
    """
    Asynchronously embed a document using AI/Ollama.

    Extracts text, chunks it, generates embeddings, and stores in DB.
    Uses RetryableEmbeddingTask for automatic retry with exponential backoff.

    Args:
        document_id: The ID of the Document to embed

    Returns:
        dict with status and embedding info
    """
    import os
    from django.conf import settings
    from django.db import transaction
    from Tracker.models import Documents, DocChunk
    from Tracker.ai_embed import embed_texts, chunk_text

    # First lookup bypasses RLS to get tenant context
    try:
        doc = Documents.all_objects.get(id=document_id)
    except Documents.DoesNotExist:
        logger.error(f"Document {document_id} not found")
        return {'status': 'error', 'message': 'Document not found'}

    # Now run with tenant context for RLS enforcement
    tenant_id = get_tenant_for_object(doc)
    with tenant_context(tenant_id):
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

        # Generate embeddings - autoretry handles transient failures
        vecs = embed_texts(chunks)

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


# ============================================================================
# 3D MODEL PROCESSING
# ============================================================================

@shared_task(bind=True, base=RetryableFileTask)
def process_3d_model(self, model_id: str):
    """
    Process uploaded 3D model asynchronously.

    Converts CAD formats (STEP) and mesh formats (STL, OBJ, PLY) to optimized GLB.
    Applies mesh decimation to keep face count under target threshold.

    Uses RetryableFileTask for automatic retry on transient failures.

    Args:
        model_id: UUID of the ThreeDModel instance to process.

    Returns:
        dict with status and processing metrics.
    """
    from pathlib import Path
    from django.core.files.base import ContentFile
    from django.utils import timezone
    from Tracker.models import ThreeDModel, ModelProcessingStatus
    from Tracker.services.model_processor import ModelProcessor, ProcessingConfig

    # Lookup model (bypass RLS for background task)
    try:
        model = ThreeDModel.all_objects.get(id=model_id)
    except ThreeDModel.DoesNotExist:
        logger.error(f"ThreeDModel {model_id} not found")
        return {'status': 'error', 'message': 'Model not found'}

    # Get tenant context for proper isolation
    tenant_id = get_tenant_for_object(model)

    with tenant_context(tenant_id):
        # Mark as processing
        model.processing_status = ModelProcessingStatus.PROCESSING
        model.save(update_fields=['processing_status'])

        try:
            # Store original file info
            original_path = model.file.path
            original_name = model.file.name
            original_ext = Path(original_path).suffix.lower()

            model.original_filename = Path(original_name).name
            model.original_format = original_ext.lstrip('.')
            model.original_size_bytes = model.file.size

            # Process the model (convert + optimize)
            processor = ModelProcessor(ProcessingConfig(
                target_faces=100_000,
                min_faces=5_000,
                linear_deflection=0.1,
                angular_deflection=0.5,
            ))

            result = processor.process(original_path)

            if not result.success:
                raise Exception(result.error)

            # If conversion produced a new file, update the model
            if result.output_path and result.output_path != original_path:
                with open(result.output_path, 'rb') as f:
                    new_filename = Path(original_name).stem + '.glb'
                    model.file.save(new_filename, ContentFile(f.read()), save=False)

                # Clean up temporary output file
                Path(result.output_path).unlink(missing_ok=True)

                # Also clean up original file if it was different
                if Path(original_path).exists() and original_path != result.output_path:
                    try:
                        Path(original_path).unlink()
                    except Exception as e:
                        logger.warning(f"Could not delete original file {original_path}: {e}")

            # Update model with results
            model.file_type = 'glb'
            model.face_count = result.face_count
            model.vertex_count = result.vertex_count
            model.final_size_bytes = result.final_size
            model.processing_status = ModelProcessingStatus.COMPLETED
            model.processed_at = timezone.now()
            model.processing_error = ''
            model.save()

            logger.info(
                f"Processed 3D model {model_id} ({model.name}): "
                f"{model.original_format}→glb, "
                f"{result.face_count:,} faces, "
                f"{model.original_size_bytes:,}→{result.final_size:,} bytes"
            )

            return {
                'status': 'success',
                'model_id': str(model_id),
                'name': model.name,
                'original_format': model.original_format,
                'face_count': result.face_count,
                'vertex_count': result.vertex_count,
                'original_size': model.original_size_bytes,
                'final_size': result.final_size,
                'compression_ratio': result.compression_ratio,
            }

        except Exception as e:
            logger.exception(f"Failed to process 3D model {model_id}")

            model.processing_status = ModelProcessingStatus.FAILED
            model.processing_error = str(e)[:1000]  # Truncate long errors
            model.save(update_fields=['processing_status', 'processing_error'])

            return {
                'status': 'error',
                'model_id': str(model_id),
                'error': str(e)
            }


@shared_task(bind=True, base=RetryableEmailTask)
def send_weekly_order_update_task(self, customer_id: int, order_data: List[Dict[str, Any]]):
    """
    Celery task to send weekly order update email to a customer.
    Uses RetryableEmailTask for automatic retry with exponential backoff.

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

    # Send email - autoretry handles SMTP failures
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


@shared_task
def send_weekly_emails_to_all_customers():
    """
    DEPRECATED: Use create_weekly_report_notifications instead.

    This task is kept for backwards compatibility but now redirects to the
    new notification system which uses NotificationTask records.

    Returns:
        dict with redirect info
    """
    logger.warning(
        "send_weekly_emails_to_all_customers is deprecated. "
        "Use create_weekly_report_notifications instead."
    )
    # Delegate to new system
    return create_weekly_report_notifications()


def _prepare_order_data(orders):
    """
    Helper function to prepare order data for email.
    Extracted from management command logic.

    Filters orders to only include those with:
    - Active gate progress (is_in_progress=True), OR
    - Production parts in progress
    """
    from django.db.models import Avg, Max
    from Tracker.models import ProcessStep

    order_summaries = []

    for order in orders:
        parts_qs = order.parts.filter(archived=False).select_related('step', 'work_order', 'work_order__process')
        total_parts = parts_qs.count()
        completed_parts = parts_qs.filter(part_status='COMPLETED').count()

        # Calculate progress based on work order's process
        progress = 0
        if total_parts > 0:
            # Get unique processes from work orders
            work_orders = order.related_orders.filter(archived=False).select_related('process')
            if work_orders.exists():
                # Use the first work order's process for progress calculation
                first_wo = work_orders.first()
                if first_wo and first_wo.process:
                    process = first_wo.process
                    max_step = process.process_steps.count()

                    if max_step > 0:
                        # Calculate average step position using ProcessStep
                        step_ids = parts_qs.values_list('step_id', flat=True).distinct()
                        avg_order = ProcessStep.objects.filter(
                            process=process,
                            step_id__in=step_ids
                        ).aggregate(a=Avg('order'))['a'] or 0
                        progress = int(round(100 * (avg_order / max_step)))

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

@shared_task(bind=True, base=RetryableEmailTask)
def send_notification_task(self, notification_id: int):
    """
    Celery task to send a single notification.
    Uses RetryableEmailTask for automatic retry with exponential backoff.

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
    from Tracker.models import NotificationTask as NotificationTaskModel
    from Tracker.notifications import get_notification_handler

    # Initial lookup to get tenant context (bypasses RLS)
    try:
        task = NotificationTaskModel.objects.get(id=notification_id)
    except NotificationTaskModel.DoesNotExist:
        logger.error(f"NotificationTask {notification_id} not found")
        return {'status': 'error', 'message': 'NotificationTask not found'}

    # Run with tenant context for RLS enforcement
    tenant_id = get_tenant_for_object(task)
    with tenant_context(tenant_id):
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

        # Send the notification - autoretry handles transient failures
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


@shared_task(bind=True, base=RetryableEmailTask)
def send_invitation_email_task(self, invitation_id: int):
    """
    Celery task to send invitation email to a user.
    Uses RetryableEmailTask for automatic retry with exponential backoff.

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

    # Send email - autoretry handles SMTP failures
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


@shared_task
def dispatch_pending_notifications():
    """
    Celery Beat scheduled task to find and dispatch pending notifications.

    This task runs every 5 minutes (configured in celery_app.py) and:
    1. Finds all NotificationTask records that are ready to send
    2. Queues a send_notification_task for each one

    Note: This task queries across all tenants but doesn't require RLS context
    because it only reads notification IDs and dispatches individual tasks.
    Each dispatched task will set its own tenant context.

    Returns:
        dict with summary of dispatched notifications
    """
    from django.utils import timezone
    from Tracker.models import NotificationTask as NotificationTaskModel

    logger.info("Dispatching pending notifications")

    # Find notifications ready to send (cross-tenant query for scheduling)
    # This is safe because we're just reading IDs and dispatching individual tasks
    now = timezone.now()
    ready_notifications = NotificationTaskModel.objects.filter(
        status='pending',
        next_send_at__lte=now
    ).select_related('recipient').values_list('id', flat=True)

    dispatched_count = 0
    for notification_id in ready_notifications:
        # Queue the send task (will set tenant context from notification)
        send_notification_task.delay(notification_id)
        dispatched_count += 1
        logger.info(f"Dispatched notification {notification_id}")

    logger.info(f"Dispatched {dispatched_count} notifications")

    return {
        'status': 'success',
        'dispatched': dispatched_count,
        'timestamp': now.isoformat()
    }


# ============================================================================
# NOTIFICATION CREATION TASKS (Create NotificationTask records for dispatch)
# ============================================================================

@shared_task
def create_weekly_report_notifications():
    """
    Celery Beat scheduled task to create WEEKLY_REPORT NotificationTask records.

    Runs weekly (Tuesday 3 PM) and creates notification records for each customer
    with active orders. The dispatch_pending_notifications task will then send them.

    Returns:
        dict with summary of created notifications
    """
    from django.db.models import Q
    from django.utils import timezone
    from django.contrib.contenttypes.models import ContentType
    from Tracker.models import User, Orders, OrdersStatus, NotificationTask as NotificationTaskModel, Tenant

    logger.info("Creating weekly report notifications")

    active_statuses = [
        OrdersStatus.RFI,
        OrdersStatus.PENDING,
        OrdersStatus.IN_PROGRESS,
        OrdersStatus.ON_HOLD
    ]

    created_count = 0
    skipped_count = 0

    # Process each active tenant
    for tenant in Tenant.objects.filter(is_active=True):
        with tenant_context(tenant.id):
            # Get customers with active orders in this tenant
            customers_with_orders = User.objects.filter(
                customer_orders__archived=False,
                customer_orders__order_status__in=active_statuses,
                customer_orders__tenant=tenant
            ).distinct()

            for customer in customers_with_orders:
                if not customer.email:
                    skipped_count += 1
                    continue

                # Check if we already have a pending weekly report for this customer
                existing = NotificationTaskModel.objects.filter(
                    notification_type='WEEKLY_REPORT',
                    recipient=customer,
                    status='pending'
                ).exists()

                if existing:
                    skipped_count += 1
                    continue

                # Create notification task (dispatch will call handler to build context)
                NotificationTaskModel.objects.create(
                    notification_type='WEEKLY_REPORT',
                    recipient=customer,
                    channel_type='email',
                    interval_type='fixed',
                    status='pending',
                    next_send_at=timezone.now(),
                )
                created_count += 1
                logger.info(f"Created weekly report notification for {customer.email}")

    logger.info(f"Weekly report notifications: {created_count} created, {skipped_count} skipped")

    return {
        'status': 'success',
        'created': created_count,
        'skipped': skipped_count,
    }


@shared_task
def check_capa_reminders():
    """
    Celery Beat scheduled task to create CAPA_REMINDER NotificationTask records.

    Runs daily and creates reminder notifications for CAPAs based on due date proximity.
    Uses escalation tiers:
    - 28+ days out: remind every 28 days
    - 14-28 days out: remind every 7 days
    - 0-14 days out: remind every 3 days
    - Overdue: remind daily

    Returns:
        dict with summary of created notifications
    """
    from django.utils import timezone
    from django.contrib.contenttypes.models import ContentType
    from Tracker.models import CAPA, NotificationTask as NotificationTaskModel, Tenant

    logger.info("Checking CAPA reminders")

    today = timezone.now().date()
    created_count = 0
    skipped_count = 0

    # Escalation tiers: [threshold_days, interval_days]
    # threshold_days: if days_until_due <= threshold, use this interval
    ESCALATION_TIERS = [
        (28, 28),   # 28+ days out: every 28 days
        (14, 7),    # 14-28 days out: every 7 days
        (0, 3),     # 0-14 days out: every 3 days
        (-9999, 1), # Overdue: daily
    ]

    capa_ct = ContentType.objects.get_for_model(CAPA)

    # Process each active tenant
    for tenant in Tenant.objects.filter(is_active=True):
        with tenant_context(tenant.id):
            # Get open CAPAs with due dates and assigned users
            open_capas = CAPA.objects.filter(
                tenant=tenant,
                assigned_to__isnull=False,
                due_date__isnull=False,
            ).exclude(
                status__in=['CLOSED', 'CANCELLED']
            ).select_related('assigned_to')

            for capa in open_capas:
                if not capa.assigned_to.email:
                    skipped_count += 1
                    continue

                days_until_due = (capa.due_date - today).days

                # Determine interval based on escalation tiers
                interval_days = None
                for threshold, interval in ESCALATION_TIERS:
                    if days_until_due <= threshold:
                        interval_days = interval
                    else:
                        break

                if interval_days is None:
                    interval_days = ESCALATION_TIERS[0][1]  # Default to longest interval

                # Check if we recently sent a reminder for this CAPA
                recent_notification = NotificationTaskModel.objects.filter(
                    notification_type='CAPA_REMINDER',
                    related_content_type=capa_ct,
                    related_object_id=str(capa.id),
                    status='sent',
                    last_sent_at__gte=timezone.now() - timezone.timedelta(days=interval_days)
                ).exists()

                if recent_notification:
                    skipped_count += 1
                    continue

                # Check for pending notification already queued
                pending_exists = NotificationTaskModel.objects.filter(
                    notification_type='CAPA_REMINDER',
                    related_content_type=capa_ct,
                    related_object_id=str(capa.id),
                    status='pending'
                ).exists()

                if pending_exists:
                    skipped_count += 1
                    continue

                # Create CAPA reminder notification
                NotificationTaskModel.objects.create(
                    notification_type='CAPA_REMINDER',
                    recipient=capa.assigned_to,
                    channel_type='email',
                    interval_type='deadline_based',
                    deadline=timezone.make_aware(
                        timezone.datetime.combine(capa.due_date, timezone.datetime.min.time())
                    ) if capa.due_date else None,
                    status='pending',
                    next_send_at=timezone.now(),
                    related_content_type=capa_ct,
                    related_object_id=str(capa.id),
                )
                created_count += 1
                logger.info(f"Created CAPA reminder for {capa.capa_number} (due in {days_until_due} days)")

    logger.info(f"CAPA reminders: {created_count} created, {skipped_count} skipped")

    return {
        'status': 'success',
        'created': created_count,
        'skipped': skipped_count,
    }


# ============================================================================
# HUBSPOT SYNC TASKS
# ============================================================================

@shared_task(bind=True, base=RetryableHubSpotTask)
def sync_hubspot_deals_task(self):
    """
    Celery task to sync all HubSpot deals.
    Uses RetryableHubSpotTask for automatic retry with exponential backoff.

    Scheduled via Celery Beat for automatic periodic syncing.
    Can also be triggered manually via management command.

    Returns:
        dict with status and sync results
    """
    from Tracker.hubspot.sync import sync_all_deals

    logger.info("Starting HubSpot deals sync task")

    result = sync_all_deals()

    if result.get('status') == 'success':
        logger.info(f"HubSpot sync task completed: {result}")
        return result
    else:
        logger.error(f"HubSpot sync task failed: {result}")
        return result


@shared_task(bind=True, base=RetryableHubSpotTask)
def update_hubspot_deal_stage_task(self, deal_id, new_stage_id, order_id):
    """
    Update a deal stage in HubSpot asynchronously.
    Uses RetryableHubSpotTask for automatic retry with exponential backoff.

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


@shared_task(bind=True, base=RetryableEmailTask)
def send_approval_request_notification(self, approval_request_id):
    """Send email notifications to all pending approvers.
    Uses RetryableEmailTask for automatic retry with exponential backoff."""
    from .models import ApprovalRequest
    from django.core.mail import send_mail
    from django.conf import settings

    # Initial lookup to get tenant context
    try:
        approval = ApprovalRequest.objects.get(id=approval_request_id)
    except ApprovalRequest.DoesNotExist:
        logger.error(f"ApprovalRequest {approval_request_id} not found")
        return {'status': 'error', 'message': 'Approval request not found'}

    # Run with tenant context for RLS enforcement
    tenant_id = get_tenant_for_object(approval)
    with tenant_context(tenant_id):
        pending_approvers = approval.get_pending_approvers()

        for approver in pending_approvers:
            if approver.email:
                subject = f"Approval Request: {approval.approval_number}"
                message = f"""
You have been assigned to approve: {approval.get_approval_type_display()}

Approval Number: {approval.approval_number}
Requested By: {approval.requested_by.get_full_name() if approval.requested_by else 'System'}
Due Date: {approval.due_date.strftime('%Y-%m-%d %H:%M') if approval.due_date else 'Not set'}

Reason: {approval.reason or 'No reason provided'}

Please log in to the system to review and respond to this approval request.
                """

                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [approver.email],
                    fail_silently=False,
                )

        return {'status': 'success', 'sent_to': len(pending_approvers)}


@shared_task(bind=True, base=RetryableEmailTask)
def send_approval_decision_notification(self, approval_request_id):
    """Send notification to requester when approval is decided.
    Uses RetryableEmailTask for automatic retry with exponential backoff."""
    from .models import ApprovalRequest
    from django.core.mail import send_mail
    from django.conf import settings

    try:
        approval = ApprovalRequest.objects.get(id=approval_request_id)
    except ApprovalRequest.DoesNotExist:
        logger.error(f"ApprovalRequest {approval_request_id} not found")
        return {'status': 'error', 'message': 'Approval request not found'}

    if approval.requested_by and approval.requested_by.email:
        subject = f"Approval Decision: {approval.approval_number}"
        decision = approval.get_status_display()

        message = f"""
Your approval request has been {decision.lower()}.

Approval Number: {approval.approval_number}
Type: {approval.get_approval_type_display()}
Decision: {decision}
Completed At: {approval.completed_at.strftime('%Y-%m-%d %H:%M') if approval.completed_at else 'N/A'}

You can view the details in the system.
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [approval.requested_by.email],
            fail_silently=False,
        )

        return {'status': 'success'}

    return {'status': 'skipped', 'message': 'No email address for requester'}


@shared_task(bind=True, base=RetryableEmailTask)
def check_overdue_approvals(self):
    """Daily task to check for overdue approvals and send reminders.
    Uses RetryableEmailTask for automatic retry with exponential backoff.

    This task runs across all tenants, processing each tenant's approvals separately
    to maintain proper tenant isolation.
    """
    from .models import ApprovalRequest, Approval_Status_Type, Tenant
    from django.core.mail import send_mail
    from django.conf import settings
    from django.utils import timezone

    total_reminder_count = 0
    total_overdue_count = 0

    # Process each active tenant separately for RLS compliance
    active_tenants = Tenant.objects.filter(is_active=True)

    for tenant in active_tenants:
        with tenant_context(tenant.id):
            overdue_approvals = ApprovalRequest.objects.filter(
                status=Approval_Status_Type.PENDING,
                due_date__lt=timezone.now(),
                tenant=tenant
            )
            total_overdue_count += overdue_approvals.count()

            for approval in overdue_approvals:
                pending_approvers = approval.get_pending_approvers()

                for approver in pending_approvers:
                    if approver.email:
                        days_overdue = (timezone.now() - approval.due_date).days

                        subject = f"OVERDUE: Approval Request {approval.approval_number}"
                        message = f"""
REMINDER: You have an overdue approval request.

Approval Number: {approval.approval_number}
Type: {approval.get_approval_type_display()}
Due Date: {approval.due_date.strftime('%Y-%m-%d %H:%M')}
Days Overdue: {days_overdue}

Please respond as soon as possible.
                        """

                        send_mail(
                            subject,
                            message,
                            settings.DEFAULT_FROM_EMAIL,
                            [approver.email],
                            fail_silently=False,
                        )
                        total_reminder_count += 1

    return {
        'status': 'success',
        'reminders_sent': total_reminder_count,
        'overdue_count': total_overdue_count,
        'tenants_processed': active_tenants.count()
    }


@shared_task
def escalate_approvals():
    """
    Check for approvals past escalation_day and create APPROVAL_ESCALATION notifications.

    Creates NotificationTask records which are then dispatched by dispatch_pending_notifications.
    This ensures escalations go through the unified notification system with templates.
    """
    from .models import ApprovalRequest, Approval_Status_Type, NotificationTask as NotificationTaskModel, Tenant
    from django.contrib.contenttypes.models import ContentType
    from django.utils import timezone

    today = timezone.now().date()
    created_count = 0
    skipped_count = 0

    approval_ct = ContentType.objects.get_for_model(ApprovalRequest)

    # Process each active tenant
    for tenant in Tenant.objects.filter(is_active=True):
        with tenant_context(tenant.id):
            escalation_approvals = ApprovalRequest.objects.filter(
                status=Approval_Status_Type.PENDING,
                escalation_day__lte=today,
                escalate_to__isnull=False,
                tenant=tenant
            ).select_related('escalate_to')

            for approval in escalation_approvals:
                if not approval.escalate_to.email:
                    skipped_count += 1
                    continue

                # Check if we already sent an escalation today
                already_sent = NotificationTaskModel.objects.filter(
                    notification_type='APPROVAL_ESCALATION',
                    related_content_type=approval_ct,
                    related_object_id=str(approval.id),
                    status='sent',
                    last_sent_at__date=today
                ).exists()

                if already_sent:
                    skipped_count += 1
                    continue

                # Check for pending escalation already queued
                pending_exists = NotificationTaskModel.objects.filter(
                    notification_type='APPROVAL_ESCALATION',
                    related_content_type=approval_ct,
                    related_object_id=str(approval.id),
                    status='pending'
                ).exists()

                if pending_exists:
                    skipped_count += 1
                    continue

                # Create escalation notification
                NotificationTaskModel.objects.create(
                    notification_type='APPROVAL_ESCALATION',
                    recipient=approval.escalate_to,
                    channel_type='email',
                    interval_type='fixed',
                    status='pending',
                    next_send_at=timezone.now(),
                    related_content_type=approval_ct,
                    related_object_id=str(approval.id),
                )
                created_count += 1
                logger.info(f"Created escalation notification for approval {approval.approval_number}")

    logger.info(f"Approval escalations: {created_count} created, {skipped_count} skipped")

    return {
        'status': 'success',
        'created': created_count,
        'skipped': skipped_count,
    }


@shared_task(bind=True, base=RetryableEmailTask)
def send_capa_assignment_notification(self, capa_id):
    """Send notification when CAPA is assigned.
    Uses RetryableEmailTask for automatic retry with exponential backoff."""
    from .models import CAPA
    from django.core.mail import send_mail
    from django.conf import settings

    # Initial lookup to get tenant context
    try:
        capa = CAPA.objects.get(id=capa_id)
    except CAPA.DoesNotExist:
        logger.error(f"CAPA {capa_id} not found")
        return {'status': 'error', 'message': 'CAPA not found'}

    # Run with tenant context for RLS enforcement
    tenant_id = get_tenant_for_object(capa)
    with tenant_context(tenant_id):
        if capa.assigned_to and capa.assigned_to.email:
            subject = f"CAPA Assignment: {capa.capa_number}"
            message = f"""
You have been assigned to a CAPA.

CAPA Number: {capa.capa_number}
Type: {capa.get_capa_type_display()}
Severity: {capa.get_severity_display()}
Initiated By: {capa.initiated_by.get_full_name() if capa.initiated_by else 'System'}
Due Date: {capa.due_date.strftime('%Y-%m-%d') if capa.due_date else 'Not set'}

Problem Statement:
{capa.problem_statement}

Please log in to review and work on this CAPA.
            """

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [capa.assigned_to.email],
                fail_silently=False,
            )

            return {'status': 'success'}

        return {'status': 'skipped', 'message': 'No email for assigned user'}


@shared_task(bind=True, base=RetryableEmailTask)
def send_capa_task_assignment_notification(self, task_id):
    """Send notification when CAPA task is assigned.
    Uses RetryableEmailTask for automatic retry with exponential backoff."""
    from .models import CapaTasks
    from django.core.mail import send_mail
    from django.conf import settings

    try:
        task = CapaTasks.objects.get(id=task_id)
    except CapaTasks.DoesNotExist:
        logger.error(f"CapaTasks {task_id} not found")
        return {'status': 'error', 'message': 'Task not found'}

    if task.assigned_to and task.assigned_to.email:
        subject = f"CAPA Task Assignment: {task.task_number}"
        message = f"""
You have been assigned a CAPA task.

Task Number: {task.task_number}
CAPA: {task.capa.capa_number}
Type: {task.get_task_type_display()}
Due Date: {task.due_date.strftime('%Y-%m-%d') if task.due_date else 'Not set'}

Description:
{task.description}

Please log in to view details and complete this task.
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [task.assigned_to.email],
            fail_silently=False,
        )

        return {'status': 'success'}

    return {'status': 'skipped', 'message': 'No email for assigned user'}


@shared_task(bind=True, base=RetryableEmailTask)
def send_capa_ready_for_verification_notification(self, capa_id):
    """Notify when CAPA is ready for verification.
    Uses RetryableEmailTask for automatic retry with exponential backoff."""
    from .models import CAPA
    from django.core.mail import send_mail
    from django.conf import settings

    try:
        capa = CAPA.objects.get(id=capa_id)
    except CAPA.DoesNotExist:
        logger.error(f"CAPA {capa_id} not found")
        return {'status': 'error', 'message': 'CAPA not found'}

    # Notify initiated_by and QA managers
    recipients = []
    if capa.initiated_by and capa.initiated_by.email:
        recipients.append(capa.initiated_by.email)

    # Add QA managers
    from django.contrib.auth.models import Group
    qa_group = Group.objects.filter(name='QA').first()
    if qa_group:
        qa_emails = list(qa_group.user_set.filter(email__isnull=False).values_list('email', flat=True))
        recipients.extend(qa_emails)

    if recipients:
        subject = f"CAPA Ready for Verification: {capa.capa_number}"
        message = f"""
CAPA {capa.capa_number} is ready for verification.

All tasks have been completed and RCA is complete.

CAPA Number: {capa.capa_number}
Severity: {capa.get_severity_display()}
Assigned To: {capa.assigned_to.get_full_name() if capa.assigned_to else 'None'}

Please perform effectiveness verification to proceed with closure.
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            list(set(recipients)),  # Remove duplicates
            fail_silently=False,
        )

        return {'status': 'success', 'recipients': len(recipients)}

    return {'status': 'skipped', 'message': 'No recipients'}


@shared_task(bind=True, base=RetryableEmailTask)
def send_capa_verification_complete_notification(self, capa_id):
    """Notify when CAPA verification is confirmed effective.
    Uses RetryableEmailTask for automatic retry with exponential backoff."""
    from .models import CAPA
    from django.core.mail import send_mail
    from django.conf import settings

    try:
        capa = CAPA.objects.get(id=capa_id)
    except CAPA.DoesNotExist:
        logger.error(f"CAPA {capa_id} not found")
        return {'status': 'error', 'message': 'CAPA not found'}

    recipients = []
    if capa.initiated_by and capa.initiated_by.email:
        recipients.append(capa.initiated_by.email)
    if capa.assigned_to and capa.assigned_to.email:
        recipients.append(capa.assigned_to.email)

    if recipients:
        subject = f"CAPA Verification Complete: {capa.capa_number}"
        message = f"""
CAPA {capa.capa_number} has been verified as effective and is ready to close.

CAPA Number: {capa.capa_number}
Verified By: {capa.verification.verified_by.get_full_name() if capa.verification and capa.verification.verified_by else 'Unknown'}
Result: {capa.verification.get_effectiveness_result_display() if capa.verification else 'N/A'}

You can now close this CAPA.
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            list(set(recipients)),
            fail_silently=False,
        )

        return {'status': 'success'}

    return {'status': 'skipped', 'message': 'No recipients'}


@shared_task(bind=True, base=RetryableEmailTask)
def check_overdue_capas(self):
    """Daily task to check for overdue CAPAs and tasks.
    Uses RetryableEmailTask for automatic retry with exponential backoff.

    This task runs across all tenants, processing each tenant's CAPAs separately
    to maintain proper tenant isolation.
    """
    from .models import CAPA, CapaTasks, CapaStatus, Tenant
    from django.core.mail import send_mail
    from django.conf import settings
    from django.utils import timezone

    today = timezone.now().date()
    total_capa_reminders = 0
    total_task_reminders = 0
    total_overdue_capas = 0
    total_overdue_tasks = 0

    # Process each active tenant separately for RLS compliance
    active_tenants = Tenant.objects.filter(is_active=True)

    for tenant in active_tenants:
        with tenant_context(tenant.id):
            # Check overdue CAPAs (filter by computed_status since status is now derived)
            overdue_capas = [
                capa for capa in CAPA.objects.filter(due_date__lt=today, tenant=tenant)
                if capa.computed_status in [CapaStatus.OPEN, CapaStatus.IN_PROGRESS, CapaStatus.PENDING_VERIFICATION]
            ]
            total_overdue_capas += len(overdue_capas)

            for capa in overdue_capas:
                if capa.assigned_to and capa.assigned_to.email:
                    days_overdue = (today - capa.due_date).days

                    subject = f"OVERDUE: CAPA {capa.capa_number}"
                    message = f"""
REMINDER: You have an overdue CAPA.

CAPA Number: {capa.capa_number}
Severity: {capa.get_severity_display()}
Due Date: {capa.due_date.strftime('%Y-%m-%d')}
Days Overdue: {days_overdue}

Please complete this CAPA as soon as possible.
                    """

                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [capa.assigned_to.email],
                        fail_silently=False,
                    )
                    total_capa_reminders += 1

            # Check overdue tasks
            overdue_tasks = CapaTasks.objects.filter(
                status__in=['NOT_STARTED', 'IN_PROGRESS'],
                due_date__lt=today,
                capa__tenant=tenant
            )
            total_overdue_tasks += overdue_tasks.count()

            for task in overdue_tasks:
                if task.assigned_to and task.assigned_to.email:
                    days_overdue = (today - task.due_date).days

                    subject = f"OVERDUE: CAPA Task {task.task_number}"
                    message = f"""
REMINDER: You have an overdue CAPA task.

Task Number: {task.task_number}
CAPA: {task.capa.capa_number}
Due Date: {task.due_date.strftime('%Y-%m-%d')}
Days Overdue: {days_overdue}

Please complete this task as soon as possible.
                    """

                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [task.assigned_to.email],
                        fail_silently=False,
                    )
                    total_task_reminders += 1

    return {
        'status': 'success',
        'capa_reminders': total_capa_reminders,
        'task_reminders': total_task_reminders,
        'overdue_capas': total_overdue_capas,
        'overdue_tasks': total_overdue_tasks,
        'tenants_processed': active_tenants.count()
    }


# ============================================================================
# PDF REPORT GENERATION TASKS
# ============================================================================

class RetryablePdfTask(Task):
    """Base task for PDF generation operations with automatic retry."""
    autoretry_for = (ConnectionError, TimeoutError, OSError)
    retry_backoff = True
    retry_backoff_max = 300  # Max 5 minutes between retries
    retry_jitter = True
    max_retries = 3


# ============================================================================
# CSV IMPORT TASKS
# ============================================================================

class RetryableImportTask(Task):
    """Base task for import operations with automatic retry."""
    autoretry_for = (ConnectionError, TimeoutError, OSError)
    retry_backoff = True
    retry_backoff_max = 60
    retry_jitter = True
    max_retries = 2
    soft_time_limit = 600  # 10 minutes soft limit
    time_limit = 900  # 15 minutes hard limit


@shared_task(bind=True, base=RetryableImportTask)
def process_import_task(self, rows: List[Dict[str, Any]], model_name: str, mode: str,
                        tenant_id: str, user_id: int, serializer_path: str):
    """
    Process CSV/Excel import in background.

    Args:
        rows: List of row dicts from parsed file
        model_name: Target model name
        mode: Import mode ('create', 'update', 'upsert')
        tenant_id: Tenant UUID string
        user_id: User ID who initiated import
        serializer_path: Dotted path to serializer class

    Returns:
        dict with summary and results
    """
    import importlib
    from django.db import transaction
    from Tracker.models import Tenant, User

    logger.info(f"Starting background import: {model_name}, {len(rows)} rows, mode={mode}")

    # Load tenant and user
    try:
        tenant = Tenant.objects.get(id=tenant_id) if tenant_id else None
        user = User.objects.get(id=user_id)
    except (Tenant.DoesNotExist, User.DoesNotExist) as e:
        logger.error(f"Import task failed: {e}")
        return {'status': 'error', 'message': str(e)}

    # Load serializer class
    try:
        module_path, class_name = serializer_path.rsplit('.', 1)
        module = importlib.import_module(module_path)
        serializer_class = getattr(module, class_name)
    except (ValueError, ImportError, AttributeError) as e:
        logger.error(f"Failed to load serializer {serializer_path}: {e}")
        return {'status': 'error', 'message': f'Invalid serializer: {serializer_path}'}

    # Run with tenant context for RLS enforcement
    with tenant_context(tenant_id):
        # Process rows
        results = []
        created = 0
        updated = 0
        errors = 0

        # Update progress every N rows
        progress_interval = max(1, len(rows) // 20)  # ~5% increments

        with transaction.atomic():
            for i, row in enumerate(rows, start=1):
                serializer = serializer_class(
                    data=row,
                    tenant=tenant,
                    user=user,
                    mode=mode,
                )

                try:
                    instance, was_created, warnings = serializer.import_row(row)
                    if was_created:
                        created += 1
                        results.append({'row': i, 'status': 'created', 'id': str(instance.id)})
                    else:
                        updated += 1
                        results.append({'row': i, 'status': 'updated', 'id': str(instance.id)})

                    if warnings:
                        results[-1]['warnings'] = warnings

                except Exception as e:
                    errors += 1
                    error_detail = e.detail if hasattr(e, 'detail') else str(e)
                    results.append({'row': i, 'status': 'error', 'errors': error_detail})

                # Update task state for progress tracking
                if i % progress_interval == 0 or i == len(rows):
                    self.update_state(
                        state='PROGRESS',
                        meta={
                            'current': i,
                            'total': len(rows),
                            'created': created,
                            'updated': updated,
                            'errors': errors,
                        }
                    )

        logger.info(f"Import complete: {created} created, {updated} updated, {errors} errors")

        return {
            'status': 'completed',
            'summary': {
                'total': len(rows),
                'created': created,
                'updated': updated,
                'errors': errors,
            },
            'results': results,
        }


@shared_task(bind=True, base=RetryablePdfTask)
def generate_and_email_report(self, user_id: int, user_email: str, report_type: str, params: dict, tenant_id: str = None):
    """
    Generate a PDF report using Playwright and email it to the user.

    This task:
    1. Creates a GeneratedReport record for audit trail
    2. Uses PdfGenerator to render the frontend page and convert to PDF
    3. Saves the PDF as a Document (part of DMS)
    4. Emails the PDF to the user
    5. Updates the GeneratedReport record with status

    Args:
        user_id: ID of requesting user (for audit trail)
        user_email: Email address to send report to
        report_type: One of "spc", "capa", "quality_report", etc.
        params: Dict of parameters specific to report type
        tenant_id: Tenant UUID string for RLS context

    Returns:
        dict with status, report_id, and info
    """
    from django.core.mail import EmailMessage
    from django.core.files.base import ContentFile
    from django.utils import timezone
    from django.db import transaction
    from Tracker.models import User, Documents, GeneratedReport
    from Tracker.services.pdf_generator import PdfGenerator

    logger.info(f"Starting PDF generation: {report_type} for user {user_id}")

    # Get user (to extract tenant if not provided)
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {'status': 'error', 'message': 'User not found'}

    # Resolve tenant context
    if not tenant_id:
        tenant_id = getattr(user, 'tenant_id', None)

    # Run with tenant context for RLS enforcement
    with tenant_context(tenant_id):
        # Create GeneratedReport record (audit trail)
        report = GeneratedReport.objects.create(
            report_type=report_type,
            generated_by=user,
            parameters=params,
            status=GeneratedReport.ReportStatus.PENDING
        )

        try:
            # Generate PDF
            generator = PdfGenerator()
            pdf_bytes = generator.generate(report_type, params)
            filename = generator.get_filename(report_type, params)
            title = generator.get_title(report_type)

            logger.info(f"Generated PDF: {filename} ({len(pdf_bytes)} bytes)")

            # Create Document record in DMS
            with transaction.atomic():
                document = Documents.objects.create(
                    file_name=filename,
                    classification='INTERNAL',  # Use ClassificationLevel enum value
                    uploaded_by=user,
                    status='RELEASED',  # Generated reports are auto-released
                )
                # Save the file to the document
                document.file.save(filename, ContentFile(pdf_bytes))
                document.save()

                # Update GeneratedReport with document reference
                report.mark_completed(document)

            logger.info(f"Saved document {document.id} for report {report.id}")

            # Email the PDF to user
            email = EmailMessage(
                subject=f"Your {title} is Ready",
                body=f"Please find your requested {title.lower()} attached.\n\n"
                     f"Report Type: {report_type}\n"
                     f"Generated: {timezone.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                     f"This report has been saved to your documents for future reference.",
                to=[user_email]
            )
            email.attach(filename, pdf_bytes, "application/pdf")
            email.send()

            # Update report with email info
            report.mark_emailed(user_email)

            logger.info(f"Successfully emailed {report_type} report to {user_email}")

            return {
                'status': 'success',
                'report_id': report.id,
                'document_id': document.id,
                'filename': filename,
                'file_size': len(pdf_bytes),
                'emailed_to': user_email
            }

        except Exception as e:
            logger.error(f"Failed to generate PDF report: {e}")
            report.mark_failed(str(e))
            return {
                'status': 'error',
                'report_id': report.id,
                'message': str(e)
            }
