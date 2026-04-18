"""
PDF report generation Celery tasks.

Split out from Tracker/tasks.py to keep report pipeline code colocated.
"""
import logging

from celery import shared_task, Task

from Tracker.utils.tenant_context import tenant_context

logger = logging.getLogger(__name__)


class RetryableTypstTask(Task):
    """
    Base task for Typst PDF generation.

    Autoretries only on **transient** errors — timeouts, OS-level
    failures, memory pressure. Template compile errors (TypstError,
    wrapped as RuntimeError by our generator service) are permanent
    bugs; retrying them wastes worker capacity and delays the user
    seeing the real failure.

    Timeouts:
        soft_time_limit = 30s — SoftTimeLimitExceeded raised in task
                                (allows cleanup + marking report failed)
        time_limit      = 60s — SIGKILL if task still running
                                (process-level memory is reclaimed)

    These match the values exposed on ReportAdapter; adjust both
    together if a specific report needs more time (override on the
    adapter, not here).
    """
    autoretry_for = (ConnectionError, TimeoutError, OSError, MemoryError)
    retry_backoff = True
    retry_backoff_max = 300  # Max 5 minutes between retries
    retry_jitter = True
    max_retries = 3
    soft_time_limit = 30
    time_limit = 60


@shared_task(bind=True, base=RetryableTypstTask)
def generate_and_email_report(self, user_id: int, user_email: str, report_type: str, params: dict, tenant_id: str = None):
    """
    Generate a Typst PDF report and email it to the user.

    This task:
    1. Creates a GeneratedReport record for audit trail
    2. Routes through PdfGenerator → adapter → Typst compile
    3. Saves the PDF as a Document (DMS)
    4. Emails the PDF to the user
    5. Updates the GeneratedReport record with status

    Args:
        user_id: ID of requesting user (for audit trail + tenant scoping)
        user_email: Email address to send report to
        report_type: Registry key (e.g. "cert_of_conformance")
        params: Dict of parameters specific to report_type; validated
            by the adapter's param_serializer_class before compile
        tenant_id: Tenant UUID for RLS context. Auto-derived from user
            if None.

    Returns:
        dict with status, report_id, and info
    """
    from django.core.mail import EmailMessage
    from django.core.files.base import ContentFile
    from django.utils import timezone
    from django.db import transaction
    from Tracker.models import User, Documents, GeneratedReport
    from Tracker.reports.services.pdf_generator import PdfGenerator

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
            # Generate PDF — pass user so tenant-scoped adapters can
            # validate IDs and scope ORM queries correctly.
            generator = PdfGenerator()
            pdf_bytes = generator.generate(report_type, params, user=user)
            filename = generator.get_filename(report_type, params)
            title = generator.get_title(report_type)

            logger.info(f"Generated PDF: {filename} ({len(pdf_bytes)} bytes)")

            # Create Document record in DMS
            with transaction.atomic():
                # tenant-safe: enclosing `with tenant_context(tenant_id)` sets RLS context
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
