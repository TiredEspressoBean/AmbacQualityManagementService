import logging
from pathlib import Path

from django.db import transaction
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .signals_versioning import revision_created

from .models import (
    QualityReports, QuarantineDisposition, ThreeDModel, Documents,
    ApprovalRequest, ApprovalResponse,
    CAPA, CapaTasks, CapaVerification,
    Equipments,
    Tenant,
    UserRole,
    WorkOrder, WorkOrderStatus,
)

logger = logging.getLogger(__name__)
User = get_user_model()


# --- TenantMembership sync -------------------------------------------------
# Keep the per-tenant membership table in step with the two ways a user gains
# tenant access, regardless of which code path created them (allauth adapters,
# serializers, management commands, seeds): their home `User.tenant`, and any
# `UserRole` grant in a tenant. ensure_membership is idempotent and never
# reactivates a suspended row, so this only ever *adds* missing memberships.

@receiver(post_save, sender=User)
def ensure_home_membership(sender, instance, **kwargs):
    if instance.tenant_id:
        from Tracker.services.core.tenant_membership import ensure_membership
        ensure_membership(instance, instance.tenant, is_home=True)


@receiver(post_save, sender=UserRole)
def ensure_membership_for_role(sender, instance, created, **kwargs):
    if not created:
        return
    from Tracker.services.core.tenant_membership import ensure_membership
    tenant = instance.group.tenant
    if tenant is not None:
        ensure_membership(instance.user, tenant)


