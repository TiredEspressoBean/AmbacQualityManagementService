import logging
from pathlib import Path

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .models import (
    QualityReports, QuarantineDisposition, ThreeDModel, Documents,
    ApprovalRequest, ApprovalResponse,
    CAPA, CapaTasks, CapaVerification,
    Tenant,
    WorkOrder, WorkOrderStatus,
)

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(post_save, sender=QualityReports)
def auto_create_disposition(sender, instance, created, **kwargs):
    """Create disposition when QualityReport fails"""
    if instance.status == 'FAIL':
        # Check if disposition already exists for this quality report
        if not instance.dispositions.filter(current_state__in=['OPEN', 'IN_PROGRESS']).exists():
            # Find a QA user to assign to (or use the operator)
            qa_user = User.objects.filter(groups__name='QA').first()
            assigned_user = qa_user or instance.operators.first() or instance.detected_by

            if assigned_user:
                # Calculate rework attempt number for this step
                existing_rework_count = 0
                if instance.part and instance.step:
                    existing_rework_count = QuarantineDisposition.objects.filter(
                        part=instance.part,
                        step=instance.step,
                        disposition_type='REWORK'
                    ).count()

                disposition = QuarantineDisposition.objects.create(
                    assigned_to=assigned_user,
                    part=instance.part,
                    step=instance.step,  # Link to the step where failure occurred
                    rework_attempt_at_step=existing_rework_count + 1,
                    description=f"Auto-created for failed quality report: {instance.description or 'No description'}"
                )
                disposition.quality_reports.add(instance)


@receiver(post_save, sender=ThreeDModel)
def queue_3d_model_processing(sender, instance, created, **kwargs):
    """
    Queue uploaded 3D model for async processing.

    Supports multiple formats:
    - CAD: STEP (.step, .stp) - converted via cascadio
    - Mesh: STL, OBJ, PLY - optimized via trimesh
    - glTF: GLB, glTF - optimized if needed

    Processing runs asynchronously in Celery to avoid blocking requests.
    """
    if not created or not instance.file:
        return

    from Tracker.services.model_processor import ACCEPTED_EXTENSIONS
    from Tracker.models import ModelProcessingStatus

    file_ext = Path(instance.file.name).suffix.lower()

    if file_ext in ACCEPTED_EXTENSIONS:
        # Queue for async processing — dispatch after commit so a rollback
        # of the signaling save doesn't leave an orphan task.
        from .tasks import process_3d_model
        model_id = str(instance.id)
        transaction.on_commit(lambda: process_3d_model.delay(model_id))
        logger.info(f"Queued 3D model {instance.id} ({instance.name}) for processing")
    else:
        # Unsupported format - mark as failed immediately
        instance.processing_status = ModelProcessingStatus.FAILED
        instance.processing_error = (
            f"Unsupported format: {file_ext}. "
            f"Supported: {', '.join(ACCEPTED_EXTENSIONS)}"
        )
        instance.save(update_fields=['processing_status', 'processing_error'])
        logger.warning(f"Unsupported 3D model format {file_ext} for {instance.id}")


@receiver(post_save, sender=Documents)
def auto_embed_document(sender, instance, created, **kwargs):
    """
    Automatically trigger async embedding when a document is saved with ai_readable=True.

    This signal handles:
    - New document uploads
    - File updates on existing documents
    - Documents marked as ai_readable after creation
    """
    from django.conf import settings

    # Only embed if AI embedding is enabled globally
    if not settings.AI_EMBED_ENABLED:
        return

    # Only embed if document is marked as ai_readable and not archived
    if not instance.ai_readable or instance.archived:
        return

    # Trigger async embedding — wrap in on_commit so the dispatch doesn't
    # fire if the saving transaction rolls back.
    transaction.on_commit(instance.embed_async)


@receiver(post_save, sender=ApprovalResponse)
def update_approval_status_on_response(sender, instance, created, **kwargs):
    """Update approval request status when response is submitted"""
    if created:
        approval_request = instance.approval_request
        approval_request.update_status()

        # For sequential approvals, notify the next approver if still pending
        from .models import SequenceTypes, ApprovalDecision
        if (approval_request.sequence_type == SequenceTypes.SEQUENTIAL and
            instance.decision == ApprovalDecision.APPROVED and
            approval_request.status == 'PENDING'):
            # Notify the next approver in sequence
            approval_request.notify_approvers()


