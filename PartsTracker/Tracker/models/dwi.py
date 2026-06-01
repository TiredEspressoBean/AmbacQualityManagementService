"""
Digital Work Instructions (DWI) Models

Contains models for substep-level work instructions: a layer of structured
content below the existing `Steps` (Op) model. Each Step can have an ordered
sequence of Substeps; operators work through them while at the Op, and the
system tracks per-substep completion, gates, captures, and signatures.

Models defined here:

Phase 1 (substep core):
- Substep: a unit of work instruction within a Step
- SubstepCompletion: per-execution record (a part visits a Step → completes
  its substeps; one row per substep per execution)
- SubstepResource: equipment/material/PPE references for a substep
- SubstepTranslation: localization rows (BCP 47 language)

Phase 2 (per-node operator state):
- SubstepGateCompletion: per-node attestation/signature gate completion
- SubstepResponse: per-node operator capture (text, choice, file, timer,
  computed-value, etc.)
- SubstepResponseKind: enum discriminating the capture node kind

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

    is_inspection_point = models.BooleanField(
        default=False,
        help_text=(
            "When True, MeasurementInput captures within this substep "
            "additionally create inspection records (QualityReports + "
            "MeasurementResult) via services/qms/inline_capture.py, firing "
            "the existing record_quality_report_side_effects pipeline "
            "(auto-quarantine on out-of-spec, ncr.opened notification, "
            "sampling fallback). Default False = process data only. Set "
            "True for FAI substeps, in-process hold-points, final "
            "inspection. See architectural decision #21 in the DWI design doc."
        ),
    )
    """Promotes routine inline measurement captures into binding inspection
    records. See architectural decision #21 — established MES/QMS systems
    (Plex, SAP QM, Aegis FactoryLogix) separate process data from inspection
    records as first-class concepts. Routine captures stay process-data-only
    (no auto-quarantine, no NCR spam); inspection-point substeps fire the
    full inspection pipeline."""
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


# =============================================================================
# Phase 2 — per-node operator state
# =============================================================================
#
# Both Phase 2 models are keyed by the composite (step_execution, substep,
# node_id). Per decision #18, `node_id` is a UUIDv7 minted client-side at
# insert time inside the Substep.body_blocks document; the server validates
# format and intra-document uniqueness on Substep.save(). At execution time
# these rows are the persistent record of what the operator did at each
# capture node.
#
# `StepExecution` is per-part-per-step-per-visit, so per-part captures already
# fall out naturally — no `part` FK needed on these tables. The unique
# constraint on (step_execution, substep, node_id) prevents duplicate writes
# from the same operator on the same node within one execution.


class SubstepResponseKind(models.TextChoices):
    """Discriminator for SubstepResponse — which capture node produced this row.

    Keep in sync with the capture node types in
    `ambac-tracker-ui/src/lib/dwi/node-id.ts` (CAPTURE_NODE_TYPES) and
    `src/types/dwi.ts` (DwiNode union).

    Numeric measurement captures (`MeasurementInput`) are NOT in this enum —
    they route through the existing `StepExecutionMeasurement` table (Phase 3
    adds the `substep` FK on that model). This enum covers the non-numeric
    capture surface only.
    """

    TEXT = 'text', 'Text input'
    CHOICE = 'choice', 'Choice (radio / select)'
    PHOTO = 'photo', 'Photo capture'
    VIDEO = 'video', 'Video capture'
    SCAN = 'scan', 'Barcode / QR scan'
    FILE = 'file', 'File upload'
    TIMER = 'timer', 'Timer (countdown / stopwatch)'
    COMPUTED = 'computed', 'Computed value (formula)'


class SubstepGateCompletion(SecureModel):
    """
    Records that an operator passed through an inline gate node within a
    substep's body — either `AttestationCheckpoint(kind='confirm')` (a
    checkbox they ticked) or `AttestationCheckpoint(kind='signature')` (an
    inline signature they captured before proceeding past that point).

    Distinct from `SubstepCompletion`:
    - `SubstepCompletion` = the operator finished the substep as a whole
    - `SubstepGateCompletion` = the operator hit a specific gate inside the
      substep body and confirmed/signed there. A single substep can have
      multiple gates; each one gets its own row.

    Signature fields are only populated when the gate node's `kind` is
    'signature'. For 'confirm' gates the row just records that the checkbox
    was ticked at the given timestamp.
    """

    step_execution = models.ForeignKey(
        'Tracker.StepExecution',
        on_delete=models.CASCADE,
        related_name='substep_gate_completions',
        help_text="The execution record where this gate was completed.",
    )

    substep = models.ForeignKey(
        Substep,
        on_delete=models.CASCADE,
        related_name='gate_completions',
        help_text="The substep the gate node lives in.",
    )

    node_id = models.CharField(
        max_length=64,
        help_text=(
            "UUIDv7 of the AttestationCheckpoint node in Substep.body_blocks "
            "(minted client-side per decision #18). Stable across the "
            "substep's lifetime as long as the engineer doesn't cut-paste "
            "the node — see src/lib/dwi/node-id.ts."
        ),
    )

    completed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='substep_gate_completions',
        help_text="Operator who confirmed/signed the gate.",
    )

    completed_at = models.DateTimeField(
        auto_now_add=True,
        help_text="UTC timestamp when the gate was confirmed/signed.",
    )

    # Signature capture (only populated when the gate node's kind == 'signature').
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
                fields=['step_execution', 'substep', 'node_id'],
                condition=models.Q(deleted_at__isnull=True),
                name='dwi_substepgate_exec_sub_node_uniq',
            ),
        ]
        indexes = [
            models.Index(
                fields=['step_execution', 'substep', 'node_id'],
                name='dwi_subgate_esn_idx',
            ),
            models.Index(
                fields=['completed_by', '-completed_at'],
                name='dwi_subgate_user_time_idx',
            ),
        ]

    def __str__(self) -> str:
        return f"gate {self.node_id} @ exec {self.step_execution_id}"


class SubstepResponse(SecureModel):
    """
    Generic per-node operator capture for non-numeric inputs in a substep's
    body. One row per capture node per execution.

    Numeric measurement captures (`MeasurementInput`) route through the
    existing `StepExecutionMeasurement` table; that table gains a nullable
    `substep` FK in Phase 3. This table covers everything else: text, choice,
    photo / video / file uploads, scans, timers, computed values.

    Storage shape:
    - `value_text` — short string or single-line capture (text, choice
      selection, scan code)
    - `value_document` — FK to a Documents row (photo, video, file)
    - `value_json` — structured payload (timer's
      `{started_at, completed_at, elapsed_seconds, direction}`, computed
      value's `{inputs, result, in_spec}`)

    At most one of value_text / value_document / value_json should be
    populated per row, but the storage layer doesn't enforce that —
    consumers know which field to read based on `kind`.
    """

    step_execution = models.ForeignKey(
        'Tracker.StepExecution',
        on_delete=models.CASCADE,
        related_name='substep_responses',
        help_text="The execution record where this response was captured.",
    )

    substep = models.ForeignKey(
        Substep,
        on_delete=models.CASCADE,
        related_name='responses',
        help_text="The substep the capture node lives in.",
    )

    node_id = models.CharField(
        max_length=64,
        help_text=(
            "UUIDv7 of the capture node in Substep.body_blocks (minted "
            "client-side per decision #18)."
        ),
    )

    kind = models.CharField(
        max_length=20,
        choices=SubstepResponseKind.choices,
        help_text="Which kind of capture node produced this response.",
    )

    # Storage shape — exactly one of these should be populated per row,
    # depending on `kind`. The model doesn't enforce that (consumers know
    # which field to read from the kind discriminator).

    value_text = models.TextField(
        blank=True,
        help_text="Short text capture: text input, choice selection, scan code.",
    )

    value_document = models.ForeignKey(
        'Tracker.Documents',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='substep_responses',
        help_text="Photo / video / file capture: FK to the uploaded Documents row.",
    )

    value_json = models.JSONField(
        null=True,
        blank=True,
        help_text=(
            "Structured payload for kinds that don't fit a single string: "
            "Timer (started_at/completed_at/elapsed_seconds/direction), "
            "ComputedValue (inputs/result/in_spec)."
        ),
    )

    responded_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='substep_responses',
        help_text="Operator who captured the response.",
    )

    responded_at = models.DateTimeField(
        auto_now_add=True,
        help_text="UTC timestamp when the response was captured.",
    )

    class Meta:
        ordering = ['-responded_at']
        constraints = [
            models.UniqueConstraint(
                fields=['step_execution', 'substep', 'node_id'],
                condition=models.Q(deleted_at__isnull=True),
                name='dwi_substepresponse_exec_sub_node_uniq',
            ),
        ]
        indexes = [
            models.Index(
                fields=['step_execution', 'substep', 'node_id'],
                name='dwi_subresp_esn_idx',
            ),
            models.Index(
                fields=['kind', '-responded_at'],
                name='dwi_subresp_kind_time_idx',
            ),
            models.Index(
                fields=['responded_by', '-responded_at'],
                name='dwi_subresp_user_time_idx',
            ),
        ]

    def __str__(self) -> str:
        return f"{self.kind} response {self.node_id} @ exec {self.step_execution_id}"