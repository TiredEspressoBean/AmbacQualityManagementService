"""
Steps aggregate services.

Cross-aggregate writes for the Steps model: sampling ruleset creation,
supersession, coverage validation, and composite versioning. Model methods
delegate here.
"""
from __future__ import annotations

from django.db import transaction

from Tracker.models.mes_lite import (
    Parts,
    PartsStatus,
    ProcessStep,
    Processes,
    ProcessStatus,
    StepExecution,
    Steps,
    StepMeasurementRequirement,
    StepRequirement,
)
from Tracker.models.mes_standard import SamplingRuleSet
from Tracker.models.qms import TrainingRequirement
from Tracker.services.mes.sampling_applier import SamplingFallbackApplier


def add_step_to_process(
    process: Processes,
    *,
    order: int = 1,
    is_entry_point: bool = False,
    **step_fields,
) -> Steps:
    """Create a new Step and attach it to `process` via ProcessStep.

    Canonical entry point for adding a step to a process. Use this from
    every editor surface (process flow canvas, CLI imports, bulk seeders)
    so the rules for creating a step + junction are written once.

    `step_fields` is forwarded to `Steps.objects.create`. `part_type`
    defaults to the process's part_type — explicit override allowed.
    """
    step_fields.setdefault('part_type', process.part_type)
    with transaction.atomic():
        step = Steps.objects.create(**step_fields)
        ProcessStep.objects.create(
            process=process,
            step=step,
            order=order,
            is_entry_point=is_entry_point,
        )
    return step


def remove_step_from_process(process: Processes, step_ids: list) -> None:
    """Detach steps from `process` after verifying none have execution
    history. Step rows themselves are preserved — they may be shared
    with other process versions.

    Raises:
        ValueError: any step has StepExecution rows. The names of the
            offending steps are included in the message.
    """
    if not step_ids:
        return
    # tenant-safe: step_ids sourced from a tenant-scoped ProcessStep set.
    protected = list(
        StepExecution.objects.filter(step_id__in=step_ids)
        .values_list('step_id', flat=True)
        .distinct()
    )
    if protected:
        names = list(
            Steps.objects.filter(id__in=protected).values_list('name', flat=True)
        )
        raise ValueError(
            f"Cannot remove steps with execution history: {', '.join(names)}."
        )
    ProcessStep.objects.filter(process=process, step_id__in=step_ids).delete()