@receiver(post_save, sender=ApprovalRequest)
def notify_requester_on_decision(sender, instance, **kwargs):
    """Send notification to requester when approval is completed (approved/rejected)"""
    # Check if status changed (using _old_status set by model's save method)
    old_status = getattr(instance, '_old_status', None)
    if old_status and old_status != instance.status and instance.status in ['APPROVED', 'REJECTED']:
        # Notify requester of decision
        instance.notify_status_change(instance.status)


@receiver(post_save, sender=ApprovalRequest)
def handle_approval_decision(sender, instance, **kwargs):
    """Cascade approval outcome to the content object when status changes."""
    old_status = getattr(instance, '_old_status', None)
    if not old_status or old_status == instance.status:
        return
    if instance.status not in ['APPROVED', 'REJECTED']:
        return

    from Tracker.services.core.approval import apply_approval_decision_to_content_object
    apply_approval_decision_to_content_object(instance, instance.status)


@receiver(post_save, sender=CAPA)
def create_initial_containment_task(sender, instance, created, **kwargs):
    """Auto-create initial containment task when CAPA is created"""
    if created and instance.immediate_action:
        from .models import CapaTasks, CapaTaskType
        # task_number auto-generated by CapaTasks.save() with race condition protection
        CapaTasks.objects.create(
            capa=instance,
            tenant=instance.tenant,  # Ensure tenant is set for proper sequence generation
            task_type=CapaTaskType.CONTAINMENT,
            description=f"Containment: {instance.immediate_action}",
            assigned_to=instance.assigned_to,
            due_date=instance.initiated_date
        )


@receiver(post_save, sender=CAPA)
def notify_assignment(sender, instance, created, **kwargs):
    """Notify assigned user when CAPA is created or reassigned"""
    if created or (instance.assigned_to and 'assigned_to' in getattr(instance, '_changed_fields', [])):
        from .tasks import send_capa_assignment_notification
        capa_id = instance.id
        transaction.on_commit(lambda: send_capa_assignment_notification.delay(capa_id))


@receiver(post_save, sender=CAPA)
def trigger_approval_for_critical_capa(sender, instance, created, **kwargs):
    """Auto-create approval request for Critical/Major CAPAs on creation."""
    if not created:
        return

    from .models import CapaSeverity
    if instance.severity not in [CapaSeverity.CRITICAL, CapaSeverity.MAJOR]:
        return

    from Tracker.services.qms.capa import auto_request_capa_approval
    auto_request_capa_approval(instance)


@receiver(post_save, sender=CapaTasks)
def notify_task_assignment(sender, instance, created, **kwargs):
    """Notify assignee when task is created or reassigned"""
    if created or (instance.assigned_to and 'assigned_to' in getattr(instance, '_changed_fields', [])):
        from .tasks import send_capa_task_assignment_notification
        task_id = instance.id
        transaction.on_commit(lambda: send_capa_task_assignment_notification.delay(task_id))


@receiver(post_save, sender=CapaTasks)
def check_capa_ready_for_verification(sender, instance, **kwargs):
    """Check if CAPA can move to verification after task completion"""
    if instance.status == 'COMPLETED':
        capa = instance.capa
        if capa.all_tasks_completed() and capa.rca_complete():
            from .tasks import send_capa_ready_for_verification_notification
            capa_id = capa.id
            transaction.on_commit(lambda: send_capa_ready_for_verification_notification.delay(capa_id))


@receiver(post_save, sender=CapaVerification)
def handle_verification_outcome(sender, instance, **kwargs):
    """Handle actions based on verification result"""
    if instance.effectiveness_result == 'CONFIRMED':
        # Notify that CAPA is ready to close
        from .tasks import send_capa_verification_complete_notification
        capa_id = instance.capa.id
        transaction.on_commit(lambda: send_capa_verification_complete_notification.delay(capa_id))
    elif instance.effectiveness_result == 'NOT_EFFECTIVE':
        # Notification already handled in verify_effectiveness method
        # RCA review status already set
        pass


