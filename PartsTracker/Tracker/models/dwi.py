"""
Digital Work Instructions (DWI) Models

Contains models for substep-level work instructions: a layer of structured
content below the existing `Steps` (Op) model. Each Step can have an ordered
sequence of Substeps; operators work through them while at the Op, and the
system tracks per-substep completion, gates, captures, and signatures.

Models defined here (Phase 1):
- Substep: a unit of work instruction within a Step
- SubstepCompletion: per-execution record (a part visits a Step → completes
  its substeps; one row per substep per execution)
- SubstepResource: equipment/material/PPE references for a substep
- SubstepTranslation: localization rows (BCP 47 language)

Models defined in later phases:
- SubstepGateCompletion + SubstepResponse (Phase 2 — per-node operator state)

Design reference: `Documents/DIGITAL_WORK_INSTRUCTIONS_DESIGN.md`.
"""

from django.db import models

from .core import SecureModel, User, VerificationMethod


# =============================================================================
# Sequencing mode for the parent Steps model
# =============================================================================
#
# Lives here (not in mes_lite.py) so the DWI subsystem owns the enum it
# introduces. Steps.sequencing_mode references this via the string
# 'sequential'/'free_order' values; importing the enum back into mes_lite.py
# for the field choices keeps the canonical definition in one place.


class SequencingMode(models.TextChoices):
    """How an Op's substeps are ordered for the operator.

    SEQUENTIAL: substep N can only be completed if N-1 is complete (or is
                optional and marked N/A).
    FREE_ORDER: any substep may be completed in any order; Op signoff
                checks that all required substeps are complete.
    """

    SEQUENTIAL = 'sequential', 'Sequential'
    FREE_ORDER = 'free_order', 'Free order'


# =============================================================================
# Substep — the unit of work instruction
# =============================================================================


class Substep(SecureModel):
    """
    A unit of work instruction within a parent Op (`Steps`).

    The substep's `body_blocks` JSON field holds a TipTap document with
    DWI-specific custom nodes (measurement specs, callouts, attestations,
    signature gates, capture inputs, etc.). See
    `ambac-tracker-ui/src/types/dwi.ts` for the node vocabulary and shape.

    Versioning rides the parent Process — substeps are part of the Process
    version pinned to a WorkOrder at start. New versions are created via
    `Processes.create_new_version()` per the existing versioning architecture.

    Sampling-driven applicability: when `sampling_rule` is set, the substep
    only applies to parts the rule selects (e.g., "every 25th part").
    Evaluation happens at part entry to the step; result is cached on the
    StepExecution.
    """

    step = models.ForeignKey(
        'Tracker.Steps',
        on_delete=models.CASCADE,
        related_name='substeps',
        help_text="The parent Op this substep belongs to.",
    )
    """The parent Op this substep belongs to."""

    order = models.PositiveIntegerField(
        default=0,
        help_text="Position within the parent Op's substep sequence (0-indexed).",
    )
    """Position within the parent Op's substep sequence."""

    title = models.CharField(
        max_length=200,
        help_text="Short human-readable title shown in substep listings.",
    )
    """Short human-readable title shown in substep listings."""

    body_blocks = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "TipTap document JSON. Shape: {type: 'doc', content: [...]}. "
            "See ambac-tracker-ui/src/types/dwi.ts (DwiDocument) for the "
            "node vocabulary."
        ),
    )
    """TipTap document JSON for the substep body. Engineer-authored only;
    never mutated by operator activity (operator captures land on
    SubstepResponse / SubstepGateCompletion / StepExecutionMeasurement)."""

    is_optional = models.BooleanField(
        default=False,
        help_text="Operator may mark this substep N/A instead of completing it.",
    )
    """If True, the operator may mark this substep `marked_not_applicable=True`
    on the SubstepCompletion row instead of working through it."""

    requires_signature = models.BooleanField(
        default=False,
        help_text=(
            "Operator must sign at substep completion. Distinct from inline "
            "AttestationCheckpoint(kind='signature') nodes within the body, "
            "which are gates inside the substep flow."
        ),
    )
    """If True, the SubstepCompletion row must carry signature_data when the
    operator marks the substep complete. Inline signature gates inside the
    substep body use SubstepGateCompletion (Phase 2) — different storage,
    different intent."""

    expected_duration = models.DurationField(
        null=True,
        blank=True,
        help_text="Estimated time the substep typically takes. Informational.",
    )
    """Mirrors `Steps.expected_duration` at substep granularity. Informational
    for now; downstream OEE / cycle-time analytics may consume it later."""

    sampling_rule = models.ForeignKey(
        'Tracker.SamplingRule',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='applicable_substeps',
        help_text=(
            "If set, the substep only applies to parts this rule selects. "
            "Null = substep always applies to every part visiting the step."
        ),
    )
    """When non-null, the substep is only live for parts the SamplingRule
    selects (e.g., "every 25th part, measure OD with the gauge"). Evaluation
    fires at part entry to the parent Step; result is cached on StepExecution
    so the operator UI knows which substeps to show."""

    # Provenance for the future LibrarySubstep concept (deferred). Both fields
    # nullable always; populated only when the substep was inserted from a
    # library template. See "Deferred Items" in the design doc.
    source_library_substep_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Forward-compatible: id of the LibrarySubstep this was inserted from.",
    )
    source_library_version = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Forward-compatible: version of the LibrarySubstep at insert time.",
    )

    class Meta:
        ordering = ['step', 'order']
        indexes = [
            models.Index(fields=['step', 'order'], name='dwi_substep_step_order_idx'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['step', 'order'],
                condition=models.Q(deleted_at__isnull=True),
                name='dwi_substep_step_order_uniq',
            ),
        ]

    def __str__(self) -> str:
        return f"{self.step_id}#{self.order} — {self.title}"