@receiver(post_save, sender=QualityReports)
def auto_create_disposition(sender, instance, created, **kwargs):
    """Create disposition when QualityReport fails"""
    if instance.status == 'FAIL':
        # Receiving-inspection failures (material_lot QRs) get a *populated* disposition
        # from the reject flow (RejectDispositionDialog → QuarantineDispositions create,
        # with type/severity/qty). Auto-creating a bare one here just duplicates it — the
        # confirmed §15 defect. So auto-create only for in-process (part) failures.
        if instance.material_lot_id:
            return
        # Batch-cycle failures span the whole load, not one part. Contain the
        # load and open a single batch-linked disposition via the service
        # (cross-aggregate write → service, not this signal). Without this the
        # part-branch below would mint an orphaned part=None disposition and
        # leave the suspect load uncontained.
        if instance.batch_execution_id:
            from Tracker.services.qms.batch_disposition import contain_failed_batch
            contain_failed_batch(instance)
            return
        # Auto-create at most ONE disposition per report. The guard used to
        # scope to current_state IN (OPEN, IN_PROGRESS), which re-fired on any
        # later save of a still-FAIL QR whose disposition had since been CLOSED
        # — resurrecting an orphan bare NCR (the double-disposition seen on some
        # exhibits). QuarantineDisposition has no CANCELLED state, so there's no
        # "voided, re-open a fresh one" case to preserve: if this report already
        # produced a disposition (any state), don't make another. A genuinely
        # new failure is a NEW QR with its own (empty) `dispositions`, so it
        # still gets one; and a human can add further dispositions deliberately
        # (QR->disposition is legitimately 1:many).
        if not instance.dispositions.exists():
            # Find a QA user to assign to (or use the operator)
            qa_user = User.objects.filter(
                user_roles__group__name__in=['QA Manager', 'QA Inspector'],
                user_roles__group__tenant=instance.tenant,
            ).first()
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
    """Emit `capa.assigned` when a CAPA is created with an assignee or
    reassigned to a new user.

    Phase 6b: emit-based notification with `recipient_user_ids=[assignee.id]`.
    A tenant rule with `recipient_strategy='from_payload'` routes to the
    actual assignee. Admins can author union-strategy rules to CC
    supervisors on assignments.

    Reassignment detection uses `_old_assigned_to_id` set by `CAPA.save()` —
    not the `_changed_fields` predicate that an earlier version relied on
    (no writer populates that attribute in production).
    """
    if not instance.assigned_to_id:
        return
    if not created:
        old = getattr(instance, '_old_assigned_to_id', None)
        if old == instance.assigned_to_id:
            return  # Same assignee — no reassignment, no notification.

    from Tracker.services.core.notifications import emit
    from Tracker.services.qms.events import CapaAssignedPayload

    capa = instance
    payload = CapaAssignedPayload(
        id=str(capa.id),
        tenant_id=str(capa.tenant_id) if capa.tenant_id else '',
        capa_id=str(capa.id),
        capa_number=capa.capa_number or '',
        capa_type=capa.capa_type or '',
        capa_type_display=capa.get_capa_type_display() if capa.capa_type else '',
        severity=capa.severity or '',
        severity_display=capa.get_severity_display() if capa.severity else '',
        status=capa.status or '',
        problem_statement=capa.problem_statement or '',
        assigned_to_id=capa.assigned_to_id,
        assigned_to_name=(
            capa.assigned_to.get_full_name() or capa.assigned_to.username
            if capa.assigned_to else ''
        ),
        assigned_to_email=capa.assigned_to.email if capa.assigned_to else '',
        initiated_by_id=capa.initiated_by_id,
        initiated_by_name=(
            capa.initiated_by.get_full_name() or capa.initiated_by.username
            if capa.initiated_by else ''
        ),
        due_date=capa.due_date,
        is_reassignment=not created,
        recipient_user_ids=[capa.assigned_to_id],
    )

    tenant = capa.tenant
    transaction.on_commit(
        lambda t=tenant, p=payload: emit('capa.assigned', tenant=t, payload=p)
    )


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
    """Emit `capa.ready_for_verification` when a CAPA's tasks + RCA complete.

    Routed to the QA verifier group via the NotificationRule starter rule
    (replaces the legacy hardcoded-email task)."""
    if instance.status != 'COMPLETED':
        return

    capa = instance.capa
    if not (capa.all_tasks_completed() and capa.rca_complete()):
        return

    from Tracker.services.core.notifications import emit
    from Tracker.services.qms.events import CapaReadyForVerificationPayload

    payload = CapaReadyForVerificationPayload(
        id=str(capa.id),
        tenant_id=str(capa.tenant_id) if capa.tenant_id else '',
        capa_id=str(capa.id),
        capa_number=capa.capa_number or '',
        capa_type=capa.capa_type or '',
        capa_type_display=capa.get_capa_type_display() if capa.capa_type else '',
        severity=capa.severity or '',
        severity_display=capa.get_severity_display() if capa.severity else '',
        status=capa.status or '',
        problem_statement=capa.problem_statement or '',
        initiated_by_id=capa.initiated_by_id,
        initiated_by_name=(
            capa.initiated_by.get_full_name() or capa.initiated_by.username
            if capa.initiated_by else ''
        ),
    )
    tenant = capa.tenant
    transaction.on_commit(
        lambda t=tenant, p=payload: emit(
            'capa.ready_for_verification', tenant=t, payload=p,
            idempotency_key=f"capa.ready_for_verification:capa:{capa.id}",
        )
    )


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


