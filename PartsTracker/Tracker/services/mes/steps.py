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
    Steps,
    StepMeasurementRequirement,
    StepRequirement,
)
from Tracker.models.mes_standard import SamplingRuleSet
from Tracker.models.qms import TrainingRequirement
from Tracker.services.mes.sampling_applier import SamplingFallbackApplier


def create_new_step_version(
    step: Steps,
    *,
    user,
    change_description: str,
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

    with transaction.atomic():
        # Base handles: row lock, current-version guard, archived guard,
        # scalar field copy (all non-excluded fields including tenant,
        # part_type, name, pass_threshold, etc.), version increment,
        # previous_version link, flipping old row's is_current_version,
        # and scheduling the revision_created signal post-commit.
        new_version = super(Steps, step).create_new_version(
            user=user,
            change_description=change_description,
            **field_updates,
        )

        # --- Child copy 1: StepMeasurementRequirement ---
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
            Documents.objects.create(**clone_data)

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
