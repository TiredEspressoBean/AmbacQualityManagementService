/**
 * Maps a substep's `body_blocks` + the operator's `OperatorResponseContext`
 * payload into the array of `captures` the backend's
 * `POST /api/Substeps/{id}/submit/` endpoint expects.
 *
 * The backend doesn't introspect the TipTap doc — the frontend already
 * knows which node type each `node_id` belongs to, so we translate here
 * and the backend just routes by `kind`.
 *
 * Why split this out: the operator runtime page would otherwise have to
 * know every capture-node shape. Centralizing the mapping makes adding
 * new structured-capture nodes a single-file change.
 */
import type { OperatorResponses } from "@/components/dwi/shared/OperatorResponseContext";

// ---------------------------------------------------------------------------
// Required-field validation
// ---------------------------------------------------------------------------

export type MissingRequired = {
    node_id: string;
    type: string;
    label: string;
    reason: string;
};

/** Walk the substep's body and return the list of required capture nodes
 *  that have no satisfactory response yet. Used by the operator runtime
 *  to block "Confirm & next" until the operator has filled what the
 *  engineer marked required.
 *
 *  "Satisfactory" is per-kind:
 *  - text / choice / scan / photo / file: non-empty string
 *  - measurement: non-empty value
 *  - timer: a captured response (operator actually ran the timer)
 *  - computed: every declared variable has an input value
 *  - attestation (confirm): boolean true
 *  - attestation (signature): a SignaturePayload object
 *  - status: non-empty string
 *  - equipment_roles / personnel_roles / defects: array with at least one row
 *  - signatures: at minimum the `detected` slot when require_detected=true
 *  - part_annotation: counted as filled if the node exists (PartAnnotator
 *    persists side-channel; we don't see it in OperatorResponseContext)
 */
export function findMissingRequired(
    body: object | undefined,
    responses: OperatorResponses,
): MissingRequired[] {
    const nodes = collectCaptureNodes(body);
    const out: MissingRequired[] = [];
    for (const { type, attrs } of nodes) {
        const required = attrs.required === true;
        const requireDetected = attrs.require_detected === true; // signatures
        const isSignatures = type === "inspectionSignatures";
        // Skip nodes that are neither required nor have a sub-required flag.
        if (!required && !(isSignatures && requireDetected)) continue;

        const node_id = attrs.node_id as string;
        const label = (attrs.label as string) || type;
        const response = responses[node_id];
        const reason = checkSatisfied(type, attrs, response);
        if (reason !== null) {
            out.push({ node_id, type, label, reason });
        }
    }
    return out;
}

function checkSatisfied(
    type: string,
    attrs: Record<string, unknown>,
    response: unknown,
): string | null {
    switch (type) {
        case "textInput":
        case "choiceInput":
        case "scanInput":
            return typeof response === "string" && response.trim() !== ""
                ? null
                : "No value captured";

        case "photoCapture":
        case "fileCapture": {
            // Satisfied by either a non-empty legacy filename string or
            // an upload response object carrying `document_id` / `file_name`.
            if (typeof response === "string") {
                return response.trim() !== "" ? null : "No file uploaded";
            }
            if (response && typeof response === "object") {
                const r = response as { document_id?: string; file_name?: string };
                return r.document_id || (r.file_name && r.file_name.trim() !== "")
                    ? null
                    : "No file uploaded";
            }
            return "No file uploaded";
        }

        case "measurementInput":
            return typeof response === "string" && response.trim() !== ""
                ? null
                : "No measurement recorded";

        case "timer": {
            // Operator must have actually run the timer (captured response).
            return response && typeof response === "object" ? null : "Timer not run";
        }

        case "computedValue": {
            const variables = (attrs.variables as Array<{ name: string }> | undefined) ?? [];
            const inputs =
                (response as { inputs?: Record<string, string> } | undefined)?.inputs ?? {};
            const missing = variables.filter(
                (v) => !(v.name in inputs) || inputs[v.name] === "",
            );
            return missing.length === 0
                ? null
                : `Missing variables: ${missing.map((v) => v.name).join(", ")}`;
        }

        case "attestationCheckpoint": {
            const kind = attrs.kind as string | undefined;
            if (kind === "signature") {
                return response && typeof response === "object"
                    ? null
                    : "Not signed";
            }
            return response === true ? null : "Not confirmed";
        }

        case "qualityStatusField":
            return typeof response === "string" && response !== ""
                ? null
                : "Status not picked";

        case "equipmentRolesField":
        case "personnelRolesField":
        case "errorTypesField": {
            const minRows = (attrs.min_rows as number | undefined) ?? 1;
            const rows = Array.isArray(response) ? response : [];
            return rows.length >= minRows
                ? null
                : `Needs at least ${minRows} row${minRows === 1 ? "" : "s"}`;
        }

        case "inspectionSignatures": {
            const requireDetected = attrs.require_detected === true;
            const requireVerified = attrs.require_verified === true;
            const r = (response as { detected?: unknown; verified?: unknown } | undefined) ?? {};
            if (requireDetected && !r.detected) return "Detected-by signature missing";
            if (requireVerified && !r.verified) return "Verified-by signature missing";
            return null;
        }

        case "partAnnotation":
            // PartAnnotator persists side-channel; treat as filled if the
            // node exists. Operator-runtime polish for "annotation count >= N"
            // is follow-up work.
            return null;

        default:
            return null;
    }
}

