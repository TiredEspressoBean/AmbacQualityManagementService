"""
Processes aggregate services.

State-machine and duplication operations for the Processes model. Model
methods delegate here so status-gate checks and cross-aggregate writes
live in one place.
"""
from __future__ import annotations

from django.utils import timezone

from Tracker.models import (
    ApprovalRequest,
    ApprovalTemplate,
    Processes,
    ProcessStep,
    ProcessStatus,
    StepEdge,
    Steps,
    StepExecution,
)
from Tracker.models.mes_lite import EdgeType


def approve_process(process: Processes, user=None) -> Processes:
    """Approve a draft or pending process for production use.

    Raises:
        ValueError: Process is not in DRAFT or PENDING_APPROVAL status.
        ValueError: Process has no steps defined.
    """
    if process.status not in (ProcessStatus.DRAFT, ProcessStatus.PENDING_APPROVAL):
        raise ValueError("Only draft or pending processes can be approved.")

    if process.process_steps.count() == 0:
        raise ValueError("Cannot approve process with no steps.")

    process.status = ProcessStatus.APPROVED
    process.approved_at = timezone.now()
    process.approved_by = user
    process.save()

    return process


def submit_process_for_approval(process: Processes, user) -> ApprovalRequest:
    """Submit a draft process for formal approval workflow.

    Transitions DRAFT → PENDING_APPROVAL and creates an ApprovalRequest
    using the tenant's PROCESS_APPROVAL template.

    Raises:
        ValueError: Process is not DRAFT, has no steps, or template not found.
    """
    if process.status != ProcessStatus.DRAFT:
        raise ValueError("Only draft processes can be submitted for approval.")

    if process.process_steps.count() == 0:
        raise ValueError("Cannot submit process with no steps for approval.")

    try:
        template = ApprovalTemplate.objects.get(
            approval_type='PROCESS_APPROVAL',
            tenant=process.tenant,
        )
    except ApprovalTemplate.DoesNotExist:
        raise ValueError(
            "PROCESS_APPROVAL approval template not found. "
            "Please configure approval templates."
        )

    approval_request = ApprovalRequest.create_from_template(
        content_object=process,
        template=template,
        requested_by=user,
        reason=f"Process Approval: {process.name} (v{process.version})",
    )

    process.status = ProcessStatus.PENDING_APPROVAL
    process.save()

    return approval_request


def reject_process_approval(process: Processes) -> Processes:
    """Reject approval and return the process to DRAFT for editing.

    Raises:
        ValueError: Process is not in PENDING_APPROVAL status.
    """
    if process.status != ProcessStatus.PENDING_APPROVAL:
        raise ValueError("Only pending processes can be rejected.")

    process.status = ProcessStatus.DRAFT
    process.save()

    return process


def deprecate_process(process: Processes) -> Processes:
    """Mark an approved process as deprecated.

    Deprecated processes can still be used by existing work orders but
    will not appear in process selection for new work orders.

    Raises:
        ValueError: Process is not in APPROVED status.
    """
    if process.status not in (ProcessStatus.APPROVED,):
        raise ValueError("Only approved processes can be deprecated.")

    process.status = ProcessStatus.DEPRECATED
    process.save()

    return process


def create_new_process_version(
    process: Processes,
    *,
    user,
    change_description: str,
    **field_updates,
) -> Processes:
    """Create a new version of an APPROVED or DEPRECATED process.

    New version starts in DRAFT with approved_at/approved_by cleared.
    Scalar fields, tenant, and category carry forward via the base
    scalar-copy mechanism. ProcessStep and StepEdge junction rows are
    copied (same Step FKs — Steps are independently versioned and
    historically pinned). Documents attached via GenericRelation are
    copied as fresh Document rows pointing at the new version, sharing
    the same file storage blobs (no duplication). ApprovalRequest GFK
    children are NOT copied — v2 starts its own approval cycle.

    The `revision_created` signal fires via the base
    `SecureModel.create_new_version` call. Downstream subscribers
    (webhooks, analytics, AI summaries) hook there.

    Args:
        process: The current version to revise.
        user: User triggering the revision (forwarded to signal).
        change_description: Required human narrative of what changed
            and why. ISO 9001 4.4 / IATF 16949 8.5.6.1 compliance.
        **field_updates: Optional field overrides for the new DRAFT.

    Raises:
        ValueError: change_description blank; status not
            APPROVED/DEPRECATED; a DRAFT successor already exists;
            base-inherited (not current, archived).
    """
    from django.contrib.contenttypes.models import ContentType
    from django.db import transaction

    from Tracker.models import Documents

    if not change_description or not change_description.strip():
        raise ValueError(
            "change_description is required when creating a new Process "
            "version (ISO 9001 4.4 / IATF 16949 8.5.6.1 audit trail)."
        )

    if process.status not in (ProcessStatus.APPROVED, ProcessStatus.DEPRECATED):
        raise ValueError(
            f"Cannot create a new version from a process in status "
            f"{process.status}. Only APPROVED or DEPRECATED processes "
            f"can be revised; DRAFT is edited in place."
        )

    existing_draft = Processes.all_tenants.filter(
        previous_version=process,
        status=ProcessStatus.DRAFT,
    ).first()
    if existing_draft:
        raise ValueError(
            f"A draft revision (v{existing_draft.version}) already exists "
            f"for this process. Complete or discard it before creating "
            f"another revision."
        )

    with transaction.atomic():
        # Base handles: row lock, current-version guard, archived guard,
        # scalar field copy (tenant, category, part_type, is_remanufactured,
        # is_batch_process, name), version increment, previous_version link,
        # flipping old row's is_current_version, and firing the
        # revision_created signal post-commit.
        new_version = super(Processes, process).create_new_version(
            user=user,
            change_description=change_description,
            # Reset lifecycle state on the new draft.
            status=ProcessStatus.DRAFT,
            approved_at=None,
            approved_by=None,
            # `change_description` is also a concrete field on the model —
            # the base's field_updates mechanism stores it on the row.
            **field_updates,
        )

        for ps in process.process_steps.all():
            ProcessStep.objects.create(
                process=new_version,
                step=ps.step,
                order=ps.order,
                is_entry_point=ps.is_entry_point,
            )

        for edge in process.step_edges.all():
            StepEdge.objects.create(
                process=new_version,
                from_step=edge.from_step,
                to_step=edge.to_step,
                edge_type=edge.edge_type,
                condition_measurement=edge.condition_measurement,
                condition_operator=edge.condition_operator,
                condition_value=edge.condition_value,
            )

        _copy_documents_to_new_process_version(process, new_version)

    return new_version