# =============================================================================
# SubstepCompletion — per-execution completion record
# =============================================================================


class SubstepCompletion(SecureModel):
    """
    Records that an operator completed a substep (or marked it N/A) during a
    specific StepExecution.

    One row per (StepExecution × Substep). `StepExecution` is per-part-per-
    visit (`mes_lite.py:StepExecution`), so for a batch of N parts going
    through an Op, each part has its own StepExecution and therefore its own
    independent set of SubstepCompletion rows.

    Signature fields mirror the `ApprovalResponse` / `CapaTasks` pattern
    (`signature_data` + `verification_method` + `ip_address`). Only populated
    when `Substep.requires_signature=True`; for substeps that don't require
    a signature, the operator just completes and these fields stay null.
    """

    step_execution = models.ForeignKey(
        'Tracker.StepExecution',
        on_delete=models.CASCADE,
        related_name='substep_completions',
        help_text="The execution record the operator was working when they completed this substep.",
    )

    substep = models.ForeignKey(
        Substep,
        on_delete=models.CASCADE,
        related_name='completions',
        help_text="The substep that was completed (or marked N/A).",
    )

    completed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='substep_completions',
        help_text="Operator who completed the substep.",
    )

    completed_at = models.DateTimeField(
        auto_now_add=True,
        help_text="UTC timestamp when the completion was recorded.",
    )

    marked_not_applicable = models.BooleanField(
        default=False,
        help_text="Set when the operator marks an optional substep N/A instead of completing it.",
    )
    """Only valid when `substep.is_optional=True`. The completion still gets a
    row (so we have an audit trail of "operator decided this didn't apply"),
    just with this flag set."""

    notes = models.TextField(
        blank=True,
        help_text="Operator notes captured at completion; required when marking N/A.",
    )

    # Signature capture (reuses the ApprovalResponse / CapaTasks pattern; only
    # populated when substep.requires_signature=True).
    signature_data = models.TextField(
        null=True,
        blank=True,
        help_text="Base64 PNG signature blob, matching the ApprovalResponse format.",
    )

    signature_meaning = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Short human-readable description of what the signature attests to.",
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When identity verification (password / SSO) succeeded.",
    )

    verification_method = models.CharField(
        max_length=20,
        choices=VerificationMethod.choices,
        default=VerificationMethod.NONE,
        help_text="How the signing operator's identity was verified.",
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Client IP at signing time; captured for audit defense.",
    )

    class Meta:
        ordering = ['-completed_at']
        constraints = [
            models.UniqueConstraint(
                fields=['step_execution', 'substep'],
                condition=models.Q(deleted_at__isnull=True),
                name='dwi_substepcompletion_exec_substep_uniq',
            ),
        ]
        indexes = [
            models.Index(fields=['step_execution', 'substep'], name='dwi_subcomp_exec_subs_idx'),
            models.Index(fields=['completed_by', '-completed_at'], name='dwi_subcomp_user_time_idx'),
        ]

    def __str__(self) -> str:
        suffix = ' (N/A)' if self.marked_not_applicable else ''
        return f"{self.substep_id} @ exec {self.step_execution_id}{suffix}"