def create_new_step_version(
    step: Steps,
    *,
    user,
    change_description: str,
    process: Processes | None = None,
    supersede_source: bool | None = None,
    **field_updates,
) -> Steps:
    """Create a new version of a Step, copying all child rows to the new version.

    Steps have no status lifecycle of their own (no DRAFT/APPROVED gate). Any
    current, non-archived Step can be versioned. The new version is a scalar
    copy of the source plus three child types:

    1. StepMeasurementRequirement (FK `step`, default reverse accessor
       `stepmeasurementrequirement_set`) — same `measurement` FK, all Control
       Plan metadata carried forward.
    2. StepRequirement (FK `step`, related_name='requirements') — same
       requirement_type, name, config, etc. carried forward.
    3. TrainingRequirement (FK `step`, related_name='training_requirements') —
       **step-owned only**. From the versioning architecture doc:
         "TrainingRequirement is complex: it links TrainingType to Step OR
          Process OR EquipmentType via FK. All three targets are versioned.
          When Steps or Processes version, TrainingRequirement rows pointing at
          the old version need to be copied. Ownership rules must be defined —
          probably copy when the Step versions (since that's the most specific
          context)."
       Decision: filter `TrainingRequirement.objects.filter(step=step,
       process__isnull=True, equipment_type__isnull=True)`. Rows linked via
       `process` or `equipment_type` belong to those aggregates' version
       lifecycles — copying them here would duplicate them.

    Documents attached via GenericRelation are copied as fresh Document rows
    pointing at the new version, sharing the same file storage blobs. Each new
    Document starts as DRAFT (re-approval required in the new version's
    context). ApprovalRequest GFK children are NOT copied.

    The `revision_created` signal fires via the base
    `SecureModel.create_new_version` call post-commit.

    Args:
        step: The current version to revise. Must be is_current_version=True
            and not archived.
        user: User triggering the revision (forwarded to signal).
        change_description: Required human narrative of what changed and why
            (ISO 9001 4.4 / IATF 16949 8.5.6.1 audit trail).
        **field_updates: Optional field overrides for the new version.

    Raises:
        ValueError: change_description blank/whitespace-only.
        ValueError: base-inherited — step not current version, or archived.
    """
    from django.contrib.contenttypes.models import ContentType

    from Tracker.models import Documents

    if not change_description or not change_description.strip():
        raise ValueError(
            "change_description is required when creating a new Step version "
            "(ISO 9001 4.4 / IATF 16949 8.5.6.1 audit trail)."
        )

    # When the edit is scoped to a DRAFT process (PCR flow), the Step
    # version is a proposal — don't supersede the baseline. Sibling
    # PCRs need the baseline Step to stay available for their own
    # forks. For non-PCR edits (admin form, direct StepsViewSet PATCH
    # outside a PCR), keep the legacy supersede-on-fork behavior.
    if supersede_source is None:
        supersede_source = process is None or process.status != ProcessStatus.DRAFT

    with transaction.atomic():
        # Base handles: row lock, current-version guard, archived guard,
        # scalar field copy (all non-excluded fields including tenant,
        # part_type, name, pass_threshold, etc.), version increment,
        # previous_version link, optionally flipping old row's
        # is_current_version, and scheduling the revision_created signal
        # post-commit.
        new_version = super(Steps, step).create_new_version(
            user=user,
            change_description=change_description,
            supersede_source=supersede_source,
            **field_updates,
        )

        # Identity propagation — the new row inherits the source's
        # identity_id so it remains part of the same logical step chain.
        # Without this, the default=uuid.uuid4 fires on the new row and
        # the chain breaks for identity lookups.
        if new_version.identity_id != step.identity_id:
            new_version.identity_id = step.identity_id
            new_version.save(update_fields=['identity_id'])

        # --- Child copy 1: Substeps (and their per-substep children) ---
        # Substeps belong to a parent Step (FK). For each version of the
        # parent Step, the substeps fork too — so a PCR DRAFT editing
        # the Step's substep content doesn't leak across other process
        # versions that still reference the prior Step row.
        #
        # Child rows of each Substep (SubstepResource, SubstepTranslation)
        # are copied with the cloned Substep so the content stays
        # complete on the new Step row.
        from Tracker.models.dwi import Substep, SubstepResource, SubstepTranslation
        for sub in Substep.objects.filter(step=step):
            new_sub = Substep.objects.create(
                step=new_version,
                identity_id=sub.identity_id,
                order=sub.order,
                title=sub.title,
                body_blocks=sub.body_blocks,
                is_optional=sub.is_optional,
                is_critical=sub.is_critical,
                is_inspection_point=getattr(sub, 'is_inspection_point', False),
                requires_signature=getattr(sub, 'requires_signature', False),
                allow_not_applicable=getattr(sub, 'allow_not_applicable', False),
                scope=getattr(sub, 'scope', None) or 'PER_PART',
                expected_duration=sub.expected_duration,
                sampling_rule=getattr(sub, 'sampling_rule', None),
            )
            for res in SubstepResource.objects.filter(substep=sub):
                SubstepResource.objects.create(
                    substep=new_sub,
                    kind=res.kind,
                    document=res.document,
                    threed_model=res.threed_model,
                    annotation_filter=res.annotation_filter,
                    order=res.order,
                    caption=res.caption,
                )
            # tenant-safe: filtered by substep (FK chain to in-tenant Step).
            for tr in SubstepTranslation.objects.filter(substep=sub):
                # tenant-safe: cloned from in-tenant SubstepTranslation row.
                SubstepTranslation.objects.create(
                    substep=new_sub,
                    locale=tr.locale,
                    title=tr.title,
                    body_blocks=tr.body_blocks,
                )

        # --- Child copy 2: StepMeasurementRequirement ---
        # No related_name set; Django default reverse accessor is used via
        # direct model query to be explicit and avoid any accessor surprises.
        for smr in StepMeasurementRequirement.objects.filter(step=step):
            StepMeasurementRequirement.objects.create(
                step=new_version,
                measurement=smr.measurement,
                is_mandatory=smr.is_mandatory,
                sequence=smr.sequence,
                characteristic_number=smr.characteristic_number,
                tolerance_upper_override=smr.tolerance_upper_override,
                tolerance_lower_override=smr.tolerance_lower_override,
            )

        # --- Child copy 2: StepRequirement ---
        for req in step.requirements.all():
            StepRequirement.objects.create(
                step=new_version,
                requirement_type=req.requirement_type,
                name=req.name,
                description=req.description,
                is_mandatory=req.is_mandatory,
                order=req.order,
                config=req.config,
            )

        # --- Child copy 3: TrainingRequirement (step-owned only) ---
        # Only copy rows where this step is the exclusive target.
        # Rows linked via `process` or `equipment_type` belong to those
        # aggregates' own version lifecycles and must not be duplicated here.
        for tr in TrainingRequirement.objects.filter(
            step=step,
            process__isnull=True,
            equipment_type__isnull=True,
        ):
            TrainingRequirement.objects.create(
                step=new_version,
                training_type=tr.training_type,
                notes=tr.notes,
                tenant=tr.tenant,
            )

        # --- Documents (GenericRelation) ---
        step_ct = ContentType.objects.get_for_model(Steps)
        # tenant-safe: scoped via the Step content_type/object_id GFK
        source_docs = Documents.objects.filter(
            content_type=step_ct,
            object_id=step.pk,
            is_current_version=True,
        )
        _reset_on_clone = {
            'id', 'created_at', 'updated_at',
            'archived', 'deleted_at',
            'version', 'previous_version', 'is_current_version',
            'object_id',
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
            clone_data['status'] = 'DRAFT'
            # tenant-safe: cloned from in-tenant Documents row (tenant FK carried in clone_data).
            Documents.objects.create(**clone_data)

        # Junction-flip: if the caller scoped this edit to a specific
        # Process version (the PCR-DRAFT editing flow), repoint that
        # process's ProcessStep junction at the new Step version. Other
        # process versions (the still-APPROVED baseline, sibling open
        # DRAFTs) keep pointing at the old Step row — that's how
        # multi-PCR isolation works.
        #
        # StepEdge incidence is also process-scoped (each Process row
        # owns its own set of edges), so the same flip applies — any
        # edge in this process whose endpoint is the old Step row needs
        # to be repointed at the new version. Without this, ELK layout
        # fails with "Referenced shape does not exist" because the
        # process_steps junction now reports the new Step id while the
        # step_edges still cite the old one.
        #
        # When `process` is None we leave junctions alone — legacy
        # editing surfaces (StepsEditor without process context) still
        # version the Step row but no process version is updated to use
        # it. That's the bug; the fix lands at the call site by
        # supplying `process`.
        if process is not None:
            ProcessStep.objects.filter(
                process=process,
                step=step,
            ).update(step=new_version)
            from Tracker.models import StepEdge
            StepEdge.objects.filter(
                process=process, from_step=step,
            ).update(from_step=new_version)
            StepEdge.objects.filter(
                process=process, to_step=step,
            ).update(to_step=new_version)

    return new_version


def apply_step_sampling_rules_update(
    step: Steps,
    rules_data: list,
    user=None,
    process=None,
    fallback_rules_data: list | None = None,
    fallback_threshold: int | None = None,
    fallback_duration: int | None = None,
) -> SamplingRuleSet:
    """Archive existing active rulesets and create fresh active ones for a step.

    Creates a fallback ruleset first (if supplied), then links it to the new
    main ruleset. Re-evaluates sampling for any active parts currently at this
    step.

    Returns the newly created main SamplingRuleSet.
    """
    with transaction.atomic():
        step.sampling_ruleset.filter(active=True).update(active=False, archived=True)

        fallback_ruleset = None
        if fallback_rules_data:
            fallback_ruleset = SamplingRuleSet.create_with_rules(
                part_type=step.part_type,
                process=process,
                step=step,
                name=f"Fallback for Step {step.id}",
                rules=fallback_rules_data,
                created_by=user,
                origin="serializer-update",
                active=True,
                is_fallback=True,
            )

        main_ruleset = SamplingRuleSet.create_with_rules(
            part_type=step.part_type,
            process=process,
            step=step,
            name=f"Rules for Step {step.id}",
            rules=rules_data,
            fallback_ruleset=fallback_ruleset,
            fallback_threshold=fallback_threshold,
            fallback_duration=fallback_duration,
            created_by=user,
            origin="serializer-update",
            active=True,
            is_fallback=False,
        )

        active_parts = Parts.objects.filter(
            step=step,
            part_status__in=[PartsStatus.PENDING, PartsStatus.IN_PROGRESS],
        )
        if active_parts.exists():
            _reevaluate_parts_sampling(list(active_parts))

        return main_ruleset


def update_step_sampling_rules(
    step: Steps,
    rules_data: list,
    user=None,
    process=None,
    fallback_rules_data: list | None = None,
    fallback_threshold: int | None = None,
    fallback_duration: int | None = None,
) -> SamplingRuleSet:
    """Supersede (or create) the primary ruleset for a step.

    If an active primary ruleset exists it is versioned via
    ``primary_ruleset.supersede_with()``. A new fallback ruleset is created and
    linked when ``fallback_rules_data`` is supplied.

    Returns the new primary SamplingRuleSet.
    """
    with transaction.atomic():
        primary_ruleset = SamplingRuleSet.objects.filter(
            step=step,
            part_type=step.part_type,
            active=True,
            is_fallback=False,
        ).first()

        if primary_ruleset:
            new_ruleset = primary_ruleset.supersede_with(
                name=f"{step.name} Rules v{primary_ruleset.version + 1}",
                rules=rules_data,
                created_by=user,
            )
        else:
            new_ruleset = SamplingRuleSet.create_with_rules(
                part_type=step.part_type,
                process=process,
                step=step,
                name=f"{step.name} Rules v1",
                rules=rules_data,
                created_by=user,
            )

        if fallback_rules_data:
            fallback_ruleset = SamplingRuleSet.create_with_rules(
                part_type=step.part_type,
                process=process,
                step=step,
                name=f"{step.name} Fallback Rules v1",
                rules=fallback_rules_data,
                created_by=user,
                is_fallback=True,
            )
            new_ruleset.fallback_ruleset = fallback_ruleset
            new_ruleset.fallback_threshold = fallback_threshold
            new_ruleset.fallback_duration = fallback_duration
            new_ruleset.save()

        return new_ruleset


def validate_step_sampling_coverage(step: Steps, work_order) -> bool:
    """Return True when the actual sampling rate meets the step's minimum.

    Queries Parts for the given work_order / step pair and compares the
    sampled fraction against ``step.min_sampling_rate``.
    """
    total_parts = Parts.objects.filter(work_order=work_order, step=step).count()
    sampled_parts = Parts.objects.filter(
        work_order=work_order, step=step, requires_sampling=True
    ).count()
    actual_rate = (sampled_parts / total_parts * 100) if total_parts > 0 else 0
    return actual_rate >= step.min_sampling_rate


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _reevaluate_parts_sampling(parts_list: list) -> None:
    """Bulk-update sampling fields for a list of Parts after rule changes."""
    updates = []
    for part in parts_list:
        evaluator = SamplingFallbackApplier(part=part)
        result = evaluator.evaluate()
        part.requires_sampling = result.get("requires_sampling", False)
        part.sampling_rule = result.get("rule")
        part.sampling_ruleset = result.get("ruleset")
        part.sampling_context = result.get("context", {})
        updates.append(part)

    Parts.objects.bulk_update(
        updates,
        ["requires_sampling", "sampling_rule", "sampling_ruleset", "sampling_context"],
    )