def _copy_documents_to_new_process_version(
    source: Processes, new_version: Processes,
) -> None:
    """Copy Document GFK children from the source process to the new
    version. Same file storage blobs (no duplication); Document
    metadata rows are fresh — each version owns its own Document chain.

    Only current Documents are copied. Superseded Document revisions
    stay with the source version's history. The new Document rows start
    as DRAFT and will need re-approval in the new version's context.

    NOT copied: ApprovalRequest GFK children (v2 starts its own approval
    cycle — v1's approval records stay with v1).

    Pattern note: replicate this shape in other composite versioning
    services when they need to carry Documents forward. Extract to a
    shared helper at `services/core/documents.py` when the second
    composite needs it — not before.
    """
    from django.contrib.contenttypes.models import ContentType

    from Tracker.models import Documents

    process_ct = ContentType.objects.get_for_model(Processes)

    # tenant-safe: scoped via the Process content_type/object_id GFK
    source_docs = Documents.objects.filter(
        content_type=process_ct,
        object_id=source.pk,
        is_current_version=True,
    )

    # Fields reset on the new Document row — a fresh attachment for the
    # new Process version. Versioning / approval lifecycle / compliance
    # dates all restart.
    _reset_on_clone = {
        'id', 'created_at', 'updated_at',
        'archived', 'deleted_at',
        'version', 'previous_version', 'is_current_version',
        'object_id',  # rewired below
        'status', 'approved_by', 'approved_at', 'change_justification',
        'effective_date', 'review_date', 'obsolete_date', 'retention_until',
    }

    for doc in source_docs:
        clone_data = {
            f.name: getattr(doc, f.name)
            for f in Documents._meta.fields
            if f.name not in _reset_on_clone and not f.auto_created
        }
        clone_data['object_id'] = new_version.pk
        clone_data['status'] = 'DRAFT'  # re-approval required in v2's context
        # tenant-safe: clone_data carries tenant from source doc + new_version
        Documents.objects.create(**clone_data)


def duplicate_process(
    process: Processes,
    user=None,
    name_suffix: str = " (Copy)",
) -> Processes:
    """Create a standalone copy of a process with no version linkage.

    Copies the process header, all ProcessStep records (referencing the
    same Step nodes), and all StepEdge records. The copy starts in DRAFT.

    Use create_new_version() instead when modifying an approved process.
    """
    new_process = Processes.objects.create(
        name=f"{process.name}{name_suffix}",
        part_type=process.part_type,
        is_remanufactured=process.is_remanufactured,
        is_batch_process=process.is_batch_process,
        status=ProcessStatus.DRAFT,
        # No previous_version — standalone copy
    )

    for ps in process.process_steps.all():
        ProcessStep.objects.create(
            process=new_process,
            step=ps.step,
            order=ps.order,
            is_entry_point=ps.is_entry_point,
        )

    for edge in process.step_edges.all():
        StepEdge.objects.create(
            process=new_process,
            from_step=edge.from_step,
            to_step=edge.to_step,
            edge_type=edge.edge_type,
            condition_measurement=edge.condition_measurement,
            condition_operator=edge.condition_operator,
            condition_value=edge.condition_value,
        )

    return new_process


# ---------------------------------------------------------------------------
# Composite Process + Steps creation / update
# ---------------------------------------------------------------------------