# =============================================================================
# DOCUMENT CHUNK CLEANUP
# =============================================================================

@receiver(post_save, sender=Documents)
def cleanup_chunks_on_archive(sender, instance, **kwargs):
    """
    Clean up DocChunks when a Document is soft-deleted (archived).

    DocChunk uses CASCADE on hard delete, but SecureModel.delete() does soft delete.
    Without this signal, chunks would accumulate forever for archived documents.
    """
    if instance.archived:
        from .models.dms import DocChunk
        deleted_count, _ = DocChunk.objects.filter(doc=instance).delete()
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} chunks for archived document {instance.id}")


# =============================================================================
# TENANT GROUP SEEDING
# =============================================================================

@receiver(post_save, sender=Tenant)
def seed_tenant_defaults(sender, instance, created, **kwargs):
    """
    Seed default groups and reference data when a new Tenant is created.

    Each tenant gets:
    - Default groups from GroupSeeder (using GROUP_PRESETS from presets.py)
    - Default document types
    - Default approval templates
    """
    if created:
        from .groups import GroupSeeder
        from .services.defaults_service import seed_reference_data_for_tenant
        from .utils.tenant_context import tenant_context

        # Run seeding inside the new tenant's context. Otherwise the
        # SecureManager auto-scope compounds filters to `tenant=instance
        # AND tenant=<caller's_ContextVar>` — either raising
        # TenantContextRequired (when the caller has no tenant) or
        # silently returning nothing (when the caller's tenant differs
        # from the one being created).
        with tenant_context(instance.id):
            GroupSeeder.seed_for_tenant(instance)
            seed_reference_data_for_tenant(instance)


# =============================================================================
# PERMISSION CACHE INVALIDATION
# =============================================================================

from django.db.models.signals import m2m_changed, post_delete


@receiver(m2m_changed, sender='Tracker.TenantGroup_permissions')
def clear_group_permission_cache(sender, instance, action, **kwargs):
    """
    Clear permission cache for all users in a group when its permissions change.

    Triggered when permissions are added/removed from a TenantGroup.
    """
    if action in ('post_add', 'post_remove', 'post_clear'):
        # instance is the TenantGroup
        for role in instance.role_assignments.select_related('user'):
            role.user.clear_permission_cache(instance.tenant)


@receiver(post_save, sender='Tracker.UserRole')
def clear_user_permission_cache_on_role_save(sender, instance, **kwargs):
    """Clear permission cache when user's role is created or updated."""
    tenant = instance.group.tenant
    instance.user.clear_permission_cache(tenant)


@receiver(post_delete, sender='Tracker.UserRole')
def clear_user_permission_cache_on_role_delete(sender, instance, **kwargs):
    """Clear permission cache when user's role is deleted."""
    tenant = instance.group.tenant
    instance.user.clear_permission_cache(tenant)


# =============================================================================
# CALIBRATION SIGNALS
# =============================================================================

@receiver(post_save, sender='Tracker.CalibrationRecord')
def handle_calibration_result(sender, instance, created, **kwargs):
    """Update equipment status based on calibration result."""
    from Tracker.services.mes.work_order import apply_calibration_result_to_equipment
    apply_calibration_result_to_equipment(instance)


# =============================================================================
# WORK ORDER COMPLETION CASCADES
# =============================================================================

@receiver(post_save, sender=WorkOrder)
def cascade_order_status_on_workorder_complete(sender, instance, **kwargs):
    """Cascade Order status when all WorkOrders reach terminal status."""
    if instance.workorder_status not in [WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED]:
        return

    from Tracker.services.mes.work_order import cascade_order_status
    cascade_order_status(instance)


@receiver(post_save, sender=WorkOrder)
def cascade_schedule_slots_on_workorder_complete(sender, instance, **kwargs):
    """Mark open ScheduleSlots COMPLETED when a WorkOrder completes."""
    if instance.workorder_status != WorkOrderStatus.COMPLETED:
        return

    from Tracker.services.mes.work_order import cascade_schedule_slots
    cascade_schedule_slots(instance)