// ---------------------------------------------------------------------------
// Human-readable summary for the review screen
// ---------------------------------------------------------------------------

export type CaptureSummary = {
    node_id: string;
    type: string;
    label: string;
    /** One-line, operator-readable rendering of the recorded value. */
    display: string;
    /** True when the operator has no response for this capture node. */
    empty: boolean;
};

function trimVal(s: string, max = 80): string {
    if (s.length <= max) return s;
    return s.slice(0, max - 1) + "…";
}

function summarizeOne(
    type: string,
    attrs: Record<string, unknown>,
    response: unknown,
): string {
    if (response === undefined || response === null || response === "") {
        return "—";
    }
    switch (type) {
        case "textInput":
        case "choiceInput":
        case "scanInput":
            return typeof response === "string" ? trimVal(response) : "—";

        case "photoCapture":
        case "fileCapture": {
            const icon = type === "photoCapture" ? "📷" : "📎";
            if (typeof response === "string") {
                return response ? `${icon} ${trimVal(response, 60)}` : "—";
            }
            if (response && typeof response === "object") {
                const r = response as { document_id?: string; file_name?: string };
                if (r.file_name) return `${icon} ${trimVal(r.file_name, 60)}`;
                if (r.document_id) return `${icon} document ${r.document_id.slice(0, 8)}…`;
            }
            return "—";
        }

        case "measurementInput": {
            const unit = (attrs.unit as string) || "";
            if (response === "PASS" || response === "FAIL") return String(response);
            return typeof response === "string"
                ? `${response}${unit ? " " + unit : ""}`
                : "—";
        }

        case "timer": {
            const r = response as {
                elapsed_seconds?: number;
                direction?: string;
            };
            if (typeof r.elapsed_seconds !== "number") return "—";
            const m = Math.floor(r.elapsed_seconds / 60);
            const s = Math.round(r.elapsed_seconds % 60);
            const mmss = `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
            return r.direction ? `${mmss} (${r.direction})` : mmss;
        }

        case "computedValue": {
            const r = response as {
                result?: number | null;
                in_spec?: boolean | null;
                inputs?: Record<string, string>;
            };
            const unit = (attrs.result_unit as string) || "";
            const precision = Number.isFinite(attrs.display_precision)
                ? Math.max(0, Math.min(10, Number(attrs.display_precision)))
                : 4;
            const resultStr =
                typeof r.result === "number"
                    ? `${r.result.toFixed(precision)}${unit ? " " + unit : ""}`
                    : "—";
            const spec =
                r.in_spec === true
                    ? " · in spec"
                    : r.in_spec === false
                        ? " · OUT OF SPEC"
                        : "";
            return `${resultStr}${spec}`;
        }

        case "attestationCheckpoint": {
            const kindAttr = attrs.kind as string | undefined;
            if (kindAttr === "signature") {
                const r = response as { signer_name?: string; signed_at?: string };
                return r.signer_name
                    ? `Signed by ${r.signer_name}`
                    : "Signed";
            }
            return response === true ? "Confirmed" : "—";
        }

        case "qualityStatusField":
            return typeof response === "string" ? response : "—";

        case "equipmentRolesField":
        case "personnelRolesField":
        case "errorTypesField": {
            const rows = Array.isArray(response) ? response : [];
            if (rows.length === 0) return "—";
            const noun =
                type === "equipmentRolesField"
                    ? "equipment"
                    : type === "personnelRolesField"
                        ? "person"
                        : "defect";
            return `${rows.length} ${noun}${rows.length === 1 ? "" : "s"} recorded`;
        }

        case "inspectionSignatures": {
            const r = response as { detected?: unknown; verified?: unknown };
            const parts: string[] = [];
            if (r.detected) parts.push("detected ✓");
            if (r.verified) parts.push("verified ✓");
            return parts.length ? parts.join(" · ") : "—";
        }

        case "partAnnotation":
            return "Annotation recorded";

        default:
            // Best-effort fallback for unknown capture kinds.
            if (typeof response === "string") return trimVal(response);
            if (typeof response === "number" || typeof response === "boolean")
                return String(response);
            return "(captured)";
    }
}

/** Walks the substep body and produces one row per capture node, with a
 *  human-readable rendering of the operator's response. The review screen
 *  uses this to surface actual values instead of just a count. */
export function summarizeResponses(
    body: object | undefined,
    responses: OperatorResponses,
): CaptureSummary[] {
    const nodes = collectCaptureNodes(body);
    return nodes.map(({ type, attrs }) => {
        const node_id = attrs.node_id as string;
        const label = (attrs.label as string) || type;
        const response = responses[node_id];
        const empty = response === undefined || response === null || response === "";
        return {
            node_id,
            type,
            label,
            display: summarizeOne(type, attrs, response),
            empty,
        };
    });
}

type TipTapNode = {
    type?: string;
    attrs?: Record<string, unknown> & { node_id?: string };
    content?: TipTapNode[];
};

type Capture = Record<string, unknown> & { node_id: string; kind: string };

/** Walks the doc collecting nodes that have a `node_id` attr. */
function collectCaptureNodes(root: TipTapNode | object | undefined): Array<{
    type: string;
    attrs: Record<string, unknown>;
}> {
    const out: Array<{ type: string; attrs: Record<string, unknown> }> = [];
    const walk = (n: TipTapNode | undefined) => {
        if (!n || typeof n !== "object") return;
        const attrs = n.attrs;
        if (attrs && typeof attrs.node_id === "string" && n.type) {
            out.push({ type: n.type, attrs: attrs as Record<string, unknown> });
        }
        if (Array.isArray(n.content)) n.content.forEach(walk);
    };
    walk(root as TipTapNode);
    return out;
}

export function buildCaptures(
    body: object | undefined,
    responses: OperatorResponses,
): Capture[] {
    const nodes = collectCaptureNodes(body);
    const captures: Capture[] = [];

    for (const { type, attrs } of nodes) {
        const node_id = attrs.node_id as string;
        const response = responses[node_id];
        if (response === undefined || response === null) continue;

        switch (type) {
            case "textInput":
            case "choiceInput":
            case "scanInput": {
                if (typeof response !== "string") break;
                const kind =
                    type === "textInput"
                        ? "text"
                        : type === "choiceInput"
                            ? "choice"
                            : "scan";
                captures.push({ node_id, kind, value_text: response });
                break;
            }

            case "photoCapture":
            case "fileCapture": {
                // Operator response is either a legacy filename string OR
                // an object `{ document_id, file_name }` once the file has
                // been uploaded to `/api/Documents/`. Send `document_id`
                // when present so the SubstepResponse FK lands on a real
                // Documents row; fall back to `value_text` for the legacy
                // case (used while an upload is in flight).
                const kind = type === "photoCapture" ? "photo" : "file";
                if (typeof response === "string") {
                    captures.push({ node_id, kind, value_text: response });
                } else if (response && typeof response === "object") {
                    const r = response as { document_id?: string; file_name?: string };
                    captures.push({
                        node_id,
                        kind,
                        ...(r.document_id ? { document_id: r.document_id } : {}),
                        ...(r.file_name ? { value_text: r.file_name } : {}),
                    });
                }
                break;
            }

            case "timer":
            case "computedValue": {
                if (typeof response !== "object") break;
                captures.push({
                    node_id,
                    kind: type === "timer" ? "timer" : "computed",
                    value_json: response as Record<string, unknown>,
                });
                break;
            }

            case "attestationCheckpoint": {
                const kindAttr = attrs.kind as string | undefined;
                if (kindAttr === "signature") {
                    if (typeof response !== "object") break;
                    captures.push({
                        node_id,
                        kind: "attestation",
                        signature: response as Record<string, unknown>,
                    });
                } else {
                    captures.push({
                        node_id,
                        kind: "attestation",
                        confirm: Boolean(response),
                    });
                }
                break;
            }

            case "measurementInput": {
                if (typeof response !== "string") break;
                const md_id = attrs.measurement_definition_id;
                const parsed = response === "" ? null : Number(response);
                const isPassFail = response === "PASS" || response === "FAIL";
                captures.push({
                    node_id,
                    kind: "measurement",
                    measurement_definition_id: md_id ?? null,
                    value_numeric:
                        parsed != null && Number.isFinite(parsed) ? parsed : null,
                    value_string: isPassFail ? response : "",
                });
                break;
            }

            case "qualityStatusField": {
                if (typeof response !== "string") break;
                captures.push({ node_id, kind: "status", status: response });
                break;
            }

            case "equipmentRolesField": {
                if (!Array.isArray(response)) break;
                captures.push({ node_id, kind: "equipment_roles", rows: response });
                break;
            }

            case "personnelRolesField": {
                if (!Array.isArray(response)) break;
                captures.push({ node_id, kind: "personnel_roles", rows: response });
                break;
            }

            case "inspectionSignatures": {
                if (typeof response !== "object") break;
                const r = response as { detected?: unknown; verified?: unknown };
                captures.push({
                    node_id,
                    kind: "signatures",
                    detected: r.detected ?? null,
                    verified: r.verified ?? null,
                });
                break;
            }

            case "errorTypesField": {
                if (!Array.isArray(response)) break;
                captures.push({ node_id, kind: "defects", rows: response });
                break;
            }

            case "partAnnotation": {
                // PartAnnotator persists HeatMapAnnotation rows directly,
                // so this is just a marker that the capture happened. The
                // OperatorResponseContext for this node may not even have
                // a value — we still surface the node so the SubstepResponse
                // row records the engineer's intent.
                captures.push({
                    node_id,
                    kind: "annotation",
                    model_id: attrs.model_id,
                });
                break;
            }
        }
    }

    return captures;
}