# =============================================================================
# SubstepResource — equipment/material/PPE references for a substep
# =============================================================================


class SubstepResource(SecureModel):
    """
    A resource (equipment, material, PPE) referenced by a substep.

    Phase 1 ships with only `equipment_type` populated; `material_type` and
    `ppe_type` are deferred until those models materialize (see
    `Documents/DIGITAL_WORK_INSTRUCTIONS_DESIGN.md` → Deferred Items).

    A SubstepResource row references a *class* of resource (e.g.
    EquipmentType="Digital micrometer 0-1 in"). At execution time the
    operator binds an instance (a specific calibrated micrometer) via the
    existing EquipmentUsage flow. Authoring layer here; binding layer there.
    """

    substep = models.ForeignKey(
        Substep,
        on_delete=models.CASCADE,
        related_name='resources',
        help_text="The substep this resource is referenced from.",
    )

    equipment_type = models.ForeignKey(
        'Tracker.EquipmentType',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='referenced_by_substeps',
        help_text="The equipment class needed (e.g. 'Digital micrometer 0-1 in').",
    )

    # NOTE: `material_type` and `ppe_type` FKs are deferred until those
    # models materialize. See DWI design doc → Deferred Items.

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Optional quantity (e.g. count of fasteners, mass of material).",
    )

    notes = models.CharField(
        max_length=200,
        blank=True,
        help_text="Short note about how/why this resource is needed.",
    )

    required = models.BooleanField(
        default=True,
        help_text="If True, operator can't proceed without the resource being present.",
    )

    class Meta:
        ordering = ['substep', 'pk']
        # Phase 1 ships with equipment_type as the only resource FK. When
        # material_type / ppe_type FKs are added later, this constraint
        # widens to "exactly one of {equipment_type, material_type, ppe_type}".
        constraints = [
            models.CheckConstraint(
                check=models.Q(equipment_type__isnull=False),
                name='dwi_substepresource_has_equipment_type',
            ),
        ]

    def __str__(self) -> str:
        et = self.equipment_type.name if self.equipment_type_id else '(unset)'
        return f"{self.substep_id} needs {et}"


# =============================================================================
# SubstepTranslation — localized title/body for a substep
# =============================================================================


class SubstepTranslation(SecureModel):
    """
    Localized version of a substep's title and body for a specific language.

    BCP 47 language tags (e.g. 'en', 'es-MX', 'pt-BR'). The unique constraint
    on (substep, language) means at most one translation per language per
    substep. The base substep's `title` and `body_blocks` are the canonical
    source; translations override at render time when the operator's
    preferred language matches.

    Phase 1 ships the data model; the translation authoring UI and runtime
    language-switching are deferred (see design doc Deferred Items).
    """

    substep = models.ForeignKey(
        Substep,
        on_delete=models.CASCADE,
        related_name='translations',
        help_text="The substep this translation applies to.",
    )

    language = models.CharField(
        max_length=10,
        help_text="BCP 47 language tag (e.g. 'en', 'es-MX', 'pt-BR').",
    )

    title = models.CharField(
        max_length=200,
        help_text="Translated title.",
    )

    body_blocks = models.JSONField(
        default=list,
        blank=True,
        help_text="Translated TipTap document JSON; same shape as Substep.body_blocks.",
    )

    class Meta:
        ordering = ['substep', 'language']
        constraints = [
            models.UniqueConstraint(
                fields=['substep', 'language'],
                condition=models.Q(deleted_at__isnull=True),
                name='dwi_substeptranslation_substep_lang_uniq',
            ),
        ]
        indexes = [
            models.Index(fields=['substep', 'language'], name='dwi_subtrans_substep_lang_idx'),
        ]

    def __str__(self) -> str:
        return f"{self.substep_id} [{self.language}]"