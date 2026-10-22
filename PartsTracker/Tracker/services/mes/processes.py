"""
Processes aggregate services.

State-machine and duplication operations for the Processes model. Model
methods delegate here so status-gate checks and cross-aggregate writes
live in one place.
"""
from __future__ import annotations

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from Tracker.models import (
    ApprovalRequest,
    ApprovalTemplate,
    Processes,
    ProcessStep,
    ProcessStatus,
    StepEdge,
    Steps,
)
from Tracker.models.mes_lite import EdgeType


# `timing` absent from a node payload means "leave it alone"; an explicit null means
# "clear it". A plain None default cannot express both.
_UNSET = object()


def process_flow_errors(process: Processes) -> list[str]:
    """The routing problems that make a process unfit to lock for production — the
    ERRORS of the flow editor's validator (ambac-tracker-ui/src/lib/process-validation.ts),
    enforced here so no path (direct approve, PCR, temporary change) can approve one.
    Warnings stay advisory in the editor. Keep the two in step.

    Node kinds follow the editor's adapter: an explicit non-TASK `step_type` wins, else
    terminal / decision flags, else START for the entry step."""
    pss = list(process.process_steps.select_related('step').order_by('order'))
    if not pss:
        return ["Process has no steps."]
    edges = list(StepEdge.objects.filter(process=process))  # tenant-safe: scoped by process
    if not edges:
        # The editor draws an order-chain when no edges are stored.
        edges = [StepEdge(from_step_id=a.step_id, to_step_id=b.step_id, edge_type=EdgeType.DEFAULT)
                 for a, b in zip(pss, pss[1:]) if not a.step.is_terminal]
    targets = {e.to_step_id for e in edges}

    def kind(i, ps):
        s = ps.step
        if s.step_type and s.step_type != 'TASK':
            return s.step_type
        if s.is_terminal:
            return 'TERMINAL'
        if s.is_decision_point:
            return 'DECISION'
        if ps.is_entry_point or (i == 0 and s.id not in targets):
            return 'START'
        return 'TASK'

    out_by = {}
    in_by = {}
    for e in edges:
        out_by.setdefault(e.from_step_id, []).append(e)
        in_by.setdefault(e.to_step_id, []).append(e)
    kinds = {ps.step_id: kind(i, ps) for i, ps in enumerate(pss)}
    names = {ps.step_id: ps.step.name for ps in pss}

    errors = []
    starts = [sid for sid, k in kinds.items() if k == 'START']
    if len(starts) != 1:
        errors.append("The routing needs exactly one Start step "
                      f"(it has {len(starts)}).")
    if not any(k == 'TERMINAL' for k in kinds.values()):
        errors.append("The routing needs at least one Terminal step.")
    for sid, k in kinds.items():
        outs, ins = out_by.get(sid, []), in_by.get(sid, [])
        name = names[sid]
        if k == 'START' and not outs:
            errors.append(f"Start step “{name}” leads nowhere.")
        elif k == 'TERMINAL' and not ins:
            errors.append(f"Terminal step “{name}” can't be reached.")
        elif k not in ('START', 'TERMINAL') and not outs and not ins:
            errors.append(f"Step “{name}” isn't connected to the routing.")
        if k == 'DECISION':
            types = {e.edge_type for e in outs}
            if EdgeType.DEFAULT not in types:
                errors.append(f"Decision step “{name}” has no Pass connection.")
            if EdgeType.ALTERNATE not in types:
                errors.append(f"Decision step “{name}” has no Fail connection.")
        if k == 'REPAIR':
            step = next(ps.step for ps in pss if ps.step_id == sid)
            if not step.repair_code_id:
                errors.append(f"Repair step “{name}” has no repair code.")
            if not outs:
                errors.append(f"Repair step “{name}” doesn't lead back into the flow.")
    return errors


