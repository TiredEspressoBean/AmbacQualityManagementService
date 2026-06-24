/**
 * DWI (Digital Work Instructions) type definitions.
 *
 * Hand-rolled because `body_blocks` is stored as a JSONField on the Substep
 * model; OpenAPI / openapi-typescript can't generate types for arbitrary JSON
 * payloads. These types describe the TipTap document shape and the attr
 * schema of each custom node.
 *
 * Cross-references:
 * - DIGITAL_WORK_INSTRUCTIONS_DESIGN.md — node library spec (source of truth)
 * - REMAN_DWI_INTEGRATION.md — HarvestedComponentCapture node spec
 * - src/lib/dwi/node-id.ts — CAPTURE_NODE_TYPES (keep in sync with this file)
 * - src/pages/DwiSpikePage.tsx — reference implementation
 *
 * Naming convention: attr field names match the Django model field names
 * where applicable (snake_case), so the editor JSON round-trips cleanly
 * with `Substep.body_blocks` without re-mapping.
 */

// ============================================================================
// TipTap document shape
// ============================================================================

/**
 * Top-level shape of `Substep.body_blocks`. Produced by `editor.getJSON()`
 * and loaded via `editor.commands.setContent()`. Same shape consumed by
 * `generateHTML(json, DWI_EXTENSIONS)` from @tiptap/html for non-interactive
 * renders (PDFs, email, search indexing).
 */
export type DwiDocument = {
    type: "doc";
    content: DwiNode[];
};

/**
 * Discriminated union of every node type that can appear inside a
 * `DwiDocument`. Carries TipTap's standard `{ type, attrs?, content?, marks? }`
 * shape; specific node attr schemas are defined below and combined here.
 */
export type DwiNode =
    | DwiContentNode
    | MeasurementSpecNode
    | CalloutNode
    | MediaNode
    | AttestationCheckpointNode
    | MeasurementInputNode
    | TextInputNode
    | ChoiceInputNode
    | PhotoCaptureNode
    | ScanInputNode
    | FileCaptureNode
    | TimerNode
    | ComputedValueNode;

/**
 * StarterKit + typography nodes (paragraph, heading, lists, blockquote, etc.).
 * Carry no DWI-specific attrs; modeled loosely as a generic shape.
 */
export type DwiContentNode = {
    type:
        | "paragraph"
        | "heading"
        | "bulletList"
        | "orderedList"
        | "listItem"
        | "blockquote"
        | "horizontalRule"
        | "hardBreak"
        | "text"
        | "codeBlock";
    attrs?: Record<string, unknown>;
    content?: DwiNode[];
    marks?: Array<{ type: string; attrs?: Record<string, unknown> }>;
    text?: string;
};

// ============================================================================
// Content nodes (display-only — no operator state)
// ============================================================================

/** Read-only measurement target reference. Mirrors `MeasurementDefinition`. */
export type MeasurementSpecAttrs = {
    label: string;
    type: "NUMERIC" | "PASS_FAIL";
    unit: string;
    nominal: number | null;
    upper_tol: number | null;
    lower_tol: number | null;
    required: boolean;
    characteristic_number: string;
    /** Optional FK to an existing MeasurementDefinition row in the tenant. */
    measurement_definition_id?: string | null;
};
export type MeasurementSpecNode = {
    type: "measurementSpec";
    attrs: MeasurementSpecAttrs & { node_id: string };
};

/** Caution / Note / Reminder / Safety callout. Body is editable paragraphs. */
export type CalloutVariant = "caution" | "note" | "reminder" | "safety";
export type CalloutAttrs = {
    variant: CalloutVariant;
};
export type CalloutNode = {
    type: "callout";
    attrs: CalloutAttrs;
    content?: DwiNode[];
};

/** Author-embedded image / video / 3D-model reference. */
export type MediaKind = "image" | "video" | "3d_model";
export type MediaAttrs = {
    kind: MediaKind;
    src: string;
    caption: string;
    /** Optional FK to a Documents row in the tenant. */
    document_id?: string | null;
};
export type MediaNode = {
    type: "media";
    attrs: MediaAttrs;
};