def _build_edges(process: Processes, edges_data: list, temp_id_map: dict) -> None:
    """Create StepEdge rows resolving any temp IDs from the id map."""
    for edge in edges_data:
        from_step_id = edge.get("from_step")
        to_step_id = edge.get("to_step")
        real_from_id = temp_id_map.get(from_step_id, from_step_id)
        real_to_id = temp_id_map.get(to_step_id, to_step_id)
        if real_from_id and real_to_id:
            StepEdge.objects.create(
                process=process,
                from_step_id=real_from_id,
                to_step_id=real_to_id,
                edge_type=edge.get("edge_type", EdgeType.DEFAULT),
                condition_measurement_id=edge.get("condition_measurement"),
                condition_operator=edge.get("condition_operator", ""),
                condition_value=edge.get("condition_value"),
            )


def create_process_with_steps(data: dict) -> Processes:
    """Create a Process plus its child Steps, ProcessSteps, and StepEdges.

    ``data`` is the validated-data dict from ProcessWithStepsSerializer (after
    ``nodes`` and ``edges`` have been popped into separate arguments).  Caller
    is responsible for wrapping in ``transaction.atomic()`` if needed.

    Negative or zero node IDs are treated as temp IDs; real IDs are tracked so
    edges can reference them.
    """
    nodes_data = data.pop("nodes", [])
    edges_data = data.pop("edges", [])

    process = Processes.objects.create(**data)

    temp_id_map: dict = {}
    for node in nodes_data:
        node = node.copy()
        temp_id = node.pop("id", None)
        order = node.pop("order", None)
        is_entry_point = node.pop("is_entry_point", False)

        step = Steps.objects.create(part_type=process.part_type, **node)

        if temp_id is not None and temp_id <= 0:
            temp_id_map[temp_id] = step.id
        temp_id_map[step.id] = step.id

        ProcessStep.objects.create(
            process=process,
            step=step,
            order=order or 1,
            is_entry_point=is_entry_point or (order == 1),
        )

    _build_edges(process, edges_data, temp_id_map)
    return process


def update_process_with_steps(instance: Processes, data: dict, user=None) -> Processes:
    """Update a Process plus its child Steps, ProcessSteps, and StepEdges.

    Node semantics:
    - positive ID  → update existing Step + ProcessStep
    - negative / no ID → create new Step + ProcessStep
    - steps present in DB but absent from payload → unlink from process
      (the Step row is preserved; it may be shared across processes)
    - edges → fully replaced each call

    Raises:
        ValueError: Process is not editable (approved/deprecated).
        ValueError: Attempting to remove a step that has execution history.
    """
    if not instance.is_editable:
        raise ValueError(
            "Cannot modify approved process. Use create_new_version() to create an editable copy."
        )

    nodes_data = data.pop("nodes", [])
    edges_data = data.pop("edges", [])

    for attr, value in data.items():
        setattr(instance, attr, value)
    instance.save()

    temp_id_map: dict = {}
    existing_process_steps = {ps.step_id: ps for ps in instance.process_steps.all()}
    incoming_step_ids: set = set()

    for node in nodes_data:
        node = node.copy()
        node_id = node.pop("id", None)
        order = node.pop("order", None)
        is_entry_point = node.pop("is_entry_point", False)

        if node_id and node_id > 0:
            incoming_step_ids.add(node_id)
            qs = Steps.objects.for_user(user) if user else Steps.objects
            step = qs.get(id=node_id)
            for attr, value in node.items():
                setattr(step, attr, value)
            step.save()

            if node_id in existing_process_steps:
                ps = existing_process_steps[node_id]
                ps.order = order or ps.order
                ps.is_entry_point = is_entry_point
                ps.save()
            else:
                ProcessStep.objects.create(
                    process=instance,
                    step=step,
                    order=order or 1,
                    is_entry_point=is_entry_point,
                )

            temp_id_map[node_id] = node_id
        else:
            step = Steps.objects.create(part_type=instance.part_type, **node)
            incoming_step_ids.add(step.id)
            ProcessStep.objects.create(
                process=instance,
                step=step,
                order=order or 1,
                is_entry_point=is_entry_point,
            )
            if node_id is not None:
                temp_id_map[node_id] = step.id
            temp_id_map[step.id] = step.id

    steps_to_unlink = set(existing_process_steps.keys()) - incoming_step_ids
    if steps_to_unlink:
        protected = list(
            # tenant-safe: step_ids sourced from existing_process_steps (already tenant-scoped)
            StepExecution.objects.filter(step_id__in=steps_to_unlink)
            .values_list("step_id", flat=True)
            .distinct()
        )
        if protected:
            protected_names = list(
                Steps.objects.filter(id__in=protected).values_list("name", flat=True)
            )
            raise ValueError(
                f"Cannot remove steps with execution history: {', '.join(protected_names)}."
            )
        ProcessStep.objects.filter(process=instance, step_id__in=steps_to_unlink).delete()

    instance.step_edges.all().delete()
    _build_edges(instance, edges_data, temp_id_map)
    return instance