def approve_process(process: Processes, user=None, *, temporary_until=None) -> Processes:
    """Approve a draft or pending process for production use.

    `temporary_until` approves it as a TEMPORARY change instead: approved, but never
    current, and the predecessor (the baseline) is left current and unarchived so new
    work keeps using it. Only the work orders the change control migrates onto it run
    it, until that date (services/change_control/temporary.py).

    Raises:
        ValueError: Process is not in DRAFT or PENDING_APPROVAL status.
        ValueError: Process has no steps defined.
    """
    if process.status not in (ProcessStatus.DRAFT, ProcessStatus.PENDING_APPROVAL):
        raise ValueError("Only draft or pending processes can be approved.")

    if process.process_steps.count() == 0:
        raise ValueError("Cannot approve process with no steps.")

    # Approving locks the routing for production: a broken one (a dead decision branch,
    # a step nothing reaches) must not get there by any path (user decision 2026-10-22).
    errors = process_flow_errors(process)
    if errors:
        raise ValueError("Fix the routing before approving it: " + " ".join(errors))

    with transaction.atomic():
        # Step the predecessor down. Two things happen in one pass:
        #   1. `is_current_version` flips to False so list queries that
        #      filter on the current flag stop returning the old row.
        #   2. `archived` flips to True so list queries that filter on
        #      the soft-delete flag also stop returning it. Historical
        #      APPROVED versions are not "deleted" — WorkOrders that FK
        #      to them still resolve — but they shouldn't appear in
        #      live process-picker lists alongside the new current.
        # Multi-PCR case (`supersede_source=False` DRAFT forks) reaches
        # the same branch: the baseline that allowed sibling co-forking
        # finally steps down once one of its proposals is approved.
        #
        # Using `.save()` rather than `.update()` so `updated_at` moves,
        # the auditlog `pre_save` / `post_save` hooks record the
        # archive event, and any model-level side effects still fire.
        if temporary_until is not None:
            process.status = ProcessStatus.APPROVED
            process.approved_at = timezone.now()
            process.approved_by = user
            process.is_current_version = False
            process.is_temporary = True
            process.temporary_until = temporary_until
            process.save()
            return process

        if process.previous_version_id is not None:
            # tenant-safe: scoped via the previous_version FK in the
            # caller's tenant.
            predecessor = (
                # tenant-safe: pk lookup of this chain's predecessor version (globally-unique UUID)
                Processes.all_tenants.filter(pk=process.previous_version_id).first()
            )
            if predecessor is not None:
                predecessor.is_current_version = False
                predecessor.archived = True
                predecessor.save(
                    update_fields=['is_current_version', 'archived', 'updated_at'],
                )

        process.status = ProcessStatus.APPROVED
        process.approved_at = timezone.now()
        process.approved_by = user
        process.is_current_version = True
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
        # tenant-safe: SecureManager .objects auto-scopes to the request tenant
        template = ApprovalTemplate.objects.get(
            approval_type='PROCESS_APPROVAL',
            is_current_version=True,
            archived=False,
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
    allow_multiple_drafts: bool = False,
    supersede_source: bool = True,
    **field_updates,
) -> Processes:
    """Create a new version of an APPROVED or DEPRECATED process.

    New version starts in DRAFT with approved_at/approved_by cleared.
    Scalar fields, tenant, and category carry forward via the base
    scalar-copy mechanism. ProcessStep and StepEdge junction rows are
    copied (same Step FKs — Steps are independently versioned and
    historically pinned). Documents attached via GenericRelation are
    copied as fresh Document rows pointing at the new version, sharing
    the same file storage blob (no re-upload) and carrying their approval
    status forward — see `clone_current_documents`. ApprovalRequest GFK
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
    from django.db import transaction

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

    # Single-DRAFT guard. PCR propose flows pass `allow_multiple_drafts=True`
    # because the change-control system supports multiple open PCRs and
    # reconciles conflicts at approval time via the rebase service.
    # Direct callers (admin actions, the deprecated standalone Duplicate
    # path) keep the safer default.
    if not allow_multiple_drafts:
        # tenant-safe: previous_version FK constrains to processes in the same
        # tenant as `process` (versioning chains never cross tenants).
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
        # name), version increment, previous_version link,
        # flipping old row's is_current_version, and firing the
        # revision_created signal post-commit.
        new_version = super(Processes, process).create_new_version(
            user=user,
            change_description=change_description,
            supersede_source=supersede_source,
            # Reset lifecycle state on the new draft.
            status=ProcessStatus.DRAFT,
            approved_at=None,
            approved_by=None,
            # `change_description` is also a concrete field on the model —
            # the base's field_updates mechanism stores it on the row.
            **field_updates,
        )

        _copy_routing(process, new_version)

        # Documents (GenericRelation) carry forward automatically — the base
        # SecureModel.create_new_version clones them inside the super() call
        # above. No explicit copy needed here.

    return new_version


def _copy_routing(source: Processes, target: Processes) -> None:
    """Copy a process version's routing onto a new version: its ProcessStep junctions
    (same Step rows — steps are shared across versions) and its edges."""
    # Every ProcessStep field, not a subset. `is_exit_point` and `auto_advance`
    # were omitted here, and both have defaults that read as "normal" — False and
    # True — so versioning a process silently dropped its early-exit paths and
    # re-enabled auto-advance on any step where it had been deliberately turned
    # off. A clone that loses settings quietly is worse than one that fails.
    for ps in source.process_steps.all():
        ProcessStep.objects.create(
            process=target,
            step=ps.step,
            order=ps.order,
            is_entry_point=ps.is_entry_point,
            is_exit_point=ps.is_exit_point,
            auto_advance=ps.auto_advance,
        )

    # Same omission on the edges: `tech_continuity` and `max_minutes` were added
    # for scheduling after this clone was written and never added to it. Losing
    # them is not cosmetic — tech_continuity=DIFFERENT is the independent-
    # verification control, and max_minutes carries real process limits (cure
    # windows, "coat within 4h of clean").
    for edge in source.step_edges.all():
        StepEdge.objects.create(
            process=target,
            from_step=edge.from_step,
            to_step=edge.to_step,
            edge_type=edge.edge_type,
            pre_approved=edge.pre_approved,
            tech_continuity=edge.tech_continuity,
            max_minutes=edge.max_minutes,
            condition_measurement=edge.condition_measurement,
            condition_operator=edge.condition_operator,
            condition_value=edge.condition_value,
        )


def fork_version_for_deviation(
    process: Processes,
    *,
    user,
    change_description: str,
) -> Processes:
    """A DRAFT fork of an approved process version — typically a retired (superseded)
    one — for a temporary change that must reach work orders still running it.

    Approving a revision archives its predecessor — archived here means retired, not
    deleted: work orders on it still run it. The generic versioning refuses to fork an
    archived row, and should for genuinely deleted ones, so this is the one process-
    specific path that forks a retired approved version. It never supersedes the
    source, and runs the same steps the generic fork does — field copy, routing,
    documents, inbound links, the revision signal — through the same helpers.

    Raises:
        ValueError: change_description blank, or the source isn't an approved,
            non-temporary version.
    """
    from django.db import transaction
    from Tracker.services.core.documents import clone_current_documents, forward_target_links
    from Tracker.services.core.version_links import apply_version_links
    from Tracker.signals_versioning import revision_created

    if not change_description or not change_description.strip():
        raise ValueError("change_description is required when forking a process version.")
    if process.status != ProcessStatus.APPROVED or process.is_temporary:
        raise ValueError("Only an approved, non-temporary version can be forked for a deviation.")

    with transaction.atomic():
        source = Processes.all_tenants.select_for_update().get(pk=process.pk)  # tenant-safe: pk of an in-tenant process
        data = {f.name: getattr(source, f.name) for f in Processes._meta.fields
                if f.name not in Processes._VERSIONING_EXCLUDE_FIELDS}
        data.update(
            version=source.version + 1, previous_version=source,
            # Never current: it carries a deviation for named work orders only.
            is_current_version=False, archived=False,
            status=ProcessStatus.DRAFT, approved_at=None, approved_by=None,
            change_description=change_description,
        )
        fork = Processes.objects.create(**data)  # tenant-safe: tenant copied from the source version in `data`
        _copy_routing(source, fork)
        clone_current_documents(source=source, target=fork)
        forward_target_links(old_target=source, new_target=fork)
        apply_version_links(source, fork, supersede_source=False)

    revision_created.send_robust(sender=Processes, old_version=source, new_version=fork,
                                 user=user, change_description=change_description)
    return fork


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
        status=ProcessStatus.DRAFT,
        # No previous_version — standalone copy
    )

    # Re-anchor each Step reference to its current version. The source
    # process may point at stale Step rows if it predates the
    # junction-flip fix (or if a sibling process versioned the shared
    # Step). Forward-walk the chain so the duplicate starts clean.
    step_remap: dict = {}
    for ps in process.process_steps.all():
        current_step = _walk_to_current_step(ps.step)
        step_remap[ps.step_id] = current_step
        ProcessStep.objects.create(
            process=new_process,
            step=current_step,
            order=ps.order,
            is_entry_point=ps.is_entry_point,
            is_exit_point=ps.is_exit_point,
            auto_advance=ps.auto_advance,
        )

    for edge in process.step_edges.all():
        StepEdge.objects.create(
            process=new_process,
            from_step=step_remap.get(edge.from_step_id, edge.from_step),
            to_step=step_remap.get(edge.to_step_id, edge.to_step),
            edge_type=edge.edge_type,
            pre_approved=edge.pre_approved,
            tech_continuity=edge.tech_continuity,
            max_minutes=edge.max_minutes,
            condition_measurement=edge.condition_measurement,
            condition_operator=edge.condition_operator,
            condition_value=edge.condition_value,
        )

    return new_process


def _walk_to_current_step(step):
    """Return the current Step row for `step`'s identity line. Uses the
    indexed `identity_id` lookup — O(1) regardless of chain depth.
    Returns the input step unchanged if it's already current, or if
    there's no current sibling (defensive fallback for stale chains).
    """
    if step.is_current_version:
        return step
    # tenant-safe: identity_id is tenant-scoped via the Step model's tenant FK.
    current = Steps.objects.filter(
        identity_id=step.identity_id,
        is_current_version=True,
    ).first()
    return current or step


# ---------------------------------------------------------------------------
# Composite Process + Steps creation / update
# ---------------------------------------------------------------------------

def _build_edges(
    process: Processes,
    edges_data: list,
    temp_id_map: dict,
    preserved: dict | None = None,
) -> None:
    """Create StepEdge rows resolving any temp IDs from the id map.

    `preserved` maps (from_step_id, to_step_id, edge_type) to the scheduling
    attributes of the edge that occupied that slot before an update deleted it.
    The process editor does not send `tech_continuity` at all, so without this a
    save would silently reset every independent-verification requirement and
    every process time limit to its default — the edges are torn down and rebuilt
    wholesale on each save, so anything the payload omits is destroyed rather than
    left alone. An explicit value in the payload still wins; the fallback only
    covers what the client never knew about.
    """
    preserved = preserved or {}
    for edge in edges_data:
        from_step_id = edge.get("from_step")
        to_step_id = edge.get("to_step")
        real_from_id = temp_id_map.get(from_step_id, from_step_id)
        real_to_id = temp_id_map.get(to_step_id, to_step_id)
        if real_from_id and real_to_id:
            edge_type = edge.get("edge_type", EdgeType.DEFAULT)
            prior = preserved.get((str(real_from_id), str(real_to_id), edge_type), {})
            StepEdge.objects.create(
                process=process,
                from_step_id=real_from_id,
                to_step_id=real_to_id,
                edge_type=edge_type,
                # A repair's pre-approval at a check: what the editor sends, else what
                # the edge had, else not pre-approved — a save that omits it must not
                # silently pre-approve or un-approve a repair.
                pre_approved=bool(edge.get(
                    "pre_approved", prior.get("pre_approved", False))),
                tech_continuity=edge.get(
                    "tech_continuity", prior.get("tech_continuity", "ANY")),
                max_minutes=(
                    edge["max_minutes"] if "max_minutes" in edge
                    else prior.get("max_minutes")),
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
        # Junction flags, not Step fields — they must come out of `node` before it is
        # splatted into Steps.objects.create, which would reject them.
        is_exit_point = node.pop("is_exit_point", False)
        auto_advance = node.pop("auto_advance", True)

        step = Steps.objects.create(part_type=process.part_type, **node)

        if temp_id is not None and temp_id <= 0:
            temp_id_map[temp_id] = step.id
        temp_id_map[step.id] = step.id

        ProcessStep.objects.create(
            process=process,
            step=step,
            order=order or 1,
            is_entry_point=is_entry_point or (order == 1),
            is_exit_point=is_exit_point,
            auto_advance=auto_advance,
        )

    _build_edges(process, edges_data, temp_id_map)
    return process


@transaction.atomic
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
    # Key by str(step_id): node ids arrive as strings (nodes is a DictField),
    # while ps.step_id is a UUID — comparing the two directly always misses,
    # which made existing steps look new (duplicate-junction insert) and also
    # mis-computed the unlink set. Normalize every step-id comparison to str.
    existing_process_steps = {str(ps.step_id): ps for ps in instance.process_steps.all()}
    incoming_step_ids: set = set()

    # Shift existing junction orders out of the 1..N range up front. ProcessStep
    # has a (process, order) unique constraint, and the per-node pass below
    # re-assigns orders / creates new steps incrementally — a new or reordered
    # step would otherwise collide with a row not yet updated or removed (the
    # unlink of dropped steps only runs at the end). Each node writes its final
    # order over this offset; any rows left at the offset are unlinked below.
    # Safe because the whole function is atomic.
    if existing_process_steps:
        ProcessStep.objects.filter(process=instance).update(order=F('order') + 100000)

    for node in nodes_data:
        node = node.copy()
        node_id = node.pop("id", None)
        # Client-only correlation id for a brand-new node (no persisted Step yet).
        # Must NOT reach Steps.objects.create; kept to map edges to the new Step.
        temp_id = node.pop("_temp_id", None)
        order = node.pop("order", None)
        is_entry_point = node.pop("is_entry_point", False)
        # Junction flags. `_UNSET` rather than a default, because these are absent from
        # the editor payload today and defaulting would reset a deliberately-set exit
        # point or a disabled auto-advance on every unrelated save.
        is_exit_point = node.pop("is_exit_point", _UNSET)
        auto_advance = node.pop("auto_advance", _UNSET)
        # Timing lives on a related one-to-one, not on Steps, so it must come out before
        # the diff below — `_changed` does `getattr(step, k)`, which would compare a
        # StepTiming instance against a dict, call it changed on every save, and then
        # hand `timing=` to create_new_step_version as though it were a model field.
        timing = node.pop("timing", _UNSET)

        # Existing step: node_id is a UUID matching a Steps row. New
        # step: node_id is None, a negative int legacy sentinel, or any
        # value that doesn't resolve to an existing Step. The legacy
        # `> 0` integer check is dead under UUIDs; resolve by lookup.
        qs = Steps.objects.for_user(user) if user else Steps.objects
        existing_step = None
        if node_id:
            try:
                existing_step = qs.get(id=node_id)
            except (Steps.DoesNotExist, ValueError, TypeError):
                existing_step = None

        if existing_step is not None:
            incoming_step_ids.add(str(existing_step.id))
            step = existing_step

            # Content edits MUST route through `create_new_step_version`
            # so a new Step row is minted and ONLY this process's
            # ProcessStep junction is repointed at it. Direct `step.save()`
            # used to mutate the shared row globally — which silently
            # changed every process version (including APPROVED) that
            # referenced the same Step.
            #
            # Diff against the persisted row and forward only changed
            # fields. If nothing material changed (e.g. the editor
            # re-sent the whole node payload but the engineer only moved
            # the node on canvas), skip versioning.
            from Tracker.services.mes.steps import create_new_step_version

            def _changed(k, v):
                cur = getattr(step, k, None)
                # FK-id fields arrive as UUID strings; the model attr is a UUID —
                # compare as strings so an unchanged FK (e.g. outside_supplier_id)
                # doesn't look "changed" and mint a spurious step version.
                if k.endswith("_id"):
                    return (str(cur) if cur is not None else None) != (str(v) if v is not None else None)
                return cur != v

            diffed = {k: v for k, v in node.items() if _changed(k, v)}
            timing_changed = timing is not _UNSET and _timing_differs(step, timing)
            note = f"Process editor save for {instance.name} v{instance.version}"
            if str(node_id) in existing_process_steps and (diffed or timing_changed):
                # The draft's own row: copied once if another process shares it,
                # edited in place after that — not a new version per save.
                from Tracker.services.mes.steps import step_for_draft
                step = step_for_draft(step, instance, user=user, change_description=note, **diffed)
            elif diffed:
                # A step brought in from elsewhere: version it for this process.
                step = create_new_step_version(
                    step, user=user, change_description=note, process=instance, **diffed,
                )

            if str(node_id) in existing_process_steps:
                # Junction may have just been repointed to the new Step
                # version by `create_new_step_version` above. Re-fetch
                # to grab the row that now binds this process to the
                # current Step row (old OR new, depending on whether we
                # versioned).
                ps = ProcessStep.objects.get(process=instance, step=step)
                ps.order = order or ps.order
                ps.is_entry_point = is_entry_point
                if is_exit_point is not _UNSET:
                    ps.is_exit_point = is_exit_point
                if auto_advance is not _UNSET:
                    ps.auto_advance = auto_advance
                ps.save()
            else:
                # A step whose substeps require a reman capture can't join a route new
                # builds run: the unit would stick there (substep N/A is retired).
                from Tracker.services.dwi.reman_capture_guard import process_step_refusal
                refusal = process_step_refusal(instance, step)
                if refusal:
                    raise ValueError(refusal)
                ProcessStep.objects.create(
                    process=instance,
                    step=step,
                    order=order or 1,
                    is_entry_point=is_entry_point,
                    is_exit_point=(False if is_exit_point is _UNSET else is_exit_point),
                    auto_advance=(True if auto_advance is _UNSET else auto_advance),
                )

            # Timing lands on whatever row we ended up on — `step` is the NEW version
            # when the diff forked it, and writing to the superseded row would look
            # like it saved and then vanish on the next read.
            if timing is not _UNSET:
                _apply_step_timing(step, timing)

            # Edges reference Step rows directly. When a Step versioned
            # above, edges must rebuild against the new Step id —
            # `_build_edges` reads `temp_id_map` so we stamp the new id
            # under the frontend's original node_id key.
            temp_id_map[node_id] = step.id
        else:
            from Tracker.services.mes.steps import add_step_to_process
            step = add_step_to_process(
                instance,
                order=order or 1,
                is_entry_point=is_entry_point,
                **node,
            )
            incoming_step_ids.add(str(step.id))
            if timing is not _UNSET:
                _apply_step_timing(step, timing)
            if node_id is not None:
                temp_id_map[node_id] = step.id
            # Edges from the canvas reference a new node by its _temp_id; map it
            # to the freshly-created Step so _build_edges can resolve them.
            if temp_id is not None:
                temp_id_map[temp_id] = step.id
            temp_id_map[step.id] = step.id

    steps_to_unlink = set(existing_process_steps.keys()) - incoming_step_ids
    if steps_to_unlink:
        from Tracker.services.mes.steps import remove_step_from_process
        remove_step_from_process(instance, list(steps_to_unlink))

    # Snapshot the scheduling attributes before tearing the edges down, so a save
    # that omits them restores rather than resets. Keyed on the REMAPPED step ids,
    # because a step that versioned above now has a new id on both sides.
    preserved = {}
    for e in instance.step_edges.all():
        from_id = str(temp_id_map.get(e.from_step_id, e.from_step_id))
        to_id = str(temp_id_map.get(e.to_step_id, e.to_step_id))
        preserved[(from_id, to_id, e.edge_type)] = {
            'tech_continuity': e.tech_continuity,
            'max_minutes': e.max_minutes,
            'pre_approved': e.pre_approved,
        }

    instance.step_edges.all().delete()
    _build_edges(instance, edges_data, temp_id_map, preserved=preserved)
    return instance


def _timing_differs(step, data) -> bool:
    """Whether saving `data` would change the step's timing. The editor sends every
    node's timing on every save; only a real change should cost the draft a copy."""
    from Tracker.models.scheduling import StepTiming
    # tenant-safe: the one-to-one of an in-tenant step.
    current = StepTiming.objects.filter(step=step, archived=False).first()
    if data is None:
        return current is not None
    fields = ('setup_minutes', 'cycle_time_minutes', 'load_unload_per_piece',
              'attention_type', 'external_setup_minutes')
    if current is None:
        return any(k in data for k in fields)
    def same(k):
        a, b = getattr(current, k), data[k]
        try:
            return float(a) == float(b)
        except (TypeError, ValueError):
            return a == b
    return any(k in data and not same(k) for k in fields)


def _apply_step_timing(step, data):
    """Create-or-update a step's `StepTiming`; `None` clears it.

    An untimed step is a real state — the solver sizes it to zero minutes and RCCP reads
    it as free — so it has to be expressible, not merely unreachable.
    """
    from Tracker.models.scheduling import StepTiming

    if data is None:
        StepTiming.objects.filter(step=step).delete()
        return
    allowed = {'setup_minutes', 'cycle_time_minutes', 'load_unload_per_piece',
               'attention_type', 'external_setup_minutes'}
    fields = {k: v for k, v in (data or {}).items() if k in allowed}
    if not fields:
        return
    # `archived: False` revives a previously-cleared row — the FK is a OneToOne, so a
    # soft-deleted row still occupies the slot and would collide with a fresh create.
    StepTiming.objects.update_or_create(
        step=step, defaults={'tenant': step.tenant, 'archived': False,
                             'deleted_at': None, **fields})