// ============================================================================
// Capture nodes (write to per-execution storage)
//
// Every capture node carries a `node_id` (UUIDv7) so per-execution rows can
// be joined back to the specific node in the document. See
// src/lib/dwi/node-id.ts for the minting/regeneration utility.
// ============================================================================

/** Checkbox or inline signature gate. Writes to `SubstepGateCompletion`. */
export type AttestationKind = "confirm" | "signature";
export type AttestationCheckpointAttrs = {
    node_id: string;
    label: string;
    kind: AttestationKind;
    /** Prompt text (kind='confirm' only). */
    prompt: string;
    required: boolean;
};
export type AttestationCheckpointNode = {
    type: "attestationCheckpoint";
    attrs: AttestationCheckpointAttrs;
};

/** Active numeric capture. Writes to `StepExecutionMeasurement`. */
export type MeasurementInputAttrs = {
    node_id: string;
    label: string;
    unit: string;
    /** Spec language: in-spec iff nominal - (lower_tol ?? ∞) <= value <= nominal + (upper_tol ?? ∞). */
    nominal: number | null;
    upper_tol: number | null;
    lower_tol: number | null;
    required: boolean;
    characteristic_number: string;
    /** Optional FK to a MeasurementDefinition row in the tenant. */
    measurement_definition_id?: string | null;
    /** Preferred + fallback gauge, copied from the linked MeasurementDefinition.
     *  Both optional (visual checks use no instrument). The operator picks which
     *  was used; the choice is captured on StepExecutionMeasurement.equipment. */
    default_equipment_id?: string | null;
    default_equipment_name?: string;
    backup_equipment_id?: string | null;
    backup_equipment_name?: string;
    /** "NUMERIC" → operator types a value; "PASS_FAIL" → operator picks Pass/Fail. */
    measurement_type?: string;
};
export type MeasurementInputNode = {
    type: "measurementInput";
    attrs: MeasurementInputAttrs;
};

/** Short / long text capture. Writes to `SubstepResponse` (kind='text'). */
export type TextInputKind = "short" | "long";
export type TextInputAttrs = {
    node_id: string;
    label: string;
    kind: TextInputKind;
    placeholder: string;
    required: boolean;
};
export type TextInputNode = {
    type: "textInput";
    attrs: TextInputAttrs;
};

/** Radio / select choice capture. Writes to `SubstepResponse` (kind='choice'). */
export type ChoiceInputKind = "radio" | "select";
export type ChoiceInputAttrs = {
    node_id: string;
    label: string;
    kind: ChoiceInputKind;
    options: string[];
    required: boolean;
};
export type ChoiceInputNode = {
    type: "choiceInput";
    attrs: ChoiceInputAttrs;
};

/** Photo capture. Writes to `SubstepResponse` (kind='photo') + `Documents`. */
export type PhotoCaptureAttrs = {
    node_id: string;
    label: string;
    required: boolean;
};
export type PhotoCaptureNode = {
    type: "photoCapture";
    attrs: PhotoCaptureAttrs;
};

/** Barcode / QR scan input. Writes to `SubstepResponse` (kind='scan'). */
export type ScanInputAttrs = {
    node_id: string;
    label: string;
    required: boolean;
};
export type ScanInputNode = {
    type: "scanInput";
    attrs: ScanInputAttrs;
};

/** Generic file upload. Writes to `SubstepResponse` (kind='file') + `Documents`. */
export type FileCaptureAttrs = {
    node_id: string;
    label: string;
    required: boolean;
};
export type FileCaptureNode = {
    type: "fileCapture";
    attrs: FileCaptureAttrs;
};

/**
 * Countdown / stopwatch timer. Writes to `SubstepResponse` (kind='timer').
 *
 * Authoring: engineer sets `duration_seconds` and `direction`.
 * Operator: clicks Start; node tracks `{started_at, completed_at, elapsed_seconds}`.
 */
export type TimerDirection = "countdown" | "stopwatch";
export type TimerAttrs = {
    node_id: string;
    label: string;
    duration_seconds: number;
    direction: TimerDirection;
    required: boolean;
};
export type TimerNode = {
    type: "timer";
    attrs: TimerAttrs;
};

/** A declared variable on a ComputedValue node. */
export type ComputedVariable = {
    name: string;
    label: string;
    unit: string;
};