@receiver(revision_created, sender=Documents)
def carry_document_links_forward(sender, old_version, new_version, **kwargs):
    """Carry a document's secondary DocumentLinks onto its new version.

    The base `create_new_version` copies concrete fields (so the primary GFK
    carries forward), but reverse-relation links are not concrete fields.
    Cloning them here keeps a re-versioned document's additional associations
    consistent with how its primary attachment already behaves. (Composite-
    parent clones go through `clone_current_documents`, not
    `create_new_version`, so they are handled there and never double-cloned.)
    """
    from .services.core.documents import clone_document_links
    clone_document_links(source_document=old_version, target_document=new_version)


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
    - Default notification rules (starter set; admins customize from there)
    """
    if created:
        from django.conf import settings
        from .groups import GroupSeeder
        from .services.core.notifications.system_rules import (
            seed_system_rules_for_tenant,
        )
        from .services.defaults_service import seed_reference_data_for_tenant
        from .utils.tenant_context import tenant_context

        # Run seeding inside the new tenant's context. Otherwise the
        # SecureManager auto-scope compounds filters to `tenant=instance
        # AND tenant=<caller's_ContextVar>` — either raising
        # TenantContextRequired (when the caller has no tenant) or
        # silently returning nothing (when the caller's tenant differs
        # from the one being created).
        with tenant_context(instance.id):
            # Groups always seed — RBAC/permission tests depend on them.
            GroupSeeder.seed_for_tenant(instance)

            # Reference data (document types, approval templates) and the
            # starter notification rules are the optional, heaviest part of
            # tenant creation. Gated behind SEED_TENANT_REFERENCE_DATA so the
            # test runner can skip it (most tests assume an empty state in
            # setUp and would choke on the starter set). Tests that assert on
            # this data call the seed_* helpers directly. Notification rules
            # go last — they reference groups seeded by GroupSeeder.
            if settings.SEED_TENANT_REFERENCE_DATA:
                seed_reference_data_for_tenant(instance)
                seed_system_rules_for_tenant(instance)


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


# =============================================================================
# REACTIVE RE-PLAN — mark the active schedule stale on disruptive change
# =============================================================================
# `ScheduleResult.is_stale` is otherwise only set when a fresh solve supersedes
# the active plan. These receivers flip it reactively when the world changes
# under the live plan (new/cancelled demand, a part leaving the flow, lost
# capacity) so the planner UI can surface "schedule out of date — re-solve".
# This is a *hint*, not an auto-solve (the periodic auto-solve beat is a policy
# choice, Phase B). Deliberately NOT tripped by routine step advances: an actuals
# drift on every advance would leave the flag permanently on and meaningless —
# reconciling actuals against the plan is the auto-solve beat's job.

# Part statuses that meaningfully change the schedulable set (a part leaving the
# flow, or being held out of it).
_DISRUPTIVE_PART_STATUSES = frozenset({'SCRAPPED', 'CANCELLED', 'QUARANTINED'})


def _mark_active_schedule_stale(tenant_id) -> None:
    """Flip the tenant's active, committed schedule to stale.

    Delegates to the scheduling service so non-signal paths trip the same flag —
    notably the bulk `.update()` / `bulk_update` quarantines in
    `services/qms/{quality_gate,batch_disposition}`, which bypass the `Parts`
    disruption signal below."""
    from Tracker.services.scheduling.staleness import mark_active_schedule_stale
    mark_active_schedule_stale(tenant_id)


def _touched(update_fields, tracked: set) -> bool:
    """True when a save may have changed a tracked field: either it was a full
    save (update_fields is None) or the passed update_fields intersects `tracked`."""
    return update_fields is None or bool(set(update_fields) & tracked)


@receiver(post_save, sender=WorkOrder)
def mark_schedule_stale_on_workorder_change(sender, instance, created, update_fields, **kwargs):
    """New demand, or a priority/status change on existing demand, invalidates the
    live plan."""
    if created or _touched(update_fields, {'workorder_status', 'priority'}):
        _mark_active_schedule_stale(instance.tenant_id)


@receiver(post_delete, sender=WorkOrder)
def mark_schedule_stale_on_workorder_delete(sender, instance, **kwargs):
    """Demand removed — the plan no longer matches the order book."""
    _mark_active_schedule_stale(instance.tenant_id)


@receiver(post_save, sender='Tracker.Parts')
def mark_schedule_stale_on_part_disruption(sender, instance, created, update_fields, **kwargs):
    """A part leaving the flow (scrap/cancel/quarantine) or being carved into its
    own lot (split) changes what the solver must cover. Gated on the disruptive
    value AND the relevant fields being touched, so routine advances (which move
    part_status to IN_PROGRESS/COMPLETED, and mostly run via bulk_update anyway)
    don't churn the flag."""
    disruptive_value = (
        instance.part_status in _DISRUPTIVE_PART_STATUSES or bool(instance.split_from_lot)
    )
    if disruptive_value and _touched(update_fields, {'part_status', 'split_from_lot'}):
        _mark_active_schedule_stale(instance.tenant_id)


@receiver(post_save, sender='Tracker.DowntimeEvent')
def mark_schedule_stale_on_downtime(sender, instance, **kwargs):
    """Lost (or edited) capacity window on a machine/work center invalidates the
    machine-layer plan."""
    _mark_active_schedule_stale(instance.tenant_id)