/**
 * Variables-plus-formula calculator (True Position, Concentricity, etc.).
 * Writes to `SubstepResponse` (kind='computed').
 *
 * Spec language matches MeasurementInput: in-spec iff result is in
 * `[nominal - (lower_tol ?? ∞), nominal + (upper_tol ?? ∞)]`. Null `nominal`
 * disables the spec check (informational result only).
 *
 * Formula is evaluated client-side via `expr-eval` with a ~100ms execution
 * cap (mitigates pathological author-authored formulas).
 */
export type ComputedValueAttrs = {
    node_id: string;
    label: string;
    variables: ComputedVariable[];
    /** Expression referencing variables by name (e.g. "2 * sqrt(X^2 + Y^2)"). */
    formula: string;
    result_label: string;
    result_unit: string;
    nominal: number | null;
    upper_tol: number | null;
    lower_tol: number | null;
    /** Decimal places shown for the result (0–10). */
    display_precision: number;
    required: boolean;
};
export type ComputedValueNode = {
    type: "computedValue";
    attrs: ComputedValueAttrs;
};

// ============================================================================
// Per-execution response shapes
//
// What the operator-side response store holds, keyed by node_id. The
// production schema persists these as rows in SubstepResponse /
// SubstepGateCompletion / StepExecutionMeasurement depending on the kind.
// ============================================================================

/** Captured by `AttestationCheckpoint(kind='confirm')`. */
export type AttestationConfirmResponse = boolean;
/** Captured by `AttestationCheckpoint(kind='signature')`. ISO 8601 timestamp or signature blob. */
export type AttestationSignatureResponse = string;

/** Captured by `MeasurementInput`. Raw string preserves "0." / "0.0" mid-typing. */
export type MeasurementInputResponse = string;

/** Captured by `TextInput` / `ScanInput`. */
export type TextResponse = string;

/** Captured by `ChoiceInput`. The selected option (one of `attrs.options`). */
export type ChoiceResponse = string;

/** Captured by `PhotoCapture` / `FileCapture`. File name or Documents row id. */
export type FileLikeResponse = string;

/** Captured by `Timer` on Stop / auto-complete. */
export type TimerResponse = {
    started_at: string;
    completed_at: string;
    elapsed_seconds: number;
    direction: TimerDirection;
};

/** Captured by `ComputedValue`. */
export type ComputedValueResponse = {
    /** Raw operator-typed strings per variable name. Numeric conversion happens at eval time. */
    inputs: Record<string, string>;
    /** Result of formula evaluation; null when inputs incomplete or formula crashes. */
    result: number | null;
    /** True iff result is within spec; null when no spec set or result null. */
    in_spec: boolean | null;
};

/** Discriminated union of every response shape, addressed by node kind. */
export type DwiNodeResponse =
    | AttestationConfirmResponse
    | AttestationSignatureResponse
    | MeasurementInputResponse
    | TextResponse
    | ChoiceResponse
    | FileLikeResponse
    | TimerResponse
    | ComputedValueResponse;

/**
 * Operator response store shape: keyed by `node_id` across all capture nodes
 * in the substep. Stays in client memory until batch-post on Complete Substep
 * per architectural decision #19 (batch-on-complete).
 */
export type OperatorResponseStore = Record<string, DwiNodeResponse>;

// ============================================================================
// can_complete_substep contract
//
// Mirrors the server-side return shape from
// `services/mes/substeps.py::can_complete_substep`. The client-side
// pre-validation uses the same shape so the operator UX can scroll-to and
// highlight specific blocked nodes before the batch is posted.
// ============================================================================

export type CompletionBlockKind =
    | "missing_required_value"
    | "missing_signature"
    | "incomplete_timer"
    | "incomplete_choice"
    | "missing_attestation"
    | "missing_upload"
    | "missing_computed_inputs"
    | "computed_formula_error"
    | "missing_substep_signature";

/**
 * A single reason a substep can't be completed. Client uses `node_id` for
 * scroll-to-highlight and `label` for the inline error message; server uses
 * the same shape to reject the batch post.
 */
export type CompletionBlock = {
    /** node_id of the blocked node, or null for substep-level blocks. */
    node_id: string | null;
    kind: CompletionBlockKind;
    label: string;
};