# Capacity / timing master data: not part/WO/downtime events, but they change
# the solver's inputs (shift calendars, plant closures, step timings, machine
# eligibility, changeover matrix, tooling capacity). Edits are infrequent and
# capacity-relevant, so the unconditional group flags on every save/delete;
# Equipments and MaterialLot are higher-churn, so they gate on the fields that
# actually affect the solve.

@receiver(post_save, sender='Tracker.Shift')
@receiver(post_delete, sender='Tracker.Shift')
@receiver(post_save, sender='Tracker.PlantCalendarException')
@receiver(post_delete, sender='Tracker.PlantCalendarException')
@receiver(post_save, sender='Tracker.StepTiming')
@receiver(post_delete, sender='Tracker.StepTiming')
@receiver(post_save, sender='Tracker.StepEquipmentAffinity')
@receiver(post_delete, sender='Tracker.StepEquipmentAffinity')
@receiver(post_save, sender='Tracker.WorkCenterChangeover')
@receiver(post_delete, sender='Tracker.WorkCenterChangeover')
@receiver(post_save, sender='Tracker.Fixture')
@receiver(post_delete, sender='Tracker.Fixture')
@receiver(post_save, sender='Tracker.LaborCalendarBlock')
@receiver(post_delete, sender='Tracker.LaborCalendarBlock')
@receiver(post_save, sender='Tracker.OvertimeWindow')
@receiver(post_delete, sender='Tracker.OvertimeWindow')
def mark_schedule_stale_on_capacity_master_change(sender, instance, **kwargs):
    """A calendar / timing / eligibility / changeover / tooling master-data edit
    changed the solver's inputs — the live plan may no longer be optimal or even
    feasible, so flag it for re-solve."""
    _mark_active_schedule_stale(instance.tenant_id)


_EQUIP_CAPACITY_FIELDS = {
    'status', 'is_schedulable', 'runs_unattended', 'calibration_interval_days',
}


@receiver(post_save, sender='Tracker.Equipments')
def mark_schedule_stale_on_equipment_change(sender, instance, created, update_fields, **kwargs):
    """A machine's schedulability, operational status, lights-out capability, or
    calibration window changing alters available capacity. Trivial edits
    (name/location) don't, so gate on the capacity fields."""
    if created or _touched(update_fields, _EQUIP_CAPACITY_FIELDS):
        _mark_active_schedule_stale(instance.tenant_id)


@receiver(m2m_changed, sender=Equipments.operating_shifts.through)
def mark_schedule_stale_on_equipment_shifts_change(sender, instance, action, **kwargs):
    """Per-machine operating calendar (E5) changed — capacity windows moved."""
    if action in ('post_add', 'post_remove', 'post_clear'):
        # `instance` is whichever side the M2M was edited from; both carry tenant_id.
        _mark_active_schedule_stale(getattr(instance, 'tenant_id', None))


# Not quantity_remaining: it drops on every partial consumption (routine
# execution), which would keep the flag permanently on. A full consumption flips
# `status` to CONSUMED, which still fires; new receipts fire via `created`.
_MATLOT_GATE_FIELDS = {'status', 'promised_date'}


@receiver(post_save, sender='Tracker.MaterialLot')
def mark_schedule_stale_on_material_lot_change(sender, instance, created, update_fields, **kwargs):
    """A new receipt, a status change (accepted / rejected / quarantined /
    consumed), or a moved promised date changes what the material gate can net,
    freeing or blocking material-gated starts."""
    if created or _touched(update_fields, _MATLOT_GATE_FIELDS):
        _mark_active_schedule_stale(instance.tenant_id)


@receiver(post_save, sender='Tracker.StepExecution')
def capture_execution_actuals(sender, instance, **kwargs):
    """Stamp the live schedule's task with the real start/end when a part/core
    enters or exits a step (planned-vs-actual capture). Deliberately does NOT mark
    the schedule stale — routine advances are not a re-solve trigger, and the
    write is a bulk update that bypasses ScheduledTask signals."""
    from Tracker.services.scheduling.actuals import record_execution_actuals
    record_execution_actuals(instance)